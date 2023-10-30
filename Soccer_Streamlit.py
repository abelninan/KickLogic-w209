#!/usr/bin/env python
# coding: utf-8

# In[2]:


import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

# Function to load data
@st.cache_data  # This function will be cached
def load_data(path):
    data = pd.read_csv(path)
    return data

# Main function for Streamlit app
def main1():
    # Load the data
    data_path = 'actions_sample.csv'  # Update path if needed
    data = load_data(data_path)

    # Sidebar - Game selection
    st.sidebar.header('Game Selection')
    sorted_unique_games = sorted(data['game_id'].unique())
    selected_game = st.sidebar.selectbox('Choose a game', sorted_unique_games)

    # Filter data based on selection
    game_data = data[data['game_id'] == selected_game]

    # Display game statistics
    st.header('Game Statistics')
    display_game_statistics(game_data)
    
    # Team selection toggle for pass map
    st.header('Passing Map')
    teams = game_data['team_id'].unique()
    if len(teams) > 1:  # Ensure there are at least two teams
        selected_team = st.radio('Choose a team to view passes', options=teams)

        # Create a passing map for the selected team
        passing_map_chart = create_passing_map(game_data, selected_team)
        st.altair_chart(passing_map_chart, use_container_width=True)
    else:
        st.write("Not enough teams to toggle between.")
        
    # Team selection toggle for shot map
    st.header('Shot Map')
    if len(teams) > 1:
        selected_team_shots = st.radio('Choose a team to view shots', options=teams, key='team_selection_shots')

        # Create a shot map for the selected team
        shot_map_chart = create_shot_map(game_data, selected_team_shots)
        st.altair_chart(shot_map_chart, use_container_width=True)
    else:
        st.write("Not enough teams to toggle between for shots.")
        
    # Calculate and display momentum
    st.header('Momentum')
    momentum_chart = calculate_momentum(game_data)
    st.altair_chart(momentum_chart, use_container_width=True)


# Function to create a passing map
def create_passing_map(game_data, selected_team):
    # Filter for 'pass' actions for the selected team
    pass_actions = game_data[(game_data['type_name'] == 'pass') & (game_data['team_id'] == selected_team)]

    # Determine if the pass was successful
    pass_actions['pass_outcome'] = pass_actions['result_name'].apply(lambda x: 'success' if x == 'success' else 'fail')

    # Define field dimensions; you might adjust these based on the coordinate system in your data
    # Store as variables we can easily reuse for the plots
    field_length_min =  0.0
    field_length_max = 105.0
    field_width_min = 0.0
    field_width_max = 68.0

    # Altair chart for passes, showing start and end points with colors indicating pass success, adjusted for field dimensions
    pass_chart = alt.Chart(pass_actions).mark_line().encode(
        x=alt.X('start_x:Q', scale=alt.Scale(domain=(field_length_min, field_length_max)), title='Start X'),
        y=alt.Y('start_y:Q', scale=alt.Scale(domain=(field_width_min, field_width_max)), title='Start Y'),
        x2='end_x:Q',
        y2='end_y:Q',
        color=alt.condition(
            alt.datum.pass_outcome == 'success',
            alt.value('green'),  # The pass was successful
            alt.value('red')     # The pass was not successful
        ),
        tooltip=['start_x', 'start_y', 'end_x', 'end_y', 'pass_outcome']
    ).properties(
        title='Pass Start and End Points',
        width=700,
        height=400  # Keeping the aspect ratio of the field in mind
    )

    return pass_chart

def create_shot_map(game_data, selected_team):
    shot_data = game_data[(game_data['type_name'] == 'shot') & (game_data['team_id'] == selected_team)]

    field_length_min =  0.0
    field_length_max = 105.0
    field_width_min = 0.0
    field_width_max = 68.0
    
    # Create points for shots
    shots = alt.Chart(shot_data).mark_point(filled=True).encode(
        x=alt.X('start_x', scale=alt.Scale(domain=(0, field_length_max))),
        y=alt.Y('start_y', scale=alt.Scale(domain=(0, field_width_max))),
        color='result_name:N',
        tooltip=['start_x', 'start_y', 'result_name']
    ).properties(
        width=700,
        height=400
    )

    return shots

def calculate_momentum(game_data):
    # Convert time from seconds to minutes for easier processing
    game_data['time_minutes'] = game_data['time_seconds'] // 60

    # Define action weights
    action_weights = {"pass": 1, "shot": 2}

    # Filter for relevant actions
    relevant_actions = game_data[game_data['type_name'].isin(action_weights.keys())]

    # Avoid SettingWithCopyWarning by creating a new DataFrame instead of modifying a slice
    relevant_actions_fixed = relevant_actions.copy()
    relevant_actions_fixed['action_weight'] = relevant_actions_fixed['type_name'].apply(lambda x: action_weights[x])

    # Group the data by game, minute, and team to count weighted actions and calculate the average x-coordinate
    weighted_grouped_data = relevant_actions_fixed.groupby(['game_id', 'time_minutes', 'team_id']).agg(
        weighted_actions=pd.NamedAgg(column='action_weight', aggfunc='sum'),
        avg_start_x=pd.NamedAgg(column='start_x', aggfunc='mean')
    ).reset_index()

    # Calculate momentum
    weighted_grouped_data['momentum'] = ((weighted_grouped_data['avg_start_x'] - 50) / 50) * weighted_grouped_data['weighted_actions']

    # Dynamically determine the teams based on the data
    teams = weighted_grouped_data['team_id'].unique()
    if len(teams) != 2:
        print("Error: There are not exactly two teams in the game data.")
        return None

    team_1_id, team_2_id = teams[0], teams[1]

    # Adjust momentum calculation considering the team identity.
    weighted_grouped_data['momentum'] = weighted_grouped_data.apply(
        lambda row: row['momentum'] if row['team_id'] == team_1_id else -row['momentum'], axis=1
    )

    # Create a DataFrame for momentum difference per minute
    momentum_per_minute = weighted_grouped_data.groupby('time_minutes')['momentum'].sum().reset_index()

    # Normalize the momentum values to be between -1 and 1
    max_momentum = momentum_per_minute['momentum'].abs().max()
    momentum_per_minute['momentum'] = momentum_per_minute['momentum'].apply(lambda x: x / max_momentum)

    st.write(momentum_per_minute)
    
    color_condition = alt.condition(
    'datum.momentum > 0',  # If this condition is true, use the first color; otherwise, use the second color.
    alt.value('green'),    # The color to use if the condition is true (momentum is positive)
    alt.value('red')       # The color to use if the condition is false (momentum is non-positive)
    )

    # Create the chart
    area_chart = alt.Chart(momentum_per_minute).mark_area(
        line={'color': 'black'},  # neutral color for the line
    ).encode(
        x=alt.X('time_minutes:Q', title='Game Time (Minutes)'),  # Define the x-axis
        y=alt.Y('momentum:Q', title='Momentum', scale=alt.Scale(domain=(-1, 1))),  # Define the y-axis
        color=alt.condition(
            'datum.momentum > 0',  # condition based on the momentum
            alt.value('green'),    # color when condition is true
            alt.value('red')       # color when condition is false
        ),
        tooltip=[alt.Tooltip('time_minutes:Q', title='Minute'), alt.Tooltip('momentum:Q', title='Momentum')]
    ).properties(
        title='Momentum Over Time',
        width=600,  # Width of the chart
        height=400  # Height of the chart
    )

    return area_chart

def display_game_statistics(game_data):
    # Ensure there are two teams
    teams = game_data['team_id'].unique()
    if len(teams) != 2:
        st.write("Error: There were not exactly two teams in the selected game data.")
        return

    # Define statistics to display
    statistics = ['shot', 'pass']  # Add more action types if needed

    # Initialize a container for data
    all_stats = []

    # Get counts for each statistic and each team, and store it in a list of dictionaries
    for stat in statistics:
        actions = game_data[game_data['type_name'] == stat]

        # Here, we're renaming the index before resetting it
        action_counts = actions['team_id'].value_counts().rename('counts')
        action_counts.index.name = 'team'  # Setting the name of the index
        action_counts = action_counts.reset_index()

        for index, row in action_counts.iterrows():
            # Now, 'team' is the actual column name, and you can access it directly
            all_stats.append({'team': row['team'], 'statistic': stat, 'counts': row['counts']})

    # Convert the list of dictionaries to a DataFrame
    stats_df = pd.DataFrame(all_stats)

    # Create a stacked bar chart
#     stacked_bar = alt.Chart(stats_df).mark_bar().encode(
#         y=alt.Y('statistic:N', title='Statistic'),  # Y-axis will show the statistic
#         x=alt.X('counts:Q', title='Count'),  # X-axis represents the count of each statistic
#         color='team:N',  # Color by team
#         order=alt.Order(  # This will ensure the stacking order is consistent
#             'team:N',
#             sort='ascending'
#         ),
#         tooltip=['team:N', 'statistic:N', 'counts:Q']
#     ).properties(
#         title='Team Statistics Comparison',
#         width=300,
#         height=200  # You can adjust the dimensions
#     )

#     st.altair_chart(stacked_bar, use_container_width=True)
    st.write(stats_df)
    

def main2():
    #st.set_page_config(layout="wide")

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

def main():
    st.title('KickLogic - Soccer Analysis Dashboard - 209')
    app_choice = st.selectbox('Choose your analysis type:', ['Player', 'Match ', 'Player Valuation', 'Club'])
    if app_choice == 'Player':
        main2()
    elif app_choice == 'Match':
        main1()

if __name__ == '__main__':
    main()


