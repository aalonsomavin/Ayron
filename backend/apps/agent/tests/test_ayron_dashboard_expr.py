import json
import shutil
import subprocess
from pathlib import Path

import pytest
from django.conf import settings


DASHBOARD_JS = Path(settings.BASE_DIR) / "static" / "js" / "ayron-dashboard.js"


def _run_node_eval(expr: str, scope: dict) -> float:
    node_script = """
const fs = require('fs');
global.window = global;
eval(fs.readFileSync(process.argv[1], 'utf8'));
const result = AyronDashboard.evaluateExpression(process.argv[2], JSON.parse(process.argv[3]));
console.log(JSON.stringify(result));
"""
    proc = subprocess.run(
        ["node", "-e", node_script, str(DASHBOARD_JS), expr, json.dumps(scope)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout.strip())


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
class TestAyronDashboardExpression:
    def test_multiply(self):
        assert _run_node_eval("units * price", {"units": 1000, "price": 42.5}) == 42500

    def test_parentheses_and_chain(self):
        scope = {"units": 1000, "price": 42.5, "fixed_cost": 30000}
        revenue = _run_node_eval("units * price", scope)
        scope["revenue"] = revenue
        margin = _run_node_eval("(revenue - fixed_cost) / revenue", scope)
        assert round(margin, 4) == round((42500 - 30000) / 42500, 4)

    def test_min_function(self):
        assert _run_node_eval("min(a, b)", {"a": 10, "b": 3}) == 3

    def test_division_by_zero_returns_nan(self):
        result = _run_node_eval("a / b", {"a": 1, "b": 0})
        assert result is None

    def test_unknown_variable_raises(self):
        with pytest.raises(RuntimeError):
            _run_node_eval("missing + 1", {})
