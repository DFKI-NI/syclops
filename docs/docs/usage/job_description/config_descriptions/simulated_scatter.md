# Simulated Scatter Plugin Documentation

The Simulated Scatter Plugin scatters 3D assets on a floor object and simulates physics to drop them realistically on the surface.

## Configuration Parameters  

The following table describes each configuration parameter for the Simulated Scatter Plugin:

| Parameter | Type | Description | Requirement |
|-----------|------|-------------|-------------|
| `name` | string | Unique identifier of the plugin | **Required** |
| `models` | array or single item | 3D assets to scatter. | **Required** |
| `floor_object` | string | Name of the floor object to scatter on. | **Required** |
| `max_texture_size` | integer | Maximum texture size in pixels. Will reduce the texture to save GPU RAM. | Optional |  
| `decimate_mesh_factor` | number (0-1) | Factor between 0-1 that decimates the number of vertices of the mesh. Lower means less vertices. | Optional |
| `density` | number | Density of objects per square meter. | **Required** |
| `density_texture` | image/texture evaluation | Texture that alters the density per pixel. Needs to be a single channel image that is normalized to 0-1. | Optional |
| `scale_standard_deviation` | number | Standard deviation of the scale randomization. | **Required** | 
| `convex_decomposition_quality` | integer (1-100) | Quality setting for the convex decomposition. Higher means more accurate but slower. | **Required** |
| `simulation_steps` | integer | Number of simulation steps to run. | **Required** |

### Dynamic Evaluators

Parameters like `density_texture` and `scale_standard_deviation` can be dynamically evaluated. This means that their values can be altered for each new frame. For more insights on dynamic evaluators and how to use them, kindly refer to [Dynamic Evaluators](../dynamic_evaluators.md).

## Example Configuration

```yaml
scene:
  syclops_plugin_simulated_scatter:  
    - name: "Rock Scatter"
      models: Example Assets/Rocks
      floor_object: "Ground" 
      max_texture_size: 2048
      density: 5
      scale_standard_deviation: 0.3
      convex_decomposition_quality: 90
      simulation_steps: 100
```

The above configuration will scatter rock models across the ground surface. The rocks will be dropped from above and settle into physically realistic positions using a convex decomposition simulation. The simulation will run for 100 steps to allow the rocks to come to rest.