# Adding a New Account

Step-by-step guide for deploying the scanner to a new target account using Terraform workspaces.

## Prerequisites

- AWS CLI access to the tooling account (where Lambda runs)
- Terraform installed and initialized (`terraform init` in `terraform/`)
- The target account already exists in your AWS Organization
- A Slack bot token with `users:read.email`, `im:write`, `chat:write` scopes

---

## Steps

### 1. Create the tfvars file

Copy the example and fill it in:

```bash
cp terraform/accounts/example.tfvars terraform/accounts/{account_name}.tfvars
```

Edit `terraform/accounts/{account_name}.tfvars`:

```hcl
account_name = "dev"   # must match workspace name below

ou_id = "ou-xxxx-xxxxxxxx"   # OU containing the accounts to scan

tooling_account_id = "123456789012"   # account where Lambda deploys

users_mapping = {
  "user-one" = {
    id    = "111111111111"
    email = "user.one@example.com"
  }
  "user-two" = {
    id    = "222222222222"
    email = "user.two@example.com"
  }
}

slack_token          = "xoxb-..."
slack_signing_secret = "..."
monitoring_channel   = "aws-alerts"

morning_scan_cron = "0 9 ? * SUN-THU *"
evening_scan_cron = "0 18 ? * SUN-THU *"
```

> **Keep this file out of version control** — it contains secrets. It is already in `.gitignore`.

### 2. Create the Terraform workspace

```bash
cd terraform
terraform workspace new dev
```

The workspace name **must match** `account_name` in the tfvars file. The `null_resource` precondition in `main.tf` will fail if they differ.

### 3. Deploy

```bash
terraform apply -var-file=accounts/dev.tfvars
```

This creates:
- Lambda function (`aws-scanner-dev`)
- IAM execution role and cross-account assume-role policy
- EventBridge scheduler rules (morning + evening)
- API Gateway endpoint (for Slack scan button)
- Parameter Store entries (Slack token, users mapping, OU ID, regions, scan toggles)
- CloudWatch log group (7-day retention)

### 4. Verify

```bash
# Trigger a manual scan
aws lambda invoke \
  --function-name aws-scanner-dev \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json
cat response.json

# Tail logs
aws logs tail /aws/lambda/aws-scanner-dev --follow
```

### 5. Set up the Slack button (optional)

See [manual-scan-deployment.md](manual-scan-deployment.md) for wiring the API Gateway URL to a Slack button.

---

## Threshold Customization

Add threshold overrides to your tfvars:

```hcl
# Alert on EC2 running > 6h instead of the default 12h
threshold_ec2_running_hours = 6

# Allow up to 1 NAT gateway (default alerts on any)
threshold_nat_gateway_count = 1
```

See [../THRESHOLDS.md](../THRESHOLDS.md) for all available thresholds.
