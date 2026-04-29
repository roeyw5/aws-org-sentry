# Manual Scan Button Setup

How to wire the Slack "Scan Now" button to the API Gateway endpoint deployed by Terraform.

## How it works

Terraform deploys an API Gateway endpoint alongside the Lambda. When a user clicks "Scan Now" in the Slack monitoring channel, Slack POSTs to that endpoint, which invokes the Lambda with the button payload. The Lambda verifies the Slack request signature (HMAC-SHA256) before processing.

## Prerequisites

- Terraform has been applied for the account (API Gateway endpoint exists)
- You have admin access to the Slack app

---

## Step 1: Get the API Gateway URL

After `terraform apply`:

```bash
terraform workspace select {account_name}
terraform output slack_trigger_url
```

Note the URL — it looks like `https://{id}.execute-api.{region}.amazonaws.com/prod/scan`.

## Step 2: Configure the Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Select your AWS Scanner Slack app
3. Click **Interactivity & Shortcuts** in the left sidebar
4. Enable **Interactivity**
5. Paste the API Gateway URL into **Request URL**
6. Click **Save Changes**

## Step 3: Add the Signing Secret to Terraform

1. In **Basic Information** → **App Credentials**, copy the **Signing Secret**
2. Add it to your tfvars:

```hcl
slack_signing_secret = "your-signing-secret-here"
```

3. Apply:

```bash
terraform workspace select {account_name}
terraform apply -var-file=accounts/{account_name}.tfvars
```

Terraform writes the signing secret to Parameter Store. The Lambda reads it at runtime to verify incoming Slack requests.

## Step 4: Test

Trigger a manual scan from the Slack monitoring channel. Check logs:

```bash
aws logs tail /aws/lambda/aws-scanner-{account_name} --follow
```

You should see the Lambda invoked with a Slack payload, followed by scan results.

---

## Troubleshooting

**"dispatch_failed" in Slack**
- Verify the Request URL in the Slack app settings matches `terraform output slack_trigger_url`
- Check API Gateway is deployed: `aws apigateway get-rest-apis`

**"invalid_signature" in Lambda logs**
- The signing secret in Parameter Store doesn't match the Slack app's signing secret
- Re-apply Terraform with the correct `slack_signing_secret`

**Lambda not triggered**
- Check API Gateway has Lambda integration permission: the IAM policy created by Terraform should include `lambda:InvokeFunction`
