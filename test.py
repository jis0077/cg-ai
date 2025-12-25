import streamlit as st
import google.generativeai as genai
import os
# --- 這是你的獨家秘密資料庫 (可以隨時把最新的修法貼進來) ---
coast_guard_law = """
【海岸巡防法】
第 4 條 (巡防機關掌理事項)：
一、海岸管制區之管制及安全維護事項。
二、入出港船舶或其他水上運輸工具之安全檢查事項。
三、海域、海岸、河口與非通商口岸之查緝走私、防止非法入出國。
四、海域及海岸巡防涉外事務之協調、調查及處理事項。
五、走私情報之蒐集，滲透及安全情報之調查處理事項。

第 5 條 (執行職權)：
巡防機關人員執行職務時，得行使下列職權：
一、對進出海域、海岸、河口、非通商口岸之人員、船舶、車輛或其他運輸工具，進行檢查。
二、對航行海域內之船舶，有事實足認有違法之虞時，得命其停止航行、回航，其抗不遵照者，得進行緊追、登臨、檢查；必要時，得強制為之。

【刑事訴訟法 - 強制處分與證據】
第 130 條 (附帶搜索)：
檢察官、檢察事務官、司法警察官或司法警察逮捕被告、犯罪嫌疑人或執行拘提、羈押時，雖無搜索票，得逕行搜索其身體、隨身攜帶之物件、所使用之交通工具及其立即可觸及之處所。

第 131 條 (逕行搜索/緊急搜索)：
有下列情形之一者，得逕行搜索住宅或其他處所：
一、因逮捕被告、犯罪嫌疑人或執行拘提、羈押，有事實足認被告或犯罪嫌疑人確實在內者。
二、因追攝現行犯或逮捕脫逃人，有事實足認現行犯或脫逃人確實在內者。
三、有明顯事實足認為有人在內犯罪而情形急迫者。

第 158-4 條 (權衡法則)：
除法律另有規定外，實施刑事訴訟程序之公務員因違背法定程序取得之證據，其有無證據能力之認定，應審酌人權保障及公共利益之均衡維護。

【中華民國刑法】
第 24 條 (緊急避難)：
因避免自己或他人生命、身體、自由、財產之緊急危難而出於不得已之行為，不罰。但避難行為過當者，得減輕或免除其刑。

第 134 條 (準受賄罪/公務員犯罪加重)：
公務員假借職務上之權力、機會或方法，以故意犯本章以外各罪者，加重其刑至二分之一。
"""
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
st.subheader("幫你突破申論題痛點")

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

