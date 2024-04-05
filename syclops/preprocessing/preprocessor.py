from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from PIL import Image
from ruamel.yaml import YAML
from syclops.preprocessing.texture_processor import process_texture
from syclops import utility


CATALOG_LIBRARY_KEY = "Preprocessed Assets"


def read_yaml(path: str) -> dict:
    yaml = YAML()
    with open(path, "r") as f:
        return yaml.load(f)


def find_key_paths(input_dict: dict, key_name: str, path: list = []) -> list:
    """
    Recursively finds the paths to all keys with the given name in a nested dictionary or list.
    Returns an empty list if no matching keys are found.
    """
    paths = []
    if isinstance(input_dict, dict):
        for key, value in input_dict.items():
            if key == key_name:
                paths.append(path + [key])
            paths.extend(find_key_paths(value, key_name, path + [key]))
    elif isinstance(input_dict, list):
        for i, value in enumerate(input_dict):
            paths.extend(find_key_paths(value, key_name, path + [i]))
    return paths


def _get_value_from_path(input_dict: dict, key_path: list) -> Any:
    """
    Gets the value of the key at the given path.
    """
    value = input_dict
    for key in key_path:
        value = value[key]
    return value


def replace_value(input_dict: dict, key_path: list, new_value) -> dict:
    """
    Replaces the value of the key at the given path with the given value.
    """
    input_dict_copy = input_dict
    for key in key_path[:-2]:
        input_dict_copy = input_dict_copy[key]
    input_dict_copy[key_path[-2]] = new_value


def write_yaml(path: str, data: dict):
    """
    Writes the given data to a YAML file at the given path.
    """
    with open(path, "w") as f:
        yaml = YAML()
        yaml.dump(data, f)


def _add_to_catalog(catalog: dict, key: str, value: Any, output_path: str):
    """
    Adds the given key and value to the catalog.
    """
    # Check if the catalog already has a library for the given key path
    if CATALOG_LIBRARY_KEY not in catalog:
        root_path = Path(output_path) / "tmp"
        catalog[CATALOG_LIBRARY_KEY] = {
            "assets": {},
            "root_path": str(root_path.absolute()),
        }
    # Add the asset to the catalog
    catalog[CATALOG_LIBRARY_KEY]["assets"][key] = value


def create_textures(config: dict, catalog: dict, output_path: str):
    """
    Creates synthetic images from the given config and catalog.
    """
    textures = {}
    if "textures" in config:
        texture_dict = config["textures"]
        for texture_name, texture_dict in texture_dict.items():
            num_textures = 1
            if "num_textures" in texture_dict["config"]:
                num_textures = texture_dict["config"]["num_textures"]
            for i in range(num_textures):
                # Combine global texture seed with texture specific seed
                if "seed" in texture_dict["config"] and "textures" in config["seeds"]:
                    texture_dict["config"]["seed"] += i + config["seeds"]["textures"]
                elif "seed" in texture_dict["config"]:
                    texture_dict["config"]["seed"] += i

                texture = process_texture(texture_name, texture_dict, textures, i)
                textures.setdefault(texture_name, []).append(texture)

                # Save the image
                image_folder = Path(output_path) / "tmp" / "images"
                image_folder.mkdir(parents=True, exist_ok=True)
                # Create the image path counting up from 0
                file_name = f"{texture_name}_{i}.png"
                image_path = image_folder / file_name
                # Save to bit from config
                if texture_dict["config"]["bit_depth"] == 8:
                    Image.fromarray((texture * 255).astype(np.uint8)).save(image_path)
                elif texture_dict["config"]["bit_depth"] == 16:
                    Image.fromarray((texture * 65535).astype(np.uint16)).save(
                        image_path
                    )
                else:
                    raise ValueError(
                        f"Invalid bit depth {texture_dict['config']['bit_depth']}. Must be 8 or 16."
                    )

                # Check if asset already in catalog
                catalog_assets = catalog.get(CATALOG_LIBRARY_KEY, {}).get("assets", {})

                if texture_name in catalog_assets:
                    asset_value = catalog_assets[texture_name]
                    if isinstance(asset_value["filepath"], list):
                        asset_value["filepath"].append(
                            str(image_path.relative_to(output_path / "tmp"))
                        )
                    else:
                        asset_value["filepath"] = [
                            asset_value["filepath"],
                            str(image_path.relative_to(output_path / "tmp")),
                        ]
                else:
                    # Add the image path to the catalog
                    asset_value = {
                        "type": "texture",
                        "filepath": str(image_path.relative_to(output_path / "tmp")),
                    }
                _add_to_catalog(catalog, texture_name, asset_value, output_path)


def evaluate_global_evaluators(config: dict, global_evaluators: dict, catalog: dict):
    """
    Evaluates global evaluators in the config.
    """
    evaluated_global_evaluators = {}
    for key, eval_value in global_evaluators.items():
        is_list = isinstance(eval_value, list) or hasattr(eval_value, "to_list")
        if is_list:
            raise ValueError("Global evaluators must be dictionaries.")
        evaluated_global_evaluators[key] = {
            "step": [
                utility.apply_sampling(eval_value, step, catalog)
                for step in range(config["steps"])
            ]
        }

    return evaluated_global_evaluators


def preprocess(config_path: str, catalog_path: str, schema: str, output_path: str):
    config = read_yaml(config_path)
    catalog = read_yaml(catalog_path)
    schema = read_yaml(schema)

    # Evaluate global evaluators
    global_evaluators = config.get("global_evaluators", {})
    evaluated_global_evaluators = evaluate_global_evaluators(
        config, global_evaluators, catalog
    )

    # Replace global evaluator references in sensor configurations
    for sensor_config in config["sensor"].values():
        for sensor in sensor_config:
            for key, value in sensor.items():
                if isinstance(value, str) and value.startswith("$global."):
                    global_key = value[8:]
                    sensor[key] = evaluated_global_evaluators[global_key]
    try:
        validate(config, schema)
        print("Job Config is valid!")
    except ValidationError as e:
        print("Job Config is invalid:")
        print(e.schema["errorMessage"] if "errorMessage" in e.schema else e.message)
    create_textures(config, catalog, output_path)
    catalog_output_path = Path(output_path) / "asset_catalog.yaml"
    config_output_path = Path(output_path) / "config.yaml"
    write_yaml(catalog_output_path, catalog)
    write_yaml(config_output_path, config)
    return config_output_path, catalog_output_path
