"""Sampled robustness maxima: 4-bit phase, mechanical/board-level errors, k drift
and the element-pattern envelope. Absolute values, not deltas."""

from __future__ import annotations

import numpy as np

import constants as C

from . import metrics, model

SEED = 20261126
QUANT_LEVELS = 16


def _positions(cand):
    n = model.N_SIDE
    r, c = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    local = np.column_stack([c.ravel() * model.PITCH, r.ravel() * model.PITCH])
    origins = cand.origins
    return (origins[:, None, :] + local[None, :, :]).reshape(-1, 2)


def _commanded_dir(u0, v0):
    w2 = 1.0 - u0 * u0 - v0 * v0
    return np.array([u0, v0, np.sqrt(max(w2, 0.0))])


def _sl_of(field, dirs, d0, cmd):
    comp = metrics.sl_components(np.abs(field), dirs, d0, cmd)
    return comp["sl_cmd"]


def _state(cand, theta_deg, phi_deg):
    t, p = np.radians(theta_deg), np.radians(phi_deg)
    return np.sin(t) * np.cos(p), np.sin(t) * np.sin(p)


def sl_4bit(cand, states, variant="mean", n_offsets=8, du=0.012):
    dirs, _, _, _ = model.direction_grid(du)
    pos = _positions(cand)
    elem = model.element_amplitude(dirs, variant)
    step = 2.0 * np.pi / QUANT_LEVELS
    worst = -np.inf
    for theta, phi in states:
        u0, v0 = _state(cand, theta, phi)
        d0 = _commanded_dir(u0, v0)
        ang = -C.WAVE_NUMBER * (u0 * pos[:, 0] + v0 * pos[:, 1])
        for k_off in range(n_offsets):
            offset = k_off * step / n_offsets
            q = np.round((ang - offset) / step) * step + offset
            w = np.exp(1j * q)
            field = np.empty(dirs.shape[0], dtype=complex)
            for s in range(0, dirs.shape[0], 2048):
                d = dirs[s:s + 2048]
                field[s:s + 2048] = (
                    np.exp(1j * C.WAVE_NUMBER * (d[:, :2] @ pos.T)) @ w
                ) * elem[s:s + 2048]
            cmd_field = np.abs(np.sum(
                w * model.element_amplitude(d0[None, :], variant) * np.exp(
                    1j * C.WAVE_NUMBER * (d0[:2] @ pos.T))))
            worst = max(worst, _sl_of(field, dirs, d0, cmd_field))
    return float(worst)


def _board_field(cand, dirs, u0, v0, variant, origins, gains, phases, k=None):
    kk = C.WAVE_NUMBER if k is None else k
    u = dirs[:, 0] - u0
    v = dirs[:, 1] - v0
    # The command uses nominal geometry. Unknown placement errors change
    # propagation but do not reprogram the drive phases.
    board_phase = (dirs[:, :2] @ origins.T
                   - np.array([u0, v0]) @ cand.origins.T)
    lat = np.exp(1j * kk * board_phase)
    lat = lat @ (np.asarray(gains) * np.exp(1j * np.asarray(phases)))
    return (model.element_amplitude(dirs, variant) * model.board_factor(u, k=kk)
            * model.board_factor(v, k=kk) * lat)


def _perturbed_origins(cand, dseams, doffsets):
    xs = [0.0]
    for seam, ds in zip(cand.seams_m, dseams):
        xs.append(xs[-1] + model.SPAN + seam + ds)
    return np.column_stack([np.asarray(xs),
                            np.asarray(cand.offsets_m) + np.asarray(doffsets)])


def _sl_mech_draw(cand, dirs, states, variant, dseams, doffsets, gains,
                  phases):
    origins = _perturbed_origins(cand, dseams, doffsets)
    worst = -np.inf
    for theta, phi in states:
        u0, v0 = _state(cand, theta, phi)
        d0 = _commanded_dir(u0, v0)
        field = _board_field(cand, dirs, u0, v0, variant, origins, gains,
                             phases)
        cmd = abs(_board_field(cand, d0[None, :], u0, v0, variant, origins,
                               gains, phases)[0])
        worst = max(worst, _sl_of(field, dirs, d0, cmd))
    return float(worst)


def _lhs(rng, n_samples, n_dim, low, high):
    ranks = np.column_stack([rng.permutation(n_samples) for _ in range(n_dim)])
    strata = (ranks + rng.random((n_samples, n_dim))) / n_samples
    return low + (high - low) * strata


def sl_mech(cand, states, variant="mean", n_draws=100, du=0.012):
    dirs, _, _, _ = model.direction_grid(du)
    rng = np.random.default_rng(SEED)
    n = cand.n_boards
    worst = -np.inf
    seams = _lhs(rng, n_draws, n - 1, -2e-4, 2e-4)
    offsets = _lhs(rng, n_draws, n - 1, -2e-4, 2e-4)
    gains = 10.0 ** (_lhs(rng, n_draws, n, -1.0, 1.0) / 20.0)
    phases = np.radians(_lhs(rng, n_draws, n, -10.0, 10.0))
    for d in range(n_draws):
        dseams = seams[d]
        doffsets = np.concatenate([[0.0], offsets[d]])
        worst = max(worst, _sl_mech_draw(cand, dirs, states, variant,
                                         dseams, doffsets, gains[d],
                                         phases[d]))
    return float(worst)


def sl_drift(cand, states, variant="mean", epsilons=(0.0035, -0.0035),
             du=0.012):
    dirs, _, _, _ = model.direction_grid(du)
    worst = -np.inf
    for eps in epsilons:
        k1 = C.WAVE_NUMBER * (1.0 + eps)
        ratio = C.WAVE_NUMBER / k1
        for theta, phi in states:
            u0, v0 = _state(cand, theta, phi)
            d0 = _commanded_dir(u0, v0)
            u = dirs[:, 0] - ratio * u0
            v = dirs[:, 1] - ratio * v0
            lat = np.exp(1j * k1 * (u[:, None] * cand.origins[None, :, 0]
                                    + v[:, None] * cand.origins[None, :, 1])
                         ).sum(axis=1)
            field = (model.element_amplitude(dirs, variant)
                     * model.board_factor(u, k=k1)
                     * model.board_factor(v, k=k1) * lat)
            uc = u0 * (1.0 - ratio)
            vc = v0 * (1.0 - ratio)
            latc = np.exp(1j * k1 * (uc * cand.origins[:, 0]
                                     + vc * cand.origins[:, 1])).sum()
            cmd = abs(model.element_amplitude(d0[None, :], variant)[0]
                      * model.board_factor(uc, k=k1)
                      * model.board_factor(vc, k=k1) * latc)
            worst = max(worst, _sl_of(field, dirs, d0, cmd))
    return float(worst)


def sl_elem(cand, states, du=0.012):
    dirs, _, _, _ = model.direction_grid(du)
    worst = -np.inf
    for variant in model.VARIANTS:
        worst = max(worst, metrics.score_states(cand, du, states, variant,
                                                dirs=dirs)["SL_cmd"])
    return float(worst)


def robust(cand, states, n_draws=100, du=0.012):
    out = {
        "SL_4bit": sl_4bit(cand, states, du=du),
        "SL_mech": sl_mech(cand, states, n_draws=n_draws, du=du),
        "SL_drift": sl_drift(cand, states, du=du),
        "SL_elem": sl_elem(cand, states, du=du),
    }
    out["robust_max"] = max(out.values())
    return out
