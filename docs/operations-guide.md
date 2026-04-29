# Operations Guide

Day-to-day operations, monitoring, and troubleshooting for the AWS Organization Scanner.

## Accessing the Tooling Account

All Lambda scanner infrastructure runs in the **tooling account** (where you deployed via Terraform). You need access to this account for operations and troubleshooting.

### AWS Console

1. Log in to your primary AWS account
2. Click your username → **Switch Role**
3. Enter the tooling account ID and role (`OrganizationAccountAccessRole` or your custom role)

### AWS CLI

```bash
export AWS_PROFILE=<your-tooling-profile>
aws sts get-caller-identity  # Verify you're in the tooling account
```

---

## Monitoring Scans

Scans run on the EventBridge schedule defined in your tfvars (`morning_scan_cron`, `evening_scan_cron`). Each scan:

1. Posts per-account alerts to individual Slack DMs (when resources exceed thresholds)
2. Posts a consolidated summary to the monitoring channel

**What to watch for in the monitoring channel:**
- Scan success rate — any failed accounts appear in the summary
- Accounts with repeated alerts (may indicate stuck resources)
- Unexpected resource counts

### Viewing Lambda Logs

```bash
# Tail live logs for an account
aws logs tail /aws/lambda/aws-scanner-{account_name} --follow

# Search for errors in the last hour
aws logs filter-log-events \
  --log-group-name /aws/lambda/aws-scanner-{account_name} \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

---

## Manual Scan

Trigger a scan outside the schedule:

```bash
aws lambda invoke \
  --function-name aws-scanner-{account_name} \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json
cat response.json
```

Or use the "Scan Now" button in the Slack monitoring channel.

---

## Configuration Management

### Updating Thresholds

Edit `terraform/accounts/{account_name}.tfvars`, then apply:

```bash
cd terraform
terraform workspace select {account_name}
terraform apply -var-file=accounts/{account_name}.tfvars
```

Threshold changes take effect on the next scan without redeploying Lambda code.

### Updating the Users Mapping

The `users_mapping` in tfvars maps account names to `{id, email}` pairs. Terraform writes this to Parameter Store when you apply.

After updating tfvars:

```bash
terraform workspace select {account_name}
terraform apply -var-file=accounts/{account_name}.tfvars
```

### Disabling Scans Temporarily

Set `enable_schedules = false` in tfvars and apply. Re-enable when ready.

Alternatively, disable the EventBridge rule directly:

```bash
aws events disable-rule --name aws-scanner-{account_name}-morning
aws events disable-rule --name aws-scanner-{account_name}-evening
```

---

## Troubleshooting

### Lambda Not Firing

1. Check EventBridge rules are enabled: `aws events list-rules --name-prefix aws-scanner-{account_name}`
2. Check Lambda execution role has `events:PutEvents` permission
3. Verify the Lambda is deployed: `aws lambda get-function --function-name aws-scanner-{account_name}`

### Slack Alerts Not Arriving

1. Check Lambda logs for `Slack API error`
2. Verify the Slack token in Parameter Store is valid: `aws ssm get-parameter --name /org-scanner/{account_name}/slack-token --with-decryption`
3. Confirm the bot is invited to the monitoring channel

### Cross-Account Scan Failing

```
Error: An error occurred (AccessDenied) when calling the AssumeRole operation
```

1. Verify the trust policy on `OrganizationAccountAccessRole` (or your custom role) in the target account allows assumption from the tooling account
2. Check the Lambda execution role has `sts:AssumeRole` permission

### "No accounts found in OU"

1. Verify `ou_id` in tfvars points to the correct OU
2. Check the Lambda has `organizations:ListAccountsForParent` permission
3. Confirm the OU actually contains accounts: `aws organizations list-accounts-for-parent --parent-id {ou_id}`

---

## Enabling / Disabling Resource Types

In `terraform/accounts/{account_name}.tfvars`:

```hcl
scan_toggles = {
  ec2           = true
  rds           = true
  eks           = false   # disabled
  elb           = true
  nat           = true
  volumes       = true
  eip           = true
  vpc_endpoints = false   # disabled
  lightsail     = true
  snapshots     = true
  rds_snapshots = true
}
```

Apply with `terraform apply -var-file=accounts/{account_name}.tfvars`.

---

## DRY_RUN Mode

Set `dry_run = true` in tfvars to run scans without sending user DMs (monitoring channel still receives summaries). Useful when testing threshold changes.
