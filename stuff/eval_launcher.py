#!/usr/bin/env python
import json
import argparse
import subprocess as sub
from pathlib import Path

from launch_utils import make_launch_job, prepare_command


def main(args):

    # info: flags used to setup environment and launch experiments
    # slurm: flags for the slurm scheduler system
    with open(args.metadata, "r") as f:
        data = json.loads(f.read())
        print(data)

    # choose correct slurm settings for cpu/gpu
    device = args.device
    slurm = data[
        f"slurm_{device}"
    ]  # cannot put device in params because experiemnts run on different devices are not "different"
    env = data["env"][args.support]

    # Example folder structure:
    #
    # results
    # └── 21April2020 -> args.folder = results/21April2020
    #        ├── rln_fixed_dwlky -> args.project = rln_fixed
    #        │   ├── data.csv
    #        │   ├── info.json
    #        │   ├── log.txt
    #        │   ├── params.json
    #        │   └── saved
    #        │       ├── neuromod_hebb-000999.model
    #        │       ├── neuromod_hebb-009999.hebb
    #        │       └── neuromod_hebb-009999.model
    #        └── testing_feature_ipqrp
    #            ├── data.csv
    #            ├── info.json
    #            ├── log.txt
    #            ├── params.json
    #            └── saved
    #                ├── neuromod_diffplast-000999.model
    #                ├── neuromod_diffplast-009999.hebb
    #                └── neuromod_diffplast-009999.model

    # Folders with the results
    path = Path(args.folder)  # e.g. results/21April2020
    trials = list(path.iterdir())  # e.g. [rln_fixed_ipqrp, rln_fixed_dwlky]

    # evaluate_classification requires path and model, gather that and assemble
    # a list of configurations to run
    configs = []
    for trial in filter(lambda trial: trial.stem.split("-")[0] == args.project, trials):
        # check what models are in the target folders and check for the correct epoch
        models = filter(
            lambda file: file.suffix == ".model"
            and f"{args.epoch :0>6}" in file.as_posix(),
            (trial / "saved").iterdir(),
        )  # epochs are 6 digits zero padded
        for model_path in models:
            # model name -> treatment -> how many layers to freeze
            # model_name = model_path.stem
            # location where to save evaluation results
            configs.append({"path": trial, "model": model_path.name, "runs": args.runs})

    # Turn the dicts into strings that will used with sbatch (through temp files), god the pain
    commands = [
        prepare_command("omniglot_testing.py", config, args.device)
        for config in configs
    ]

    launch_job = make_launch_job(slurm, env)
    for command in commands:
        if args.debug:
            print(launch_job(command, debug=True))
            print("---")
        else:
            if args.support == "local":
                command = command.split(" ")
                print(command)
                process = sub.Popen(command)
                process.wait()
            else:
                print("Launching", command)
                launch_job(command, debug=False)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()

    # OPTIONAL
    argparser.add_argument(
        "--metadata",
        type=str,
        help="Json file containing the information about slurm and such.",
        default="SLURM.json",
    )
    argparser.add_argument("--device", type=str, help="cpu/gpu", default="cpu")
    argparser.add_argument("--support", type=str, help="local/slurm", default="local")
    argparser.add_argument(
        "--debug",
        action="store_true",
        help="Use debug to print commands instead of running them.",
    )
    argparser.add_argument(
        "--runs", type=int, help="How many repetitions to run.", default=5,
    )

    # NEEDED
    argparser.add_argument(
        "--folder", required=True, type=str, help="Folder with the models to evaluate.",
    )
    argparser.add_argument(
        "--project", required=True, type=str, help="Name of the project to evaluate.",
    )
    argparser.add_argument(
        "--epoch",
        required=True,
        type=int,
        help="Epoch of the model to evaluate (e.g. 20000)",
    )

    ARGS = argparser.parse_args()
    print(ARGS)
    main(ARGS)
