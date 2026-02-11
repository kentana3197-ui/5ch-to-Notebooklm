import requests
import os
import json
import unicodedata
from datetime import datetime

# ==================================
# 監視対象
# ==================================
TARGETS = {
    "liveuranus_nanjnva": {
        "board": "liveuranus",
        "keywords": ["なんJNVA"]
    },
    "cg_grok_bring": {
        "board": "cg",
        "keywords": ["Grok", "持ち込み"]
    },
    "cg_comfyui": {
        "board": "cg",
        "keywords": ["ComfyUI"]
    },
    "cg_grok_2ji": {
        "board": "cg",
        "keywords": ["Grok", "2次"]
    },
    "cg_grok_general": {
        "board": "cg",
        "keywords": ["Grok", "総合"]
    },
    "cg_ai_questions": {
        "board": "cg",
        "keywords": ["画像生成AI", "質問"]
    },
    "jisaku_rtx50": {
        "board": "jisaku",
        "keywords": ["RTX50"]
    }
}

STATE_FILE = "state.json"
OUTPUT_DIR = "threads"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================================
# 正規化
# ==================================
def normalize(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = text.replace(" ", "").replace("　", "")
    return text

# ==================================
# 最新スレ検出（最大dat優先）
# ==================================
def find_latest_thread(board, keywords):

    url = f"https://{board}.5ch.net/{board}/subject.txt"
    r = requests.get(url, headers=HEADERS)
    r.encoding = "shift_jis"

    normalized_keywords = [normalize(k) for k in keywords]

    candidates = []

    for line in r.text.splitlines():
        dat, title = line.split(".dat<>")
        norm_title = normalize(title)

        # すべてのキーワードを含む場合のみ
        if all(kw in norm_title for kw in normalized_keywords):
            candidates.append((int(dat), title))

    if not candidates:
        return None, None

    # dat最大（＝最新スレ）
    latest = max(candidates, key=lambda x: x[0])
    return str(latest[0]), latest[1]

# ==================================
# state読み込み
# ==================================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {}

# ==================================
# メイン処理
# ==================================
for name, cfg in TARGETS.items():

    board = cfg["board"]
    keywords = cfg["keywords"]

    os.makedirs(f"{OUTPUT_DIR}/{name}", exist_ok=True)

    latest_dat, title = find_latest_thread(board, keywords)

    if not latest_dat:
        print("スレ未検出:", name)
        continue

    saved = state.get(name, {})
    old_dat = saved.get("dat")
    last_res = saved.get("last_res", 0)

    
# ★ ここに追加 ★
print("DEBUG:", name)
print("  latest_dat:", latest_dat)
print("  old_dat:", old_dat)
print("  last_res:", last_res)

    # 次スレ検出
    if old_dat != latest_dat:
        print("次スレ検出:", name)
        last_res = 0

    dat_url = f"https://{board}.5ch.net/{board}/dat/{latest_dat}.dat"
    r = requests.get(dat_url, headers=HEADERS)

    if r.status_code != 200:
        print("dat取得失敗:", name)
        continue

    r.encoding = "shift_jis"
    lines = r.text.splitlines()
    total_res = len(lines)

    if total_res > last_res:

        new_lines = lines[last_res:]

        now = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        path = f"{OUTPUT_DIR}/{name}/{now}_{last_res+1}-{total_res}.txt"

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\n\n")
            f.write("\n".join(new_lines))

        state[name] = {
            "dat": latest_dat,
            "last_res": total_res
        }

        print("取得:", name, last_res+1, "→", total_res)

# ==================================
# state保存
# ==================================
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

