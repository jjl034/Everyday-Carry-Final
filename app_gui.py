# app_gui.py
from datetime import datetime
import json
import os
import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.core.window import Window

import paho.mqtt.client as mqtt
from threading import Thread

kivy.require("2.3.1")

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
    items_list = list(items_dict.values())
    with open(ITEMS_FILE, "w") as f:
        json.dump(items_list, f, indent=2)


# ============================
# Popup for Missing Items
# ============================
def show_missing_popup(item_name, last_seen):
    content = BoxLayout(orientation="vertical", padding=5)
    content.add_widget(Label(text=f"Missing: {item_name}\nLast seen: {last_seen}", font_size=14))

    popup = Popup(
        title="Missing Item",
        content=content,
        size_hint=(None, None),
        size=(260, 120),
        auto_dismiss=True,
        separator_height=0
    )

    popup.pos = (Window.width - 280, Window.height - 150)
    popup.open()

    Clock.schedule_once(lambda dt: popup.dismiss(), 4)


# ============================
# Main Screen
# ============================
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.items = load_items()

        self.layout = GridLayout(cols=1, spacing=5, padding=10)
        self.add_widget(self.layout)

        # Create Add Item button once
        self.add_btn = Button(text="Add Item", size_hint_y=None, height=40)
        self.add_btn.bind(on_release=self.go_to_add_item)

        self.refresh_dashboard()

    def go_to_add_item(self, instance):
        self.manager.current = "add_item"

    def refresh_dashboard(self):
        self.layout.clear_widgets()

        for mac, item in self.items.items():
            name = item.get("name", "Unnamed")
            loc = item.get("last_seen_location", "Unknown")
            ts = item.get("last_seen_time", "Never")

            self.layout.add_widget(
                Label(text=f"{name} — Last seen: {ts} at {loc}")
            )

        self.layout.add_widget(self.add_btn)

    def update_item(self, mac, location):
        mac = mac.lower()
        if mac not in self.items:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.items[mac]["last_seen_location"] = location
        self.items[mac]["last_seen_time"] = timestamp

        save_items(self.items)
        self.refresh_dashboard()


# ============================
# Add Item Screen
# ============================
class AddItemScreen(Screen):
    def __init__(self, main_screen, **kwargs):
        super().__init__(**kwargs)
        self.main_screen = main_screen

        layout = BoxLayout(orientation="vertical", padding=10, spacing=5)

        self.name_input = TextInput(hint_text="Item Name", multiline=False, size_hint_y=None, height=40)
        layout.add_widget(self.name_input)

        self.mac_input = TextInput(hint_text="MAC Address", multiline=False, size_hint_y=None, height=40)
        layout.add_widget(self.mac_input)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=5)
        save_btn = Button(text="Save")
        save_btn.bind(on_release=self.save_item)

        back_btn = Button(text="Back")
        back_btn.bind(on_release=self.go_back)

        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(back_btn)

        layout.add_widget(btn_layout)
        self.add_widget(layout)

    def save_item(self, instance):
        name = self.name_input.text.strip()
        mac = self.mac_input.text.strip().lower()

        if not name or not mac:
            return

        self.main_screen.items[mac] = {
            "name": name,
            "mac": mac,
            "last_seen_location": "Unknown",
            "last_seen_time": "Never"
        }

        save_items(self.main_screen.items)
        self.main_screen.refresh_dashboard()
        self.go_back(instance)

    def go_back(self, instance):
        self.manager.current = "main"


# ============================
# MQTT Handling
# ============================
class MQTTHandler:
    def __init__(self, main_screen):
        self.main_screen = main_screen
        self.client = mqtt.Client()

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect("localhost", 1883, 60)
        thread = Thread(target=self.client.loop_forever, daemon=True)
        thread.start()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT broker")
        client.subscribe("edc/devices")
        client.subscribe("edc/missing")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except:
            print("Invalid MQTT JSON")
            return

        # BLE detection update
        if msg.topic == "edc/devices":
            mac = data.get("mac", "").lower()
            location = data.get("location", "Unknown")

            Clock.schedule_once(lambda dt: self.main_screen.update_item(mac, location))

        # Missing item alert
        if msg.topic == "edc/missing":
            name = data.get("name", "Unknown")
            last_seen = data.get("last_seen", "Unknown")

            Clock.schedule_once(lambda dt: show_missing_popup(name, last_seen))


# ============================
# App
# ============================
class EverydayCarryApp(App):
    def build(self):
        sm = ScreenManager()

        main_screen = MainScreen(name="main")
        add_screen = AddItemScreen(main_screen, name="add_item")

        sm.add_widget(main_screen)
        sm.add_widget(add_screen)

        # Start MQTT listener
        mqtt_handler = MQTTHandler(main_screen)
        mqtt_handler.start()

        return sm


if __name__ == "__main__":
    EverydayCarryApp().run()