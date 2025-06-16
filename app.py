import streamlit as st
import pandas as pd
import altair as alt
from fetch_data import scrape_esg_scores

st.set_page_config(page_title="ESG Dashboard", layout="wide")

def render_risk_badge(level: str):
    level = (level or "").lower()
    if level == "negligible":
        return "🟢 Negligible"
    elif level == "medium":
        return "🟠 Medium"
    elif level == "severe":
        return "🔴 Severe"
    else:
        return "N/A"

@st.cache_data(show_spinner=True)
def fetch_data(tickers):
    results = []
    total = len(tickers)

    valid_count = 0

    for t in tickers:
        data = scrape_esg_scores(t)
        if data and data["total"] is not None:
            valid_count += 1
            results.append({
                "Ticker": t,
                "Total ESG Risk Score": data["total"],
                "Total ESG Risk Level": data["total_level"],
                "Environmental Risk": data["environmental"],
                "Social Risk": data["social"],
                "Governance Risk": data["governance"],
                "Controversy Score": data["controversy_score"],
                "Controversy Category Average": data["controversy_category_average"],
                "Involvement Areas": data.get("involvement_areas", {}),
            })

    return pd.DataFrame(results), valid_count

def explode_involvement_columns(df):
    if df.empty:
        return df
    involvement_df = df["Involvement Areas"].apply(pd.Series).fillna("No")
    involvement_df.columns = [f"{c}" for c in involvement_df.columns]
    df_expanded = pd.concat([df.drop(columns=["Involvement Areas"]), involvement_df], axis=1)
    return df_expanded

# sidebar inputs
st.sidebar.header("Input")
uploaded_file = st.sidebar.file_uploader("Upload CSV file with tickers (must have 'Ticker' column)", type=["csv"])
single_ticker = st.sidebar.text_input("Or enter a single ticker:")

tickers = []

if uploaded_file:
    try:
        df_uploaded = pd.read_csv(uploaded_file)
        if "Ticker" not in df_uploaded.columns:
            st.sidebar.error("CSV must have a 'Ticker' column")
        else:
            tickers = df_uploaded["Ticker"].dropna().astype(str).str.upper().unique().tolist()
    except Exception as e:
        st.sidebar.error(f"Error reading CSV: {e}")

if single_ticker:
    tickers = [single_ticker.upper()]

if not tickers:
    st.info("Please upload a CSV with tickers or enter a ticker in the sidebar.")
    st.stop()

# show while fetching data
with st.spinner("Getting ESG data..."):
    df, valid_count = fetch_data(tickers)

if df.empty:
    st.error("No ESG data found for the given tickers.")
    st.stop()

df_expanded = explode_involvement_columns(df)

# export button csv
export_csv = df_expanded.to_csv(index=False)
st.download_button(
    label="Export data as CSV",
    data=export_csv,
    file_name="esg_data_export.csv",
    mime="text/csv",
    key="export-csv",
    help="Download the full ESG data"
)

# nrmalize risk level column for consistent plotting
df["Total ESG Risk Level"] = df["Total ESG Risk Level"].str.lower().fillna("unknown")

# overall summary only if multiple tickers
if len(df) > 1:
    st.header("ESG Overview")
    
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        coverage_pct = (valid_count / len(tickers)) * 100
        st.metric(
            "Data Coverage", 
            f"{coverage_pct:.1f}%",
            delta=f"{valid_count}/{len(tickers)} companies",
            help="Percentage of tickers with available ESG data"
        )
    
    with metric_col2:
        avg_total = df["Total ESG Risk Score"].mean()
        median_total = df["Total ESG Risk Score"].median()
        delta_avg_median = avg_total - median_total
        st.metric(
            "Avg ESG Risk Score", 
            f"{avg_total:.1f}",
            delta=f"{delta_avg_median:+.1f} vs median",
            help="Average total ESG risk score across all companies"
        )
    
    with metric_col3:
        high_risk_count = len(df[df["Total ESG Risk Level"] == "severe"])
        high_risk_pct = (high_risk_count / len(df)) * 100 if len(df) > 0 else 0
        st.metric(
            "High Risk Companies", 
            f"{high_risk_count}",
            delta=f"{high_risk_pct:.1f}% of portfolio",
            delta_color="inverse",
            help="Companies with 'Severe' ESG risk level"
        )
    
    with metric_col4:
        risk_counts = df["Total ESG Risk Level"].value_counts()
        most_common_risk = risk_counts.index[0] if len(risk_counts) > 0 else "N/A"
        st.metric(
            "Most Common Risk Level", 
            most_common_risk.title(),
            delta=f"{risk_counts.iloc[0]} companies" if len(risk_counts) > 0 else "0",
            help="Most frequently occurring risk level in portfolio"
        )
    
    st.markdown("---")
    
    # Visualizations row
    viz_col1, viz_col2 = st.columns(2)
    
    with viz_col1:
        risk_color_map = {
            'negligible': '#2E8B57',
            'medium': '#FF8C00',
            'severe': '#DC143C',
            'unknown': '#888888'
        }
        
        chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("Total ESG Risk Level:N", 
                   title="Risk Level",
                   sort=['negligible', 'medium', 'severe', 'unknown']),
            y=alt.Y("count()", title="Number of Companies"),
            color=alt.Color("Total ESG Risk Level:N", 
                           scale=alt.Scale(
                               domain=['negligible', 'medium', 'severe', 'unknown'],
                               range=[risk_color_map['negligible'], risk_color_map['medium'], risk_color_map['severe'], risk_color_map['unknown']]
                           ),
                           legend=alt.Legend(title="Risk Level")),
            tooltip=[alt.Tooltip("Total ESG Risk Level:N", title="Risk Level"), alt.Tooltip("count()", title="Count")]
        ).properties(
            title="Distribution of Total ESG Risk Levels",
            width=300,
            height=300
        )
        st.altair_chart(chart, use_container_width=True)
    
    with viz_col2:
        avg_scores = {
            'Environmental': df["Environmental Risk"].mean(),
            'Social': df["Social Risk"].mean(), 
            'Governance': df["Governance Risk"].mean()
        }
        
        components_df = pd.DataFrame(list(avg_scores.items()), 
                                   columns=['Component', 'Average Score'])
        
        components_chart = alt.Chart(components_df).mark_bar(
            cornerRadiusTopLeft=3, 
            cornerRadiusTopRight=3,
            color='#4472C4'
        ).encode(
            x=alt.X('Component:N', title='ESG Component'),
            y=alt.Y('Average Score:Q', title='Average Risk Score'),
            tooltip=['Component:N', alt.Tooltip('Average Score:Q', format='.2f')]
        ).properties(
            title='Average ESG Component Scores',
            width=300,
            height=300
                            )
        st.altair_chart(components_chart, use_container_width=True)
    
    # Key insights
    st.markdown("### 🔍 Key Insights")
    
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        st.markdown("**Risk Level Breakdown:**")
        risk_summary = df["Total ESG Risk Level"].value_counts()
        for risk_level, count in risk_summary.items():
            percentage = (count / len(df)) * 100
            badge = render_risk_badge(risk_level)
            st.write(f"• {badge}: {count} companies ({percentage:.1f}%)")
    
    with insight_col2:
        st.markdown("**Average ESG:**")
        env_avg = df["Environmental Risk"].mean()
        soc_avg = df["Social Risk"].mean()
        gov_avg = df["Governance Risk"].mean()
        
        highest_risk = max([
            ("Environmental", env_avg),
            ("Social", soc_avg), 
            ("Governance", gov_avg)
        ], key=lambda x: x[1])
        
        st.write(f"• Highest average risk: **{highest_risk[0]}** ({highest_risk[1]:.1f})")
        st.write(f"• Environmental: {env_avg:.1f}")
        st.write(f"• Social: {soc_avg:.1f}")
        st.write(f"• Governance: {gov_avg:.1f}")
    
    if st.checkbox("Show companies with highest ESG risk", key="show_high_risk"):
        st.markdown("### ⚠️ Highest Risk Companies")
        top_risk = df.nlargest(5, "Total ESG Risk Score")[
            ["Ticker", "Total ESG Risk Score", "Total ESG Risk Level"]
        ]
        st.dataframe(top_risk, use_container_width=True, hide_index=True)

# Individual company details
selected_ticker = st.selectbox("Select a company ticker to view details:", options=df["Ticker"].tolist())

row = df[df["Ticker"] == selected_ticker].iloc[0]

st.subheader(f"Details for {selected_ticker}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total ESG Risk Score", row["Total ESG Risk Score"])
col1.markdown(f"**Risk Level:** {render_risk_badge(row['Total ESG Risk Level'])}")
col2.metric("Environmental Risk", row["Environmental Risk"])
col3.metric("Social Risk", row["Social Risk"])
col4.metric("Governance Risk", row["Governance Risk"])

st.markdown("### Product Involvement Areas")
involvement_df = pd.DataFrame(row["Involvement Areas"].items(), columns=["Product", "Involvement"])
st.table(involvement_df)

st.markdown("### Controversy")
st.write(f"Score: {row['Controversy Score'] if pd.notna(row['Controversy Score']) else 'N/A'}")
st.write(f"Category Average: {row['Controversy Category Average'] if pd.notna(row['Controversy Category Average']) else 'N/A'}")
