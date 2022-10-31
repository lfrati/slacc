import os
import subprocess as sub
import random
from copy import deepcopy
from itertools import product
from pathlib import Path
import json
import numpy as np


def make_instantiate(parameters, deps="deps.json"):
    if deps != "":
        constraints = Path(deps)
        if constraints.exists():
            constraints = json.loads(constraints.read_text())
            yield from smart_instantiate(parameters, constraints)
        else:
            raise RuntimeError(f"Dependency file {deps} not found!")
    else:
        yield from instantiate(parameters)


def get_ignores(constraints):
    """
    Ignores are provided as a group of lists of 2 lists (keys and values).
    Expand it into a dictionary of {key : values}
    e.g.
    "groups":[{ "names": ["ANML", "OML"],
                "ignore": ["onehot_lr","signvec_lr"]
              }]
    ->
    {"ANML":["onehot_lr","signvec_lr"],
     "OML" :["onehot_lr","signvec_lr"]}

    """
    return {
        name: group["ignore"]
        for group in constraints["groups"]
        for name in group["names"]
    }


def make_xorfn(fields, val):
    """
    Check that not all the target fields are False/0
    -> at least one (any) is True/1
    """
    return lambda x: any([x[field] != val for field in fields])


def smart_instantiate(parameters, constraints):
    variables = {key: val for key, val in parameters.items() if isinstance(val, list)}
    fixed = {key: val for key, val in parameters.items() if not isinstance(val, list)}
    ignores = get_ignores(constraints)

    # get the values of the key field e.g.
    # key_field = model_type
    # vals[key_field] = ["ANML","hebb"]
    key_field = constraints["key_field"]

    for key in parameters[key_field]:

        # check if there are restrictions to apply
        if key in ignores:
            to_ignore = ignores[key]
        else:
            to_ignore = []

        # get the options that are not ignored, nor the key_field
        # e.g. var_fields = [('onehot_lr', [0.1, 10]), ('noinner', [0, 1])]
        variable_fields = [
            (field, values)
            for field, values in variables.items()
            if field not in to_ignore and field != constraints["key_field"]
        ]

        # Get a list of list of pairs of options
        # opts = [[('onehot_lr', 0.1),('onehot_lr', 10)],
        #         [('noinner', 0), ('noinner', 1)]]
        opts = [[(key, val) for val in vals] for key, vals in variable_fields]

        # Generate possible combinations
        # [(('onehot_lr', 0.1), ('noinner', 0)),
        #  (('onehot_lr', 0.1), ('noinner', 1)),
        #  (('onehot_lr',  10), ('noinner', 0)),
        #  (('onehot_lr',  10), ('noinner', 1))]
        instances = list(product(*opts))

        # check that none of the xor conditions are violated
        # -> all of the checks are true
        xor_false_checks = lambda x: all(
            [make_xorfn(fields, 1)(x) for fields in constraints["xor_TRUE"]]
        )

        for instance in instances:
            # init the template with fixed fields commont to all runs
            template = deepcopy(fixed)
            # add the key_field value e.g. 'model_type': 'ANML'
            template[key_field] = key
            # insert remaining fields from iterable of pairs
            template.update(instance)

            # Check if dict just created is legal
            if xor_false_checks(template):
                yield template


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


def test_make_instantiate():
    opts = {
        "model_type": ["ANML", "hebb", "OML", "neuromod_diffplast"],
        "onehot_lr": [0.1, 0.001, 0.001],
        "noinner": [0, 1],
        "steps": 42,
    }
    full_variables = [len(val) for key, val in opts.items() if isinstance(val, list)]
    full_instantiate = np.prod(full_variables)

    assert (
        len([conf for conf in make_instantiate(opts, deps=False)]) == full_instantiate
    )

    constraints = Path("deps.json")
    if constraints.exists():
        constraints = json.loads(constraints.read_text())
        smart_variables = {
            key: len(val) for key, val in opts.items() if isinstance(val, list)
        }
        ignores = get_ignores(constraints)
        partial_instantiate = 0
        for key in opts[constraints["key_field"]]:
            fields = [
                num_opts
                for field, num_opts in smart_variables.items()
                if field not in ignores[key] and field != constraints["key_field"]
            ]
            partial_instantiate += np.prod(fields)
        assert (
            len([conf for conf in make_instantiate(opts, deps=True)])
            == partial_instantiate
        )


def make_launch_job(params, env):
    """
    Create function to use to run each job script. The scripts have a header with info for the
    SLURM workload manager, instead of passing it around we use a closure.
    """

    # create the header only once
    slurm_header = make_header(params, env)

    def launch_job(cmd, debug=False):
        # add header to command
        cmd = slurm_header + cmd
        if debug:
            return cmd
        # one day I'll figure out how to use srun directly, for now
        # create a temp file with the sbatch syntax, launch it and then delete it
        tmp_name = f"{random.getrandbits(32)}.batch"
        with open(tmp_name, "w") as f:
            f.write(cmd)

        # redirect unwanted output to null
        with open(os.devnull, "w") as FNULL:
            try:
                sub.call(["sbatch", f"{tmp_name}"], shell=False, stdout=FNULL)
            except sub.CalledProcessError as e:
                print("ERROR", e)

        # delete the temporary file we passed to sbatch
        sub.call(["rm", f"{tmp_name}"], shell=False)

    return launch_job


def prepare_command(entrypoint, py_params, device):
    """
    Generate the python command to run with all the needed flags
    """
    py_flags = [f"--{key} {val}" for key, val in py_params.items()]
    py_flags.append(f"--device {device}")

    return f"python {entrypoint} {' '.join(sorted(py_flags))}"


def make_header(slurm, env):
    """
    Generate the information to be passed to SLURM about the job
    Also take care of setting up the environment
    The python command will be added afterwards
    """
    shebang = ["#!/bin/bash", ""]
    flags = [
        f"#SBATCH --{flag}={value}" for flag, value in slurm.items() if flag != "env"
    ]
    environment = [
        "",
        f"{env}\n",
    ]
    return "\n".join(shebang + flags + environment)
