import time
from abc import abstractmethod
from pathlib import Path

from syclops.postprocessing.postprocessor_base import PostprocessorBase


class PostprocessorInterface(PostprocessorBase):
    meta_description: dict = {}

    def __init__(self, config: dict, polling_delay: float = 0.1):
        super().__init__(config)
        self.polling_delay = polling_delay

    # LIFECYCLE

    def run(self):
        """Main function that does the following:
        1. Searches until all needed source metadata.yaml files are found.
        2. Processes individual steps/frames once they become available.
        3. When all steps are available, the process_all_steps function is called.
        """
        while not self._source_ids_found():
            self._find_metadata_yaml()
            time.sleep(self.polling_delay)
        self._setup(self._output_folder_path())
        self._prepare()
        while not self._finished_all_steps():
            self._update_metadata()
            step_num, step_dict = self._get_unprocessed_step()
            if step_num is not None:
                processed_dict = self.process_step(step_num, step_dict)
                self._write_output_metadata(processed_dict)
                self._update_processed_step_dict(step_num)
            else:
                time.sleep(self.polling_delay)
        processed_dict = self.process_all_steps()
        self._write_output_metadata(processed_dict)

    # INTERFACE

    @abstractmethod
    def process_step(self, step_num: int, step_dict: dict) -> dict:
        """Processing function that is called when a new step is available.

        Args:
            step_num (int): Step number of the current step
            step_dict (dict): Dictionary containing the data of the current step
                            It has the following structure:
                            {<source_id_1>: [
                                {'path': <path_to_source_file_1>, 'type': <type_of_source_file_1>},
                                {'path': <path_to_source_file_2>...}
                            ],
                            <source_id_2>: [...]
                            }

        Returns:
            dict: Dictionary containing the processed data of the current step
                It has the following structure:
                {<step_num>: [
                    {'path': <path_to_ouput_file_1>, 'type': <type_of_ouput_file_1>},
                    {'path': <path_to_ouput_file_2>...}
                ]}
        """
        pass

    @abstractmethod
    def process_all_steps(self) -> dict:
        """Processing function that is called when all source steps are available.
        Usefull for postprocessors that need to wait for all steps to be available before processing.

        Returns:
        dict: Dictionary containing the processed data of the current step
            It has the following structure:
            {<step_num>: [
                {'path': <path_to_ouput_file_1>, 'type': <type_of_ouput_file_1>},
                {'path': <path_to_ouput_file_2>...}
            ],
            <step_num>: [...]}

        """
        pass

    @abstractmethod
    def _output_folder_path(self) -> str:
        """Function that returns the path to the output folder.

        Returns:
            str: Path to the output folder
        """
        raise NotImplementedError

    def _prepare(self):
        """Function that can be overwritten to perform initializations that require metadata
        this is called within the same thread as the run method (in contrast to constructor)
        """
        pass

    # CONVENIENCE METHODS

    def get_base_paths_by_type(self):
        """
        @param step_type (str): Type of step
        @return: path
        """
        paths = {
            m["metadata"]["type"]: Path(m["path"]).parent
            for m in self.input_metadata.values()
        }
        return paths

    def get_full_paths_from_step_dict(self, step_dict: dict):
        base_paths = self.get_base_paths_by_type()
        paths_all = {}
        for step in step_dict.values():
            paths = {x["type"]: str(base_paths[x["type"]] / x["path"]) for x in step}
            for step_type, path in paths.items():
                if step_type in paths_all:
                    paths_all[step_type].extend(path)
                else:
                    paths_all[step_type] = [path]
        return paths_all
