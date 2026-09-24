"""
Regression Test Suite for all 12 issues documented in live_adversarial_browser_report.md.
Verifies backend logic, boundary synthesis on typed functions, empty/syntax error handling,
unified diff newline formatting, SSE TERMINATE timestamps, path normalization, and frontend DOM invariants.
"""

import json
import pytest
from fastapi.testclient import TestClient

from linus.agent import LinusAgent
from linus.tools.ast_inspector import inspect_source_ast
from linus.tools.boundary_synthesizer import BoundarySynthesizer
from linus.tools.patch_verifier import DualRegressionVerifier
from web_demo.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Issue #7: Strictly Typed Clean Functions & Empty Source Code Handling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("clean_code", [
    "def add(a: int, b: int) -> int:\n    return a + b\n",
    "def multiply(x: float, y: float) -> float:\n    return x * y\n",
    "def greet(name: str) -> str:\n    return 'Hello ' + name\n",
    "def greet_user(user: str) -> str:\n    return 'Hello ' + user\n",
    "def count_items(items: list[str]) -> int:\n    return len(items)\n",
    "def check_data(data: dict) -> int:\n    return len(data)\n",
    "def normalize_name(name: str) -> str:\n    return name.strip().lower()\n",
    "def combine(a, b):\n    return a + b\n",
])
def test_issue_7_clean_typed_function_zero_false_positive(clean_code):
    """Verify clean functions with zero AST risk vectors are never falsely flagged by passing None."""
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id="PR-TYPED-CLEAN",
        repository="custom/user-repo",
        source_code=clean_code,
        target_filename="math_utils.py",
    )
    assert res.status == "VERIFIED_CLEAN"
    assert res.defect_proven is False


@pytest.mark.parametrize("empty_input", ["", "   ", "\n\t\n"])
def test_issue_7_empty_input_returns_inconclusive_not_clean(empty_input):
    """Verify empty or whitespace-only custom input returns INCONCLUSIVE rather than AMBIENT SILENCE."""
    res = client.post(
        "/api/audit",
        json={"scenario_id": "PR-CUSTOM", "custom_source": empty_input, "custom_filename": "empty.py"},
    )
    assert res.status_code == 200
    data = res.json()["result"]
    assert data["status"] == "INCONCLUSIVE"
    assert data["defect_proven"] is False
    assert data["failing_test"]["exception_type"] == "EmptySourceError"


# ---------------------------------------------------------------------------
# Issue #6: Syntax Error Audits Return INCONCLUSIVE & Null Patch
# ---------------------------------------------------------------------------

def test_issue_6_syntax_error_returns_inconclusive_with_syntax_error_details():
    """Verify malformed syntax returns INCONCLUSIVE, defect_proven=False, patch=None, and SyntaxError details."""
    res = client.post(
        "/api/audit",
        json={"scenario_id": "PR-CUSTOM", "custom_source": "def broken(:\n    pass", "custom_filename": "broken.py"},
    )
    assert res.status_code == 200
    data = res.json()["result"]
    assert data["status"] == "INCONCLUSIVE"
    assert data["defect_proven"] is False
    assert data["patch"] is None
    assert data["failing_test"]["exception_type"] == "SyntaxError"


# ---------------------------------------------------------------------------
# Issue #8: Unified Diff Line Concatenation When Source Lacks Trailing Newline
# ---------------------------------------------------------------------------

def test_issue_8_unified_diff_preserves_newlines_without_trailing_newline():
    """Verify generate_unified_diff never concatenates + lines onto - lines when original lacks trailing newline."""
    verifier = DualRegressionVerifier()
    original_no_newline = "def calc_margin(revenue, profit):\n    return (profit / revenue) * 100"
    patched_with_newline = (
        "def calc_margin(revenue, profit):\n"
        "    if revenue == 0:\n"
        "        return 0.0\n"
        "    return (profit / revenue) * 100\n"
    )
    diff_text = verifier.generate_unified_diff(original_no_newline, patched_with_newline, filename="margin.py")
    # Ensure no removed line has a `+` line concatenated onto its end
    for line in diff_text.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            assert "+    " not in line, f"Corrupted concatenated diff line: {line!r}"


# ---------------------------------------------------------------------------
# Issue #3: SSE TERMINATE Timestamp & Normalized Regression Filename
# ---------------------------------------------------------------------------

def test_issue_3_sse_terminate_event_includes_valid_timestamp_and_normalized_commit_path():
    """Verify SSE stream, audit result, download header, and commit path all normalize pr_PR- and include HH:MM:SS timestamps."""
    res = client.post("/api/audit", json={"scenario_id": "PR-104"})
    assert res.status_code == 200
    body = res.json()
    audit_id = body["audit_id"]
    assert body["result"]["dual_verification"]["permanent_test_path"] == "tests/regressions/test_linus_pr_104.py"

    res_get = client.get(f"/api/audit/result/{audit_id}")
    assert res_get.status_code == 200
    assert res_get.json()["dual_verification"]["permanent_test_path"] == "tests/regressions/test_linus_pr_104.py"

    dl_res = client.get(f"/api/download/test/{audit_id}")
    assert dl_res.status_code == 200
    assert "filename=test_linus_pr_104.py" in dl_res.headers.get("content-disposition", "")

    stream_res = client.get(f"/api/audit/stream/{audit_id}")
    assert stream_res.status_code == 200
    events = [
        json.loads(line[len("data: "):])
        for line in stream_res.text.splitlines()
        if line.startswith("data: ")
    ]
    for ev in events:
        assert "pr_PR-" not in json.dumps(ev)
    terminate_evts = [e for e in events if e.get("phase") == "TERMINATE"]
    assert len(terminate_evts) >= 1
    for te in terminate_evts:
        assert te.get("timestamp") is not None
        assert te.get("timestamp") != "now"
        assert ":" in te["timestamp"]

    commit_res = client.post("/api/patch/commit", json={"audit_id": audit_id})
    assert commit_res.status_code == 200
    commit_data = commit_res.json()
    assert "pr_PR-" not in commit_data["permanent_test_path"]
    assert "test_linus_pr_104.py" in commit_data["permanent_test_path"]

    from pathlib import Path
    created_file = Path(commit_data["written_file"])
    if created_file.exists() and "tests" in str(created_file):
        created_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Issues #1, #2, #4, #5, #6, #9, #10, #11, #12: Frontend HTML & JS Invariants
# ---------------------------------------------------------------------------

def test_frontend_html_contains_all_12_ergonomic_and_security_fixes():
    """Verify web_demo/static/index.html implements all DOM, state, race-condition, and responsive fixes."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Issue #1: selectScenario resets #pr-status-badge and #telemetry-status
    assert "Unit Tests Passing (2/2)" in html
    assert "Ready for Custom Code" in html

    # Issue #2: Compact above-the-fold Panel 3 and scroll reset on scenario switch
    assert "window.scrollTo({ top: 0, behavior: 'instant' })" in html
    assert "max-h-20" in html

    # Issue #3: normalizeRegressionPath helper eliminates pr_PR- mismatch
    assert "function normalizeRegressionPath(" in html

    # Issue #4: No blocking window.alert() in copyGithubMarkdown
    assert "alert(" not in html
    assert "Copied to Clipboard!" in html

    # Issue #5: applyVerifiedPatch uses manualPatch || synthPatch and never wipes source code with ""
    assert "const effectivePatch = manualPatch || synthPatch;" in html

    # Issue #6: Dedicated #card-inconclusive-state container and resetSurfaceCardFields()
    assert 'id="card-inconclusive-state"' in html
    assert "function resetSurfaceCardFields()" in html
    assert "INCONCLUSIVE • NO DEFECT" in html

    # Issue #9: Custom filename input in Custom PR Playground
    assert 'id="custom-filename-input"' in html

    # Issue #10: Mid-audit scenario switch race condition protection via activeAuditToken & AbortController
    assert "let activeAuditToken = 0;" in html
    assert "activeAbortController" in html
    assert "scenarioIdAtStart" in html

    # Issue #11: Safe textContent DOM creation in appendTelemetryLog instead of unescaped innerHTML
    assert "tsSpan.textContent =" in html
    assert "phaseSpan.textContent =" in html
    assert "msgSpan.textContent =" in html

    # Issue #12: Responsive col-span-12 lg:col-span-4 grid, whitespace-nowrap pills, and fixed Python 3.12+ label
    assert html.count("col-span-12 lg:col-span-4") == 3
    assert "Python 3.12+ +" not in html
    assert "Engine: Python 3.12+ &bull; Bedrock Claude 3.7" in html


# ---------------------------------------------------------------------------
# Live Headless Chrome CDP Verification across Viewports & Archetype Flows
# ---------------------------------------------------------------------------

def test_headless_chrome_live_viewports_and_interactive_flows():
    """
    Launches a live uvicorn server and Headless Chrome via CDP to verify:
    1. Above-the-fold CTA button visibility at 1920x1080 and 1280x800 (Issue #2)
    2. Scenario switch badge/status reset from PR-104 -> PR-209 (Issue #1)
    3. Custom Playground Approve Patch with blank candidate patch box preserves/updates source code (Issue #5)
    4. Custom Playground SyntaxError renders INCONCLUSIVE • NO DEFECT and hides DEFECT PROVEN (Issue #6)
    5. Tablet (768x1024) and Mobile (390x844) single-column responsive stacking (Issue #12)
    """
    import asyncio
    import socket
    import subprocess
    import tempfile
    import threading
    import time
    import urllib.request
    from pathlib import Path
    import shutil
    import uvicorn

    chrome_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    for linux_bin in ("google-chrome", "chromium-browser", "chromium"):
        found = shutil.which(linux_bin)
        if found:
            chrome_candidates.append(Path(found))
    browser_bin = next((p for p in chrome_candidates if p.exists()), None)
    if not browser_bin:
        pytest.skip("No local Chrome/Edge binary found for headless CDP test")

    websockets = pytest.importorskip("websockets")

    def get_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    app_port = get_free_port()
    cdp_port = get_free_port()

    config = uvicorn.Config(app, host="127.0.0.1", port=app_port, log_level="error")
    server = uvicorn.Server(config)
    srv_thread = threading.Thread(target=server.run, daemon=True)
    srv_thread.start()

    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{app_port}/api/scenarios", timeout=1) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.1)

    with tempfile.TemporaryDirectory() as user_data_dir:
        proc = subprocess.Popen(
            [
                str(browser_bin),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                f"--remote-debugging-port={cdp_port}",
                f"--user-data-dir={user_data_dir}",
                f"http://127.0.0.1:{app_port}/",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            ws_url = None
            for _ in range(80):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json", timeout=1) as r:
                        targets = json.loads(r.read().decode())
                        page_targets = [
                            t for t in targets
                            if t.get("type") == "page" and str(app_port) in t.get("url", "")
                        ]
                        if page_targets:
                            ws_url = page_targets[0]["webSocketDebuggerUrl"]
                            break
                except Exception:
                    time.sleep(0.1)
            assert ws_url is not None, "Failed to connect to Headless Chrome CDP target"

            async def run_cdp_checks():
                async with websockets.connect(ws_url, max_size=10_000_000) as ws:
                    msg_id = 0

                    async def cdp_call(method: str, params: dict | None = None):
                        nonlocal msg_id
                        msg_id += 1
                        await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
                        while True:
                            raw = await ws.recv()
                            resp = json.loads(raw)
                            if resp.get("id") == msg_id:
                                return resp.get("result", {})

                    async def eval_js(expr: str):
                        res = await cdp_call(
                            "Runtime.evaluate",
                            {"expression": expr, "returnByValue": True, "awaitPromise": True},
                        )
                        return res.get("result", {}).get("value")

                    # Wait for scenarios to load
                    loaded = False
                    for i in range(150):
                        loaded = await eval_js("Boolean(typeof currentScenario !== 'undefined' && currentScenario && currentScenario.id === 'PR-104')")
                        if loaded:
                            break
                        if i == 30:
                            await eval_js("if (typeof loadScenarios === 'function' && !currentScenario) loadScenarios();")
                        await asyncio.sleep(0.1)
                    assert loaded is True

                    # 1. Test 1920x1080 & 1280x800 above-the-fold layout on PR-104 Defect Proven
                    for width, height in [(1920, 1080), (1280, 800)]:
                        await cdp_call(
                            "Emulation.setDeviceMetricsOverride",
                            {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False},
                        )
                        await eval_js("selectScenario('PR-104'); triggerAudit();")
                        for _ in range(80):
                            badge = await eval_js("document.getElementById('card-status-badge').innerText")
                            if badge == "DEFECT PROVEN":
                                break
                            await asyncio.sleep(0.1)
                        assert badge == "DEFECT PROVEN"

                        metrics = await eval_js("""(() => {
                            const applyRect = document.getElementById('btn-apply-patch').getBoundingClientRect();
                            const copyRect = document.getElementById('btn-copy-markdown').getBoundingClientRect();
                            const dlRect = document.getElementById('btn-download-test').getBoundingClientRect();
                            return {
                                innerHeight: window.innerHeight,
                                scrollY: window.scrollY,
                                applyBottom: applyRect.bottom,
                                copyBottom: copyRect.bottom,
                                dlBottom: dlRect.bottom
                            };
                        })()""")
                        assert metrics["scrollY"] == 0
                        assert metrics["applyBottom"] <= metrics["innerHeight"], f"Clipped at {width}x{height}: {metrics}"
                        assert metrics["copyBottom"] <= metrics["innerHeight"], f"Clipped at {width}x{height}: {metrics}"
                        assert metrics["dlBottom"] <= metrics["innerHeight"], f"Clipped at {width}x{height}: {metrics}"

                    # 2. Approve patch on PR-104, then switch to PR-209 and verify status reset (Issue #1)
                    await eval_js("applyVerifiedPatch()")
                    immune_badge = await eval_js("document.getElementById('pr-status-badge').innerText.trim()")
                    assert "Immune & Clean" in immune_badge

                    await eval_js("selectScenario('PR-209')")
                    reset_state = await eval_js("""({
                        prBadge: document.getElementById('pr-status-badge').innerText.trim(),
                        telemetryStatus: document.getElementById('telemetry-status').innerText.trim(),
                        scrollY: window.scrollY
                    })""")
                    assert "Unit Tests Passing (2/2)" in reset_state["prBadge"]
                    assert reset_state["telemetryStatus"] == "Idle"
                    assert reset_state["scrollY"] == 0

                    # 3. Custom Playground: blank patch input + Approve Patch applies synthesized patch (Issue #5)
                    await eval_js("""(() => {
                        selectScenario('CUSTOM');
                        document.getElementById('custom-source-input').value = 'def calc_ratio(a, b):\\n    return a / b';
                        document.getElementById('custom-patch-input').value = '';
                        triggerAudit();
                    })()""")
                    for _ in range(80):
                        badge = await eval_js("document.getElementById('card-status-badge').innerText")
                        if badge == "DEFECT PROVEN":
                            break
                        await asyncio.sleep(0.1)
                    assert badge == "DEFECT PROVEN"

                    await eval_js("applyVerifiedPatch()")
                    updated_src = await eval_js("document.getElementById('custom-source-input').value")
                    assert updated_src.strip() != "", "Custom source input was wiped out!"
                    assert "return a / b" in updated_src

                    # 4. Custom Playground: SyntaxError displays INCONCLUSIVE • NO DEFECT and hides DEFECT PROVEN (Issue #6)
                    await eval_js("""(() => {
                        selectScenario('CUSTOM');
                        document.getElementById('custom-source-input').value = 'def broken(:\\n    pass';
                        triggerAudit();
                    })()""")
                    for _ in range(80):
                        badge = await eval_js("document.getElementById('card-status-badge').innerText")
                        if "INCONCLUSIVE" in badge:
                            break
                        await asyncio.sleep(0.1)
                    inconc_state = await eval_js("""({
                        badge: document.getElementById('card-status-badge').innerText.trim(),
                        inconcHidden: document.getElementById('card-inconclusive-state').classList.contains('hidden'),
                        defectHidden: document.getElementById('card-proven-defect').classList.contains('hidden'),
                        diffText: document.getElementById('card-patch-diff').textContent
                    })""")
                    assert inconc_state["badge"] == "INCONCLUSIVE • NO DEFECT"
                    assert inconc_state["inconcHidden"] is False
                    assert inconc_state["defectHidden"] is True
                    assert inconc_state["diffText"] == "# No patch diff available"

                    # 5. Responsive Tablet (768x1024) and Mobile (390x844) single-column stacking (Issue #12)
                    for width, height in [(768, 1024), (390, 844)]:
                        await cdp_call(
                            "Emulation.setDeviceMetricsOverride",
                            {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": True},
                        )
                        await asyncio.sleep(0.1)
                        layout = await eval_js("""(() => {
                            const sections = Array.from(document.querySelectorAll('main > section'));
                            const r0 = sections[0].getBoundingClientRect();
                            const r1 = sections[1].getBoundingClientRect();
                            return { w0: r0.width, b0: r0.bottom, t1: r1.top };
                        })()""")
                        assert layout["w0"] > width * 0.85, f"Panel 1 too narrow ({layout['w0']}px) at {width}x{height}"
                        assert layout["t1"] >= layout["b0"], f"Panels did not stack vertically at {width}x{height}: {layout}"

            asyncio.run(run_cdp_checks())
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
            server.should_exit = True
            for fname in ("test_linus_pr_104.py", "test_linus_pr_custom.py"):
                p = Path(__file__).resolve().parent / "regressions" / fname
                p.unlink(missing_ok=True)


