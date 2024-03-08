# Postprocessing

Postprocessing operations are applied to the generated data after the scene rendering is complete. One common postprocessing task is generating bounding box annotations from the instance and semantic segmentation outputs.

## Bounding Box Generation

The `syclops_postprocessing_bounding_boxes` plugin is used to generate bounding box annotations in the YOLO format from the instance and semantic segmentation images.

```yaml
postprocessing:
  syclops_postprocessing_bounding_boxes:
    - type: "YOLO" 
      classes_to_skip: [0, 1] # List of class ids to exclude from bounding boxes
      id: yolo_bound_boxes
      sources: ["main_cam_instance", "main_cam_semantic"] # Names of instance and semantic outputs
```

The key parameters are:

- `type`: The output format, in this case "YOLO" for the YOLO bounding box format.
- `classes_to_skip`: A list of class ids to exclude from the bounding box generation.
- `id`: A unique identifier for this postprocessing output.
- `sources`: The names of the instance and semantic segmentation outputs to use as sources.

### Algorithm 

The bounding box generation algorithm works as follows:

1. Load the instance and semantic segmentation images for the current frame.
2. Create a mask of pixels to skip based on the `classes_to_skip` list.
3. Find all unique remaining instance ids after applying the skip mask.
4. For each instance id:
    - Find the class ids associated with that instance, excluding low pixel count classes.
    - If `multiple_bb_per_instance` is enabled, generate one bounding box per class id.
    - Otherwise, use the main class id and generate one bounding box.
5. Write the bounding boxes in YOLO format to an output file.

The bounding box coordinates are calculated from the pixel extents of each instance mask for the given class id(s).

### Output

The bounding box output is generated as a text file in the YOLO format for each frame, located in the `<sensor_name>_annotations/bounding_box/` folder. Each line represents one bounding box:

```
<class_id> <x_center> <y_center> <width> <height>
```

The coordinates are normalized between 0-1 based on the image width/height.