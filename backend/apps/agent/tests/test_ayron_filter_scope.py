import json
import shutil
import subprocess
from pathlib import Path

import pytest
from django.conf import settings


DASHBOARD_JS = Path(settings.BASE_DIR) / "static" / "js" / "ayron-dashboard.js"
CHART_JS = Path(settings.BASE_DIR) / "static" / "js" / "ayron-chart.js"


def _run_node_scope(script: str) -> str:
    node_script = """
const fs = require('fs');
global.window = global;
eval(fs.readFileSync(process.argv[1], 'utf8'));
eval(process.argv[2]);
"""
    proc = subprocess.run(
        ["node", "-e", node_script, str(DASHBOARD_JS), script],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc.stdout.strip()


def _run_node_chart(script: str) -> str:
    node_script = """
const fs = require('fs');
global.window = global;
eval(fs.readFileSync(process.argv[1], 'utf8'));
eval(process.argv[2]);
"""
    proc = subprocess.run(
        ["node", "-e", node_script, str(CHART_JS), script],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc.stdout.strip()


ROWS = [
    {"year": 2009, "country": "USA", "genre": "Rock", "amount": 12.5, "invoice_id": "INV-1"},
    {"year": 2009, "country": "USA", "genre": "Jazz", "amount": 8.2, "invoice_id": "INV-2"},
    {"year": 2010, "country": "Canada", "genre": "Rock", "amount": 6.1, "invoice_id": "INV-3"},
    {"year": 2010, "country": "Brazil", "genre": "Rock", "amount": 4.8, "invoice_id": "INV-4"},
]

SLICERS = [
    {"id": "year", "field": "year", "label": "Año"},
    {"id": "country", "field": "country", "label": "País"},
    {"id": "genre", "field": "genre", "label": "Género"},
]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
class TestAyronFilterScope:
    def test_rows_for_excludes_dimension(self):
        script = f"""
const rows = {json.dumps(ROWS)};
const slicers = {json.dumps(SLICERS)};
const scope = AyronDashboard.createFilterScope(rows, slicers);
scope.toggle('country', 'USA');
const filtered = scope.rowsFor('country');
console.log(JSON.stringify(filtered.map(r => r.invoice_id)));
"""
        result = json.loads(_run_node_scope(script))
        assert set(result) == {"INV-1", "INV-2", "INV-3", "INV-4"}

    def test_toggle_updates_kpi_aggregate(self):
        script = f"""
const rows = {json.dumps(ROWS)};
const slicers = {json.dumps(SLICERS)};
const scope = AyronDashboard.createFilterScope(rows, slicers);
const totalAll = scope.aggregate('sum:amount', null, null);
scope.toggle('country', 'USA');
const totalUsa = scope.aggregate('sum:amount', null, null);
console.log(JSON.stringify({{ totalAll, totalUsa }}));
"""
        result = json.loads(_run_node_scope(script))
        assert result["totalAll"] == 31.6
        assert result["totalUsa"] == 20.7

    def test_clear_all_restores_state(self):
        script = f"""
const rows = {json.dumps(ROWS)};
const slicers = {json.dumps(SLICERS)};
const scope = AyronDashboard.createFilterScope(rows, slicers);
scope.toggle('year', 2009);
scope.toggle('country', 'USA');
scope.clearAll();
console.log(JSON.stringify(scope.getState()));
"""
        result = json.loads(_run_node_scope(script))
        assert result == {"year": [], "country": [], "genre": []}

    def test_aggregate_by_dimension_excludes_self(self):
        script = f"""
const rows = {json.dumps(ROWS)};
const slicers = {json.dumps(SLICERS)};
const scope = AyronDashboard.createFilterScope(rows, slicers);
scope.toggle('genre', 'Rock');
const byCountry = scope.aggregate('sum:amount', 'country', 'country');
console.log(JSON.stringify(byCountry));
"""
        result = json.loads(_run_node_scope(script))
        assert result["labels"] == ["Brazil", "Canada", "USA"]
        assert result["values"] == [4.8, 6.1, 12.5]

    def test_cross_filter_has_tracks_selection(self):
        script = f"""
const rows = {json.dumps(ROWS)};
const slicers = {json.dumps(SLICERS)};
const scope = AyronDashboard.createFilterScope(rows, slicers);
scope.toggle('country', 'USA');
console.log(JSON.stringify({{
  hasUsa: scope.has('country', 'USA'),
  hasCanada: scope.has('country', 'Canada'),
  state: scope.getState().country
}}));
"""
        result = json.loads(_run_node_scope(script))
        assert result["hasUsa"] is True
        assert result["hasCanada"] is False
        assert result["state"] == ["USA"]

    def test_chart_live_payload_aggregates(self):
        script = f"""
const rows = {json.dumps(ROWS)};
const slicers = {json.dumps(SLICERS)};
const scope = AyronDashboard.createFilterScope(rows, slicers);
const node = {{
  dataset: {{
    dimension: 'country',
    measure: 'sum:amount',
    crossFilter: 'country',
    chartId: 'x'
  }}
}};
global.document = {{
  documentElement: {{}},
  getElementById: () => ({{
    textContent: JSON.stringify({{
      chart_type: 'bar',
      title: 'Por país',
      datasets: [{{ label: 'Importe', color_index: 0 }}],
      value_format: 'currency'
    }})
  }})
}};
global.getComputedStyle = () => ({{ getPropertyValue: () => '#3b6ef6' }});
const payload = AyronChart.buildLivePayload(scope, node);
console.log(JSON.stringify({{ labels: payload.labels, data: payload.datasets[0].data }}));
"""
        result = json.loads(_run_node_chart(script))
        assert result["labels"] == ["Brazil", "Canada", "USA"]
        assert result["data"] == [4.8, 6.1, 20.7]
