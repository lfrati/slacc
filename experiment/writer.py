from pathlib import Path
import csv


class Writer:
    def __init__(self, path, fieldnames, name="data"):
        assert len(fieldnames) == len(set(fieldnames)), "Duplicates in fieldnames"

        self.results_path = Path(path) / (name + ".csv")
        self.results_file = open(self.results_path, "w")
        self.fieldnames = set(fieldnames)

        self.results_csv_writer = csv.DictWriter(
            self.results_file, fieldnames=sorted(list(self.fieldnames))
        )
        self.results_csv_writer.writeheader()
        self.buffer = []

    def add(self, results):
        assert (
            set(results.keys()) == self.fieldnames
        ), f"Logging wrong fieldnames: Expected {self.fieldnames}, got {set(results.keys())}"
        self.buffer.append(results)

    def write(self):
        self.results_csv_writer.writerows(self.buffer)
        self.buffer = []
