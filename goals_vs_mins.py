import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(layout="wide")

st.write("# Player-Role Analysis")

st.write('\n')

st.write("In soccer, teams strategically field players in various positions to maximize their performance on the field. Each player's position determines their role during a game, impacting the amount of time they spend on the pitch and their goal-scoring responsibilities.\n\nThis diverse array of positions and player roles contributes to the dynamic and multifaceted nature of the game, allowing teams to balance defense, midfield control, and attacking prowess for a winning strategy.")

st.markdown("""
* **Chart 1** : *Minutes Played vs Goals Scored for each Distinct Role*
* **Chart 2** : *Clearer Examination of Minutes Played*
* **Chart 3** : *Clearer Examination of Goals Scored*
* **Chart 4** : *Goal-Scoring Frequency*
    * *Larger values indicate less frequent scoring*
    * *Smaller values indicate more frequent scoring*
""")

st.write("Utilize the click-and-drag interactivity on **Chart 1** to filter the player roles to the ones you wish to examine.")

st.write('## Overview of Goals Scored and Minutes Played')
st.write('##### *Grouped by Player Role*')
st.write('\n')

playerank = pd.read_csv('playerank.csv')
#playerank

playerank_grouping = playerank.groupby('roleCluster').agg({'goalScored': 'sum', 'minutesPlayed': 'sum'}).reset_index()
playerank_grouping['minutes_per_goal'] = round(playerank_grouping['minutesPlayed'] / playerank_grouping['goalScored'], 1)
playerank_grouping['minutes_per_goal'] = playerank_grouping['minutes_per_goal'].replace([float('inf')], 0)

#playerank_grouping

# creating a tri-plot viz that gives a little more clarity on the goals scored by each player role
# and the goals per minutes ratio

# same click and drag interactivity
selection = alt.selection_interval()

# intial dot plot
dot_plot = alt.Chart(playerank_grouping).mark_circle(size=100).encode(
    x = alt.X('goalScored', title='Number of Goals Scored'),
    y = alt.Y('minutesPlayed', title='Minutes Played'),
    color = alt.Color('roleCluster:N', legend=alt.Legend(title='Player Roles')),
    tooltip = ['roleCluster:N', 'goalScored:Q', 'minutesPlayed:Q']
).add_params(selection).properties(height = 520, width = 400)


# histogram of goals scored per player role
bar_1 = alt.Chart(playerank_grouping).mark_bar().encode(
    x = alt.X('goalScored', title='Goals Scored'),
    y = alt.Y('roleCluster', title='Player Roles'),
    color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
    tooltip = ['goalScored:Q']
).transform_filter(selection).properties(width = 300)

bar_2 = alt.Chart(playerank_grouping).mark_bar().encode(
    x = alt.X('minutesPlayed', title='Minutes Played'),
    y = alt.Y('roleCluster', title='Player Roles'),
    color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
    tooltip = ['minutesPlayed:Q']
).transform_filter(selection).properties(width = 300)

# ratio of minutes per goal per player role
bar_3 = alt.Chart(playerank_grouping).mark_bar().encode(
    x = alt.X('minutes_per_goal', title='Ratio of Minutes Per Goal'),
    y = alt.Y('roleCluster', title='Player Roles'),
    color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
    tooltip = ['minutes_per_goal:Q']
).transform_filter(selection).properties(width = 300)


# combining all 3 plots
combined_plot_2 = alt.hconcat(dot_plot, bar_2, bar_1, bar_3)

combined_plot_2