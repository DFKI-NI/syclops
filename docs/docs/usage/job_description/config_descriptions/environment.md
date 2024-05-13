# Environment Plugin Documentation

The Environment Plugin is designed to set the ambiance of the scene. It establishes the lighting and background elements. By randomly changing the environment, the colors drastically shift and adds variety to the generated data.

## Configuration Parameters

The following table describes each configuration parameter for the Environment Plugin:

| Parameter | Type | Description | Requirement |
| ----------- | ------ | -------------- | --------------- |
| `type` | string (enum: `hdri`, `hdri_and_sun`) | Determines the type of environment setup. Choose from solely HDRI or a combination of HDRI with sun. | **Required** |
| `environment_image` | string (dynamic evaluator capable) | The HDRI image used as the environment map, serving as both the background and the illumination source. | **Required** |
| `sun_elevation` | number (dynamic evaluator capable) | The elevation angle of the sun, defined in radians. | Required if `type` is `hdri_and_sun` |
| `sun_rotation` | number (dynamic evaluator capable) | The sun's rotation angle, measured in radians. | Required if `type` is `hdri_and_sun` |
| `random_rotation` | boolean | Randomly rotates the environment map every frame. | Optional (default: `true`) |

!!! warning
    When you choose `hdri_and_sun` for the `type`, you must also provide values for `sun_elevation` and `sun_rotation`.

### Dynamic Evaluators

Parameters like `environment_image`, `sun_elevation`, and `sun_rotation` can be set to change dynamically in every frame. This is handy for simulating the motion of the environment or sun over time. To understand how to apply dynamic evaluators to these parameters, please refer to [Dynamic Evaluators](../dynamic_evaluators.md).

## Example Configuration

Here's a sample configuration for the Environment Plugin:

```yaml
scene:
  syclops_plugin_environment:
    - type: hdri
      environment_image: Example Assets/Sunflower Field
```

In the above setup, the scene will have a sunflower field HDRI backdrop.