from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from apps.agent.runner import create_agent
from apps.agent.skills import (
    PLATFORM_SKILLS_PATH,
    WORKSPACE_ROOT,
    build_agent_backend,
    get_platform_skill_sources,
    get_platform_skills_dir,
)
from apps.chat.models import Conversation
from deepagents.backends import CompositeBackend, StateBackend
from deepagents.backends.filesystem import FilesystemBackend


@pytest.mark.django_db
class TestPlatformSkills:
    def test_platform_skills_dir_exists(self):
        skills_dir = get_platform_skills_dir()
        assert skills_dir.is_dir()
        assert (skills_dir / "docx-documents" / "SKILL.md").is_file()
        assert (skills_dir / "html-reports" / "SKILL.md").is_file()

    def test_html_reports_guidelines_exist(self):
        skills_dir = get_platform_skills_dir() / "html-reports"
        assert (skills_dir / "GUIDELINES.md").is_file()
        assert (skills_dir / "starter-dashboard.html").is_file()

    def test_html_reports_skill_references_guidelines(self):
        skills_dir = get_platform_skills_dir() / "html-reports"
        skill_path = skills_dir / "SKILL.md"
        body = skill_path.read_text(encoding="utf-8")
        assert "GUIDELINES.md" in body
        assert "publish_html_artifact" in body
        assert "hydrate_html_artifact" in body
        assert "validate_html_artifact" in body
        assert "write_todos" in body
        assert "append_html_report_block" not in body
        assert "ay-dash-tabs--section" in body
        assert "ay-dash-calculator" in (skills_dir / "GUIDELINES.md").read_text(encoding="utf-8")
        guidelines = (skills_dir / "GUIDELINES.md").read_text(encoding="utf-8")
        assert "ay-dash-tabs--section" in guidelines
        assert "data-panels-target" in guidelines
        assert "create_html_dashboard_report" not in body
        assert "ay-dash-page" in body or "ay-dash-" in body
        assert "Dos tipos de entregable" in body
        assert "expandida" in body.lower()

    def test_docx_skill_frontmatter(self):
        skill_path = get_platform_skills_dir() / "docx-documents" / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        frontmatter, body = text.split("---\n", 2)[1:]
        meta = yaml.safe_load(frontmatter)
        assert meta["name"] == "docx-documents"
        assert "docx" in meta["description"].lower()
        assert "create_document" in body
        assert "write_todos" in body
        assert "python-docx" in body
        assert "Calidad y formato" in body

    def test_platform_skill_sources(self):
        assert get_platform_skill_sources() == [PLATFORM_SKILLS_PATH]

    def test_create_agent_passes_platform_skills(self, db):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="skilluser", password="pass")
        conversation = Conversation.objects.create(user=user)

        with patch("apps.agent.runner.create_deep_agent") as mock_create:
            mock_create.return_value = object()
            create_agent(conversation)

        kwargs = mock_create.call_args.kwargs
        assert kwargs["skills"] == [PLATFORM_SKILLS_PATH]
        backend = kwargs["backend"]
        assert isinstance(backend, CompositeBackend)
        assert isinstance(backend.default, StateBackend)
        assert isinstance(backend.routes[PLATFORM_SKILLS_PATH], FilesystemBackend)
        assert backend.artifacts_root == WORKSPACE_ROOT
        assert kwargs["permissions"]
        assert len(kwargs["middleware"]) == 2
        assert kwargs["middleware"][0].__class__.__name__ == "DeliverableGuardMiddleware"
        assert kwargs["middleware"][1].__class__.__name__ == "ToolFailureFeedbackMiddleware"
        assert kwargs["checkpointer"] is not None
