from apps.agent.tools.html_provenance import inject_provenance_bridge


class TestInjectProvenanceBridge:
    def test_injects_script_before_body_close(self):
        html = "<html><body><div class='ay-dash-page'></div></body></html>"
        result = inject_provenance_bridge(html, "file-123")
        assert "__AYRON_PROVENANCE__" in result
        assert "ayron:provenance-open" in result
        assert "file-123" in result

    def test_skips_non_dashboard_html(self):
        html = "<div class='ay-report-prose'><p>Hola</p></div>"
        result = inject_provenance_bridge(html, "file-123")
        assert result == html

    def test_skips_without_file_id(self):
        html = "<div class='ay-dash-page'></div>"
        assert inject_provenance_bridge(html, "") == html
