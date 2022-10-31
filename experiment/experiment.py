import datetime
import json
import logging
import os
import sys
import random
import string
from datetime import datetime as dt
from git import Repo
from pathlib import Path
from copy import deepcopy
import logging.handlers


def is_git():
    """
    Returns true if the current folder is a git repo.
    """
    return os.system("git rev-parse") == 0


def random_tag(size=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(size))


class experiment:
    """
    Class to create directory and other meta information to store experiment results.
    """

    def __init__(self, name, args, output_dir="../"):
        assert args is not None, "Experiment args cannot be None"

        self.command_args = "python " + " ".join(sys.argv)
        self.date = datetime.datetime.now().strftime("%d%B%Y")

        if is_git():
            self.repo = Repo(".", search_parent_directories=True)
            self.root = Path(self.repo.git.rev_parse("--show-toplevel"))
            self.info = {
                "commit": self.repo.head.commit.hexsha,
                "time_start": str(dt.now()),
                "completed": False,
            }
        else:
            self.root = Path(".")
            self.info = {
                "commit": "no_git",
                "time_start": str(dt.now()),
                "completed": False,
            }

        self.name = name
        self.params = deepcopy(vars(args))
        print("Experiment params", self.params)
        # params should contain values common to every job with the same config, move seed to info
        # this way I can group jobs with the same configuration by hashing the params dict
        self.info["seed"] = self.params["seed"]
        del self.params["seed"]
        self.results = {}
        self.dir = self.root / output_dir / self.date

        # create folder with experiments grouped by day
        self.dir.mkdir(exist_ok=True, parents=True)

        # add short random string to have semi-unique folder names
        self.folder = self.name + "-" + random_tag(5)
        self.path = self.dir / self.folder

        # create folder for the current experiment
        self.path.mkdir(exist_ok=True, parents=True)

        # add folder to store saved models and stuff
        self.save_dir = self.path / "saved"
        self.save_dir.mkdir(exist_ok=True, parents=True)

        self.logger = logging.getLogger("experiment")
        # Add handler to store log in the experiment folder
        fh = logging.FileHandler(self.path / "log.txt")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s %(name)s: - %(message)s", datefmt="%d-%b-%y %H:%M:%S"
            )
        )
        self.logger.addHandler(fh)
        # we still want to see what's going on so we'll add a stream going to the terminal
        ch = logging.handlers.logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(
            logging.Formatter(
                "%(asctime)s %(name)s %(levelname)s: - %(message)s",
                datefmt="%d-%b-%y %H:%M:%S",
            )
        )
        self.logger.addHandler(ch)
        self.logger.setLevel(logging.INFO)

        self.write(self.params, "params")
        self.write(self.info, "info")

    def write(self, data, name):
        with open(self.path / f"{name}.json", "w") as outfile:
            json.dump(data, outfile, indent=4, separators=(",", ": "), sort_keys=True)
            outfile.write("")

    def elapsed(self, end, start):
        return str(dt.fromisoformat(end) - dt.fromisoformat(start))

    def finish(self):
        self.info["time_end"] = str(dt.now())
        self.info["time_elapsed"] = self.elapsed(
            self.info["time_end"], self.info["time_start"]
        )
        self.info["completed"] = True
        self.write(self.info, "info")
