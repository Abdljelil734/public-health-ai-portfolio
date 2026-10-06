import io
import html
import difflib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Public Health Intelligence Platform",
    page_icon="🏥",
    layout="wide",
)

# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """Normalize text for safer indicator/Woreda matching."""
    if pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ").strip().lower()
    text = " ".join(text.split())
    return text


def clean_number(value):
    """Convert numbers such as '3,154' or ' 3,154 ' to numeric."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return pd.to_numeric(value, errors="coerce")


def classify_performance(value):
    if pd.isna(value):
        return "No Data"
    if value >= 95:
        return "Excellent"
    if value >= 80:
        return "Good"
    if value >= 60:
        return "Moderate"
    return "Poor"


def priority_level(score):
    if score >= 50:
        return "High"
    if score >= 20:
        return "Medium"
    if score > 0:
        return "Low"
    return "No Immediate Priority"


def priority_recommendation(level):
    recommendations = {
        "High": "Immediate review and corrective action required.",
        "Medium": "Close monitoring and targeted supportive action recommended.",
        "Low": "Monitor routinely and address emerging gaps.",
        "No Immediate Priority": "Maintain current performance and routine monitoring.",
    }
    return recommendations.get(level, "Review data.")


def read_performance_file(uploaded_file):
    """Read the existing v0.6-style performance matrix."""
    if uploaded_file is None:
        return None

    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    try:
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data))
        else:
            # Existing v0.6 format: first row is blank/title and row 2 has headers.
            df = pd.read_excel(io.BytesIO(data), header=1)
    except Exception as e:
        st.error(f"Could not read the performance file: {e}")
        return None

    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    if "Activity" not in df.columns and len(df.columns) > 0:
        # Try to identify the indicator/activity column.
        first_col = df.columns[0]
        df = df.rename(columns={first_col: "Activity"})

    if "Activity" not in df.columns:
        st.error("The performance file must contain an 'Activity' column.")
        return None

    df["Activity"] = df["Activity"].astype(str).str.strip()
    df = df[
        (df["Activity"].notna())
        & (df["Activity"].astype(str).str.strip() != "")
        & (df["Activity"].astype(str).str.lower() != "nan")
    ].copy()

    for col in df.columns[1:]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )

    # Remove columns that contain no usable numeric values.
    keep_cols = ["Activity"]
    for col in df.columns[1:]:
        if df[col].notna().any():
            keep_cols.append(col)
    df = df[keep_cols].copy()

    return df


def find_plan_header(raw):
    """
    Locate the plan header row containing Woreda names.
    The uploaded plan currently has Woreda names on row 0.
    """
    preferred = [
        "Atoti Ulo",
        "Halaba Kulito TA",
        "Wera Dijo",
        "Wera",
    ]

    for r in range(min(10, len(raw))):
        row_values = [normalize_text(x) for x in raw.iloc[r].tolist()]
        matches = sum(
            1 for name in preferred
            if normalize_text(name) in row_values
        )
        if matches >= 2:
            return r

    return 0


def read_plan_file(uploaded_file):
    """
    Read the Halaba HIV/STI/Hepatitis plan workbook.

    Supports the current clean format:
        index | Indicator | Atoti Ulo - Yearly | Atoti Ulo - Monthly |
        ... | Halaba Zone - Yearly

    It also retains compatibility with the older Baseline/Target layout.
    """
    if uploaded_file is None:
        return None, None

    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    try:
        if name.endswith(".csv"):
            raw = pd.read_csv(io.BytesIO(data), header=None)
        else:
            raw = pd.read_excel(io.BytesIO(data), header=None)
    except Exception as e:
        st.error(f"Could not read the plan file: {e}")
        return None, None

    raw = raw.dropna(axis=1, how="all")
    if raw.empty:
        st.error("The plan file appears to be empty.")
        return None, None

    # --------------------------------------------------------
    # FORMAT 1: current clean plan format
    # Header contains "Indicator" and columns such as
    # "Atoti Ulo - Monthly".
    # --------------------------------------------------------
    clean_header_row = None
    for r in range(min(10, len(raw))):
        values = [normalize_text(x) for x in raw.iloc[r].tolist()]
        if "indicator" in values and any(
            "monthly" in x and "atoti ulo" in x for x in values
        ):
            clean_header_row = r
            break

    if clean_header_row is not None:
        headers = [
            str(x).strip() if pd.notna(x) else f"Unnamed_{i}"
            for i, x in enumerate(raw.iloc[clean_header_row].tolist())
        ]

        data_df = raw.iloc[clean_header_row + 1:].copy()
        data_df.columns = headers
        data_df = data_df.dropna(how="all")

        # Find the indicator column robustly.
        indicator_col = next(
            (c for c in data_df.columns if normalize_text(c) == "indicator"),
            None,
        )
        if indicator_col is None:
            st.error("The plan file has no Indicator column.")
            return None, None

        # Woreda aliases used in the plan workbook.
        woreda_specs = {
            "Atoti Ulo": "atoti ulo",
            "Halaba Kulito TA": "halaba kulito ta",
            "Wera Dijo": "wera dijo",
            "Wera": "wera",
        }

        records = []
        extra_by_indicator = {}

        for _, row in data_df.iterrows():
            indicator = row[indicator_col]
            if pd.isna(indicator) or str(indicator).strip() == "":
                continue

            indicator = str(indicator).strip()

            # Ignore accidental repeated header rows.
            if normalize_text(indicator) == "indicator":
                continue

            extra = {
                "Indicator": indicator,
                "Zone Plan": np.nan,
                "Monthly Plan": np.nan,
                "Q1 Plan": np.nan,
                "Q2 Plan": np.nan,
                "Q3 Plan": np.nan,
                "Q4 Plan": np.nan,
            }

            for col in data_df.columns:
                ncol = normalize_text(col)

                if "halaba zone" in ncol and "yearly" in ncol:
                    extra["Zone Plan"] = clean_number(row[col])

                if ncol.endswith("- monthly") or (
                    "monthly" in ncol and "target" in ncol
                ):
                    # This is the zone-independent monthly column only if
                    # it is not a Woreda-specific monthly column.
                    if not any(
                        normalize_text(w) in ncol
                        for w in woreda_specs
                    ):
                        extra["Monthly Plan"] = clean_number(row[col])

                for q in ["q1", "q2", "q3", "q4"]:
                    if ncol.endswith(f"- {q}") and not any(
                        normalize_text(w) in ncol
                        for w in woreda_specs
                    ):
                        extra[f"{q.upper()} Plan"] = clean_number(row[col])

            # Extract each Woreda's yearly and monthly target.
            for display_woreda, base in woreda_specs.items():
                yearly_col = None
                monthly_col = None
                q_cols = {}

                for col in data_df.columns:
                    ncol = normalize_text(col)
                    if base in ncol:
                        if "yearly" in ncol:
                            yearly_col = col
                        elif "monthly" in ncol:
                            monthly_col = col
                        elif "q1" in ncol:
                            q_cols["Q1"] = col
                        elif "q2" in ncol:
                            q_cols["Q2"] = col
                        elif "q3" in ncol:
                            q_cols["Q3"] = col
                        elif "q4" in ncol:
                            q_cols["Q4"] = col

                records.append({
                    "Indicator": indicator,
                    "Woreda": display_woreda,
                    "Plan": clean_number(row[yearly_col]) if yearly_col else np.nan,
                    "Annual Plan": clean_number(row[yearly_col]) if yearly_col else np.nan,
                    "Monthly Plan": clean_number(row[monthly_col]) if monthly_col else np.nan,
                    "Q1 Plan": clean_number(row[q_cols["Q1"]]) if "Q1" in q_cols else np.nan,
                    "Q2 Plan": clean_number(row[q_cols["Q2"]]) if "Q2" in q_cols else np.nan,
                    "Q3 Plan": clean_number(row[q_cols["Q3"]]) if "Q3" in q_cols else np.nan,
                    "Q4 Plan": clean_number(row[q_cols["Q4"]]) if "Q4" in q_cols else np.nan,
                    "Zone Plan": extra["Zone Plan"],
                })

        plan_long = pd.DataFrame(records)

        if plan_long.empty:
            st.error("No usable indicator/Woreda plan records were found.")
            return None, None

        # Make sure numeric fields are actually numeric.
        for col in [
            "Plan", "Annual Plan", "Monthly Plan",
            "Q1 Plan", "Q2 Plan", "Q3 Plan", "Q4 Plan", "Zone Plan"
        ]:
            if col in plan_long.columns:
                plan_long[col] = plan_long[col].apply(clean_number)

        return plan_long, raw

    # --------------------------------------------------------
    # FORMAT 2: older Baseline/Target layout
    # --------------------------------------------------------
    preferred = [
        "Atoti Ulo",
        "Halaba Kulito TA",
        "Wera Dijo",
        "Wera",
    ]

    header_row = 0
    for r in range(min(10, len(raw))):
        row_values = [normalize_text(x) for x in raw.iloc[r].tolist()]
        matches = sum(
            1 for name in preferred
            if normalize_text(name) in row_values
        )
        if matches >= 2:
            header_row = r
            break

    header_values = raw.iloc[header_row].tolist()
    zone_col = None
    woreda_cols = {}

    for idx, value in enumerate(header_values):
        n = normalize_text(value)
        if n == "halaba zone":
            zone_col = idx
        elif n in {
            "atoti ulo",
            "halaba kulito ta",
            "wera dijo",
            "wera",
        }:
            woreda_cols[str(value).strip()] = idx

    if len(woreda_cols) < 2 and raw.shape[1] >= 8:
        for idx in range(4, 8):
            value = raw.iloc[header_row, idx]
            if pd.notna(value):
                woreda_cols[str(value).strip()] = idx

    if len(woreda_cols) == 0:
        st.error(
            "I could not identify the Woreda target columns in the plan file."
        )
        return None, None

    records = []

    for r in range(len(raw) - 1):
        indicator_number = clean_number(raw.iloc[r, 0])
        indicator_name = raw.iloc[r, 1] if raw.shape[1] > 1 else np.nan
        next_label = normalize_text(
            raw.iloc[r + 1, 2] if raw.shape[1] > 2 else ""
        )

        if (
            pd.notna(indicator_number)
            and pd.notna(indicator_name)
            and next_label == "target"
        ):
            indicator_name = str(indicator_name).strip()
            target_row = r + 1

            for woreda, col_idx in woreda_cols.items():
                records.append({
                    "Indicator Number": int(indicator_number),
                    "Indicator": indicator_name,
                    "Woreda": woreda,
                    "Plan": clean_number(raw.iloc[target_row, col_idx]),
                })

    if not records:
        st.error("No Target rows were detected in the plan file.")
        return None, None

    plan_long = pd.DataFrame(records)

    monthly_col = None
    quarter_cols = {}

    for idx, value in enumerate(header_values):
        n = normalize_text(value)
        if n == "monthly target":
            monthly_col = idx
        elif n in {"q1", "q2", "q3", "q4"}:
            quarter_cols[n.upper()] = idx

    extra = []
    for r in range(len(raw) - 1):
        indicator_number = clean_number(raw.iloc[r, 0])
        indicator_name = raw.iloc[r, 1] if raw.shape[1] > 1 else np.nan
        next_label = normalize_text(
            raw.iloc[r + 1, 2] if raw.shape[1] > 2 else ""
        )

        if (
            pd.notna(indicator_number)
            and pd.notna(indicator_name)
            and next_label == "target"
        ):
            target_row = r + 1
            extra.append({
                "Indicator": str(indicator_name).strip(),
                "Annual Plan": np.nan,
                "Zone Plan": (
                    clean_number(raw.iloc[target_row, zone_col])
                    if zone_col is not None else np.nan
                ),
                "Monthly Plan": (
                    clean_number(raw.iloc[target_row, monthly_col])
                    if monthly_col is not None else np.nan
                ),
                "Q1 Plan": (
                    clean_number(raw.iloc[target_row, quarter_cols["Q1"]])
                    if "Q1" in quarter_cols else np.nan
                ),
                "Q2 Plan": (
                    clean_number(raw.iloc[target_row, quarter_cols["Q2"]])
                    if "Q2" in quarter_cols else np.nan
                ),
                "Q3 Plan": (
                    clean_number(raw.iloc[target_row, quarter_cols["Q3"]])
                    if "Q3" in quarter_cols else np.nan
                ),
                "Q4 Plan": (
                    clean_number(raw.iloc[target_row, quarter_cols["Q4"]])
                    if "Q4" in quarter_cols else np.nan
                ),
            })

    extra_df = pd.DataFrame(extra)
    if not extra_df.empty:
        plan_long = plan_long.merge(
            extra_df, on="Indicator", how="left"
        )

    return plan_long, raw

def match_indicators(plan_indicators, actual_indicators):
    """
    Match actual indicator names to plan indicators.
    Exact normalized matching is preferred.
    Fuzzy matching is used only when similarity is high.
    """
    plan_lookup = {
        normalize_text(x): x
        for x in plan_indicators
        if normalize_text(x)
    }

    matches = []
    plan_norms = list(plan_lookup.keys())

    for actual in actual_indicators:
        actual_norm = normalize_text(actual)

        if actual_norm in plan_lookup:
            matches.append(
                {
                    "Actual Indicator": actual,
                    "Plan Indicator": plan_lookup[actual_norm],
                    "Match Type": "Exact",
                    "Similarity": 100.0,
                }
            )
            continue

        # First try containment.
        contained = [
            p for p in plan_norms
            if actual_norm in p or p in actual_norm
        ]

        if len(contained) == 1:
            p = contained[0]
            matches.append(
                {
                    "Actual Indicator": actual,
                    "Plan Indicator": plan_lookup[p],
                    "Match Type": "Name similarity",
                    "Similarity": 95.0,
                }
            )
            continue

        candidates = difflib.get_close_matches(
            actual_norm,
            plan_norms,
            n=1,
            cutoff=0.86,
        )

        if candidates:
            p = candidates[0]
            ratio = difflib.SequenceMatcher(
                None, actual_norm, p
            ).ratio() * 100

            matches.append(
                {
                    "Actual Indicator": actual,
                    "Plan Indicator": plan_lookup[p],
                    "Match Type": "Fuzzy",
                    "Similarity": round(ratio, 1),
                }
            )
        else:
            matches.append(
                {
                    "Actual Indicator": actual,
                    "Plan Indicator": None,
                    "Match Type": "Unmatched",
                    "Similarity": 0.0,
                }
            )

    return pd.DataFrame(matches)


def normalize_woreda_name(value):
    """Create a flexible key so plan and performance Woreda labels can match."""
    if pd.isna(value):
        return ""
    x = normalize_text(value)
    # Common reporting suffixes used in plan/performance files.
    for token in [
        "town administration",
        "woreda",
        "district",
    ]:
        x = x.replace(token, " ")
    x = " ".join(x.split())
    # Treat TA and Town as naming variants when they are used only as a
    # geographic suffix in one of the two files.
    x = x.replace(" ta", " ")
    x = x.replace(" town", " ")
    return " ".join(x.split())


def build_plan_actual(performance_df, plan_long, months_covered=1):
    """Merge performance with a period-adjusted plan using Indicator + Woreda.

    The main Plan value is the monthly target multiplied by the selected
    number of months. The official annual Woreda target is retained as a
    reference column and is not used for shorter reporting periods.
    """
    actual_long = performance_df.melt(
        id_vars=["Activity"],
        var_name="Woreda",
        value_name="Actual",
    ).rename(columns={"Activity": "Actual Indicator"})

    actual_long["Actual"] = pd.to_numeric(
        actual_long["Actual"], errors="coerce"
    )

    # Match indicators.
    mapping = match_indicators(
        plan_long["Indicator"].dropna().unique().tolist(),
        actual_long["Actual Indicator"].dropna().unique().tolist(),
    )

    actual_long = actual_long.merge(
        mapping,
        on="Actual Indicator",
        how="left",
    )

    # Normalize Woreda names for safer matching.
    plan_long = plan_long.copy()
    actual_long["Woreda Key"] = actual_long["Woreda"].map(normalize_woreda_name)
    plan_long["Woreda Key"] = plan_long["Woreda"].map(normalize_woreda_name)

    merged = actual_long.merge(
        plan_long,
        left_on=["Plan Indicator", "Woreda Key"],
        right_on=["Indicator", "Woreda Key"],
        how="left",
        suffixes=("", "_plan"),
    )

    # Preserve the official annual target and calculate the target for the
    # selected reporting period from the monthly target.
    merged["Annual Plan"] = pd.to_numeric(
        merged.get("Plan", np.nan), errors="coerce"
    )
    merged["Monthly Plan"] = pd.to_numeric(
        merged.get("Monthly Plan", np.nan), errors="coerce"
    )
    merged["Months Covered"] = int(months_covered)
    merged["Period Plan"] = merged["Monthly Plan"] * int(months_covered)

    # If a monthly target is unavailable, retain the annual target only for
    # the 12-month period as a fallback.
    annual_fallback = (
        (merged["Months Covered"] == 12)
        & merged["Period Plan"].isna()
        & merged["Annual Plan"].notna()
    )
    merged.loc[annual_fallback, "Period Plan"] = merged.loc[annual_fallback, "Annual Plan"]

    # All downstream Plan-vs-Actual calculations use the selected period plan.
    merged["Plan"] = merged["Period Plan"]

    # Gap is defined as Actual minus Expected Plan. Negative means below plan.
    merged["Gap"] = merged["Actual"] - merged["Plan"]

    merged["Achievement %"] = np.where(
        merged["Plan"] > 0,
        (merged["Actual"] / merged["Plan"]) * 100,
        np.nan,
    )

    def interpret(row):
        plan = row["Plan"]
        actual = row["Actual"]
        ach = row["Achievement %"]

        if pd.isna(plan):
            return "No matching plan"
        if pd.isna(actual):
            return "No actual reported"
        if plan == 0 and actual == 0:
            return "Zero plan and zero actual"
        if plan == 0 and actual > 0:
            return "Actual reported against zero plan - validate"
        if actual == 0 and plan > 0:
            return "Critical - zero reported"
        if ach >= 100:
            return "Target met/exceeded"
        if ach >= 95:
            return "Excellent"
        if ach >= 80:
            return "Good"
        if ach >= 60:
            return "Moderate"
        return "Poor"

    merged["Interpretation"] = merged.apply(interpret, axis=1)

    def pa_priority(row):
        plan = row["Plan"]
        actual = row["Actual"]
        ach = row["Achievement %"]

        if pd.isna(plan):
            return "Review"
        if pd.isna(actual):
            return "High"
        if plan > 0 and actual == 0:
            return "High"
        if pd.notna(ach) and ach < 60:
            return "High"
        if pd.notna(ach) and ach < 80:
            return "Medium"
        if pd.notna(ach) and ach < 95:
            return "Low"
        if plan == 0 and actual > 0:
            return "Review"
        return "No Immediate Priority"

    merged["Priority"] = merged.apply(pa_priority, axis=1)

    return merged, mapping


def aggregate_plan_actual_by_indicator(pa_df):
    """Aggregate Woreda-level plan and actual to indicator level."""
    work = pa_df.copy()
    work["Plan"] = pd.to_numeric(work["Plan"], errors="coerce")
    work["Actual"] = pd.to_numeric(work["Actual"], errors="coerce")

    result = (
        work.groupby("Plan Indicator", dropna=False)
        .agg(
            Woredas=("Woreda", "nunique"),
            Plan=("Plan", "sum"),
            Actual=("Actual", "sum"),
            Missing_Woredas=("Actual", lambda s: int(s.isna().sum())),
            Zero_Woredas=(
                "Actual",
                lambda s: int((s.fillna(np.nan) == 0).sum()),
            ),
        )
        .reset_index()
    )

    result["Achievement %"] = np.where(
        result["Plan"] > 0,
        result["Actual"] / result["Plan"] * 100,
        np.nan,
    )
    result["Gap"] = result["Actual"] - result["Plan"]
    result["Performance"] = result["Achievement %"].apply(
        classify_performance
    )
    result["Priority"] = result["Achievement %"].apply(
        lambda x: (
            "High" if pd.notna(x) and x < 60
            else "Medium" if pd.notna(x) and x < 80
            else "Low" if pd.notna(x) and x < 95
            else "No Immediate Priority"
            if pd.notna(x)
            else "Review"
        )
    )
    return result


def aggregate_plan_actual_by_woreda(pa_df):
    """Aggregate Woreda-level plan and actual."""
    work = pa_df.copy()
    work["Plan"] = pd.to_numeric(work["Plan"], errors="coerce")
    work["Actual"] = pd.to_numeric(work["Actual"], errors="coerce")

    result = (
        work.groupby("Woreda", dropna=False)
        .agg(
            Indicators=("Plan Indicator", "nunique"),
            Plan=("Plan", "sum"),
            Actual=("Actual", "sum"),
            Missing_Indicators=("Actual", lambda s: int(s.isna().sum())),
            Zero_Indicators=(
                "Actual",
                lambda s: int((s.fillna(np.nan) == 0).sum()),
            ),
        )
        .reset_index()
    )

    result["Achievement %"] = np.where(
        result["Plan"] > 0,
        result["Actual"] / result["Plan"] * 100,
        np.nan,
    )
    result["Gap"] = result["Actual"] - result["Plan"]
    result["Performance"] = result["Achievement %"].apply(
        classify_performance
    )
    result["Priority"] = result["Achievement %"].apply(
        lambda x: (
            "High" if pd.notna(x) and x < 60
            else "Medium" if pd.notna(x) and x < 80
            else "Low" if pd.notna(x) and x < 95
            else "No Immediate Priority"
            if pd.notna(x)
            else "Review"
        )
    )
    return result


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🏥 Public Health Intelligence")

st.sidebar.subheader("📂 Data Input")

performance_file = st.sidebar.file_uploader(
    "📄 Upload Performance / Actual Data",
    type=["xlsx", "xls", "csv"],
    help="Your current reporting/performance file.",
)

plan_file = st.sidebar.file_uploader(
    "🎯 Upload Plan / Target Data — Optional",
    type=["xlsx", "xls", "csv"],
    help="Optional. Upload a plan to activate Plan-vs-Actual intelligence.",
)

months_covered = 1
if plan_file is not None:
    st.sidebar.subheader("📅 Performance Period")
    month_options = list(range(1, 13))
    months_covered = st.sidebar.selectbox(
        "Number of months of actual data",
        options=month_options,
        index=1,
        format_func=lambda n: {
            1: "1 month",
            3: "3 months — Quarterly",
            6: "6 months — Half-year",
            9: "9 months — 3 quarters",
            12: "12 months — Annual",
        }.get(n, f"{n} months"),
        key="months_covered_v071",
        help=(
            "The app compares actual performance with Monthly Target × "
            "the selected number of months. For 12 months, the official "
            "annual target is also retained for reference."
        ),
    )
    st.sidebar.caption(
        f"Expected period plan = Monthly Target × {months_covered} month(s)"
    )

st.sidebar.markdown("---")

# ============================================================
# LOAD PERFORMANCE DATA
# ============================================================

df = read_performance_file(performance_file)

if df is None:
    st.title("🏥 Public Health Intelligence Platform")
    st.info(
        "Upload your Performance / Actual Excel or CSV file from the "
        "left sidebar to begin."
    )
    st.markdown(
        """
### Version 0.7

This version supports two operating modes:

**🟢 Performance-only mode**
- Trend analysis
- Indicator comparison
- Woreda comparison
- Completeness
- Priority identification
- Public-health intelligence
- Visualizations

**🎯 Plan-vs-Actual mode**
- Upload the optional Plan/Target file
- Automatic Indicator + Woreda matching
- Achievement %
- Gap analysis
- Underperforming Woredas and indicators
- Automatic interpretation
- Decision-support recommendations
        """
    )
    st.stop()

# ============================================================
# OPTIONAL PLAN
# ============================================================

plan_long = None
plan_raw = None

if plan_file is not None:
    plan_long, plan_raw = read_plan_file(plan_file)

# ============================================================
# SIDEBAR DATA SELECTION
# ============================================================

st.sidebar.subheader("🔎 Data Selection")

indicator_options = df["Activity"].dropna().astype(str).unique().tolist()

if "selected_indicators_v06" not in st.session_state:
    st.session_state.selected_indicators_v06 = indicator_options.copy()

indicator_search = st.sidebar.text_input(
    "Search indicators",
    placeholder="Type letters to search...",
    key="indicator_search_v07",
)

filtered_indicators = [
    x for x in indicator_options
    if indicator_search.lower() in x.lower()
]

selected_indicators = st.sidebar.multiselect(
    "Select indicators",
    options=filtered_indicators,
    default=[
        x for x in st.session_state.selected_indicators_v06
        if x in filtered_indicators
    ],
    key="indicator_multiselect_v07",
)

st.session_state.selected_indicators_v06 = selected_indicators

# Highlight selected indicator names in the sidebar so long names remain easy to read.
st.sidebar.markdown(
    """
    <style>
    /* Give the sidebar a little more horizontal space for long DHIS-2 names. */
    [data-testid="stSidebar"] {
        min-width: 360px;
        max-width: 420px;
    }

    /* Make the selected-indicator area visually distinct. */
    .selected-indicator-box {
        background: rgba(49, 130, 206, 0.12);
        border-left: 4px solid #3182ce;
        border-radius: 6px;
        padding: 8px 10px;
        margin: 5px 0 6px 0;
        line-height: 1.35;
        word-wrap: break-word;
        overflow-wrap: anywhere;
    }

    .selected-indicator-title {
        font-weight: 700;
        margin-bottom: 7px;
    }

    .selected-indicator-name {
        background: rgba(255, 255, 0, 0.22);
        border-radius: 4px;
        padding: 5px 7px;
        margin: 4px 0;
        font-size: 0.88rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if selected_indicators:
    selected_html = [
        '<div class="selected-indicator-box">',
        f'<div class="selected-indicator-title">🎯 Selected indicators ({len(selected_indicators)})</div>',
    ]
    for indicator in selected_indicators:
        safe_indicator = html.escape(str(indicator))
        selected_html.append(
            f'<div class="selected-indicator-name">✓ {safe_indicator}</div>'
        )
    selected_html.append('</div>')
    st.sidebar.markdown("".join(selected_html), unsafe_allow_html=True)
else:
    st.sidebar.info("No indicator selected.")

woreda_options = [
    c for c in df.columns
    if c != "Activity"
]

if "selected_woredas_v06" not in st.session_state:
    st.session_state.selected_woredas_v06 = woreda_options.copy()

woreda_search = st.sidebar.text_input(
    "Search Woredas",
    placeholder="Type letters to search...",
    key="woreda_search_v07",
)

filtered_woredas = [
    x for x in woreda_options
    if woreda_search.lower() in x.lower()
]

selected_woredas = st.sidebar.multiselect(
    "Select Woredas",
    options=filtered_woredas,
    default=[
        x for x in st.session_state.selected_woredas_v06
        if x in filtered_woredas
    ],
    key="woreda_multiselect_v07",
)

st.session_state.selected_woredas_v06 = selected_woredas

# Apply selection.
selected_df = df[
    df["Activity"].isin(selected_indicators)
][["Activity"] + [
    c for c in selected_woredas if c in df.columns
]].copy()

if len(selected_woredas) == 0:
    selected_df = df[
        df["Activity"].isin(selected_indicators)
    ].copy()

# ============================================================
# PLAN-ACTUAL MERGE
# ============================================================

pa_df = None
indicator_match_df = None

if plan_long is not None and not selected_df.empty:
    pa_df, indicator_match_df = build_plan_actual(
        df,
        plan_long,
        months_covered=months_covered,
    )

# ============================================================
# TABS
# ============================================================

tabs = [
    "📊 Overview",
    "📋 Indicator Performance & Ranking",
    "🏘️ Woreda Performance & Ranking",
    "🚨 Priority Identification",
    "🧠 Public-Health Intelligence",
    "💡 Decision-Support Recommendations",
    "📈 Visualization",
]

if plan_long is not None:
    tabs.append("🎯 Plan vs Actual Intelligence")

tab_objects = st.tabs(tabs)

# ============================================================
# TAB 1: OVERVIEW
# ============================================================

with tab_objects[0]:
    st.header("📊 Executive Overview")

    total_indicators = len(selected_df)
    total_woredas = len(
        [c for c in selected_df.columns if c != "Activity"]
    )

    numeric_values = selected_df.iloc[:, 1:].apply(
        pd.to_numeric, errors="coerce"
    )

    total_cells = numeric_values.size
    reported_cells = int(numeric_values.notna().sum().sum())
    missing_cells = total_cells - reported_cells
    zero_cells = int((numeric_values == 0).sum().sum())

    completeness = (
        reported_cells / total_cells * 100
        if total_cells > 0
        else 0
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Indicators", total_indicators)
    c2.metric("Woredas", total_woredas)
    c3.metric("Reporting Completeness", f"{completeness:.1f}%")
    c4.metric("Reported Values", f"{reported_cells:,}")
    c5.metric("Missing Values", f"{missing_cells:,}")
    c6.metric("Zero Values", f"{zero_cells:,}")

    st.subheader("Selected Data Preview")
    st.dataframe(
        selected_df,
        use_container_width=True,
        height=420,
    )

    if plan_long is not None:
        st.success(
            "🎯 Plan file detected. Plan-vs-Actual Intelligence is active."
        )
    else:
        st.info(
            "Performance-only mode is active. Uploading a Plan/Target file "
            "will activate Plan-vs-Actual Intelligence."
        )

# ============================================================
# TAB 2: INDICATOR PERFORMANCE
# ============================================================

with tab_objects[1]:
    st.header("📋 Indicator Performance & Ranking")

    work = selected_df.copy()
    rows = []

    for _, row in work.iterrows():
        values = pd.to_numeric(
            row.iloc[1:],
            errors="coerce",
        )

        total = len(values)
        reported = int(values.notna().sum())
        missing = total - reported
        zeros = int((values == 0).sum())
        reporting_pct = (
            reported / total * 100
            if total > 0
            else 0
        )

        performance = classify_performance(reporting_pct)
        score = (
            missing * 3
            + zeros
            + max(0, 100 - reporting_pct)
        )
        priority = priority_level(score)

        rows.append(
            {
                "Indicator": row["Activity"],
                "Reported Woredas": reported,
                "Missing Woredas": missing,
                "Zero Values": zeros,
                "Reporting %": round(reporting_pct, 1),
                "Performance": performance,
                "Priority Score": round(score, 1),
                "Priority": priority,
                "Recommendation": priority_recommendation(priority),
            }
        )

    indicator_rank = pd.DataFrame(rows).sort_values(
        ["Priority Score", "Reporting %"],
        ascending=[False, True],
    )

    st.dataframe(
        indicator_rank,
        use_container_width=True,
        height=500,
    )

# ============================================================
# TAB 3: WOREDA PERFORMANCE
# ============================================================

with tab_objects[2]:
    st.header("🏘️ Woreda Performance & Ranking")

    rows = []

    for woreda in selected_woredas:
        if woreda not in selected_df.columns:
            continue

        values = pd.to_numeric(
            selected_df[woreda],
            errors="coerce",
        )

        total = len(values)
        reported = int(values.notna().sum())
        missing = total - reported
        zeros = int((values == 0).sum())
        completeness = (
            reported / total * 100
            if total > 0
            else 0
        )

        performance = classify_performance(completeness)
        score = (
            missing * 3
            + zeros
            + max(0, 100 - completeness)
        )
        priority = priority_level(score)

        rows.append(
            {
                "Woreda": woreda,
                "Reported Indicators": reported,
                "Missing Indicators": missing,
                "Zero Values": zeros,
                "Completeness %": round(completeness, 1),
                "Performance": performance,
                "Priority Score": round(score, 1),
                "Priority": priority,
                "Recommendation": priority_recommendation(priority),
            }
        )

    woreda_rank = pd.DataFrame(rows).sort_values(
        ["Priority Score", "Completeness %"],
        ascending=[False, True],
    )

    st.dataframe(
        woreda_rank,
        use_container_width=True,
        height=500,
    )

# ============================================================
# TAB 4: PRIORITY IDENTIFICATION
# ============================================================

with tab_objects[3]:
    st.header("🚨 Priority Identification")

    overall_priority_score = (
        missing_cells * 3
        + zero_cells
        + max(0, 100 - completeness)
    )

    overall_priority = priority_level(overall_priority_score)

    if completeness < 60:
        st.error(
            f"🔴 High concern: overall reporting completeness is "
            f"{completeness:.1f}%."
        )
    elif completeness < 80:
        st.warning(
            f"🟠 Moderate concern: reporting completeness is "
            f"{completeness:.1f}%."
        )
    else:
        st.success(
            f"🟢 Reporting completeness is {completeness:.1f}%."
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Priority", overall_priority)
    c2.metric("Missing Values", f"{missing_cells:,}")
    c3.metric("Zero Values", f"{zero_cells:,}")

    st.subheader("Critical Missing Data")
    missing_table = []

    for _, row in selected_df.iterrows():
        for woreda in selected_woredas:
            if woreda in selected_df.columns:
                value = pd.to_numeric(
                    row[woreda],
                    errors="coerce",
                )
                if pd.isna(value):
                    missing_table.append(
                        {
                            "Indicator": row["Activity"],
                            "Woreda": woreda,
                            "Issue": "Missing / not reported",
                        }
                    )

    if missing_table:
        st.dataframe(
            pd.DataFrame(missing_table),
            use_container_width=True,
            height=400,
        )
    else:
        st.success("No missing values found in the selected data.")

# ============================================================
# TAB 5: INTELLIGENCE
# ============================================================

with tab_objects[4]:
    st.header("🧠 Public-Health Intelligence")

    if not indicator_rank.empty:
        worst_indicator = indicator_rank.iloc[0]

        st.subheader("Indicator-level finding")
        st.write(
            f"**{worst_indicator['Indicator']}** has the highest priority "
            f"score among the selected indicators, with "
            f"{worst_indicator['Reporting %']:.1f}% reporting."
        )

    if "woreda_rank" in locals() and not woreda_rank.empty:
        worst_woreda = woreda_rank.iloc[0]

        st.subheader("Woreda-level finding")
        st.write(
            f"**{worst_woreda['Woreda']}** has the highest priority score "
            f"among the selected Woredas, with "
            f"{worst_woreda['Completeness %']:.1f}% completeness."
        )

    st.subheader("Management interpretation")

    if completeness >= 95:
        st.success(
            "The selected reporting dataset has very high completeness. "
            "Management attention can focus more strongly on program "
            "performance and service-delivery results."
        )
    elif completeness >= 80:
        st.info(
            "Reporting completeness is generally good, but selected "
            "missing and zero values should be reviewed before drawing "
            "strong programmatic conclusions."
        )
    else:
        st.warning(
            "Data completeness requires management attention. "
            "Performance interpretation should be combined with "
            "data-quality verification."
        )

# ============================================================
# TAB 6: RECOMMENDATIONS
# ============================================================

with tab_objects[5]:
    st.header("💡 Decision-Support Recommendations")

    st.subheader("🏘️ Woreda-level recommendations")

    if "woreda_rank" in locals() and not woreda_rank.empty:
        for _, row in woreda_rank.head(10).iterrows():
            st.write(
                f"**{row['Woreda']} — {row['Priority']}:** "
                f"{row['Recommendation']}"
            )

    st.subheader("📋 Indicator-level recommendations")

    if not indicator_rank.empty:
        for _, row in indicator_rank.head(10).iterrows():
            st.write(
                f"**{row['Indicator']} — {row['Priority']}:** "
                f"{row['Recommendation']}"
            )

    st.subheader("👔 Executive action")
    st.write(
        "Use the priority list to focus supportive supervision, "
        "data-quality review, mentorship and performance-improvement "
        "actions on the Woredas and indicators with the largest gaps."
    )

# ============================================================
# TAB 7: VISUALIZATION
# ============================================================

with tab_objects[6]:
    st.header("📈 Visualization")

    if selected_df.shape[1] <= 1:
        st.warning("Select at least one Woreda for visualization.")
    elif selected_df.empty:
        st.warning("Select at least one indicator.")
    else:
        st.subheader("🎯 Selected Indicators by Woreda")

        visualization_options = [
            "📊 Grouped Bar — Indicator by Woreda",
            "📈 Line Chart — Indicator by Woreda",
            "📚 Stacked Bar — Indicator by Woreda",
            "🔥 Heatmap — Indicator vs Woreda",
            "📊 Total Reported Value by Indicator",
        ]

        selected_visualization = st.selectbox(
            "Choose visualization",
            visualization_options,
            key="selected_visualization_v07",
        )

        selected_long = selected_df.melt(
            id_vars=["Activity"],
            var_name="Woreda",
            value_name="Value",
        )

        selected_long["Value"] = pd.to_numeric(
            selected_long["Value"],
            errors="coerce",
        )

        selected_long = selected_long.dropna(subset=["Value"])

        if selected_visualization.startswith("📊 Grouped"):
            fig = px.bar(
                selected_long,
                x="Woreda",
                y="Value",
                color="Activity",
                barmode="group",
                title="Selected Indicators by Woreda",
            )
            st.plotly_chart(fig, use_container_width=True)

        elif selected_visualization.startswith("📈 Line"):
            fig = px.line(
                selected_long,
                x="Woreda",
                y="Value",
                color="Activity",
                markers=True,
                title="Selected Indicators by Woreda",
            )
            st.plotly_chart(fig, use_container_width=True)

        elif selected_visualization.startswith("📚 Stacked"):
            fig = px.bar(
                selected_long,
                x="Woreda",
                y="Value",
                color="Activity",
                barmode="stack",
                title="Stacked Indicator Values by Woreda",
            )
            st.plotly_chart(fig, use_container_width=True)

        elif selected_visualization.startswith("🔥 Heatmap"):
            heat = selected_df.set_index("Activity")
            heat = heat.apply(pd.to_numeric, errors="coerce")

            fig = px.imshow(
                heat,
                aspect="auto",
                labels={
                    "x": "Woreda",
                    "y": "Indicator",
                    "color": "Value",
                },
                title="Indicator vs Woreda Heatmap",
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            totals = (
                selected_long.groupby("Activity")["Value"]
                .sum()
                .reset_index()
                .sort_values("Value", ascending=False)
            )

            fig = px.bar(
                totals,
                x="Activity",
                y="Value",
                title="Total Reported Value by Indicator",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📌 Secondary Visualization")

        secondary_options = [
            "🏘️ Woreda Completeness Ranking",
            "📋 Indicator Completeness Ranking",
            "↔️ Reported vs Missing by Woreda",
            "🎯 Woreda Completeness vs Missing Indicators",
        ]

        secondary = st.selectbox(
            "Choose secondary visualization",
            secondary_options,
            key="secondary_visualization_v07",
        )

        if secondary.startswith("🏘️"):
            fig = px.bar(
                woreda_rank.sort_values("Completeness %"),
                x="Completeness %",
                y="Woreda",
                orientation="h",
                title="Woreda Completeness Ranking",
            )
            st.plotly_chart(fig, use_container_width=True)

        elif secondary.startswith("📋"):
            fig = px.bar(
                indicator_rank.sort_values("Reporting %"),
                x="Reporting %",
                y="Indicator",
                orientation="h",
                title="Indicator Completeness Ranking",
            )
            st.plotly_chart(fig, use_container_width=True)

        elif secondary.startswith("↔️"):
            compare = woreda_rank[
                ["Woreda", "Reported Indicators", "Missing Indicators"]
            ].melt(
                id_vars=["Woreda"],
                var_name="Status",
                value_name="Count",
            )

            fig = px.bar(
                compare,
                x="Woreda",
                y="Count",
                color="Status",
                barmode="group",
                title="Reported vs Missing Indicators by Woreda",
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            fig = px.scatter(
                woreda_rank,
                x="Completeness %",
                y="Missing Indicators",
                text="Woreda",
                title="Woreda Completeness vs Missing Indicators",
            )
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 8: PLAN VS ACTUAL
# ============================================================

if plan_long is not None:
    with tab_objects[7]:
        st.header("🎯 Plan vs Actual Intelligence")

        st.info(
            f"Reporting period: **{months_covered} month(s)**. "
            f"Expected plan is based on **Monthly Target × {months_covered}**. "
            "The official annual Woreda target is retained as a reference."
        )

        if pa_df is None or pa_df.empty:
            st.warning(
                "The plan was uploaded, but no Plan-vs-Actual records "
                "could be created from the current performance data."
            )
        else:
            # Restrict the display to the selected Woredas/indicators.
            pa_selected = pa_df.copy()

            if selected_woredas:
                pa_selected = pa_selected[
                    pa_selected["Woreda"].isin(selected_woredas)
                ]

            if selected_indicators:
                # selected actual indicators may differ slightly from plan names
                pa_selected = pa_selected[
                    pa_selected["Actual Indicator"].isin(
                        selected_indicators
                    )
                ]

            valid = pa_selected[
                pa_selected["Plan"].notna()
                & pa_selected["Actual"].notna()
                & (pa_selected["Plan"] > 0)
            ].copy()

            total_plan = valid["Plan"].sum()
            total_actual = valid["Actual"].sum()

            overall_achievement = (
                total_actual / total_plan * 100
                if total_plan > 0
                else np.nan
            )

            total_gap = total_actual - total_plan
            missing_actual = int(
                pa_selected["Actual"].isna().sum()
            )
            zero_actual = int(
                (pa_selected["Actual"].fillna(np.nan) == 0).sum()
            )

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric(
                "Total Plan",
                f"{total_plan:,.0f}",
            )
            c2.metric(
                "Total Actual",
                f"{total_actual:,.0f}",
            )
            c3.metric(
                "Achievement",
                (
                    f"{overall_achievement:.1f}%"
                    if pd.notna(overall_achievement)
                    else "N/A"
                ),
            )
            c4.metric(
                "Gap",
                f"{total_gap:,.0f}",
            )
            c5.metric(
                "Missing Actual",
                f"{missing_actual:,}",
            )

            # Automatic interpretation.
            st.subheader("🧠 Automatic Interpretation")

            if pd.isna(overall_achievement):
                st.warning(
                    "There is not enough matched Plan and Actual data "
                    "to calculate overall achievement."
                )
            elif overall_achievement >= 100:
                st.success(
                    f"Overall achievement is {overall_achievement:.1f}%. "
                    "The selected program has met or exceeded the "
                    "expected plan for the selected reporting period. Values substantially above "
                    "100% should still be validated."
                )
            elif overall_achievement >= 95:
                st.success(
                    f"Overall achievement is {overall_achievement:.1f}%, "
                    "indicating excellent progress against plan."
                )
            elif overall_achievement >= 80:
                st.info(
                    f"Overall achievement is {overall_achievement:.1f}%, "
                    "indicating generally good progress, with remaining "
                    "gaps requiring monitoring."
                )
            elif overall_achievement >= 60:
                st.warning(
                    f"Overall achievement is {overall_achievement:.1f}%, "
                    "indicating moderate performance and a need for "
                    "targeted improvement."
                )
            else:
                st.error(
                    f"Overall achievement is {overall_achievement:.1f}%. "
                    "This indicates a substantial gap against plan and "
                    "requires priority management attention."
                )

            # Woreda ranking.
            st.subheader("🏘️ Woreda Achievement Ranking")

            woreda_pa = aggregate_plan_actual_by_woreda(
                pa_selected
            )

            st.dataframe(
                woreda_pa.sort_values(
                    "Achievement %",
                    ascending=True,
                ),
                use_container_width=True,
                height=400,
            )

            # Indicator ranking.
            st.subheader("📋 Indicator Achievement Ranking")

            indicator_pa = aggregate_plan_actual_by_indicator(
                pa_selected
            )

            st.dataframe(
                indicator_pa.sort_values(
                    "Achievement %",
                    ascending=True,
                ),
                use_container_width=True,
                height=450,
            )

            # Critical gaps.
            st.subheader("🚨 Critical Gaps")

            critical = pa_selected[
                (
                    (pa_selected["Priority"] == "High")
                    | (
                        pa_selected["Achievement %"].notna()
                        & (pa_selected["Achievement %"] < 60)
                    )
                    | (
                        pa_selected["Actual"].isna()
                        & pa_selected["Plan"].notna()
                    )
                )
            ].copy()

            critical_cols = [
                "Actual Indicator",
                "Woreda",
                "Months Covered",
                "Monthly Plan",
                "Period Plan",
                "Annual Plan",
                "Plan",
                "Actual",
                "Achievement %",
                "Gap",
                "Interpretation",
                "Priority",
            ]

            if not critical.empty:
                st.dataframe(
                    critical[
                        [
                            c for c in critical_cols
                            if c in critical.columns
                        ]
                    ].sort_values(
                        ["Priority", "Achievement %"],
                        ascending=[True, True],
                    ),
                    use_container_width=True,
                    height=450,
                )
            else:
                st.success(
                    "No critical Plan-vs-Actual gaps were detected "
                    "in the selected data."
                )

            # Visualization.
            st.subheader("📈 Plan vs Actual Visualization")

            pa_chart_options = [
                "📊 Plan vs Actual by Woreda",
                "📋 Plan vs Actual by Indicator",
                "🎯 Achievement % by Woreda",
                "🎯 Achievement % by Indicator",
            ]

            pa_chart = st.selectbox(
                "Choose Plan-vs-Actual visualization",
                pa_chart_options,
                key="plan_actual_chart_v07",
            )

            if pa_chart.startswith("📊"):
                chart_df = woreda_pa.melt(
                    id_vars=["Woreda"],
                    value_vars=["Plan", "Actual"],
                    var_name="Type",
                    value_name="Value",
                )

                fig = px.bar(
                    chart_df,
                    x="Woreda",
                    y="Value",
                    color="Type",
                    barmode="group",
                    title="Plan vs Actual by Woreda",
                )
                st.plotly_chart(fig, use_container_width=True)

            elif pa_chart.startswith("📋"):
                chart_df = indicator_pa.melt(
                    id_vars=["Plan Indicator"],
                    value_vars=["Plan", "Actual"],
                    var_name="Type",
                    value_name="Value",
                )

                fig = px.bar(
                    chart_df,
                    x="Plan Indicator",
                    y="Value",
                    color="Type",
                    barmode="group",
                    title="Plan vs Actual by Indicator",
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            elif pa_chart.startswith("🎯") and "Woreda" in pa_chart:
                chart_df = woreda_pa.dropna(
                    subset=["Achievement %"]
                ).sort_values("Achievement %")

                fig = px.bar(
                    chart_df,
                    x="Achievement %",
                    y="Woreda",
                    orientation="h",
                    title="Achievement % by Woreda",
                )
                fig.add_vline(
                    x=95,
                    line_dash="dash",
                    annotation_text="95% target",
                )
                st.plotly_chart(fig, use_container_width=True)

            else:
                chart_df = indicator_pa.dropna(
                    subset=["Achievement %"]
                ).sort_values("Achievement %")

                fig = px.bar(
                    chart_df,
                    x="Achievement %",
                    y="Plan Indicator",
                    orientation="h",
                    title="Achievement % by Indicator",
                )
                fig.add_vline(
                    x=95,
                    line_dash="dash",
                    annotation_text="95% target",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "Plan values shown as **Plan** are the selected-period expected plan. "
                "Annual Plan is the official annual Woreda target from the uploaded workbook."
            )

            # Matching quality.
            st.subheader("🔗 Indicator Matching Quality")

            if indicator_match_df is not None:
                st.dataframe(
                    indicator_match_df,
                    use_container_width=True,
                    height=350,
                )

                unmatched = indicator_match_df[
                    indicator_match_df["Match Type"] == "Unmatched"
                ]

                fuzzy = indicator_match_df[
                    indicator_match_df["Match Type"] == "Fuzzy"
                ]

                if not unmatched.empty:
                    st.warning(
                        f"{len(unmatched)} performance indicator(s) "
                        "could not be matched to the plan."
                    )

                if not fuzzy.empty:
                    st.info(
                        f"{len(fuzzy)} indicator(s) were matched using "
                        "name similarity. Review these matches before "
                        "using the results for formal reporting."
                    )

            # Detailed data.
            with st.expander("🔍 View detailed Plan-vs-Actual records"):
                detail_cols = [
                    "Actual Indicator",
                    "Plan Indicator",
                    "Woreda",
                    "Plan",
                    "Actual",
                    "Achievement %",
                    "Gap",
                    "Interpretation",
                    "Priority",
                ]

                st.dataframe(
                    pa_selected[
                        [
                            c for c in detail_cols
                            if c in pa_selected.columns
                        ]
                    ],
                    use_container_width=True,
                    height=500,
                )

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

if plan_long is not None:
    st.caption(
        "🏥 Public Health Intelligence Platform | "
        "DHIS-2 + Data Analytics + AI Engineering | Version 0.7.1 | "
        "Performance + Plan-vs-Actual Intelligence"
    )
else:
    st.caption(
        "🏥 Public Health Intelligence Platform | "
        "DHIS-2 + Data Analytics + AI Engineering | Version 0.7.1 | "
        "Performance-only mode"
    )
