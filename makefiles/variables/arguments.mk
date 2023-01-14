# Arguments
PYTHON ?= .venv/bin/python
FOCUS_CATS ?= T005 T007 T017 T022 T031 T033 T037 T038 T058 T062 T074 T082 T091 T092 T097 T098 T103 T168 T170 T201 T204
# NEGATIVE_CATS ?= T054 T055 T056 T064 T065 T066 T068 T075 T079 T080 T081 T099 T100 T101 T102 T171 T194 T200 $(DBPEDIA_CATS)
WITH_NEGATIVE_CATEGORIES ?= False
NEGATIVE_CATS ?= $(shell ${PYTHON} -m cli.preprocess.load_negative_categories --focus-categories $(subst $() ,_,$(FOCUS_CATS)) --with-negative_categories $(WITH_NEGATIVE_CATEGORIES))
# WITH_NC ?= True
WITH_O ?= True
FIRST_STAGE_CHUNKER ?= enumerated # ２段階モデルの１段階目 擬似データの際のChunkerを意味しない
POSITIVE_RATIO_THR_OF_NEGATIVE_CAT ?= 1.0
# O_SAMPLING_RATIO ?= 1.0
NEGATIVE_RATIO_OVER_POSITIVE ?= 1.0
# MSC_O_SAMPLING_RATIO ?= 1.0
UNDERSAMPLE_MSLC ?= False
TRAIN_SNT_NUM ?= 9223372036854775807
MSMLC_PN_RATIO_EQUIVALENCE ?= False
MSMLC_DYNAMIC_PN_RATIO_EQUIVALENCE ?= False
MSMLC_NEGATIVE_RATIO_OVER_POSITIVE ?= 1.0
FLATTEN_NER_THRESHOLD ?= 0.97
TRAIN_BATCH_SIZE ?= 16
EVAL_BATCH_SIZE ?= 32



MSC_ARGS := "WITH_O: $(WITH_O) FIRST_STAGE_CHUNKER: $(FIRST_STAGE_CHUNKER) NEGATIVE_RATIO_OVER_POSITIVE: $(NEGATIVE_RATIO_OVER_POSITIVE)"
MSMLC_ARGS := "FIRST_STAGE_CHUNKER: $(FIRST_STAGE_CHUNKER) UNDERSAMPLE_MSLC: $(UNDERSAMPLE_MSLC) MSMLC_PN_RATIO_EQUIVALENCE: $(MSMLC_PN_RATIO_EQUIVALENCE) MSMLC_NEGATIVE_RATIO_OVER_POSITIVE: $(MSMLC_NEGATIVE_RATIO_OVER_POSITIVE) MSMLC_DYNAMIC_PN_RATIO_EQUIVALENCE: $(MSMLC_DYNAMIC_PN_RATIO_EQUIVALENCE)"
