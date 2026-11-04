"""GitHub REST API 的最小客户端（只用标准库 urllib，进程内，零额外依赖）。

为什么不用 git push：本机 github.com 被墙（git push / git ls-remote 都是连接重置），
但 api.github.com 通。所以整条链路走 REST 的 Git Data API
（blobs / trees / commits / refs）。

凭据：token 由 `gh auth token` 在内存里取，只放请求头，绝不落盘、不进日志、不进报告。

限流：GitHub 的「core」限额是 5000 次/小时；每个响应都带 X-RateLimit-Remaining，
这里做全局跟踪，接近上限时调用方可以停下来报告，而不是盲目重试。
"""

import http.client
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Windows: 子进程默认会弹控制台窗口，必须带 CREATE_NO_WINDOW
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

API_ROOT = 'https://api.github.com'
OWNER = 'hyfdracula'
UA = 'dsh'


class RateLimitHit(Exception):
    """触发 GitHub 限流（429 / 403 secondary limit）。"""


class ApiError(Exception):
    def __init__(self, status, body, url):
        super().__init__('HTTP %s %s: %s' % (status, url, str(body)[:400]))
        self.status = status
        self.body = body


def get_token():
    """用 gh CLI 取 token（gh 已登录 keyring）。只返回到内存，不打印。"""
    proc = subprocess.run(
        ['gh', 'auth', 'token'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        creationflags=CREATE_NO_WINDOW)
    if proc.returncode != 0:
        raise RuntimeError('gh auth token 失败：' + (proc.stderr or '').strip()[:200])
    token = (proc.stdout or '').strip()
    if not token:
        raise RuntimeError('gh auth token 返回空')
    return token


class GitHub:
    def __init__(self, token, owner=OWNER):
        self.token = token
        self.owner = owner
        self.calls = 0
        self.rate_remaining = None
        self.rate_limit_max = None
        self.rate_reset = None
        self.secondary_hits = 0

    def _headers(self):
        return {
            'Authorization': 'Bearer ' + self.token,
            'User-Agent': UA,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }

    def request(self, method, path, body=None, raw_body=None, retries=6, timeout=180):
        """发一次请求。body 为 dict 时自动 JSON 编码；raw_body 为 bytes 时原样发送。

        重试口径：GitHub 的 400「malformed request」与 401「Bad credentials」在这里是
        **传输层串包**（连接被复用/截断时服务端的报错），不是真凭据问题；
        连同 429、二次限流、5xx、连接被重置一并退避重试。
        """
        url = API_ROOT + path
        data = None
        headers = self._headers()
        if raw_body is not None:
            data = raw_body
            headers['Content-Type'] = 'application/octet-stream'
        elif body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        delay = 3
        last = None
        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    self._track(resp.headers)
                    self.calls += 1
                    return resp.status, json.loads(resp.read().decode('utf-8') or '{}')
            except urllib.error.HTTPError as err:
                self._track(err.headers)
                self.calls += 1
                payload = err.read().decode('utf-8', 'replace')
                try:
                    parsed = json.loads(payload or '{}')
                except ValueError:
                    parsed = {'raw': payload[:300]}
                text = payload.lower()
                garbled = ('malformed request' in text) or (err.code == 401)
                throttled = (err.code == 429) or (err.code == 403 and 'rate limit' in text)
                server_side = err.code >= 500
                if garbled or throttled or server_side:
                    self.secondary_hits += 1
                    last = 'HTTP %s %s: %s' % (err.code, url, payload[:200])
                    if attempt == retries - 1:
                        raise RateLimitHit(last)
                    time.sleep(delay + (attempt * 0.7))
                    delay = min(delay * 2, 90)
                    continue
                raise ApiError(err.code, parsed, url)
            except (urllib.error.URLError, ConnectionError, http.client.HTTPException,
                    socket.timeout, OSError) as err:
                last = '%s %s: %s' % (type(err).__name__, url, str(err)[:200])
                if attempt == retries - 1:
                    raise ApiError(0, {'error': last}, url)
                time.sleep(delay + (attempt * 0.7))
                delay = min(delay * 2, 90)
        raise ApiError(0, {'error': last or 'retries exhausted'}, url)

    def _track(self, headers):
        try:
            rem = headers.get('X-RateLimit-Remaining')
            lim = headers.get('X-RateLimit-Limit')
            rst = headers.get('X-RateLimit-Reset')
        except AttributeError:
            return
        if rem is not None:
            rem = int(rem)
            self.rate_remaining = rem if self.rate_remaining is None else min(self.rate_remaining, rem)
        if lim is not None:
            self.rate_limit_max = int(lim)
        if rst is not None:
            self.rate_reset = int(rst)

    # ------------------------------------------------------------ 具体接口

    def rate_limit(self):
        _, data = self.request('GET', '/rate_limit')
        return data

    def repo_exists(self, name):
        try:
            _, data = self.request('GET', '/repos/%s/%s' % (self.owner, name))
            return True, data
        except ApiError as err:
            if err.status == 404:
                return False, None
            raise

    def create_repo(self, name, description):
        _, data = self.request('POST', '/user/repos', {
            'name': name,
            'private': False,
            'description': description,
            'auto_init': False,
        })
        return data

    def create_blob(self, repo, content_b64):
        _, data = self.request('POST', '/repos/%s/%s/git/blobs' % (self.owner, repo), {
            'content': content_b64,
            'encoding': 'base64',
        })
        return data['sha']

    def create_tree(self, repo, entries):
        _, data = self.request('POST', '/repos/%s/%s/git/trees' % (self.owner, repo), {
            'tree': entries,
        })
        return data['sha']

    def create_commit(self, repo, message, tree, parents, author, committer):
        _, data = self.request('POST', '/repos/%s/%s/git/commits' % (self.owner, repo), {
            'message': message,
            'tree': tree,
            'parents': parents,
            'author': author,
            'committer': committer,
        })
        return data['sha']

    def create_ref(self, repo, ref, sha):
        _, data = self.request('POST', '/repos/%s/%s/git/refs' % (self.owner, repo), {
            'ref': ref,
            'sha': sha,
        })
        return data

    def patch_repo(self, repo, fields):
        _, data = self.request('PATCH', '/repos/%s/%s' % (self.owner, repo), fields)
        return data

    def get_commit(self, repo, sha):
        _, data = self.request('GET', '/repos/%s/%s/git/commits/%s' % (self.owner, repo, sha))
        return data

    # ------------------------------------------------------------ release

    def create_release(self, repo, tag, name, body, prerelease=False, draft=False):
        """建一个 release（附件随后用 upload_asset 传）。"""
        _, data = self.request('POST', '/repos/%s/%s/releases' % (self.owner, repo), {
            'tag_name': tag,
            'name': name,
            'body': body,
            'prerelease': prerelease,
            'draft': draft,
        })
        return data

    def upload_asset(self, repo, release_id, filename, data, content_type='application/octet-stream'):
        """往 release 上传一个附件。

        上传走的是**另一个域名** `uploads.github.com`（不是 api.github.com），
        所以这里不用通用的 request()，自己发一次。

        为什么必须分两个域名（实测）：GitHub 的 release 附件上传接口只认
        uploads.github.com；本机 github.com 被墙，但 uploads/api/objects
        三个域名都通 ✓（2026-11-04 实测）。
        """
        url = ('https://uploads.github.com/repos/%s/%s/releases/%s/assets?name=%s'
               % (self.owner, repo, release_id, urllib.parse.quote(filename)))
        headers = self._headers()
        headers['Content-Type'] = content_type
        last = None
        delay = 3
        for attempt in range(4):
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=900) as resp:
                    self._track(resp.headers)
                    self.calls += 1
                    return json.loads(resp.read().decode('utf-8') or '{}')
            except urllib.error.HTTPError as err:
                self._track(err.headers)
                self.calls += 1
                payload = err.read().decode('utf-8', 'replace')
                last = 'HTTP %s: %s' % (err.code, payload[:300])
                if err.status not in (502, 503, 504) and 'timeout' not in payload.lower():
                    raise ApiError(err.status, payload, url)
            except (urllib.error.URLError, ConnectionError, socket.timeout, OSError) as err:
                last = '%s: %s' % (type(err).__name__, str(err)[:200])
            time.sleep(delay)
            delay = min(delay * 2, 60)
        raise ApiError(0, {'error': last or 'upload failed'}, url)

    def get_release_by_tag(self, repo, tag):
        try:
            _, data = self.request('GET', '/repos/%s/%s/releases/tags/%s'
                                   % (self.owner, repo, urllib.parse.quote(tag)))
            return data
        except ApiError as err:
            if err.status == 404:
                return None
            raise
