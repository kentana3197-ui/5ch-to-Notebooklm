import os
import re
import json
import requests
from datetime import datetime

# =====================
# 設定
# =====================
BOARD = "liveuranus"
THREAD_KEYWORD = "なんJ"

BASE_SUBJECT_URL = f"https://itest.5ch.net/public/newapi/subject/{BOARD}.json"
BASE_DAT_URL = f"https://itest.5ch.net/public/newapi/dat/{BOARD}"

THREAD_DIR = "threads"
STATE_FILE = "state.json"
ERROR_LOG = "error.log"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHub Actions)"
}

# =====================
# ユーティリティ
# =====================
def safe_filename(text: str) -> str:
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:80]

def log_error(message: str):
    timestamp = datetime.now().isoformat()
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

# =====================
# メイン処理
# =====================
def main():
    # threads ディレクトリ作成
    os.makedirs(THREAD_DIR, exist_ok=True)

    # state 読み込み
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {}

    # スレ一覧取得
    try:
        res = requests.get(BASE_SUBJECT_URL, headers=HEADERS, timeout=15)
        res.raise_for_status()
        subjects = res.json().get("subjects", [])
    except Exception as e:
        log_error(f"スレ一覧取得失敗: {e}")
        raise SystemExit(1)

    # 対象スレ検索
    target = None
    for s in subjects:
        title = s.get("title", "")
        if THREAD_KEYWORD in title:
            target = s
            break

    if not target:
        log_error("対象スレが見つかりません")
        return

    dat = target["key"]
    title = target["title"]

    # DAT取得
    dat_url = f"{BASE_DAT_URL}/{dat}.json"

    try:
        res = requests.get(dat_url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        dat_json = res.json()
    except Exception as e:
        log_error(f"DAT取得失敗 ({dat}): {e}")
        raise SystemExit(1)

    posts = dat_json.get("res", [])
    if not posts:
        log_error(f"レスが空です ({dat})")
        return

    # ファイル名（dat番号入り）
    safe_title = safe_filename(title)
    filename = f"{dat}_{safe_title}.txt"
    filepath = os.path.join(THREAD_DIR, filename)

    # 既読レス番号
    last_read = state.get(dat, 0)

    # NotebookLM最適フォーマットで追記
    written = 0
    with open(filepath, "a", encoding="utf-8") as f:
        for p in posts:
            num = p.get("number", 0)
            if num <= last_read:
                continue

            name = p.get("name", "")
            mail = p.get("mail", "")
            date = p.get("date", "")
            body = p.get("message", "")

            f.write(
                f"### {num}\n"
                f"NAME: {name}\n"
                f"MAIL: {mail}\n"
                f"DATE: {date}\n"
                f"{body}\n\n"
            )
            written += 1

    # state 更新
    state[dat] = posts[-1]["number"]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"✅ 保存完了: {filepath}（新規 {written} 件）")

# =====================
# エントリーポイント
# =====================
if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log_error(traceback.format_exc())
        raise
