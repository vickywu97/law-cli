#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A1 核验工具：上海市生活垃圾管理条例（2026 修正版）逐条（第X条）比对
------------------------------------------------------------------
把本地 seed（已按 2026-07-29 修正案 diff 更新）与官方"重新公布全文"
逐条比对，报告哪些条文逐字一致、哪些有差异。

用法：
    python3 verify_shanghai_a1.py [官方全文txt路径]

- 默认官方路径 = ./_official_shanghai_2026.txt
  （请把《上海市生活垃圾管理条例》2026 修正重新公布全文保存为 UTF-8 放这里）
- seed 路径默认 = ./seed/上海市生活垃圾管理条例_2019通过_全文_官方原文.txt
  （注：该文件名虽带"2019通过"，但内容已是 2026 修正版）

比对口径：
- 先按"行首第X条"切分为条文；
- 正文比较时忽略所有空白（换行/空格），以捕获"实质性"差异；
- 若有差异，用 unified_diff 展示 seed 与官方的行级差异，供人工复核。

注意：若官方全文含"目录"且目录里也出现"第X条"，可能干扰切分；
      出现明显噪声时，请先去掉目录再比对（脚本会列出差异供判断）。
"""
import sys
import os
import re
import difflib

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "seed", "上海市生活垃圾管理条例_2019通过_全文_官方原文.txt")
DEFAULT_OFFICIAL = os.path.join(HERE, "_official_shanghai_2026.txt")

ART_RE = re.compile(r"^第([一二三四五六七八九十百零0-9]+)条")


def split_articles(path):
    """按行首'第X条'切分为 {序号: 正文}。返回 (dict, err)。"""
    if not os.path.exists(path):
        return None, "文件不存在: %s" % path
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    arts = {}
    cur = None
    buf = []
    for ln in lines:
        m = ART_RE.match(ln.strip())
        if m:
            if cur is not None:
                arts[cur] = "\n".join(buf).strip()
            cur = m.group(1)
            buf = [ln]
        else:
            if cur is not None:
                buf.append(ln)
    if cur is not None:
        arts[cur] = "\n".join(buf).strip()
    return arts, None


def norm(s):
    return re.sub(r"\s+", "", s)


def sort_key(k):
    return (len(k), k)


def main():
    official_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OFFICIAL

    seed_arts, err1 = split_articles(SEED)
    off_arts, err2 = split_articles(official_path)

    if err1:
        print("SEED 读取错误:", err1)
        sys.exit(1)
    if err2:
        print("[阻塞] 官方重新公布全文尚未就位：%s" % err2)
        print("请把《上海市生活垃圾管理条例》（2026 修正重新公布全文）保存为 UTF-8：")
        print("    %s" % official_path)
        print("本地 seed 已识别条文数：%d 条" % len(seed_arts))
        print("放置文件后重新运行：python3 verify_shanghai_a1.py")
        sys.exit(2)

    print("seed 条文数 = %d    官方条文数 = %d" % (len(seed_arts), len(off_arts)))

    only_seed = set(seed_arts) - set(off_arts)
    only_off = set(off_arts) - set(seed_arts)
    common = set(seed_arts) & set(off_arts)

    exact = 0
    diffs = []
    for k in common:
        if norm(seed_arts[k]) == norm(off_arts[k]):
            exact += 1
        else:
            diffs.append(k)

    print("共有条数 = %d    逐字一致(忽略空白) = %d    有差异 = %d"
          % (len(common), exact, len(diffs)))

    if only_seed:
        print("仅 seed 有（官方缺失）:", sorted(only_seed, key=sort_key))
    if only_off:
        print("仅官方有（seed 缺失）:", sorted(only_off, key=sort_key))

    for k in sorted(diffs, key=sort_key):
        print("\n=== 第%s条 差异（官方→seed）===" % k)
        sd = seed_arts[k].splitlines()
        od = off_arts[k].splitlines()
        for line in difflib.unified_diff(od, sd, fromfile="官方", tofile="seed", lineterm=""):
            print(line)

    if not diffs and not only_seed and not only_off:
        print("\n✅ A1 逐字核通过：seed 与官方重新公布全文完全一致（忽略空白差异）。")
    else:
        print("\n⚠️ A1 存在需人工复核的差异，详见上文。")


if __name__ == "__main__":
    main()
