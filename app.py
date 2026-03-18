import streamlit as st

st.set_page_config(page_title="股市短線評級 5.0", page_icon="⚡")
st.title("⚡ 專屬股市短線評級 - 實戰診斷器")
st.write("由於 API 資料常有誤差，建議參考看盤軟體數值手動輸入，或直接提供截圖進行 AI 分析。")

# --- 第一部分：手動輸入診斷表 ---
with st.expander("📝 手動輸入數值進行 10 大指標評級", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 技術與量能")
        v_turnover = st.number_input("今日周轉率 (%)", min_value=0.0, value=9.5, step=0.1)
        v_k = st.number_input("今日 K 值", min_value=0.0, max_value=100.0, value=55.0)
        v_d = st.number_input("今日 D 值", min_value=0.0, max_value=100.0, value=50.0)
        v_macd_red = st.checkbox("DIF - MACD 位於 0 軸之上 (柱狀圖翻紅)", value=True)
        v_volume_healthy = st.checkbox("今日量 > 5T/10T 均量且收紅 K (或強勢漲停)", value=True)

    with col2:
        st.subheader("法人與均線")
        v_inst_3d = st.number_input("近三日法人平均買賣超 (張)", value=500)
        v_ma_up = st.checkbox("5T、10T、20T 均線皆全面上揚", value=True)
        v_above_60ma = st.checkbox("股價大於季線扣抵 (60MA 趨勢向上)", value=True)
        v_stay_5t = st.checkbox("股價站穩 5T", value=True)
        v_stay_10t = st.checkbox("股價站穩 10T", value=True)
        v_stay_20t = st.checkbox("股價站穩 20T", value=True)

    if st.button("啟動數據評級"):
        score = 0
        details = []
        
        # 1. 周轉率
        if v_turnover > 9.0: score += 1; details.append("✅ 周轉率 > 9%")
        # 2. KD 低檔交叉
        if v_k > v_d and v_k < 60 and v_d < 55: score += 1; details.append("✅ KD 低檔黃金交叉")
        # 3. 均線上揚
        if v_ma_up: score += 1; details.append("✅ 5/10/20T 均線上揚")
        # 4. 籌碼買超
        if v_inst_3d > 0: score += 1; details.append("✅ 近三日法人平均買超")
        # 5. 季線趨勢
        if v_above_60ma: score += 1; details.append("✅ 股價大於季線扣抵")
        # 6. MACD 紅柱
        if v_macd_red: score += 1; details.append("✅ DIF-MACD 零軸之上")
        # 7-9. 站穩均線
        if v_stay_5t: score += 1; details.append("✅ 站穩 5T")
        if v_stay_10t: score += 1; details.append("✅ 站穩 10T")
        if v_stay_20t: score += 1; details.append("✅ 站穩 20T")
        # 10. 量能
        if v_volume_healthy: score += 1; details.append("✅ 量能健康/強勢漲停")

        st.divider()
        st.subheader(f"📊 最終得分：{score} / 10")
        for d in details: st.write(d)
        
        if score >= 8: st.success("🔥 S 級：強勢爆發！"); st.balloons()
        elif score >= 5: st.warning("⚠️ A 級：多頭發酵中")
        else: st.error("❄️ B 級：弱勢或盤整")

# --- 第二部分：AI 截圖分析引導 ---
st.divider()
st.subheader("📸 AI 視覺診斷模式")
st.write("如果你不確定數值，請直接把你的 **技術分析圖** 與 **籌碼圖** 截圖貼到下方的對話框給我。")
st.info("💡 我會根據圖片內容，精準比對你設定的 10 大指標並給出評級結論。")
