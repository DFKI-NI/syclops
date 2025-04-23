import sys
import zipfile
import tarfile
import platform
from pathlib import Path
from rich.progress import Progress
import requests
import appdirs
from rich.console import Console
from rich.prompt import Prompt
from ruamel import yaml


def download_file(url: str, dest: Path) -> None:
    """
    Download a file from the given URL to the specified destination with rich progress.
    """
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        total_length = int(response.headers.get("content-length", 0))
        task_description = f"[cyan]Downloading {url.split('/')[-1]}...[/cyan]"
        with Progress() as progress:
            task = progress.add_task(task_description, total=total_length)
            with dest.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
                    progress.update(task, advance=len(chunk))


def extract_zip(src: Path, dest: Path) -> None:
    """
    Extract a zip file with rich progress.
    """
    with zipfile.ZipFile(src, "r") as zip_ref:
        total_files = len(zip_ref.namelist())
        task_description = f"[red]Extracting {src.name}...[/red]"
        with Progress() as progress:
            task = progress.add_task(task_description, total=total_files)
            for member in zip_ref.namelist():
                zip_ref.extract(member, dest)
                progress.update(task, advance=1)
    # Rename folder
    extracted_folder = dest / src.stem
    stem_parts = src.stem.split('-')
    if len(stem_parts) > 1:
        extracted_folder.rename(dest / f"blender-{stem_parts[1]}")
    else:
        raise ValueError(f"Unexpected file naming convention: {src.stem}")
    if len(stem_parts) > 1:
        extracted_folder.rename(dest / f"blender-{stem_parts[1]}")
    else:
        raise ValueError(f"Unexpected file name format: {src.stem}")


def extract_tar(src: Path, dest: Path) -> None:
    """
    Extract a tar.xz file with rich progress.
    """
    with tarfile.open(src, "r:xz") as tar_ref:
        total_files = len(tar_ref.getnames())
        task_description = f"[red]Extracting {src.name}...[/red]"
        with Progress() as progress:
            task = progress.add_task(task_description, total=total_files)
            for member in tar_ref:
                tar_ref.extract(member, dest)
                progress.update(task, advance=1)
    # Rename folder
    extracted_folder = dest / src.stem.split(".tar")[0]
    extracted_folder.rename(dest / f"blender-{src.stem.split('-')[1]}")


def install_blender(version: str, install_dir: Path) -> None:
    """
    Check if Blender is installed in the package directory,
    and if not, download the appropriate version for the OS.
    """
    base_url = "https://ftp.halifax.rwth-aachen.de/blender/release/"
    version_major = ".".join(version.split(".")[:-1])

    # Check OS and set download path accordingly
    os_type = platform.system()
    if os_type == "Windows":
        file_name = f"blender-{version}-windows-x64.zip"
        extract_func = extract_zip
    elif os_type == "Linux":
        file_name = f"blender-{version}-linux-x64.tar.xz"
        extract_func = extract_tar
    elif os_type == "Darwin":
        machine = platform.machine()
        if machine == "arm64":
            file_name = f"blender-{version}-macos-arm64.dmg"
        elif machine == "x86_64":
            file_name = f"blender-{version}-macos-x64.dmg"
        else:
            print(f"Unsupported macOS architecture: {machine}")
            sys.exit(1)
        extract_func = None  # macOS .dmg files typically don't require extraction
        print("macOS detected. Please install Blender manually from the downloaded .dmg file.")
        # For macOS, we download but don't extract or expect a specific installation structure.
        # We'll download the file and then exit gracefully after informing the user.
        download_path = f"{base_url}Blender{version_major}/{file_name}"
        dest_file = install_dir / file_name
        print(f"Downloading Blender for macOS ({machine})...")
        download_file(download_path, dest_file)
        print(f"Download complete: {dest_file}")
        print("Please open the .dmg file and drag Blender to your Applications folder.")
        # We return here because the rest of the function assumes extraction and specific folder structure
        return
    else:
        print("Unsupported OS")
        sys.exit(1)

    download_path = f"{base_url}Blender{version_major}/{file_name}"
    dest_file = install_dir / file_name

    # Check if Blender is already installed in the package directory (Skip for macOS as we return earlier)
    if (install_dir / f"blender-{version}").exists():
        print(f"Blender {version} already installed.")
        return

    # Download Blender (Skip for macOS as we return earlier)
    download_file(download_path, dest_file)

    # Extract Blender (Skip for macOS as we return earlier)
    if extract_func:
        extract_func(dest_file, install_dir)

    # Clean up (Skip for macOS as we return earlier)
    dest_file.unlink()


def get_or_create_install_folder(install_folder_path: str = None) -> Path:
    """
    Get the install folder from the config file, or ask the user for a folder.

    Args:
        install_folder_path (str): The path to the install folder, if it exists.

    Returns:
        Path: The path to the install folder.
    """
    config = _load_config()
    install_folder_key = "install_folder"

    def determine_folder():
        if install_folder_path is not None:
            return Path(install_folder_path).resolve()
        return _ask_directory().resolve()

    # If 'install_folder' is not in the config or the saved folder doesn't exist
    if (
        install_folder_key not in config
        or not Path(config[install_folder_key]).exists()
        or install_folder_path is not None
    ):
        install_folder = determine_folder()
        config[install_folder_key] = str(install_folder)
        _write_config(config)
    else:
        install_folder = Path(config[install_folder_key]).resolve()

    # Ensure the folder exists
    install_folder.mkdir(parents=True, exist_ok=True)
    return install_folder


def _load_config() -> dict:
    config_file = _get_or_create_config_file_path()
    if config_file.exists():
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    return {}


def _get_or_create_config_file_path() -> Path:
    app_name = "syclops"
    return Path(appdirs.user_data_dir(app_name)) / "config.yaml"


def _write_config(config: dict):
    config_file = _get_or_create_config_file_path()
    # Create the directory if it doesn't exist
    if not config_file.parent.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.dump(config, f)


def _ask_directory() -> Path:
    console = Console()
    console.print("Please enter a directory for syclops:", style="bold blue")
    directory = Path(Prompt.ask("Directory", default="."))
    console.print(f"You entered: {directory}", style="bold green")
    return directory


if __name__ == "__main__":
    # Example use:
    package_location = Path(__file__).parent
    blender_version = input("Enter the Blender version (e.g., 3.6.1): ")
    install_blender(blender_version, package_location)
