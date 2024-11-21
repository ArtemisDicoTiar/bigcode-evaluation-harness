LANGUAGE=$1;
MULTIPLE_LANG=$2;
TARGET_TASK=$3;
SAVE_FOLDER=$4;
MODEL_DIR=$5;
MODEL_NAME=$6;
EXPERIMENT_NAME=$7;
IS_PEFT=${8:-false};
IS_SFT=${9:-false};
USE_LARGEST_CHECKPOINT=${10:-true};

# peft and sft are mutually exclusive
if [ $IS_PEFT = "true" ] && [ $IS_SFT = "true" ]; then
  echo "PEFT and SFT cannot be true at the same time";
  exit;
fi;


source ~/.zshrc
va bigcode-evaluation-harness

if [ $MULTIPLE_LANG = "py" ]; then
  TASK=${TARGET_TASK}
else
  TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
fi;

#TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
GENERATION_PATH=/workspace/DeepSeek-Coder/${EXPERIMENT_NAME}/${MODEL_NAME}/${SAVE_FOLDER}/generations_$TASK.json
METRIC_OUTPUT_DIR=/workspace/DeepSeek-Coder/${EXPERIMENT_NAME}/${MODEL_NAME}/${SAVE_FOLDER}
mkdir -p ${METRIC_OUTPUT_DIR}
METRIC_OUTPUT_PATH=${METRIC_OUTPUT_DIR}/evaluation_results_$TASK.json;

echo "--- Running evaluation script ---";
echo "LANGUAGE: $LANGUAGE";
echo "MULTIPLE_LANG: $MULTIPLE_LANG";
echo "TARGET_TASK: $TARGET_TASK";
echo "SAVE_FOLDER: $SAVE_FOLDER";
echo "MODEL_DIR: $MODEL_DIR";
echo "MODEL_NAME: $MODEL_NAME";
echo "EXPERIMENT_NAME: $EXPERIMENT_NAME";
echo "IS_PEFT: $IS_PEFT";
echo "IS_SFT: $IS_SFT";
echo "TASK: $TASK";
echo "GENERATION_PATH: $GENERATION_PATH";
echo "METRIC_OUTPUT_PATH: $METRIC_OUTPUT_PATH";
echo "---------------------------------";


# check whether the model directory exists
if [ -d $MODEL_DIR ]; then
  if [ $USE_LARGEST_CHECKPOINT = "true" ]; then
    echo "Using largest checkpoint";
    # List directories with the prefix 'checkpoint-', extract the numbers, sort numerically, and get the largest value
    largest_checkpoint=$(ls -d ${MODEL_DIR}/checkpoint-* 2>/dev/null | grep -oP 'checkpoint-\K[0-9]+' | sort -nr | head -n 1)
    if [[ -n "$largest_checkpoint" ]]; then
      echo "checkpoint-$largest_checkpoint"
      MODEL_PATH=${MODEL_DIR}/checkpoint-$largest_checkpoint
    else
        echo "No checkpoint directories found."
        MODEL_PATH=$MODEL_DIR
    fi
  else
    echo "Using model directory";
    MODEL_PATH=$MODEL_DIR
  fi;
  # Check if we found any checkpoints and print the result
else
  MODEL_PATH=$MODEL_DIR
fi;

echo "MODEL_PATH: $MODEL_PATH";

if [ -f $GENERATION_PATH ]; then
    echo "Generation file already exists. Skipping evaluation.";
else
  if [ $IS_PEFT = "true" ]; then
    echo "Running PEFT evaluation";
    accelerate launch --main_process_port 29511 --num_processes=1 \
      /workspace/bigcode-evaluation-harness/main.py \
      --model $MODEL_NAME \
      --peft_model $MODEL_PATH \
      --precision bf16 \
      --max_memory_per_gpu auto \
      --tasks $TASK \
      --max_length_generation 1024 \
      --temperature 0.2  \
      --do_sample True  \
      --n_samples 200  \
      --batch_size 50  \
      --trust_remote_code \
      --save_generations \
      --allow_code_execution \
      --save_generations_path $GENERATION_PATH \
      --metric_output_path $METRIC_OUTPUT_PATH;

  elif [ $IS_SFT = "true" ]; then
    echo "Running SFT evaluation";
    accelerate launch --main_process_port 29511 --num_processes=1 \
      /workspace/bigcode-evaluation-harness/main.py \
      --model $MODEL_NAME \
      --sft_path $MODEL_PATH \
      --precision bf16 \
      --max_memory_per_gpu auto \
      --tasks $TASK \
      --max_length_generation 1024 \
      --temperature 0.2  \
      --do_sample True  \
      --n_samples 200  \
      --batch_size 50  \
      --trust_remote_code \
      --save_generations \
      --allow_code_execution \
      --save_generations_path $GENERATION_PATH \
      --metric_output_path $METRIC_OUTPUT_PATH;

  else
    echo "Running normal evaluation";
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
        --save_generations \
        --allow_code_execution \
        --save_generations_path $GENERATION_PATH \
        --metric_output_path $METRIC_OUTPUT_PATH;
  fi;
fi;

sh /workspace/DeepSeek-Coder/merge_results.sh $METRIC_OUTPUT_DIR;
PING $TASK PEFT: $IS_PEFT, SFT: $IS_SFT evaluation completed;
