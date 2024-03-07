import logging
import os
from pathlib import Path

import bpy
import numpy as np
from syclops import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface

# META DESCRIPTION
meta_description_semantic = {
    "type": "SEMANTIC_SEGMENTATION",
    "format": "NPZ",
    "description": "Semantic segmentation mask with individual integers for each object in the scene.",
}

meta_description_instance = {
    "type": "INSTANCE_SEGMENTATION",
    "format": "NPZ",
    "description": "Instance segmentation mask with individual integers for each object in the scene.",
}

meta_description_depth = {
    "type": "DEPTH",
    "format": "NPZ",
    "description": "Contains the z-coordinate of each pixel in the camera coordinate system in meters.",
}

meta_description_pointcloud = {
    "type": "POINTCLOUD",
    "format": "NPZ",
    "description": "Contains the x,y and z coordinate of every pixel in the camera coordinate system in meters.",
}

meta_description_object_volume = {
    "type": "VOLUME",
    "format": "NPZ",
    "description": "Each pixel contains the volume of the object it belongs to. It is described in cm^3.",
}



# Output postprocessing functions
def postprocess_functions(img, file):
    if "semantic_segmentation" in file:
        img = np.round(img).astype(np.int32)

    elif "instance_segmentation" in file:
        try:
            # Convert x, y, z to mm and round to integer
            img_mm = np.round(img * 1000)

            # Calculate unique x, y, z values and assign new index
            values, index = np.unique(img_mm.reshape(-1, img_mm.shape[2]), axis=0, return_inverse=True)

            # Hash the unique values to get the instance id
            vectorized_hash = np.vectorize(utility.hash_vector, signature='(n)->()')
            instance_id = vectorized_hash(values)

            # Create instance segmentation mask
            img_mask = instance_id[index]
            img = img_mask.reshape(img_mm.shape[0], img_mm.shape[1])
            if values.shape[0] != instance_id.shape[0]:
                logging.warning("Hashing of instance ids created collisions")
        except IndexError:
            logging.warning("Instance segmentation mask is empty")
            img = np.zeros(img.shape[:2], dtype=np.int32)
    elif "object_volume" in file:
        img = np.trunc(img * 10**3) / (10**3)
    return img


class PixelAnnotation(OutputInterface):
    """Generate pixel accurate ground truth output"""

    def generate_output(self, parent_class: object = None):
        with utility.RevertAfter():
            self.configure_semantic_seg()
            self.configure_instance_seg()
            self.configure_depth()
            self.configure_pointcloud()
            self.configure_object_volume()
            self.render_configuration()

    @staticmethod
    def set_object_class_ids():
        """Set the class id for each object in the scene."""
        for obj in bpy.data.objects:
            class_id = obj.get("class_id")
            if class_id is not None:
                obj.pass_index = class_id

            class_id_offset = obj.get("class_id_offset")
            if class_id_offset is not None:
                for material_name, offset in class_id_offset.items():
                    for mat in obj.data.materials:
                        # Strip of the .001, .002, etc. from the material name
                        # Name can have multiple dots, so we only strip the last one
                        if mat.name.rsplit(".", 1)[0] == material_name:
                            offset_node = mat.node_tree.nodes.new("ShaderNodeValue")
                            offset_node.name = "class_id_offset"
                            offset_node.outputs[0].default_value = offset

    def configure_semantic_seg(self):
        """Configure the semantic segmentation pass."""
        self.set_object_class_ids()
        for mat in bpy.data.materials:
            if mat.use_nodes:
                alpha_node, alpha_is_zero = self.process_alpha(mat)
                aov = self.add_aov(
                    mat, "semantic_segmentation", alpha_node, alpha_is_zero
                )
                # Add object info node
                obj_info = mat.node_tree.nodes.new("ShaderNodeObjectInfo")
                # Link Object index to AOV
                links = mat.node_tree.links

                # If class_id_offset value node exists, link it a new math node to add the offset
                if "class_id_offset" in mat.node_tree.nodes:
                    class_id_offset = mat.node_tree.nodes["class_id_offset"]
                    math_node = mat.node_tree.nodes.new("ShaderNodeMath")
                    math_node.operation = "ADD"
                    links.new(class_id_offset.outputs["Value"], math_node.inputs[0])
                    links.new(obj_info.outputs["Object Index"], math_node.inputs[1])
                    links.new(math_node.outputs["Value"], aov.inputs[1])
                else:
                    links.new(obj_info.outputs["Object Index"], aov.inputs[1])

    def configure_instance_seg(self):
        """Configure the instance segmentation pass"""
        for mat in bpy.data.materials:
            if mat.use_nodes:
                alpha_node, alpha_is_zero = self.process_alpha(mat)
                aov = self.add_aov(
                    mat, "instance_segmentation", alpha_node, alpha_is_zero, "Color"
                )

                # Add object info node
                obj_info = mat.node_tree.nodes.new("ShaderNodeObjectInfo")
                # Link Object Location to AOV
                links = mat.node_tree.links
                links.new(obj_info.outputs["Location"], aov.inputs[1])

    def configure_depth(self):
        """Configure the depth pass"""
        for mat in bpy.data.materials:
            if mat.use_nodes:
                alpha_node, alpha_is_zero = self.process_alpha(mat)
                aov = self.add_aov(mat, "depth", alpha_node, alpha_is_zero)
                # Add object info node
                cam_data = mat.node_tree.nodes.new("ShaderNodeCameraData")
                # Link Object index to AOV
                links = mat.node_tree.links
                links.new(cam_data.outputs["View Z Depth"], aov.inputs[1])

    def configure_pointcloud(self):
        """Configure a pointcloud pass"""
        for mat in bpy.data.materials:
            if mat.use_nodes:
                alpha_node, alpha_is_zero = self.process_alpha(mat)
                aov = self.add_aov(
                    mat, "pointcloud", alpha_node, alpha_is_zero, "Color"
                )
                # Add geometry node
                geom_node = mat.node_tree.nodes.new("ShaderNodeNewGeometry")
                # Add vector transform node
                transform_node = mat.node_tree.nodes.new("ShaderNodeVectorTransform")
                transform_node.vector_type = "POINT"
                transform_node.convert_to = "CAMERA"
                # Link nodes
                links = mat.node_tree.links
                links.new(geom_node.outputs["Position"], transform_node.inputs[0])
                links.new(transform_node.outputs["Vector"], aov.inputs[1])

    def configure_object_volume(self):
        """Configure the object volume pass"""
        for mat in bpy.data.materials:
            if mat.use_nodes:
                alpha_node, alpha_is_zero = self.process_alpha(mat)
                aov = self.add_aov(mat, "object_volume", alpha_node, alpha_is_zero)
                # Add Attribute Nodes
                vol_attribute = mat.node_tree.nodes.new("ShaderNodeAttribute")
                vol_attribute.attribute_name = "volume"
                scale_attribute = mat.node_tree.nodes.new("ShaderNodeAttribute")
                scale_attribute.attribute_type = "INSTANCER"
                scale_attribute.attribute_name = "instance_scale"
                # Add Math Nodes
                compare_node = mat.node_tree.nodes.new("ShaderNodeMath")
                compare_node.operation = "COMPARE"
                compare_node.inputs[1].default_value = 0.0
                compare_node.inputs[2].default_value = 0.00001
                multiply_node = mat.node_tree.nodes.new("ShaderNodeMath")
                multiply_node.operation = "MULTIPLY"
                mix_node = mat.node_tree.nodes.new("ShaderNodeMix")
                # Link Object index to AOV
                links = mat.node_tree.links
                links.new(vol_attribute.outputs["Fac"], mix_node.inputs["B"])
                links.new(vol_attribute.outputs["Fac"], multiply_node.inputs[0])
                links.new(scale_attribute.outputs["Fac"], multiply_node.inputs[1])
                links.new(multiply_node.outputs[0], mix_node.inputs["A"])
                links.new(compare_node.outputs[0], mix_node.inputs["Factor"])
                links.new(scale_attribute.outputs["Fac"], compare_node.inputs[0])
                links.new(mix_node.outputs[0], aov.inputs[1])

    def render_configuration(self):
        """Setup all render settings for the output"""
        utility.configure_render()
        scene = bpy.context.scene
        scene.cycles.use_denoising = False
        scene.cycles.samples = 1

        # Add AOV Outputs
        bpy.ops.scene.view_layer_add_aov()
        aov = bpy.context.scene.view_layers["ViewLayer"].active_aov
        aov.name = "semantic_segmentation"
        aov.type = "VALUE"
        bpy.ops.scene.view_layer_add_aov()
        aov = bpy.context.scene.view_layers["ViewLayer"].active_aov
        aov.name = "instance_segmentation"
        aov.type = "COLOR"
        bpy.ops.scene.view_layer_add_aov()
        aov = bpy.context.scene.view_layers["ViewLayer"].active_aov
        aov.name = "depth"
        aov.type = "VALUE"
        bpy.ops.scene.view_layer_add_aov()
        aov = bpy.context.scene.view_layers["ViewLayer"].active_aov
        aov.name = "pointcloud"
        aov.type = "COLOR"
        bpy.ops.scene.view_layer_add_aov()
        aov = bpy.context.scene.view_layers["ViewLayer"].active_aov
        aov.name = "object_volume"
        aov.type = "VALUE"

        scene.use_nodes = True
        tree = scene.node_tree
        # Create new output node
        output_node = tree.nodes.new("CompositorNodeOutputFile")
        output_node.name = "Output_File"

        # Set-up the output img format
        output_node.format.file_format = "OPEN_EXR"
        output_node.format.color_mode = "RGBA"
        output_node.format.color_depth = "32"

        output_files = []

        # Configure output passes
        output_files = self.configure_ground_truth_pass(
            output_node, "semantic_segmentation", output_files
        )
        output_files = self.configure_ground_truth_pass(
            output_node, "instance_segmentation", output_files
        )
        output_files = self.configure_ground_truth_pass(
            output_node, "depth", output_files
        )
        output_files = self.configure_ground_truth_pass(
            output_node, "pointcloud", output_files
        )
        output_files = self.configure_ground_truth_pass(
            output_node, "object_volume", output_files
        )

        # Set Blender output file name to current frame
        cam_name = bpy.context.scene.camera["name"]
        output_path = Path(f"{cam_name}_annotations")
        output_node.base_path = str(
            utility.append_output_path(output_path, set_blend_path=False)
        )

        self.check_debug_breakpoint()
        logging.info(f"Rendering Pixel Annotations for sensor {cam_name}")
        bpy.ops.render.render(write_still=False)

        for file in output_files:
            file_path = Path(output_node.base_path, file + ".exr")
            new_file = self.exr_to_npy(str(file_path), postprocess_functions)
            self.write_meta_output_file(Path(new_file))

    def write_meta_output_file(self, file: Path):
        """Write the meta output file"""
        # Get the output folder
        output_path = Path(file).parent

        with utility.AtomicYAMLWriter(str(output_path / "metadata.yaml")) as writer:
            # Add metadata
            curr_frame = bpy.context.scene.frame_current
            if "semantic_segmentation" in str(file):
                writer.data.update(meta_description_semantic)
                type_name = "SEMANTIC_SEGMENTATION"
                id_str = self.config["semantic_segmentation"]["id"]
            elif "instance_segmentation" in str(file):
                writer.data.update(meta_description_instance)
                type_name = "INSTANCE_SEGMENTATION"
                id_str = self.config["instance_segmentation"]["id"]
            elif "depth" in str(file):
                writer.data.update(meta_description_depth)
                type_name = "DEPTH"
                id_str = self.config["depth"]["id"]
            elif "pointcloud" in str(file):
                writer.data.update(meta_description_pointcloud)
                type_name = "POINTCLOUD"
                id_str = self.config["pointcloud"]["id"]
            elif "object_volume" in str(file):
                writer.data.update(meta_description_object_volume)
                type_name = "VOLUME"
                id_str = self.config["object_volume"]["id"]
            # Add current step
            writer.add_step(
                step=curr_frame,
                step_dicts=[{"type": type_name, "path": str(file.name)}],
            )

            # Add expected steps
            writer.data["expected_steps"] = utility.get_job_conf()["steps"]
            writer.data["sensor"] = bpy.context.scene.camera["name"]
            writer.data["id"] = id_str

    def configure_ground_truth_pass(self, output_node, gt_pass, output_files):
        scene = bpy.context.scene
        tree = scene.node_tree
        links = tree.links
        render_layers = scene.node_tree.nodes["Render Layers"]

        active_camera_name = scene.camera["name"]
        curr_frame = bpy.context.scene.frame_current

        if gt_pass in self.config:
            slot_instance = output_node.layer_slots.new(gt_pass)
            output_node.file_slots[gt_pass].path = os.sep + gt_pass + os.sep
            links.new(render_layers.outputs[gt_pass], slot_instance)
            output_files.append(gt_pass + os.sep + str(curr_frame).rjust(4, "0"))
            logging.info("%s output for sensor %s", gt_pass, active_camera_name)
        return output_files
