"""Measured directivity of the TR4010HC transducer, digitized from its
datasheet polar chart (the only directivity data available for the part).

    from transducer import DI_DB, amplitude, level_db

    DI_DB        # 11.2 dB (Q ~ 13), 4 pi convention
    amplitude(cos_beta)   # normalized pressure factor for the far-field sum

Both halves of the asymmetric measured cut are kept in ``directivity.csv``;
``amplitude`` uses their power average as an axisymmetric pattern.
"""

from .directivity import (
    DATA_PATH,
    DI_DB,
    SOURCE,
    amplitude,
    beamwidth_6db,
    di_db,
    half_angle_6db,
    level_db,
    load,
    q,
)

__all__ = [
    "DATA_PATH",
    "DI_DB",
    "SOURCE",
    "amplitude",
    "beamwidth_6db",
    "di_db",
    "half_angle_6db",
    "level_db",
    "load",
    "q",
]
