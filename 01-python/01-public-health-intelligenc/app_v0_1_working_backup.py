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

        # Row 1 is empty.
        # Row 2 contains the real column names.
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

    df.columns = df.columns.astype(str).str.strip()

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
    # CHECK FOR ACTIVITY COLUMN
    # --------------------------------------------------

    if "Activity" in df.columns:

        st.subheader("📌 Public Health Indicator Analysis")


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
        # MULTIPLE INDICATOR SELECTION
        # --------------------------------------------------

        selected_indicators = st.multiselect(
            "Select indicators to compare:",
            indicator_list
        )


        # --------------------------------------------------
        # INDICATOR COMPARISON
        # --------------------------------------------------

        if selected_indicators:

            # --------------------------------------------------
            # LOCATION COLUMNS
            # --------------------------------------------------

            value_columns = [
                col for col in df.columns
                if col not in ["Activity", "Total"]
            ]


            # --------------------------------------------------
            # INDICATOR COMPARISON TABLE
            # --------------------------------------------------

            st.subheader("📊 Indicator Comparison")

            comparison_data = []


            for indicator in selected_indicators:

                selected_row = df[
                    df["Activity"].astype(str).str.strip()
                    == indicator
                ]


                if not selected_row.empty:

                    numeric_values = selected_row[
                        value_columns
                    ].apply(
                        pd.to_numeric,
                        errors="coerce"
                    )


                    total_reported = numeric_values.sum(
                        axis=1,
                        skipna=True
                    ).iloc[0]


                    reporting_locations = numeric_values.notna().sum(
                        axis=1
                    ).iloc[0]


                    missing_locations = numeric_values.isna().sum(
                        axis=1
                    ).iloc[0]


                    comparison_data.append({
                        "Indicator": indicator,
                        "Total Reported": total_reported,
                        "Locations Reporting": reporting_locations,
                        "Missing Locations": missing_locations
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

            st.subheader("📊 Indicator Total Comparison")

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
            # WOREDA / LOCATION COMPARISON TABLE
            # --------------------------------------------------

            st.subheader("🏥 Woreda / Location Comparison")

            facility_comparison = []


            for indicator in selected_indicators:

                selected_row = df[
                    df["Activity"].astype(str).str.strip()
                    == indicator
                ]


                if not selected_row.empty:

                    row = selected_row.iloc[0]


                    for location in value_columns:

                        value = pd.to_numeric(
                            row[location],
                            errors="coerce"
                        )


                        facility_comparison.append({
                            "Indicator": indicator,
                            "Location": location,
                            "Reported": value
                        })


            facility_df = pd.DataFrame(
                facility_comparison
            )


            st.dataframe(
                facility_df,
                use_container_width=True
            )


            # --------------------------------------------------
            # WOREDA / LOCATION GROUPED BAR CHART
            # --------------------------------------------------

            st.subheader(
                "📊 Woreda / Location Comparison Chart"
            )


            # Remove missing values
            chart_df = facility_df.dropna(
                subset=["Reported"]
            )


            # Create grouped bar chart
            location_chart = px.bar(
                chart_df,
                x="Location",
                y="Reported",
                color="Indicator",
                barmode="group",
                title="Reported Values by Woreda / Location",
                text="Reported"
            )


            location_chart.update_traces(
                textposition="outside"
            )


            location_chart.update_layout(
                xaxis_title="Woreda / Location",
                yaxis_title="Reported Value",
                height=600,
                legend_title="Indicator",
                xaxis_tickangle=-30
            )


            st.plotly_chart(
                location_chart,
                use_container_width=True
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