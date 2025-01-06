import logging
from pathlib import Path

import bpy
import numpy as np
from syclops import utility
from syclops.blender.plugins.plugin_interface import PluginInterface



class Ground(PluginInterface):
    """Plugin to create a ground mesh in the blender scene"""

    def __init__(self, config):
        self.ground: utility.ObjPointer = None
        super().__init__(config)

    def load(self):
        """Create the ground mesh"""
        # Create collection for the ground
        collection = utility.create_collection(self.config["name"])
        utility.set_active_collection(collection)

        if "object_path" in self.config:
            self.objs = utility.import_objects(
                utility.abs_path(self.config["object_path"]),
            )
            for obj in self.objs:
                self.write_config(obj)

        else:
            self.ground = utility.ObjPointer(self._setup_ground_geometry())
            self.configure_settings()
            self._setup_modifiers(self.ground.get())

        logging.info("Ground: %s loaded", self.config["name"])

    def _setup_modifiers(self, ground):
        """Add modifiers to the ground object."""
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = ground
        ground.select_set(True)

        # Apply modifiers
        for modifier in ground.modifiers:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.object.select_all(action="DESELECT")

        # Enable adaptive subdivision for modifiers
        bpy.context.scene.cycles.feature_set = "EXPERIMENTAL"

        # Add Subsurf modifier
        ground.active_material.cycles.displacement_method = "DISPLACEMENT"
        bpy.ops.object.modifier_add(type="SUBSURF")
        bpy.context.object.modifiers["Subdivision"].subdivision_type = "SIMPLE"
        bpy.context.object.modifiers["Subdivision"].levels = 2
        bpy.context.object.cycles.use_adaptive_subdivision = True
        bpy.context.object.cycles.dicing_rate = 1.0

    def _setup_ground_material(self):
        """Configure the ground material."""
        nodes = self.ground.get().active_material.node_tree.nodes
        texture = utility.get_asset(utility.eval_param(self.config["texture"]))
        root_path = Path(
            utility.get_lib_path(utility.eval_param(self.config["texture"]))
        )

        # Configure nodes and textures
        self._configure_node_mappings(nodes, texture["texture_size"])
        self._import_and_set_images(nodes, root_path, texture)
        self._set_voronoi_scale(nodes)
        self._set_displacement_params(nodes, texture)

    def _configure_node_mappings(self, nodes, texture_size):
        scale = self.config["size"] / texture_size
        for node_name in ["Mapping", "Mapping.001"]:
            nodes.get(node_name).inputs["Scale"].default_value = [scale] * 3

    def _import_and_set_images(self, nodes, root_path, texture):
        texture_map = {
            "base_color_1": texture["diffuse_filepath"],
            "roughness_1": texture["roughness_filepath"],
            "normal_1": texture["normal_filepath"],
            "displacement_1": texture["displacement_filepath"],
        }

        for key, value in texture_map.items():
            image = utility.load_image(root_path / value)
            nodes.get(key).image = image
            if key != "base_color_1":
                image.colorspace_settings.name = "Non-Color"

        # Set texture for second set of nodes
        nodes["base_color_2"].image = nodes["base_color_1"].image
        nodes["roughness_2"].image = nodes["roughness_1"].image
        nodes["normal_2"].image = nodes["normal_1"].image
        nodes["displacement_2"].image = nodes["displacement_1"].image

    def _set_voronoi_scale(self, nodes):
        scale_value = 2 * self.config["size"]
        for node_name in ["Voronoi Texture", "Voronoi Texture.001"]:
            nodes.get(node_name).inputs["Scale"].default_value = scale_value

    def _set_displacement_params(self, nodes, texture):
        if "texture_displacement_scale" in texture:
            nodes.get("Displacement").inputs["Scale"].default_value = float(
                texture["texture_displacement_scale"]
            )
        if "texture_displacement_midlevel" in texture:
            nodes.get("Displacement").inputs["Midlevel"].default_value = float(
                texture["texture_displacement_midlevel"]
            )


    def _setup_ground_geometry(self):
        """Create a plane, scale and subdivide according to the ground size."""
        # Import Ground Object
        ground_path = utility.abs_path("./plugin_data/ground.blend")
        ground = utility.import_objects(ground_path)[0]

        self.write_config(ground)

        # Scale Ground object and apply scale
        ground.scale = (self.config["size"], self.config["size"], 0)
        mb = ground.matrix_basis
        if hasattr(ground.data, "transform"):
            ground.data.transform(mb)
        for c in ground.children:
            c.matrix_local = mb @ c.matrix_local
        ground.matrix_basis.identity()

        # Add Subdivisions
        num_subdivisions = np.ceil(np.log2(self.config["size"]) - np.log2(2)) + 2
        ground.modifiers["Subdivision"].subdivision_type = "SIMPLE"
        ground.modifiers["Subdivision"].levels = int(num_subdivisions)
        ground.modifiers["Subdivision"].render_levels = int(num_subdivisions)

        self.geo_node_modifier = ground.modifiers["GeometryNodes"]
        return ground

    def configure(self):
        """Configure the ground object."""
        if "object_path" not in self.config:
            self._setup_ground_material()
