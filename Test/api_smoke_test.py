"""Backend API 冒烟测试（不依赖 pytest）。

用法（先启动后端服务）：
    .venv\\Scripts\\python.exe Test\\api_smoke_test.py
    .venv\\Scripts\\python.exe Test\\api_smoke_test.py --skip-chat      # 跳过需要调用 LLM 的聊天用例
    .venv\\Scripts\\python.exe Test\\api_smoke_test.py --base-url http://127.0.0.1:8000

覆盖：健康检查、文档列表、非法类型/伪造PDF/重名上传拒绝、正常上传增量构建、
删除、路径穿越拦截、全量重建、聊天（含同会话连续两轮）、历史、会话删除。
"""

import argparse
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_SOURCE = PROJECT_ROOT / "data" / "documents" / "product_c.pdf"
UPLOAD_NAME = "api_smoke_uploaded_product_C.pdf"
EXISTING_NAME = "product_c.pdf"

passed = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    mark = "PASS" if ok else "FAIL"
    suffix = f"  -> {detail}" if detail and not ok else ""
    print(f"[{mark}] {name}{suffix}")
    if ok:
        passed += 1
    else:
        failed += 1


def expect_status(name: str, resp: httpx.Response, code: int, err_code: str = None) -> None:
    ok = resp.status_code == code
    if ok and err_code:
        try:
            ok = resp.json().get("detail", {}).get("code") == err_code
        except Exception:
            ok = False
    check(name, ok, f"status={resp.status_code} body={resp.text[:300]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-chat", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url, timeout=300.0)

    # 1. 健康检查
    resp = client.get("/api/health")
    ok = resp.status_code == 200 and resp.json().get("agent_ready") is True
    check("GET /api/health", ok, resp.text[:300])

    # 2. 文档列表
    resp = client.get("/api/documents")
    ok = resp.status_code == 200 and resp.json().get("total", 0) >= 1
    check("GET /api/documents", ok, resp.text[:300])

    # 3. 错误类型上传（.txt）-> 400 NOT_PDF
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    expect_status("upload .txt 拒绝(400 NOT_PDF)", resp, 400, "NOT_PDF")

    # 4. 扩展名正确但内容非 PDF -> 400 NOT_PDF（魔数校验）
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("fake.pdf", b"this is not a pdf at all", "application/pdf")},
    )
    expect_status("upload 伪造pdf 拒绝(400 NOT_PDF)", resp, 400, "NOT_PDF")

    # 5. 空文件 -> 400 EMPTY_FILE
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    expect_status("upload 空文件 拒绝(400 EMPTY_FILE)", resp, 400, "EMPTY_FILE")

    if UPLOAD_SOURCE.exists():
        data = UPLOAD_SOURCE.read_bytes()

        # 6. 与现有文档重名 -> 409 DUPLICATE_FILENAME
        resp = client.post(
            "/api/documents/upload",
            files={"file": (EXISTING_NAME, data, "application/pdf")},
        )
        expect_status("重复上传 拒绝(409 DUPLICATE_FILENAME)", resp, 409, "DUPLICATE_FILENAME")

        # 7. 正常上传（增量构建，立即生效）
        resp = client.post(
            "/api/documents/upload",
            files={"file": (UPLOAD_NAME, data, "application/pdf")},
        )
        ok = resp.status_code == 201 and resp.json().get("chunks", 0) > 0
        check("upload 新PDF(201, chunks>0)", ok, resp.text[:300])

        # 8. 文档列表包含新文件
        resp = client.get("/api/documents")
        names = [d["filename"] for d in resp.json().get("documents", [])]
        check("文档列表包含新文件", UPLOAD_NAME in names)

        # 9. 删除新文件 + 再次删除 404
        resp = client.delete(f"/api/documents/{UPLOAD_NAME}")
        ok = resp.status_code == 200 and resp.json().get("success") is True
        check(f"delete {UPLOAD_NAME}(200)", ok, resp.text[:300])
        resp = client.delete(f"/api/documents/{UPLOAD_NAME}")
        expect_status("重复删除(404 FILE_NOT_FOUND)", resp, 404, "FILE_NOT_FOUND")

    # 10. 路径穿越拦截：无论路由层如何处理，目标文件都不能被误删
    resp = client.delete("/api/documents/..%2Fproduct_c.pdf")
    blocked = resp.status_code in (400, 404)
    check("路径穿越被拦截(400/404)", blocked, f"status={resp.status_code} body={resp.text[:200]}")
    if UPLOAD_SOURCE.exists():
        resp = client.get("/api/documents")
        names = [d["filename"] for d in resp.json().get("documents", [])]
        check("路径穿越后原文件仍在", EXISTING_NAME in names)

    # 11. 全量重建
    resp = client.post("/api/documents/rebuild")
    ok = resp.status_code == 200 and resp.json().get("chunks", 0) > 0
    check("POST /api/documents/rebuild", ok, resp.text[:300])

    # 12. 聊天：新建会话 + 同会话连续第二轮（验证记忆）+ 历史 + 删除会话
    if not args.skip_chat:
        resp = client.post("/api/chat", json={"question": "你好，请用一句话介绍你自己。"})
        ok = resp.status_code == 200 and bool(resp.json().get("answer")) and resp.json().get("trace") is not None
        check("POST /api/chat 第一轮(新会话)", ok, resp.text[:300])
        if ok:
            sid = resp.json()["session_id"]

            resp = client.post(
                "/api/chat",
                json={"question": "我上一句话问了你什么？", "session_id": sid},
            )
            check("POST /api/chat 第二轮(同会话连续对话)", resp.status_code == 200 and bool(resp.json().get("answer")), resp.text[:300])

            resp = client.get(f"/api/sessions/{sid}/history")
            ok = resp.status_code == 200 and resp.json().get("count", 0) >= 4
            check("GET /api/sessions/{id}/history", ok, resp.text[:300])

            resp = client.delete(f"/api/sessions/{sid}")
            ok = resp.status_code == 200 and resp.json().get("success") is True
            check("DELETE /api/sessions/{id}", ok, resp.text[:300])

            resp = client.get(f"/api/sessions/{sid}/history")
            expect_status("删除后历史404", resp, 404, "SESSION_NOT_FOUND")

    print("=" * 50)
    print(f"结果：{passed} 通过，{failed} 失败")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
