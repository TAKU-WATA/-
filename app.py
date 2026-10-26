import json
import random
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="語彙学習実験2 (5サイクル本格版)",
    layout="centered"
)

# Google Apps ScriptのWebアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzZhBUlm_MniZCLGkDiPblGx_VAsCahYGwJQNr_UI7yGUs-PixItMlBLl9d0HxfXsY4/exec"

# ターゲット4語 ＋ バッファー1語
TARGET_WORDS = [
    {"id": 1, "en": "billow", "ja": "大波"},
    {"id": 2, "en": "fracas", "ja": "大騒ぎ"},
    {"id": 3, "en": "loach", "ja": "ドジョウ"},
    {"id": 4, "en": "toupee", "ja": "かつら"},
]
FILLER_WORD = {"id": 99, "en": "vestige", "ja": "面影"}
WORD_DICT = {w["id"]: w for w in TARGET_WORDS + [FILLER_WORD]}

# --- 5サイクル学習スケジュール生成 ---
def generate_schedule(group):
    trials = []
    w_ids = [1, 2, 3, 4]       # 全体4語
    b1_ids = [1, 2]            # ブロック1 (2語)
    b2_ids = [3, 4]            # ブロック2 (2語)

    def shuffle_list(lst):
        res = list(lst)
        random.shuffle(res)
        return res

    if "全習群" in group:
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PRES", "cycle": 1, "label": "第1段階: 初回提示 (4秒)"})
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 2, "label": "第2段階: 想起練習 1/4"})
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 3, "label": "第3段階: 想起練習 2/4"})
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 4, "label": "第4段階: 想起練習 3/4"})
        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 5, "label": "第5段階: 想起練習 4/4 (最終復習)"})

    elif "長間隔" in group:
        for wid in shuffle_list(b1_ids):
            trials.append({"id": wid, "type": "PRES", "cycle": 1, "label": "第1段階: 初回提示 (4秒)"})
        for wid in shuffle_list(b1_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 2, "label": "第2段階: 想起練習 1/4"})
        
        for wid in shuffle_list(b2_ids):
            trials.append({"id": wid, "type": "PRES", "cycle": 1, "label": "第1段階: 初回提示 (4秒)"})
        for wid in shuffle_list(b2_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 2, "label": "第2段階: 想起練習 1/4"})

        for wid in shuffle_list(b1_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 3, "label": "第3段階: 想起練習 2/4"})
        for wid in shuffle_list(b1_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 4, "label": "第4段階: 想起練習 3/4"})
            
        for wid in shuffle_list(b2_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 3, "label": "第3段階: 想起練習 2/4"})
        for wid in shuffle_list(b2_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 4, "label": "第4段階: 想起練習 3/4"})

        for wid in shuffle_list(w_ids):
            trials.append({"id": wid, "type": "PROD", "cycle": 5, "label": "第5段階: 想起練習 4/4 (最終復習)"})

    elif "短間隔" in group or "Control" in group:
        for b in [b1_ids, b2_ids]:
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

st.title("語彙学習実験2 (5段階学習セッション)")

# --- URLパラメータの自動判定 ---
# 例: ?group=whole, ?group=part_long, ?group=control
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
    st.info("計5回の学習サイクル（初回提示 ＋ 4回の想起練習）を行います。所要時間は約2〜3分です。")
    
    name = st.text_input("学籍番号 または お名前:")

    # URLでグループが指定されている場合は自動確定（選択肢を出さない）
    if assigned_group:
        group = assigned_group
        st.success(f"あなたの割り当てグループ: **{group}**（自動設定済み）")
    else:
        # URLに指定がない場合のみプルダウンで選択
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

    # 初回提示 (4秒)
    if cur["type"] == "PRES":
        st.subheader(f"【{cur['label']}】単語の学習")
        st.markdown(f"## 英単語: **`{word['en']}`**")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")
        st.info("英単語と日本語訳の組み合わせを覚えてください。")
        
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

    # 産出想起 (タイピング)
    elif cur["type"] == "PROD":
        st.subheader(f"【{cur['label']}】")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")

        with st.form(key=f"prod_form_{idx}"):
            ans = st.text_input("対応する英単語を半角小文字で入力:")
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
        st.success(f"⭕ 正解！ 英単語: **`{word['en']}`**")
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

# --- ステップ3: 完了 ＆ スプレッドシート自動保存 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("すべての学習セッションが完了しました！お疲れ様でした。")

    c2_cor = sum(1 for log in st.session_state.logs if log.get("cycle") == 2 and log.get("is_correct"))
    c3_cor = sum(1 for log in st.session_state.logs if log.get("cycle") == 3 and log.get("is_correct"))
    c4_cor = sum(1 for log in st.session_state.logs if log.get("cycle") == 4 and log.get("is_correct"))
    c5_cor = sum(1 for log in st.session_state.logs if log.get("cycle") == 5 and log.get("is_correct"))
    total_cor = sum(1 for log in st.session_state.logs if log.get("is_correct"))
    
    score_summary = f"総計:{total_cor}/16 (想起1:{c2_cor}/4, 想起2:{c3_cor}/4, 想起3:{c4_cor}/4, 想起4:{c5_cor}/4)"

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

    st.markdown(f"### あなたの想起スコア内訳:\n**{score_summary}**")
    st.info("✅ データは自動でスプレッドシートに保存されました。続けて直後テスト用のGoogleフォームに進んでください。")
