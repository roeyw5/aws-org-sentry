"""EKS cluster scanning."""

import boto3
from typing import List, Dict


def scan_eks_clusters(credentials: Dict[str, str], region: str) -> List[Dict]:
    """Scan EKS clusters in a specific region.

    Args:
        credentials: AWS credentials dict from assume_role()
        region: AWS region name (e.g., 'ap-south-1')

    Returns:
        List of EKS cluster dictionaries with name, status, created_at
        Example: [{'name': 'my-cluster', 'status': 'ACTIVE', 'created_at': datetime}]
    """
    eks = boto3.client("eks", region_name=region, **credentials)

    cluster_names = eks.list_clusters()["clusters"]
    clusters = []

    for name in cluster_names:
        try:
            cluster = eks.describe_cluster(name=name)["cluster"]
            clusters.append(
                {
                    "name": cluster["name"],
                    "version": cluster.get("version", "unknown"),
                    "status": cluster["status"],
                    "created_at": cluster["createdAt"],
                }
            )
        except Exception as e:
            print(f"Warning: Failed to describe EKS cluster {name}: {e}")
            continue

    return clusters
