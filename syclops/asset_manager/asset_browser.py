import json
import os
import shutil
import subprocess
import webbrowser
from http.server import SimpleHTTPRequestHandler, test
from pathlib import Path

import yaml
from syclops.utility import get_or_create_install_folder

# Paths
BASE_PATH = Path(__file__).resolve().parent
BROWSER_THUMBNAIL_PATH = BASE_PATH / "asset_browser" / "src" / "thumbnails"
BROWSER_CATALOG_PATH = BASE_PATH / "asset_browser" / "src" / "catalog.json"


def read_and_process_catalog(install_folder: Path):
    """Read the catalog.yaml, process thumbnails and write to catalog.json."""
    catalog_path = install_folder / "asset_catalog.yaml"
    with catalog_path.open("r") as stream:
        catalog = yaml.safe_load(stream)

        for library_name, library_dict in catalog.items():
            root_path = Path(library_dict["root_path"])
            thumbnails_folder = root_path / "thumbnails"

            if thumbnails_folder.exists():
                for file in thumbnails_folder.iterdir():
                    target_path = BROWSER_THUMBNAIL_PATH / f"{library_name}_{file.name}"
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(file, target_path)

    with BROWSER_CATALOG_PATH.open("w") as outfile:
        json.dump(catalog, outfile)


def setup_and_launch_server():
    """Set up and launches the asset browser server."""
    asset_browser_path = BASE_PATH / "asset_browser"
    os.chdir(asset_browser_path)

    subprocess.check_call("npm install", shell=True)
    subprocess.check_call("npm run build", shell=True)

    build_path = asset_browser_path / "build"
    os.chdir(build_path)

    webbrowser.open("http://localhost:8000/")
    test(SimpleHTTPRequestHandler)


if __name__ == "__main__":
    install_folder = get_or_create_install_folder(None)
    read_and_process_catalog(install_folder)
    setup_and_launch_server()
