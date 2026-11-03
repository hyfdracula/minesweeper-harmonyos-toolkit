"""把本地 git 仓原样推到 GitHub（公开仓），只用 GitHub REST API。

背景：本机 github.com 被墙，git push / git ls-remote 都连不上，只有 api.github.com 通。
所以走 Git Data API：blobs -> trees -> commits -> refs，把提交历史一比一复刻。

流程：
  1) `gh auth token` 取 token（只在内存里）
  2) 读本地提交（git rev-list --reverse）和每棵树的条目（git ls-tree -r）
  3) 把所有出现过的 blob 并发 base64 上传（拿到远端 SHA）
  4) 按时间顺序逐个建 tree -> commit（父提交用上一个建出来的远端 SHA）
  5) 建 refs/heads/main，并 PATCH 设默认分支
  6) 对比远端建出来的 commit SHA 与本地 SHA，报告一致/不一致数量

用法：
  python push_repo.py --check              # 体检：凭据 / 仓库名可用性 / 限流 / 待传对象数
  python push_repo.py --repo app           # 推应用仓
  python push_repo.py --repo spec          # 推规格仓
  python push_repo.py --repo app --dry-run # 只走查不写远端
"""

import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gh_api import CREATE_NO_WINDOW, ApiError, GitHub, RateLimitHit, get_token  # noqa: E402

REPOS = {
    'app': {
        'path': r'C:\Users\19161\saolei',
        'name': 'harmonyos-minesweeper',
        'description': 'HarmonyOS (ArkTS) port of Windows 7 Minesweeper, with the original Microsoft artwork',
        'branch': 'master',
    },
    'spec': {
        'path': r'D:\software\harmony\projects\minesweeper',
        'name': 'minesweeper-harmonyos-toolkit',
        'description': 'Specs, layout math, offline engine tests and device-verification evidence for the HarmonyOS Minesweeper port',
        'branch': 'master',
    },
}

# 剩余额度低于这个数就停下来报告，不盲目重试
RATE_STOP_AT = 150


def git(repo_path, *args, binary=False):
    proc = subprocess.run(
        ['git', '-C', repo_path] + list(args),
        capture_output=True, creationflags=CREATE_NO_WINDOW)
    if proc.returncode != 0:
        raise RuntimeError('git %s 失败：%s' % (' '.join(args),
                                                proc.stderr.decode('utf-8', 'replace')[:300]))
    return proc.stdout if binary else proc.stdout.decode('utf-8', 'replace')


class BlobReader:
    """用 `git cat-file --batch` 流式读 blob，避免每个文件起一个进程。

    注意：上传是并发的，但这个读口是**单进程管道**，必须加锁 ——
    多个线程同时写 stdin / 读 stdout 会把内容读串，直接卡死。
    """

    def __init__(self, repo_path):
        self.proc = subprocess.Popen(
            ['git', '-C', repo_path, 'cat-file', '--batch'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW)
        self.lock = threading.Lock()

    def read(self, sha):
        with self.lock:
            self.proc.stdin.write((sha + '\n').encode('ascii'))
            self.proc.stdin.flush()
            header = self.proc.stdout.readline().decode('ascii', 'replace').strip()
            parts = header.split()
            if len(parts) < 3:
                raise RuntimeError('cat-file 读 %s 失败：%s' % (sha, header))
            size = int(parts[2])
            data = self.proc.stdout.read(size)
            self.proc.stdout.read(1)  # 末尾换行
            return data

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def list_commits(repo_path, branch):
    out = git(repo_path, 'rev-list', '--reverse', branch)
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_meta(repo_path, sha):
    """取提交信息、作者与时间。

    提交信息从**原始提交对象**里切（cat-file commit 的头部之后就是原文），
    比 `git log --format=%B` 可靠：后者会额外补一个换行，差一个字节 SHA 就对不上。
    """
    raw = git(repo_path, 'cat-file', 'commit', sha, binary=True)
    head, sep, message = raw.partition(b'\n\n')
    if not sep:
        raise RuntimeError('提交对象 %s 没有正文分隔' % sha)
    message = message.decode('utf-8', 'replace')
    has_gpg = b'gpgsig ' in head
    fmt = '%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI'
    out = git(repo_path, 'log', '--format=' + fmt, '-1', sha).rstrip('\n')
    an, ae, ai, cn, ce, ci = out.split('\x00')
    return {
        'message': message,
        'author': {'name': an, 'email': ae, 'date': ai},
        'committer': {'name': cn, 'email': ce, 'date': ci},
        'has_gpg': has_gpg,
    }


def list_tree(repo_path, sha):
    """返回 [(mode, type, blobsha, path)]，路径含空格也没关系（用 tab 切分）。"""
    out = git(repo_path, 'ls-tree', '-r', sha)
    rows = []
    for line in out.splitlines():
        if not line:
            continue
        head, _, path = line.partition('\t')
        mode, typ, blob = head.split()
        rows.append((mode, typ, blob, path))
    return rows


def blob_sizes(repo_path, shas):
    """一次 `git cat-file --batch-check` 拿全部 blob 的大小。"""
    if not shas:
        return {}
    proc = subprocess.run(
        ['git', '-C', repo_path, 'cat-file', '--batch-check'],
        input=('\n'.join(shas) + '\n').encode('ascii'),
        capture_output=True, creationflags=CREATE_NO_WINDOW)
    sizes = {}
    for line, sha in zip(proc.stdout.decode('utf-8', 'replace').splitlines(), shas):
        parts = line.split()
        if len(parts) >= 3 and parts[1] == 'blob':
            sizes[sha] = int(parts[2])
    return sizes


def do_check(gh, key, cfg, args):
    print('=== 体检 %s ===' % key)
    exists, info = gh.repo_exists(cfg['name'])
    print('  仓库名 %s：%s' % (cfg['name'], '已存在（会复用）' if exists else '可用'))
    if exists:
        print('    现有可见性：%s  默认分支：%s' % (info.get('visibility'), info.get('default_branch')))
    commits = list_commits(cfg['path'], cfg['branch'])
    blobs = set()
    modes = {}
    for sha in commits:
        for mode, typ, blob, _path in list_tree(cfg['path'], sha):
            if typ == 'blob':
                blobs.add(blob)
                modes[blob] = mode
    total = 0
    biggest = 0
    sizes = blob_sizes(cfg['path'], list(blobs))
    for size in sizes.values():
        total += size
        biggest = max(biggest, size)
    print('  提交 %d 个，唯一 blob %d 个，总字节 %.1f MB，最大单文件 %.2f MB'
          % (len(commits), len(blobs), total / 1048576.0, biggest / 1048576.0))
    print('  预计 API 调用：blob %d + tree %d + commit %d + 少量 = 约 %d 次'
          % (len(blobs), len(commits), len(commits), len(blobs) + 2 * len(commits) + 5))
    return len(commits), len(blobs)


def bootstrap_repo(gh, repo_name):
    """空仓不能直接建 blob 或 tree：GitHub 一律回 409「Git Repository is empty」。

    绕法：用 Contents API 放一个占位文件（会自动生成首个提交与分支），仓就非空了，
    之后 blob/tree 都能建。正式历史建好后把分支指过去，占位提交成为不可达对象，
    不会出现在仓库历史里。
    """
    body = {
        'message': 'bootstrap: temporary placeholder (replaced by the real history right after)',
        'content': base64.b64encode(b'placeholder\n').decode('ascii'),
    }
    try:
        _, data = gh.request('PUT', '/repos/%s/%s/contents/.bootstrap-placeholder'
                             % (gh.owner, repo_name), body)
        sha = data.get('commit', {}).get('sha', '')
        print('  已放占位提交 %s（稍后被正式历史替换）' % sha[:10])
    except ApiError as err:
        if err.status == 422:
            print('  占位文件已存在（仓已非空），跳过')
        else:
            raise


# 单次 tree 请求的条目上限。GitHub 的 tree 接口处理大目录时会 502/422
# （实测 1800 条一个目录就挂），所以大目录要分块、用 base_tree 逐块叠加。
TREE_CHUNK = 250


def _post_tree(gh, repo, entries, base_tree=None):
    body = {'tree': entries}
    if base_tree:
        body['base_tree'] = base_tree
    _, data = gh.request('POST', '/repos/%s/%s/git/trees' % (gh.owner, repo), body,
                         timeout=90, retries=8)
    return data['sha']


def create_tree_recursive(gh, repo, rows, cache, uploaded):
    """自底向上建树。

    GitHub 的 tree 接口一次吃不下两千多条目的**平铺**树：会回 422
    「Sorry, your request timed out ... Consider building the tree incrementally」。
    官方建议就是增量建，这里照做：先把子目录的树建出来，再建父目录的。

    目录本身条目太多（docs/verify 有 1800 多个文件）时，再按块叠：
    第一块直接建，后面的块用 base_tree 指向前一块的结果往上叠。

    缓存按**目录内容**（而不是路径）做：内容相同的目录，git 树对象本来就完全一样，
    SHA 也一样，所以跨提交、跨路径都能复用。
    """
    root = {}
    for mode, _typ, blob, path in rows:
        parts = path.split('/')
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = (mode, uploaded.get(blob, blob))

    def build(node):
        entries = []
        for name in sorted(node.keys()):
            value = node[name]
            if isinstance(value, dict):
                sub_sha = build(value)
                entries.append({'path': name, 'mode': '040000', 'type': 'tree', 'sha': sub_sha})
            else:
                mode, blob = value
                entries.append({'path': name, 'mode': mode, 'type': 'blob', 'sha': blob})
        # 缓存键用目录内容的哈希（不用整段 JSON，否则缓存文件会涨到几 MB）
        key = hashlib.sha1(json.dumps(entries, sort_keys=True).encode('utf-8')).hexdigest()
        if key in cache:
            return cache[key]
        started = time.time()
        if len(entries) <= TREE_CHUNK:
            sha = _post_tree(gh, repo, entries)
        else:
            sha = _post_tree(gh, repo, entries[:TREE_CHUNK])
            for i in range(TREE_CHUNK, len(entries), TREE_CHUNK):
                sha = _post_tree(gh, repo, entries[i:i + TREE_CHUNK], base_tree=sha)
        cache[key] = sha
        if len(entries) > TREE_CHUNK:
            print('      大目录树 %d 条 -> %s（%.1f 秒）'
                  % (len(entries), sha[:10], time.time() - started))
        return sha

    return build(root)


def point_ref_at(gh, repo, branch, sha):
    """把某个分支指到目标提交。

    GitHub 不允许删默认分支（422 Cannot delete the default branch），
    而 PATCH 更新分支又要求**快进** —— 占位提交不是正式历史的祖先，两条路都堵。
    绕法：先建一个临时分支，把默认分支挪到它身上，删掉旧分支，再用目标 SHA 建回来，
    最后把默认分支指回去并删掉临时分支。
    """
    try:
        gh.create_ref(repo, 'refs/heads/' + branch, sha)
        print('  已建 refs/heads/%s' % branch)
        return
    except ApiError as err:
        if err.status != 422:
            raise
    tmp = 'tmp-bootstrap'
    try:
        gh.create_ref(repo, 'refs/heads/' + tmp, sha)
    except ApiError:
        pass
    gh.patch_repo(repo, {'default_branch': tmp})
    gh.request('DELETE', '/repos/hyfdracula/%s/git/refs/heads/%s' % (repo, branch))
    gh.create_ref(repo, 'refs/heads/' + branch, sha)
    gh.patch_repo(repo, {'default_branch': branch})
    try:
        gh.request('DELETE', '/repos/hyfdracula/%s/git/refs/heads/%s' % (repo, tmp))
    except ApiError:
        pass
    print('  已把 refs/heads/%s 指向正式历史尖端（占位分支已清理）' % branch)


def push(gh, key, cfg, args):
    path = cfg['path']
    branch = cfg['branch']
    remote_branch = 'main'
    print('=== 推送 %s -> hyfdracula/%s ===' % (key, cfg['name']))

    exists, info = gh.repo_exists(cfg['name'])
    if not exists:
        if args.dry_run:
            print('  [dry-run] 将创建公开仓 %s' % cfg['name'])
        else:
            created = gh.create_repo(cfg['name'], cfg['description'])
            print('  已创建公开仓：%s（visibility=%s）' % (created.get('html_url'), created.get('visibility')))
    if not args.dry_run:
        # 空仓必须先放占位提交，否则建 blob 一律 409
        bootstrap_repo(gh, cfg['name'])

    commits = list_commits(path, branch)
    print('  本地提交 %d 个，按时间顺序重建' % len(commits))

    # 1) 收集所有出现过的 blob
    blob_modes = {}
    trees = {}
    for sha in commits:
        rows = list_tree(path, sha)
        trees[sha] = rows
        for mode, typ, blob, _p in rows:
            if typ == 'blob':
                blob_modes[blob] = mode
            else:
                print('  跳过非 blob 条目（类型 %s）' % typ)
    blob_list = list(blob_modes.keys())
    print('  唯一 blob %d 个，开始并发上传（%d 线程）' % (len(blob_list), args.workers))

    # 2) 并发上传 blob
    # 断点续传：已传成功的 blob 记在 state_<key>.json 里，重跑时直接跳过（省限流）
    state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state_%s.json' % key)
    uploaded = {}
    if os.path.exists(state_path):
        try:
            uploaded = json.load(io.open(state_path, encoding='utf-8'))
            print('  断点续传：已有 %d 个 blob 传过' % len(uploaded))
        except Exception:
            uploaded = {}
    todo = [b for b in blob_list if b not in uploaded]
    print('  唯一 blob %d 个，本次待传 %d 个（%d 线程）'
          % (len(blob_list), len(todo), args.workers))

    reader = BlobReader(path)
    failed = []
    done = [0]

    def worker(blob_sha):
        data = reader.read(blob_sha)
        b64 = base64.b64encode(data).decode('ascii')
        remote_sha = gh.create_blob(cfg['name'], b64)
        uploaded[blob_sha] = remote_sha
        done[0] += 1
        if done[0] % 25 == 0:
            with lock:
                io.open(state_path, 'w', encoding='utf-8').write(json.dumps(uploaded))
            print('    已上传 %d/%d（限流剩余 %s）' % (done[0], len(todo), gh.rate_remaining))

    lock = threading.Lock()

    def worker_safe(blob_sha):
        try:
            worker(blob_sha)
        except Exception as err:
            with lock:
                failed.append((blob_sha, str(err)))

    start = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(worker_safe, todo))
    finally:
        reader.close()
        io.open(state_path, 'w', encoding='utf-8').write(json.dumps(uploaded))
    print('  blob 上传完成：成功 %d，失败 %d，用时 %.1f 秒'
          % (len(uploaded), len(failed), time.time() - start))

    match = sum(1 for k, v in uploaded.items() if k == v)
    print('  blob SHA 与本地一致：%d / %d' % (match, len(uploaded)))
    for sha, err in failed[:10]:
        print('    上传失败 %s：%s' % (sha, err[:200]))
    if failed:
        raise RuntimeError('有 %d 个 blob 上传失败，中止' % len(failed))

    # 3) 逐个建 tree -> commit
    remote_parent = None
    same = 0
    diff = 0
    diff_list = []
    # 树缓存也落盘：树对象一共就 300 来个，重建一次不贵，但中断重来能省调用
    tree_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'tree_cache_%s.json' % key)
    tree_cache = {}
    if os.path.exists(tree_cache_path):
        try:
            tree_cache = json.load(io.open(tree_cache_path, encoding='utf-8'))
            print('  树缓存续传：%d 条' % len(tree_cache))
        except Exception:
            tree_cache = {}
    for idx, sha in enumerate(commits, 1):
        rows = trees[sha]
        tree_sha = create_tree_recursive(gh, cfg['name'], rows, tree_cache, uploaded)
        meta = commit_meta(path, sha)
        parents = [remote_parent] if remote_parent else []
        remote_sha = gh.create_commit(
            cfg['name'], meta['message'], tree_sha, parents,
            meta['author'], meta['committer'])
        remote_parent = remote_sha
        if remote_sha == sha:
            same += 1
        else:
            diff += 1
            diff_list.append((sha, remote_sha, meta['has_gpg']))
        if idx % 20 == 0 or idx == len(commits):
            io.open(tree_cache_path, 'w', encoding='utf-8').write(json.dumps(tree_cache))
            print('    已建 %d/%d 个提交（树缓存 %d 条，限流剩余 %s）'
                  % (idx, len(commits), len(tree_cache), gh.rate_remaining))
    io.open(tree_cache_path, 'w', encoding='utf-8').write(json.dumps(tree_cache))
    print('  提交 SHA 与本地一致：%d，不一致：%d' % (same, diff))
    for local, remote, gpg in diff_list[:10]:
        print('    %s -> %s%s' % (local[:10], remote[:10], '（本地带 GPG 签名，API 无法复刻）' if gpg else ''))

    # 4) 建 ref + 默认分支
    if args.dry_run:
        print('  [dry-run] 将建 refs/heads/%s -> %s' % (remote_branch, remote_parent))
    else:
        point_ref_at(gh, cfg['name'], remote_branch, remote_parent)
        gh.patch_repo(cfg['name'], {'default_branch': remote_branch})
        print('  默认分支设为 %s' % remote_branch)

    return {
        'repo': cfg['name'],
        'commits': len(commits),
        'blobs': len(uploaded),
        'sha_same': same,
        'sha_diff': diff,
        'failed': failed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', choices=['app', 'spec', 'both'], default='check')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    token = get_token()
    gh = GitHub(token)
    rl = gh.rate_limit()
    core = rl.get('resources', {}).get('core', {})
    print('限流 core：%s / %s，剩余 %s' % (core.get('remaining'), core.get('limit'), core.get('reset')))
    print('token 已在内存中取得（不打印、不落盘）')

    keys = ['app', 'spec'] if args.repo == 'both' else ([args.repo] if args.repo in REPOS else ['app', 'spec'])
    if args.check or args.repo == 'check':
        for key in keys:
            do_check(gh, key, REPOS[key], args)
        return 0

    results = []
    for key in keys:
        if gh.rate_remaining is not None and gh.rate_remaining < RATE_STOP_AT:
            print('限流剩余 %s < %d，停下来报告，不再继续请求' % (gh.rate_remaining, RATE_STOP_AT))
            break
        try:
            results.append(push(gh, key, REPOS[key], args))
        except RateLimitHit as err:
            print('触发限流，停下：%s' % err)
            break
    print('=== 汇总 ===')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print('API 调用次数：%d；限流剩余：%s / %s；二次限流命中：%d'
          % (gh.calls, gh.rate_remaining, gh.rate_limit_max, gh.secondary_hits))
    return 0


if __name__ == '__main__':
    sys.exit(main())
