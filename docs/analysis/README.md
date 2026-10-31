# analysis —— 取证与量测留档

这个目录放的是**过程证据**，不是交付物：凡是「为了确定某个像素、某条规则而做的量测」
留下的脚本、放大图、对照渲染图，都在这里。文档正文（SPEC / DEV-CHECKLIST / ASSET-AUDIT /
WIN7-FEATURE-GAP / SOUND-MAP）在上层目录。

## 命名约定

| 前缀 | 来源 | 用途 |
|---|---|---|
| `audit_*` | 素材盘点 | 各精灵表的放大图与局部特写 |
| `dlg_*` / `dialog_*` / `crop_*` / `m_*.txt` / `stats_layout*` | 对话框量测 | loss/win/about/statistics 四张参考图的逐像素量测脚本与结果 |
| `explode_*` / `sheet_*` / `minesheet_*` / `digits_check` / `scanbar_*` / `frame_*` / `helpboard*` / `face_*` | 精灵与动画定位 | 爆炸帧、扫描条、时钟/笑脸之争的取证 |
| `render_check*` / `render_stats*` / `ref_render*` | 渲染自检 | 把 .ets 里的常量反渲染出来与参考图并排对照 |
| `icon_*` | 应用图标 | 新旧图标对照与圆形遮罩预览 |
| `probe*.py` / `measure_out.txt` / `cmp_*` | 杂项探针 | 一次性验证 |

## 几条重要的取证结论（原图在这里，结论写进了 SPEC）

- `audit_helpboard_lefticon.png` / `audit_helpboard_strip_5x.png`：真 Win7 状态条左端那个圆钮
  放大后是**时钟（有指针）**，不是笑脸；左边 LED「18」是计时、右边 LED「-40」是雷数。
  这推翻了中间一次「Win7 有笑脸」的误判，见 SPEC §5.5 的两次返工记录。
- `audit_blueSheet_overview.png` / `audit_greenSheet_overview.png`：蓝绿两张图集**逐像素同构**，
  数字/旗/问号/高亮/红叉/阴影完全一致，只有砖块渐变与地板底色不同 —— 绿色主题的复用成本极低。
- `explode_region.png` / `explode_frames_check.png`：踩雷爆炸的 23 帧定位。
- `render_check.png` / `render_stats.png`：对话框与统计窗口的常量反渲染对照。

这些图都是**微软原版资产的放大截图**，仅供本机自查，不对外分发。
