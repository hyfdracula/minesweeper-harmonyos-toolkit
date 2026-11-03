# -*- coding: utf-8 -*-
"""
check_sign_profile.py —— 看调试签名的 profile 授权了哪些设备。

为什么需要这个工具（2026-11-03）：
  HarmonyOS NEXT（API 26）的设备只认**华为云签发**的调试 profile，
  里面的 `debug-info.device-ids` 是设备白名单。
  profile 里没有这台设备的 UDID，就会被拒：
      code:9568423  device is unauthorized,
      make sure the UDID of your device is configured in the signing profile

  白名单里的 UDID **不是 hdc 的序列号**，是设备自己的 64 位十六进制 UDID，
  用 `hdc shell bm get --udid` 取。

用法：
    python tools\\check_sign_profile.py                 # 列出来 + 对比已连接设备
    python tools\\check_sign_profile.py --expect <udid> # 断言某个 UDID 在里面
"""
import argparse
import glob
import json
import os
import re
import subprocess

PROFILE_DIR = os.path.expanduser(r"~\\.ohos\\config")
HDC = r"D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"


def load_profile(path):
    """从 .p7b 里抠出那段 JSON（外层是云签的 PKCS#7）。"""
    data = open(path, "rb").read()
    start = data.find(b"{")
    if start < 0:
        raise ValueError("profile 里没找到 JSON 部分")
    depth = 0
    end = None
    for i in range(start, len(data)):
        c = data[i:i + 1]
        if c == b"{":
            depth += 1
        elif c == b"}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise ValueError("profile 的 JSON 不完整")
    return json.loads(data[start:end].decode("utf-8", errors="replace"))


def connected_devices():
    """已连接设备的 (序列号, UDID) 列表。"""
    out = []
    try:
        targets = subprocess.run([HDC, "list", "targets"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace",
                                 timeout=60).stdout
    except Exception:
        return out
    for line in targets.splitlines():
        line = line.strip()
        if not line or line.startswith("["):
            continue
        serial = line.split()[0]
        try:
            r = subprocess.run([HDC, "-t", serial, "shell", "bm get --udid"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=60).stdout
        except Exception:
            continue
        m = re.search(r"([0-9A-F]{64})", r or "")
        out.append((serial, m.group(1) if m else None))
    return out


def main():
    ap = argparse.ArgumentParser(description="查调试签名的 profile 授权了哪些设备")
    ap.add_argument("--expect", help="断言这个 UDID 在授权列表里")
    ap.add_argument("--profile", help="指定 .p7b 路径（默认取 ~/.ohos/config 下那个）")
    args = ap.parse_args()

    if args.profile:
        path = args.profile
    else:
        files = sorted(glob.glob(os.path.join(PROFILE_DIR, "*.p7b")))
        if not files:
            print("没找到 profile：%s" % PROFILE_DIR)
            return 1
        path = files[0]
    print("profile: %s" % path)

    prof = load_profile(path)
    ids = prof.get("debug-info", {}).get("device-ids", []) or []
    bundle = prof.get("bundle-info", {}).get("bundle-name")
    issuer = prof.get("issuer")
    print("bundle-name: %s   issuer: %s" % (bundle, issuer))
    print("授权设备 %d 台：" % len(ids))
    for i in ids:
        print("   %s" % i)

    devs = connected_devices()
    if devs:
        print("当前已连接设备：")
        for serial, udid in devs:
            ok = "已授权" if udid in ids else "**未授权**"
            print("   %-20s %s  %s" % (serial, udid or "（取不到 UDID）", ok))

    if args.expect:
        hit = args.expect.upper() in [i.upper() for i in ids]
        print("期望的 UDID %s：%s" % (args.expect, "在授权列表里" if hit else "**不在**"))
        return 0 if hit else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
