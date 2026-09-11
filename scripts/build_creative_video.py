"""
Creative, High-Engagement Demo Video Generator for Linus Hackathon Pitch.

Renders 7 custom-designed 720p HTML scenes (Tailwind CSS, dark mode, high visual polish)
via Microsoft Edge headless, synthesizes punchy narrative audio via edge-tts,
and compiles the final linus_demo_pitch.mp4 with ffmpeg.
"""
import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path

# Paths
ASSETS_DIR = Path("demo_video_assets")
FINAL_VIDEO = Path("linus_demo_pitch.mp4")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
VOICE = "en-US-ChristopherNeural"

SCENES = [
    {
        "id": "scene_01_the_crisis",
        "title": "The Verification Crisis",
        "html_file": "scene_01_the_crisis.html",
        "script": (
            "It's 4:45 PM on a Friday. A pull request lands in your repo. "
            "All unit tests are green. The linter reports zero warnings. Traditional AI bots posted eight pointless comments about variable names. "
            "You click merge. Thirty minutes later, production drops dead. "
            "In 2026, AI coding velocity is up three hundred percent, but code churn and rollbacks are up forty percent. "
            "Why? Because code is cheap, but verification is expensive. "
            "What if an AI reviewer spoke only when it could empirically prove a crash in production?"
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="absolute -top-32 -left-32 w-96 h-96 bg-red-500/15 rounded-full blur-3xl pointer-events-none"></div>
  <div class="absolute -bottom-32 -right-32 w-96 h-96 bg-cyan-500/15 rounded-full blur-3xl pointer-events-none"></div>

  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div>
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">AWS AGENTS FOR HUMANS • TRACK 2</span>
    </div>
    <div class="mono text-xs px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
      THE 2026 VERIFICATION CRISIS
    </div>
  </div>

  <div class="grid grid-cols-2 gap-8 my-auto relative z-10">
    <div class="bg-slate-900/90 border border-emerald-500/40 rounded-2xl p-6 flex flex-col justify-between shadow-2xl relative overflow-hidden">
      <div class="absolute top-0 left-0 w-full h-1 bg-emerald-500"></div>
      <div>
        <div class="flex items-center justify-between mb-4">
          <span class="mono text-xs text-emerald-400 font-semibold uppercase tracking-wider">GitHub Actions • 4:45 PM</span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ALL CHECKS PASSED
          </span>
        </div>
        <h3 class="text-xl font-bold text-white mb-2">PR-104: Tiered Discounts</h3>
        <p class="text-sm text-slate-300 mb-4 leading-relaxed">
          Developer added checkout loyalty promo logic. Unit tests passed 100%. Linter reported zero style warnings. Traditional AI bots posted 8 comments on variable names.
        </p>
      </div>
      <div class="bg-slate-950 rounded-xl p-3 border border-slate-800 mono text-xs text-emerald-400 flex items-center justify-between">
        <span>✓ pytest: 4 passed in 0.42s</span>
        <span class="text-slate-400">False Sense of Security</span>
      </div>
    </div>

    <div class="bg-slate-900/90 border border-red-500/50 rounded-2xl p-6 flex flex-col justify-between shadow-2xl relative overflow-hidden">
      <div class="absolute top-0 left-0 w-full h-1 bg-red-500"></div>
      <div>
        <div class="flex items-center justify-between mb-4">
          <span class="mono text-xs text-red-400 font-semibold uppercase tracking-wider">PagerDuty Alert • 5:15 PM</span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/40 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping"></span> P1 OUTAGE TRIGGERED
          </span>
        </div>
        <h3 class="text-xl font-bold text-red-400 mb-2">500 Internal Server Error</h3>
        <p class="text-sm text-slate-300 mb-4 leading-relaxed">
          Checkout service collapsed on empty cart guest sessions. Unhandled <span class="mono text-red-400 font-bold">IndexError: list index out of range</span>.
          Cost: $84,000 in lost transactions and an emergency Friday rollback.
        </p>
      </div>
      <div class="bg-slate-950 rounded-xl p-3 border border-red-900/50 mono text-xs text-red-400">
        Fatal: items[0] accessed when cart.items was empty!
      </div>
    </div>
  </div>

  <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center justify-between relative z-10">
    <div>
      <span class="text-xs mono uppercase text-slate-400 tracking-wider">DORA & GitClear 2026 Benchmark</span>
      <p class="text-sm font-bold text-white mt-0.5">Code velocity surged 300%, but code churn & rollbacks surged 40%.</p>
    </div>
    <div class="text-right">
      <span class="text-sm font-bold text-cyan-400">What if an AI reviewer only spoke when it could PROVE a crash?</span>
    </div>
  </div>
</body>
</html>"""
    },
    {
        "id": "scene_02_the_guarantee",
        "title": "The Linus Guarantee",
        "html_file": "scene_02_the_guarantee.html",
        "script": (
            "Meet Linus. An autonomous adversarial Pull Request verifier built with the official Strands Agents SDK and Amazon Bedrock AgentCore. "
            "Linus is not a linter. Linus doesn't care about your indentation, variable names, or stylistic preferences. "
            "Linus operates under one unbreakable rule: The Assured Execution Gate. "
            "Linus is physically barred from commenting on a Pull Request unless it runs an adversarial boundary test in an isolated sandbox and captures an unhandled runtime crash. "
            "Zero false positives. Zero noise. Guaranteed."
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="absolute -top-32 -left-32 w-96 h-96 bg-cyan-500/15 rounded-full blur-3xl pointer-events-none"></div>
  <div class="absolute -bottom-32 -right-32 w-96 h-96 bg-purple-500/15 rounded-full blur-3xl pointer-events-none"></div>

  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-cyan-400"></div>
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">THE ARCHITECTURAL CONTRACT</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="mono text-xs px-2.5 py-1 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">Bedrock AgentCore</span>
      <span class="mono text-xs px-2.5 py-1 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Strands SDK</span>
    </div>
  </div>

  <div class="bg-slate-900/90 border-2 border-red-500/50 rounded-2xl p-7 shadow-2xl relative z-10 my-auto">
    <div class="flex items-center justify-between mb-4">
      <span class="mono text-xs text-red-400 font-bold uppercase tracking-widest">THE UNBREAKABLE LAW</span>
      <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
        THE ASSURED EXECUTION GATE
      </span>
    </div>
    <h2 class="text-2xl font-extrabold text-white leading-snug mb-3">
      "Linus is physically barred from commenting on a Pull Request unless it executes an adversarial boundary test in an isolated sandbox and captures an unhandled runtime crash."
    </h2>
    <p class="text-slate-400 text-sm">
      Traditional review bots predict bugs with high hallucinations. Linus executes exploits with empirical certainty.
    </p>
  </div>

  <div class="grid grid-cols-4 gap-4 relative z-10">
    <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
      <div class="mono text-xs text-teal-400 font-bold mb-1">01 • AMBIENT SILENCE</div>
      <p class="text-xs text-slate-400">Zero comments on clean PRs. Silence is a feature.</p>
    </div>
    <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
      <div class="mono text-xs text-purple-400 font-bold mb-1">02 • 0ms AST PARSING</div>
      <p class="text-xs text-slate-400">Deterministic scans for null guards, zero divisors, and indices.</p>
    </div>
    <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
      <div class="mono text-xs text-amber-400 font-bold mb-1">03 • SANDBOX GATE</div>
      <p class="text-xs text-slate-400">Pytest subprocess isolation. Exit code != 0 required to speak.</p>
    </div>
    <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
      <div class="mono text-xs text-cyan-400 font-bold mb-1">04 • PERMANENT IMMUNITY</div>
      <p class="text-xs text-slate-400">Commits regression test to disk. 0 regressions across 268 tests.</p>
    </div>
  </div>
</body>
</html>"""
    },
    {
        "id": "scene_03_crime_scene",
        "title": "The Crime Scene: PR-104",
        "html_file": "scene_03_crime_scene.html",
        "script": (
            "Here is the crime scene in Acme Corp's checkout service: Pull Request 104. "
            "The developer added tiered volume discounts and retrieved the first item in the cart for partner promotions. "
            "Look at the developer's unit tests on the right: four out of four pass with flying colors. "
            "Why? Because every mock cart used during testing had items in it! "
            "Neither the developer nor human code review ever tested an empty cart. "
            "Lurking on line five is a fatal flaw: items index zero with zero length protection."
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">INVESTIGATION • SCENARIO PR-104</span>
    </div>
    <span class="mono text-xs px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Acme Corp Checkout Service</span>
  </div>

  <div class="grid grid-cols-12 gap-6 my-auto relative z-10">
    <!-- Code view -->
    <div class="col-span-7 bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl">
      <div class="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
        <span class="mono text-xs text-slate-400 font-semibold">checkout_service.py (PR-104 Diff)</span>
        <span class="mono text-[10px] text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/30">Line 5: Vulnerable</span>
      </div>
      <div class="mono text-xs space-y-1.5 leading-relaxed">
        <div class="text-slate-500">1 | def calculate_order_total(cart: dict) -> float:</div>
        <div class="text-slate-400">2 |     items = cart.get("items", [])</div>
        <div class="text-slate-500">3 |     </div>
        <div class="text-slate-500">4 |     # Partner promo tier check:</div>
        <div class="bg-red-500/20 border-l-4 border-red-500 px-2 py-1 text-red-200 font-bold rounded">
          5 |     primary_category = items[0].get("category", "general")
        </div>
        <div class="text-slate-500">6 |     </div>
        <div class="text-slate-400">7 |     subtotal = sum(i["price"] * i["quantity"] for i in items)</div>
        <div class="text-slate-400">8 |     if subtotal >= 100.0:</div>
        <div class="text-slate-400">9 |         return subtotal * 0.85</div>
        <div class="text-slate-400">10|     return subtotal</div>
      </div>
    </div>

    <!-- The Blind Spot -->
    <div class="col-span-5 flex flex-col justify-between space-y-4">
      <div class="bg-slate-900 border border-emerald-500/30 rounded-2xl p-5">
        <div class="flex items-center justify-between mb-2">
          <span class="mono text-xs text-emerald-400 font-bold">DEVELOPER TEST SUITE</span>
          <span class="mono text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">100% PASSING</span>
        </div>
        <div class="mono text-xs text-slate-400 space-y-1">
          <div>✓ test_single_item_cart() -> PASS</div>
          <div>✓ test_tiered_volume_discount() -> PASS</div>
          <div>✓ test_partner_promo_code() -> PASS</div>
        </div>
      </div>

      <div class="bg-slate-900 border border-red-500/40 rounded-2xl p-5">
        <span class="mono text-xs text-red-400 font-bold block mb-1">THE FATAL BLIND SPOT</span>
        <p class="text-xs text-slate-300 leading-relaxed">
          Every developer test mocked a cart containing 1 or 2 items. Nobody tested an empty cart: <code class="mono text-cyan-300">{"items": []}</code>.
          Linus's deterministic AST analyzer spots this boundary trap in under one millisecond.
        </p>
      </div>
    </div>
  </div>

  <div class="mono text-xs text-slate-400 flex items-center justify-between border-t border-slate-800 pt-3 relative z-10">
    <span>Traditional Linter: 0 warnings</span>
    <span>LLM Reviewer: Comments on docstrings</span>
    <span class="text-red-400 font-bold">Linus: Formulating Red Team Exploit...</span>
  </div>
</body>
</html>"""
    },
    {
        "id": "scene_04_execution_gate",
        "title": "Adversarial Proof in Action",
        "html_file": "scene_04_execution_gate.html",
        "script": (
            "Watch Linus trigger on pull request ingress. "
            "First, deterministic AST inspection flags the unchecked subscript hazard in zero milliseconds. "
            "Second, the Bedrock agent synthesizes an adversarial hypothesis: What if a visitor triggers checkout with an empty cart? "
            "Third, Linus runs this test inside an isolated pytest sandbox subprocess. "
            "Boom! Exit Code 1. Unhandled IndexError on line five captured! "
            "Because the crash is empirically proven in a sandbox, Linus finally speaks. Not a prediction—an undeniable fact."
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-cyan-400 animate-pulse"></div>
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">AMAZON BEDROCK AGENTCORE • LIVE TELEMETRY</span>
    </div>
    <span class="mono text-xs px-2.5 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/30 font-bold">DEFECT EMPIRICALLY PROVEN</span>
  </div>

  <!-- Telemetry Terminal -->
  <div class="bg-slate-900 border border-cyan-500/30 rounded-2xl p-5 shadow-2xl my-auto relative z-10 overflow-hidden">
    <div class="flex items-center justify-between mb-4 border-b border-slate-800 pb-2">
      <div class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-red-500/80"></span>
        <span class="w-3 h-3 rounded-full bg-amber-500/80"></span>
        <span class="w-3 h-3 rounded-full bg-emerald-500/80"></span>
        <span class="mono text-xs text-slate-400 ml-2">EventSource: /api/audit/stream/PR-104</span>
      </div>
      <span class="mono text-xs text-cyan-400">ResponseStream Mode • AWS Lambda</span>
    </div>

    <div class="mono text-xs space-y-2.5">
      <div class="flex items-center gap-3">
        <span class="text-slate-500 text-[11px]">14:32:01</span>
        <span class="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px] font-bold">INGRESS</span>
        <span class="text-slate-300">PR-104 webhook received: calculate_order_total (author: @alex-dev)</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-slate-500 text-[11px]">14:32:01</span>
        <span class="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] font-bold">AST_ANALYSIS</span>
        <span class="text-slate-300">Deterministic AST inspection (0.002s): Unchecked subscript on Line 5: items[0]</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-slate-500 text-[11px]">14:32:02</span>
        <span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold">SANDBOX_TEST</span>
        <span class="text-slate-300">Synthesized boundary test: def test_empty_cart_boundary_linus(): total = calculate_order_total({'items': []})</span>
      </div>
      <div class="flex items-center gap-3 bg-red-500/20 border border-red-500/40 p-2 rounded-lg">
        <span class="text-red-400 text-[11px] font-bold">14:32:03</span>
        <span class="px-2 py-0.5 rounded bg-red-500 text-white text-[10px] font-bold">CRASH_PROVEN</span>
        <span class="text-red-200 font-bold">EXIT CODE 1! Caught: IndexError: list index out of range on Line 5</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-slate-500 text-[11px]">14:32:04</span>
        <span class="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-bold">PATCH_SYNTHESIS</span>
        <span class="text-slate-300">Synthesized defensive guard: if not items: return 0.0</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-slate-500 text-[11px]">14:32:05</span>
        <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold">DUAL_VERIFICATION</span>
        <span class="text-emerald-300 font-semibold">Dual-Suite PASSED: Adversarial Test PASS | Baseline Tests 268/268 PASS (0 regressions)</span>
      </div>
    </div>
  </div>

  <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center justify-between relative z-10 mono text-xs">
    <span class="text-slate-400">Total Execution Time: <strong class="text-white">4.18s</strong></span>
    <span class="text-slate-400">False Alarms: <strong class="text-emerald-400">0%</strong></span>
    <span class="text-cyan-400 font-bold">Proof over Prediction. Zero Hallucinations.</span>
  </div>
</body>
</html>"""
    },
    {
        "id": "scene_05_immunization",
        "title": "Dual-Suite Verification & Immunity",
        "html_file": "scene_05_immunization.html",
        "script": (
            "Linus doesn't just alert engineers to crashes; it delivers the cure. "
            "Linus synthesizes a minimal defensive patch and runs Dual-Suite Verification: "
            "proving the adversarial exploit now passes, and all two hundred and sixty-eight baseline unit tests continue to pass with zero regressions. "
            "Then comes the magic: Recursive Test Addition. "
            "With one click, Linus commits the reproduction test permanently into tests/regressions on disk. "
            "This defect is permanently immunized against regressions forever."
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-emerald-400"></div>
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">THE CURE • 1-CLICK DUAL-VERIFIED REMEDIATION</span>
    </div>
    <span class="mono text-xs px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">0 REGRESSIONS</span>
  </div>

  <div class="grid grid-cols-12 gap-6 my-auto relative z-10">
    <!-- Patch Card -->
    <div class="col-span-6 bg-slate-900 border border-cyan-500/30 rounded-2xl p-5 shadow-2xl">
      <div class="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
        <span class="mono text-xs text-cyan-400 font-bold">Minimal Defensive Patch (PR-104)</span>
        <span class="mono text-[10px] bg-cyan-500/10 text-cyan-300 px-2 py-0.5 rounded">Synthesized by Linus</span>
      </div>
      <div class="mono text-xs space-y-1.5 leading-relaxed">
        <div class="text-slate-500">  items = cart.get("items", [])</div>
        <div class="bg-emerald-500/20 border-l-4 border-emerald-500 px-2 py-1 text-emerald-200 font-bold rounded">
          + # Guard against empty cart boundary condition<br>
          + if not items:<br>
          +     return 0.0
        </div>
        <div class="text-slate-500">  primary_category = items[0].get("category")</div>
        <div class="text-slate-500">  subtotal = sum(...)</div>
      </div>
    </div>

    <!-- Verification Matrix -->
    <div class="col-span-6 flex flex-col justify-between space-y-4">
      <div class="bg-slate-900 border border-emerald-500/40 rounded-2xl p-5">
        <span class="mono text-xs text-emerald-400 font-bold block mb-2">DUAL-SUITE VERIFICATION MATRIX</span>
        <div class="space-y-2 mono text-xs">
          <div class="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800">
            <span class="text-slate-300">1. Adversarial Boundary Exploit:</span>
            <span class="text-emerald-400 font-bold">✓ PASSED (0.01s)</span>
          </div>
          <div class="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800">
            <span class="text-slate-300">2. Full Test Suite (10 suites):</span>
            <span class="text-emerald-400 font-bold">✓ 268/268 PASSED (0 regressions)</span>
          </div>
        </div>
      </div>

      <div class="bg-slate-900 border border-purple-500/40 rounded-2xl p-5">
        <span class="mono text-xs text-purple-400 font-bold block mb-1">RECURSIVE TEST ADDITION</span>
        <p class="text-xs text-slate-300 leading-relaxed">
          Permanent regression guard committed to: <code class="mono text-cyan-300">tests/regressions/test_linus_pr_104.py</code>.
          The bug can never slip into production again.
        </p>
      </div>
    </div>
  </div>

  <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center justify-between relative z-10 mono text-xs">
    <span class="text-slate-400">Human-in-the-loop: <strong class="text-white">1-Click Approval</strong></span>
    <span class="text-emerald-400 font-bold">Codebase Permanently Immunized Forever</span>
  </div>
</body>
</html>"""
    },
    {
        "id": "scene_06_ambient_silence",
        "title": "Ambient Silence & Zero Waste",
        "html_file": "scene_06_ambient_silence.html",
        "script": (
            "What happens when a pull request is written well? "
            "Consider PR-401 from our payments core. The developer included defensive null checks on payment intents. "
            "Linus runs AST hazard analysis. Linus synthesizes adversarial boundary tests for null accounts and zero amounts. "
            "Every sandbox test exits cleanly with code zero. "
            "And what does Linus do? Linus remains completely, beautifully silent. "
            "No comments. No spam. No wasted developer attention. "
            "Noise is the enemy of engineering. Silence is our signature feature."
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-teal-400"></div>
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">SCENARIO PR-401 • PAYMENTS CORE</span>
    </div>
    <span class="mono text-xs px-2.5 py-1 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30 font-bold">AMBIENT SILENCE TRIGGERED</span>
  </div>

  <div class="my-auto relative z-10 space-y-6">
    <div class="bg-slate-900 border border-teal-500/40 rounded-2xl p-7 shadow-2xl">
      <div class="flex items-center justify-between mb-4">
        <span class="mono text-xs text-teal-400 font-bold uppercase tracking-widest">RESILIENT CODE DETECTED</span>
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40">
          ZERO COMMENTS POSTED
        </span>
      </div>
      <h2 class="text-2xl font-bold text-white mb-2">
        PR-401: Resilient Payment Intent Processor
      </h2>
      <p class="text-slate-300 text-sm leading-relaxed mb-4">
        The engineer defensively guarded against null accounts and zero amounts: <code class="mono text-teal-300">if not account: return REJECTED</code>.
        Linus executed boundary attacks with <code class="mono text-teal-300">None</code> and <code class="mono text-teal-300">amount=0</code>. All exited with code 0.
      </p>
      <div class="bg-slate-950 rounded-xl p-4 border border-slate-800 mono text-xs text-teal-400 flex items-center justify-between">
        <span>✓ Linus Sandbox: Zero unhandled runtime crashes captured</span>
        <span class="text-slate-400">Status: Clean & Merged</span>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-6">
      <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
        <div class="mono text-xs text-red-400 font-bold mb-1">TRADITIONAL AI REVIEW BOTS</div>
        <p class="text-xs text-slate-400">Spam 15 comments on variable names, cyclomatic complexity, and stylistic trivia. Developers mute them.</p>
      </div>
      <div class="bg-slate-900/80 border border-teal-500/30 rounded-xl p-4">
        <div class="mono text-xs text-teal-400 font-bold mb-1">THE LINUS ADVANTAGE</div>
        <p class="text-xs text-slate-400">Absolute ambient silence. When Linus speaks, it's a guaranteed fire drill. When it's quiet, you merge in peace.</p>
      </div>
    </div>
  </div>

  <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center justify-between relative z-10 mono text-xs">
    <span class="text-slate-400">Noise is the enemy of engineering.</span>
    <span class="text-teal-400 font-bold">Silence is our signature feature.</span>
  </div>
</body>
</html>"""
    },
    {
        "id": "scene_07_architecture_live",
        "title": "AWS Serverless & Production Live",
        "html_file": "scene_07_architecture_live.html",
        "script": (
            "Under the hood, Linus is packaged natively for Amazon Bedrock AgentCore and deployed serverless on AWS Lambda using the AWS Lambda Web Adapter. "
            "With Response Stream mode and public Function URLs, Linus delivers live Server-Sent Events with zero idle costs. "
            "Zero dollars per month when idle. Instant scale-to-zero. "
            "Linus is one hundred percent open source under the MIT license, with two hundred and sixty-eight passing tests, live on AWS today. "
            "Stop reviewing noise. Start proving crashes. "
            "Welcome to Linus."
        ),
        "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 w-[1280px] h-[720px] overflow-hidden flex flex-col justify-between p-10 border-4 border-slate-800 relative">
  <div class="flex items-center justify-between border-b border-slate-800 pb-3 relative z-10">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-emerald-400"></div>
      <span class="mono text-xs tracking-widest text-slate-400 uppercase font-semibold">AWS SERVERLESS ARCHITECTURE & LIVE PRODUCTION</span>
    </div>
    <span class="mono text-xs px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">$0.00/MONTH IDLE COST</span>
  </div>

  <div class="my-auto relative z-10 space-y-5">
    <!-- Live deployment box -->
    <div class="bg-slate-900 border-2 border-cyan-500/50 rounded-2xl p-5 shadow-2xl">
      <span class="mono text-xs text-cyan-400 font-bold block mb-1">LIVE INTERACTIVE SRE CONSOLE</span>
      <h2 class="text-xl font-extrabold text-white mono mb-2 break-all">
        https://snyy6s27u7t3pyufxbu7yzei3y0dixmk.lambda-url.us-east-1.on.aws/
      </h2>
      <p class="text-xs text-slate-300">
        Live on AWS Lambda • Response Stream Mode • 4 Production Scenarios + Custom Input Sandbox
      </p>
    </div>

    <!-- Architecture Grid -->
    <div class="grid grid-cols-3 gap-4 mono text-xs">
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <span class="text-purple-400 font-bold block mb-1">AMAZON BEDROCK</span>
        <span class="text-slate-300">Claude 3.7 via agentcore.yaml for hypothesis reasoning and defensive patch synthesis.</span>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <span class="text-cyan-400 font-bold block mb-1">STRANDS AGENTS SDK</span>
        <span class="text-slate-300">Native tool calling, deterministic AST parser, and isolated subprocess sandbox test runner.</span>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <span class="text-emerald-400 font-bold block mb-1">LAMBDA WEB ADAPTER</span>
        <span class="text-slate-300">Scale-to-zero serverless container on ECR. $0.00 standing cost. Real-time SSE streaming.</span>
      </div>
    </div>

    <!-- GitHub Box -->
    <div class="bg-slate-900 border border-purple-500/30 rounded-xl p-4 flex items-center justify-between mono text-xs">
      <div>
        <span class="text-purple-400 font-bold">100% OPEN SOURCE (MIT LICENSE):</span>
        <span class="text-white ml-2 font-bold">https://github.com/Tony-Stark2025/linus</span>
      </div>
      <span class="text-emerald-400 font-bold">268/268 Tests Passing (100%)</span>
    </div>
  </div>

  <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center justify-between relative z-10 mono text-xs">
    <span class="text-slate-300">"Code is cheap. Verification is expensive."</span>
    <span class="text-cyan-400 font-bold">Linus — Proving crashes before production.</span>
  </div>
</body>
</html>"""
    },
]


def render_html_to_png(html_path: Path, png_path: Path):
    cmd = [
        EDGE_PATH,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        f"--screenshot={png_path.resolve()}",
        "--window-size=1280,720",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True)


async def generate_speech(text: str, output_file: Path):
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE)
    await comm.save(str(output_file))


def get_audio_duration(audio_file: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_file),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


async def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    scene_videos = []

    print("🚀 Starting High-Impact Creative Demo Video Generation...")
    for idx, scene in enumerate(SCENES, 1):
        scene_id = scene["id"]
        print(f"\n[{idx}/{len(SCENES)}] Processing '{scene['title']}' ({scene_id})...")

        # 1. Save HTML
        html_path = ASSETS_DIR / scene["html_file"]
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(scene["html"])

        # 2. Render HTML to 720p PNG
        png_path = ASSETS_DIR / f"{scene_id}.png"
        render_html_to_png(html_path, png_path)
        print(f"  ✓ Rendered high-impact slide: {png_path.name}")

        # 3. Generate Neural Voiceover
        audio_path = ASSETS_DIR / f"{scene_id}.mp3"
        await generate_speech(scene["script"], audio_path)
        duration = get_audio_duration(audio_path)
        print(f"  ✓ Synthesized audio: {audio_path.name} ({duration:.2f}s)")

        # 4. Compile scene MP4
        total_duration = duration + 0.4
        scene_mp4 = ASSETS_DIR / f"{scene_id}.mp4"
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(png_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", f"{total_duration:.2f}",
            str(scene_mp4),
        ]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"  ✓ Compiled scene MP4: {scene_mp4.name}")
        scene_videos.append(scene_mp4)

    # 5. Concatenate all scenes into final video
    print(f"\n🎬 Concatenating {len(scene_videos)} scenes into {FINAL_VIDEO.name}...")
    concat_list_file = ASSETS_DIR / "creative_concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for sv in scene_videos:
            f.write(f"file '{sv.resolve().as_posix()}'\n")

    ffmpeg_concat_cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(FINAL_VIDEO),
    ]
    subprocess.run(ffmpeg_concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    size_mb = FINAL_VIDEO.stat().st_size / (1024 * 1024)
    print(f"\n🎉 CREATIVE DEMO VIDEO COMPLETED!")
    print(f"  File: {FINAL_VIDEO.resolve()}")
    print(f"  Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    asyncio.run(main())
