import os
import re
import json
import requests
from datetime import datetime

BOARD = "liveuranus"
THREAD_KEYWORD = "なんJ"

BOARD_URL = f"https://itest.5ch.net/{BOARD}/"

THREAD_DIR = "threads"
STATE_FILE = "state.json"
ERROR_LOG = "error.log"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

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

    # state読み込み
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

    # 板HTML取得
    try:
        r = requests.get(BOARD_URL, headers=HEADERS, timeout=15)
        html = r.text
    except Exception as e:
        log_error(f"板取得失敗: {e}")
        return

    # スレッドURL抽出
    pattern = rf"/{BOARD}/(\d+)/"
    matches = re.findall(pattern, html)

    if not matches:
        log_error("スレッド抽出失敗")
        return

    dat = matches[0]  # 一番上のスレ

    thread_url = f"https://itest.5ch.net/{BOARD}/{dat}/"

    try:
        r = requests.get(thread_url, headers=HEADERS, timeout=15)
        thread_html = r.text
    except Exception as e:
        log_error(f"スレ取得失敗: {e}")
        return

    # タイトル抽出
    title_match = re.search(r"<title>(.*?)</title>", thread_html)
    title = title_match.group(1) if title_match else "unknown"

    filename = f"{dat}_{safe_filename(title)}.txt"
    filepath = os.path.join(THREAD_DIR, filename)

    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(thread_html)

    print("保存完了:", filepath)

if __name__ == "__main__":
    main()
