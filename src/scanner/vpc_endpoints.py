"""VPC endpoint scanning."""

import boto3
from typing import Dict


def scan_vpc_endpoints(credentials: Dict[str, str], region: str) -> Dict:
    """Scan for VPC interface endpoints in a specific region.

    Interface endpoints incur hourly charges ($0.01/hour).
    Gateway endpoints (S3, DynamoDB) are free and excluded from count.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        Dict with count and service_names of interface endpoints
        Example: {'count': 4, 'service_names': ['ec2', 'rds', 'secretsmanager', 'cloudwatch'], 'region': 'ap-south-1'}
    """
    ec2 = boto3.client("ec2", region_name=region, **credentials)

    response = ec2.describe_vpc_endpoints()

    interface_endpoints = [
        ep
        for ep in response.get("VpcEndpoints", [])
        if ep["VpcEndpointType"] == "Interface"
        and ep["State"] in ["available", "pending"]
    ]

    service_names = []
    for ep in interface_endpoints:
        service_name = ep.get("ServiceName", "")
        if service_name:
            # Extract service name: com.amazonaws.ap-south-1.ec2 -> ec2
            parts = service_name.split(".")
            service_names.append(parts[-1])

    return {
        "count": len(interface_endpoints),
        "service_names": service_names,
        "region": region,
    }
