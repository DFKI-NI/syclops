"""Utility module for general functions."""

import logging
from pathlib import Path
from typing import List
import pkg_resources
from filelock import FileLock, Timeout
from ruamel import yaml
import importlib.util
import hashlib
import struct

def hash_vector(vector):
    # Convert the 3D vector into bytes
    packed_vector = struct.pack('fff', *vector)

    # Use SHA-256 and truncate to 64 bits
    hash_object = hashlib.sha256(packed_vector)
    hash_digest = hash_object.digest()[:8]

    # Convert the first 8 bytes of the hash to a 64-bit integer
    hash_value = int.from_bytes(hash_digest, byteorder='big', signed=True)

    return hash_value


def create_folder(path: str) -> None:
    """
    Create a folder if it doesn't exist.

    Args:
        path: Path to the folder.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


class AtomicYAMLWriter(object):
    """
    Write YAML files atomically.

    Args:
        filename: Path to the YAML file.
        timeout: Timeout for acquiring the lock.
    """

    def __init__(self, filename: str, timeout: int = 10) -> None:
        """
        Initialize the AtomicYAMLWriter.

        Args:
            filename: Path to the YAML file.
            timeout: Timeout for acquiring the lock.
        """
        self.filename = filename
        self.timeout = timeout

    def add_step(self, step: int, step_dicts: List[dict]) -> None:
        """
        Add a step to the metadata file.

        Args:
            step: The step to add.
            step_dicts: The step details.
        """
        self.data.setdefault("steps", {})[step] = step_dicts

    def __enter__(self) -> "AtomicYAMLWriter":
        """
        Enter the atomic writer context, acquiring the file lock.

        Returns:
            self: Returns the instance of the writer.

        Raises:
            TimeoutError: If the lock could not be acquired.
        """
        self.lock = FileLock("{0}.lock".format(self.filename), timeout=10)

        # Try to acquire lock
        try:
            self.lock.acquire()
        except Timeout:
            raise_str = "Could not acquire lock on {0}.".format(self.filename)
            logging.error(raise_str)
            raise TimeoutError(raise_str)

        # Try to read the YAML file
        try:
            with open(self.filename, "r") as yaml_file:
                self.data = yaml.safe_load(yaml_file)
        except FileNotFoundError:
            self.data = {}

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the atomic writer context, writing data and releasing the lock.

        Args:
            exc_type: The type of the exception.
            exc_value: The exception value.
            traceback: The traceback.
        """
        with open(self.filename, "w") as yaml_file:
            yaml.safe_dump(self.data, yaml_file)
        self.lock.release()


def find_class_id_mapping(job_config: dict) -> dict:
    """Find the class id mapping from the job config.

    Args:
        job_config: The job configuration.

    Returns:
        dict: The class id mapping.
    """
    class_id_mapping = {}

    def recursive_search(dictionary):
        if isinstance(dictionary, dict):
            if "class_id" in dictionary and "name" in dictionary:
                class_id = dictionary["class_id"]
                name = dictionary["name"]
                class_id_mapping.setdefault(class_id, []).append(name)

                if "class_id_offset" in dictionary:
                    for material_name, offset in dictionary["class_id_offset"].items():
                        new_class_id = class_id + offset
                        material_key = f"{name}/{material_name}"
                        class_id_mapping.setdefault(new_class_id, []).append(
                            material_key,
                        )
            for value in dictionary.values():
                recursive_search(value)
        elif isinstance(dictionary, list):
            for element in dictionary:
                recursive_search(element)

    for element in job_config.values():
        recursive_search(element)

    return class_id_mapping

def get_site_packages_path():
    return pkg_resources.get_distribution("syclops").location

def get_module_path(module_name: str) -> Path:
    spec = importlib.util.find_spec(module_name)
    if spec and spec.origin:
        return Path(spec.origin)
    else:
        raise ValueError(f"Cannot find module named {module_name}")
