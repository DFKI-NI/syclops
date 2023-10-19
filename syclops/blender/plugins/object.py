import logging

import bpy
from syclops import utility
from syclops.blender.plugins.plugin_interface import PluginInterface


class Object(PluginInterface):
    """Plugin that places individual objects into the scene."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.objs = []

    def load(self):
        """Add objects to blender and load into scene."""
        self._set_active_collection()
        self._import_and_process_objects()
        if self.config.get("place_on_ground", False):
            self.align_objects_to_ground()
        self.setup_tf()
        logging.info("Object: %s loaded", self.config["name"])

    def configure(self):
        """Configure settings for current frame."""
        logging.info("Object: %s configured", self.config["name"])
        self._add_volume_attribute_to_objects()

    def _set_active_collection(self):
        """Set the active collection based on config name."""
        collection = utility.create_collection(self.config["name"])
        utility.set_active_collection(collection)

    def _import_and_process_objects(self):
        """Import and process objects as per the configuration."""
        objs = utility.import_assets(self.config["models"])
        for obj in objs:
            self.reduce_size(obj)
            self.write_config(obj)
            self.objs.append(utility.ObjPointer(obj))

    def _add_volume_attribute_to_objects(self):
        """Add volume attribute to each object in the list."""
        for obj in self.objs:
            utility.add_volume_attribute(obj.get())

    def align_objects_to_ground(self):
        """Place objects to z-height of ground and align to ground normal."""
        self._deselect_all_objects()
        ground = self._get_ground_object()
        foot = self._create_primitive_circle()
        self._parent_objects_to_circle(foot)
        self._apply_shrinkwrap_to_foot(foot, ground)
        self.objs.append(utility.ObjPointer(foot))

    @staticmethod
    def _deselect_all_objects():
        bpy.ops.object.select_all(action="DESELECT")

    def _get_ground_object(self):
        floor_object = self.config["floor_object"]
        return utility.filter_objects("name", floor_object)[0]

    @staticmethod
    def _create_primitive_circle():
        bpy.ops.mesh.primitive_circle_add(vertices=8)
        return bpy.context.object

    def _parent_objects_to_circle(self, foot):
        for obj in self.objs:
            if obj.get().parent is None:
                obj.get().select_set(True)
        bpy.context.view_layer.objects.active = foot
        bpy.ops.object.parent_set(type="VERTEX_TRI")

    @staticmethod
    def _apply_shrinkwrap_to_foot(foot, ground):
        shrink_wrap = foot.modifiers.new(name="SW", type="SHRINKWRAP")
        shrink_wrap.target = ground
        shrink_wrap.wrap_method = "PROJECT"
        shrink_wrap.use_positive_direction = True
        shrink_wrap.use_negative_direction = True
        shrink_wrap.use_project_z = True
