"""Load Balancer scanning for AWS accounts."""

import boto3
from typing import Dict


def scan_load_balancers(credentials: Dict, region: str) -> int:
    """Scan for active Load Balancers in region.

    Args:
        credentials: AWS credentials from assumed role
        region: AWS region to scan

    Returns:
        Total count of all load balancers (ALB + NLB + CLB)
    """
    total = 0

    # Scan ALB/NLB (ELBv2)
    try:
        elbv2 = boto3.client('elbv2', region_name=region, **credentials)
        response = elbv2.describe_load_balancers()
        total += len(response.get('LoadBalancers', []))

    except Exception as e:
        print(f"Error scanning ELBv2 in {region}: {e}")

    # Scan Classic Load Balancers
    try:
        elb = boto3.client('elb', region_name=region, **credentials)
        response = elb.describe_load_balancers()
        total += len(response.get('LoadBalancerDescriptions', []))

    except Exception as e:
        print(f"Error scanning Classic ELB in {region}: {e}")

    return total
