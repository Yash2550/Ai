"""
Lightweight CPU-friendly Background Job Queue for Heavy Label Reconstruction.
Supports job IDs, real progress steps, cancellation, SHA-256 caching, and temp cleanup.
"""

import time
import uuid
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="gomzi_recon")
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_RESULT_CACHE: dict[str, dict] = {}


def submit_reconstruction_job(file_bytes: bytes, filename: str, use_vision: bool = True, runner_fn=None) -> str:
    """Submits a label reconstruction task to background queue and returns job_id."""
    job_id = f"recon_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    cache_key = hashlib.sha256(file_bytes).hexdigest() + f"_v{int(use_vision)}"

    with _JOBS_LOCK:
        if len(_JOBS) > 40:
            # Prune oldest completed jobs
            old_ids = [k for k, v in _JOBS.items() if v.get("status") in ("completed", "failed", "cancelled")][:20]
            for oid in old_ids:
                _JOBS.pop(oid, None)

        _JOBS[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "progress": 5,
            "stage": "Queued for validation & layout analysis",
            "cancelled": False,
            "result": None,
            "error": None,
            "started_at": time.time(),
            "elapsed_ms": 0,
        }

    def _task():
        t0 = time.time()
        try:
            if cache_key in _RESULT_CACHE:
                cached = dict(_RESULT_CACHE[cache_key])
                with _JOBS_LOCK:
                    _JOBS[job_id].update({
                        "status": "completed",
                        "progress": 100,
                        "stage": "Loaded cached reconstruction",
                        "result": cached,
                        "elapsed_ms": int((time.time() - t0) * 1000),
                    })
                return

            def _progress_cb(pct: int, msg: str):
                with _JOBS_LOCK:
                    if _JOBS[job_id]["cancelled"]:
                        raise RuntimeError("Job cancelled by user")
                    _JOBS[job_id]["status"] = "processing"
                    _JOBS[job_id]["progress"] = int(pct)
                    _JOBS[job_id]["stage"] = msg

            _progress_cb(15, "Validating file structure & preserving original...")
            res = runner_fn(file_bytes, filename, use_vision=use_vision, progress_cb=_progress_cb)
            elapsed = int((time.time() - t0) * 1000)
            res["elapsed_ms"] = elapsed
            _RESULT_CACHE[cache_key] = res
            with _JOBS_LOCK:
                if not _JOBS[job_id]["cancelled"]:
                    _JOBS[job_id].update({
                        "status": "completed",
                        "progress": 100,
                        "stage": "Reconstruction ready",
                        "result": res,
                        "elapsed_ms": elapsed,
                    })
        except Exception as exc:
            with _JOBS_LOCK:
                _JOBS[job_id].update({
                    "status": "cancelled" if _JOBS[job_id]["cancelled"] else "failed",
                    "error": str(exc),
                    "stage": "Stopped",
                    "elapsed_ms": int((time.time() - t0) * 1000),
                })

    _EXECUTOR.submit(_task)
    return job_id


def get_job_status(job_id: str) -> dict | None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return None
        return dict(job)


def cancel_job(job_id: str) -> bool:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return False
        job["cancelled"] = True
        if job["status"] == "queued":
            job["status"] = "cancelled"
        return True
