# Create a Plugin

This document instructs users on how to create a plugin to enhance the functionality of Syclops.
---

## Overview

Plugins in Syclops are Python classes executed within Blender during synthetic data generation. They typically follow a structure that involves an initial setup (the "load" function) run once at the beginning, followed by a configuration step (the "configure" function) run for each rendered frame. This often pertains to importing 3D models initially and then adjusting their position and other properties for each step.

Syclops provides an interface class to inherit from, ensuring plugin compatibility with the pipeline. This class offers the 'load' and 'configure' methods and other useful utility functions. Additionally, you can extend the plugin class with functions unique to the plugin's needs.

## Basic Example

Below is a basic example illustrating how a plugin can add a cube to the scene, attach it to a transformation tree node, and change its color using the config file.

### Plugin

```python title="cube.py"
import logging
import bpy # Blender python API
from syclops_blender import utility # Collection of usefull utility functions
from syclops_plugins_core.plugins.plugin_interface import PluginInterface

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

        self.objs.append(utility.ObjPointer(cube_obj)) # (4)!

        self.setup_tf() # (5)!

        logging.info("Cube: %s loaded", self.config["name"])


    def configure(self):
        """Configure the cube for the current frame"""

        # Set color of cube
        cube_obj = self.objs[0].get() # (6)!
        cube_material = cube_obj.data.materials[0]
        rgba_value = utility.eval_param(self.config["color"])
        cube_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = rgba_value

        logging.info("Cube: %s configured", self.config["name"])
```

1. !!! info
    The blender cube object is stored as a pointer in order to be able to reference it later. This is necessary, because the "cube_obj" variable is not a safe reference to the object. To retrieve the object, the "get" function of the ObjPointer class is used.
5. This function attaches all objects in self.objs to a transformation node, if "frame_id" is specified in the config file.
6. Retrieve the cube object from the pointer

### Asset Configuration

For the plugin to be operational, you must add it to an asset library. Here's a YAML file that constructs a simple library and integrates the cube plugin:

```yaml title="asset.yaml"
name: Docs Example Asset Library
description: Asset library that contains the cube example plugin

assets:
  Cube: # (1)!
    type: plugin
    tags: [cube, color]
    license: CC0
    filepath: plugins/cube.py
    schema: plugins/schema/cube.schema.yaml # (2)!
```

1. Should have the same name as the plugin class
2. Specifying a schema is optional, but recommended. It allows to validate the plugin configuration.


**Directory Structure:**

```
.
├── assets.yaml
├── plugins
│   ├── cube.py
│   └── schema
│       └── cube.schema.yaml
```

To **install** the plugin, add it to the asset paths file or position it in the `assets` folder. Running `syclops -c` will traverse the new `Docs Example Asset Library` and register it in the asset catalog. Now, you can utilize the plugin in a job configuration file within the `scene` section:

```yaml title="cube_example_job.syclops.yaml"
# ...
transformations:
    cube_node:
        location: [0, 0, 0]
        rotation: [0, 0, 0]
scene:
    Docs Example Asset Library/Cube:
        - name: cube1
          frame_id: cube_node
          color: [1, 0, 0, 1] # (1)!
# ...
```

1. In order to randomize the RGBA value every frame, a dynamic evaluator can be used:
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