import streamlit as st
import pandas as pd
import requests
import datetime
import yfinance as yf

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
    .status-mid { background-color: #3E321A; color: #F1C40F; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #F1C40F; min-width: 90px; text-align: center; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; min-width: 90px; text-align: center; }
    input[data-testid="stTextInput"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; text-align: center; font-size: 18px !important;}
    div[data-baseweb="select"] > div { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; font-size: 16px !important; }
    ul[role="listbox"] { background-color: #1E1E1E !important; color: #EAEAEA !important; }
</style>
""", unsafe_allow_html=True)

# --- 首頁標題 ---
st.markdown('<h1 class="main-title" style="text-align:center;">⚡ 台股短線買入評級</h1>', unsafe_allow_html=True)
st.write("") 

# --- 🎯 數據庫引擎 ---
@st.cache_data(ttl=86400)
def fetch_stock_mapping
