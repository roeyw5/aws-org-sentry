# Removing an Account

Steps for safely decommissioning the scanner for an account that no longer needs monitoring.

## Steps

### 1. Disable schedules first (optional but safe)

Prevent any scans from firing during the teardown:

```bash
cd terraform
terraform workspace select {account_name}
```

In `terraform/accounts/{account_name}.tfvars`, set:

```hcl
enable_schedules = false
```

```bash
terraform apply -var-file=accounts/{account_name}.tfvars
```

### 2. Destroy all infrastructure

```bash
terraform workspace select {account_name}
terraform destroy -var-file=accounts/{account_name}.tfvars
```

This removes:
- Lambda function
- IAM role and policies
- EventBridge rules
- API Gateway
- Parameter Store entries
- CloudWatch log group

### 3. Delete the workspace

```bash
terraform workspace select default
terraform workspace delete {account_name}
```

### 4. Archive the tfvars file

Either delete `terraform/accounts/{account_name}.tfvars` or move it to an `archive/` folder. Do **not** leave it committed if it contains real secrets.

### 5. Confirm in AWS Console

- Lambda → Functions: `aws-scanner-{account_name}` should be gone
- Systems Manager → Parameter Store: no entries under `/org-scanner/{account_name}/`
- EventBridge → Rules: no rules prefixed `aws-scanner-{account_name}`

---

## If Terraform State is Lost

If the workspace still exists but state is lost, manually delete resources:

```bash
# Lambda
aws lambda delete-function --function-name aws-scanner-{account_name}

# Parameter Store
for param in slack-token users-mapping ou-id regions scan-toggles; do
  aws ssm delete-parameter --name /org-scanner/{account_name}/$param
done

# EventBridge rules
aws events remove-targets --rule aws-scanner-{account_name}-morning --ids lambda
aws events delete-rule --name aws-scanner-{account_name}-morning
aws events remove-targets --rule aws-scanner-{account_name}-evening --ids lambda
aws events delete-rule --name aws-scanner-{account_name}-evening

# CloudWatch log group
aws logs delete-log-group --log-group-name /aws/lambda/aws-scanner-{account_name}
```
