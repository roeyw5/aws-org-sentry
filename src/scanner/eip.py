"""Elastic IP scanning."""

import boto3
from datetime import datetime
from typing import List, Dict


def scan_elastic_ips(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan for unattached Elastic IPs in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of unattached Elastic IP dictionaries with id, public_ip, allocation_time
        Example: [{'id': 'eipalloc-123', 'public_ip': '1.2.3.4', 'allocation_time': datetime, 'region': 'ap-south-1'}]
    """
    ec2 = boto3.client("ec2", region_name=region, **credentials)

    response = ec2.describe_addresses()

    elastic_ips = []
    for address in response.get("Addresses", []):
        # EIP is unattached if it has no AssociationId
        if "AssociationId" not in address:
            # Use datetime.now() fallback for moto mock compatibility
            allocation_time = address.get("AllocationTime", datetime.now())
            elastic_ips.append(
                {
                    "id": address["AllocationId"],
                    "public_ip": address["PublicIp"],
                    "allocation_time": allocation_time,
                    "region": region,
                }
            )

    return elastic_ips
