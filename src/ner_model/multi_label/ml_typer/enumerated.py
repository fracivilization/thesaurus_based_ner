import os
from typing import List, Optional
import numpy as np
from transformers.trainer_utils import set_seed
from src.ner_model.multi_label.ml_typer.abstract import (
    MultiLabelTyper,
    MultiLabelTyperConfig,
)
from src.ner_model.typer.data_translator import (
    log_label_ratio,
)

from src.utils.hydra import (
    HydraAddaptedTrainingArguments,
    get_orig_transoformers_train_args_from_hydra_addapted_train_args,
)
from .abstract import MultiLabelTyper, MultiLabelTyperOutput, MultiLabelTyperOutput
from dataclasses import field, dataclass
from omegaconf import MISSING
from transformers import TrainingArguments
from datasets import DatasetDict, Dataset
from loguru import logger
from transformers import (
    AutoConfig,
    AutoTokenizer,
    Trainer,
    set_seed,
)
import torch
import torch.nn
from transformers.models.bert.modeling_bert import BertForTokenClassification
from tqdm import tqdm
from typing import Dict
import itertools
from hydra.utils import get_original_cwd
from transformers.modeling_outputs import (
    TokenClassifierOutput,
)
from scipy.special import expit
import psutil
import itertools
import datasets
from datasets import DatasetDict
from hydra.utils import get_original_cwd, to_absolute_path
import random

span_start_token = "[unused1]"
span_end_token = "[unused2]"


@dataclass
class LabelReconstructionArguments:
    """
    Arguments to use label reconstruction model by Lin and Ji 2019 of
    "An Attentive Fine-Grained Entity Typing Model with Latent Type Representation".
    """

    latent_representation_dim: int = field(
        default=100,
        metadata={"help": "number of dimmension to compress by trancated SVD"},
    )
    weight_for_label_reconstruction_loss: float = field(
        default=0.1,
        metadata={"help": "Weight for loss from truncated SVD"},
    )


@dataclass
class MultiLabelEnumeratedModelArguments:
    """
    Arguments pertaining to which model/config/tokenizer we are going to fine-tune from.
    """

    model_name_or_path: str = field(
        metadata={
            "help": "Path to pretrained model or model identifier from huggingface.co/models"
        }
    )
    config_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "Pretrained config name or path if not the same as model_name"
        },
    )
    tokenizer_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "Pretrained tokenizer name or path if not the same as model_name"
        },
    )
    cache_dir: Optional[str] = field(
        default=None,
        metadata={
            "help": "Where do you want to store the pretrained models downloaded from huggingface.co"
        },
    )
    saved_param_path: Optional[str] = field(
        default=None,
        metadata={"help": "Fine-Tuned parameters. If there is, load this parameter."},
    )
    o_label_id: int = 0  # Update when model loading, so 0 is temporal number
    o_sampling_ratio: float = 0.3  # O sampling in train
    nc_sampling_ratio: float = 1.0  # O sampling in train
    loss_func: str = field(
        default="MarginalCrossEntropyLoss",
        metadata={
            "help": "loss_fucntion of model: BCEWithLogitsLoss or MarginalCrossEntropyLoss"
        },
    )
    pn_ratio_equivalence: bool = field(
        default=False,
        metadata={
            "help": "Make positive and negative ratio equal for each category by label mask.(statically: not on running)"
        },
    )
    dynamic_pn_ratio_equivalence: bool = field(
        default=False,
        metadata={
            "help": "Make positive and negative ratio equal for each category by label mask.(Dinamically: on running)"
        },
    )
    negative_ratio_over_positive: float = field(
        default=1.0,
        metadata={
            "help": "Positive Negative Ratio; if negative is twice as positive, this parameter will be 2."
        },
    )
    label_reconstruction_args: LabelReconstructionArguments = field(
        default=False,
        metadata={
            "help": "Use dense label space by Singular Value Decomposition (c.f. https://aclanthology.org/D19-1641.pdf)"
        },
    )


class MarginalCrossEntropyLoss(torch.nn.BCEWithLogitsLoss):
    def forward(self, input: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """Calculate marginal cross entropy

        Args:
            input (torch.Tensor): input logits: (batch_size, seq_length, label_num)
            target (torch.Tensor): correct label: Shape: (batch_size, seq_length, label_num)

        Returns:
            torch.Tensor: loss: Shape: (batch_size, seq_length, label_num)
        """
        log_likelihood = torch.nn.functional.log_softmax(input, dim=2)
        return -log_likelihood * target


class BertForEnumeratedMultiLabelTyper(BertForTokenClassification):
    @classmethod
    def from_pretrained(
        cls,
        model_args: MultiLabelEnumeratedModelArguments,
        negative_under_sampling_ratio: float,
        *args,
        label_reconstruction_linear_map: np.array = None,
        **kwargs,
    ):
        cls.model_args = model_args
        self = super().from_pretrained(model_args.model_name_or_path, *args, **kwargs)
        assert model_args.o_label_id >= 0
        self.model_args = model_args
        self.negative_sampling_ratio = negative_under_sampling_ratio
        if model_args.label_reconstruction_args:
            # NOTE: BertForTokenClassificationのfrom_pretrainedをベースにうごかしている
            # NOTE: このため__init__にlabel_reconstruction_linear_map関係のモデルパラメタを記載できない
            # NOTE: (__init__にconfig以外のものを渡せないため)
            # NOTE: もしかしたらこのことが原因で動かない可能性が万が一存在するが
            # NOTE: 一旦はfrom_pretrained内部に実装を進める
            # NOTE: 実装は先行研究 https://github.com/limteng-rpi/fet/blob/master/model.py を参考にした

            # NOTE: linear_mapをパラメタにして読み込む
            label_num, latent_dim = label_reconstruction_linear_map.shape
            self.latent_to_label = torch.nn.Linear(latent_dim, label_num,
                                         bias=False)
            self.latent_to_label.weight = torch.nn.Parameter(torch.Tensor(label_reconstruction_linear_map), requires_grad=True)
            self.latent_to_label.weight.requires_grad = False
            self.label_reconstruction_linear_map = torch.nn.Parameter(
                torch.Tensor(label_reconstruction_linear_map), requires_grad=False
            ).T
            # NOTE: ベクトルを圧縮するようの線形変換を準備する
            self.start_compress_linear_map = torch.nn.Linear(
                self.config.hidden_size,
                latent_dim,
            )
            self.end_compress_linear_map = torch.nn.Linear(
                self.config.hidden_size,
                latent_dim,
            )
        return self

    def __init__(self, config):
        super().__init__(config)
        self.start_classifier = torch.nn.Linear(config.hidden_size, config.num_labels)
        self.end_classifier = torch.nn.Linear(config.hidden_size, config.num_labels)
        self.config = config

    def get_valid_entities(self, starts, ends, labels):
        """
        Get valid entities from start, end and label, cut tensor by no-ent label.
        """
        max_filled_ent_id = (labels != -1).sum(dim=1).max()
        valid_labels = labels[:, :max_filled_ent_id]
        valid_starts = starts[:, :max_filled_ent_id]
        valid_ends = ends[:, :max_filled_ent_id]
        return valid_starts, valid_ends, valid_labels

    def get_o_under_sampled_label_masks(self, starts, ends, labels, label_masks):
        """
        Get valid entities from start, end and label, cut tensor by no-ent label.
        """
        # O ラベルをサンプリングする
        o_label_mask = labels[:, :, self.model_args.o_label_id]
        mention_num = label_masks.sum()
        o_label_num = o_label_mask.sum()
        NE_num = mention_num - o_label_num
        o_sampling_ratio = NE_num / o_label_num
        sample_mask = (
            torch.rand(o_label_mask.shape, device=o_label_mask.device)
            < o_sampling_ratio
        )  # 1-sample ratio の割合で True となる mask
        not_o_label_mask = torch.logical_not(o_label_mask)
        ret_label_masks = torch.logical_or(
            not_o_label_mask * label_masks, o_label_mask * label_masks * sample_mask
        )
        return ret_label_masks

    def get_under_sampling_label_masks(self, starts, ends, labels, label_masks):
        """
        Get valid entities from start, end and label, cut tensor by no-ent label.
        """
        device = starts.device
        pos_sampling_ratio = torch.Tensor(self.pos_sampling_ratio).to(device=device)
        neg_sampling_ratio = torch.Tensor(self.neg_sampling_ratio).to(device=device)
        rand_tensor = torch.rand(labels.shape, device=device)
        pos_sample_mask = rand_tensor < pos_sampling_ratio[None, None, :]
        neg_sample_mask = rand_tensor < neg_sampling_ratio[None, None, :]
        pos_labels = labels == True
        neg_labels = labels == False
        sample_mask = torch.logical_or(
            pos_labels * pos_sample_mask, neg_labels * neg_sample_mask
        )
        # O ラベルをサンプリングする
        ret_label_masks = sample_mask * label_masks[:, :, None]
        return ret_label_masks

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        starts=None,
        ends=None,
        labels=None,
        label_masks=None,
    ):
        r"""
        labels (:obj:`torch.LongTensor` of shape :obj:`(batch_size, sequence_length)`, `optional`):
            Labels for computing the token classification loss. Indices should be in ``[0, ..., config.num_labels -
            1]``.
        """
        if self.model_args.dynamic_pn_ratio_equivalence and labels is not None:
            # hypothesize "O" as "nc-O"
            o_labeled_spans = labels[:, :, self.model_args.o_label_id]
            non_o_spans = torch.logical_not(o_labeled_spans)
            remained_spans = (
                torch.rand(o_labeled_spans.shape, device=o_labeled_spans.device)
                < self.negative_sampling_ratio
            )
            remained_o_spans = o_labeled_spans * remained_spans
            label_masks = torch.logical_or(non_o_spans, remained_o_spans) * label_masks
        minibatch_size, max_seq_lens = input_ids.shape
        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
        )
        hidden_states = outputs.last_hidden_state  # (BatchSize, SeqLength, EmbedDim)
        droped_hidden_states = self.dropout(hidden_states)
        start_logits = self.start_classifier(
            droped_hidden_states
        )  # (BatchSize, SeqLength, ClassNum)
        end_logits = self.end_classifier(
            droped_hidden_states
        )  # (BatchSize, SeqLength, ClassNum)
        if self.model_args.label_reconstruction_args:
            # start_logistsに追加する値を取得し、加算する
            # end_logits に追加する値を取得し、加算する
            compressed_start = self.start_compress_linear_map(droped_hidden_states)
            start_logits += self.latent_to_label(compressed_start)
            compressed_end = self.end_compress_linear_map(droped_hidden_states)
            end_logits += self.latent_to_label(compressed_end)
        minibatch_size, max_span_num = starts.shape
        start_logits_per_span = torch.gather(
            start_logits,
            1,
            starts[:, :, None].expand(
                minibatch_size, max_span_num, self.config.num_labels
            ),
        )  # (BatchSize, SpanNum, ClassNum)
        end_logits_per_span = torch.gather(
            end_logits,
            1,
            ends[:, :, None].expand(
                minibatch_size, max_span_num, self.config.num_labels
            ),
        )  # (BatchSize, SpanNum, ClassNum)
        logits = start_logits_per_span + end_logits_per_span
        loss = None
        if labels is not None:
            if self.model_args.loss_func == "BCEWithLogitsLoss":
                loss_fct = torch.nn.BCEWithLogitsLoss(reduction="none")
                loss = loss_fct(logits, labels.to(torch.float))
                masked_loss = label_masks * loss
                loss = masked_loss.sum() / label_masks.sum()
            elif self.model_args.loss_func == "MarginalCrossEntropyLoss":
                label_masks = label_masks[:, :, None]
                loss_fct = MarginalCrossEntropyLoss(reduction="none")
                loss = loss_fct(logits, labels.to(torch.float))
                masked_loss = label_masks * loss
                loss = masked_loss.sum()
            # ポジネガの比率をprintする

        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )


@dataclass
class MultiLabelEnumeratedDataTrainingArguments:
    """
    Arguments pertaining to what data we are going to input our model for training and eval.
    """

    overwrite_cache: bool = field(
        default=False,
        metadata={"help": "Overwrite the cached preprocessed datasets or not."},
    )
    max_span_num: int = field(
        default=512,
        metadata={"help": "Max span num in training."},
    )

    task_name: Optional[str] = field(
        default="ner", metadata={"help": "The name of the task (ner, pos...)."}
    )
    dataset_config_name: Optional[str] = field(
        default=None,
        metadata={
            "help": "The configuration name of the dataset to use (via the datasets library)."
        },
    )
    preprocessing_num_workers: Optional[int] = field(
        default=None,
        metadata={"help": "The number of processes to use for the preprocessing."},
    )
    label_all_tokens: bool = field(
        default=False,
        metadata={
            "help": "Whether to put the label for one word on all tokens of generated by that word or just on the "
            "one (in which case the other tokens will have a padding index)."
        },
    )
    max_length: int = field(
        default=512,
        metadata={"help": "Max sequence length in training."},
    )


@dataclass
class MultiLabelEnumeratedTrainingArguments(TrainingArguments):
    load_best_model_at_end: Optional[bool] = field(
        default=False,
        metadata={
            "help": "Whether or not to load the best model found during training at the end of training."
        },
    )


@dataclass
class MultiLabelEnumeratedTyperConfig(MultiLabelTyperConfig):
    multi_label_typer_name: str = "MultiLabelEnumeratedTyper"
    label_names: str = "non_initialized: this variable is dinamically decided"
    train_datasets: str = "Please add path to DatasetDict"
    model_args: MultiLabelEnumeratedModelArguments = MultiLabelEnumeratedModelArguments(
        model_name_or_path="dmis-lab/biobert-base-cased-v1.1"
    )
    data_args: MultiLabelEnumeratedDataTrainingArguments = (
        MultiLabelEnumeratedDataTrainingArguments()
    )
    train_args: HydraAddaptedTrainingArguments = HydraAddaptedTrainingArguments(
        output_dir="."
    )
    model_output_path: str = MISSING
    prediction_threshold: float = 0.5


class MultiLabelEnumeratedTyperPreprocessor:
    """MultiLabelEnumeratedTyperのためのPreprocessor
    分散処理をする際にクラスにGPU情報を持たせないために前処理に関連する情報だけ分離する
    """

    pass

    def __init__(
        self,
        model_args: MultiLabelEnumeratedModelArguments,
        data_args: MultiLabelEnumeratedDataTrainingArguments,
        label_names: List[str],
        negative_sampling_ratio: float,
        positive_sampling_ratio: Optional[float] = 1.0,
    ) -> None:
        self.model_args = model_args
        self.data_args = data_args
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_args.tokenizer_name
            if model_args.tokenizer_name
            else model_args.model_name_or_path,
            cache_dir=model_args.cache_dir,
            use_fast=True,
            additional_special_tokens=[span_start_token, span_end_token],
        )
        self.label_names = label_names
        self.negative_sampling_ratio = negative_sampling_ratio
        self.positive_sampling_ratio = positive_sampling_ratio

    def padding_spans(self, example: Dict, max_span_num=10000) -> Dict:
        """add padding for example

        Args:
            example (Dict): {"tokens": List[List[str]], "starts": List[List[int]], "ends": List[List[int]], "label": List[List[int]]}
        Returns:
            Dict: [description]
        """
        sn = max_span_num
        padding_label = 0
        ignore_span_label = [-1] * max_span_num
        for key, value in example.items():
            if key in {"starts", "ends", "labels"}:
                new_value = []
                if value:
                    for snt in value:
                        if key in {"starts", "ends"}:
                            new_value.append(
                                snt[:sn] + [padding_label] * (sn - len(snt))
                            )
                        elif key == "labels":
                            new_value.append(
                                snt[:sn] + [ignore_span_label] * (sn - len(snt))
                            )
                    example[key] = new_value
                else:
                    example[key] = value
        return example

    def load_model_input(
        self,
        tokens: List[List[str]],
        snt_starts: List[List[int]],
        snt_ends: List[List[int]],
        label_num: int,
        labels: List[List[int]] = None,
        max_span_num=10000,
    ):
        example = self.padding_spans(
            {
                "tokens": tokens,
                "starts": snt_starts,
                "ends": snt_ends,
                "labels": labels,
            },
            max_span_num=max_span_num,
        )
        all_padded_subwords = []
        all_attention_mask = []
        all_starts = []
        all_ends = []
        starts = np.array(example["starts"])
        ends = np.array(example["ends"])
        snt_lens = [len(snt) for snt in example["tokens"]]
        snt_split = list(itertools.accumulate(snt_lens))
        all_words = [w for snt in example["tokens"] for w in snt]
        tokenized_tokens = self.tokenizer.batch_encode_plus(
            all_words, add_special_tokens=False
        )["input_ids"]
        snt_split = list(zip([0] + snt_split, snt_split))
        pad_token_id = self.tokenizer.pad_token_id
        for snt_id in tqdm(list(range(len(example["tokens"])))):
            snt_starts = starts[snt_id]
            snt_ends = ends[snt_id]
            s, e = snt_split[snt_id]
            tokens = tokenized_tokens[s:e]
            subwords = [w for li in tokens for w in li]
            token2subword = [0] + list(itertools.accumulate(len(li) for li in tokens))
            new_starts = [token2subword[s] for s in snt_starts]
            new_ends = [token2subword[e] for e in snt_ends]
            for i, (s, e) in enumerate(zip(new_starts, new_ends)):
                if s > self.data_args.max_length or e > self.data_args.max_length:
                    pass
                    new_starts[i] = 0
                    new_ends[i] = 0
            assert all(s <= self.data_args.max_length for s in new_starts)
            assert all(e <= self.data_args.max_length for e in new_ends)
            all_starts.append(new_starts)
            all_ends.append(new_ends)
            padded_subwords = (
                [self.tokenizer.cls_token_id]
                + subwords[: self.data_args.max_length - 2]
                + [self.tokenizer.sep_token_id]
            )
            all_attention_mask.append(
                [1] * len(padded_subwords)
                + [0] * (self.data_args.max_length - len(padded_subwords))
            )
            padded_subwords = padded_subwords + [pad_token_id] * (
                self.data_args.max_length - len(padded_subwords)
            )
            all_padded_subwords.append(padded_subwords)
            # TODO: labelsをTensor(shapeが一貫したものに変換する)
        all_labels = []
        all_label_masks = []
        no_span_mask = [False] * label_num
        if example["labels"]:
            padded_labels = [False for i in range(label_num)]
            for snt_labels in example["labels"]:
                ret_snt_labels = []
                ret_snt_label_mask = []
                for span_labels in snt_labels:
                    if self.model_args.pn_ratio_equivalence:
                        if self.model_args.loss_func == "MarginalCrossEntropyLoss":
                            if -1 in span_labels:
                                span_labels = padded_labels
                                span_label_mask = False
                            elif 0 in span_labels:
                                span_labels = [
                                    i in span_labels for i in range(label_num)
                                ]
                                if random.random() < self.negative_sampling_ratio:
                                    span_label_mask = True
                                else:
                                    span_label_mask = False
                            else:
                                span_labels = [
                                    i in span_labels for i in range(label_num)
                                ]
                                span_label_mask = True
                            ret_snt_labels.append(span_labels)
                            ret_snt_label_mask.append(span_label_mask)
                        elif self.model_args.loss_func == "BCEWithLogitLoss":
                            if -1 in span_labels:
                                span_labels = padded_labels
                                span_label_mask = no_span_mask
                            else:
                                span_labels = [
                                    i in span_labels for i in range(label_num)
                                ]
                                pos_labels = np.array(span_labels)
                                neg_labels = np.logical_not(pos_labels)
                                rand_array = np.random.random(label_num)
                                positive_mask = (
                                    rand_array < self.positive_sampling_ratio
                                )
                                negative_mask = (
                                    rand_array < self.negative_sampling_ratio
                                )
                                span_label_mask = np.logical_or(
                                    pos_labels * positive_mask,
                                    neg_labels * negative_mask,
                                )
                            ret_snt_labels.append(span_labels)
                            ret_snt_label_mask.append(span_label_mask)
                        else:
                            raise NotImplementedError
                    else:
                        if -1 in span_labels:
                            span_labels = padded_labels
                            span_label_mask = False
                        else:
                            span_labels = [i in span_labels for i in range(label_num)]
                            span_label_mask = True
                        ret_snt_labels.append(span_labels)
                        ret_snt_label_mask.append(span_label_mask)
                all_labels.append(ret_snt_labels)
                all_label_masks.append(ret_snt_label_mask)
        ret_dict = {
            "input_ids": all_padded_subwords,
            "attention_mask": all_attention_mask,
            "starts": all_starts,
            "ends": all_ends,
            "labels": all_labels,
            "label_masks": all_label_masks,
        }
        return ret_dict

    def preprocess_function(self, example: Dict) -> Dict:
        return self.load_model_input(
            example["tokens"],
            example["starts"],
            example["ends"],
            label_num=len(self.label_names),
            labels=example["labels"],
            max_span_num=self.data_args.max_span_num,
        )

    def preprocess_function_for_prediction(self, example: Dict) -> Dict:
        model_input = self.load_model_input(
            example["tokens"],
            example["starts"],
            example["ends"],
            label_num=len(self.label_names),
            max_span_num=self.data_args.max_span_num,
        )
        del model_input["labels"]
        del model_input["label_masks"]
        return model_input


class MultiLabelEnumeratedTyper(MultiLabelTyper):
    def __init__(
        self,
        config: MultiLabelEnumeratedTyperConfig,
    ) -> None:
        """[summary]

        Args:
            span_classification_datasets (DatasetDict): with context tokens
        """
        self.conf = config
        train_args = get_orig_transoformers_train_args_from_hydra_addapted_train_args(
            config.train_args
        )
        model_args = config.model_args
        data_args = config.data_args
        self.model_args = config.model_args
        self.data_args = config.data_args
        self.train_args = train_args
        logger.info("Start Loading BERT")
        if (
            os.path.exists(train_args.output_dir)
            and os.listdir(train_args.output_dir)
            and train_args.do_train
            and not train_args.overwrite_output_dir
        ):
            raise ValueError(
                f"Output directory ({train_args.output_dir}) already exists and is not empty."
                "Use --overwrite_output_dir to overcome."
            )
        logger.warning(
            f"Process rank: {train_args.local_rank}, device: {train_args.device}, n_gpu: {train_args.n_gpu}"
            + f"distributed training: {bool(train_args.local_rank != -1)}, 16-bits training: {train_args.fp16}"
        )
        logger.info("Training/evaluation parameters %s", train_args)
        # Set seed before initializing model.
        set_seed(train_args.seed)
        # msml: Multi Span Multi Label
        from hydra.core.hydra_config import HydraConfig

        if HydraConfig.initialized():
            train_datasets_path = os.path.join(
                get_original_cwd(), config.train_datasets
            )
        else:
            train_datasets_path = config.train_datasets
        msml_datasets = DatasetDict.load_from_disk(train_datasets_path)
        log_label_ratio(msml_datasets)
        if train_args.do_train:
            features = msml_datasets["train"].features
        else:
            features = msml_datasets["validation"].features

        label_list = features["labels"].feature.feature.names
        self.label_names = label_list
        num_labels = len(label_list)
        self.label_num = num_labels

        # Load pretrained model and tokenizer
        #
        # Distributed training:
        # The .from_pretrained methods guarantee that only one local process can concurrently
        # download model & vocab.
        auto_config = AutoConfig.from_pretrained(
            model_args.config_name
            if model_args.config_name
            else model_args.model_name_or_path,
            num_labels=num_labels,
            finetuning_task=data_args.task_name,
            cache_dir=model_args.cache_dir,
            model_args=model_args,
        )
        if "nc-O" in label_list:
            model_args.o_label_id = label_list.index("nc-O")
        else:
            model_args.o_label_id = -2

        msml_datasets = DatasetDict(
            {
                "train": msml_datasets["train"],
                "validation": msml_datasets["validation"],
            }
        )
        self.msml_datasets = msml_datasets
        # NOTE: positive_sampling_ratioはBCEWithLogitLossのときにしか使わない
        # TODO: BCEWithLogitLossの削除と同時に消したい
        (
            negative_sampling_ratio,
            positive_sampling_ratio,
        ) = self.load_negpog_sampling_ratio(model_args, msml_datasets["train"])
        self.negative_sampling_ratio = negative_sampling_ratio

        self.preprocessor = MultiLabelEnumeratedTyperPreprocessor(
            model_args,
            data_args,
            label_names=self.label_names,
            negative_sampling_ratio=negative_sampling_ratio,
            positive_sampling_ratio=positive_sampling_ratio,
        )

        self.model = self.init_model(
            auto_config, model_args, negative_sampling_ratio, msml_datasets
        )

        self.trainer = self.init_trainer(
            train_args,
            data_args,
            model_args,
            auto_config,
            self.model,
            label_list,
            self.preprocessor,
            msml_datasets,
        )

    def load_negpog_sampling_ratio(self, model_args, train_dataset):
        positive_sampling_ratio = 1.0
        if model_args.pn_ratio_equivalence or model_args.dynamic_pn_ratio_equivalence:
            if model_args.loss_func == "MarginalCrossEntropyLoss":
                label_names = train_dataset.features["labels"].feature.feature.names
                assert label_names.index("nc-O") == 0
                pos_label_count = 0
                neg_label_count = 0
                for snt in train_dataset:
                    for span in snt["labels"]:
                        span_labels = [label_names[l] for l in span]
                        if span_labels == ["nc-O"]:
                            neg_label_count += 1
                        else:
                            pos_label_count += 1
                negative_sampling_ratio = (
                    model_args.negative_ratio_over_positive
                    * pos_label_count
                    / neg_label_count
                )
            else:
                label_names = train_dataset.features["labels"].feature.feature.names
                label_count = [0] * len(label_names)
                span_num = 0
                for snt in train_dataset:
                    for span in snt["labels"]:
                        span_num += 1
                        for label in span:
                            label_count[label] += 1
                label_count = np.array(label_count)
                negative_count = span_num - label_count
                positive_sampling_ratio = negative_count / (
                    label_count * model_args.negative_ratio_over_positive
                )
                negative_sampling_ratio = (
                    model_args.negative_ratio_over_positive
                    * label_count
                    / negative_count
                )
        else:
            negative_sampling_ratio = 1.0
        return negative_sampling_ratio, positive_sampling_ratio

    def load_label_reconstruction_linear_map(
        self,
        model_args: MultiLabelEnumeratedModelArguments,
        train_msml_dataset: Dataset,
    ):
        # 正解のラベル確率を取得する
        label_num = train_msml_dataset.features["labels"].feature.feature.num_classes
        Y = []
        one_hots = np.eye(label_num)
        for snt in train_msml_dataset:
            for span in snt["labels"]:
                Y.append(one_hots[span].sum(axis=0) / len(span))
        Y = np.array(Y)

        from sklearn.decomposition import TruncatedSVD

        svd = TruncatedSVD(
            n_components=model_args.label_reconstruction_args.latent_representation_dim
        )
        svd.fit(Y)

        # U*ΣでW_l を取得する
        U = svd.components_.T
        Σ = np.diag(svd.singular_values_)
        W_l = np.matmul(U, Σ)
        return W_l

    def init_model(
        self,
        auto_config,
        model_args: MultiLabelEnumeratedModelArguments,
        negative_sampling_ratio: float,
        msml_datasets: DatasetDict,
    ):
        label_reconstruction_linear_map = None
        if model_args.label_reconstruction_args:
            label_reconstruction_linear_map = self.load_label_reconstruction_linear_map(
                model_args, msml_datasets["train"]
            )
        # TODO: label_reconstruction_linear_mapを後でBertForEnumeratedMultiLabelTyperに渡す
        model = BertForEnumeratedMultiLabelTyper.from_pretrained(
            model_args,
            negative_under_sampling_ratio=negative_sampling_ratio,
            from_tf=bool(".ckpt" in model_args.model_name_or_path),
            config=auto_config,
            cache_dir=model_args.cache_dir,
            label_reconstruction_linear_map=label_reconstruction_linear_map,
        )
        if model_args.saved_param_path:
            model.load_state_dict(
                torch.load(
                    os.path.join(
                        to_absolute_path(model_args.saved_param_path),
                        "pytorch_model.bin",
                    )
                )
            )
        return model

    def init_trainer(
        self,
        train_args,
        data_args,
        model_args,
        auto_config,
        model,
        label_list,
        preprocessor,
        msml_datasets,
    ):
        num_labels = len(label_list)
        if model_args.loss_func == "MarginalCrossEntropyLoss":
            features = datasets.Features(
                {
                    "input_ids": datasets.Sequence(
                        datasets.Value("int32"),
                        length=auto_config.max_position_embeddings,
                    ),
                    "attention_mask": datasets.Sequence(
                        datasets.Value("int8"),
                        length=auto_config.max_position_embeddings,
                    ),
                    "starts": datasets.Sequence(datasets.Value("int16")),
                    "ends": datasets.Sequence(datasets.Value("int16")),
                    "labels": datasets.features.Array2D(
                        (data_args.max_span_num, num_labels), "bool"
                    ),
                    "label_masks": datasets.Sequence(datasets.Value("bool")),
                }
            )
        elif model_args.loss_func == "BCEWithLogitsLoss":
            features = datasets.Features(
                {
                    "input_ids": datasets.Sequence(
                        datasets.Value("int32"),
                        length=auto_config.max_position_embeddings,
                    ),
                    "attention_mask": datasets.Sequence(
                        datasets.Value("int8"),
                        length=auto_config.max_position_embeddings,
                    ),
                    "starts": datasets.Sequence(datasets.Value("int16")),
                    "ends": datasets.Sequence(datasets.Value("int16")),
                    "labels": datasets.features.Array2D(
                        (data_args.max_span_num, num_labels), "bool"
                    ),
                    "label_masks": datasets.Sequence(
                        datasets.Sequence(
                            datasets.Value("bool"),
                            length=self.label_num,
                        ),
                        length=auto_config.max_position_embeddings,
                    ),
                }
            )

        if train_args.do_train:
            self.span_classification_datasets = DatasetDict(
                {
                    key: Dataset.from_dict(
                        preprocessor.preprocess_function(split.to_dict()),
                        features=features,
                    )
                    for key, split in msml_datasets.items()
                }
            )
            # TODO: なぜかテストでは動かない
            # self.span_classification_datasets: DatasetDict = msml_datasets.map(
            #     preprocessor.preprocess_function,
            #     batched=False,
            #     load_from_cache_file=False,
            #     keep_in_memory=True,
            #     num_proc=psutil.cpu_count(logical=False),
            #     features=features,
            # )

        def compute_metrics(p):
            predictions, labels = p
            predictions = np.argmax(predictions, axis=2)

            # Remove ignored index (special tokens)
            true_predictions = [
                [label_list[p] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            true_labels = [
                [label_list[l] for (p, l) in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            from seqeval.metrics import (
                accuracy_score,
                f1_score,
                precision_score,
                recall_score,
            )

            return {
                "accuracy_score": accuracy_score(true_labels, true_predictions),
                "precision": precision_score(true_labels, true_predictions),
                "recall": recall_score(true_labels, true_predictions),
                "f1": f1_score(true_labels, true_predictions),
            }

        # Initialize our Trainer
        from transformers import default_data_collator

        return Trainer(
            model=model,
            args=train_args,
            train_dataset=self.span_classification_datasets["train"]
            if train_args.do_train
            else None,
            eval_dataset=self.span_classification_datasets["validation"]
            if train_args.do_train
            else None,
            tokenizer=preprocessor.tokenizer,
            data_collator=default_data_collator,
            compute_metrics=compute_metrics,
        )

    def predict(
        self, tokens: List[str], starts: List[str], ends: List[str]
    ) -> MultiLabelTyperOutput:
        context_tokens = self.get_spanned_token(tokens, starts, ends)
        tokenized_context = self.preprocessor.tokenizer(
            context_tokens,
            # We use this argument because the texts in our dataset are lists of words (with a label for each word).
            is_split_into_words=True,
            return_offsets_mapping=True,
        )
        tokenized_context
        kwargs = {
            "span_context_input_ids": torch.LongTensor(
                [tokenized_context["input_ids"]]
            ).to(self.model.device),
            "span_context_attention_mask": torch.LongTensor(
                [tokenized_context["attention_mask"]]
            ).to(self.model.device),
        }
        outputs = self.model(**kwargs)
        # TODO: change into TyperOutput
        raise NotImplementedError

    def batch_predict(
        self, tokens: List[List[str]], starts: List[List[int]], ends: List[List[int]]
    ) -> List[List[MultiLabelTyperOutput]]:
        assert len(tokens) == len(starts)
        assert len(starts) == len(ends)
        input_dataset = Dataset.from_dict(
            {"tokens": tokens, "starts": starts, "ends": ends}
        )
        dataset = input_dataset.map(
            self.preprocessor.preprocess_function_for_prediction,
            batched=True,
            load_from_cache_file=True,
            keep_in_memory=True,
            num_proc=psutil.cpu_count(logical=False),
        )
        outputs = self.trainer.predict(dataset)
        logits = outputs.predictions
        ret_list = []
        assert all(len(s) == len(e) for s, e in zip(starts, ends))
        for snt_logit, span_num in tqdm(zip(logits, map(len, starts))):
            snt_logit = snt_logit[:span_num]
            labels = [[]] * span_num
            for span_id, label_id in zip(
                *np.where(expit(snt_logit) > self.conf.prediction_threshold)
            ):
                labels[span_id] = labels[span_id] + [self.label_names[label_id]]
            snt_ret_list = []
            for span_logit, span_labels in zip(snt_logit, labels):
                snt_ret_list.append(
                    MultiLabelTyperOutput(
                        labels=span_labels,
                        logits=span_logit,
                    )
                )
            ret_list.append(snt_ret_list)
        return ret_list

    def train(self):
        # Training
        output_path = to_absolute_path(self.conf.model_output_path)
        if self.train_args.do_train:
            self.trainer.train(
                model_path=self.model_args.model_name_or_path
                if os.path.isdir(self.model_args.model_name_or_path)
                else None
            )
            self.trainer.save_model(
                output_path
            )  # Saves the tokenizer too for easy upload
