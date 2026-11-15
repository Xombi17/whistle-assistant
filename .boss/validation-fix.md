Output complete replacement for jarvis/validation.py in builder format. Write function validate(response) as follows:
1. If not isinstance(response,dict) or response.get('success') is not True or response.get('type') != 'call', raise ValueError.
2. If response.get('suppressed_calls') or response.get('validation', {}).get('ungrounded'), raise ValueError. The ungrounded data is inside a nested 'validation' dictionary, not a dotted key.
3. calls=response.get('function_calls'); if not a list or len(calls) <1 or >8, raise ValueError.
4. Define specs mapping each name to tuple (required set, optional set): open_app ({'name'}, set()), find_files ({'query'},set()), open_file ({'path'},set()), create_reminder ({'title','when'},set()), list_reminders (set(),set()), modify_reminder ({'id'},{'title','when'}), cancel_reminder ({'id'},set()).
5. For each call: require isinstance(call,dict), call.get('name') in specs, isinstance(call.get('arguments'),dict). Set args=call['arguments']; required,optional=specs[call['name']]; if required - args.keys() or args.keys() - required - optional, raise ValueError. If name is modify_reminder and neither title nor when is present, raise ValueError.
6. For each key,value in args.items(): if key=='id', reject unless type(value) is int and value>0; for all other keys, reject unless isinstance(value,str) and value.strip() is nonempty and len(value)<=300. In particular do not try to access args['id'] on calls that have no id.
7. Return calls. No imports or extra functions. Ensure valid Python code.
