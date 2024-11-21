LANGUAGE=$1;
MULTIPLE_LANG=$2;
TARGET_TASK=$3;
SAVE_FOLDER=$4;
MODEL_DIR=$5;
MODEL_NAME=$6;
EXPERIMENT_NAME=$7;

source ~/.zshrc
va bigcode-evaluation-harness

if [ $MULTIPLE_LANG = "py" ]; then
  TASK=${TARGET_TASK}
else
  TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
fi;

#TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
GENERATION_PATH=/workspace/DeepSeek-Coder/${EXPERIMENT_NAME}/${MODEL_NAME}/${SAVE_FOLDER}/generations_${TASK}_${TASK}.json
METRIC_OUTPUT_DIR=/workspace/DeepSeek-Coder/${EXPERIMENT_NAME}/${MODEL_NAME}/${SAVE_FOLDER}
mkdir -p ${METRIC_OUTPUT_DIR}
METRIC_OUTPUT_PATH=${METRIC_OUTPUT_DIR}/evaluation_results_$TASK.json;


# check whether the model directory exists
if [ -d $MODEL_DIR ]; then
  # List directories with the prefix 'checkpoint-', extract the numbers, sort numerically, and get the largest value
  largest_checkpoint=$(ls -d ${MODEL_DIR}/checkpoint-* 2>/dev/null | grep -oP 'checkpoint-\K[0-9]+' | sort -nr | head -n 1)

  # Check if we found any checkpoints and print the result
  if [[ -n "$largest_checkpoint" ]]; then
      echo "checkpoint-$largest_checkpoint"
  else
      echo "No checkpoint directories found."
  fi

  MODEL_PATH=${MODEL_DIR}/checkpoint-$largest_checkpoint
else
  MODEL_PATH=$MODEL_DIR
fi;

# generation path not exists exit

if [ ! -f $GENERATION_PATH ]; then
    echo "Generation file not found. Exiting."
else
  accelerate launch --main_process_port 29511 --num_processes=1 \
      /workspace/bigcode-evaluation-harness/main.py \
      --model $MODEL_PATH \
      --precision bf16 \
      --max_memory_per_gpu auto \
      --tasks $TASK \
      --max_length_generation 1024 \
      --temperature 0.2  \
      --do_sample True  \
      --n_samples 200  \
      --batch_size 50  \
      --trust_remote_code \
      --allow_code_execution \
      --load_generations_path $GENERATION_PATH \
      --metric_output_path $METRIC_OUTPUT_PATH;
fi;

sh /workspace/DeepSeek-Coder/merge_results.sh $METRIC_OUTPUT_DIR;
PING $TASK only_eval Done;
