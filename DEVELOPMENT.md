# Development

Detailed dev notes that complement the [README](README.md).

## Project Layout

```
org-scanner/
├── src/
│   ├── lambda_function.py       # Lambda entry point (~540 lines)
│   └── scanner/
│       ├── config.py            # Config loading from Parameter Store
│       ├── accounts.py          # OU → account list via Organizations API
│       ├── utils.py             # Uptime calculation, shared utilities
│       ├── slack.py             # Slack messaging + threshold evaluation
│       ├── ec2.py / rds.py / eks.py / nat.py / elb.py
│       ├── volumes.py / eip.py / vpc_endpoints.py
│       └── lightsail.py / snapshots.py / rds_snapshots.py
├── terraform/
│   ├── main.tf                  # Root: workspace validation + module call
│   ├── variables.tf             # Root input variables
│   ├── modules/account-scanner/ # Lambda, IAM, EventBridge, API GW, SSM
│   └── accounts/example.tfvars  # Template — copy per account
├── dev/
│   ├── tests/                   # pytest suite (17 test files)
│   ├── config/                  # pytest.ini, requirements-dev.txt
│   ├── scripts/                 # Makefile, package-lambda.sh, validation script
│   └── testing/test-event.json  # Sample Lambda event for manual testing
├── docs/                        # Operations and account management guides
└── THRESHOLDS.md                # Full threshold reference
```

## Key Code Locations

- **Entry point**: [src/lambda_function.py](src/lambda_function.py) — `lambda_handler(event, context)`
- **Config loading**: [src/scanner/config.py](src/scanner/config.py) — reads from Parameter Store
- **Account discovery**: [src/scanner/accounts.py](src/scanner/accounts.py) — Organizations API walk
- **Threshold evaluation**: [src/scanner/slack.py](src/scanner/slack.py) — `should_alert_*` functions
- **Per-resource scanners**: individual files in [src/scanner/](src/scanner/)

## Packaging the Lambda

```bash
# Build zip (uses Docker for Amazon Linux 2 compatible binaries)
./dev/scripts/package-lambda.sh

# Or via the Makefile
cd dev && make package
```

## Code-only Lambda update (skip Terraform)

```bash
aws lambda update-function-code \
  --function-name aws-scanner-{account_name} \
  --zip-file fileb://lambda-package.zip
```

## Terraform Workflow

```bash
cd terraform

# First time for a new account
terraform init
terraform workspace new dev
terraform apply -var-file=accounts/dev.tfvars

# Update existing account
terraform workspace select dev
terraform apply -var-file=accounts/dev.tfvars

# Destroy
terraform workspace select dev
terraform destroy -var-file=accounts/dev.tfvars
```

Workspace name **must match** `account_name` in the tfvars file — enforced by a `null_resource` precondition in `main.tf`.

## Adding a New Resource Scanner

1. Create `src/scanner/<resource>.py` with a `scan_<resource>(session, account_id, regions, thresholds)` function
2. Import and call it in `src/lambda_function.py` in the scan loop
3. Add a toggle to `scan_toggles` in `terraform/variables.tf` and the module's `variables.tf`
4. Add threshold variables if needed (follow the pattern in `terraform/variables.tf`)
5. Add tests in `dev/tests/test_<resource>.py`

## Lambda Environment Variables

Set by Terraform on the Lambda function:

| Variable | Description |
|---|---|
| `ACCOUNT_NAME` | Account workspace name |
| `DRY_RUN` | Skip user DMs, send monitoring only |
| `TEST_USER_EMAIL` | Redirect all DMs to this address |
| `SLACK_SIGNING_SECRET_PARAM` | SSM param path for Slack signing secret |
| `SCAN_TIMEZONE` | IANA timezone for timestamp formatting |

All other config (OU ID, users mapping, Slack token, regions, scan toggles) is loaded from Parameter Store at runtime by `config.py`.

## Gotchas

- Lambda runs in the **tooling account**, not in target accounts. Cross-account access is via `AssumeRole`.
- The IAM role assumed in target accounts defaults to `OrganizationAccountAccessRole`. If your org uses a different role name, set `assume_role_name` in tfvars.
- Slack signature verification uses the `SLACK_SIGNING_SECRET_PARAM` env var to look up the signing secret from SSM. If not set, webhook requests won't be verified (fine for scheduled scans, required for button callbacks).
- EventBridge crons in the example tfvars default to Sunday–Thursday — adjust for your workweek.
- The packaging script requires Docker to produce Amazon Linux 2 compatible binaries. Plain `pip install` on macOS/Linux can produce incompatible native extensions.
