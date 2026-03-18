import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import datetime

st.set_page_config(page_title="股市短線評級 App", page_icon="⚡")
st.title("⚡ 專屬股市短線評級 - 強勢股掃描器")

# 改良輸入框，預設文字加上提示
stock_id = st.text_input("請輸入台股代號 (例如: 2337)", "2337")

# --- 🚀 終極正名：全面抓取台股「中文名稱」 ---
@st.cache_data(ttl=86400) 
def get_tw_stock_name(stock_no):
    # 1. 先查上市 (TWSE)
    try:
        twse_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(twse_url, timeout=5).json()
        for stock in res:
            if stock['Code'] == stock_no:
                return stock['Name'], ".TW"
    except:
        pass
    
    # 2. 再查上櫃 (TPEx)
    try:
        tpex_url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        res = requests.get(tpex_url, timeout=5).json()
        for stock in res:
            if stock['SecuritiesCompanyCode'] == stock_no:
                return stock['CompanyName'], ".TWO"
    except:
        pass
        
    return None, ".TW" 

# --- 籌碼抓取 (防呆機制) ---
@st.cache_data(ttl=3600)
def get_institutional_data_finmind(stock_no):
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=15)).strftime("%Y-%m-%d")
    
    url = "https://api.finmindtrade.com/api/v4/data"
    parameter = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_no,
        "start_date": start_date,
        "end_date": end_date,
    }
    
    try:
        resp = requests.get(url, params=parameter, timeout=10)
        data = resp.json()
        
        if data["msg"] == "success" and len(data["data"]) > 0:
            df_inst = pd.DataFrame(data["data"])
            df_grouped = df_inst.groupby('date')['buy_sell'].sum().reset_index()
            df_grouped = df_grouped.sort_values(by='date').reset_index(drop=True)
            
            if len(df_grouped) >= 4:
                return [int(x) // 1000 for x in df_grouped.tail(4)['buy_sell'].tolist()]
            elif len(df_grouped) > 0:
                 return [int(x) // 1000 for x in df_grouped['buy_sell'].tolist()]
    except:
        pass
        
    return [0, 0, 0, 0] 

if st.button("啟動評級，開始分析！"):
    # 優先使用我們自己抓的中文名稱
    tw_name, suffix = get_tw_stock_name(stock_id)
    yf_symbol = f"{stock_id}{suffix}"
    
    # 如果真的連台灣官方 API 都掛了，才顯示未知名稱，絕不用英文
    display_name = tw_name if tw_name else "未知名稱"
            
    # ✨ 這裡就會顯示你指定的格式： 例如 "正在分析 2337 旺宏 的數據"
    st.info(f"正在連線資料庫，分析 {stock_id} {display_name} 的數據...")
    
    ticker = yf.Ticker(yf_symbol)
    df = ticker.history(period="1y")
    
    if df.empty:
        st.error("找不到這檔股票，請確認代號是否正確。")
    else:
        current_price = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        is_limit_up = (current_price - prev_close) / prev_close >= 0.095
        
        # 顯示大大字體的股票名稱與價格
        st.markdown(f"## {stock_id} {display_name}")
        
        if is_limit_up:
            st.metric(label=f"目前收盤價", value=f"{current_price:.2f} 元", delta="🔥 強勢漲停")
        else:
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
        
        # --- 近三日籌碼 ---
        inst_data = get_institutional_data_finmind(stock_id)
        while len(inst_data) < 4:
            inst_data.insert(0, 0)
            
        if inst_data[-1] == 0 and sum(inst_data[-4:-1]) != 0:
            v1, v2, v3 = inst_data[-4], inst_data[-3], inst_data[-2]
            st.caption("*(註：今日籌碼尚未更新或因漲停無資料，採用前三個交易日數據評估)*")
        else:
            v1, v2, v3 = inst_data[-3], inst_data[-2], inst_data[-1]
            
        avg_inst = (v1 + v2 + v3) / 3
        
        trend_text = "籌碼震盪整理"
        if v3 > 0 and v2 > 0 and v1 > 0:
            if v3 > v2 and v2 > v1: trend_text = "🔥 連續買超且擴大"
            else: trend_text = "📈 連續買超穩定"
        elif v3 < 0 and v2 < 0 and v1 < 0:
            if v3 < v2 and v2 < v1: trend_text = "⚠️ 連續賣超且擴大"
            else: trend_text = "📉 連續賣超穩定"
        elif v3 > 0 and v2 <= 0: trend_text = "✨ 由賣轉買"
        elif v3 < 0 and v2 >= 0: trend_text = "🚨 由買轉賣"
            
        shares_out = ticker.info.get('sharesOutstanding', 0)
        today_volume = float(today['Volume'])
        if shares_out and shares_out > 0:
            real_turnover = (today_volume / shares_out) * 100
        else:
            real_turnover = 0 

        # --- 顯示數據 ---
        st.write("### 📊 量能與籌碼資訊")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("今日成交量", f"{int(today_volume):,} 股")
        col2.metric("周轉率", f"{real_turnover:.2f} %" if real_turnover > 0 else "無法取得")
        col3.metric("5T 均量", f"{int(today['5VMA']):,} 股")
        col4.metric("近三日平均買賣", f"{int(avg_inst):,} 張")
        
        st.info(f"**三大法人動向：** {v1:,} 張 ➡️ {v2:,} 張 ➡️ {v3:,} 張 ({trend_text})")

        # --- 10 大條件判定 ---
        st.subheader("📋 核心指標檢驗報告")
        score = 0
        
        if real_turnover > 9.0:
            st.success(f"✅ 1. 週轉率 > 9% (目前: {real_turnover:.2f}%)")
            score += 1
        else:
            st.error(f"❌ 1. 週轉率未達 9% (目前: {real_turnover:.2f}%)")
            
        # 🚀 KD 嚴格版：噴太高(K>60)一律不買！
        k_val, d_val = float(today['K']), float(today['D'])
        if k_val > d_val and k_val < 60 and d_val < 55:
            st.success(f"✅ 2. KD 呈現低檔交叉 (K:{k_val:.1f}, D:{d_val:.1f})")
            score += 1
        else:
            st.error(f"❌ 2. KD 未符合低檔交叉條件 (K:{k_val:.1f}, D:{d_val:.1f})")

        if float(today['5MA']) > float(yesterday['5MA']) and float(today['10MA']) > float(yesterday['10MA']) and float(today['20MA']) > float(yesterday['20MA']):
            st.success("✅ 3. 均線全面上揚 (5T、10T、20T皆大於昨日)")
            score += 1
        else:
            st.error("❌ 3. 均線尚未全面上揚")

        if avg_inst > 0:
            st.success(f"✅ 4. 籌碼偏多：近三日平均買超 {int(avg_inst):,} 張")
            score += 1
        elif avg_inst < 0:
            st.error(f"❌ 4. 籌碼偏空：近三日平均賣超 {abs(int(avg_inst)):,} 張")
        else:
            st.error(f"❌ 4. 籌碼無明顯動向或等待更新")

        if float(today['Close']) > float(df.iloc[-60]['Close']):
            st.success("✅ 5. 股價大於季線扣抵 (60MA趨勢向上)")
            score += 1
        else:
            st.error("❌ 5. 股價小於季線扣抵")

        macd_diff = float(today['DIF']) - float(today['MACD'])
        if macd_diff > 0:
            st.success(f"✅ 6. DIF - MACD 大於 0 (目前數值: {macd_diff:.3f})")
            score += 1
        else:
            st.error(f"❌ 6. DIF - MACD 小於或等於 0 (目前數值: {macd_diff:.3f})")

        if float(today['Close']) > float(today['5MA']):
            st.success(f"✅ 7. 股價站穩 5T ({float(today['5MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 7. 股價跌破 5T ({float(today['5MA']):.2f})")

        if float(today['Close']) > float(today['10MA']):
            st.success(f"✅ 8. 股價站穩 10T ({float(today['10MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 8. 股價跌破 10T ({float(today['10MA']):.2f})")

        if float(today['Close']) > float(today['20MA']):
            st.success(f"✅ 9. 股價站穩 20T ({float(today['20MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 9. 股價跌破 20T ({float(today['20MA']):.2f})")
            
        is_red_candle = float(today['Close']) > float(today['Open'])
        if (today_volume > float(today['5VMA']) and today_volume > float(today['10VMA']) and is_red_candle) or is_limit_up:
            st.success(f"✅ 10. 量能健康：溫和放量收紅K，或強勢漲停籌碼鎖定")
            score += 1
        else:
            st.error(f"❌ 10. 量能未達標：量縮或收黑K (留意出貨風險)")

        st.divider()
        st.subheader("💡 系統最終評級 (滿分 10 項)")
        if score >= 8:
            st.balloons()
            st.markdown(f"### 🔥 **S 級：強勢爆發！** (達成 {score}/10 項)")
        elif score >= 5:
            st.markdown(f"### ⚠️ **A 級：多頭發酵中** (達成 {score}/10 項)")
        else:
            st.markdown(f"### ❄️ **B 級：弱勢或盤整** (達成 {score}/10 項)")
