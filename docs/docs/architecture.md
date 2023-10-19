# Syclops Codebase Architecture

Syclops is a multifaceted synthetic data generation tool with its codebase spread across various repositories. The following section provides an overview of the architectural structure of Syclops, helping developers and users understand the interplay between different components.

## Repository Overview
![An overview of how the different repositories work together to create synthetic data in Syclops](img/docs/syclops_overview.png)

| Repository Name | Description |
|:---:|:---:|
| **syclops-pipeline** | Acts as the central repository and connects all other Syclops components. It orchestrates the entire workflow and manages the setup and execution of the pipeline. |
| **syclops-blender** | Contains the core code responsible for creating 3D scenes in Blender. It ensures that the virtual environment is rendered and prepared for data generation. |
| **syclops-plugins-core** | Houses plugins that extend the pipeline's functionality. This includes plugins for Blender scene creation, virtual sensors, and generating sensor outputs. Both interface classes and their basic implementations can be found here. |
| **syclops-postprocessing** | Offers capabilities for altering the generated synthetic data post-creation. It allows users to refine or adjust the outputs based on their requirements. |

### Key Components:
The following is a list of relevant files in each repository:

- **syclops-pipeline**
    - **setup.py**: A central setup script which:
        - Clones other repositories listed in `installation/repos.yml`.
        - Downloads and sets up Blender for 3D environment rendering.
        - Installs required packages in a conda environment.
        - Generates an environment file (`env`) for proper path sourcing.
        - Moves python code from the `src` folder to the `install` directory ensuring that all modules are in the appropriate locations.
    - **pipeline.py**: Contains the code for the syclops [CLI interface](usage/command_line.md). It also orchestrates the preprocessing, postprocessing, and starting of Blender for the synthetic data generation.
    - **preprocesor.py**: Script that gets called before the scene generation. It adjusts the job description and can create additional files that are needed for the scene generation.
- **syclops-blender**
    - **main.py**: Entrypoint script that gets run in Blender with the Blender Python environment.
    - **scene.py**: Contains the code for creating the 3D scene in Blender. It creates the transformation tree, and loads the plugin/sensor instances that are defined in the job file.
- **syclops-plugins-core**
    - **plugins/plugin_interface.py**: Contains the interface class for the plugins. These are the classes that are used to generate objects or environments in the scene.
    - **sensors/sensor_interface.py**: Contains the interface class for the sensors. These are the classes that are used to place virtual sensors in the scene.
    - **sensor_outputs/output_interface.py**: Contains the interface class for the sensor outputs. A sensor output is instanced by a sensor and is responsible for generating the data for that sensor.
- **syclops-postprocessing**
    - **main.py**: Entrypoint script that gets run as a parallel process to the Blender process. It is responsible for postprocessing the generated data.
    - **postprocessing_interface.py**: Contains the interface class for the postprocessing. It defines, how a postprocessing plugin should be structured.
