import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Union

import bpy
from syclops import utility


class PluginInterface(ABC):
    """Interface class for scene generation plugins."""

    def __init__(self, config: dict):
        self.config: dict = config
        self.objs: List[utility.ObjPointer] = []
        self.geo_node_modifier: bpy.types.Modifier = None
        self.instance_objects: utility.ObjPointer = None
        self.config["plugin_type"] = self.__class__.__name__

        self.load()

    def write_config(self, objs: Union[List[bpy.types.Object], bpy.types.Object]):
        """Write custom attributes to python objects."""
        objs = [objs] if not isinstance(objs, list) else objs

        for obj in objs:
            for attr, value in self.config.items():
                obj[attr] = value

    def configure_settings(self):
        """Set config settings on the geo_node_modifier."""
        if self.geo_node_modifier:
            input_dict = self.extract_input_mapping()
            for key in self.config.keys():
                self._apply_config_based_on_input_type(key, input_dict)

            self._configure_ground(input_dict)
            self._configure_instance(input_dict)
            self._configure_uvmap(input_dict)

    def extract_input_mapping(self) -> Dict[str, Dict]:
        """Extract input mapping from geo_node_modifier."""
        return {
            input.name: {"socket": input.identifier, "type": input.type}
            for input in self.geo_node_modifier.node_group.inputs
        }

    def setup_tf(self):
        """Check if plugin has a frame_id and if so, add relationship."""
        frame_id = self.config.get("frame_id")
        if frame_id:
            _parent_frame_id = bpy.data.objects[frame_id]
            for obj in self.objs:
                if obj.get().parent is None:
                    obj.get().parent = _parent_frame_id
            logging.info(
                f"Adding {self.config['name']} to parent frame {_parent_frame_id.name}"
            )
        else:
            logging.error(f"No frame_id specified for {self.config['name']}")

    def reduce_size(self, obj: bpy.types.Object):
        """Reduce texture and mesh size of object if specified."""
        max_texture_size = self.config.get("max_texture_size")
        decimate_mesh_factor = self.config.get("decimate_mesh_factor")

        if max_texture_size:
            utility.resize_textures(obj, max_texture_size)
            logging.info(f"Resized textures on {obj.name}")

        if decimate_mesh_factor:
            utility.decimate_mesh(obj, decimate_mesh_factor)

    @abstractmethod
    def load(self):
        """Load into scene."""
        logging.error(f"Class: {self.__class__.__name__} does not implement load()")

    @abstractmethod
    def configure(self):
        """Configure created objects."""
        logging.error(
            f"Class: {self.__class__.__name__} does not implement configure()"
        )

    def _apply_config_based_on_input_type(self, key: str, input_dict: Dict):
        # This method applies config based on the input type.
        try:
            input_type = input_dict[key]["type"]
            socket = input_dict[key]["socket"]
            config_value = self.config[key]
            evaluated_param = utility.eval_param(config_value)

            if input_type == "VALUE":
                self.geo_node_modifier[socket] = float(evaluated_param)
            elif input_type == "INT":
                self.geo_node_modifier[socket] = int(evaluated_param)
            elif input_type == "IMAGE":
                self._handle_image_input(socket, evaluated_param, key)
            elif input_type == "BOOLEAN":
                self.geo_node_modifier[socket] = bool(evaluated_param)

        except KeyError:
            pass

    def _handle_image_input(self, socket: str, evaluated_asset: str, key: str):
        # This method specifically handles the IMAGE type configuration.
        root_path, image_path = utility.get_asset_path(evaluated_asset)
        image_texture_name = f"{self.config['name']}_{key}"
        image_texture = bpy.data.textures.new(image_texture_name, type="IMAGE")

        frame = bpy.context.scene.frame_current
        if isinstance(image_path, list):
            image_path = image_path[frame % len(image_path)]

        image_texture.image = utility.load_image(str(root_path / image_path))
        image_texture.extension = "EXTEND"
        image_texture.image.colorspace_settings.name = "Linear"
        self.geo_node_modifier[socket] = image_texture.image

    def _configure_ground(self, input_dict: Dict):
        # Configure ground objects.
        if "Ground" in input_dict:
            floor_object = self.config["floor_object"]
            ground = utility.filter_objects("name", floor_object)[0]
            self.geo_node_modifier[input_dict["Ground"]["socket"]] = ground

    def _configure_instance(self, input_dict: Dict):
        # Configure instance objects.
        if "Instance Objects" in input_dict and self.instance_objects:
            self.geo_node_modifier[
                input_dict["Instance Objects"]["socket"]
            ] = self.instance_objects.get()

    def _configure_uvmap(self, input_dict: Dict):
        if "UVMap" in input_dict.keys():
            # Configure UVMap input
            self.geo_node_modifier[
                input_dict["UVMap"]["socket"] + "_use_attribute"
            ] = True
            self.geo_node_modifier[
                input_dict["UVMap"]["socket"] + "_attribute_name"
            ] = "UVMap"
