# Define a job

The entire pipeline is controlled and configured by a job. A job is a YAML file that defines the pipeline and its steps.

## Job structure

Each job can be divided into the following sections:

* **general**: General configuration that apply to Blender and the current hardware.
* **transformations**: Contains the transformation tree of objects and sensors in the scene.
* **scene**: Describes how the virtual environment should be created.
* **sensor**: Configuration of individual sensors and their corresponding outputs.
* **postprocessing** - [*optional]*: Operations that are applied to the generated data after creation.
* **textures** - [*optional]*: Dynamically generated textures that can be used in the scene.
* **global_evaluators**: Defines global evaluators that can be referenced by multiple plugins or sensors.

=== "general"

    General settings that configure Blender and the used hardware.

    **Example**:
    ```yaml
    steps: 1 # Number of steps to render
    seeds:
      numpy: 42 
      cycles: 42
    render_device: "GPU" # GPU or CPU
    render_hardware: "CUDA" # CUDA or OPTIX
    denoising_enabled: False
    denoising_algorithm: "OPTIX" # OPTIX or OPENIMAGEDENOISE
    ```
    !!! warning
        Setting **CUDA** or **OPTIX** on an unsupported GPU will result in an error. Only Nvidia RTX GPUs support **OPTIX**.
        To be safe, set the denoising_algorithm to **OPENIMAGEDENOISE**.

=== "transformations"

    Most 3D objects and sensors are positioned in the scene using a transformation tree. It is similar to a robot's kinematic tree. Each node in the tree has a unique name and can have multiple children. The transformation of a node is defined by its location and rotation.
    Objects are then later on linked to a specific node by their name.

    === "Structure"

        ```yaml title="Basic transformations structure"
        transformations:
            <name_of_node>:
                location: [x, y, z] # Location of the transformation in meters
                rotation: [x, y, z] # Rotation of the transformation in radians
                children: # Children of the transformation node
                    <name_of_child_node>:
                        location: [x, y, z] # Location of the transformation in meters
                        rotation: [x, y, z] # Rotation of the transformation in radians
                        children: # Children of the transformation node
                            ...
        ```

        Optionally, **velocities** can be defined for a node. This is only useful for dynamic sensor effects like motion blur. The pose is not effected or updated by the velocity.
        ```yaml title="Transformation node with velocities"
        <name_of_node>:
            location: [x, y, z] # Location of the transformation in meters
            rotation: [x, y, z] # Rotation of the transformation in radians
            velocities:
                translation: [x, y, z] # Translation velocity in meters per second
                rotation: [x, y, z] # Rotation velocity in radians per second
        ```
    === "Example"

        ```yaml title="Basic transformation tree example"
        transformations:
          map: # ID of a transformation
            location: [0, 0, 0] # Location of the transformation
            rotation: [0, 0, 0] # Rotation of the transformation in radians
            children:   # Children of the transformation node
              camera_link:
                location: [-20,0,2]
                rotation: [0.785398, 0, 0]
        ```

    !!! tip
        To alter the pose of a node, you can use the **dynamic evaluators**. See [Dynamic Evaluators](dynamic_evaluators.md) for more information.


=== "scene"

    In this section, all elements of the virtual environment are defined. This includes the objects, lights, materials, and textures.
    For this, plugins are used that have some specific functionality to alter the scene. Each plugin has its own configuration options.
    The general structure of a scene is as follows:

    === "Structure"
        ```yaml title="Basic scene structure"
        scene:
            <plugin_name>: # Name of the plugin
                - <plugin_configuration> # Plugin specific configuration
                - <plugin_configuration>
                - ...
            <plugin_name>:
                - <plugin_configuration>
                - ...
        ```

    === "Example"
        ```yaml title="Basic scene example"
        scene:
        syclops_plugin_ground: # Plugin that creates a ground plane
            - name: "Ground"
              size: 50 # Size of the ground rectangle in meters
              texture: Example Assets/Muddy Dry Ground # Texture of the ground
              class_id: 1 # Class ID of the ground

        syclops_plugin_environment: # Plugin that creates a backdrop and environment lighting
            - type: hdri
              environment_image: Example Assets/Sunflower Field
        ```

    !!! tip
        Most parameters of a plugin configuration can be dynamically altered in each new frame with **dynamic evaluators**. See [Dynamic Evaluators](dynamic_evaluators.md) for more information.


=== "sensor"

    Here, all sensors and their corresponding outputs are defined. Each sensor has its own configuration options.
    The general structure of a sensor is as follows:

    === "Structure"
        ```yaml title="Basic sensor structure"
        scene:
            <sensor_name>: # Name of the sensor
                - <sensor_configuration> # Sensor specific configuration
                - <sensor_configuration>
                - ...
            <sensor_name>:
                - <sensor_configuration>
                - ...
        ```
    === "Example"

        ```yaml title="Basic scene example"
        sensor:
            syclops_sensor_camera: # Name of the sensor plugin
                - name: "main_camera"
                frame_id: "camera_link" # Name of the transformation node
                resolution: [1280, 960] # Resolution of the sensor in pixels
                focal_length: 65 # Focal length of the camera in mm
                sensor_width: 35 # Sensor width of the camera in mm
                exposure: 0.0 # Exposure (stops) shift of camera
                gamma: 1.0 # Gamma correction applied to the image
                outputs:
                    syclops_output_rgb:
                        - samples: 256
                            id: main_cam_rgb
                    syclops_output_object_positions:
                        - id: main_cam_object_positions
                    syclops_output_pixel_annotation:
                        - semantic_segmentation:
                            id: main_cam_semantic
                          instance_segmentation:
                            id: main_cam_instance
                          pointcloud:
                            id: main_cam_pointcloud
                          depth:
                            id: main_cam_depth
                          object_volume:
                            id: main_cam_object_volume
        ```
    Each sensor is linked to a node of the transformation tree to define its pose. The most import attribute of a sensor configuration is its **outputs**.
    It contains which data the sensor should generate.

    !!! tip
        Most parameters of a plugin configuration can be dynamically altered in each new frame with **dynamic evaluators**. See [Dynamic Evaluators](dynamic_evaluators.md) for more information.



=== "postprocessing"
  
      Postprocessing operations are applied to the generated data after the scene generation. This can be used to refine or adjust the outputs based on the requirements.
      The general structure of a postprocessing operation is as follows:
  
    === "Structure"
        ```yaml title="Basic postprocessing structure"
        postprocessing:
            <postprocessing_name>: # Name of the postprocessing operation
                - <postprocessing_configuration> # Postprocessing specific configuration
                - <postprocessing_configuration>
                - ...
            <postprocessing_name>:
                - <postprocessing_configuration>
                - ...
        ```  
    === "Example"
  
        ```yaml title="Basic postprocessing example"
        postprocessing:
        syclops_postprocessing_bounding_boxes:
            - type: "YOLO"
              classes_to_skip: [0, 1]
              id: yolo_bound_boxes
              sources: ["main_cam_instance", "main_cam_semantic"]
        ```

=== "textures"

    Textures are dynamically generated based on instructions in the job file during preprocessing. They can be used in the scene to add more variation to the generated data.
    A genereated texture can be referenced in the scene by its ID like this: `Preprocessed Assets/<texture_id>`
    The general structure of a texture is as follows:

    === "Structure"
        ```yaml title="Basic texture structure"
        textures:
            <texture_id>: # ID of the texture
                config: # Configuration of the texture
                    <texture_configuration>
                    <texture_configuration>
                    ...
                ops: # Sequental operations that are applied to the texture
                    - <texture_operation>
                    - <texture_operation>
                    - ...

            <texture_id>:
                config:
                    <texture_configuration>
                    ...
                ops:
                    - <texture_operation>
                    - ...
        ```

    === "Example"

        ```yaml title="Basic texture example"
        textures:
        perlin_noise_tex_1:
            config:
            image_size: [512, 512]
            bit_depth: 16
            seed: 3
            num_textures: 3
            ops:
            - perlin:
                res: 8
                octaves: 4
        ```
    </details>

=== "global_evaluators"

    This section defines global evaluators that can be referenced by multiple plugins or sensor. These evaluators are evaluated once per frame and ensure that the same random value is used for all plugins/sensors within a single frame. This is useful for multiple cameras that should have the same random exposure value every frame.

    !!! tip
        See [Dynamic Evaluators](dynamic_evaluators.md) for more information.

    **Example**:
    ```yaml
    global_evaluators:
      gamma:
        uniform: [0.8, 1.2]
      exposure:
        normal: [0, 1]
    ```
