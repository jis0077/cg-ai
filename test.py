import streamlit as st
from groq import Groq # 換成 Groq 套件
import os
import time
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from laws import law_database

# --- 1. 設定 Groq API ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("找不到 GROQ_API_KEY，請檢查 Secrets 設定！")
    st.stop()

# --- 2. 設定 Google Sheets 連線 ---
def save_to_google_sheet(data_row):
    try:
        secret_data = st.secrets["GOOGLE_SHEETS_KEY"]
        key_dict = json.loads(secret_data, strict=False) if isinstance(secret_data, str) else secret_data
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client_gs = gspread.authorize(creds)
        
        sheet = client_gs.open("海巡特考練習紀錄").sheet1
        if len(sheet.get_all_values()) == 0:
            sheet.append_row(["時間", "科目", "題目", "你的擬答", "AI 建議"])
            
        sheet.append_row(data_row)
        return True
    except Exception as e:
        st.error(f"Google Sheet 存檔失敗: {e}")
        return False

# --- 3. 設定 Notion 連線 ---
def save_to_notion(subject, question, answer, feedback):
    try:
        token = st.secrets["NOTION_TOKEN"]
        database_id = st.secrets["NOTION_DATABASE_ID"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        data = {
            "parent": {"database_id": database_id},
            "properties": {
                "題目": {"title": [{"text": {"content": question[:2000]}}]},
                "科目": {"select": {"name": subject}},
                "日期": {"date": {"start": time.strftime("%Y-%m-%d")}},
                "你的擬答": {"rich_text": [{"text": {"content": answer[:2000]}}]},
                "AI 建議": {"rich_text": [{"text": {"content": feedback[:2000]}}]}
            }
        }
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Notion 連線異常: {e}")
        return False

# --- 4. 網頁介面 ---
st.title("🌊 海巡特考 AI 陪讀教練")
st.subheader("Groq 極速引擎版 (Sheets + Notion)")

with st.sidebar:
    st.header("功能選單")
    subject = st.selectbox("選擇科目", ("海巡法規", "刑法", "刑事訴訟法", "行政法"))
    st.info("🚀 Groq 強力驅動：模型選用 Llama-3.3-70b")

# AI 出題邏輯
if st.button("🔥 請 Groq 出一題申論題"):
    selected_law = law_database.get(subject, "查無資料")
    prompt = f"你是一位嚴格的海巡特考老師。參考法規資料：{selected_law}\n任務：針對「{subject}」設計一道情境式申論題。只要題目，不要答案。"
    
    with st.spinner('Groq 正在光速思考...'):
        # 呼叫 Groq 模型 (Llama 3.3 是目前最強推薦)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        st.session_state['question'] = chat_completion.choices[0].message.content
        st.session_state['current_feedback'] = None 

# 作答與存檔區
if 'question' in st.session_state:
    st.info(st.session_state['question'])
    with st.form(key='answer_form'):
        user_answer = st.text_area("請輸入擬答", height=200)
        submit_btn = st.form_submit_button("📝 提交並同步存檔")

    if submit_btn and user_answer:
        selected_law = law_database.get(subject, "查無資料")
        verify_prompt = f"題目：{st.session_state['question']}\n考生回答：{user_answer}\n參考法條：{selected_law}\n任務：閱卷評分並給予精確的申論建議。"
        
        with st.spinner('Groq 正在閱卷並存檔...'):
            # 1. AI 批改
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": verify_prompt}],
                model="llama-3.3-70b-versatile",
            )
            feedback_text = response.choices[0].message.content
            st.session_state['current_feedback'] = feedback_text
            
            # 2. 存檔到試算表與 Notion
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            google_ok = save_to_google_sheet([timestamp, subject, st.session_state['question'], user_answer, feedback_text])
            notion_ok = save_to_notion(subject, st.session_state['question'], user_answer, feedback_text)

            if google_ok and notion_ok:
                st.success("✅ 雙平台存檔成功！")

if 'current_feedback' in st.session_state and st.session_state['current_feedback']:
    st.markdown("### 批改結果")
    st.write(st.session_state['current_feedback'])