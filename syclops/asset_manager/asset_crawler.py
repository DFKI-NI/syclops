import hashlib
import os
import subprocess
from pathlib import Path

import ruamel.yaml
from syclops.utility import get_site_packages_path

RESET_MD5_HASH = False
ASSET_LIBRARY_PATHS = []
CATALOG_OUTPUT_PATH = ""
MANIFEST_FILE_NAME = "assets.yaml"


class AssetCrawler(object):
    """Crawler searches all subfolders for manifest files and creates a catalog file."""

    def __init__(self, asset_paths: list):
        """Initialize the crawler.

        Args:
            asset_paths (list): List of paths to asset libraries.
        """
        self.asset_paths = asset_paths
        self.asset_catalog: dict = {}
        self.yaml = ruamel.yaml.YAML()
        self.manifest_files = []
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def crawl(self):
        """Crawls all asset paths and creates a catalog file."""
        for path in self.asset_paths:
            print(f"Crawling {path} for {MANIFEST_FILE_NAME} ...")
            library_root_paths = self.crawl_root_paths(path)
            for library_root_path in library_root_paths:
                manifest_files = self._crawl_path(library_root_path)
                print(f"... found {[str(f) for f in manifest_files]}")
                self._add_missing_md5_checksums(manifest_files, library_root_path)
                parsed_manifest_files = self._parse_manifest_files(manifest_files)
                self.manifest_files.extend(manifest_files)
                merged_manifests = self._merge_manifests(
                    parsed_manifest_files,
                    library_root_path,
                )
                self._add_assets_to_catalog(merged_manifests)

    def crawl_root_paths(self, path: str) -> list:
        """Crawls all subfolders for manifest files and checks if they contain library descriptions."""
        root_paths = []
        for root, dirs, files in os.walk(path):
            if MANIFEST_FILE_NAME in files:
                with open(Path(root) / MANIFEST_FILE_NAME, "r") as f:
                    manifest = self.yaml.load(f)
                    if "name" in manifest:
                        root_paths.append(Path(root))

        self._check_nested_root_paths(root_paths)
        return root_paths

    def _check_nested_root_paths(self, root_paths: list):
        # Check for duplicates in root paths
        root_paths = set(root_paths)
        if len(root_paths) != len(root_paths):
            duplicates = root_paths - set(root_paths)
            raise ValueError(
                "Multiple asset library descriptions {0} are in the same folder.".format(
                    duplicates,
                ),
            )
        # Check if path is subpath of another path
        for root_path in root_paths:
            for other_root_path in root_paths:
                if (
                    root_path != other_root_path
                    and root_path in other_root_path.parents
                ):
                    raise ValueError(
                        "Asset library description {} is nested in {}.".format(
                            other_root_path, root_path
                        )
                    )

    def _crawl_path(self, path: Path) -> list:
        manifest_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file == MANIFEST_FILE_NAME:
                    manifest_files.append(Path(root) / file)
        return manifest_files

    def _find_root_path(self, manifest_files: list) -> Path:
        """Finds the manifest file with the global asset description and returns its path."""
        for manifest_file in manifest_files:
            with open(manifest_file, "r") as f:
                manifest = self.yaml.load(f)
                if "name" in manifest:
                    return Path(manifest_file).parent
        raise Exception("Could not find the base manifest file.")

    def _parse_manifest_files(self, manifest_files: list) -> list:
        """Parses all manifest files and returns a list of dictionaries."""
        return [
            self.yaml.load(open(manifest_file, "r")) for manifest_file in manifest_files
        ]

    def _merge_manifests(self, manifest_files: list, root_path: Path) -> dict:
        merged_manifest: dict = {}
        for manifest_file in manifest_files:
            for key, value in manifest_file.items():
                if key in merged_manifest:
                    if key != "assets":
                        raise Exception(
                            "Multiple manifests with unmergable keys: {}".format(key)
                        )
                    merged_manifest[key].update(value)
                else:
                    merged_manifest[key] = value
        merged_manifest["root_path"] = str(root_path.absolute())
        return merged_manifest


    def _add_assets_to_catalog(self, manifest: dict):
        asset_library_name = manifest["name"]
        if asset_library_name in self.asset_catalog:
            print(
                "Warning: Asset library '{}' already exists in catalog. Skipping addition.".format(
                    asset_library_name
                )
            )
            return
        self.asset_catalog[asset_library_name] = manifest

    def check_catalog(self):
        """Checks the asset catalog for missing assets, md5 checksum and duplicate names"""
        for _, asset_library in self.asset_catalog.items():
            self._check_file_md5(asset_library)

    def _check_file_md5(self, asset_library: dict):
        for _, content in asset_library["assets"].items():
            for key, value in content.items():
                if "filepath" in key and "md5" not in key:
                    filepath = Path(value)
                    root_path = Path(asset_library["root_path"])
                    full_path = root_path / filepath
                    if not full_path.exists():
                        raise Exception(
                            "Asset {} does not exist in {}".format(filepath, root_path)
                        )
                    if key + "_md5" in content:
                        if not self._hash_file(full_path) == content[key + "_md5"]:
                            raise Exception(
                                "Asset {} has incorrect md5 checksum.".format(filepath)
                            )
                    else:
                        raise Exception(
                            "Asset {} has no md5 checksum.".format(filepath)
                        )

    def _hash_file(self, filepath: Path) -> str:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _add_missing_md5_checksums(self, manifests: list, root_path: Path):
        for manifest_path in manifests:
            with open(manifest_path, "r") as f:
                manifest = self.yaml.load(f)
            for asset, content in manifest["assets"].items():
                for key, value in content.copy().items():
                    if "filepath" in key and "md5" not in key:
                        filepath = Path(value)
                        full_path = root_path / filepath
                        if not full_path.exists():
                            raise Exception(
                                "Asset {} does not exist in {}".format(
                                    filepath, root_path
                                )
                            )
                        if key + "_md5" not in content or RESET_MD5_HASH:
                            md5_checksum = self._hash_file(full_path)
                            content[key + "_md5"] = md5_checksum
            with open(manifest_path, "w") as f:
                self.yaml.dump(manifest, f)

    def write_catalog(self, catalog_path: str):
        """Writes the asset catalog to a file."""
        with open(catalog_path, "w") as f:
            self.yaml.dump(self.asset_catalog, f)

    def create_thumbnails(self, blender_path: Path):
        thumbnail_generator_path = Path(__file__).parent / "thumbnail_generator.py"

        for manifest_path in self.manifest_files:
            print(f"Generate thumbnails for {manifest_path}")
            subprocess.run(
                [
                    blender_path,
                    Path(__file__).resolve().parent / "studio.blend",
                    "-P",
                    thumbnail_generator_path,
                    "-b",
                    "--",
                    "--asset",
                    manifest_path,
                    "--site-packages-path",
                    get_site_packages_path(),
                ]
            )


if __name__ == "__main__":
    # Create a new asset crawler
    asset_crawler = AssetCrawler(ASSET_LIBRARY_PATHS)
    asset_crawler.crawl()
    asset_crawler.write_catalog(CATALOG_OUTPUT_PATH)
