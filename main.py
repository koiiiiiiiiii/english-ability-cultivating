import streamlit as st
import random
import string
import io
import time
import soundfile as sf
import numpy as np

# ==========================================
# 0. 环境检查与库导入
# ==========================================
try:
    from datasets import load_dataset, Audio
    from deep_translator import GoogleTranslator
    HAS_ONLINE_LIBS = True
except ImportError:
    HAS_ONLINE_LIBS = False

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

# ==========================================
# 1. 增强型数据结构 (模拟数据库)
# ==========================================
# 这里我们手动构建一批带有“等级”和“语法标签”的数据
# 在实际产品中，这些应该存储在 JSON 或 SQLite 数据库中
RICH_DATA = [
    # --- 小学/初中 (Primary/Junior) ---
    {
        "english": "My name is Tom and I like apples.",
        "chinese": "我叫汤姆，我喜欢苹果。",
        "level": "小学/初中",
        "tags": ["基础句型", "自我介绍"],
        "source": "Basic English"
    },
    {
        "english": "There is a cat under the table.",
        "chinese": "桌子底下有一只猫。",
        "level": "小学/初中",
        "tags": ["There be句型", "方位介词"],
        "source": "Grammar 101"
    },
    # --- 高中/四级 (Senior/CET-4) ---
    {
        "english": "It is important for us to learn English well.",
        "chinese": "学好英语对我们来说很重要。",
        "level": "高中/四级",
        "tags": ["形式主语", "不定式"],
        "source": "Textbook"
    },
    {
        "english": "The man who is standing there is my teacher.",
        "chinese": "站在那里的那个男人是我的老师。",
        "level": "高中/四级",
        "tags": ["定语从句", "人物描述"],
        "source": "CET-4 Listening"
    },
    # --- 六级/考研 (CET-6) ---
    {
        "english": "Had I known it earlier, I would have acted differently.",
        "chinese": "如果我早知道，我会采取不同的行动。",
        "level": "六级/考研",
        "tags": ["虚拟语气", "倒装句"],
        "source": "Classic Grammar"
    },
    {
        "english": "Whatever happens, we must remain calm.",
        "chinese": "无论发生什么，我们必须保持冷静。",
        "level": "六级/考研",
        "tags": ["让步状语从句", "情态动词"],
        "source": "News Report"
    },
    # --- 雅思/托福 (IELTS/TOEFL) ---
    {
        "english": "The proliferation of technology has significantly altered social interactions.",
        "chinese": "技术的扩散极大地改变了社会互动。",
        "level": "雅思/托福",
        "tags": ["学术写作", "长难句"],
        "source": "Academic Article"
    },
    {
        "english": "Not only did he refuse to accept the offer, but he also criticized it publicly.",
        "chinese": "他不仅拒绝接受这个提议，还公开批评了它。",
        "level": "雅思/托福",
        "tags": ["倒装句", "强调句"],
        "source": "Debate Clip"
    }
]

# ==========================================
# 2. 工具函数
# ==========================================

def get_audio_bytes(text):
    """优先使用 gTTS 生成音频，保证流畅度"""
    if HAS_GTTS:
        try:
            tts = gTTS(text=text, lang='en')
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            return mp3_fp
        except:
            return None
    return None

def filter_data(level_select, tag_select):
    """根据用户选择筛选题目"""
    filtered = []
    for item in RICH_DATA:
        # 筛选等级
        if level_select != "所有等级" and item["level"] != level_select:
            continue
        # 筛选语法标签
        if tag_select != "所有题型" and tag_select not in item["tags"]:
            continue
        filtered.append(item)
    return filtered

def clean_text(text):
    return text.strip(string.punctuation).lower()

# ==========================================
# 3. 页面主逻辑
# ==========================================

st.set_page_config(page_title="英语专项特训", page_icon="🎓", layout="centered")

# --- CSS 样式注入 (为了让输入框看起来更像填空) ---
st.markdown("""
<style>
    .stTextInput input {
        text-align: center;
        color: #4CAF50;
        font-weight: bold;
        background-color: #f0f2f6;
        border-bottom: 2px solid #4CAF50 !important;
        border-top: none !important;
        border-left: none !important;
        border-right: none !important;
        border-radius: 0 !important;
    }
    .big-chinese {
        font-size: 20px;
        font-weight: bold;
        color: #333;
        margin-bottom: 15px;
    }
    .tag-badge {
        background-color: #e0e0e0;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏：筛选控制器 ---
st.sidebar.header("🎯 特训设置")

# 1. 等级选择
levels = ["所有等级", "小学/初中", "高中/四级", "六级/考研", "雅思/托福"]
selected_level = st.sidebar.selectbox("选择难度分级", levels, index=2)

# 2. 题型选择 (动态获取所有标签)
all_tags = set()
for d in RICH_DATA:
    all_tags.update(d["tags"])
tags_list = ["所有题型"] + list(all_tags)
selected_tag = st.sidebar.selectbox("选择专项题型", tags_list)

st.sidebar.markdown("---")
st.sidebar.info("💡 提示：筛选 '六级/考研' 可以练习虚拟语气和倒装句。")

# --- 数据加载与筛选 ---
current_pool = filter_data(selected_level, selected_tag)

if not current_pool:
    st.warning("⚠️ 当前筛选条件下没有找到题目，请尝试放宽筛选条件（例如选择'所有等级'）。")
    st.stop()

# --- 状态管理 ---
if 'q_index' not in st.session_state:
    st.session_state.q_index = 0
if 'user_inputs' not in st.session_state:
    st.session_state.user_inputs = {}
if 'check_mode' not in st.session_state:
    st.session_state.check_mode = False

# 确保索引安全
if st.session_state.q_index >= len(current_pool):
    st.session_state.q_index = 0

data = current_pool[st.session_state.q_index]
words = data['english'].split()

# --- 挖空逻辑 (动态生成) ---
if 'masked_indices' not in st.session_state or st.session_state.get('last_id') != data['english']:
    # 如果换题了，重新计算挖空
    st.session_state.last_id = data['english']
    
    # 简单的难度逻辑：越难挖得越多，或者挖越长的词
    mask_prob = 0.3 # 默认
    if selected_level == "雅思/托福": mask_prob = 0.6
    elif selected_level == "小学/初中": mask_prob = 0.2
    
    indices = []
    for i, w in enumerate(words):
        # 简单的策略：随机挖空，但避开太短的词（除非是初级）
        if len(w) > 2 and random.random() < mask_prob:
            indices.append(i)
            
    if not indices: indices = [random.randint(0, len(words)-1)]
    st.session_state.masked_indices = sorted(indices)
    st.session_state.user_inputs = {} # 清空输入
    st.session_state.check_mode = False

# ==========================================
# 4. 界面核心布局
# ==========================================

st.title("🎓 英语听力语法特训")

# 显示标签
tags_html = "".join([f"<span class='tag-badge'>{t}</span>" for t in data['tags']])
st.markdown(f"{tags_html} <small style='color:grey'>{data['level']}</small>", unsafe_allow_html=True)

st.divider()

# --- 步骤 1: 中文与音频 ---
st.markdown(f"<div class='big-chinese'>{data['chinese']}</div>", unsafe_allow_html=True)

audio_file = get_audio_bytes(data['english'])
if audio_file:
    st.audio(audio_file, format='audio/mp3')

st.divider()

# --- 步骤 2: 模拟行内填空 (Inline Input Simulation) ---
# Streamlit 无法做到真正的 HTML 行内混排，我们使用“紧凑网格”来模拟
# 我们把句子拆分成 chunks，如果是填空，就放一个 text_input

st.subheader("✍️ 听音填空")

with st.form(key="cloze_form"):
    # 使用容器和列来布局
    # 为了防止一行太长，我们简单粗暴地按行处理，或者使用 wrap
    
    # 这里的逻辑是：显示一个带序号的文本预览，下面放对应的输入框
    # 这种方式在 Streamlit 中是最整洁的
    
    text_preview = []
    for i, w in enumerate(words):
        if i in st.session_state.masked_indices:
            # 挖空位置显示序号
            text_preview.append(f"**[ {i+1} ]**")
        else:
            text_preview.append(w)
    
    st.markdown(f"#### {' '.join(text_preview)}")
    st.caption("请在下方对应的编号框中输入听到的单词：")
    
    # 创建多列布局输入框 (每行放 3 个输入框)
    cols = st.columns(3)
    for idx_in_list, word_idx in enumerate(st.session_state.masked_indices):
        col = cols[idx_in_list % 3]
        with col:
            # 获取之前的输入值
            val = st.session_state.user_inputs.get(word_idx, "")
            new_val = st.text_input(
                f"填空 {word_idx+1}", 
                value=val, 
                key=f"input_{word_idx}",
                placeholder="?"
            )
            st.session_state.user_inputs[word_idx] = new_val

    submit_btn = st.form_submit_button("✅ 提交检查")

# ==========================================
# 5. 结果反馈与下一步
# ==========================================

if submit_btn:
    st.session_state.check_mode = True

if st.session_state.check_mode:
    st.info("🔍 检查结果：")
    all_correct = True
    
    # 使用列布局显示结果比对
    for idx in st.session_state.masked_indices:
        user_val = st.session_state.user_inputs.get(idx, "").strip()
        correct_val = words[idx]
        
        clean_user = clean_text(user_val)
        clean_correct = clean_text(correct_val)
        
        if clean_user == clean_correct:
            st.markdown(f"✅ **No.{idx+1}:** 正确 ({correct_val})")
        else:
            st.markdown(f"❌ **No.{idx+1}:** 你的答案 `{user_val}` -> 正确答案 **`{correct_val}`**")
            all_correct = False
            
    if all_correct:
        st.balloons()
        st.success("完美！全对！")

st.markdown("<br><br>", unsafe_allow_html=True)

# --- 独立布置的“下一步”按钮 ---
# 使用 full_width 且加大
if st.button("➡️ 下一句 (Next Sentence)", type="primary", use_container_width=True):
    # 移动到下一题
    if st.session_state.q_index < len(current_pool) - 1:
        st.session_state.q_index += 1
    else:
        st.session_state.q_index = 0 # 循环回第一题
        st.toast("已经是最后一题啦，回到开头！")
    
    # 重置状态
    st.session_state.masked_indices = [] 
    st.session_state.check_mode = False
    st.session_state.user_inputs = {}
    st.rerun()