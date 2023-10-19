import json
import logging
from pathlib import Path

import bpy
from mathutils import Vector
from syclops import utility
from syclops_plugins_core.sensor_outputs.output_interface import OutputInterface

META_DESCRIPTION = {
    "type": "DISTANCE",
    "format": "JSON",
    "description": "Distance of a single laser ray to the closest object in the scene",
}


class LaserDistanceOutput(OutputInterface):
    """Handles the generation of laser distance output for sensors."""

    def generate_output(self, parent_class: object):
        """Generate and save the laser ray distance output to JSON."""
        with utility.RevertAfter():
            # Update dependencies
            self._update_depsgraph()

            # Get ray origin and direction
            sensor_empty = parent_class.objs[0].get()
            ray_origin, ray_direction = self._compute_ray(sensor_empty)

            # Raycast
            hit, location, _, _, obj_hit, _ = self._raycast(ray_origin, ray_direction)

            distance = (location - ray_origin).length if hit else -1
            class_id = obj_hit.get("class_id") if hit else None

            # Save output
            output_path = self._prepare_output_folder(parent_class.config["name"])
            json_file = output_path / f"{bpy.context.scene.frame_current:04}.json"
            self._save_output(json_file, distance, class_id, location, ray_origin)

            # Write meta output
            self.write_meta_output_file(json_file, parent_class.config["name"])
            logging.info(f"Writing laser distance output to {json_file}")

    def _update_depsgraph(self):
        """Update the dependency graph."""
        bpy.context.view_layer.update()
        utility.refresh_modifiers()

    def _compute_ray(self, sensor_empty):
        """Compute the ray's origin and direction from the sensor_empty."""
        ray_origin = sensor_empty.matrix_world.translation
        ray_direction = sensor_empty.matrix_world.to_quaternion() @ Vector(
            (0.0, 0.0, -1.0)
        )
        return ray_origin, ray_direction

    def _raycast(self, ray_origin, ray_direction):
        """Perform ray casting in the Blender scene."""
        return bpy.context.scene.ray_cast(
            bpy.context.view_layer.depsgraph,
            ray_origin,
            ray_direction,
        )

    def _prepare_output_folder(self, sensor_name):
        """Prepare the output folder and return its path."""
        output_folder = utility.append_output_path(f"{sensor_name}_annotations")
        utility.create_folder(output_folder)
        return output_folder

    def _save_output(self, json_file, distance, class_id, location, ray_origin):
        """Save the output data to a JSON file."""
        data = {
            "distance": distance,
            "class_id": class_id,
            "hit_location": list(location),
            "origin": list(ray_origin),
        }
        with open(json_file, "w") as f:
            json.dump(data, f)

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
