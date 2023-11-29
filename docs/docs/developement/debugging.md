# Debugging
A variety a different debugging methods exist for syclops. They consist of either visually debugging a generated scene or IDE debugging of the python code.

## 🐝 Visually Debug a Job File
To better understand, how a scene looks inside of Blender, the `-d scene` flag can be used to break the pipeline at a certain point and open the Blender GUI. 
```bash
syclops -c -j src/syclops-pipeline/examples/example_job.yaml -d scene
```
The breakpoint is set inside the job file for a sensor output. The pipeline will break befor the rendering of that output occurs and cannot continue afterwards.

In order to add a breakpoint, add the following attribute to a sensor output:
```yaml
debug_breakpoint: True
```
Example of this is given in the `example_job.syclops.yaml` file ([link](https://github.com/agri-gaia/syclops-pipeline/blob/e727e558084d460977c0a6091eb2bcdfb2a40ff2/examples/example_job.yaml#L98)). Blender will open right before the RGB image is rendered.
!!! note
    Only one breakpoint can be set per job file. Other outputs before the breakpoint will be rendered, but the pipeline will stop after the breakpoint.

## 🐜 Code Debugging
Either the pipeline code or the Blender code can be debugged. It is strongly recommended to use VSCode for debugging, but other IDEs may work as well.

To debug the code, add the `-d pipeline-code` or `-d blender-code` flag to the syclops command. Syclops will wait for a debugger to attach to the process on port 5678.
> Breakpoints have to be set in the code inside the install folder, since the src folder is not used for execution.


=== "VSCode"

    !!! note
        To attach VSCode to the process and start debugging, add the following configuration to the `launch.json` file and press F5.

    ```json
    {
        "version": "0.2.0",
        "configurations": [
            {
            "name": "Syclops: Attach",
            "type": "python",
            "request": "attach",
            "connect": {
              "host": "localhost",
              "port": 5678
                }
            }
        ]
    }
    ```
=== "PyCharm"

    1. Open your project in PyCharm.
    2. Click on the **Run** menu and select **Edit Configurations...**
    3. In the left-hand menu, click on the **+** button and select **Python Remote Debug** from the dropdown menu.
    4. In the **Configuration** tab, enter a name for your configuration (e.g. ```Syclops: Attach```).
    5. In the **Debugger** tab, ensure that the **Localhost** checkbox is selected under **Address**.
    6. Enter **5678** as the port number in the **Port** field.
    7. Click **Apply** and then **OK** to save the configuration.

