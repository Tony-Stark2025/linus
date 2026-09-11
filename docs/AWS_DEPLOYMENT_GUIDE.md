# AWS Deployment & Submission Guide for Linus

This guide outlines how to deploy the Linus Enterprise SRE Console to AWS and complete the submission for the **AWS Agents for Humans Hackathon** (Track 2: Professional Agents).

---

## 📌 Step 1: Push Codebase to GitHub (Prerequisite)

Devpost and AWS container deployment workflows require a public GitHub repository.

Using the GitHub CLI (`gh`):
```bash
# Ensure latest commits are pushed to your repository
git push origin master
```
Repository URL: `https://github.com/Tony-Stark2025/linus`

---

## 💰 Cost-Optimized Deployment: Serverless vs Container

| Deployment Strategy | Monthly Idle Cost | HTTPS Endpoint | Free Tier Covered? | Best For |
| :--- | :---: | :---: | :---: | :--- |
| **Method A: AWS Lambda Serverless (via Lambda Web Adapter)** | **$0.00 / month** | Free Native Function URL | ✅ 100% Free Tier | **Hackathons, Demos, $0 Cost** |
| **Method B: Amazon ECS Express Mode** | **~$35 – $45 / month** | Managed ALB Endpoint | ❌ ALB fee applies | High continuous 24/7 traffic |

> [!TIP]
> **Recommended**: Use **Method A (AWS Lambda Serverless)**. It costs **$0.00** when idle, handles up to 15-minute timeouts, supports real-time Server-Sent Events (SSE) telemetry response streaming, and generates a free public HTTPS URL instantly.

---

## 🚀 Method A: Deploy to AWS Lambda Serverless ($0/mo, 100% Free Tier)

Linus includes native support for the official **[AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)** inside [`Dockerfile`](../Dockerfile). It runs the FastAPI app and SSE telemetry streams on AWS Lambda with zero code modifications.

### 1. Build and Push Container Image to Amazon ECR

```bash
# 1. Set your AWS environment configuration
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO="linus-sre-console"

# 2. Create Amazon ECR repository (if not created yet)
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION

# 3. Authenticate Docker with Amazon ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# 4. Build the container image
docker build -t $ECR_REPO:latest .

# 5. Tag and push to ECR
docker tag $ECR_REPO:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest
```

### 2. Create the Serverless Lambda Function

1. Open the [AWS Lambda Console](https://console.aws.amazon.com/lambda).
2. Click **Create function** &rarr; select **Container image**:
   - **Function name**: `linus-sre-console`
   - **Container image URI**: Select `linus-sre-console:latest` from ECR.
   - **Architecture**: `x86_64`
3. Click **Create function**.

### 3. Configure Resources & Free Public HTTPS Function URL

Under the newly created function's **Configuration** tab:
1. **General configuration**:
   - **Memory**: `2048 MB` (allocates 2 dedicated vCPUs for rapid pytest execution).
   - **Timeout**: `3 min 0 sec` (180s).
   - **Ephemeral storage (`/tmp`)**: `1024 MB` (provides isolated scratch space for tests).
2. **Function URL** (Instant Free HTTPS Endpoint):
   - Navigate to **Function URL** &rarr; click **Create Function URL**.
   - **Auth type**: `NONE` (Publicly accessible for Devpost judges and GitHub PR webhooks).
   - Expand **Additional settings**:
     - **Invoke mode**: Select **`RESPONSE_STREAM`** (enables live Server-Sent Events telemetry streaming!).
     - Check **Configure cross-origin resource sharing (CORS)**.
   - Click **Save**.

Your live, zero-cost public HTTPS endpoint is immediately ready:
👉 **`https://<unique-id>.lambda-url.us-east-1.on.aws`**

---

## 🏗️ Method B: Deploy to Amazon ECS Express Mode (Alternative)

> [!NOTE]
> Starting April 30, 2026, AWS App Runner is no longer accepting new customers. AWS officially recommends **Amazon ECS Express Mode** for full container cluster deployments.

1. Open the [Amazon ECS Express Mode Console](https://us-east-1.console.aws.amazon.com/ecs/v2/express-mode?region=us-east-1).
2. Click **Create Service**:
   - **Service Name**: `linus-sre-console`
   - **Container Image URI**: `<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/linus-sre-console:latest`
   - **Container Port**: `8000`
   - **Public IP / Internet Access**: Enabled
   - **Environment Variables**:
     - `PORT`: `8000`
     - `AWS_DEFAULT_REGION`: `us-east-1`
3. Click **Deploy**.

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
5. **Live Application URL**: Your AWS Lambda Function URL (`https://<id>.lambda-url.us-east-1.on.aws`) or ECS Express Mode URL.
6. **Demo Video Link**: Link your recorded demo video (≤ 5 minutes, see `docs/DEMO_VIDEO_SCRIPT.md`).
7. **Project Description**: Copy the executive summary and architecture diagrams from `README.md`.
8. **Bonus Points (+0.6)**: Publish `docs/AWS_BUILDER_POST.md` on [builder.aws.com](https://builder.aws.com) and paste the article link in the submission form!
