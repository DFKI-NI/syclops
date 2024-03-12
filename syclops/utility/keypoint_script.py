"""
Script to be used inside of Blender to add keypoint information to 3d objects
"""

import bpy
import mathutils


# Function to get relative position
def get_relative_position(obj, target):
    return target.matrix_world.inverted() @ obj.matrix_world.translation


# Function to create empties at keypoint positions relative to the mesh object
def create_empties_from_keypoints(mesh_object):
    keypoints = mesh_object["keypoints"]
    for key, pos in keypoints.items():
        # Calculate the world position from the relative position
        world_position = mesh_object.matrix_world @ mathutils.Vector(
            (pos["x"], pos["y"], pos["z"])
        )
        # Create an empty and set its world position
        bpy.ops.object.empty_add(location=world_position)
        empty = bpy.context.active_object
        empty.name = f"Keypoint_{key}"


# Main script
selected_objects = bpy.context.selected_objects
active_object = bpy.context.active_object

# Case 1: Multiple objects selected, last is a mesh
if len(selected_objects) > 1 and active_object.type == "MESH":
    selected_objects.remove(active_object)
    selected_objects.sort(key=lambda x: x.name)

    keypoints = {}

    for index, obj in enumerate(selected_objects):
        if obj.type == "EMPTY":
            relative_pos = get_relative_position(obj, active_object)
            keypoints[str(index)] = {
                "x": relative_pos.x,
                "y": relative_pos.y,
                "z": relative_pos.z,
            }

    if "keypoints" in active_object:
        del active_object["keypoints"]

    active_object["keypoints"] = keypoints
    print("Key points added to", active_object.name)

# Case 2: Single mesh object with keypoints attribute
elif len(selected_objects) == 1 and selected_objects[0].type == "MESH":
    active_object = selected_objects[0]
    if "keypoints" in active_object:
        create_empties_from_keypoints(active_object)
        print("Empties created from key points in", active_object.name)
    else:
        print("No keypoints attribute found in", active_object.name)

else:
    print(
        "Please select either multiple objects with a mesh as the active object, or a single mesh with a keypoints attribute."
    )
