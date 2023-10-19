import logging
from pathlib import Path

import bpy
from syclops import utility
from syclops.blender.sensor_outputs.output_interface import OutputInterface

# META DESCRIPTION
meta_description = {
    "type": "RGB",
    "format": "PNG",
    "description": "Color images from the camera",
}


class RGB(OutputInterface):
    """Generate Camera RGB output"""

    def generate_output(self, parent_class: object = None):
        with utility.RevertAfter():
            utility.configure_render()

            job_description = utility.get_job_conf()
            bpy.context.scene.cycles.use_denoising = job_description[
                "denoising_enabled"
            ]
            try:
                bpy.context.scene.cycles.denoiser = job_description[
                    "denoising_algorithm"
                ]
            except TypeError as e:
                logging.error(
                    f"Could not set denoiser to {job_description['denoising_algorithm']}. Try 'OPENIMAGEDENOISE'."
                )
                raise e
            bpy.context.scene.cycles.samples = self.config["samples"]

            if "image_compression" in job_description:
                bpy.data.scenes[
                    "Scene"
                ].render.image_settings.compression = job_description[
                    "image_compression"
                ]

            bpy.context.scene.render.image_settings.color_mode = "RGB"

            # Create subfolders
            cam_name = bpy.context.scene.camera["name"]
            # Set filename
            curr_frame = bpy.context.scene.frame_current

            output_folder = Path(f"{cam_name}", "rect")
            file_string = str(curr_frame).rjust(4, "0") + ".png"
            output_path = utility.append_output_path(output_folder)
            utility.append_output_path(file_string)
            self.compositor()

            self.check_debug_breakpoint()
            logging.info(f"Rendering RGB Image for sensor {cam_name}")
            bpy.ops.render.render(write_still=True)

            with utility.AtomicYAMLWriter(str(output_path / "metadata.yaml")) as writer:
                # Add metadata
                writer.data.update(meta_description)
                # Add current step
                writer.add_step(
                    step=curr_frame,
                    step_dicts=[{"type": "RGB", "path": str(file_string)}],
                )
                # Add expected steps
                writer.data["expected_steps"] = job_description["steps"]
                writer.data["sensor"] = cam_name
                writer.data["id"] = self.config["id"]
            logging.info("RGB output for sensor %s", cam_name)
