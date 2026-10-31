# -*- coding: utf-8 -*-
"""Second pass: crop the UNREFERENCED atlas regions (suspected missing features)
and write the sprite index. Read-only against the app repo."""
import os, json
from PIL import Image

RAW = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
S = 2
os.makedirs(OUT, exist_ok=True)

blue = Image.open(os.path.join(RAW, 'blueSheet.png')).convert('RGBA')
other = Image.open(os.path.join(RAW, 'otherSheet.png')).convert('RGBA')

def crop(im, box, name, scale=1):
    sub = im.crop(box)
    if scale > 1:
        sub = sub.resize((sub.width * scale, sub.height * scale), Image.NEAREST)
    sub.convert('RGB').save(os.path.join(OUT, name))
    print('%-42s box=%s  size=%dx%d' % (name, box, sub.width, sub.height))

# ---- suspected-missing regions (reached by hand from the coverage map) ----
crop(other, (728, 0, 1456, 300),    'unused_otherSheet_green_beam.png')
crop(other, (1810, 0, 2048, 304),   'unused_otherSheet_flower_trip.png')
crop(other, (0, 1948, 460, 2016),    'unused_otherSheet_led_digits.png')
crop(other, (0, 1824, 560, 1948),    'unused_otherSheet_scanbar_row.png')
crop(other, (728, 900, 1460, 1200),  'unused_otherSheet_green_beam_mid.png')
crop(blue,  (1900, 0, 2034, 300),   'unused_blueSheet_right_strip.png')
crop(blue,  (0, 1140, 2034, 1206),  'unused_blueSheet_counter_row.png')
crop(blue,  (0, 1104, 2034, 1160),  'unused_blueSheet_sprite_row.png')
crop(blue,  (0, 1008, 2034, 1160),  'unused_blueSheet_sprite_band.png')

# ---- exact rectangle accounting -------------------------------------------
audit = json.load(open(os.path.join(OUT, '_audit.json'), encoding='utf-8'))
live = 0
dead = 0
for r in audit['rows']:
    n = r.get('frames', 1)
    if 'DEAD' in r['ref']:
        dead += n
    else:
        live += n
print()
print('named reference entries : %d  (live %d, dead %d)'
      % (len(audit['rows']),
         len([r for r in audit['rows'] if 'DEAD' not in r['ref']]),
         len([r for r in audit['rows'] if 'DEAD' in r['ref']])))
print('individual source rects : live %d + dead %d = %d' % (live, dead, live + dead))
print('out of bounds            : %d' % len(audit['oob']))
print('duplicate groups         : %d' % len(set((a, b, s) for a, b, s, _ in
      [(d[0], d[1], d[2], d[3]) for d in audit['dup']])))
json.dump(dict(live=live, dead=dead, entries=len(audit['rows'])),
          open(os.path.join(OUT, '_counts.json'), 'w'), indent=1)

# ---- file inventory of the crop dir ---------------------------------------
files = sorted(f for f in os.listdir(OUT) if f.lower().endswith('.png'))
print('\ncrop files: %d' % len(files))
for f in files:
    print('   ' + f)
