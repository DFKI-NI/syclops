import bpy
import mathutils

def get_relative_position(obj, target):
    return target.matrix_world.inverted() @ obj.matrix_world.translation

def create_empties_from_keypoints(mesh_object):
    keypoints = mesh_object["keypoints"]
    for key, pos in keypoints.items():
        world_position = mesh_object.matrix_world @ mathutils.Vector((pos["x"], pos["y"], pos["z"]))
        bpy.ops.object.empty_add(location=world_position)
        empty = bpy.context.active_object
        empty.name = f"Keypoint_{mesh_object.name}_{key}"

def add_keypoints_to_mesh(mesh_object, empty_objects):
    mesh_object["keypoints"] = {}
    for index, empty in enumerate(empty_objects):
        relative_pos = get_relative_position(empty, mesh_object)
        mesh_object["keypoints"][str(index)] = {
            "x": relative_pos.x,
            "y": relative_pos.y,
            "z": relative_pos.z,
        }

# Main script
selected_objects = bpy.context.selected_objects
mesh_objects = [obj for obj in selected_objects if obj.type == "MESH"]
empty_objects = [obj for obj in selected_objects if obj.type == "EMPTY"]

if mesh_objects and empty_objects:
    # Sort empty objects by name
    empty_objects.sort(key=lambda x: x.name)
    
    for mesh in mesh_objects:
        add_keypoints_to_mesh(mesh, empty_objects)
        print(f"Key points added to {mesh.name}")
elif len(selected_objects) == 1 and selected_objects[0].type == "MESH":
    active_object = selected_objects[0]
    if "keypoints" in active_object:
        create_empties_from_keypoints(active_object)
        print(f"Empties created from key points in {active_object.name}")
    else:
        print(f"No keypoints attribute found in {active_object.name}")
else:
    print("Please select either multiple mesh objects and at least one empty, or a single mesh with a keypoints attribute.")