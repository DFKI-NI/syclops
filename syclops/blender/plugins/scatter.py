import logging

import bpy
from syclops import utility
from syclops.blender.plugins.plugin_interface import PluginInterface


class Scatter(PluginInterface):
    """Plugin for scattering objects inside a Blender scene."""

    def __init__(self, config: dict):
        self.scatter: utility.ObjPointer = None
        super().__init__(config)

    def load(self):
        """Setup nodes and load geometry into blender."""
        self._set_active_collection()
        self._setup_geo_nodes()
        self._import_models_and_clumps()
        self._append_node_group()
        logging.info("Scatter: %s loaded", self.config["name"])

    def configure(self):
        """Set settings for current frame."""
        self._refresh_references()
        self.configure_settings()
        self._add_volume_attribute_to_objects()
        logging.info("Scatter: %s configured", self.config["name"])

    def _set_active_collection(self):
        """Set the active collection based on config name."""
        collection = utility.create_collection(self.config["name"])
        utility.set_active_collection(collection)

    def _setup_geo_nodes(self):
        """Setup GeoNodes."""
        bpy.ops.mesh.primitive_plane_add()
        bpy.context.active_object.name = self.config["name"]
        self.scatter = utility.ObjPointer(bpy.context.active_object)

    def _import_models_and_clumps(self):
        """Import models and clumps if available."""
        self.instance_objects = utility.ObjPointer(
            utility.create_collection(self.config["name"] + "_Objs"),
        )
        utility.set_active_collection(self.instance_objects.get())

        loaded_objs = utility.import_assets(self.config["models"])
        for obj in loaded_objs:
            self._process_loaded_object(obj)

        if "clumps" in self.config:
            self._process_clumps()

        self.instance_objects.get().hide_render = True

    def _process_loaded_object(self, obj):
        """Process each loaded object."""
        self.reduce_size(obj)
        obj.hide_set(True)
        self.write_config(obj)

    def _process_clumps(self):
        """Create and process clumps based on config."""
        clump_objs = utility.create_clumps(
            self.instance_objects.get(), self.config["clumps"]
        )
        for clump_obj in clump_objs:
            self.write_config(clump_obj)
        logging.info(
            f"Scatter: Created {len(clump_objs)} clumps for {self.config['name']}"
        )

    def _append_node_group(self):
        """Append node group from blend file."""
        node_group_name = "Scatter"
        blend_path = utility.abs_path("./plugin_data/scatter.blend")
        scatter_nodes = utility.load_from_blend(
            blend_path,
            "node_groups",
            node_group_name,
        )[0]

        self.geo_node_modifier = self.scatter.get().modifiers.new(
            self.config["name"], "NODES"
        )
        self.geo_node_modifier.node_group = scatter_nodes

    def _refresh_references(self):
        """Refresh references to the geo node modifier."""
        self.geo_node_modifier = self.scatter.get().modifiers[self.config["name"]]

    def _add_volume_attribute_to_objects(self):
        """Add volume attribute to each object in the instance."""
        for obj in self.instance_objects.get().objects:
            utility.add_volume_attribute(obj)
