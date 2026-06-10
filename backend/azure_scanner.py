import os
import json
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK_AZURE_CLI", "false").lower() == "true"
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")

# ---------------------------------------------------------------------------
# Mock data — used when USE_MOCK_AZURE_CLI=true (local dev, no Azure account)
# ---------------------------------------------------------------------------
MOCK_RESOURCE_GROUPS = [
    {"name": "dev-resources-rg", "location": "eastus"},
    {"name": "prod-app-rg",      "location": "eastus"},
]

MOCK_RESOURCES = [
    {
        "type": "Microsoft.Compute/virtualMachines",
        "name": "dev-vm-01",
        "location": "eastus",
        "sku": {"name": "Standard_D8s_v3"},
        "tags": {"env": "dev"},
        "properties": {"powerState": "VM running"},
    },
    {
        "type": "Microsoft.Sql/servers/databases",
        "name": "prod-db",
        "location": "eastus",
        "sku": {"name": "Premium_P4"},
        "tags": {"env": "prod"},
        "properties": {},
    },
    {
        "type": "Microsoft.Network/publicIPAddresses",
        "name": "unused-ip-1",
        "location": "eastus",
        "sku": {"name": "Standard"},
        "tags": {},
        "properties": {"ipAddress": "20.10.5.220", "ipConfiguration": None},
    },
]


# ---------------------------------------------------------------------------
# Helpers — build rich resource dict from an Azure SDK resource object
# ---------------------------------------------------------------------------
def _serialize_resource(res) -> dict:
    """Convert an azure-mgmt-resource GenericResourceExpanded to a plain dict."""
    return {
        "type": res.type,
        "name": res.name,
        "location": res.location,
        "kind": getattr(res, "kind", None),
        "sku": (
            {"name": res.sku.name, "tier": getattr(res.sku, "tier", None)}
            if res.sku
            else None
        ),
        "tags": dict(res.tags) if res.tags else {},
        "properties": {},   # generic resources don't expose full properties
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_resource_groups() -> list:
    """Return list of {name, location} dicts for all resource groups."""
    if USE_MOCK:
        return MOCK_RESOURCE_GROUPS

    if not AZURE_SUBSCRIPTION_ID:
        raise Exception(
            "AZURE_SUBSCRIPTION_ID is not set. "
            "Add it to backend/.env or set USE_MOCK_AZURE_CLI=true for local dev."
        )

    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient

        credential = DefaultAzureCredential()
        client = ResourceManagementClient(credential, AZURE_SUBSCRIPTION_ID)

        groups = []
        for rg in client.resource_groups.list():
            groups.append({"name": rg.name, "location": rg.location})
        return groups

    except ImportError:
        raise Exception(
            "Azure SDK not installed. Run: pip install azure-identity azure-mgmt-resource"
        )
    except Exception as e:
        raise Exception(f"Azure SDK error listing resource groups: {str(e)}")


def get_resources_in_group(resource_group: str) -> list:
    """Return a list of resource dicts for every resource in the given group."""
    if USE_MOCK:
        return MOCK_RESOURCES

    if not AZURE_SUBSCRIPTION_ID:
        raise Exception(
            "AZURE_SUBSCRIPTION_ID is not set. "
            "Add it to backend/.env or set USE_MOCK_AZURE_CLI=true for local dev."
        )

    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient
        from azure.mgmt.compute import ComputeManagementClient

        credential = DefaultAzureCredential()
        resource_client = ResourceManagementClient(credential, AZURE_SUBSCRIPTION_ID)
        compute_client  = ComputeManagementClient(credential, AZURE_SUBSCRIPTION_ID)

        resources = []
        for res in resource_client.resources.list_by_resource_group(resource_group):
            entry = _serialize_resource(res)

            # Enrich VMs with power state (running / deallocated / stopped)
            if res.type and res.type.lower() == "microsoft.compute/virtualmachines":
                try:
                    iv = compute_client.virtual_machines.instance_view(
                        resource_group, res.name
                    )
                    statuses = [s.display_status for s in (iv.statuses or [])]
                    entry["properties"]["powerState"] = (
                        next((s for s in statuses if "VM" in s), "Unknown")
                    )
                except Exception:
                    entry["properties"]["powerState"] = "Unknown"

            resources.append(entry)

        return resources

    except ImportError:
        raise Exception(
            "Azure SDK not installed. Run: "
            "pip install azure-identity azure-mgmt-resource azure-mgmt-compute"
        )
    except Exception as e:
        raise Exception(f"Azure SDK error listing resources: {str(e)}")
