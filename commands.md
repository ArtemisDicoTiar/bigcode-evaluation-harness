```bash

ts --gpus 2 sh ./evaluate.sh cpp cpp humaneval baseline deepseek-ai/deepseek-coder-6.7b-instruct;
ts --gpus 2 sh ./evaluate.sh cpp cpp mbpp baseline deepseek-ai/deepseek-coder-6.7b-instruct;

ts --gpus 2 sh ./evaluate.sh php php humaneval baseline deepseek-ai/deepseek-coder-6.7b-instruct;
ts --gpus 2 sh ./evaluate.sh php php mbpp baseline deepseek-ai/deepseek-coder-6.7b-instruct;

ts --gpus 2 sh ./evaluate.sh swift swift humaneval baseline deepseek-ai/deepseek-coder-6.7b-instruct;
ts --gpus 2 sh ./evaluate.sh swift swift mbpp baseline deepseek-ai/deepseek-coder-6.7b-instruct;

ts --gpus 2 sh ./evaluate.sh go go humaneval baseline deepseek-ai/deepseek-coder-6.7b-instruct;
ts --gpus 2 sh ./evaluate.sh go go mbpp baseline deepseek-ai/deepseek-coder-6.7b-instruct;

ts --gpus 2 sh ./evaluate.sh rust rs humaneval baseline deepseek-ai/deepseek-coder-6.7b-instruct;
ts --gpus 2 sh ./evaluate.sh rust rs mbpp baseline deepseek-ai/deepseek-coder-6.7b-instruct;

ts --gpus 2 sh ./evaluate.sh scala scala humaneval baseline deepseek-ai/deepseek-coder-6.7b-instruct;
ts --gpus 2 sh ./evaluate.sh scala scala mbpp baseline deepseek-ai/deepseek-coder-6.7b-instruct;


# todos
ts --gpus 2 sh ./evaluate.sh php php humaneval results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/php;
ts --gpus 2 sh ./evaluate.sh php php mbpp results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/php;

ts --gpus 2 sh ./evaluate.sh cpp cpp humaneval results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/cpp;
ts --gpus 2 sh ./evaluate.sh cpp cpp mbpp results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/cpp;

ts --gpus 2 sh ./evaluate.sh swift swift humaneval results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/swift;
ts --gpus 2 sh ./evaluate.sh swift swift mbpp results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/swift;

ts --gpus 2 sh ./evaluate.sh go go humaneval results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/go;
ts --gpus 2 sh ./evaluate.sh go go mbpp results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/go;

ts --gpus 2 sh ./evaluate.sh rust rs humaneval results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/rust;
ts --gpus 2 sh ./evaluate.sh rust rs mbpp results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/rust;

ts --gpus 2 sh ./evaluate.sh scala scala humaneval results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/scala;
ts --gpus 2 sh ./evaluate.sh scala scala mbpp results /workspace/DeepSeek-Coder/experiments/deepseek-coder-6.7b-instruct/scala;
```

~~~
while true; do
for id in $(ts -g | awk 'NR > 1 {print $1}'); do
    command=$(ts -F $id)

    # Capture only the last line of progress
    progress=$(tail -n 1 $(ts -o $id))
    
    # Extract "X/Y" from the last line
    steps=$(echo "$progress" | grep -oP '\d+/\d+' | tail -n 1)
    
    # Extract "HH:MM" from the last line
    remaining_time=$(echo "$progress" | grep -oP '\d+:\d+(?=,)' | tail -n 1)
    
    # Check if both variables are non-empty (i.e., if the pattern was matched)
    if [[ -n "$steps" && -n "$remaining_time" ]]; then
        # Output the extracted values
        PING ${command} \n${steps} ${remaining_time}
    fi
done;
sleep 1800;
done;
~~~
