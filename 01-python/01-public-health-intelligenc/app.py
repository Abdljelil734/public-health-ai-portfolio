import streamlit as st
import pandas as pd
import plotly.express as px


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Public Health Intelligence Platform",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Public Health Intelligence Platform")

st.markdown(
    """
    **DHIS-2 + Data Analytics + AI-Assisted Public Health Intelligence**
    """
)

st.divider()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_performance(completeness):
    """Classify Woreda performance based on reporting completeness."""

    if completeness >= 95:
        return "Excellent"

    elif completeness >= 80:
        return "Good"

    elif completeness >= 60:
        return "Moderate"

    else:
        return "Poor"


def calculate_priority(row):
    """
    Calculate Woreda priority score.

    Missing indicators are weighted heavily because missing
    reporting requires follow-up.

    Score components:
    - Missing indicators × 3
    - Zero values × 1
    - Completeness gap from 100%
    """

    missing = row["Missing Indicators"]

    zero = row["Zero Values"]

    completeness = row["Completeness %"]

    score = (
        missing * 3
        + zero
        + max(0, 100 - completeness)
    )

    return round(score, 1)


def classify_priority(score):
    """Classify priority level."""

    if score >= 50:
        return "🔴 High"

    elif score >= 20:
        return "🟠 Medium"

    elif score > 0:
        return "🟡 Low"

    else:
        return "🟢 No Immediate Priority"


# ============================================================
# SESSION STATE
# ============================================================

# These preserve selections while the user searches.

if "selected_indicators" not in st.session_state:

    st.session_state.selected_indicators = []


if "selected_woredas" not in st.session_state:

    st.session_state.selected_woredas = []


# ============================================================
# DATA UPLOAD
# ============================================================

st.header("📂 Upload Public Health Dataset")

uploaded_file = st.file_uploader(
    "Upload Excel or CSV file",
    type=["xlsx", "xls", "csv"]
)


if uploaded_file is None:

    st.info(
        "Please upload an Excel or CSV dataset to begin."
    )

    st.stop()


# ============================================================
# READ DATA
# ============================================================

try:

    if uploaded_file.name.lower().endswith(".csv"):

        df = pd.read_csv(
            uploaded_file
        )

    else:

        # DHIS-2 style Excel files commonly have
        # the actual column names on row 2.

        df = pd.read_excel(
            uploaded_file,
            header=1
        )


except Exception as e:

    st.error(
        f"Unable to read the uploaded file: {e}"
    )

    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================

df = df.dropna(
    axis=0,
    how="all"
)

df = df.dropna(
    axis=1,
    how="all"
)

df.columns = [
    str(column).strip()
    for column in df.columns
]


# ============================================================
# CHECK ACTIVITY COLUMN
# ============================================================

if "Activity" not in df.columns:

    st.error(
        "The dataset must contain a column named 'Activity'."
    )

    st.write(
        "Available columns:"
    )

    st.write(
        list(df.columns)
    )

    st.stop()


# ============================================================
# DATA PREVIEW
# ============================================================

st.header("📊 Data Preview")

st.dataframe(
    df,
    use_container_width=True,
    height=300
)


# ============================================================
# DATA INFORMATION
# ============================================================

st.header("📋 Data Information")

info_col1, info_col2, info_col3, info_col4 = st.columns(4)


with info_col1:

    st.metric(
        "Rows",
        df.shape[0]
    )


with info_col2:

    st.metric(
        "Columns",
        df.shape[1]
    )


with info_col3:

    st.metric(
        "Indicators",
        df.shape[0]
    )


with info_col4:

    st.metric(
        "Woredas / Locations",
        max(0, df.shape[1] - 1)
    )


# ============================================================
# IDENTIFY INDICATORS
# ============================================================

all_indicators = (
    df["Activity"]
    .dropna()
    .astype(str)
    .str.strip()
    .tolist()
)


# Remove duplicate indicator names while
# preserving original order.

all_indicators = list(
    dict.fromkeys(
        all_indicators
    )
)


# ============================================================
# IDENTIFY WOREDAS
# ============================================================

all_woredas = [
    column
    for column in df.columns
    if column != "Activity"
]


# ============================================================
# DATA SELECTION
# ============================================================

st.header("🎯 Data Selection")


# ============================================================
# INDICATOR SEARCH
# ============================================================

st.subheader("🔎 Select Indicators")

indicator_search = st.text_input(
    "Search indicators by typing part of the name",
    placeholder="Example: HIV, ANC, PMTCT, testing...",
    key="indicator_search"
)


# Filter indicators based on search.

if indicator_search.strip():

    filtered_indicators = [

        indicator

        for indicator in all_indicators

        if indicator_search.lower()
        in indicator.lower()

    ]

else:

    filtered_indicators = all_indicators.copy()


# ============================================================
# PRESERVE PREVIOUS INDICATOR SELECTIONS
# ============================================================

valid_previous_indicators = [

    indicator

    for indicator
    in st.session_state.selected_indicators

    if indicator in all_indicators

]


# Current search results + previously selected indicators.

indicator_options = list(
    dict.fromkeys(
        filtered_indicators
        + valid_previous_indicators
    )
)


selected_indicators = st.multiselect(

    "Choose one or more indicators",

    options=indicator_options,

    default=valid_previous_indicators,

    key="indicator_multiselect"

)


# Save selection.

st.session_state.selected_indicators = (
    selected_indicators
)


# Display selected indicators.

if selected_indicators:

    st.success(
        f"{len(selected_indicators)} indicator(s) selected."
    )

    st.write(
        "Selected indicators:"
    )

    st.write(
        selected_indicators
    )

else:

    st.info(
        "No indicators selected yet."
    )


# ============================================================
# WOREDA SEARCH
# ============================================================

st.subheader("📍 Select Woredas / Locations")

woreda_search = st.text_input(
    "Search Woredas by typing part of the name",
    placeholder="Example: Halaba, Kulito, Atoti...",
    key="woreda_search"
)


# Filter Woredas.

if woreda_search.strip():

    filtered_woredas = [

        woreda

        for woreda in all_woredas

        if woreda_search.lower()
        in woreda.lower()

    ]

else:

    filtered_woredas = all_woredas.copy()


# ============================================================
# PRESERVE PREVIOUS WOREDA SELECTIONS
# ============================================================

valid_previous_woredas = [

    woreda

    for woreda
    in st.session_state.selected_woredas

    if woreda in all_woredas

]


# Search results + previous selections.

woreda_options = list(
    dict.fromkeys(
        filtered_woredas
        + valid_previous_woredas
    )
)


selected_woredas = st.multiselect(

    "Choose one or more Woredas / Locations",

    options=woreda_options,

    default=valid_previous_woredas,

    key="woreda_multiselect"

)


# Save selection.

st.session_state.selected_woredas = (
    selected_woredas
)


if selected_woredas:

    st.success(
        f"{len(selected_woredas)} Woreda/location(s) selected."
    )

else:

    st.info(
        "No Woredas selected."
    )


# ============================================================
# VALIDATE SELECTION
# ============================================================

if not selected_indicators:

    st.warning(
        "Please select at least one indicator."
    )

    st.stop()


if not selected_woredas:

    st.warning(
        "Please select at least one Woreda/location."
    )

    st.stop()


# ============================================================
# PREPARE ANALYSIS DATA
# ============================================================

analysis_df = df[
    df["Activity"]
    .astype(str)
    .isin(selected_indicators)
].copy()


# Convert Woreda values to numbers.

for woreda in selected_woredas:

    analysis_df[woreda] = pd.to_numeric(
        analysis_df[woreda],
        errors="coerce"
    )


# ============================================================
# INDICATOR COMPARISON
# ============================================================

st.header("📊 Indicator Comparison")

indicator_results = []


total_locations = len(
    selected_woredas
)


for indicator in selected_indicators:

    row = analysis_df[
        analysis_df["Activity"]
        .astype(str)
        == indicator
    ]

    if row.empty:

        continue


    values = row[
        selected_woredas
    ].iloc[0]


    numeric_values = pd.to_numeric(
        values,
        errors="coerce"
    )


    reported = (
        numeric_values
        .notna()
        .sum()
    )


    missing = (
        numeric_values
        .isna()
        .sum()
    )


    zero_values = (
        numeric_values
        .fillna(0)
        == 0
    ).sum()


    total_reported = (
        numeric_values
        .fillna(0)
        .sum()
    )


    reporting_percentage = (

        reported
        / total_locations
        * 100

        if total_locations > 0

        else 0

    )


    indicator_results.append(

        {
            "Indicator": indicator,

            "Total Reported": total_reported,

            "Locations Reporting": reported,

            "Missing Locations": missing,

            "Zero Values": zero_values,

            "Reporting %": round(
                reporting_percentage,
                1
            )
        }

    )


indicator_comparison = pd.DataFrame(
    indicator_results
)


if not indicator_comparison.empty:

    st.dataframe(
        indicator_comparison,
        use_container_width=True
    )


# ============================================================
# DATA QUALITY
# ============================================================

st.header(
    "🧠 Data Quality & Public Health Intelligence"
)


total_possible_values = (

    len(selected_indicators)
    * len(selected_woredas)

)


reported_values = 0

missing_values = 0

zero_values = 0

total_reported = 0


# ============================================================
# CALCULATE OVERALL DATA QUALITY
# ============================================================

for indicator in selected_indicators:

    row = analysis_df[
        analysis_df["Activity"]
        .astype(str)
        == indicator
    ]


    if row.empty:

        continue


    values = pd.to_numeric(

        row[selected_woredas]
        .iloc[0],

        errors="coerce"

    )


    reported_values += (
        values.notna().sum()
    )


    missing_values += (
        values.isna().sum()
    )


    zero_values += (

        values.fillna(0)
        == 0

    ).sum()


    total_reported += (
        values.fillna(0).sum()
    )


if total_possible_values > 0:

    overall_completeness = (

        reported_values
        / total_possible_values
        * 100

    )

else:

    overall_completeness = 0


# ============================================================
# QUALITY METRICS
# ============================================================

metric1, metric2, metric3, metric4, metric5 = st.columns(5)


with metric1:

    st.metric(
        "Completeness",
        f"{overall_completeness:.1f}%"
    )


with metric2:

    st.metric(
        "Reported Values",
        reported_values
    )


with metric3:

    st.metric(
        "Missing Values",
        missing_values
    )


with metric4:

    st.metric(
        "Zero Values",
        zero_values
    )


with metric5:

    st.metric(
        "Total Reported",
        f"{total_reported:,.0f}"
    )


# ============================================================
# MISSING DATA ANALYSIS
# ============================================================

st.subheader(
    "⚠️ Missing Data Analysis"
)


missing_records = []


for indicator in selected_indicators:

    row = analysis_df[
        analysis_df["Activity"]
        .astype(str)
        == indicator
    ]


    if row.empty:

        continue


    for woreda in selected_woredas:

        value = pd.to_numeric(

            row[woreda].iloc[0],

            errors="coerce"

        )


        if pd.isna(value):

            missing_records.append(

                {
                    "Indicator": indicator,

                    "Woreda": woreda,

                    "Issue": "Missing Data"
                }

            )


missing_df = pd.DataFrame(
    missing_records
)


if not missing_df.empty:

    st.dataframe(
        missing_df,
        use_container_width=True
    )

else:

    st.success(
        "No missing values detected."
    )


# ============================================================
# ZERO VALUE ANALYSIS
# ============================================================

st.subheader(
    "0️⃣ Zero-Value Analysis"
)


zero_records = []


for indicator in selected_indicators:

    row = analysis_df[
        analysis_df["Activity"]
        .astype(str)
        == indicator
    ]


    if row.empty:

        continue


    for woreda in selected_woredas:

        value = pd.to_numeric(

            row[woreda].iloc[0],

            errors="coerce"

        )


        if pd.notna(value) and value == 0:

            zero_records.append(

                {
                    "Indicator": indicator,

                    "Woreda": woreda,

                    "Issue": "Zero Value"
                }

            )


zero_df = pd.DataFrame(
    zero_records
)


if not zero_df.empty:

    st.dataframe(
        zero_df,
        use_container_width=True
    )

else:

    st.success(
        "No zero values detected."
    )


# ============================================================
# WOREDA PERFORMANCE INTELLIGENCE
# ============================================================

st.header(
    "🏆 Woreda Performance Intelligence"
)


woreda_results = []


for woreda in selected_woredas:

    values = []


    for indicator in selected_indicators:

        row = analysis_df[
            analysis_df["Activity"]
            .astype(str)
            == indicator
        ]


        if row.empty:

            continue


        value = pd.to_numeric(

            row[woreda].iloc[0],

            errors="coerce"

        )


        values.append(value)


    series = pd.Series(
        values,
        dtype="float64"
    )


    reported = (
        series
        .notna()
        .sum()
    )


    missing = (
        series
        .isna()
        .sum()
    )


    zero = (

        series
        .fillna(0)
        == 0

    ).sum()


    completeness = (

        reported
        / len(selected_indicators)
        * 100

        if len(selected_indicators) > 0

        else 0

    )


    total = (
        series
        .fillna(0)
        .sum()
    )


    performance = classify_performance(
        completeness
    )


    woreda_results.append(

        {

            "Woreda": woreda,

            "Total Reported": total,

            "Reported Indicators": reported,

            "Missing Indicators": missing,

            "Zero Values": zero,

            "Completeness %": round(
                completeness,
                1
            ),

            "Performance": performance

        }

    )


performance_df = pd.DataFrame(
    woreda_results
)


# ============================================================
# PRIORITY CALCULATION
# ============================================================

if not performance_df.empty:

    performance_df[
        "Priority Score"
    ] = performance_df.apply(

        calculate_priority,

        axis=1

    )


    performance_df[
        "Priority Level"
    ] = performance_df[
        "Priority Score"
    ].apply(

        classify_priority

    )


# ============================================================
# PERFORMANCE TABLE
# ============================================================

if not performance_df.empty:

    display_performance = (

        performance_df
        .sort_values(
            by="Completeness %",
            ascending=False
        )

    )


    st.dataframe(
        display_performance,
        use_container_width=True
    )


# ============================================================
# PERFORMANCE CLASSIFICATION
# ============================================================

st.subheader(
    "📈 Performance Classification"
)


if not performance_df.empty:

    performance_counts = (

        performance_df[
            "Performance"
        ]
        .value_counts()
        .reset_index()

    )


    performance_counts.columns = [

        "Performance",

        "Number of Woredas"

    ]


    st.dataframe(
        performance_counts,
        use_container_width=True
    )


# ============================================================
# HIGH PRIORITY LOCATIONS
# ============================================================

st.subheader(
    "🚨 High-Priority Locations"
)


if not performance_df.empty:

    priority_locations = performance_df[

        performance_df[
            "Priority Level"
        ]
        == "🔴 High"

    ].sort_values(

        by="Priority Score",

        ascending=False

    )


    if not priority_locations.empty:

        st.dataframe(

            priority_locations,

            use_container_width=True

        )

    else:

        st.success(
            "No high-priority locations detected."
        )


# ============================================================
# AUTOMATIC INTELLIGENCE ALERTS
# ============================================================

st.subheader(
    "🚨 Automatic Intelligence Alerts"
)


alerts = []


# ------------------------------------------------------------
# Low completeness alerts
# ------------------------------------------------------------

for _, row in performance_df.iterrows():

    if row["Completeness %"] < 80:

        alerts.append(

            f"⚠️ **{row['Woreda']}** has low "
            f"reporting completeness "
            f"({row['Completeness %']:.1f}%)."

        )


# ------------------------------------------------------------
# Missing data alert
# ------------------------------------------------------------

if missing_values > 0:

    alerts.append(

        f"⚠️ **{missing_values} missing values** "
        "were detected. Follow up with the "
        "responsible reporting locations."

    )


# ------------------------------------------------------------
# Zero value alert
# ------------------------------------------------------------

if zero_values > 0:

    alerts.append(

        f"⚠️ **{zero_values} zero-value records** "
        "were detected. Review whether these "
        "represent true zero activity or "
        "missing reporting."

    )


if alerts:

    for alert in alerts:

        st.warning(
            alert
        )

else:

    st.success(
        "✅ No major automatic alerts detected."
    )


# ============================================================
# INDICATOR PERFORMANCE INTELLIGENCE
# ============================================================

st.header(
    "📌 Indicator Performance Intelligence"
)


indicator_intelligence = []


for _, row in indicator_comparison.iterrows():

    missing = row[
        "Missing Locations"
    ]


    reporting = row[
        "Reporting %"
    ]


    priority_score = (

        missing * 3

        + max(
            0,
            100 - reporting
        )

    )


    indicator_intelligence.append(

        {

            "Indicator": row["Indicator"],

            "Reporting %": reporting,

            "Missing Locations": missing,

            "Zero Values": row["Zero Values"],

            "Priority Score": round(
                priority_score,
                1
            ),

            "Priority": classify_priority(
                priority_score
            )

        }

    )


indicator_intelligence_df = pd.DataFrame(
    indicator_intelligence
)


if not indicator_intelligence_df.empty:

    indicator_intelligence_df = (

        indicator_intelligence_df
        .sort_values(
            by="Priority Score",
            ascending=False
        )

    )


    st.dataframe(

        indicator_intelligence_df,

        use_container_width=True

    )


# ============================================================
# AUTOMATIC PUBLIC HEALTH INTELLIGENCE SUMMARY
# ============================================================

st.header(
    "🤖 Automatic Public Health Intelligence Summary"
)


if not performance_df.empty:

    highest_performing = performance_df.loc[

        performance_df[
            "Completeness %"
        ].idxmax()

    ]


    lowest_performing = performance_df.loc[

        performance_df[
            "Completeness %"
        ].idxmin()

    ]


    st.markdown(

        f"""
### 📊 Current Situation

- **Overall reporting completeness:** {overall_completeness:.1f}%
- **Total indicators analyzed:** {len(selected_indicators)}
- **Total locations analyzed:** {len(selected_woredas)}
- **Missing values:** {missing_values}
- **Zero values:** {zero_values}

### 🏆 Best Reporting Location

**{highest_performing['Woreda']}**

Reporting completeness:

**{highest_performing['Completeness %']:.1f}%**

### ⚠️ Location Requiring Most Attention

**{lowest_performing['Woreda']}**

Reporting completeness:

**{lowest_performing['Completeness %']:.1f}%**

### 🎯 Recommended Action

Prioritize follow-up with locations showing:

1. Low reporting completeness
2. High numbers of missing indicators
3. High numbers of zero values
4. High overall priority scores

These findings can support:

- **Supportive supervision**
- **Data-quality improvement**
- **Reporting follow-up**
- **Program monitoring**
- **Resource prioritization**
- **Management decision-making**
"""
    )


# ============================================================
# VISUALIZATION
# ============================================================

st.header(
    "📊 Visualization"
)


# ============================================================
# INDICATOR BAR CHART
# ============================================================

if not indicator_comparison.empty:

    st.subheader(
        "Indicator Total Reported"
    )


    fig_indicator = px.bar(

        indicator_comparison,

        x="Indicator",

        y="Total Reported",

        title="Total Reported by Indicator"

    )


    fig_indicator.update_layout(

        xaxis_tickangle=-45

    )


    st.plotly_chart(

        fig_indicator,

        use_container_width=True

    )


# ============================================================
# WOREDA COMPARISON
# ============================================================

st.subheader(
    "Woreda Comparison"
)


if not performance_df.empty:

    chart_type = st.selectbox(

        "Choose visualization",

        [

            "Grouped Bar",

            "Horizontal Bar",

            "Pie",

            "Stacked Bar",

            "Scatter"

        ]

    )


    # --------------------------------------------------------
    # GROUPED BAR
    # --------------------------------------------------------

    if chart_type == "Grouped Bar":

        fig = px.bar(

            performance_df,

            x="Woreda",

            y="Total Reported",

            color="Performance",

            barmode="group",

            title="Woreda Performance Comparison"

        )


        fig.update_layout(

            xaxis_tickangle=-45

        )


    # --------------------------------------------------------
    # HORIZONTAL BAR
    # --------------------------------------------------------

    elif chart_type == "Horizontal Bar":

        fig = px.bar(

            performance_df,

            x="Total Reported",

            y="Woreda",

            color="Performance",

            orientation="h",

            title="Woreda Performance Comparison"

        )


    # --------------------------------------------------------
    # PIE
    # --------------------------------------------------------

    elif chart_type == "Pie":

        fig = px.pie(

            performance_df,

            names="Woreda",

            values="Total Reported",

            title="Share of Total Reported Values"

        )


    # --------------------------------------------------------
    # STACKED BAR
    # --------------------------------------------------------

    elif chart_type == "Stacked Bar":

        chart_data = performance_df[

            [

                "Woreda",

                "Reported Indicators",

                "Missing Indicators",

                "Zero Values"

            ]

        ].copy()


        chart_data = chart_data.melt(

            id_vars="Woreda",

            var_name="Category",

            value_name="Count"

        )


        fig = px.bar(

            chart_data,

            x="Woreda",

            y="Count",

            color="Category",

            barmode="stack",

            title="Woreda Data Quality Profile"

        )


        fig.update_layout(

            xaxis_tickangle=-45

        )


    # --------------------------------------------------------
    # SCATTER
    # --------------------------------------------------------

    else:

        fig = px.scatter(

            performance_df,

            x="Completeness %",

            y="Total Reported",

            size="Priority Score",

            hover_name="Woreda",

            title="Completeness vs Total Reported"

        )


    st.plotly_chart(

        fig,

        use_container_width=True

    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(

    "Public Health Intelligence Platform | "
    "DHIS-2 + Data Analytics + AI-Assisted Intelligence | "
    "Version 0.5"

)