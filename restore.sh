#!/bin/bash
# ============================================
# Pwnagotchi Restore Script
# Generated: 2026-07-08 03:14
# Source: pwnagotchi
# ============================================
#
# Usage:
#   git clone git@github.com:YOUR/REPO.git
#   cd REPO
#   sudo ./restore.sh
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root${NC}"
    echo "Usage: sudo ./restore.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo " Pwnagotchi Restore"
echo " From backup: pwnagotchi"
echo "========================================"
echo ""

read -p "This will overwrite existing files. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Stopping pwnagotchi service..."
systemctl stop pwnagotchi 2>/dev/null || true

echo ""
echo "Restoring files..."

# Restore all backed-up directories
for dir in etc home root usr; do
    if [ -d "$SCRIPT_DIR/$dir" ]; then
        echo -e "  ${YELLOW}Processing /$dir...${NC}"
        cp -r "$SCRIPT_DIR/$dir"/* "/$dir/" 2>/dev/null || true
    fi
done

echo ""
echo "Fixing permissions..."

# SSH permissions (critical!)
if [ -d /root/.ssh ]; then
    chown -R root:root /root/.ssh
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/* 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} /root/.ssh"
fi

if [ -d /etc/ssh ]; then
    chown -R root:root /etc/ssh
    chmod 644 /etc/ssh/*.pub 2>/dev/null || true
    chmod 600 /etc/ssh/ssh_host_*_key 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} /etc/ssh"
fi

# Pi home directory
if [ -d /home/pi ]; then
    chown -R pi:pi /home/pi 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} /home/pi"
fi

echo ""
echo -e "${GREEN}========================================"
echo " Restore complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review /etc/pwnagotchi/config.toml"
echo "  2. sudo systemctl start pwnagotchi"
echo ""
