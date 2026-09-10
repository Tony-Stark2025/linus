# AWS Deployment & Submission Guide for Linus

This guide outlines how to deploy Linus to AWS and complete the submission for the **AWS Agents for Humans Hackathon** (Track 2: Professional Agents).

---

## 📌 Step 1: Push Codebase to GitHub (Prerequisite)

Devpost and AWS App Runner require a public GitHub repository.

Using the GitHub CLI (`gh`):
```bash
# 1. Create a public repository and push
gh repo create linus --public --source=. --remote=origin --push

# 2. Or manually link to an existing GitHub repository
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/linus.git
git branch -M main
git push -u origin main
```

---

## 🚀 Step 2: Deploy to AWS App Runner (Live Public HTTPS URL)

**AWS App Runner** is the fastest, cleanest way to host the Linus SRE Console on AWS with an automatic public HTTPS URL (`https://<app-id>.us-east-1.awsapprunner.com`) and zero server management.

### Method A: Via AWS Management Console (Recommended, 3 minutes)
1. Open the **AWS Management Console** &rarr; navigate to **AWS App Runner**.
2. Click **Create service**.
3. Under **Source**:
   - Choose **Source code repository**.
   - Connect your GitHub account and select repository: `linus`.
   - Branch: `main` (or `master`).
   - Deployment trigger: **Automatic**.
4. Under **Build settings**:
   - Configuration file: select **Configure all settings here**.
   - Runtime: **Python 3**.
   - Build command: `pip install -e .`
   - Start command: `python -m uvicorn web_demo.server:app --host 0.0.0.0 --port 8000`
   - Port: `8000`
5. Under **Service settings**:
   - Service name: `linus-sre-console`.
   - CPU: `1 vCPU`, Memory: `2 GB`.
6. Click **Create & Deploy**.
   - In ~2 minutes, AWS App Runner will issue a live, publicly accessible HTTPS URL!

### Method B: Via Docker Container (AWS ECR)
```bash
# 1. Authenticate Docker to your AWS ECR registry
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build the Docker image
docker build -t linus-verifier:latest .

# 3. Tag and push to AWS ECR
docker tag linus-verifier:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linus-verifier:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linus-verifier:latest

# 4. Deploy image to App Runner or ECS Fargate
```

---

## 🧠 Step 3: Register in Amazon Bedrock AgentCore

Linus is architected natively for Amazon Bedrock AgentCore and pre-configured via [`agentcore.yaml`](../agentcore.yaml).

### In the AWS Management Console:
1. Navigate to **Amazon Bedrock** &rarr; **Agents** (in `us-east-1` or `us-west-2`).
2. Click **Create Agent**:
   - Agent Name: `linus-adversarial-verifier`
   - Model: Select **Anthropic Claude 3.7 Sonnet** (or Nova Pro).
   - Instructions / System Prompt: Copy from `agentcore.yaml`:
     > *"You are Linus, an autonomous adversarial PR verifier. Your mission is to formulate boundary hypotheses against AST-identified risk vectors, execute them in an isolated sandbox, and only surface if an unhandled runtime crash is empirically proven with zero false positives."*
3. **Action Groups (Tools)**:
   - Add Action Group 1: `inspect_ast_risks` (AST deterministic parser).
   - Add Action Group 2: `run_test_in_sandbox` (Subprocess isolated pytest sandbox).
   - Add Action Group 3: `verify_patch_dual_suite` (Dual verification & recursive test addition).
4. **AgentCore Memory**:
   - Enable session state memory with TTL: 86400s.
5. Click **Prepare Agent** and test via the Bedrock interactive test pane!

---

## 🏆 Step 4: Submit to Devpost

Go to the [AWS Agents for Humans Hackathon on Devpost](https://devpost.com):

1. **Project Title**: `Linus — Autonomous Adversarial PR Verifier`
2. **Tagline**: `Zero false-positive ambient PR verification powered by Strands Agents SDK & Amazon Bedrock AgentCore.`
3. **Track**: Select **Track 2: Professional Agents**.
4. **GitHub Repository URL**: Link your GitHub repository.
5. **Demo Video Link**: Link your recorded demo video (≤ 5 minutes, see `docs/DEMO_VIDEO_SCRIPT.md`).
6. **Project Description**: Copy the executive summary from `README.md`.
7. **Bonus Points (+0.6)**: Publish `docs/AWS_BUILDER_POST.md` on [builder.aws.com](https://builder.aws.com) and paste the article link in the submission form!
