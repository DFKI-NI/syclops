"""Define the Scene class to setup virtual environment for rendering."""

import logging
import pickle
from pathlib import Path

import bpy
from rich.logging import RichHandler
from syclops import utility
from syclops.blender.transformations import Transformations
from ruamel import yaml

SEPARATOR = "#"
SEPARATOR_LENGTH = 40


class Scene(object):
    """Represent the scene configuration and rendering capabilities."""

    def __init__(self, catalog: dict, job_description: dict) -> None:
        """
        Initialize and set up the virtual environment for rendering.

        Args:
            catalog: Information about the catalog.
            job_description: Information about the job description.
        """
        utility.clear_scene()

        self.job_description = job_description
        self.catalog = catalog

        # Write dicts to scene as string of bytes
        catalog_bytes = str(pickle.dumps(catalog), encoding="latin1")
        bpy.data.scenes["Scene"]["catalog"] = catalog_bytes

        job_bytes = str(
            pickle.dumps(job_description),
            encoding="latin1",
        )
        bpy.data.scenes["Scene"]["job_description"] = job_bytes

        self.output_path = Path(bpy.context.scene.render.filepath)
        self.configure_logging()
        utility.set_seeds(job_description["seeds"])

        # Write class_id_mapping to file
        class_id_mapping = utility.find_class_id_mapping(job_description)
        class_id_mapping_path = self.output_path / "class_id_mapping.yaml"
        with open(class_id_mapping_path, "w") as file:
            yaml.dump(class_id_mapping, file)

        self.tf_tree = Transformations()
        self.tf_tree.create_tf_tree(job_description["transformations"])

        self.plugin_instances = utility.create_module_instances(
            job_description["scene"],
        )
        self.sensor_instances = utility.create_module_instances(
            job_description["sensor"],
        )

    def render(self) -> None:
        """Generate sensor outputs and render them."""
        logging.info(
            "{0}RENDERING{1}".format(
                SEPARATOR * SEPARATOR_LENGTH,
                SEPARATOR * SEPARATOR_LENGTH,
            ),
        )
        for step in range(self.job_description["steps"]):
            logging.info("Step: {0}".format(step))
            bpy.context.scene.frame_set(step)
            self.tf_tree.configure_tf_tree()

            for plugin_instance in self.plugin_instances:
                plugin_instance.configure()
            for sensor_instance in self.sensor_instances:
                with utility.RevertAfter():
                    sensor_instance.render_outputs()

    def configure_logging(self) -> None:
        """Set up logging to a file and to the console."""
        logging_path = self.output_path / "logs.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)-15s %(levelname)8s %(name)s %(message)s",
            filename=str(logging_path),
        )
        logging.getLogger().addHandler(RichHandler())
        logging.info(
            "{0}SCENE CONFIGURATION{1}".format(
                SEPARATOR * SEPARATOR_LENGTH,
                SEPARATOR * SEPARATOR_LENGTH,
            ),
        )
