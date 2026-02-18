import os
import json
import requests
from datetime import datetime

# ======================
# 設定
# ======================
THREADS_FILE = "threads.json"
STATE_FILE = "state.json"
OUTPUT_DIR = "logs"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ======================
# Utility
# ======================
def safe_filename(text):
    invalid = r'\/:*?"<>|'
    for c in invalid:
        text = text.replace(c, "")
    return text.strip()

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ======================
# Load data
# ======================
threads = load_json(THREADS_FILE, {})
state = load_json(STATE_FILE, {})

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ======================
# Main loop
# ======================
for name, info in threads.items():

    dat_url = info["dat"]
    board = info["board"]

    print("Checking:", name)

    try:
        res = requests.get(dat_url, headers=HEADERS, timeout=30)
        res.raise_for_status()
    except Exception as e:
        print("Fetch failed:", e)
        continue

    text = res.text
    lines = text.split("\n")
    total_res = len(lines)

    latest_dat = dat_url.split("/")[-1]

    last_state = state.get(name, {})
    last_res = last_state.get("last_res", 0)
    old_dat = last_state.get("dat")

    # スレが切り替わったらリセット
    if old_dat != latest_dat:
        last_res = 0

    if total_res <= last_res:
        print("No update")
        continue

    # ======================
    # Parse title
    # ======================
    first = lines[0].split("<>")
    title = first[4] if len(first) >= 5 else "unknown_thread"

    filename = safe_filename(title) + ".txt"
    thread_dir = os.path.join(OUTPUT_DIR, name)
    os.makedirs(thread_dir, exist_ok=True)

    path = os.path.join(thread_dir, filename)

    new_lines = lines[last_res:]

    with open(path, "a", encoding="utf-8") as f:

        # 初回のみタイトル
        if last_res == 0:
            f.write(f"TITLE: {title}\n")
            f.write(f"BOARD: {board}\n")
            f.write("=" * 70 + "\n\n")

        for line in new_lines:
            parts = line.split("<>")
            if len(parts) < 5:
                continue

            name_, mail, date_id, body, _ = parts[:5]

            f.write(name_ + "\n")
            f.write(date_id + "\n")
            f.write(body.replace("<br>", "\n") + "\n")
            f.write("-" * 40 + "\n")

    # ======================
    # Save state
    # ======================
    state[name] = {
        "dat": latest_dat,
        "last_res": total_res
    }

    print(f"Updated {name}: {last_res + 1} → {total_res}")

# ======================
# Save state.json
# ======================
save_json(STATE_FILE, state)
print("Done.")
