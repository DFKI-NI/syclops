# Create Plugin

This document describes how to create a new sensor in order to add functionality to syclops.

## Overview

Plugins are python classes that are executed inside of Blender during the synthetic data generation. They follow a simple structure, which is composed of a initial setup step (the "load" function) which is run once at the beginning and a configure step (the "configure" function) which is run for each individual rendered frame. Usually this relates importing the 3D models initially and then altering their position, etc. for each step.

An interface class is provided that can be inherited from to make the plugin compatible with the pipeline. This interface class provides the load and configure functions, aswell as usefull utility functions. The plugin class can be extended with additional functions that are specific to the plugin.

## Basic Example
To give a better understanding, a very basic example is provided. This example plugin simply adds a cube to the scene and attaches it to a node from the transformation tree. Additionally, the color of the cube can be changed by specifying a color in the config file.

### Plugin
```python title="cube.py"
import logging
import bpy # (1)!
from syclops_blender import utility # (2)!
from syclops_plugins_core.plugins.plugin_interface import PluginInterface # (3)!

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

1. Blender python API
2. Collection of usefull utility functions
3. Interface class that provides load, configure and plugin specific utility functions
4. !!! info
    The blender cube object is stored as a pointer in order to be able to reference it later. This is necessary, because the "cube_obj" variable is not a safe reference to the object. To retrieve the object, the "get" function of the ObjPointer class is used.
5. This function attaches all objects in self.objs to a transformation node, if "frame_id" is specified in the config file.
6. Retrieve the cube object from the pointer

In order to use this plugin, it has to be added to an asset library. The following yaml file creates a simple library and adds the cube plugin to it.

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

The folder structure for this example is as follows:

```
.
├── assets.yaml
├── plugins
│   ├── cube.py
│   └── schema
│       └── cube.schema.yaml
```

To *install* the plugin, it has to be added to the asset paths file, or placed in the `assets` folder.
Calling `syclops -c` will crawl the new `Docs Example Asset Library` and add it to the asset catalog.
The plugin can now be used in a job config file in the `scene` section:

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