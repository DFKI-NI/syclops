# Object Positions Output Documentation

The Object Positions Output provides information about the global position, rotation and scale of all objects within the scene. Each object's details are cataloged with their respective class IDs, their xyz coordinates (in meters) xyz euler angles (in radians) and xyz scale. This information is presented in a JSON format. The structure is the following:
  
  ```json
  {
      "<class_id>": [
        {
          "loc": [x, y, z], // location in meters
          "rot": [x, y, z], // euler in radians
          "scl": [x, y, z]  // scale
        },
        ...
      ]
  }
  ```

## Configuration Parameters

The following table describes each configuration parameter for the Object Positions Output:

| Parameter          | Type      | Description                                                                                                         | Requirement                               |
|--------------------|-----------|---------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| `id`               | string    | Unique identifier of the output.                                                                                    | **Required**                              |
| `debug_breakpoint` | boolean   | Specifies whether to pause and open Blender before rendering. This functionality is available only when scene debugging is active. | **Optional**                          |

!!! note
    For each Object Positions Output configuration, an `id` is mandatory. Ensure the uniqueness of this identifier across different outputs.

## Example Configuration

```yaml
syclops_output_object_positions:
  - id: "obj_pos_1"
    debug_breakpoint: true
```

In the example configuration, the global positions of objects within the scene will be captured with the identifier `obj_pos_1`. Additionally, if the [scene debugging](../../../developement/debugging.md#visually-debug-a-job-file) is active, the scene will break and open in Blender before rendering.

## Metadata Output

Along with the output files, a `metadata.yaml` file is generated in the output folder. This file contains metadata about the keypoint output, including the output type, format, description, expected steps, sensor name, and output ID.
