import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="股市短線評級 App", page_icon="⚡")
st.title("⚡ 專屬股市短線評級 - 強勢股掃描器")

stock_id = st.text_input("請輸入台股代號 (例如: 2330)", "1711")

# --- 全面抓取台股中文名稱 (上市 + 上櫃) ---
@st.cache_data(ttl=86400) 
def get_tw_stock_name(stock_no):
    try:
        twse_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(twse_url, timeout=5).json()
        for stock in res:
            if stock['Code'] == stock_no:
                return stock['Name'], ".TW"
    except:
        pass
    
    try:
        tpex_url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        res = requests.get(tpex_url, timeout=5).json()
        for stock in res:
            if stock['SecuritiesCompanyCode'] == stock_no:
                return stock['CompanyName'], ".TWO"
    except:
        pass
        
    return None, ".TW" 

# --- 🚀 真實連線：抓取證交所/櫃買中心三大法人真實買賣超 ---
@st.cache_data(ttl=3600)
def get_institutional_buy(stock_no):
    # 1. 嘗試抓取上市 (TWSE) 籌碼
    try:
        url = "https://www.twse.com.tw/fund/T86?response=json&selectType=ALLBUT0999"
        res = requests.get(url, timeout=5).json()
        if res.get('stat') == 'OK':
            fields = res['fields']
            data = res['data']
            code_idx = fields.index('證券代號')
            total_idx = fields.index('三大法人買賣超股數')
            for row in data:
                if row[code_idx] == stock_no:
                    # 官方單位是股數，除以1000換算成張數
                    return int(row[total_idx].replace(',', '')) // 1000 
    except:
        pass
    
    # 2. 嘗試抓取上櫃 (TPEx) 籌碼
    try:
        url = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D"
        res = requests.get(url, timeout=5).json()
        if 'aaData' in res:
            for row in res['aaData']:
                if row[0] == stock_no:
                    # 上櫃的第10欄位通常為三大法人合計買賣超
                    return int(row[10].replace(',', '')) // 1000
    except:
        pass
        
    return 0 # 若假日無資料或查無此檔，回傳 0

if st.button("啟動評級，開始分析！"):
    stock_name, suffix = get_tw_stock_name(stock_id)
    yf_symbol = f"{stock_id}{suffix}"
    
    ticker = yf.Ticker(yf_symbol)
    if not stock_name:
        try:
            stock_name = ticker.info.get('shortName', '未知名稱')
        except:
            stock_name = "未知名稱"
            
    st.info(f"正在分析： {stock_id} {stock_name} ...")
    
    df = ticker.history(period="1y")
    
    if df.empty:
        st.error("找不到這檔股票，請確認代號是否正確。")
    else:
        current_price = float(df['Close'].iloc[-1])
        st.metric(label=f"目前收盤價", value=f"{current_price:.2f} 元")
        
        # --- 計算技術指標 ---
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        df['5VMA'] = df['Volume'].rolling(window=5).mean()
        df['10VMA'] = df['Volume'].rolling(window=10).mean()
        
        df['9K_Min'] = df['Low'].rolling(window=9).min()
        df['9K_Max'] = df['High'].rolling(window=9).max()
        df['RSV'] = 100 * (df['Close'] - df['9K_Min']) / (df['9K_Max'] - df['9K_Min'] + 1e-9)
        df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = df['EMA12'] - df['EMA26']
        df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # 取得周轉率與籌碼
        shares_out = ticker.info.get('sharesOutstanding', 0)
        today_volume = float(today['Volume'])
        if shares_out and shares_out > 0:
            real_turnover = (today_volume / shares_out) * 100
        else:
            real_turnover = 0 
            
        inst_buy_lots = get_institutional_buy(stock_id)

        # --- 顯示量能與籌碼數據 ---
        st.write("### 📊 量能與籌碼資訊")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("今日成交量", f"{int(today_volume):,} 股")
        col2.metric("周轉率", f"{real_turnover:.2f} %" if real_turnover > 0 else "無法取得")
        col3.metric("5T 均量", f"{int(today['5VMA']):,} 股")
        col4.metric("三大法人買賣超", f"{inst_buy_lots:,} 張")

        # --- 10 大條件判定 ---
        st.subheader("📋 核心指標檢驗報告")
        score = 0
        
        # 1. 周轉率 > 9%
        if real_turnover > 9.0:
            st.success(f"✅ 1. 週轉率 > 9% (目前: {real_turnover:.2f}%)")
            score += 1
        elif real_turnover == 0:
            st.warning(f"⚠️ 1. 無法取得總發行股數，略過周轉率計算。")
        else:
            st.error(f"❌ 1. 週轉率未達 9% (目前: {real_turnover:.2f}%)")
            
        # 2. KD 低檔交叉 
        k_val = float(today['K'])
        d_val = float(today['D'])
        if k_val > d_val and k_val < 60 and d_val < 55:
            st.success(f"✅ 2. KD 呈現低檔交叉 (K:{k_val:.1f}, D:{d_val:.1f})")
            score += 1
        else:
            st.error(f"❌ 2. KD 未符合低檔交叉條件 (K:{k_val:.1f}, D:{d_val:.1f})")

        # 3. 均線上揚
        if float(today['5MA']) > float(yesterday['5MA']) and float(today['10MA']) > float(yesterday['10MA']) and float(today['20MA']) > float(yesterday['20MA']):
            st.success("✅ 3. 均線全面上揚 (5T、10T、20T皆大於昨日)")
            score += 1
        else:
            st.error("❌ 3. 均線尚未全面上揚")

        # 4. 籌碼買超 (真實數據)
        if inst_buy_lots > 0:
            st.success(f"✅ 4. 籌碼偏多：三大法人買超 {inst_buy_lots:,} 張")
            score += 1
        elif inst_buy_lots < 0:
            st.error(f"❌ 4. 籌碼偏空：三大法人賣超 {abs(inst_buy_lots):,} 張")
        else:
            st.error(f"❌ 4. 籌碼無明顯買賣超或無資料 (0 張)")

        # 5. 大於季線扣抵
        if float(today['Close']) > float(df.iloc[-60]['Close']):
            st.success("✅ 5. 股價大於季線扣抵 (60MA趨勢向上)")
            score += 1
        else:
            st.error("❌ 5. 股價小於季線扣抵")

        # 6. DIF - MACD > 0
        macd_diff = float(today['DIF']) - float(today['MACD'])
        if macd_diff > 0:
            st.success(f"✅ 6. DIF - MACD 大於 0 (目前數值: {macd_diff:.3f})")
            score += 1
        else:
            st.error(f"❌ 6. DIF - MACD 小於或等於 0 (目前數值: {macd_diff:.3f})")

        # 7. 站穩 5T
        if float(today['Close']) > float(today['5MA']):
            st.success(f"✅ 7. 股價站穩 5T ({float(today['5MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 7. 股價跌破 5T ({float(today['5MA']):.2f})")

        # 8. 站穩 10T
        if float(today['Close']) > float(today['10MA']):
            st.success(f"✅ 8. 股價站穩 10T ({float(today['10MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 8. 股價跌破 10T ({float(today['10MA']):.2f})")

        # 9. 站穩 20T
        if float(today['Close']) > float(today['20MA']):
            st.success(f"✅ 9. 股價站穩 20T ({float(today['20MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 9. 股價跌破 20T ({float(today['20MA']):.2f})")
            
        # 10. 量能健康 
        is_red_candle = float(today['Close']) > float(today['Open'])
        if today_volume > float(today['5VMA']) and today_volume > float(today['10VMA']) and is_red_candle:
            st.success(f"✅ 10. 量能健康：溫和放量且收紅K (無爆量出貨疑慮)")
            score += 1
        else:
            st.error(f"❌ 10. 量能未達標：量縮或收黑K (留意出貨風險)")

        # --- 結論 ---
        st.divider()
        st.subheader("💡 系統最終評級 (滿分 10 項)")
        if score >= 8:
            st.balloons()
            st.markdown(f"### 🔥 **S 級：強勢爆發！** (達成 {score}/10 項)")
            st.write("量價配合極佳，短線動能極強，是勝率極高的突破點！")
        elif score >= 5:
            st.markdown(f"### ⚠️ **A 級：多頭發酵中** (達成 {score}/10 項)")
            st.write("指標逐步轉強，建議列入自選股密切觀察量能變化。")
        else:
            st.markdown(f"### ❄️ **B 級：弱勢或盤整** (達成 {score}/10 項)")
            st.write("動能與籌碼不足，建議保留資金等待更好時機。")
