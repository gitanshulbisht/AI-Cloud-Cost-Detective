import os
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK_AZURE_CLI", "false").lower() == "true"

MOCK_RESOURCE_GROUPS = [
    {"name": "dev-resources-rg", "location": "eastus"},
    {"name": "prod-app-rg", "location": "westus"}
]

MOCK_RESOURCES = [
    {
        "type": "Microsoft.Compute/virtualMachines",
        "name": "dev-vm-01",
        "location": "eastus",
        "sku": {"name": "Standard_D8s_v3"},
        "tags": {"env": "dev"}
    },
    {
        "type": "Microsoft.Sql/servers/databases",
        "name": "prod-db",
        "location": "westus",
        "sku": {"name": "Premium_P4"},
        "tags": {"env": "prod"}
    },
    {
        "type": "Microsoft.Network/publicIPAddresses",
        "name": "unused-ip-1",
        "location": "eastus",
        "sku": {"name": "Basic"},
        "tags": {}
    }
]

def get_resource_groups():
    if USE_MOCK:
        return MOCK_RESOURCE_GROUPS

    try:
        result = subprocess.run(["az", "group", "list", "-o", "json"], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except FileNotFoundError:
        raise Exception("Azure CLI is not installed.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Azure CLI error: {e.stderr}")
    except json.JSONDecodeError:
        raise Exception("Failed to parse Azure CLI output.")

def get_resources_in_group(resource_group: str):
    if USE_MOCK:
        return MOCK_RESOURCES

    try:
        result = subprocess.run(
            ["az", "resource", "list", "--resource-group", resource_group, "-o", "json"],
            capture_output=True, text=True, check=True
        )
        resources = json.loads(result.stdout)
        # Extract relevant fields
        parsed_resources = []
        for res in resources:
            parsed_resources.append({
                "type": res.get("type"),
                "name": res.get("name"),
                "location": res.get("location"),
                "sku": res.get("sku"),
                "tags": res.get("tags")
            })
        return parsed_resources
    except FileNotFoundError:
        raise Exception("Azure CLI is not installed.")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Azure CLI error: {e.stderr}")
    except json.JSONDecodeError:
        raise Exception("Failed to parse Azure CLI output.")
