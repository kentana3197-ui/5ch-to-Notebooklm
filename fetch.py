import os
import re
import json
import requests
from datetime import datetime

BOARD = "liveuranus"
THREAD_KEYWORD = "なんJ"

SUBJECT_URL = f"https://itest.5ch.net/public/newapi/subject/{BOARD}.json"
DAT_BASE_URL = f"https://itest.5ch.net/public/newapi/dat/{BOARD}"

THREAD_DIR = "threads"
STATE_FILE = "state.json"
ERROR_LOG = "error.log"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHub Actions)"
}

def log(msg):
    print(msg)

def log_error(msg):
    ts = datetime.now().isoformat()
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print("ERROR:", msg)

def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:80]

def main():
    os.makedirs(THREAD_DIR, exist_ok=True)

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            log_error(f"state.json 読み込み失敗: {e}")

    # subject 取得
    try:
        r = requests.get(SUBJECT_URL, headers=HEADERS, timeout=15)
        data = r.json()
    except Exception as e:
        log_error(f"subject API 失敗: {e}")
        return

    subjects = data.get("subjects")
    if not isinstance(subjects, list):
        log_error(f"subjects が不正: {data}")
        return

    target = None
    for s in subjects:
        title = s.get("title", "")
        if THREAD_KEYWORD in title:
            target = s
            break

    if not target:
        log("対象スレなし（正常終了）")
        return

    # dat番号取得（key/dat 両対応）
    dat = target.get("key") or target.get("dat")
    if not dat:
        log_error(f"dat番号が取得できない: {target}")
        return

    title = target.get("title", "unknown")

    # dat取得
    dat_url = f"{DAT_BASE_URL}/{dat}.json"
    try:
        r = requests.get(dat_url, headers=HEADERS, timeout=15)
        dat_json = r.json()
    except Exception as e:
        log_error(f"DAT取得失敗 {dat}: {e}")
        return

    posts = dat_json.get("res")
    if not isinstance(posts, list) or not posts:
        log_error(f"レス無し or 不正 {dat}: {dat_json}")
        return

    filename = f"{dat}_{safe_filename(title)}.txt"
    filepath = os.path.join(THREAD_DIR, filename)

    last_read = state.get(dat, 0)
    new_count = 0

    with open(filepath, "a", encoding="utf-8") as f:
        for p in posts:
            num = p.get("number", 0)
            if num <= last_read:
                continue

            f.write(
                f"### {num}\n"
                f"NAME: {p.get('name','')}\n"
                f"MAIL: {p.get('mail','')}\n"
                f"DATE: {p.get('date','')}\n"
                f"{p.get('message','')}\n\n"
            )
            new_count += 1

    state[dat] = posts[-1].get("number", last_read)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    log(f"保存完了: {filepath} / 追加 {new_count}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        log_error(traceback.format_exc())
