# EZ1‑M Graphite uploader

This script polls an APsystems EZ1‑M solar inverter over the local network, extracts metrics and sends them to Graphite on Grafana Cloud.

## Features

- Polls inverter every 60 seconds (configurable)
- Maps raw inverter fields into meaningful metric names
- Sends metrics to Grafana Cloud’s Graphite endpoint
- Graceful handling of network errors
- Optional debug logging
- Ready for systemd deployment

## Requirements

- Python 3.8+
- requests library

Install:

    pip install requests

## Configuration

Edit the top of the script:

    ez1m_ip = "IP_ADDRESS"

    graphite_url = "https://graphite-prod-01-eu-west-0.grafana.net/graphite/metrics"
    user_id = "YOUR_GRAFANA_USER_ID"
    api_token = "YOUR_GRAFANA_API_TOKEN"
    metric_prefix = "EZ1-M"

# Running as a systemd Service

Recommended for continuous operation.

## 1. Copy the script

Place it somewhere persistent:

    /opt/ez1-m_graphite/ez1-m_graphite.py

Make it executable:

    chmod +x /opt/ez1-m_graphite/ez1-m_graphite.py

## 2. Create a systemd service file

Create:

    /etc/systemd/system/ez1-m_graphite.service

Contents:

    [Unit]
    Description=EZ1-M Graphite uploader
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    ExecStart=/usr/bin/python3 /opt/ez1-m_graphite/ez1-m_graphite.py
    WorkingDirectory=/opt/ez1-m_graphite
    Restart=always
    RestartSec=10
    User=root
    Environment=PYTHONUNBUFFERED=1

    [Install]
    WantedBy=multi-user.target

## 3. Reload systemd and enable service

    sudo systemctl daemon-reload
    sudo systemctl enable --now ez1-m_graphite.service

## 4. Check logs

    journalctl -u ez1-m_graphite.service -f
