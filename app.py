import streamlit as st
from streamlit import session_state as sst
import pandas as pd
from datetime import datetime
from utils.process_github_data import *
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from utils.util import load_css, format_date_ddmmyyyy
from utils.fetch_github_data import *
from utils.streamlit_ui import base_ui, growth_stats
import os

color = "#26a641"

def main():
    base_ui()  # Base UI containing title, star button, and sidebar form

    ## Fetch username and token from Streamlit secrets
    sst.username = st.secrets["github"]["username"]  # Fetch GitHub username from Streamlit secrets
    TOKEN = st.secrets["github"]["token"]  # Fetch GitHub token from Streamlit secrets

    if sst.username and TOKEN and sst.button_pressed:
        # Fetch data
        cont_data = fetch_contribution_data(sst.username, TOKEN)
        user_data = fetch_user_data(sst.username, TOKEN)
        repo_data = fetch_repo_data(sst.username, TOKEN)

        if "errors" in cont_data or "errors" in user_data or "errors" in repo_data:
            st.error("Error fetching data. Check your username/token.")
        else:
            # Process data
            cont_stats = process_contribution_data(cont_data)
            user_stats = process_user_data(user_data)

            # --- User Stats Summary ---
            st.markdown("### User Summary")
            with st.container():
                user_info, user_stats_info = st.columns([1, 3], border=True, vertical_alignment="center")
                with user_info:
                    avatar_url = user_stats.get("avatar_url")
                    user_bio = user_stats.get("bio")
                    location = user_stats.get("location")
                    followers = user_stats.get("followers")
                    following = user_stats.get("following")
                    repositories = user_stats.get("repositories")
                    total_prs = user_stats.get("total_pullrequests")
                    total_issues = user_stats.get("total_issues")
                    created_at = datetime.strptime(user_stats.get("created_at"), "%Y-%m-%dT%H:%M:%SZ")
                    created_at = created_at.strftime("%Y-%m-%d")

                    custom_css = load_css()
                    st.markdown(f"""
                                <style>
                                {custom_css}
                                </style>
                                """, unsafe_allow_html=True)

                    st.markdown(f"""
                                <div class="user-container">
                                    <div class="user-card">
                                        <img src="{avatar_url}" alt="Avatar" class="avatar">
                                        <div class="username">{sst.username}</div>
                                        <div class="bio">{user_bio}</div>
                                        <div class="stats">
                                            <div class="stat">Location:<b> {location}</b></div>
                                            <div class="stat">Repos:<b> {repositories}</b></div>
                                            <div class="stat">Followers:<b> {followers}</b></div>
                                            <div class="stat">Following:<b> {following}</b></div>
                                            <div class="stat">PRs:<b> {total_prs}</b></div>
                                            <div class="stat">Issues:<b> {total_issues}</b></div>
                                        </div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                with user_stats_info:
                    # --- Summary Stats ---
                    total_contributions = cont_stats.get("total_contributions", 0)
                    public_contributions = cont_stats.get("public_contributions", 0)
                    private_contributions = cont_stats.get("private_contributions", 0)
                    highest_contribution = cont_stats.get("highest_contribution", 0)
                    highest_contribution_date = cont_stats.get("highest_contribution_date", None)
                    today_commits = cont_stats.get("today_commits", 0)
                    current_streak = cont_stats.get("current_streak", 0)
                    longest_streak = cont_stats.get("longest_streak", 0)
                    days = cont_stats.get("days", [])

                    # Validate contribution data
                    if public_contributions == 0 and private_contributions == 0:
                        st.warning("No contributions found. If you have private repositories, make sure your token has the 'repo' scope.")

                    # Calculate contributions based on toggle
                    display_total = public_contributions + private_contributions
                    if private_contributions == 0:
                        st.info("No private contributions found. If you have private repositories, verify your token permissions.")

                    # Display summary metrics
                    if today_commits > 0:
                        st.markdown(f"#### 🔥 Today: {today_commits} commits")
                    col1, col2, col3 = st.columns(3, border=True)
                    col1.metric(
                        "Total Contributions", 
                        value=f"{display_total:,} commits",
                        delta=f"Public: {public_contributions:,} | Private: {private_contributions:,}",
                        delta_color="off" if display_total == 0 else "normal"
                    )
                    col2.metric(
                        "Current Streak", 
                        value=f"{'☹️' if current_streak == 0 else '🔥'} {current_streak} days",
                        delta=f"Longest: {longest_streak} days",
                        delta_color="off" if current_streak == 0 else "normal"
                    )
                    col3.metric(
                        "Most Productive Day",
                        value=f"{highest_contribution} commits",
                        delta=f"{highest_contribution_date if highest_contribution > 0 else 'No activity found'}",
                        delta_color="normal"
                    )

                    # Days on GitHub & Active days
                    formatted_date = user_stats.get("formatted_date")
                    joined_since = user_stats.get("joined_since")
                    github_days = user_stats.get("github_days")
                    active_days = cont_stats.get("active_days")
                    less_than_2_months_old = user_stats.get("less_than_2_months_old")

                    col1, col2 = st.columns(2, border=True)
                    col1.metric(
                        label="Joined Github since",
                        value=formatted_date,
                        delta=joined_since,
                        delta_color="inverse" if less_than_2_months_old else "normal"
                    )

                    col2.metric(
                        label="Total days on GitHub",
                        value=f"{github_days} days",
                        delta=f"Active for: {active_days} days",
                        delta_color="off" if active_days < 7 else "normal"
                    )

            # Prepare data for visualizations
            if not days:
                st.warning("No contribution data available for visualizations.")
            else:
                dates = [datetime.strptime(day["date"], "%Y-%m-%d") for day in days]
                contributions = [day.get("contributionCount", 0) for day in days]

                # --- Contributions Over Time ---
                st.markdown("### Contributions Over Time")
                chart_data = pd.DataFrame({"Date": dates, "Contributions": contributions})
                st.line_chart(chart_data.set_index("Date"))

                # --- Yearly Growth ---
                st.markdown("### Yearly Growth")
                chart_data['Year'] = chart_data['Date'].dt.year
                yearly_contributions = chart_data.groupby('Year')['Contributions'].sum().round(1)
                st.bar_chart(yearly_contributions, color=color)

                # --- Weekday vs. Weekend Contributions ---
                st.markdown("### Weekday vs. Weekend Contributions")
                chart_data['IsWeekend'] = chart_data['Date'].dt.dayofweek >= 5
                weekend_data = chart_data.groupby('IsWeekend')['Contributions'].sum()
                st.bar_chart(weekend_data, color=color)

if __name__ == "__main__":
    main()
