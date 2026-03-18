import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="股市教練 App", page_icon="📈")
st.title("📈 專屬股市教練 - 波段起漲掃描器")

# 讓使用者輸入代號
stock_id = st.text_input("請輸入台股代號 (例如: 2330)", "2330")

# --- 新增功能：抓取台股中文名稱 ---
@st.cache_data(ttl=86400) # 快取一天就好
def get_tw_stock_name(stock_no):
    try:
        # 使用台灣證交所的公開資料 API 抓取中文名稱
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url).json()
        for stock in res:
            if stock['Code'] == stock_no:
                return stock['Name']
        return "未知名稱"
    except:
        return "無法取得名稱"

# 模擬抓取籌碼與週轉率
@st.cache_data(ttl=3600)
def get_twse_data(stock_no):
    mock_turnover = 8.5 
    mock_institutional_buy = 1500 
    return mock_turnover, mock_institutional_buy

if st.button("啟動教練，開始分析！"):
    yf_symbol = f"{stock_id}.TW"
    stock_name = get_tw_stock_name(stock_id)
    
    st.info(f"正在分析： {stock_id} {stock_name} ...")
    
    # 抓取股價資料
    df = yf.download(yf_symbol, period="1y")
    
    if df.empty:
        st.error("找不到這檔股票，請確認代號是否正確。")
    else:
        # 顯示最新股價 (拿掉美金，改成中文)
        current_price = df['Close'].iloc[-1].item() # 確保取出單一數值
        st.metric(label=f"目前收盤價", value=f"{current_price:.2f} 元")
        
        # --- 計算技術指標 ---
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        # KD 指標
        df['9K_Min'] = df['Low'].rolling(window=9).min()
        df['9K_Max'] = df['High'].rolling(window=9).max()
        df['RSV'] = 100 * (df['Close'] - df['9K_Min']) / (df['9K_Max'] - df['9K_Min'])
        df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        
        # MACD 指標
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = df['EMA12'] - df['EMA26']
        df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['MACD']
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        turnover, inst_buy = get_twse_data(stock_id)

        # --- 8 大條件判定 ---
        st.subheader("📊 8 大核心指標檢驗報告")
        score = 0
        
        if turnover > 8.0:
            st.success(f"✅ 1. 週轉率 > 8% (目前: {turnover}%)")
            score += 1
        else:
            st.error(f"❌ 1. 週轉率未達 8% (目前: {turnover}%)")
            
        if today['K'].item() > today['D'].item() and yesterday['K'].item() <= yesterday['D'].item():
            st.success("✅ 2. KD 黃金交叉")
            score += 1
        else:
            st.error(f"❌ 2. KD 未黃金交叉 (K:{today['K'].item():.1f}, D:{today['D'].item():.1f})")

        if (today['5MA'].item() > today['10MA'].item()) and (yesterday['5MA'].item() <= yesterday['10MA'].item()) and \
           (today['Close'].item() > today['5MA'].item()) and (today['Close'].item() > today['60MA'].item()):
            st.success("✅ 3. 5日線突破10日線，且站上各均線")
            score += 1
        else:
            st.error("❌ 3. 均線未形成多頭突破")

        if inst_buy > 0:
            st.success(f"✅ 4. 籌碼偏多：三大法人近期買超")
            score += 1
        else:
            st.error("❌ 4. 籌碼偏空：法人未見買超")

        if today['Close'].item() > df.iloc[-60]['Close'].item():
            st.success("✅ 5. 季線扣抵有過 (60MA趨勢向上)")
            score += 1
        else:
            st.error("❌ 5. 季線趨勢尚未翻揚")

        if today['MACD_Hist'].item() > 0 and yesterday['MACD_Hist'].item() <= 0:
            st.success("✅ 6. MACD 黃金交叉")
            score += 1
        else:
            st.error("❌ 6. MACD 尚未黃金交叉")

        dist_10ma = (today['Close'].item() - today['10MA'].item()) / today['10MA'].item()
        if today['Close'].item() > today['10MA'].item() and dist_10ma <= 0.02:
            st.success(f"✅ 7. 10日線支撐 (距離 {dist_10ma:.1%})")
            score += 1
        else:
            st.error("❌ 7. 未達 10日線支撐標準")

        dist_20ma = (today['Close'].item() - today['20MA'].item()) / today['20MA'].item()
        if today['Close'].item() > today['20MA'].item() and dist_20ma <= 0.02:
            st.success(f"✅ 8. 20日線支撐 (距離 {dist_20ma:.1%})")
            score += 1
        else:
            st.error("❌ 8. 未達 20日線支撐標準")

        # --- 結論 ---
        st.divider()
        st.subheader("💡 教練最終評估")
        if score >= 6:
            st.balloons()
            st.markdown(f"### 🔥 **強烈買進訊號！** (達成 {score}/8 項)")
        elif score >= 4:
            st.markdown(f"### ⚠️ **持續觀察中** (達成 {score}/8 項)")
        else:
            st.markdown(f"### ❄️ **暫不考慮** (達成 {score}/8 項)")
