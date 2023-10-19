import logging
import os
from abc import ABC, abstractmethod
from typing import Callable

import bpy
import numpy as np
from syclops import utility


class OutputInterface(ABC):
    """Abstract class for an output pass"""

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def generate_output(self, parent_class: object = None):
        """Setup and generate the output.

        Args:
            parent_class (object, optional): Parent class. Defaults to None.
        """
        pass

    @staticmethod
    def process_alpha(mat, threshold=0.5):
        """Get alpha nodes in material

        Args:
            mat (blender material): Material to process
            threshold (float, optional): Opacity threshold deciding if visible in pass. Defaults to 0.5.

        Returns:
            alpha_node (dict): Alpha node
            alpha_is_zero (bool): If alpha is zero
        """
        alpha_nodes = []
        alpha_is_zero = False
        nt = mat.node_tree
        links = nt.links
        for node in nt.nodes:
            if node.type == "BSDF_PRINCIPLED":
                # Search for alpha map linked to principled BSDF
                if node.inputs["Alpha"].is_linked:
                    from_node = node.inputs["Alpha"].links[0].from_node
                    from_socket = node.inputs["Alpha"].links[0].from_socket
                    while from_node.type == "REROUTE":
                        from_socket = from_node.inputs[0].links[0].from_socket
                        from_node = from_node.inputs[0].links[0].from_node
                    alpha_nodes.append({"node": from_node, "socket": from_socket})
                # If no link, check if alpha is set to number
                elif node.inputs["Alpha"].default_value < 1:
                    value = node.inputs["Alpha"].default_value
                    alpha_is_zero = value <= threshold
                    node.inputs["Alpha"].default_value = value > threshold

        if len(alpha_nodes) == 0:
            for node in nt.nodes:
                if node.type == "BSDF_TRANSPARENT":
                    to_node = node.outputs["BSDF"].links[0].to_node
                    while to_node.type == "REROUTE":
                        to_node = to_node.outputs[0].links[0].to_node
                    # Check if node is mix shader
                    if to_node.type == "MIX_SHADER":
                        # Fix Graswald object pass index dependency
                        from_node = to_node.inputs["Fac"].links[0].from_node
                        if from_node.type == "GROUP":
                            if "Object Info" in from_node.node_tree.nodes:
                                object_info_node = from_node.node_tree.nodes[
                                    "Object Info"
                                ]
                                try:
                                    object_info_to_node = (
                                        object_info_node.outputs["Object Index"]
                                        .links[0]
                                        .to_node
                                    )
                                    # Remove link
                                    from_node.node_tree.links.remove(
                                        object_info_node.outputs["Object Index"].links[
                                            0
                                        ]
                                    )
                                    object_info_to_node.inputs[0].default_value = 0
                                except:
                                    pass
                        from_socket = to_node.inputs["Fac"].links[0].from_socket
                        alpha_nodes.append({"node": to_node, "socket": from_socket})

        assert len(alpha_nodes) <= 1, (
            "Multiple alpha nodes found for material " + mat.name
        )  # Currently support only one alpha node per material
        alpha_node = alpha_nodes[0] if len(alpha_nodes) > 0 else None
        # Make alpha binary with color ramp node
        if alpha_node is not None:
            # New color ramp node
            color_ramp = nt.nodes.new("ShaderNodeValToRGB")
            # Link alpha to color ramp
            color_ramp.color_ramp.interpolation = "CONSTANT"
            color_ramp.color_ramp.elements[1].position = threshold
            # Link alpha to outputs
            for link in alpha_node["socket"].links:
                links.new(color_ramp.outputs["Color"], link.to_socket)
            links.new(alpha_node["socket"], color_ramp.inputs[0])
            # Add to list of binary alpha nodes
            alpha_node = {"node": color_ramp, "socket": color_ramp.outputs["Color"]}
        return alpha_node, alpha_is_zero

    @staticmethod
    def add_aov(mat, aov_name, alpha_node, alpha_is_zero, aov_type="Value"):
        """Add AOV to material"""
        # Add AOV output node and combine with alpha node
        if mat.use_nodes:
            aov_node = mat.node_tree.nodes.new("ShaderNodeOutputAOV")
            aov_node.name = aov_name
            if aov_type == "Value":
                math_node = mat.node_tree.nodes.new("ShaderNodeMath")
            else:
                math_node = mat.node_tree.nodes.new("ShaderNodeVectorMath")
            math_node.operation = "MULTIPLY"
            # Link math node to AOV
            links = mat.node_tree.links
            links.new(math_node.outputs[0], aov_node.inputs[aov_type])

            if alpha_node is not None:
                # Link alpha to math node
                links.new(alpha_node["socket"], math_node.inputs[0])
            elif alpha_is_zero:
                if aov_type == "Value":
                    val = 0.0
                else:
                    val = [0.0, 0.0, 0.0]
                # If alpha is zero, set AOV to zero
                math_node.inputs[0].default_value = val
            else:
                if aov_type == "Value":
                    val = 1.0
                else:
                    val = [1.0, 1.0, 1.0]

                math_node.inputs[0].default_value = val
            return math_node
        else:
            return None

    @staticmethod
    def exr_to_npy(file: str, conversion_function: Callable = None) -> str:
        """Convert exr to npy"""
        if file.endswith(".exr"):
            img = utility.load_img_as_array(file)
            # Remove alpha
            img = img[:, :, :3]
            # Check if channels have equal values
            if np.all(img[:, :, 0] == img[:, :, 1]) and np.all(
                img[:, :, 0] == img[:, :, 2]
            ):
                img = img[:, :, 0]  # Convert to single channel

            if conversion_function is not None:
                img = conversion_function(img, file)
            # Save as numpy array
            np.savez_compressed(file.replace(".exr", ".npz"), array=img)
            os.remove(file)
            logging.info("Converted %s to numpy array", file)
        return file.replace(".exr", ".npz")

    def compositor(self):
        """Add nodes to compositor"""
        if "compositor" in self.config:
            if "chromatic_aberration" in self.config["compositor"]:
                chrom_node = self.add_compositor_node("Lensdist")
                chrom_node.inputs[2].default_value = self.config["compositor"][
                    "chromatic_aberration"
                ]
            if "bloom" in self.config["compositor"]:
                bloom_node = self.add_compositor_node("Glare")
                bloom_node.threshold = self.config["compositor"]["bloom"]["threshold"]
                bloom_node.glare_type = "FOG_GLOW"

    def check_debug_breakpoint(self):
        """Check if debug breakpoint is set, gui mode is active and break if so"""
        if (
            not bpy.app.background
            and "debug_breakpoint" in self.config
            and self.config["debug_breakpoint"]
        ):
            utility.show_all_modifiers()
            raise Exception("Exiting Python to view scene in Blender")

    @staticmethod
    def add_compositor_node(name):
        """Add node to compositor"""
        scene = bpy.context.scene
        scene.use_nodes = True
        tree = scene.node_tree
        links = tree.links
        node = tree.nodes.new(type="CompositorNode" + name)
        composite = tree.nodes["Composite"]
        from_socket = composite.inputs["Image"].links[0].from_socket
        links.new(from_socket, node.inputs["Image"])
        links.new(node.outputs["Image"], composite.inputs["Image"])
        return node
