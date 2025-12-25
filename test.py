import streamlit as st
import google.generativeai as genai
import os
from laws import law_database  # ✅ 改成匯入總目錄 (這是關鍵)

# --- 設定 API Key ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = "上傳前記得把真鑰匙刪掉"

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-flash-latest')

# --- 網頁標題 ---
st.title("🌊 海巡特考 AI 陪讀教練")
st.subheader("幫你抓到申論題痛點")

# --- 側邊欄 ---
subject = st.sidebar.selectbox(
    "選擇今天想練習的科目",
    ("海巡法規", "刑法", "刑事訴訟法", "行政法")
)

st.write(f"### 目前科目：{subject}")

# --- AI 出題 ---
if st.button("🔥 請 Gemini 出一題申論題"):
    
    # ✅ 關鍵邏輯：根據科目去抓對應的法條
    selected_law = law_database.get(subject, "查無資料")

    if selected_law == "查無資料" or "目前專注" in selected_law:
        st.warning(f"目前 {subject} 還在擴充中，請先選擇其他科目！")
        st.stop()

    prompt = f"""
    你是一位嚴格的「海巡特考」出題老師。
    
    請參考以下【核心法規資料庫】：
    {selected_law}
    
    任務：
    1. 請針對「{subject}」這個科目，從上面的資料庫中，設計一道「情境式」的申論題。
    2. 題目必須結合海巡執法情境 (如：安檢、追緝、用槍)。
    3. 只要給題目，不要給答案。
    """
    
    with st.spinner('AI 老師正在翻法條出題中...'):
        response = model.generate_content(prompt)
        st.session_state['question'] = response.text

# --- 顯示題目與批改 ---
if 'question' in st.session_state:
    st.info(st.session_state['question'])
    user_answer = st.text_area("請輸入擬答", height=200)
    
    if st.button("📝 提交給 AI 批改"):
        if user_answer:
            selected_law = law_database.get(subject, "查無資料")
            
            verify_prompt = f"""
            題目：{st.session_state['question']}
            考生的回答：{user_answer}
            參考法條：{selected_law}
            
            任務：
            請扮演閱卷老師，依據參考法條進行評分與解析。
            請指出考生的盲點，並補充相關的實務見解或法條依據。
            """
            with st.spinner('閱卷中...'):
                feedback = model.generate_content(verify_prompt)
                st.markdown("### 批改結果")
                st.write(feedback.text)
        else:
            st.warning("請先輸入答案！")