def validate(response):
    if not isinstance(response, dict) or response.get('success') is not True or response.get('type') != 'call':
        raise ValueError("Invalid response structure")
    
    if response.get('suppressed_calls') or response.get('validation', {}).get('ungrounded'):
        raise ValueError("Suppressed calls or ungrounded validation found")
    
    calls = response.get('function_calls')
    if not isinstance(calls, list) or len(calls) < 1 or len(calls) > 8:
        raise ValueError("Invalid number of function calls")
    
    specs = {
        'open_app': ({'name'}, set()),
        'find_files': ({'query'}, set()),
        'open_file': ({'path'}, set()),
        'create_reminder': ({'title', 'when'}, set()),
        'list_reminders': (set(), set()),
        'modify_reminder': ({'id'}, {'title', 'when'}),
        'cancel_reminder': ({'id'}, set())
    }
    
    for call in calls:
        if not isinstance(call, dict) or call.get('name') not in specs or not isinstance(call.get('arguments'), dict):
            raise ValueError("Invalid call structure")
        
        name = call['name']
        args = call['arguments']
        required, optional = specs[name]
        
        if required - args.keys() or args.keys() - required - optional:
            raise ValueError("Invalid arguments for call")
        
        if name == 'modify_reminder' and 'title' not in args and 'when' not in args:
            raise ValueError("Missing required arguments for modify_reminder")
        
        for key, value in args.items():
            if key == 'id':
                if not isinstance(value, int) or value <= 0:
                    raise ValueError("Invalid 'id' value")
            else:
                if not isinstance(value, str) or not value.strip() or len(value) > 300:
                    raise ValueError("Invalid argument value")
    
    return calls
