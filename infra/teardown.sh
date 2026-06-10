#!/usr/bin/env bash
# =============================================================================
# AI Cloud Cost Detective — Azure Infrastructure Teardown
# =============================================================================
# Usage: bash infra/teardown.sh
#
# Deletes the entire "cost-detective-rg" resource group and ALL resources
# inside it. This stops all Azure charges immediately.
#
# ⚠️  This is IRREVERSIBLE. All data in the PostgreSQL database will be lost.
# =============================================================================

set -euo pipefail

RG="cost-detective-rg"

echo ""
echo "⚠️  WARNING: This will permanently delete the resource group '$RG'"
echo "    and ALL resources inside it (VM, Storage, Public IP, PostgreSQL)."
echo ""
read -r -p "Are you sure? Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "🗑  Deleting resource group: $RG ..."
az group delete --name "$RG" --yes --no-wait

echo ""
echo "✅ Deletion initiated. Resources are being removed in the background."
echo "   This typically takes 2-5 minutes to complete."
echo ""
echo "   Check status with:"
echo "   az group show --name $RG --query properties.provisioningState -o tsv"
