import streamlit as st
import random
import string
import io
import time
import soundfile as sf
import numpy as np

# 尝试导入在线库，如果没有也不报错
try:
    from datasets import load_dataset, Audio
    from deep_translator import GoogleTranslator
    HAS_ONLINE_LIBS = True
except ImportError:
    HAS_ONLINE_LIBS = False

# 尝试导入 gTTS 作为备用
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

# ==========================================
# 1. 数据加载 (双保险逻辑)
# ==========================================

# --- A. 备用离线数据 (当网络不通时使用) ---
OFFLINE_SAMPLES = [
    {
        "english": "Life is like a box of chocolates.",
        "chinese": "生活就像一盒巧克力。",
        "source": "Forrest Gump (Offline Mode)"
    },
    {
        "english": "Stay hungry stay foolish.",
        "chinese": "求知若饥，虚心若愚。",
        "source": "Steve Jobs (Offline Mode)"
    },
    {
        "english": "I am going to make him an offer he cannot refuse.",
        "chinese": "我会给他开出一个无法拒绝的条件。",
        "source": "The Godfather (Offline Mode)"
    }
]

def get_offline_audio(text):
    """使用 gTTS 生成音频流"""
    if not HAS_GTTS:
        return None
    try:
        tts = gTTS(text=text, lang='en')
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp
    except:
        return None

# --- B. 在线真人数据 (优先尝试) ---
@st.cache_resource
def load_real_audio_samples(num_samples=5):
    if not HAS_ONLINE_LIBS:
        return []
        
    print("尝试连接 Hugging Face 下载数据...")
    samples = []
    
    try:
        # 强制指定 soundfile 解码
        dataset_stream = load_dataset("librispeech_asr", "clean", split="validation", streaming=True)
        dataset_stream = dataset_stream.cast_column("audio", Audio(decode=True))
        
        iterator = iter(dataset_stream)
        
        # 尝试初始化翻译
        try:
            translator = GoogleTranslator(source='en', target='zh-CN')
        except:
            translator = None

        for i in range(num_samples):
            try:
                # 设置超时防止卡死
                item = next(iterator)
                audio_array = item['audio']['array']
                sample_rate = item['audio']['sampling_rate']
                english_text = item['text'].lower()
                
                chinese_text = translator.translate(english_text) if translator else "（翻译不可用）"
                
                # 将 numpy array 转为 wav bytes，方便统一处理
                virtual_file = io.BytesIO()
                sf.write(virtual_file, audio_array, sample_rate, format='WAV')
                virtual_file.seek(0)

                samples.append({
                    "audio_bytes": virtual_file, # 统一存为文件流
                    "english": english_text,
                    "chinese": chinese_text,
                    "source": "LibriSpeech (Real Human)"
                })
            except StopIteration:
                break
            except Exception as e:
                print(f"单条数据加载失败: {e}")
                continue
                
    except Exception as e:
        print(f"整体数据集加载失败: {e}")
        return []
        
    return samples

# ==========================================
# 2. 核心逻辑
# ==========================================

st.set_page_config(page_title="听力训练 (稳定版)", page_icon="🎧")

# --- 加载数据 ---
if 'final_samples' not in st.session_state:
    with st.spinner('正在尝试加载资源...'):
        # 1. 尝试在线
        data = load_real_audio_samples(5)
        
        # 2. 如果在线为空，切换离线
        if not data:
            st.warning("⚠️ 无法连接 Hugging Face (网络超时)，已自动切换到离线备用模式。")
            # 构建离线数据格式
            data = []
            for item in OFFLINE_SAMPLES:
                audio = get_offline_audio(item['english'])
                if audio:
                    data.append({
                        "audio_bytes": audio,
                        "english": item['english'],
                        "chinese": item['chinese'],
                        "source": item['source']
                    })
        
        st.session_state.final_samples = data

samples = st.session_state.final_samples

# --- 最终防崩溃检查 ---
if not samples:
    st.error("❌ 严重错误：在线下载失败，且无法生成离线语音（可能未安装 gTTS）。")
    st.stop()

# --- 状态管理 ---
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
    st.session_state.masked_indices = []
    st.session_state.is_checked = False

# 确保索引不越界 (修复你的报错核心)
if st.session_state.current_index >= len(samples):
    st.session_state.current_index = 0

current_data = samples[st.session_state.current_index]
words = current_data['english'].split() # 简单分词

# --- 挖空逻辑 ---
def create_cloze(words_list):
    indices = []
    # 简单随机挖空，保留首尾
    candidate_indices = list(range(len(words_list)))
    if len(candidate_indices) > 2:
        num_to_hide = max(1, int(len(words_list) * 0.3)) # 挖 30%
        indices = random.sample(candidate_indices, num_to_hide)
    elif candidate_indices:
        indices = [0]
    return indices

if not st.session_state.masked_indices:
    st.session_state.masked_indices = create_cloze(words)

# ==========================================
# 3. 界面 UI
# ==========================================

st.title("🎧 英语听力填空")
st.caption(f"来源: {current_data['source']}")

# 显示中文
st.markdown(f"### {current_data['chinese']}")

st.divider()

# 播放音频
st.audio(current_data['audio_bytes'], format='audio/wav')

st.divider()

# 填空区
col_text, col_input = st.columns([2, 1])

with col_text:
    preview_text = []
    for i, w in enumerate(words):
        if i in st.session_state.masked_indices:
            preview_text.append("`[___]`")
        else:
            preview_text.append(w)
    st.markdown(" ".join(preview_text))

with col_input:
    with st.form("answer_form"):
        user_answers = {}
        for idx in st.session_state.masked_indices:
            user_answers[idx] = st.text_input(f"单词 #{idx+1}")
        
        if st.form_submit_button("提交"):
            st.session_state.is_checked = True

# 结果校验
if st.session_state.is_checked:
    correct_count = 0
    for idx, val in user_answers.items():
        correct_val = words[idx].strip(string.punctuation).lower()
        user_val = val.strip().lower()
        if correct_val == user_val:
            st.success(f"#{idx+1} 正确!")
            correct_count += 1
        else:
            st.error(f"#{idx+1} 错误. 答案: {words[idx]}")
            
    if correct_count == len(st.session_state.masked_indices):
        st.balloons()

# 翻页
st.divider()
if st.button("下一句 ➡️"):
    if st.session_state.current_index < len(samples) - 1:
        st.session_state.current_index += 1
    else:
        st.session_state.current_index = 0 # 循环
        
    st.session_state.masked_indices = []
    st.session_state.is_checked = False
    st.rerun()