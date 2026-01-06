import math
# avoid importing repo packages when run as standalone
SCREEN_HEIGHT = 1080

# current hardcoded params - keep in sync with utils/game_utils.py
vertical_factor_top = 0.41
vertical_factor_bottom = -0.09
wiggle_coeff = -0.05
pos_floor = 0.15

# samples to fit to target=700
samples = [
    (965,1050,961,504),
    (965,625,962,222),
    (965,595,962,201),
    (751,265,1207,226),
    (663,1031,1307,977),
    (663,1031,1307,977),
    (754,241,1204,202),
    (745,322,1215,282),
    (735,411,1226,370),
    (722,517,1240,474),
    (711,613,1252,567),
    (702,694,1263,647),
    (691,791,1275,742),
    (681,875,1286,824),
    (670,971,1299,918),
    (661,1050,1309,995),
]
TARGET = 700.0

A = []
B = []
for px, py, tx, ty in samples:
    dx = px - tx
    dy = py - ty
    pixel_dist = math.hypot(dx, dy)
    if pixel_dist == 0:
        continue
    norm_y = (py - (SCREEN_HEIGHT / 2.0)) / (SCREEN_HEIGHT / 2.0)
    norm_y = max(-1.0, min(1.0, norm_y))
    t = (norm_y + 1.0) / 2.0
    v = vertical_factor_top * (1.0 - t) + vertical_factor_bottom * t
    wiggle = wiggle_coeff * (norm_y ** 3)
    pos_multiplier = 1.0 + v + wiggle
    pos_multiplier = max(pos_floor, pos_multiplier)
    sep_ratio = abs(dy) / pixel_dist
    Ai = pixel_dist * pos_multiplier
    Bi = Ai * sep_ratio
    A.append(Ai)
    B.append(Bi)

n = len(A)
S_AA = sum(a*a for a in A)
S_AB = sum(a*b for a,b in zip(A,B))
S_BB = sum(b*b for b in B)
S_AT = sum(a*TARGET for a in A)
S_BT = sum(b*TARGET for b in B)

# Solve [ [S_AA, S_AB], [S_AB, S_BB] ] [u, c] = [S_AT, S_BT]
D = S_AA * S_BB - S_AB * S_AB
if abs(D) < 1e-12:
    print('Singular system; cannot fit')
else:
    u = (S_AT * S_BB - S_AB * S_BT) / D
    c = (S_AA * S_BT - S_AB * S_AT) / D
    k_sep = c / u if abs(u) > 1e-12 else float('inf')
    print('Fitted unit_scale (u)=', u)
    print('Fitted c = u * k_sep =', c)
    print('Derived k_sep =', k_sep)
    # suggest max_sep_mult as 1 + k_sep (if sep_ratio up to 1)
    suggested_max = 1.0 + k_sep
    print('Suggested max_sep_mult ~=', suggested_max)

# Print per-sample predicted values using fitted params
try:
    for i,(px,py,tx,ty) in enumerate(samples):
        dx = px - tx
        dy = py - ty
        pd = math.hypot(dx,dy)
        norm_y = (py - (SCREEN_HEIGHT / 2.0)) / (SCREEN_HEIGHT / 2.0)
        t = (norm_y + 1.0) / 2.0
        v = vertical_factor_top * (1.0 - t) + vertical_factor_bottom * t
        wiggle = wiggle_coeff * (norm_y ** 3)
        pos_multiplier = 1.0 + v + wiggle
        pos_multiplier = max(pos_floor, pos_multiplier)
        sep_ratio = abs(dy)/pd
        pred = u * pd * pos_multiplier * (1.0 + k_sep * sep_ratio)
        print(f'sample {i}: pred={pred:.2f}, target={TARGET}')
except Exception as e:
    print('Error computing predictions:', e)
