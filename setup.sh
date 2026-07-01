#!/bin/bash
# Run once on the Oracle VPS to install and start the relay as a systemd service.
set -e

# 1. Open UDP 9000 in Oracle's iptables (the OS firewall - separate from OCI security list)
sudo iptables -I INPUT -p udp --dport 9000 -j ACCEPT
sudo netfilter-persistent save

# 2. Install systemd service
sudo cp bto-relay.service /etc/systemd/system/bto-relay.service
sudo systemctl daemon-reload
sudo systemctl enable bto-relay
sudo systemctl start bto-relay

echo ""
echo "Done. Check status with:  sudo systemctl status bto-relay"
echo "Follow logs with:         sudo journalctl -u bto-relay -f"
