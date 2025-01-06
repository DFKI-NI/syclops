# Camera Plugin Documentation

The Camera Plugin simulates a basic camera sensor, allowing you to configure the optical and digital properties of the camera within your scene. It supports various parameters such as resolution, lens types (perspective and fisheye), exposure, depth of field, motion blur, and frustum visualization for debugging purposes. Additionally, it outputs the intrinsic and extrinsic camera parameters.

## Configuration Parameters

The following table describes each configuration parameter for the Camera Plugin:

| Parameter        | Type                                                  | Description                                                                                                        | Requirement  |
| ---------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------ |
| `name`           | string                                                | Unique identifier of the sensor.                                                                                   | **Required** |
| `frame_id`       | string                                                | Transformation tree node the camera attaches to.                                                                   | **Required** |
| `resolution`     | array (2 integers: width x height)                    | Width and height of the camera in pixels.                                                                          | **Required** |
| `lens_type`      | string                                                | Type of lens projection (PERSPECTIVE [default], FISHEYE_EQUISOLID, FISHEYE_EQUIDISTANT).                          | Optional     |
| `focal_length`   | float                                                 | Focal length of the camera in mm. Required for PERSPECTIVE and FISHEYE_EQUISOLID.                                  | Conditional  |
| `fisheye_fov`    | float                                                 | Horizontal angular field of view in radians. Required for FISHEYE_EQUIDISTANT and FISHEYE_EQUISOLID.              | Conditional  |
| `sensor_width`   | float                                                 | Width of the sensor in mm.                                                                                         | **Required** |
| `exposure`       | float                                                 | Exposure offset in stops.                                                                                          | Optional     |
| `gamma`          | float                                                 | Gamma correction applied to the image (1 means no change in gamma).                                                | Optional     |
| `shutter_speed`  | float                                                 | Shutter speed in seconds. Affects the strength of motion blur. If `motion_blur` is enabled, this becomes required. | Conditional  |
| `depth_of_field` | object (contains aperture, autofocus, focus_distance) | Settings for the depth of field of the camera.                                                                     | Optional     |
| `motion_blur`    | object (contains enabled, rolling_shutter)            | Settings for the motion blur of the camera.                                                                        | Optional     |
| `frustum`        | object (contains settings for frustum visualization)  | Settings for the camera frustum visualization (for debugging purposes).                                            | Optional     |
| `outputs`        | object                                                | Output configuration, which can include RGB, Pixel Annotation, and Object Positions.                               | **Required** |

### Depth of Field

| Sub-parameter    | Type    | Description                                                               |
| ---------------- | ------- | ------------------------------------------------------------------------- |
| `aperture`       | number  | f-number of the aperture.                                                 |
| `autofocus`      | boolean | Whether the camera should focus on the object in the center of the image. |
| `focus_distance` | number  | Fixed focus distance of the camera in m.                                  |

### Motion Blur

| Sub-parameter     | Type    | Description                                         |
| ----------------- | ------- | --------------------------------------------------- |
| `enabled`         | boolean | Whether motion blur is enabled.                     |
| `rolling_shutter` | object  | Contains parameters for the rolling shutter effect. |

#### Rolling Shutter

| Sub-parameter | Type    | Description                               |
| ------------- | ------- | ----------------------------------------- |
| `enabled`     | boolean | Whether rolling shutter is enabled.       |
| `duration`    | number  | Exposure time of the scanline in seconds. |

### Frustum Visualization

| Sub-parameter | Type    | Description                                                                                |
| ------------- | ------- | ------------------------------------------------------------------------------------------ |
| `enabled`     | boolean | Whether to enable frustum visualization.                                                  |
| `type`        | string  | Type of frustum visualization (e.g., "pyramid").                                          |
| `depth`       | number  | Depth of the frustum in meters.                                                           |
| `color`       | array   | RGB color of the frustum as a list of 3 floats.                                           |
| `transparency`| number  | Transparency value between 0-1.                                                           |
| `wireframe`   | object  | Settings for wireframe rendering mode.                                                    |
| `hide_render` | boolean | Whether to hide the frustum in the final rendered images.                                 |

#### Wireframe Settings

| Sub-parameter | Type    | Description                           |
| ------------- | ------- | --------------------------------------|
| `enabled`     | boolean | Whether to render as wireframe lines. |
| `thickness`   | number  | Thickness of the wireframe lines.     |

### Lens Types and Parameters

The camera supports three types of lens projections:

1. **PERSPECTIVE** (default)
   - Requires `focal_length`
   - Standard perspective projection

2. **FISHEYE_EQUISOLID**
   - Requires both `focal_length` and `fisheye_fov`
   - Follows the equisolid angle projection formula
   - Commonly used in real fisheye lenses

3. **FISHEYE_EQUIDISTANT**
   - Requires `fisheye_fov`
   - Linear mapping between angle and image distance
   - Theoretical fisheye projection

!!! note
    When using fisheye lens types, the frustum visualization is not supported and will be disabled automatically.
    Camera extrinsic parameters are not output when using fisheye lens types as they are not supported.

!!! warning
    If `motion_blur` is enabled, `shutter_speed` becomes a required parameter.

!!! tip
    The frustum visualization is primarily intended for debugging purposes when running Syclops with the `-d scene` flag. This flag opens the scene in Blender and allows you to visualize the frustum of the sensor, which can be useful for sensor placement prototyping.

## Intrinsic Camera Parameters Output

The Camera Plugin outputs the intrinsic camera parameters, which include the camera matrix. The camera matrix is written to a YAML file named `<frame_number>.yaml` in the `<camera_name>/intrinsics` folder for each frame.

### Example Intrinsics Output

```yaml
camera_matrix:
  - [fx, 0, cx]
  - [0, fy, cy] 
  - [0, 0, 1]
```

Where:
- `fx`, `fy`: Focal lengths in pixels
- `cx`, `cy`: Principal point coordinates in pixels

## Extrinsic Camera Parameters Output

The Camera Plugin also outputs the extrinsic camera parameters, which represent the global pose of the camera in the scene. The camera pose is written to a YAML file named `<frame_number>.yaml` in the `<camera_name>/extrinsics` folder for each frame.

### Example Extrinsics Output

```yaml
camera_pose:
  - [r11, r12, r13, tx]
  - [r21, r22, r23, ty]
  - [r31, r32, r33, tz]
  - [0, 0, 0, 1]
```

Where:
- `r11` to `r33`: Rotation matrix elements
- `tx`, `ty`, `tz`: Translation vector elements

## Metadata Output

Along with the intrinsic and extrinsic parameter files, a `metadata.yaml` file is generated in the respective output folders. This file contains metadata about the parameter outputs, including the output type, format, description, expected steps, sensor name, and output ID.

## Example Configuration

```yaml
syclops_sensor_camera:
  - name: Main_Camera
    frame_id: Camera_Node_01
    resolution: [1920, 1080]
    focal_length: 35
    sensor_width: 36
    exposure: 0.5
    gamma: 1.2
    depth_of_field:
      aperture: 2.8
      autofocus: true
    motion_blur:
      enabled: true
      rolling_shutter:
        enabled: true
        duration: 0.001
    frustum:
      enabled: true
      type: pyramid
      depth: 10
      color: [1, 0, 0]
      transparency: 0.5
      wireframe:
        enabled: true
        thickness: 0.1
    outputs:
        syclops_output_rgb:
            - samples: 256
              id: main_cam_rgb
```

In the example above, a camera named "Main_Camera" is defined with a resolution of 1920x1080 pixels, a focal length of 35mm, and other specific properties. The camera will also utilize motion blur with a rolling shutter effect. Additionally, the frustum visualization is enabled, displaying a wireframe pyramid with a depth of 10 meters, colored red, and semi-transparent. The intrinsic and extrinsic camera parameters will be output according to the specified configuration.