"""Whistle Assistant — Native Linux Desktop GUI built with GTK4 and Libadwaita.
Engineered for ultra-fast, privacy-first voice dictation and intelligent WhisperFlow formatting.
"""

import math
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add project root to path
REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

import cairo
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from jarvis.formatter import load_config, polish_transcript, save_config
from jarvis.history import clear_all_history, delete_history_item, list_history, save_history_item
from jarvis.server import get_active_audio_device

CSS_STYLE = b"""
/* Window & Surface */
window.whistle-window {
    background-color: #0c0e14;
}

.brand-title {
    font-weight: 800;
    font-size: 15px;
    letter-spacing: -0.2px;
    color: #f8fafc;
}

.brand-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border-radius: 6px;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

/* System Pill */
.status-pill {
    padding: 5px 12px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.status-pill.ready {
    color: #34d399;
}
.status-pill.recording {
    color: #fb7185;
    background: rgba(244, 63, 94, 0.15);
    border-color: rgba(244, 63, 94, 0.4);
}
.status-pill.processing {
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.4);
}

/* Hardware / Status Bar */
.hardware-bar {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 10px 16px;
}
.hardware-bar label {
    font-size: 12px;
    color: #94a3b8;
}

/* Hero Studio Card */
.studio-hero {
    background: linear-gradient(180deg, rgba(26, 29, 43, 0.75) 0%, rgba(16, 18, 28, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px 20px;
}

.mic-hero-btn {
    min-width: 76px;
    min-height: 76px;
    border-radius: 38px;
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
    border: none;
    color: white;
}
.mic-hero-btn:hover {
    background: linear-gradient(135deg, #60a5fa 0%, #818cf8 100%);
    box-shadow: 0 10px 30px rgba(99, 102, 241, 0.55);
}
.mic-hero-btn.recording {
    background: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%);
    box-shadow: 0 8px 28px rgba(244, 63, 94, 0.55);
}

/* Tone Mode Chips */
.tone-chip {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
}
.tone-chip:checked {
    background: rgba(99, 102, 241, 0.2);
    border-color: #6366f1;
    color: #c7d2fe;
}

/* Transcript Canvas */
.transcript-card {
    background: rgba(15, 17, 26, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 4px;
}
.transcript-card textview {
    background: transparent;
    color: #f1f5f9;
    font-size: 14px;
    line-height: 1.6;
}
.transcript-header {
    padding: 8px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

/* History Cards */
.history-entry {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.history-entry:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(99, 102, 241, 0.3);
}

.action-btn-subtle {
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
}
"""


def clean_mic_name(name: str) -> str:
    """Shorten verbose Linux ALSA/PipeWire device names into a clean label."""
    if not name:
        return "Default Microphone"
    name = name.split(".")[0].strip()
    if "Core Ultra" in name:
        return "Core Ultra HD Mic"
    if "Built-in" in name or "Internal" in name:
        return "Internal Mic"
    if "USB" in name:
        return "USB Microphone"
    if len(name) > 28:
        return name[:26] + "…"
    return name


class VisualizerArea(Gtk.DrawingArea):
    """Dynamic animated audio soundwave visualizer."""
    def __init__(self):
        super().__init__()
        self.set_content_height(34)
        self.set_content_width(260)
        self.is_active = False
        self.phase = 0.0
        self.set_draw_func(self._draw)

    def set_active(self, active: bool):
        self.is_active = active
        self.queue_draw()

    def tick(self):
        if self.is_active:
            self.phase += 0.25
            self.queue_draw()

    def _draw(self, area, cr: cairo.Context, width: int, height: int):
        num_bars = 24
        bar_width = 4.0
        spacing = (width - (num_bars * bar_width)) / (num_bars - 1)
        mid_y = height / 2.0

        for i in range(num_bars):
            x = i * (bar_width + spacing)
            if self.is_active:
                # Dynamic reactive waves
                wave = math.sin(self.phase + i * 0.45) * 0.5 + 0.5
                wave2 = math.cos(self.phase * 0.7 + i * 0.3) * 0.5 + 0.5
                h = 6 + (wave * 0.6 + wave2 * 0.4) * (height - 10)
                # Gradient rose/purple while recording
                cr.set_source_rgba(0.96, 0.25, 0.37, 0.9)
            else:
                # Idle subtle bars
                h = 4.0
                cr.set_source_rgba(0.3, 0.35, 0.45, 0.4)

            y = mid_y - (h / 2.0)
            radius = bar_width / 2.0

            # Draw rounded bar
            cr.new_sub_path()
            cr.arc(x + radius, y + radius, radius, math.pi, 1.5 * math.pi)
            cr.arc(x + bar_width - radius, y + radius, radius, 1.5 * math.pi, 2 * math.pi)
            cr.arc(x + bar_width - radius, y + h - radius, radius, 0, 0.5 * math.pi)
            cr.arc(x + radius, y + h - radius, radius, 0.5 * math.pi, math.pi)
            cr.close_path()
            cr.fill()


class WhistleWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Whistle")
        self.set_default_size(760, 620)
        self.add_css_class("whistle-window")

        self.is_recording = False
        self.config = load_config()
        self.recording_start_time = 0.0

        self._build_ui()
        self._refresh_history()

        # Visualizer animation loop (30 FPS)
        GLib.timeout_add(33, self._on_anim_tick)

    def _on_anim_tick(self):
        if hasattr(self, "visualizer"):
            self.visualizer.tick()
        if self.is_recording:
            elapsed = time.time() - self.recording_start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self.hero_caption.set_markup(f"<span color='#fb7185'><b>● Recording: {mins:02d}:{secs:02d}</b></span>")
        return True

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header Bar
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        main_box.append(header)

        # Left Header: App Branding
        brand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        brand_box.set_margin_start(8)
        icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
        icon.set_pixel_size(18)
        brand_box.append(icon)

        title_lbl = Gtk.Label(label="Whistle")
        title_lbl.add_css_class("brand-title")
        brand_box.append(title_lbl)

        badge_lbl = Gtk.Label(label="v1.0")
        badge_lbl.add_css_class("brand-badge")
        brand_box.append(badge_lbl)
        header.pack_start(brand_box)

        # Center Header: View Switcher
        self.view_stack = Adw.ViewStack()
        switcher_title = Adw.ViewSwitcherTitle()
        switcher_title.set_stack(self.view_stack)
        header.set_title_widget(switcher_title)

        # Right Header: Live Status Badge
        self.status_badge = Gtk.Label(label="● Ready")
        self.status_badge.add_css_class("status-pill")
        self.status_badge.add_css_class("ready")
        self.status_badge.set_margin_end(8)
        header.pack_end(self.status_badge)

        # Pages
        self._build_studio_tab()
        self._build_history_tab()
        self._build_settings_tab()

        main_box.append(self.view_stack)

    def _build_studio_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        clamp = Adw.Clamp(maximum_size=720, tightening_threshold=520)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)
        scroll.set_child(clamp)

        # 1. Sleek Hardware & Status Capsule
        hw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hw_box.add_css_class("hardware-bar")

        mic_name = clean_mic_name(get_active_audio_device())
        mic_lbl = Gtk.Label(label=f"🎙️  <b>Mic:</b> {mic_name}", use_markup=True, xalign=0)
        mic_lbl.set_hexpand(True)
        hw_box.append(mic_lbl)

        shortcut_lbl = Gtk.Label(label="⚡  <b>Shortcut:</b> <tt>Super+Shift+J</tt>", use_markup=True)
        hw_box.append(shortcut_lbl)

        model_name = self.config.get("groq_model", "Llama 3.3 70B").split("/")[-1].split(":")[0]
        engine_lbl = Gtk.Label(label=f"🧠  <b>Engine:</b> {model_name}", use_markup=True)
        hw_box.append(engine_lbl)
        box.append(hw_box)

        # 2. Hero Dictation Card
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        hero.add_css_class("studio-hero")

        # Visualizer & Mic Button
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        center_box.set_halign(Gtk.Align.CENTER)

        self.mic_btn = Gtk.Button()
        self.mic_btn.add_css_class("mic-hero-btn")
        mic_icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
        mic_icon.set_pixel_size(32)
        self.mic_btn.set_child(mic_icon)
        self.mic_btn.connect("clicked", self._on_mic_toggle)
        center_box.append(self.mic_btn)

        self.visualizer = VisualizerArea()
        center_box.append(self.visualizer)

        self.hero_caption = Gtk.Label(
            label="Press and hold <b>Super+Shift+J</b> or click mic to dictate",
            use_markup=True,
            xalign=0.5
        )
        self.hero_caption.add_css_class("dim-label")
        center_box.append(self.hero_caption)
        hero.append(center_box)

        # Tone / Format Presets
        presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        presets_box.set_halign(Gtk.Align.CENTER)
        
        self.preset_radios = []
        first_radio = None
        for name in ["💻 Code & Tech", "💼 Clean Pro", "💬 Hinglish", "📝 Bullets"]:
            radio = Gtk.CheckButton(label=name)
            radio.add_css_class("tone-chip")
            if first_radio is None:
                first_radio = radio
                radio.set_active(True)
            else:
                radio.set_group(first_radio)
            presets_box.append(radio)
            self.preset_radios.append(radio)
        hero.append(presets_box)
        box.append(hero)

        # 3. Transcribed Text Canvas
        transcript_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        transcript_container.add_css_class("transcript-card")

        # Header bar of transcript card
        th = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        th.add_css_class("transcript-header")

        self.word_count_lbl = Gtk.Label(label="0 words", xalign=0)
        self.word_count_lbl.add_css_class("dim-label")
        self.word_count_lbl.set_hexpand(True)
        th.append(self.word_count_lbl)

        repolish_btn = Gtk.Button(label="✨ Polish")
        repolish_btn.add_css_class("action-btn-subtle")
        repolish_btn.connect("clicked", self._on_repolish_clicked)
        th.append(repolish_btn)

        copy_btn = Gtk.Button(label="📋 Copy")
        copy_btn.add_css_class("action-btn-subtle")
        copy_btn.connect("clicked", self._on_copy_clicked)
        th.append(copy_btn)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.add_css_class("action-btn-subtle")
        clear_btn.connect("clicked", lambda b: self._set_text(""))
        th.append(clear_btn)
        transcript_container.append(th)

        # Editor
        text_scroll = Gtk.ScrolledWindow()
        text_scroll.set_min_content_height(140)
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(16)
        self.text_view.set_right_margin(16)
        self.text_view.set_top_margin(14)
        self.text_view.set_bottom_margin(14)
        self.text_view.get_buffer().connect("changed", self._on_text_changed)
        text_scroll.set_child(self.text_view)
        transcript_container.append(text_scroll)

        box.append(transcript_container)

        page = self.view_stack.add_titled(scroll, "studio", "Studio")
        page.set_icon_name("audio-input-microphone-symbolic")

    def _build_history_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        clamp = Adw.Clamp(maximum_size=740, tightening_threshold=540)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        clamp.set_child(box)
        scroll.set_child(clamp)

        # Search Bar & Actions
        bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.set_placeholder_text("Search past dictations...")
        self.search_entry.connect("search-changed", lambda e: self._refresh_history())
        bar_box.append(self.search_entry)

        clear_history_btn = Gtk.Button(label="Clear History")
        clear_history_btn.add_css_class("destructive-action")
        clear_history_btn.connect("clicked", self._on_clear_all_history)
        bar_box.append(clear_history_btn)
        box.append(bar_box)

        # Dynamic Container for History Cards
        self.history_cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(self.history_cards_box)

        page = self.view_stack.add_titled(scroll, "history", "History")
        page.set_icon_name("document-open-recent-symbolic")

    def _build_settings_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        clamp = Adw.Clamp(maximum_size=720, tightening_threshold=520)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)

        pref_page = Adw.PreferencesPage()
        clamp.set_child(pref_page)
        scroll.set_child(clamp)

        # Cloud AI
        cloud_group = Adw.PreferencesGroup(
            title="Cloud Intelligence",
            description="Ultra-fast Groq Llama 3.3 70B formatting with technical auto-correction."
        )
        pref_page.add(cloud_group)

        self.groq_key_row = Adw.PasswordEntryRow(title="Groq API Key")
        self.groq_key_row.set_text(self.config.get("groq_api_key", ""))
        cloud_group.add(self.groq_key_row)

        self.groq_model_row = Adw.EntryRow(title="Groq Model")
        self.groq_model_row.set_text(self.config.get("groq_model", "llama-3.3-70b-versatile"))
        cloud_group.add(self.groq_model_row)

        # Local Fallback
        local_group = Adw.PreferencesGroup(
            title="Offline & Local Engine",
            description="Local Cactus compute fallback for 100% private, zero-latency dictation."
        )
        pref_page.add(local_group)

        self.ollama_url_row = Adw.EntryRow(title="Ollama Endpoint")
        self.ollama_url_row.set_text(self.config.get("ollama_url", "http://localhost:11434"))
        local_group.add(self.ollama_url_row)

        self.ollama_model_row = Adw.EntryRow(title="Ollama Model")
        self.ollama_model_row.set_text(self.config.get("ollama_model", "llama3.2"))
        local_group.add(self.ollama_model_row)

        # Shortcuts
        key_group = Adw.PreferencesGroup(
            title="Desktop Global Hotkey",
            description="Control how dictation triggers across your entire Linux desktop."
        )
        pref_page.add(key_group)

        shortcut_row = Adw.ActionRow(
            title="Active Hotkey",
            subtitle="Super+Shift+J (Hold to speak, release to auto-paste)"
        )
        key_group.add(shortcut_row)

        # Save Button
        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        save_box.set_halign(Gtk.Align.END)
        save_box.set_margin_top(16)
        save_btn = Gtk.Button(label="Save Preferences")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_settings)
        save_box.append(save_btn)

        action_group = Adw.PreferencesGroup()
        action_group.add(save_box)
        pref_page.add(action_group)

        page = self.view_stack.add_titled(scroll, "settings", "Settings")
        page.set_icon_name("emblem-system-symbolic")

    def _on_mic_toggle(self, btn):
        if not self.is_recording:
            # Start Recording
            self.is_recording = True
            self.recording_start_time = time.time()
            self.mic_btn.add_css_class("recording")
            self.visualizer.set_active(True)

            self.status_badge.set_text("● Recording")
            self.status_badge.remove_css_class("ready")
            self.status_badge.add_css_class("recording")

            def run_capture():
                try:
                    hotkey_script = str(REPO_DIR / "jarvis" / "hotkey.py")
                    subprocess.run([sys.executable, hotkey_script], check=True)
                except Exception as e:
                    print(f"Recording error: {e}")
                GLib.idle_add(self._on_dictation_finished)

            threading.Thread(target=run_capture, daemon=True).start()
        else:
            # Finish Recording
            self._set_processing_state()

    def _set_processing_state(self):
        self.is_recording = False
        self.visualizer.set_active(False)
        self.mic_btn.remove_css_class("recording")
        self.status_badge.set_text("⚡ Polishing")
        self.status_badge.remove_css_class("recording")
        self.status_badge.add_css_class("processing")
        self.hero_caption.set_markup("<span color='#38bdf8'><b>WhisperFlow is polishing speech...</b></span>")

    def _on_dictation_finished(self):
        self.is_recording = False
        self.visualizer.set_active(False)
        self.mic_btn.remove_css_class("recording")

        self.status_badge.set_text("● Ready")
        self.status_badge.remove_css_class("recording")
        self.status_badge.remove_css_class("processing")
        self.status_badge.add_css_class("ready")

        self.hero_caption.set_markup("<span><b>Dictation finished!</b> Text copied to clipboard & history.</span>")

        # Load newest result
        history = list_history(limit=1)
        if history:
            text = history[0].get("formatted_text") or history[0].get("raw_text", "")
            self._set_text(text)

        self._refresh_history()

    def _on_repolish_clicked(self, btn):
        text = self._get_text()
        if not text.strip():
            return
        btn.set_sensitive(False)
        self.status_badge.set_text("⚡ Polishing")
        self.status_badge.add_css_class("processing")

        def do_polish():
            polished = polish_transcript(text)
            GLib.idle_add(lambda: self._finish_repolish(btn, polished))

        threading.Thread(target=do_polish, daemon=True).start()

    def _finish_repolish(self, btn, polished_text):
        btn.set_sensitive(True)
        self._set_text(polished_text)
        self.status_badge.set_text("● Ready")
        self.status_badge.remove_css_class("processing")
        self.status_badge.add_css_class("ready")
        save_history_item(raw_text=self._get_text(), formatted_text=polished_text, duration_sec=1.0)
        self._refresh_history()

    def _on_copy_clicked(self, btn):
        text = self._get_text()
        if text:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(text)
            toast = Adw.Toast.new("Copied to clipboard!")
            toast.set_timeout(2)
            self.add_toast(toast)

    def _on_save_settings(self, btn):
        self.config["groq_api_key"] = self.groq_key_row.get_text().strip()
        self.config["groq_model"] = self.groq_model_row.get_text().strip()
        self.config["ollama_url"] = self.ollama_url_row.get_text().strip()
        self.config["ollama_model"] = self.ollama_model_row.get_text().strip()
        save_config(self.config)

        toast = Adw.Toast.new("Preferences saved successfully")
        toast.set_timeout(2)
        self.add_toast(toast)

    def _refresh_history(self):
        # Clear existing cards
        while True:
            child = self.history_cards_box.get_first_child()
            if child is None:
                break
            self.history_cards_box.remove(child)

        query = self.search_entry.get_text().strip()
        items = list_history(limit=40, query=query)

        if not items:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_box.set_halign(Gtk.Align.CENTER)
            empty_box.set_margin_top(40)
            empty_icon = Gtk.Image.new_from_icon_name("document-open-recent-symbolic")
            empty_icon.set_pixel_size(48)
            empty_box.append(empty_icon)
            empty_lbl = Gtk.Label(label="No dictations found yet.")
            empty_lbl.add_css_class("dim-label")
            empty_box.append(empty_lbl)
            self.history_cards_box.append(empty_box)
            return

        for item in items:
            text = item.get("formatted_text") or item.get("raw_text", "")
            created = item.get("created_at", "")
            item_id = item.get("id")

            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("history-entry")

            # Card Header
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            time_lbl = Gtk.Label(label=f"⏱ {created}", xalign=0)
            time_lbl.add_css_class("dim-label")
            time_lbl.set_hexpand(True)
            header.append(time_lbl)

            # Copy button
            c_btn = Gtk.Button(icon_name="edit-copy-symbolic")
            c_btn.add_css_class("flat")
            c_btn.set_tooltip_text("Copy text")
            c_btn.connect("clicked", lambda b, t=text: self._copy_text(t))
            header.append(c_btn)

            # Delete button
            d_btn = Gtk.Button(icon_name="user-trash-symbolic")
            d_btn.add_css_class("flat")
            d_btn.set_tooltip_text("Delete entry")
            d_btn.connect("clicked", lambda b, i=item_id: self._delete_item(i))
            header.append(d_btn)
            card.append(header)

            # Card Body
            body_lbl = Gtk.Label(label=text, xalign=0, wrap=True)
            body_lbl.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            body_lbl.set_selectable(True)
            card.append(body_lbl)

            self.history_cards_box.append(card)

    def _copy_text(self, text: str):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        toast = Adw.Toast.new("Copied to clipboard!")
        toast.set_timeout(2)
        self.add_toast(toast)

    def _delete_item(self, item_id: int):
        delete_history_item(item_id)
        self._refresh_history()

    def _on_clear_all_history(self, btn):
        clear_all_history()
        self._refresh_history()
        toast = Adw.Toast.new("History cleared")
        toast.set_timeout(2)
        self.add_toast(toast)

    def _on_text_changed(self, buf):
        text = self._get_text()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self.word_count_lbl.set_text(f"{words} words  •  {chars} characters")

    def _get_text(self) -> str:
        buf = self.text_view.get_buffer()
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        return buf.get_text(start, end, True)

    def _set_text(self, text: str):
        buf = self.text_view.get_buffer()
        buf.set_text(text)


class WhistleApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="com.xombi.whistle",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        # Load modern custom CSS
        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS_STYLE)
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
