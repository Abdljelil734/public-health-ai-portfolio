import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Public Health Intelligence Platform",
    page_icon="🏥",
    layout="wide"
)

# ============================================================
# TITLE
# ============================================================

st.title("🏥 Public Health Intelligence Platform")

st.markdown(
    """
    **DHIS-2 + Data Analytics + AI-Assisted Public Health Intelligence**

    Upload your public-health reporting dataset to generate:
    - Indicator performance and ranking
    - Woreda performance and ranking
    - Priority identification
    - Public-health intelligence
    - Decision-support recommendations
    - Interactive visualizations
    """
)

# ============================================================
# SIDEBAR — DATA INPUT
# KEEP THIS STRUCTURE
# ============================================================

st.sidebar.header("📂 Data Input")

uploaded_file = st.sidebar.file_uploader(
    "Upload Excel or CSV file",
    type=["xlsx", "xls", "csv"]
)

st.sidebar.markdown("---")

st.sidebar.info(
    """
    **Version 0.6**

    Current focus:
    - Data quality
    - Performance intelligence
    - Woreda ranking
    - Indicator ranking
    - Priority identification
    - Decision support
    - Selected indicator visualization
    """
)

# ============================================================
# NO FILE UPLOADED
# ============================================================

if uploaded_file is None:

    st.info("👈 Please upload an Excel or CSV dataset from the sidebar.")

    st.markdown("## 🚀 What this platform can do")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            ### 📋 Indicator Intelligence

            - Indicator performance
            - Indicator ranking
            - Reporting completeness
            - Missing values
            - Zero values
            """
        )

    with col2:
        st.markdown(
            """
            ### 🏘️ Woreda Intelligence

            - Woreda ranking
            - Performance classification
            - Underperforming Woredas
            - Completeness analysis
            """
        )

    with col3:
        st.markdown(
            """
            ### 🧠 Decision Support

            - Priority identification
            - Automatic alerts
            - Public-health interpretation
            - Management recommendations
            """
        )

    st.stop()

# ============================================================
# READ DATA
# ============================================================

try:

    if uploaded_file.name.lower().endswith(".csv"):

        df = pd.read_csv(uploaded_file)

    else:

        # Excel files from your current dataset
        # have the actual headers on row 2.
        df = pd.read_excel(
            uploaded_file,
            header=1
        )

except Exception as e:

    st.error(f"❌ Error reading the file: {e}")
    st.stop()

# ============================================================
# CLEAN DATA
# ============================================================

df = df.dropna(how="all")

df = df.dropna(
    axis=1,
    how="all"
)

df.columns = [
    str(col).strip()
    for col in df.columns
]

# ============================================================
# CHECK ACTIVITY COLUMN
# ============================================================

if "Activity" not in df.columns:

    st.error(
        "❌ The dataset must contain an 'Activity' column."
    )

    st.write("Detected columns:")

    st.write(
        list(df.columns)
    )

    st.stop()

# ============================================================
# IDENTIFY WOREDA COLUMNS
# ============================================================

woreda_columns = [
    col
    for col in df.columns
    if col != "Activity"
]

if len(woreda_columns) == 0:

    st.error(
        "❌ No Woreda columns were detected."
    )

    st.stop()

# ============================================================
# CONVERT WOREDA VALUES TO NUMERIC
# ============================================================

for col in woreda_columns:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# ============================================================
# REMOVE COMPLETELY EMPTY INDICATOR ROWS
# ============================================================

df = df[
    df[woreda_columns]
    .notna()
    .any(axis=1)
].copy()

# ============================================================
# INDICATORS
# ============================================================

indicators = (
    df["Activity"]
    .astype(str)
    .str.strip()
    .tolist()
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def search_options(options, search_text):

    if not search_text:

        return options

    search_text = search_text.lower()

    return [
        option
        for option in options
        if search_text in str(option).lower()
    ]


def classify_performance(completeness):

    if completeness >= 95:

        return "Excellent"

    elif completeness >= 80:

        return "Good"

    elif completeness >= 60:

        return "Moderate"

    else:

        return "Poor"


def calculate_priority(
    missing,
    zero,
    completeness
):

    score = (
        (missing * 3)
        + zero
        + max(
            0,
            100 - completeness
        )
    )

    if score >= 50:

        level = "High"

    elif score >= 20:

        level = "Medium"

    elif score > 0:

        level = "Low"

    else:

        level = "No Immediate Priority"

    return score, level


def woreda_recommendation(row):

    if row["Completeness %"] < 60:

        return (
            "Urgent follow-up required. "
            "Review reporting completeness, "
            "missing indicators and data submission."
        )

    elif row["Completeness %"] < 80:

        return (
            "Conduct targeted supportive supervision "
            "and improve reporting completeness."
        )

    elif row["Zero Values"] > 0:

        return (
            "Review zero-reported indicators and "
            "verify whether zeros represent true "
            "program performance."
        )

    else:

        return (
            "Maintain performance and share good practices "
            "with lower-performing Woredas."
        )


def indicator_recommendation(row):

    if row["Reporting %"] < 60:

        return (
            "High attention required. Investigate missing "
            "reports and strengthen reporting mechanisms."
        )

    elif row["Reporting %"] < 80:

        return (
            "Improve reporting completeness through "
            "facility-level follow-up and supportive supervision."
        )

    elif row["Zero Values"] > 0:

        return (
            "Validate zero values and determine whether "
            "they reflect actual service performance."
        )

    else:

        return (
            "Continue monitoring and maintain reporting quality."
        )


# ============================================================
# SIDEBAR — DATA SELECTION
# KEEP ON LEFT
# ============================================================

st.sidebar.markdown("---")

st.sidebar.header("🔎 Data Selection")

# ------------------------------------------------------------
# INDICATOR SEARCH
# ------------------------------------------------------------

indicator_search = st.sidebar.text_input(
    "Search indicators",
    placeholder="Type indicator name..."
)

filtered_indicators = search_options(
    indicators,
    indicator_search
)

if not filtered_indicators:

    st.sidebar.warning(
        "No indicators match your search."
    )

    filtered_indicators = indicators

# ------------------------------------------------------------
# INDICATOR SELECTION
# ------------------------------------------------------------

if "selected_indicators_v06" not in st.session_state:

    st.session_state.selected_indicators_v06 = (
        indicators.copy()
    )

selected_indicators = st.sidebar.multiselect(

    "Select indicators",

    options=filtered_indicators,

    default=[
        x
        for x in st.session_state.selected_indicators_v06
        if x in filtered_indicators
    ],

    key="indicator_selector_v06"
)

st.session_state.selected_indicators_v06 = (
    selected_indicators
)

# ------------------------------------------------------------
# WOREDA SEARCH
# ------------------------------------------------------------

woreda_search = st.sidebar.text_input(
    "Search Woredas",
    placeholder="Type Woreda name..."
)

filtered_woredas = search_options(
    woreda_columns,
    woreda_search
)

if not filtered_woredas:

    st.sidebar.warning(
        "No Woredas match your search."
    )

    filtered_woredas = woreda_columns

# ------------------------------------------------------------
# WOREDA SELECTION
# ------------------------------------------------------------

if "selected_woredas_v06" not in st.session_state:

    st.session_state.selected_woredas_v06 = (
        woreda_columns.copy()
    )

selected_woredas = st.sidebar.multiselect(

    "Select Woredas",

    options=filtered_woredas,

    default=[
        x
        for x in st.session_state.selected_woredas_v06
        if x in filtered_woredas
    ],

    key="woreda_selector_v06"
)

st.session_state.selected_woredas_v06 = (
    selected_woredas
)

# ============================================================
# VALIDATE SELECTION
# ============================================================

if not selected_indicators:

    st.warning(
        "⚠️ Please select at least one indicator."
    )

    st.stop()

if not selected_woredas:

    st.warning(
        "⚠️ Please select at least one Woreda."
    )

    st.stop()

# ============================================================
# SELECTED DATA
# ============================================================

selected_df = df[
    df["Activity"].isin(
        selected_indicators
    )
].copy()

# ============================================================
# ANALYSIS VALUES
# ============================================================

analysis_values = selected_df[
    selected_woredas
]

total_cells = analysis_values.size

reported_cells = (
    analysis_values
    .notna()
    .sum()
    .sum()
)

missing_cells = (
    analysis_values
    .isna()
    .sum()
    .sum()
)

zero_cells = (
    analysis_values == 0
).sum().sum()

overall_completeness = (

    reported_cells
    / total_cells
    * 100

    if total_cells > 0

    else 0
)

# ============================================================
# EXECUTIVE SNAPSHOT
# ============================================================

st.markdown("---")

st.subheader("📌 Executive Snapshot")

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:

    st.metric(
        "Indicators",
        len(selected_indicators)
    )

with c2:

    st.metric(
        "Woredas",
        len(selected_woredas)
    )

with c3:

    st.metric(
        "Completeness",
        f"{overall_completeness:.1f}%"
    )

with c4:

    st.metric(
        "Reported",
        f"{reported_cells:,}"
    )

with c5:

    st.metric(
        "Missing",
        f"{missing_cells:,}"
    )

with c6:

    st.metric(
        "Zero Values",
        f"{zero_cells:,}"
    )

# ============================================================
# INDICATOR PERFORMANCE
# ============================================================

indicator_rows = []

for indicator in selected_indicators:

    indicator_data = selected_df[
        selected_df["Activity"] == indicator
    ]

    if indicator_data.empty:

        continue

    row = indicator_data[
        selected_woredas
    ].iloc[0]

    total_woredas = len(
        selected_woredas
    )

    reported = row.notna().sum()

    missing = row.isna().sum()

    zero = (row == 0).sum()

    reporting_percent = (

        reported
        / total_woredas
        * 100

        if total_woredas > 0

        else 0
    )

    performance = classify_performance(
        reporting_percent
    )

    priority_score, priority_level = (
        calculate_priority(
            missing,
            zero,
            reporting_percent
        )
    )

    indicator_rows.append(
        {
            "Indicator": indicator,
            "Reported Woredas": reported,
            "Missing Woredas": missing,
            "Zero Values": zero,
            "Reporting %": reporting_percent,
            "Performance": performance,
            "Priority Score": priority_score,
            "Priority": priority_level
        }
    )

indicator_performance = pd.DataFrame(
    indicator_rows
)

indicator_ranking = (
    indicator_performance
    .sort_values(
        by="Reporting %",
        ascending=False
    )
    .reset_index(drop=True)
)

indicator_ranking.insert(
    0,
    "Rank",
    range(
        1,
        len(indicator_ranking) + 1
    )
)

# ============================================================
# WOREDA PERFORMANCE
# ============================================================

woreda_rows = []

for woreda in selected_woredas:

    values = selected_df[woreda]

    total_indicators = len(
        selected_indicators
    )

    reported = values.notna().sum()

    missing = values.isna().sum()

    zero = (values == 0).sum()

    completeness = (

        reported
        / total_indicators
        * 100

        if total_indicators > 0

        else 0
    )

    performance = classify_performance(
        completeness
    )

    priority_score, priority_level = (
        calculate_priority(
            missing,
            zero,
            completeness
        )
    )

    woreda_rows.append(
        {
            "Woreda": woreda,
            "Reported Indicators": reported,
            "Missing Indicators": missing,
            "Zero Values": zero,
            "Completeness %": completeness,
            "Performance": performance,
            "Priority Score": priority_score,
            "Priority": priority_level
        }
    )

woreda_performance = pd.DataFrame(
    woreda_rows
)

woreda_ranking = (
    woreda_performance
    .sort_values(
        by="Completeness %",
        ascending=False
    )
    .reset_index(drop=True)
)

woreda_ranking.insert(
    0,
    "Rank",
    range(
        1,
        len(woreda_ranking) + 1
    )
)

# ============================================================
# RECOMMENDATIONS
# ============================================================

woreda_ranking[
    "Recommendation"
] = woreda_ranking.apply(
    woreda_recommendation,
    axis=1
)

indicator_ranking[
    "Recommendation"
] = indicator_ranking.apply(
    indicator_recommendation,
    axis=1
)

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(

    [
        "📊 Overview",
        "📋 Indicator Performance & Ranking",
        "🏘️ Woreda Performance & Ranking",
        "🚨 Priority Identification",
        "🧠 Public-Health Intelligence",
        "💡 Decision-Support Recommendations",
        "📈 Visualization"
    ]
)

# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab1:

    st.header(
        "📊 Public Health Data Overview"
    )

    st.markdown(
        """
        This section provides a high-level assessment
        of completeness and reporting status.
        """
    )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "📌 Overall Data Quality"
        )

        quality_data = pd.DataFrame(
            {
                "Measure": [
                    "Total data cells",
                    "Reported cells",
                    "Missing cells",
                    "Zero values",
                    "Completeness"
                ],

                "Value": [
                    f"{total_cells:,}",
                    f"{reported_cells:,}",
                    f"{missing_cells:,}",
                    f"{zero_cells:,}",
                    f"{overall_completeness:.1f}%"
                ]
            }
        )

        st.dataframe(
            quality_data,
            use_container_width=True,
            hide_index=True
        )

    with col2:

        st.subheader(
            "📊 Data Completeness"
        )

        completeness_chart = pd.DataFrame(
            {
                "Category": [
                    "Reported",
                    "Missing"
                ],

                "Value": [
                    reported_cells,
                    missing_cells
                ]
            }
        )

        fig = px.pie(
            completeness_chart,
            names="Category",
            values="Value",
            title="Reported vs Missing Data"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.markdown("---")

    st.subheader(
        "🏘️ Woreda Reporting Status"
    )

    st.dataframe(
        woreda_ranking[
            [
                "Rank",
                "Woreda",
                "Reported Indicators",
                "Missing Indicators",
                "Zero Values",
                "Completeness %",
                "Performance"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# TAB 2 — INDICATOR PERFORMANCE
# ============================================================

with tab2:

    st.header(
        "📋 Indicator Performance & Ranking"
    )

    st.markdown(
        """
        Indicators are ranked according to reporting
        completeness across the selected Woredas.
        """
    )

    best_indicator = (
        indicator_ranking.iloc[0]
    )

    worst_indicator = (
        indicator_ranking.iloc[-1]
    )

    a, b = st.columns(2)

    with a:

        st.success(
            f"🏆 Best reporting indicator: "
            f"**{best_indicator['Indicator']}** "
            f"({best_indicator['Reporting %']:.1f}%)"
        )

    with b:

        st.warning(
            f"⚠️ Lowest reporting indicator: "
            f"**{worst_indicator['Indicator']}** "
            f"({worst_indicator['Reporting %']:.1f}%)"
        )

    st.markdown("---")

    st.subheader(
        "🏆 Indicator Ranking"
    )

    st.dataframe(
        indicator_ranking,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader(
        "🚨 Critical Indicators"
    )

    critical_indicators = indicator_ranking[
        indicator_ranking["Reporting %"] < 80
    ]

    if len(critical_indicators) > 0:

        st.warning(
            f"{len(critical_indicators)} indicator(s) "
            "have reporting completeness below 80%."
        )

        st.dataframe(
            critical_indicators[
                [
                    "Rank",
                    "Indicator",
                    "Missing Woredas",
                    "Zero Values",
                    "Reporting %",
                    "Performance",
                    "Priority"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✅ No indicator has reporting completeness below 80%."
        )

# ============================================================
# TAB 3 — WOREDA PERFORMANCE
# ============================================================

with tab3:

    st.header(
        "🏘️ Woreda Performance & Ranking"
    )

    st.markdown(
        """
        Woredas are ranked according to the completeness
        of indicator reporting.
        """
    )

    best_woreda = (
        woreda_ranking.iloc[0]
    )

    worst_woreda = (
        woreda_ranking.iloc[-1]
    )

    a, b = st.columns(2)

    with a:

        st.success(
            f"🏆 Best-performing Woreda: "
            f"**{best_woreda['Woreda']}** "
            f"({best_woreda['Completeness %']:.1f}%)"
        )

    with b:

        st.warning(
            f"⚠️ Lowest-performing Woreda: "
            f"**{worst_woreda['Woreda']}** "
            f"({worst_woreda['Completeness %']:.1f}%)"
        )

    st.markdown("---")

    st.subheader(
        "🏆 Woreda Ranking"
    )

    st.dataframe(
        woreda_ranking,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader(
        "⚠️ Underperforming Woredas"
    )

    underperforming = woreda_ranking[
        woreda_ranking["Completeness %"] < 80
    ]

    if len(underperforming) > 0:

        st.warning(
            f"{len(underperforming)} Woreda(s) "
            "have completeness below 80%."
        )

        st.dataframe(
            underperforming[
                [
                    "Rank",
                    "Woreda",
                    "Missing Indicators",
                    "Zero Values",
                    "Completeness %",
                    "Performance",
                    "Priority"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✅ No Woreda has completeness below 80%."
        )

# ============================================================
# TAB 4 — PRIORITY IDENTIFICATION
# ============================================================

with tab4:

    st.header(
        "🚨 Priority Identification"
    )

    st.markdown(
        """
        The platform automatically identifies areas requiring
        management attention using missing data, zero values,
        and reporting completeness.
        """
    )

    high_count = (

        (
            woreda_ranking["Priority"]
            == "High"
        ).sum()

        +

        (
            indicator_ranking["Priority"]
            == "High"
        ).sum()
    )

    medium_count = (

        (
            woreda_ranking["Priority"]
            == "Medium"
        ).sum()

        +

        (
            indicator_ranking["Priority"]
            == "Medium"
        ).sum()
    )

    low_count = (

        (
            woreda_ranking["Priority"]
            == "Low"
        ).sum()

        +

        (
            indicator_ranking["Priority"]
            == "Low"
        ).sum()
    )

    p1, p2, p3 = st.columns(3)

    with p1:

        st.metric(
            "🔴 High Priority",
            high_count
        )

    with p2:

        st.metric(
            "🟠 Medium Priority",
            medium_count
        )

    with p3:

        st.metric(
            "🟡 Low Priority",
            low_count
        )

    priority_chart = pd.DataFrame(
        {
            "Priority": [
                "High",
                "Medium",
                "Low"
            ],

            "Count": [
                high_count,
                medium_count,
                low_count
            ]
        }
    )

    fig = px.bar(
        priority_chart,
        x="Priority",
        y="Count",
        title="Priority Distribution"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader(
        "🏘️ Priority Woredas"
    )

    priority_woredas = woreda_ranking[
        woreda_ranking["Priority"]
        != "No Immediate Priority"
    ]

    if len(priority_woredas) > 0:

        st.dataframe(
            priority_woredas[
                [
                    "Rank",
                    "Woreda",
                    "Completeness %",
                    "Missing Indicators",
                    "Zero Values",
                    "Priority Score",
                    "Priority",
                    "Recommendation"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✅ No Woreda requires immediate priority attention."
        )

    st.subheader(
        "📋 Priority Indicators"
    )

    priority_indicators = indicator_ranking[
        indicator_ranking["Priority"]
        != "No Immediate Priority"
    ]

    if len(priority_indicators) > 0:

        st.dataframe(
            priority_indicators[
                [
                    "Rank",
                    "Indicator",
                    "Reporting %",
                    "Missing Woredas",
                    "Zero Values",
                    "Priority Score",
                    "Priority",
                    "Recommendation"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "✅ No indicator requires immediate priority attention."
        )

    st.markdown("---")

    st.subheader(
        "🚨 Automatic Alerts"
    )

    if overall_completeness < 60:

        st.error(
            f"🔴 CRITICAL: Overall reporting completeness "
            f"is only {overall_completeness:.1f}%."
        )

    elif overall_completeness < 80:

        st.warning(
            f"🟠 ATTENTION: Overall reporting completeness "
            f"is {overall_completeness:.1f}%."
        )

    else:

        st.success(
            f"🟢 Overall reporting completeness "
            f"is {overall_completeness:.1f}%."
        )

    if missing_cells > 0:

        st.warning(
            f"⚠️ There are {missing_cells:,} missing "
            "data cells requiring review."
        )

    if zero_cells > 0:

        st.info(
            f"ℹ️ There are {zero_cells:,} zero values. "
            "Validate whether these represent true zero "
            "service delivery or reporting/data-entry issues."
        )

# ============================================================
# TAB 5 — PUBLIC HEALTH INTELLIGENCE
# ============================================================

with tab5:

    st.header(
        "🧠 Public-Health Intelligence"
    )

    st.markdown(
        """
        This section converts the reporting dataset into
        management-oriented findings.
        """
    )

    st.subheader(
        "🔍 Automatically Generated Key Findings"
    )

    if overall_completeness >= 95:

        st.success(
            f"🟢 Reporting completeness is excellent "
            f"at {overall_completeness:.1f}%."
        )

    elif overall_completeness >= 80:

        st.info(
            f"🔵 Overall reporting completeness is good "
            f"at {overall_completeness:.1f}%, "
            "but some gaps remain."
        )

    elif overall_completeness >= 60:

        st.warning(
            f"🟠 Overall reporting completeness is moderate "
            f"at {overall_completeness:.1f}%. "
            "Targeted follow-up is recommended."
        )

    else:

        st.error(
            f"🔴 Overall reporting completeness is poor "
            f"at {overall_completeness:.1f}%. "
            "Immediate management attention is recommended."
        )

    if len(woreda_ranking) > 1:

        performance_gap = (

            woreda_ranking.iloc[0][
                "Completeness %"
            ]

            -

            woreda_ranking.iloc[-1][
                "Completeness %"
            ]
        )

        st.write(
            f"📊 The difference between the best and lowest "
            f"Woreda reporting completeness is "
            f"**{performance_gap:.1f} percentage points**."
        )

    if len(underperforming) > 0:

        st.write(
            f"🏘️ **{len(underperforming)} Woreda(s)** "
            "are below the 80% reporting threshold "
            "and should receive targeted follow-up."
        )

    if len(critical_indicators) > 0:

        st.write(
            f"📋 **{len(critical_indicators)} indicator(s)** "
            "have reporting completeness below 80%."
        )

    if zero_cells > 0:

        st.write(
            f"0️⃣ The dataset contains **{zero_cells:,} "
            "zero values**. These should be interpreted "
            "carefully because a zero may represent either "
            "true absence of service or a reporting/data-entry problem."
        )

    st.markdown("---")

    st.subheader(
        "🎯 Key Intelligence Summary"
    )

    intelligence_summary = pd.DataFrame(
        {
            "Intelligence Area": [
                "Overall Reporting",
                "Best Woreda",
                "Lowest Woreda",
                "Best Indicator",
                "Lowest Indicator",
                "Underperforming Woredas",
                "Critical Indicators",
                "Missing Data Cells",
                "Zero Values"
            ],

            "Finding": [

                f"{overall_completeness:.1f}%",

                f"{best_woreda['Woreda']} "
                f"({best_woreda['Completeness %']:.1f}%)",

                f"{worst_woreda['Woreda']} "
                f"({worst_woreda['Completeness %']:.1f}%)",

                f"{best_indicator['Indicator']} "
                f"({best_indicator['Reporting %']:.1f}%)",

                f"{worst_indicator['Indicator']} "
                f"({worst_indicator['Reporting %']:.1f}%)",

                len(underperforming),

                len(critical_indicators),

                f"{missing_cells:,}",

                f"{zero_cells:,}"
            ]
        }
    )

    st.dataframe(
        intelligence_summary,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader(
        "🎯 Management Focus Areas"
    )

    management_actions = []

    if overall_completeness < 80:

        management_actions.append(
            "Improve overall reporting completeness through "
            "targeted follow-up and supportive supervision."
        )

    if len(underperforming) > 0:

        management_actions.append(
            "Prioritize underperforming Woredas for data-quality "
            "review and performance improvement."
        )

    if len(critical_indicators) > 0:

        management_actions.append(
            "Investigate indicators with low reporting completeness "
            "and identify facilities responsible for reporting gaps."
        )

    if zero_cells > 0:

        management_actions.append(
            "Validate zero values to distinguish true zero "
            "service delivery from data-entry or reporting problems."
        )

    if not management_actions:

        management_actions.append(
            "Maintain current reporting performance and continue "
            "routine data-quality monitoring."
        )

    for action in management_actions:

        st.markdown(
            f"- 💡 {action}"
        )

# ============================================================
# TAB 6 — DECISION SUPPORT
# ============================================================

with tab6:

    st.header(
        "💡 Decision-Support Recommendations"
    )

    st.markdown(
        """
        The platform translates observed data patterns
        into practical management actions.
        """
    )

    st.subheader(
        "🏘️ Woreda-Level Recommendations"
    )

    recommendation_woredas = woreda_ranking[
        woreda_ranking["Completeness %"] < 80
    ]

    if len(recommendation_woredas) > 0:

        for _, row in recommendation_woredas.iterrows():

            st.markdown(
                f"""
                **{row['Woreda']} — {row['Performance']}**

                - Completeness: **{row['Completeness %']:.1f}%**
                - Missing indicators: **{row['Missing Indicators']}**
                - Zero values: **{row['Zero Values']}**
                - Priority: **{row['Priority']}**
                - Recommended action: {row['Recommendation']}
                """
            )

            st.markdown("---")

    else:

        st.success(
            "✅ No Woreda currently requires targeted "
            "performance intervention."
        )

    st.subheader(
        "📋 Indicator-Level Recommendations"
    )

    recommendation_indicators = indicator_ranking[
        indicator_ranking["Reporting %"] < 80
    ]

    if len(recommendation_indicators) > 0:

        for _, row in recommendation_indicators.iterrows():

            st.markdown(
                f"""
                **{row['Indicator']}**

                - Reporting: **{row['Reporting %']:.1f}%**
                - Missing Woredas: **{row['Missing Woredas']}**
                - Zero values: **{row['Zero Values']}**
                - Priority: **{row['Priority']}**
                - Recommended action: {row['Recommendation']}
                """
            )

            st.markdown("---")

    else:

        st.success(
            "✅ No indicator currently requires targeted "
            "reporting intervention."
        )

    st.subheader(
        "🎯 Executive Management Recommendations"
    )

    executive_recommendations = [

        "Use the Woreda ranking to focus supportive "
        "supervision on the lowest-performing Woredas.",

        "Use the indicator ranking to identify indicators "
        "requiring reporting-system improvement.",

        "Review missing data before making program-performance conclusions.",

        "Validate zero values before interpreting them "
        "as low service utilization.",

        "Share good reporting practices from high-performing Woredas.",

        "Repeat the analysis routinely to monitor improvement over time."
    ]

    for recommendation in executive_recommendations:

        st.markdown(
            f"- **{recommendation}**"
        )

# ============================================================
# TAB 7 — VISUALIZATION
# ============================================================

with tab7:

    st.header(
        "📈 Public Health Visualizations"
    )

    st.markdown(
        """
        ### 🎯 Visualization of Your Selected Indicators

        The charts below automatically use the **indicators and
        Woredas selected from the left sidebar**.
        """
    )

    # ========================================================
    # SELECTED INDICATOR VISUALIZATION
    # ========================================================

    st.subheader(
        "🎯 Selected Indicators by Woreda"
    )

    st.caption(
        f"Showing {len(selected_indicators)} selected indicator(s) "
        f"across {len(selected_woredas)} selected Woreda(s)."
    )

    # --------------------------------------------------------
    # VISUALIZATION SELECTION
    # --------------------------------------------------------

    selected_visualization = st.selectbox(

        "Choose visualization",

        [
            "📊 Grouped Bar — Indicator by Woreda",
            "📈 Line Chart — Indicator by Woreda",
            "📚 Stacked Bar — Indicator by Woreda",
            "🔥 Heatmap — Indicator vs Woreda",
            "📊 Total Reported Value by Indicator"
        ],

        key="selected_indicator_visualization_v06"
    )

    # ========================================================
    # PREPARE CHART DATA
    # ========================================================

    chart_df = selected_df.melt(

        id_vars=["Activity"],

        value_vars=selected_woredas,

        var_name="Woreda",

        value_name="Reported Value"
    )

    # ========================================================
    # GROUPED BAR
    # ========================================================

    if selected_visualization == (
        "📊 Grouped Bar — Indicator by Woreda"
    ):

        fig = px.bar(

            chart_df,

            x="Woreda",

            y="Reported Value",

            color="Activity",

            barmode="group",

            title="Selected Indicators by Woreda",

            labels={
                "Activity": "Indicator",
                "Woreda": "Woreda",
                "Reported Value": "Reported Value"
            },

            hover_data={
                "Activity": True,
                "Woreda": True,
                "Reported Value": True
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            legend_title="Indicator"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # LINE CHART
    # ========================================================

    elif selected_visualization == (
        "📈 Line Chart — Indicator by Woreda"
    ):

        fig = px.line(

            chart_df,

            x="Woreda",

            y="Reported Value",

            color="Activity",

            markers=True,

            title="Selected Indicator Values Across Woredas",

            labels={
                "Activity": "Indicator",
                "Woreda": "Woreda",
                "Reported Value": "Reported Value"
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            legend_title="Indicator"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # STACKED BAR
    # ========================================================

    elif selected_visualization == (
        "📚 Stacked Bar — Indicator by Woreda"
    ):

        fig = px.bar(

            chart_df,

            x="Woreda",

            y="Reported Value",

            color="Activity",

            barmode="stack",

            title="Stacked Selected Indicators by Woreda",

            labels={
                "Activity": "Indicator",
                "Woreda": "Woreda",
                "Reported Value": "Reported Value"
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45,
            legend_title="Indicator"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # HEATMAP
    # ========================================================

    elif selected_visualization == (
        "🔥 Heatmap — Indicator vs Woreda"
    ):

        heatmap_df = (
            selected_df
            .set_index("Activity")
            [selected_woredas]
        )

        fig = px.imshow(

            heatmap_df,

            aspect="auto",

            title="Selected Indicators vs Woredas",

            labels={
                "x": "Woreda",
                "y": "Indicator",
                "color": "Reported Value"
            },

            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # TOTAL BY INDICATOR
    # ========================================================

    elif selected_visualization == (
        "📊 Total Reported Value by Indicator"
    ):

        totals = (
            selected_df[
                ["Activity"] + selected_woredas
            ]
            .set_index("Activity")
            .sum(
                axis=1,
                skipna=True
            )
            .reset_index()
        )

        totals.columns = [
            "Indicator",
            "Total Reported Value"
        ]

        fig = px.bar(

            totals,

            x="Indicator",

            y="Total Reported Value",

            title="Total Reported Value by Selected Indicator",

            text="Total Reported Value",

            labels={
                "Indicator": "Indicator",
                "Total Reported Value": "Total Reported Value"
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # VISUALIZATION DATA TABLE
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📋 Data Used for Selected Visualization"
    )

    st.dataframe(
        selected_df[
            ["Activity"] + selected_woredas
        ],
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # SECONDARY VISUALIZATIONS
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📊 Additional Performance Visualizations"
    )

    secondary_visualization = st.selectbox(

        "Choose additional visualization",

        [
            "🏘️ Woreda Completeness Ranking",
            "📋 Indicator Completeness Ranking",
            "↔️ Reported vs Missing by Woreda",
            "🎯 Woreda Completeness vs Missing Indicators"
        ],

        key="secondary_visualization_v06"
    )

    # --------------------------------------------------------
    # WOREDA COMPLETENESS
    # --------------------------------------------------------

    if secondary_visualization == (
        "🏘️ Woreda Completeness Ranking"
    ):

        chart_data = woreda_ranking.copy()

        fig = px.bar(

            chart_data,

            x="Woreda",

            y="Completeness %",

            text="Completeness %",

            title="Woreda Reporting Completeness Ranking",

            labels={
                "Completeness %":
                "Completeness (%)"
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # INDICATOR COMPLETENESS
    # --------------------------------------------------------

    elif secondary_visualization == (
        "📋 Indicator Completeness Ranking"
    ):

        chart_data = indicator_ranking.copy()

        fig = px.bar(

            chart_data,

            x="Indicator",

            y="Reporting %",

            text="Reporting %",

            title="Indicator Reporting Completeness Ranking",

            labels={
                "Reporting %":
                "Reporting (%)"
            }
        )

        fig.update_layout(
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # REPORTED VS MISSING
    # --------------------------------------------------------

    elif secondary_visualization == (
        "↔️ Reported vs Missing by Woreda"
    ):

        status_df = woreda_ranking[
            [
                "Woreda",
                "Reported Indicators",
                "Missing Indicators"
            ]
        ].copy()

        status_melted = status_df.melt(

            id_vars="Woreda",

            var_name="Status",

            value_name="Count"
        )

        fig = px.bar(

            status_melted,

            x="Woreda",

            y="Count",

            color="Status",

            barmode="group",

            title="Reported vs Missing Indicators by Woreda"
        )

        fig.update_layout(
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # SCATTER
    # --------------------------------------------------------

    elif secondary_visualization == (
        "🎯 Woreda Completeness vs Missing Indicators"
    ):

        fig = px.scatter(

            woreda_ranking,

            x="Missing Indicators",

            y="Completeness %",

            size="Zero Values",

            hover_name="Woreda",

            title="Woreda Completeness vs Missing Indicators",

            labels={
                "Missing Indicators":
                "Missing Indicators",

                "Completeness %":
                "Completeness (%)",

                "Zero Values":
                "Zero Values"
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "🏥 Public Health Intelligence Platform | "
    "DHIS-2 + Data Analytics + AI Engineering | "
    "Version 0.6"
)