# person_detector.py
import cv2
import json
import time
import paho.mqtt.client as mqtt
from pathlib import Path
from datetime import datetime

# ============================
# MQTT Setup
# ============================
MQTT_BROKER = "localhost"
MQTT_TOPIC = "edc/missing"

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# ============================
# Items File
# ============================
DATA_FILE = Path(__file__).parent / "items.json"


def load_items():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def get_missing_items():
    """
    Determine which items are missing based on last_seen_location.
    If last_seen_location != 'Home', we consider it missing.
    """
    items = load_items()
    missing = []

    for item in items:
        loc = item.get("last_seen_location", "Unknown")
        if loc != "Home":  # You can change this rule later
            missing.append({
                "name": item.get("name", "Unknown"),
                "mac": item.get("mac", "unknown"),
                "last_seen": item.get("last_seen_time", "Never")
            })

    return missing


# ============================
# OpenCV Person Detector
# ============================
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

print("Starting person detector...")

person_detected_last_frame = False

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    frame_resized = cv2.resize(frame, (640, 480))

    # Detect people
    rects, weights = hog.detectMultiScale(
        frame_resized,
        winStride=(8, 8),
        padding=(16, 16),
        scale=1.05
    )

    person_detected = len(rects) > 0

    # Draw rectangles (optional)
    for (x, y, w, h) in rects:
        cv2.rectangle(frame_resized, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Trigger when person leaves
    if person_detected_last_frame and not person_detected:
        print("Person left — checking missing items...")

        missing_items = get_missing_items()

        if missing_items:
            print("Missing items detected:", [m["name"] for m in missing_items])
            mqtt_client.publish(MQTT_TOPIC, json.dumps(missing_items))

    person_detected_last_frame = person_detected

    # Show camera feed (optional)
    cv2.imshow("Person Detector", frame_resized)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()