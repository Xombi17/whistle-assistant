# JARVIS Ubuntu MVP — frozen interfaces

## Runtime and boundaries
Python 3 desktop app with Tkinter, SQLite and Cactus Compute's local Needle 3 and Whistle runtime. At launch set CACTUS_TELEMETRY=0 and HF_HUB_OFFLINE=1 before importing cactus. Setup separately downloads the pinned upstream engine and weights. No network access is needed by the application. Use arecord (16 kHz mono WAV) for push-to-talk and espeak-ng for local speech. Runtime work must stay off the GUI thread.

## Contracts
- Inference: `cactus.Cactus(tools=SCHEMAS).complete(text)` returns a proposal; `cactus.transcribe(wav)['text']` transcribes. Do not use `run()`. Validate success, calls and arguments, reject ungrounded calls, and never evaluate shell text.
- Tool contract: allowlist `open_app(name)`, `find_files(query)`, `open_file(path)`, `create_reminder(title, when)`, `list_reminders()`, `modify_reminder(id, title?, when?)`, `cancel_reminder(id)`. `when` is a local datetime, normalized before confirmation. All actions return readable results. Proposal display and explicit confirmation precede every execution. Multi-call batches are handled sequentially, capped. Needle conversation remains in memory and is reset when a proposal is rejected.
- Apps: only discover local .desktop files and launch using `gio launch` with a discovered desktop path, never model supplied executable/arguments. Files: search only explicitly approved directories, do not follow symlinks out of roots, opening checks resolved paths against roots. Never delete files.
- Storage: SQLite under XDG data directory; settings and reminders locally. Reminders notify while app runs, persist across restarts, and are marked delivered after alert. No background scheduling claim.
- UI: transcript input and recording toggle; proposal confirmation; status/results; directory consent picker; reminders. Errors visible, accessible keyboard controls. Reject incomplete or ambiguous requests instead of guessing.

## Milestones and verification
1. Build modules + desktop UI, installation instructions, tests with injected model/action adapters. 2. Install real Cactus runtime and prefetch weights, test real inference and offline acceptance. 3. Document untested hardware and limitations. Android, general LLM, wake word, document QA, pairing and plugins are future work, not fabricated.
- Reject executable files and .desktop files in file-open actions; show and confirm the resolved target. Model results must be returned through `complete(json.dumps(result))` when supporting dependent actions; do not claim unsupported follow-ups. Do not mark reminders delivered before displaying their alerts.
- Natural reminder dates use local dateparser and require an explicitly provided time; normalize and show the actual local date/time before confirmation. Include a manual reminder editor for requests Needle cannot route correctly.
- In testing, feeding a file-search result back caused Needle to propose opening the file without the user asking. Never auto-execute subsequent model calls; require explicit per-action approval and do not infer consent from a search. Reject ungrounded calls, reset model context after refusals, and limit follow-up loops.
