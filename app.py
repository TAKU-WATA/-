import json
import random
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="語彙学習実験2 (スワヒリ語本格版)",
    layout="centered"
)

# Google Apps ScriptのWebアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzZhBUlm_MniZCLGkDiPblGx_VAsCahYGwJQNr_UI7yGUs-PixItMlBLl9d0HxfXsY4/exec"

# --- スワヒリ語 単語リスト（20語 ＋ バッファー3語） ---
TARGET_WORDS = [
    # ブロック1
    {"id": 1, "en": "adui", "ja": "敵"},
    {"id": 2, "en": "farasi", "ja": "馬"},
    {"id": 3, "en": "ziwa", "ja": "湖"},
    {"id": 4, "en": "ndege", "ja": "鳥"},
    # ブロック2
    {"id": 5, "en": "simba", "ja": "ライオン"},
    {"id": 6, "en": "samaki", "ja": "魚"},
    {"id": 7, "en": "nyumba", "ja": "家"},
    {"id": 8, "en": "moto", "ja": "火"},
    # ブロック3
    {"id": 9, "en": "kitabu", "ja": "本"},
    {"id": 10, "en": "meza", "ja": "机"},
    {"id": 11, "en": "kisu", "ja": "ナイフ"},
    {"id": 12, "en": "chumvi", "ja": "塩"},
    # ブロック4
    {"id": 13, "en": "dawa", "ja": "薬"},
    {"id": 14, "en": "maji", "ja": "水"},
    {"id": 15, "en": "safari", "ja": "旅"},
    {"id": 16, "en": "ndizi", "ja": "バナナ"},
    # ブロック5
    {"id": 17, "en": "nguo", "ja": "服"},
    {"id": 18, "en": "mwezi", "ja": "月"},
    {"id": 19, "en": "pepo", "ja": "風"},
    {"id": 20, "en": "sahani", "ja": "皿"},
]

BUFFER_WORDS = [
    {"id": 21, "en": "moyo", "ja": "心"},
    {"id": 22, "en": "kichwa", "ja": "頭"},
    {"id": 23, "en": "kalamu", "ja": "ペン"},
]

WORD_DICT = {w["id"]: w for w in TARGET_WORDS + BUFFER_WORDS}

# --- 5サイクル学習スケジュール生成 ---
def generate_schedule(group):
    trials = []
    w_ids = [w["id"] for w in TARGET_WORDS]
    blocks = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16],
        [17, 18, 19, 20]
    ]

    def shuffle_list(lst):
        res = list(lst)
        random.shuffle(res)
        return res

    if "全習群" in group:
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PRES", "cycle": 1, "label": "第1段階: 初回提示 (4秒)"})
        for c in range(2, 6):
            for wid in shuffle_list(w_ids):
                trials.append({"id": wid, "type": "PROD", "cycle": c, "label": f"第{c}段階: 想起練習 {c-1}/4"})

    elif "長間隔" in group:
        # 各ブロックの提示＋第1回復習
        for b in blocks:
            for wid in shuffle_list(b):
                trials.append({"id": wid, "type": "PRES", "cycle": 1, "label": "第1段階: 初回提示 (4秒)"})
            for wid in shuffle_list(b):
                trials.append({"id": wid, "type": "PROD", "cycle": 2, "label": "第2段階: 想起練習 1/4"})
        
        # 間隔を空けてからの第2・3回復習
        for b in blocks:
            for wid in shuffle_list(b):
                trials.append({"id": wid, "type": "PROD", "cycle": 3, "label": "第3段階: 想起練習 2/4"})
            for wid in shuffle_list(b):
                trials.append({"id": wid, "type": "PROD", "cycle": 4, "label": "第4段階: 想起練習 3/4"})

        # 最終全シャッフル復習
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 5, "label": "第5段階: 想起練習 4/4 (最終復習)"})

    elif "短間隔" in group or "Control" in group:
        for b in blocks:
            for wid in shuffle_list(b):
                trials.append({"id": wid, "type": "PRES", "cycle": 1, "label": "第1段階: 初回提示 (4秒)"})
            for c in range(2, 6):
                for wid in shuffle_list(b):
                    trials.append({"id": wid, "type": "PROD", "cycle": c, "label": f"第{c}段階: 想起練習 {c-1}/4"})

    return trials

# --- セッション初期化 ---
if "phase" not in st.session_state:
    st.session_state.phase = "START"
    st.session_state.trial_idx = 0
    st.session_state.schedule = []
    st.session_state.logs = []
    st.session_state.user_name = ""
    st.session_state.group = ""

st.title("語彙学習実験2 (スワヒリ語セッション)")

query_params = st.query_params
url_group_param = query_params.get("group", "").lower()

group_mapping = {
    "whole": "全習群 (Whole)",
    "part_long": "分習・長間隔群 (Part-Long)",
    "control": "分習・短間隔群 (Control)",
    "1": "全習群 (Whole)",
    "2": "分習・長間隔群 (Part-Long)",
    "3": "分習・短間隔群 (Control)"
}
assigned_group = group_mapping.get(url_group_param, None)

# --- ステップ0: 参加登録 ---
if st.session_state.phase == "START":
    st.markdown("### 実験への参加登録")
    st.info("スワヒリ語20単語の学習（初回提示 ＋ 4回のタイピング練習）を行います。所要時間は約15分です。")
    
    name = st.text_input("学籍番号 または お名前:")

    if assigned_group:
        group = assigned_group
        st.success(f"あなたの割り当てグループ: **{group}**（自動設定済み）")
    else:
        group = st.selectbox(
            "指定された実験グループを選択してください:",
            ["全習群 (Whole)", "分習・長間隔群 (Part-Long)", "分習・短間隔群 (Control)"]
        )

    if st.button("学習セッションを開始する"):
        if name:
            st.session_state.user_name = name
            st.session_state.group = group
            st.session_state.schedule = generate_schedule(group)
            st.session_state.trial_idx = 0
            st.session_state.logs = []
            st.session_state.phase = "RUN_TRIAL"
            st.rerun()
        else:
            st.warning("お名前または学籍番号を入力してください。")

# --- ステップ1: 各試行の実行 ---
elif st.session_state.phase == "RUN_TRIAL":
    idx = st.session_state.trial_idx
    total = len(st.session_state.schedule)
    cur = st.session_state.schedule[idx]
    word = WORD_DICT[cur["id"]]

    st.caption(f"全体進捗: {idx + 1} / {total} 試行 ｜ グループ: {st.session_state.group}")

    if cur["type"] == "PRES":
        st.subheader(f"【{cur['label']}】単語の学習")
        st.markdown(f"## スワヒリ語: **`{word['en']}`**")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")
        st.info("単語と日本語訳の組み合わせを覚えてください。")
        
        bar = st.progress(1.0)
        for i in range(40, 0, -1):
            time.sleep(0.1)
            bar.progress(i / 40.0)

        if idx + 1 < total:
            st.session_state.trial_idx += 1
            st.rerun()
        else:
            st.session_state.phase = "FINISHED"
            st.rerun()

    elif cur["type"] == "PROD":
        st.subheader(f"【{cur['label']}】")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")

        with st.form(key=f"prod_form_{idx}"):
            ans = st.text_input("対応するスワヒリ語を半角小文字で入力:")
            submitted = st.form_submit_button("送信")

            if submitted:
                is_correct = (ans.strip().lower() == word["en"].lower())
                st.session_state.last_ans = ans
                st.session_state.last_correct = is_correct

                st.session_state.logs.append({
                    "trial_num": idx + 1,
                    "cycle": cur["cycle"],
                    "word_id": word["id"],
                    "word_en": word["en"],
                    "word_ja": word["ja"],
                    "label": cur["label"],
                    "user_input": ans,
                    "is_correct": is_correct
                })
                st.session_state.phase = "FEEDBACK"
                st.rerun()

# --- ステップ2: フィードバック (2秒) ---
elif st.session_state.phase == "FEEDBACK":
    idx = st.session_state.trial_idx
    total = len(st.session_state.schedule)
    cur = st.session_state.schedule[idx]
    word = WORD_DICT[cur["id"]]

    st.subheader("【正解の確認】")
    if st.session_state.last_correct:
        st.success(f"⭕ 正解！ スワヒリ語: **`{word['en']}`**")
    else:
        st.error(f"❌ 不正解... 正解は **`{word['en']}`** でした")
    st.info(f"日本語訳: **`{word['ja']}`** ｜ あなたの入力: **`{st.session_state.last_ans}`**")

    bar = st.progress(1.0)
    for i in range(20, 0, -1):
        time.sleep(0.1)
        bar.progress(i / 20.0)

    if idx + 1 < total:
        st.session_state.trial_idx += 1
        st.session_state.phase = "RUN_TRIAL"
        st.rerun()
    else:
        st.session_state.phase = "FINISHED"
        st.rerun()

# --- ステップ3: 完了 ＆ 自動保存 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("すべての学習セッションが完了しました！お疲れ様でした。")

    total_cor = sum(1 for log in st.session_state.logs if log.get("is_correct"))
    score_summary = f"総正解数: {total_cor} / 80試行"

    if "submitted" not in st.session_state:
        payload = {
            "participant": str(st.session_state.user_name),
            "group": str(st.session_state.group),
            "summary": score_summary,
            "raw_data": json.dumps(st.session_state.logs, ensure_ascii=False)
        }
        try:
            requests.post(GAS_URL, json=payload, timeout=10)
            st.session_state.submitted = True
        except Exception:
            st.session_state.submitted = False

    st.markdown(f"### あなたの学習スコア:\n**{score_summary}**")
    st.info("✅ データは自動でスプレッドシートに保存されました。そのまま直後テスト用フォームに進んでください。")
