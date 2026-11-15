import os
import json

SCHEMAS = [
    {
        "name": "open_app",
        "description": "Open an application by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the application to open."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "find_files",
        "description": "Find files matching a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query to search for files."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "open_file",
        "description": "Open a file by path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the file to open."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_reminder",
        "description": "Create a reminder with a title and a time.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The title of the reminder."},
                "when": {"type": "string", "description": "The time when the reminder should be triggered."}
            },
            "required": ["title", "when"]
        }
    },
    {
        "name": "list_reminders",
        "description": "List all reminders."
    },
    {
        "name": "modify_reminder",
        "description": "Modify an existing reminder.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "The ID of the reminder to modify."},
                "title": {"type": "string", "description": "The new title of the reminder.", "optional": True},
                "when": {"type": "string", "description": "The new time when the reminder should be triggered.", "optional": True}
            },
            "required": ["id"]
        }
    },
    {
        "name": "cancel_reminder",
        "description": "Cancel an existing reminder.",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "The ID of the reminder to cancel."}
            },
            "required": ["id"]
        }
    }
]

class Inference:
    def __init__(self, model=None):
        self.model = model
        if self.model is None:
            os.environ['CACTUS_TELEMETRY'] = '0'
            os.environ['HF_HUB_OFFLINE'] = '1'
            import cactus
            self.model = cactus.Cactus(tools=SCHEMAS)

    def propose(self, text):
        response = self.model.complete(text)
        if not response['success'] or response['type'] != 'call' or response.get('suppressed_calls') or response.get('validation', {}).get('ungrounded'):
            raise ValueError("Invalid response from model")
        if not isinstance(response['function_calls'], list) or not 1 <= len(response['function_calls']) <= 8:
            raise ValueError("Invalid function calls")
        for call in response['function_calls']:
            if not isinstance(call, dict) or 'name' not in call or not isinstance(call['name'], str) or not call['name']:
                raise ValueError("Invalid function call name")
            if not all(isinstance(arg, dict) for arg in call.get('arguments', [])):
                raise ValueError("Invalid function call arguments")
            for arg in call['arguments']:
                if not isinstance(arg, dict) or not all(k in arg for k in ['name', 'value']) or not isinstance(arg['name'], str) or not isinstance(arg['value'], str) or not arg['name'] or not arg['value']:
                    raise ValueError("Invalid function call argument")
        return response['function_calls']

    def reset(self):
        if self.model:
            self.model.reset()

    def transcribe(self, path):
        os.environ['CACTUS_TELEMETRY'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        return cactus.transcribe(path)['text']
