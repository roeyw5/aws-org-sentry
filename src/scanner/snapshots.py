"""EBS snapshot scanning."""

import boto3
from typing import List, Dict


def scan_snapshots(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan EBS snapshots owned by the account in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of snapshot dictionaries with id, volume_id, size_gb, region, created_at
        Example: [{'id': 'snap-1234', 'volume_id': 'vol-5678', 'size_gb': 50, 'region': 'ap-south-1', 'created_at': datetime}]
    """
    ec2 = boto3.client("ec2", region_name=region, **credentials)

    response = ec2.describe_snapshots(OwnerIds=["self"])

    snapshots = []
    for snapshot in response.get("Snapshots", []):
        snapshots.append(
            {
                "id": snapshot["SnapshotId"],
                "volume_id": snapshot.get("VolumeId", "N/A"),
                "size_gb": snapshot["VolumeSize"],
                "region": region,
                "created_at": snapshot["StartTime"],
            }
        )

    return snapshots
