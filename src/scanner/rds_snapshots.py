"""RDS snapshot scanning."""

import boto3
from typing import List, Dict


def scan_rds_snapshots(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan for manual RDS snapshots in a region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of manual RDS snapshot dictionaries with id, created_at,
        size_gb, region. Example: [{'id': 'my-snapshot', 'created_at': datetime,
        'size_gb': 100, 'region': 'ap-south-1'}]
    """
    rds = boto3.client("rds", region_name=region, **credentials)

    try:
        response = rds.describe_db_snapshots(SnapshotType="manual")

        # Filter available snapshots only
        snapshots = [
            {
                "id": s["DBSnapshotIdentifier"],
                "created_at": s["SnapshotCreateTime"],
                "size_gb": s["AllocatedStorage"],
                "region": region,
            }
            for s in response["DBSnapshots"]
            if s["Status"] == "available"
        ]

        return snapshots

    except Exception as e:
        print(f"    ERROR scanning RDS snapshots in {region}: {e}")
        return []
