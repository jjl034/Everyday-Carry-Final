# mqtt_listener.py
import paho.mqtt.client as mqtt
import json
import os
from datetime import datetime

# ============================
# Settings
# ============================
MQTT_BROKER = "localhost"      # Kivy app + broker on same Pi
MQTT_PORT = 1883
MQTT_TOPIC = "edc/devices"     # ESP32 publishes BLE detections

ITEMS_FILE = "items.json"


# ============================
# Load / Save Items
# ============================
def load_items():
    if not os.path.exists(ITEMS_FILE):
        return {}

    try:
        with open(ITEMS_FILE, "r") as f:
            items = json.load(f)
            return {item["mac"].lower(): item for item in items}
    except:
        return {}


def save_items(items_dict):
    # Convert dict back to list for JSON storage
    items_list = list(items_dict.values())
    with open(ITEMS_FILE, "w") as f:
        json.dump(items_list, f, indent=2)


# ============================
# MQTT Callbacks
# ============================
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code", rc)
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except:
        print("Invalid JSON received")
        return

    mac = payload.get("mac", "").lower()
    location = payload.get("location", "Unknown")
    rssi = payload.get("rssi", None)

    if not mac:
        return

    print(f"Seen {mac} at {location} (RSSI {rssi})")

    items = load_items()
    updated = False

    if mac in items:
        # Update existing item
        items[mac]["last_seen_location"] = location
        items[mac]["last_seen_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        items[mac]["rssi"] = rssi
        updated = True
        print(f"Updated {items[mac]['name']}")
    else:
        # Unknown MAC detected — ignore or auto-add?
        print(f"Unknown MAC detected: {mac} (ignored)")
        return

    if updated:
        save_items(items)


# ============================
# Main
# ============================
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)

print("Listening for BLE devices on topic:", MQTT_TOPIC)
client.loop_forever()