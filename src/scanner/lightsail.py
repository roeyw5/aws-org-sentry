"""Lightsail instance scanning."""

import boto3
from typing import List, Dict


def scan_lightsail_instances(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan for Lightsail instances in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of Lightsail instance dictionaries with name, bundle_id, state,
        created_at, region
        Example: [{'name': 'my-instance', 'bundle_id': 'nano_2_0',
                   'state': 'running', 'created_at': datetime,
                   'region': 'ap-south-1'}]
    """
    lightsail = boto3.client("lightsail", region_name=region, **credentials)

    try:
        response = lightsail.get_instances()
    except Exception as e:
        # Handle regions where Lightsail is unavailable or permission denied
        print(f"    Lightsail scanning error in {region}: {e}")
        return []

    instances = []
    for instance in response.get("instances", []):
        state = instance.get("state", {}).get("name", "").lower()

        # Exclude terminated/terminating instances
        if state in ["terminated", "terminating"]:
            continue

        instances.append(
            {
                "name": instance["name"],
                "bundle_id": instance["bundleId"],
                "state": state,
                "created_at": instance["createdAt"],
                "region": region,
            }
        )

    return instances
