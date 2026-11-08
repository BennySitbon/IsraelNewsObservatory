import os, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Israel News Observatory", page_icon="📰", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { direction: rtl; }
[data-testid="stAppViewContainer"] { background: #f5f7fc; }
[data-testid="stSidebar"] { direction: rtl; }
h1,h2,h3,p,div { text-align: right; }
.metric-card {background:white;border:1px solid #e3e8f2;border-radius:14px;padding:16px;}
.small-muted {color:#667085;font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

DB = os.getenv("DATABASE_PATH", "data/news.db")
st.title("🇮🇱 Israel News Observatory")
st.caption("ניטור וניתוח כותרות מאתרי חדשות בישראל · נתוני המערכת מתעדכנים בהרצות האיסוף")

if not Path(DB).exists():
    st.warning("עדיין אין מסד נתונים. הרץ את `python -m src.collect` או הפעל את GitHub Action.")
    st.stop()

@st.cache_data(ttl=60)
def load_data():
    con = sqlite3.connect(DB)
    articles = pd.read_sql_query("SELECT * FROM articles", con)
    obs = pd.read_sql_query("SELECT * FROM observations", con)
    runs = pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC LIMIT 20", con)
    con.close()
    return articles, obs, runs

articles, obs, runs = load_data()
if articles.empty:
    st.info("לא נאספו כתבות עדיין.")
    st.stop()

articles["first_seen_at"] = pd.to_datetime(articles["first_seen_at"], utc=True, errors="coerce")
obs["observed_at"] = pd.to_datetime(obs["observed_at"], utc=True, errors="coerce")
today = datetime.now(timezone.utc).date()
with st.sidebar:
    st.header("מסננים")
    days = st.selectbox("טווח זמן", [1, 7, 30, 90], index=1, format_func=lambda x: f"{x} ימים")
    sources = sorted(articles["source"].dropna().unique().tolist())
    selected = st.multiselect("אתרים", sources, default=sources)
    st.caption("האחוזים מחושבים לפי כתבות ייחודיות, אלא אם צוין אחרת.")

cutoff = pd.Timestamp(datetime.now(timezone.utc) - timedelta(days=days))
df = articles[(articles["first_seen_at"] >= cutoff) & (articles["source"].isin(selected))]
if df.empty:
    st.warning("אין נתונים בטווח ובמסננים שנבחרו.")
    st.stop()

total = len(df)
negative = (df["sentiment"] == "שלילי").mean() * 100
positive = (df["sentiment"] == "חיובי").mean() * 100
neutral = (df["sentiment"] == "ניטרלי").mean() * 100
c1,c2,c3,c4 = st.columns(4)
c1.metric("כתבות ייחודיות", f"{total:,}")
c2.metric("שליליות", f"{negative:.1f}%")
c3.metric("חיוביות", f"{positive:.1f}%")
c4.metric("ניטרליות", f"{neutral:.1f}%")

left, right = st.columns(2)
with right:
    st.subheader("חלוקת נושאים")
    cat = df.groupby("category", dropna=False).size().reset_index(name="כתבות").sort_values("כתבות", ascending=False)
    fig = px.pie(cat, names="category", values="כתבות", hole=.58)
    fig.update_layout(legend_title_text="", margin=dict(t=10,b=10,l=10,r=10))
    st.plotly_chart(fig, use_container_width=True)
with left:
    st.subheader("סנטימנט הכותרות")
    sent = df.groupby("sentiment").size().reset_index(name="כתבות")
    fig = px.pie(sent, names="sentiment", values="כתבות", hole=.58,
                 color="sentiment", color_discrete_map={"שלילי":"#ef4444","ניטרלי":"#9ca3af","חיובי":"#22c55e"})
    fig.update_layout(legend_title_text="", margin=dict(t=10,b=10,l=10,r=10))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("השוואה בין אתרים")
site = df.groupby("source").agg(
    כתבות=("id","count"),
    שליליות=("sentiment",lambda x: (x=="שלילי").mean()*100),
    חיוביות=("sentiment",lambda x: (x=="חיובי").mean()*100)
).reset_index()
if not site.empty:
    fig = px.bar(site, x="source", y=["שליליות","חיוביות"], barmode="group")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(site.round(1), use_container_width=True, hide_index=True)

st.subheader("מגמות לאורך זמן")
trend = df.copy()
trend["יום"] = trend["first_seen_at"].dt.tz_convert(None).dt.date
daily = trend.groupby(["יום","sentiment"]).size().reset_index(name="כתבות")
if not daily.empty:
    fig = px.line(daily, x="יום", y="כתבות", color="sentiment",
                  color_discrete_map={"שלילי":"#ef4444","ניטרלי":"#9ca3af","חיובי":"#22c55e"}, markers=True)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("כותרות אחרונות")
display = df.sort_values("first_seen_at", ascending=False)[
    ["first_seen_at","source","title","category","subcategory","sentiment","severity","confidence","url"]
].head(100).copy()
display["first_seen_at"] = display["first_seen_at"].dt.strftime("%Y-%m-%d %H:%M UTC")
st.dataframe(display, use_container_width=True, hide_index=True,
             column_config={"url": st.column_config.LinkColumn("קישור", display_text="פתיחת כתבה"),
                            "confidence": st.column_config.NumberColumn("ביטחון", format="%.2f")})

with st.expander("מצב איסוף ותקלות"):
    st.dataframe(runs, use_container_width=True, hide_index=True)
    if not runs.empty and runs.iloc[0].get("errors"):
        st.error(runs.iloc[0]["errors"])

st.caption("הערה מחקרית: RSS אינו בהכרח משקף את עמוד הבית או את בולטות הכותרת. סיווג אוטומטי עשוי לטעות; confidence נמוך מצביע על צורך בבדיקה.")
