import os

import ruamel.yaml as yaml
from filelock import FileLock, Timeout
import pkg_resources


def crawl_output_meta(parent_dir: str) -> dict:
    "Craw through folders and subfolders to finde output_meta.yaml files."
    output_meta_dict = {}
    # Scan the folder and its subfolders
    try:
        for root, dirs, files in os.walk(parent_dir):
            if "output_meta.yaml" in files:
                # Acquire a lock on the file
                lock = FileLock(os.path.join(root, "output_meta.yaml.lock"))
                with lock.acquire():
                    # Read the contents of the output_meta.yaml file
                    with open(os.path.join(root, "output_meta.yaml"), "r") as f:
                        output_meta_dict[root] = yaml.safe_load(f)
    except Timeout:
        error_string = f"Could not acquire filelock for {os.path.join(root, 'output_meta.yaml.lock')}"
        print(error_string)
        raise TimeoutError(error_string)
    return output_meta_dict


def filter_type(output_meta_dict: dict, type: str) -> dict:
    "Filter output_meta_dict for a specific type."
    filtered_dict = {}
    for key, value in output_meta_dict.items():
        if value["type"] == type:
            filtered_dict[key] = value
    return filtered_dict

def create_module_instances_pp(config: dict) -> list:
    """Create module instances from config.

    Args:
        config (dict): Config of the module

    Returns:
        list: List of module instances
    """
    instances = []
    modules = _load_plugins_pp()
    for module_name, module_list in config.items():
        for module_instance in module_list:
            instance = modules[module_name](module_instance)
            instances.append(instance)
    return instances

def _load_plugins_pp():
    plugins = {}
    for entry_point in pkg_resources.iter_entry_points('syclops.postprocessing'):
        try:
            plugins[entry_point.name] = entry_point.load()
        except ModuleNotFoundError:
            pass
    return plugins
