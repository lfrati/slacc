#!/usr/bin/env python
"""
Experiments launcher.

Press [Tab] to complete the current word.
- The first Tab press fills in the common part of all completions
    and shows all the completions. (In the menu)
- Any following tab press cycles through all the possible completions.
"""
import json
import argparse
from pathlib import Path
from time import sleep
import subprocess as sub

from prompt_toolkit.completion import FuzzyCompleter, PathCompleter
from prompt_toolkit.shortcuts import CompleteStyle, ProgressBar, confirm, prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator

from git import Repo

from launch_utils import make_launch_job, prepare_command, make_instantiate
from experiment.experiment import is_git


def py_filter(f):
    return f and f.endswith(".py")


def json_filter(f):
    return f and f.endswith(".json")


def main(args):

    if args.debug:
        print()
        print("##################")
        print("# > DEBUG MODE < #")
        print("##################")
        print()

    if is_git():
        git_repo = Repo(".", search_parent_directories=True)
        # root = Path(git_repo.git.rev_parse("--show-toplevel"))
        dirty = git_repo.is_dirty()
    else:
        dirty = False

    py_completer = PathCompleter(file_filter=py_filter)
    json_completer = PathCompleter(file_filter=json_filter)

    validator = Validator.from_callable(
        lambda x: Path(x).exists(),
        error_message="Please select a file.",
        move_cursor_to_end=True,
    )

    # add some color to guide the attention
    style = Style.from_dict({"prompt": "#ff0066"})

    try:
        entrypoint = prompt(
            [("class:prompt", "Choose the entrypoint (.py): ")],
            completer=FuzzyCompleter(py_completer),
            complete_while_typing=True,
            complete_style=CompleteStyle.MULTI_COLUMN,
            validator=validator,
            validate_while_typing=False,
            style=style,
        )
        params_json = prompt(
            [("class:prompt", "Choose parameters (.json): ")],
            completer=FuzzyCompleter(json_completer),
            complete_while_typing=True,
            complete_style=CompleteStyle.MULTI_COLUMN,
            validator=validator,
            validate_while_typing=False,
            style=style,
        )
    except KeyboardInterrupt:
        print("ABORTING.")
        return

    with open(params_json, "r") as f:
        params = json.loads(f.read())

    # info: flags used to setup environment and launch experiments
    # slurm: flags for the slurm scheduler system
    with open(args.metadata, "r") as f:
        data = json.loads(f.read())

    # choose correct slurm settings for cpu/gpu
    device = args.device
    slurm = data[f"slurm_{device}"]
    env = data["env"][args.support]
    if args.support == "local":
        print(f"Running experiments on local/{args.device}")
    elif args.support == "slurm":
        print(f"Runnins experiments on slurm/{args.device} : {slurm}")

    # check if the repository is clean
    try:
        if not args.debug and dirty:
            answer = confirm(f"There are uncommitted changes. Abort?")
            print()
            if answer:
                print("ABORTING.")
                return
    except KeyboardInterrupt:
        print("ABORTING.")
        return

    # Generate all combinations of parameters that contain lists
    # configs = list(make_instantiate(params))
    # Turn the dicts into strings that will used with sbatch (through temp files), god the pain
    commands = [
        prepare_command(entrypoint, config, args.device)
        for _ in range(args.runs)
        for config in make_instantiate(params)
    ]

    answer = confirm(
        f"\n {len(commands)} jobs ready to launch on {args.support}/{args.device}. Continue?"
    )
    print()

    if answer:
        launch_job = make_launch_job(slurm, env)
        if args.debug:
            for command in commands:
                if args.support == "local":
                    print(command)
                else:
                    print(launch_job(command, debug=True))
                print("---")
        else:
            if args.support == "local":
                for command in commands:
                    parts = command.split(" ")
                    process = sub.Popen(parts)
                    process.wait()
                print("\nLaunch COMPLETED.")
            elif args.support == "slurm":
                with ProgressBar() as pb:
                    for command in pb(commands):
                        launch_job(command)
                        sleep(0.01)
                print("\nLaunch COMPLETED.")
    else:
        print("\nLaunch ABORTED.")

    # patch progress bar shutdown errors
    # https://github.com/prompt-toolkit/python-prompt-toolkit/issues/964
    sleep(0.5)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--metadata",
        type=str,
        help="Json file containing the information about slurm and such.",
        default="SLURM.json",
    )
    argparser.add_argument(
        "--runs", type=int, help="How many repetitions to run.", default=5,
    )
    argparser.add_argument("--device", type=str, help="cpu/gpu", default="cpu")
    argparser.add_argument("--support", type=str, help="local/slurm", default="local")
    argparser.add_argument(
        "--debug",
        action="store_true",
        help="Use debug to print commands instead of running them.",
    )
    ARGS = argparser.parse_args()
    main(ARGS)
