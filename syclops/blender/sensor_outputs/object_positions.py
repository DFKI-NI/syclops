import json
import logging
from pathlib import Path
import numpy as np
import bpy
from syclops import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface
from typing import List
import mathutils
# META DESCRIPTION
meta_description_object_positions = {
    "type": "OBJECT_POSITIONS",
    "format": "JSON",
    "description": "Output of all individual object location, rotation and scale with their class id.",
}


class ObjectPositions(OutputInterface):
    """Generate Camera RGB output"""

    def generate_output(self, parent_class: object = None):
        with utility.RevertAfter():
            # Depsgraph update
            bpy.context.view_layer.update()
            utility.refresh_modifiers()
            obj_dict = {}
            depsgraph = bpy.context.view_layer.depsgraph
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
                        location = object_instance.matrix_world.translation
                        rotation = object_instance.matrix_world.to_euler()
                        scale = object_instance.matrix_world.to_scale()
                        # Round to 4 decimal places
                        location = [round(x, 4) for x in location]
                        rotation = [round(x, 4) for x in rotation]
                        scale = [round(x, 4) for x in scale]
                        pose_dict = {
                            "loc": location,
                            "rot": rotation,
                            "scl": scale,
                            "id": self._calculate_instance_id(location),
                        }
                        if "keypoints" in object_instance.object:
                            pose_dict["keypoints"] = {}
                            for keypoint, pos in object_instance.object["keypoints"].items():
                                vec = mathutils.Vector((pos['x'], pos['y'], pos['z']))
                                world_position = object_instance.object.matrix_world @ vec
                                # Add keypoint to pose_dict
                                pose_dict["keypoints"][keypoint] = {
                                    "loc": [round(x, 4) for x in world_position]
                                }

                        if class_id not in obj_dict:
                            obj_dict[class_id] = []
                        obj_dict[class_id].append(pose_dict)

            output_folder = utility.append_output_path("object_positions")
            utility.create_folder(output_folder)

            # Set filename
            curr_frame = bpy.context.scene.frame_current
            json_file = output_folder / (str(curr_frame).rjust(4, "0") + ".json")
            # Write to json
            with open(json_file, "w") as f:
                f.write(json.dumps(obj_dict))
            self.write_meta_output_file(Path(json_file))
            logging.info("Wrote object positions to %s", json_file)

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
            writer.data.update(meta_description_object_positions)
            # Add current step
            writer.add_step(
                step=bpy.context.scene.frame_current,
                step_dicts=[
                    {
                        "type": meta_description_object_positions["type"],
                        "path": str(file.name),
                    }
                ],
            )

            # Add expected steps
            writer.data["expected_steps"] = utility.get_job_conf()["steps"]
            writer.data["sensor"] = bpy.context.scene.camera["name"]
            writer.data["id"] = self.config["id"]
