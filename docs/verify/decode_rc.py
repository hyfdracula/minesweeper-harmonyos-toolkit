# -*- coding: utf-8 -*-
"""Decode Lmy0217's Minesweeper.rc: the file is UTF-16LE whose code units are
byte-swapped GBK, so take the low byte of each UTF-16 unit and decode as GBK."""
import io, re, sys

P = r'C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\Minesweeper\utf8\Minesweeper.rc'
raw = open(P, 'rb').read()
# UTF-16LE units -> low bytes
units = []
for i in range(0, len(raw) - 1, 2):
    units.append(raw[i] | (raw[i + 1] << 8))
bs = bytes(u & 0xFF for u in units)
try:
    txt = bs.decode('gbk', errors='replace')
except Exception as e:
    txt = bs.decode('latin-1', errors='replace')

lines = txt.splitlines()
out = []
for n, ln in enumerate(lines, 1):
    s = ln.strip()
    if not s:
        continue
    if re.search(r'MENUITEM|POPUP|CONTROL|LTEXT|CTEXT|DEFPUSHBUTTON|CHECKBOX|RADIOBUTTON|GROUPBOX|'
                 r'CAPTION|IDC_CHECK|IDD_|STRINGTABLE|"\s*,"', s):
        out.append('%4d | %s' % (n, s[:220]))
print('\n'.join(out))
print('\n================ STRINGS ================')
for n, ln in enumerate(lines, 1):
    s = ln.strip()
    if s.startswith('"') and ('"' in s[1:]) and not re.search(r'CONTROL|LTEXT|DEFPUSHBUTTON', s):
        print('%4d | %s' % (n, s[:200]))
