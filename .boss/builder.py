#!/usr/bin/env python3
"""python .boss/builder.py BRIEF.md --only a.js,b.css -> writes the files the builder returns"""
import argparse, json, pathlib, re, sys, time, urllib.request
p = argparse.ArgumentParser()
p.add_argument("brief")
p.add_argument("--only", default="", help="comma-separated paths this brief may write; anything else is refused")
p.add_argument("--model", default="qwen3.8:27b")
p.add_argument("--url", default="http://localhost:11434/api/chat")
p.add_argument("--ctx", type=int, default=16384)
p.add_argument("--timeout", type=int, default=1800)
a = p.parse_args()
SYSTEM = ("You are a code builder. Output ONLY files, each in this exact form:\n"
          "=== FILE: relative/path.ext ===\n<complete file contents>\n=== END ===\n"
          "No explanations, no diffs, no placeholders, no TODOs. Every file must be complete and runnable.")
body = {"model": a.model, "stream": False, "think": False,
        "options": {"num_ctx": a.ctx, "temperature": 0.2},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": pathlib.Path(a.brief).read_text(encoding="utf-8")}]}
req = urllib.request.Request(a.url, json.dumps(body).encode(), {"Content-Type": "application/json"})
t0 = time.time()
try:
    resp = json.load(urllib.request.urlopen(req, timeout=a.timeout))
except Exception as e:
    print(f"BUILDER_FAILED: {e}"); sys.exit(2)
out = resp["message"]["content"]
runs = pathlib.Path(".boss/runs"); runs.mkdir(parents=True, exist_ok=True)
raw = runs / f"{pathlib.Path(a.brief).stem}-{int(t0)}.txt"
raw.write_text(out, encoding="utf-8")                 # quote this in a retry brief
allowed = {pathlib.PurePosixPath(x.strip()).as_posix() for x in a.only.split(",") if x.strip()}
files = re.findall(r"=== FILE: (.+?) ===\r?\n(.*?)\r?\n=== END ===", out, re.S)
if not files:
    print(f"BUILDER_NO_FILES (raw output: {raw})\n" + out[:3000]); sys.exit(3)
for path, content in files:
    dest = pathlib.Path(path.strip())
    if dest.is_absolute() or ".." in dest.parts or dest.parts[:1] == (".boss",):
        print(f"SKIPPED_UNSAFE_PATH {path}"); continue
    if allowed and dest.as_posix() not in allowed:
        print(f"SKIPPED_NOT_IN_BRIEF {path}"); continue
    content = re.sub(r"^```[\w-]*\n", "", content.strip("\n"))
    content = re.sub(r"\n```$", "", content)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content + "\n", encoding="utf-8")
    print(f"WROTE {dest} ({len(content.splitlines())} lines)")
print(f"STATS seconds={time.time()-t0:.0f} tokens_out={resp.get('eval_count')} raw={raw}")
