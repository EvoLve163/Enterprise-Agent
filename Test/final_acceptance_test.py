"""最终验收联调测试（阶段六）。

前置：后端已启动（默认 http://127.0.0.1:8000），.env 已配置可用 LLM key。
用法：
    .venv\\Scripts\\python.exe Test\\final_acceptance_test.py
    .venv\\Scripts\\python.exe Test\\final_acceptance_test.py --base-url http://127.0.0.1:8000

覆盖（全部真实调用，无 mock）：
  A1 健康检查
  A2 聊天-问候（无工具路径）
  A3 聊天-calculator 工具 + trace 结构校验（同会话连续对话）
  A4 聊天-knowledge_search 工具 + 引用来源
  A5 PDF 上传入库（增量）
  A6 新文档立即可检索（上传后新会话问答）
  A7 删除文档后 FAISS 同步（新会话问答不再命中）
  A8 知识库全量重建
  A9 评测接口：启动→防重复409→轮询至完成→结果校验
  A10 会话历史（assistant 轮带 trace）与会话删除
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZENITH_PDF = Path(__file__).resolve().parent / "zenith_test_manual.pdf"
ZENITH_NAME = "zenith_test_manual.pdf"

passed = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    mark = "PASS" if ok else "FAIL"
    suffix = f"  -> {detail}" if detail and not ok else ""
    print(f"[{mark}] {name}{suffix}", flush=True)
    if ok:
        passed += 1
    else:
        failed += 1


def ask(client: httpx.Client, question: str, session_id: str = None) -> dict:
    payload = {"question": question}
    if session_id:
        payload["session_id"] = session_id
    resp = client.post("/api/chat", json=payload)
    if resp.status_code != 200:
        return {"_status": resp.status_code, "_body": resp.text[:300]}
    return resp.json()


def tools_in_trace(trace: list) -> list:
    out = []
    for e in trace or []:
        if e.get("action") == "tool_call" and isinstance(e.get("detail"), list):
            out.extend(e["detail"])
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    client = httpx.Client(base_url=args.base_url, timeout=300.0)

    # A1 健康检查
    resp = client.get("/api/health")
    ok = resp.status_code == 200 and resp.json().get("agent_ready") is True
    check("A1 GET /api/health", ok, resp.text[:300])

    # A2 问候（无工具）
    r = ask(client, "你好，请用一句话介绍你自己")
    ok = r.get("answer") and "session_id" in r and r.get("trace") is not None
    no_tool = not tools_in_trace(r.get("trace") or [])
    check("A2 问候问答(200, 有answer/trace)", bool(ok), str(r)[:300])
    check("A2b 问候未调用工具", no_tool, str(r.get("trace"))[:300])
    s1 = r.get("session_id")

    # A3 calculator + 连续对话（同会话追问）
    r = ask(client, "用计算器精确计算 (1234567 * 89 + 4321) / 56", session_id=s1)
    tools = tools_in_trace(r.get("trace") or [])
    check("A3 calculator 工具被调用", "calculator" in tools, f"tools={tools}")
    check("A3b 连续对话同 session_id 返回", r.get("session_id") == s1, str(r.get("session_id")))
    r = ask(client, "把上一步的结果四舍五入到整数是多少？只回答数字", session_id=s1)
    ok = r.get("answer") and ("1962157" in r["answer"] or "1,962,157" in r["answer"])
    check("A3c 多轮上下文延续(引用上一步结果)", bool(ok), str(r.get("answer"))[:300])

    # A4 knowledge_search + 引用
    r = ask(client, "公司的差旅报销制度里，报销申请需要在几个工作日内提交？")
    tools = tools_in_trace(r.get("trace") or [])
    check("A4 knowledge_search 工具被调用", "knowledge_search" in tools, f"tools={tools}")
    check(
        "A4b 回答包含知识库引用来源",
        bool(r.get("answer")) and "demo_company_policy.pdf" in r["answer"],
        str(r.get("answer"))[:200],
    )
    reflection = [e for e in (r.get("trace") or []) if e.get("node") == "reflection"]
    check("A4c trace 含 Reflection 节点", bool(reflection), str(r.get("trace"))[:300])

    # A5 上传 zenith PDF
    if not ZENITH_PDF.exists():
        check("A5 上传 zenith PDF", False, f"测试文件不存在: {ZENITH_PDF}")
    else:
        before = client.get("/api/documents").json()
        resp = client.post(
            "/api/documents/upload",
            files={"file": (ZENITH_NAME, ZENITH_PDF.read_bytes(), "application/pdf")},
        )
        ok = resp.status_code == 201 and resp.json().get("chunks", 0) >= 1
        check("A5 上传 zenith PDF(201, chunks>=1)", ok, resp.text[:300])
        after = client.get("/api/documents").json()
        check(
            "A5b 文档列表数量 +1",
            after.get("total") == before.get("total") + 1,
            f"before={before.get('total')} after={after.get('total')}",
        )

    # A6 新文档立即可检索
    r = ask(client, "Project Zenith 逃生舱的访问码是多少？")
    ok = r.get("answer") and "7391" in r["answer"]
    check("A6 上传后新会话可检索到访问码 7391", bool(ok), str(r.get("answer"))[:300])

    # A7 删除后 FAISS 同步
    resp = client.delete(f"/api/documents/{ZENITH_NAME}")
    ok = resp.status_code == 200 and resp.json().get("success") is True
    check("A7 删除 zenith PDF", ok, resp.text[:300])
    r = ask(client, "Project Zenith 逃生舱的访问码是多少？请只根据知识库回答")
    ok = r.get("answer") and "7391" not in r["answer"]
    check("A7b 删除后新会话检索不到 7391(FAISS 已同步)", bool(ok), str(r.get("answer"))[:300])

    # A8 全量重建
    resp = client.post("/api/documents/rebuild")
    ok = resp.status_code == 200 and isinstance(resp.json().get("chunks"), int)
    check("A8 知识库全量重建", ok, resp.text[:300])

    # A9 评测
    resp = client.post("/api/evaluation/run")
    ok = resp.status_code == 202 and resp.json().get("status") == "running"
    check("A9 POST /api/evaluation/run(202 running)", ok, resp.text[:300])
    resp2 = client.post("/api/evaluation/run")
    ok = (
        resp2.status_code == 409
        and resp2.json().get("detail", {}).get("code") == "EVALUATION_ALREADY_RUNNING"
    )
    check("A9b 运行中重复提交 -> 409", ok, resp2.text[:300])

    final = None
    for _ in range(60):  # 最长 150s
        time.sleep(2.5)
        j = client.get("/api/evaluation/results").json()
        if j.get("status") in ("completed", "failed"):
            final = j
            break
    ok = final and final.get("status") == "completed"
    check("A9c 评测轮询至 completed", bool(ok), str(final)[:200])
    if final and final.get("status") == "completed":
        s = final["summary"]
        check(
            "A9d 评测 summary 合法(total=4, 分数在[0,1])",
            s.get("total") == 4
            and 0.0 <= s.get("average_score", -1) <= 1.0
            and len(final.get("cases") or []) == 4,
            str(s),
        )
        scores_ok = all(0.0 <= (c.get("score") or 0) <= 1.0 for c in final["cases"])
        check("A9e 每用例得分在 [0,1] 且 answer 非空", scores_ok and all(c.get("answer") for c in final["cases"]), str(final["cases"])[:200])

    # A10 会话历史 + 删除
    resp = client.get(f"/api/sessions/{s1}/history")
    j = resp.json()
    assistants = [m for m in j.get("messages", []) if m.get("role") == "assistant"]
    ok = resp.status_code == 200 and len(assistants) >= 3 and any(m.get("trace") for m in assistants)
    check("A10 会话历史含多轮且 assistant 带 trace", ok, str(j)[:300])
    resp = client.delete(f"/api/sessions/{s1}")
    check("A10b 删除会话", resp.status_code in (200, 204), resp.text[:200])

    print(f"\n==== 最终验收: {passed} passed, {failed} failed ====")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
