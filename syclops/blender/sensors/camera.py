import logging
import os
from pathlib import Path

import bmesh
import bpy
import numpy as np
import yaml
from mathutils import Matrix, Vector
from syclops import utility
from syclops.blender.sensors.sensor_interface import SensorInterface


class Camera(SensorInterface):
    """Plugin creating a camera inside blender"""

    def setup_sensor(self):
        self.create_camera()  # Create self.objs
        cam = self.get_camera()
        cam["name"] = self.config["name"]
        if "depth_of_field" in self.config:
            cam.data.dof.use_dof = True
            cam.data.dof.aperture_fstop = self.config["depth_of_field"]["aperture"]
        self.create_frustum()
        logging.info("Camera: %s created", self.config["name"])

    def create_frustum_pyramid(self):
        """Create sensor's frustum as pyramid"""

        # Get cam object
        cam = self.get_camera()

        cam_matrix = cam.matrix_world.normalized()
        scene = bpy.context.scene
        # Set the resolution for the camera
        scene.render.resolution_x = self.config["resolution"][0]
        scene.render.resolution_y = self.config["resolution"][1]

        # Get the camera frustum points
        points = [cam_matrix @ vec for vec in cam.data.view_frame(scene=scene)]
        cam_pos = cam_matrix.to_translation()

        # Camera normal vector
        cam_normal = cam_matrix.to_quaternion() @ Vector((0, 0, -1))

        # Scale the frustum to the desired depth
        depth_m = self.config["frustum"]["depth"]
        scale_factor = depth_m / (points[0] - cam_pos).dot(cam_normal)
        scaled_points = [cam_pos + scale_factor * (point - cam_pos) for point in points]

        bm = bmesh.new()
        scaled_points.append(cam_pos)
        for point in scaled_points:
            bm.verts.new(point)

        # Create a new mesh and object
        mesh = bpy.data.meshes.new(self.config["name"] + " Frustum Pyramid Mesh")
        obj = bpy.data.objects.new(self.config["name"] + " Frustum Pyramid", mesh)

        # Add the object to the scene
        scene = bpy.context.scene
        scene.collection.objects.link(obj)

        # Create the faces of the pyramid
        bm.verts.ensure_lookup_table()
        for i in range(4):
            bm.faces.new((bm.verts[i], bm.verts[(i + 1) % 4], bm.verts[4]))
        bm.faces.new((bm.verts[0], bm.verts[1], bm.verts[2], bm.verts[3]))

        # Update the bmesh and mesh
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        # Create a new material
        mat = bpy.data.materials.new(
            name=self.config["name"] + " Frustum Pyramid Material"
        )
        mat.use_nodes = True

        # Get the material output node
        tree = mat.node_tree
        nodes = tree.nodes
        links = tree.links
        out_node = nodes.get("Material Output")

        # Create a principled BSDF node for the material
        bsdf_node = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf_node.inputs["Base Color"].default_value = tuple(
            self.config["frustum"]["color"]
        ) + (
            1,
        )  # Set the RGB base color
        bsdf_node.inputs["Alpha"].default_value = self.config["frustum"][
            "transparency"
        ]  # Set the transparency

        # Connect the nodes
        links.new(bsdf_node.outputs["BSDF"], out_node.inputs["Surface"])

        # Assign the material
        mesh.materials.append(mat)

        # Add a wireframe modifier to the mesh to make it a wireframe in the renderer
        if "wireframe" in self.config["frustum"]:
            if self.config["frustum"]["wireframe"]["enabled"]:
                # Todo rename modifier according to name
                mod = obj.modifiers.new(self.config["name"] + " Wireframe", "WIREFRAME")
                mod.thickness = self.config["frustum"]["wireframe"][
                    "thickness"
                ]  # Set the thickness of the wireframe
                # Apply the modifier to create the solid volume
                # bpy.ops.object.modifier_apply(modifier="Wireframe")

        if "hide_render" in self.config["frustum"]:
            obj.hide_render = self.config["frustum"]["hide_render"]
        else:
            obj.hide_render = False

        sensor_coll = utility.create_collection("Sensors")
        sensor_coll.objects.link(obj)

        # Add frustum to objects
        self.objs.append(utility.ObjPointer(obj))

    def create_frustum(self):
        """Create sensor's frustum"""
        if "frustum" in self.config:
            if self.config["frustum"]["enabled"]:
                if self.get_camera().data.type != "PERSP":
                    logging.warning(
                        "Camera: create_frustum not supported for non-perspective cameras"
                    )
                    return
                if self.config["frustum"]["type"] == "pyramid":
                    self.create_frustum_pyramid()
                else:
                    logging.info(
                        "Camera: %s frustum type not implemented", self.config["name"]
                    )
                    return
                logging.info("Camera: %s frustum created", self.config["name"])

    def render_outputs(self):
        logging.info(
            "Camera: %s generating outputs at frame %d",
            self.config["name"],
            bpy.context.scene.frame_current,
        )
        scene = bpy.context.scene
        scene.render.resolution_x = self.config["resolution"][0]
        scene.render.resolution_y = self.config["resolution"][1]
        # Set camera as active camera
        cam = self.get_camera()
        scene.camera = cam

        if cam.data.dof.use_dof:
            if self.config["depth_of_field"]["autofocus"]:
                cam.data.dof.focus_distance = self.calculate_focus_distance()
            else:
                cam.data.dof.focus_distance = self.config["depth_of_field"][
                    "focus_distance"
                ]
            logging.info(
                "Camera: %s focus distance: %f",
                self.config["name"],
                cam.data.dof.focus_distance,
            )

        if "lens_type" in self.config:
            lens_type = utility.eval_param(self.config["lens_type"])
        else:
            lens_type = "PERSPECTIVE"

        # Set camera settings
        cam.data.sensor_width = utility.eval_param(self.config["sensor_width"])
        if lens_type == "PERSPECTIVE":
            cam.data.lens = utility.eval_param(self.config["focal_length"])
        elif lens_type == "FISHEYE_EQUIDISTANT":
            cam.data.cycles.fisheye_fov = utility.eval_param(self.config["fisheye_fov"])
        elif lens_type == "FISHEYE_EQUISOLID":
            cam.data.cycles.fisheye_lens = utility.eval_param(self.config["focal_length"])
            cam.data.cycles.fisheye_fov = utility.eval_param(self.config["fisheye_fov"])
        else:
            raise ValueError("Camera: not supported lens type \"%s\"", lens_type)

        if "motion_blur" in self.config:
            if self.config["motion_blur"]["enabled"]:
                time_per_frame = 1 / bpy.context.scene.render.fps
                try:
                    shutter_speed = self.config["shutter_speed"]
                except KeyError:
                    logging.error(
                        "Camera: %s shutter speed not set and motion blur enabled",
                        self.config["name"],
                    )
                scene.render.use_motion_blur = True
                scene.render.motion_blur_shutter = shutter_speed / time_per_frame

            if "rolling_shutter" in self.config["motion_blur"]:
                if self.config["motion_blur"]["rolling_shutter"]["enabled"]:
                    time_per_frame = 1 / bpy.context.scene.render.fps
                    bpy.context.scene.cycles.rolling_shutter_type = "TOP"
                    bpy.context.scene.cycles.rolling_shutter_duration = (
                        self.config["motion_blur"]["rolling_shutter"]["duration"]
                        / time_per_frame
                    )

        if "exposure" in self.config:
            bpy.data.scenes["Scene"].view_settings.exposure = utility.eval_param(
                self.config["exposure"]
            )
        if "gamma" in self.config:
            bpy.data.scenes["Scene"].view_settings.gamma = utility.eval_param(
                self.config["gamma"]
            )

        # Render image
        self.write_intrinsics()
        self.write_extrinsics()
        for output in self.outputs:
            output.generate_output(self)

    def create_camera(self):
        """Place camera object in scene"""
        # Place Camera in scene
        camera_data = bpy.data.cameras.new(name=self.config["name"])

        # Set lens type and use "PERSPECTIVE" as default
        if "lens_type" in self.config:
            lens_type = utility.eval_param(self.config["lens_type"])
        else:
            lens_type = "PERSPECTIVE"

        # Initial camera settings
        if lens_type == "PERSPECTIVE":
            camera_data.type = "PERSP"
            camera_data.lens = utility.eval_param(self.config["focal_length"])
        elif lens_type == "FISHEYE_EQUIDISTANT":
            camera_data.type = "PANO"
            camera_data.cycles.panorama_type = "FISHEYE_EQUIDISTANT"
            camera_data.cycles.fisheye_fov = utility.eval_param(self.config["fisheye_fov"])
        elif lens_type == "FISHEYE_EQUISOLID":
            camera_data.type = "PANO"
            camera_data.cycles.panorama_type = "FISHEYE_EQUISOLID"
            camera_data.cycles.fisheye_lens = utility.eval_param(self.config["focal_length"])
            camera_data.cycles.fisheye_fov = utility.eval_param(self.config["fisheye_fov"])
        else:
            raise ValueError("Camera: not supported lens type \"%s\"", lens_type)

        camera_data.sensor_width = utility.eval_param(self.config["sensor_width"])

        camera_object = bpy.data.objects.new(self.config["name"], camera_data)
        sensor_coll = utility.create_collection("Sensors")
        sensor_coll.objects.link(camera_object)

        # Add camera to objects
        self.objs.append(utility.ObjPointer(camera_object))

    def calculate_focus_distance(self):
        """Calculate the focus distance by raytracing a beam in center of image"""
        context = bpy.context
        cam = context.scene.camera
        bpy.context.view_layer.update()
        ray_origin = cam.matrix_world.translation
        ray_direction = cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        hit, location, _, _, _, _ = bpy.context.scene.ray_cast(
            context.evaluated_depsgraph_get(), ray_origin, ray_direction
        )

        if hit:
            distance = (location - ray_origin).length
            return distance
        else:
            logging.warning(
                "Camera: %s could not calculate focus distance", self.config["name"]
            )
            return 50

    @staticmethod
    def get_sensor_size(sensor_fit, sensor_x, sensor_y):
        if sensor_fit == "VERTICAL":
            return sensor_y
        return sensor_x

    @staticmethod
    def get_sensor_fit(sensor_fit, size_x, size_y):
        if sensor_fit == "AUTO":
            if size_x >= size_y:
                return "HORIZONTAL"
            else:
                return "VERTICAL"
        return sensor_fit

    # ---------------------------------------------------------------
    # https://blender.stackexchange.com/questions/38009/3x4-camera-matrix-from-blender-camera/120063#120063
    # ---------------------------------------------------------------

    def get_camera_matrix(self, camera):
        """Get the camera matrix for the given camera.

        Args:
            camera (bpy.types.Object): The camera object

        Returns:
            numpy.array: The camera matrix
        """
        if camera.type != "PERSP":
            logging.warning(
                "Camera: get_camera_matrix not supported for non-perspective cameras"
            )
            return Matrix(((1, 0, 0), (0, 1, 0), (0, 0, 1)))

        scene = bpy.context.scene
        f_in_mm = camera.lens
        resolution_x_in_px = self.config["resolution"][0]
        resolution_y_in_px = self.config["resolution"][1]
        sensor_size_in_mm = Camera.get_sensor_size(
            camera.sensor_fit, camera.sensor_width, camera.sensor_height
        )
        sensor_fit = Camera.get_sensor_fit(
            camera.sensor_fit,
            scene.render.pixel_aspect_x * resolution_x_in_px,
            scene.render.pixel_aspect_y * resolution_y_in_px,
        )
        pixel_aspect_ratio = scene.render.pixel_aspect_y / scene.render.pixel_aspect_x
        if sensor_fit == "HORIZONTAL":
            view_fac_in_px = resolution_x_in_px
        else:
            view_fac_in_px = pixel_aspect_ratio * resolution_y_in_px
        pixel_size_mm_per_px = sensor_size_in_mm / f_in_mm / view_fac_in_px
        s_u = 1 / pixel_size_mm_per_px
        s_v = 1 / pixel_size_mm_per_px / pixel_aspect_ratio

        # Parameters of intrinsic calibration matrix K
        u_0 = resolution_x_in_px / 2 - camera.shift_x * view_fac_in_px
        v_0 = (
            resolution_y_in_px / 2
            + camera.shift_y * view_fac_in_px / pixel_aspect_ratio
        )
        skew = 0  # only use rectangular pixels

        K = Matrix(((s_u, skew, u_0), (0, s_v, v_0), (0, 0, 1)))
        return K

    @staticmethod
    def get_camera_pose(camera):
        """Get the camera pose for the given camera.

        Args:
            camera (bpy.types.Object): The camera object

        Returns:
            numpy.array: The 6D camera pose
        """
        # Blender Camera rotation correction
        R_cam = Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))
        RT_cam = camera.matrix_world @ R_cam.to_4x4()
        return RT_cam

    def write_intrinsics(self):
        """Write the camera intrinsics to a file"""
        cam = self.get_camera()
        curr_frame = bpy.context.scene.frame_current
        cam_name = cam["name"]
        calibration_folder = (
            Path(bpy.context.scene.render.filepath) / cam_name / "intrinsics"
        )
        calibration_folder.mkdir(parents=True, exist_ok=True)
        calibration_file = calibration_folder / f"{curr_frame:04}.yaml"

        cam_matrix = np.array(self.get_camera_matrix(cam.data))

        meta_description_intrinsics = {
            "type": "INTRINSICS",
            "format": "YAML",
            "description": "Writes the camera matrix.",
        }

        # Write camera intrinsics to file
        with open(calibration_file, "w") as f:
            yaml.dump({"camera_matrix": cam_matrix.tolist()}, f)

        with utility.AtomicYAMLWriter(
            str(calibration_folder / "metadata.yaml")
        ) as writer:
            # Add metadata
            writer.data.update(meta_description_intrinsics)
            # Add current step
            writer.add_step(
                step=bpy.context.scene.frame_current,
                step_dicts=[
                    {
                        "type": meta_description_intrinsics["type"],
                        "path": str(calibration_file.name),
                    }
                ],
            )

            # Add expected steps
            writer.data["expected_steps"] = utility.get_job_conf()["steps"]
            writer.data["sensor"] = cam_name
            writer.data["id"] = cam_name + "_intrinsics"

    def write_extrinsics(self):
        """Write the camera extrinsics to a file"""
        cam = self.get_camera()

        curr_frame = bpy.context.scene.frame_current
        cam_name = cam["name"]
        calibration_folder = (
            Path(bpy.context.scene.render.filepath) / cam_name / "extrinsics"
        )

        if not os.path.exists(calibration_folder):
            os.makedirs(calibration_folder)
        calibration_file = calibration_folder / f"{curr_frame:04}.yaml"
        cam_pose = np.array(self.get_camera_pose(cam))

        # Write camera extrinsics to file
        with open(calibration_file, "w") as f:
            yaml.dump({"camera_pose": cam_pose.tolist()}, f)

        meta_description_extrinsics = {
            "type": "EXTRINSICS",
            "format": "YAML",
            "description": "Writes the global pose of the camera.",
        }

        with utility.AtomicYAMLWriter(
            str(calibration_folder / "metadata.yaml")
        ) as writer:
            # Add metadata
            writer.data.update(meta_description_extrinsics)
            # Add current step
            writer.add_step(
                step=bpy.context.scene.frame_current,
                step_dicts=[
                    {
                        "type": meta_description_extrinsics["type"],
                        "path": str(calibration_file.name),
                    }
                ],
            )

            # Add expected steps
            writer.data["expected_steps"] = utility.get_job_conf()["steps"]
            writer.data["sensor"] = cam_name
            writer.data["id"] = cam_name + "_extrinsics"

    def get_camera(self):
        for obj in self.objs:
            if obj.get().type == "CAMERA":
                return obj.get()
        raise Exception("'self' has no object 'CAMERA'.")
