"""Module for handling transformations in Blender."""

import bpy
from mathutils import Euler, Vector
from syclops import utility


class Transformations(object):
    """Class for managing and applying transformations in Blender."""

    def __init__(self) -> None:
        """Initialize the transformations handler."""
        self.tf_nodes = {}

    def create_tf_tree(
        self,
        transformations: dict,
        parent: bpy.types.Object = None,
    ) -> None:
        """
        Recursively create transformation tree in Blender with empties as nodes.

        Args:
            transformations (dict): Dictionary of transformations.
            parent (bpy.types.Object, optional): Current parent object. Defaults to None.
        """
        for tf_name, tf_params in transformations.items():
            tf_node = self.create_transformation_empty(tf_name)
            for attr, param_value in tf_params.items():
                tf_node[attr] = param_value
            if parent:
                tf_node.parent = parent
            children = tf_params.get("children")
            if children is not None:
                self.create_tf_tree(children, tf_node)

    def create_transformation_empty(self, name: str) -> bpy.types.Object:
        """
        Create empty object with name and add it to the scene.

        Args:
            name (str): Name of the empty object.

        Returns:
            bpy.types.Object: Empty object.
        """
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_size = 0.1
        empty.empty_display_type = "ARROWS"
        sensor_collection = utility.create_collection("Transformations")
        sensor_collection.objects.link(empty)
        self.tf_nodes[name] = utility.ObjPointer(empty)
        return empty

    def configure_tf_tree(self) -> None:
        """Apply the transformations to the current frame."""
        for _, tf_node in self.tf_nodes.items():
            tf_obj = tf_node.get()
            tf_obj.location = utility.eval_param(tf_obj["location"])
            tf_obj.rotation_euler = Euler(utility.eval_param(tf_obj["rotation"]), "XYZ")

            if "velocities" in tf_obj:
                self.create_transformation_keyframes(tf_obj)

    def create_transformation_keyframes(self, tf_obj: bpy.types.Object) -> None:
        """
        Create keyframes around the current frame to simulate velocity.

        Args:
            tf_obj (bpy.types.Object): Transformation object.
        """
        sec_per_frame = 1 / bpy.context.scene.render.fps
        velocities = {
            "location": Vector(utility.eval_param(tf_obj["velocities"]["location"]))
            * sec_per_frame,
            "rotation": Vector(utility.eval_param(tf_obj["velocities"]["rotation"]))
            * sec_per_frame,
        }

        self.insert_keyframes(tf_obj, "location", bpy.context.scene.frame_current)
        self.insert_keyframes(tf_obj, "rotation_euler", bpy.context.scene.frame_current)

        self.update_transformation(
            tf_obj,
            velocities["location"],
            velocities["rotation"],
            bpy.context.scene.frame_current + 1,
        )
        self.update_transformation(
            tf_obj,
            -velocities["location"],
            -velocities["rotation"],
            bpy.context.scene.frame_current - 1,
        )

    def insert_keyframes(
        self,
        tf_obj: bpy.types.Object,
        data_path: str,
        frame: int,
    ) -> None:
        """Insert a keyframe for a given data path and frame.

        Args:
            tf_obj (bpy.types.Object): Transformation object.
            data_path (str): Data path of the attribute.
            frame (int): Frame number.
        """
        tf_obj.keyframe_insert(data_path=data_path, frame=frame)

    def update_transformation(
        self,
        tf_obj: bpy.types.Object,
        loc_change: Vector,
        rot_change: Vector,
        frame: int,
    ) -> None:
        """Update object transformation and insert keyframes.

        Args:
            tf_obj (bpy.types.Object): Transformation object.
            loc_change (Vector): Change in location.
            rot_change (Vector): Change in rotation.
            frame (int): Frame number.
        """
        tf_obj.location += loc_change
        tf_obj.rotation_euler.rotate(Euler(rot_change, "XYZ"))

        self.insert_keyframes(tf_obj, "location", frame)
        self.insert_keyframes(tf_obj, "rotation_euler", frame)

        bpy.context.scene.frame_set(frame)
