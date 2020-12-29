#!/usr/bin/env python

import argparse
import json
import os
from uuid import uuid4
from datetime import date
import subprocess as sub
from pathlib import Path

from prompt_toolkit.shortcuts import confirm, prompt

DEBUG = os.getenv("DEBUG", None) is not None


def slurm_launcher(cmd, name, delete=False):
    """
    one day I'll figure out how to use srun directly, for now create a temp
    file with the slurm sbatch syntax, launch it and then delete it
    """
    if DEBUG:
        print(cmd)
        return

    with open(name, "w") as f:
        f.write(cmd)

    # redirect unwanted output to null
    with open(os.devnull, "w") as FNULL:
        try:
            sub.call(["sbatch", f"{name}"], shell=False, stdout=FNULL)
        except sub.CalledProcessError as e:
            print("ERROR", e)

    if delete:
        # delete the temporary file we passed to sbatch
        sub.call(["rm", f"{name}"], shell=False)


def local_launcher(cmd):
    if DEBUG:
        print(cmd)
        return

    parts = cmd.split(" ")
    process = sub.Popen(parts)
    process.wait()


def slurm_script(conf, cmd):
    """
    Generate the information to be passed to SLURM about the job
    Also take care of setting up the environment
    The python command will be added afterwards
    """
    shebang = "#!/bin/bash"
    flags = "\n".join(
        f"#SBATCH --{flag}={value}" for flag, value in conf["resources"].items()
    )
    script = f"{shebang}\n{flags}\n\n{conf['env']}\n{cmd}"
    return script


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="neurun")
    parser.add_argument("support")
    parser.add_argument("device")
    parser.add_argument(
        "--runs",
        type=int,
        help="How many repetitions to run.",
        default=5,
    )
    parser.add_argument("entry")
    parser.add_argument("flags", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    config_file = "config.json"

    print("File:", args.entry)
    print("Support:", args.support)
    print("Device:", args.device)
    print("Flags:", args.flags)

    ################# VALIDATE INPUT #################
    assert Path(args.entry).exists(), f"File {args.entry} not found."
    assert Path(config_file).exists(), f"Configuration file ({config_file}) not found."
    with open(config_file, "r") as f:
        available_configs = json.loads(f.read())
    assert (
        args.support in available_configs.keys()
    ), f"Requested configuration ({args.support}) not found in config file ({config_file})"
    assert args.device in [
        "cpu",
        "gpu",
    ], f"Wrong device requested: {args.device} not in [cpu, gpu]"
    assert (
        args.device in available_configs[args.support].keys()
    ), f"Requested device ({args.device}) not found in {config_file}"
    config = available_configs[args.support][args.device]
    ##################################################

    print("Config:\n", json.dumps(config, indent=2, sort_keys=True))

    cmd = f"python {args.entry} {' '.join(args.flags)}"

    if args.support == "local":
        commands = [cmd for _ in range(args.runs)]
        for command in commands:
            local_launcher(cmd)

    elif args.support == "slurm":
        scripts = [slurm_script(config, cmd) for _ in range(args.runs)]
        day = date.today().strftime("%Y%m%d")
        exp = f"exp{uuid4().hex[:8]}"
        for i, script in enumerate(scripts):
            name = f"{exp}-{day}-{i}.sbatch"
            slurm_launcher(script, name)
    else:
        raise NotImplementedError
