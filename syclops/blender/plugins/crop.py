"""This module contains the Crop plugin for Syclops.

It is used to place objects in a row like fashion to simulate crop.
"""

import logging

import bpy
from syclops import utility
from syclops.blender.plugins.plugin_interface import PluginInterface


class Crop(PluginInterface):
    """Plugin scatters objects in a row like fashion to simulate crop."""

    crop: utility.ObjPointer

    def load(self):
        """Load everything into the scene but does not configure it."""
        self.create_base_object()
        self.load_instance_objects()
        self.load_geometry_nodes()
        logging.info("Crop: {0} loaded".format(self.config["name"]))

    def load_geometry_nodes(self):
        """Load geometry nodes from .blend file and assigns them to the crop."""
        # Add crop node group to the scene
        node_group_name = "Crop"
        blend_path = utility.abs_path("./plugin_data/crop.blend")

        crop_nodes = utility.load_from_blend(
            blend_path,
            "node_groups",
            node_group_name,
        )[0]

        # Create GeoNode Modifier
        self.geo_node_modifier = self.crop.get().modifiers.new(
            self.config["name"],
            "NODES",
        )
        self.geo_node_modifier.show_viewport = False
        self.geo_node_modifier.node_group = crop_nodes

    def load_instance_objects(self):
        """Load crop geometry."""
        # Create new collection and assign a pointer
        self.instance_objects = utility.ObjPointer(
            utility.create_collection("{0}_Objs".format(self.config["name"])),
        )
        utility.set_active_collection(self.instance_objects.get())

        # Import the geometry
        loaded_objs = utility.import_assets(self.config["models"])
        for obj in loaded_objs:
            self.reduce_size(obj)
            obj.hide_set(True)
            self.write_config(obj)
        self.instance_objects.get().hide_render = True

    def create_base_object(self):
        """Add placeholder object to assign GeoNode Modifier to."""
        # Setup a blender collection
        collection = utility.create_collection(self.config["name"])
        utility.set_active_collection(collection)

        # Setup GeoNodes
        bpy.ops.mesh.primitive_plane_add()
        bpy.context.active_object.name = self.config["name"]
        self.crop = utility.ObjPointer(bpy.context.active_object)

    def configure(self):
        """Apply configuration for current frame."""
        # Refresh References
        self.geo_node_modifier = self.crop.get().modifiers[self.config["name"]]
        # Configure settings from config
        self.configure_settings()
        for obj in self.instance_objects.get().objects:
            utility.add_volume_attribute(obj)
        logging.info("Crop: {0} configured".format(self.config["name"]))
