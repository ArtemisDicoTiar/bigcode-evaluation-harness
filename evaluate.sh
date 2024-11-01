LANGUAGE=$1;
MULTIPLE_LANG=$2;
TARGET_TASK=$3;
SAVE_FOLDER=$4;
MODEL_PATH=$5;
MODEL_NAME=$6;
EXPERIMENT_NAME=$7;

source ~/.zshrc
va bigcode-evaluation-harness

if [$MULTIPLE_LANG = "py"]; then
  TASK=${TARGET_TASK}
else
  TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
fi;
#TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
GENERATION_PATH=/workspace/DeepSeek-Coder/${EXPERIMENT_NAME}/${MODEL_NAME}/${SAVE_FOLDER}/generations_$TASK.json
MODEL_PATH=$MODEL_PATH
METRIC_OUTPUT_DIR=/workspace/DeepSeek-Coder/${EXPERIMENT_NAME}/${MODEL_NAME}/${SAVE_FOLDER}
mkdir -p ${METRIC_OUTPUT_DIR}
METRIC_OUTPUT_PATH=${METRIC_OUTPUT_DIR}/evaluation_results_$TASK.json;

if [ -f $GENERATION_PATH ]; then
    echo "Generation file already exists. Skipping evaluation.";
else
  accelerate launch --main_process_port 29511 --num_processes=1 \
      /workspace/bigcode-evaluation-harness/main.py \
      --model $MODEL_PATH \
      --precision bf16 \
      --max_memory_per_gpu auto \
      --tasks $TASK \
      --max_length_generation 650 \
      --temperature 0.2  \
      --do_sample True  \
      --n_samples 200  \
      --batch_size 100  \
      --trust_remote_code \
      --save_generations \
      --allow_code_execution \
      --save_generations_path $GENERATION_PATH \
      --metric_output_path $METRIC_OUTPUT_PATH;
fi;
PING $TASK DONE;
