import glob
import hashlib
import inspect
import logging
import pickle
import sys
from importlib import util
from os.path import isdir, splitext
from pathlib import Path
from typing import List, Type, Union, Tuple

import bmesh
import bpy
import numpy as np

import pkg_resources


def load_plugins():
    entry_points = [
        "syclops.plugins",
        "syclops.sensors",
        "syclops.outputs",
        "syclops.postprocessing",
    ]
    plugins = {}
    for group in entry_points:
        for entry_point in pkg_resources.iter_entry_points(group):
            plugins[entry_point.name] = entry_point.load()

    return plugins


def abs_path(rel_path: Union[str, list]) -> Union[str, list]:
    """Convert a relative to an absolute file path.

    Args:
        rel_path (str, List(string)): Relative path or list of relative paths.

    Returns:
        Absolute path or list of absolute paths.
    """
    if isinstance(rel_path, str):
        parent_path = Path(inspect.stack()[1].filename).parent
        out_path = str(parent_path / rel_path)
    else:
        out_path = []
        for path in rel_path:
            parent_path = Path(inspect.stack()[1].filename).parent
            out_path.append(str(parent_path / path))
    return out_path


def absolute_path_to_dot_path(path: Path) -> str:
    """Convert absolute path to dot path.

    Args:
        path (Path): Absolute path

    Returns:
        str: Dot path
    """
    return str(path).replace("\\", ".")


def load_spec_and_module(module_name: str, root_path: Path, asset_path: str):
    """Load module from file path.

    Args:
        module_name (str): Name of the module
        root_path (Path): Root path of the module
        asset_path (str): Path to the module

    Returns:
        module: Loaded module
    """
    module_filepath = root_path / Path(asset_path)
    spec = util.spec_from_file_location(module_name, module_filepath)
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def get_module_classes(module) -> List[Type]:
    """Get all classes from a module.

    Args:
        module (module): Module to search

    Returns:
        List[Type]: List of classes
    """
    return [
        obj
        for _, obj in inspect.getmembers(module)
        if inspect.isclass(obj) and obj.__module__ == module.__name__
    ]


def load_module(module_name: str) -> object:
    """Load module from catalog.

    Args:
        module_name (str): Name of the module

    Returns:
        object: Loaded module

    Raises:
        ValueError: If module does not contain exactly one class
    """
    root_path, asset_path = get_asset_path(module_name, "filepath")
    module = load_spec_and_module(module_name, root_path, asset_path)

    members = get_module_classes(module)
    if len(members) != 1:
        raise ValueError(
            "Exactly 1 class in module {0} expected but {1} found".format(
                module_name,
                len(members),
            ),
        )

    return members[0]


def create_module_instances(config: dict) -> list:
    """Create module instances from config.

    Args:
        config (dict): Config of the module

    Returns:
        list: List of module instances
    """
    instances = []
    modules = load_plugins()
    for module_name, module_list in config.items():
        for module_instance in module_list:
            instance = modules[module_name](module_instance)
            instances.append(instance)
    return instances


def split_asset_name(asset_name: str) -> Tuple[str, str]:
    """Split asset name into a library name and asset name.

    Args:
        asset_name (str): Name of the asset

    Returns:
        tuple[str, str]: Library name and asset name
    """
    library = asset_name.split("/")[0]
    asset = asset_name.split("/")[1]
    return library, asset


def get_asset_path(
    asset_name: str,
    path_key: str = "filepath",
) -> Tuple[Path, Union[str, list]]:
    """Get asset path from catalog.

    Args:
        asset_name (str): Name of the asset
        path_key (str, optional): Key of the path in the catalog. Defaults to "filepath".

    Returns:
        tuple[Path, Union[str, List]]: Root path and asset path
    """
    asset = get_asset(asset_name)
    if asset is not None:
        root_path = Path(get_lib_path(asset_name))
        asset_path = asset[path_key]
    else:
        logging.info(f"Asset {asset_name} not part of catalog")
        asset_path = Path(asset_name)
        root_path = asset_path.parent
        asset_path = asset_path.name
    return root_path, asset_path


def get_asset(asset_name: str) -> dict:
    """Get asset from catalog.

    Args:
        asset_name (str): Name of the asset

    Returns:
        dict: Asset
    """
    catalog_string = bpy.data.scenes["Scene"]["catalog"]
    catalog = pickle.loads(bytes(catalog_string, "latin1"))

    library, asset = split_asset_name(asset_name)
    if library in catalog and asset in catalog[library]["assets"]:
        return catalog[library]["assets"][asset]


def import_assets(
    asset_name: Union[str, list],
    path_key: str = "filepath",
) -> List[bpy.types.Object]:
    """Extract filepath from asset and import.

    Args:
        asset_name (str, list): Name of the asset
        path_key (str, optional): Key of the path in the catalog. Defaults to "filepath".

    Returns:
        list[bpy.types.Object]: Imported Blender objects
    """
    assets = [asset_name] if isinstance(asset_name, str) else asset_name
    obj_paths = []
    for asset in assets:
        root_dir, obj_path = get_asset_path(asset, path_key)
        obj_paths.append(str((root_dir / obj_path).resolve()))
    return import_objects(obj_paths)


def remove_unused_objects() -> None:
    """Remove all dangling data from Blender."""
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def create_mesh_hash(obj: bpy.types.Object) -> str:
    """Create a hash of the mesh vertices.

    Args:
        obj (bpy.types.Object): Blender object

    Returns:
        str: Hash of the mesh vertices
    """
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        verts = np.array([vert.co[:] for vert in bm.verts])
        if verts.shape[0] <= 4:
            # Ignore small meshes
            return None
    except:
        return None
    verts_bytes = verts.astype(np.float16).tobytes()
    verts_hash = hashlib.sha224(verts_bytes).hexdigest()
    obj["mesh_hash"] = verts_hash
    bm.free()
    return verts_hash


def link_duplicate_objs(obj_list: List[bpy.types.Object]) -> None:
    """Find duplicate meshes and link them to save memory.

    Args:
        obj_list (list[bpy.types.Object]): List of Blender objects
    """
    obj_hashes = {
        obj["mesh_hash"]: obj for obj in bpy.data.objects if "mesh_hash" in obj
    }
    mesh_hashs = {create_mesh_hash(obj): obj for obj in obj_list}
    dup_hashs = set(mesh_hashs.keys()).intersection(obj_hashes.keys())
    for dup_hash in dup_hashs:
        mesh_hashs[dup_hash].data = obj_hashes[dup_hash].data


def import_objects(obj_paths: Union[str, list]) -> List[bpy.types.Object]:
    """Import Objects into Blender.

    Args:
        obj_paths (Union[str, list]): Path to object file or list of paths

    Returns:
        list[bpy.types.Object]: Imported Blender objects
    """
    obj_paths = [obj_paths] if isinstance(obj_paths, str) else obj_paths
    imported_objs = []
    for obj_path in obj_paths:
        if isdir(obj_path):
            for file in glob.glob("{0}/*".format(obj_path)):
                import_file(file, imported_objs)
        else:
            import_file(obj_path, imported_objs)
    link_duplicate_objs(imported_objs)
    remove_unused_objects()
    return imported_objs


def _import_fbx(obj_path: str):
    bpy.ops.import_scene.fbx(filepath=obj_path)


def _import_obj(obj_path: str):
    bpy.ops.import_scene.obj(filepath=obj_path)


def _import_blend(obj_path: str):
    loaded_objs = []
    with bpy.data.libraries.load(obj_path, link=False) as (data_from, data_to):
        data_to.objects = data_from.objects
    loaded_objs.extend(data_to.objects)
    for obj in loaded_objs:
        if obj:
            collection = bpy.context.view_layer.active_layer_collection.collection
            collection.objects.link(obj)


def import_file(obj_path: str, imported_objs: List[bpy.types.Object]):
    """Import a single object file.

    Currently supports .fbx, .obj, and .blend files.

    Args:
        obj_path (str): Path to object file
        imported_objs (list[bpy.types.Object]): List of imported objects

    Raises:
        ValueError: If file extension is not supported
    """
    extension = splitext(obj_path)[1]
    prior_objects = list(bpy.context.scene.objects)

    # Use a dictionary for function dispatch
    import_dispatch = {
        ".fbx": _import_fbx,
        ".obj": _import_obj,
        ".blend": _import_blend,
    }

    try:
        import_func = import_dispatch[extension]
        import_func(obj_path)
    except KeyError:
        raise ValueError(f"Unsupported file extension: {extension}")

    new_objects = set(bpy.context.scene.objects) - set(prior_objects)
    imported_objs.extend(new_objects)


def get_lib_path(asset_name: str) -> str:
    """Get library path from catalog"""
    catalog_string = bpy.data.scenes["Scene"]["catalog"]
    catalog = pickle.loads(bytes(catalog_string, "latin1"))

    library, _ = split_asset_name(asset_name)
    return catalog[library]["root_path"]
