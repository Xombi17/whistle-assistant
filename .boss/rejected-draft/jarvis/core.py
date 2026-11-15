import os
import json
import sqlite3
import subprocess
import threading
import queue
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from dateparser import parse
from cactus_compute import Model

class Assistant:
    def __init__(self, db_path=None, model=None, launch=None, speak=None):
        self.db_path = db_path or os.path.expanduser("~/.local/share/jarvis/jarvis.sqlite3")
        self.model = model or Model()
        self.launch = launch or self.default_launch
        self.speak = speak or self.default_speak
        self.reminders = {}
        self.init_db()

    def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS reminders
                     (id INTEGER PRIMARY KEY, title TEXT, when TEXT, delivered BOOLEAN)''')
        conn.commit()
        conn.close()

    def propose(self, text):
        response = self.model.complete(text)
        calls = response.get('function_calls', [])
        for call in calls:
            if not self.validate_call(call):
                messagebox.showerror("Invalid Call", f"Call {call} is invalid or suppressed.")
                return
        return calls

    def validate_call(self, call):
        if call['name'] not in ['open_app', 'find_files', 'open_file', 'create_reminder', 'list_reminders', 'modify_reminder', 'cancel_reminder']:
            messagebox.showerror("Invalid Call", f"Call {call['name']} is not registered.")
            return False
        if call['name'] == 'create_reminder':
            when = parse(call['arguments']['when'])
            if when is None or when < datetime.now():
                messagebox.showerror("Invalid Call", f"Invalid date for reminder: {call['arguments']['when']}")
                return False
        return True

    def execute(self, call):
        if call['name'] == 'open_app':
            self.launch(call['arguments']['name'])
        elif call['name'] == 'open_file':
            self.open_file(call['arguments']['path'])
        elif call['name'] == 'create_reminder':
            self.create_reminder(call['arguments']['title'], call['arguments']['when'])
        elif call['name'] == 'list_reminders':
            self.list_reminders()
        elif call['name'] == 'modify_reminder':
            self.modify_reminder(call['arguments']['id'], call['arguments'].get('title'), call['arguments'].get('when'))
        elif call['name'] == 'cancel_reminder':
            self.cancel_reminder(call['arguments']['id'])

    def default_launch(self, name):
        desktop_path = self.find_desktop_path(name)
        if desktop_path:
            subprocess.Popen(['gio', 'launch', desktop_path])

    def find_desktop_path(self, name):
        desktop_dirs = os.environ.get('XDG_DESKTOP_DIR', os.path.expanduser("~/.local/share/applications")).split(':')
        for dir in desktop_dirs:
            for file in os.listdir(dir):
                if file.endswith('.desktop'):
                    with open(os.path.join(dir, file), 'r') as f:
                        config = configparser.ConfigParser()
                        config.read_file(f)
                        if config['Desktop']['Name'] == name and not config['Desktop'].getboolean('NoDisplay') and not config['Desktop'].getboolean('Hidden'):
                            return os.path.join(dir, file)
        return None

    def open_file(self, path):
        if os.path.isfile(path) and not os.path.islink(path):
            subprocess.Popen(['xdg-open', path])

    def create_reminder(self, title, when):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO reminders (title, when, delivered) VALUES (?, ?, ?)", (title, when, False))
        conn.commit()
        conn.close()

    def list_reminders(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, title, when, delivered FROM reminders")
        reminders = c.fetchall()
        conn.close()
        for reminder in reminders:
            print(reminder)

    def modify_reminder(self, id, title=None, when=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if title:
            c.execute("UPDATE reminders SET title = ? WHERE id = ?", (title, id))
        if when:
            when = parse(when)
            if when is not None and when > datetime.now():
                c.execute("UPDATE reminders SET when = ? WHERE id = ?", (when, id))
        conn.commit()
        conn.close()

    def cancel_reminder(self, id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM reminders WHERE id = ?", (id,))
        conn.commit()
        conn.close()

    def due(self):
        now = datetime.now()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, title, when FROM reminders WHERE when <= ? AND delivered = ?", (now, False))
        reminders = c.fetchall()
        conn.close()
        for reminder in reminders:
            self.speak(f"Reminder: {reminder[1]} at {reminder[2]}")
            self.mark_delivered(reminder[0])

    def mark_delivered(self, id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE reminders SET delivered = ? WHERE id = ?", (True, id))
        conn.commit()
        conn.close()

    def default_speak(self, text):
        subprocess.Popen(['espeak-ng', text])
