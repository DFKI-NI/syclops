import json
import logging
from pathlib import Path
import numpy as np
import bpy
from syclops import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface
from typing import List
import mathutils
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import math


# META DESCRIPTION
meta_description_object_occlusion = {
    "type": "OBJECT_OCCLUSION",
    "format": "JSON",
    "description": "Output of the occlusion percentage for each object instance.",
}


class ObjectOcclusion(OutputInterface):
    """Generate object occlusion output"""

    def generate_output(self, parent_class: object = None):
        with utility.RevertAfter():
            # Depsgraph update
            bpy.context.view_layer.update()
            utility.refresh_modifiers()
            logging.info("Generating object occlusion output")
            scene = bpy.context.scene
            camera = scene.camera
            depsgraph = bpy.context.evaluated_depsgraph_get()
            num_instances = len(depsgraph.object_instances)
            for instance in depsgraph.object_instances:
                # Iterate over all objects in the scene
                obj = instance.object
                if obj.type == "MESH":
                    # Check if the object is in the camera's frustum
                    if not self.is_object_in_frustum(obj, camera, scene):
                        obj.hide_viewport = True
                        obj.hide_render = True

            bpy.context.view_layer.update()
            depsgraph.update()
            logging.info(
                "Removed %d instances that are out of view.",
                num_instances - len(depsgraph.object_instances),
            )
            res_ratio = self.config.get("res_ratio", 0.1)
            res_x = int(scene.render.resolution_x * res_ratio)
            res_y = int(scene.render.resolution_y * res_ratio)

            occlusion_dict = self.occlusion_test(scene, depsgraph, camera, res_x, res_y)
            # Set Blender output file name to current frame
            cam_name = bpy.context.scene.camera["name"]
            output_path = Path(f"{cam_name}_annotations/object_occlusion")
            output_folder = utility.append_output_path(
                output_path, set_blend_path=False
            )
            utility.create_folder(output_folder)

            # Set filename
            curr_frame = bpy.context.scene.frame_current
            json_file = output_folder / (str(curr_frame).rjust(4, "0") + ".json")

            # Write to json
            with open(json_file, "w") as f:
                f.write(json.dumps(occlusion_dict))

            self.write_meta_output_file(Path(json_file))
            logging.info("Wrote object occlusion to %s", json_file)

    @staticmethod
    def occlusion_test(scene, depsgraph, camera, resolution_x, resolution_y):
        """Calculate the percentage of an object's bounding box that is visible and occluded."""
        top_right, _, bottom_left, top_left = camera.data.view_frame(scene=scene)

        camera_quaternion = camera.matrix_world.to_quaternion()
        camera_translation = camera.matrix_world.translation

        x_range = np.linspace(top_left[0], top_right[0], resolution_x)
        y_range = np.linspace(top_left[1], bottom_left[1], resolution_y)

        z_dir = top_left[2]

        unoccluded_hits = {}
        occluded_hits = {}

        # Iterate over all X/Y coordinates
        for x in x_range:
            for y in y_range:
                pixel_vector = Vector((x, y, z_dir))
                pixel_vector.rotate(camera_quaternion)
                pixel_vector.normalized()

                origin = camera_translation
                direction = pixel_vector

                hit_objects = set()
                first_contact = True

                while True:
                    result, location, _, _, hit_obj, _ = scene.ray_cast(
                        depsgraph, origin, direction
                    )

                    if result:
                        if first_contact:
                            if hit_obj not in unoccluded_hits:
                                unoccluded_hits[hit_obj] = 0
                            unoccluded_hits[hit_obj] += 1
                            hit_objects.add(hit_obj)
                            first_contact = False
                        elif hit_obj not in hit_objects:
                            if hit_obj not in occluded_hits:
                                occluded_hits[hit_obj] = 0
                            occluded_hits[hit_obj] += 1
                            hit_objects.add(hit_obj)

                        # Adjust the new origin based on the last hit position and a small offset
                        origin = location + direction * 0.0001
                    else:
                        break

        total_rays = resolution_x * resolution_y
        occlusion_dict = {}

        for obj in depsgraph.object_instances:
            if obj.object.type == "MESH" and obj != camera:
                unoccluded_count = unoccluded_hits.get(obj.object.original, 0)
                occluded_count = occluded_hits.get(obj.object.original, 0)
                if unoccluded_count + occluded_count == 0:
                    continue
                visibility = unoccluded_count / total_rays
                occlusion = occluded_count / (unoccluded_count + occluded_count)

                instance_id = ObjectOcclusion._calculate_instance_id(
                    obj.object.matrix_world.translation
                )
                occlusion_dict[instance_id] = {
                    "visibility": visibility,
                    "occlusion": occlusion,
                }

        return occlusion_dict

    @staticmethod
    def is_object_in_frustum(obj, camera, scene):
        # Get the object's bounding box corners in world space
        bbox_corners = [
            obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box
        ]

        # Initialize variables to store the signs of the coordinates
        x_sign = None
        y_sign = None
        z_sign = None

        # Check if any of the bounding box corners are in view
        for corner in bbox_corners:
            # Convert the corner to normalized device coordinates (NDC)
            cv = world_to_camera_view(scene, camera, corner)

            # Check if the corner is within the view frustum
            if 0.0 <= cv.x <= 1.0 and 0.0 <= cv.y <= 1.0 and 0.0 <= cv.z:
                return True

            # Check if the signs of the coordinates are different
            if x_sign is None:
                x_sign = math.copysign(1, cv.x)
            elif math.copysign(1, cv.x) != x_sign:
                return True

            if y_sign is None:
                y_sign = math.copysign(1, cv.y)
            elif math.copysign(1, cv.y) != y_sign:
                return True

            if z_sign is None:
                z_sign = math.copysign(1, cv.z)
            elif math.copysign(1, cv.z) != z_sign:
                return True

        return False

    @staticmethod
    def _calculate_instance_id(location: List[float]) -> int:
        """Calculate the instance id from the location.

        Args:
            location: The location.

        Returns:
            int: The instance id.
        """
        # Convert x, y, z to mm and round to integer
        location = np.round(np.array(location) * 1000)

        return utility.hash_vector(location)

    def write_meta_output_file(self, file: Path):
        """Write the meta output file"""
        # Get the output folder
        output_path = file.parent

        with utility.AtomicYAMLWriter(str(output_path / "metadata.yaml")) as writer:
            # Add metadata
            writer.data.update(meta_description_object_occlusion)
            # Add current step
            writer.add_step(
                step=bpy.context.scene.frame_current,
                step_dicts=[
                    {
                        "type": meta_description_object_occlusion["type"],
                        "path": str(file.name),
                    }
                ],
            )

            # Add expected steps
            writer.data["expected_steps"] = utility.get_job_conf()["steps"]
            writer.data["sensor"] = bpy.context.scene.camera["name"]
            writer.data["id"] = self.config["id"]
