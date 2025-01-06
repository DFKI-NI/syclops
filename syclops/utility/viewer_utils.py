import json
import time
from pathlib import Path

import cv2
import numpy as np
import yaml
from syclops.preprocessing.texture_processor import process_texture


def _load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def read_image(img_path, cmap=cv2.COLORMAP_JET):
    img = np.load(img_path)["array"]
    img = ((img - img.min()) / (img.max() - img.min()) * 255).astype(np.uint8)
    return cv2.applyColorMap(img, cmap)


def read_and_draw_bounding_boxes(img, bb_path):
    with open(bb_path, "r") as f:
        lines = f.readlines()

    bb_img = img.copy()
    for line in lines:
        _, x_center, y_center, width, height, *_ = map(float, line.split())
        x = int(x_center * img.shape[1] - width * img.shape[1] / 2)
        y = int(y_center * img.shape[0] - height * img.shape[0] / 2)
        w = int(width * img.shape[1])
        h = int(height * img.shape[0])
        cv2.rectangle(bb_img, (x, y), (x + w, y + h), (0, 255, 0), 1)
    return bb_img


def dataset_viewer(args):
    print("Starting Dataset Browser")
    dataset_path = Path(args.dataset_path)

    camera_folder = next(
        (folder for folder in dataset_path.iterdir() if (folder / "rect").exists()),
        None,
    )
    if not camera_folder:
        raise ValueError("No rect folder found")

    annotations = [
        "semantic_segmentation",
        "instance_segmentation",
        "depth",
        "object_volume",
        "bounding_box",
        "pointcloud",
        "keypoints",
    ]
    annotation_data = {annotation: None for annotation in annotations}
    annotation_path = camera_folder.parent / (camera_folder.name + "_annotations")
    for annotation_folder in annotation_path.iterdir():
        if annotation_folder.name in annotation_data:
            annotation_data[annotation_folder.name] = sorted(list(annotation_folder.iterdir()))

    camera_intrinsics = (
        sorted(list((camera_folder / "intrinsics").iterdir()))
        if (camera_folder / "intrinsics").exists()
        else None
    )

    camera_extrinsics = (
        sorted(list((camera_folder / "extrinsics").iterdir()))
        if (camera_folder / "extrinsics").exists()
        else None
    )
    object_positions = (
        sorted(list((dataset_path / "object_positions").iterdir()))
        if (dataset_path / "object_positions").exists()
        else None
    )
    image_paths = sorted(list(Path(camera_folder / "rect").iterdir()))

    for i, image in enumerate(image_paths):
        img = cv2.imread(str(image))
        cv2.imshow("RGB", img)

        if annotation_data["semantic_segmentation"]:
            cv2.imshow(
                "Semantic", read_image(annotation_data["semantic_segmentation"][i])
            )

        if annotation_data["instance_segmentation"]:
            instance_img = read_image(annotation_data["instance_segmentation"][i])
            cv2.imshow("Instance", instance_img)

        if annotation_data["depth"]:
            cv2.imshow("Depth", read_image(annotation_data["depth"][i]))

        if annotation_data["object_volume"]:
            cv2.imshow("Volume", read_image(annotation_data["object_volume"][i]))

        if annotation_data["bounding_box"]:
            bb_img = read_and_draw_bounding_boxes(
                img, annotation_data["bounding_box"][i]
            )
            cv2.imshow("Bounding Boxes", bb_img)
        
        if annotation_data["keypoints"]:
            keypoint_img = img.copy()
            with open(annotation_data["keypoints"][i], "r") as f:
                keypoints = json.load(f)
            for instance_id, keypoint_dict in keypoints.items():
                for key, keypoint in keypoint_dict.items():
                    if key == "class_id":
                        continue
                    else:
                        cv2.circle(keypoint_img, (int(keypoint["x"]), int(keypoint["y"])), 4, (0, 0, 255), 1)
            cv2.imshow("Keypoints", keypoint_img)

        if camera_intrinsics and camera_extrinsics and object_positions:
            pos_img = img.copy()
            # Read camera intrinsics yaml
            camera_matrix = np.array(_load_yaml(camera_intrinsics[i])["camera_matrix"])
            # Read camera extrinsics yaml
            pose_matrix = np.array(_load_yaml(camera_extrinsics[i])["camera_pose"])
            # Read object positions yaml
            with open(object_positions[i], "r") as f:
                # Import JSON as dict
                object_positions_dict = json.load(f)
            for _, poses in object_positions_dict.items():
                location_list = [element["loc"] for element in poses]
                rotation_list = [element["rot"] for element in poses]
                positions_array = np.array(location_list, dtype=np.float32).reshape(
                    (-1, 3)
                )
                # Add 1 to position to get homogeneous coordinates
                positions_array = np.concatenate(
                    (positions_array, np.ones((positions_array.shape[0], 1))),
                    axis=1,
                    dtype=np.float32,
                )
                # Transform to camera coordinates
                positions_array = np.matmul(
                    np.linalg.inv(pose_matrix), positions_array.T
                ).T
                # Transform to image coordinates
                positions_array = np.matmul(camera_matrix, positions_array[:, :3].T).T
                # Normalize
                positions_array = positions_array / positions_array[:, 2:]
                # Draw points
                for position in positions_array:
                    width, height = img.shape[1], img.shape[0]
                    x, y = int(position[0]), int(position[1])
                    if x >= 0 and x < width and y >= 0 and y < height:
                        cv2.circle(pos_img, (int(x), int(y)), 4, (0, 0, 255), 1)
                cv2.imshow("Object Positions", pos_img)

        cv2.waitKey(0)


def texture_viewer(args):
    print("Starting Texture Viewer - Press Q to stop")
    job_filepath = Path(args.texture_viewer)
    view_active = True
    # Continuously read the yaml file
    while view_active:
        try:
            with open(job_filepath, "r") as f:
                yaml_dict = yaml.safe_load(f)

            if "textures" in yaml_dict:
                textures = {}
                for texture_name, texture_dict in yaml_dict["textures"].items():
                    # Combine global texture seed with texture specific seed
                    if (
                        "seed" in texture_dict["config"]
                        and "textures" in yaml_dict["seeds"]
                    ):
                        texture_dict["config"]["seed"] = (
                            yaml_dict["seeds"]["textures"]
                            + texture_dict["config"]["seed"]
                        )

                    texture = process_texture(texture_name, texture_dict, textures, 1)
                    textures[texture_name] = texture
                    cv2.imshow(texture_name, texture)
                    if cv2.waitKey(1) == ord("q"):
                        view_active = False
                        break
                time.sleep(1)
        except Exception as e:
            print(e)
            time.sleep(1)
