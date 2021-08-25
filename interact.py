import argparse
from pathlib import Path
import json


def make_flags(conf):
    flags = " ".join(f"--{flag}={value}" for flag, value in conf["resources"].items())
    return flags


config_file = "config.json"


def read_conf(resource):
    assert Path(config_file).exists(), f"Configuration file ({config_file}) not found."
    with open(config_file, "r") as f:
        available_configs = json.loads(f.read())
    assert (
        resource in available_configs.keys()
    ), f"Requested configuration ({resource}) not found in config file ({config_file})"

    config = available_configs[resource]
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="interact")
    parser.add_argument("resource")
    args = parser.parse_args()

    # print("Config:\n", json.dumps(config, indent=2, sort_keys=True))
    config = read_conf(args.resource)
    flags = make_flags(config)
    cmd = f"srun {flags} --accel-bind=g --pty bash"

    print(cmd)
