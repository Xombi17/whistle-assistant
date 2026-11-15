"""JARVIS / WhisperFlow desktop application: Settings, Dedicated Clipboard History, and Profile management."""

import datetime
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jarvis.formatter import CONFIG_FILE, load_config, save_config
from jarvis.history import clear_all_history, delete_history_item, list_history


class JarvisApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JARVIS · Voice Writing & Assistant")
        self.root.geometry("780x620")
        self.root.minsize(680, 520)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Color palette (Modern Slate Dark)
        self.bg_dark = "#0f172a"
        self.card_bg = "#1e293b"
        self.accent_blue = "#38bdf8"
        self.accent_purple = "#a855f7"
        self.text_primary = "#f8fafc"
        self.text_secondary = "#94a3b8"

        self.root.configure(bg=self.bg_dark)
        self.config_data = load_config()

        self.setup_ui()
        self.load_history_items()

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg=self.card_bg, height=64)
        header.pack(fill="x", side="top")

        title_lbl = tk.Label(
            header,
            text="JARVIS  ·  WHISPERFLOW DESKTOP",
            font=("Sans", 13, "bold"),
            bg=self.card_bg,
            fg=self.text_primary,
        )
        title_lbl.pack(side="left", padx=20, pady=16)

        test_btn = tk.Button(
            header,
            text="🎙 Open Voice HUD",
            font=("Sans", 10, "bold"),
            bg=self.accent_blue,
            fg="#0f172a",
            relief="flat",
            padx=12,
            pady=4,
            command=self.launch_hud,
        )
        test_btn.pack(side="right", padx=20, pady=14)

        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=16)

        # Tab 1: Clipboard History
        self.history_frame = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.history_frame, text="  📋 Clipboard History  ")
        self.setup_history_tab()

        # Tab 2: Settings & API Keys
        self.settings_frame = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.settings_frame, text="  ⚙️ Settings & API Keys  ")
        self.setup_settings_tab()

        # Tab 3: About & Shortcuts
        self.shortcuts_frame = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.shortcuts_frame, text="  ⌨️ Shortcuts & Integration  ")
        self.setup_shortcuts_tab()

    def setup_history_tab(self):
        top_bar = tk.Frame(self.history_frame, bg=self.bg_dark)
        top_bar.pack(fill="x", pady=(8, 12))

        search_lbl = tk.Label(top_bar, text="Search History:", bg=self.bg_dark, fg=self.text_secondary, font=("Sans", 10))
        search_lbl.pack(side="left", padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_history_items())
        search_ent = tk.Entry(
            top_bar,
            textvariable=self.search_var,
            bg=self.card_bg,
            fg=self.text_primary,
            insertbackground=self.accent_blue,
            font=("Sans", 10),
            width=32,
            relief="flat",
        )
        search_ent.pack(side="left", ipady=4)

        refresh_btn = tk.Button(
            top_bar,
            text="🔄 Refresh",
            bg=self.card_bg,
            fg=self.text_primary,
            relief="flat",
            command=self.load_history_items,
        )
        refresh_btn.pack(side="left", padx=8)

        clear_btn = tk.Button(
            top_bar,
            text="🗑 Clear All",
            bg=self.card_bg,
            fg="#f87171",
            relief="flat",
            command=self.confirm_clear_history,
        )
        clear_btn.pack(side="right")

        # Split pane: list on left/top, full text preview on right/bottom
        paned = tk.PanedWindow(self.history_frame, orient="vertical", bg=self.bg_dark, sashwidth=4)
        paned.pack(fill="both", expand=True)

        list_container = tk.Frame(paned, bg=self.card_bg)
        paned.add(list_container, minsize=180)

        # Treeview for items
        columns = ("id", "time", "mode", "text")
        self.tree = ttk.Treeview(list_container, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="#")
        self.tree.heading("time", text="Time")
        self.tree.heading("mode", text="Mode")
        self.tree.heading("text", text="Transcript Preview")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("time", width=130, anchor="center")
        self.tree.column("mode", width=90, anchor="center")
        self.tree.column("text", width=450, anchor="w")

        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_history_select)

        # Bottom text review pane
        preview_container = tk.Frame(paned, bg=self.card_bg)
        paned.add(preview_container, minsize=140)

        action_bar = tk.Frame(preview_container, bg=self.card_bg)
        action_bar.pack(fill="x", padx=12, pady=6)

        tk.Label(action_bar, text="Full Text & Formatting:", bg=self.card_bg, fg=self.text_secondary, font=("Sans", 9, "bold")).pack(side="left")

        self.copy_btn = tk.Button(
            action_bar,
            text="📋 Copy to Clipboard",
            font=("Sans", 9, "bold"),
            bg=self.accent_blue,
            fg="#0f172a",
            relief="flat",
            command=self.copy_selected_text,
        )
        self.copy_btn.pack(side="right")

        self.preview_text = tk.Text(
            preview_container,
            bg="#0b1120",
            fg=self.text_primary,
            insertbackground=self.accent_blue,
            font=("Monospace", 10),
            wrap="word",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.preview_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def setup_settings_tab(self):
        canvas = tk.Canvas(self.settings_frame, bg=self.bg_dark, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.settings_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.bg_dark)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Provider Section
        sec_provider = tk.LabelFrame(inner, text=" AI Formatting Provider ", bg=self.card_bg, fg=self.accent_blue, font=("Sans", 10, "bold"), padx=16, pady=14)
        sec_provider.pack(fill="x", pady=8)

        tk.Label(sec_provider, text="Select Formatter Engine:", bg=self.card_bg, fg=self.text_primary, font=("Sans", 10)).grid(row=0, column=0, sticky="w", pady=6)
        self.provider_var = tk.StringVar(value=self.config_data.get("provider", "groq"))
        provider_combo = ttk.Combobox(sec_provider, textvariable=self.provider_var, values=["groq", "ollama", "xai", "deterministic"], state="readonly", width=22)
        provider_combo.grid(row=0, column=1, sticky="w", padx=12, pady=6)

        # Groq Settings
        sec_groq = tk.LabelFrame(inner, text=" Groq Cloud Configuration (Free, Sub-second) ", bg=self.card_bg, fg=self.accent_blue, font=("Sans", 10, "bold"), padx=16, pady=14)
        sec_groq.pack(fill="x", pady=8)

        tk.Label(sec_groq, text="Groq API Key:", bg=self.card_bg, fg=self.text_primary).grid(row=0, column=0, sticky="w", pady=6)
        self.groq_key_var = tk.StringVar(value=self.config_data.get("groq_api_key", ""))
        self.groq_key_ent = tk.Entry(sec_groq, textvariable=self.groq_key_var, show="•", width=42, bg="#0f172a", fg=self.text_primary, insertbackground=self.accent_blue, relief="flat")
        self.groq_key_ent.grid(row=0, column=1, sticky="w", padx=12, pady=6, ipady=3)

        self.groq_show_var = tk.BooleanVar(value=False)
        chk_show = tk.Checkbutton(sec_groq, text="Show", variable=self.groq_show_var, bg=self.card_bg, fg=self.text_secondary, selectcolor=self.bg_dark, command=self.toggle_groq_visibility)
        chk_show.grid(row=0, column=2, padx=4)

        tk.Label(sec_groq, text="Groq Model:", bg=self.card_bg, fg=self.text_primary).grid(row=1, column=0, sticky="w", pady=6)
        self.groq_model_var = tk.StringVar(value=self.config_data.get("groq_model", "llama-3.3-70b-versatile"))
        groq_model_ent = tk.Entry(sec_groq, textvariable=self.groq_model_var, width=32, bg="#0f172a", fg=self.text_primary, insertbackground=self.accent_blue, relief="flat")
        groq_model_ent.grid(row=1, column=1, sticky="w", padx=12, pady=6, ipady=3)

        # xAI / Grok Settings
        sec_xai = tk.LabelFrame(inner, text=" xAI / Grok Configuration ", bg=self.card_bg, fg=self.accent_blue, font=("Sans", 10, "bold"), padx=16, pady=14)
        sec_xai.pack(fill="x", pady=8)

        tk.Label(sec_xai, text="xAI (Grok) API Key:", bg=self.card_bg, fg=self.text_primary).grid(row=0, column=0, sticky="w", pady=6)
        self.xai_key_var = tk.StringVar(value=self.config_data.get("xai_api_key", ""))
        xai_key_ent = tk.Entry(sec_xai, textvariable=self.xai_key_var, show="•", width=42, bg="#0f172a", fg=self.text_primary, insertbackground=self.accent_blue, relief="flat")
        xai_key_ent.grid(row=0, column=1, sticky="w", padx=12, pady=6, ipady=3)

        # Ollama Local Settings
        sec_ollama = tk.LabelFrame(inner, text=" Local Ollama Configuration ", bg=self.card_bg, fg=self.accent_blue, font=("Sans", 10, "bold"), padx=16, pady=14)
        sec_ollama.pack(fill="x", pady=8)

        tk.Label(sec_ollama, text="Ollama URL:", bg=self.card_bg, fg=self.text_primary).grid(row=0, column=0, sticky="w", pady=6)
        self.ollama_url_var = tk.StringVar(value=self.config_data.get("ollama_url", "http://localhost:11434"))
        ollama_url_ent = tk.Entry(sec_ollama, textvariable=self.ollama_url_var, width=32, bg="#0f172a", fg=self.text_primary, insertbackground=self.accent_blue, relief="flat")
        ollama_url_ent.grid(row=0, column=1, sticky="w", padx=12, pady=6, ipady=3)

        tk.Label(sec_ollama, text="Ollama Model:", bg=self.card_bg, fg=self.text_primary).grid(row=1, column=0, sticky="w", pady=6)
        self.ollama_model_var = tk.StringVar(value=self.config_data.get("ollama_model", "qwen2.5-coder:7b"))
        ollama_model_ent = tk.Entry(sec_ollama, textvariable=self.ollama_model_var, width=32, bg="#0f172a", fg=self.text_primary, insertbackground=self.accent_blue, relief="flat")
        ollama_model_ent.grid(row=1, column=1, sticky="w", padx=12, pady=6, ipady=3)

        # Save Button
        save_btn = tk.Button(
            inner,
            text="💾 Save Settings",
            font=("Sans", 11, "bold"),
            bg=self.accent_blue,
            fg="#0f172a",
            relief="flat",
            padx=24,
            pady=8,
            command=self.save_settings,
        )
        save_btn.pack(pady=16)

    def setup_shortcuts_tab(self):
        box = tk.Frame(self.shortcuts_frame, bg=self.card_bg, padx=20, pady=20)
        box.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(box, text="Keyboard Shortcuts & Usage Guide", font=("Sans", 12, "bold"), bg=self.card_bg, fg=self.accent_blue).pack(anchor="w", pady=(0, 12))

        guide_text = (
            "1. Hold-to-Talk Dictation (WhisperFlow Mode):\n"
            "   • Press and hold <Super><Shift>J while speaking.\n"
            "   • Release the keys to finish. Text is formatted by AI and typed directly into your active window.\n"
            "   • Transcripts are also saved to your Clipboard History automatically.\n\n"
            "2. Mode Switching:\n"
            "   • Inside the HUD: Press 'Tab' or click '⇄ Switch' to flip between Dictation and JARVIS Commands.\n"
            "   • Command Mode: Speak commands like 'open chrome', 'launch files', or 'open terminal'.\n\n"
            "3. Config Location:\n"
            f"   • Settings are saved to: {CONFIG_FILE}\n"
            "   • History database: ~/.local/share/jarvis/history.sqlite3\n\n"
            "4. Free Groq API Key:\n"
            "   • You can generate a free, instantaneous Groq key at: https://console.groq.com/keys"
        )

        lbl = tk.Label(box, text=guide_text, justify="left", font=("Sans", 10), bg=self.card_bg, fg=self.text_primary)
        lbl.pack(anchor="w", pady=4)

    def toggle_groq_visibility(self):
        self.groq_key_ent.configure(show="" if self.groq_show_var.get() else "•")

    def save_settings(self):
        new_config = {
            "provider": self.provider_var.get(),
            "groq_api_key": self.groq_key_var.get().strip(),
            "groq_model": self.groq_model_var.get().strip(),
            "xai_api_key": self.xai_key_var.get().strip(),
            "ollama_url": self.ollama_url_var.get().strip(),
            "ollama_model": self.ollama_model_var.get().strip(),
        }
        save_config(new_config)
        messagebox.showinfo("JARVIS Settings", "Settings successfully saved!")

    def load_history_items(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        items = list_history(limit=100, query=self.search_var.get())
        for row in items:
            dt = datetime.datetime.fromtimestamp(row["timestamp"]).strftime("%b %d, %H:%M:%S")
            mode = "Dictate" if row["mode"] == "transcribe" else "Command"
            preview = row["formatted_text"].replace("\n", " ")[:60]
            self.tree.insert("", "end", iid=str(row["id"]), values=(row["id"], dt, mode, preview))

    def on_history_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = int(selected[0])
        items = list_history(limit=1, query="")
        for it in list_history(limit=200):
            if it["id"] == item_id:
                self.preview_text.delete("1.0", "end")
                self.preview_text.insert("1.0", it["formatted_text"])
                break

    def copy_selected_text(self):
        text = self.preview_text.get("1.0", "end").strip()
        if text:
            subprocess.run(["wl-copy", "-n", "--", text], check=False)
            messagebox.showinfo("Clipboard", "Copied to clipboard!")

    def confirm_clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all clipboard history?"):
            clear_all_history()
            self.preview_text.delete("1.0", "end")
            self.load_history_items()

    def launch_hud(self):
        script_path = str(Path(__file__).resolve().parent / "hotkey.py")
        subprocess.Popen([sys.executable, script_path])


def main():
    root = tk.Tk()
    app = JarvisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
