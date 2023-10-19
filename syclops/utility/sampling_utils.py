"""
Sampling Utilities for Blender.

This module provides utility functions to sample parameters and assets in Blender.
"""

import fnmatch
import glob
import logging
import numbers
import pickle
from typing import List, Union

import bpy
import numpy as np
# from scipy.interpolate import RegularGridInterpolator


# def interpolate_img(img: np.ndarray, locations: np.ndarray) -> np.ndarray:
#     """Get image value at a specific subpixel location using RegularGridInterpolator.

#     Args:
#         img: Image as a numpy ndarray.
#         locations: Locations where image value is needed.

#     Returns:
#         np.ndarray: Interpolated image values.
#     """
#     rows = np.arange(img.shape[0])
#     cols = np.arange(img.shape[1])

#     pixels = (rows, cols)
#     interpol_func = RegularGridInterpolator(
#         pixels,
#         img,
#         method="linear",
#         bounds_error=False,
#         fill_value=0,
#     )
#     return interpol_func(locations)
def interpolate_img(img: np.ndarray, locations: np.ndarray) -> np.ndarray:
    """Get image value at a specific subpixel location using bilinear interpolation."""
    
    # Extract x and y coordinates from locations
    y, x = locations[:, 0], locations[:, 1]
    
    # Obtain the four surrounding integer coordinates
    x1 = np.floor(x).astype(int)
    x2 = np.clip(x1 + 1, 0, img.shape[1]-1)
    y1 = np.floor(y).astype(int)
    y2 = np.clip(y1 + 1, 0, img.shape[0]-1)
    
    # Compute the weights
    w1, w2 = x - x1, y - y1
    
    # Bilinear interpolation formula
    values = (
        (1 - w1) * (1 - w2) * img[y1, x1] +
        w1 * (1 - w2) * img[y1, x2] +
        (1 - w1) * w2 * img[y2, x1] +
        w1 * w2 * img[y2, x2]
    )
    
    return values

def sample_normal(config: tuple) -> np.ndarray:
    """Sample from a normal distribution.

    Args:
        config: Tuple of mean and standard deviation.

    Returns:
        np.ndarray: Sampled value.
    """
    mean = np.array(config[0])
    std = np.array(config[1])
    return np.random.normal(mean, std)


def sample_uniform(config: tuple) -> np.ndarray:
    """Sample from a uniform distribution.

    Args:
        config: Tuple of minimum and maximum values.

    Returns:
        np.ndarray: Sampled value.
    """
    min_val = np.array(config[0])
    max_val = np.array(config[1])
    return np.random.uniform(min_val, max_val)


def sample_step(config: List[Union[float, List]]) -> Union[float, List]:
    """Sample a value based on the current frame in Blender.

    Args:
        config: List of values to be sampled.

    Returns:
        Union[float, List]: Sampled value.
    """
    curr_frame = bpy.context.scene.frame_current
    return config[curr_frame % len(config)]


def sample_linear(config: List[Union[float, List]]) -> Union[float, List]:
    """Sample a linearly interpolated value based on the current frame.

    Args:
        config: List of values to be sampled.

    Returns:
        Union[float, List]: Sampled value.
    """
    curr_frame = bpy.context.scene.frame_current
    start_val = np.array(config[0])
    step_val = np.array(config[1])
    return start_val + step_val * curr_frame


def sample_random_selection(config: List[Union[float, List]]) -> Union[float, List]:
    """Randomly select a value from the given list.

    Args:
        config: List of values to be sampled.

    Returns:
        Union[float, List]: Sampled value.
    """
    return config[np.random.randint(0, len(config))]


def sample_selection_folder(config: str) -> str:
    """Randomly select a file from a given folder.

    Args:
        config: Path to the folder.

    Returns:
        str: Path to the selected file.
    """
    files_in_folder = glob.glob("{0}/*".format(config))
    return files_in_folder[np.random.randint(0, len(files_in_folder))]


def _get_catalog_from_scene() -> dict:
    """Get the catalog dictionary from the Blender scene.

    Returns:
        dict: Catalog dictionary.
    """
    catalog_string = bpy.data.scenes["Scene"]["catalog"]
    return pickle.loads(bytes(catalog_string, "latin1"))


def sample_selection_asset(config: dict) -> str:
    """Randomly select an asset from a given catalog.

    Args:
        config: Dictionary containing the catalog name and asset type.

    Returns:
        str: Path to the selected asset.
    """
    catalog = _get_catalog_from_scene()
    library = catalog[config["library"]]["assets"]
    asset_names = [
        name for name, asset in library.items() if asset["type"] == config["type"]
    ]
    selected_asset = asset_names[np.random.randint(0, len(asset_names))]
    return "{0}/{1}".format(config["library"], selected_asset)


def sample_wildcard(config: dict) -> str:
    """Randomly select an asset matching a given pattern from a catalog.

    Args:
        config: Dictionary containing the catalog name and pattern.

    Returns:
        str: Path to the selected asset.
    """
    catalog = _get_catalog_from_scene()
    library = catalog[config["library"]]["assets"]
    asset_names = [name for name in library if fnmatch.fnmatch(name, config["pattern"])]
    selected_asset = asset_names[np.random.randint(0, len(asset_names))]
    return "{0}/{1}".format(config["library"], selected_asset)


def _sample(parameter):
    sample_functions = [
        "normal",
        "uniform",
        "step",
        "linear",
        "random_selection",
        "selection_folder",
        "selection_asset",
    ]

    if isinstance(parameter, (numbers.Number, str)):
        return parameter
    for sample_func in sample_functions:
        if sample_func in parameter:
            return eval("sample_{0}".format(sample_func))(parameter[sample_func])
    logging.warning("Parameter {0} not supported format".format(parameter))
    raise ValueError("Parameter {0} not supported format".format(parameter))


def eval_param(eval_params: Union[float, dict, str]) -> Union[float, list, str]:
    """Convert a parameter to a discrete value with the help of a sample function.

    Args:
        eval_params: Parameter to be evaluated.

    Returns:
        Union[float, list, str]: Evaluated parameter.
    """
    is_list = isinstance(eval_params, list) or hasattr(eval_params, "to_list")
    eval_params = eval_params if is_list else [eval_params]

    evaluated_param = list(map(_sample, eval_params))
    return evaluated_param if is_list else evaluated_param[0]