"""
render_ref.py —— 离线复刻 ArkTS 端的渲染逻辑，生成参考图。

目的：在装机之前用像素比对验证布局（状态条位置、渐变、阴影、数字、地板），
避免每一版都要插线装机才能看到效果。

与 GameController.ets 保持同一套坐标约定：
  unit = 每个逻辑单位的设备像素数 = 2 × 缩放档位 n
  棋盘区 = 白色地板 + 左/右/下三边 1px 凹槽线
  底部状态条 = [时钟][计时面板] …… [雷数面板][雷图标]，贴着棋盘左右沿

用法：
  python render_ref.py [输出png] [行] [列] [雷数] [n]
"""

import os
import sys
import random
from PIL import Image, ImageDraw, ImageFont

BASE = r"C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images"

TILE = 18
SPRITE_SCALE = 2
GRAD_COLS, GRAD_ROWS, GRAD_PER_ROW = 30, 24, 25

COLOR_OUTSIDE = (198, 206, 222, 255)
COLOR_FLOOR = (255, 255, 255, 255)
COLOR_SUNKEN = (76, 85, 111, 255)

STRIP_BAND = 32
STRIP_CLOCK_SIZE = 25
STRIP_PANEL_W = 40
STRIP_PANEL_H = 21
STRIP_GAP = 6

# 逻辑坐标（Theme.ets）
RECT_FLAG = (400, 560, 18, 18)
RECT_QUESTION = (420, 560, 18, 18)
RECT_HILITE = (440, 560, 18, 18)
RECT_MISFLAG = (460, 560, 18, 18)
RECT_SHADOW_U = (480, 560, 18, 3)
RECT_SHADOW_L = (1012, 0, 3, 18)
RECT_COUNTER = (0, 580, 40, 21)
RECT_MINE = (27, 0, 18, 18)
RECT_PANEL_MINE = (0, 0, 25, 25)
RECT_CLOCK = (905, 425, 25, 25)


def gradient_frame(row, col, rows, cols):
    r = min(GRAD_ROWS - 1, row + max(0, (GRAD_ROWS - rows) // 2))
    c = min(GRAD_COLS - 1, col + max(0, (GRAD_COLS - cols) // 2))
    return r * GRAD_COLS + c


def strip_margin(cols):
    return max(0, round((cols - 12.5) * TILE / 7))


class Renderer:
    def __init__(self, rows=9, cols=9, mines=10, n=2, canvas=(1200, 900)):
        self.rows, self.cols = rows, cols
        self.mines = mines
        self.unit = 2 * n
        self.tile = TILE * self.unit
        self.canvas = canvas
        self.img = Image.new("RGBA", canvas, COLOR_OUTSIDE)
        self.d = ImageDraw.Draw(self.img)
        self.blue = Image.open(os.path.join(BASE, "blueSheet.png")).convert("RGBA")
        self.game = Image.open(os.path.join(BASE, "minesweeperSheet.png")).convert("RGBA")
        self.other = Image.open(os.path.join(BASE, "otherSheet.png")).convert("RGBA")

        board_w = cols * self.tile
        board_h = rows * self.tile
        # 棋盘居中，纵向给状态条留出 32 个逻辑单位
        self.board_x = (canvas[0] - board_w) // 2
        self.board_y = (canvas[1] - (board_h + STRIP_BAND * self.unit)) // 2

    # ---------- 基础绘制 ----------

    def sprite(self, sheet, rect, dx, dy, dw, dh):
        """rect 是逻辑坐标 [x,y,w,h]；目标尺寸单位是设备像素。"""
        sx, sy, sw, sh = [v * SPRITE_SCALE for v in rect]
        crop = sheet.crop((sx, sy, sx + sw, sy + sh))
        if crop.size != (int(dw), int(dh)):
            crop = crop.resize((int(dw), int(dh)), Image.NEAREST)
        self.img.alpha_composite(crop, (int(dx), int(dy)))

    def sprite_scaled(self, sheet, rect, dx, dy):
        """目标尺寸 = 逻辑尺寸 × unit。"""
        self.sprite(sheet, rect, dx, dy, rect[2] * self.unit, rect[3] * self.unit)

    def draw_board_area(self):
        x, y = self.board_x, self.board_y
        w, h = self.cols * self.tile, self.rows * self.tile
        self.d.rectangle([x, y, x + w, y + h], fill=COLOR_FLOOR)
        # 凹槽线：左、右、下各 1px
        self.d.rectangle([x - 1, y, x - 1, y + h], fill=COLOR_SUNKEN)
        self.d.rectangle([x + w, y, x + w, y + h], fill=COLOR_SUNKEN)
        self.d.rectangle([x - 1, y + h, x + w, y + h], fill=COLOR_SUNKEN)

    def draw_cell(self, r, c, state):
        x = self.board_x + c * self.tile
        y = self.board_y + r * self.tile
        if not state["revealed"]:
            f = gradient_frame(r, c, self.rows, self.cols)
            self.sprite_scaled(self.blue, (TILE * (f % GRAD_PER_ROW), TILE * (f // GRAD_PER_ROW), TILE, TILE), x, y)
            if state.get("flag"):
                self.sprite_scaled(self.blue, RECT_FLAG, x, y)
            if state.get("question"):
                self.sprite_scaled(self.blue, RECT_QUESTION, x, y)
            if state.get("misflagged"):
                self.sprite_scaled(self.blue, RECT_MISFLAG, x, y)
            return
        # 地板 = 该格的「按下态」渐变砖块（浅灰）
        f = gradient_frame(r, c, self.rows, self.cols)
        self.sprite_scaled(self.blue, (TILE * (f % GRAD_PER_ROW) + 500, TILE * (f // GRAD_PER_ROW), TILE, TILE), x, y)
        # 黑边：上方/左方有凸起格子时
        up = (r == 0) or not state["up_covered"]
        left = (c == 0) or not state["left_covered"]
        t = 3 * self.unit
        if up:
            self.sprite_scaled(self.blue, RECT_SHADOW_U, x, y)
        if left:
            if up:
                self.sprite(self.blue, (1012, 3, 3, 15), x, y + t, 3 * self.unit, 15 * self.unit)
            else:
                self.sprite_scaled(self.blue, RECT_SHADOW_L, x, y)
        n = state.get("adjacent", 0)
        if state.get("exploded"):
            self.sprite_scaled(self.game, RECT_MINE, x, y)
        elif state.get("mine"):
            self.sprite_scaled(self.game, RECT_MINE, x, y)
        elif state.get("misflagged"):
            self.sprite_scaled(self.blue, RECT_FLAG, x, y)
            self.sprite_scaled(self.blue, RECT_MISFLAG, x, y)
        elif n > 0:
            rect = (1000, 15 * (n - 1), 12, 15)
            w, h = 12 * self.unit, 15 * self.unit
            self.sprite(self.blue, rect, x + (self.tile - w) // 2, y + (self.tile - h) // 2, w, h)

    def draw_strip(self, seconds, mines_left):
        u = self.unit
        bottom = self.board_y + self.rows * self.tile
        right = self.board_x + self.cols * self.tile
        margin = strip_margin(self.cols) * u

        clock_x = self.board_x + margin
        clock_y = bottom + round((STRIP_BAND - STRIP_CLOCK_SIZE) / 2) * u
        time_x = clock_x + (STRIP_CLOCK_SIZE + STRIP_GAP) * u
        time_y = bottom + round((STRIP_BAND - STRIP_PANEL_H) / 2) * u
        icon_x = right - margin - STRIP_CLOCK_SIZE * u
        icon_y = clock_y
        mine_x = icon_x - (STRIP_GAP + STRIP_PANEL_W) * u
        mine_y = time_y

        self.sprite_scaled(self.other, RECT_CLOCK, clock_x, clock_y)
        self.sprite_scaled(self.blue, RECT_COUNTER, time_x, time_y)
        self.sprite_scaled(self.blue, RECT_COUNTER, mine_x, mine_y)
        self.sprite_scaled(self.game, RECT_PANEL_MINE, icon_x, icon_y)

        size = max(8, int(12 * u))
        try:
            font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", size)
        except OSError:
            font = ImageFont.load_default()
        for text, bx, by in ((str(seconds), time_x, time_y), (str(mines_left), mine_x, mine_y)):
            w, h = STRIP_PANEL_W * u, STRIP_PANEL_H * u
            bbox = self.d.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            self.d.text((bx + (w - tw) / 2 - bbox[0], by + (h - th) / 2 - bbox[1]),
                        text, font=font, fill=(255, 255, 255, 255))

    def render(self, cells, seconds=25, mines_left=10):
        self.draw_board_area()
        for r in range(self.rows):
            for c in range(self.cols):
                st = cells[r][c]
                st["up_covered"] = r > 0 and not cells[r - 1][c]["revealed"]
                st["left_covered"] = c > 0 and not cells[r][c - 1]["revealed"]
                self.draw_cell(r, c, st)
        self.draw_strip(seconds, mines_left)
        return self.img


def make_board(rows, cols, mines, seed=7, lost=False):
    """摆一个像样的局面：左上角开了一片，右上角有旗和问号。

    lost=True 时按引擎 lose() 的规则补出判负后的画面：
    未插旗的雷全部翻开（其中一颗是踩中的），插错旗的安全格打叉。
    """
    rng = random.Random(seed)
    cells = [[{"revealed": False, "adjacent": 0, "mine": False} for _ in range(cols)] for _ in range(rows)]
    revealed = set()
    stack = [(0, 0)]
    while stack and len(revealed) < 18:
        r, c = stack.pop()
        if (r, c) in revealed:
            continue
        revealed.add((r, c))
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in revealed:
                    stack.append((nr, nc))
    mines_set = set()
    while len(mines_set) < mines:
        mines_set.add((rng.randrange(rows), rng.randrange(cols)))
    for r, c in mines_set:
        cells[r][c]["mine"] = True
    for r, c in revealed:
        if cells[r][c]["mine"]:
            continue
        n = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if 0 <= r + dr < rows and 0 <= c + dc < cols and cells[r + dr][c + dc]["mine"])
        cells[r][c]["revealed"] = True
        cells[r][c]["adjacent"] = n
    cells[1][cols - 1]["flag"] = True
    cells[0][cols - 1]["question"] = True

    if lost:
        # 踩中一颗雷：所有未插旗的雷翻开，一颗标记为 exploded
        flagged = {(r, c) for r in range(rows) for c in range(cols) if cells[r][c].get("flag")}
        hit = None
        for r, c in sorted(mines_set - flagged):
            cells[r][c]["revealed"] = True
            cells[r][c]["adjacent"] = 0
            if hit is None:
                hit = (r, c)
        if hit:
            cells[hit[0]][hit[1]]["exploded"] = True
        # 安全格上插错旗
        for r, c in flagged:
            if not cells[r][c]["mine"]:
                cells[r][c]["misflagged"] = True
                break
    return cells


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else r"D:\software\harmony\projects\minesweeper\docs\ref_render.png"
    rows = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 9
    mines = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    cw, ch = (1200, 900) if cols <= 16 else (1400, 1000)
    lost = len(sys.argv) > 6 and sys.argv[6] == "lost"
    r = Renderer(rows, cols, mines, n, (cw, ch))
    img = r.render(make_board(rows, cols, mines, lost=lost))
    img.save(out)
    print("saved", out, img.size, f"unit={r.unit} tile={r.tile} margin={strip_margin(cols)} lost={lost}")
