import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import datetime

# Page config
st.set_page_config(page_title="Telegram AI Dashboard", page_icon="🤖", layout="wide")

# Database connection
def get_connection():
    return sqlite3.connect('data/raw_messages.db')

# Load data
def load_data():
    conn = get_connection()
    query = """
    SELECT internal_id, chat_name, author_name, content, summary, tags, timestamp, processed
    FROM messages
    ORDER BY timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.title("🤖 Telegram AI 信息自动化中心")

# Sidebar
st.sidebar.header("⚙️ 控制面板")
if st.sidebar.button("🔄 刷新数据"):
    st.rerun()

# Stats
df = load_data()
total = len(df)
analyzed = len(df[df['processed'] == 1])
st.sidebar.metric("总消息数", total)
st.sidebar.metric("已 AI 分析", analyzed)

# Tabs
tab1, tab2 = st.tabs(["📊 已分析信息", "📥 原始数据"])

with tab1:
    st.header("已分析消息详情")
    analyzed_df = df[df['processed'] == 1].copy()
    
    if not analyzed_df.empty:
        for idx, row in analyzed_df.iterrows():
            with st.expander(f"🔹 {row['chat_name']} - {row['timestamp'][:16]}", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**AI 摘要:**")
                    st.info(row['summary'])
                    
                    st.markdown("**标签:**")
                    tags = row['tags']
                    if isinstance(tags, str):
                        try:
                            tags = json.loads(tags)
                        except:
                            tags = []
                    
                    if tags:
                        tag_cols = st.columns(len(tags))
                        for i, tag in enumerate(tags):
                            st.button(tag, key=f"tag_{idx}_{i}")
                
                with col2:
                    st.markdown("**元数据:**")
                    st.write(f"作者: {row['author_name']}")
                    st.write(f"平台: Telegram")
                    
                with st.container():
                    st.markdown("**原始内容:**")
                    st.code(row['content'], language=None)
    else:
        st.write("暂无已分析的消息。")

with tab2:
    st.header("数据库原始消息")
    st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("*由 Antigravity 强力驱动*")
