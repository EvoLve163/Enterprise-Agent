# -*- coding: utf-8 -*-
"""阶段六异常测试（环境故障注入：临时起 8001 端口后端实例，注入错误环境变量）。

用真实子进程 + 真实 HTTP 请求验证:
  case invalid_llm_key : LLM_API_KEY=sk-invalid-xxx  -> chat 5xx, AGENT 上游失败
  case missing_llm_key : LLM_API_KEY=""              -> health llm_configured=false, chat 5xx
  case llm_timeout     : LLM_TIMEOUT=1               -> chat 5xx(超时被包装)
  case invalid_serp    : SERPAPI_API_KEY=garbage     -> web_search 工具内部失败但 chat 正常返回

用法: .venv/Scripts/python.exe Test/env_failure_test.py
"""
import os
import socket
import subprocess
import sys
import time

import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8001
BASE = f"http://127.0.0.1:{PORT}"

PASSED = 0
FAILED = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"[PASS] {name}")
    else:
        FAILED += 1
        print(f"[FAIL] {name}" + (f" | {detail}" if detail else ""))


def wait_health(client: httpx.Client, timeout_s: float = 120.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if client.get("/api/health", timeout=5.0).status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.5)
    return False


def start_backend(env_overrides: dict) -> subprocess.Popen:
    env = {**os.environ, **env_overrides}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def stop_backend(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    time.sleep(2)


def run_case(name: str, env_overrides: dict, checks) -> None:
    print(f"\n===== case: {name} | env={env_overrides} =====")
    proc = start_backend(env_overrides)
    client = httpx.Client(base_url=BASE, timeout=180.0, trust_env=False)  # 直连本机, 绕过系统代理
    try:
        if not wait_health(client):
            print(f"[FAIL] {name}: 实例 {PORT} 未在限时内就绪")
            globals()["FAILED"] += 1
            return
        print(f"      实例就绪 (pid={proc.pid})")
        checks(client)
    finally:
        client.close()
        stop_backend(proc)
        print(f"      实例已停止 (pid={proc.pid})")


def case_invalid_llm_key(client: httpx.Client) -> None:
    h = client.get("/api/health").json()
    check("K1a health 返回 llm_configured=true(非空即真, 已知展示局限)", h.get("llm_configured") is True, str(h))
    r = client.post("/api/chat", json={"question": "你好"})
    check("K1b 无效LLM Key -> 5xx 而非崩溃", r.status_code >= 500, f"HTTP {r.status_code}")
    body = r.json()
    code = body.get("detail", {}).get("code", "")
    check("K1c 错误码为 AGENT_RUN_FAILED/INTERNAL_ERROR", code in ("AGENT_RUN_FAILED", "INTERNAL_ERROR"), str(body)[:300])


def case_missing_llm_key(client: httpx.Client) -> None:  # pragma: no cover - 已由 run_exit_case 取代
    raise NotImplementedError


def case_llm_timeout(client: httpx.Client) -> None:
    r = client.post("/api/chat", json={"question": "你好，请介绍一下你自己"})
    check("K3a LLM_TIMEOUT=1s -> chat 5xx(超时被包装, 不悬挂)", r.status_code >= 500, f"HTTP {r.status_code}")
    check("K3b 响应体为统一错误结构", "detail" in r.json(), r.text[:200])


def case_invalid_serp(client: httpx.Client) -> None:
    r = client.post("/api/chat", json={"question": "请用 web_search 搜索 OpenAI 最近的新闻，并给出来源链接。"})
    ok = r.status_code == 200
    check("K4a 无效SerpAPI Key -> chat 仍 200(工具失败不击穿)", ok, f"HTTP {r.status_code}: {r.text[:200]}")
    if ok:
        data = r.json()
        tools = [t for step in data["trace"] for t in (step.get("detail") or []) if isinstance(step.get("detail"), list)]
        check("K4b trace 显示调用了 web_search", "web_search" in tools, str(tools))
        check("K4c Agent 如实说明搜索失败/无法给出链接(不编造)",
              any(k in data["answer"] for k in ("无法", "失败", "不能", "没有", "无法确认", "暂时")),
              data["answer"][:200])
        print(f"      (K4 回答节选: {data['answer'][:150]!r})")


def port_free(port: int) -> bool:
    """用原始 socket 判定端口空闲(不走 HTTP, 避免系统代理伪造 502 响应)。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) != 0


def run_exit_case(name: str, env_overrides: dict, expect_msg: str, timeout_s: float = 90.0) -> None:
    """期望后端 fail-fast 快速退出的用例（缺 LLM_API_KEY 时 core/llm.py:7-8 在启动期抛错）。"""
    print(f"\n===== case: {name} | env={env_overrides} (预期 fail-fast) =====")
    err_path = os.path.join(PROJECT_ROOT, "Test", "_env_failure_stderr.log")
    env = {**os.environ, **env_overrides}
    with open(err_path, "w", encoding="utf-8", errors="replace") as errf:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=PROJECT_ROOT, env=env, stdout=errf, stderr=errf,
        )
        deadline = time.time() + timeout_s
        exited = False
        while time.time() < deadline:
            if proc.poll() is not None:
                exited = True
                break
            time.sleep(1.0)
        if not exited:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
            globals()["FAILED"] += 1
            print(f"[FAIL] {name}: 实例未在 {timeout_s:.0f}s 内退出(预期 fail-fast)")
            return
    content = open(err_path, encoding="utf-8", errors="replace").read()
    check(f"K2a 缺失LLM Key -> 后端 fail-fast 拒绝启动(退出码 {proc.returncode})", exited)
    check("K2b 启动错误信息明确指出缺少 LLM_API_KEY", expect_msg in content, content[-400:])


def main() -> None:
    # 确认 8001 未被占用
    if not port_free(PORT):
        print(f"端口 {PORT} 已被占用，请先释放")
        sys.exit(2)

    run_case("invalid_llm_key", {"LLM_API_KEY": "sk-invalid-for-phase6-test"}, case_invalid_llm_key)
    run_exit_case("missing_llm_key", {"LLM_API_KEY": ""}, "缺少 LLM_API_KEY")
    run_case("llm_timeout_1s", {"LLM_TIMEOUT": "1"}, case_llm_timeout)
    run_case("invalid_serp_key", {"SERPAPI_API_KEY": "garbage-key-for-phase6-test"}, case_invalid_serp)

    print(f"\n==== 环境故障注入测试: {PASSED} passed, {FAILED} failed ====")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
