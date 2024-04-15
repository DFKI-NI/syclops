# RGB Output Plugin Documentation

The RGB Output Plugin captures the RGB color output of the camera sensor and delivers photorealistic images. The generated output can range in quality, based on the number of samples per pixel. Lower samples per pixel will result in a grainy image, while higher samples per pixel will result in a smoother image.

## Configuration Parameters

The following table describes each configuration parameter for the RGB Output Plugin:

| Parameter | Type | Description | Requirement |
| ----------- | ------ | -------------- | --------------- |
| `id` | string | A unique identifier for the output. | **Required** |
| `samples` | integer | Specifies the render quality of the image. A higher number indicates better quality with more samples per pixel. | **Required** |
| `debug_breakpoint` | boolean | Determines if the scene should break and open in Blender before rendering. This feature is functional only if scene debugging is active. | Optional |

### Important Notes
- The `id` is essential to distinguish between different RGB outputs, especially when handling multiple configurations.
  
- While `samples` directly impact the image quality, increasing the number might also increase the rendering time.

- Using the `debug_breakpoint` in combination with active scene debugging can be invaluable during the development process, as it allows for real-time modifications within Blender before final rendering.

## Example Configuration

Below is a sample configuration for the RGB Output Plugin:

```yaml
syclops_output_rgb:
  - id: MainView
    samples: 200
    debug_breakpoint: true
```

In this configuration, the RGB output with the identifier "MainView" will have a quality of 200 samples per pixel. Additionally, if the [scene debugging](../../../developement/debugging.md#visually-debug-a-job-file) is active, the scene will break and open in Blender before rendering.

## Metadata Output

Along with the output files, a `metadata.yaml` file is generated in the output folder. This file contains metadata about the keypoint output, including the output type, format, description, expected steps, sensor name, and output ID.
