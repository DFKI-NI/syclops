# Getting Started

## Prerequisites

Necessary Software to install on your machine:


- Python version 3.9 or higher.

We recommend using a virtual environment to avoid potential package conflicts. Below are instructions for setting up with `virtualenv` or `conda`.

## Installing

=== "virtualenv"
    If you don't have `virtualenv` installed:

    ```bash
    pip install virtualenv
    ```

    To create and activate a new virtual environment named `syclops`:
    
    === "Windows"
        ```bash
        virtualenv syclops_venv
        .\syclops_venv\Scripts\activate
        ```
    === "Linux"
        ```bash
        virtualenv syclops_venv
        source syclops_venv/bin/activate
        ```

=== "conda"
    If you use Anaconda or Miniconda, you can create a new environment:

    ```bash
    conda create --name syclops_venv python=3.9
    conda activate syclops_venv
    ```


### Installing Syclops

Once you have your environment set up and activated:

=== "From PyPI"
    ```bash
    pip install syclops
    ```

=== "From Source"
    To install `Syclops` directly from the source code:

    ```bash
    git clone https://github.com/DFKI-NI/syclops.git
    cd syclops
    pip install .
    ```

    !!! warning
        `pip install . -e` does not work with the current setup.

## Run a job

Next, the assets need to be crawled by the pipeline. This only needs to be done once, or if new assets are added.
```bash
syclops -c
```

> To run a **job**, a job file is needed. You can find an example in the [syclops/\_\_example_assets\_\_](https://github.com/DFKI-NI/syclops/blob/main/syclops/__example_assets__/example_job.syclops.yaml) folder.

To test the installation with the example job file run:
```bash
syclops --example-job
```

To run a specific job, simply pass the path to the job file to the `syclops` command:
```bash
syclops -j path/to/job.syclops.yaml
```

That's all you need to know to render images! 🎉

The rendered data will be in `output/<timestamp>` inside of your specified syclops directory.
To quickly visuzalize the data, you can use the dataset viewer tool.

> Adjust the output path accordingly.

```bash
syclops -da output/2022-09-01_12-00-00
```
