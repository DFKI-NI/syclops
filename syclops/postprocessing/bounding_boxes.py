import os
from pathlib import Path
from typing import Union

import numpy as np
from syclops.postprocessing.postprocessor_interface import \
    PostprocessorInterface


class BoundingBoxes(PostprocessorInterface):
    meta_description = {
        "type": "BOUNDING_BOX",
        "format": "YOLO",
        "description": "Bounding boxes with their respective class id of the current image.",
    }

    def __init__(self, config):
        super().__init__(config)

    def process_step(self, step_num: int, step_dict: dict) -> dict:
        segmentation_image, instance_image = self._load_images(step_dict)

        # Get classes to skip
        classes_to_skip = self._get_classes_to_skip()

        # Create mask of segmentation image with classes to skip
        mask = np.zeros(segmentation_image.shape)
        for class_id in classes_to_skip:
            mask += segmentation_image == class_id

        # Get unique instance ids from masked instance image
        unique_instance_ids = np.unique(instance_image[mask == 0])

        output_file_name = format(step_num, "04d") + ".txt"
        output_file = open(
            Path(self.output_folder) / output_file_name, "w", encoding="utf-8"
        )
        # Loop over all unique instance ids
        for instance_id in unique_instance_ids:
            num_pixels = np.sum(instance_image == instance_id)
            class_ids, count = np.unique(
                segmentation_image[instance_image == instance_id], return_counts=True
            )

            # Remove class_ids with count less than 1% of total pixels
            class_ids = class_ids[count > num_pixels * 0.01]
            count = count[count > num_pixels * 0.01]
            # Remove class_ids with count less than 5 pixels
            class_ids = class_ids[count > 5]
            count = count[count > 5]

            if (
                "multiple_bb_per_instance" in self.config
                and self.config["multiple_bb_per_instance"]
            ):
                for class_id, count in zip(class_ids, count):
                    # Get indices of pixels with instance id and class id
                    instance_idx = np.where(
                        (instance_image == instance_id)
                        & (segmentation_image == class_id)
                    )

                    if class_id in classes_to_skip:
                        continue
                    # Bounding box
                    self.write_bb(
                        segmentation_image, class_id, output_file, instance_idx
                    )

            else:
                try:
                    # Get lowest class id (first class id is main class id)
                    class_id = np.min(class_ids)
                    # Get mask of pixels with instance id and one of the class ids
                    instance_idx = np.where(
                        (instance_image == instance_id)
                        & np.isin(segmentation_image, class_ids)
                    )
                    # Bounding box
                    self.write_bb(
                        segmentation_image, class_id, output_file, instance_idx
                    )
                except ValueError:
                    pass
        # Close file
        output_file.close()

        output_step_dict = {
            step_num: [{"type": "BOUNDING_BOX", "path": output_file_name}]
        }
        return output_step_dict

    def write_bb(self, segmentation_image, class_id, output_file, instance_idx):
        try:
            x = np.min(instance_idx[1])
            y = np.min(instance_idx[0])
            w = np.max(instance_idx[1]) - x
            h = np.max(instance_idx[0]) - y

            # Write to file
            output_string = self._convert_to_output_format(
                x, y, w, h, segmentation_image, class_id
            )
            output_file.write(output_string)
            output_file.write("\n")
        except ValueError:
            pass

    def process_all_steps(self) -> dict:
        pass

    def update_output_dict(self, output_dict: dict):
        output_dict["bounding_box"] = self._output_folder_path()
        return output_dict

    def _output_folder_path(self):
        return str(
            Path(self.config["parent_dir"])
            / f"{self.sensor_name}_annotations"
            / "bounding_box"
        )

    def _get_classes_to_skip(self):
        return self._make_list(self.config["classes_to_skip"])

    def _make_list(self, input_list: Union[list, int, float, str]):
        if not isinstance(input_list, list):
            input_list = [input_list]
        return input_list

    def _load_images(self, step_dict: dict):
        paths = self.get_full_paths_from_step_dict(step_dict)
        instance_path = paths["INSTANCE_SEGMENTATION"][0]
        semantic_path = paths["SEMANTIC_SEGMENTATION"][0]

        if os.path.isfile(semantic_path) and os.path.isfile(instance_path):
            segmentation_image = np.load(semantic_path)["array"]
            instance_image = np.load(instance_path)["array"]
        else:
            raise FileNotFoundError("Semantic or instance segmentation image not found")
        return segmentation_image, instance_image

    def _convert_to_output_format(self, x, y, w, h, img, class_id):
        """Convert bounding box location to output string

        Args:
            x (float): top left pixel location of bounding box in x direction
            y (float): top left pixel location of bounding box in y direction
            w (float): width of bounding box
            h (float): height of bounding box
            img (float): instance mask of bounding box
            class_id (float): class id of bounding box

        Returns:
            string: bounding box in output format
        """
        img_width = img.shape[1]
        img_height = img.shape[0]

        x_center = x + w / 2
        y_center = y + h / 2
        x_center = x_center / img_width
        y_center = y_center / img_height
        w = w / img_width
        h = h / img_height
        return f"{int(class_id)} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}"
