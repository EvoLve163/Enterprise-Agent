"""评测服务：安全地封装现有 evaluation/evaluator.py 的评测逻辑。

设计要点：
- 复用现有函数：evaluation.evaluator.load_cases()（读取
  evaluation/test_cases.json）与 evaluate_answer()（关键词命中率评分），
  本文件不重新实现评分规则；
- 复用组合根已构建的 EnterpriseAgent 单例（与聊天接口共享），不调用
  evaluator.build_agent()——那会再加载一份 Embedding 模型与 FAISS 索引；
- 与 evaluator.run()（CLI 打印版）的差异：每个用例使用独立的
  thread_id（eval-<run_id>-<序号>），避免用例之间经 MemorySaver
  检查点互相污染上下文；run() 对所有用例共用 "default" 线程；
- 评测在后台线程执行，start_run() 立即返回；重复提交返回 409；
- 任何异常都被捕获并记入状态（status=failed + error），不会静默成功；
- 结果只来自实际执行——服务启动时没有"最近结果"，直到真正跑完一次。
"""

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from agent.graph import EnterpriseAgent

from backend.errors import ConflictError
from evaluation.evaluator import evaluate_answer, load_cases

logger = logging.getLogger(__name__)


class EvaluationService:
    """串行执行的评测任务管理器（进程内单例）。"""

    def __init__(self, agent: EnterpriseAgent) -> None:
        self._agent = agent
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "status": "idle",  # idle | running | completed | failed
            "started_at": None,
            "finished_at": None,
            "error": None,
            "summary": None,
            "cases": None,
        }

    # ---------------- 对外 ----------------

    def start_run(self) -> dict:
        """启动一次评测（后台线程）。已有多评测在跑时抛 409。"""
        with self._lock:
            if self._state["status"] == "running":
                raise ConflictError(
                    code="EVALUATION_ALREADY_RUNNING",
                    message="评测正在执行中，请等待完成后再提交",
                )
            # 先加载用例，让调用方立刻知道用例数；加载失败直接抛错
            cases = load_cases()
            self._state = {
                "status": "running",
                "started_at": datetime.now(),
                "finished_at": None,
                "error": None,
                "summary": {"total": len(cases)},
                "cases": None,
            }

        worker = threading.Thread(
            target=self._run_cases, args=(cases,), name="evaluation-worker", daemon=True
        )
        worker.start()
        return {"status": "running", "total_cases": len(cases)}

    def get_results(self) -> dict:
        """返回最近一次评测的状态与结果（尚未执行过时 status=idle）。"""
        with self._lock:
            return dict(self._state)

    # ---------------- 内部 ----------------

    def _run_cases(self, cases: list[dict]) -> None:
        run_id = uuid.uuid4().hex[:8]
        results: list[dict] = []
        total_score = 0.0
        failed = False
        error_message: Optional[str] = None

        try:
            for index, case in enumerate(cases):
                case_result = self._run_single_case(case, run_id, index)
                results.append(case_result)
                if case_result["error"] is None:
                    total_score += case_result["score"]
        except Exception as exc:  # 单用例失败已就地记录，这里是整体异常兜底
            failed = True
            error_message = f"评测执行异常：{exc}"
            logger.exception("评测任务整体异常（run=%s）", run_id)

        with self._lock:
            executed = len(results)
            self._state["finished_at"] = datetime.now()
            if failed and executed == 0:
                self._state["status"] = "failed"
                self._state["error"] = error_message
                return
            # 至少跑完部分用例：给出基于实际执行结果的汇总
            self._state["status"] = "completed" if not failed else "failed"
            self._state["error"] = error_message
            self._state["cases"] = results
            self._state["summary"] = {
                "total": len(cases),
                "executed": executed,
                "average_score": (
                    round(total_score / executed, 4) if executed else 0.0
                ),
                "full_score_count": sum(
                    1 for r in results if r["error"] is None and r["score"] == 1.0
                ),
                "case_failed_count": sum(1 for r in results if r["error"] is not None),
            }

    def _run_single_case(self, case: dict, run_id: str, index: int) -> dict:
        question = case["question"]
        keywords = case.get("expected_keywords", [])
        started = time.perf_counter()
        try:
            # 每个用例独立 thread：用例间上下文互不影响
            answer, _trace = self._agent.ask(
                question, thread_id=f"eval-{run_id}-{index}"
            )
            answer = str(answer)
            score = evaluate_answer(answer, keywords)
            matched = [w for w in keywords if w in answer]
            missed = [w for w in keywords if w not in answer]
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "评测用例 #%s 完成：score=%s elapsed=%sms",
                index + 1, score, elapsed_ms,
            )
            return {
                "index": index,
                "question": question,
                "type": case.get("type", ""),
                "answer": answer,
                "expected_keywords": keywords,
                "matched_keywords": matched,
                "missed_keywords": missed,
                "score": score,
                "elapsed_ms": elapsed_ms,
                "error": None,
            }
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception("评测用例执行失败（run=%s index=%s）", run_id, index)
            return {
                "index": index,
                "question": question,
                "type": case.get("type", ""),
                "answer": "",
                "expected_keywords": keywords,
                "matched_keywords": [],
                "missed_keywords": list(keywords),
                "score": 0.0,
                "elapsed_ms": elapsed_ms,
                "error": f"用例执行失败：{exc}",
            }
