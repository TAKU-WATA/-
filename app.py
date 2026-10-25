import time
import pandas as pd
import streamlit as st

# 画面設定
st.set_page_config(
    page_title="語彙学習実験 (Nakata & Webb, 2016)", layout="centered"
)

# 単語リスト（20ターゲット語 + 3ダミー語）
VOCAB_LIST = [
    {"en": "apparition", "ja": "亡霊"},
    {"en": "citadel", "ja": "要塞"},
    {"en": "diaspora", "ja": "集団離散"},
    {"en": "effigy", "ja": "肖像"},
    {"en": "grotto", "ja": "洞窟"},
    {"en": "horde", "ja": "大群"},
    {"en": "juggernaut", "ja": "不可抗力"},
    {"en": "kaleidoscope", "ja": "万華鏡"},
    {"en": "labyrinth", "ja": "迷宮"},
    {"en": "mane", "ja": "たてがみ"},
    {"en": "necropolis", "ja": "巨大墓地"},
    {"en": "oasis", "ja": "オアシス"},
    {"en": "palisade", "ja": "杭垣"},
    {"en": "quagmire", "ja": "泥沼"},
    {"en": "sanctuary", "ja": "聖域"},
    {"en": "tapestry", "ja": "タペストリー"},
    {"en": "utopia", "ja": "理想郷"},
    {"en": "vortex", "ja": "渦潮"},
    {"en": "wasteland", "ja": "荒野"},
    {"en": "zenith", "ja": "頂点"},
    {"en": "urn", "ja": "骨壺"},
    {"en": "vestige", "ja": "面影"},
    {"en": "promontory", "ja": "岬"},
]

# セッション状態の初期化
if "phase" not in st.session_state:
    st.session_state.phase = "START"
    st.session_state.current_idx = 0
    st.session_state.answers = []
    st.session_state.user_name = ""

st.title("語彙学習実験セッション")

# --- ステップ0: 被験者情報入力 ---
if st.session_state.phase == "START":
    st.write("実験を開始します。お名前または学籍番号を入力してください。")
    name = st.text_input("参加者ID / 氏名:")
    if st.button("実験開始"):
        if name:
            st.session_state.user_name = name
            st.session_state.phase = "INITIAL_PRESENTATION"
            st.rerun()
        else:
            st.warning("IDを入力してください。")

# --- ステップ1: 第1試行 (初回提示 - 8秒間同時表示) ---
elif st.session_state.phase == "INITIAL_PRESENTATION":
    idx = st.session_state.current_idx
    word = VOCAB_LIST[idx]

    st.subheader(f"単語 {idx + 1} / {len(VOCAB_LIST)} (初回提示)")
    st.markdown(f"### **英単語:** `{word['en']}`")
    st.markdown(f"### **日本語訳:** `{word['ja']}`")

    # 8秒間のカウントダウンタイマー
    progress_bar = st.progress(1.0)
    for i in range(80, 0, -1):
        time.sleep(0.1)
        progress_bar.progress(i / 80.0)

    # 次の単語またはタイピング練習へ移行
    if idx + 1 < len(VOCAB_LIST):
        st.session_state.current_idx += 1
        st.rerun()
    else:
        st.session_state.current_idx = 0
        st.session_state.phase = "RECALL_INPUT"
        st.rerun()

# --- ステップ2: 産出タイピング練習 ---
elif st.session_state.phase == "RECALL_INPUT":
    idx = st.session_state.current_idx
    word = VOCAB_LIST[idx]

    st.subheader(f"タイピング練習 {idx + 1} / {len(VOCAB_LIST)}")
    st.markdown(f"### **日本語訳:** `{word['ja']}`")

    with st.form(key=f"recall_form_{idx}"):
        user_input = st.text_input(
            "対応する英単語をタイピングしてください:", key=f"input_{idx}"
        )
        submit_button = st.form_submit_button("回答送信")

        if submit_button:
            st.session_state.last_input = user_input
            st.session_state.answers.append({
                "participant": st.session_state.user_name,
                "word_en": word["en"],
                "word_ja": word["ja"],
                "user_input": user_input,
                "is_correct": user_input.strip().lower()
                == word["en"].lower(),
            })
            st.session_state.phase = "FEEDBACK"
            st.rerun()

# --- ステップ3: 5秒間フィードバック ---
elif st.session_state.phase == "FEEDBACK":
    idx = st.session_state.current_idx
    word = VOCAB_LIST[idx]
    user_input = st.session_state.last_input

    st.subheader("【5秒間フィードバック】")
    st.success(f"正解の英単語: **{word['en']}**")
    st.info(f"日本語訳: **{word['ja']}**")
    st.warning(f"あなたの回答: **{user_input}**")

    # 5秒間のカウントダウン
    progress_bar = st.progress(1.0)
    for i in range(50, 0, -1):
        time.sleep(0.1)
        progress_bar.progress(i / 50.0)

    if idx + 1 < len(VOCAB_LIST):
        st.session_state.current_idx += 1
        st.session_state.phase = "RECALL_INPUT"
        st.rerun()
    else:
        st.session_state.phase = "FINISHED"
        st.rerun()

# --- ステップ4: 実験終了 ＆ データ保存 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("実験セッションがすべて完了しました！お疲れ様でした。")

    # 回答データのCSV化
    df = pd.DataFrame(st.session_state.answers)
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="解答データ(CSV)をダウンロード",
        data=csv,
        file_name=f"result_{st.session_state.user_name}.csv",
        mime="text/csv",
    )
