### 4.1 What the gate does

**One burst, then silence.** The gate chops the continuous 40 kHz drive into 4 ms on / 96 ms off (10 Hz). The mic is analysed only in the first few milliseconds after the direct arrival, before the first floor bounce.

**Why.** The 54.75° null is a −25 to −30 dB cancellation. In a normal room the direct wave is followed by floor, ceiling and wall reflections; a continuous drive fills the room with reverberation, and that reflected field — even 10–20 dB below the direct — fills the null. A burst from silence measures the direct path alone.

**Timing (Figure 3).** At 3 m the first arrival is 8.75 ms after the gate edge; 0.79 ms aperture fill plus ~0.7 ms settling leave a 1.6–4.0 ms analysis window; the first floor bounce is at +5.07 ms. The 96 ms off lets the room decay ~90 dB (RT60 ≈ 70 ms at 40 kHz).

**Trigger.** The primary outputs the gate on MISC_C (scope Ch2); the secondary follows it on MISC_F, so both boards pulse together. It does not steer or shape the beam — the frame does that; it only decides when the drive is on.
