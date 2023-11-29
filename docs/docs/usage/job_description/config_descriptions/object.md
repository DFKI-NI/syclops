# Object Plugin Documentation

The Object Plugin facilitates the addition of individual 3D models within the scene. It's essential to note that the positioning (pose) of these objects is managed by the transformation tree.

## Configuration Parameters

The following table describes each configuration parameter for the Object Plugin:

| Parameter | Type | Description | Requirement |
|-----------|------|-------------|-------------|
| `name` | string | A unique identifier for the plugin instance. | **Required** |
| `models` | array or single item | 3D models to be placed in the scene. It can be a list or a single item of 3D assets. | **Required** |
| `frame_id` | string | Denotes the node in the transformation tree where the object is attached. | **Required** |
| `place_on_ground` | boolean | If set to `true`, the object will be positioned on the ground and aligned to its normal. | Optional (Default: `false`) |
| `floor_object` | string | Specifies the ground object's name on which the model is placed. It's mandatory if `place_on_ground` is true. | Required if `place_on_ground` is true |
| `max_texture_size` | integer | The texture's upper limit in pixels. Useful for reducing texture size and conserving GPU memory. | Optional |
| `decimate_mesh_factor` | number (0-1) | The factor to reduce the number of mesh vertices. A lower value means fewer vertices. | Optional |
| `class_id` | integer | Used for specifying the Class ID in the ground truth output. | **Required** |

!!! warning
    When setting the `place_on_ground` parameter to `true`, ensure you also specify the `floor_object`.

### Dynamic Evaluators

For parameters that can undergo dynamic evaluation, their values can be adjusted for every frame, offering flexibility in simulation. More on this can be found in the [Dynamic Evaluators](../dynamic_evaluators.md) section.

## Example Configuration

```yaml
scene:
  syclops_plugin_object:
    - name: "Tree1"
      models: Example Assets/Tree
      frame_id: "frame_001"
      place_on_ground: true
      floor_object: "Ground"
      max_texture_size: 1024
      decimate_mesh_factor: 0.5
      class_id: 2
```

The configuration places a tree model on the ground, adjusts its texture size and reduces its vertices, also assigning a class ID.