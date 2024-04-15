# Frequently Asked Questions

Here are some common questions and issues that users may encounter when using Syclops:

## Installation

### Q: I'm having trouble installing Syclops. What should I do?

A: Make sure you have the correct version of Python installed (3.9 or higher) and that you're using a virtual environment to avoid package conflicts. If you're still having issues, please open an issue on the [GitHub repository](https://github.com/DFKI-NI/syclops/issues) with details about your operating system, Python version, and the error messages you're seeing.

## Assets

### Q: How do I add new assets to my project?

A: To add new assets, create an `assets.yaml` file in your project directory that defines the asset library and its assets. Then, run `syclops -c` to crawl the assets and update the catalog. For more information, see the [Assets documentation](./assets/assets.md).

### Q: I'm getting an error message saying an asset file is missing. What should I do?

A: Check that the file paths in your `assets.yaml` file are correct and that the files exist in the specified locations. If you've recently added or moved assets, make sure to run `syclops -c` to update the asset catalog.

## Job Configuration

### Q: My job configuration isn't working as expected. How can I debug it?

A: You can use the `-d` flag to enable debugging mode in Syclops. Use `-d scene` to open the scene in Blender for visual debugging, or `-d blender-code` and `-d pipeline-code` to debug the Blender and pipeline code, respectively. For more information, see the [Debugging documentation](../developement/debugging.md).

### Q: How do I use dynamic evaluators in my job configuration?

A: Dynamic evaluators allow you to randomize parameter values for each frame in your scene. To use them, replace a fixed value in your job configuration with a dynamic evaluator expression, such as `uniform: [0, 1]` for a uniform random value between 0 and 1. For more examples, see the [Dynamic Evaluators documentation](./job_description/dynamic_evaluators.md).

## Rendering

### Q: My renders are taking a long time. How can I speed them up?

A: To speed up rendering, you can try reducing the number of samples per pixel in your sensor configuration, or using a lower resolution for your output images. You can also make sure you're using GPU rendering if you have a compatible graphics card. For more tips, see the [Sensor Configuration documentation](./job_description/config_descriptions/camera.md).

### Q: I'm getting artifacts or noise in my rendered images. What can I do?

A: Increase the number of samples per pixel in your sensor configuration to reduce noise and artifacts. You can also try enabling denoising in your job configuration by setting `denoising_enabled: True` and choosing an appropriate denoising algorithm, such as `OPTIX` or `OPENIMAGEDENOISE`.

## Postprocessing

### Q: How do I create custom postprocessing plugins?

A: To create a custom postprocessing plugin, define a new Python class that inherits from `PostprocessorInterface` and implement the required methods, such as `process_step` and `process_all_steps`. Then, register your plugin in the `pyproject.toml` file under the `[project.entry-points."syclops.postprocessing"]` section. For more details, see the [Postprocessing documentation](/usage/job_description/config_descriptions/postprocessing).

If you have any other questions or issues that aren't covered here, please open an issue on the [GitHub repository](https://github.com/DFKI-NI/syclops/issues) or reach out to the Syclops community for help.