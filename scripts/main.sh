TMPFILE=$(mktemp)

echo "PseudoAnno"
NO_NC=True
GOLD_NER_DATA_DIR=$(NO_NC=${NO_NC} make -n all | grep GOLD_NER_DATA_DIR | awk '{print $3}')
poetry run python -m cli.train \
    ner_model=PseudoTwoStage \
    ++dataset.name_or_path=${GOLD_NER_DATA_DIR} 2>&1 | tee ${TMPFILE}
RUN_ID_PseudoAnno=$(cat ${TMPFILE} | grep "mlflow_run_id" | awk '{print $2}')
echo "RUN_ID_PseudoAnno" ${RUN_ID_PseudoAnno}

get_enumerated_model_cmd () {
    CMD="\
        poetry run python -m cli.train \
        ++dataset.name_or_path=${RUN_DATASET} \
        ner_model/chunker=${CHUNKER} \
        ner_model.typer.msc_args.with_enumerated_o_label=${WITH_ENUMERATED_O} \
        ner_model.typer.model_args.o_sampling_ratio=${O_SAMPLING_RATIO} \
        ner_model.typer.train_args.per_device_train_batch_size=8 \
        ner_model.typer.train_args.per_device_eval_batch_size=32 \
        ner_model.typer.train_args.do_train=True \
        ner_model.typer.train_args.overwrite_output_dir=True
    "
    echo ${CMD}
}

echo "All Negatives"
# Get Dataset
NO_NC=True
RUN_DATASET=$(NO_NC=${NO_NC} make -n all | grep PSEUDO_NER_DATA_DIR | awk '{print $3}')
# Run
O_SAMPLING_RATIO=0.0001
WITH_ENUMERATED_O=True
CHUNKER="enumerated"
CMD=`get_enumerated_model_cmd`
eval ${CMD} 2>&1 | tee ${TMPFILE}
RUN_ID_AllNegatives=$(cat ${TMPFILE} | grep "mlflow_run_id" | awk '{print $2}')
echo "RUN_ID_AllNegatives" ${RUN_ID_AllNegatives}

echo "All Negatives (NP)"
NO_NC=True
RUN_DATASET=$(NO_NC=${NO_NC} make -n all | grep PSEUDO_NER_DATA_DIR | awk '{print $3}')
O_SAMPLING_RATIO=0.02
WITH_ENUMERATED_O=True
CHUNKER="spacy_np"
CMD=`get_enumerated_model_cmd`
eval ${CMD} 2>&1 | tee ${TMPFILE}
RUN_ID_AllNegatives_NP=$(cat ${TMPFILE} | grep "mlflow_run_id" | awk '{print $2}')
echo "RUN_ID_AllNegatives (NP)" ${RUN_ID_AllNegatives_NP}

echo "Thesaurus Negatives (UMLS)"
NO_NC=False
RUN_DATASET=$(NO_NC=${NO_NC} make -n all | grep PSEUDO_NER_DATA_DIR | awk '{print $3}')
O_SAMPLING_RATIO=0.00
WITH_ENUMERATED_O=False
CHUNKER="spacy_np"
CMD=`get_enumerated_model_cmd`
eval ${CMD} 2>&1 | tee ${TMPFILE}
RUN_ID_Thesaurus_Negatives_UMLS=$(cat ${TMPFILE} | grep "mlflow_run_id" | awk '{print $2}')
echo "RUN_ID_Thesaurus_Negatives (UMLS)" ${RUN_ID_Thesaurus_Negatives_UMLS}


echo "Thesaurus Negatives (UMLS) + All Negatives (NP)"
NO_NC=False
RUN_DATASET=$(NO_NC=${NO_NC} make -n all | grep PSEUDO_NER_DATA_DIR | awk '{print $3}')
O_SAMPLING_RATIO=0.02
WITH_ENUMERATED_O=True
CHUNKER="spacy_np"
CMD=`get_enumerated_model_cmd`
eval ${CMD} 2>&1 | tee ${TMPFILE}
RUN_ID_Thesaurus_Negatives_UMLS=$(cat ${TMPFILE} | grep "mlflow_run_id" | awk '{print $2}')
echo "RUN_ID_Thesaurus_Negatives (UMLS)" ${RUN_ID_Thesaurus_Negatives_UMLS}


# Thesaurus Negatives (UMLS + DBPedia)