"""在 GitHub 上发一个带安装包的 release（给「别人想下载安装」用）。

为什么要有这个：两个仓原来都是**纯源码**（0 个 release，仓里也没有 HAP），
想给别人一个能点的下载链接，只能发一个带附件的 release。

发哪个包 —— **未签名**的 HAP：
- 现在仓里/本机那个已签名 HAP 是**调试签名**，profile 的 `device-ids`
  只含本机的两台设备，有效期到 2027-11-03。
  别人拿到直接装会报 `9568423 device is unauthorized`（本项目 2026-11-03 踩过）。
- 未签名的 HAP 反而是**通用**的：拿到签名材料（自己的 DevEco 自动签名）
  签一下就能装到自己的机器上。签名步骤写进 INSTALL.md。

用法：
  python make_release.py --repo app --tag v1.0.0 --build      # 先编译再发
  python make_release.py --repo app --tag v1.0.0 --dry-run    # 只查，不写远端
"""

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_api import CREATE_NO_WINDOW, ApiError, GitHub, RateLimitHit, get_token  # noqa: E402

REPOS = {
    'app': {
        'name': 'harmonyos-minesweeper',
        'path': r'C:\Users\19161\saolei',
        'branch': 'master',
    },
    'spec': {
        'name': 'minesweeper-harmonyos-toolkit',
        'path': r'D:\software\harmony\projects\minesweeper',
        'branch': 'master',
    },
}

HAP_NAME = 'harmonyos-minesweeper-unsigned.hap'
BUILD_PS1 = r'D:\software\harmony\projects\minesweeper\tools\build.ps1'
HAP_UNSIGNED = r'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-unsigned.hap'

RELEASE_BODY = """\
这是 **Windows 7 扫雷**的鸿蒙（HarmonyOS / ArkTS）像素级移植版。

## 本次更新（2026-11-05）

**音效**（这一版的主要改动）：

- **音画同步**了 —— 声音不再比画面慢一大截。原来声音是「调用播放的那一刻」
  才开始异步准备，画面是按绝对时间轴走的，两套时钟各走各的；
  现在播放器提前建好、准备好，播放时按**画面那条时间轴**对齐。
- **点第一个方块不再播开始音**了。原来把「发牌配乐」错挂在首点上，
  按两份复刻的交叉证据改正：首点没有专属音效，按翻开几格播对应的那一声；
  发牌动画才播发牌配乐。
- **判负改成每颗雷各炸一声**（原版语义），几声叠在一起，而不是只响一声。

## 下载与安装

附件是**未签名**的 HAP 安装包（`harmonyos-minesweeper-unsigned.hap`）。
HarmonyOS 的安装包必须签名才能装，所以**装之前要用你自己的签名材料签一次**：

1. 装 DevEco Studio（[官方下载](https://developer.huawei.com/consumer/cn/deveco-studio/)），
   用华为开发者账号登录，在「设置 → 签名配置」里**自动签名**生成你自己的
   `.cer` / `.p12` / `.p7b`（把要装的那台设备连上并选上）。
2. 打开 DevEco Studio 的 **Project Structure → Signing Configs**，
   指向你自己的 `.cer` / `.p12` / `.p7b`，然后 **Build → Build Hap(s)/APP(s) → Build HAP(s)**。
3. 出来的 HAP 用 hdc 装到手机上：

```bash
hdc install -r entry-default-signed.hap
```

> 也可以**不用 DevEco Studio**：直接用 SDK 里的 `hap-sign-tool.jar` 签，
> 命令行参数见 `INSTALL.md`。

## 关于设备

- 目标机是 **华为 MatePad Pro 12.2**（画布 1840×2650 竖屏 / 2800×1840 横屏）。
- 折叠屏（华为 Pura X Max）的**代码**在仓库里（折叠换屏重取密度、换屏重建布局），
  但按项目决定**不做针对那台设备的适配与验收**。

## 授权

- **代码**：MIT（见仓库根目录 `LICENSE`）。
- **素材**：`entry/src/main/resources/rawfile/` 下的 10 个 PNG 与 15 个 WAV
  是从原版 `minesweeper.exe` 里提取的**微软原始资源**，**不在 MIT 授权范围内**，
  仅供个人学习研究使用，详见 `ASSETS-NOTICE.md`。
"""


def build_hap() -> str:
    """跑一遍构建，返回未签名 HAP 的路径。"""
    print("编译中 …")
    proc = subprocess.run(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', BUILD_PS1],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        creationflags=CREATE_NO_WINDOW, timeout=1800)
    tail = (proc.stdout or '').strip().splitlines()[-3:]
    for line in tail:
        print('   ', line)
    if proc.returncode != 0:
        raise RuntimeError('构建失败，退出码 %d' % proc.returncode)
    if not os.path.exists(HAP_UNSIGNED):
        raise RuntimeError('找不到未签名 HAP：' + HAP_UNSIGNED)
    return HAP_UNSIGNED


def main() -> int:
    ap = argparse.ArgumentParser(description='发一个带 HAP 附件的 GitHub release')
    ap.add_argument('--repo', choices=sorted(REPOS), default='app')
    ap.add_argument('--tag', default='v1.0.0')
    ap.add_argument('--build', action='store_true', help='发之前先重新编译')
    ap.add_argument('--replace', action='store_true',
                    help='同名附件已存在时**替换**它（发新版安装包时必须带）')
    ap.add_argument('--dry-run', action='store_true', help='只查，不写远端')
    args = ap.parse_args()

    repo = REPOS[args.repo]
    gh = GitHub(get_token())

    if args.build:
        hap_path = build_hap()
    else:
        hap_path = HAP_UNSIGNED
    size_mb = os.path.getsize(hap_path) / (1024.0 * 1024.0)
    print("附件：%s（%.1f MB）" % (os.path.basename(hap_path), size_mb))

    if args.dry_run:
        exist = gh.get_release_by_tag(repo['name'], args.tag)
        print('远端 release %s 已存在：%s' % (args.tag, bool(exist)))
        print('限流剩余：%s' % gh.rate_remaining)
        return 0

    # 同一个 tag 只发一次；已存在就补传附件，不重复建
    rel = gh.get_release_by_tag(repo['name'], args.tag)
    if rel is None:
        rel = gh.create_release(repo['name'], args.tag,
                                'v1.0.0 - Win7 扫雷的鸿蒙移植版', RELEASE_BODY)
        print('已建 release：%s' % rel['html_url'])
    else:
        print('release 已存在，沿用：%s' % rel['html_url'])

    have = {a['name'] for a in rel.get('assets', [])}
    if HAP_NAME in have and args.replace:
        # **替换**旧附件：GitHub 不允许同名附件，所以先删再传。
        # （发新版安装包时必须带 --replace，否则脚本会跳过，线上还是旧包。）
        for a in rel.get('assets', []):
            if a.get('name') == HAP_NAME:
                gh.delete_asset(repo['name'], a['id'])
                print('已删掉旧附件：%s（%d 字节）' % (a['name'], a.get('size', -1)))
        have.discard(HAP_NAME)
    if HAP_NAME in have:
        print('附件已存在，跳过上传（要替换就加 --replace）')
    else:
        with open(hap_path, 'rb') as fh:
            data = fh.read()
        asset = gh.upload_asset(repo['name'], rel['id'], HAP_NAME, data,
                                'application/octet-stream')
        print('已上传附件：%s（%d 字节）' % (asset.get('name'), asset.get('size', -1)))
        print('下载直链：%s' % asset.get('browser_download_url'))

    print('release 页面：%s' % rel['html_url'])
    # 正文同步更新（带上「本次更新」那段）
    try:
        gh.patch_release(repo['name'], rel['id'], {'body': RELEASE_BODY})
        print('正文已更新')
    except ApiError as err:
        print('正文更新失败（不影响附件）：%s' % err)
    print('限流剩余：%s' % gh.rate_remaining)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ApiError, RateLimitHit) as err:
        print('失败：%s' % err)
        sys.exit(1)
