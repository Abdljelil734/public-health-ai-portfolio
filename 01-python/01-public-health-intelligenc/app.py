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


# ============================================================
# TITLE
# ============================================================

st.title("🏥 Public Health Intelligence Platform")

st.markdown(
    """
    **DHIS-2 + Data Analytics + AI for Public Health Intelligence**

    Upload a public health Excel or CSV dataset to explore indicators,
    reporting completeness, data quality, Woreda performance, and
    visualizations.
    """
)


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "📂 Upload your Excel or CSV file",
    type=["xlsx", "xls", "csv"]
)


if uploaded_file is None:

    st.info(
        "Please upload an Excel or CSV file to begin the analysis."
    )

    st.stop()


# ============================================================
# READ DATA
# ============================================================

try:

    if uploaded_file.name.lower().endswith(".csv"):

        df = pd.read_csv(uploaded_file)

    else:

        # The current DHIS-2-style Excel files have the real
        # column headers on the second row.
        df = pd.read_excel(
            uploaded_file,
            header=1
        )

except Exception as e:

    st.error(
        f"❌ Could not read the uploaded file: {e}"
    )

    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================

# Remove completely empty rows
df = df.dropna(
    how="all"
)

# Remove completely empty columns
df = df.dropna(
    axis=1,
    how="all"
)

# Clean column names
df.columns = [
    str(column).strip()
    for column in df.columns
]


# ============================================================
# CHECK FOR ACTIVITY COLUMN
# ============================================================

if "Activity" not in df.columns:

    st.error(
        "❌ The uploaded dataset does not contain an 'Activity' column."
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

st.markdown("---")

st.header("📋 Data Preview")

st.dataframe(
    df,
    width="stretch"
)


# ============================================================
# DATA INFORMATION
# ============================================================

st.header("ℹ️ Data Information")

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Rows",
        df.shape[0]
    )

with col2:

    st.metric(
        "Columns",
        df.shape[1]
    )

with col3:

    st.metric(
        "Indicators",
        df["Activity"].nunique()
    )

with col4:

    st.metric(
        "Woredas / Locations",
        len(
            [
                column
                for column in df.columns
                if column not in ["Activity", "Total"]
            ]
        )
    )


# ============================================================
# DATA SELECTION
# ============================================================

st.markdown("---")

st.header("🔎 Data Selection")


# ------------------------------------------------------------
# INDICATOR SEARCH
# ------------------------------------------------------------

indicator_list = (
    df["Activity"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

indicator_list = sorted(
    indicator_list
)


indicator_search = st.text_input(
    "🔎 Search indicators:",
    placeholder="Type part of an indicator name..."
)


# Filter indicators according to search
if indicator_search.strip():

    filtered_indicators = [
        indicator
        for indicator in indicator_list
        if indicator_search.lower() in indicator.lower()
    ]

else:

    filtered_indicators = indicator_list


st.caption(
    f"Showing {len(filtered_indicators)} of "
    f"{len(indicator_list)} indicators"
)


selected_indicators = st.multiselect(
    "Select indicators:",
    filtered_indicators
)


# ------------------------------------------------------------
# WORеда / LOCATION SEARCH
# ------------------------------------------------------------

value_columns = [
    column
    for column in df.columns
    if column not in ["Activity", "Total"]
]


woreda_search = st.text_input(
    "🔎 Search Woredas / Locations:",
    placeholder="Type part of a Woreda or location name..."
)


if woreda_search.strip():

    filtered_woredas = [
        woreda
        for woreda in value_columns
        if woreda_search.lower() in woreda.lower()
    ]

else:

    filtered_woredas = value_columns


st.caption(
    f"Showing {len(filtered_woredas)} of "
    f"{len(value_columns)} Woredas / Locations"
)


selected_woredas = st.multiselect(
    "Select Woreda(s) / Location(s):",
    filtered_woredas,
    default=filtered_woredas
)


# ============================================================
# STOP IF NOTHING SELECTED
# ============================================================

if len(selected_indicators) == 0:

    st.info(
        "👆 Please search for and select at least one indicator."
    )

    st.stop()


if len(selected_woredas) == 0:

    st.warning(
        "👆 Please search for and select at least one Woreda / Location."
    )

    st.stop()


# ============================================================
# FILTER DATA
# ============================================================

filtered_df = df[
    df["Activity"].astype(str).isin(
        selected_indicators
    )
].copy()


# Keep only selected Woredas
analysis_columns = [
    "Activity"
] + selected_woredas


analysis_df = filtered_df[
    [
        column
        for column in analysis_columns
        if column in filtered_df.columns
    ]
].copy()


# ============================================================
# CONVERT NUMERIC DATA
# ============================================================

for column in selected_woredas:

    if column in analysis_df.columns:

        analysis_df[column] = pd.to_numeric(
            analysis_df[column],
            errors="coerce"
        )


# ============================================================
# INDICATOR COMPARISON
# ============================================================

st.markdown("---")

st.header("📊 Indicator Comparison")


# ------------------------------------------------------------
# CALCULATE TOTALS
# ------------------------------------------------------------

indicator_summary = []


for _, row in analysis_df.iterrows():

    indicator = row["Activity"]

    values = row[
        [
            column
            for column in selected_woredas
            if column in row.index
        ]
    ]

    numeric_values = pd.to_numeric(
        values,
        errors="coerce"
    )

    reported_values = numeric_values.notna()

    total_reported = numeric_values.sum(
        skipna=True
    )

    reporting_count = reported_values.sum()

    total_locations = len(
        selected_woredas
    )

    missing_count = (
        total_locations
        - reporting_count
    )

    if total_locations > 0:

        reporting_percentage = (
            reporting_count
            / total_locations
            * 100
        )

    else:

        reporting_percentage = 0


    indicator_summary.append(
        {
            "Indicator": indicator,
            "Total Reported": total_reported,
            "Locations Reporting": reporting_count,
            "Missing Locations": missing_count,
            "Reporting %": round(
                reporting_percentage,
                1
            )
        }
    )


indicator_summary_df = pd.DataFrame(
    indicator_summary
)


st.dataframe(
    indicator_summary_df,
    width="stretch"
)


# ============================================================
# DATA QUALITY & INTELLIGENCE
# ============================================================

st.markdown("---")

st.header("🧠 Data Quality & Intelligence")


# ============================================================
# OVERALL DATA QUALITY CALCULATIONS
# ============================================================

quality_records = []


for woreda in selected_woredas:

    if woreda not in analysis_df.columns:

        continue


    values = pd.to_numeric(
        analysis_df[woreda],
        errors="coerce"
    )


    total_indicators = len(
        values
    )


    reported_count = values.notna().sum()

    missing_count = values.isna().sum()

    zero_count = (
        values.eq(0)
        .sum()
    )


    if total_indicators > 0:

        completeness = (
            reported_count
            / total_indicators
            * 100
        )

    else:

        completeness = 0


    total_reported = values.sum(
        skipna=True
    )


    quality_records.append(
        {
            "Woreda / Location": woreda,
            "Indicators": total_indicators,
            "Reported Values": reported_count,
            "Missing Values": missing_count,
            "Zero Values": zero_count,
            "Reporting Completeness %": round(
                completeness,
                1
            ),
            "Total Reported": total_reported
        }
    )


quality_df = pd.DataFrame(
    quality_records
)


# ============================================================
# QUALITY METRICS
# ============================================================

total_expected = (
    len(selected_woredas)
    * len(selected_indicators)
)


total_reported_values = sum(
    record["Reported Values"]
    for record in quality_records
)


total_missing_values = sum(
    record["Missing Values"]
    for record in quality_records
)


total_zero_values = sum(
    record["Zero Values"]
    for record in quality_records
)


if total_expected > 0:

    overall_completeness = (
        total_reported_values
        / total_expected
        * 100
    )

else:

    overall_completeness = 0


# ============================================================
# QUALITY METRIC DISPLAY
# ============================================================

q1, q2, q3, q4 = st.columns(4)


with q1:

    st.metric(
        "Reporting Completeness",
        f"{overall_completeness:.1f}%"
    )


with q2:

    st.metric(
        "Reported Values",
        total_reported_values
    )


with q3:

    st.metric(
        "Missing Values",
        total_missing_values
    )


with q4:

    st.metric(
        "Zero Values",
        total_zero_values
    )


# ============================================================
# COMPLETENESS INTERPRETATION
# ============================================================

if overall_completeness >= 95:

    st.success(
        "🟢 Excellent reporting completeness."
    )

elif overall_completeness >= 80:

    st.info(
        "🟡 Good reporting completeness, "
        "but some missing data should be reviewed."
    )

elif overall_completeness >= 60:

    st.warning(
        "🟠 Moderate reporting completeness. "
        "Data quality improvement is recommended."
    )

else:

    st.error(
        "🔴 Low reporting completeness. "
        "Immediate data quality review is recommended."
    )


# ============================================================
# MISSING DATA TABLE
# ============================================================

st.subheader("📭 Missing Data by Woreda / Location")


missing_table = quality_df[
    [
        "Woreda / Location",
        "Indicators",
        "Reported Values",
        "Missing Values",
        "Reporting Completeness %"
    ]
].copy()


st.dataframe(
    missing_table,
    width="stretch"
)


# ============================================================
# ZERO VALUE ANALYSIS
# ============================================================

st.subheader("0️⃣ Zero-Value Analysis")


zero_records = []


for _, row in analysis_df.iterrows():

    indicator = row["Activity"]


    for woreda in selected_woredas:

        if woreda not in row.index:

            continue


        value = row[woreda]


        if pd.notna(value) and value == 0:

            zero_records.append(
                {
                    "Indicator": indicator,
                    "Woreda / Location": woreda,
                    "Value": 0
                }
            )


if len(zero_records) > 0:

    zero_df = pd.DataFrame(
        zero_records
    )

    st.dataframe(
        zero_df,
        width="stretch"
    )

    st.info(
        "ℹ️ Zero is treated as a reported value, "
        "not as missing data."
    )

else:

    st.success(
        "No zero values were detected in the selected data."
    )


# ============================================================
# WOREDA PERFORMANCE SUMMARY
# ============================================================

st.subheader("🏆 Woreda / Location Performance Summary")


performance_df = quality_df[
    [
        "Woreda / Location",
        "Total Reported",
        "Reporting Completeness %",
        "Missing Values",
        "Zero Values"
    ]
].copy()


performance_df = performance_df.sort_values(
    by="Total Reported",
    ascending=False
)


st.dataframe(
    performance_df,
    width="stretch"
)


# ============================================================
# HIGHEST AND LOWEST PERFORMING LOCATIONS
# ============================================================

if len(performance_df) > 0:

    highest_woreda = performance_df.iloc[0]

    lowest_woreda = performance_df.iloc[-1]


    h1, h2 = st.columns(2)


    with h1:

        st.success(
            f"🏆 Highest total reported: "
            f"**{highest_woreda['Woreda / Location']}** "
            f"({highest_woreda['Total Reported']:,.0f})"
        )


    with h2:

        st.warning(
            f"📉 Lowest total reported: "
            f"**{lowest_woreda['Woreda / Location']}** "
            f"({lowest_woreda['Total Reported']:,.0f})"
        )


# ============================================================
# AUTOMATIC INTELLIGENCE SUMMARY
# ============================================================

st.subheader("🤖 Automatic Intelligence Summary")


summary_messages = []


# Reporting completeness
if overall_completeness >= 95:

    summary_messages.append(
        f"Reporting completeness is excellent at "
        f"{overall_completeness:.1f}%."
    )

elif overall_completeness >= 80:

    summary_messages.append(
        f"Reporting completeness is good at "
        f"{overall_completeness:.1f}%, "
        f"although some missing data remains."
    )

elif overall_completeness >= 60:

    summary_messages.append(
        f"Reporting completeness is moderate at "
        f"{overall_completeness:.1f}%. "
        f"Further follow-up is recommended."
    )

else:

    summary_messages.append(
        f"Reporting completeness is low at "
        f"{overall_completeness:.1f}%. "
        f"Immediate data quality follow-up is recommended."
    )


# Missing data
if total_missing_values > 0:

    summary_messages.append(
        f"There are {total_missing_values} missing "
        f"indicator-location values."
    )

else:

    summary_messages.append(
        "No missing indicator-location values "
        "were detected."
    )


# Zero data
if total_zero_values > 0:

    summary_messages.append(
        f"{total_zero_values} reported values are zero. "
        f"These should be reviewed to distinguish true zero "
        f"performance from possible non-reporting or data-entry issues."
    )

else:

    summary_messages.append(
        "No zero values were detected."
    )


# Highest performer
if len(performance_df) > 0:

    summary_messages.append(
        f"The highest total reported value is from "
        f"{highest_woreda['Woreda / Location']}."
    )


# Lowest performer
if len(performance_df) > 1:

    summary_messages.append(
        f"The lowest total reported value is from "
        f"{lowest_woreda['Woreda / Location']}."
    )


for message in summary_messages:

    st.write(
        f"• {message}"
    )


# ============================================================
# INDICATOR TOTAL VISUALIZATION
# ============================================================

st.markdown("---")

st.header("📈 Indicator Visualization")


indicator_chart_df = indicator_summary_df[
    [
        "Indicator",
        "Total Reported"
    ]
].copy()


fig_indicator = px.bar(
    indicator_chart_df,
    x="Indicator",
    y="Total Reported",
    title="Total Reported by Indicator"
)


fig_indicator.update_layout(
    xaxis_title="Indicator",
    yaxis_title="Total Reported"
)


st.plotly_chart(
    fig_indicator,
    width="stretch"
)


# ============================================================
# WOREDA COMPARISON TABLE
# ============================================================

st.header("🏘️ Woreda / Location Comparison")


comparison_df = analysis_df.copy()


comparison_df = comparison_df.set_index(
    "Activity"
)


st.dataframe(
    comparison_df,
    width="stretch"
)


# ============================================================
# VISUALIZATION SELECTION
# ============================================================

st.header("📊 Visualization")


visualization_type = st.selectbox(
    "Select visualization type:",
    [
        "Grouped Bar Chart",
        "Horizontal Bar Chart",
        "Pie Chart",
        "Stacked Bar Chart",
        "Scatter Plot"
    ]
)


# ============================================================
# PREPARE VISUALIZATION DATA
# ============================================================

viz_df = analysis_df.copy()


# ============================================================
# GROUPED BAR CHART
# ============================================================

if visualization_type == "Grouped Bar Chart":

    melted_df = viz_df.melt(
        id_vars="Activity",
        value_vars=selected_woredas,
        var_name="Woreda / Location",
        value_name="Value"
    )


    fig = px.bar(
        melted_df,
        x="Activity",
        y="Value",
        color="Woreda / Location",
        barmode="group",
        title="Indicator Comparison by Woreda / Location"
    )


    fig.update_layout(
        xaxis_title="Indicator",
        yaxis_title="Reported Value"
    )


    st.plotly_chart(
        fig,
        width="stretch"
    )


# ============================================================
# HORIZONTAL BAR CHART
# ============================================================

elif visualization_type == "Horizontal Bar Chart":

    melted_df = viz_df.melt(
        id_vars="Activity",
        value_vars=selected_woredas,
        var_name="Woreda / Location",
        value_name="Value"
    )


    fig = px.bar(
        melted_df,
        y="Activity",
        x="Value",
        color="Woreda / Location",
        barmode="group",
        orientation="h",
        title="Horizontal Indicator Comparison"
    )


    fig.update_layout(
        xaxis_title="Reported Value",
        yaxis_title="Indicator"
    )


    st.plotly_chart(
        fig,
        width="stretch"
    )


# ============================================================
# PIE CHART
# ============================================================

elif visualization_type == "Pie Chart":

    pie_data = quality_df[
        [
            "Woreda / Location",
            "Total Reported"
        ]
    ].copy()


    fig = px.pie(
        pie_data,
        names="Woreda / Location",
        values="Total Reported",
        title="Distribution of Reported Values by Woreda / Location"
    )


    st.plotly_chart(
        fig,
        width="stretch"
    )


# ============================================================
# STACKED BAR CHART
# ============================================================

elif visualization_type == "Stacked Bar Chart":

    melted_df = viz_df.melt(
        id_vars="Activity",
        value_vars=selected_woredas,
        var_name="Woreda / Location",
        value_name="Value"
    )


    fig = px.bar(
        melted_df,
        x="Activity",
        y="Value",
        color="Woreda / Location",
        barmode="stack",
        title="Stacked Indicator Comparison"
    )


    fig.update_layout(
        xaxis_title="Indicator",
        yaxis_title="Reported Value"
    )


    st.plotly_chart(
        fig,
        width="stretch"
    )


# ============================================================
# SCATTER PLOT
# ============================================================

elif visualization_type == "Scatter Plot":

    scatter_df = quality_df[
        [
            "Woreda / Location",
            "Reporting Completeness %",
            "Total Reported"
        ]
    ].copy()


    fig = px.scatter(
        scatter_df,
        x="Reporting Completeness %",
        y="Total Reported",
        text="Woreda / Location",
        title="Reporting Completeness vs Total Reported",
        size="Total Reported"
    )


    fig.update_traces(
        textposition="top center"
    )


    fig.update_layout(
        xaxis_title="Reporting Completeness (%)",
        yaxis_title="Total Reported"
    )


    st.plotly_chart(
        fig,
        width="stretch"
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Public Health Intelligence Platform | "
    "DHIS-2 + Data Analytics + AI"
)