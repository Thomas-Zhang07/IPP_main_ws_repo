"""Digitizer tests: the extraction must be reproducible from the jpg and
must land on the verified numbers (`directivity.csv` is derived, not hand
edited)."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import transducer.digitize as dg  # noqa: E402

IMAGE = ROOT / "transducers.jpg"
CSV = ROOT / "sim" / "transducer" / "directivity.csv"


@pytest.fixture(scope="module")
def extracted():
    if not IMAGE.exists():
        pytest.skip("source image not present")
    return dg.extract(IMAGE)


def test_check_image_rejects_wrong_shape():
    with pytest.raises(ValueError):
        dg.check_image(np.zeros((10, 10, 3), dtype=int))


def test_extract_grid(extracted):
    assert extracted["angles_deg"].shape == (361,)
    assert extracted["angles_deg"][0] == 0.0
    assert extracted["angles_deg"][-1] == 180.0
    assert extracted["db_right"].shape == (361,)
    assert extracted["db_left"].shape == (361,)
    assert extracted["db_mean_power"].shape == (361,)
    assert np.all(np.isfinite(extracted["db_mean_power"]))


def test_derived_numbers(extracted):
    assert extracted["di_db"] == pytest.approx(11.2, abs=0.6)
    assert 38.5 <= extracted["half_right_deg"] <= 43.5
    assert 41.0 <= extracted["half_left_deg"] <= 45.0


def test_missing_image_raises():
    with pytest.raises(FileNotFoundError):
        dg.extract(ROOT / "no_such_image.jpg")


def test_csv_matches_extraction(extracted):
    if not CSV.exists():
        pytest.skip("csv not generated yet")
    tab = np.genfromtxt(CSV, delimiter=",", names=True)
    rms = np.sqrt(np.mean((tab["db_mean_power"] - extracted["db_mean_power"]) ** 2))
    assert rms < 1.0
