import requests
import time

# Configuration
ez1m_ip = "IP_ADDRESS"

graphite_url = "https://graphite-prod-01-eu-west-0.grafana.net/graphite/metrics"
user_id = "YOUR_GRAFANA_USER_ID"
api_token = "YOUR_GRAFANA_API_TOKEN"
metric_prefix = "EZ1-M"

interval = 60
debug = False

# Debug helper
def dbg(msg):
    if debug:
        print(msg)

# Fetch inverter data
def fetch_data():
    try:
        dbg("Fetching device data...")
        r = requests.get("http://" + ez1m_ip + ":8050/getOutputDataDetail", timeout=5)
        dbg(f"Device HTTP status: {r.status_code}")
        r.raise_for_status()
        data = r.json()
        dbg(f"Device JSON: {data}")
        return data
    except Exception as e:
        dbg(f"Failed to fetch device data: {e}")
        return None

# Map raw inverter fields → meaningful metrics
def map_metrics(raw):
    metrics = {}

    # Direct mappings
    metrics["total_power_p1"] = raw.get("p1")
    metrics["total_power_p2"] = raw.get("p2")

    metrics["today_production_p1"] = raw.get("e1")
    metrics["today_production_p2"] = raw.get("e2")

    metrics["lifetime_production_p1"] = raw.get("te1")
    metrics["lifetime_production_p2"] = raw.get("te2")

    metrics["voltage_p1"] = raw.get("v1")
    metrics["voltage_p2"] = raw.get("v2")

    metrics["current_p1"] = raw.get("c1")
    metrics["current_p2"] = raw.get("c2")

    metrics["grid_voltage"] = raw.get("gv")
    metrics["grid_frequency"] = raw.get("gf")
    metrics["inverter_temperature"] = raw.get("t")

    # Calculated totals
    metrics["total_power"] = (raw.get("p1") or 0) + (raw.get("p2") or 0)
    metrics["today_production"] = (raw.get("e1") or 0) + (raw.get("e2") or 0)
    metrics["lifetime_production"] = (raw.get("te1") or 0) + (raw.get("te2") or 0)

    return metrics

# Build JSON payload for Grafana Cloud Graphite
def build_graphite_payload(metrics, timestamp):
    payload = []

    for key, value in metrics.items():
        try:
            value = float(value)
        except (TypeError, ValueError):
            dbg(f"Skipping non-numeric metric {key}={value}")
            continue

        payload.append({
            "name": f"{metric_prefix}.{key}",
            "interval": interval,
            "value": value,
            "time": timestamp
        })

    return payload

# Send metrics to Grafana Cloud
def send_to_graphite(metrics):
    timestamp = int(time.time())
    body = build_graphite_payload(metrics, timestamp)

    if not body:
        dbg("No metrics to send (empty payload).")
        return

    dbg("Sending JSON payload to Grafana Cloud:")
    dbg(body)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_id}:{api_token}"
    }

    try:
        r = requests.post(
            graphite_url,
            json=body,
            headers=headers,
            timeout=10
        )
        dbg(f"Grafana response status: {r.status_code}")
        dbg(f"Grafana response text: {r.text}")
    except Exception as e:
        dbg(f"Failed to send to Grafana: {e}")

# Main loop
while True:
    dbg("Starting new cycle...")

    payload = fetch_data()

    if payload and "data" in payload:
        metrics = map_metrics(payload["data"])
        send_to_graphite(metrics)
    else:
        dbg("No valid data received from device")

    dbg(f"Sleeping {interval} seconds...")
    time.sleep(interval)