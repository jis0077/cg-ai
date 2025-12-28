import streamlit as st
import google.generativeai as genai
import os
import time
import json
import requests  # 必備
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from laws import law_database

# --- 1. 設定 Google Gemini API Key ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("找不到 GOOGLE_API_KEY，請檢查 Secrets 設定！")
    st.stop()

genai.configure(api_key=api_key)
# 依照你的要求，鎖定使用這個版本
model = genai.GenerativeModel('gemini-flash-latest')

# --- 2. 設定 Google Sheets 連線 ---
def save_to_google_sheet(data_row):
    try:
        secret_data = st.secrets["GOOGLE_SHEETS_KEY"]
        if isinstance(secret_data, dict):
            key_dict = secret_data
        else:
            key_dict = json.loads(secret_data, strict=False)
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open("海巡特考練習紀錄").sheet1
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
            "Authorization": "Bearer " + token,
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
        if response.status_code == 200:
            return True
        else:
            st.error(f"Notion 回傳錯誤: {response.text}")
            return False
    except Exception as e:
        st.error(f"Notion 連線異常: {e}")
        return False

# --- 4. 網頁主程式 ---
st.title("🌊 海巡特考 AI 陪讀教練")
st.subheader("雲端錯題本版 (Sheets + Notion)")

with st.sidebar:
    st.header("功能選單")
    subject = st.selectbox("選擇科目", ("海巡法規", "刑法", "刑事訴訟法", "行政法"))
    st.info("💡 雙重存檔啟動中")

# 出題
if st.button("🔥 請 Gemini 出一題申論題"):
    selected_law = law_database.get(subject, "查無資料")
    prompt = f"""
    你是一位嚴格的「海巡特考」出題老師。
    請參考：{selected_law}
    任務：針對「{subject}」設計一道情境式申論題。
    只要給題目，不要給答案。
    """
    with st.spinner('出題中...'):
        response = model.generate_content(prompt)
        st.session_state['question'] = response.text
        st.session_state['current_feedback'] = None 

# 作答
if 'question' in st.session_state:
    st.info(st.session_state['question'])
    
    with st.form(key='answer_form'):
        user_answer = st.text_area("請輸入擬答", height=200)
        submit_btn = st.form_submit_button("📝 提交並存檔")

    if submit_btn:
        if user_answer:
            selected_law = law_database.get(subject, "查無資料")
            verify_prompt = f"""
            題目：{st.session_state['question']}
            考生回答：{user_answer}
            參考法條：{selected_law}
            任務：評分並給予建議。
            """
            
            with st.spinner('閱卷與存檔中...'):
                # 1. 先取得 AI 回饋
                feedback_resp = model.generate_content(verify_prompt)
                feedback_text = feedback_resp.text
                st.session_state['current_feedback'] = feedback_text
                
                # 2. 準備存檔內容
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                
                # 3. 執行雙重存檔
                google_ok = save_to_google_sheet([timestamp, subject, st.session_state['question'], user_answer, feedback_text])
                notion_ok = save_to_notion(subject, st.session_state['question'], user_answer, feedback_text)

                if google_ok and notion_ok:
                    st.success("✅ 雙平台存檔成功！")
                elif google_ok:
                    st.warning("⚠️ Google 成功，但 Notion 失敗")
                elif notion_ok:
                    st.warning("⚠️ Notion 成功，但 Google 失敗")
                else:
                    st.error("❌ 存檔全部失敗")
        else:
            st.warning("請先輸入答案！")

if 'current_feedback' in st.session_state and st.session_state['current_feedback']:
    st.markdown("### 批改結果")
    st.write(st.session_state['current_feedback'])