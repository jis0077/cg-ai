import streamlit as st
import google.generativeai as genai
import os
from laws import coast_guard_law
# --- ✅ 改用 try-except 結構 (最穩定的寫法) ---
try:
    # 嘗試從雲端抓取鑰匙
    # 如果你在本機沒設定 secrets 檔案，這一行會報錯，直接跳去 except
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    # 只要上面出錯 (代表你在本機)，就用這把鑰匙
    api_key = "上傳前記得把真鑰匙刪掉" 

# 設定給 Gemini
genai.configure(api_key=api_key)

# 這裡就是我們指揮 Gemini 的地方
model = genai.GenerativeModel('gemini-flash-latest')
# --- 設定網頁標題 ---
st.title("🌊 海巡特考 AI 陪讀教練")
st.subheader("幫你抓到申論題痛點")

# --- 側邊欄：選擇科目 ---
subject = st.sidebar.selectbox(
    "選擇今天想練習的科目",
    ("刑法", "刑事訴訟法", "行政法", "海巡法規")
)

# --- 功能區：AI 出題 ---
st.write(f"### 目前科目：{subject}")

if st.button("🔥 請 Gemini 出一題申論題"):
 
    
    prompt = f"""
    你是一位嚴格的「海巡特考」出題老師。
    
    請參考以下【核心法規資料庫】：
    {coast_guard_law}
    
    任務：
    1. 請針對「{subject}」這個科目，從上面的資料庫中，設計一道「情境式」的申論題。
    2. 題目要結合海巡人員在海上或港口執法的情境（例如：登船檢查、發現走私）。
    3. 只要給題目，不要給答案。
    """
    
    with st.spinner('AI 老師正在翻法條出題中...'):
        response = model.generate_content(prompt)
        st.session_state['question'] = response.text # 把題目存起來

# 顯示題目
if 'question' in st.session_state:
    st.info(st.session_state['question'])
    
    # 讓使用者作答
    user_answer = st.text_area("請在此輸入你的擬答 (模擬考場情境)", height=200)
    
    if st.button("📝 提交給 AI 批改"):
        if user_answer:
            verify_prompt = f"""
            題目：{st.session_state['question']}
            考生的回答：{user_answer}
            
            請你扮演閱卷老師，針對這份回答：
            1. 給予評分 (0-25分)。
            2. 指出引用的法條是否正確。
            3. 點評邏輯漏洞。
            4. 給出一段「更完美的擬答範例」。
            """
            with st.spinner('閱卷中...'):
                feedback = model.generate_content(verify_prompt)
                st.markdown("### 批改結果")
                st.write(feedback.text)
        else:

            st.warning("請先輸入答案再提交！")

