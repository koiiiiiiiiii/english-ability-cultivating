import streamlit as st
import random
import string
import io
import time

# 尝试导入 gTTS，如果没有安装也不会报错，只是没声音
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

# ==========================================
# 1. 专业特训题库 (Curriculum Database)
# ==========================================
# 这是一个模拟的专业数据库，包含了分级和语法专项分类
TRAINING_DATABASE = {
    "基础巩固 (Primary/Junior)": {
        "时态专项": [
            {"en": "I have been waiting for you for two hours.", "zh": "我已经等你两个小时了。", "focus": "现在完成进行时"},
            {"en": "She was reading a book when the phone rang.", "zh": "电话响的时候她正在看书。", "focus": "过去进行时"},
        ],
        "被动语态": [
            {"en": "The window was broken by the naughty boy.", "zh": "窗户被那个淘气的男孩打破了。", "focus": "一般过去时的被动"},
            {"en": "English is spoken all over the world.", "zh": "全世界都说英语。", "focus": "一般现在时的被动"},
        ]
    },
    "大学英语 (CET-4/6)": {
        "虚拟语气": [
            {"en": "If I were you, I would not accept the offer.", "zh": "如果我是你，我就不会接受这个提议。", "focus": "与现在事实相反"},
            {"en": "I wish I had known the truth earlier.", "zh": "我要是早点知道真相就好了。", "focus": "wish宾语从句"},
            {"en": "Had he worked harder, he would have passed the exam.", "zh": "如果他更努力一点，他就通过考试了。", "focus": "省略if的倒装"},
        ],
        "定语从句": [
            {"en": "He is the only person that I can trust.", "zh": "他是唯一我可以信任的人。", "focus": "that引导"},
            {"en": "The house, whose roof was damaged, has been repaired.", "zh": "那所屋顶受损的房子已经修好了。", "focus": "whose引导"},
        ]
    },
    "出国留学 (IELTS/TOEFL)": {
        "倒装与强调": [
            {"en": "Not only is the problem complex, but it is also urgent.", "zh": "这个问题不仅复杂，而且紧迫。", "focus": "部分倒装"},
            {"en": "It was primarily due to his negligence that the accident occurred.", "zh": "主要是因为他的疏忽，事故才发生的。", "focus": "强调句型"},
            {"en": "Seldom have we seen such a magnificent view.", "zh": "我们很少看到如此壮丽的景色。", "focus": "否定副词倒装"},
        ],
        "学术长难句": [
            {"en": "The correlation between poverty and crime is a subject of intense debate.", "zh": "贫困与犯罪之间的相关性是一个激烈争论的话题。", "focus": "抽象名词主语"},
            {"en": "Despite the overwhelming evidence, some skeptics remain unconvinced.", "zh": "尽管有压倒性的证据，一些怀疑论者仍然不信服。", "focus": "让步状语"},
        ]
    }
}

# ==========================================
# 2. CSS 美化注入 (Visual Overhaul)
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
        /* 全局背景与字体 */
        .stApp {
            background-color: #f8f9fa;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        /* 隐藏 Streamlit 默认的丑陋元素 */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* 卡片容器样式 */
        .training-card {
            background-color: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            border-left: 5px solid #4F8BF9;
        }

        /* 标题与标签 */
        .focus-badge {
            background-color: #E3F2FD;
            color: #1565C0;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .chinese-text {
            font-size: 22px;
            color: #2c3e50;
            font-weight: 600;
            margin: 15px 0;
            line-height: 1.5;
        }

        /* 单词槽位样式 */
        .word-container {
            line-height: 2.5;
            font-size: 18px;
        }
        .word-normal {
            margin: 0 4px;
            color: #333;
        }
        .word-gap {
            display: inline-block;
            min-width: 60px;
            border-bottom: 2px dashed #4F8BF9;
            text-align: center;
            color: #4F8BF9;
            font-weight: bold;
            margin: 0 5px;
            padding: 0 5px;
        }
        
        /* 结果反馈 */
        .result-correct { color: #2ecc71; font-weight: bold; }
        .result-wrong { color: #e74c3c; font-weight: bold; }

        /* 输入框美化 (Streamlit 的 input 很难改，只能尽量) */
        div[data-testid="stTextInput"] input {
            border-radius: 8px;
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
            font-size: 16px;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #4F8BF9;
            box-shadow: 0 0 0 1px #4F8BF9;
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 核心逻辑
# ==========================================

@st.cache_data
def get_tts_audio(text):
    if not HAS_GTTS: return None
    try:
        tts = gTTS(text=text, lang='en')
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf
    except:
        return None

def get_masked_indices(words, difficulty_mode):
    """根据模式决定挖空逻辑"""
    indices = []
    # 排除标点和太短的词
    candidates = [i for i, w in enumerate(words) if len(w) > 2 and w.isalnum()]
    
    if not candidates: return []

    # 简单的逻辑：每隔几个词挖一个
    if difficulty_mode == "Hard":
        count = int(len(candidates) * 0.6) # 挖 60%
    else:
        count = int(len(candidates) * 0.3) # 挖 30%
    
    if count < 1: count = 1
    return sorted(random.sample(candidates, count))

# ==========================================
# 4. 页面 UI 构建
# ==========================================

st.set_page_config(page_title="英语语法特训营", page_icon="🚀", layout="centered")
inject_custom_css()

# --- 侧边栏：特训配置 ---
st.sidebar.title("⚙️ 特训设置")
st.sidebar.markdown("根据你的目标选择专项训练内容。")

selected_level = st.sidebar.selectbox("1️⃣ 选择等级", list(TRAINING_DATABASE.keys()))
available_topics = list(TRAINING_DATABASE[selected_level].keys())
selected_topic = st.sidebar.selectbox("2️⃣ 选择专项", available_topics)

difficulty = st.sidebar.radio("3️⃣ 挖空难度", ["Normal (填关键词)", "Hard (深度听写)"])

st.sidebar.divider()
st.sidebar.caption("🚀 Powered by English Spec-Trainer")

# --- 获取当前题库 ---
current_questions = TRAINING_DATABASE[selected_level][selected_topic]

# --- Session State 初始化 ---
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = selected_topic

# 如果切换了 topic，重置进度
if st.session_state.current_topic != selected_topic:
    st.session_state.current_topic = selected_topic
    st.session_state.q_idx = 0
    st.session_state.user_answers = {}
    st.session_state.check = False
    st.session_state.masks = []

# 确保索引安全
if st.session_state.q_idx >= len(current_questions):
    st.session_state.q_idx = 0

# 获取当前题目数据
q_data = current_questions[st.session_state.q_idx]
words = q_data['en'].split()

# 生成挖空 (只在每一题开始时生成一次)
if 'masks' not in st.session_state or not st.session_state.masks:
    st.session_state.masks = get_masked_indices(words, difficulty)
    st.session_state.user_answers = {}
    st.session_state.check = False

# ==========================================
# 5. 主展示区 (Main Display)
# ==========================================

# 顶部进度条
progress = (st.session_state.q_idx + 1) / len(current_questions)
st.progress(progress)
st.caption(f"Mission Progress: {st.session_state.q_idx + 1} / {len(current_questions)}")

# --- 题目卡片 ---
st.markdown(f"""
<div class="training-card">
    <span class="focus-badge">{selected_topic} | {q_data['focus']}</span>
    <div class="chinese-text">{q_data['zh']}</div>
</div>
""", unsafe_allow_html=True)

# 音频播放
col_audio, col_hint = st.columns([3, 1])
with col_audio:
    audio_data = get_tts_audio(q_data['en'])
    if audio_data:
        st.audio(audio_data, format='audio/mp3')
    else:
        st.warning("语音生成失败 (请检查 gTTS)")

# --- 填空交互区 ---
st.markdown("### ✍️ Listen & Fill")

# 1. 视觉预览 (Visual Preview of the Sentence)
preview_html = "<div class='word-container'>"
for i, w in enumerate(words):
    if i in st.session_state.masks:
        # 如果是挖空位置，显示序号
        preview_html += f"<span class='word-gap'>{i+1}</span>"
    else:
        preview_html += f"<span class='word-normal'>{w}</span>"
preview_html += "</div>"
st.markdown(preview_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 2. 输入表单 (Input Form)
with st.form("training_form"):
    # 使用网格布局让输入框整齐排列
    cols = st.columns(3)
    sorted_masks = sorted(st.session_state.masks)
    
    for idx, mask_idx in enumerate(sorted_masks):
        col = cols[idx % 3]
        with col:
            # 以前的输入保留
            prev_val = st.session_state.user_answers.get(mask_idx, "")
            user_in = st.text_input(
                f"Gap {mask_idx+1}", 
                value=prev_val,
                key=f"in_{mask_idx}",
                label_visibility="collapsed", # 隐藏自带label，更清爽
                placeholder=f"No.{mask_idx+1} word"
            )
            st.session_state.user_answers[mask_idx] = user_in
    
    st.markdown("<br>", unsafe_allow_html=True)
    submit = st.form_submit_button("✅ Check Answer", type="primary", use_container_width=True)

# ==========================================
# 6. 结果与导航
# ==========================================

if submit:
    st.session_state.check = True

if st.session_state.check:
    st.markdown("---")
    st.subheader("📊 Result Analysis")
    
    all_right = True
    # 结果展示容器
    res_cols = st.columns(2)
    
    sorted_masks = sorted(st.session_state.masks)
    for i, mask_idx in enumerate(sorted_masks):
        u_val = st.session_state.user_answers.get(mask_idx, "").strip().lower()
        # 去除标点比较
        c_val = words[mask_idx].strip(string.punctuation).lower()
        original_word = words[mask_idx]
        
        col_res = res_cols[i % 2]
        with col_res:
            if u_val == c_val:
                st.markdown(f"✅ **Gap {mask_idx+1}:** <span class='result-correct'>{original_word}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"❌ **Gap {mask_idx+1}:** <span class='result-wrong'>{u_val}</span> → <b>{original_word}</b>", unsafe_allow_html=True)
                all_right = False
    
    if all_right:
        st.success("🎉 Perfect! Excellent listening skills.")
    else:
        st.info("💪 Keep going! Review the mistakes above.")

st.markdown("<br>", unsafe_allow_html=True)

# 下一题按钮 (独立在外)
if st.button("➡️ Next Mission", use_container_width=True):
    if st.session_state.q_idx < len(current_questions) - 1:
        st.session_state.q_idx += 1
    else:
        st.session_state.q_idx = 0
        st.toast("Round Complete! Restarting from beginning.")
    
    # Reset state
    st.session_state.masks = []
    st.session_state.check = False
    st.rerun()