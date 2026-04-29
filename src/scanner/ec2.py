"""EC2 instance scanning."""

import boto3
from typing import List, Dict


def scan_ec2_instances(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan EC2 instances in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of EC2 instance dictionaries with id, type, state, launch_time
        Example: [{'id': 'i-1234', 'type': 't2.micro', 'state': 'running', 'launch_time': datetime}]
    """
    ec2 = boto3.client("ec2", region_name=region, **credentials)

    response = ec2.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]
    )

    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            # Extract Name tag
            name = "No Name"
            if instance.get("Tags"):
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

            instances.append(
                {
                    "id": instance["InstanceId"],
                    "name": name,
                    "type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "launch_time": instance["LaunchTime"],
                }
            )

    return instances
