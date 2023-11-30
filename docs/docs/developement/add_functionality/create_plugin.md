# Create a Scene Plugin
This document instructs users on how to create a plugin to enhance the functionality of Syclops.

## Overview

Plugins in Syclops are Python classes executed within Blender during synthetic data generation. They typically follow a structure that involves an initial setup (the ***load*** function) run once at the beginning, followed by a configuration step (the ***configure*** function) run for each rendered frame. This often pertains to importing 3D models initially and then adjusting their position and other properties for each step.

Syclops provides an interface class to inherit from, ensuring sensor compatibility with the pipeline. This class contains the abstract methods ***load*** and ***configure***, as well as other useful utility functions. Additionally, you can extend the plugin class with functions unique to the plugin's needs.

## Basic Example

Below is a basic example illustrating how a plugin can add a cube to the scene, attach it to a transformation tree node, and change its color using the config file.

### Plugin

```python title="cube.py"
import logging
import bpy # Blender python API
from syclops import utility # Collection of useful utility functions
from syclops.blender.plugins.plugin_interface import PluginInterface

class Cube(PluginInterface):
    def __init__(self, config: dict):
        super().__init__(config)

    def load(self):
        """Add cube to the scene"""
        # Create a Blender collection to store the cube in
        collection = utility.create_collection(self.config["name"]) 
        utility.set_active_collection(collection)

        # Create a cube and add it to the collection
        bpy.ops.mesh.primitive_cube_add() 
        cube_obj = bpy.context.object
        # Create a material for the cube
        material = bpy.data.materials.new(name=self.config["name"] + "_material")
        material.use_nodes = True
        # Assign material to cube
        cube_obj.data.materials.append(material)

        self.objs.append(utility.ObjPointer(cube_obj)) # (1)!

        self.setup_tf() # (2)!

        logging.info("Cube: %s loaded", self.config["name"])


    def configure(self):
        """Configure the cube for the current frame"""

        # Set color of cube
        cube_obj = self.objs[0].get() # (3)!
        cube_material = cube_obj.data.materials[0]
        rgba_value = utility.eval_param(self.config["color"])
        pbr_node = cube_material.node_tree.nodes["Principled BSDF"]
        pbr_node.inputs["Base Color"].default_value = rgba_value

        logging.info("Cube: %s configured", self.config["name"])
```

1. The blender cube object is stored as a pointer in order to be able to reference it later. This is necessary, because the "cube_obj" variable is not a safe reference to the object. To retrieve the object, the "get" function of the ObjPointer class is used.
2. This function attaches all objects in self.objs to a transformation node, if "frame_id" is specified in the config file.
3. Retrieve the cube object from the pointer

### Plugin Registration

To register your plugin with Syclops, add an entry in your pyproject.toml file under the [project.entry-points."syclops.plugins"] section. For example:

```toml title="pyproject.toml"
[project.entry-points."syclops.plugins"]
syclops_cube_plugin = "path.to.cube:Cube"
```

Replace path.to.cube with the actual module path where your Cube class is defined.

The plugin is now directly integrated into your package and recognized by Syclops through the pyproject.toml entry. Ensure your package is installed via pip in the same virtual environment as Syclops.

**Directory Structure:**

```
.
├── pyproject.toml
├── plugins
│   ├── cube.py
│   └── schema
│       └── cube.schema.yaml
```

To **install** the plugin, simply install your package using pip. Once installed, Syclops will automatically detect and register the plugin. You can then use the plugin in a Syclops job configuration file within the `scene` section:


```yaml title="cube_example_job.syclops.yaml"
# ...
transformations:
    cube_node:
        location: [0, 0, 0]
        rotation: [0, 0, 0]
scene:
    syclops_cube_plugin: # (1)!
        - name: cube1
          frame_id: cube_node
          color: [1, 0, 0, 1] # (2)!
# ...
```

1. This is the name of the entry point defined in the pyproject.toml file.
2. In order to randomize the RGBA value every frame, a dynamic evaluator can be used:
```yaml
color: 
    uniform: [[0, 0, 0, 1], [1, 1, 1, 1]]
```

### Schema
A YAML schema file can be used to define the limits of the plugin configuration:

```yaml title="cube.schema.yaml"
description: A plugin that places a cube with a defined color in the scene
type: array # (1)!
items:
    type: object
    properties:
        name:
            type: string
            description: Unique name of the cube
        frame_id:
            type: string
            description: Name of the transformation node to attach the cube to
        color:
            type: array
            items:
                type: number
                minimum: 0
                maximum: 1
            minItems: 4
            maxItems: 4
            description: RGBA color value
    required: [name, frame_id, color]
```

1. Multiple instances of a plugin can be created. Therefore, the schema has to be of type array.