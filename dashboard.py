import streamlit as st
import pandas as pd
import plotly.express as px
from db.database import SessionLocal, Account, Post, Insight

st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")

st.title("📊 Market Intelligence Dashboard")

def load_accounts():
    db = SessionLocal()
    accounts = db.query(Account).all()
    db.close()
    return pd.DataFrame([{
        "ID": a.id,
        "Platform": a.platform,
        "Username": a.username,
        "Followers": a.followers_count
    } for a in accounts])

def load_posts():
    db = SessionLocal()
    posts = db.query(Post).all()
    db.close()
    return pd.DataFrame([{
        "Account ID": p.account_id,
        "Type": p.media_type,
        "URL": p.post_url,
        "Caption": p.caption,
        "Timestamp": p.timestamp
    } for p in posts])

def load_insights():
    db = SessionLocal()
    insights = db.query(Insight).order_by(Insight.created_at.desc()).all()
    db.close()
    return insights

# --- UI Setup ---
tab1, tab2, tab3 = st.tabs(["Accounts Overview", "Posts Analysis", "AI Insights"])

with tab1:
    st.header("Tracked Competitors")
    accounts_df = load_accounts()
    if not accounts_df.empty:
        st.dataframe(accounts_df, use_container_width=True)
        # Simple chart
        fig = px.pie(accounts_df, names="Platform", title="Competitors by Platform")
        st.plotly_chart(fig)
    else:
        st.info("No accounts collected yet.")

with tab2:
    st.header("Recent Content")
    posts_df = load_posts()
    if not posts_df.empty:
        # Group by type
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(posts_df[["Type", "Caption", "Timestamp"]], use_container_width=True)
        with col2:
            fig2 = px.histogram(posts_df, x="Type", title="Content Distribution")
            st.plotly_chart(fig2)
    else:
        st.info("No posts collected yet.")

with tab3:
    st.header("Gemini AI Insights")
    insights = load_insights()
    if insights:
        for ins in insights:
            with st.expander(f"Report for: {ins.target} ({ins.created_at.strftime('%Y-%m-%d %H:%M')})"):
                st.markdown(ins.insight_text)
    else:
        st.info("No AI insights generated yet. Run the collector with --analyze.")
