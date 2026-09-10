# Linus: Demo Video Script (4-Minute Pitch)

**Target Duration**: 3:45 – 4:15 minutes  
**Format**: Screen recording with voiceover (Split view: Code & Dashboard)  
**Hackathon Track**: AWS Agents for Humans — Track 2: Professional Agents

---

## Timeline & Scene-by-Scene Breakdown

| Time | Scene | Visual | Voiceover Audio |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:40** | **The Hook & Problem** | Slide / Headshot with DORA / GitClear 2026 charts showing +40% code churn and PR review fatigue. | *"Welcome. In 2026, AI lets us write code ten times faster than ever. But here’s the harsh reality: code velocity is up, but production stability is down. DORA calls this the Verification Gap. Code churn is up 40%, and senior developers spend the majority of their week debugging subtle PR edge cases. Even worse, current AI review bots spam PRs with hundreds of nitpicks and 65% false alarms. Developers just mute them. What if an AI reviewer only spoke when it could prove a crash in production?"* |
| **0:40 - 1:15** | **Introducing Linus** | Title card: **LINUS — Autonomous Adversarial PR Verifier** with Strands SDK & Bedrock badges. | *"Introducing Linus, the autonomous adversarial PR verifier built with the official Strands Agents SDK and Amazon Bedrock AgentCore. Linus acts as an automated Red Teamer that operates silently in the background on pull requests. Linus has one unbreakable rule: The Assured Execution Gate. It is physically forbidden from commenting unless it executes an adversarial boundary test in an isolated sandbox and captures an unhandled runtime crash. Zero noise. Zero false positives."* |
| **1:15 - 1:45** | **Scenario Setup (PR-104)** | Web Dashboard: Showing PR-104 (`calculate_checkout_total`), developer diff, and green passing unit tests badge. | *"Let’s see it live on our Enterprise SRE Console. Here is PR-104 from Acme Corp. The developer added tiered volume discounts and checked the first item in the cart for partner promotions. Look at the status badge: all existing developer unit tests are passing 100%. A traditional CI pipeline or human reviewer would merge this right now."* |
| **1:45 - 2:40** | **Live Audit & Proof** | Click **Run Autonomous Audit**. Watch AgentCore telemetry stream live in Panel 2. | *"Now, let's trigger Linus. Watch the real-time Bedrock AgentCore telemetry trace on the middle panel. First, Linus’s deterministic AST engine inspects the code in zero milliseconds. It spots a high-risk structural vector: subscript indexing on the items list with constant index 0, with no preceding length check. Next, the Strands agent formulates an adversarial hypothesis: What happens when a user applies a discount with an empty cart? Linus executes this boundary test in an isolated pytest sandbox. Boom! Exit Code 1. Captured: IndexError: list index out of range on line 5."* |
| **2:40 - 3:20** | **Patching & Immunization** | Panel 3: Defect Proven card, verified diff, and 1-click Approve button. | *"Because the defect is empirically proven, Linus surfaces the Surface Decision Card on the right. Linus doesn’t just report the crash—it synthesizes a minimal defensive patch and runs Dual-Suite Verification: proving both the adversarial test and all baseline tests pass with zero regressions. Now watch: when we click 'Approve Patch', Linus performs Recursive Test Addition. It commits the reproduction test permanently into tests/regressions/test_linus_pr_104.py. This bug can never happen again."* |
| **3:20 - 3:55** | **Architecture & Bedrock Core** | Quick cut to `agentcore.yaml` and Mermaid architecture diagram. | *"Under the hood, Linus is powered by the Strands Agents SDK and packaged natively for Amazon Bedrock AgentCore via agentcore.yaml. It leverages Claude 3.7 on Bedrock for hypothesis reasoning, combined with deterministic AST parsing and sandboxed subprocess execution for instant verification. All eight engine and web server unit tests are verified and passing 100%."* |
| **3:55 - 4:10** | **Closing & Impact** | Final screen: GitHub repo link, MIT license, Devpost submission. | *"Linus is 100% open source under the MIT license, ready to deploy to your AWS environment today. Code is cheap. Verification is expensive. Linus proves crashes before they hit production. Thank you!"* |

---

## Screen Recording Tips for Presenter:
1. Ensure the browser is at 100% zoom with dark mode enabled.
2. Have `http://localhost:8000` open and verified.
3. Test the "Run Autonomous Audit" button once before recording so the animation is smooth.
4. Keep the cursor movements smooth and deliberate when highlighting the AST findings, stack trace, and 1-click patch button.
