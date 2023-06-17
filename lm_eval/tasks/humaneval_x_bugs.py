"""WIP

Homepage: https://github.com/bigcode-project/commits

Recommended evaluation:
--max_length_generation 2048
    - The longest solution by split using the santacoder tokenizer:
        - CPP: 562
        - Java: 399
        - JS: 465
        - Go: 349
        - Rust: 753
    - In addition comes:
        - the function docstring (~100 tokens max)
        - the instruction (~10 tokens)
        - the generation/duplication with fixed bug (i.e. docstring again & solution) 
    - So for e.g. Rust the entire thing may be ~1800 tokens (worst case)
Sampling:
    - pass@1: `--do_sample False` (sometimes temperature 0.2 is better, but greedy is faster & gives the actual most likely prediction of the model)
    - pass@10 & pass@100: `--do_sample True --temperature 0.8 -- n_samples 200`
"""

import re
from evaluate import load
from lm_eval.base import Task


_CITATION = """
"""

LANGUAGES = ["python", "cpp", "js", "java", "go", "rust"]

# Taken from https://huggingface.co/datasets/nuprl/MultiPL-E/ & https://github.com/THUDM/CodeGeeX
LANGUAGE_TO_STOP_WORDS = {
    # https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L164
    "python": ["\nclass", "\ndef", "\n#", "\n@", "\nprint", "\nif", "\nassert"],
    # https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L185
    "cpp": [],
    # https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L188
    "js": [],
    # https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L177
    "go": ["\n//", "\nfunc main(", "struct", "\nfunc"],
    # https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L169
    "java": [],
    "rust": [],
}

LANGUAGE_TO_TIMEOUT = {
    "python": 10,
    "cpp": 10,
    "js": 10,
    "java": 10,
    "go": 20,
    "rust": 300, # Necessary for first-time compilation of cargo
}

# Java sometimes fails with more workers; For JS it's twice as fast with 4 workers
LANGUAGE_TO_NUM_WORKERS = {
    "python": 4,
    "cpp": 4,
    "js": 4,
    "java": 1,
    "go": 4,
    "rust": 1,
}


# https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L6
IMPORT_HELPER = {
    "python": [
        "import math",
        "import re",
        "import sys",
        "import copy",
        "import datetime",
        "import itertools",
        "import collections",
        "import heapq",
        "import statistics",
        "import functools",
        "import hashlib",
        "import numpy",
        "import numpy as np",
        "import string",
        "from typing import *",
        "from collections import *",
    ],
    "go": [
        "math",
        "strings",
        "fmt",
        "strconv",
        "time",
        "bytes",
        "regexp",
        "sort",
        "math/rand",
        "crypto/md5",
    ],
    "cpp": [
        "#include<stdlib.h>",
        "#include<algorithm>",
        "#include<math.h>",
        "#include<stdio.h>",
        "#include<vector>",
        "#include<string>",
        "#include<climits>",
        "#include<cstring>",
        "#include<iostream>",
    ],
}

def create_all_tasks():
    """Creates a dictionary of tasks from a list of levels
    :return: {task_name: task}
        e.g. {apps-interview: Task, apps-competitoon: Task}
    """
    return {f"humaneval-x-bugs-{language}": create_task(language) for language in LANGUAGES}


def create_task(language):
    class HumanEvalXBugs(GeneralHumanEvalXBugs):
        def __init__(self, mutate_method="prompt", language=language):
            super().__init__(mutate_method=mutate_method, language=language)

    return HumanEvalXBugs


class GeneralHumanEvalXBugs(Task):
    """A task represents an entire benchmark including its dataset, problems,
    answers, generation settings and evaluation methods.
    """

    DATASET_PATH = "bigcode/humaneval-x-bugs"
    DATASET_NAME = None

    def __init__(self, mutate_method="prompt", language="python"):
        
        self.DATASET_NAME = language
        self.mutate_method = mutate_method
        
        stop_words = LANGUAGE_TO_STOP_WORDS[language]
        if self.mutate_method.startswith("edit"):
            stop_words.extend([
                "<commit_before>",
                "<commit_msg>",
                "<commit_after>",
            ])
        elif self.mutate_method == "diff":
            stop_words = ["<commit_before>", "<commit_msg>", "<commit_after>"]
        elif self.mutate_method == "diff-carper":
            stop_words = ["<BEF>", "<MSG>", "<DFF>", "\ No newline at end of file"]

        stop_words.append("<|endoftext|>")

        if self.mutate_method == "diff-carper":
            self.max_length_multiplier = 1.5 # Allow 1.5 times the length of the prompt

        super().__init__(
            stop_words=stop_words,
            requires_execution=True,
        )

    def check_fn(self, code):
        """
        Adapted from https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L115

        Checks whether the generated code is finished
        """
        if any([w in code for w in self.stop_words]):
            return True

        # The heuristics below do not hold for diff generation
        if self.mutate_method.startswith("diff"):
            return False

        if self.DATASET_NAME == "python":
            for line in code.split("\n"):
                if len(line.strip()) > 0 and line[0] != ' ' and line[0] != '\t':
                    return True
        elif self.DATASET_NAME == "java":
            if code.count("{") + 1 == code.count("}"):
                return True
        elif self.DATASET_NAME == "go":
            if code.count("{") + 1 == code.count("}"):
                return True
        elif self.DATASET_NAME == "js":
            if code.count("{") + 1 == code.count("}"):
                return True
        elif self.DATASET_NAME == "cpp":
            if code.count("{") + 1 == code.count("}"):
                return True
        elif self.DATASET_NAME == "rust":
            if code.count("{") + 1 == code.count("}"):
                return True
        return False

    def get_dataset(self):
        """Returns dataset for the task or an iterable of any object, that get_prompt can handle"""
        return self.dataset["test"]

    def get_filename_with_extension(self, input_file):
        """Returns the synthetic filename for different datasets"""
        file_name = input_file if input_file is not None else "solution"
        if self.DATASET_NAME == "python":
            file_name += ".py"
        elif self.DATASET_NAME == "java":
            file_name += ".java"
        elif self.DATASET_NAME == "go":
            file_name += ".go"
        elif self.DATASET_NAME == "js":
            file_name += ".js"
        elif self.DATASET_NAME == "cpp":
            file_name += ".cpp"
        elif self.DATASET_NAME == "rust":
            file_name += ".rs"
        else:
            raise ValueError("Not supporting the dataset for file name")
        return file_name
    
    def get_prompt_base(self, doc):
        # See 
        # https://github.com/roG0d/CodeGeeX/blob/f66205b5f615a4eead9c26d7ec297e14738ea18d/codegeex/benchmark/evaluate_humaneval_x.py#L78
        # https://github.com/THUDM/CodeGeeX/pull/76#issuecomment-1500653190
        if self.DATASET_NAME == "rust":
            main = "\nfn main(){ \n } \n"
            prompt_base = main + doc["declaration"] + doc["prompt"]
        else:
            prompt_base = doc["prompt"]
        return prompt_base

    def get_prompt_encoder(self, doc):
        """Encoder input for models with Enc-Dec architecture like CodeT5"""
        assert self.mutate_method == "prompt", "Only prompt mutation is supported for Enc-Dec models"
        # This is the simplest, most natural way of prompting regardless of language
        prompt = self.get_prompt_base(doc) + doc["buggy_solution"]
        # One could add a comment here, but then it becomes language-specific & for some languages it may not
        # compile anyways since repeating the prompt results in double imports, so let's keep it simple
        prompt += "\n" + "Fix bug in " + doc["entry_point"] # This will be cut-off, so it will compile
        return prompt

    def get_prompt(self, doc):
        """Builds the prompt for the LM to generate from."""
        prompt_base = self.get_prompt_base(doc)

        if self.mutate_method == "file":
            file_name = self.get_filename_with_extension(input_file=doc["entry_point"])
            prompt = "<file_name>\n" + file_name + "\n<commit_before>\n" + prompt_base + doc["buggy_solution"]
            prompt += "\n<commit_msg>\n" + "Fix bug in " + doc["entry_point"]
            prompt += "\n<commit_after>\n" + prompt_base
        elif self.mutate_method == "edit":
            prompt = "<commit_before>" + prompt_base + doc["buggy_solution"]
            prompt += "<commit_msg>" + "Fix bug in " + doc["entry_point"]
            prompt += "<commit_after>" + prompt_base
        elif self.mutate_method == "edit-newline":
            prompt = "<commit_before>\n" + prompt_base + doc["buggy_solution"]
            prompt += "\n<commit_msg>\n" + "Fix bug in " + doc["entry_point"]
            prompt += "\n<commit_after>\n" + prompt_base
        elif self.mutate_method == "edit-type":
            prompt = "<commit_before>" + prompt_base + doc["buggy_solution"]
            prompt += "<commit_msg>" + "Fix " + doc["bug_type"] + " in " + doc["entry_point"]
            prompt += "<commit_after>" + prompt_base
        elif self.mutate_method == "diff":
            prompt = "<commit_before>" + prompt_base + doc["buggy_solution"]
            prompt += "<commit_msg>" + "Fix bug in " + doc["entry_point"]
            prompt += "<commit_after>"
        elif self.mutate_method == "diff-carper":
            if self.DATASET_NAME == "python":
                prompt = f"<NME> {doc['entry_point']}.py" + "\n"
            elif self.DATASET_NAME == "java":
                prompt = f"<NME> {doc['entry_point']}.java" + "\n"
            elif self.DATASET_NAME == "go":
                prompt = f"<NME> {doc['entry_point']}.go" + "\n"
            elif self.DATASET_NAME == "js":
                prompt = f"<NME> {doc['entry_point']}.js" + "\n"
            elif self.DATASET_NAME == "cpp":
                prompt = f"<NME> {doc['entry_point']}.cpp" + "\n"
            elif self.DATASET_NAME == "rust":
                prompt = f"<NME> {doc['entry_point']}.rs" + "\n"
            prompt += "<BEF> " + prompt_base + doc["buggy_solution"] + "\n"
            prompt += "<MSG> " + "Fix bug in " + doc["entry_point"] + "\n"
            prompt += "<DFF>"   
        elif self.mutate_method == "prompt-python":
            # This is sligthly better than just prompt, but it's kind of prompt engineering which we'd like to avoid
            # Also the comments # only work for Python
            prompt = "# Buggy function"
            prompt += "\n" + prompt_base + doc["buggy_solution"] + "\n"
            prompt += "# Fixed function\n" + prompt_base
        elif self.mutate_method == "prompt":
            # This is the simplest, most natural way of prompting regardless of language
            prompt = prompt_base + doc["buggy_solution"]
            # One could add a comment here, but then it becomes language-specific & for some languages it may not
            # compile anyways since repeating the prompt results in double imports, so let's keep it simple
            prompt += "\n" + "Fix bug in " + doc["entry_point"] # This will be cut-off, so it will compile
            prompt += "\n" + prompt_base
        elif self.mutate_method == "instruct":
            # input_template = "Instructions: {instruction}\nInput: {input} Output: "
            # https://github.com/SivilTaram/santacoder-finetuning-commit/blob/82a5598d632d299b7350c8b2ffb4af39527befa3/train.py#L115
            prompt = f"Instructions: Fix bug in {doc['entry_point']}\n"
            prompt += f"Input:\n{prompt_base + doc['buggy_solution']}\n"
            prompt += f"Output:\n" + prompt_base
        else:
            raise ValueError(f"Unknown mutate_method: {self.mutate_method}")
        # Strip off the final \n to make the tokens more natural
        # Essentially, we want to make sure that if there was no distinction between
        # input & output, the tokens would be the same
        # E.g. for SantaCoder:
        # tokenize("""def hi()\n   return""")
        # ['def', 'Ġhi', '()', 'ĊĠĠ', 'Ġreturn']
        # So we need to split before the \n so that the input is
        # ['def', 'Ġhi', '()'] and the model can generate ['ĊĠĠ', 'Ġreturn']
        # If instead we provide def hi()\n the tokens will be
        # ['def', 'Ġhi', '()', 'Ċ'] and the model would need to generate ['ĠĠ', 'Ġreturn']
        # Which would be harder, as it's not the usual way these tokens are tokenized
        # i.e. the model has never seen the token sequence of ['()', 'Ċ', 'ĠĠ'], but only ['()', 'ĊĠĠ']
        # The same holds for Java, JS, Go, Rust, C++ tho the start sequences are slightly different
        return prompt.strip()

    def get_reference(self, doc, get_solution=False):
        """Builds the reference solution for the doc (sample from the test dataset)."""
        if get_solution:
            prompt_base = self.get_prompt_base(doc)
            if self.mutate_method == "diff":
                from diff_match_patch import diff_match_patch
                text1 = prompt_base + doc["buggy_solution"]
                text2 = prompt_base + doc["canonical_solution"]
                dmp = diff_match_patch()
                patches = dmp.patch_make(text1, text2)
                diff = dmp.patch_toText(patches)
                return diff
            else:
                return prompt_base + doc["canonical_solution"]
                # To check that all buggy solutions result in a 0 score:
                # return prompt_base + doc["buggy_solution"]
        else:
            test_func = doc["test"]
            # check(func_name) is already included
            return "\n" + test_func

    def remove_last_block(self, code):
        """
        Adapted from https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L151
        """
        for w in self.stop_words:
            if w in code:
                code = code[:code.rfind(w)]

        if self.mutate_method.startswith("diff"):
            return code

        if self.DATASET_NAME == "python":
            for i, line in enumerate(code.split("\n")):
                if len(line.strip()) > 0 and line[0] != ' ' and line[0] != '\t':
                    return "\n".join(code.split("\n")[:i])
        elif self.DATASET_NAME == "java":
            main_pos = code.find("public static void main")
            if main_pos != -1:
                code = code[:main_pos] + '}'
            if '}' in code:
                code = code[:code.rfind('}')] + '}'
            if code.count('{') + 1 == code.count('}'):
                code += "\n}"
        elif self.DATASET_NAME == "go":
            if '}' in code:
                code = code[:code.rfind('}')] + '}'
        elif self.DATASET_NAME == "cpp":
            if '}' in code:
                code = code[:code.rfind('}')] + '}'
        elif self.DATASET_NAME == "js":
            if '}' in code:
                code = code[:code.rfind('}')] + '}'
        elif self.DATASET_NAME == "rust":
            if '}' in code:
                code = code[:code.rfind('}')] + '}'
        return code

    def postprocess_generation(self, generation, idx):
        """Defines the postprocessing for a LM generation.
        :param generation: str
            code generation from LM
        :param idx: int
            index of doc in the dataset to which the generation belongs
            (not used for Humaneval-Task)
        """
        doc = self.get_dataset()[idx]
        prompt = self.get_prompt(doc)        
        if self.mutate_method == "diff-carper":
            # Only remove final stopwords like <MSG>
            generation = self.remove_last_block(generation[len(prompt):].rstrip())
            generation = prompt + generation
            from lm_eval.tasks.custom_metrics.diff_eval import split_diff
            # From https://github.com/CarperAI/OpenELM/blob/e6402a0696096011572152334ccbe049f89c332e/src/openelm/benchmarks/benchmark_bugs.py#L93
            end_of_diff = re.compile("\n[^ +-@]+")
            parsed: dict = split_diff(generation)
            if parsed and all(
                (s in parsed for s in ["name", "file", "message", "diff"])
            ):
                # truncate diff hunk at the first line not starting with " ", "+", "-", or "@"
                diff_hunk: str = end_of_diff.split(parsed["diff"])[0]
                # We apply diff patch loosely:
                #   1. it ignores the line numbers;
                #   2. it ignores invalid lines (not starting with " ",
                #   "+" or "-" and not being "@@ ... @@").
                # https://github.com/CarperAI/OpenELM/blob/e6402a0696096011572152334ccbe049f89c332e/src/openelm/benchmarks/benchmark_bugs.py#L162
                nme_idx: int = diff_hunk.find("<NME>")
                if nme_idx != -1:
                    diff_hunk = diff_hunk[:nme_idx]
                return diff_hunk
        else:
            gen = self.remove_last_block(generation[len(prompt):].rstrip())
            if self.mutate_method.startswith("diff"):
                return gen
            else:
                # Strip on the right to maintain same behavior as with get_prompt
                prompt_base = self.get_prompt_base(doc)
                return prompt_base.rstrip() + gen

    def process_results(self, generations, references):
        """Takes the list of LM generations and evaluates them against ground truth references,
        returning the metric for the generations.
        :param generations: list(list(str))
            list of lists containing generations
        :param references: list(str)
            list of str containing refrences
        """
        code_metric = load("Muennighoff/code_eval")
        timeout = LANGUAGE_TO_TIMEOUT[self.DATASET_NAME]
        num_workers = LANGUAGE_TO_NUM_WORKERS[self.DATASET_NAME]
        language = self.DATASET_NAME if self.DATASET_NAME != "js" else "javascript"

        # Apply the diff to the input
        if self.mutate_method == "diff":
            # !wget https://raw.githubusercontent.com/google/diff-match-patch/master/python3/diff_match_patch.py
            from diff_match_patch import diff_match_patch
            dmp = diff_match_patch()
            ds = self.get_dataset().select(range(len(generations)))
            for gen, doc in zip(generations, ds):
                prompt_base = self.get_prompt_base(doc)
                old_code = prompt_base + doc["buggy_solution"]
                for i, diff in enumerate(gen): 
                    try:
                        # Strip away anything to the left such as \n
                        patches = dmp.patch_fromText(diff.lstrip())
                        fixed_code, _ = dmp.patch_apply(patches, old_code)
                    except Exception as e:
                        print(f"Failed with {e} when applying patch to buggy code: {diff}")
                        fixed_code = ""
                    gen[i] = fixed_code
        elif self.mutate_method == "diff-carper":
            from lm_eval.tasks.custom_metrics.diff_eval import apply_diff
            ds = self.get_dataset().select(range(len(generations)))
            for gen, doc in zip(generations, ds):
                prompt_base = self.get_prompt_base(doc)
                old_code = prompt_base + doc["buggy_solution"]
                for i, diff_hunk in enumerate(gen):
                    if not(diff_hunk):
                        gen[i] = ""
                        continue
                    res: str = apply_diff(old_code, diff_hunk)        
                    gen[i] = res
        # See https://github.com/THUDM/CodeGeeX/blob/ebeb850f227a90c79de39f7e26b1302f374f3240/codegeex/benchmark/evaluate_humaneval_x.py
        if language == "python":
            python_imports = "\n".join(IMPORT_HELPER["python"])
            generations = [
                [(python_imports + "\n" + g).strip() for g in gen] for gen in generations
            ]
        elif language == "cpp":
            for gen in generations:
                for i, g in enumerate(gen):
                    for s in IMPORT_HELPER["cpp"]:
                        if s not in g:
                            gen[i] = s + "\n" + g
        elif language == "go":
            ds = self.get_dataset().select(range(len(generations)))
            for gen, doc in zip(generations, ds):
                import_string = doc["import"]
                test_setup = doc["test_setup"]
                for i, g in enumerate(gen):
                    other_pkgs = []
                    for pkg in IMPORT_HELPER["go"]:
                        if pkg not in test_setup:
                            p = pkg.split("/")[-1]
                            if p + "." in g:
                                # The problem is that it could appear in a comment
                                # For example in problem 158, the docstring is:
                                # // ... a list of strings.
                                # but the "strings" package is never used
                                # Golang throws an error if the package is not used
                                # Hence search for the package & make sure it's not in a commented line
                                #other_pkgs.append(f"\"{pkg}\"")
                                lines = g.split("\n")
                                for line in lines:
                                    if p + "." in line and not line.startswith("//"):
                                        other_pkgs.append(f"\"{pkg}\"")
                                        break

                    gen[i] = g.replace(import_string, "")
                    if other_pkgs:
                        import_other_pkgs = "import (\n" + "    ".join([p + "\n" for p in other_pkgs]) + ")"
                        gen[i] = test_setup + "\n" + import_other_pkgs + "\n" + gen[i]
                    else:
                        gen[i] = test_setup + "\n" + gen[i]
        elif language == "rust":
            ds = self.get_dataset().select(range(len(generations)))
            main = "\nfn main(){ \n } \n"
            for gen, doc in zip(generations, ds):
                declaration = doc["declaration"]
                for i, g in enumerate(gen):
                    gen[i] = main + declaration + g

        results, logs = code_metric.compute(
            references=references,
            predictions=generations,
            language=language,
            timeout=timeout,
            num_workers=num_workers,
        )
        """Debugging help
        for i, (gen, ref) in enumerate(zip(generations, references)):
            import time
            starttime = time.time()            
            results, log = code_metric.compute(
                references=[ref],
                predictions=[gen],
                language=language,
                timeout=timeout,
            )
            print("TOOK: ", time.time() - starttime)
            with open("errors.txt", "a") as f:
                f.write(log[0][0][1]["result"] + "\n")
            if ("compilation error" in log[0][0][1]["result"]) or (results["pass@1"] != 0):
                print("XXXXX")
                print(results)
                print(log)
                print(i)
                print(gen[0])
                print(ref)        
        """
        return results