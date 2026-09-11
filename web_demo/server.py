"""
FastAPI Server for Linus Enterprise SRE Console.
Provides real-time SSE telemetry streaming, GitHub webhook ingestion, and scenario auditing.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from linus.agent import LinusAgent
from linus.scenarios import ALL_SCENARIOS, SCENARIO_CHECKOUT_DISCOUNT
from linus.tools.patch_verifier import commit_permanent_test

app = FastAPI(title="Linus Enterprise SRE Console", version="0.1.0")

# Active audit telemetry streams {audit_id: asyncio.Queue}
ACTIVE_STREAMS: Dict[str, asyncio.Queue] = {}
AUDIT_RESULTS: Dict[str, Any] = {}
MAX_CACHED_AUDITS = 50

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def evict_old_cache():
    """Evicts oldest audit records to prevent memory leaks."""
    while len(AUDIT_RESULTS) > MAX_CACHED_AUDITS:
        oldest_key = next(iter(AUDIT_RESULTS))
        del AUDIT_RESULTS[oldest_key]
        if oldest_key in ACTIVE_STREAMS:
            del ACTIVE_STREAMS[oldest_key]


class AuditRequest(BaseModel):
    scenario_id: Optional[str] = "PR-104"
    custom_source: Optional[str] = None
    custom_test: Optional[str] = None
    custom_patch: Optional[str] = None
    custom_filename: Optional[str] = "service.py"


class CommitPatchRequest(BaseModel):
    audit_id: str
    apply_source_patch: bool = False


@app.get("/api/scenarios")
async def get_scenarios():
    """Returns all pre-loaded enterprise scenarios."""
    summary = {}
    for sid, data in ALL_SCENARIOS.items():
        summary[sid] = {
            "id": data["id"],
            "title": data["title"],
            "author": data["author"],
            "repository": data["repository"],
            "branch": data["branch"],
            "target_file": data["target_file"],
            "pr_description": data["pr_description"],
            "source_code": data["source_code"],
            "baseline_test_code": data["baseline_test_code"],
            "adversarial_test_code": data["adversarial_test_code"],
            "patched_code": data["patched_code"],
            "explanation": data["explanation"],
        }
    return summary


@app.post("/api/audit")
async def start_audit(req: AuditRequest, background_tasks: BackgroundTasks):
    """Starts an autonomous Linus audit and returns an audit_id for telemetry streaming."""
    evict_old_cache()
    audit_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()
    ACTIVE_STREAMS[audit_id] = queue

    # Prepare audit payload
    if req.scenario_id and req.scenario_id in ALL_SCENARIOS:
        sc = ALL_SCENARIOS[req.scenario_id]
        pr_id = sc["id"]
        repo = sc["repository"]
        source = sc["source_code"]
        filename = sc["target_file"]
        adv_test = sc["adversarial_test_code"]
        base_test = sc["baseline_test_code"]
        patch = sc["patched_code"]
        expl = sc["explanation"]
    else:
        pr_id = "PR-CUSTOM"
        repo = "custom/user-repo"
        source = req.custom_source or ""
        filename = req.custom_filename or "service.py"
        adv_test = req.custom_test if (req.custom_test and req.custom_test.strip()) else None
        base_test = None
        patch = req.custom_patch
        expl = "Custom user submitted patch"

    main_loop = asyncio.get_running_loop()

    def telemetry_callback(event: Dict[str, Any]):
        # Schedule message put into the async queue safely from worker thread
        try:
            main_loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception:
            pass

    def run_agent_job():
        agent = LinusAgent(telemetry_callback=telemetry_callback)
        result = agent.audit_pull_request(
            pr_id=pr_id,
            repository=repo,
            source_code=source,
            target_filename=filename,
            adversarial_test_code=adv_test,
            baseline_test_code=base_test,
            candidate_patch=patch,
            patch_explanation=expl,
        )
        AUDIT_RESULTS[audit_id] = result.model_dump()
        evict_old_cache()
        telemetry_callback({"phase": "TERMINATE", "message": "Audit completed.", "data": {"audit_id": audit_id}})

    background_tasks.add_task(run_agent_job)
    return {"audit_id": audit_id, "status": "QUEUED"}


@app.get("/api/download/test/{audit_id}")
async def download_regression_test(audit_id: str):
    """Downloads the verified regression test as a standalone .py file."""
    if audit_id in AUDIT_RESULTS:
        res = AUDIT_RESULTS[audit_id]
        if res.get("failing_test") and res["failing_test"].get("test_code"):
            test_content = res["failing_test"]["test_code"]
            pr_id = res.get("pr_id", "pr").replace("-", "_").lower()
            return Response(
                content=test_content,
                media_type="text/x-python",
                headers={"Content-Disposition": f"attachment; filename=test_linus_{pr_id}.py"},
            )
    return JSONResponse(status_code=404, content={"error": "Test not found for audit"})


@app.post("/api/patch/commit")
async def commit_patch_and_test(req: CommitPatchRequest):
    """
    Physically commits the permanent regression test to tests/regressions/
    and permanently immunizes the repository.
    """
    if req.audit_id not in AUDIT_RESULTS:
        return JSONResponse(status_code=404, content={"error": "Audit result not found."})

    audit_data = AUDIT_RESULTS[req.audit_id]
    dual_ver = audit_data.get("dual_verification")
    failing_test = audit_data.get("failing_test")

    if not failing_test or not failing_test.get("test_code"):
        return JSONResponse(status_code=400, content={"error": "No verified test code available to commit."})

    perm_path = dual_ver.get("permanent_test_path") if dual_ver else None
    if not perm_path:
        pr_id = audit_data.get("pr_id", "custom").replace("-", "_").lower()
        perm_path = f"tests/regressions/test_linus_pr_{pr_id}.py"

    workspace_root = BASE_DIR.parent
    written_path = commit_permanent_test(
        permanent_test_path=perm_path,
        test_code=failing_test["test_code"],
        base_dir=workspace_root,
    )

    return {
        "status": "COMMITTED",
        "permanent_test_path": str(perm_path),
        "written_file": str(written_path),
        "message": f"Permanent regression guard successfully written to {perm_path}.",
    }


@app.get("/api/audit/stream/{audit_id}")
async def stream_telemetry(audit_id: str):
    """Streams real-time AgentCore telemetry events via Server-Sent Events (SSE)."""
    if audit_id not in ACTIVE_STREAMS:
        if audit_id in AUDIT_RESULTS:
            async def replay_generator():
                for evt in AUDIT_RESULTS[audit_id].get("telemetry_trace", []):
                    yield f"data: {json.dumps(evt)}\n\n"
                yield f"data: {json.dumps({'phase': 'TERMINATE', 'message': 'Audit completed.'})}\n\n"
            return StreamingResponse(replay_generator(), media_type="text/event-stream")
        return JSONResponse(status_code=404, content={"error": "Audit stream not found"})

    queue = ACTIVE_STREAMS[audit_id]

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    break
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("phase") == "TERMINATE":
                    break
        finally:
            if audit_id in ACTIVE_STREAMS:
                del ACTIVE_STREAMS[audit_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/audit/result/{audit_id}")
async def get_audit_result(audit_id: str):
    """Retrieves final audit result for a completed run."""
    if audit_id in AUDIT_RESULTS:
        return AUDIT_RESULTS[audit_id]
    return JSONResponse(status_code=404, content={"error": "Audit result not ready"})


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Live GitHub Webhook receiver for pull_request events."""
    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    
    if action in ("opened", "synchronize", "reopened"):
        pr_number = pr.get("number", 1)
        repo_name = payload.get("repository", {}).get("full_name", "unknown/repo")
        # In live enterprise production, clones repo and runs audit
        return {"status": "INGESTED", "pr": pr_number, "repo": repo_name}
        
    return {"status": "IGNORED", "reason": f"Action {action} does not require verification."}


# Mount static files and index
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>Linus Enterprise SRE Console</h1><p>Static files loading...</p>"
