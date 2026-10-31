# -*- coding: utf-8 -*-
"""Patch the throwaway copy of the project so SevenSeg.ets is actually compiled."""
import io
import sys

p = r'C:\Users\19161\AppData\Local\Temp\sevenseg-probe\entry\src\main\ets\pages\Index.ets'
s = io.open(p, encoding='utf-8').read()
if 'SevenSeg' in s:
    print('already patched')
    sys.exit(0)

imp = "import { SoundPlayer } from '../common/SoundPlayer';"
assert imp in s, 'anchor import not found'
s = s.replace(imp, imp + "\nimport { SevenSeg } from '../common/SevenSeg';")

anchor = '  aboutToAppear(): void {'
assert anchor in s, 'anchor method not found'
probe = (anchor + "\n    console.info('[probe] SevenSeg slots=' + SevenSeg.slotsFor(-40).length);")
s = s.replace(anchor, probe)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('patched Index.ets')
