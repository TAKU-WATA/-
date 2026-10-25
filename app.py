import json
import random
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="語彙学習実験 (ゼミ短縮版)",
    layout="centered"
)

# 先ほど発行されたGoogle Apps ScriptのURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzZhBUlm_MniZCLGkDiPblGx_VAsCahYGwJQNr_UI7yGUs-PixItMlBLl9d0HxfXsY4/exec"

# 実験2から抜粋したターゲット4語 ＋ バッファー1語
TARGET_WORDS = [
    {"id": 1, "en": "apparition", "ja": "亡霊"},
    {"id": 2, "en": "citadel", "ja": "要塞"},
    {"id": 3, "en": "mane", "ja": "たてがみ"},
    {"id": 4, "en": "scowl", "ja": "にらみつける"},
]
FILLER_WORD = {"id": 99, "en": "urn", "ja": "骨壺"}
WORD_DICT = {w["id"]: w for w in TARGET_WORDS + [FILLER_WORD]}

# --- 1分版スケジュール生成 (3群の構造を再現) ---
def generate_schedule(group):
    trials = []
    
    if group == "全習群 (Whole)":
        # 4語まとめて提示 → 4語まとめて想起1回目 → 4語まとめて想起2回目 (長間隔)
        w_ids = [1, 2, 3, 4]
        for wid in sorted(w_ids, key=lambda _: random.random()):
            trials.append({"id": wid, "type": "PRES", "label": "初回提示 (4秒)"})
        for wid in sorted(w_ids, key=lambda _: random.random()):
            trials.append({"id": wid, "type": "PROD", "label": "想起練習 1/2"})
        for wid in sorted(w_ids, key=lambda _: random.random()):
            trials.append({"id": wid, "type": "PROD", "label": "想起練習 2/2"})
            
    elif group == "分習・長間隔群 (Part-Long)":
        # 2語ずつ提示・想起するが、間に別ブロックを挟んで復習間隔を空ける
        # ブロック1提示
        for wid in [1, 2]:
            trials.append({"id": wid, "type": "PRES", "label": "初回提示 (4秒)"})
        # ブロック2提示
        for wid in [3, 4]:
            trials.append({"id": wid, "type": "PRES", "label": "初回提示 (4秒)"})
        # ブロック1想起1回目
        for wid in [1, 2]:
            trials.append({"id": wid, "type": "PROD", "label": "想起練習 1/2"})
        # ブロック2想起1回目
        for wid in [3, 4]:
            trials.append({"id": wid, "type": "PROD", "label": "想起練習 1/2"})
        # 全体まとめ想起2回目
        for wid in sorted([1, 2, 3, 4], key=lambda _: random.random()):
            trials.append({"id": wid, "type": "PROD", "label": "想起練習 2/2"})
            
    elif group == "分習・短間隔群 (Control)":
        # 2語ごとに「提示 → 想起1 → 想起2」を連続で完結させる (短間隔・集中学習)
        for b in [[1, 2], [3, 4]]:
            for wid in b:
                trials.append({"id": wid, "type": "PRES", "label": "初回提示 (4秒)"})
            for wid in b:
                trials.append({"id": wid, "type": "PROD", "label": "想起練習 1/2"})
            for wid in b:
                trials.append({"id": wid, "type": "PROD", "label": "想起練習 2/2"})
                
    return trials

# --- セッション初期化 ---
if "phase" not in st.session_state:
    st.session_state.phase = "START"
    st.session_state.trial_idx = 0
    st.session_state.schedule = []
    st.session_state.logs = []
    st.session_state.user_name = ""
    st.session_state.group = ""

st.title("語彙学習実験 (約1分)")

# --- ステップ0: 参加登録 ---
if st.session_state.phase == "START":
    st.info("約1分間で終了する短い英単語学習実験です。")
    name = st.text_input("学籍番号 または お名前:")
    group = st.selectbox(
        "指定された実験グループを選択してください:",
        ["全習群 (Whole)", "分習・長間隔群 (Part-Long)", "分習・短間隔群 (Control)"]
    )
    if st.button("実験を開始する"):
        if name:
            st.session_state.user_name = name
            st.session_state.group = group
            st.session_state.schedule = generate_schedule(group)
            st.session_state.trial_idx = 0
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

    st.caption(f"進捗: {idx + 1} / {total} ｜ グループ: {st.session_state.group}")

    # 初回提示 (テンポよく4秒)
    if cur["type"] == "PRES":
        st.subheader(f"【{cur['label']}】単語を覚えてください")
        st.markdown(f"## 英単語: **`{word['en']}`**")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")
        
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
                    "participant": st.session_state.user_name,
                    "group": st.session_state.group,
                    "trial_num": idx + 1,
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

    # 2秒タイマー
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

# --- ステップ3: 完了 ＆ スプレッドシートへ自動保存 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("すべての実験が完了しました！ご協力ありがとうございました。")

    if "submitted" not in st.session_state:
        payload = {
            "participant": st.session_state.user_name,
            "group": st.session_state.group,
            "summary": f"短縮本番完了 ({len(st.session_state.logs)}試行)",
            "raw_data": json.dumps(st.session_state.logs, ensure_ascii=False)
        }
        try:
            requests.post(GAS_URL, json=payload, timeout=10)
            st.session_state.submitted = True
        except Exception:
            st.session_state.submitted = False

    st.info("✅ 回答データは自動でスプレッドシートに送信されました。このブラウザタブは閉じていただいて構いません。")
