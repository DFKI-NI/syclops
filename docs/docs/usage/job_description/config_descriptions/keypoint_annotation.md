# Keypoint Output Documentation

The Keypoint Output is designed to provide the 2D pixel coordinates of predefined keypoints on 3D objects in the camera space. This output is particularly useful for tasks such as pose estimation, tracking, and analysis of object articulation.

## Keypoint Definition

Keypoints are defined using a Blender [script](https://github.com/DFKI-NI/syclops/blob/main/syclops/utility/keypoint_script.py) that allows users to easily add keypoint information to 3D objects. To use it, open Blender with the model and paste the [script](https://github.com/DFKI-NI/syclops/blob/main/syclops/utility/keypoint_script.py) in the Blender text editor. The script can be used in two ways:

1. The user should create empty objects at the desired keypoint locations relative to the mesh object. Then, select all the empty objects and the mesh object, with the mesh object being the active object. Run the script, and it will add the keypoint information to the mesh object based on the positions of the empty objects. The empty objects will be sorted alphabetically, and their index will be used as the keypoint number.

2. With a single mesh object selected that already has a keypoints attribute: The script will create empty objects at the keypoint positions defined in the mesh object to visualize the keypoint locations.

Here's an example of how the keypoints are stored in the mesh object:

```python
obj["keypoints"] = {
    "0": {"x": -0.5, "y": 1.0, "z": 0.0},
    "1": {"x": 0.5, "y": 1.0, "z": 0.0},
    "2": {"x": 0.0, "y": 1.5, "z": 0.0},
    ...
}
```

Each keypoint is represented by a unique index (based on the alphabetical order of the empty objects) and its 3D coordinates relative to the object's local space.

## Output Format

The keypoint output is saved as a JSON file for each frame, with the following structure:

```json
{
  "instance_id_1": {
    "class_id": 1,
    "0": {
      "x": 100,
      "y": 200
    },
    "1": {
      "x": 150,
      "y": 220
    }
  },
  "instance_id_2": {
    "class_id": 2,
    "0": {
      "x": 300,
      "y": 400
    },
    "1": {
      "x": 350,
      "y": 420
    }
  }
}
```

Each object instance is identified by a unique `instance_id`, which is calculated based on the object's 3D location. The `class_id` represents the semantic class of the object. Each keypoint is then listed with its index and 2D pixel coordinates (`x`, `y`) in the camera space.

## Configuration Parameters

The keypoint output does not require any additional configuration parameters beyond the standard `id` field for uniquely identifying the output.

| Parameter | Type   | Description                                     | Requirement                        |
|-----------|--------|-------------------------------------------------|-----------------------------------|
| `id`      | string | Unique identifier of the keypoint output. | **Required** |

## Example Configuration

```yaml
syclops_output_keypoint:
  - id: "keypoints1"
```

In this example, a keypoint output is configured with the identifier `"keypoints1"`.

## Metadata Output

Along with the keypoint JSON files, a `metadata.yaml` file is generated in the output folder. This file contains metadata about the keypoint output, including the output type, format, description, expected steps, sensor name, and output ID.

## Limitations and Considerations

- Keypoints are only generated if they are visible in the rendered image.
- The accuracy of keypoint locations depends on the precision of their definition in the 3D object space.
- Keypoint outputs are generated per frame, so the number of output files will depend on the total number of frames in the animation.

By leveraging the keypoint output, users can obtain precise 2D locations of predefined keypoints on 3D objects, enabling various downstream tasks that require spatial understanding of object parts and their relationships.