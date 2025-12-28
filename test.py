import streamlit as st
import google.generativeai as genai
import os
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from laws import law_database

# --- 設定 Google Gemini API Key ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("找不到 GOOGLE_API_KEY，請檢查 Secrets 設定！")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-flash-latest')

# --- 設定 Google Sheets 連線 (改良防呆版) ---
def save_to_google_sheet(data_row):
    try:
        # 讀取 Secrets
        secret_data = st.secrets["GOOGLE_SHEETS_KEY"]
        
        # 防呆機制 1：如果 Streamlit 已經自動把它轉成 dict，就不用 json.loads
        if isinstance(secret_data, dict):
            key_dict = secret_data
        else:
            # 防呆機制 2：如果是字串，加上 strict=False 來忽略某些控制字元錯誤
            key_dict = json.loads(secret_data, strict=False)
        
        # 2. 連線設定
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        client = gspread.authorize(creds)
        
        # 3. 打開試算表
        sheet = client.open("海巡特考練習紀錄").sheet1
        
        # 4. 如果是新表，自動寫入標題列
        if len(sheet.get_all_values()) == 0:
            sheet.append_row(["時間", "科目", "題目", "你的擬答", "AI 建議"])
            
        # 5. 寫入資料
        sheet.append_row(data_row)
        return True
    except json.JSONDecodeError as e:
        st.error(f"鑰匙格式錯誤 (JSON Error)：請檢查 Secrets 的格式。詳細錯誤：{e}")
        return False
    except Exception as e:
        st.error(f"雲端存檔失敗：{e}")
        return False

# --- 網頁介面開始 ---
st.title("🌊 海巡特考 AI 陪讀教練")
st.subheader("雲端錯題本版")

# --- 側邊欄 ---
with st.sidebar:
    st.header("功能選單")
    subject = st.selectbox(
        "選擇今天想練習的科目",
        ("海巡法規", "刑法", "刑事訴訟法", "行政法")
    )
    st.info("💡 提示：提交後，題目會自動存入你的 Google 試算表！")

# --- AI 出題 ---
if st.button("🔥 請 Gemini 出一題申論題"):
    selected_law = law_database.get(subject, "查無資料")
    if selected_law == "查無資料" or "目前專注" in selected_law:
        st.warning(f"目前 {subject} 還在擴充中，請先選擇其他科目！")
        st.stop()

    prompt = f"""
    你是一位嚴格的「海巡特考」出題老師。
    請參考以下【核心法規資料庫】：
    {selected_law}
    任務：
    針對「{subject}」設計一道情境式申論題，結合執法情境。
    只要給題目，不要給答案。
    """
    
    with st.spinner('出題中...'):
        response = model.generate_content(prompt)
        st.session_state['question'] = response.text
        st.session_state['current_feedback'] = None 

# --- 作答區 ---
if 'question' in st.session_state:
    st.info(st.session_state['question'])
    
    with st.form(key='answer_form'):
        user_answer = st.text_area("請輸入擬答", height=200)
        # 這裡的按鈕文字變了，這是我們判斷是否更新成功的依據
        submit_btn = st.form_submit_button("📝 提交並存檔")

    if submit_btn:
        if user_answer:
            selected_law = law_database.get(subject, "查無資料")
            
            verify_prompt = f"""
            題目：{st.session_state['question']}
            考生的回答：{user_answer}
            參考法條：{selected_law}
            任務：扮演閱卷老師評分並給予建議，指出盲點。
            """
            with st.spinner('閱卷與存檔中...'):
                # 1. 取得 AI 回饋
                feedback = model.generate_content(verify_prompt)
                st.session_state['current_feedback'] = feedback.text
                
                # 2. 準備要存的資料
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                save_data = [
                    timestamp, 
                    subject, 
                    st.session_state['question'], 
                    user_answer, 
                    feedback.text
                ]
                
                # 3. 呼叫存檔函式
                if save_to_google_sheet(save_data):
                    st.success("✅ 已成功存入 Google 試算表！")
                
        else:
            st.warning("請先輸入答案！")

if 'current_feedback' in st.session_state and st.session_state['current_feedback']:
    st.markdown("### 批改結果")
    st.write(st.session_state['current_feedback'])