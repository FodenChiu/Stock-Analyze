import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime
from PIL import Image

st.set_page_config(page_title="股市短線評級 6.0", page_icon="⚡", layout="wide")
st.title("⚡ 專屬股市短線評級 - 全自動診斷器")

# --- 🚀 第一區：輸入與自動抓取 ---
user_input = st.text_input("請輸入台股代號或中文名稱 (例如: 2337 或 旺宏)", "2337")

@st.cache_data(ttl=86400)
def build_stock_dictionary():
    s_dict, n_dict = {}, {}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=headers).json()
        for s in res:
            s_dict[s['Code']] = (s['Name'], ".TW"); n_dict[s['Name']] = (s['Code'], ".TW")
        res2 = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=headers).json()
        for s in res2:
            s_dict[s['SecuritiesCompanyCode']] = (s['CompanyName'], ".TWO"); n_dict[s['CompanyName']] = (s['SecuritiesCompanyCode'], ".TWO")
    except: pass
    return s_dict, n_dict

@st.cache_data(ttl=3600)
def get_finmind_inst(stock_no):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": "TaiwanStockInstitutionalInvestorsBuySell", "data_id": stock_no, 
              "start_date": (datetime.date.today() - datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
              "end_date": datetime.date.today().strftime("%Y-%m-%d")}
    try:
        data = requests.get(url, params=params).json()["data"]
        df = pd.DataFrame(data).groupby('date')['buy_sell'].sum().tail(4).tolist()
        return [int(x)//1000 for x in df]
    except: return [0,0,0,0]

stock_dict, name_dict = build_stock_dictionary()

if st.button("啟動全自動評級"):
    query = user_input.strip()
    code, name, suffix = query, "未知名稱", ".TW"
    if query.isdigit() and query in stock_dict:
        name, suffix = stock_dict[query]
    elif query in name_dict:
        code, suffix = name_dict[query]; name = query
    
    st.info(f"正在分析： {code} {name} ...")
    ticker = yf.Ticker(f"{code}{suffix}")
    df = ticker.history(period="1y")
    
    if not df.empty:
        # 指標計算
        df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean(); df['60MA'] = df['Close'].rolling(60).mean()
        df['5VMA'] = df['Volume'].rolling(5).mean(); df['10VMA'] = df['Volume'].rolling(10).mean()
        df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
        df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
        df['K'] = df['RSV'].ewm(com=2, adjust=False).mean(); df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        df['DIF'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        df['MACD'] = df['DIF'].ewm(span=9).mean()
        
        today, yest = df.iloc[-1], df.iloc[-2]
        shares = ticker.info.get('sharesOutstanding', 0)
        turnover = (today['Volume'] / shares * 100) if shares else 0
        inst = get_finmind_inst(code)
        while len(inst) < 4: inst.insert(0,0)
        v1, v2, v3 = (inst[-4], inst[-3], inst[-2]) if inst[-1]==0 else (inst[-3], inst[-2], inst[-1])
        avg_inst = (v1+v2+v3)/3
        
        # 顯示數值
        st.subheader(f"📊 {code} {name} 診斷報告")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("收盤價", f"{today['Close']:.2f}")
        c2.metric("周轉率", f"{turnover:.2f}%")
        c3.metric("近三日平均買超", f"{int(avg_inst)}張")
        c4.metric("DIF-MACD", f"{(today['DIF']-today['MACD']):.3f}")

        # 10大指標自動判定
        score = 0
        checks = [
            (turnover > 9, f"週轉率 > 9% ({turnover:.2f}%)"),
            (today['K']>today['D'] and today['K']<60 and today['D']<55, f"KD 低檔黃叉 (K:{today['K']:.1f})"),
            (today['5MA']>yest['5MA'] and today['10MA']>yest['10MA'] and today['20MA']>yest['20MA'], "5/10/20T 均線上揚"),
            (avg_inst > 0, f"法人三日平均買超 ({int(avg_inst)}張)"),
            (today['Close'] > df.iloc[-60]['Close'], "股價 > 季線扣抵"),
            (today['DIF']-today['MACD'] > 0, "DIF-MACD 零軸之上"),
            (today['Close'] > today['5MA'], "站穩 5T"),
            (today['Close'] > today['10MA'], "站穩 10T"),
            (today['Close'] > today['20MA'], "站穩 20T"),
            (today['Volume'] > today['5VMA'] and today['Close'] > today['Open'], "量增紅K")
        ]
        
        for ok, msg in checks:
            if ok: score += 1; st.success(f"✅ {msg}")
            else: st.error(f"❌ {msg}")
            
        st.divider()
        if score >= 8: st.balloons(); st.success(f"🔥 S 級：強勢爆發！ ({score}/10)")
        elif score >= 5: st.warning(f"⚠️ A 級：多頭發酵 ({score}/10)")
        else: st.error(f"❄️ B 級：弱勢盤整 ({score}/10)")

# --- 🚀 第二區：視覺對照與上傳區 ---
st.divider()
st.subheader("📸 視覺校對區 (選用)")
uploaded_file = st.file_uploader("若數據不準，請上傳看盤截圖對照", type=['png', 'jpg', 'jpeg'])
if uploaded_file:
    st.image(Image.open(uploaded_file), caption="手機看盤截圖", use_container_width=True)
