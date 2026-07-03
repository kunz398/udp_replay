#!/bin/bash
# Run once on Oracle Linux 9 VPS to install and start the UDP relay as a systemd service.
# This is only needed if you want a STANDALONE relay on a separate machine.
# If the full server (main.py) runs on this VPS, the relay runs in-process — skip this script.
set -e

echo "==> Installing Python 3.11..."
sudo dnf install -y python3.11

echo "==> Opening firewall ports (OS level)..."
sudo firewall-cmd --permanent --add-port=9000/udp   # game relay
sudo firewall-cmd --permanent --add-port=9001/tcp   # health check
sudo firewall-cmd --reload

echo ""
echo "NOTE: Also open ports 9000/udp and 9001/tcp in the Oracle Cloud console"
echo "      under Networking > Virtual Cloud Networks > Security Lists."
echo ""

echo "==> Installing systemd service..."
sudo cp bto-relay.service /etc/systemd/system/bto-relay.service
sudo systemctl daemon-reload
sudo systemctl enable bto-relay
sudo systemctl restart bto-relay

echo ""
echo "Done. Check status with:  sudo systemctl status bto-relay"
echo "Follow logs with:         sudo journalctl -u bto-relay -f"
