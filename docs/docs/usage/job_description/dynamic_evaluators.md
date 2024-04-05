# Dynamic Evaluators

An important part of a synthetic dataset is variety. This increases the domain size and hopefully encapsulates the domain of the real dataset.
In syclops, this is achieved by using dynamic evaluators that replace attributes in the job configuration, telling the pipeline which values and how to change them for each new image.

A common randomization is the pose of the camera. The following example shows how this can be achieved.

```yaml title="Fixed camera pose"
camera_node:
  location: [1, 0, 0] # Location fixed to [1, 0, 0]
  rotation: [0, 0, 0] # Rotation fixed to [0, 0, 0]
```

```yaml title="Random camera pose"
camera_node:
  location:
    # Location starts at [-5, 0, 0] and moves 0.5 units in x direction per step
    linear: [[-5, 0, 0], [0.5, 0, 0]]
  rotation:
    # Rotation is normally distributed around [0.785398, 0, 0] with a standard deviation of [0.05, 0.05, 0.05]
    normal: [[0.785398, 0, 0], [0.05, 0.05, 0.05]] 
```

The attribute values were replaced with dynamic evaluators (```linear```, ```normal```) which change the values for each new image.
Most attributes can be randomized in this way, but some are fixed and cannot be changed.

## List of Dynamic Evaluators

The following table lists all dynamic evaluators and their parameters.

| Name | Parameters | Description |
| --- | --- | --- |
| linear | ```[<start>, <step>]``` | Linearly increases the value by ```step``` for each new image. |
| normal | ```[<mean>, <std>]``` | Samples a value from a normal distribution with the given mean and standard deviation. |
| uniform | ```[<min>, <max>]``` | Samples a value from a uniform distribution with the given minimum and maximum. |
| step | ```[<step1>, <step2>, ...]``` | Samples a value from a list of steps in the given order. |
| random_selection | ```[<step1>, <step2>, ...]``` | Samples a value from a list of steps in a random order. |
| selection_asset | ```{library: <library_name>, type: <type>} ``` | Randomly picks an asset from the given library and type. |
| selection_wildcard | ```{library: <library_name>, wildcard: <wildcard_pattern>}``` | Randomly selects an asset from a library that matches the given wildcard pattern. |


## Referencing Global Evaluators

In addition to the dynamic evaluators that are specific to each attribute, you can also reference global evaluators defined in the `global_evaluators` section of the job configuration. Global evaluators are evaluated once per frame and ensure that the same random value is used for all sensors within a single frame.

To reference a global evaluator, use the syntax `$global.<evaluator_name>`. For example:

```yaml
sensor:
  syclops_sensor_camera:
    - name: "main_camera"
      gamma: $global.gamma
      # ...
    - name: "secondary_camera"
      gamma: $global.gamma
      # ...
```

In this example, both the `main_camera` and `secondary_camera` will use the same random value for `gamma` in each frame, as defined in the `global_evaluators` section.