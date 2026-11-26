"""Validation: the model must reproduce the report's numbers before any
figure is trusted."""

from __future__ import annotations

import math
import pathlib
import sys
import zipfile

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "sim"))

import constants as C  # noqa: E402
import field  # noqa: E402
import geometry  # noqa: E402


def test_single_board_matches_sonicsurface_pick_place():
    repo = pathlib.Path(__file__).resolve().parents[2]
    archive = (repo / "SonicSurface/Electronics/16x16 10mm transducers SMD PCB Gerbers"
               / "SonicSurface1.2_2Layers_183x169.zip")
    with zipfile.ZipFile(archive) as z:
        lines = z.read("Project Outputs for SonicSurface/Pick Place for Main.txt").splitlines()
    rows = [row for line in lines if len(row := line.split()) > 3 and row[1] == b"Transducer_10mm"]
    centers = np.array([[float(x.removesuffix(b"mil")) for x in row[2:4]] for row in rows]) * 25.4e-6
    centers -= centers.mean(axis=0)
    model = geometry.single().positions[:, :2]
    assert len(centers) == len(model) == 256
    distances = np.linalg.norm(model[:, None, :] - centers[None, :, :], axis=2)
    assert len(set(distances.argmin(axis=1))) == len(model)
    assert distances.min(axis=1).max() < 1e-6


def _metrics(layout, taper="uniform", du=0.008):
    return field.analyse(
        layout.positions, layout.normals, layout.amplitudes(taper), du=du
    )


def test_grating_angle():
    assert C.GRATING_ANGLE_DEG == pytest.approx(54.75, abs=0.01)


def test_single_board_grating_lobe():
    m = _metrics(geometry.single())
    assert m["lobe_54_75_db"] == pytest.approx(-12.8, abs=0.6)


def test_pair_nulls_the_exact_lobe():
    pair = _metrics(geometry.coplanar_gap())
    butt = _metrics(geometry.coplanar_butt())
    assert pair["lobe_54_75_db"] <= butt["lobe_54_75_db"] - 10.0


def test_seam_and_offset_roles():
    """The seam nulls phi=0, the half-pitch offset nulls phi=90."""
    seam_only = _metrics(geometry.pair_seam_only())
    butt = _metrics(geometry.coplanar_butt())
    # x-axis lobe (phi = 0 / 180) is cancelled by the 1.5-pitch seam...
    assert seam_only["lobe_by_az_db"]["0.0"] <= butt["lobe_54_75_db"] - 10.0
    # ...while the y-axis lobe survives without the 5.25 mm offset.
    assert seam_only["lobe_by_az_db"]["90.0"] >= butt["lobe_54_75_db"] - 1.0


def test_symmetry_single_and_pair():
    single = geometry.single()
    left = field.far_field(
        single.positions, single.normals, single.amplitudes(),
        np.array([field.dir_from_angles(30.0, 20.0)]),
    )
    right = field.far_field(
        single.positions, single.normals, single.amplitudes(),
        np.array([field.dir_from_angles(30.0, -20.0)]),
    )
    assert abs(left[0]) == pytest.approx(abs(right[0]), rel=1e-6)

    pair = geometry.coplanar_butt()
    left = field.far_field(
        pair.positions, pair.normals, pair.amplitudes(),
        np.array([field.dir_from_angles(20.0, 30.0)]),
    )
    right = field.far_field(
        pair.positions, pair.normals, pair.amplitudes(),
        np.array([field.dir_from_angles(20.0, 150.0)]),
    )
    assert abs(left[0]) == pytest.approx(abs(right[0]), rel=1e-6)


def test_butt_seam_is_physical():
    a, b = geometry.coplanar_butt().boards
    # innermost emitter columns, 10.902 mm apart, no y offset
    assert b.positions[:, 0].min() - a.positions[:, 0].max() == pytest.approx(
        C.BUTT_SEAM_M, abs=1e-9
    )
    # PCB outlines just touch: no overlap and no visible gap
    assert b.outline[:, 0].min() - a.outline[:, 0].max() == pytest.approx(0.0, abs=1e-9)


def test_v_hinge_is_butted():
    v = geometry.v_pair(120.0, "test", "test")
    a, b = v.boards
    # Both hinge edges sit at z = 0; the boards open forward (z > 0).
    assert a.outline[:, 2].min() == pytest.approx(0.0, abs=1e-9)
    assert b.outline[:, 2].min() == pytest.approx(0.0, abs=1e-9)
    assert a.outline[:, 2].max() > 0.0
    assert b.outline[:, 2].max() > 0.0
    # Faces open by 120 deg, so the normals diverge by 180 - 120 = 60 deg.
    na = a.normals[0] / np.linalg.norm(a.normals[0])
    nb = b.normals[0] / np.linalg.norm(b.normals[0])
    assert math.degrees(math.acos(float(np.dot(na, nb)))) == pytest.approx(60.0, abs=1e-6)


def test_concave_wings_converge():
    lay = geometry.concave3(30.0)
    left, centre, right = lay.boards
    # Wing normals point inward (toward +x for the left wing, -x for the right).
    assert left.normals[0][0] > 0.0
    assert right.normals[0][0] < 0.0
    # Wings sit forward of the centre plane.
    assert left.positions[:, 2].max() > 0.0
    assert right.positions[:, 2].max() > 0.0


def test_near_field_matches_far_field_axis():
    """At 50 m the near-field on-axis level must approach the far field."""
    lay = geometry.coplanar_gap()
    xs = np.array([0.0])
    zs = np.array([50.0])
    _, _, p_near = field.near_field_plane(
        lay.positions, lay.normals, lay.amplitudes(), xs, zs, 0.0
    )
    dirs = np.array([field.dir_from_angles(0.0, 0.0)])
    p_far = field.far_field(lay.positions, lay.normals, lay.amplitudes(), dirs)
    # 1/r scaling: near/far magnitude ratio must equal 1/50
    ratio = abs(p_near[0, 0]) / abs(p_far[0])
    assert ratio == pytest.approx(1.0 / 50.0, rel=5e-3)


def test_phased_near_field_converges_to_complex_far_field_off_axis():
    pos = np.array([[0, 0, 0], [0.0105, 0, 0], [0, 0.0105, 0]])
    normals = np.tile([0, 0, 1], (len(pos), 1))
    weights = np.exp(1j * np.array([0, 1.1, -0.6]))
    dirs = np.stack([field.dir_from_angles(24, a) for a in (0, 90, 180)])
    radius = 100.0
    near = field.near_field_points(pos, normals, weights, radius * dirs)
    far = field.far_field(pos, normals, weights, dirs)
    np.testing.assert_allclose(near * radius * np.exp(1j * C.WAVE_NUMBER * radius),
                               far, rtol=0.001)


def test_long_wavelength_piston_approaches_point_emitter():
    p = field.far_field(np.zeros((1, 3)), np.array([[0, 0, 1]]),
                        np.ones(1), np.array([field.dir_from_angles(55, 0)]),
                        wavenumber=0.01)
    assert abs(p[0]) == pytest.approx(1, abs=1e-8)


@pytest.mark.parametrize("du", [0.1, 0.02, 0.012, 0.004])
def test_uv_cells_tile_the_hemisphere(du):
    _, _, _, dirs, _, _, omega = field.uv_grid(du)
    assert np.all(omega > 0)
    assert np.sum(omega) == pytest.approx(2 * np.pi, rel=1e-12)
    # A dipole pointing along y has squared pressure v².
    assert omega @ dirs[:, 1]**2 == pytest.approx(2 * np.pi / 3, rel=0.015)
