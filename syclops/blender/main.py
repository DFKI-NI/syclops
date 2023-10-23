"""Main module for handling command-line arguments and launching the scene creator."""

import argparse
import sys
from pathlib import Path

# Constants
DEBUG_PORT = 5678
DEFAULT_JOB_CONFIG = "job_config.yaml"
DEFAULT_CATALOG = "catalog.yaml"


def read_yaml_file(file_path: str) -> dict:
    """Read a YAML file and return its content.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        dict: Content of the YAML file.
    """
    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit(f"File {file_path} not found.")
    except yaml.YAMLError:
        sys.exit(f"Error reading {file_path}.")


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        Namespace: Command-line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug-scene-creator",
        help="Enable debug mode",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--config", help="Path to config file", default=DEFAULT_JOB_CONFIG
    )
    parser.add_argument(
        "--catalog", help="Path to catalog file", default=DEFAULT_CATALOG
    )
    parser.add_argument(
        "--site-packages-path", help="Path to site-packages"
    )

    argv = sys.argv
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]
    return parser.parse_args(argv)


def main(args):
    """Execute the main scene rendering workflow.

    Args:
        args (Namespace): Command-line arguments
    """
    job_config = read_yaml_file(str(Path(args.config).resolve()))
    catalog = read_yaml_file(str(Path(args.catalog).resolve()))

    scene = Scene(catalog, job_config)
    scene.render()


if __name__ == "__main__":
    args = parse_arguments()
    
    site_packages_path = Path(args.site_packages_path).resolve()
    print(f"Adding {site_packages_path} to sys.path")
    sys.path.append(str(site_packages_path))

    import debugpy
    import yaml
    from syclops.blender.scene import Scene

    if args.debug_scene_creator:
        print("Waiting for debugger to attach...")
        debugpy.listen(DEBUG_PORT)
        debugpy.wait_for_client()

    main(args)

