import logging
import pickle
from abc import ABC, abstractmethod

import bpy
from syclops import utility


class SensorInterface(ABC):
    """Abstract class for sensors"""

    def __init__(self, config):
        self.config: dict = config
        self.objs: list[utility.ObjPointer] = []

        self.config = config
        if "outputs" in config:
            self.outputs: list[object] = utility.create_module_instances(
                config["outputs"],
            )
        self.setup_sensor()
        self.setup_tf()

    def write_config(self, objs):
        """Write custom attributes to python objects.

        Args:
            objs (bpy.obj): List of objects to write attributes to.
        """
        # Make objs a list if it is not already
        if not isinstance(objs, list):
            objs = [objs]
        for obj in objs:
            for attr, value in self.config.items():
                obj[attr] = value

    def setup_tf(self):
        """Check if plugin has a frame_id and if so, add relationship."""
        if "frame_id" in self.config:
            _parent_frame_id = bpy.data.objects[self.config["frame_id"]]
            for obj in self.objs:
                if obj.get().parent == None:
                    obj.get().parent = _parent_frame_id
            logging.info(
                "Adding %s to parent frame %s",
                self.config["name"],
                _parent_frame_id.name,
            )
        else:
            logging.error("No frame_id specified for %s", self.config["name"])

    @abstractmethod
    def setup_sensor(self):
        """Setup the sensor"""
        pass

    @abstractmethod
    def render_outputs(self):
        """Render all outputs"""
        pass