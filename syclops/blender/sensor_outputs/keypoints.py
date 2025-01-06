import json
import logging
from pathlib import Path

import bpy
import bpy_extras
from mathutils import Vector
import mathutils
from syclops import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface
import numpy as np
from typing import List

META_DESCRIPTION = {
    "type": "KEYPOINTS",
    "format": "JSON",
    "description": "Keypoints of objects in camera space.",
}


class Keypoints(OutputInterface):

    def generate_output(self, parent_class: object):
        """Calculate the 3D keypoint positions and transform to camera space."""
        with utility.RevertAfter():
            # Update dependencies
            self._update_depsgraph()
            self.check_debug_breakpoint()
            
            obj_dict = {}
            depsgraph = bpy.context.view_layer.depsgraph
            scene = bpy.context.scene
            camera = scene.camera
            render_scale = scene.render.resolution_percentage / 100
            width = int(scene.render.resolution_x * render_scale)
            height = int(scene.render.resolution_y * render_scale)

            for object_instance in depsgraph.object_instances:
                if object_instance.object.type == "MESH":
                    parent = object_instance.parent
                    class_id = None
                    is_instance = (
                        object_instance.object.is_from_instancer and parent is not None
                    )
                    object_visible = utility.render_visibility(object_instance.object)
                    if is_instance:
                        parent_visible = utility.render_visibility(parent)
                        if parent_visible:
                            class_id = object_instance.object.get("class_id")
                    elif object_visible:
                        class_id = object_instance.object.get("class_id")

                    if class_id is not None:
                        if "keypoints" in object_instance.object:
                            location = object_instance.matrix_world.translation
                            location = [round(x, 6) for x in location]
                            instance_id = self._calculate_instance_id(location)
                            for keypoint, pos in object_instance.object["keypoints"].items():
                                vec = mathutils.Vector((pos['x'], pos['y'], pos['z']))
                                vec = object_instance.matrix_world @ vec
                                co_2d = bpy_extras.object_utils.world_to_camera_view(scene, camera, vec)

                                pixel_x = round(co_2d.x * width)
                                pixel_y = height - round(co_2d.y * height)

                                if pixel_x < 0 or pixel_y < 0 or pixel_x > width or pixel_y > height:
                                    continue
                                
                                # Add to obj_dict
                                if instance_id not in obj_dict:
                                    obj_dict[instance_id] = {"class_id": class_id}
                                obj_dict[instance_id][keypoint] = {
                                    "x": pixel_x,
                                    "y": pixel_y,
                                }

            # Save output
            output_path = self._prepare_output_folder(parent_class.config["name"])
            json_file = output_path / f"{bpy.context.scene.frame_current:04}.json"
            with open(json_file, "w") as f:
                json.dump(obj_dict, f)

            # Write meta output
            self.write_meta_output_file(json_file, parent_class.config["name"])
            logging.info(f"Writing keypoints output to {json_file}")

    def _update_depsgraph(self):
        """Update the dependency graph."""
        bpy.context.view_layer.update()
        utility.refresh_modifiers()

    def _prepare_output_folder(self, sensor_name):
        """Prepare the output folder and return its path."""
        output_folder = utility.append_output_path(f"{sensor_name}_annotations/keypoints/")
        utility.create_folder(output_folder)
        return output_folder

    def write_meta_output_file(self, file: Path, sensor_name: str):
        """Write the metadata output to a YAML file."""
        output_path = file.parent

        with utility.AtomicYAMLWriter(str(output_path / "metadata.yaml")) as writer:
            writer.data.update(META_DESCRIPTION)
            writer.add_step(
                step=bpy.context.scene.frame_current,
                step_dicts=[
                    {
                        "type": META_DESCRIPTION["type"],
                        "path": str(file.name),
                    },
                ],
            )
            writer.data["expected_steps"] = utility.get_job_conf()["steps"]
            writer.data["sensor"] = sensor_name
            writer.data["id"] = self.config["id"]

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
