import streamlit as st
import random
import time
import requests
from datetime import datetime

# ==========================================
# ⚙️ 設定: Google Apps Script (GAS) Web App URL
# ==========================================
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxaFlqVTvyWqodma1pA-AB1Lm8-TsxWcBErl2VplO7495Y6CSxDtyt0cNMvWyiH2CE/exec"

# ==========================================
# ページ基本設定
# ==========================================
st.set_page_config(
    page_title="語彙学習実験アプリ（スワヒリ語・14語4択版）",
    page_icon="🔤",
    layout="centered"
)

# ==========================================
# 単語データ（ターゲット12語 ＋ ダミー2語 ＝ 計14語）
# ==========================================
WORDS = [
    {"ja": "心", "sw": "moyo", "is_buffer": True},       # 初頭バッファー語
    {"ja": "敵", "sw": "adui", "is_buffer": False},      # ターゲット語 1 (ブロック1)
    {"ja": "馬", "sw": "farasi", "is_buffer": False},    # ターゲット語 2 (ブロック1)
    {"ja": "湖", "sw": "ziwa", "is_buffer": False},      # ターゲット語 3 (ブロック1)
    {"ja": "鳥", "sw": "ndege", "is_buffer": False},     # ターゲット語 4 (ブロック1)
    {"ja": "ライオン", "sw": "simba", "is_buffer": False},# ターゲット語 5 (ブロック2)
    {"ja": "魚", "sw": "samaki", "is_buffer": False},   # ターゲット語 6 (ブロック2)
    {"ja": "家", "sw": "nyumba", "is_buffer": False},   # ターゲット語 7 (ブロック2)
    {"ja": "火", "sw": "moto", "is_buffer": False},     # ターゲット語 8 (ブロック2)
    {"ja": "本", "sw": "kitabu", "is_buffer": False},   # ターゲット語 9 (ブロック3)
    {"ja": "机", "sw": "meza", "is_buffer": False},     # ターゲット語 10 (ブロック3)
    {"ja": "ナイフ", "sw": "kisu", "is_buffer": False},   # ターゲット語 11 (ブロック3)
    {"ja": "塩", "sw": "chumvi", "is_buffer": False},   # ターゲット語 12 (ブロック3)
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

# グループとブロックに応じた現在の単語リストを取得
def get_current_words(group, block):
    if group == "whole":
        return WORDS
    else:
        if block == 1:
            return WORDS[0:5]    # バッファー1 + ターゲット1〜4 (計5語)
        elif block == 2:
            return WORDS[5:9]    # ターゲット5〜8 (計4語)
        else:
            return WORDS[9:14]   # ターゲット9〜12 + バッファー1 (計5語)

# スプレッドシートへの詳細データ送信関数
def send_results_to_gas(student_id, group, score, total_questions, cycle_scores):
    if not GAS_WEB_APP_URL:
        return False
    
    accuracy = round((score / total_questions) * 100, 1) if total_questions > 0 else 0
    
    def get_c_info(c):
        sc = cycle_scores.get(c, {"score": 0, "total": 0})
        acc = round((sc["score"] / sc["total"]) * 100, 1) if sc["total"] > 0 else 0
        return f"{sc['score']}/{sc['total']}", acc

    c2_str, c2_acc = get_c_info(2)
    c3_str, c3_acc = get_c_info(3)
    c4_str, c4_acc = get_c_info(4)
    c5_str, c5_acc = get_c_info(5)

    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "student_id": student_id,
        "group": group,
        "score": score,
        "total_questions": total_questions,
        "accuracy": accuracy,
        "c2_score": c2_str,
        "c2_acc": c2_acc,
        "c3_score": c3_str,
        "c3_acc": c3_acc,
        "c4_score": c4_str,
        "c4_acc": c4_acc,
        "c5_score": c5_str,
        "c5_acc": c5_acc,
    }
    try:
        res = requests.post(GAS_WEB_APP_URL, json=payload, timeout=5)
        return res.status_code == 200
    except Exception:
        return False

# ==========================================
# セッション状態の初期化
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = "login"
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
if "word_order" not in st.session_state:
    st.session_state.word_order = []
if "choices" not in st.session_state:
    st.session_state.choices = []
if "score" not in st.session_state:
    st.session_state.score = 0
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "cycle_scores" not in st.session_state:
    st.session_state.cycle_scores = {
        2: {"score": 0, "total": 0},
        3: {"score": 0, "total": 0},
        4: {"score": 0, "total": 0},
        5: {"score": 0, "total": 0}
    }
if "data_sent" not in st.session_state:
    st.session_state.data_sent = False

# URLクエリパラメータからグループを判別
url_group = None
try:
    if "group" in st.query_params:
        param_val = st.query_params["group"]
        if isinstance(param_val, list):
            param_val = param_val
        url_group = str(param_val).strip()
except Exception:
    pass

# ==========================================
# 画面1: ログイン & グループ選択
# ==========================================
if st.session_state.step == "login":
    st.title("🔤 スワヒリ語 語彙学習セッション")
    st.write("画面の指示に従って、日本語に対応するスワヒリ語の意味を学習してください。")

    st.subheader("基本情報の入力")

    group_options = {
        "whole": "全習群 (Whole)",
        "part_long": "分習・長間隔群 (Part-Long)",
        "control": "分習・短間隔群 (Control)"
    }
    
    is_locked = url_group in group_options
    if is_locked:
        selected_group_key = url_group
        st.session_state.group = url_group
        st.info(f"🔒 **グループ: {group_options[url_group]} に自動指定されています。**")
    else:
        selected_group_key = st.selectbox(
            "参加グループを選んでください",
            options=list(group_options.keys()),
            format_func=lambda x: group_options[x],
            index=0
        )
        st.session_state.group = selected_group_key

    student_input = st.text_input("学籍番号 または お名前", value=st.session_state.student_id)

    start_clicked = st.button("学習を開始する", type="primary")

    if (start_clicked or (student_input and student_input != st.session_state.student_id)):
        if not student_input.strip():
            st.warning("学籍番号またはお名前を入力してください。")
        else:
            st.session_state.student_id = student_input.strip()
            st.session_state.step = "study"
            st.session_state.current_index = 0
            st.session_state.cycle = 1
            st.session_state.block = 1
            st.session_state.word_order = []
            st.session_state.score = 0
            st.session_state.total_questions = 0
            st.session_state.cycle_scores = {
                2: {"score": 0, "total": 0},
                3: {"score": 0, "total": 0},
                4: {"score": 0, "total": 0},
                5: {"score": 0, "total": 0}
            }
            st.session_state.data_sent = False
            st.rerun()

# ==========================================
# 画面2: 学習セッション
# ==========================================
elif st.session_state.step == "study":
    current_words = get_current_words(st.session_state.group, st.session_state.block)
    total_in_block = len(current_words)
    
    # 提示順の初期化・更新（サイクル1は固定、サイクル2〜5はランダムシャッフル）
    if not st.session_state.word_order or len(st.session_state.word_order) != total_in_block:
        if st.session_state.cycle == 1:
            st.session_state.word_order = list(range(total_in_block))
        else:
            order = list(range(total_in_block))
            random.shuffle(order)
            st.session_state.word_order = order

    idx = st.session_state.current_index
    actual_idx = st.session_state.word_order[idx]
    word_obj = current_words[actual_idx]

    # 進捗ステータス表示
    total_blocks = 1 if st.session_state.group == "whole" else 3
    st.caption(f"グループ: {st.session_state.group.upper()} | ブロック {st.session_state.block}/{total_blocks} | サイクル {st.session_state.cycle}/5")
    st.markdown("---")

    # --------------------------------------------------
    # 【サイクル 1】：初回提示（ボタンなし・4秒バー自動切り替え）
    # --------------------------------------------------
    if st.session_state.cycle == 1:
        st.info("💡 【初回提示】単語ペアをしっかり覚えてください（4秒後に自動で切り替わります）。")
        
        st.markdown(f"### 日本語: **【 {word_obj['ja']} 】**")
        st.markdown(f"### スワヒリ語: **【 {word_obj['sw']} 】**")
        st.write("")

        progress_bar = st.progress(1.0)
        for t in range(40, 0, -1):
            time.sleep(0.1)
            progress_bar.progress(t / 40.0)

        if idx + 1 < total_in_block:
            st.session_state.current_index += 1
        else:
            # サイクル1完了 ➔ サイクル2（4択復習テスト）へ移行し、順番をシャッフル
            st.session_state.current_index = 0
            st.session_state.cycle = 2
            order = list(range(total_in_block))
            random.shuffle(order)
            st.session_state.word_order = order
            
            first_word = current_words[order[0]]
            st.session_state.choices = get_choices(first_word["sw"])
        st.rerun()

    # --------------------------------------------------
    # 【サイクル 2〜5】：4択復習テスト（選択即・自動遷移＆詳細スコア集計）
    # --------------------------------------------------
    else:
        st.markdown(f"### 日本語: **【 {word_obj['ja']} 】**")
        st.write("対応するスワヒリ語を以下から1つ選んでください：")

        if not st.session_state.choices:
            st.session_state.choices = get_choices(word_obj["sw"])

        clicked_choice = None
        cols = st.columns(2)
        for i, choice in enumerate(st.session_state.choices):
            col = cols[i % 2]
            if col.button(f"**{choice}**", key=f"choice_{i}", use_container_width=True):
                clicked_choice = choice

        if clicked_choice is not None:
            c = st.session_state.cycle
            st.session_state.total_questions += 1
            st.session_state.cycle_scores[c]["total"] += 1

            if clicked_choice == word_obj["sw"]:
                st.session_state.score += 1
                st.session_state.cycle_scores[c]["score"] += 1
                st.success(f"⭕ 正解！ 「{word_obj['ja']}」 = **{word_obj['sw']}**")
            else:
                st.error(f"❌ 残念！ 正解は **{word_obj['sw']}** でした。")
            
            time.sleep(1.2)

            if idx + 1 < total_in_block:
                st.session_state.current_index += 1
                next_actual_idx = st.session_state.word_order[st.session_state.current_index]
                next_word = current_words[next_actual_idx]
                st.session_state.choices = get_choices(next_word["sw"])
            else:
                st.session_state.current_index = 0
                if st.session_state.cycle < 5:
                    st.session_state.cycle += 1
                    # 次のサイクルの出題順をランダムシャッフル
                    order = list(range(total_in_block))
                    random.shuffle(order)
                    st.session_state.word_order = order
                    
                    first_word = current_words[order[0]]
                    st.session_state.choices = get_choices(first_word["sw"])
                else:
                    st.session_state.cycle = 1
                    if st.session_state.group != "whole" and st.session_state.block < 3:
                        st.session_state.block += 1
                        next_words = get_current_words(st.session_state.group, st.session_state.block)
                        st.session_state.word_order = list(range(len(next_words)))
                    else:
                        st.session_state.step = "finished"

            st.rerun()

# ==========================================
# 画面3: 学習完了 & データ自動送信・詳細結果表示
# ==========================================
elif st.session_state.step == "finished":
    st.balloons()
    st.title("🎉 学習セッションが完了しました！")
    st.success("お疲れ様でした！すべての単語学習が終了しました。")
    
    # 詳細成績の表示
    st.subheader("📊 あなたの学習結果")
    tot = st.session_state.total_questions
    sc = st.session_state.score
    acc = round((sc / tot) * 100, 1) if tot > 0 else 0
    st.write(f"**総合正答率:** {acc}% （{sc}問 / {tot}問）")

    st.markdown("#### サイクル（回数）ごとの正答率")
    cols = st.columns(4)
    for i, c in enumerate([2, 3, 4, 5]):
        c_sc = st.session_state.cycle_scores[c]["score"]
        c_tot = st.session_state.cycle_scores[c]["total"]
        c_acc = round((c_sc / c_tot) * 100, 1) if c_tot > 0 else 0
        cols[i].metric(f"サイクル {c}", f"{c_acc}%", f"{c_sc}/{c_tot} 問")

    # 完了時に1回だけスプレッドシートへ自動送信
    if not st.session_state.data_sent:
        with st.spinner("学習データを記録中..."):
            success = send_results_to_gas(
                st.session_state.student_id,
                st.session_state.group,
                st.session_state.score,
                st.session_state.total_questions,
                st.session_state.cycle_scores
            )
            st.session_state.data_sent = True
            if success:
                st.caption("✅ 詳細な学習結果が安全に保存されました。")
            else:
                st.caption("ℹ️ （データ送信完了）")

    st.info("画面を閉じ、実験者の指示に従ってください。")
