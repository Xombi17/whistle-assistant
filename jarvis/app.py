"""Native Linux Desktop GUI for Whistle Assistant built with GTK4 and Libadwaita."""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from jarvis.formatter import load_config, polish_transcript, save_config
from jarvis.history import clear_all_history, delete_history_item, list_history, save_history_item
from jarvis.server import get_active_audio_device


class WhistleWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Whistle")
        self.set_default_size(880, 680)

        self.recording_process = None
        self.is_recording = False
        self.config = load_config()

        self._build_ui()
        self._refresh_history()

    def _build_ui(self):
        # Main layout container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header Bar
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title="Whistle", subtitle="Local Voice Dictation & WhisperFlow")
        header.set_title_widget(title_widget)
        main_box.append(header)

        # View Stack for navigation tabs
        self.view_stack = Adw.ViewStack()
        
        # View Switcher in HeaderBar or subheader
        switcher_title = Adw.ViewSwitcherTitle()
        switcher_title.set_stack(self.view_stack)
        header.set_title_widget(switcher_title)

        # Tabs: 1. Dictate Studio, 2. History, 3. Settings
        self._build_dictate_tab()
        self._build_history_tab()
        self._build_settings_tab()

        # Bottom ViewSwitcherBar for adaptive mobile/compact sizing
        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self.view_stack)
        switcher_title.bind_property("title-visible", switcher_bar, "reveal", GObject.BindingFlags.SYNC_CREATE)

        main_box.append(self.view_stack)
        main_box.append(switcher_bar)

    def _build_dictate_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        clamp = Adw.Clamp(maximum_size=750, tightening_threshold=550)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(box)
        scroll.set_child(clamp)

        # Status & Hardware Banner
        status_group = Adw.PreferencesGroup(title="System & Audio Status")
        box.append(status_group)

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.add_css_class("card")
        status_box.set_margin_top(6)
        status_box.set_margin_bottom(6)
        status_box.set_margin_start(6)
        status_box.set_margin_end(6)

        mic_label = Gtk.Label(
            label=f"🎤  <b>Mic:</b> {get_active_audio_device()}    |    ⚡  <b>Shortcut:</b> <tt>Super+Shift+J</tt>",
            use_markup=True,
            xalign=0
        )
        mic_label.set_hexpand(True)
        mic_label.set_margin_start(12)
        mic_label.set_margin_top(10)
        mic_label.set_margin_bottom(10)
        status_box.append(mic_label)
        status_group.add(status_box)

        # Prominent Voice Dictate Card
        dictate_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        dictate_card.add_css_class("card")
        dictate_card.set_margin_top(8)
        dictate_card.set_margin_bottom(8)
        dictate_card.set_margin_start(6)
        dictate_card.set_margin_end(6)

        dictate_title = Gtk.Label(
            label="<big><b>Voice Dictation Studio</b></big>",
            use_markup=True,
            xalign=0.5
        )
        dictate_title.set_margin_top(16)
        dictate_card.append(dictate_title)

        # Record Trigger Button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_halign(Gtk.Align.CENTER)
        
        self.record_btn = Gtk.Button()
        self.record_btn.add_css_class("suggested-action")
        self.record_btn.add_css_class("pill")
        self.record_btn.set_label("🎙️  Start Dictation")
        self.record_btn.set_size_request(240, 56)
        self.record_btn.connect("clicked", self._on_record_btn_clicked)
        btn_box.append(self.record_btn)
        dictate_card.append(btn_box)

        self.status_feedback = Gtk.Label(
            label="Click above or hold <b>Super+Shift+J</b> anywhere on your desktop to dictate.",
            use_markup=True,
            xalign=0.5
        )
        self.status_feedback.add_css_class("dim-label")
        self.status_feedback.set_margin_bottom(16)
        dictate_card.append(self.status_feedback)
        box.append(dictate_card)

        # Output / Editor Area
        output_group = Adw.PreferencesGroup(title="Transcribed & Polished Text")
        box.append(output_group)

        editor_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        editor_card.add_css_class("card")
        editor_card.set_margin_top(6)
        editor_card.set_margin_bottom(6)
        editor_card.set_margin_start(6)
        editor_card.set_margin_end(6)

        text_scroll = Gtk.ScrolledWindow()
        text_scroll.set_min_content_height(160)
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        text_scroll.set_child(self.text_view)
        editor_card.append(text_scroll)

        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END)
        action_box.set_margin_end(12)
        action_box.set_margin_bottom(12)

        polish_btn = Gtk.Button(label="✨  Re-polish Text")
        polish_btn.connect("clicked", self._on_repolish_clicked)
        action_box.append(polish_btn)

        copy_btn = Gtk.Button(label="📋  Copy to Clipboard")
        copy_btn.connect("clicked", self._on_copy_clicked)
        action_box.append(copy_btn)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", lambda b: self._set_text(""))
        action_box.append(clear_btn)

        editor_card.append(action_box)
        output_group.add(editor_card)

        # Add to stack
        page = self.view_stack.add_titled(scroll, "dictate", "Dictate")
        page.set_icon_name("audio-input-microphone-symbolic")

    def _build_history_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        clamp = Adw.Clamp(maximum_size=800, tightening_threshold=600)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)
        scroll.set_child(clamp)

        # Search bar and clear all
        bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.set_placeholder_text("Search dictation history...")
        self.search_entry.connect("search-changed", lambda e: self._refresh_history())
        bar_box.append(self.search_entry)

        clear_history_btn = Gtk.Button(label="Clear All")
        clear_history_btn.add_css_class("destructive-action")
        clear_history_btn.connect("clicked", self._on_clear_all_history)
        bar_box.append(clear_history_btn)
        box.append(bar_box)

        # History list group
        self.history_group = Adw.PreferencesGroup(title="Recent Transcriptions")
        box.append(self.history_group)

        self.history_listbox = Gtk.ListBox()
        self.history_listbox.add_css_class("boxed-list")
        self.history_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.history_group.add(self.history_listbox)

        page = self.view_stack.add_titled(scroll, "history", "History")
        page.set_icon_name("document-open-recent-symbolic")

    def _build_settings_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)

        clamp = Adw.Clamp(maximum_size=750, tightening_threshold=550)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)

        pref_page = Adw.PreferencesPage()
        clamp.set_child(pref_page)
        scroll.set_child(clamp)

        # Provider group
        provider_group = Adw.PreferencesGroup(
            title="Transcription & LLM Service",
            description="Configure cloud formatting (Groq) or local fallback (Ollama / Needle 3)."
        )
        pref_page.add(provider_group)

        self.groq_key_row = Adw.PasswordEntryRow(title="Groq API Key")
        self.groq_key_row.set_text(self.config.get("groq_api_key", ""))
        provider_group.add(self.groq_key_row)

        self.groq_model_row = Adw.EntryRow(title="Groq Model")
        self.groq_model_row.set_text(self.config.get("groq_model", "llama-3.3-70b-versatile"))
        provider_group.add(self.groq_model_row)

        self.ollama_url_row = Adw.EntryRow(title="Ollama URL")
        self.ollama_url_row.set_text(self.config.get("ollama_url", "http://localhost:11434"))
        provider_group.add(self.ollama_url_row)

        self.ollama_model_row = Adw.EntryRow(title="Ollama Model")
        self.ollama_model_row.set_text(self.config.get("ollama_model", "llama3.2"))
        provider_group.add(self.ollama_model_row)

        # Shortcut & Desktop Group
        desktop_group = Adw.PreferencesGroup(
            title="Desktop Shortcut & Auto-Paste",
            description="Global shortcuts are managed via GNOME Settings."
        )
        pref_page.add(desktop_group)

        shortcut_row = Adw.ActionRow(
            title="Global Hotkey",
            subtitle="<Super><Shift>j — Press and hold to dictate, release to auto-paste into active app"
        )
        desktop_group.add(shortcut_row)

        # Save Button
        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        save_box.set_halign(Gtk.Align.END)
        save_box.set_margin_top(16)
        save_btn = Gtk.Button(label="Save Preferences")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_settings)
        save_box.append(save_btn)
        
        pref_group_action = Adw.PreferencesGroup()
        pref_group_action.add(save_box)
        pref_page.add(pref_group_action)

        page = self.view_stack.add_titled(scroll, "settings", "Settings")
        page.set_icon_name("emblem-system-symbolic")

    def _on_record_btn_clicked(self, btn):
        if not self.is_recording:
            # Start dictation trigger
            self.is_recording = True
            self.record_btn.remove_css_class("suggested-action")
            self.record_btn.add_css_class("destructive-action")
            self.record_btn.set_label("⏹️  Stop & Transcribe")
            self.status_feedback.set_markup("<span color='#3584e4'><b>● Recording audio... Speak now!</b></span>")

            def run_capture():
                try:
                    hotkey_script = str(Path(__file__).resolve().parent / "hotkey.py")
                    subprocess.run([sys.executable, hotkey_script], check=True)
                except Exception as e:
                    print(f"Error running hotkey script: {e}")
                GLib.idle_add(self._on_dictation_finished)

            threading.Thread(target=run_capture, daemon=True).start()
        else:
            # Send stop signal to hotkey
            self.is_recording = False
            self.record_btn.remove_css_class("destructive-action")
            self.record_btn.add_css_class("suggested-action")
            self.record_btn.set_label("🎙️  Start Dictation")
            self.status_feedback.set_text("Processing speech...")

    def _on_dictation_finished(self):
        self.is_recording = False
        self.record_btn.remove_css_class("destructive-action")
        self.record_btn.add_css_class("suggested-action")
        self.record_btn.set_label("🎙️  Start Dictation")
        self.status_feedback.set_markup("<span><b>Dictation complete!</b> Copied to clipboard & history.</span>")

        # Fetch latest history item to display in editor
        history = list_history(limit=1)
        if history:
            latest = history[0]
            self._set_text(latest.get("formatted_text") or latest.get("raw_text", ""))

        self._refresh_history()

    def _on_repolish_clicked(self, btn):
        text = self._get_text()
        if not text.strip():
            return
        
        btn.set_sensitive(False)
        self.status_feedback.set_text("Re-polishing with WhisperFlow...")

        def do_polish():
            polished = polish_transcript(text)
            GLib.idle_add(lambda: self._finish_repolish(btn, polished))

        threading.Thread(target=do_polish, daemon=True).start()

    def _finish_repolish(self, btn, polished_text):
        btn.set_sensitive(True)
        self._set_text(polished_text)
        self.status_feedback.set_text("Re-polishing complete.")
        save_history_item(raw_text=self._get_text(), formatted_text=polished_text, duration_sec=1.0)
        self._refresh_history()

    def _on_copy_clicked(self, btn):
        text = self._get_text()
        if text:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(text)
            self.status_feedback.set_text("Copied to clipboard!")

    def _on_save_settings(self, btn):
        self.config["groq_api_key"] = self.groq_key_row.get_text().strip()
        self.config["groq_model"] = self.groq_model_row.get_text().strip()
        self.config["ollama_url"] = self.ollama_url_row.get_text().strip()
        self.config["ollama_model"] = self.ollama_model_row.get_text().strip()
        save_config(self.config)

        toast = Adw.Toast.new("Preferences saved successfully!")
        toast.set_timeout(3)
        self.add_toast(toast)

    def _refresh_history(self):
        # Clear existing rows
        while True:
            row = self.history_listbox.get_first_child()
            if row is None:
                break
            self.history_listbox.remove(row)

        query = self.search_entry.get_text().strip()
        items = list_history(limit=50, query=query)

        if not items:
            empty_row = Adw.ActionRow(title="No history found")
            self.history_listbox.append(empty_row)
            return

        for item in items:
            text = item.get("formatted_text") or item.get("raw_text", "")
            created = item.get("created_at", "")
            item_id = item.get("id")

            row = Adw.ActionRow(
                title=text[:90] + ("..." if len(text) > 90 else ""),
                subtitle=f"⏱ {created}"
            )

            # Copy button
            copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
            copy_btn.set_valign(Gtk.Align.CENTER)
            copy_btn.add_css_class("flat")
            copy_btn.set_tooltip_text("Copy text")
            copy_btn.connect("clicked", lambda b, t=text: self._copy_text(t))
            row.add_suffix(copy_btn)

            # Delete button
            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.add_css_class("flat")
            del_btn.set_tooltip_text("Delete entry")
            del_btn.connect("clicked", lambda b, i=item_id: self._delete_item(i))
            row.add_suffix(del_btn)

            self.history_listbox.append(row)

    def _copy_text(self, text: str):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)
        toast = Adw.Toast.new("Copied to clipboard")
        self.add_toast(toast)

    def _delete_item(self, item_id: int):
        delete_history_item(item_id)
        self._refresh_history()

    def _on_clear_all_history(self, btn):
        clear_all_history()
        self._refresh_history()
        toast = Adw.Toast.new("All history cleared")
        self.add_toast(toast)

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
        win = self.props.active_window
        if not win:
            win = WhistleWindow(application=self)
        win.present()


def main():
    app = WhistleApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
