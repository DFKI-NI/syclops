import logging

import bpy
from syclops import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface

# META DESCRIPTION
meta_description = {
    "type": "STRUCTURED_LIGHT",
    "format": "PNG",
    "description": "Color images with structured light patterns from the camera",
}


class StructuredLight(OutputInterface):
    """Generate structured light images"""

    def generate_output(self, parent_class: object = None):
        with utility.RevertAfter():
            utility.configure_render()

            job_description = utility.get_job_conf()
            bpy.context.scene.cycles.use_denoising = job_description[
                "denoising_enabled"
            ]
            try:
                bpy.context.scene.cycles.denoiser = job_description[
                    "denoising_algorithm"
                ]
            except TypeError as e:
                logging.error(
                    f"Could not set denoiser to {job_description['denoising_algorithm']}. Try 'OPENIMAGEDENOISE'."
                )
                raise e
            bpy.context.scene.cycles.samples = self.config["samples"]

            if "image_compression" in job_description:
                bpy.data.scenes["Scene"].render.image_settings.compression = (
                    job_description["image_compression"]
                )

            bpy.context.scene.render.image_settings.color_mode = "RGB"

            # Get the camera
            cam_name = bpy.context.scene.camera["name"]
            # Create subfolders
            output_path = self._prepare_output_folder(cam_name)
            # Set filename
            curr_frame = bpy.context.scene.frame_current

            file_string = str(curr_frame).rjust(4, "0") + ".png"
            output_path = utility.append_output_path(output_path)
            utility.append_output_path(file_string)
            self.compositor()

            # Turn off all lights
            self.turn_off_all_lights()
            # Add a spotlight with nodes
            self.add_spotlight_with_nodes()

            self.check_debug_breakpoint()
            logging.info(f"Rendering Structured Light for sensor {cam_name}")
            bpy.ops.render.render(write_still=True)

            with utility.AtomicYAMLWriter(str(output_path / "metadata.yaml")) as writer:
                # Add metadata
                writer.data.update(meta_description)
                # Add current step
                writer.add_step(
                    step=curr_frame,
                    step_dicts=[{"type": "STRUCTURED_LIGHT", "path": str(file_string)}],
                )
                # Add expected steps
                writer.data["expected_steps"] = job_description["steps"]
                writer.data["sensor"] = cam_name
                writer.data["id"] = self.config["id"]
            logging.info("Structured Light output for sensor %s", cam_name)

    def turn_off_all_lights(self):
        # Turn off all lamps
        for light in bpy.data.lights:
            light.energy = 0

        # Turn off all emission nodes in all materials
        for material in bpy.data.materials:
            if material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == "EMISSION":
                        node.inputs["Strength"].default_value = 0

        # Set the lighting strength of the environment to 0
        if bpy.context.scene.world:
            bpy.context.scene.world.node_tree.nodes["Background"].inputs[
                "Strength"
            ].default_value = 0

    def add_spotlight_with_nodes(self):
        """Add a spotlight with nodes, that will generate a random dot pattern"""

        collection = utility.create_collection(self.config["id"])
        utility.set_active_collection(collection)
        # Create a new spotlight
        bpy.ops.object.light_add(type="SPOT")
        spotlight = bpy.context.object
        spotlight.data.energy = self.config["intensity"]
        spotlight.data.spot_size = 3.14159  # Set cone angle to 180 degrees (in radians)

        # Setting frame_id as parent
        frame_id = self.config["frame_id"]
        parent_frame_id = bpy.data.objects[frame_id]
        spotlight.parent = parent_frame_id

        # Enable use_nodes for this spotlight
        spotlight.data.use_nodes = True
        nodes = spotlight.data.node_tree.nodes

        # Clear existing nodes
        for node in nodes:
            nodes.remove(node)

        # Create the required nodes and recreate the structure
        texture_coordinate_node = nodes.new("ShaderNodeTexCoord")
        separate_xyz_node = nodes.new("ShaderNodeSeparateXYZ")
        divide_node = nodes.new("ShaderNodeVectorMath")
        divide_node.operation = "DIVIDE"
        mapping_node = nodes.new("ShaderNodeMapping")
        voronoi_texture_node = nodes.new("ShaderNodeTexVoronoi")
        voronoi_texture_node.feature = "F1"
        voronoi_texture_node.distance = "EUCLIDEAN"
        voronoi_texture_node.voronoi_dimensions = "2D"
        color_ramp_node = nodes.new("ShaderNodeValToRGB")
        color_ramp_node.color_ramp.interpolation = "EASE"
        emission_node = nodes.new("ShaderNodeEmission")
        light_output_node = nodes.new("ShaderNodeOutputLight")

        # Link nodes together as per the provided structure
        links = spotlight.data.node_tree.links
        links.new(
            texture_coordinate_node.outputs["Normal"],
            separate_xyz_node.inputs["Vector"],
        )
        links.new(texture_coordinate_node.outputs["Normal"], divide_node.inputs[0])
        links.new(separate_xyz_node.outputs["Z"], divide_node.inputs[1])
        links.new(divide_node.outputs[0], mapping_node.inputs["Vector"])
        links.new(mapping_node.outputs["Vector"], voronoi_texture_node.inputs["Vector"])
        links.new(
            voronoi_texture_node.outputs["Distance"], color_ramp_node.inputs["Fac"]
        )
        links.new(color_ramp_node.outputs["Color"], emission_node.inputs["Strength"])
        links.new(
            emission_node.outputs["Emission"], light_output_node.inputs["Surface"]
        )

        # Set specific values for nodes based on the image
        voronoi_texture_node.inputs["Scale"].default_value = self.config["scale"]
        voronoi_texture_node.inputs["Randomness"].default_value = 1.0
        color_ramp_node.color_ramp.elements[1].position = 0.3
        color_ramp_node.color_ramp.elements[1].color = (0, 0, 0, 1)
        color_ramp_node.color_ramp.elements[0].color = (1, 1, 1, 1)

    def compositor(self):
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree

        # Clear existing nodes
        for node in tree.nodes:
            tree.nodes.remove(node)

        # Create input node
        render_layers_node = tree.nodes.new(type="CompositorNodeRLayers")

        # Create RGB to BW node
        rgb_to_bw_node = tree.nodes.new(type="CompositorNodeRGBToBW")

        # Create output node
        composite_node = tree.nodes.new(type="CompositorNodeComposite")

        # Link nodes
        links = tree.links
        link = links.new(render_layers_node.outputs["Image"], rgb_to_bw_node.inputs["Image"])
        link = links.new(rgb_to_bw_node.outputs["Val"], composite_node.inputs["Image"])

    def _prepare_output_folder(self, sensor_name):
        """Prepare the output folder and return its path."""
        output_folder = utility.append_output_path(
            f"{sensor_name}_annotations/structured_light/"
        )
        utility.create_folder(output_folder)
        return output_folder