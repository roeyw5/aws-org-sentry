"""NAT Gateway scanning for AWS accounts."""

import boto3
from typing import Dict


def scan_nat_gateways(credentials: Dict, region: str) -> int:
    """Scan for active NAT Gateways in region.

    Args:
        credentials: AWS credentials from assumed role
        region: AWS region to scan

    Returns:
        Count of active NAT Gateways (available or pending state)
    """
    try:
        ec2 = boto3.client('ec2', region_name=region, **credentials)

        response = ec2.describe_nat_gateways(
            Filters=[
                {'Name': 'state', 'Values': ['available', 'pending']}
            ]
        )

        return len(response.get('NatGateways', []))

    except Exception as e:
        print(f"Error scanning NAT Gateways in {region}: {e}")
        return 0
