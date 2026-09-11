# AWS Deployment & Submission Guide for Linus

This guide outlines how to deploy the Linus Enterprise SRE Console to AWS and complete the submission for the **AWS Agents for Humans Hackathon** (Track 2: Professional Agents).

---

## 📌 Step 1: Push Codebase to GitHub (Prerequisite)

Devpost and AWS container deployment workflows require a public GitHub repository.

Using the GitHub CLI (`gh`):
```bash
# 1. Ensure latest commits are pushed to your repository
git push origin master
```
Repository URL: `https://github.com/Tony-Stark2025/linus`

---

## 🚀 Step 2: Deploy to Amazon ECS Express Mode (Modern Container Hosting)

> [!IMPORTANT]
> **AWS Platform Note**: Starting April 30, 2026, AWS App Runner is no longer accepting new customers. AWS officially recommends **[Amazon ECS Express Mode](https://us-east-1.console.aws.amazon.com/ecs/v2/express-mode?region=us-east-1)** for deploying containerized web applications with automatic scaling, simplified networking, and public HTTPS endpoints.

### 1. Build and Push Container to Amazon ECR

```bash
# Set your AWS configuration
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO="linus-sre-console"

# 1. Create ECR repository (if not already created)
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION

# 2. Authenticate Docker with Amazon ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# 3. Build the Linus Docker image
docker build -t $ECR_REPO:latest .

# 4. Tag and push to ECR
docker tag $ECR_REPO:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest
```

### 2. Deploy via Amazon ECS Express Mode

1. Open the [Amazon ECS Express Mode Console](https://us-east-1.console.aws.amazon.com/ecs/v2/express-mode?region=us-east-1).
2. Click **Create Service**:
   - **Service Name**: `linus-sre-console`
   - **Container Image URI**: `<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linus-sre-console:latest`
   - **Container Port**: `8000`
   - **Public IP / Internet Access**: Enabled (Assign Public IP)
   - **Environment**:
     - `PORT`: `8000`
     - `AWS_DEFAULT_REGION`: `us-east-1`
3. Click **Deploy**.
4. In ~2 minutes, Amazon ECS Express Mode provisions the task and provides an active public HTTPS endpoint for your live Linus SRE Console!

---

## 🧠 Step 3: Register in Amazon Bedrock AgentCore

Linus is architected natively for Amazon Bedrock AgentCore and pre-configured via [`agentcore.yaml`](../agentcore.yaml).

### In the AWS Management Console:
1. Navigate to **Amazon Bedrock** &rarr; **Agents** (in `us-east-1` or `us-west-2`).
2. Click **Create Agent**:
   - **Agent Name**: `linus-adversarial-verifier`
   - **Model**: Select **Anthropic Claude 3.7 Sonnet** (or Amazon Nova Pro).
   - **Instructions / System Prompt**: Copy from `agentcore.yaml`:
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
4. **GitHub Repository URL**: `https://github.com/Tony-Stark2025/linus`
5. **Live Application URL**: Your Amazon ECS Express Mode public endpoint (or local demo recording link).
6. **Demo Video Link**: Link your recorded demo video (≤ 5 minutes, see `docs/DEMO_VIDEO_SCRIPT.md`).
7. **Project Description**: Copy the executive summary and architecture diagrams from `README.md`.
8. **Bonus Points (+0.6)**: Publish `docs/AWS_BUILDER_POST.md` on [builder.aws.com](https://builder.aws.com) and paste the article link in the submission form!
