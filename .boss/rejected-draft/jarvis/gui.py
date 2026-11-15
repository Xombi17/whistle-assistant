import os
import threading
import queue
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
from dateparser import parse
from jarvis.core import Assistant

class JarvisGUI:
    def __init__(self, root, assistant):
        self.root = root
        self.assistant = assistant
        self.transcript = tk.Text(root, height=20, width=80)
        self.transcript.pack()
        self.entry = tk.Entry(root, width=80)
        self.entry.pack()
        self.send_button = tk.Button(root, text="Send", command=self.send_message)
        self.send_button.pack()
        self.record_button = tk.Button(root, text="Record", command=self.start_record)
        self.record_button.pack()
        self.record_button.config(state=tk.DISABLED)
        self.record_thread = None
        self.record_queue = queue.Queue()
        self.reminder_editor = ReminderEditor(root, self.assistant)
        self.reminder_editor.pack()

    def send_message(self):
        text = self.entry.get()
        self.entry.delete(0, tk.END)
        calls = self.assistant.propose(text)
        if calls:
            for call in calls:
                self.assistant.execute(call)
                self.transcript.insert(tk.END, f"Executed: {call}\n")
        else:
            self.transcript.insert(tk.END, "No valid calls proposed.\n")

    def start_record(self):
        self.record_button.config(state=tk.DISABLED)
        self.record_thread = threading.Thread(target=self.record_audio)
        self.record_thread.start()

    def record_audio(self):
        temp_file = os.path.join(os.getcwd(), "temp.wav")
        subprocess.Popen(['arecord', '-q', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', temp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.record_queue.put(temp_file)
        self.record_thread.join()
        self.record_button.config(state=tk.NORMAL)
        self.transcript.insert(tk.END, "Recording stopped.\n")
        self.transcript.insert(tk.END, "Transcribing...\n")
        self.transcript.see(tk.END)
        self.root.after(1000, self.transcribe_audio)

    def transcribe_audio(self):
        if not self.record_queue.empty():
            temp_file = self.record_queue.get()
            result = subprocess.run(['sox', temp_file, '-t', 'wav', '-e', 'signed-integer', '-b', '16', '-r', '16000', '-c', '1', '-'], capture_output=True, text=True)
            text = result.stdout.strip()
            self.transcript.insert(tk.END, f"Transcription: {text}\n")
            self.entry.insert(0, text)
            self.transcript.see(tk.END)
            self.root.after(1000, self.transcribe_audio)

class ReminderEditor:
    def __init__(self, root, assistant):
        self.root = root
        self.assistant = assistant
        self.frame = tk.Frame(root)
        self.frame.pack()
        self.title_label = tk.Label(self.frame, text="Title:")
        self.title_label.pack()
        self.title_entry = tk.Entry(self.frame, width=80)
        self.title_entry.pack()
        self.when_label = tk.Label(self.frame, text="When:")
        self.when_label.pack()
        self.when_entry = tk.Entry(self.frame, width=80)
        self.when_entry.pack()
        self.create_button = tk.Button(self.frame, text="Create Reminder", command=self.create_reminder)
        self.create_button.pack()
        self.list_button = tk.Button(self.frame, text="List Reminders", command=self.list_reminders)
        self.list_button.pack()
        self.modify_button = tk.Button(self.frame, text="Modify Reminder", command=self.modify_reminder)
        self.modify_button.pack()
        self.cancel_button = tk.Button(self.frame, text="Cancel Reminder", command=self.cancel_reminder)
        self.cancel_button.pack()

    def create_reminder(self):
        title = self.title_entry.get()
        when = self.when_entry.get()
        when = parse(when)
        if when is not None and when > datetime.now():
            self.assistant.create_reminder(title, when)
            messagebox.showinfo("Reminder Created", f"Reminder created: {title} at {when}")
        else:
            messagebox.showerror("Invalid Reminder", "Invalid date for reminder.")

    def list_reminders(self):
        self.assistant.list_reminders()

    def modify_reminder(self):
        id = int(self.title_entry.get())
        title = self.when_entry.get()
        when = self.when_entry.get()
        when = parse(when)
        if when is not None and when > datetime.now():
            self.assistant.modify_reminder(id, title, when)
            messagebox.showinfo("Reminder Modified", f"Reminder modified: {id} to {title} at {when}")
        else:
            messagebox.showerror("Invalid Reminder", "Invalid date for reminder.")

    def cancel_reminder(self):
        id = int(self.title_entry.get())
        self.assistant.cancel_reminder(id)
        messagebox.showinfo("Reminder Cancelled", f"Reminder cancelled: {id}")
