# Camera Plugin Documentation

The Camera Plugin simulates a basic camera sensor, allowing you to configure the optical and digital properties of the camera within your scene. It supports various parameters such as resolution, focal length, exposure, and depth of field, among others.

## Configuration Parameters

The following table describes each configuration parameter for the Camera Plugin:

| Parameter        | Type                                                  | Description                                                                                                        | Requirement  |
| ---------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------ |
| `name`           | string                                                | Unique identifier of the sensor.                                                                                   | **Required** |
| `frame_id`       | string                                                | Transformation tree node the camera attaches to.                                                                   | **Required** |
| `resolution`     | array (2 integers: width x height)                    | Width and height of the camera in pixels.                                                                          | **Required** |
| `focal_length`   | float                                                 | Focal length of the camera in mm.                                                                                  | **Required** |
| `sensor_width`   | float                                                 | Width of the sensor in mm.                                                                                         | **Required** |
| `exposure`       | float                                                 | Exposure offset in stops.                                                                                          | Optional     |
| `gamma`          | float                                                 | Gamma correction applied to the image (1 means no change in gamma).                                                | Optional     |
| `shutter_speed`  | float                                                 | Shutter speed in seconds. Affects the strength of motion blur. If `motion_blur` is enabled, this becomes required. | Conditional  |
| `depth_of_field` | object (contains aperture, autofocus, focus_distance) | Settings for the depth of field of the camera.                                                                     | Optional     |
| `motion_blur`    | object (contains enabled, rolling_shutter)            | Settings for the motion blur of the camera.                                                                        | Optional     |
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

!!! warning
    If `motion_blur` is enabled, `shutter_speed` becomes a required parameter.


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
    outputs:
        Base Plugins/RGB:
            - samples: 256
            id: main_cam_rgb
```

In the example above, a camera named "Main_Camera" is defined with a resolution of 1920x1080 pixels, a focal length of 35mm, and other specific properties. The camera will also utilize motion blur with a rolling shutter effect.
