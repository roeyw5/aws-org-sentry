"""RDS database scanning."""

import boto3
from typing import List, Dict


def scan_rds_instances(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan RDS database instances in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of RDS instance dictionaries with id, class, status,
        create_time. Example: [{'id': 'mydb', 'class': 'db.t3.micro',
        'status': 'available', 'create_time': datetime}]
    """
    rds = boto3.client("rds", region_name=region, **credentials)

    response = rds.describe_db_instances()

    databases = []
    for db in response["DBInstances"]:
        databases.append(
            {
                "id": db["DBInstanceIdentifier"],
                "name": db["DBInstanceIdentifier"],
                "class": db["DBInstanceClass"],
                "status": db["DBInstanceStatus"],
                "create_time": db["InstanceCreateTime"],
            }
        )

    return databases
