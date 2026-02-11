import json
import os
import re
import requests
from datetime import datetime

DATE = datetime.now().strftime("%Y-%m-%d")

TARGETS = {
    "cg_grok": {
        "board": "https://mevius.5ch.net/cg/",
        "keyword": "Grok"
    },
    "cg_comfyui": {
        "board": "https://mevius.5ch.net/cg/",
        "keyword": "ComfyUI"
    },
    "cg_ai_questions": {
        "board": "https://mevius.5ch.net/cg/",
        "keyword": "画像生成AI質問"
    },
    "liveuranus_nanj": {
        "board": "https://fate.5ch.net/liveuranus/",
        "keyword": "なんJNVA部"
    },
    "jisaku_rtx": {
        "board": "https://egg.5ch.net/jisaku/",
        "keyword": "RTX"
    },
    "pink_sd": {
        "board": "https://mercury.bbspink.com/erocg/",
        "keyword": "StableDiffusion"
    }
}

def get_text(url):
    r = requests.get("https://r.jina.ai/" + url)
    return r.text

def extract_latest_thread(board_text, keyword):
    lines = board_text.splitlines()
    for line in lines:
        if keyword in line:
            m = re.search(r'https://[^ ]+/test/read.cgi/[^/]+/(\d+)/', line)
            if m:
                return m.group(1)
    return None

def extract_responses(thread_text):
    matches = re.findall(r'^\d+', thread_text, re.MULTILINE)
    if matches:
        return int(matches[-1])
    return 0

# load state
with open("state.json", "r") as f:
    state = json.load(f)

for name, cfg in TARGETS.items():
    os.makedirs(f"threads/{name}", exist_ok=True)

    board_text = get_text(cfg["board"])
    latest_thread = extract_latest_thread(board_text, cfg["keyword"])

    if not latest_thread:
        continue

    old_thread = state[name]["thread_id"]
    last_res = state[name]["last_res"]

    if old_thread != latest_thread:
        last_res = 0
        state[name]["thread_id"] = latest_thread

    thread_url = f"https://{cfg['board'].split('/')[2]}/test/read.cgi/{cfg['board'].split('/')[-2]}/{latest_thread}/{last_res + 1}-"
    thread_text = get_text(thread_url)

    new_last_res = extract_responses(thread_text)

    if new_last_res > last_res:
        path = f"threads/{name}/{DATE}_{last_res+1}-{new_last_res}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(thread_text)
        state[name]["last_res"] = new_last_res

# save state
with open("state.json", "w") as f:
    json.dump(state, f, indent=2)
