import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="股市短線評級 9.0", page_icon="⚡", layout="wide")
st.title("⚡ 專屬股市短線評級 - 純技術指標版")

# --- 第一區：快速輸入 ---
stock_id = st.text_input("請輸入台股代號 (例如: 2337)", "1711")

if st.button("🚀 立即極速分析"):
    yf_symbol = f"{stock_id}.TW"
    
    with st.spinner("正在抓取最新數據並計算指標..."):
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="1y")
        
        if df.empty:
            st.error(f"❌ 找不到代號「{stock_id}」的數據，請確認代號是否正確。")
        else:
            # --- 1. 自動運算指標 ---
            df['5MA'] = df['Close'].rolling(5).mean()
            df['10MA'] = df['Close'].rolling(10).mean()
            df['20MA'] = df['Close'].rolling(20).mean()
            df['60MA'] = df['Close'].rolling(60).mean()
            df['5VMA'] = df['Volume'].rolling(5).mean()
            df['10VMA'] = df['Volume'].rolling(10).mean()
            
            # KD 指標
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
            df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            
            # MACD 指標
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today = df.iloc[-1]
            yesterday = df.iloc[-2]
            
            # 週轉率計算
            shares = ticker.info.get('sharesOutstanding', 0)
            real_turnover = (today['Volume'] / shares * 100) if shares else 0
            
            # --- 2. 呈現評級報告 ---
            st.subheader(f"📊 {stock_id} 短線診斷報告 (技術面)")
            
            score = 0
            details = []
            
            # 判斷指標 (已移除籌碼項)
            # 1. 周轉率
            if real_turnover > 9.0: score += 1; details.append(f"✅ 1. 週轉率 > 9% (實測: {real_turnover:.2f}%)")
            else: details.append(f"❌ 1. 週轉率未達 9% (實測: {real_turnover:.2f}%)")
            
            # 2. KD 低檔黃叉
            k_val, d_val = float(today['K']), float(today['D'])
            if k_val > d_val and k_val < 60 and d_val < 55: score += 1; details.append(f"✅ 2. KD 低檔黃金交叉 (K:{k_val:.1f})")
            else: details.append(f"❌ 2. KD 未符合低檔交叉條件 (K:{k_val:.1f})")
            
            # 3. 均線上揚
            if today['5MA'] > yesterday['5MA'] and today['10MA'] > yesterday['10MA'] and today['20MA'] > yesterday['20MA']:
                score += 1; details.append("✅ 3. 5/10/20T 均線全面上揚")
            else: details.append("❌ 3. 均線尚未全面上揚")
            
            # 4. 季線趨勢
            if today['Close'] > df.iloc[-60]['Close']: score += 1; details.append("✅ 4. 股價大於季線扣抵")
            else: details.append("❌ 4. 股價小於季線扣抵")
            
            # 5. MACD
            if (today['DIF'] - today['MACD']) > 0: score += 1; details.append("✅ 5. DIF-MACD 零軸之上 (紅柱)")
            else: details.append("❌ 5. DIF-MACD 水下 (綠柱)")
            
            # 6. 站穩 5T
            if today['Close'] > today['5MA']: score += 1; details.append("✅ 6. 站穩 5T")
            else: details.append("❌ 6. 跌破 5T")
            
            # 7. 站穩 10T
            if today['Close'] > today['10MA']: score += 1; details.append("✅ 7. 站穩 10T")
            else: details.append("❌ 7. 跌破 10T")
            
            # 8. 站穩 20T
            if today['Close'] > today['20MA']: score += 1; details.append("✅ 8. 站穩 20T")
            else: details.append("❌ 8. 跌破 20T")
            
            # 9. 量能
            is_red = today['Close'] > today['Open']
            if today['Volume'] > today['5VMA'] and is_red: score += 1; details.append("✅ 9. 量增收紅K")
            else: details.append("❌ 9. 量縮或收黑K")

            # 顯示結果
            for d in details:
                if "✅" in d: st.success(d)
                else: st.error(d)
            
            st.divider()
            # 評分標準按比例微調
            if score >= 7: st.balloons(); st.success(f"🔥 S 級：強勢爆發！ ({score}/9)")
            elif score >= 4: st.warning(f"⚠️ A 級：多頭發酵 ({score}/9)")
            else: st.error(f"❄️ B 級：弱勢盤整 ({score}/9)")
