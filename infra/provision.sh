#!/usr/bin/env bash
# =============================================================================
# AI Cloud Cost Detective — Azure Infrastructure Provisioning Script
# =============================================================================
# Usage:  bash infra/provision.sh
#
# What it creates (all inside a single resource group for easy teardown):
#   1. Resource Group     : cost-detective-rg  (eastus)
#   2. Virtual Machine    : auto-selected SKU  (intentionally over-provisioned)
#   3. Storage Account    : Standard_LRS       (idle, no data)
#   4. Public IP Address  : Static / Standard  (unattached)
#   5. PostgreSQL Flex    : Standard_B1ms      (app database)
#   6. PostgreSQL DB      : costdetectivedb
#
# Resources 2-4 are purposely "wasteful" so the AI has real findings to report.
# The VM is stopped (deallocated) right after creation — you won't pay compute.
#
# Cost estimate (eastus, resources running 24/7):
#   VM (stopped/deallocated) : ~$0/month  (only disk ~$2/month)
#   Storage Account          : ~$0.02/month (empty LRS)
#   Public IP (static)       : ~$3.65/month
#   PostgreSQL B1ms          : ~$12.50/month
#   ─────────────────────────────────────────
#   Total estimate           : ~$18/month
#   Run `bash infra/teardown.sh` when done to stop all charges.
# =============================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
RG="cost-detective-rg"
LOCATION="eastus"
VM_NAME="costdetective-vm"
STORAGE_NAME="costdetectivestore$(openssl rand -hex 4)"   # must be globally unique
PIP_NAME="costdetective-pip"
PG_SERVER="costdetective-pg-$(openssl rand -hex 4)"       # must be globally unique
PG_DB="costdetectivedb"
PG_ADMIN="pgadmin"
# Generate a strong random password (letters + digits + special chars)
PG_PASSWORD="CostDet-$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9' | head -c 16)!"

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "🔍 Checking prerequisites..."

if ! command -v az &>/dev/null; then
  echo "❌ Azure CLI not found. Install with: brew install azure-cli"
  exit 1
fi

ACCOUNT=$(az account show --query "{name:name, id:id}" -o json 2>/dev/null || echo "")
if [ -z "$ACCOUNT" ]; then
  echo "❌ Not logged in. Run: az login"
  exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "✅ Logged in to subscription: $SUBSCRIPTION_ID"
echo ""

# ── 1. Resource Group ─────────────────────────────────────────────────────────
echo "📦 [1/6] Creating resource group: $RG in $LOCATION..."
az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --output none
echo "✅ Resource group created."

# ── 2. Virtual Machine ────────────────────────────────────────────────────────
echo ""
echo "💻 [2/6] Finding an available VM SKU in $LOCATION..."

# Try a list of "over-provisioned" SKUs in order of preference.
# Standard_D4s_v3 is common but can be capacity-restricted on free subscriptions.
CANDIDATE_SKUS=(
  "Standard_D4s_v3"
  "Standard_D4s_v4"
  "Standard_D4s_v5"
  "Standard_D4_v3"
  "Standard_D4_v4"
  "Standard_D2s_v3"
  "Standard_B4ms"
  "Standard_B2ms"
)

VM_SIZE=""
for SKU in "${CANDIDATE_SKUS[@]}"; do
  echo "   Checking $SKU..."
  RESTRICTIONS=$(az vm list-skus \
    --location "$LOCATION" \
    --size "$SKU" \
    --query "[0].restrictions[?reasonCode=='NotAvailableForSubscription'] | length(@)" \
    -o tsv 2>/dev/null || echo "99")
  if [ "$RESTRICTIONS" = "0" ] || [ -z "$RESTRICTIONS" ]; then
    VM_SIZE="$SKU"
    echo "   ✅ $SKU is available — using this."
    break
  else
    echo "   ⚠️  $SKU has capacity restrictions, trying next..."
  fi
done

if [ -z "$VM_SIZE" ]; then
  echo "❌ No suitable VM SKU found in $LOCATION. Skipping VM creation."
  echo "   The other resources will still be provisioned."
  VM_SIZE="SKIPPED"
fi

if [ "$VM_SIZE" != "SKIPPED" ]; then
  echo "💻 Creating VM: $VM_NAME (size: $VM_SIZE — intentionally over-provisioned)..."
  az vm create \
    --resource-group "$RG" \
    --name "$VM_NAME" \
    --image Ubuntu2204 \
    --size "$VM_SIZE" \
    --admin-username azureuser \
    --generate-ssh-keys \
    --tags "env=dev" "purpose=cost-detective-test" \
    --output none

  echo "⏸  Deallocating VM to avoid compute charges..."
  az vm deallocate \
    --resource-group "$RG" \
    --name "$VM_NAME" \
    --output none
  echo "✅ VM ($VM_SIZE) created and deallocated (disk only billing ~\$2/month)."
fi

# ── 3. Storage Account ────────────────────────────────────────────────────────
echo ""
echo "🗄  [3/6] Creating storage account: $STORAGE_NAME (idle/unused)..."
az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags "env=dev" "purpose=cost-detective-test" \
  --output none
echo "✅ Storage account created."

# ── 4. Unattached Public IP ───────────────────────────────────────────────────
echo ""
echo "🌐 [4/6] Creating unattached public IP: $PIP_NAME..."
az network public-ip create \
  --resource-group "$RG" \
  --name "$PIP_NAME" \
  --sku Standard \
  --allocation-method Static \
  --tags "env=dev" "purpose=cost-detective-test" \
  --output none
echo "✅ Public IP created (unattached — will be flagged by AI)."

# ── 5. PostgreSQL Flexible Server ─────────────────────────────────────────────
echo ""
echo "🐘 [5/6] Creating Azure PostgreSQL Flexible Server: $PG_SERVER..."
echo "   (This takes 3-5 minutes...)"
az postgres flexible-server create \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --location "$LOCATION" \
  --admin-user "$PG_ADMIN" \
  --admin-password "$PG_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15 \
  --storage-size 32 \
  --public-access 0.0.0.0 \
  --tags "env=dev" "purpose=cost-detective-app-db" \
  --output none
echo "✅ PostgreSQL Flexible Server created."

# ── 6. App Database ───────────────────────────────────────────────────────────
echo ""
echo "📋 [6/6] Creating database: $PG_DB on $PG_SERVER..."
az postgres flexible-server db create \
  --resource-group "$RG" \
  --server-name "$PG_SERVER" \
  --database-name "$PG_DB" \
  --output none
echo "✅ Database created."

# ── Summary ───────────────────────────────────────────────────────────────────
PG_HOST="$PG_SERVER.postgres.database.azure.com"
DATABASE_URL="postgresql://$PG_ADMIN:$PG_PASSWORD@$PG_HOST/$PG_DB?ssl=require"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅  ALL RESOURCES PROVISIONED SUCCESSFULLY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Resource Group : $RG"
echo "Location       : $LOCATION"
echo "Subscription   : $SUBSCRIPTION_ID"
echo ""
echo "📋 Copy the following into your backend/.env file:"
echo ""
echo "AZURE_SUBSCRIPTION_ID=\"$SUBSCRIPTION_ID\""
echo "USE_MOCK_AZURE_CLI=\"false\""
echo "DATABASE_URL=\"$DATABASE_URL\""
echo ""
echo "⚠️  Store these credentials securely — they will not be shown again."
echo ""
echo "Next steps:"
echo "  1. Update backend/.env with the values above"
echo "  2. cd backend && source venv/bin/activate"
echo "  3. pip install -r requirements.txt"
echo "  4. uvicorn main:app --reload"
echo ""
echo "💡 To delete ALL resources and stop billing:"
echo "   bash infra/teardown.sh"
echo "════════════════════════════════════════════════════════════════"
