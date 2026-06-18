from apps.agent.tools.html_insight import normalize_insight_markup
from apps.agent.tools.html_sanitize import normalize_agent_html


def test_normalize_insight_replaces_custom_logo():
    html = """
    <div class="ay-dash-card ay-dash-card--insight">
      <div class="ay-dash-insight-head">
        <div class="ay-dash-insight-logo"><span>$</span></div>
        <span class="ay-dash-insight-brand">Ayron</span>
        <span class="ay-dash-insight-kind">insight</span>
      </div>
      <div class="ay-dash-insight-text">La facturación creció.</div>
    </div>
    """
    result = normalize_insight_markup(html)
    assert "#6fe6cf" in result
    assert "<span>$</span>" not in result


def test_normalize_insight_injects_head_when_missing():
    html = """
    <div class="ay-dash-card ay-dash-card--insight">
      <div class="ay-dash-insight-text">La facturación creció.</div>
    </div>
    """
    result = normalize_insight_markup(html)
    assert "ay-dash-insight-head" in result
    assert "ay-dash-insight-brand" in result
    assert "ay-dash-insight-kind" in result
    assert "#6fe6cf" in result


def test_normalize_insight_strips_rogue_icon_and_injects_head():
    html = """
    <div class="ay-dash-card ay-dash-card--insight">
      <div><svg viewBox="0 0 24 24"><path d="M12 2v20"></path></svg></div>
      <div class="ay-dash-insight-text">La facturación creció.</div>
    </div>
    """
    result = normalize_insight_markup(html)
    assert result.count("ay-dash-insight-head") == 1
    assert "<path d=\"M12 2v20\"></path>" not in result
    assert "ay-dash-insight-text" in result


def test_normalize_insight_dedupes_existing_heads():
    html = """
    <div class="ay-dash-card ay-dash-card--insight">
      <div class="ay-dash-insight-head">
        <div class="ay-dash-insight-logo"></div>
        <span class="ay-dash-insight-brand">Ayron</span>
        <span class="ay-dash-insight-kind">insight</span>
      </div>
      <div class="ay-dash-insight-head">
        <div class="ay-dash-insight-logo"></div>
        <span class="ay-dash-insight-brand">Ayron</span>
        <span class="ay-dash-insight-kind">insight</span>
      </div>
      <div class="ay-dash-insight-text">La facturación creció.</div>
    </div>
    """
    result = normalize_insight_markup(html)
    assert result.count("ay-dash-insight-head") == 1
    assert result.count("ay-dash-insight-brand") == 1


def test_normalize_insight_keeps_single_head_with_extra_classes():
    html = """
    <div class="ay-dash-card ay-dash-card--insight">
      <div class="ay-dash-insight-head is-primary">
        <div class="ay-dash-insight-logo"></div>
        <span class="ay-dash-insight-brand">Ayron</span>
        <span class="ay-dash-insight-kind">insight</span>
      </div>
      <div class="ay-dash-insight-text">La facturación creció.</div>
    </div>
    """
    result = normalize_insight_markup(html)
    assert result.count("ay-dash-insight-head") == 1
    assert "is-primary" in result
    html = """
    <div class="ay-dash-page">
      <div class="ay-dash-card ay-dash-card--insight">
        <div class="ay-dash-insight-text">Resumen.</div>
      </div>
    </div>
    """
    result = normalize_agent_html(html)
    assert "ay-dash-insight-head" in result["body_html"]
    assert "#6fe6cf" in result["body_html"]
