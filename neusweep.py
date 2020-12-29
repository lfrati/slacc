#!/usr/bin/env python

import argparse
import json
import os
import subprocess as sub
from copy import deepcopy
from itertools import product
from pathlib import Path

from prompt_toolkit.shortcuts import confirm

import numpy as np

DEBUG = os.getenv("DEBUG", None) is not None


def instantiate(parameters):
    """
    Turn a dictionary of lists into a list of dictionaries of all combinations
      key   values
    {'lr':[0.1,0.01]}} -> [{'lr',0.1},{'lr',0.1}]
    """
    variables = [
        [(key, value) for value in values]
        for key, values in parameters.items()
        if isinstance(values, list)
    ]

    if len(variables) > 0:
        # generate all possible combinations
        options = list(product(*variables))

        for option in options:
            # replace the fields that contained lists with actual values
            template = deepcopy(parameters)
            template.update(option)
            yield template
    else:
        yield parameters


def launcher(cmd):
    if DEBUG:
        print(cmd)
        return

    parts = cmd.split(" ")
    process = sub.Popen(parts)
    process.wait()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="neusweep")
    parser.add_argument("entry", help="Python script to sweep")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments to be passed to the script being swept",
    )
    args = parser.parse_args()

    params_file = "params.json"

    print("Entry:", args.entry)
    print("Args:", args.args)

    ################# VALIDATE INPUT #################
    assert Path(args.entry).exists(), f"File {args.entry} not found."
    assert Path(params_file).exists(), f"Configuration file ({params_file}) not found."
    with open(params_file, "r") as f:
        params = json.loads(f.read())
    ##################################################

    print("Params:\n", json.dumps(params, indent=2, sort_keys=True))

    cmd = f"python {args.entry} {' '.join(args.args)}"
    print(cmd)

    configurations = [
        " ".join(f"--{key}={val}" for key, val in configuration.items())
        for configuration in list(instantiate(params))
    ]

    try:
        answer = confirm(f"\n {len(configurations)} jobs ready to launch. Continue?")
        print()
    except OSError:
        pass

    for configuration in configurations:
        launcher(cmd + configuration)
