"""EBS volume scanning."""

import boto3
from typing import List, Dict


def scan_volumes(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan unattached EBS volumes in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of volume dictionaries with id, size_gb, region, created_at
        Example: [{'id': 'vol-1234', 'size_gb': 50, 'region': 'ap-south-1', 'created_at': datetime}]
    """
    ec2 = boto3.client("ec2", region_name=region, **credentials)

    response = ec2.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )

    volumes = []
    for volume in response.get("Volumes", []):
        volumes.append(
            {
                "id": volume["VolumeId"],
                "size_gb": volume["Size"],
                "region": region,
                "created_at": volume["CreateTime"],
            }
        )

    return volumes
