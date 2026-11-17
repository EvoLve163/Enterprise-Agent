# -*- coding: utf-8 -*-
"""阶段六异常测试（主后端 127.0.0.1:8000 在线时的 HTTP 级异常用例）。

用法:
    .venv/Scripts/python.exe Test/exception_test.py [--base-url http://127.0.0.1:8000]
"""
import io
import sys
import time
import argparse

import httpx

BASE = "http://127.0.0.1:8000"
PASSED = 0
FAILED = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    mark = "PASS" if cond else "FAIL"
    if cond:
        PASSED += 1
    else:
        FAILED += 1
    print(f"[{mark}] {name}" + (f" | {detail}" if detail and not cond else ""))


def expect_status(name: str, resp: httpx.Response, *codes: int) -> None:
    check(name, resp.status_code in codes, f"HTTP {resp.status_code}: {resp.text[:200]}")


def main() -> None:
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE)
    args = parser.parse_args()
    BASE = args.base_url

    client = httpx.Client(base_url=BASE, timeout=180.0, trust_env=False)  # trust_env=False: 绕过系统代理直连本机

    # ---- 前置: 后端在线 ----
    try:
        health = client.get("/api/health")
    except Exception as exc:  # noqa: BLE001
        print(f"后端不可达，请先启动: {exc}")
        sys.exit(2)
    check("E0 后端在线 /api/health", health.status_code == 200)

    # ---- E1 上传非 PDF (txt) -> 400 NOT_PDF ----
    r = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    expect_status("E1 上传非PDF(.txt) 拒绝", r, 400)
    check("E1b 错误码 NOT_PDF", r.json().get("detail", {}).get("code") == "NOT_PDF", r.text[:200])

    # ---- E2 上传空文件(.pdf 后缀但 0 字节) -> 400 EMPTY_FILE ----
    r = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    expect_status("E2 上传空文件 拒绝", r, 400)
    check("E2b 错误码 EMPTY_FILE", r.json().get("detail", {}).get("code") == "EMPTY_FILE", r.text[:200])

    # ---- E3 伪造 PDF(魔数通过但结构非法) -> 结构化错误拒绝(400 NOT_PDF 或 502 INDEX_BUILD_FAILED) ----
    r = client.post(
        "/api/documents/upload",
        files={"file": ("fake.pdf", b"%PDF-this-is-not-a-real-pdf" * 10, "application/pdf")},
    )
    code = r.json().get("detail", {}).get("code", "")
    expect_status("E3 伪造PDF(魔数后无合法结构) 拒绝", r, 400, 502)
    check("E3b 拒绝且错误结构化(code)", code in ("NOT_PDF", "INDEX_BUILD_FAILED"), f"HTTP {r.status_code} code={code}")
    names = {d["filename"] for d in client.get("/api/documents").json()["documents"]}
    check("E3c 失败上传不留孤儿文件(fake.pdf 不在列表)", "fake.pdf" not in names, str(names))

    # ---- E4 删除不存在的文档 -> 404 ----
    r = client.delete("/api/documents/no_such_file_xyz.pdf")
    expect_status("E4 删除不存在文档 -> 404", r, 404)

    # ---- E5 路径穿越文件名 -> 拒绝且原文件不受影响 ----
    before = {d["filename"] for d in client.get("/api/documents").json()["documents"]}
    r = client.delete("/api/documents/..%2F..%2Frequirements.txt.pdf")
    expect_status("E5 路径穿越删除 拦截(400/404/422)", r, 400, 404, 422)
    after = {d["filename"] for d in client.get("/api/documents").json()["documents"]}
    check("E5b 原有文档未受影响", before == after, f"{before} -> {after}")

    # ---- E6 超长问题 -> 422 ----
    r = client.post("/api/chat", json={"question": "长" * 2001})
    expect_status("E6 超长问题(2001字) -> 422", r, 422)

    # ---- E7 非法 session_id -> 422 ----
    r = client.post("/api/chat", json={"question": "你好", "session_id": "bad id!!"})
    expect_status("E7 非法session_id -> 422", r, 422)

    # ---- E8 查询不存在会话历史 -> 404 ----
    r = client.get("/api/sessions/nonexistent_session_000/history")
    expect_status("E8 不存在会话历史 -> 404", r, 404)

    # ---- E9 calculator 除零(真实 LLM 调用, 工具内部报错被优雅处理) ----
    t0 = time.time()
    r = client.post("/api/chat", json={"question": "请用 calculator 工具精确计算 100/0 等于多少？"})
    ok = r.status_code == 200
    check("E9 除零问题 /api/chat 正常返回(工具错误不击穿接口)", ok, f"HTTP {r.status_code}: {r.text[:200]}")
    if ok:
        data = r.json()
        answer = data["answer"]
        tools = [t for step in data["trace"] for t in (step.get("detail") or []) if isinstance(step.get("detail"), list)]
        check("E9b trace 中调用了 calculator", "calculator" in tools, str(tools))
        check(
            "E9c 回答如实说明无法计算/除零(未编造数值)",
            any(k in answer for k in ("无法", "不能", "除零", "未定义", "错误", "失败")),
            answer[:200],
        )
        print(f"      (E9 耗时 {time.time() - t0:.1f}s, 回答节选: {answer[:120]!r})")

    print(f"\n==== 异常测试(HTTP级): {PASSED} passed, {FAILED} failed ====")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
