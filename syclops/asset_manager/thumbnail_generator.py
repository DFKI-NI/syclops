"""
Script that generates thumbnails for assets
blender .\studio.blend -P .\asset_thumbnail_generator.py -b -- --asset asset.yaml
"""
import argparse
import glob
import os
import random
import sys
from os.path import isdir, splitext
from pathlib import Path
from typing import Union, List

import bpy

# Get catalog path from command line
argv = sys.argv
if "--" in sys.argv:
    argv = sys.argv[sys.argv.index("--") + 1 :]

parser = argparse.ArgumentParser(description="Generate thumbnails for an asset.")
parser.add_argument(
    "--asset", type=str, required=True, help="Path to the asset yaml file"
)
parser.add_argument(
    "--debug-scene-creator",
    help="Enable debug mode",
    action="store_true",
    default=False,
)
parser.add_argument(
    "--site-packages-path", help="Path to site-packages"
)


class RevertAfter:
    """Context manager to revert changes after execution"""

    def __init__(self):
        pass

    def __enter__(self):
        bpy.ops.ed.undo_push()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # If no exception was raised, revert changes
        if exc_type is None:
            bpy.ops.ed.undo_push()
            bpy.ops.ed.undo()


def import_assets(
    asset_dict: dict, root_dir: str, path_key: str = "filepath"
) -> List[bpy.types.Object]:
    """Extract filepath from asset and import"""
    root_dir = Path(root_dir)
    obj_path = asset_dict[path_key]
    obj_path = str((root_dir / obj_path).resolve())
    return import_objects(obj_path)


def import_objects(obj_paths: Union[str, list]) -> List[bpy.types.Object]:
    """Import Objects into Blender.
    Args:
        obj_paths (string/list(string)): String of a single file,
            list of multiple files or string of a folder.
    Returns:
        blende object: Imported Blender objects
    """
    obj_paths = [obj_paths] if isinstance(obj_paths, str) else obj_paths
    imported_objs = []
    for obj_path in obj_paths:
        if isdir(obj_path):
            for file in glob.glob(obj_path + "/*"):
                import_file(file, imported_objs)
        else:
            import_file(obj_path, imported_objs)
    return imported_objs


def import_file(obj_path: str, imported_objs: List[bpy.types.Object]):
    """Import a single object file. Can handle multiple formats
    Args:
        obj_path (string): Path to object file (fbx,obj,blend supported)
        imported_objs (list): list of the imported objects
    """
    _, extension = splitext(obj_path)
    prior_objects = list(bpy.context.scene.objects)
    if extension == ".fbx":
        bpy.ops.import_scene.fbx(filepath=obj_path)
    elif extension == ".obj":
        bpy.ops.import_scene.obj(filepath=obj_path)
    elif extension == ".blend":
        loaded_objects = utility.load_from_blend(obj_path, "objects")
        for obj in loaded_objects:
            if obj is not None:
                bpy.context.view_layer.active_layer_collection.collection.objects.link(
                    obj
                )
    new_and_prior_objects = list(bpy.context.scene.objects)
    imported_objs += list(set(new_and_prior_objects) - set(prior_objects))


def calc_bounding_box(obj: bpy.types.Object) -> tuple:
    """Calculate the bounding box of an object
    Args:
        obj (bpy.types.Object): Object to calculate the bounding box of
    Returns:
        tuple: (x,y,z) of the bounding box
    """
    # Apply location rotation and scale

    mb = obj.matrix_basis
    if hasattr(obj.data, "transform"):
        obj.data.transform(mb)
    for c in obj.children:
        c.matrix_local = mb @ c.matrix_local
    obj.matrix_basis.identity()

    # Update scene
    bpy.context.view_layer.update()

    bbox = obj.bound_box
    min_x = min_y = min_z = sys.maxsize
    max_x = max_y = max_z = -sys.maxsize
    for i in range(0, len(bbox)):
        x = bbox[i][0]
        y = bbox[i][1]
        z = bbox[i][2]
        if x < min_x:
            min_x = x
        if x > max_x:
            max_x = x
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
        if z < min_z:
            min_z = z
        if z > max_z:
            max_z = z
    return (min_x, min_y, min_z), (max_x, max_y, max_z)


if __name__ == "__main__":
    args = parser.parse_known_args(argv)[0]

    site_packages_path = Path(args.site_packages_path).resolve()
    print(f"Adding {site_packages_path} to sys.path")
    sys.path.append(str(site_packages_path))

    import debugpy
    import numpy as np
    import ruamel.yaml
    from syclops import utility

    if args.debug_scene_creator:
        debugpy.listen(5678)
        print("Start Debugging")
        debugpy.wait_for_client()  # blocks execution until client is attached

    yaml = ruamel.yaml.YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    asset_path = args.asset
    with open(asset_path, "r") as f:
        assets = yaml.load(f)

    # Render Thumbnail Settings
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.device = "GPU"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = 75

    bpy.context.scene.render.resolution_x = 512
    bpy.context.scene.render.resolution_y = 512

    # Random seed 42
    random.seed(42)

    for asset_name, asset_dict in assets["assets"].items():
        root_dir = str(Path(asset_path).parent.resolve())
        current_dir = Path(os.getcwd())

        if "vertices" not in asset_dict:
            if asset_dict["type"] == "model":
                with RevertAfter():
                    objs = import_assets(asset_dict, root_dir)
                    try:
                        assets["assets"][asset_name]["vertices"] = str(
                            len(objs[0].data.vertices)
                        )
                    except:
                        assets["assets"][asset_name]["vertices"] = "0"
                    with open(asset_path, "w") as f:
                        yaml.dump(assets, f)

        if "height" not in asset_dict:
            if asset_dict["type"] == "model":
                with RevertAfter():
                    objs = import_assets(asset_dict, root_dir)
                    try:
                        bb = calc_bounding_box(objs[0])
                        max_height = bb[1][2] - bb[0][2]
                        assets["assets"][asset_name]["height"] = round(max_height, 3)
                    except:
                        assets["assets"][asset_name]["height"] = "0"
                    with open(asset_path, "w") as f:
                        yaml.dump(assets, f)

        # Skip if already rendered
        if "thumbnail" not in asset_dict:
            if asset_dict["type"] == "model":
                with RevertAfter():
                    objs = import_assets(asset_dict, root_dir)
                    for i in range(int(np.ceil(len(objs)))):
                        if i > 10:
                            break

                        # Hide all objects from render
                        for obj in objs:
                            obj.hide_render = True

                        bb = calc_bounding_box(objs[i])
                        max_val = max(
                            abs(bb[0][0]),
                            abs(bb[1][0]),
                            abs(bb[0][1]),
                            abs(bb[1][1]),
                            abs(bb[1][2]),
                            abs(bb[0][2]),
                        )

                        try:
                            scale_val = (0.7) / max_val
                        except ZeroDivisionError:
                            scale_val = 1

                        scale = objs[i].scale
                        scale *= scale_val
                        objs[i].scale = scale
                        objs[i].hide_render = False

                        # Select objects that will be rendered
                        for obj in bpy.context.scene.objects:
                            obj.select_set(False)
                        for obj in objs:
                            if not (obj.hide_get() or obj.hide_render):
                                obj.select_set(True)
                        focal_length = bpy.data.cameras["Camera"].lens
                        bpy.data.cameras["Camera"].lens *= 1.2
                        bpy.ops.view3d.camera_to_view_selected()
                        bpy.data.cameras["Camera"].lens = focal_length

                        # Current directory
                        output_path = (
                            Path(root_dir)
                            / "thumbnails"
                            / "{}_{}.jpg".format(asset_name, i)
                        )
                        bpy.context.scene.render.filepath = str(output_path)
                        bpy.ops.render.render(write_still=True)
                        objs[i].hide_render = True
                        # Check if thumbnail list exists
                        if "thumbnail" not in assets["assets"][asset_name]:
                            assets["assets"][asset_name]["thumbnail"] = []
                        # Add thumbnail to list
                        assets["assets"][asset_name]["thumbnail"].append(
                            str(Path("thumbnails") / "{}_{}.jpg".format(asset_name, i))
                        )
                        with open(asset_path, "w") as f:
                            yaml.dump(assets, f)

            elif asset_dict["type"] == "pbr_texture":
                with RevertAfter():
                    # Create 1x1m plane at z position 0.2m
                    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.5))
                    plane = bpy.context.active_object

                    # Set material
                    mat = bpy.data.materials.new("pbr")
                    plane.data.materials.append(mat)
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links
                    principled = nodes["Principled BSDF"]

                    # Specularity to 0.3
                    principled.inputs["Specular"].default_value = 0.3

                    # Add image textures
                    diffuse_texture = nodes.new("ShaderNodeTexImage")
                    diffuse_texture.image = bpy.data.images.load(
                        str(Path(root_dir) / asset_dict["diffuse_filepath"])
                    )
                    displacement_texture = nodes.new("ShaderNodeTexImage")
                    displacement_texture.image = bpy.data.images.load(
                        str(Path(root_dir) / asset_dict["displacement_filepath"])
                    )
                    displacement_texture.image.colorspace_settings.name = "Non-Color"
                    normal_texture = nodes.new("ShaderNodeTexImage")
                    normal_texture.image = bpy.data.images.load(
                        str(Path(root_dir) / asset_dict["normal_filepath"])
                    )
                    normal_texture.image.colorspace_settings.name = "Non-Color"
                    roughness_texture = nodes.new("ShaderNodeTexImage")
                    roughness_texture.image = bpy.data.images.load(
                        str(Path(root_dir) / asset_dict["roughness_filepath"])
                    )
                    roughness_texture.image.colorspace_settings.name = "Non-Color"

                    # Add normal map and displacement node
                    normal_map = nodes.new("ShaderNodeNormalMap")
                    normal_map.space = "TANGENT"
                    displacement_map = nodes.new("ShaderNodeDisplacement")
                    displacement_map.inputs[2].default_value = asset_dict[
                        "texture_displacement_scale"
                    ]

                    # Link textures to principled shader
                    links.new(
                        diffuse_texture.outputs[0], principled.inputs["Base Color"]
                    )
                    links.new(
                        displacement_texture.outputs[0], displacement_map.inputs[0]
                    )
                    links.new(normal_texture.outputs[0], normal_map.inputs[0])
                    links.new(
                        roughness_texture.outputs[0], principled.inputs["Roughness"]
                    )

                    # Link normal map to principled shader
                    links.new(normal_map.outputs[0], principled.inputs["Normal"])

                    # Link displacement map to material displacement output
                    links.new(
                        displacement_map.outputs[0], nodes["Material Output"].inputs[2]
                    )

                    bpy.context.scene.cycles.feature_set = "EXPERIMENTAL"

                    # Add adaptive subdivide modifier to plane
                    bpy.ops.object.modifier_add(type="SUBSURF")
                    bpy.context.object.modifiers[
                        "Subdivision"
                    ].subdivision_type = "SIMPLE"
                    bpy.context.object.cycles.use_adaptive_subdivision = True
                    bpy.context.object.active_material.cycles.displacement_method = (
                        "DISPLACEMENT"
                    )

                    # Current directory
                    output_path = (
                        Path(root_dir) / "thumbnails" / "{}_0.jpg".format(asset_name)
                    )
                    bpy.context.scene.render.filepath = str(output_path)
                    bpy.ops.render.render(write_still=True)
                    # Check if thumbnail list exists
                    if "thumbnail" not in assets["assets"][asset_name]:
                        assets["assets"][asset_name]["thumbnail"] = []
                    # Add thumbnail to list
                    assets["assets"][asset_name]["thumbnail"].append(
                        str(Path("thumbnails") / "{}_0.jpg".format(asset_name))
                    )
                    with open(asset_path, "w") as f:
                        yaml.dump(assets, f)
            elif asset_dict["type"] == "texture":
                with RevertAfter():
                    # Blender load image
                    texture_image = bpy.data.images.load(
                        str(Path(root_dir) / asset_dict["filepath"])
                    )
                    # Resize image to 1024x1024
                    texture_image.scale(1024, 1024)
                    texture_image.update()
