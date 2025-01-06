import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

import debugpy
import yaml
from syclops.preprocessing.preprocessor import preprocess
from syclops.utility import (
    install_blender,
    ProgressTracker,
    dataset_viewer,
    texture_viewer,
    get_or_create_install_folder,
    get_site_packages_path,
    get_module_path,
)
from syclops.asset_manager.asset_crawler import AssetCrawler
import sys
from rich.console import Console
import pkg_resources


BLENDER_VERSION = "3.6.1"

parser = argparse.ArgumentParser()
parser.add_argument(
    "-j",
    "--job-description",
    help="Path to job description file",
)
parser.add_argument(
    "--example-job",
    help="Use example job description file",
    action="store_true",
)
parser.add_argument(
    "--test-job",
    help="Run test job for an integration test",
    action="store_true",
)
parser.add_argument(
    "-log",
    "--show-logging",
    help="Display the logging messages",
    action="store_true",
)
parser.add_argument(
    "-o",
    "--output-path",
    help="Output path of generated files. Defaults to <install_folder>/output",
    default=None,
)
parser.add_argument(
    "-d",
    "--debug",
    help="Debug mode. Available options: 'code', 'scene'",
    default=None,
    choices=["pipeline-code", "blender-code", "scene"],
)
parser.add_argument(
    "-b",
    "--asset_browser",
    help="Start Asset Browser",
    action="store_true",
)
parser.add_argument(
    "-da",
    "--dataset_path",
    help="Path of dataset to look at",
    default=None,
)
parser.add_argument(
    "-c",
    "--crawl-assets",
    help="Crawl assets",
    action="store_true",
)
parser.add_argument(
    "-t",
    "--generate_thumbnails",
    help="Render thumbnails for all assets",
    action="store_true",
)

parser.add_argument(
    "-tv",
    "--texture_viewer",
    help="Live view of textures in the job config",
)

parser.add_argument(
    "-if",
    "--install_folder",
    help="Path to install folder",
    default=None,
)


def _run_subprocess(args, cwd=None, env=None, execution_info="Command"):
    process_result = subprocess.run(args, cwd=cwd, env=env)
    if process_result.returncode != 0:
        raise RuntimeError(
            f"{execution_info} failed with error code {process_result.returncode}",
        )


def _crawl_assets(install_folder: Path, generate_thumbnails: bool = False):
    print("Crawling assets...")

    asset_catalog_path = install_folder / "asset_catalog.yaml"
    asset_paths_path = install_folder / "asset_paths.yaml"
    if not asset_paths_path.exists():
        with open(asset_paths_path, "w") as f:
            yaml.dump({"asset_paths": []}, f)

    # Read asset paths
    with open(asset_paths_path, "r") as f:
        asset_paths = yaml.load(f, Loader=yaml.FullLoader)["asset_paths"]
    # Convert relative paths to absolute paths
    asset_paths = [str(install_folder / path) for path in asset_paths]

    package_path = Path(__file__).parent.parent
    asset_paths.append(str(package_path))

    asset_crawler = AssetCrawler(asset_paths)
    asset_crawler.crawl()
    asset_crawler.write_catalog(asset_catalog_path)
    if generate_thumbnails:
        blender_path = install_folder / f"blender-{BLENDER_VERSION}" / "blender"
        asset_crawler.create_thumbnails(blender_path)
    _build_schema(install_folder)
    print("Assets crawled")


def available_plugins():
    entry_points = [
        "syclops.plugins",
        "syclops.sensors",
        "syclops.outputs",
        "syclops.postprocessing",
    ]
    plugins = {}
    for group in entry_points:
        plugins[group] = [
            (entry_point.name, entry_point.module_name)
            for entry_point in pkg_resources.iter_entry_points(group)
        ]
    return plugins


def _build_schema(intall_folder: Path):
    print("Building schema...")
    source_path = Path(sys.modules["syclops"].__file__).parent
    schema_path = intall_folder / "schema.yaml"
    asset_catalog_path = intall_folder / "asset_catalog.yaml"
    avl_plugins = available_plugins()
    if not asset_catalog_path.exists():
        print("Asset catalog does not exist. Please crawl assets first.")
        return
    with open(asset_catalog_path, "r") as f:
        asset_catalog = yaml.load(f, Loader=yaml.FullLoader)
    # Load base schema
    base_schema_path = source_path / "schema" / "base_schema.yaml"
    with open(base_schema_path, "r") as f:
        base_schema = yaml.load(f, Loader=yaml.FullLoader)
    for lib, lib_dict in asset_catalog.items():
        for asset, asset_dict in lib_dict["assets"].items():
            asset_type = asset_dict["type"]
            if asset_type == "model":
                if "asset_models" not in base_schema["definitions"]:
                    base_schema["definitions"]["asset_models"] = {
                        "type": "string",
                        "enum": [],
                    }
                base_schema["definitions"]["asset_models"]["enum"].append(
                    f"{lib}/{asset}"
                )
    for group, plugins in avl_plugins.items():
        for plugin in plugins:
            module_name = plugin[1].split(":")[0]
            plugin_name = module_name.split(".")[-1]
            plugin_path = get_module_path(module_name)
            plugin_schema_path = (
                plugin_path.parent / "schema" / f"{plugin_name}.schema.yaml"
            )
            if plugin_schema_path.exists():
                with open(plugin_schema_path, "r") as f:
                    schema = yaml.load(f, Loader=yaml.FullLoader)
                if group == "syclops.plugins":
                    schema = {plugin[0]: schema}
                    base_schema["properties"]["scene"]["properties"].update(schema)
                elif group == "syclops.sensors":
                    schema = {plugin[0]: schema}
                    base_schema["properties"]["sensor"]["properties"].update(schema)
                elif group == "syclops.outputs":
                    base_def = base_schema.setdefault("definitions", {})
                    base_def[plugin[0]] = schema
    with open(schema_path, "w") as f:
        yaml.dump(base_schema, f)
    print("Schema built")


def _configure_output_path(output_folder: Path) -> Path:
    # Create output folder with current date and time
    now = datetime.now()
    sequence_path = now.strftime("%Y_%m_%d_%H_%M_%S")
    output_path = output_folder / sequence_path
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def _wait_for_process(process, poll_interval=0.1):
    if process:
        while process.poll() is None:
            time.sleep(poll_interval)


def _wait_for_debugger():
    debugpy.listen(("localhost", 5678))
    print("Waiting for debugger attach")
    debugpy.wait_for_client()
    print("Debugger attached")


def _run_syclops_job(args, install_folder: Path, job_description: Path):
    output_path = (_configure_output_path(Path(args.output_path).absolute())
                   if args.output_path
                   else _configure_output_path(install_folder / "output"))

    job_filepath = job_description
    asset_catalog_filepath = install_folder / "asset_catalog.yaml"
    schema_catalog_filepath = install_folder / "schema.yaml"

    job_filepath, asset_catalog_filepath = preprocess(
        job_filepath,
        asset_catalog_filepath,
        schema_catalog_filepath,
        output_path,
    )

    blender_logs = open(output_path / "blender.log", "w")
    blender_path = install_folder / f"blender-{BLENDER_VERSION}" / "blender"
    blender_entry_point = get_module_path("syclops.blender.main")
    postprocessor_path = get_module_path("syclops.postprocessing.main")
    cmd_blender = [
        blender_path,
        "-o",
        str(output_path.absolute()),
        "-P",
        blender_entry_point,
        "-b",
        "--",
    ]
    cmd_postprocessor = [
        postprocessor_path,
        "--output-path",
        str(output_path),
    ]
    cmd_syclops = [
        "--config",
        job_filepath,
        "--catalog",
        asset_catalog_filepath,
        "--site-packages-path",
        get_site_packages_path(),
    ]

    if args.debug == "blender-code":
        cmd_blender.append("--debug-scene-creator")

    elif args.debug == "scene":
        # Remove -b flag from cmd_blender
        cmd_blender.remove("-b")

    # Run Postprocessing
    process_postprocessor = subprocess.Popen(
        [sys.executable] + cmd_postprocessor + cmd_syclops[:-2]
    )

    # Run Blender pipeline
    if not args.show_logging:
        with ProgressTracker(output_path) as tracker:
            subprocess.run(
                cmd_blender + cmd_syclops, stdout=blender_logs, stderr=blender_logs
            )
            if tracker.check_errors():
                process_postprocessor.terminate()
                raise Exception("Syclops Blender failed")
            _wait_for_process(process_postprocessor)
    else:
        subprocess.run(cmd_blender + cmd_syclops)
        _wait_for_process(process_postprocessor)


def _asset_browser():
    print("Starting Asset Browser")
    venv_path = sys.executable
    asset_browser_path = get_module_path("syclops.asset_manager.asset_browser")
    _run_subprocess([venv_path, asset_browser_path], execution_info="Asset browser")


def _ensure_catalog_exists(install_folder: Path):
    asset_catalog_path = install_folder / "asset_catalog.yaml"
    if not asset_catalog_path.exists():
        _crawl_assets(install_folder)


def main():
    args = parser.parse_args()

    install_folder = get_or_create_install_folder(args.install_folder)
    install_blender(BLENDER_VERSION, install_folder)
    _ensure_catalog_exists(install_folder)
    console = Console()
    console.print(f"Syclops folder: {install_folder}", style="bold green")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.debug == "pipeline-code":
        _wait_for_debugger()

    if args.crawl_assets:
        if args.generate_thumbnails:
            _crawl_assets(install_folder, generate_thumbnails=True)
        else:
            _crawl_assets(install_folder)

    if args.job_description:
        _run_syclops_job(args, install_folder, Path(args.job_description))

    elif args.example_job:
        job_filepath = (
            get_module_path("syclops").parent
            / "__example_assets__"
            / "example_job.syclops.yaml"
        )
        _run_syclops_job(args, install_folder, job_filepath)

    elif args.test_job:
        job_filepath = (
            get_module_path("syclops").parent
            / "__example_assets__"
            / "test_job.syclops.yaml"
        )
        _run_syclops_job(args, install_folder, job_filepath)

    elif args.texture_viewer:
        texture_viewer(args)

    elif args.asset_browser:
        _asset_browser()

    elif args.dataset_path:
        dataset_viewer(args)


if __name__ == "__main__":
    main()
