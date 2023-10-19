# Command Line
To source the environment variables and aliases, run the following command in your terminal:

=== "Windows"
    ```powershell
    . .\env.ps1
    ```
=== "Linux"
    ```bash
    . ./env.sh
    ```

The most important alias is `syclops` which is the main command to use the pipeline.
Following is a list of the command line arguments for `syclops`:

| Argument | Description | Default | Type |
| --- | --- | --- | --- |
| `-j` | Path to the job description file. | None | String |
| `-o` | Path to the output directory. | `./output` | String |
| `-c` | Crawl assets and write a catalog file. | `False` | Boolean |
| `-i` | Install changes from the source folder. Optional: Install only selected repos. | `False` | [Boolean, String] |
| `-p` | Pull repos in the source folder. Optional: Pull only selected repos. | `False` | [Boolean, String] |
| `-da` | Path generated data to view. | `False` | String |
| `-t` | Command to generate thumbnails for the asset browser. | `False` | Boolean |
| `-b` | Start the asset browser. | `False` | Boolean |
| `-log` | Display all log messages in the console. | `False` | Boolean |
| `-d` | Debugging mode. See [Debugging](debugging.md) | `False` | String [scene, blender-code, pipeline-code]