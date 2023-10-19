import os
import threading
import time
from pathlib import Path

import ruamel.yaml as yaml
from filelock import FileLock
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import MofNCompleteColumn, Progress
from rich.status import Status


class ProgressTracker:
    def __init__(self, folder):
        self.folder = folder
        self.output_dicts = {}
        self.color_index = 0
        self.colors = ["[yellow]", "[red]", "[green]", "[magenta]", "[cyan]", "[blue]"]

    def __enter__(self):
        self.running = True
        self.thread = threading.Thread(target=self.scan)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.running = False
        self.thread.join()

        errors = self.check_errors()
        if errors:
            # Print to rich console in a panel
            console = Console()
            errors_string = ""
            for error in errors:
                errors_string += error
            console.print(Panel(errors_string, title="[red bold] ERRORS"))

    def check_errors(self):
        # Check for errors in the logs and return all lines after the first "error"
        try:
            with open(Path(self.folder) / "blender.log", "r") as logs_file:
                lines = logs_file.readlines()
            for i, line in enumerate(lines):
                if line.lower().startswith("error"):
                    return lines[i:]
        except (FileNotFoundError, IndexError):
            pass

    def scan(self):
        console = Console()
        main_status = Status("Waiting for first generated data")
        log_status = Status("Waiting for logs", spinner="earth")
        prog_bar_dict = {}
        with Live(Panel(Group(main_status, Panel(log_status, title="LAST LOG")))) as lv:
            while self.running:
                curr_blender_samples = ""
                try:
                    with open(Path(self.folder) / "blender.log", "r") as logs_file:
                        lines = logs_file.readlines()

                    if "ViewLayer | Sample " in lines[-1]:
                        curr_blender_samples = (
                            " [blue]Sample: " + lines[-1].split(" ")[-1][:-1]
                        )
                except (FileNotFoundError, IndexError):
                    pass
                # Read last line in logs file
                try:
                    with open(Path(self.folder) / "logs.log", "r") as logs_file:
                        lines = logs_file.readlines()
                    # String of last 3 lines
                    try:
                        last_lines = "".join(lines[-3:])[:-1]
                        # Add spaces infront of 2nd and 3rd line for correct indentation
                        last_lines = last_lines.replace("\n", "\n    ")
                        log_status.update(last_lines + curr_blender_samples)
                    except IndexError:
                        log_status.update(lines[-1][:-1] + curr_blender_samples)
                except FileNotFoundError:
                    pass
                # Scan the folder and its subfolders
                for root, dirs, files in os.walk(self.folder):
                    metadata_files = [f for f in files if f.endswith("metadata.yaml")]
                    for file in metadata_files:
                        # Acquire a lock on the file
                        lock = FileLock(os.path.join(root, file + ".lock"))
                        with lock.acquire():
                            # Read the contents of the output_meta.yaml file
                            with open(os.path.join(root, file), "r") as f:
                                self.output_dicts[root] = yaml.safe_load(f)
                for _, output_dict in self.output_dicts.items():
                    main_status.update("[bold white]Generating Data...")
                    # Check if the output_dict is valid
                    if output_dict is not None:
                        expected_steps = output_dict["expected_steps"]
                        len_generated_steps = len(output_dict["steps"])
                        sensor = output_dict["sensor"]
                        output_type = output_dict["type"]
                        prog_dict = {"sensor": sensor, "type": output_type}
                        # Check if output is already a progress bar
                        if sensor in prog_bar_dict.keys():
                            progress_bar_exists = False
                            for progress_bar in prog_bar_dict[sensor].renderable.tasks:
                                if progress_bar.fields["fields"] == prog_dict:
                                    if progress_bar.completed < len_generated_steps:
                                        prog_bar_dict[sensor].renderable.update(
                                            progress_bar.id, advance=1
                                        )
                                    progress_bar_exists = True
                            if not progress_bar_exists:
                                prog_bar_dict[sensor].renderable.add_task(
                                    f"{self.colors[self.color_index]} {output_type}",
                                    completed=len_generated_steps,
                                    total=expected_steps,
                                    fields=prog_dict,
                                )
                                self.color_index = (self.color_index + 1) % len(
                                    self.colors
                                )
                        else:
                            prog_bar_dict[sensor] = Panel(
                                Progress(
                                    *Progress.get_default_columns(),
                                    MofNCompleteColumn(),
                                    console=console,
                                    transient=True,
                                    speed_estimate_period=300,
                                ),
                                title=f"[bold]Sensor: [blue]{sensor}",
                                title_align="left",
                            )
                            lv.update(
                                Panel(
                                    Group(
                                        main_status,
                                        *prog_bar_dict.values(),
                                        Panel(log_status, title="LOGS"),
                                    )
                                )
                            )
                time.sleep(1)
                errors = self.check_errors()
                if errors:
                    self.running = False
