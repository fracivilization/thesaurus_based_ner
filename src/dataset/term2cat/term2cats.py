from typing import Dict, List, Set, Tuple
from seqeval.metrics.sequence_labeling import get_entities
from hydra.utils import get_original_cwd, to_absolute_path
from hashlib import md5
import os
from dataclasses import dataclass
from omegaconf import MISSING
from collections import defaultdict
import re
from tqdm import tqdm
from src.utils.string_match import ComplexKeywordTyper
from hydra.core.config_store import ConfigStore
from datasets import DatasetDict
from collections import Counter
from prettytable import PrettyTable
from src.dataset.utils import (
    tui2ST,
    MRCONSO,
    MRSTY,
    get_ascendant_tuis,
    get_ascendant_dbpedia_thesaurus_node,
)
from src.dataset.utils import ST21pvSrc
from functools import lru_cache
import json

DBPedia_dir = "data/DBPedia"
# DBPedia(Wikipedia)
DBPedia_ontology = os.path.join(DBPedia_dir, "ontology--DEV_type=parsed_sorted.nt")
DBPedia_instance_type = os.path.join(DBPedia_dir, "instance-types_lang=en_specific.ttl")
DBPedia_mapping_literals = os.path.join(
    DBPedia_dir, "mappingbased-literals_lang=en.ttl"
)
DBPedia_infobox = os.path.join(DBPedia_dir, "infobox-properties_lang=en.ttl")
DBPedia_redirect = os.path.join(DBPedia_dir, "redirects_lang=en.ttl")
DBPedia_disambiguate = os.path.join(DBPedia_dir, "disambiguations_lang=en.ttl")
DBPedia_labels = os.path.join(DBPedia_dir, "labels_lang=en.ttl")
# DBPedia (Wikidata)
DBPedia_WD_instance_type = os.path.join(DBPedia_dir, "instance-types_specific.ttl")
DBPedia_WD_SubClassOf = os.path.join(DBPedia_dir, "ontology-subclassof.ttl")
DBPedia_WD_labels = os.path.join(DBPedia_dir, "labels.ttl")
DBPedia_WD_alias = os.path.join(DBPedia_dir, "alias.ttl")


@dataclass
class Term2CatsConfig:
    name: str = MISSING
    output: str = MISSING


@dataclass
class DictTerm2CatsConfig(Term2CatsConfig):
    name: str = "dict"
    knowledge_base: str = "UMLS"
    remain_common_sense: bool = (
        True  # 複数のエンティティから共通のカテゴリのみを利用する。Falseの場合KBに含まれる全ての語義（カテゴリ）を残す
    )
    output: str = MISSING


@dataclass
class OracleTerm2CatsConfig(Term2CatsConfig):
    name: str = "oracle"
    gold_dataset: str = MISSING
    output: str = MISSING


def register_term2cat_configs(group="ner_model/typer/term2cat") -> None:
    cs = ConfigStore.instance()
    cs.store(
        group=group,
        name="base_DictTerm2Cats_config",
        node=DictTerm2CatsConfig,
    )
    cs.store(
        group=group,
        name="base_OracleTerm2Cats_config",
        node=OracleTerm2CatsConfig,
    )


def get_anomaly_suffixes(term2cat):
    buffer_file = os.path.join(
        get_original_cwd(),
        "data/buffer/%s"
        % md5(("anomaly_suffixes" + str(term2cat)).encode()).hexdigest(),
    )
    anomaly_suffixes = set()
    complex_typer = ComplexKeywordTyper(term2cat)
    lowered2orig = defaultdict(list)
    for term in term2cat:
        lowered2orig[term.lower()].append(term)
    for term, cat in term2cat.items():
        confirmed_common_suffixes = complex_typer.get_confirmed_common_suffixes(term)
        for pred_cat, start in confirmed_common_suffixes:
            if pred_cat != cat and start != 0:
                anomaly_suffix = term[start:]
                lowered2orig[anomaly_suffix]
                for orig_term in lowered2orig[anomaly_suffix]:
                    anomaly_suffixes.add(orig_term)
    return anomaly_suffixes


def load_term2cuis():
    term2cuis = defaultdict(set)
    # 相対パスではうまくとれないのでプロジェクトルートから取れるようにする
    with open(os.path.join(get_original_cwd(), MRCONSO)) as f:
        for line in tqdm(f, total=16132274):
            (
                cui,
                lang,
                _,
                _,
                _,
                _,
                _,
                _,
                _,
                _,
                _,
                src,
                _,
                _,
                term,
                _,
                _,
                _,
                _,
            ) = line.strip().split("|")
            if lang == "ENG" and src in ST21pvSrc:
                term2cuis[term].add(cui)
    return term2cuis


@lru_cache(maxsize=None)
def load_cui2tuis() -> Dict:
    cui2tuis = defaultdict(set)
    cui_loc = 0
    tui_loc = 1
    with open(os.path.join(get_original_cwd(), MRSTY)) as f:
        for line in f:
            line = line.strip().split("|")
            cui = line[cui_loc]
            tui = line[tui_loc]
            cui2tuis[cui].add(tui)
    return cui2tuis


def expand_tuis(tuis: Set[str]) -> Set:
    # 1. シソーラスの構造に応じてラベル集合L={l_i}_iをパスに展開
    #    各ラベルまでのパス上にあるノードをすべて集める
    #    PATHS = {l \in PATH(l_i)}_{i in L}
    expanded_tuis = set()
    for tui in tuis:
        expanded_tuis |= set(get_ascendant_tuis(tui))
    return expanded_tuis


def cuis2labels(cuis: List[str], config: DictTerm2CatsConfig):
    cui2tuis = load_cui2tuis()
    if config.remain_common_sense:
        labels = tui2ST.keys()
        # 各CUI:j は複数のラベルからなるラベル集合L_j={l_{ij}}を持つとしたときに
        # すべてのCUIのPATHSに含まれるラベル集合を取得する
    else:
        labels = set()
        # 各CUI:j は複数のラベルからなるラベル集合L_j={l_{ij}}を持つとしたときに
        # いずれかのCUIのPATHSに含まれるラベル集合を取得する

    for cui in cuis:
        tuis = cui2tuis[cui]
        if config.remain_common_sense:
            labels &= expand_tuis(tuis)
        else:
            labels |= expand_tuis(tuis)
    return labels


def load_ambiguous2monosemies_in_dbpedia() -> Dict[str, Set[str]]:
    un_disambiguate = defaultdict(set)
    pattern = (
        "(<[^>]+>) "
        + "<http://dbpedia.org/ontology/wikiPageDisambiguates> "
        + "(<[^>]+>) ."
    )
    pattern = re.compile(pattern)
    disambiguated_entities = set()
    ambiguous_entities = set()
    with open(to_absolute_path(DBPedia_disambiguate)) as f:
        for line in tqdm(f, total=1984950):
            assert pattern.match(line)
            ambiguous_entity, disambiguated_entity = pattern.findall(line)[0]
            disambiguated_entities.add(disambiguated_entity)
            ambiguous_entities.add(ambiguous_entity)
            un_disambiguate[disambiguated_entity].add(ambiguous_entity)
    # NOTE: ambiguateなentityをdisambiguated entitiesに紐付けるmapをつくる
    ambiguous2monosemies = defaultdict(set)
    # NOTE: leafノード全てに対してルートまでのパスに存在する全てのノードと紐付ける
    monosemy_entities = disambiguated_entities - ambiguous_entities
    for monosemy_entity in tqdm(monosemy_entities):
        # 曖昧語と曖昧性解消語を辺とするentity上の木構造からmonosemy_entityより曖昧なエンティティを取得する
        ambigous_ascendants = set()
        search_target_entities = {monosemy_entity}
        next_search_target_entities = set()
        while search_target_entities:
            for search_target_entity in search_target_entities:
                if search_target_entity in un_disambiguate:
                    more_ambiguous_entities = un_disambiguate[search_target_entity]
                    for more_ambiguous_entity in more_ambiguous_entities:
                        if more_ambiguous_entity not in ambigous_ascendants:
                            ambigous_ascendants.add(more_ambiguous_entity)
                            next_search_target_entities.add(more_ambiguous_entity)
            search_target_entities = next_search_target_entities
            next_search_target_entities = set()
        for ambiguous_ascendant in ambigous_ascendants:
            ambiguous2monosemies[ambiguous_ascendant].add(monosemy_entity)
    return ambiguous2monosemies


def load_term2dbpedia_entities():
    term2entities = defaultdict(set)
    # 基本的にはlabels.ttlからterm2entitiesを取得する

    # Wikipdiaに含まれるentityだけ考慮する。Wikidataに含まれるだけのものはとりあえず考慮しない
    pattern = (
        "(<http://dbpedia.org/resource/[^>]+>) "
        + "<http://www.w3.org/2000/01/rdf-schema#label>"
        + ' "([^"]+)"@en .'
    )
    pattern = re.compile(pattern)
    entity2term = dict()
    with open(to_absolute_path(DBPedia_labels)) as f:
        for i, line in enumerate(tqdm(f, total=16751238)):
            if pattern.match(line):
                disambiguated_entity, term = pattern.findall(line)[0]
                term2entities[term].add(disambiguated_entity)
                assert disambiguated_entity not in entity2term
                entity2term[disambiguated_entity] = term
    # NOTE: 曖昧語によってterm2entitiesを拡張する。
    # NOTE: 例えば"はし"は「橋」か「箸」という曖昧性がある
    # NOTE: そこでterm2entitiesにはし->「橋」・「箸」という対応を追加する
    # そこで、entity2termに含まれる曖昧性のないエンティティ「箸」・「橋」に対して
    # もしそのエンティティが曖昧性解消の結果として現れるならば、「はし」という別の呼称をついかする
    # つまり曖昧性解消の逆を行う
    # NOTE: ambiguousなentityの全てに対して、その名前とdisambiguated enttiesの対応をterm2entitiesに追加し、
    ambiguous2monosemies = load_ambiguous2monosemies_in_dbpedia()
    for (
        ambiguous_entity,
        correspond_monosemy_entities,
    ) in ambiguous2monosemies.items():
        if ambiguous_entity in entity2term:
            ambiguous_term = entity2term[ambiguous_entity]
            assert term2entities[ambiguous_term] == {ambiguous_entity}
            term2entities[ambiguous_term] = correspond_monosemy_entities
        else:
            # 本来はここを通らないはずだが一旦動作検証のために素通りさせる
            print(
                "ambiguous entity: ", ambiguous_entity, "isn't included in entity2term."
            )
    return term2entities


@lru_cache(maxsize=None)
def load_dbpedia_entity2cats() -> Dict:
    entity2cats = defaultdict(set)
    with open(to_absolute_path(DBPedia_instance_type)) as f:
        for line in tqdm(f, total=7636009):
            # 例: line = "<http://dbpedia.org/resource/'Ara'ir> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://dbpedia.org/ontology/Settlement> ."
            line = line.strip().split()
            assert len(line) == 4
            assert line[1] == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
            entity, _, cat, _ = line
            entity2cats[entity].add(cat)
    # Expand Wikipedia Articles using Redirect
    with open(to_absolute_path(DBPedia_redirect)) as f:
        for line in tqdm(f, total=10338969):
            line = line.strip().split()
            assert len(line) == 4
            assert line[1] == "<http://dbpedia.org/ontology/wikiPageRedirects>"
            entity, _, redirect, _ = line
            if entity not in entity2cats:
                entity2cats[entity] |= entity2cats[redirect]
            else:
                # print(entity, " is already included entity2cats, but also in redirect.")
                pass
    return entity2cats


def expand_dbpedia_cats(cats: Set[str]) -> Set:
    # 1. シソーラスの構造に応じてラベル集合L={l_i}_iをパスに展開
    #    各ラベルまでのパス上にあるノードをすべて集める
    #    PATHS = {l \in PATH(l_i)}_{i in L}
    expanded_cats = set()
    for cat in cats:
        expanded_cats |= set(get_ascendant_dbpedia_thesaurus_node(cat))
    return expanded_cats


def dbpedia_entities2labels(entities: Tuple[str], config: DictTerm2CatsConfig):
    entity2cats = load_dbpedia_entity2cats()
    for i, entity in enumerate(entities):
        cats = entity2cats[entity]
        if i == 0:
            labels = expand_dbpedia_cats(cats)
        else:
            if config.remain_common_sense:
                # 各CUI:j は複数のラベルからなるラベル集合L_j={l_{ij}}を持つとしたときに
                # すべてのCUIのPATHSに含まれるラベル集合を取得する
                labels &= expand_dbpedia_cats(cats)
            else:
                # 各CUI:j は複数のラベルからなるラベル集合L_j={l_{ij}}を持つとしたときに
                # いずれかのCUIのPATHSに含まれるラベル集合を取得する
                labels |= expand_dbpedia_cats(cats)
    return labels


def load_dict_term2cats(conf: DictTerm2CatsConfig):
    term2cats = dict()
    if conf.knowledge_base == "UMLS":

        # 1. 表層形からCUIへのマップを構築し
        print("load term2cuis")
        term2cuis = load_term2cuis()
        # 2. CUI(の集合)からそれらの共通・合併成分をとる
        print("load intersection or union labels (tuis) for each cuis")
        for term, cuis in tqdm(term2cuis.items()):
            term2cats[term] = tuple(sorted(cuis2labels(cuis, conf)))
        return term2cats
    elif conf.knowledge_base == "DBPedia":
        # 1. 表層形からOntologyへのマップを構築し
        print("load term2entities")
        term2entities = load_term2dbpedia_entities()
        # 2. entity(の集合)からそれらの共通・合併成分をとる
        print("load intersection or union labels (ontology classes) for each entities")
        for term, entities in tqdm(term2entities.items()):
            cats = sorted(dbpedia_entities2labels(entities, conf))
            if cats:
                term2cats[term] = json.dumps(cats)
        load_dbpedia_entity2cats.cache_clear()
        return term2cats
    else:
        raise NotImplementedError


def load_oracle_term2cat(conf: OracleTerm2CatsConfig):
    gold_datasets = DatasetDict.load_from_disk(
        os.path.join(get_original_cwd(), conf.gold_dataset)
    )
    cat2terms = defaultdict(set)
    for key, split in gold_datasets.items():
        label_names = split.features["ner_tags"].feature.names
        for snt in split:
            for cat, s, e in get_entities(
                [label_names[tag] for tag in snt["ner_tags"]]
            ):
                term = " ".join(snt["tokens"][s : e + 1])
                cat2terms[cat].add(term)
    remove_terms = set()
    for i1, (c1, t1) in enumerate(cat2terms.items()):
        for i2, (c2, t2) in enumerate(cat2terms.items()):
            if i2 > i1:
                duplicated = t1 & t2
                if duplicated:
                    remove_terms |= duplicated
                    # for t in duplicated:
                    # term2cats[t] |= {c1, c2}
    term2cat = dict()
    for cat, terms in cat2terms.items():
        for non_duplicated_term in terms - remove_terms:
            term2cat[non_duplicated_term] = cat
    return term2cat


def load_term2cats(conf: Term2CatsConfig):
    if conf.name == "dict":
        term2cat = load_dict_term2cats(conf)
    elif conf.name == "oracle":
        term2cat = load_oracle_term2cat(conf)
    else:
        raise NotImplementedError
    return term2cat


def log_term2cats(term2cats: Dict):
    print("log term2cat count")
    tbl = PrettyTable(["cats", "count"])
    counter = Counter(term2cats.values())
    for cats, count in sorted(list(counter.items()), key=lambda x: x[0]):
        tbl.add_row([cats, count])
    print(tbl.get_string())
    print("category num: ", len(counter))

    cat2count = defaultdict(lambda: 0)
    for cats, count in sorted(list(counter.items()), key=lambda x: x[0]):
        for cat in cats:
            cat2count[cat] += count

    tbl = PrettyTable(["cat", "count"])
    for cat, count in cat2count.items():
        tbl.add_row([cat, count])
    print(tbl.get_string())
    print("category num: ", len(cat2count.keys()))
