# Pixel Annotation Output Documentation

The Pixel Annotation Output is dedicated to providing various pixel-level annotations of the sensor image. This encompasses a range of annotations from semantic segmentation to the volume of objects.

## Configuration Parameters

The following table describes each configuration parameter for the Pixel Annotation Output:

| Parameter               | Type                                            | Description                                                                                                         | Requirement               |
|-------------------------|-------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|---------------------------|
| **`semantic_segmentation`** | object                                          | Represents the semantic segmentation output where pixels are mapped with the class id value of the object.           | **Optional**              |
|     ↳ `id`              | string                                          | Unique identifier of the output.                                                                                    | **Required** for this annotation type |
|     ↳ `class_id_offset` | boolean                                         | Specifies if custom models can have multiple class ids. Must be set in the model materials.                         | **Optional**              |
| **`instance_segmentation`** | object                                          | Produces an instance segmentation output, tagging each object with a unique id in the image.                        | **Optional**              |
|     ↳ `id`              | string                                          | Unique identifier of the output.                                                                                    | **Required** for this annotation type |
| **`pointcloud`**            | object                                          | Offers 3D coordinates of every pixel in the camera coordinates in meters.                                           | **Optional**              |
|     ↳ `id`              | string                                          | Unique identifier of the output.                                                                                    | **Required** for this annotation type |
| **`depth`**                 | object                                          | Displays the Z Depth of a pixel relative to the camera in meters.                                                   | **Optional**              |
|     ↳ `id`              | string                                          | Unique identifier of the output.                                                                                    | **Required** for this annotation type |
| **`object_volume`**         | object                                          | Shows the volume of objects in cm^3.                                                                                | **Optional**              |
|     ↳ `id`              | string                                          | Unique identifier of the output.                                                                                    | **Required** for this annotation type |
| `debug_breakpoint`      | boolean                                         | Decides if the rendering process should pause and open Blender before proceeding. Only functions with scene debugging active. | **Optional**              |

!!! note
    Ensure that each annotation type, if used, contains a unique `id`. The `id` is imperative for differentiating between various annotations.

## Example Configuration

```yaml
syclops_output_pixel_annotation:
  - semantic_segmentation:
      id: "seg1"
      class_id_offset: true
  - instance_segmentation:
      id: "inst1"
  - pointcloud:
      id: "pc1"
  - depth:
      id: "depth1"
  - debug_breakpoint: true
```

In the provided configuration, a variety of pixel annotations are set up, each with their unique identifiers. Additionally, if the [scene debugging](/developement/debugging/#visually-debug-a-job-file) is active, the scene will break and open in Blender before rendering.