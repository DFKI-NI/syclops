# Create a Sensor and Output Plugins
In this document, the process of creating a new sensor with a new output for Syclops is explained.

## Overview

***Sensor-Plugins*** in Syclops are Python classes, that mimic the behavior of real sensors in the virtual environment. They are treated as the foundation for the ***Output-Plugins***, which are responsible for generating the data of the sensors. The sensor class is responsible for creating the sensor in the virtual environment and for providing the data to the ***Output-Plugin***. The ***Output-Plugin*** is responsible for generating the data for the sensor. This allows to reuse the same sensor for different ***Output-Plugins***.

Syclops provides interface classes to inherit from, ensuring compatibility with the pipeline. For a sensor, the class has two abstract methods, that need to be implemented: ***setup_sensor*** and ***render_outputs***. In the case of an output, the interface contains one abstract method: ***generate_output***.

## Basic Example

Below is a basic example illustrating how a laser distance sensor can be added to Syclops. Since the sensor class itself does not generate any data, it is a fairly simple class. The rest of the functionality is implemented in the [output plugin](#output).

### Sensor

```python title="laser_distance_sensor.py"
import logging
import bpy  # Blender python API
from syclops_blender import utility  # Collection of useful utility functions
from syclops.blender.sensors.sensor_interface import SensorInterface


class LaserDistanceSensor(SensorInterface):
    def setup_sensor(self):
        """Goal of this function is to create an object in the scene, that represents the sensor."""
        # Create empty object to represent the sensor
        sensor_empty = bpy.data.objects.new(self.config["name"], None)
        sensor_coll = utility.create_collection("Sensors")
        sensor_coll.objects.link(sensor_empty)
        # Add empty to class variable objs in order to be correctly attached to the tf-tree
        self.objs.append(utility.ObjPointer(sensor_empty))  # (1)!

        logging.info("Laser Distance Sensor: %s created", self.config["name"])

    def render_outputs(self):
        """This function calls all outputs that are assigned to this sensor"""
        for output in self.outputs:
            output.generate_output(self)
```

1. The blender empty object is stored as a pointer in order to be able to reference it later. This is necessary, because the "sensor_empty" variable is not a safe reference to the object. To retrieve the object, the "get" function of the ObjPointer class is used.

!!! warning
    This sensor class is in its current state not usable, because it does not generate any data. In order to use it, an output plugin has to be created.

### Output
```python title="laser_distance_output.py"
import json
import logging
from pathlib import Path

import bpy
from mathutils import Vector
from syclops_blender import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface

META_DESCRIPTION = {
    "type": "DISTANCE",
    "format": "JSON",
    "description": "Distance of a single laser ray to the closest object in the scene",
}


class LaserDistanceOutput(OutputInterface):
    """Handles the generation of laser distance output for sensors."""

    def generate_output(self, parent_class: object):
        """Generate and save the laser ray distance output to JSON."""
        with utility.RevertAfter():  # (1)!
            # Refresh the virtual scene
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
```

1. The `RevertAfter` context manager is used to revert all changes made to the scene after the context manager is exited.

### Sensor and Ouput Registration

To register your sensor and output plugins with Syclops, add entries in your pyproject.toml file under the [project.entry-points."syclops.plugins"] section. For example:

```toml title="pyproject.toml"
[project.entry-points."syclops.sensors"]
syclops_laser_sensor = "path.to.laser_distance_sensor:LaserDistanceSensor"
[project.entry-points."syclops.outputs"]
syclops_laser_output = "path.to.laser_distance_output:LaserDistanceOutput"
```

Replace `path.to.laser_distance_sensor` and `path.to.laser_distance_output` with the actual module paths where your `LaserDistanceSensor` and `LaserDistanceOutput` classes are defined.

The plugins are now directly integrated into your package and recognized by Syclops through the pyproject.toml entry. Ensure your package is installed via pip in the same virtual environment as Syclops.

**Directory Structure:**
```
.
├── pyproject.toml
├── sensors
│   ├── laser_distance_sensor.py
│   └── schema
│       └── laser_distance_sensor.schema.yaml
└── outputs
    ├── laser_distance_output.py
    └── schema
        └── laser_distance_output.schema.yaml
```

To **install** the plugins, simply install your package using pip. Once installed, Syclops will automatically detect and register the plugins. You can then use the plugins in a Syclops job configuration file within the `scene` section:

```yaml title="laser_distance_example_job.syclops.yaml"
# ...
transformations:
    laser_node:
        location: [0, 0, 2]
        rotation: [0, 0, 0]
sensor:
    syclops_laser_sensor: # (1)!
        - name: laser_sensor
          frame_id: laser_node
          outputs:
            - syclops_laser_output: # (1)!
              id: laser_output
# ...
```

1. This is the name of the entry point defined in the pyproject.toml file.

### Schema
A YAML schema file can be used to define the limits of the plugin configuration:

```yaml title="laser_distance_sensor.schema.yaml"
description: Frame for a laser distance sensor
type: array # (1)!
items:
  type: object
  properties:
    name:
      description: Unique identifier of the sensor
      type: string
    frame_id:
      description: Transformation tree node to attach to.
      type: string
    outputs:
      type: object
      properties:
        Docs Example Asset Library/LaserDistanceOutput:
          $ref: "#/definitions/Docs Example Asset Library/LaserDistanceOutput" # (2)!
      additionalProperties: False

  required: [name, frame_id, outputs]
```

1. Multiple instances of a plugin can be created. Therefore, the schema has to be of type array.
2. The schema of the output plugin is referenced here. This allows to define, which outputs are supported by the sensor.

```yaml title="laser_distance_output.schema.yaml"
description: Laser distance output. The distance and class_id are saved to a JSON file.
type: array # (1)!
items:
  type: object
  properties:
    id:
      description: Unique identifier of the output
      type: string
    debug_breakpoint:
      description: Wether to break and open Blender before rendering. Only works if scene debugging is active.
      type: boolean
  required: [id]
```

1. Multiple instances of a plugin can be created. Therefore, the schema has to be of type array.