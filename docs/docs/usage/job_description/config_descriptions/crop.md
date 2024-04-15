# Crop Plugin Documentation

The Crop Plugin scatters 3D models on a floor object in a grid pattern to simulate crop rows. 

## Configuration Parameters

The following table describes each configuration parameter for the Crop Plugin:

| Parameter | Type | Description | Requirement |
|-----------|------|-------------|-------------|
| `name` | string | Unique identifier of the plugin | **Required** |
| `models` | array or single item | 3D assets to scatter. | **Required** | 
| `floor_object` | string | Name of the floor object to scatter on. | **Required** |
| `max_texture_size` | integer | Maximum texture size in pixel. Will reduce the texture to save GPU RAM. | Optional |
| `density_map` | image/texture evaluation | Texture that alters the density. It is normalized to 0-1. | Optional |
| `decimate_mesh_factor` | number (0-1) | Factor between 0-1 that decimates the number of vertices of the mesh. Lower means less vertices. | Optional |
| `scale_standard_deviation` | number evaluation | Scale variance of the scattered objects. | **Required** |
| `class_id` | integer | Class ID for ground truth output. | **Required** |
| `crop_angle` | number evaluation | Global orientation of the row direction in degrees. | **Required** |
| `row_distance` | number evaluation | Distance between rows in meters. | **Required** |
| `row_standard_deviation` | number evaluation | Standard deviation of the row distance in meters. | **Required** |
| `plant_distance` | number evaluation | Intra row distance between plants in meters. | **Required** |
| `plant_standard_deviation` | number evaluation | Standard deviation of the intra row distance in meters. | **Required** |

### Dynamic Evaluators

Most parameters, like `scale_standard_deviation`, `crop_angle` etc., can be dynamically evaluated. This means that their values can be altered for each new frame. For more insights on dynamic evaluators and how to use them, kindly refer to [Dynamic Evaluators](../dynamic_evaluators.md).

## Example Configuration

```yaml
scene:  
  syclops_plugin_crop:
    - name: "Corn Crop"
      models: Example Assets/Corn
      floor_object: "Ground"
      max_texture_size: 2048
      scale_standard_deviation: 0.1
      class_id: 2
      crop_angle: 45
      row_distance: 1
      row_standard_deviation: 0.1
      plant_distance: 0.3  
      plant_standard_deviation: 0.05
```

The above configuration will scatter corn models across the ground surface in a grid pattern resembling crop rows. The rows will be oriented at a 45 degree angle, with 1 meter spacing between rows and 30 cm spacing between plants. The row and plant spacings will vary according to the specified standard deviations.


