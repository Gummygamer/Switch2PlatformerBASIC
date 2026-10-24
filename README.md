# Gravity Lab

A self-contained rolling-disk platformer for the documented **SMILEBASIC 4** API. Copy `GRAVITY.BAS` into a program slot in SMILEBASIC 4 and run it. No external graphics or sound assets are required. The corrected version has been reported working on Switch 2 with the Japanese SmileBASIC 4 demo. Broader hardware compatibility and performance have not been measured.

## Controls

| Input | Action |
| --- | --- |
| Left stick / D-pad | Apply motor torque |
| A | Jump from a supporting surface |
| B | Apply rotational brake |
| X | Respawn at checkpoint |
| Y | Toggle electromagnetic fields |

Reach the green checkpoint at 26 meters, then the finish at 52 meters. Missed jumps have a lower recovery route. Some falls require respawning. The simulation continues after finishing.

## Physics

Positions use meters, time uses seconds, mass is 1 kg, and the disk radius is 0.25 m. Rendering uses 64 pixels per meter. Four fixed 1/240-second physics steps run per 60 Hz display frame. If rendering misses its budget, simulation time slows instead of increasing the integration step.

- **Gravity:** downward acceleration of 9.81 m/s². Each step changes velocity before moving the disk. Without other forces, downward speed increases by 9.81 m/s each simulated second. There is no arbitrary fall-speed cap. Small quadratic air drag eventually opposes falling.
- **Rotation:** solid-disk inertia `I = mr²/2`; movement applies torque rather than assigning horizontal speed. Airborne torque changes spin without steering the center of mass.
- **Friction:** accumulated normal and tangential contact impulses with Coulomb bound `abs(Jt) <= mu*Jn`. Tangential contact velocity includes angular motion. Friction can produce rolling without slipping when the required impulse fits inside that bound, otherwise the disk slides. Ice has coefficient 0.025; stone is roughly 0.7; rubber is 1.1. One coefficient is used for both static and kinetic friction. Braking removes angular energy and ground friction transfers the braking effect to translation.
- **Collisions:** closest-point circle/segment contacts include slopes, walls, undersides, and rounded endpoints. Eight velocity-solver passes and three positional-correction passes handle simultaneous contacts. Low restitution applies only above a 1 m/s approach speed.
- **Moving platforms:** prescribed sinusoidal translations with contact-relative velocities. Friction transfers platform momentum. These are externally powered, infinite-mass bodies.
- **Jumping:** an active impulse along the support normal sets a minimum 5.8 m/s separating velocity relative to the platform, preserving existing tangential momentum. A 0.12-second input buffer helps timing; gravity remains unchanged during jumps.
- **Electromagnetism:** the charged disk obeys the point-charge Lorentz force `F = q(E + v × B)`, with `q = +1 C`. The cyan region applies an upward 5 N/C electric field. The purple region applies a 1.6 T magnetic field into the screen. Coordinates have positive Y downward. A Boris magnetic rotation preserves translational speed in a magnetic-only step, with symmetric gravity/electric half-kicks.

The fields are prescribed, idealized regions with abrupt boundaries. This is not a Maxwell field solver: there are no self-fields, radiation, charge redistribution, induction from switching fields, electromagnetic torque, or interactions between multiple charged bodies. Values are chosen for visible gameplay effects.

Collision detection is discrete, with small substeps; sufficiently extreme velocities can tunnel through a segment. Segments have no volume and are solid from both sides. The solver is an approximation, especially at joins and multiple contacts. The rolling disk avoids pretending that an animated humanoid is a complete biomechanical simulation.

## Adjusting the game

`G`, `DT`, `R`, `M`, and `CHARGE` are near the top. If changing mass/radius, keep the derived inverse inertia `II` calculation. World `DATA` rows contain endpoint coordinates, friction coefficient, horizontal/vertical motion amplitudes, angular frequency, and phase. Keep segment lengths nonzero. Increase the `DATA` count when adding segments, up to the 64-element array capacity. Initial moving-platform phases are zero so their initial offsets match the initialized arrays.

## Validation

Run `python3 tools/check_physics.py` for independent numerical checks of gravitational acceleration, magnetic speed conservation, friction impulse bounds, and world data integrity. These checks do not replace compiling and playing the BASIC program on hardware.

Run `python3 tools/run_headless.py --frames 1800` to execute the local `GRAVITY.BAS` through a limited Python translation of the subset used by this game. It exercises settling, jumping, scripted movement/braking, checkpoint and field regions, finish text, field toggling, and respawning. Drawing calls evaluate and record arguments without displaying graphics. Controller input is scripted. This is a custom smoke-test runner, not a SmileBASIC emulator: it cannot validate SmileBASIC parsing, reserved names, API signatures, device timing, or the copy typed into the console. It executes trusted local source as Python.

API reference: [official SMILEBASIC 4 manual](https://sup4.smilebasic.com/en/doku.php?id=reference:all_references).

## Saving in the Japanese demo

Stop the game with the controller's **+** button. In DIRECT mode, enter these three lines individually to save slot 0 through `SAVEV`:

```basic
PRGEDIT 0:S$=""
FOR I=0 TO PRGSIZE(0)-1:S$=S$+PRGGET$()+CHR$(10):NEXT
SAVEV "TXT:GRAVITY",S$
```

To restore the saved source, enter the following lines individually. This replaces slot 0:

```basic
S$=LOADV("TXT:GRAVITY")
PRGEDIT 0:PRGDEL -1:PRGINS S$
RUN
```

## Optional Pico keyboard sender

`pico/boot.py` and `pico/code.py` provide a one-shot CircuitPython USB keyboard sender. Copy `pico/settings.example.json` as the device's `settings.json` and supply the game source as `/bootstrap.bas` for bootstrap mode. The example is disabled and unarmed. The sender requires a keyboard layout matching its US HID punctuation mapping; letter-shift inversion is configurable. Its default delays take roughly 14 minutes for the full source. Prepare an empty SmileBASIC editor slot before enabling bootstrap mode and arming the sender. Arming is consumed once on boot; a later boot returns to maintenance mode. The sender does not save or run the program.

Device backups, live settings, and transfer metadata are excluded from version control.
