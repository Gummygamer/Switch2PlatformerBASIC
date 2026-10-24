"""Independent numerical checks; not a SmileBASIC interpreter."""
from math import hypot
from pathlib import Path

dt = 1 / 240
vy = y = 0.0
for _ in range(240):
    vy += 9.81 * dt
    y += vy * dt
assert abs(vy - 9.81) < 1e-10
assert abs(y - 4.905) < 0.021

vx, vy = 3.0, -4.0
for _ in range(24000):
    bt = 1.6 * dt / 2
    bs = 2 * bt / (1 + bt * bt)
    px, py = vx + vy * bt, vy - vx * bt
    vx, vy = vx + py * bs, vy - px * bs
assert abs(hypot(vx, vy) - 5) < 1e-10

# A contact impulse cancels slip when sufficient traction exists.
radius, inverse_inertia = 0.25, 32.0
vx, omega, normal_impulse, mu = 1.0, 0.0, 1.0, 0.7
slip = vx - omega * radius
jt = max(-mu * normal_impulse, min(mu * normal_impulse,
          -slip / (1 + radius * radius * inverse_inertia)))
vx += jt
omega -= radius * jt * inverse_inertia
assert abs(vx - omega * radius) < 1e-12
assert abs(jt) <= mu * normal_impulse

source = (Path(__file__).resolve().parents[1] / 'GRAVITY.BAS').read_text()
rows = [line[5:] for line in source.splitlines() if line.startswith('DATA ')]
assert int(rows[0]) == len(rows) - 1
for row in rows[1:]:
    ax, ay, bx, by, mu, mx, my, hz, phase = map(float, row.split(','))
    assert (ax, ay) != (bx, by)
    assert mu >= 0 and phase == 0
labels = [line for line in source.splitlines() if line.startswith('@')]
assert len(labels) == len(set(labels))
print('PASS: gravity acceleration, magnetic speed conservation, friction, world data')
