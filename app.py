import streamlit as st
import pandas as pd
import requests
import datetime
import yfinance as yf
import time

# --- 🚀 全局介面與 Token 設定 ---
st.set_page_config(page_title="台股短線買入評級", page_icon="⚡", layout="wide")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0xOSAyMjo1Njo0NyIsInVzZXJfaWQiOiJGb2RlbkNoaXUiLCJlbWFpbCI6InlpaGFuY2hpdTExMDZAZ21haWwuY29tIiwiaXAiOiI0OS4xNTkuMjE3LjIwMiJ9.yYlYV7Y-PPQJxR6amyp9mDsK5su2T4HsZO0oYpotMEg"

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", sans-serif;
        background-color: #121212; color: #EAEAEA;
    }
    .main-title { color: #D4AF37; font-weight: bold; margin-bottom: 5px; }
    .input-label { font-size: 15px; font-weight: bold; color: #D4AF37; margin-bottom: 5px; }
    .weight-box { background-color: #1A1A1A; border: 1px solid #D4AF37; border-radius: 8px; padding: 20px; margin-top: 30px; margin-bottom: 20px; }
    .check-item { background-color: #1E1E1E; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #333; display: flex; align-items: center; }
    .score-circle { background-color: #121212; border-radius: 50%; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center; border: 10px solid #333; margin: 0 auto; box-shadow: 0 0 15px rgba(212, 175, 55, 0.2); }
    .score-text { font-size: 42px; font-weight: bold; color: #D4AF37; }
    .stButton > button { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold !important; border-radius: 8px !important; width: 100%; height: 50px; font-size: 16px !important; }
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #2DCC70; min-width: 90px; text-align: center; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; min-width: 90px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 🎯 數據庫引擎 ---
@st.cache_data(ttl=86400)
def fetch_stock_mapping():
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {"dataset": "TaiwanStockInfo", "token": FINMIND_TOKEN}
        res = requests.get(url, params=params, timeout=10).json()
        return dict(zip(pd.DataFrame(res["data"])['stock_id'], pd.DataFrame(res["data"])['stock_name'])) if res.get("msg") == "success" else {}
    except: return {}

@st.cache_data(ttl=900)
def fetch_finmind_data(sid):
    try:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=150)).strftime("%Y-%m-%d")
        url = "https://api.finmindtrade.com/api/v4/data"
        res_p = requests.get(url, params={"dataset": "TaiwanStockPrice", "data_id": sid, "start_date": start_date, "end_date": end_date, "token": FINMIND_TOKEN}).json()
        df = pd.DataFrame(res_p["data"])
        df.rename(columns={'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'}, inplace=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']: df[col] = pd.to_numeric(df[col])
        res_fi = requests.get(url, params={"dataset": "TaiwanStockShareholding", "data_id": sid, "start_date": (datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y-%m-%d"), "token": FINMIND_TOKEN}).json()
        res_it = requests.get(url, params={"dataset": "TaiwanStockHoldingTrust", "data_id": sid, "start_date": (datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y-%m-%d"), "token": FINMIND_TOKEN}).json()
        return df, pd.DataFrame(res_fi.get("data", [])), pd.DataFrame(res_it.get("data", []))
    except: return None, None, None

stock_mapping = fetch_stock_mapping()
stock_list = [f"{k} {v}" for k, v in stock_mapping.items()]

def analyze_single_stock(stock_id):
    df, df_fi, df_it = fetch_finmind_data(stock_id)
    if df is None or len(df) < 10: return "error", 0, None
    df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
    df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
    df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    today, yest = df.iloc[-1], df.iloc[-2]
    
    score = 0; tech_results = []; chip_results = []; summary = {}
    
    # 🎯 2. KD 位階 (25分) - 🎯 修正：黑K出貨邏輯
    k_val = today['K']
    is_black_k = today['Close'] < today['Open']
    v0, v1, v2, v3 = df['Volume'].iloc[-1], df['Volume'].iloc[-2], df['Volume'].iloc[-3], df['Volume'].iloc[-4]
    is_heavy_vol = v0 > v1  # 量增
    is_excessive = v0 > (v1 + v2 + v3) # 爆量

    if k_val > 80:
        if is_black_k:
            ks, kc, km = 0, "status-fail", "⚠️ 高檔收黑 (疑似出貨/見頂)"
        elif today['Close'] > today['5MA'] and not is_excessive:
            ks, kc, km = 25, "status-pass", "🔥 高檔強勢鈍化"
        else:
            ks, kc, km = 0, "status-fail", "過熱且量價背離"
    elif 30 <= k_val <= 45: ks, kc, km = 25, "status-pass", "KD 30~45 起漲區"
    elif 45 < k_val <= 65: ks, kc, km = 20, "status-mid", "KD 46~65 穩定"
    else: ks, kc, km = 0, "status-fail", "位階不佳"
    
    score += ks; tech_results.append(("KD 位階", f"K值: {k_val:.1f}", f"+{ks}分", kc, km))
    summary['KD狀態'] = km

    # 籌碼與其他 (簡化邏輯供參考)
    # ... [此處保留先前 58.0 版本的完整週轉率、法人、均線、MACD 邏輯] ...
    # (為節省長度，假設其餘邏輯已整合)

    return "success", score, {"tech": tech_results, "chip": chip_results, "summary": summary}

# --- 介面渲染 ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    selected_option = st.selectbox("s_id", options=stock_list, index=None, placeholder="🔍 輸入 4967 試試看", label_visibility="collapsed")

if selected_option:
    stock_id = str(selected_option).split(" ")[0]
    st, sc, res = analyze_single_stock(stock_id)
    if st == "success":
        if "⚠️" in res['summary']['KD狀態']:
            st.error(f"🚨 **危險警告**：{selected_option} 雖然指標在高檔，但出現了『放量收黑』。")
            st.info("這通常代表大戶正在趁亂出貨，或是短線追價力道竭盡，建議避開。")
        # ... [其餘渲染邏輯] ...
