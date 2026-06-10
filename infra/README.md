# Infrastructure — Azure Test Environment

This directory contains scripts to provision and tear down the real Azure resources used to test the AI Cloud Cost Detective.

## Resources Created

| Resource | Name | Type/SKU | Purpose | Est. Cost/mo |
|---|---|---|---|---|
| Resource Group | `cost-detective-rg` | — | Container for all resources | Free |
| Virtual Machine | `costdetective-vm` | `Standard_D4s_v3` (deallocated) | **Intentionally over-provisioned** → triggers AI high-severity finding | ~$2 (disk only) |
| Storage Account | `costdetectivestore*` | `Standard_LRS` | **Idle storage** → triggers AI unused finding | ~$0.02 |
| Public IP Address | `costdetective-pip` | Static/Standard | **Unattached IP** → triggers AI unused finding | ~$3.65 |
| PostgreSQL Flexible Server | `costdetective-pg-*` | `Standard_B1ms` Burstable | App database (replaces local Docker) | ~$12.50 |
| PostgreSQL Database | `costdetectivedb` | — | Application tables (users, analyses) | Included |
| **Total** | | | | **~$18/month** |

> **Note:** Resources with `*` have a random 4-char hex suffix appended to ensure global name uniqueness.

---

## Usage

### 1. Prerequisites

```bash
# Install Azure CLI (if not already installed)
brew install azure-cli

# Authenticate
az login
az account show   # confirm subscription
```

### 2. Provision All Resources

```bash
bash infra/provision.sh
```

The script will:
1. Create the `cost-detective-rg` resource group in `eastus`
2. Provision all test resources
3. Immediately deallocate the VM (stops compute charges)
4. Generate a secure random PostgreSQL password
5. Print the exact env vars to copy into `backend/.env`

**Total runtime:** ~5-8 minutes (PostgreSQL provisioning takes the longest).

### 3. Update `backend/.env`

After provisioning, the script prints values like:

```env
AZURE_SUBSCRIPTION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
USE_MOCK_AZURE_CLI="false"
DATABASE_URL="postgresql://pgadmin:<generated-password>@costdetective-pg-xxxx.postgres.database.azure.com/costdetectivedb?ssl=require"
```

Copy these into `backend/.env`.

### 4. Start the Backend

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt   # installs azure-identity, azure-mgmt-*
uvicorn main:app --reload
```

The backend will use `DefaultAzureCredential` which automatically picks up your `az login` session.

### 5. Tear Down (Stop All Charges)

```bash
bash infra/teardown.sh
```

This deletes the entire resource group and **all resources inside it** in one command.

---

## Authentication

The backend uses [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential) from the Azure Python SDK. It automatically tries these credential sources in order:

1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
2. **Azure CLI credentials** (`az login`) ← used in local dev
3. Managed Identity (when running on Azure infrastructure)

For local development, just running `az login` is sufficient — no service principal needed.

---

## Cost Control Tips

- The VM is **deallocated** by the provision script — you only pay for the disk (~$2/month).
- To stop ALL charges: run `bash infra/teardown.sh` when not actively testing.
- PostgreSQL `Standard_B1ms` is the smallest available tier — $12.50/month.
- All resources have `purpose=cost-detective-test` tags for easy cost tracking in Azure Cost Management.
