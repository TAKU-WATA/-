import streamlit as st
import random
import time

# ==========================================
# ページ基本設定
# ==========================================
st.set_page_config(
    page_title="語彙学習実験アプリ（スワヒリ語・4択版）",
    page_icon="🔤",
    layout="centered"
)

# ==========================================
# 単語データ（ターゲット10語 ＋ ダミー2語 ＝ 計12語）
# ==========================================
WORDS = [
    {"ja": "心", "sw": "moyo", "is_buffer": True},       # 初頭バッファー語
    {"ja": "敵", "sw": "adui", "is_buffer": False},      # ターゲット語 1
    {"ja": "馬", "sw": "farasi", "is_buffer": False},    # ターゲット語 2
    {"ja": "湖", "sw": "ziwa", "is_buffer": False},      # ターゲット語 3
    {"ja": "鳥", "sw": "ndege", "is_buffer": False},     # ターゲット語 4
    {"ja": "ライオン", "sw": "simba", "is_buffer": False},# ターゲット語 5
    {"ja": "魚", "sw": "samaki", "is_buffer": False},   # ターゲット語 6
    {"ja": "家", "sw": "nyumba", "is_buffer": False},   # ターゲット語 7
    {"ja": "火", "sw": "moto", "is_buffer": False},     # ターゲット語 8
    {"ja": "本", "sw": "kitabu", "is_buffer": False},   # ターゲット語 9
    {"ja": "机", "sw": "meza", "is_buffer": False},     # ターゲット語 10
    {"ja": "頭", "sw": "kichwa", "is_buffer": True}      # 終末バッファー語
]

ALL_SWAHILI = [w["sw"] for w in WORDS]

# 4択の選択肢を生成する関数
def get_choices(correct_sw):
    distractors = [sw for sw in ALL_SWAHILI if sw != correct_sw]
    wrong_choices = random.sample(distractors, 3)
    choices = wrong_choices + [correct_sw]
    random.shuffle(choices)
    return choices

# ==========================================
# セッション状態の初期化
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = "login"  # login -> ready -> study -> finished
if "student_id" not in st.session_state:
    st.session_state.student_id = ""
if "group" not in st.session_state:
    st.session_state.group = ""
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "cycle" not in st.session_state:
    st.session_state.cycle = 1
if "block" not in st.session_state:
    st.session_state.block = 1
if "choices" not in st.session_state:
    st.session_state.choices = []
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# URLクエリパラメータからグループを判別
query_params = st.query_params
url_group = query_params.get("group", None)

# ==========================================
# 画面1: ログイン & グループ選択
# ==========================================
if st.session_state.step == "login":
    st.title("🔤 スワヒリ語 語彙学習セッション")
    st.write("画面の指示に従って、日本語に対応するスワヒリ語の意味を学習してください。")

    st.subheader("基本情報の入力")
    st.session_state.student_id = st.text_input("学籍番号 または お名前", value=st.session_state.student_id)

    # URL引数があれば自動選択、無ければ手動選択
    group_options = {
        "whole": "全習群 (Whole)",
        "part_long": "分習・長間隔群 (Part-Long)",
        "control": "分習・短間隔群 (Control)"
    }
    
    default_index = 0
    if url_group in group_options:
        default_index = list(group_options.keys()).index(url_group)

    selected_group_key = st.selectbox(
        "参加グループを選んでください",
        options=list(group_options.keys()),
        format_func=lambda x: group_options[x],
        index=default_index
    )
    st.session_state.group = selected_group_key

    if st.button("次へ進む ➔", type="primary"):
        if not st.session_state.student_id.strip():
            st.warning("学籍番号またはお名前を入力してください。")
        else:
            st.session_state.step = "ready"
            st.rerun()

# ==========================================
# 画面2: 準備画面（注意事項とスタートボタン）
# ==========================================
elif st.session_state.step == "ready":
    st.title("💡 学習開始の準備")
    st.info("""
    **【学習の進め方】**
    1. 最初に、単語ペアが**4秒間ずつ自動で表示**されます（初回提示）。しっかり覚えてください。
    2. その後、日本語に対応するスワヒリ語を答える**4択テスト（4サイクル）**を行います。
    
    準備ができたら、下のボタンを押して学習を開始してください。
    """)

    if st.button("準備完了（単語学習を開始） ➔", type="primary", use_container_width=True):
        st.session_state.step = "study"
        st.session_state.current_index = 0
        st.session_state.cycle = 1
        st.session_state.block = 1
        st.rerun()

# ==========================================
# 画面3: 学習セッション (初回4秒バー提示 ➔ 4択復習)
# ==========================================
elif st.session_state.step == "study":
    # グループごとのリスト管理（全習：12語全一括 / 分習：4語×3ブロック）
    if st.session_state.group == "whole":
        current_words = WORDS
    else:  # part_long or control
        b = st.session_state.block
        if b == 1:
            current_words = WORDS[0:4]
        elif b == 2:
            current_words = WORDS[4:8]
        else:
            current_words = WORDS[8:12]

    total_in_block = len(current_words)
    idx = st.session_state.current_index
    word_obj = current_words[idx]

    # 進捗ステータス表示
    st.caption(f"グループ: {st.session_state.group.upper()} | ブロック {st.session_state.block}/3 | サイクル {st.session_state.cycle}/5")

    st.markdown("---")

    # --------------------------------------------------
    # 【サイクル 1】：初回提示（4秒間のバータイマー自動表示）
    # --------------------------------------------------
    if st.session_state.cycle == 1:
        st.info("💡 【初回提示】単語ペアをしっかり覚えてください（4秒後に自動で切り替わります）。")
        
        st.markdown(f"### 日本語: **【 {word_obj['ja']} 】**")
        st.markdown(f"### スワヒリ語: **【 {word_obj['sw']} 】**")
        st.write("")

        # 4秒間のカウントダウンプログレスバー
        progress_bar = st.progress(1.0)
        for t in range(40, 0, -1):
            time.sleep(0.1)
            progress_bar.progress(t / 40.0)

        # 4秒経過後に自動遷移
        if idx + 1 < total_in_block:
            st.session_state.current_index += 1
        else:
            # サイクル1完了 ➔ サイクル2（4択テスト）へ移行
            st.session_state.current_index = 0
            st.session_state.cycle += 1
            next_word = current_words[0]
            st.session_state.choices = get_choices(next_word["sw"])
        st.rerun()

    # --------------------------------------------------
    # 【サイクル 2〜5】：4択復習テストフェーズ
    # --------------------------------------------------
    else:
        st.markdown(f"### 日本語: **【 {word_obj['ja']} 】**")
        st.write("対応するスワヒリ語を以下から1つ選んでください：")

        # 4択ボタンの配置
        cols = st.columns(2)
        for i, choice in enumerate(st.session_state.choices):
            col = cols[i % 2]
            if col.button(f"**{choice}**", key=f"choice_{i}", use_container_width=True):
                if choice == word_obj["sw"]:
                    st.session_state.feedback = ("correct", f"⭕ 正解！ 「{word_obj['ja']}」 = **{word_obj['sw']}**")
                else:
                    st.session_state.feedback = ("incorrect", f"❌ 残念！ 正解は **{word_obj['sw']}** でした。")

        # フィードバック表示と次への遷移
        if st.session_state.feedback is not None:
            status, msg = st.session_state.feedback
            if status == "correct":
                st.success(msg)
            else:
                st.error(msg)

            if st.button("次の問題へ ➔", type="primary"):
                st.session_state.feedback = None
                
                # 次の単語・サイクルの更新ロジック
                if idx + 1 < total_in_block:
                    st.session_state.current_index += 1
                else:
                    # ブロック内の単語が一巡完了
                    st.session_state.current_index = 0
                    if st.session_state.cycle < 5:
                        st.session_state.cycle += 1
                    else:
                        # 5サイクル完了
                        st.session_state.cycle = 1
                        if st.session_state.group != "whole" and st.session_state.block < 3:
                            st.session_state.block += 1
                        else:
                            # 全学習セッション終了
                            st.session_state.step = "finished"
                
                # 次の問題用の選択肢を用意してリロード
                if st.session_state.step == "study":
                    if st.session_state.group != "whole":
                        b = st.session_state.block
                        if b == 1:
                            next_words = WORDS[0:4]
                        elif b == 2:
                            next_words = WORDS[4:8]
                        else:
                            next_words = WORDS[8:12]
                    else:
                        next_words = WORDS
                    next_word = next_words[st.session_state.current_index]
                    st.session_state.choices = get_choices(next_word["sw"])
                st.rerun()

# ==========================================
# 画面4: 学習完了
# ==========================================
elif st.session_state.step == "finished":
    st.balloons()
    st.title("🎉 学習セッションが完了しました！")
    st.success("お疲れ様でした！すべての単語学習が終了しました。")
    st.info("画面を閉じ、実験者の指示に従ってください。")
