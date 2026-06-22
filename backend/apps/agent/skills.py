from pathlib import Path

from django.conf import settings
from deepagents.backends import CompositeBackend, StateBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemPermission

SKILLS_DIR_NAME = "skills"
PLATFORM_SKILLS_PATH = f"/{SKILLS_DIR_NAME}/"
WORKSPACE_ROOT = "/workspace/"


def get_platform_skills_dir() -> Path:
    return Path(settings.BASE_DIR) / SKILLS_DIR_NAME


def get_platform_skill_sources() -> list[str]:
    return [PLATFORM_SKILLS_PATH]


def build_agent_backend() -> CompositeBackend:
    skills_dir = get_platform_skills_dir()
    return CompositeBackend(
        default=StateBackend(),
        routes={
            PLATFORM_SKILLS_PATH: FilesystemBackend(
                root_dir=str(skills_dir),
                virtual_mode=True,
            ),
        },
        artifacts_root=WORKSPACE_ROOT,
    )


def get_platform_skill_permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(
            paths=[f"{PLATFORM_SKILLS_PATH}**"],
            mode="deny",
            operations=["write"],
        ),
    ]
