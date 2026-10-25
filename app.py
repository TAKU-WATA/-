import json
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="【回収テスト用】語彙実験", layout="centered")

# テスト用の2単語のみ
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

st.title("🧪 データ回収テスト（短縮版）")

# --- ステップ0: 参加登録 ---
if st.session_state.phase == "START":
    st.info("テスト用のため、2問・各数秒ですぐ終了します。")
    name = st.text_input("テスト用ID (例: test01):", value="test_user")
    group = st.selectbox(
        "テストグループ:", ["20語全習群", "4語分習・長間隔群", "4語分習・短間隔群"]
    )

    if st.button("テスト開始"):
        if name:
            st.session_state.user_name = name
            st.session_state.group = group
            st.session_state.phase = "PRESENTATION"
            st.rerun()

# --- ステップ1: 初回提示 (テスト用に2秒短縮) ---
elif st.session_state.phase == "PRESENTATION":
    idx = st.session_state.current_idx
    word = TEST_WORDS[idx]

    st.subheader(f"単語 {idx + 1} / {len(TEST_WORDS)} (提示)")
    st.markdown(f"## 英単語: **`{word['en']}`**")
    st.markdown(f"## 日本語: **`{word['ja']}`**")

    # 2秒タイマー
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
        user_input = st.text_input("英単語を半角小文字で入力:")
        submitted = st.form_submit_button("回答送信")

        if submitted:
            is_correct = user_input.strip().lower() == word["en"].lower()
            st.session_state.last_input = user_input
            st.session_state.last_correct = is_correct

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

# --- ステップ3: フィードバック (テスト用に1秒短縮) ---
elif st.session_state.phase == "FEEDBACK":
    idx = st.session_state.current_idx
    word = TEST_WORDS[idx]

    st.subheader("【フィードバック】")
    st.success(f"正解: **`{word['en']}`**")
    st.info(f"あなたの入力: **`{st.session_state.last_input}`**")

    # 1秒タイマー
    time.sleep(1.0)

    if idx + 1 < len(TEST_WORDS):
        st.session_state.current_idx += 1
        st.session_state.phase = "RECALL"
        st.rerun()
    else:
        st.session_state.phase = "FINISHED"
        st.rerun()

# --- ステップ4: 完了 ＆ Googleスプレッドシートへ送信 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("テストセッションが完了しました！")

    if "submitted" not in st.session_state:
        FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeeuvuH2cOpsxX_gGrzdocksTtfEYkh7DRa7-KFQPhyTP2gKQ/formResponse"

        logs_json = json.dumps(
            st.session_state.answers, ensure_ascii=False, indent=2
        )

        form_data = {
            "entry.1991852866": st.session_state.user_name,
            "entry.809893665": st.session_state.group,
            "entry.1328811381": "テスト回収完了 (2問)",
            "entry.504388348": logs_json,
        }

        try:
            # 診断用送信
            res = requests.post(FORM_URL, data=form_data, timeout=10)

            # 結果ステータスを表示
            if res.status_code == 200:
                st.success(
                    "✅ Googleから「受付完了(200)」が返ってきました！スプレッドシートを確認してください。"
                )
                st.session_state.submitted = True
            else:
                st.error(
                    f"❌ Google側で受信が拒否されました。ステータスコード: {res.status_code}"
                )
                with st.expander("詳細エラー内容を見る"):
                    st.write(res.text[:600])
        except Exception as e:
            st.error(f"❌ 通信エラー: {e}")
