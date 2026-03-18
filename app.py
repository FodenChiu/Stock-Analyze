import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="股市短線評級 11.0", page_icon="⚡", layout="wide")
st.title("⚡ 專屬股市短線評級 - 上市櫃全支援版")

# --- 快速輸入 ---
stock_id = st.text_input("請輸入台股代號 (例如: 1711 或 8069)", "1711")

if st.button("🚀 啟動權重分析"):
    # --- 🚀 自動判定上市櫃後綴 ---
    def get_stock_data(sid):
        # 先試上市 (.TW)
        ticker = yf.Ticker(f"{sid}.TW")
        df = ticker.history(period="1y")
        if not df.empty:
            return df, ticker
        
        # 失敗則試上櫃 (.TWO)
        ticker = yf.Ticker(f"{sid}.TWO")
        df = ticker.history(period="1y")
        if not df.empty:
            return df, ticker
        
        return None, None

    with st.spinner(f"正在分析 {stock_id} 的數據..."):
        df, ticker = get_stock_data(stock_id)
        
        if df is None:
            st.error(f"❌ 找不到代號「{stock_id}」的數據，請確認代號是否正確。")
        else:
            # --- 1. 自動運算指標 ---
            df['5MA'] = df['Close'].rolling(5).mean()
            df['10MA'] = df['Close'].rolling(10).mean()
            df['20MA'] = df['Close'].rolling(20).mean()
            df['60MA'] = df['Close'].rolling(60).mean()
            df['5VMA'] = df['Volume'].rolling(5).mean()
            df['10VMA'] = df['Volume'].rolling(10).mean()
            
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
            df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today = df.iloc[-1]
            yesterday = df.iloc[-2]
            
            shares = ticker.info.get('sharesOutstanding', 0)
            real_turnover = (today['Volume'] / shares * 100) if shares else 0
            
            # --- 2. 加權計分邏輯 ---
            st.subheader(f"📊 {stock_id} 加權診斷報告")
            
            total_score = 0
            details = []
            
            # 指標判定 (依據你的權重)
            # 1. 周轉率 > 9% (10%)
            if real_turnover > 9.0:
                total_score += 10; details.append(f"✅ 1. 週轉率 > 9% ({real_turnover:.2f}%) 【+10分】")
            else:
                details.append(f"❌ 1. 週轉率不足 ({real_turnover:.2f}%) 【0分】")
            
            # 2. KD 低檔黃叉 (20%)
            k_val, d_val = float(today['K']), float(today['D'])
            if k_val > d_val and k_val < 60 and d_val < 55:
                total_score += 20; details.append(f"✅ 2. KD 低檔黃金交叉 (K:{k_val:.1f}) 【+20分】")
            else:
                details.append(f"❌ 2. KD 未符合低檔交叉條件 (K:{k_val:.1f}) 【0分】")
            
            # 3. 5/10/20T 均線上揚 (20%)
            if today['5MA'] > yesterday['5MA'] and today['10MA'] > yesterday['10MA'] and today['20MA'] > yesterday['20MA']:
                total_score += 20; details.append("✅ 3. 5/10/20T 均線全面上揚 【+20分】")
            else:
                details.append("❌ 3. 均線尚未全面上揚 【0分】")
            
            # 4. 股價大於季線扣抵 (5%)
            if today['Close'] > df.iloc[-60]['Close']:
                total_score += 5; details.append("✅ 4. 股價大於季線扣抵 【+5分】")
            else:
                details.append("❌ 4. 股價小於季線扣抵 【0分】")
            
            # 5. DIF-MACD 零軸之上 (5%)
            if (today['DIF'] - today['MACD']) > 0:
                total_score += 5; details.append("✅ 5. DIF-MACD 零軸之上 【+5分】")
            else:
                details.append("❌ 5. DIF-MACD 零軸之下 【0分】")
            
            # 6-8. 站穩均線 (各 5%)
            for i, (ma_key, label) in enumerate([('5MA', '5T'), ('10MA', '10T'), ('20MA', '20T')], 6):
                if today['Close'] > today[ma_key]:
                    total_score += 5; details.append(f"✅ {i}. 站穩 {label} 【+5分】")
                else:
                    details.append(f"❌ {i}. 跌破 {label} 【0分】")
            
            # 9. 量能健康 (20%)
            is_red = today['Close'] > today['Open']
            if today['Volume'] > today['5VMA'] and is_red:
                total_score += 20; details.append("✅ 9. 量增收紅K 【+20分】")
            else:
                details.append("❌ 9. 量縮或收黑K (動能不足) 【0分】")

            # 顯示列表
            for d in details:
                if "✅" in d: st.success(d)
                else: st.error(d)
            
            st.divider()
            st.subheader(f"🏆 最終評分：{total_score} / 100 分")
            
            if total_score >= 70:
                st.balloons(); st.success(f"🔥 **值得買入！** (總分 {total_score}% 已達標)")
            elif total_score >= 40:
                st.warning(f"⚠️ **列入觀察** (總分 {total_score}% 尚未達標)")
            else:
                st.error(f"❄️ **暫不考慮** (總分 {total_score}% 指標太弱)")
