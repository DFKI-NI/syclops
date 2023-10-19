import os
from abc import ABC
from pathlib import Path
from typing import Union

import ruamel.yaml as yaml
from filelock import FileLock, Timeout


class PostprocessorBase(ABC):
    def __init__(self, config: dict):
        self.config: dict = config
        self.input_metadata: dict = {}
        self.output_metadata: dict = {}

        self.processed_steps: dict = {}
        self.expected_steps: int = 0
        self.sensor_name: str = ""
        self.output_folder: str = ""

    def _setup(self, output_folder: str):
        self.expected_steps = self._calc_expected_steps()
        self.output_folder = output_folder
        self._create_output_folder()

    def _write_output_metadata(self, processed_dict: dict):
        """Function that writes the output metadata to the metadata.yaml file.

        Args:
            processed_dict (dict): Dictionary containing the processed data of one or multiple steps
        """
        self._update_output_metadata(processed_dict)
        self._safe_write(self.output_metadata)

    def _update_output_metadata(self, processed_dict: dict):
        """Function that updates the output_metadata instance variable.

        Args:
            processed_dict (dict): Dictionary containing the processed data of one or multiple steps
        """
        if processed_dict:
            self.output_metadata.update(self.meta_description)
            self.output_metadata["sensor"] = self.sensor_name
            self.output_metadata["id"] = self.config["id"]
            self.output_metadata["expected_steps"] = self.expected_steps
            self.output_metadata.setdefault("steps", {}).update(processed_dict)

    def _calc_expected_steps(self) -> int:
        """Function that calculates the expected steps.
        If it is not set in the config, then it will look for the expected steps of the source metadata files.

        Returns:
            int: Expected steps
        """
        if "expected_steps" in self.config.keys():
            return self.config["expected_steps"]
        else:
            return list(self.input_metadata.values())[0]["metadata"]["expected_steps"]

    def _create_output_folder(self):
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def _source_ids_found(self) -> bool:
        """Boolean function that checks if all source id metadata files are found."""
        return all(
            source_id in self.input_metadata.keys()
            for source_id in self.config["sources"]
        )

    def _finished_all_steps(self) -> bool:
        """Boolean function that checks if all expected steps are available."""
        processed_steps = sum(
            [
                1
                for step, step_dict in self.processed_steps.items()
                if step_dict["finished"]
            ]
        )
        return processed_steps == self.expected_steps

    def _get_unprocessed_step(self) -> Union[int, None]:
        """Function that returns a single unprocessed step.

        Returns:
            Union[int, None]: Returns the step number and the step dictionary if there is an unprocessed step.
            Otherwise it returns None.
        """
        if self.processed_steps:
            for step_num, step_dict in self.processed_steps.items():
                if not step_dict["finished"]:
                    return step_num, step_dict["sources"]
        return None, None

    def _find_metadata_yaml(self):
        """Function that finds the metadata.yaml files of the source metadata files."""
        for root, dirs, files in os.walk(self.config["parent_dir"]):
            files_filtered = [
                f for f in files if "metadata.yaml" in f and ".lock" not in f
            ]
            for file in files_filtered:
                metadata_file_path = os.path.join(root, file)
                metadata = self._safe_read(metadata_file_path)
                if metadata["id"] in self.config["sources"]:
                    self.input_metadata[metadata["id"]] = {
                        "metadata": metadata,
                        "path": metadata_file_path,
                    }
                    self._set_sensor_name()

    def _set_sensor_name(self):
        """Set the instance variable of the sensor name."""
        if not self.sensor_name:
            self.sensor_name = list(self.input_metadata.values())[0]["metadata"][
                "sensor"
            ]

    def _safe_write(self, metadata: dict):
        """Write a dictionary to a yaml file with locking in order to avoid corrupting the file.

        Args:
            metadata (dict): Dictionary to write

        Raises:
            TimeoutError: If the filelock could not be acquired within 5 seconds.
        """
        metadata_file_path = str(
            Path(self.output_folder) / f'{self.config["id"]}_metadata.yaml'
        )
        try:
            lock = FileLock(f"{metadata_file_path}.lock", timeout=5)
            with lock.acquire():
                with open(metadata_file_path, "w") as f:
                    yaml.dump(metadata, f)
        except Timeout:
            error_string = f"Could not acquire filelock for {metadata_file_path}"
            raise TimeoutError(error_string)

    def _safe_read(self, metadata_file_path: str):
        """Read a yaml file with locking in order to avoid corrupting the file.

        Args:
            metadata_file_path (str): Path to the metadata file

        Raises:
            TimeoutError: If the filelock could not be acquired within 5 seconds.
        """
        try:
            lock = FileLock(f"{metadata_file_path}.lock", timeout=5)
            with lock.acquire():
                with open(metadata_file_path, "r") as f:
                    metadata = yaml.safe_load(f)
            return metadata
        except Timeout:
            error_string = f"Could not acquire filelock for {metadata_file_path}"
            raise TimeoutError(error_string)

    def _update_processed_step_dict(self, step_id: int):
        """Functino that updates the processed_steps dict if a step is finished."""
        self.processed_steps[step_id]["finished"] = True

    def _get_dict_of_available_steps(self, available_steps: list) -> dict:
        """Function that returns the dictionary of available steps.

        Args:
            available_steps (list): List of available steps

        Returns:
            dict: Dictionary of available steps
        """
        available_steps_dict = {}
        steps_filtered = [
            s for s in available_steps if s not in self.processed_steps.keys()
        ]
        for step in steps_filtered:
            available_steps_dict[step] = {"sources": {}, "finished": False}
            for source_id, metadata_dict in self.input_metadata.items():
                available_steps_dict[step]["sources"][source_id] = metadata_dict[
                    "metadata"
                ]["steps"][step]
        return available_steps_dict

    def _intersection_of_available_steps(self) -> list:
        """Function that returns a list of steps that are available for all source metadata files.

        Returns:
            list: List of available steps
        """
        all_steps = [
            list(v["metadata"]["steps"].keys()) for v in self.input_metadata.values()
        ]
        available = [
            s for s in all_steps[0] if all([s in steps for steps in all_steps])
        ]
        return available

    def _update_metadata(self):
        """Function that reads and updates the metadata of the source metadata files."""
        for data_id, _ in self.input_metadata.items():
            self.input_metadata[data_id]["metadata"] = self._safe_read(
                self.input_metadata[data_id]["path"]
            )
        available_steps = self._intersection_of_available_steps()
        self.processed_steps.update(self._get_dict_of_available_steps(available_steps))
