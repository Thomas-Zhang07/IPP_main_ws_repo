"""Optimal 2-/3-board search: fast evaluator, rubrics, front, report."""

from .model import (
    VARIANTS,
    Candidate,
    array_factor,
    board_factor,
    commanded_amp,
    direction_grid,
    element_amplitude,
    field_fast,
    from_key,
    pair,
    triple,
)

__all__ = [
    "VARIANTS",
    "Candidate",
    "array_factor",
    "board_factor",
    "commanded_amp",
    "direction_grid",
    "element_amplitude",
    "field_fast",
    "from_key",
    "pair",
    "triple",
]
