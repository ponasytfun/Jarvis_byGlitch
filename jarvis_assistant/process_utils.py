from __future__ import annotations

import subprocess
from pathlib import Path

import psutil

from jarvis_assistant.models import JarvisConfig
from jarvis_assistant.paths import expand_windows_path


FORBIDDEN_BRAVE_ARGS = (
    "--user-data-dir",
    "--guest",
    "--incognito",
    "--profile-directory",
)


def path_exists(path_value: str) -> bool:
    expanded = expand_windows_path(path_value)
    return bool(expanded) and Path(expanded).exists()


def build_command(executable: str, args: list[str] | None = None) -> list[str]:
    expanded_executable = expand_windows_path(executable)
    if not expanded_executable:
        raise ValueError("Executable path is empty.")
    return [expanded_executable, *[expand_windows_path(item) for item in (args or [])]]


def build_target_command(target_name: str, config: JarvisConfig) -> list[str]:
    paths = config.paths
    if target_name == "brave":
        validate_brave_args(paths.brave_args)
        return build_command(paths.brave_path, paths.brave_args)
    if target_name == "vscode":
        return build_command(paths.vscode_path, paths.vscode_args)
    if target_name == "discord":
        return build_command(paths.discord_path, paths.discord_launch_args)
    if target_name == "obs":
        return build_command(paths.obs_path, paths.obs_args)
    raise KeyError(f"Unknown target name: {target_name}")


def build_brave_url_command(config: JarvisConfig, url: str) -> list[str]:
    validate_brave_args(config.paths.brave_args)
    return build_command(config.paths.brave_path, [*config.paths.brave_args, url])


def get_working_directory(executable: str) -> str | None:
    expanded = expand_windows_path(executable)
    if not expanded:
        return None
    return str(Path(expanded).parent)


def validate_brave_args(args: list[str]) -> None:
    for item in args:
        lowered = item.casefold()
        if lowered.startswith(FORBIDDEN_BRAVE_ARGS):
            raise ValueError(
                "Brave args may not include temporary profile, guest, or incognito flags."
            )


def is_any_process_running(process_names: list[str]) -> bool:
    normalized = {item.casefold() for item in process_names if item}
    if not normalized:
        return False
    for process in psutil.process_iter(attrs=["name"]):
        name = (process.info.get("name") or "").casefold()
        if name in normalized:
            return True
    return False


def launch_subprocess(command: list[str], executable_for_cwd: str) -> subprocess.Popen:
    cwd = get_working_directory(executable_for_cwd)
    return subprocess.Popen(command, cwd=cwd or None)
