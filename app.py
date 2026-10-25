import json
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="【回収テスト】語彙実験", layout="centered")

# 発行していただいたGoogle Apps ScriptのURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzZhBUlm_MniZCLGkDiPblGx_VAsCahYGwJQNr_UI7yGUs-PixItMlBLl9d0HxfXsY4/exec"

# テスト用の2単語
TEST_WORDS = [
    {"en": "apple", "ja": "りんご"},
    {"en": "banana", "ja": "バナナ"},
]

# セッション状態の初期化
if "phase" not in st.session_state:
    st.session_state.phase = "START"
    st.session_state.current_idx = 0
    st.session_state.answers = []
    st.session_state.user_name = ""
    st.session_state.group = ""

st.title("🧪 スプレッドシート自動回収テスト")

# --- ステップ0: 参加登録 ---
if st.session_state.phase == "START":
    st.info("テスト用のため、2問ですぐ終了します。")
    name = st.text_input("テスト用ID:", value="test_user01")
    group = st.selectbox(
        "テストグループ:", ["20語全習群", "4語分習・長間隔群", "4語分習・短間隔群"]
    )

    if st.button("テスト開始"):
        if name:
            st.session_state.user_name = name
            st.session_state.group = group
            st.session_state.phase = "PRESENTATION"
            st.rerun()

# --- ステップ1: 初回提示 (テスト用に2秒) ---
elif st.session_state.phase == "PRESENTATION":
    idx = st.session_state.current_idx
    word = TEST_WORDS[idx]

    st.subheader(f"単語 {idx + 1} / {len(TEST_WORDS)} (提示)")
    st.markdown(f"## 英単語: **`{word['en']}`**")
    st.markdown(f"## 日本語: **`{word['ja']}`**")

    bar = st.progress(1.0)
    for i in range(20, 0, -1):
        time.sleep(0.1)
        bar.progress(i / 20.0)

    if idx + 1 < len(TEST_WORDS):
        st.session_state.current_idx += 1
        st.rerun()
    else:
        st.session_state.current_idx = 0
        st.session_state.phase = "RECALL"
        st.rerun()

# --- ステップ2: タイピング回答 ---
elif st.session_state.phase == "RECALL":
    idx = st.session_state.current_idx
    word = TEST_WORDS[idx]

    st.subheader(f"タイピング {idx + 1} / {len(TEST_WORDS)}")
    st.markdown(f"## 日本語: **`{word['ja']}`**")

    with st.form(key=f"test_form_{idx}"):
        user_input = st.text_input("英単語を入力:")
        submitted = st.form_submit_button("回答送信")

        if submitted:
            is_correct = user_input.strip().lower() == word["en"].lower()
            st.session_state.last_input = user_input

            st.session_state.answers.append({
                "participant": st.session_state.user_name,
                "group": st.session_state.group,
                "word_en": word["en"],
                "word_ja": word["ja"],
                "user_input": user_input,
                "is_correct": is_correct,
            })
            st.session_state.phase = "FEEDBACK"
            st.rerun()

# --- ステップ3: フィードバック (1秒) ---
elif st.session_state.phase == "FEEDBACK":
    idx = st.session_state.current_idx
    word = TEST_WORDS[idx]

    st.subheader("【フィードバック】")
    st.success(f"正解: **`{word['en']}`**")
    st.info(f"あなたの入力: **`{st.session_state.last_input}`**")

    time.sleep(1.0)

    if idx + 1 < len(TEST_WORDS):
        st.session_state.current_idx += 1
        st.session_state.phase = "RECALL"
        st.rerun()
    else:
        st.session_state.phase = "FINISHED"
        st.rerun()

# --- ステップ4: 完了 ＆ Googleスプレッドシートへ自動送信 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("テストセッションが完了しました！")

    if "submitted" not in st.session_state:
        # 送信データの作成
        payload = {
            "participant": st.session_state.user_name,
            "group": st.session_state.group,
            "summary": "テスト回収完了 (2問)",
            "raw_data": json.dumps(
                st.session_state.answers, ensure_ascii=False
            ),
        }

        try:
            # GASのURLにJSONデータをPOST送信
            res = requests.post(GAS_URL, json=payload, timeout=10)
            if "SUCCESS" in res.text:
                st.session_state.submitted = True
                st.success(
                    "✅ スプレッドシートにデータが正常に追記されました！"
                )
            else:
                st.session_state.submitted = True
                st.info(
                    "✅ 送信完了しました（スプレッドシートをご確認ください）。"
                )
        except Exception as e:
            st.error(f"❌ 通信エラー: {e}")

    st.info(
        "Googleスプレッドシートを開いて、新しい行が自動で追加されたか確認してください。"
    )
