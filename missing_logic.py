# missing_logic.py
import json
import os
from datetime import datetime

ITEMS_FILE = "items.json"


# ============================
# Load Items
# ============================
def load_items():
    """Load items from items.json and ensure consistent structure."""
    if not os.path.exists(ITEMS_FILE):
        return []

    try:
        with open(ITEMS_FILE, "r") as f:
            items = json.load(f)
    except json.JSONDecodeError:
        return []

    # Normalize structure
    for item in items:
        item.setdefault("name", "Unnamed")
        item.setdefault("mac", "unknown")
        item.setdefault("last_seen_location", "Unknown")
        item.setdefault("last_seen_time", "Never")

    return items


# ============================
# Save Items
# ============================
def save_items(items_list):
    """Save items back to items.json."""
    with open(ITEMS_FILE, "w") as f:
        json.dump(items_list, f, indent=2)


# ============================
# Quick Lookup Dictionary
# ============================
def items_dict():
    """Return items keyed by MAC address (lowercase)."""
    return {item["mac"].lower(): item for item in load_items()}


# ============================
# Update a Single Item
# ============================
def update_item(mac, last_seen_location=None, last_seen_time=None):
    """
    Update a single item by MAC address.
    Returns True if updated, False if item not found.
    """
    mac = mac.lower()
    items = load_items()
    updated = False

    for item in items:
        if item["mac"].lower() == mac:
            if last_seen_location is not None:
                item["last_seen_location"] = last_seen_location
            if last_seen_time is not None:
                item["last_seen_time"] = last_seen_time
            updated = True
            break

    if updated:
        save_items(items)

    return updated


# ============================
# Determine Missing Items
# ============================
def get_missing_items(seen_macs):
    """
    Given a set of seen MAC addresses, return a list of missing items.
    """
    seen_macs = {m.lower() for m in seen_macs}
    items = load_items()
    missing = []

    for item in items:
        mac = item["mac"].lower()
        if mac and mac not in seen_macs:
            missing.append(item)

    return missing