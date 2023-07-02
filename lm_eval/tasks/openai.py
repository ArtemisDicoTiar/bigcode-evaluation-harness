"""
from datasets import load_dataset

ds = load_dataset("bigcode/humaneval-x-bugs", "python")["test"]
idx = 0

def get_prompt_base(doc, language="python"):
    # See 
    # https://github.com/roG0d/CodeGeeX/blob/f66205b5f615a4eead9c26d7ec297e14738ea18d/codegeex/benchmark/evaluate_humaneval_x.py#L78
    # https://github.com/THUDM/CodeGeeX/pull/76#issuecomment-1500653190
    if language == "rust":
        main = "\nfn main(){ \n } \n"
        prompt_base = main + doc["declaration"] + doc["prompt"]
    else:
        prompt_base = doc["prompt"]
    return prompt_base

prompt_base = get_prompt_base(ds[idx], language="python")
    
messages = [
    {
        "role": "user",
        "content": ds[idx]["instruction"],
    },
    {
        "role": "assistant",
        "content": prompt_base,
    },
]

gpt-4-0613
response = openai.ChatCompletion.create(
model=gpt-4-0613,
messages=messages
)
"""

import os
import openai
import jsonlines
import termcolor

from cdifflib import CSequenceMatcher
from camel_converter import to_snake
from datasets import load_dataset
from typing import List, Dict

def get_prompt_generate(doc):
    return doc["instruction"]


def get_prompt_bugs(doc, language="python", mode="tests"):
    if language == "rust":
        if mode == "tests":
            return "\nfn main(){ \n } \n" + doc["declaration"]
        elif mode == "docs":
            return "\nfn main(){ \n } \n" + doc["declaration"] + doc["prompt"]
        else:
            raise ValueError
    else:
        if mode == "tests":
            return doc["declaration"]
        elif mode == "docs":
            return doc["prompt"]
        else:
            raise ValueError

def get_prompt_explain_desc(doc, language="python"):
    if language == "rust":
        main = "\nfn main(){ \n } \n"
        prompt_base = main + doc["declaration"]
    else:
        prompt_base = doc["declaration"]
    docstring_len = len(doc["docstring"])

    instruction = f"Provide a concise natural language description of the code using at most {docstring_len} characters."
    func = prompt_base + doc["canonical_solution"]

    return instruction + "\n" + func

def get_prompt_explain_gen(sample):
    raise NotImplementedError

class ParseError(Exception):
    pass

class ContentParser:

    @staticmethod
    def _entry_point_variations(entry_point: str) -> List[str]:
        # NOTE: workaround dataset's bug with entry point naming
        return [
            entry_point,
            to_snake(entry_point),
            entry_point[0].lower() + entry_point[1:],
        ]

    def __call__(self, prompt: str, content: str, entry_point: str):
        # NOTE: Model doesn't follow instructions directly:
        # adds description of change and sometimes fixes
        # typos, or other "bugs" in description.
        if "```" in content:
            content = content.split("```")[1]
        # first parse with assumption that content has description
        matcher = CSequenceMatcher(None, prompt, content)
        tag, _, _, j1, j2 = matcher.get_opcodes()[-1]
        if tag == "insert":
            return content[j1:j2]
        # second parse content with assumption that model wrote code without description
        for entry_point in self._entry_point_variations(entry_point):
            if entry_point in content:
                content = content.split(entry_point)[-1]
                return "".join(content.splitlines(keepends=True)[1:])
        raise ParseError(f"Prompt is not in content:\n{content}")


class ChatWrapper:

    def __init__(self, model: str):
        self._model = model

    def __call__(self, prompt: str) -> str:
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]
        while True:
            try:
                response = openai.ChatCompletion.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.2,
                    top_p=0.95,
                )
                message = response["choices"][0]["message"]
                assert message["role"] == "assistant"
                return message["content"]
            except Exception as e:
                print("API EXCEPTION:", e)


if __name__ == '__main__':
    TIMES = 1
    VERBOSE = True
    LANGUAGE = "python"
    MODEL = "gpt-4-0613"
    TASK = "humaneval-x-generate"

    openai.organization = os.getenv("OPENAI_ORGANIZATION")
    openai.api_key = os.getenv("OPENAI_API_KEY")

    samples = [s for s in load_dataset("bigcode/humaneval-x-bugs", LANGUAGE)["test"]] * TIMES

    chat_wrapper = ChatWrapper(MODEL)
    parse_errors = 0
    parser = ContentParser()
    for idx, sample in enumerate(samples):
        if TASK == "humaneval-x-bugs":
            prompt = get_prompt_bugs(sample, language=LANGUAGE)
        elif TASK == "humaneval-x-generate":
            prompt = get_prompt_generate(sample, language=LANGUAGE)
        elif TASK == "humaneval-x-explain-describe":
            prompt = get_prompt_explain_desc(sample, language=LANGUAGE)
        elif TASK == "humaneval-x-explain-generate":
            prompt = get_prompt_explain_gen(sample)

        if VERBOSE:
            print(f"Processing {sample['task_id']} ({idx + 1}/{len(samples)}))...")
            print(termcolor.colored(sample["entry_point"], "yellow", attrs=["bold"]))
            print(termcolor.colored(prompt, "yellow"))
            print(termcolor.colored(sample["buggy_solution"], "red"))
        sample["raw_generation"] = chat_wrapper(prompt)
        try:
            sample["generation"] = parser(prompt, sample["raw_generation"], sample["entry_point"])
        except ParseError as e:
            parse_errors += 1
            print("PARSE EXCEPTION:", e)
            sample["generation"] = ""
        if VERBOSE:
            print(termcolor.colored(sample["generation"], "green"))
    if VERBOSE:
        print("parse error rate:", parse_errors / len(samples))

    results_filename = f"completions_{LANGUAGE}.jsonl"
    with jsonlines.open(results_filename, "w") as writer:
        writer.write_all(samples)