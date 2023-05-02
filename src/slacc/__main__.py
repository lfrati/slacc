import argparse
import importlib.resources as pkg_resources
import json
import os
from pathlib import Path
import shutil
import subprocess as sub
import tempfile

DEBUG = os.getenv("DEBUG", None) is not None


def write_conf():
    available_configs = json.loads(pkg_resources.read_text(__package__, "config.json"))
    user_config_file = Path.home() / ".config" / "slacc" / "config.json"
    if not user_config_file.exists():
        with open(user_config_file, "w") as f:
            f.write(json.dumps(available_configs, indent=2))
        print(f"Copied default config.json to {user_config_file}")
    else:
        print(f"{user_config_file} exists already. Abort.")


def read_conf(args, parser):
    """
    Retrieve the requested configuration from the available json configs.
    """

    # first look for the default ones shipped with the package
    available_configs = json.loads(pkg_resources.read_text(__package__, "config.json"))

    user_config_file = Path.home() / ".config" / "slacc" / "config.json"

    if user_config_file.exists():
        assert (
            user_config_file.is_file()
        ), f"Configuration file ({user_config_file}) is not a file."
        print(f"Found custom configs: {user_config_file}")
        try:
            with open(user_config_file, "r") as f:
                user_configs = json.loads(f.read())
        except json.JSONDecodeError:
            parser.error(f"Could not parse custom config: {user_config_file}")
        else:
            print(
                f"Added user configs {list(user_configs.keys())} to available configs."
            )
            available_configs.update(user_configs)
    else:
        print(f"No user defined configs found in: {user_config_file}.")

    # then for any custom ones in the same folder as the script being launched
    try:
        custom_config_file = args.script.parent / "config.json"
    except AttributeError:
        # or the current folder if using sinteract (doesn't specify a script)
        custom_config_file = Path.cwd() / "config.json"

    if custom_config_file.exists():
        assert (
            custom_config_file.is_file()
        ), f"Configuration file ({custom_config_file}) is not a file."
        print(f"Found custom configs: {custom_config_file}")
        try:
            with open(custom_config_file, "r") as f:
                custom_configs = json.loads(f.read())
        except json.JSONDecodeError:
            parser.error(f"Could not parse custom config: {custom_config_file}")
        else:
            print(
                f"Added custom configs {list(custom_configs.keys())} to available configs."
            )
            available_configs.update(custom_configs)

    if args.resource not in available_configs.keys():
        parser.error(
            f"Requested resource ({args.resource}) not found in config file.\nAvailable: {available_configs}"
        )

    config = available_configs[args.resource]
    return config


########################### cli command: sinteract resource ###########################


def make_flags(conf):
    flags = " ".join(f"--{flag}={value}" for flag, value in conf["resources"].items())
    return flags


def interact():
    parser = argparse.ArgumentParser(prog="interact")
    parser.add_argument("resource")
    args = parser.parse_args()

    # print("Config:\n", json.dumps(config, indent=2, sort_keys=True))
    config = read_conf(args, parser)
    flags = make_flags(config)
    cmd = f"srun {flags} --accel-bind=g --pty bash"

    print(cmd)
    if not DEBUG:
        sub.call(cmd.split(" "), shell=False)


########################### cli command: slaunch opts ###########################

"""
Utility to launch a python script on SLURM, using CPU or GPU. Uses configuration
information from config.json and supports launching sweeps or repeats.

Flags can be passed to the delegated script by appending them at the end as follows
    > slaunch <resource> [--runs] <script> [<flags>...]
For example, this:
    > slaunch moran-gpu --runs 2 dummy_gpujob.py --epochs=10 --seed 42
is equivalent to twice running this:
    > python dummy_gpujob.py --epochs=10 --seed 42

Furthermore, any settings accepted by `sbatch` may be supplied on the command line.
IMPORTANT: The sbatch options must be supplied in "--name=value" fashion, with an
equals sign; "--name value" will NOT parse correctly. For any other options
(including script flags) you may use either format.
"""


class HelpFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    """
    This class adds no new functionality, only is used to combine the existing functionality of two different
    formatters through multiple inheritance.
    """

    pass


def slurm_launcher(cmd, sbatch_args):
    """
    Create a temp file with the slurm sbatch syntax, launch it and then delete it.
    """
    if DEBUG:
        print("\n#### OUTPUT SCRIPT ####")
        print(cmd)
        print("\n#### SBATCH CALL ####")
        sbatch_cmd = ["sbatch"] + sbatch_args + ["<file>"]
        print(" ".join(sbatch_cmd))
        print()
        return 0

    with tempfile.NamedTemporaryFile() as f:
        f.write(cmd.encode("utf-8"))
        f.flush()
        return sub.call(["sbatch"] + sbatch_args + [f"{f.name}"], shell=False)


def make_slurm_script(conf, cmd, argfile, num_runs):
    """
    Generate the information to be passed to SLURM about the job.
    Also take care of setting up the environment.
    The python command will be added afterwards.
    """
    if argfile:
        # Count the number of arg lines in the arg file.
        with argfile.open() as f:
            num_runs = 0
            has_blank = False
            for i, line in enumerate(f):
                if line.strip():
                    # This is a non-blank line.
                    num_runs += 1
                    # If a non-blank follows any blank line...
                    if has_blank:
                        raise RuntimeError(
                            "Argfile cannot have blank lines, except at the end of the file. Found"
                            f" blank at line {i-1}."
                        )
                else:
                    has_blank = True
    if num_runs < 1:
        raise ValueError(
            f"num_runs should be a positive number, but is {num_runs} instead."
        )

    # Gur furonat vf abg arrqrq ol fyhez, ohg pna or hfrshy vs jr jnag gb gel ehaavat gur fpevcg
    # bhefryirf.
    script = "#!/bin/bash\n"

    # sbatch flags
    for flag, value in conf["resources"].items():
        script += f"#SBATCH --{flag}={value}\n"
    if num_runs > 1:
        # If we have multiple jobs, launch them as an array.
        script += f"#SBATCH --array=1-{num_runs}\n"

    # Shell commands
    script += "\n"
    script += "source ~/.bash_profile\n"  # build the user's environment just as if we spawned a new login shell
    script += "set -e\n"  # exit if any command fails (IMPORTANT: only set this after shell setup)
    script += "set -o pipefail\n"  # cause errors within a series of piped commands to bubble to the surface
    script += "cd ${SLURM_SUBMIT_DIR}\n"  # run in the same directory as the python script, so relative paths work
    script += f'CMD="{cmd}"\n'
    if argfile:
        # Takes the Nth line from the argfile as additional args for the command.
        script += f'ARGLIST="$(head -$SLURM_ARRAY_TASK_ID {argfile} | tail -1)"\n'
        script += 'CMD="$CMD $ARGLIST"\n'
    script += 'echo "Command: $CMD"\n'  # print the command we're about to run
    script += conf["env"] + "\n"  # activate conda env
    script += f'eval "$CMD"\n'  # finally, launch program
    return script


def validate_and_setup(parser, args):
    """
    Validate command line arguments, and setup files for input/output.
    """

    print(f"{args=}")

    config = read_conf(args, parser)

    # Set up destination directory.
    if args.rundir:
        args.rundir = Path(args.rundir).resolve()
        if not DEBUG:
            args.rundir.mkdir(exist_ok=True, parents=True)
    else:
        args.rundir = Path(".").resolve()

    if not args.force and list(args.rundir.glob("slurm-*.out")):
        parser.error(
            f"A Slurm output file already exists in the target directory: {args.rundir.resolve()}.\n"
            "Use -f/--force to run in this folder anyway."
        )

    # Copy argfile to destination if not already there (do this last so we don't copy it needlessly when the above
    # checks fail).
    if args.argfile and args.argfile.parent != args.rundir:
        destfile = args.rundir / args.argfile.name
        if not args.force and destfile.exists():
            parser.error(
                f"Argfile already exists in the target directory: {destfile}.\nUse -f/--force to overwrite."
            )
        if not DEBUG:
            shutil.copy(args.argfile, args.rundir)
            args.argfile = destfile
        else:
            print(f"Would copy {args.argfile} into {args.rundir}.")

    return config


def check_path(path):
    pathobj = Path(path)
    if pathobj.exists():
        return pathobj.resolve()
    else:
        raise argparse.ArgumentTypeError(f"Not a valid path: {path}")


def check_file(path):
    pathobj = check_path(path)
    if pathobj.is_file():
        return pathobj
    else:
        raise argparse.ArgumentTypeError(f"Exists, but not a file: {path}")


def launch():
    if DEBUG:
        print(
            "#####################\n" + "##### DEBUG MODE ####\n"
            "#####################\n"
        )

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=HelpFormatter)
    parser.add_argument(
        "resource",
        help="Identifier of the resource configuration to use. Must be one of the configs present in config.json.",
    )
    parser.add_argument(
        "-r",
        "--runs",
        type=int,
        default=1,
        help="How many repetitions to run. This will result in an array of jobs, rather than a single job.",
    )
    parser.add_argument(
        "--argfile",
        type=check_path,
        help="A file containing a list of argument strings, one per job. This will result in an array of jobs, where"
        " each job corresponds to a single line of this file. The args in the file are tacked onto the end of the"
        " command given. If this argument is present, --runs will be ignored.",
    )
    parser.add_argument(
        "-d",
        "--rundir",
        type=Path,
        help="The directory from which to launch the script. Slurm output will be directed here.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Launch a new job even if another job has already used this output directory. Does not remove the"
        " previous output log, and only needed when specifying --rundir.",
    )
    parser.add_argument("script", type=check_file, help="The python script to launch.")
    parser.add_argument(
        "flags",
        nargs=argparse.REMAINDER,
        help="Flags to be passed to the python script.",
    )
    args, sbatch_args = parser.parse_known_args()

    config = validate_and_setup(parser, args)

    if not DEBUG:
        os.chdir(args.rundir)
    print("Running from:", args.rundir.resolve())
    print("Python script:", args.script)
    print("Flags:", args.flags)
    print("Config:\n", json.dumps(config, indent=2, sort_keys=True))

    cmd = f"time python {args.script} {' '.join(args.flags)}"
    script = make_slurm_script(config, cmd, args.argfile, args.runs)
    return slurm_launcher(script, sbatch_args)
