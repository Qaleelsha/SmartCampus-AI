import os
import pickle
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo import MongoClient


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="SmartCampus AI | Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#14213D"
BLUE = "#2563EB"
TEAL = "#0D9488"
RED = "#DC2626"
AMBER = "#D97706"
MUTED = "#64748B"
GRID = "#E8EDF5"

RISK_ORDER = ["HIGH", "MEDIUM", "LOW"]
RISK_COLORS = {"HIGH": RED, "MEDIUM": AMBER, "LOW": TEAL}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")

# Newer Streamlit versions use width="stretch" instead of use_container_width
_version = tuple(int(x) for x in st.__version__.split(".")[:2])
STRETCH = {"width": "stretch"} if _version >= (1, 50) else {"use_container_width": True}


# --------------------------------------------------
# STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #F5F7FB; }
    .block-container { padding-top: 2.2rem; max-width: 1300px; }

    [data-testid="stHeader"] { background: rgba(245, 247, 251, 0.9); }
    #MainMenu, footer { visibility: hidden; }

    /* main-area headings */
    .block-container h1, .block-container h2,
    .block-container h3, .block-container h4 { color: #14213D; letter-spacing: -0.4px; }

    /* ---------- sidebar ---------- */
    [data-testid="stSidebar"] { background: #101B33; }
    [data-testid="stSidebar"] * { color: #E8EEF9; }
    [data-testid="stSidebar"] hr { border-color: #34415D; }

    [data-testid="stSidebar"] pre,
    [data-testid="stSidebar"] code {
        background: #1B2A4A !important;
        color: #9FD3FF !important;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] .stButton button {
        background: #2563EB;
        border: none;
        border-radius: 10px;
        font-weight: 600;
    }
    [data-testid="stSidebar"] .stButton button:hover { background: #1D4ED8; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #1B2A4A;
        border-color: #34415D;
    }

    .brand {
        font-size: 25px; font-weight: 800; color: #FFFFFF;
        letter-spacing: -0.8px; margin-bottom: 2px;
    }
    .brand-subtitle {
        font-size: 11px; color: #AAB8D0; letter-spacing: 1.2px; margin-bottom: 18px;
    }

    /* ---------- hero ---------- */
    .hero {
        background: linear-gradient(120deg, #14213D 0%, #244A83 60%, #2F6BC4 100%);
        padding: 28px 32px;
        border-radius: 18px;
        margin-bottom: 22px;
        color: white;
        box-shadow: 0 10px 28px rgba(20, 33, 61, 0.18);
    }
    .hero h1 {
        color: white !important; font-size: 30px; font-weight: 800;
        margin: 0 0 8px 0; letter-spacing: -1px;
    }
    .hero p { color: #D8E4F8; font-size: 14px; margin: 0; line-height: 1.6; }
    .chip {
        display: inline-block; background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.22);
        padding: 4px 12px; border-radius: 999px;
        font-size: 11.5px; font-weight: 600; margin: 14px 8px 0 0;
        color: #FFFFFF;
    }

    /* ---------- KPI cards ---------- */
    .kpi {
        background: #FFFFFF;
        border: 1px solid #E5EAF3;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 3px 12px rgba(20, 33, 61, 0.05);
        border-top: 4px solid var(--accent, #2563EB);
        height: 100%;
    }
    .kpi-label { color: #64748B; font-size: 13px; font-weight: 600; white-space: nowrap; }
    .kpi-value {
        color: #14213D; font-size: 32px; font-weight: 800;
        letter-spacing: -1px; margin: 4px 0 2px 0; white-space: nowrap;
    }
    .kpi-value small { font-size: 15px; font-weight: 600; color: #64748B; }
    .kpi-sub { font-size: 12px; font-weight: 600; color: #64748B; }
    .kpi-sub.bad { color: #DC2626; }
    .kpi-sub.good { color: #0D9488; }

    /* ---------- section headings ---------- */
    .section-title { color: #14213D; font-size: 19px; font-weight: 700; margin: 26px 0 2px 0; }
    .section-subtitle { color: #64748B; font-size: 12.5px; margin-bottom: 12px; }

    /* ---------- chart cards ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border-radius: 14px;
        border-color: #E5EAF3;
        box-shadow: 0 3px 12px rgba(20, 33, 61, 0.04);
    }

    /* ---------- tabs ---------- */
    div[data-testid="stTabs"] button { font-weight: 650; }

    .info-note {
        background: #EFF6FF; border-left: 4px solid #2563EB;
        padding: 13px 16px; border-radius: 7px;
        color: #1E3A5F; font-size: 13px; line-height: 1.6; margin-top: 14px;
    }
    .footer {
        border-top: 1px solid #E2E8F0; margin-top: 35px; padding-top: 16px;
        color: #64748B; font-size: 12px; line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def kpi_card(label, value, sub="", tone="", accent=BLUE):
    st.markdown(
        f"""
        <div class="kpi" style="--accent:{accent};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub {tone}">{sub}&nbsp;</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title, subtitle=""):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def style_fig(fig, height=360):
    # explicit colours so the chart never inherits a dark theme
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, Arial", color=NAVY, size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, title_text="",
        ),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID)
    return fig


def show_chart(fig):
    st.plotly_chart(fig, theme=None, **STRETCH)


def color_risk(value):
    styles = {
        "HIGH": "background-color:#FEE2E2;color:#B91C1C;font-weight:600",
        "MEDIUM": "background-color:#FEF3C7;color:#B45309;font-weight:600",
        "LOW": "background-color:#CCFBF1;color:#0F766E;font-weight:600",
    }
    return styles.get(value, "")


def style_risk_column(frame):
    styler = frame.style
    apply = styler.map if hasattr(styler, "map") else styler.applymap
    return apply(color_risk, subset=["riskLevel"])


# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------

@st.cache_data(ttl=60, show_spinner="Loading student records...")
def load_students():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    records = list(client["smartcampus"]["students"].find({}, {"_id": 0}))
    client.close()
    return pd.DataFrame(records)


@st.cache_resource
def load_model():
    with open("risk_model.pkl", "rb") as file:
        saved = pickle.load(file)
    return saved["model"], saved["features"]


try:
    df = load_students()
except Exception as error:
    st.error("Unable to connect to MongoDB.")
    st.markdown("Make sure your local MongoDB service is running.")
    st.code(str(error))
    st.stop()

if df.empty:
    st.warning("No student records found in MongoDB.")
    st.stop()


# --------------------------------------------------
# PREPARE AND VALIDATE DATA
# --------------------------------------------------

required_columns = [
    "studentId", "name", "department", "semester", "attendance", "averageMarks",
]
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    st.error("Required fields are missing from MongoDB: " + ", ".join(missing_columns))
    st.stop()

for col in ["attendance", "averageMarks", "semester"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["assignmentsCompleted"] = pd.to_numeric(
    df.get("assignmentsCompleted", pd.Series(0, index=df.index)),
    errors="coerce",
).fillna(0)

df = df.dropna(subset=required_columns).copy()

if df.empty:
    st.warning("No valid student records are available.")
    st.stop()

df["department"] = df["department"].astype(str)
df["semester"] = df["semester"].astype(int)


# --------------------------------------------------
# RISK CLASSIFICATION
# --------------------------------------------------

model_source = "Random Forest model"

try:
    model, features = load_model()

    for feature in features:
        if feature not in df.columns:
            raise ValueError(f"Missing model feature: {feature}")

    df["riskLevel"] = model.predict(df[features]).astype(str)

except Exception:
    # fallback if the saved model is unavailable
    model_source = "Rule-based fallback"

    def calculate_risk(row):
        low_attendance = row["attendance"] < 75
        low_marks = row["averageMarks"] < 60
        if low_attendance and low_marks:
            return "HIGH"
        if low_attendance or low_marks:
            return "MEDIUM"
        return "LOW"

    df["riskLevel"] = df.apply(calculate_risk, axis=1)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="brand">🎓 SmartCampus AI</div>
        <div class="brand-subtitle">STUDENT INTELLIGENCE PLATFORM</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("### Filters")
    st.caption("Applies to every chart and table.")

    all_departments = sorted(df["department"].unique().tolist())
    all_semesters = sorted(df["semester"].unique().tolist())

    sel_departments = st.multiselect("Departments", all_departments, default=all_departments)
    sel_semesters = st.multiselect("Semesters", all_semesters, default=all_semesters)

    st.divider()

    st.markdown("### Data source")
    st.markdown("🟢 Local MongoDB")
    st.code("smartcampus.students", language="text")

    if st.button("↻ Refresh dashboard", **STRETCH):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Academic Analytics · Mini Project")


# apply global filters
df_all = df
df = df[df["department"].isin(sel_departments) & df["semester"].isin(sel_semesters)].copy()

if df.empty:
    st.warning("No students match the selected filters.")
    st.stop()


# --------------------------------------------------
# HERO
# --------------------------------------------------

st.markdown(
    f"""
    <div class="hero">
        <h1>Academic Performance Dashboard</h1>
        <p>A unified view of student outcomes, attendance, department
        performance, and academic support indicators.</p>
        <span class="chip">● LIVE DATABASE VIEW</span>
        <span class="chip">Refreshed {datetime.now().strftime("%d %b %Y, %I:%M %p")}</span>
        <span class="chip">Model: {model_source}</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------

total_students = len(df)
average_marks = df["averageMarks"].mean()
average_attendance = df["attendance"].mean()
high_risk_count = int((df["riskLevel"] == "HIGH").sum())
high_risk_pct = high_risk_count / total_students * 100
below_75 = int((df["attendance"] < 75).sum())

k1, k2, k3, k4 = st.columns(4)

with k1:
    kpi_card(
        "👥 Total Students", f"{total_students:,}",
        f"of {len(df_all):,} in database", accent=BLUE,
    )
with k2:
    kpi_card(
        "📊 Average Marks", f"{average_marks:.1f}<small> / 100</small>",
        "across selected students", accent=TEAL,
    )
with k3:
    kpi_card(
        "📅 Avg Attendance", f"{average_attendance:.1f}<small>%</small>",
        f"{below_75} students below 75%",
        "bad" if average_attendance < 75 else "good", accent=AMBER,
    )
with k4:
    kpi_card(
        "⚠️ High-Risk Students", f"{high_risk_count:,}",
        f"↑ {high_risk_pct:.1f}% of records",
        "bad" if high_risk_count else "good", accent=RED,
    )


# --------------------------------------------------
# OVERVIEW CHARTS
# --------------------------------------------------

section("Academic Overview", "Department comparisons and academic risk distribution")

department_data = (
    df.groupby("department")
    .agg(
        totalStudents=("studentId", "count"),
        averageMarks=("averageMarks", "mean"),
        averageAttendance=("attendance", "mean"),
    )
    .reset_index()
)

risk_data = (
    df["riskLevel"].value_counts()
    .rename_axis("riskLevel")
    .reset_index(name="students")
)

chart_col1, chart_col2 = st.columns([1.55, 1])

with chart_col1:
    with st.container(border=True):
        st.markdown("#### Department Performance")

        department_long = department_data.melt(
            id_vars="department",
            value_vars=["averageMarks", "averageAttendance"],
            var_name="metric",
            value_name="score",
        )
        department_long["metric"] = department_long["metric"].map({
            "averageMarks": "Average Marks",
            "averageAttendance": "Average Attendance (%)",
        })

        fig_department = px.bar(
            department_long,
            x="department", y="score", color="metric",
            barmode="group", text_auto=".1f",
            color_discrete_map={
                "Average Marks": BLUE,
                "Average Attendance (%)": TEAL,
            },
            labels={"department": "Department", "score": "Average score"},
        )
        fig_department.update_traces(
            textposition="outside", cliponaxis=False, marker_line_width=0
        )
        style_fig(fig_department, 380)
        fig_department.update_layout(bargap=0.3, yaxis=dict(range=[0, 105]))
        show_chart(fig_department)

with chart_col2:
    with st.container(border=True):
        st.markdown("#### Academic Risk Distribution")

        fig_risk = px.pie(
            risk_data,
            names="riskLevel", values="students",
            hole=0.66,
            color="riskLevel", color_discrete_map=RISK_COLORS,
            category_orders={"riskLevel": RISK_ORDER},
        )
        fig_risk.update_traces(
            textposition="outside",
            textinfo="percent+label",
            sort=False,
            marker=dict(line=dict(color="#FFFFFF", width=3)),
        )
        style_fig(fig_risk, 380)
        fig_risk.update_layout(
            showlegend=False,
            annotations=[dict(
                text=f"<b style='font-size:28px'>{total_students}</b><br>"
                     f"<span style='color:{MUTED}'>Students</span>",
                x=0.5, y=0.5, showarrow=False, font=dict(color=NAVY, size=14),
            )],
        )
        show_chart(fig_risk)


# --------------------------------------------------
# TABS
# --------------------------------------------------

overview_tab, students_tab, insights_tab, data_tab = st.tabs([
    "📌 Overview",
    "👥 Student Directory",
    "📈 Academic Insights",
    "🗄️ Data Explorer",
])


# ---------- OVERVIEW TAB ----------

with overview_tab:
    st.markdown("### Students Requiring Attention")

    at_risk = df[df["riskLevel"].isin(["HIGH", "MEDIUM"])].copy()
    at_risk["riskRank"] = at_risk["riskLevel"].map({"HIGH": 0, "MEDIUM": 1})
    at_risk = at_risk.sort_values(["riskRank", "averageMarks"])

    if at_risk.empty:
        st.success("No students meet the current risk criteria.")
    else:
        st.caption(
            f"{len(at_risk)} students flagged HIGH or MEDIUM, "
            "sorted by risk level and lowest marks."
        )

        overview_columns = [
            "studentId", "name", "department",
            "attendance", "averageMarks", "riskLevel",
        ]

        st.dataframe(
            style_risk_column(at_risk[overview_columns]),
            hide_index=True,
            height=320,
            column_config={
                "studentId": st.column_config.TextColumn("Student ID"),
                "name": st.column_config.TextColumn("Student Name"),
                "department": st.column_config.TextColumn("Dept"),
                "attendance": st.column_config.NumberColumn("Attendance (%)", format="%.1f%%"),
                "averageMarks": st.column_config.NumberColumn("Avg Marks", format="%.1f"),
                "riskLevel": st.column_config.TextColumn("Risk"),
            },
            **STRETCH,
        )

    st.markdown(
        """
        <div class="info-note">
        <b>How to interpret risk:</b> HIGH, MEDIUM and LOW are academic
        support indicators. Review individual student records before
        making any academic decisions.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- STUDENT DIRECTORY TAB ----------

with students_tab:
    st.markdown("### Student Directory")
    st.caption("Search student records and narrow results using the filters.")

    f1, f2 = st.columns([1.6, 1])

    with f1:
        search_text = st.text_input(
            "Search by ID or name", placeholder="e.g. CSE101 or Rahul"
        )
    with f2:
        selected_risk = st.selectbox("Risk level", ["All Risk Levels"] + RISK_ORDER)

    filtered_df = df.copy()

    if search_text.strip():
        term = search_text.strip().lower()
        filtered_df = filtered_df[
            filtered_df["studentId"].astype(str).str.lower().str.contains(term, na=False)
            | filtered_df["name"].astype(str).str.lower().str.contains(term, na=False)
        ]

    if selected_risk != "All Risk Levels":
        filtered_df = filtered_df[filtered_df["riskLevel"] == selected_risk]

    st.caption(f"Showing {len(filtered_df)} of {len(df)} student records")

    directory_columns = [
        "studentId", "name", "department", "semester",
        "attendance", "averageMarks", "assignmentsCompleted", "riskLevel",
    ]
    directory_df = filtered_df[directory_columns].sort_values("studentId")

    st.dataframe(
        style_risk_column(directory_df),
        hide_index=True,
        height=420,
        column_config={
            "studentId": st.column_config.TextColumn("Student ID"),
            "name": st.column_config.TextColumn("Student Name"),
            "department": st.column_config.TextColumn("Department"),
            "semester": st.column_config.NumberColumn("Semester", format="%d"),
            "attendance": st.column_config.ProgressColumn(
                "Attendance", min_value=0, max_value=100, format="%.0f%%"
            ),
            "averageMarks": st.column_config.ProgressColumn(
                "Average Marks", min_value=0, max_value=100, format="%.0f"
            ),
            "assignmentsCompleted": st.column_config.NumberColumn("Assignments"),
            "riskLevel": st.column_config.TextColumn("Risk Level"),
        },
        **STRETCH,
    )

    st.download_button(
        "⬇️ Download filtered student report",
        data=directory_df.to_csv(index=False),
        file_name="smartcampus_student_report.csv",
        mime="text/csv",
    )

    # ----- single student profile -----
    st.markdown("---")
    st.markdown("### Student Profile")

    if filtered_df.empty:
        st.info("No students to show. Adjust the filters above.")
    else:
        options = filtered_df.sort_values("studentId")
        labels = (options["studentId"].astype(str) + "  ·  " + options["name"]).tolist()
        choice = st.selectbox("Select a student", labels)
        student = options.iloc[labels.index(choice)]

        dept_avg = df_all[df_all["department"] == student["department"]]
        marks_gap = student["averageMarks"] - dept_avg["averageMarks"].mean()
        att_gap = student["attendance"] - dept_avg["attendance"].mean()
        risk_accent = RISK_COLORS.get(student["riskLevel"], BLUE)

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            kpi_card("Risk Level", student["riskLevel"],
                     f'{student["department"]} · Semester {student["semester"]}',
                     accent=risk_accent)
        with p2:
            kpi_card("Average Marks", f'{student["averageMarks"]:.1f}',
                     f"{marks_gap:+.1f} vs dept average",
                     "good" if marks_gap >= 0 else "bad", accent=BLUE)
        with p3:
            kpi_card("Attendance", f'{student["attendance"]:.1f}%',
                     f"{att_gap:+.1f} pts vs dept average",
                     "good" if att_gap >= 0 else "bad", accent=TEAL)
        with p4:
            kpi_card("Assignments", f'{int(student["assignmentsCompleted"])}',
                     "completed", accent=AMBER)


# ---------- ACADEMIC INSIGHTS TAB ----------

with insights_tab:
    st.markdown("### Performance Insights")

    i1, i2 = st.columns(2)

    with i1:
        with st.container(border=True):
            st.markdown("#### Attendance vs Average Marks")

            fig_scatter = px.scatter(
                df,
                x="attendance", y="averageMarks",
                color="riskLevel", color_discrete_map=RISK_COLORS,
                category_orders={"riskLevel": RISK_ORDER},
                hover_name="name",
                hover_data=["studentId", "department", "semester"],
                labels={
                    "attendance": "Attendance (%)",
                    "averageMarks": "Average Marks",
                    "riskLevel": "Risk Level",
                },
                opacity=0.85,
            )
            fig_scatter.update_traces(marker=dict(size=9, line=dict(width=0.5, color="white")))
            # reference lines at the 75% attendance / 60 marks thresholds
            fig_scatter.add_vline(x=75, line_dash="dash", line_color=MUTED, opacity=0.5)
            fig_scatter.add_hline(y=60, line_dash="dash", line_color=MUTED, opacity=0.5)
            style_fig(fig_scatter, 400)
            show_chart(fig_scatter)

    with i2:
        with st.container(border=True):
            st.markdown("#### Average Marks by Semester")

            semester_data = (
                df.groupby("semester")
                .agg(averageMarks=("averageMarks", "mean"), students=("studentId", "count"))
                .reset_index()
            )

            fig_semester = px.line(
                semester_data,
                x="semester", y="averageMarks",
                markers=True, text="averageMarks",
                labels={"semester": "Semester", "averageMarks": "Average Marks"},
            )
            fig_semester.update_traces(
                line=dict(color=BLUE, width=3),
                marker=dict(size=10, color=BLUE, line=dict(width=2, color="white")),
                texttemplate="%{text:.1f}",
                textposition="top center",
            )
            style_fig(fig_semester, 400)
            fig_semester.update_layout(xaxis=dict(dtick=1))
            show_chart(fig_semester)

    i3, i4 = st.columns(2)

    with i3:
        with st.container(border=True):
            st.markdown("#### Risk Mix by Department")

            risk_by_dept = (
                df.groupby(["department", "riskLevel"]).size().reset_index(name="students")
            )
            fig_stack = px.bar(
                risk_by_dept,
                x="department", y="students", color="riskLevel",
                color_discrete_map=RISK_COLORS,
                category_orders={"riskLevel": RISK_ORDER},
                text_auto=True,
                labels={"department": "Department", "students": "Students", "riskLevel": "Risk"},
            )
            fig_stack.update_traces(marker_line_width=0)
            style_fig(fig_stack, 360)
            fig_stack.update_layout(bargap=0.35)
            show_chart(fig_stack)

    with i4:
        with st.container(border=True):
            st.markdown("#### Marks Distribution")

            fig_hist = px.histogram(
                df,
                x="averageMarks", color="riskLevel", nbins=20,
                color_discrete_map=RISK_COLORS,
                category_orders={"riskLevel": RISK_ORDER},
                labels={"averageMarks": "Average Marks", "riskLevel": "Risk"},
            )
            fig_hist.update_layout(yaxis_title="Students")
            style_fig(fig_hist, 360)
            show_chart(fig_hist)

    st.markdown("#### Department Summary")

    summary = department_data.rename(columns={
        "department": "Department",
        "totalStudents": "Total Students",
        "averageMarks": "Average Marks",
        "averageAttendance": "Average Attendance (%)",
    })

    st.dataframe(summary.round(2), hide_index=True, **STRETCH)


# ---------- DATA EXPLORER TAB ----------

with data_tab:
    st.markdown("### MongoDB Data Explorer")
    st.caption("Inspect the fields currently loaded from the students collection.")

    m1, m2, m3 = st.columns(3)
    with m1:
        kpi_card("Records Loaded", f"{len(df):,}", "after filters", accent=BLUE)
    with m2:
        kpi_card("Fields", f"{len(df.columns)}", "including risk label", accent=TEAL)
    with m3:
        kpi_card("Departments", f'{df["department"].nunique()}', "in view", accent=AMBER)

    st.markdown("#### Available fields")
    st.write(", ".join(df.columns.astype(str).tolist()))

    st.markdown("#### Raw student data")
    st.dataframe(df.sort_values("studentId"), hide_index=True, height=450, **STRETCH)

    st.download_button(
        "⬇️ Export dataset",
        data=df.to_csv(index=False),
        file_name="smartcampus_all_students.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown(
    f"""
    <div class="footer">
        <b>SmartCampus AI</b> &nbsp;·&nbsp; Intelligent NoSQL Databases Project
        <br>
        Classification source: {model_source}.
        Student records are synthetic demonstration data.
        Risk labels are based on rule-generated training labels and
        have not been validated against real academic outcomes.
    </div>
    """,
    unsafe_allow_html=True,
)