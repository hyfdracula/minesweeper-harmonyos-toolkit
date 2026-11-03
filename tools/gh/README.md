# tools/gh —— 用 GitHub REST API 推仓（因为 github.com 被墙）

## 为什么不用 git push

本机实测（2026-11-03）：

| 通道 | 结果 |
|---|---|
| `git ls-remote https://github.com/...` | `Recv failure: Connection was reset` |
| `PowerShell Invoke-WebRequest https://github.com` | `基础连接已经关闭: 发送时发生错误` |
| `https://api.github.com/rate_limit` | **HTTP 200** |

也就是说 **github.com 本身连不上，只有 api.github.com 通**（与全局约定里那张表一致）。
所以推送走 **GitHub REST API 的 Git Data API**（blobs / trees / commits / refs），
不走 git 协议。

## 用法

```powershell
cd D:\software\harmony\projects\minesweeper
python tools\gh\push_repo.py --repo spec      # 规格仓
python tools\gh\push_repo.py --repo app       # 应用仓
```

token 从 `gh auth token` 取（`gh` CLI 已登录 `hyfdracula`），**只在内存里用**：
放在请求头 `Authorization: Bearer <token>`，不落盘、不进日志、不进提交信息。

脚本**可断点续传**：已经传过的 blob 记在 `state_spec.json` / `state_app.json` 里，
重跑时只补没传过的。

## 做法（为什么是这样）

1. **先传 blob**：每个文件按 base64 传一次 `POST /git/blobs`。
   GitHub 算出来的 blob SHA 与本地 git **完全一致**（都是 `"blob <长度>\0<内容>"` 的 SHA-1），
   所以树和提交都能直接引用本地 SHA。
2. **自底向上增量建树**：`POST /git/trees` 一次吃不下 2443 条的平铺树（422 too large），
   所以按目录从叶子往上建；`docs/verify` 单目录 1814 个文件再按 250 条分块、用 `base_tree` 叠加。
3. **逐个重建提交**：按时间顺序 `git ls-tree -r <sha>` 取那棵树的文件清单，建树，
   再 `POST /git/commits`（`message` / `tree` / `parents` / `author` / `committer` 都用原值）。
4. **最后改 ref**：`POST /git/refs` 把 `refs/heads/main` 指向最后一个提交。

## 踩过的坑

| 现象 | 原因 | 处置 |
|---|---|---|
| `409 Git Repository is empty` | 空仓不许建 blob，也不许建 tree | 先用 Contents API 放一个占位文件生成首个提交，等仓非空再传；建完正式历史把 main 指过去，占位提交变成不可达对象，不进历史 |
| `422 Cannot delete the default branch` + `422 Update is not a fast forward` | 不能删默认分支，而 PATCH 更新分支要求快进，占位提交不是正式历史的祖先 | 先建临时分支把默认分支挪过去，删旧分支，用目标 SHA 重建，再把默认分支指回去并删临时分支 |
| `422 your request timed out ... too large to process` | tree 接口一次吃不下 2443 条平铺树 | 自底向上增量建树 |
| `502` / 卡住 | `docs/verify` 单目录 1814 个文件，单目录树也过大 | 大目录按 250 条分块 + `base_tree` 叠加；树请求单独设 90 秒超时、8 次重试，失败快速暴露而不是无声卡死 |
| `400 malformed request` / `401 Bad credentials`（偶发 10 个 blob） | 传输层串包，与凭据无关 | 归入可重试类（连同 429/5xx/连接重置）退避重试，最后全部成功 |

## 速率限制

核心限额 **5000 次/小时**。一轮完整推送约 3200 次调用
（blob ~2600 + 建树 ~400 + 建提交 ~170 + 校验若干）。
脚本里有「剩余低于 150 就停」的闸门。

## 结果（2026-11-03 实测）

| 仓 | 文件 | 提交 | SHA 一致 |
|---|---|---|---|
| `hyfdracula/harmonyos-minesweeper`（应用） | 95 | 57 | blob 222/222、提交 57/57，**不一致 0** |
| `hyfdracula/minesweeper-harmonyos-toolkit`（规格） | 2467 | 108 | blob 2385/2385、提交 108/108，**不一致 0** |

远端分支叫 `main`，本地分支叫 `master` —— **历史与内容一比一复刻**，
只是分支名不同（GitHub 上默认分支一般是 `main`）。

> 规格仓在 GitHub 页面上可能显示 `size` 为 0 KB：那是 GitHub 的**异步统计缓存**没刷新，
> 内容实打实在（contents API 能取到 README、LICENSE 和 2.27 MB 的素材二进制）。
