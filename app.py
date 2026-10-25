import random
import time
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="語彙学習実験2 (Nakata & Webb, 2016)", layout="centered"
)

# ターゲット20語 + フィラー3語 (実験2の英単語リスト)
TARGET_WORDS = [
    {"id": 1, "en": "apparition", "ja": "亡霊"},
    {"id": 2, "en": "billow", "ja": "大波"},
    {"id": 3, "en": "cadge", "ja": "ねだる"},
    {"id": 4, "en": "citadel", "ja": "要塞"},
    {"id": 5, "en": "dally", "ja": "時間を浪費する"},
    {"id": 6, "en": "fawn", "ja": "へつらう"},
    {"id": 7, "en": "fracas", "ja": "大騒ぎ"},
    {"id": 8, "en": "gouge", "ja": "削り取る"},
    {"id": 9, "en": "grig", "ja": "元気のよい人"},
    {"id": 10, "en": "levee", "ja": "堤防"},
    {"id": 11, "en": "loach", "ja": "ドジョウ"},
    {"id": 12, "en": "mane", "ja": "たてがみ"},
    {"id": 13, "en": "mirth", "ja": "陽気"},
    {"id": 14, "en": "nadir", "ja": "どん底"},
    {"id": 15, "en": "pique", "ja": "怒らせる"},
    {"id": 16, "en": "quail", "ja": "尻込みする"},
    {"id": 17, "en": "rue", "ja": "後悔する"},
    {"id": 18, "en": "scowl", "ja": "にらみつける"},
    {"id": 19, "en": "toupee", "ja": "かつら"},
    {"id": 20, "en": "warble", "ja": "さえずる"},
]

FILLER_WORDS = [
    {"id": 21, "en": "promontory", "ja": "岬"},
    {"id": 22, "en": "urn", "ja": "骨壺"},
    {"id": 23, "en": "vestige", "ja": "面影"},
]

WORD_DICT = {w["id"]: w for w in TARGET_WORDS + FILLER_WORDS}


# --- 実験2の試行スケジュール生成 (Table 5 準拠) ---
def generate_schedule(group):
    trials = []

    def get_shuffled_block(start_id, end_id):
        ids = list(range(start_id, end_id + 1))
        random.shuffle(ids)
        return ids

    def get_shuffled_fillers(count):
        pool = [2, 6, 7]
        res = []
        while len(res) < count:
            random.shuffle(pool)
            res.extend(pool)
        return res[:count]

    if group == "20語全習群 (Whole)":
        # Primacy 11 fillers
        for fid in get_shuffled_fillers(11):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })
        # Cycle 1: 1-20 初回提示 (8s)
        for wid in get_shuffled_block(1, 20):
            trials.append(
                {"id": wid, "type": "PRES", "label": "初回提示 (8秒)"}
            )
        # Cycle 2 - 5: 1-20 産出想起 (タイピング + 5s FB)
        for c in range(2, 6):
            for wid in get_shuffled_block(1, 20):
                trials.append({
                    "id": wid,
                    "type": "PROD",
                    "label": f"想起練習 {c-1}/4",
                })
        # Recency 3 fillers
        for fid in get_shuffled_fillers(3):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })

    elif group == "4語分習・長間隔群 (Part-Long)":
        # Primacy 3 fillers
        for fid in get_shuffled_fillers(3):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })
        # Cycle 1 - 10: 4語ずつの提示と想起1回目
        for b in range(5):
            s, e = b * 4 + 1, b * 4 + 4
            for wid in get_shuffled_block(s, e):
                trials.append(
                    {"id": wid, "type": "PRES", "label": "初回提示 (8秒)"}
                )
            for wid in get_shuffled_block(s, e):
                trials.append(
                    {"id": wid, "type": "PROD", "label": "想起練習 1/4"}
                )
        # 8 fillers
        for fid in get_shuffled_fillers(8):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })
        # Cycle 11 - 20: 4語ずつの想起2回目・3回目
        for b in range(5):
            s, e = b * 4 + 1, b * 4 + 4
            for wid in get_shuffled_block(s, e):
                trials.append(
                    {"id": wid, "type": "PROD", "label": "想起練習 2/4"}
                )
            for wid in get_shuffled_block(s, e):
                trials.append(
                    {"id": wid, "type": "PROD", "label": "想起練習 3/4"}
                )
        # Final Review 1-20 (想起4回目)
        for wid in get_shuffled_block(1, 20):
            trials.append({"id": wid, "type": "PROD", "label": "想起練習 4/4"})
        # Recency 3 fillers
        for fid in get_shuffled_fillers(3):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })

    elif group == "4語分習・短間隔群 (Control)":
        # Primacy 11 fillers
        for fid in get_shuffled_fillers(11):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })
        # 5つの4語ブロックで、提示 + 4回想起を連続実施
        for b in range(5):
            s, e = b * 4 + 1, b * 4 + 4
            for wid in get_shuffled_block(s, e):
                trials.append(
                    {"id": wid, "type": "PRES", "label": "初回提示 (8秒)"}
                )
            for c in range(1, 5):
                for wid in get_shuffled_block(s, e):
                    trials.append({
                        "id": wid,
                        "type": "PROD",
                        "label": f"想起練習 {c}/4",
                    })
        # Recency 3 fillers
        for fid in get_shuffled_fillers(3):
            trials.append({
                "id": fid,
                "type": "FILL_PROD",
                "label": "バッファー試行",
            })

    return trials


# --- セッション初期化 ---
if "phase" not in st.session_state:
    st.session_state.phase = "START"
    st.session_state.trial_idx = 0
    st.session_state.schedule = []
    st.session_state.logs = []
    st.session_state.user_name = ""
    st.session_state.group = ""

st.title("語彙学習実験2 (Nakata & Webb, 2016)")

# --- ステップ0: 被験者情報 ＆ グループ選択 ---
if st.session_state.phase == "START":
    st.markdown("### 実験への参加登録")
    name = st.text_input("参加者ID / 氏名:")
    group = st.selectbox(
        "実験グループを選択してください:",
        [
            "20語全習群 (Whole)",
            "4語分習・長間隔群 (Part-Long)",
            "4語分習・短間隔群 (Control)",
        ],
    )
    if st.button("実験セッションを開始"):
        if name:
            st.session_state.user_name = name
            st.session_state.group = group
            st.session_state.schedule = generate_schedule(group)
            st.session_state.trial_idx = 0
            st.session_state.phase = "RUN_TRIAL"
            st.rerun()
        else:
            st.warning("IDを入力してください。")

# --- ステップ1: 各試行の実行 ---
elif st.session_state.phase == "RUN_TRIAL":
    idx = st.session_state.trial_idx
    total = len(st.session_state.schedule)
    cur = st.session_state.schedule[idx]
    word = WORD_DICT[cur["id"]]

    st.caption(
        f"進行状況: {idx + 1} / {total} 試行 ｜ グループ: {st.session_state.group}"
    )

    # 1. 初回提示試行 (8秒間)
    if cur["type"] == "PRES":
        st.subheader(f"【{cur['label']}】単語の学習")
        st.markdown(f"## 英単語: **`{word['en']}`**")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")
        st.info("英単語と日本語訳の組み合わせを覚えてください。")

        bar = st.progress(1.0)
        for i in range(80, 0, -1):
            time.sleep(0.1)
            bar.progress(i / 80.0)

        if idx + 1 < total:
            st.session_state.trial_idx += 1
            st.rerun()
        else:
            st.session_state.phase = "FINISHED"
            st.rerun()

    # 2. 産出想起試行 (タイピング)
    elif cur["type"] in ["PROD", "FILL_PROD"]:
        st.subheader(f"【{cur['label']}】")
        st.markdown(f"## 日本語訳: **`{word['ja']}`**")

        with st.form(key=f"prod_form_{idx}"):
            ans = st.text_input("対応する英単語を半角小文字でタイピング:")
            submitted = st.form_submit_button("回答送信")

            if submitted:
                is_correct = ans.strip().lower() == word["en"].lower()
                st.session_state.last_ans = ans
                st.session_state.last_correct = is_correct

                # ログ記録
                st.session_state.logs.append({
                    "participant": st.session_state.user_name,
                    "group": st.session_state.group,
                    "trial_num": idx + 1,
                    "word_id": word["id"],
                    "word_en": word["en"],
                    "word_ja": word["ja"],
                    "trial_type": cur["type"],
                    "label": cur["label"],
                    "user_input": ans,
                    "is_correct_strict": is_correct,
                })
                st.session_state.phase = "FEEDBACK"
                st.rerun()

# --- ステップ2: 5秒間フィードバック ---
elif st.session_state.phase == "FEEDBACK":
    idx = st.session_state.trial_idx
    total = len(st.session_state.schedule)
    cur = st.session_state.schedule[idx]
    word = WORD_DICT[cur["id"]]

    st.subheader("【5秒間フィードバック】")
    st.success(f"正解の英単語: **`{word['en']}`**")
    st.info(f"日本語訳: **`{word['ja']}`**")
    st.warning(f"あなたの入力: **`{st.session_state.last_ans}`**")

    bar = st.progress(1.0)
    for i in range(50, 0, -1):
        time.sleep(0.1)
        bar.progress(i / 50.0)

    if idx + 1 < total:
        st.session_state.trial_idx += 1
        st.session_state.phase = "RUN_TRIAL"
        st.rerun()
    else:
        st.session_state.phase = "FINISHED"
        st.rerun()

# --- ステップ3: 完了 ＆ CSV保存 ---
elif st.session_state.phase == "FINISHED":
    st.balloons()
    st.success("すべての学習セッションが完了しました！")

    df = pd.DataFrame(st.session_state.logs)
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="学習ログデータ(CSV)をダウンロード",
        data=csv,
        file_name=f"result_{st.session_state.group}_{st.session_state.user_name}.csv",
        mime="text/csv",
    )
