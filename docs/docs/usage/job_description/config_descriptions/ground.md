# Ground Plugin Documentation

The Ground Plugin is a fundamental asset that lets you set up the floor plane for the virtual scene. With the flexibility to assign different materials and height maps, the Ground Plugin offers a realistic baseline for the virtual environment. 

## Overview

The Ground Plugin is responsible for creating a square floor in the virtual environment. Most other plugins rely on the ground plane for object placement. Depending on your needs, this floor can be designed using predefined 3D models, or you can create a floor plane from scratch by specifying its size and texture.

## Configuration Parameters

The following table describes each configuration parameter for the Ground Plugin:

| Parameter | Type | Description | Requirement |
| ----------- | ------ | -------------- | --------------- |
| `name` | string | A unique identifier for the plugin instance. | **Required** |
| `object_path` | asset model | The path to a 3D Object representing the ground. If used, `size`, `texture`, and `displacement_texture` must not be specified. | Optional |
| `size` | number | Specifies the width and length of the ground in meters. This is used when generating a floor plane without a 3D model. | Optional |
| `texture` | string (dynamic evaluator capable) | The PBR texture of the ground. This is required if you're creating a floor plane without using a 3D model. | Optional |
| `displacement_texture` | image texture (dynamic evaluator capable) | A height map for the ground. If the texture is 16-bit, a pixel value of 32768 signifies 0m in height. An increase in pixel value by 1 corresponds to a height difference of 0.5cm. | Optional |
| `class_id` | integer | Class ID for ground truth output. | **Required** |

!!! warning
    When using `object_path`, you must **not** specify `size`, `texture`, and `displacement_texture`. Conversely, when specifying `size` and `texture`, the `object_path` parameter must not be used.

### Dynamic Evaluators

Some parameters, like `texture` and `displacement_texture`, can be dynamically evaluated. This means that their values can be altered for each new frame. For more insights on dynamic evaluators and how to use them, kindly refer to [Dynamic Evaluators](../dynamic_evaluators.md).

## Example Configuration

Here's a simple example of how to configure the Ground Plugin:

```yaml
scene:
  syclops_plugin_ground:
    - name: "Ground"
      size: 50
      texture: Example Assets/Muddy Dry Ground
      displacement_texture: Example Assets/Ground Displacement 1
      class_id: 1
```

In the example above, a square floor plane of 50 meters with a muddy dry ground texture and a height map is created.