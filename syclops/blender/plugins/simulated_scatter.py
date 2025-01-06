import logging

import bpy
import numpy as np
from mathutils import Vector
from syclops import utility
from syclops.blender.plugins.plugin_interface import PluginInterface


class SimulatedScatter(PluginInterface):
    """
    Plugin scatters objects and drops them on a given floor object.
    """

    def __init__(self, config: dict):
        self.floor_objects: list[utility.ObjPointer] = None
        self.conv_hull_instances: list[utility.ObjPointer] = []
        self.conv_hull_instances_collection: utility.ObjPointer = None
        self.instanced_conv_hulls: list[utility.ObjPointer] = []
        super().__init__(config)

    def load(self):
        self._load_instance_objects()
        self._load_floor_object()
        logging.info("Calculating Spawn Points")
        scatter_points = self._calc_scatter_points()
        logging.info("Running Physics Simulation")
        self._simulate_convex_objects(scatter_points)

    def _simulate_convex_objects(self, scatter_points: np.array):
        obj_poses = {}
        with utility.RevertAfter():
            bpy.ops.rigidbody.world_add()
            collection_rigidbody = bpy.data.collections.new("Rigidbody")
            bpy.data.scenes["Scene"].rigidbody_world.collection = collection_rigidbody
            for scatter_point in scatter_points:
                new_conv_hulls = []
                # Select random convex hull
                parent_uuid = np.random.choice(self.conv_hull_instances).get()[
                    "PARENT_UUID"
                ]
                conv_hulls = utility.filter_objects("PARENT_UUID", parent_uuid)
                random_rotation = Vector(np.random.uniform(0, 2 * np.pi, size=3))
                random_scale_value = (
                    np.random.normal(1, self.config["scale_standard_deviation"])
                    if "scale_standard_deviation" in self.config
                    else 1
                )
                random_scale = Vector([random_scale_value] * 3)
                for conv_hull in conv_hulls:
                    new_conv_hull = conv_hull.copy()
                    new_conv_hull.data = conv_hull.data.copy()
                    new_conv_hull.location = scatter_point
                    new_conv_hull.rotation_euler = random_rotation
                    new_conv_hull.scale = random_scale
                    self.conv_hull_instances_collection.get().objects.link(
                        new_conv_hull
                    )
                    new_conv_hull["PARENT_UUID_COPY"] = conv_hull["PARENT_UUID"]
                    del new_conv_hull["UUID"]
                    del new_conv_hull["PARENT_UUID"]
                    self.instanced_conv_hulls.append(utility.ObjPointer(new_conv_hull))
                    # Delete Parent UUID to prevent further copying
                    bpy.data.scenes["Scene"].rigidbody_world.collection.objects.link(
                        new_conv_hull
                    )
                    new_conv_hull.rigid_body.type = "ACTIVE"
                    new_conv_hull.rigid_body.friction = 10
                    new_conv_hull.select_set(True)
                    new_conv_hulls.append(new_conv_hull)
                if len(new_conv_hulls) > 1:
                    bpy.ops.object.select_all(action="DESELECT")
                    for new_conv_hull in new_conv_hulls:
                        new_conv_hull.select_set(True)
                    bpy.context.view_layer.objects.active = new_conv_hulls[0]
                    bpy.ops.rigidbody.connect()
            for obj in self.floor_objects:
                convex_hulls = utility.convex_decomposition(
                    obj,
                    self.conv_hull_instances_collection,
                    self.config["convex_decomposition_quality"],
                )
                for convex_hull in convex_hulls:
                    bpy.data.scenes["Scene"].rigidbody_world.collection.objects.link(
                        convex_hull
                    )
                    convex_hull.rigid_body.type = "PASSIVE"
                    convex_hull.rigid_body.friction = 10

            for i in range(self.config["simulation_steps"]):
                logging.info(f"Simulation Step: {i}")
                bpy.context.scene.frame_set(i + 1)

            disSet = utility.DisjointSet()
            if bpy.data.scenes["Scene"].rigidbody_world.constraints:
                for constraint in bpy.data.scenes[
                    "Scene"
                ].rigidbody_world.constraints.objects:
                    obj1 = constraint.rigid_body_constraint.object1
                    obj2 = constraint.rigid_body_constraint.object2
                    if obj1 and obj2:
                        disSet.union(obj1, obj2)

            processed_clusters = []

            # Iterate over all instanced convex hulls
            for obj in self.instanced_conv_hulls:
                obj = obj.get()
                if disSet.find_cluster(obj) in processed_clusters:
                    continue
                if disSet.find_cluster(obj):
                    processed_clusters.append(disSet.find_cluster(obj))

                # Write pose to dictionary
                parent_uuid = obj["PARENT_UUID_COPY"]
                if parent_uuid in obj_poses:
                    # Check if current pose is already in the pose list
                    current_pose = obj.matrix_world.copy()
                    if current_pose in obj_poses[parent_uuid]:
                        pass
                    else:
                        obj_poses[parent_uuid].append(current_pose)
                else:
                    # Create new list for object
                    obj_poses[parent_uuid] = [obj.matrix_world.copy()]

        # Set the object poses
        # Create new collection and assign a pointer
        final_collection = utility.create_collection(self.config["name"] + "_Final")

        for parent_uuid, poses in obj_poses.items():
            parent_obj = utility.filter_objects("UUID", parent_uuid)[0]
            for pose in poses:
                # Creater instance object
                instance_object = parent_obj.copy()
                instance_object.data = parent_obj.data.copy()
                # Add instance object to collection
                final_collection.objects.link(instance_object)
                # Set instance object pose
                instance_object.matrix_world = pose

        self._add_volume_attribute(final_collection)

        # Delete self.conv_hull_instances
        for obj in self.conv_hull_instances:
            bpy.data.objects.remove(obj.get(), do_unlink=True)
        self.conv_hull_instances = []
        bpy.data.collections.remove(self.conv_hull_instances_collection.get())
        self.conv_hull_instances_collection = None

    def _create_base_object(self):
        """Add placeholder object to assign GeoNode Modifier to"""
        # Setup a blender collection
        _coll = utility.create_collection(self.config["name"])

        utility.set_active_collection(_coll)

        # Setup GeoNodes
        bpy.ops.mesh.primitive_plane_add()
        bpy.context.active_object.name = self.config["name"]
        self.scatter_geo_node_obj = utility.ObjPointer(bpy.context.active_object)

    def _load_instance_objects(self):
        # Create new collection and assign a pointer
        self.instance_objects = utility.ObjPointer(
            utility.create_collection(self.config["name"] + "_Objs")
        )
        utility.set_active_collection(self.instance_objects.get())

        # Import the geometry
        loaded_objs = utility.import_assets(self.config["models"])
        loaded_objs_pointer = [utility.ObjPointer(obj) for obj in loaded_objs]
        self.conv_hull_instances_collection = utility.ObjPointer(
            utility.create_collection(self.config["name"] + "_ConvHulls")
        )
        for obj_pointer in loaded_objs_pointer:
            self.reduce_size(obj_pointer.get())
            obj_pointer.get().hide_set(True)
            self.write_config(obj_pointer.get())
            conv_hulls = utility.convex_decomposition(
                obj_pointer,
                self.conv_hull_instances_collection,
                self.config["convex_decomposition_quality"],
            )
            self.conv_hull_instances.extend(
                [utility.ObjPointer(obj) for obj in conv_hulls]
            )
        self.instance_objects.get().hide_render = True

    def _load_floor_object(self):
        # Create new collection and assign a pointer
        floor_object_name = self.config["floor_object"]
        floor_objects = utility.filter_objects("name", floor_object_name)
        self.floor_objects = [utility.ObjPointer(obj) for obj in floor_objects]

    def _calc_scatter_points(self):
        """Scatter points inside the floor bounding box with a minimum distance of the biggest radius.
        Scatter points in accordance to the density specified in the config.
        """
        floor_bbox_x, floor_bbox_y, height = self._get_floor_bbox()
        # Calculate the minimum distance between scatter points
        min_distance = self._calc_biggest_bbox_radius()
        # Number of objects to scatter inside the rectangle in accordance to the density
        num_objects = int(
            (floor_bbox_x[1] - floor_bbox_x[0])
            * (floor_bbox_y[1] - floor_bbox_y[0])
            * self.config["density"]
        )

        # Randomly scatter points inside the rectangle with a minimum distance of the biggest radius
        points = self._grid_points_in_rectangle(
            floor_bbox_x, floor_bbox_y, min_distance
        )
        points = self._remove_points_outside_floor(points)
        points = self._remove_if_too_many_points(points, num_objects)
        points = self._shift_points_above_floor(height, min_distance, points)
        points = self._layer_points(points, num_objects, min_distance)
        if "density_texture" in self.config:
            points = self._apply_density_texture(points, floor_bbox_x, floor_bbox_y)
        points = self._add_position_jitter(points, min_distance)
        return points

    def _get_floor_bbox(self):
        """Returns the x and y points of the floor bounding box and the height of the floor"""
        x = []
        y = []
        height = 0
        for obj in self.floor_objects:
            bbox = obj.get().bound_box
            x.extend([point[0] for point in bbox])
            y.extend([point[1] for point in bbox])
            height = max(height, max([point[2] for point in bbox]))
        return (min(x), max(x)), (min(y), max(y)), height

    def _calc_biggest_bbox_radius(self):
        """Calculates the biggest radius from an object center to a corner"""
        biggest_bbox = 0
        for obj in self.instance_objects.get().objects:
            bbox = self._calc_bbox_radius(obj)
            biggest_bbox = max(biggest_bbox, bbox)
        return biggest_bbox

    def _calc_bbox_radius(self, obj: bpy.types.Object):
        """Calculates the radius from an object origin to a corner"""
        bbox = obj.bound_box
        origin = obj.matrix_world @ obj.location
        distances_to_origin = [
            origin - obj.matrix_world @ Vector(corner) for corner in bbox
        ]
        return max([dist.length for dist in distances_to_origin])

    def _grid_points_in_rectangle(self, floor_bbox_x, floor_bbox_y, min_distance):
        x_min, x_max = floor_bbox_x
        y_min, y_max = floor_bbox_y
        min_distance = min(min_distance, (x_max - x_min) / 2)
        min_distance = min(min_distance, (y_max - y_min) / 2)
        x = np.arange(x_min, x_max, min_distance)
        y = np.arange(y_min, y_max, min_distance)
        points = np.array(np.meshgrid(x, y)).T.reshape(-1, 2)
        return points

    def _remove_if_too_many_points(self, points, num_objects):
        # Randomly delete points if there are too many
        if points.shape[0] > num_objects:
            points = np.delete(
                points,
                np.random.choice(
                    points.shape[0], points.shape[0] - num_objects, replace=False
                ),
                axis=0,
            )
        return points

    def _remove_points_outside_floor(self, points: np.array):
        """Cast a ray from a point and check if floor geometry is hit

        Args:
            points (np.array): Array of points to check

        Returns:
            np.array: Array of points that are above the floor geometry
        """
        direction = Vector((0, 0, -1))
        new_points = []
        for point in points:
            bpy_point = Vector((point[0], point[1], 1000))
            hit = False
            for obj in self.floor_objects:
                obj = obj.get()
                hit, _, _, _ = obj.ray_cast(bpy_point, direction)
                if hit:
                    new_points.append(point)
                    break
        return np.array(new_points)

    def _shift_points_above_floor(self, height, min_distance, points):
        return np.hstack(
            (points, np.ones((points.shape[0], 1)) * height + min_distance * 2)
        )

    def _layer_points(self, points, num_objects, min_distance):
        """Layers points to reach desired number of objects

        Args:
            points (np.array): Points to layer
            num_objects (int): Number of objects to reach

        Returns:
            np.array: Layed out points
        """
        # If the number of points is already higher than the desired number of objects, return the points
        if points.shape[0] >= num_objects:
            return points
        # Calculate the number of points to add
        num_points_to_add = num_objects - points.shape[0]
        # Calculate the number of layers needed
        num_layers = int(np.ceil(num_points_to_add / points.shape[0]))
        # Add layers with additions height of the minimum distance
        original_points = points.copy()
        changed_height_vector = np.array([0, 0, min_distance])
        for i in range(num_layers - 1):
            points = np.vstack(
                (points, original_points + changed_height_vector * (i + 1))
            )
        return points

    def _apply_density_texture(self, points, floor_bbox_x, floor_bbox_y):
        """Load a density texture and apply it to the points"""
        image_asset = utility.eval_param(self.config["density_texture"])
        root_path, texture_path = utility.get_asset_path(image_asset)

        image = utility.load_img_as_array(str(root_path / texture_path))
        img_x, img_y = image.shape[1], image.shape[0]
        # Check which side of floor is bigger
        if floor_bbox_x[1] - floor_bbox_x[0] > floor_bbox_y[1] - floor_bbox_y[0]:
            offset_x = floor_bbox_x[0]
            offset_y = floor_bbox_y[0]
            scale_x = (floor_bbox_x[1] - floor_bbox_x[0]) / img_x
            scale_y = (floor_bbox_x[1] - floor_bbox_x[0]) / img_y
        else:
            offset_y = floor_bbox_y[0]
            offset_x = floor_bbox_x[0]
            scale_y = (floor_bbox_y[1] - floor_bbox_y[0]) / img_y
            scale_x = (floor_bbox_y[1] - floor_bbox_y[0]) / img_x
        # Get pixel values of the points
        pixel_coords = np.array(
            [(points[:, 0] - offset_x) / scale_x, (points[:, 1] - offset_y) / scale_y]
        ).T
        pixel_values = utility.interpolate_img(image[:, :, 0], pixel_coords)
        # Remove points by probability
        points = points[pixel_values > np.random.uniform(size=pixel_values.shape[0])]
        return points

    def _add_position_jitter(self, points, min_distance):
        """Add jitter to each point"""
        jitter = np.random.uniform(-min_distance, min_distance, size=points.shape)
        points += jitter
        return points

    def _add_volume_attribute(self, collection: bpy.types.Collection):
        """Add volume attribute to each object in the instance."""
        for obj in collection.objects:
            utility.add_volume_attribute(obj)

    def configure(self):
        """Apply configuration for current frame"""
        logging.info("Simulated Scatter: %s configured", self.config["name"])
