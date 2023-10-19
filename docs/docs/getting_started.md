# Getting Started

## Prerequisites

Necessary Software to install on your machine:

!!! note
    === "Windows"
        - [Miniconda](https://docs.conda.io/en/latest/miniconda.html) - Python 3.9 or higher
        - [Git](https://git-scm.com/downloads)
        - [Powershell](https://docs.microsoft.com/de-de/powershell/scripting/install/installing-powershell?view=powershell-7.2)

    === "Linux"
        - [Miniconda](https://docs.conda.io/en/latest/miniconda.html) - Python 3.9 or higher
        - [Git](https://git-scm.com/downloads)



## Installing

First setup a folder structure like this:

```bash
├───syclops-dev
│   ├───assets
│   └───src
```

```bash
mkdir syclops-dev
cd syclops-dev
mkdir assets
mkdir src
```

Then clone the main [syclops repository](https://github.com/agri-gaia/syclops-pipeline) into the `src` folder checkout to the latest release tag.

```bash
cd src
git clone git@github.com:agri-gaia/syclops-pipeline.git
cd syclops-pipeline
git fetch --tags
syclops_latest_tag=$(git describe --tags $(git rev-list --tags --max-count=1))
git checkout $syclops_latest_tag
```

Create the conda `syclops` environment and activate it:

```bash
conda create --yes --name syclops python=3.9 pip
conda activate syclops
```

To run the setup script, run `setup.py` from the `syclops-dev` folder:

```bash
python src/syclops-pipeline/setup.py
```

This will do the following:

- Clone all necessary repositories into the `src` folder
- Install Python dependencies to a virtual environment
- Download Blender
- Create an environment file for the current os

## Run a job

> To run a **job**, a job file is needed. You can find an example in the `syclops-pipeline/examples` folder.

Bevore running a job, you need to source the environment file.

=== "Windows"
    ```powershell
    . .\env.ps1
    ```
=== "Linux"
    ```py
    . ./env.sh
    ```

Next, the assets have to crawled by the pipeline. This only needs to be done once, or if new assets are added.
```bash
syclops -c
```
Then run the pipeline with the job file as an argument:

```bash
syclops -j src/syclops-pipeline/examples/example_job.syclops.yaml
```

That's all you need to know to render images! 🎉

The rendered data will be in a timestamped folder inside of the `output` folder.
To quickly visuzalize the data, you can use the dataset viewer tool.

!!! info
    Adjust the output path accordingly.

```bash
syclops -da output/2022-09-01_12-00-00
```