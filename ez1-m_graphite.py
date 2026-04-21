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
disable_send = False

# Debug helper
def dbg(msg):
    if debug:
        print(msg)

# Fetch all data from the inverter
def fetch_all():
    results = {}
    endpoints = {
        "output": "/getOutputDataDetail",
        "device":  "/getDeviceInfo",
        "alarm":   "/getAlarm",
    }
    for key, path in endpoints.items():
        try:
            dbg(f"Fetching {path}...")
            r = requests.get("http://" + ez1m_ip + ":8050" + path, timeout=5)
            dbg(f"  HTTP status: {r.status_code}")
            r.raise_for_status()
            data = r.json()
            dbg(f"  JSON: {data}")
            results[key] = data.get("data")
        except Exception as e:
            dbg(f"  Failed to fetch {path}: {e}")
            results[key] = None
    return results

# Map all raw data → metrics dict
def map_all_metrics(raw):
    metrics = {}

    # Output data
    output = raw.get("output") or {}
    metrics["total_power_p1"]         = output.get("p1")
    metrics["total_power_p2"]         = output.get("p2")
    metrics["today_production_p1"]    = output.get("e1")
    metrics["today_production_p2"]    = output.get("e2")
    metrics["lifetime_production_p1"] = output.get("te1")
    metrics["lifetime_production_p2"] = output.get("te2")
    metrics["voltage_p1"]             = output.get("v1")
    metrics["voltage_p2"]             = output.get("v2")
    metrics["current_p1"]             = output.get("c1")
    metrics["current_p2"]             = output.get("c2")
    metrics["grid_voltage"]           = output.get("gv")
    metrics["grid_frequency"]         = output.get("gf")
    metrics["inverter_temperature"]   = output.get("t")
    metrics["total_power"]            = (output.get("p1") or 0) + (output.get("p2") or 0)
    metrics["today_production"]       = (output.get("e1") or 0) + (output.get("e2") or 0)
    metrics["lifetime_production"]    = (output.get("te1") or 0) + (output.get("te2") or 0)

    # Device info
    device = raw.get("device") or {}
    metrics["inverter_min_power"] = device.get("minPower")
    metrics["inverter_max_power"] = device.get("maxPower")
    dbg(f"Device ID={device.get('deviceId', 'unknown')} | Firmware={device.get('devVer', 'unknown')}")

    # Alarm status (0=normal, 1=alarm)
    alarm = raw.get("alarm") or {}
    metrics["alarm_off_grid"]         = alarm.get("og")    # 0: normal, 1: alarm
    metrics["alarm_output_fault"]     = alarm.get("oe")    # 0: normal, 1: alarm
    metrics["alarm_short_circuit_p1"] = alarm.get("isce1") # 0: normal, 1: alarm
    metrics["alarm_short_circuit_p2"] = alarm.get("isce2") # 0: normal, 1: alarm

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

# Send metrics to Grafana Cloud Graphite
def send_to_graphite(metrics):
    timestamp = int(time.time())
    body = build_graphite_payload(metrics, timestamp)

    if not body:
        dbg("No metrics to send (empty payload).")
        return

    dbg("Sending JSON payload to Grafana Cloud Graphite:")
    dbg(body)

    if disable_send:
        dbg("Disable send mode enabled — skipping send to Graphite.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_id}:{api_token}"
    }

    try:
        r = requests.post(graphite_url, json=body, headers=headers, timeout=10)
        dbg(f"Graphite response status: {r.status_code}")
        dbg(f"Graphite response text: {r.text}")
    except Exception as e:
        dbg(f"Failed to send to Graphite: {e}")

# Main loop
while True:
    dbg("Starting new cycle...")

    raw = fetch_all()

    if raw.get("output") is None:
        dbg("No valid output data received from device")
    if raw.get("device") is None:
        dbg("No valid device info received from device")
    if raw.get("alarm") is None:
        dbg("No valid alarm data received from device")

    if any(v is not None for v in raw.values()):
        metrics = map_all_metrics(raw)
        send_to_graphite(metrics)
    else:
        dbg("No data received from any endpoint, skipping send")

    dbg(f"Sleeping {interval} seconds...")
    time.sleep(interval)
