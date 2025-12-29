import streamlit as st
import openai # DeepSeek 使用 OpenAI 的套件格式
import os
import time
import json
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from laws import law_database

# --- 1. 設定 DeepSeek API ---
try:
    # DeepSeek 官方 API 網址
    client = openai.OpenAI(
        api_key = st.secrets["DEEPSEEK_API_KEY"], 
        base_url = "https://api.deepseek.com"
    )
except:
    st.error("找不到 DEEPSEEK_API_KEY，請檢查 Secrets 設定！")
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
st.subheader("DeepSeek 強力驅動版 (Sheets + Notion)")

with st.sidebar:
    st.header("功能選單")
    subject = st.selectbox("選擇科目", ("海巡法規", "刑法", "刑事訴訟法", "行政法"))
    st.info("💡 已切換至 DeepSeek API，不再受 Google 20次限制")

# AI 出題邏輯
if st.button("🔥 請 DeepSeek 出一題申論題"):
    selected_law = law_database.get(subject, "查無資料")
    prompt = f"你是一位嚴格的海巡特考老師。參考法規：{selected_law}\n任務：針對「{subject}」設計一道情境式申論題。只要題目，不要答案。"
    
    with st.spinner('DeepSeek 思考中...'):
        # 呼叫 DeepSeek 模型
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        st.session_state['question'] = response.choices[0].message.content
        st.session_state['current_feedback'] = None 

# 作答與存檔
if 'question' in st.session_state:
    st.info(st.session_state['question'])
    with st.form(key='answer_form'):
        user_answer = st.text_area("請輸入擬答", height=200)
        submit_btn = st.form_submit_button("📝 提交並同步存檔")

    if submit_btn and user_answer:
        selected_law = law_database.get(subject, "查無資料")
        verify_prompt = f"題目：{st.session_state['question']}\n考生回答：{user_answer}\n參考法條：{selected_law}\n任務：閱卷評分並給予改進建議。"
        
        with st.spinner('DeepSeek 閱卷與存檔中...'):
            # 1. AI 批改
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": verify_prompt}],
                stream=False
            )
            feedback_text = response.choices[0].message.content
            st.session_state['current_feedback'] = feedback_text
            
            # 2. 存檔
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            google_ok = save_to_google_sheet([timestamp, subject, st.session_state['question'], user_answer, feedback_text])
            notion_ok = save_to_notion(subject, st.session_state['question'], user_answer, feedback_text)

            if google_ok and notion_ok:
                st.success("✅ 雙平台存檔成功！")

if 'current_feedback' in st.session_state and st.session_state['current_feedback']:
    st.markdown("### 批改結果")
    st.write(st.session_state['current_feedback'])