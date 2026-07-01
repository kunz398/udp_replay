#!/bin/bash
# Run once on the Oracle VPS to install and start the relay as a systemd service.
set -e

echo "==> Installing iptables-persistent..."
DEBIAN_FRONTEND=noninteractive sudo apt-get install -y iptables-persistent

echo "==> Opening UDP port 9000..."
sudo iptables -I INPUT -p udp --dport 9000 -j ACCEPT
sudo netfilter-persistent save

echo "==> Installing systemd service..."
sudo cp bto-relay.service /etc/systemd/system/bto-relay.service
sudo systemctl daemon-reload
sudo systemctl enable bto-relay
sudo systemctl start bto-relay

echo ""
echo "Done. Check status with:  sudo systemctl status bto-relay"
echo "Follow logs with:         sudo journalctl -u bto-relay -f"
