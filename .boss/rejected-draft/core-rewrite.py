import os
import re
import sqlite3
import subprocess
from datetime import datetime
import dateparser
from pathlib import Path

class Jarvis:
    def __init__(self, db_path=None, model=None, launch=None, speak=None):
        self.db_path = db_path or os.path.expanduser('~/.local/share/jarvis/jarvis.sqlite3')
        self.model = model
        self.launch = launch
        self.speak = speak
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS roots (path TEXT PRIMARY KEY)
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY,
                title TEXT,
                due TEXT,
                delivered INTEGER NOT NULL DEFAULT 0
            )
        ''')
        self.conn.commit()

    def propose(self, text):
        os.environ['CACTUS_TELEMETRY'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        import cactus
        response = cactus.complete(text)
        if not response['success'] or response['validation']['ungrounded'] or response['validation']['suppressed_calls']:
            raise ValueError("Invalid response from model")
        if len(response['call']['function_calls']) < 1 or len(response['call']['function_calls']) > 8:
            raise ValueError("Invalid number of function calls")
        for call in response['call']['function_calls']:
            if call['name'] not in ['open_app', 'find_files', 'open_file', 'create_reminder', 'list_reminders', 'modify_reminder', 'cancel_reminder']:
                raise ValueError("Invalid function name")
            for key in call['arguments']:
                if len(key) > 300:
                    raise ValueError("Invalid key length")
                if key not in call['function']['parameters']['properties']:
                    raise ValueError("Unknown key")
        return response['call']['function_calls']

    def prepare(self, call):
        if call['name'] == 'open_app':
            desktop_path = Path.home() / '.local/share/applications'
            xdg_data_dirs = os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
            for dir in [desktop_path] + [Path(x) / 'applications' for x in xdg_data_dirs]:
                for entry in dir.glob('*.desktop'):
                    config = entry.read_text()
                    if '[Desktop Entry]' in config and 'Type=Application' in config and 'Hidden=false' in config and 'NoDisplay=false' in config:
                        name = re.search(r'Name=(.*)', config, re.IGNORECASE).group(1).casefold()
                        if name == call['arguments']['name'].casefold():
                            target = entry.resolve()
                            return {'name': call['arguments']['name'], 'arguments': call['arguments'], 'target': str(target)}
            raise ValueError("App not found")
        elif call['name'] == 'open_file':
            path = Path(call['arguments']['path']).resolve(strict=True)
            if not path.is_file() or path.is_symlink() or path.suffix in ['.desktop', '.sh'] or path.stat().st_mode & 0o111:
                raise ValueError("Invalid file")
            return {'name': call['name'], 'arguments': call['arguments'], 'target': str(path)}
        elif call['name'] in ['create_reminder', 'modify_reminder']:
            due = dateparser.parse(call['arguments']['when'], settings={'PREFER_DATES_FROM': 'future'})
            if not due or due < datetime.now():
                raise ValueError("Invalid date")
            due = due.strftime('%Y-%m-%d %H:%M')
            if call['name'] == 'create_reminder':
                self.conn.execute('INSERT INTO reminders (title, due) VALUES (?, ?)', (call['arguments']['title'], due))
                self.conn.commit()
                return {'id': self.conn.lastrowid, 'due': due}
            else:
                self.conn.execute('UPDATE reminders SET title=?, due=? WHERE id=?', (call['arguments'].get('title', None), call['arguments'].get('when', None), call['arguments']['id']))
                self.conn.commit()
                return {'id': call['arguments']['id'], 'due': due}
        elif call['name'] == 'cancel_reminder':
            self.conn.execute('DELETE FROM reminders WHERE id=?', (call['arguments']['id'],))
            self.conn.commit()
            return f"Reminder {call['arguments']['id']} cancelled"
        else:
            return call

    def execute(self, prepared):
        for call in prepared:
            if call['name'] == 'open_app':
                target = Path(call['target']).resolve()
                self.launch(['gio', 'launch', str(target)])
            elif call['name'] == 'open_file':
                target = Path(call['target']).resolve()
                self.launch(['xdg-open', str(target)])
            elif call['name'] == 'create_reminder':
                return f"Reminder created: {call['due']}"
            elif call['name'] == 'list_reminders':
                reminders = self.conn.execute('SELECT id, title, due FROM reminders WHERE delivered=0').fetchall()
                return '\n'.join([f"{r[0]}: {r[1]} - {r[2]}" for r in reminders])
            elif call['name'] == 'modify_reminder':
                return f"Reminder {call['id']} modified"
            elif call['name'] == 'cancel_reminder':
                return f"Reminder {call['id']} cancelled"

    def add_root(self, path):
        path = Path(path).resolve()
        if not path.is_dir():
            raise ValueError("Invalid directory")
        self.conn.execute('INSERT INTO roots (path) VALUES (?)', (str(path),))
        self.conn.commit()

    def roots(self):
        return [r[0] for r in self.conn.execute('SELECT path FROM roots').fetchall()]

    def file_lookup(self, path):
        path = Path(path).resolve()
        for root in self.roots():
            if path.is_relative_to(root):
                return True
        raise ValueError("File not in approved root")

    def due(self):
        now = datetime.now()
        return self.conn.execute('SELECT id, title, due FROM reminders WHERE delivered=0 AND due<=?', (now.strftime('%Y-%m-%d %H:%M'),)).fetchall()

    def mark_delivered(self, id):
        self.conn.execute('UPDATE reminders SET delivered=1 WHERE id=?', (id,))
        self.conn.commit()
