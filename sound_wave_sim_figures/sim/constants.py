"""Physical constants for the 16x16 SonicSurface boards.

Mirrors demo/emitters.py and demo/acoustics.py; copied rather than imported
because this workspace must also model tilted, non-planar arrangements that
those modules reject.
"""

from __future__ import annotations

import math

FREQUENCY_HZ = 40000.0
SOUND_SPEED_MPS = 343.0
WAVELENGTH_M = SOUND_SPEED_MPS / FREQUENCY_HZ      # 8.575 mm
WAVE_NUMBER = 2.0 * math.pi / WAVELENGTH_M
TWO_PI = 2.0 * math.pi

N_SIDE = 16
N_PER_BOARD = N_SIDE * N_SIDE
PITCH_M = 0.0105                                   # 10.5 mm
SPAN_M = (N_SIDE - 1) * PITCH_M                    # 157.5 mm

ELEMENT_DIAMETER_M = 0.010                         # 10 mm piston
ELEMENT_RADIUS_M = 0.5 * ELEMENT_DIAMETER_M

# PCB outline in the fixture orientation (boards rotated 90 deg):
# 168.402 x 185.092 mm, element grid inset by these margins.
PCB_WIDTH_M = 0.168402
PCB_HEIGHT_M = 0.185092
MARGIN_LEFT_M = 0.005406
MARGIN_RIGHT_M = 0.005496
MARGIN_BOTTOM_M = 0.013706
MARGIN_TOP_M = 0.013886

# Element seam with the PCB edges butted (5.496 + 5.406).
BUTT_SEAM_M = MARGIN_RIGHT_M + MARGIN_LEFT_M        # 10.902 mm

# Current fixture: seam 15.750 mm, half-pitch y offset 5.250 mm.
CURRENT_SEAM_M = 0.015750
CURRENT_OFFSET_Y_M = 0.5 * PITCH_M                  # 5.250 mm

GRATING_ANGLE_DEG = math.degrees(math.asin(WAVELENGTH_M / PITCH_M))  # 54.75 deg

DB_FLOOR = -40.0
