import argparse
import sys
import threading
from pathlib import Path

import yaml
from syclops import utility

argv = sys.argv
parser = argparse.ArgumentParser()
parser.add_argument(
    "--config",
    help="Path to config file",
    default="job_config.yaml",
)
parser.add_argument(
    "--catalog",
    help="Path to catalog file",
    default="catalog.yaml",
)
parser.add_argument(
    "--output-path",
    help="Output path folder",
    default="",
)



def main():
    args = parser.parse_args(argv[1:])

    JOB_CONFIG = str(Path(args.config).resolve())
    CATALOG = str(Path(args.catalog).resolve())

    postprocessing_jobs = []

    # Read YAML files
    with open(JOB_CONFIG, "r") as f:
        job_config = yaml.safe_load(f)
    with open(CATALOG, "r") as f:
        catalog = yaml.safe_load(f)

    # Add output folder as parent dir to job config postprocessing
    if "postprocessing" in job_config:
        for _, job in job_config["postprocessing"].items():
            for elem in job:
                elem["parent_dir"] = str(Path(args.output_path).resolve())

        postprocessing_jobs = utility.create_module_instances_pp(
            job_config["postprocessing"],
        )

        jobs = [threading.Thread(target=job.run) for job in postprocessing_jobs]
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()


if __name__ == "__main__":
    main()
