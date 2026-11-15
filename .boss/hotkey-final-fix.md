Copy complete source below into jarvis/hotkey.py in builder format, changing exactly two things: (1) replace `open('/tmp/jarvis-speech-test-%s.lock' % os.getuid(), 'w')` with `open(os.path.join(os.environ['XDG_RUNTIME_DIR'], 'jarvis-speech-test.lock'), 'a')`; (2) in the msg line, change literal backslash-n (`\\n`) to Python newline escapes (`\n`) so the dialog has real line breaks. Keep everything else exactly unchanged.
import os
import sys
import json
import tempfile
import subprocess
import fcntl
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jarvis.model import LocalModels

def main():
    with open('/tmp/jarvis-speech-test-%s.lock' % os.getuid(), 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            subprocess.run(['notify-send', 'JARVIS', 'Already recording'], check=False)
            return

        try:
            subprocess.run(['notify-send', 'JARVIS', 'Listening for 5 seconds. Say open calculator'], check=False)
            with tempfile.TemporaryDirectory() as directory:
                wav = os.path.join(directory, 'recording.wav')
                subprocess.run(['arecord', '-q', '-d', '5', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', wav], check=True)
                tools = [{'name': 'open_app', 'description': 'Open an installed application', 'parameters': {'type': 'object', 'properties': {'name': {'type': 'string'}}, 'required': ['name']}}]
                model = LocalModels(tools)
                transcript = model.transcribe(wav)
                if not transcript:
                    raise ValueError('No speech detected')
                response = model.propose(transcript)
                calls = response.get('function_calls', [])
                msg = 'Transcript: ' + transcript + '\n\nProposed action: ' + json.dumps(calls, ensure_ascii=False) + '\n\nNo action was executed.'
                subprocess.run(['zenity', '--info', '--title=JARVIS speech test', '--text=' + msg], check=False)
        except Exception as exc:
            subprocess.run(['zenity', '--error', '--title=JARVIS speech test', '--text=' + str(exc)], check=False)
            return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
