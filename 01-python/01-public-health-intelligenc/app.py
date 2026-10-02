import streamlit as st
import pandas as pd
import plotly.express as px


# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Public Health Intelligence Platform",
    page_icon="🏥",
    layout="wide"
)


# --------------------------------------------------
# TITLE
# --------------------------------------------------

st.title("🏥 Public Health Intelligence Platform")

st.write(
    "Upload a public-health Excel or CSV file to begin data analysis."
)


# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload your public-health data",
    type=["xlsx", "csv"]
)


# --------------------------------------------------
# READ DATA
# --------------------------------------------------

if uploaded_file is not None:

    if uploaded_file.name.endswith(".xlsx"):

        df = pd.read_excel(
            uploaded_file,
            header=1
        )

    else:

        df = pd.read_csv(uploaded_file)


    # --------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------

    df = df.dropna(how="all")

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    if "Activity" in df.columns:

        df["Activity"] = (
            df["Activity"]
            .astype(str)
            .str.strip()
        )


    st.success("File uploaded successfully!")


    # --------------------------------------------------
    # DATA PREVIEW
    # --------------------------------------------------

    st.subheader("📋 Data Preview")

    st.dataframe(
        df,
        use_container_width=True
    )


    # --------------------------------------------------
    # DATASET INFORMATION
    # --------------------------------------------------

    st.subheader("📊 Dataset Information")

    col1, col2 = st.columns(2)

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


    # --------------------------------------------------
    # CHECK ACTIVITY COLUMN
    # --------------------------------------------------

    if "Activity" in df.columns:

        st.subheader(
            "📌 Public Health Indicator Analysis"
        )


        # --------------------------------------------------
        # INDICATOR LIST
        # --------------------------------------------------

        indicator_list = (
            df["Activity"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )


        # --------------------------------------------------
        # INDICATOR FILTER
        # --------------------------------------------------

        st.markdown("### 🔎 Data Selection")

        selected_indicators = st.multiselect(
            "Select indicators:",
            indicator_list
        )


        # --------------------------------------------------
        # LOCATION / WOREDA COLUMNS
        # --------------------------------------------------

        value_columns = [
            col
            for col in df.columns
            if col not in ["Activity", "Total"]
        ]


        # --------------------------------------------------
        # WOREDA FILTER
        # --------------------------------------------------

        selected_woredas = st.multiselect(
            "Select Woreda(s):",
            value_columns,
            default=value_columns
        )


        # --------------------------------------------------
        # CHECK INDICATOR SELECTION
        # --------------------------------------------------

        if selected_indicators:

            # --------------------------------------------------
            # CHECK WOREDA SELECTION
            # --------------------------------------------------

            if selected_woredas:

                # --------------------------------------------------
                # INDICATOR COMPARISON
                # --------------------------------------------------

                st.subheader(
                    "📊 Indicator Comparison"
                )

                comparison_data = []


                for indicator in selected_indicators:

                    selected_row = df[
                        df["Activity"]
                        .astype(str)
                        .str.strip()
                        == indicator
                    ]


                    if not selected_row.empty:

                        numeric_values = selected_row[
                            selected_woredas
                        ].apply(
                            pd.to_numeric,
                            errors="coerce"
                        )


                        total_reported = numeric_values.sum(
                            axis=1,
                            skipna=True
                        ).iloc[0]


                        reporting_locations = (
                            numeric_values
                            .notna()
                            .sum(axis=1)
                            .iloc[0]
                        )


                        missing_locations = (
                            numeric_values
                            .isna()
                            .sum(axis=1)
                            .iloc[0]
                        )


                        comparison_data.append({

                            "Indicator": indicator,

                            "Total Reported":
                                total_reported,

                            "Locations Reporting":
                                reporting_locations,

                            "Missing Locations":
                                missing_locations

                        })


                comparison_df = pd.DataFrame(
                    comparison_data
                )


                st.dataframe(
                    comparison_df,
                    use_container_width=True
                )


                # --------------------------------------------------
                # INDICATOR TOTAL CHART
                # --------------------------------------------------

                st.subheader(
                    "📊 Indicator Total Comparison"
                )


                indicator_chart = px.bar(
                    comparison_df,
                    x="Indicator",
                    y="Total Reported",
                    title="Total Reported by Indicator",
                    text="Total Reported"
                )


                indicator_chart.update_traces(
                    textposition="outside"
                )


                indicator_chart.update_layout(
                    xaxis_title="Indicator",
                    yaxis_title="Total Reported",
                    height=500
                )


                st.plotly_chart(
                    indicator_chart,
                    use_container_width=True
                )


                # --------------------------------------------------
                # WOREDA COMPARISON
                # --------------------------------------------------

                st.subheader(
                    "🏥 Woreda Comparison"
                )


                facility_comparison = []


                for indicator in selected_indicators:

                    selected_row = df[
                        df["Activity"]
                        .astype(str)
                        .str.strip()
                        == indicator
                    ]


                    if not selected_row.empty:

                        row = selected_row.iloc[0]


                        for woreda in selected_woredas:

                            value = pd.to_numeric(
                                row[woreda],
                                errors="coerce"
                            )


                            facility_comparison.append({

                                "Indicator":
                                    indicator,

                                "Woreda":
                                    woreda,

                                "Reported":
                                    value

                            })


                facility_df = pd.DataFrame(
                    facility_comparison
                )


                st.dataframe(
                    facility_df,
                    use_container_width=True
                )


                # --------------------------------------------------
                # VISUALIZATION SELECTOR
                # --------------------------------------------------

                st.subheader(
                    "📊 Visualization"
                )


                chart_type = st.selectbox(
                    "Choose a visualization:",
                    [
                        "Grouped Bar Chart",
                        "Horizontal Bar Chart",
                        "Pie Chart",
                        "Stacked Bar Chart",
                        "Scatter Plot"
                    ]
                )


                # --------------------------------------------------
                # REMOVE MISSING VALUES
                # --------------------------------------------------

                chart_df = facility_df.dropna(
                    subset=["Reported"]
                )


                # --------------------------------------------------
                # GROUPED BAR CHART
                # --------------------------------------------------

                if chart_type == "Grouped Bar Chart":

                    location_chart = px.bar(
                        chart_df,
                        x="Woreda",
                        y="Reported",
                        color="Indicator",
                        barmode="group",
                        title="Reported Values by Woreda",
                        text="Reported"
                    )


                    location_chart.update_traces(
                        textposition="outside"
                    )


                    location_chart.update_layout(
                        xaxis_title="Woreda",
                        yaxis_title="Reported Value",
                        height=600,
                        legend_title="Indicator",
                        xaxis_tickangle=-30
                    )


                    st.plotly_chart(
                        location_chart,
                        use_container_width=True
                    )


                # --------------------------------------------------
                # HORIZONTAL BAR CHART
                # --------------------------------------------------

                elif chart_type == "Horizontal Bar Chart":

                    horizontal_chart = px.bar(
                        chart_df,
                        x="Reported",
                        y="Woreda",
                        color="Indicator",
                        barmode="group",
                        orientation="h",
                        title="Reported Values by Woreda",
                        text="Reported"
                    )


                    horizontal_chart.update_traces(
                        textposition="outside"
                    )


                    horizontal_chart.update_layout(
                        xaxis_title="Reported Value",
                        yaxis_title="Woreda",
                        height=600,
                        legend_title="Indicator"
                    )


                    st.plotly_chart(
                        horizontal_chart,
                        use_container_width=True
                    )


                # --------------------------------------------------
                # PIE CHART
                # --------------------------------------------------

                elif chart_type == "Pie Chart":

                    pie_indicator = st.selectbox(
                        "Select an indicator for the pie chart:",
                        selected_indicators
                    )


                    pie_df = chart_df[
                        chart_df["Indicator"]
                        == pie_indicator
                    ]


                    pie_chart = px.pie(
                        pie_df,
                        names="Woreda",
                        values="Reported",
                        title=(
                            f"{pie_indicator} — "
                            "Distribution by Woreda"
                        )
                    )


                    pie_chart.update_layout(
                        height=600
                    )


                    st.plotly_chart(
                        pie_chart,
                        use_container_width=True
                    )


                # --------------------------------------------------
                # STACKED BAR CHART
                # --------------------------------------------------

                elif chart_type == "Stacked Bar Chart":

                    stacked_chart = px.bar(
                        chart_df,
                        x="Woreda",
                        y="Reported",
                        color="Indicator",
                        barmode="stack",
                        title="Indicator Composition by Woreda",
                        text="Reported"
                    )


                    stacked_chart.update_traces(
                        textposition="inside"
                    )


                    stacked_chart.update_layout(
                        xaxis_title="Woreda",
                        yaxis_title="Reported Value",
                        height=600,
                        legend_title="Indicator",
                        xaxis_tickangle=-30
                    )


                    st.plotly_chart(
                        stacked_chart,
                        use_container_width=True
                    )


                # --------------------------------------------------
                # SCATTER PLOT
                # --------------------------------------------------

                elif chart_type == "Scatter Plot":

                    if len(selected_indicators) >= 2:

                        scatter_x = st.selectbox(
                            "Select X-axis indicator:",
                            selected_indicators,
                            key="scatter_x"
                        )


                        scatter_y_options = [
                            indicator
                            for indicator in selected_indicators
                            if indicator != scatter_x
                        ]


                        scatter_y = st.selectbox(
                            "Select Y-axis indicator:",
                            scatter_y_options,
                            key="scatter_y"
                        )


                        scatter_data = chart_df[
                            chart_df["Indicator"].isin(
                                [
                                    scatter_x,
                                    scatter_y
                                ]
                            )
                        ]


                        scatter_pivot = (
                            scatter_data
                            .pivot(
                                index="Woreda",
                                columns="Indicator",
                                values="Reported"
                            )
                            .reset_index()
                        )


                        scatter_chart = px.scatter(
                            scatter_pivot,
                            x=scatter_x,
                            y=scatter_y,
                            hover_name="Woreda",
                            title=(
                                f"{scatter_y} vs "
                                f"{scatter_x}"
                            )
                        )


                        scatter_chart.update_layout(
                            xaxis_title=scatter_x,
                            yaxis_title=scatter_y,
                            height=600
                        )


                        st.plotly_chart(
                            scatter_chart,
                            use_container_width=True
                        )


                    else:

                        st.info(
                            "Select at least two indicators "
                            "to create a scatter plot."
                        )


            else:

                st.warning(
                    "Please select at least one Woreda."
                )


        else:

            st.info(
                "Please select one or more indicators "
                "to begin comparison."
            )


    else:

        st.error(
            "The column 'Activity' was not found. "
            "Please check the Excel file structure."
        )