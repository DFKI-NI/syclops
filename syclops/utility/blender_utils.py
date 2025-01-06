import logging
import pickle
import uuid
from pathlib import Path
from typing import Union, List

import bmesh
import bpy
import coacd
import numpy as np
from mathutils import Matrix
from . import sampling_utils as su


def apply_transform(
    obj: bpy.types.Object,
    use_location: bool = False,
    use_rotation: bool = False,
    use_scale: bool = False,
):
    """Apply the object's transformation to its data and children.

    Args:
        obj: Object to apply the transformation to.
        use_location: Whether to apply the location transformation.
        use_rotation: Whether to apply the rotation transformation.
        use_scale: Whether to apply the scale transformation.
    """

    # Decompose the object matrix basis into its components.
    loc, _, scale = obj.matrix_basis.decompose()

    # Create identity matrix
    identity = Matrix()

    # Determine matrices based on flags
    translation_matrix = Matrix.Translation(loc) if use_location else identity
    rotation_matrix = (
        obj.matrix_basis.to_3x3().normalized().to_4x4() if use_rotation else identity
    )
    scaling_matrix = Matrix.Diagonal(scale).to_4x4() if use_scale else identity

    # Compute the final transformation matrix.
    final_matrix = translation_matrix @ rotation_matrix @ scaling_matrix

    # Apply the transformation to the object's data if applicable.
    if hasattr(obj.data, "transform"):
        obj.data.transform(final_matrix)

    # Apply the transformation to all child objects.
    for child in obj.children:
        child.matrix_local = final_matrix @ child.matrix_local

    # Update the object's own transformation.
    obj.matrix_basis = final_matrix


def apply_modifiers(target_object: bpy.types.Object) -> None:
    """
    Apply all modifiers to an object.

    Args:
        target_object: Object to which the modifiers are to be applied.
    """
    context = bpy.context.copy()
    context["object"] = target_object

    for modifier in target_object.modifiers:
        try:
            context["modifier"] = modifier
        except RuntimeError:
            info_msg = "Error applying {0} to {1}, removing it instead.".format(
                modifier.name,
                target_object.name,
            )
            logging.info(info_msg)
            target_object.modifiers.remove(modifier)
        else:
            try:
                bpy.ops.object.modifier_apply(context, modifier=modifier.name)
            except RuntimeError:
                info_msg = "Error applying {0} to {1}, removing it instead.".format(
                    modifier.name,
                    target_object.name,
                )
                logging.info(info_msg)
                target_object.modifiers.remove(modifier)

    # Clean up remaining modifiers
    for modifier in target_object.modifiers:
        target_object.modifiers.remove(modifier)


def clear_scene() -> None:
    """Clear the scene of all objects."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def set_seeds(seeds: dict) -> None:
    """Set the random seeds for the scene.

    Args:
        seeds: Dictionary containing the seeds for the scene.
    """
    np.random.seed(seeds["numpy"])
    bpy.context.scene.cycles.seed = seeds["cycles"]


def get_job_conf() -> dict:
    """Get the job configuration from the scene.

    Returns:
        dict: Job configuration.
    """
    job_string = bpy.data.scenes["Scene"]["job_description"]
    return pickle.loads(bytes(job_string, "latin1"))


def append_output_path(path: Union[str, Path], set_blend_path: bool = True) -> Path:
    """Append a path to the current output path.

    Args:
        path (str, Path): Path to append.
        set_blend_path (bool, optional): Whether to set the appended path as the new output path. Defaults to True.

    Returns:
        Path: The new output path.
    """
    base_path = Path(bpy.context.scene.render.filepath)
    base_path = base_path.parent if base_path.is_file() else base_path
    if set_blend_path:
        bpy.context.scene.render.filepath = str(base_path / path)
    return base_path / path


def configure_render():
    """Set Blender rendering settings.

    Raises:
        TypeError: If the render device or hardware is not supported.
    """
    job_description = get_job_conf()

    scene = bpy.context.scene
    addons = bpy.context.preferences.addons
    scene.render.engine = "CYCLES"
    try:
        scene.cycles.device = job_description["render_device"]
    except TypeError as error:
        logging.error(
            'Could not set render device to {0}. Try "GPU" or "CPU"'.format(
                job_description["render_device"],
            ),
        )
        raise error
    try:
        addons["cycles"].preferences.compute_device_type = job_description[
            "render_hardware"
        ]
    except TypeError as error:
        logging.error(
            "Could not set compute device type to {0}. Try a different hardware.".format(
                job_description["render_hardware"],
            ),
        )
        raise error
    addons["cycles"].preferences.refresh_devices()


def render_visibility(obj: bpy.types.Object) -> bool:
    """Return the visibility of the object in the scene.

    Args:
        obj: Object to check visibility of.

    Returns:
        bool: Whether the object is visible in the scene.
    """
    return not (
        bpy.data.objects[obj.name].users_collection[0].hide_render or obj.hide_render
    )


def create_collection(name: str) -> bpy.types.Collection:
    """Create or return a collection with the given name.

    Args:
        name (str): Name of the collection.

    Returns:
        bpy.types.Collection: The collection.
    """
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        scene_collection = bpy.context.scene.collection
        scene_collection.children.link(collection)
    return collection


def set_active_collection(collection: bpy.types.Collection):
    """Activate collection.

    Args:
        collection (bpy.types.Collection): Collection to set active.
    """
    layer_collection = bpy.context.view_layer.layer_collection.children[collection.name]
    bpy.context.view_layer.active_layer_collection = layer_collection


def filter_objects(filter_attribute: str, filter_value: str) -> list[bpy.types.Object]:
    """Filter objects based on a custom attribute.

    Args:
        filter_attribute (str): Name of the custom attribute to filter by.
        filter_value (str): Value of the custom attribute to filter by.

    Returns:
        list: List of objects matching the filter.
    """
    filtered_objs = []
    for obj in bpy.data.objects:
        if obj.get(filter_attribute) == filter_value:
            filtered_objs.append(obj)
    return filtered_objs


def load_img_as_array(path: str) -> np.ndarray:
    """Load image as numpy array.

    Args:
        path (str): Path to image

    Returns:
        np.ndarray: Image as numpy array
    """
    out_data = bpy.data.images.load(path)
    width, height = out_data.size
    img = np.array(out_data.pixels[:])
    img.resize((height, width, out_data.channels))
    return np.flip(img, 0)


def load_image(path: str) -> bpy.types.Image:
    """Load image from path.

    Checks if an image with the same path is already loaded and returns it if so.

    Args:
        path (str): Path to image.

    Returns:
        bpy.types.Image: Image.
    """
    for image in bpy.data.images:
        if image.get("PATH") == str(path):
            return image

    loaded_img = bpy.data.images.load(str(path))
    loaded_img["PATH"] = str(path)
    return loaded_img


class ObjPointer(object):
    """Class to store pointers of blender objects. This prevents reference issues."""

    def __init__(self, obj: bpy.types.Object):
        """Create a pointer to a blender object.

        Args:
            obj (bpy.types.Object): Object to create pointer to.

        Raises:
            TypeError: If the object is not of a supported type.
        """
        if isinstance(obj, bpy.types.Object):
            self.type = "OBJECT"
        elif isinstance(obj, bpy.types.Collection):
            self.type = "COLLECTION"
        else:
            err_msg = "Object {0} is type {1} and not supported in ObjPointer".format(
                obj,
                type(obj),
            )
            logging.error(err_msg)
            raise TypeError(err_msg)
        self.uuid = self.write_uuid_to_obj(obj)

    def write_uuid_to_obj(
        self, obj: Union[bpy.types.Object, bpy.types.Collection]
    ) -> str:
        """Generate uuid and store in objs attributes.

        Args:
            obj (Union[bpy.types.Object, bpy.types.Collection]): Object to store uuid in.

        Returns:
            str: UUID of object.
        """
        if self.type == "OBJECT":
            if "UUID" in obj:
                return obj["UUID"]
            ob_id = str(uuid.uuid4())
            obj["UUID"] = ob_id
        elif self.type == "COLLECTION":
            ob_id = obj.name
        return ob_id

    def get(self) -> Union[bpy.types.Object, bpy.types.Collection]:
        """Get object from uuid.

        Returns:
            Union[bpy.types.Object, bpy.types.Collection]: Object with uuid.

        Raises:
            ValueError: If object with uuid is not found.
        """
        if self.type == "OBJECT":
            for obj in bpy.data.objects:
                if obj.get("UUID") == self.uuid:
                    return obj
        elif self.type == "COLLECTION":
            for collection in bpy.data.collections:
                if collection.name == self.uuid:
                    return collection
        err_msg = "Object with UUID {0} not found".format(self.uuid)
        logging.error(err_msg)
        raise ValueError(err_msg)


class RevertAfter(object):
    """Context manager to revert changes after execution."""

    def __enter__(self):
        """Save the current state of the scene."""
        bpy.ops.ed.undo_push()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Revert changes if no exception was raised.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        # If no exception was raised, revert changes
        if exc_type is None:
            bpy.ops.ed.undo_push()
            bpy.ops.ed.undo()


def _get_bounding_box(tmp_obj):
    min_x, min_y, min_z = tmp_obj.bound_box[0]
    max_x, max_y, max_z = tmp_obj.bound_box[6]
    return max_x - min_x, max_y - min_y, max_z - min_z


def _scale_obj(tmp_obj, width, height, depth):
    # Catch division by zero
    if width == 0:
        width = 1
    if height == 0:
        height = 1
    if depth == 0:
        depth = 1
    scale_x, scale_y, scale_z = 1.0 / width, 1.0 / height, 1.0 / depth

    tmp_obj.scale = (scale_x, scale_y, scale_z)
    apply_transform(tmp_obj, use_scale=True)
    # Apply all modifiers
    apply_modifiers(tmp_obj)


def _extract_bm(tmp_obj):
    # Check if the object data is already a BMesh
    if isinstance(tmp_obj.data, bmesh.types.BMesh):
        bm = tmp_obj.data
    else:
        # Create a BMesh from the mesh data
        bm = bmesh.new()
        bm.from_mesh(tmp_obj.data)

    # Triangulate the BMesh
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    # Extract vertices and faces from the triangulated BMesh
    vertices = np.array([v.co for v in bm.verts])
    faces = np.array([[v.index for v in f.verts] for f in bm.faces])
    # Cleanup
    if not isinstance(tmp_obj.data, bmesh.types.BMesh):
        bm.free()
    bpy.data.objects.remove(tmp_obj, do_unlink=True)
    return vertices, faces


def convex_decomposition(
    obj_pointer: ObjPointer,
    conv_hull_collection_pointer: ObjPointer,
    quality: float = 90,
    max_hull_vertices: int = 100,
) -> List[bpy.types.Object]:
    """Decompose an object into convex hulls for physics simulation.

    Args:
        obj_pointer (ObjPointer): Pointer to object to decompose.
        conv_hull_collection_pointer (ObjPointer): Pointer to collection to store convex hulls in.
        quality (float, optional): Quality of the convex decomposition. Defaults to 90.
        max_hull_vertices (int, optional): Maximum number of vertices in a convex hull. Defaults to 256.
    Returns:
        list[bpy.types.Object]: List of convex hulls.
    """
    obj = obj_pointer.get()
    tmp_obj = duplicate_object(obj, actions=False)
    # Calculate the bounding box
    width, height, depth = _get_bounding_box(tmp_obj)

    # Calculate the scale factors for each axis
    _scale_obj(tmp_obj, width, height, depth)
    vertices, faces = _extract_bm(tmp_obj)

    coacd_mesh = coacd.Mesh(vertices, faces)

    # Run the convex decomposition
    coacd_result = run_coacd(quality, coacd_mesh)

    convex_hulls = []
    for i, convex_hull in enumerate(coacd_result):
        # Create a new mesh
        mesh = bpy.data.meshes.new(f"{obj.name}_convex_{i}")
        # Create a new object
        convex_obj = bpy.data.objects.new(f"{obj.name}_convex_{i}", mesh)

        # Link to active collection
        conv_hull_collection_pointer.get().objects.link(convex_obj)

        # Create the mesh data
        mesh.from_pydata(convex_hull[0], [], convex_hull[1])

        # Num vertices of mesh
        num_vertices = len(mesh.vertices)
        if num_vertices > max_hull_vertices:
            decimate_factor = max_hull_vertices / num_vertices

            # Decimate the mesh if it has too many vertices
            decimate_mesh(convex_obj, decimate_factor)


        # Update the mesh and object
        mesh.update()
        convex_obj.select_set(True)
        bpy.context.view_layer.objects.active = convex_obj
        convex_obj.select_set(False)

        # Scale the convex object back to its original scale
        convex_obj.scale = (width, height, depth)
        apply_transform(convex_obj, use_scale=True)
        convex_obj.location += obj.location
        convex_obj["PARENT_UUID"] = obj_pointer.uuid
        convex_obj.scale = obj.scale
        convex_hulls.append(convex_obj)

    return convex_hulls


class DisjointSet:
    def __init__(self):
        self.parent = {}

    def find(self, item):
        if item not in self.parent:
            self.parent[item] = item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, item1, item2):
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 != root2:
            self.parent[root1] = root2

    def get_clusters(self):
        clusters = {}
        for item in self.parent:
            root = self.find(item)
            if root not in clusters:
                clusters[root] = set()
            clusters[root].add(item)
        return list(clusters.values())

    def find_cluster(self, item):
        if item not in self.parent:
            return None  # Item not present in any cluster

        root = self.find(item)
        cluster = set()
        for key in self.parent:
            if self.find(key) == root:
                cluster.add(key)
        return cluster


def run_coacd(quality: float, coacd_mesh: coacd.Mesh) -> list:
    """Run the COACD algorithm on a mesh with default parameters.

    Args:
        quality (float): Quality of the convex decomposition
        coacd_mesh (coacd.Mesh): Mesh to decompose

    Returns:
        list: List of convex hulls
    """
    return coacd.run_coacd(
        coacd_mesh,
        threshold=-0.0099 * quality + 1,
        max_convex_hull=-1,
        preprocess_resolution=20,
        resolution=1000,
    )


def resize_textures(obj: bpy.types.Object, max_size: int):
    """Resize all textures linked to an object to a maximum size while maintaining aspect ratio.

    Args:
        obj (bpy.types.Object): Object to resize textures of.
        max_size (int): Maximum size of textures.
    """
    materials = {
        slot.material
        for slot in obj.material_slots
        if slot.material and slot.material.use_nodes
    }
    texture_nodes = [
        node
        for mat in materials
        for node in mat.node_tree.nodes
        if node.type == "TEX_IMAGE"
    ]
    for node in texture_nodes:
        if node.image:
            longest_side = max(node.image.size[0], node.image.size[1])
            if longest_side > max_size:
                scale_factor = max_size / longest_side
                width = int(node.image.size[0] * scale_factor)
                height = int(node.image.size[1] * scale_factor)
                node.image.scale(width, height)
                node.image.update()


def decimate_mesh(obj: bpy.types.Object, percent: float):
    """Reduce mesh complexity by decimating it.

    Args:
        obj (bpy.types.Object): Object to decimate.
        percent (float): Percentage of faces to keep.
    """
    obj.modifiers.new("Decimate", "DECIMATE")
    obj.modifiers["Decimate"].ratio = percent

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Decimate")
    bpy.ops.object.select_all(action="DESELECT")


def show_all_modifiers():
    """Disable and then enable all modifiers."""
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            mod.show_viewport = False
            mod.show_viewport = True
        obj.update_tag()


def duplicate_object(
    obj: bpy.types.Object,
    obj_data: bool = True,
    actions: bool = True,
    collection: bpy.types.Collection = None,
) -> bpy.types.Object:
    """Duplicate an object.

    Args:
        obj (bpy.types.Object): Object to duplicate.
        obj_data (bool, optional): Whether to duplicate the object data. Defaults to True.
        actions (bool, optional): Whether to duplicate the actions. Defaults to True.
        collection (bpy.types.Collection, optional): Collection to link the duplicate to. Defaults to None.

    Returns:
        bpy.types.Object: The duplicate object.
    """
    obj_copy = obj.copy()

    if obj_data:
        obj_copy.data = obj_copy.data.copy()

    if actions and obj_copy.animation_data:
        obj_copy.animation_data.action = obj_copy.animation_data.action.copy()

    link_collection = collection or bpy.context.collection
    link_collection.objects.link(obj_copy)

    return obj_copy


def load_from_blend(
    abs_blend_path: Union[str, Path],
    data_type: str,
    filter_names: Union[str, list[str]] = None,
):
    """
    Load data from a Blender (.blend) file and return the loaded data.

    Parameters:
        abs_blend_path (str,Path): The path to the .blend file.
        data_type (str): The type of data to load (node_groups, objects, worlds, etc.)
        filter_names (str, List[str]): The name to filter the data by (optional).

    Returns:
        The loaded data.
    """
    # Initialize data_to variable
    data_to_return = None

    # Turn filter_names into a list if it is a string
    filter_names = [filter_names] if isinstance(filter_names, str) else filter_names

    # Load from blend file
    with bpy.data.libraries.load(str(abs_blend_path), link=False) as (
        data_from,
        data_to,
    ):
        data_from_values = getattr(data_from, data_type, [])

        if filter_names:
            filtered_values = [c for c in data_from_values if c in filter_names]
            setattr(data_to, data_type, filtered_values)
        else:
            setattr(data_to, data_type, list(data_from_values))

        data_to_return = getattr(data_to, data_type, None)

    return data_to_return


def add_volume_attribute(obj: bpy.types.Object):
    """Add a volume attribute to an object.

    Create geometry nodes modifier to write an attribute containing the volume of the object.

    Args:
        obj (bpy.types.Object): Object to add volume attribute to.
    """
    # Convert to cm^3 from m^3
    volume_conversion_factor = 1000000

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Calculate the raw volume (without considering scaling)
    raw_volume = float(bm.calc_volume())

    # Calculate the scale factor (product of the scale on all axes)
    scale_factor = obj.scale.x * obj.scale.y * obj.scale.z
    # Adjust the volume for the object's scaling
    volume = raw_volume * scale_factor * volume_conversion_factor

    # Remove bmesh
    bm.free()
    bm = None

    if "Volume_Attribute" in obj.modifiers:
        obj.modifiers["Volume_Attribute"].node_group.nodes["Volume"].inputs[
            4
        ].default_value = volume
    else:
        # Add geometry nodes to object
        attribute_mod = obj.modifiers.new(
            "Volume_Attribute",
            "NODES",
        )

        # Add node group to modifier
        node_group = bpy.data.node_groups.new(
            "Attribute",
            "GeometryNodeTree",
        )
        attribute_mod.node_group = node_group

        input_node = node_group.nodes.new("NodeGroupInput")
        output_node = node_group.nodes.new("NodeGroupOutput")

        node_group.outputs.new("NodeSocketGeometry", "Geometry")
        node_group.inputs.new("NodeSocketGeometry", "Geometry")

        # Add attribute node
        attribute_node = node_group.nodes.new("GeometryNodeStoreNamedAttribute")
        attribute_node.inputs["Name"].default_value = "volume"
        attribute_node.inputs[4].default_value = volume
        attribute_node.name = "Volume"

        # Add links
        node_group.links.new(
            input_node.outputs["Geometry"],
            attribute_node.inputs["Geometry"],
        )
        node_group.links.new(attribute_node.outputs["Geometry"], output_node.inputs[0])


def refresh_modifiers():
    """Flip the visibility of all modifiers to refresh them."""
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            if mod.show_viewport:
                mod.show_viewport = False
                bpy.context.view_layer.update()
                mod.show_viewport = True
                bpy.context.view_layer.update()
            elif render_visibility(obj):
                mod.show_viewport = True
                bpy.context.view_layer.update()


def _get_num_clumps(num_objects: int, ratio: float) -> int:
    return int(-(ratio * num_objects) / (ratio - 1))


def _get_instance_indices(obj_count: int, mean: int, std_dev: int) -> list:
    num_objs_in_instance = max(int(np.random.normal(mean, std_dev)), 2)
    return np.random.choice(obj_count, num_objs_in_instance)


def random_transform_object(
    obj: bpy.types.Object, pos_std: float, scale_std: float
) -> None:
    """Randomly transform object.

    Args:
        obj (bpy.types.Object): Object to transform.
        pos_std (float): Standard deviation of position.
        scale_std (float): Standard deviation of scale.
    """
    obj.location[0] = np.random.normal(0, pos_std)
    obj.location[1] = np.random.normal(0, pos_std)
    obj.rotation_euler[2] = np.random.uniform(0, 2 * np.pi)
    scale_factor = np.random.normal(1, scale_std)
    obj.scale = [scale_factor, scale_factor, scale_factor]


def apply_transformations(clump_obj) -> None:
    mb = clump_obj.matrix_basis
    if hasattr(clump_obj.data, "transform"):
        clump_obj.data.transform(mb)
    for child in clump_obj.children:
        child.matrix_local = mb @ child.matrix_local
    clump_obj.matrix_basis.identity()


def create_clumps(collection: bpy.types.Collection, config: dict) -> list:
    """Create clumps out of object in collection.

    Args:
        collection (bpy.types.Collection): Collection to create clumps from.
        config (dict): Configuration for clumps.

    Returns:
        list: List of clumps objects.
    """
    all_objects = [obj for obj in collection.all_objects if obj.type == "MESH"]
    new_clumps = []
    num_objects = len(all_objects)
    num_clumps = _get_num_clumps(num_objects, config["ratio"])
    instance_objects = []

    # Generate object instances
    for _ in range(num_clumps):
        indices = _get_instance_indices(
            len(all_objects), config["size"], config["size_std"]
        )
        instance_objects.append([all_objects[idx] for idx in indices])

    # Process each instance
    for instance in instance_objects:
        clump_items = []
        for obj in instance:
            clump_item = obj.copy()

            clump_item.data = obj.data.copy()
            random_transform_object(
                clump_item, config["position_std"], config["scale_std"]
            )
            collection.objects.link(clump_item)
            clump_item.hide_set(True)
            clump_items.append(clump_item)

        clump = merge_objects(clump_items)
        new_clumps.append(clump)
        apply_transformations(clump)

    return new_clumps


def merge_objects(obj_list: list) -> bpy.types.Object:
    """Merge objects into single object.

    Args:
        obj_list (list): List of objects to merge

    Returns:
        bpy.types.Object: Merged object
    """
    with bpy.context.temp_override(
        active_object=obj_list[0],
        selected_objects=obj_list,
    ):
        bpy.ops.object.join()
    return obj_list[0]


def eval_param(eval_params: Union[float, dict, str]) -> Union[float, list, str]:
    """Convert a parameter to a discrete value with the help of a sample function.

    Args:
        eval_params: Parameter to be evaluated.

    Returns:
        Union[float, list, str]: Evaluated parameter.
    """
    is_list = isinstance(eval_params, list) or hasattr(eval_params, "to_list")
    eval_params = eval_params if is_list else [eval_params]

    curr_frame = bpy.context.scene.frame_current
    catalog_string = bpy.data.scenes["Scene"]["catalog"]
    catalog = pickle.loads(bytes(catalog_string, "latin1"))

    evaluated_param = list(
        map(lambda x: su.apply_sampling(x, curr_frame, catalog), eval_params)
    )
    return evaluated_param if is_list else evaluated_param[0]
