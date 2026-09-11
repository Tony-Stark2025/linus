"""
Automated AWS Serverless Deployment Script for Linus.
Builds and pushes the container image to Amazon ECR for AWS Account 423716910242.
"""

import sys
import os
import subprocess
import base64
from pathlib import Path

AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "423716910242")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
REPO_NAME = "linus-sre-console"
IMAGE_TAG = "latest"
ECR_URI = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{REPO_NAME}:{IMAGE_TAG}"

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def check_docker():
    """Verifies that Docker daemon is active and responsive."""
    print("🐳 Checking Docker status...")
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            print("\n❌ Docker daemon is not running.")
            print("👉 Please launch Docker Desktop from your Start menu, wait ~30 seconds for it to start, and run this script again.")
            return False
        print("✅ Docker daemon is running.")
        return True
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False


def get_ecr_login_token():
    """Uses boto3 to fetch ECR login token if credentials are present."""
    try:
        import boto3
        ecr = boto3.client("ecr", region_name=AWS_REGION)
        
        # Ensure repository exists
        try:
            ecr.describe_repositories(repositoryNames=[REPO_NAME])
            print(f"✅ ECR repository '{REPO_NAME}' exists.")
        except Exception:
            print(f"📦 Creating ECR repository '{REPO_NAME}'...")
            ecr.create_repository(repositoryName=REPO_NAME)
            print(f"✅ ECR repository '{REPO_NAME}' created.")

        token_res = ecr.get_authorization_token()
        auth_data = token_res["authorizationData"][0]
        token = base64.b64decode(auth_data["authorizationToken"]).decode("utf-8")
        username, password = token.split(":")
        endpoint = auth_data["proxyEndpoint"]
        return username, password, endpoint
    except Exception as e:
        print(f"⚠️ Could not authenticate automatically via boto3: {e}")
        return None, None, None


def ensure_aws_credentials():
    """Ensures AWS credentials are set or prompts interactively."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        print("\n🔑 No AWS credentials found in environment.")
        try:
            key = input("Enter your AWS_ACCESS_KEY_ID (or press Enter to use AWS CLI login): ").strip()
            if key:
                os.environ["AWS_ACCESS_KEY_ID"] = key
                secret = input("Enter your AWS_SECRET_ACCESS_KEY: ").strip()
                os.environ["AWS_SECRET_ACCESS_KEY"] = secret
        except (EOFError, KeyboardInterrupt):
            pass


def main():
    print("=" * 70)
    print("🛡️  LINUS: AWS Serverless Lambda Deployment")
    print(f"Account ID: {AWS_ACCOUNT_ID}")
    print(f"Region:     {AWS_REGION}")
    print(f"ECR Image:  {ECR_URI}")
    print("=" * 70)

    if not check_docker():
        sys.exit(1)

    ensure_aws_credentials()
    print("\n🔑 Authenticating Docker with Amazon ECR...")
    username, password, endpoint = get_ecr_login_token()

    if password:
        login_proc = subprocess.run(
            ["docker", "login", "--username", username, "--password-stdin", endpoint],
            input=password,
            text=True,
            capture_output=True,
        )
        if login_proc.returncode == 0:
            print(f"✅ Successfully authenticated with {endpoint}")
        else:
            print(f"❌ Docker login failed: {login_proc.stderr}")
            sys.exit(1)
    else:
        print("\nℹ️  If you have AWS CLI installed, run:")
        print(f"    aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com")
        print("\nOr export your AWS credentials:")
        print("    $env:AWS_ACCESS_KEY_ID='your-access-key'")
        print("    $env:AWS_SECRET_ACCESS_KEY='your-secret-key'")

    print(f"\n🔨 Building Docker image ({REPO_NAME}:{IMAGE_TAG})...")
    build_proc = subprocess.run(
        ["docker", "build", "-t", f"{REPO_NAME}:{IMAGE_TAG}", "."],
        cwd=str(WORKSPACE_ROOT),
    )
    if build_proc.returncode != 0:
        print("❌ Docker build failed.")
        sys.exit(1)

    print(f"\n🏷️  Tagging image as {ECR_URI}...")
    subprocess.run(["docker", "tag", f"{REPO_NAME}:{IMAGE_TAG}", ECR_URI], check=True)

    print(f"\n🚀 Pushing image to Amazon ECR...")
    push_proc = subprocess.run(["docker", "push", ECR_URI])
    if push_proc.returncode != 0:
        print("❌ Docker push failed.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("🎉 SUCCESS: Container image pushed to Amazon ECR!")
    print(f"URI: {ECR_URI}")
    print("=" * 70)
    print("\n📋 Next Step: Create your $0/mo Serverless Lambda Function:")
    print("1. Open: https://console.aws.amazon.com/lambda/home?region=us-east-1#/create/function")
    print("2. Choose 'Container image'")
    print(f"3. Function name: {REPO_NAME}")
    print(f"4. Image URI: {ECR_URI}")
    print("5. Under Configuration -> General: Memory = 2048 MB, Timeout = 3 min")
    print("6. Under Configuration -> Function URL: Create Function URL with Auth=NONE, InvokeMode=RESPONSE_STREAM")
    print("\nDone! Your live public URL will be generated instantly.")


if __name__ == "__main__":
    main()
