#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""law-cli 纯函数单测（零依赖，仅标准库）。

覆盖 split_articles / cn_to_int / parse_range 的已知边界：
- 中文/阿拉伯数字；
- 条文内交叉引用不应产生伪条文（连续脊启发式）；
- 跳号边界；
- parse_range 区间与离散。
"""
import contextlib
import io
import os
import sys
import tempfile
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import law_cli  # noqa: E402


def test_cn_to_int():
    assert law_cli.cn_to_int("1") == 1
    assert law_cli.cn_to_int("5") == 5
    assert law_cli.cn_to_int("十") == 10
    assert law_cli.cn_to_int("二十一") == 21
    assert law_cli.cn_to_int("九十九") == 99
    assert law_cli.cn_to_int("一百零八") == 108
    assert law_cli.cn_to_int("零") == 0
    assert law_cli.cn_to_int("foo") is None


def test_parse_range():
    assert law_cli.parse_range("1-5") == {"1", "2", "3", "4", "5"}
    assert law_cli.parse_range("1,3,5") == {"1", "3", "5"}
    assert law_cli.parse_range("2-4,7") == {"2", "3", "4", "7"}


def test_split_articles_basic():
    text = "第一条 内容A。\n第二条 内容B。\n第三条 内容C。"
    out = law_cli.split_articles(text)
    assert out == {"1": "第一条 内容A。", "2": "第二条 内容B。", "3": "第三条 内容C。"}


def test_split_articles_cross_reference():
    # 真实场景：第1-3条连续，第2条正文内引用"第五十一条"不应被切成伪条文/截断
    text = ("第一条 规定A。\n"
            "第二条 违反本条规定的，依照本条例第五十一条规定处罚；本条自公布之日起施行。\n"
            "第三条 规定C。")
    out = law_cli.split_articles(text)
    assert out == {"1": "第一条 规定A。", "2": "第二条 违反本条规定的，依照本条例第五十一条规定处罚；本条自公布之日起施行。", "3": "第三条 规定C。"}
    # 第2条正文应包含其对第五十一条的引用，而非被截断
    assert "第五十一条" in out["2"]
    assert out["2"].startswith("第二条")
    assert "51" not in out  # 引用不生成伪条文


def test_split_articles_skip_preface():
    # 修订决定前置引用"第十二条规定"不应被当作正文起点（无"第1条"）
    text = ("根据某某法律第十二条规定，作如下修改：\n"
            "第一条 真正正文起点。\n第二条 续。")
    out = law_cli.split_articles(text)
    assert "1" in out and out["1"].startswith("第一条")
    assert "根据" not in out  # 前置引用不应成伪条


def test_migrate_db_adds_fields():
    db = {"schema_version": 1, "records": [{"law": "x", "article": "1", "text": "t", "source": {}, "sha256": "z"}]}
    out = law_cli.migrate_db(db)
    assert out["schema_version"] == 2
    rec = out["records"][0]
    assert "lineage" in rec and "review_status" in rec
    assert rec["review_status"] == "pending"


def test_split_official_strips_trailing_chapter_and_blank():
    # 真实种子结构：条正文末行 -> 空行 -> "第X章"标题 -> 空行 -> 下一「第Y条」。
    # _split_official 须剥离尾部空行与章标题，否则会把章标题误报为实质性差异。
    text = ("第一条 甲。\n"
            "\n"
            "第二章 规划与建设\n"
            "\n"
            "第二条 乙。\n")
    # _split_official 接收路径，故写入临时文件再测
    fd, p = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        out = law_cli._split_official(p)
    finally:
        os.remove(p)
    assert out["1"] == "第一条 甲。", f"第1条残留章标题: {out['1']!r}"
    assert out["2"] == "第二条 乙。", f"第2条异常: {out['2']!r}"


def test_reconcile_surfaces_amended_version_diffs():
    # 同一法两条版本（2019基线 + 2026修正版）同条号；官方全文为2019原文。
    # reconcile 必须逐版本核对，不能 dict 去重把 2026 版的差异掩盖成「一致」。
    official = "第一条 甲。\n\n第二章 建设\n\n第二条 乙。\n"
    fd, p = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(official)
    try:
        db = {"schema_version": 2, "records": [
            {"law": "X法", "article": "1", "text": "第一条 甲。",
             "source": {"version_tag": "2019通过"}, "sha256": "", "disclaimer": "",
             "lineage": {}, "review_status": "pending", "reviewed_by": "", "review_date": ""},
            {"law": "X法", "article": "1", "text": "第一条 甲。丙。",  # 2026版：多一句
             "source": {"version_tag": "2026修正"}, "sha256": "", "disclaimer": "",
             "lineage": {}, "review_status": "pending", "reviewed_by": "", "review_date": ""},
        ]}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            law_cli.reconcile(db, p, "X法")
        out = buf.getvalue()
    finally:
        os.remove(p)
    # 必须报出 1 处实质性差异（2026版），而非因去重而误报 0
    assert "实质性差异 1" in out, f"reconcile 未暴露修正版差异:\n{out}"
    assert "X法.1 [2026修正]" in out, "差异应标注版本"


def test_whitelist_no_spcsc():
    # spcsc.sh.cn 实测已被体育直播站占用，已从官方白名单移除；
    # 上海官方源一律走 *.gov.cn，地方条例重新公布全文 canonical 取 flk.npc.gov.cn。
    assert "spcsc.sh.cn" not in law_cli.OFFICIAL_DOMAINS, "spcsc.sh.cn 不应再在白名单"
    assert "flk.npc.gov.cn" in law_cli.OFFICIAL_DOMAINS, "国家法律法规数据库须在白名单"
    assert "gov.cn" in law_cli.OFFICIAL_DOMAINS


def test_reconcile_order_mismatch():
    # 修正决定常"对条文顺序作相应调整"；reconcile 须能报出条序不一致。
    import tempfile as _t
    fd, p = _t.mkstemp(suffix=".txt")
    os.write(fd, "第一条 甲。\n第二章 规划与建设\n第二条 乙。\n".encode("utf-8"))
    os.close(fd)
    db = {"schema_version": 2, "records": [
        {"law": "Y法", "article": "1", "text": "第一条 甲。",
         "source": {"version_tag": "2026修正"}, "sha256": "", "disclaimer": "",
         "lineage": {}, "review_status": "pending", "reviewed_by": "", "review_date": ""},
        {"law": "Y法", "article": "2", "text": "第二条 乙。",
         "source": {"version_tag": "2026修正"}, "sha256": "", "disclaimer": "",
         "lineage": {}, "review_status": "pending", "reviewed_by": "", "review_date": ""},
    ]}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        law_cli.reconcile(db, p, "Y法")
    out = buf.getvalue()
    os.remove(p)
    # DB 顺序 [1,2] 与官方顺序 [1,2] 一致 → 不应报条序不一致
    assert "条序不一致" not in out, f"不应误报条序不一致:\n{out}"
    # 故意构造顺序不同：DB 为 [2,1]
    db["records"][0]["article"] = "2"
    db["records"][1]["article"] = "1"
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        law_cli.reconcile(db, p := _t.mkstemp(suffix=".txt")[1], "Y法") if False else None
    # 重新写官方文件并跑
    fd2, p2 = _t.mkstemp(suffix=".txt")
    os.write(fd2, "第一条 甲。\n第二章 规划与建设\n第二条 乙。\n".encode("utf-8"))
    os.close(fd2)
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        law_cli.reconcile(db, p2, "Y法")
    os.remove(p2)
    assert "条序不一致" in buf2.getvalue(), "应报出条序不一致"


def test_close_O1_dry_run():
    # 烟雾测试：close_O1 在 --dry-run 下应跑通且不写库。
    # 以 2019 基线全文作为"官方"代理，2026 版差异恰为已知修正点 {1,21,37,57}。
    import sys as _sys
    import close_O1_shanghai_2026 as c1
    seed = os.path.abspath(os.path.join(
        os.path.dirname(law_cli.DB_PATH), "..",
        "seed", "上海市生活垃圾管理条例_2019通过_全文_官方原文_备份2019版.txt"))
    if not os.path.exists(seed):
        print("⚠ test_close_O1_dry_run 跳过：缺基线种子")
        return
    argv = _sys.argv
    _sys.argv = ["close_O1", "--official", seed, "--dry-run"]
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            c1.main()
        out = buf.getvalue()
    finally:
        _sys.argv = argv
    assert "dry-run" in out, f"close_O1 dry-run 未正常输出:\n{out}"
    assert "将对" in out and "写入" in out, f"close_O1 dry-run 未给出写入说明:\n{out}"


def test_whitelist_blocks_non_official():
    # 复制 cmd_fetch 的域名闸门逻辑：白名单外一律拒绝。
    blocked = [
        "https://www.spcsc.sh.cn/x",   # 曾遭劫持的域，已移出白名单
        "http://spcsc.sh.cn/x",
        "https://www.wkinfo.com.cn/x",  # 商业库
    ]
    allowed = [
        "https://www.gov.cn/y",        # 根域
        "https://www.jiading.gov.cn/y",  # 次级官方域（gov.cn 覆盖）
        "https://flk.npc.gov.cn/y",
    ]
    for u in blocked:
        host = urllib.parse.urlparse(u).hostname or ""
        ok = any(host == d or host.endswith("." + d) for d in law_cli.OFFICIAL_DOMAINS)
        assert not ok, f"白名单应拒绝非官方域: {u}"
    for u in allowed:
        host = urllib.parse.urlparse(u).hostname or ""
        ok = any(host == d or host.endswith("." + d) for d in law_cli.OFFICIAL_DOMAINS)
        assert ok, f"白名单应放行官方域: {u}"


def test_show_version_filter():
    # show --version 应能从一个多版本法条中过滤出指定版本。
    import argparse
    import json as _json
    db = {
        "schema_version": 2,
        "records": [
            {"law": "X法", "article": "1", "text": "甲",
             "source": {"version_tag": "v1"}, "lineage": {},
             "review_status": "pending", "reviewed_by": "", "review_date": "",
             "sha256": "", "disclaimer": ""},
            {"law": "X法", "article": "1", "text": "乙",
             "source": {"version_tag": "v2"}, "lineage": {},
             "review_status": "pending", "reviewed_by": "", "review_date": "",
             "sha256": "", "disclaimer": ""},
        ],
    }
    fd, p = tempfile.mkstemp(suffix=".json")
    os.write(fd, _json.dumps(db, ensure_ascii=False).encode("utf-8"))
    os.close(fd)
    old = law_cli.DB_PATH
    law_cli.DB_PATH = __import__("pathlib").Path(p)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            law_cli.cmd_show(argparse.Namespace(
                query="X法.1", version="v1", law=None))
        out = buf.getvalue()
        assert "甲" in out and "乙" not in out, f"版本过滤失效:\n{out}"
    finally:
        law_cli.DB_PATH = old
        os.remove(p)


def test_gate_accepts_ai_verified():
    # 口径：AI 审核即终核。review_status=ai_verified 应通过闸门（exit 0），不再要求律师签署。
    import argparse
    db = {"schema_version": 2, "records": [
        {"law": "X法", "article": "1", "text": "甲",
         "source": {"version_tag": "v1"}, "lineage": {},
         "review_status": "ai_verified", "reviewed_by": "AI审核", "review_date": "2026-08-28",
         "sha256": law_cli.sha256("甲"), "disclaimer": ""},
    ]}
    fd, p = tempfile.mkstemp(suffix=".json")
    os.write(fd, law_cli.json.dumps(db, ensure_ascii=False).encode("utf-8"))
    os.close(fd)
    old = law_cli.DB_PATH
    law_cli.DB_PATH = __import__("pathlib").Path(p)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                law_cli.cmd_verify(argparse.Namespace(
                    gate=True, reconcile=False, law=None, official=None))
            except SystemExit as e:
                assert e.code == 0, f"gate 应放行 ai_verified，却 exit {e.code}"
        assert "闸门通过" in buf.getvalue(), f"gate 未输出通过:\n{buf.getvalue()}"
    finally:
        law_cli.DB_PATH = old
        os.remove(p)


def test_gate_blocks_pending():
    # 仅存在 pending（未经审核）记录时，闸门必须关闭（exit 1）。
    import argparse
    db = {"schema_version": 2, "records": [
        {"law": "X法", "article": "1", "text": "甲",
         "source": {"version_tag": "v1"}, "lineage": {},
         "review_status": "pending", "reviewed_by": "", "review_date": "",
         "sha256": law_cli.sha256("甲"), "disclaimer": ""},
    ]}
    fd, p = tempfile.mkstemp(suffix=".json")
    os.write(fd, law_cli.json.dumps(db, ensure_ascii=False).encode("utf-8"))
    os.close(fd)
    old = law_cli.DB_PATH
    law_cli.DB_PATH = __import__("pathlib").Path(p)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                law_cli.cmd_verify(argparse.Namespace(
                    gate=True, reconcile=False, law=None, official=None))
            except SystemExit as e:
                assert e.code == 1, f"gate 应因 pending 关闭，却 exit {e.code}"
        assert "闸门失败" in buf.getvalue(), f"gate 未输出失败:\n{buf.getvalue()}"
    finally:
        law_cli.DB_PATH = old
        os.remove(p)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✓ {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"✗ {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} 通过" + ("（有失败）" if failed else "（全部通过）"))
    sys.exit(1 if failed else 0)
