"""Whistle Assistant — Native Linux Desktop Hub modeled after Wispr Flow.
Ambient, high-fidelity voice dictation, smart technical WhisperFlow formatting,
custom dictionary, and personal writing styles.
"""

import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add project root to sys.path
REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from jarvis.formatter import load_config, polish_transcript, save_config
from jarvis.history import clear_all_history, delete_history_item, list_history, save_history_item
from jarvis.server import get_active_audio_device

CONFIG_DIR = Path.home() / ".config" / "jarvis"
DICT_FILE = CONFIG_DIR / "dictionary.json"

DEFAULT_DICTIONARY = [
    {"from": "crawl", "to": "Groq"},
    {"from": "allama", "to": "Ollama"},
    {"from": "deep sick", "to": "DeepSeek"},
    {"from": "whisper flow", "to": "WhisperFlow"},
    {"from": "pipe wire", "to": "PipeWire"},
    {"from": "wire plumber", "to": "WirePlumber"},
    {"from": "way land", "to": "Wayland"},
    {"from": "pie torch", "to": "PyTorch"},
]


def load_dictionary():
    if DICT_FILE.is_file():
        try:
            return json.loads(DICT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return list(DEFAULT_DICTIONARY)


def save_dictionary(words):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DICT_FILE.write_text(json.dumps(words, indent=2), encoding="utf-8")


def clean_mic_name(name: str) -> str:
    if not name:
        return "Default Microphone"
    name = name.split(".")[0].strip()
    if "Core Ultra" in name:
        return "Core Ultra Mic"
    if "Built-in" in name or "Internal" in name:
        return "Internal Mic"
    if "USB" in name:
        return "USB Microphone"
    if len(name) > 22:
        return name[:20] + "…"
    return name


APP_CSS = b"""
/* Main Hub Architecture */
window.whistle-hub {
    background-color: #121316;
    color: #e4e4e7;
}

/* Sidebar Styling */
.hub-sidebar {
    background-color: #16171b;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    padding: 12px;
}

.brand-label {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.2px;
    color: #f4f4f5;
}

.brand-version {
    font-size: 10px;
    font-weight: 600;
    color: #a1a1aa;
    background: rgba(255, 255, 255, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
}

.nav-item {
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 3px;
    font-size: 13px;
    font-weight: 500;
    color: #a1a1aa;
    transition: all 120ms ease;
    border: none;
    background: transparent;
}
.nav-item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #f4f4f5;
}
.nav-item.active {
    background: rgba(255, 255, 255, 0.09);
    color: #ffffff;
    font-weight: 600;
}

/* Status capsule in sidebar footer */
.sidebar-footer {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 10px 12px;
}
.sidebar-footer label {
    font-size: 11px;
    color: #71717a;
}
.sidebar-footer .mic-name {
    font-weight: 600;
    color: #d4d4d8;
}

/* Content Area */
.hub-content {
    background-color: #121316;
}

/* Stats Pill Bar */
.stats-banner {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 12px;
    color: #71717a;
}
.stats-banner b {
    color: #e4e4e7;
}

/* Dictation Cards (Wispr Flow style) */
.dictation-card {
    background: #18191e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 150ms ease;
}
.dictation-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
}

.dictation-time {
    font-size: 11px;
    font-weight: 600;
    color: #71717a;
}

.dictation-body {
    font-size: 13.5px;
    line-height: 1.55;
    color: #f4f4f5;
    margin-top: 6px;
    margin-bottom: 8px;
}

.dictation-meta {
    font-size: 11px;
    color: #71717a;
}

/* Action button subtle */
.btn-icon-subtle {
    border-radius: 6px;
    padding: 4px;
    min-height: 28px;
    min-width: 28px;
    color: #a1a1aa;
}
.btn-icon-subtle:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #f4f4f5;
}

/* Quick Try / Test Bar at bottom of Dictations */
.try-bar {
    background: #18191e;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 6px 10px;
    margin-top: 12px;
}
.try-entry {
    background: transparent;
    border: none;
    box-shadow: none;
    font-size: 13px;
    color: #f4f4f5;
}
.try-mic-btn {
    border-radius: 8px;
    min-width: 32px;
    min-height: 32px;
    padding: 4px;
    background: rgba(255, 255, 255, 0.08);
    color: #e4e4e7;
}
.try-mic-btn:hover {
    background: rgba(255, 255, 255, 0.14);
}
.try-mic-btn.recording {
    background: #ef4444;
    color: white;
}

/* Dictionary & Style Cards */
.clean-card {
    background: #18191e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 10px;
}

.style-card {
    background: #18191e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    transition: all 150ms ease;
}
.style-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
}
.style-card.selected {
    border-color: #3b82f6;
    background: rgba(59, 130, 246, 0.06);
}
"""


class WhistleWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Whistle")
        self.set_default_size(860, 620)
        self.add_css_class("whistle-hub")

        self.config = load_config()
        self.dictionary = load_dictionary()
        self.is_recording = False
        self.active_style = self.config.get("style", "code")

        self._build_ui()
        self._refresh_history()

    def _build_ui(self):
        # Master Navigation Split View
        self.split_view = Adw.NavigationSplitView()
        self.set_content(self.split_view)

        # 1. SIDEBAR
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.add_css_class("hub-sidebar")
        sidebar_box.set_size_request(210, -1)

        # Brand header
        brand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        brand_box.set_margin_top(8)
        brand_box.set_margin_bottom(20)
        brand_box.set_margin_start(4)

        icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
        icon.set_pixel_size(18)
        brand_box.append(icon)

        title = Gtk.Label(label="Whistle")
        title.add_css_class("brand-label")
        brand_box.append(title)

        ver = Gtk.Label(label="Hub")
        ver.add_css_class("brand-version")
        brand_box.append(ver)
        sidebar_box.append(brand_box)

        # Nav items
        self.nav_buttons = {}
        nav_items = [
            ("dictations", "📝  Dictations"),
            ("dictionary", "📖  Dictionary"),
            ("styles", "✨  Styles"),
            ("settings", "⚙️  Settings"),
        ]

        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for key, label in nav_items:
            btn = Gtk.Button()
            btn.add_css_class("nav-item")
            lbl = Gtk.Label(label=label, xalign=0)
            lbl.set_hexpand(True)
            btn.set_child(lbl)
            btn.connect("clicked", lambda b, k=key: self._switch_view(k))
            nav_box.append(btn)
            self.nav_buttons[key] = btn

        sidebar_box.append(nav_box)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar_box.append(spacer)

        # Sidebar Footer: Device status & Shortcut
        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        footer.add_css_class("sidebar-footer")

        mic_label = clean_mic_name(get_active_audio_device())
        mic_row = Gtk.Label(label=f"● {mic_label}", xalign=0)
        mic_row.add_css_class("mic-name")
        footer.append(mic_row)

        shortcut_row = Gtk.Label(label="Hold Super+Shift+J", xalign=0)
        footer.append(shortcut_row)

        sidebar_box.append(footer)

        sidebar_page = Adw.NavigationPage(child=sidebar_box, title="Whistle")
        self.split_view.set_sidebar(sidebar_page)

        # 2. CONTENT AREA
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(150)
        self.content_stack.add_css_class("hub-content")

        self._build_dictations_view()
        self._build_dictionary_view()
        self._build_styles_view()
        self._build_settings_view()

        content_page = Adw.NavigationPage(child=self.content_stack, title="Whistle Hub")
        self.split_view.set_content(content_page)

        # Select initial view
        self._switch_view("dictations")

    def _switch_view(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")
        self.content_stack.set_visible_child_name(key)

    # -------------------------------------------------------------
    # VIEW 1: DICTATIONS (Main Hub View)
    # -------------------------------------------------------------
    def _build_dictations_view(self):
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        title = Adw.WindowTitle(title="Dictations", subtitle="Voice transcripts and auto-pastes")
        header.set_title_widget(title)

        # Clear history button
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.add_css_class("flat")
        clear_btn.connect("clicked", self._on_clear_history)
        header.pack_end(clear_btn)
        main.append(header)

        # Body container
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_margin_start(24)
        body.set_margin_end(24)
        body.set_margin_top(8)
        body.set_margin_bottom(16)
        body.set_vexpand(True)

        # Search bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search transcripts...")
        self.search_entry.connect("search-changed", lambda e: self._refresh_history())
        body.append(self.search_entry)

        # Stats banner
        self.stats_label = Gtk.Label(
            label="<b>3 dictations</b> · 42 words spoken · 100% Wayland auto-paste ready",
            use_markup=True,
            xalign=0
        )
        self.stats_label.add_css_class("stats-banner")
        body.append(self.stats_label)

        # Scrolled card list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.dictations_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.set_child(self.dictations_container)
        body.append(scroll)

        # Bottom "Try Dictation" bar (discreet, Wispr Flow style)
        try_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        try_bar.add_css_class("try-bar")

        self.try_entry = Gtk.Entry()
        self.try_entry.add_css_class("try-entry")
        self.try_entry.set_hexpand(True)
        self.try_entry.set_placeholder_text("Type or hold Super+Shift+J anywhere on your desktop to dictate...")
        self.try_entry.connect("activate", self._on_try_entry_submit)
        try_bar.append(self.try_entry)

        self.try_mic_btn = Gtk.Button()
        self.try_mic_btn.add_css_class("try-mic-btn")
        self.try_mic_btn.set_child(Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic"))
        self.try_mic_btn.set_tooltip_text("Click to test voice dictation")
        self.try_mic_btn.connect("clicked", self._on_try_mic_clicked)
        try_bar.append(self.try_mic_btn)

        body.append(try_bar)

        main.append(body)
        self.content_stack.add_named(main, "dictations")

    def _refresh_history(self):
        while True:
            child = self.dictations_container.get_first_child()
            if child is None:
                break
            self.dictations_container.remove(child)

        query = self.search_entry.get_text().strip() if hasattr(self, "search_entry") else ""
        items = list_history(limit=50, query=query)

        total_words = sum(len((it.get("formatted_text") or it.get("raw_text", "")).split()) for it in items)
        if hasattr(self, "stats_label"):
            count_str = f"<b>{len(items)} dictations</b>" if items else "<b>0 dictations</b>"
            self.stats_label.set_markup(f"{count_str} · {total_words} words spoken · Active engine: Groq Llama 3.3")

        if not items:
            empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_margin_top(60)
            icon = Gtk.Image.new_from_icon_name("document-open-recent-symbolic")
            icon.set_pixel_size(42)
            icon.set_opacity(0.4)
            empty.append(icon)

            lbl = Gtk.Label(label="No dictations yet\nHold Super+Shift+J anywhere on your desktop to dictate.")
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_opacity(0.6)
            empty.append(lbl)
            self.dictations_container.append(empty)
            return

        for item in items:
            text = item.get("formatted_text") or item.get("raw_text", "")
            created = item.get("created_at", "")
            item_id = item.get("id")
            words = len(text.split())

            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            card.add_css_class("dictation-card")

            # Card Header
            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            time_lbl = Gtk.Label(label=f"{created}", xalign=0)
            time_lbl.add_css_class("dictation-time")
            time_lbl.set_hexpand(True)
            top_row.append(time_lbl)

            # Copy button
            c_btn = Gtk.Button()
            c_btn.set_child(Gtk.Image.new_from_icon_name("edit-copy-symbolic"))
            c_btn.add_css_class("btn-icon-subtle")
            c_btn.set_tooltip_text("Copy transcript")
            c_btn.connect("clicked", lambda b, t=text: self._copy_text(t))
            top_row.append(c_btn)

            # Delete button
            d_btn = Gtk.Button()
            d_btn.set_child(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
            d_btn.add_css_class("btn-icon-subtle")
            d_btn.set_tooltip_text("Delete entry")
            d_btn.connect("clicked", lambda b, i=item_id: self._delete_item(i))
            top_row.append(d_btn)
            card.append(top_row)

            # Body text
            body_lbl = Gtk.Label(label=text, xalign=0, wrap=True)
            body_lbl.add_css_class("dictation-body")
            body_lbl.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            body_lbl.set_selectable(True)
            card.append(body_lbl)

            # Metadata footer
            meta_lbl = Gtk.Label(label=f"{words} words · Auto-pasted", xalign=0)
            meta_lbl.add_css_class("dictation-meta")
            card.append(meta_lbl)

            self.dictations_container.append(card)

    def _on_try_entry_submit(self, entry):
        text = entry.get_text().strip()
        if not text:
            return
        entry.set_text("")
        self.try_entry.set_placeholder_text("Polishing with WhisperFlow...")
        
        def run():
            formatted = polish_transcript(text)
            save_history_item(raw_text=text, formatted_text=formatted, duration_sec=1.0)
            GLib.idle_add(self._on_try_finished)

        threading.Thread(target=run, daemon=True).start()

    def _on_try_finished(self):
        self.try_entry.set_placeholder_text("Type or hold Super+Shift+J anywhere on your desktop to dictate...")
        self._refresh_history()

    def _on_try_mic_clicked(self, btn):
        if not self.is_recording:
            self.is_recording = True
            self.try_mic_btn.add_css_class("recording")
            self.try_entry.set_placeholder_text("Listening... Speak now, then click mic to finish.")

            def run_capture():
                try:
                    hotkey_script = str(REPO_DIR / "jarvis" / "hotkey.py")
                    subprocess.run([sys.executable, hotkey_script], check=True)
                except Exception as e:
                    print(f"Error: {e}")
                GLib.idle_add(self._on_mic_finished)

            threading.Thread(target=run_capture, daemon=True).start()
        else:
            self.is_recording = False
            self.try_mic_btn.remove_css_class("recording")
            self.try_entry.set_placeholder_text("Processing speech...")

    def _on_mic_finished(self):
        self.is_recording = False
        self.try_mic_btn.remove_css_class("recording")
        self.try_entry.set_placeholder_text("Type or hold Super+Shift+J anywhere on your desktop to dictate...")
        self._refresh_history()

    # -------------------------------------------------------------
    # VIEW 2: DICTIONARY (Custom Technical Words)
    # -------------------------------------------------------------
    def _build_dictionary_view(self):
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.add_css_class("flat")
        title = Adw.WindowTitle(title="Dictionary", subtitle="Teach Whistle custom developer words and Hinglish")
        header.set_title_widget(title)
        main.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        clamp = Adw.Clamp(maximum_size=740, tightening_threshold=540)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)
        scroll.set_child(clamp)

        # Add Word Card
        add_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_card.add_css_class("clean-card")

        add_title = Gtk.Label(label="<b>Add Custom Word or Acronym</b>", use_markup=True, xalign=0)
        add_card.append(add_title)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.dict_from_entry = Gtk.Entry(placeholder_text="Spoken / Misheard (e.g. 'crawl')")
        self.dict_from_entry.set_hexpand(True)
        input_row.append(self.dict_from_entry)

        arrow_lbl = Gtk.Label(label="→")
        arrow_lbl.set_opacity(0.5)
        input_row.append(arrow_lbl)

        self.dict_to_entry = Gtk.Entry(placeholder_text="Target Replacement (e.g. 'Groq')")
        self.dict_to_entry.set_hexpand(True)
        input_row.append(self.dict_to_entry)

        add_btn = Gtk.Button(label="Add Rule")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_dictionary_word)
        input_row.append(add_btn)

        add_card.append(input_row)
        box.append(add_card)

        # Dictionary list
        self.dict_list_group = Adw.PreferencesGroup(
            title="Active Vocabulary Rules",
            description="WhisperFlow automatically prioritizes these spellings during transcription."
        )
        box.append(self.dict_list_group)

        self.dict_listbox = Gtk.ListBox()
        self.dict_listbox.add_css_class("boxed-list")
        self.dict_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.dict_list_group.add(self.dict_listbox)

        self._render_dictionary_list()

        main.append(scroll)
        self.content_stack.add_named(main, "dictionary")

    def _render_dictionary_list(self):
        while True:
            row = self.dict_listbox.get_first_child()
            if row is None:
                break
            self.dict_listbox.remove(row)

        for idx, item in enumerate(self.dictionary):
            row = Adw.ActionRow(
                title=f"<b>{item['to']}</b>",
                subtitle=f"Replaces acoustic variations like: <i>{item['from']}</i>"
            )
            row.set_use_markup(True)

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", lambda b, i=idx: self._delete_dict_word(i))
            row.add_suffix(del_btn)
            self.dict_listbox.append(row)

    def _on_add_dictionary_word(self, btn):
        f = self.dict_from_entry.get_text().strip()
        t = self.dict_to_entry.get_text().strip()
        if f and t:
            self.dictionary.insert(0, {"from": f, "to": t})
            save_dictionary(self.dictionary)
            self.dict_from_entry.set_text("")
            self.dict_to_entry.set_text("")
            self._render_dictionary_list()
            toast = Adw.Toast.new(f"Added '{t}' to dictionary")
            self.add_toast(toast)

    def _delete_dict_word(self, index):
        if 0 <= index < len(self.dictionary):
            removed = self.dictionary.pop(index)
            save_dictionary(self.dictionary)
            self._render_dictionary_list()
            toast = Adw.Toast.new(f"Removed '{removed['to']}'")
            self.add_toast(toast)

    # -------------------------------------------------------------
    # VIEW 3: STYLES (Writing Personalization)
    # -------------------------------------------------------------
    def _build_styles_view(self):
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.add_css_class("flat")
        title = Adw.WindowTitle(title="Writing Styles", subtitle="Configure formatting tone and structure")
        header.set_title_widget(title)
        main.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        clamp = Adw.Clamp(maximum_size=740, tightening_threshold=540)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        clamp.set_child(box)
        scroll.set_child(clamp)

        styles = [
            ("code", "🛠️  Developer &amp; Technical", "Preserves camelCase, programming flags, CLI commands, and technical acronyms without stripping punctuation.", True),
            ("pro", "💼  Clean &amp; Professional", "Removes verbal fillers (um, uh, like), corrects grammar, and formats into clean, publication-ready prose.", False),
            ("hinglish", "💬  Hinglish Natural", "Retains mixed Hindi-English speech in English letters (Latin script) without awkward translations.", False),
            ("bullets", "📝  Structured Bullets", "Transforms spoken trains of thought into concise, organized bullet points.", False),
        ]

        self.style_widgets = {}
        for key, name, desc, default in styles:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.add_css_class("style-card")
            if key == self.active_style:
                card.add_css_class("selected")

            header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            title_lbl = Gtk.Label(label=f"<b>{name}</b>", use_markup=True, xalign=0)
            title_lbl.set_hexpand(True)
            header_row.append(title_lbl)

            select_btn = Gtk.Button(label="Active" if key == self.active_style else "Select")
            select_btn.add_css_class("flat")
            select_btn.connect("clicked", lambda b, k=key: self._on_select_style(k))
            header_row.append(select_btn)
            card.append(header_row)

            desc_lbl = Gtk.Label(label=desc, xalign=0, wrap=True)
            desc_lbl.set_opacity(0.7)
            card.append(desc_lbl)

            box.append(card)
            self.style_widgets[key] = (card, select_btn)

        main.append(scroll)
        self.content_stack.add_named(main, "styles")

    def _on_select_style(self, style_key):
        self.active_style = style_key
        self.config["style"] = style_key
        save_config(self.config)

        for key, (card, btn) in self.style_widgets.items():
            if key == style_key:
                card.add_css_class("selected")
                btn.set_label("Active")
            else:
                card.remove_css_class("selected")
                btn.set_label("Select")

        toast = Adw.Toast.new("Writing style updated")
        self.add_toast(toast)

    # -------------------------------------------------------------
    # VIEW 4: SETTINGS (Preferences)
    # -------------------------------------------------------------
    def _build_settings_view(self):
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.add_css_class("flat")
        title = Adw.WindowTitle(title="Settings", subtitle="System shortcuts, audio and AI models")
        header.set_title_widget(title)
        main.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        clamp = Adw.Clamp(maximum_size=740, tightening_threshold=540)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)

        pref_page = Adw.PreferencesPage()
        clamp.set_child(pref_page)
        scroll.set_child(clamp)

        # Shortcuts
        sh_group = Adw.PreferencesGroup(title="Global Shortcuts and Dictation")
        pref_page.add(sh_group)

        hotkey_row = Adw.ActionRow(
            title="Global Hotkey",
            subtitle="Super+Shift+J — Press and hold to dictate, release to auto-paste"
        )
        sh_group.add(hotkey_row)

        mic_row = Adw.ActionRow(
            title="Audio Input Device",
            subtitle=get_active_audio_device()
        )
        sh_group.add(mic_row)

        # Cloud AI
        cloud_group = Adw.PreferencesGroup(title="Cloud Intelligence (Groq)")
        pref_page.add(cloud_group)

        self.groq_key_row = Adw.PasswordEntryRow(title="Groq API Key")
        self.groq_key_row.set_text(self.config.get("groq_api_key", ""))
        cloud_group.add(self.groq_key_row)

        self.groq_model_row = Adw.EntryRow(title="Groq Model")
        self.groq_model_row.set_text(self.config.get("groq_model", "llama-3.3-70b-versatile"))
        cloud_group.add(self.groq_model_row)

        # Local Fallback
        local_group = Adw.PreferencesGroup(title="Local Offline Fallback")
        pref_page.add(local_group)

        self.ollama_url_row = Adw.EntryRow(title="Ollama URL")
        self.ollama_url_row.set_text(self.config.get("ollama_url", "http://localhost:11434"))
        local_group.add(self.ollama_url_row)

        self.ollama_model_row = Adw.EntryRow(title="Ollama Model")
        self.ollama_model_row.set_text(self.config.get("ollama_model", "llama3.2"))
        local_group.add(self.ollama_model_row)

        # Save Button
        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        save_box.set_halign(Gtk.Align.END)
        save_box.set_margin_top(16)
        save_btn = Gtk.Button(label="Save Settings")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_settings)
        save_box.append(save_btn)

        action_group = Adw.PreferencesGroup()
        action_group.add(save_box)
        pref_page.add(action_group)

        main.append(scroll)
        self.content_stack.add_named(main, "settings")

    def _on_save_settings(self, btn):
        self.config["groq_api_key"] = self.groq_key_row.get_text().strip()
        self.config["groq_model"] = self.groq_model_row.get_text().strip()
        self.config["ollama_url"] = self.ollama_url_row.get_text().strip()
        self.config["ollama_model"] = self.ollama_model_row.get_text().strip()
        save_config(self.config)

        toast = Adw.Toast.new("Settings saved")
        self.add_toast(toast)

    # -------------------------------------------------------------
    # SHARED ACTIONS
    # -------------------------------------------------------------
    def _copy_text(self, text: str):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        toast = Adw.Toast.new("Copied to clipboard")
        self.add_toast(toast)

    def _delete_item(self, item_id: int):
        delete_history_item(item_id)
        self._refresh_history()

    def _on_clear_history(self, btn):
        clear_all_history()
        self._refresh_history()
        toast = Adw.Toast.new("History cleared")
        self.add_toast(toast)


class WhistleApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.xombi.whistle",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_data(APP_CSS)
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        win = self.props.active_window
        if not win:
            win = WhistleWindow(application=self)
        win.present()


def main():
    app = WhistleApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
