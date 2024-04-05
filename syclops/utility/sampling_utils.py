"""
Sampling Utilities for Blender.

This module provides utility functions to sample parameters and assets in Blender.
"""

import fnmatch
import glob
import logging
import numbers
from typing import List, Union
import numpy as np

def sample_normal(config: tuple, *args) -> np.ndarray:
    """Sample from a normal distribution.

    Args:
        config: Tuple of mean and standard deviation.

    Returns:
        np.ndarray: Sampled value.
    """
    mean = np.array(config[0])
    std = np.array(config[1])
    return np.random.normal(mean, std)


def sample_uniform(config: tuple, *args) -> np.ndarray:
    """Sample from a uniform distribution.

    Args:
        config: Tuple of minimum and maximum values.

    Returns:
        np.ndarray: Sampled value.
    """
    min_val = np.array(config[0])
    max_val = np.array(config[1])
    return np.random.uniform(min_val, max_val)


def sample_step(
    config: List[Union[float, List]], curr_frame, *args
) -> Union[float, List]:
    """Sample a value based on the current frame in Blender.

    Args:
        config: List of values to be sampled.
        curr_frame: Current frame in Blender.

    Returns:
        Union[float, List]: Sampled value.
    """
    return config[curr_frame % len(config)]


def sample_linear(
    config: List[Union[float, List]], curr_frame, *args
) -> Union[float, List]:
    """Sample a linearly interpolated value based on the current frame.

    Args:
        config: List of values to be sampled.
        curr_frame: Current frame in Blender.

    Returns:
        Union[float, List]: Sampled value.
    """

    start_val = np.array(config[0])
    step_val = np.array(config[1])
    return start_val + step_val * curr_frame


def sample_random_selection(
    config: List[Union[float, List]], *args
) -> Union[float, List]:
    """Randomly select a value from the given list.

    Args:
        config: List of values to be sampled.

    Returns:
        Union[float, List]: Sampled value.
    """
    return config[np.random.randint(0, len(config))]


def sample_selection_folder(config: str, *args) -> str:
    """Randomly select a file from a given folder.

    Args:
        config: Path to the folder.

    Returns:
        str: Path to the selected file.
    """
    files_in_folder = glob.glob("{0}/*".format(config))
    return files_in_folder[np.random.randint(0, len(files_in_folder))]


def sample_selection_asset(config: dict, *args, catalog) -> str:
    """Randomly select an asset from a given catalog.

    Args:
        config: Dictionary containing the catalog name and asset type.
        catalog: Dictionary containing the catalog.

    Returns:
        str: Path to the selected asset.
    """
    library = catalog[config["library"]]["assets"]
    asset_names = [
        name for name, asset in library.items() if asset["type"] == config["type"]
    ]
    selected_asset = asset_names[np.random.randint(0, len(asset_names))]
    return "{0}/{1}".format(config["library"], selected_asset)


def sample_wildcard(config: dict, *args, catalog) -> str:
    """Randomly select an asset matching a given pattern from a catalog.

    Args:
        config: Dictionary containing the catalog name and pattern.
        catalog: Dictionary containing the catalog.

    Returns:
        str: Path to the selected asset.
    """
    library = catalog[config["library"]]["assets"]
    asset_names = [name for name in library if fnmatch.fnmatch(name, config["pattern"])]
    selected_asset = asset_names[np.random.randint(0, len(asset_names))]
    return "{0}/{1}".format(config["library"], selected_asset)


def apply_sampling(parameter, curr_frame=None, catalog=None):
    sample_functions = [
        "normal",
        "uniform",
        "step",
        "linear",
        "random_selection",
        "selection_folder",
        "selection_asset",
        "wildcard",
    ]

    if isinstance(parameter, (numbers.Number, str)):
        return parameter
    for sample_func in sample_functions:
        if sample_func in parameter:
            if sample_func in ["selection_asset", "wildcard"]:
                return eval(f"sample_{sample_func}")(
                    parameter[sample_func], curr_frame, catalog=catalog
                )
            else:
                return eval(f"sample_{sample_func}")(
                    parameter[sample_func], curr_frame
                )
    logging.warning("Parameter {0} not supported format".format(parameter))
    raise ValueError("Parameter {0} not supported format".format(parameter))
