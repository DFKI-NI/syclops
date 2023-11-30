# Scatter Plugin Documentation

The Scatter Plugin serves the purpose of distributing instances of objects on a ground surface. Various configuration options allow for intricate control over how objects are scattered.

## Configuration Parameters

The following table describes each configuration parameter for the Scatter Plugin:

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `name` | string | Unique identifier for the plugin instance. | **Required** |
| `models` | array or single item | 3D assets intended for scattering on the floor object. | **Required** |
| `floor_object` | string | Specifies the name of the ground surface on which the models are scattered. | **Required** |
| `max_texture_size` | integer | Specifies the texture's maximum allowable pixel size for GPU RAM conservation. | Optional |
| `density_map` | image/texture evaluation | A texture guiding scattering density. The texture is normalized between 0-1 and density is determined by multiplying this with `density_max` at each spatial location. | Optional |
| `decimate_mesh_factor` | number (0-1) | Decimation factor for mesh vertices. Lower values result in fewer vertices. | Optional |
| `density_max` | number evaluation | Defines the maximum number of scattered instances per square meter. | **Required** |
| `distance_min` | number evaluation | Minimum allowable distance between the origins of each scattered instance. | **Required** |
| `scale_standard_deviation` | number evaluation | Standard deviation for the size of scattered instances. | **Required** |
| `seed` | number evaluation | Sets a random seed value for scattering. | **Required** |
| `class_id` | integer | Specifies the Class ID in the ground truth output. | **Required** |
| `align_to_normal` | boolean | Dictates whether the scattered objects should align with the surface's normal. | Optional |
| `clumps` | object | Provides options for creating optional clusters of objects. Further detailed in the sub-table below. | Optional |

### Clumps Configuration

When using the `clumps` parameter, consider the following additional configurations:

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `ratio` | number | Ratio of clumped vs. individual scattered objects. | **Required** |
| `size` | number | Average number of plants or items per clump. | **Required** |
| `size_std` | number | Variance in the number of plants or items within a clump. | **Required** |
| `position_std` | number | Variability in meters of a plant or item's location relative to the clump's center. | **Required** |
| `scale_std` | number | Variability in the size of the plants or items in a clump. | **Required** |

### Dynamic Evaluators

Most parameters, like `density_max` and `seed`, can be dynamically evaluated. This means that their values can be altered for each new frame. For more insights on dynamic evaluators and how to use them, kindly refer to [Dynamic Evaluators](../dynamic_evaluators.md).


## Example Configuration

```yaml
scene:
  syclops_plugin_scatter:
    - name: "Forest"
      models: Example Assets/Trees
      floor_object: "Ground"
      max_texture_size: 2048
      density_max: 5
      distance_min: 0.5
      scale_standard_deviation: 0.1
      seed: 42
      class_id: 3
      align_to_normal: true
      clumps:
        ratio: 0.7
        size: 5
        size_std: 2
        position_std: 0.25
        scale_std: 0.05
```

The above configuration will scatter tree models across the ground surface. These trees will have a mix of clumped and individual placements, with specifics detailed by the `clumps` parameters.