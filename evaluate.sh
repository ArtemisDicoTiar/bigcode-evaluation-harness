LANGUAGE=$1;
MULTIPLE_LANG=$2;
TARGET_TASK=$3;
SAVE_FOLDER=$4;
MODEL_PATH=$5;

source ~/.zshrc
va bigcode-evaluation-harness

TASK=multiple-${TARGET_TASK}-${MULTIPLE_LANG}
GENERATION_PATH=/workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/${SAVE_FOLDER}/generations_$TASK.json
MODEL_PATH=$MODEL_PATH
METRIC_OUTPUT_PATH=/workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/${SAVE_FOLDER}/evaluation_results_$TASK.json;
accelerate launch --main_process_port 29511 --num_processes=1 main.py \
    --model $MODEL_PATH \
    --precision bf16 \
    --max_memory_per_gpu auto \
    --tasks $TASK \
    --max_length_generation 650 \
    --temperature 0.2   \
    --do_sample True  \
    --n_samples 200  \
    --batch_size 100  \
    --trust_remote_code \
    --save_generations \
    --allow_code_execution \
    --save_generations_path $GENERATION_PATH \
    --metric_output_path $METRIC_OUTPUT_PATH;
PING $TASK DONE;