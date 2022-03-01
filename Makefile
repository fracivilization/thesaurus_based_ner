# pseudo dataset related args
DBPEDIA_CATS = GeneLocation Species Disease Work SportsSeason Device Media SportCompetitionResult EthnicGroup Protocol Award Demographics MeanOfTransportation FileSystem Medicine Area Flag UnitOfWork MedicalSpecialty GrossDomesticProduct Biomolecule Identifier Blazon PersonFunction List TimePeriod Event Relationship Altitude TopicalConcept Spreadsheet Currency Cipher Browser Tank Food Depth Population Statistic StarCluster Language GrossDomesticProductPerCapita ChemicalSubstance ElectionDiagram Diploma Place Algorithm ChartsPlacements Unknown Activity PublicService Agent Name AnatomicalStructure Colour
UMLS_CATS = T000 T116 T020 T052 T100 T087 T011 T190 T008 T017 T195 T194 T123 T007 T031 T022 T053 T038 T012 T029 T091 T122 T023 T030 T026 T043 T025 T019 T103 T120 T104 T185 T201 T200 T077 T049 T088 T060 T056 T203 T047 T065 T069 T196 T050 T018 T071 T126 T204 T051 T099 T021 T013 T033 T004 T168 T169 T045 T083 T028 T064 T102 T096 T068 T093 T058 T131 T125 T016 T078 T129 T055 T197 T037 T170 T130 T171 T059 T034 T015 T063 T066 T074 T041 T073 T048 T044 T085 T191 T114 T070 T086 T057 T090 T109 T032 T040 T001 T092 T042 T046 T072 T067 T039 T121 T002 T101 T098 T097 T094 T080 T081 T192 T014 T062 T075 T089 T167 T095 T054 T184 T082 T024 T079 T061 T005 T127 T010
FOCUS_CATS ?= T005 T007 T017 T022 T031 T033 T037 T038 T058 T062 T074 T082 T091 T092 T097 T098 T103 T168 T170 T201 T204
NEGATIVE_CATS ?= T054 T055 T056 T064 T065 T066 T068 T075 T079 T080 T081 T099 T100 T101 T102 T171 T194 T200 $(DBPEDIA_CATS)
# WITH_NC ?= True
WITH_O ?= True
FIRST_STAGE_CHUNKER ?= enumerated # ２段階モデルの１段階目 擬似データの際のChunkerを意味しない
POSITIVE_RATIO_THR_OF_NEGATIVE_CAT ?= 1.0
O_SAMPLING_RATIO ?= 1.0
MSC_O_SAMPLING_RATIO ?= 1.0
UNDERSAMPLE_MSLC ?= False
TRAIN_SNT_NUM ?= 9223372036854775807
MSMLC_PN_RATIO_EQUIVALENCE ?= False
MSMLC_NEGATIVE_RATIO_OVER_POSITIVE ?= 0.8
FLATTEN_NER_THRESHOLD ?= 0.97

MSC_ARGS := "WITH_O: $(WITH_O) FIRST_STAGE_CHUNKER: $(FIRST_STAGE_CHUNKER) MSC_O_SAMPLING_RATIO: $(MSC_O_SAMPLING_RATIO)"
MSMLC_ARGS := "FIRST_STAGE_CHUNKER: $(FIRST_STAGE_CHUNKER) UNDERSAMPLE_MSLC: $(UNDERSAMPLE_MSLC) MSMLC_PN_RATIO_EQUIVALENCE: $(MSMLC_PN_RATIO_EQUIVALENCE) MSMLC_NEGATIVE_RATIO_OVER_POSITIVE: $(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE)"
FLATTEN_MSMLC_ARGS := "FLATTEN_NER_THRESHOLD: $(FLATTEN_NER_THRESHOLD) MSMLC_ARGS: $(MSMLC_ARGS)"

DATA_DIR := data
TERM2CAT_DIR := $(DATA_DIR)/term2cat

TERM2CAT := $(TERM2CAT_DIR)/$(firstword $(shell echo  "TERM2CAT" "FOCUS_CATS: $(FOCUS_CATS)" "NEGATIVE_CATS: $(NEGATIVE_CATS)" "POSITIVE_RATIO_THR_OF_NEGATIVE_CAT: ${POSITIVE_RATIO_THR_OF_NEGATIVE_CAT}" | sha1sum)).pkl
TERM2CATS_REMOVE_AMBIGUATE := True
UMLS_TERM2CATS := $(TERM2CAT_DIR)/$(firstword $(shell echo  "TERM2CATS" "FOCUS_CATS: $(UMLS_CATS)" "REMOVE_AMBIGUATE: $(TERM2CATS_REMOVE_AMBIGUATE)" | sha1sum)).pkl

PSEUDO_DATA_ARGS := $(TERM2CAT)
RUN_ARGS := $(O_SAMPLING_RATIO) $(FIRST_STAGE_CHUNKER)

APPEARED_CATS := $(FOCUS_CATS) $(NEGATIVE_CATS)
DICT_DIR := $(DATA_DIR)/dict
DICT_FILES := $(addprefix $(DICT_DIR)/,$(APPEARED_CATS))
UMLS_DICT_FILES := $(addprefix $(DICT_DIR)/,$(UMLS_CATS))
UMLS_DIR := $(DATA_DIR)/2021AA-full
DBPEDIA_DIR := $(DATA_DIR)/DBPedia
PubChem_DIR := $(DATA_DIR)/PubChem
RAW_SENTENCE_NUM := 50000
# APPEARED_CATS を使って 出力先のフォルダを決める
RAW_CORPUS_DIR := $(DATA_DIR)/raw
PUBMED := $(RAW_CORPUS_DIR)/pubmed
SOURCE_TXT_DIR := $(PUBMED)
RAW_CORPUS_OUT := $(RAW_CORPUS_DIR)/$(firstword $(shell echo $(RAW_CORPUS_NUM) | sha1sum))
PSEUDO_DATA_DIR := $(DATA_DIR)/pseudo
PSEUDO_NER_DATA_DIR := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo $(PSEUDO_DATA_ARGS) $(RAW_CORPUS_NUM) | sha1sum))
PSEUDO_MSC_NER_DATA_DIR := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "MSC DATASET" $(PSEUDO_NER_DATA_DIR) $(WITH_O) $(FIRST_STAGE_CHUNKER) | sha1sum)) 
PSEUDO_OUT := outputs/$(firstword $(shell echo "PSEUDO_OUT" $(PSEUDO_DATA_ARGS) | sha1sum))

GOLD_DIR := $(DATA_DIR)/gold
GOLD_DATA := $(GOLD_DIR)/$(firstword $(shell echo "MedMentions" $(FOCUS_CATS) $(TRAIN_SNT_NUM) | sha1sum))
GOLD_MSC_DATA := $(GOLD_DIR)/$(firstword $(shell echo "GOLD MSC DATA" $(GOLD_DATA) $(MSC_ARGS) | sha1sum)) 
GOLD_MULTI_LABEL_NER_DATA := $(GOLD_DIR)/multi_label_ner
GOLD_MSMLC_BINARY_DATA := $(GOLD_DIR)/$(firstword $(shell echo "GOLD MSMLC BINARY DATA" $(GOLD_DATA) $(MSMLC_ARGS) | sha1sum)) 
GOLD_MSMLC_DATA := $(GOLD_DIR)/$(firstword $(shell echo "GOLD MSMLC DATA" $(GOLD_DATA) $(MSMLC_ARGS) | sha1sum)) 
GOLD_TRAINED_MSMLC_BINARY_MODEL := $(DATA_DIR)/buffer/$(firstword $(shell echo "GOLD TRAINED MSMLC MODEL" $(GOLD_MSMLC_DATA) | sha1sum)) 
GOLD_TRAINED_MSMLC_MODEL := $(DATA_DIR)/buffer/$(firstword $(shell echo "GOLD TRAINED MSMLC MODEL" $(GOLD_MSMLC_DATA) | sha1sum)) 
GOLD_FLATTEN_MULTILABEL_NER_OUTPUT := $(DATA_DIR)/outputs/$(firstword $(shell echo "OUTPUTS Multi Label NER" $(GOLD_MSMLC_DATA) $(FOCUS_CATS) $(FLATTEN_NER_THRESHOLD) | sha1sum)) 

PSEUDO_DATA_BASE_CMD := poetry run python -m cli.preprocess.load_pseudo_ner \
		++ner_model.typer.term2cat=$(TERM2CAT) \
        +gold_corpus=$(GOLD_DATA)
MSC_DATA_BASE_CMD := poetry run python -m cli.preprocess.load_msc_dataset chunker=$(FIRST_STAGE_CHUNKER) ++with_o=$(WITH_O) ++o_sampling_ratio=$(MSC_O_SAMPLING_RATIO)
MSMLC_DATA_BASE_CMD := poetry run python -m cli.preprocess.load_msmlc_dataset +chunker=$(FIRST_STAGE_CHUNKER) ++under_sample=$(UNDERSAMPLE_MSLC) ++with_o=True
MSMLC_BINARY_DATA_BASE_CMD := poetry run python -m cli.preprocess.load_msmlc_dataset +chunker=$(FIRST_STAGE_CHUNKER) ++under_sample=$(UNDERSAMPLE_MSLC) ++with_o=False
FLATTEN_MULTILABEL_NER_BASE_CMD := poetry run python -m cli.train ner_model=flatten_ner \
		ner_model.focus_cats=$(subst $() ,_,$(FOCUS_CATS)) \
		ner_model/multi_label_ner_model=two_stage \
		+ner_model/multi_label_ner_model/chunker=$(FIRST_STAGE_CHUNKER) \
		+ner_model/multi_label_ner_model/multi_label_typer=enumerated \
		++ner_model.multi_label_ner_model.multi_label_typer.prediction_threshold=$(FLATTEN_NER_THRESHOLD) \
		testor.baseline_typer.term2cat=data/term2cat/8a23fbd2bc56b5182ab677063f52af0497d1d5c6.pkl
FLATTEN_MARGINAL_SOFTMAX_NER_BASE_CMD := poetry run python -m cli.train \
		ner_model=flatten_marginal_softmax_ner \
		ner_model.focus_cats=$(subst $() ,_,$(FOCUS_CATS)) \
		ner_model/multi_label_ner_model=two_stage \
		+ner_model/multi_label_ner_model/chunker=$(FIRST_STAGE_CHUNKER) \
		+ner_model/multi_label_ner_model/multi_label_typer=enumerated \
		testor.baseline_typer.term2cat=$(TERM2CAT) \
		++ner_model.multi_label_ner_model.multi_label_typer.train_args.do_train=False \
		++ner_model.multi_label_ner_model.multi_label_typer.model_output_path="no_output" \
		++msmlc_datasets=$(GOLD_MSMLC_DATA) \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.loss_func=MarginalCrossEntropyLoss

PSEUDO_DATA_ON_GOLD := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "PSEUDO_DATA_ON_GOLD" $(PSEUDO_DATA_ARGS) $(GOLD_DATA) | sha1sum)) 
PSEUDO_MSC_DATA_ON_GOLD := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "PSEUDO MSC DATASET ON GOLD" $(PSEUDO_DATA_ON_GOLD) $(MSC_ARGS) | sha1sum)) 
PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "PSEUDO MULTI LABEL NER DATASET ON GOLD" $(UMLS_TERM2CATS) | sha1sum)) 
PSEUDO_MSMLC_DATA_ON_GOLD := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "PSEUDO MSMLC DATASET ON GOLD" $(PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD) $(MSMLC_ARGS) | sha1sum))  
PSEUDO_ON_GOLD_FLATTEN_MULTILABEL_NER_OUTPUT := $(DATA_DIR)/outputs/$(firstword $(shell echo "OUTPUTS Multi Label NER" $(PSEUDO_MSMLC_DATA_ON_GOLD) $(FOCUS_CATS) $(FLATTEN_NER_THRESHOLD) | sha1sum)) 
PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "PSEUDO ON GOLD TRAINED MSMLC MODEL" $(PSEUDO_MSMLC_DATA_ON_GOLD) | sha1sum)) 
FP_REMOVED_PSEUDO_DATA := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "FP_REMOVED_PSEUDO_DATA" $(PSEUDO_DATA_ARGS) $(GOLD_DATA) | sha1sum))
EROSION_PSEUDO_DATA := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "EROSION_PSEUDO_DATA" $(PSEUDO_DATA_ARGS) $(GOLD_DATA) | sha1sum))
MISGUIDANCE_PSEUDO_DATA := $(PSEUDO_DATA_DIR)/$(firstword $(shell echo "MISGUIDANCE_PSEUDO_DATA" $(PSEUDO_DATA_ARGS) $(GOLD_DATA) | sha1sum))

TRAIN_ON_GOLD_OUT := outputs/$(firstword $(shell echo "TRAIN_ON_GOLD_LOCK" $(GOLD_MSC_DATA) $(RUN_ARGS) | sha1sum))
TRAIN_OUT := outputs/$(firstword $(shell echo "TRAIN_LOCK" $(PSEUDO_MSC_DATA_ON_GOLD) $(RUN_ARGS) | sha1sum))
TRAIN_AND_EVAL_MSMLC_OUT := outputs/$(firstword $(shell echo "TRAIN_AND_EVAL_MSMLC_OUT" $(PSEUDO_MSMLC_DATA_ON_GOLD) $(MSMLC_ARGS) | sha1sum))

TRAIN_BASE_CMD := poetry run python -m cli.train \
		++dataset.name_or_path=$(GOLD_DATA) \
		ner_model/chunker=$(FIRST_STAGE_CHUNKER) \
		ner_model.typer.model_args.o_sampling_ratio=$(O_SAMPLING_RATIO) \
		ner_model.typer.train_args.per_device_train_batch_size=8 \
		ner_model.typer.train_args.per_device_eval_batch_size=16 \
		ner_model.typer.train_args.do_train=True \
		ner_model.typer.train_args.overwrite_output_dir=True \
		testor.baseline_typer.term2cat=$(TERM2CAT)
test: 
	@echo MSC_O_SAMPLING_RATIO: $(MSC_O_SAMPLING_RATIO)
	@echo MSC_ARGS: $(MSC_ARGS)
term2cat: $(TERM2CAT)
	@echo TERM2CAT: $(TERM2CAT)


$(DATA_DIR):
	mkdir $(DATA_DIR)
$(DICT_DIR): $(DATA_DIR)
	mkdir -p $(DICT_DIR)
$(UMLS_DIR): $(DATA_DIR)
	@echo "Please Download UMLS2021AA full from https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html"
	@echo "You need UMLS Account, so please acces by web browser and mv the file into $(UMLS_DIR)"
	# unzip $(UMLS_DIR)/mmsys.zip
	@echo "Plaese refer to README.md"
$(DBPEDIA_DIR): $(DATA_DIR)
	mkdir -p $(DBPEDIA_DIR)
	# wget https://databus.dbpedia.org/ontologies/dbpedia.org/ontology--DEV/2021.07.09-070001/ontology--DEV_type=parsed_sorted.nt # DBPedia Ontlogy
	# # Wikipedia in DBPedia
	# wget https://databus.dbpedia.org/dbpedia/mappings/instance-types/2021.06.01/instance-types_lang=en_specific.ttl.bz2 # Wikipedia Articles Types
	# wget https://databus.dbpedia.org/dbpedia/generic/labels/2021.06.01/labels_lang=en.ttl.bz2 # Wikipedia Article Label
	# wget https://databus.dbpedia.org/dbpedia/mappings/mappingbased-literals/2021.06.01/mappingbased-literals_lang=en.ttl.bz2 ## Literals extracted with mappings 
	# wget https://databus.dbpedia.org/dbpedia/generic/infobox-properties/2021.06.01/infobox-properties_lang=en.ttl.bz2 ## Extracted facts from Wikipedia Infoboxes 
	# wget https://databus.dbpedia.org/dbpedia/generic/redirects/2021.06.01/redirects_lang=en.ttl.bz2	## redirects dataset
	# # Wikidata in DBPedia
	# wget https://databus.dbpedia.org/dbpedia/wikidata/instance-types/2021.06.01/instance-types_specific.ttl.bz2 # Type of Wikidata Instance
	# wget https://databus.dbpedia.org/dbpedia/wikidata/labels/2021.03.01/labels.ttl.bz2 # Wikidata Labels
	# wget https://databus.dbpedia.org/dbpedia/wikidata/ontology-subclassof/2021.02.01/ontology-subclassof.ttl.bz2 # Wikidata SubClassOf
	# wget https://databus.dbpedia.org/dbpedia/wikidata/alias/2021.02.01/alias.ttl.bz2 # Wikidata Alias
	# bunzip2 *.bz2
	# mv *.ttl $(DBPEDIA_DIR)
	# mv *.nt $(DBPEDIA_DIR)
$(PubChem_DIR): $(DATA_DIR)
	mkdir -p $(PubChem_DIR)
	wget https://ftp.ncbi.nlm.nih.gov/pubchem/Substance/CURRENT-Full/XML/
	FILES=`cat index.html  | grep xml.gz | grep -v md5| sed -e 's/<[^>]*>//g' | awk '{print $$1}'`
	for f in `cat index.html  | grep xml.gz | grep -v md5| sed -e 's/<[^>]*>//g' | awk '{print $1}'`; do 
		wget "https://ftp.ncbi.nlm.nih.gov/pubchem/Substance/CURRENT-Full/XML/${f}"
	done
	gunzip *.gz
	mv *.xml $(PubChem_DIR)/

$(TERM2CAT_DIR): $(DATA_DIR)
	mkdir -p $(TERM2CAT_DIR)
$(TERM2CAT): $(TERM2CAT_DIR) $(DICT_FILES)
	@echo TERM2CAT: $(TERM2CAT)
	poetry run python -m cli.preprocess.load_term2cat \
		output=$(TERM2CAT) \
		focus_cats=$(subst $() ,_,$(FOCUS_CATS)) \
		negative_cats=$(subst $() ,_,$(NEGATIVE_CATS)) \
		++positive_ratio_thr_of_negative_cat=${POSITIVE_RATIO_THR_OF_NEGATIVE_CAT}

$(PSEUDO_DATA_DIR): $(DATA_DIR)
	echo $(PSEUDO_DATA_DIR)
	mkdir -p $(PSEUDO_DATA_DIR)

$(GOLD_DIR): $(DATA_DIR)
	mkdir -p $(GOLD_DIR)
$(GOLD_DIR)/MedMentions: $(GOLD_DIR)
	# git clone https://github.com/chanzuckerberg/MedMentions
	# for f in `find MedMentions/ | grep gz`; do gunzip $$f; done
	# mv MedMentions $(GOLD_DIR)/MedMentions
	# cp data/gold/MedMentions/full/data/corpus_pubtator_pmids_trng.txt data/gold/MedMentions/st21pv/data/
	# cp data/gold/MedMentions/full/data/corpus_pubtator_pmids_dev.txt data/gold/MedMentions/st21pv/data/
	# cp data/gold/MedMentions/full/data/corpus_pubtator_pmids_test.txt data/gold/MedMentions/st21pv/data/
$(GOLD_DATA): $(GOLD_DIR)/MedMentions
	@echo "Gold Data"
	@echo GOLD_NER_DATA_DIR: $(GOLD_DATA)
	@poetry run python -m cli.preprocess.load_gold_ner --focus-cats $(subst $() ,_,$(FOCUS_CATS)) --output $(GOLD_DATA) --input-dir $(GOLD_DIR)/MedMentions/st21pv/data --train-snt-num $(TRAIN_SNT_NUM)
	poetry run python -m cli.preprocess.load_gold_ner --focus-cats $(subst $() ,_,$(FOCUS_CATS)) --output $(GOLD_DATA) --input-dir $(GOLD_DIR)/MedMentions/st21pv/data --train-snt-num $(TRAIN_SNT_NUM)
$(GOLD_MSC_DATA): $(GOLD_DATA)
	@echo GOLD_MSC_DATA_ON_GOLD: $(GOLD_MSC_DATA)
	$(MSC_DATA_BASE_CMD) \
		+ner_dataset=$(GOLD_DATA) \
		+output_dir=$(GOLD_MSC_DATA)


all: ${DICT_FILES} $(PSEUDO_NER_DATA_DIR) $(PSEUDO_MSC_NER_DATA_DIR) $(GOLD_DATA) $(GOLD_MSC_DATA) $(PSEUDO_DATA_ON_GOLD) $(PSEUDO_MSC_DATA_ON_GOLD) $(FP_REMOVED_PSEUDO_DATA)

$(DICT_FILES) $(UMLS_DICT_FILES): $(DICT_DIR) $(UMLS_DIR) $(DBPEDIA_DIR)
	@echo make dict files $@
	poetry run python -m cli.preprocess.load_terms --category $(notdir $@) --output $@

$(RAW_CORPUS_DIR):
	mkdir -p $(RAW_CORPUS_DIR)
$(PUBMED): $(RAW_CORPUS_DIR)
	# mkdir -p $(PUBMED)
	# for f in `seq -w 1062`; do wget https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/pubmed21n$$f.xml.gz ; gunzip pubmed21n$$f.xml.gz & done
	# mv pubmed21n*.xml $(PUBMED)
	# for f in `ls $(PUBMED)/pubmed21n*.xml`; do poetry run python -m cli.preprocess.load_pubmed_txt $$f & done
	

$(RAW_CORPUS_OUT): $(SOURCE_TXT_DIR)
	@echo raw sentence num: $(RAW_SENTENCE_NUM)
	@echo raw corpus out dir: $(RAW_CORPUS_OUT)
	poetry run python -m cli.preprocess.load_raw_corpus --raw-sentence-num $(RAW_SENTENCE_NUM) --source-txt-dir $(SOURCE_TXT_DIR) --output-dir $(RAW_CORPUS_OUT)

$(PSEUDO_NER_DATA_DIR): $(DICT_FILES) $(PSEUDO_DATA_DIR) $(GOLD_DATA) $(RAW_CORPUS_OUT) $(TERM2CAT)
	@echo make pseudo ner data from $(DICT_FILES)
	@echo focused categories: $(FOCUS_CATS)
	@echo negative categories: $(NEGATIVE_CATS)
	@echo PSEUDO_NER_DATA_DIR: $(PSEUDO_NER_DATA_DIR)
	$(PSEUDO_DATA_BASE_CMD) \
		+raw_corpus=$(RAW_CORPUS_OUT) \
		+output_dir=$(PSEUDO_NER_DATA_DIR)
$(PSEUDO_MSC_NER_DATA_DIR): $(PSEUDO_NER_DATA_DIR)
	@echo PSEUDO_MSC_NER_DATA_DIR: $(PSEUDO_MSC_NER_DATA_DIR)
	$(MSC_DATA_BASE_CMD) \
		+ner_dataset=$(PSEUDO_DATA_ON_GOLD) \
		+output_dir=$(PSEUDO_MSC_NER_DATA_DIR)

        
$(FP_REMOVED_PSEUDO_DATA): $(DICT_FILES) $(GOLD_DATA) $(PSEUDO_DATA_DIR) $(PSEUDO_NER_DATA_DIR) $(TERM2CAT)
	@echo make pseudo data whose FP is removed according to Gold dataset
	@echo make from Gold: $(GOLD_DATA)
	@echo focused categories: $(FOCUS_CATS)
	@echo negative categories: $(NEGATIVE_CATS)
	@echo FP_REMOVED_PSEUDO_DATA: $(FP_REMOVED_PSEUDO_DATA)
	$(PSEUDO_DATA_BASE_CMD) \
		+raw_corpus=$(GOLD_DATA) \
		+output_dir=$(FP_REMOVED_PSEUDO_DATA) \
		++remove_fp_instance=True

$(PSEUDO_DATA_ON_GOLD): $(GOLD_DATA) $(DICT_FILES) $(PSEUDO_DATA_DIR) $(PSEUDO_NER_DATA_DIR) $(TERM2CAT)
	@echo make pseudo data on Gold dataset for comparison
	@echo make from Gold: $(GOLD_DATA)
	@echo focused categories: $(FOCUS_CATS)
	@echo negative categories: $(NEGATIVE_CATS)
	@echo PSEUDO_DATA_ON_GOLD: $(PSEUDO_DATA_ON_GOLD)
	$(PSEUDO_DATA_BASE_CMD) \
		+raw_corpus=$(GOLD_DATA) \
		+output_dir=$(PSEUDO_DATA_ON_GOLD)
$(PSEUDO_MSC_DATA_ON_GOLD): $(PSEUDO_DATA_ON_GOLD)
	@echo PSEUDO_MSC_DATA_ON_GOLD: $(PSEUDO_MSC_DATA_ON_GOLD)
	$(MSC_DATA_BASE_CMD) \
		+ner_dataset=$(PSEUDO_DATA_ON_GOLD) \
		+output_dir=$(PSEUDO_MSC_DATA_ON_GOLD)

$(TRAIN_OUT): $(PSEUDO_MSC_DATA_ON_GOLD) $(TERM2CAT)
	$(TRAIN_BASE_CMD) \
		ner_model.typer.msc_datasets=$(PSEUDO_MSC_DATA_ON_GOLD) 2>&1 | tee $(TRAIN_OUT)
train: $(TRAIN_OUT)
	@echo TRAIN_OUT: $(TRAIN_OUT)

$(TRAIN_ON_GOLD_OUT): $(GOLD_MSC_DATA)
	$(TRAIN_BASE_CMD) \
		ner_model.typer.msc_datasets=$(GOLD_MSC_DATA) 2>&1 | tee $(TRAIN_ON_GOLD_OUT)
train_on_gold: $(TRAIN_ON_GOLD_OUT) 
	@echo TRAIN_ON_GOLD_OUT: $(TRAIN_ON_GOLD_OUT)

$(PSEUDO_OUT): $(GOLD_DATA) $(TERM2CAT)
	poetry run python -m cli.train \
		ner_model=PseudoTwoStage \
		++dataset.name_or_path=$(GOLD_DATA) \
		+ner_model.typer.term2cat=$(TERM2CAT) \
		+testor.baseline_typer.term2cat=$(TERM2CAT) 2>&1 | tee ${PSEUDO_OUT}
train_pseudo_anno: $(PSEUDO_OUT)
	@echo $(PSEUDO_OUT)

$(GOLD_MULTI_LABEL_NER_DATA):
	poetry run python -m cli.preprocess.load_gold_multi_label_ner --output-dir $(GOLD_MULTI_LABEL_NER_DATA)
$(GOLD_MSMLC_BINARY_DATA): $(GOLD_MULTI_LABEL_NER_DATA)
	$(MSMLC_BINARY_DATA_BASE_CMD) \
	+multi_label_ner_dataset=$(GOLD_MULTI_LABEL_NER_DATA) \
	+output_dir=$(GOLD_MSMLC_DATA)


$(GOLD_MSMLC_DATA): $(GOLD_MULTI_LABEL_NER_DATA)
	$(MSMLC_DATA_BASE_CMD) \
	+multi_label_ner_dataset=$(GOLD_MULTI_LABEL_NER_DATA) \
	+output_dir=$(GOLD_MSMLC_DATA)

make_gold_binary_msmlc: $(GOLD_MSMLC_BINARY_DATA)
	echo $(GOLD_MSMLC_BINARY_DATA)

make_gold_msmlc: $(GOLD_MSMLC_DATA)
	echo $(GOLD_MSMLC_DATA)
$(PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD): $(UMLS_TERM2CATS) $(GOLD_MULTI_LABEL_NER_DATA)
	poetry run python -m cli.preprocess.load_pseudo_multi_label_ner \
		++multi_label_ner_model.multi_label_typer.term2cats=$(UMLS_TERM2CATS) \
		+gold_corpus=$(GOLD_MULTI_LABEL_NER_DATA) \
		+raw_corpus=$(GOLD_MULTI_LABEL_NER_DATA) \
		+output_dir=$(PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD)
$(PSEUDO_MSMLC_DATA_ON_GOLD): $(PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD)
	$(MSMLC_DATA_BASE_CMD) \
	+multi_label_ner_dataset=$(PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD) \
	+output_dir=$(PSEUDO_MSMLC_DATA_ON_GOLD)
make_pseudo_multi_label_ner: $(PSEUDO_MULTI_LABEL_NER_DATA_ON_GOLD)
make_pseudo_msmlc: $(PSEUDO_MSMLC_DATA_ON_GOLD)

$(UMLS_TERM2CATS): $(UMLS_DICT_FILES)
	@echo TERM2CAT: $(UMLS_TERM2CATS)
	poetry run python -m cli.preprocess.load_term2cats \
		output=$(UMLS_TERM2CATS) \
		focus_cats=$(subst $() ,_,$(UMLS_CATS)) \
		++remove_ambiguate_terms=$(TERM2CATS_REMOVE_AMBIGUATE)

make_umls_term2cats: $(UMLS_TERM2CATS)
	@echo UMLS_TERM2CATS: $(UMLS_TERM2CATS)
check_pseudo_msmlc: $(GOLD_MSMLC_DATA) $(UMLS_TERM2CATS)
	poetry run python -m cli.train_msmlc +multi_label_typer=MultiLabelDictMatchTyper ++msmlc_datasets=$(GOLD_MSMLC_DATA) multi_label_typer.term2cats=$(UMLS_TERM2CATS)
check_pseudo_msmlc_on_ner: $(UMLS_TERM2CATS)
	poetry run python -m cli.train \ 
		ner_model=PseudoMultiLabelTwoStage \
		ner_model.multi_label_typer.term2cats=$(UMLS_TERM2CATS) \
		ner_model.focus_cats=$(subst $() ,_,$(FOCUS_CATS)) \
		++dataset.name_or_path=$(GOLD_DATA) \
		+testor.baseline_typer.term2cat=$(TERM2CAT) 2>&1 | tee ${PSEUDO_OUT}

$(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL): $(PSEUDO_MSMLC_DATA_ON_GOLD) $(GOLD_MSMLC_DATA)
	poetry run python -m cli.train_msmlc +multi_label_typer=enumerated \
		++multi_label_typer.train_datasets=$(PSEUDO_MSMLC_DATA_ON_GOLD) \
		++multi_label_typer.model_output_path=$(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL) \
		++msmlc_datasets=$(GOLD_MSMLC_DATA) \
		++multi_label_typer.model_args.loss_func=MarginalCrossEntropyLoss \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.pn_ratio_equivalence=True \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.negative_ratio_over_positive=$(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE)
train_msmlc: $(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL)
	@echo $(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL)

$(GOLD_TRAINED_MSMLC_MODEL): $(GOLD_MSMLC_DATA)
	poetry run python -m cli.train_msmlc +multi_label_typer=enumerated \
		++multi_label_typer.train_datasets=$(GOLD_MSMLC_DATA) \
		++multi_label_typer.model_output_path=$(GOLD_TRAINED_MSMLC_MODEL) \
		++msmlc_datasets=$(GOLD_MSMLC_DATA) \
		++multi_label_typer.model_args.loss_func=MarginalCrossEntropyLoss \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.pn_ratio_equivalence=True \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.negative_ratio_over_positive=$(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE)
train_msmlc_gold: $(GOLD_TRAINED_MSMLC_MODEL)
	@echo $(GOLD_TRAINED_MSMLC_MODEL)


$(GOLD_FLATTEN_MULTILABEL_NER_OUTPUT): $(GOLD_MSMLC_DATA)
	$(FLATTEN_MULTILABEL_NER_BASE_CMD) \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.pn_ratio_equivalence=$(MSMLC_PN_RATIO_EQUIVALENCE) \
		++multi_label_typer.model_args.negative_ratio_over_positive=$(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE) \
		++ner_model.multi_label_ner_model.multi_label_typer.train_datasets=$(GOLD_MSMLC_DATA)
train_flattern_multilabel_ner_gold: $(GOLD_FLATTEN_MULTILABEL_NER_OUTPUT)
	@echo GOLD_MULTILABEL_NER_OUTPUT: $(GOLD_FLATTEN_MULTILABEL_NER_OUTPUT)


$(PSEUDO_ON_GOLD_FLATTEN_MULTILABEL_NER_OUTPUT): $(PSEUDO_MSMLC_DATA_ON_GOLD)
	$(FLATTEN_MULTILABEL_NER_BASE_CMD) \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.pn_ratio_equivalence=$(MSMLC_PN_RATIO_EQUIVALENCE) \
		++multi_label_typer.model_args.negative_ratio_over_positive=$(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE) \
		++ner_model.multi_label_ner_model.multi_label_typer.train_datasets=$(PSEUDO_MSMLC_DATA_ON_GOLD)
train_flattern_multilabel_ner: $(PSEUDO_ON_GOLD_FLATTEN_MULTILABEL_NER_OUTPUT)
	@echo PSEUDO_ON_GOLD_FLATTEN_MULTILABEL_NER_OUTPUT: $(PSEUDO_ON_GOLD_FLATTEN_MULTILABEL_NER_OUTPUT)

eval_flatten_marginal_softmax_gold: $(GOLD_TRAINED_MSMLC_MODEL) $(TERM2CAT) $(GOLD_MSMLC_DATA)
	$(FLATTEN_MARGINAL_SOFTMAX_NER_BASE_CMD) \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.saved_param_path=$(GOLD_TRAINED_MSMLC_MODEL) \
		++ner_model.multi_label_ner_model.multi_label_typer.train_datasets=$(GOLD_MSMLC_DATA) 

eval_flatten_marginal_softmax: $(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL) $(TERM2CAT) $(PSEUDO_MSMLC_DATA_ON_GOLD)
	@echo $(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL)
	$(FLATTEN_MARGINAL_SOFTMAX_NER_BASE_CMD) \
		++ner_model.multi_label_ner_model.multi_label_typer.model_args.saved_param_path=$(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL) \
		++ner_model.multi_label_ner_model.multi_label_typer.train_datasets=$(PSEUDO_MSMLC_DATA_ON_GOLD)

$(TRAIN_AND_EVAL_MSMLC_OUT): $(TERM2CAT) $(GOLD_MSMLC_DATA) $(GOLD_DATA) $(PSEUDO_MSMLC_DATA_ON_GOLD)
	@echo $(TRAIN_AND_EVAL_MSMLC_OUT)
	poetry run python -m cli.train \
			ner_model=flatten_marginal_softmax_ner \
			ner_model.focus_cats=$(subst $() ,_,$(FOCUS_CATS)) \
			ner_model/multi_label_ner_model=two_stage \
			+ner_model/multi_label_ner_model/chunker=$(FIRST_STAGE_CHUNKER) \
			+ner_model/multi_label_ner_model/multi_label_typer=enumerated \
			testor.baseline_typer.term2cat=$(TERM2CAT) \
			++ner_model.multi_label_ner_model.multi_label_typer.train_args.do_train=True \
			++ner_model.multi_label_ner_model.multi_label_typer.model_output_path=$(PSEUDO_ON_GOLD_TRAINED_MSMLC_MODEL) \
			++msmlc_datasets=$(GOLD_MSMLC_DATA) \
			++dataset.name_or_path=$(GOLD_DATA) \
			++ner_model.multi_label_ner_model.multi_label_typer.model_args.loss_func=MarginalCrossEntropyLoss \
			++ner_model.multi_label_ner_model.multi_label_typer.train_datasets=$(PSEUDO_MSMLC_DATA_ON_GOLD) \
			++ner_model.multi_label_ner_model.multi_label_typer.model_args.dynamic_pn_ratio_equivalence=$(MSMLC_PN_RATIO_EQUIVALENCE) \
			++ner_model.multi_label_ner_model.multi_label_typer.model_args.negative_ratio_over_positive=$(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE) \
			2>&1 | tee $(TRAIN_AND_EVAL_MSMLC_OUT)
train_and_eval_flatten_marginal_softmax: $(TRAIN_AND_EVAL_MSMLC_OUT)
	@echo $(TRAIN_AND_EVAL_MSMLC_OUT)




eval_msmlc:
	poetry run python -m cli.train \
		ner_model=PseudoMSMLCTwoStage \
		--focused_cats=
eval_msmlc_gold:
	poetry run python -m cli.train \
		ner_model=PseudoMSMLCTwoStage \
		--focused_cats=

make_umls_dict_files: $(UMLS_DICT_FILES)