"""Read the shipped HTML just as the offline viewer does."""
import base64
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def payload():
    page = (ROOT / "docs/array-demo.html").read_text(encoding="utf-8")
    return json.loads(page.split('<script id="payload" type="application/json">')[1]
                      .split("</script>", 1)[0])


def test_demo_contains_both_fields_for_all_six_layouts(payload):
    assert len(payload["layouts"]) == 6
    saved = json.loads((ROOT / "data/search2/leaders.json").read_text(encoding="utf-8"))
    assert set(saved.values()) <= {g["key"] for g in payload["layouts"]}
    for layout in payload["layouts"]:
        for angle in payload["commands"]:
            for element in ("measured", "isotropic"):
                for observe in ("far", "2m"):
                    raw = base64.b64decode(layout["states"][f"{angle}/{element}/{observe}"])
                    assert len(raw) == payload["nt"]*payload["np"] + 721


def test_demo_preserves_order_and_near_field_reference(payload):
    single = payload["layouts"][0]["states"]
    def level(state, angle):
        return base64.b64decode(single[state])[-721 + round((angle+90)*4)]/5 - 50
    assert level("0/isotropic/far", 54.75) == 0
    assert level("0/measured/far", 54.75) == pytest.approx(-28.2, abs=.2)
    assert level("20/isotropic/far", 20) == 0
    assert level("0/measured/2m", 0) < level("0/measured/far", 0)
