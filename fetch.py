import json
import os
import re
import requests
from datetime import datetime

# =====================
# 設定
# =====================
BASE_DIR = "threads"
STATE_FILE = "state.json"
ERROR_LOG = "error.log"

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
    }
}

# =====================
# ユーティリティ
# =====================
def log_error(msg: str):
    ts = datetime.now().isoformat()
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def safe_filename(text: str) -> str:
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:80]

def get_text(url: str) -> str:
    r = requests.get("https://r.jina.ai/" + url, timeout=20)
    r.raise_for_status()
    return r.text

def extract_latest_thread(board_text: str, keyword: str):
    for line in board_text.splitlines():
        if keyword in line:
            m = re.search(
                r'https://[^ ]+/test/read.cgi/[^/]+/(\d+)/(.+?)</a>',
                line
            )
            if m:
                return m.group(1), m.group(2)
    return None, None

def extract_last_res(thread_text: str) -> int:
    matches = re.findall(r'^\d+', thread_text, re.MULTILINE)
    if matches:
        return int(matches[-1])
    return 0

# =====================
# 初期化
# =====================
os.makedirs(BASE_DIR, exist_ok=True)

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {}

# =====================
# メイン処理
# =====================
for name, cfg in TARGETS.items():
    try:
        os.makedirs(f"{BASE_DIR}/{name}", exist_ok=True)

        board_text = get_text(cfg["board"])
        dat, title = extract_latest_thread(board_text, cfg["keyword"])

        if not dat:
            log_error(f"{name}: スレ取得失敗")
            continue

        prev = state.get(name, {})
        prev_dat = prev.get("dat")
        last_res = prev.get("last_res", 0)

        # 次スレ判定
        if dat != prev_dat:
            last_res = 0

        board_host = cfg["board"].split("/")[2]
        board_name = cfg["board"].rstrip("/").split("/")[-1]

        thread_url = (
            f"https://{board_host}/test/read.cgi/"
            f"{board_name}/{dat}/{last_res + 1}-"
        )

        thread_text = get_text(thread_url)
        new_last_res = extract_last_res(thread_text)

        if new_last_res > last_res:
            safe_title = safe_filename(title)
            filename = f"{dat}_{safe_title}.txt"
            path = f"{BASE_DIR}/{name}/{filename}"

            with open(path, "a", encoding="utf-8") as f:
                f.write(thread_text)

            state[name] = {
                "dat": dat,
                "last_res": new_last_res
            }

            print(f"✅ 更新: {name} ({last_res+1}-{new_last_res})")

    except Exception as e:
        log_error(f"{name}: {e}")

# =====================
# state 保存
# =====================
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
