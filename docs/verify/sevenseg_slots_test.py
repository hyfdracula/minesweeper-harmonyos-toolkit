# -*- coding: utf-8 -*-
"""1:1 mirror of SevenSeg.slotsFor() in ArkTS, to check every edge case."""
import math

SEG = {'a': 1, 'b': 2, 'c': 4, 'd': 8, 'e': 16, 'f': 32, 'g': 64}
NAMES = {v: k for k, v in SEG.items()}
DIGIT_MASKS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
SLOT_COUNT = 3
MIN_VALUE = -99
MAX_VALUE = 999


def trunc(x):
    return math.trunc(x)


def slots_for(value):
    out = [0, 0, 0]
    if not math.isfinite(value):
        return out
    n = trunc(value)
    if n > MAX_VALUE:
        n = MAX_VALUE
    elif n < MIN_VALUE:
        n = MIN_VALUE
    negative = n < 0
    if negative:
        n = -n
    digits = []
    if n == 0:
        digits.append(0)
    while n > 0:
        digits.append(n % 10)
        n = math.floor(n / 10)
    text = list(reversed(digits))
    start = 0
    count = len(text)
    if negative and count >= SLOT_COUNT:
        count = SLOT_COUNT - 1
        start = len(text) - count
    elif count > SLOT_COUNT:
        start = len(text) - SLOT_COUNT
        count = SLOT_COUNT
    for i in range(count):
        out[SLOT_COUNT - count + i] = DIGIT_MASKS[text[start + i]]
    if negative:
        minus_slot = SLOT_COUNT - count - 1
        out[minus_slot if minus_slot >= 0 else 0] = SEG['g']
    return out


def show(v):
    sl = slots_for(v)
    cells = []
    for m in sl:
        if m == 0:
            cells.append('----')
        elif m == SEG['g']:
            cells.append(' -  ')
        else:
            cells.append(''.join(sorted(NAMES[b] for b in SEG.values() if m & b)))
    return ' | '.join(cells)


print('%-12s %s' % ('value', 'slot0 | slot1 | slot2'))
for v in [0, 1, 5, 9, 10, 18, 40, 99, 100, 123, 999, 1000, 1234, -1, -4, -9, -10,
          -40, -99, -100, -999, -1000, 3.7, -3.7]:
    print('%-12s %s' % (v, show(v)))
print('%-12s %s' % ('NaN', show(float('nan'))))
print('%-12s %s' % ('Infinity', show(float('inf'))))
print('%-12s %s' % ('-Infinity', show(float('-inf'))))

# exhaustive: every value must render the clamped value's digits, right-aligned
bad = []
for v in range(-1200, 1201):
    sl = slots_for(v)
    cells = [m for m in sl if m != 0]
    cv = max(MIN_VALUE, min(MAX_VALUE, v))
    if cv == 0:
        if cells != [DIGIT_MASKS[0]]:
            bad.append((v, sl))
        continue
    if cv > 0:
        digits = [int(c) for c in str(cv)]
        expect = [DIGIT_MASKS[d] for d in digits]
        if cells != expect:
            bad.append((v, sl, expect))
    else:
        digits = [int(c) for c in str(-cv)]
        expect = ([SEG['g']] + [DIGIT_MASKS[d] for d in digits]) if len(digits) == 2 else \
                 ([0, SEG['g']] + [DIGIT_MASKS[d] for d in digits])
        expect = [m for m in expect]
        if cells != [m for m in expect if m != 0]:
            bad.append((v, sl, expect))
print('\nexhaustive -1200..1200 : %d mismatches' % len(bad))
for b in bad[:10]:
    print('   ', b)

# the clamp must never show a wrong number: check the displayed magnitude
bad2 = []
for v in range(-1200, 1201):
    sl = slots_for(v)
    cells = [m for m in sl if m != 0]
    cv = max(MIN_VALUE, min(MAX_VALUE, v))
    if cv < 0:
        # the last cell must be the units digit of |cv|
        if cells[-1] != DIGIT_MASKS[abs(cv) % 10]:
            bad2.append((v, cells))
print('clamp sanity (units digit always right) : %d mismatches' % len(bad2))
