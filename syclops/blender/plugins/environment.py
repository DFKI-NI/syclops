import logging

import bpy
import numpy as np
from syclops import utility
from syclops.blender.plugins.plugin_interface import PluginInterface


class Environment(PluginInterface):
    """Plugin responsible for setting up the environment of the blender scene.

    This includes the sky, sun, and lighting.
    """

    def load(self):
        """Create the environment shader."""
        if self.config["type"] == "hdri":
            world_name = "hdri"
        elif self.config["type"] == "hdri_and_sun":
            world_name = "hdri_and_sun"

        # Load world shader
        blend_path = utility.abs_path("./plugin_data/environment.blend")
        utility.load_from_blend(
            blend_path,
            "worlds",
            world_name,
        )
        bpy.context.scene.world = bpy.data.worlds[world_name]

        logging.info("Environment loaded")

    def configure(self):
        """Configure the environment shader for the current frame."""
        if self.config["type"] == "hdri_and_sun":
            self._configure_hdri_and_sun()
        self._load_and_set_env_texture()
        if "random_rotation" in self.config:
            bpy.context.scene.world.node_tree.nodes["rotation_multiplier"].inputs[
                1
            ].default_value = (self.config["random_rotation"] * 1000)
        if "strength" in self.config:
            self._set_strength()
        logging.info("Environment configured")

    def _configure_hdri_and_sun(self):
        """Configure HDRI and sun settings."""
        hdri_sun = bpy.data.worlds["hdri_and_sun"]
        sky_texture = hdri_sun.node_tree.nodes["Sky Texture"]
        sky_texture.sun_elevation = np.deg2rad(
            utility.eval_param(self.config["sun_elevation"]),
        )
        sky_texture.sun_rotation = np.deg2rad(
            utility.eval_param(self.config["sun_rotation"]),
        )

    def _load_and_set_env_texture(self):
        """Load and sets the environment texture."""
        env_texture = utility.eval_param(self.config["environment_image"])
        root_path, env_texture_path = utility.get_asset_path(env_texture)
        img = utility.load_image(root_path / env_texture_path)
        world = bpy.context.scene.world
        world.node_tree.nodes["Environment Texture"].image = img

    def _set_strength(self):
        """Set the strength for the environment shader."""
        world_node_tree = bpy.context.scene.world.node_tree
        strength_input = world_node_tree.nodes["Background"].inputs[1]
        strength_input.default_value = utility.eval_param(self.config["strength"])
