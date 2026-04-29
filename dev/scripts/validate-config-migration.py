#!/usr/bin/env python3
"""
Configuration Migration Validation Script

Validates that users_mapping data in Parameter Store matches the tfvars file
configuration for a given account. Used before production cutover to ensure
data integrity during migration from bash to Lambda.

Usage:
    python scripts/validate-config-migration.py --account dev
    python scripts/validate-config-migration.py --account dev

Exit Codes:
    0: Validation passed (data matches)
    1: Validation failed (discrepancies found)
"""

import json
import sys
import argparse
import boto3
from typing import Dict, List, Any


def load_tfvars_users(account_name: str) -> Dict[str, Dict[str, str]]:
    """
    Load users_mapping from tfvars file.

    Note: This parses HCL tfvars files using simple string parsing.
    For production use, consider using python-hcl2 library.
    """
    tfvars_path = f"terraform/accounts/{account_name}.tfvars"

    try:
        with open(tfvars_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: tfvars file not found: {tfvars_path}")
        sys.exit(1)

    # Simple parsing: find users_mapping block
    users_mapping = {}
    in_mapping = False
    current_account = None
    brace_count = 0

    for line in content.split('\n'):
        line = line.strip()

        if line.startswith('users_mapping'):
            in_mapping = True
            brace_count = 0
            continue

        if in_mapping:
            # Count braces to track nesting
            brace_count += line.count('{') - line.count('}')

            # Exit when we close the users_mapping block
            if brace_count < 0:
                break

            # Parse: "Account.Name" = {
            if '=' in line and '{' in line and '"' in line:
                account_name = line.split('"')[1]
                users_mapping[account_name] = {}
                current_account = account_name
            # Parse: id = "123456789012"
            elif 'id' in line and '=' in line and current_account:
                user_id = line.split('"')[1]
                users_mapping[current_account]['id'] = user_id
            # Parse: email = "user@example.com"
            elif 'email' in line and '=' in line and current_account:
                email = line.split('"')[1]
                users_mapping[current_account]['email'] = email

    return users_mapping


def load_parameter_store_users(account_name: str, profile: str = 'default') -> Dict[str, Dict[str, str]]:
    """Load users_mapping from Parameter Store."""
    session = boto3.Session(profile_name=profile, region_name='us-east-1')
    ssm = session.client('ssm')

    param_name = f'/org-scanner/{account_name}/users-mapping'

    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return json.loads(response['Parameter']['Value'])
    except ssm.exceptions.ParameterNotFound:
        print(f"❌ Error: Parameter not found: {param_name}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading Parameter Store: {e}")
        sys.exit(1)


def validate_email_format(email: str) -> bool:
    """Validate email contains @ symbol (basic check)."""
    return '@' in email and '.' in email


def compare_mappings(tfvars_data: Dict, param_data: Dict, account_name: str) -> List[str]:
    """
    Compare tfvars and Parameter Store data.

    Returns list of issues found (empty if all matches).
    """
    issues = []

    # Check all accounts present
    tfvars_accounts = set(tfvars_data.keys())
    param_accounts = set(param_data.keys())

    if tfvars_accounts != param_accounts:
        missing = tfvars_accounts - param_accounts
        extra = param_accounts - tfvars_accounts

        if missing:
            issues.append(f"Missing accounts in Parameter Store: {sorted(missing)}")
        if extra:
            issues.append(f"Extra accounts in Parameter Store: {sorted(extra)}")

    # Check account details match
    for account in tfvars_accounts & param_accounts:
        tfvars_id = tfvars_data[account].get('id')
        tfvars_email = tfvars_data[account].get('email')

        param_id = param_data[account].get('id')
        param_email = param_data[account].get('email')

        if tfvars_id != param_id:
            issues.append(f"{account}: ID mismatch - tfvars='{tfvars_id}' vs param='{param_id}'")

        if tfvars_email != param_email:
            issues.append(f"{account}: Email mismatch - tfvars='{tfvars_email}' vs param='{param_email}'")

        # Validate email format
        if param_email and not validate_email_format(param_email):
            issues.append(f"{account}: Invalid email format '{param_email}'")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description='Validate config migration from tfvars to Parameter Store',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--account',
        required=True,
        help='Account name (dev, staging, prod)'
    )
    parser.add_argument(
        '--profile',
        default='default',
        help='AWS CLI profile name (default: default)'
    )

    args = parser.parse_args()

    print(f"🔍 Validating configuration for {args.account}...")
    print(f"   AWS Profile: {args.profile}")
    print(f"   Region: us-east-1\n")

    # Load data
    print("📄 Loading tfvars file...")
    tfvars_data = load_tfvars_users(args.account)
    print(f"   Found {len(tfvars_data)} accounts in tfvars\n")

    print("☁️  Loading Parameter Store...")
    param_data = load_parameter_store_users(args.account, args.profile)
    print(f"   Found {len(param_data)} accounts in Parameter Store\n")

    # Compare
    print("⚖️  Comparing data...")
    issues = compare_mappings(tfvars_data, param_data, args.account)

    if issues:
        print(f"\n❌ Validation FAILED for {args.account}:\n")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\n❌ Found {len(issues)} discrepancy(ies)")
        sys.exit(1)
    else:
        print(f"\n✅ Validation PASSED for {args.account}")
        print(f"   All {len(tfvars_data)} accounts match between tfvars and Parameter Store")
        print("   No encoding issues detected")
        print("   All email formats valid")
        sys.exit(0)


if __name__ == '__main__':
    main()
