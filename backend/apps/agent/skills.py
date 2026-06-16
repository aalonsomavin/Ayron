from pathlib import Path

from django.conf import settings
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemPermission

SKILLS_DIR_NAME = "skills"
PLATFORM_SKILLS_PATH = f"/{SKILLS_DIR_NAME}/"


def get_platform_skills_dir() -> Path:
    return Path(settings.BASE_DIR) / SKILLS_DIR_NAME


def get_platform_skill_sources() -> list[str]:
    return [PLATFORM_SKILLS_PATH]


def build_agent_backend() -> FilesystemBackend:
    return FilesystemBackend(
        root_dir=settings.BASE_DIR,
        virtual_mode=True,
    )


def get_platform_skill_permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(
            paths=[f"{PLATFORM_SKILLS_PATH}**"],
            mode="deny",
            operations=["write"],
        ),
    ]
