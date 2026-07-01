#!/bin/bash
# Run once on Oracle Linux 8 VPS to install and start the relay as a systemd service.
set -e

echo "==> Installing Python 3.9..."
sudo dnf install -y python39

echo "==> Opening firewall ports..."
sudo firewall-cmd --permanent --add-port=9000/udp   # game relay
sudo firewall-cmd --permanent --add-port=9001/tcp   # health check
sudo firewall-cmd --reload

echo "==> Installing systemd service..."
sudo cp bto-relay.service /etc/systemd/system/bto-relay.service
sudo systemctl daemon-reload
sudo systemctl enable bto-relay
sudo systemctl restart bto-relay

echo ""
echo "Done. Check status with:  sudo systemctl status bto-relay"
echo "Follow logs with:         sudo journalctl -u bto-relay -f"
