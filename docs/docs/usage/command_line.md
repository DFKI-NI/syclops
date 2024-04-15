# Command Line
To use `Syclops` the virtual environment needs to be activated. This can be done by running the following command in the terminal:

=== "conda"
    ```bash
    conda activate syclops_venv
    ```

=== "virtualenv"    
    ```bash
    # For Windows
    ./syclops_venv/Scripts/activate

    # For Linux
    source syclops_venv/bin/activate
    ```

The most important alias is `syclops` which is the main command to use the pipeline.
Following is a list of the command line arguments for `syclops`:

| Argument | Description | Default | Type |
| --- | --- | --- | --- |
| `-j` | Path to the job description file. | `None` | String |
| `-o` | Path to the output directory. Defaults to <install_folder>/output | `./output` | String |
| `-c` | Crawl assets and write a catalog file. | `False` | Boolean |
| `--example-job` | Run the example job config. | `False` | Boolean |
| `-da` | Path generated data to view. | `False` | String |
| `-t` | Command to generate thumbnails for the asset browser. | `False` | Boolean |
| `-b` | Start the asset browser. | `False` | Boolean |
| `-log` | Display all log messages in the console. | `False` | Boolean |
| `-tv` | Live display of the procedural textures in a job config. | `None` | String |
| `-if` | Path to the install folder. | `None` | String |
| `-d` | Debugging mode. See [Debugging](../developement/debugging.md) | `False` | String [scene, blender-code, pipeline-code]