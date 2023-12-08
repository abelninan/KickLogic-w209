#!/usr/bin/env python
# coding: utf-8

# In[2]:
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import math


# Function to load data
@st.cache_data  # This function will be cached
def load_data(path):
    data = pd.read_csv(path)
    return data

# Main function for Streamlit app
def main1():

    st.write("# Match Analysis")

    st.write('\n')

    st.write("In a 90 minute soccer match, thousands of 'actions' occur. These include things like passes, shots, fouls, saves, dribbles, among others. For each of these, there are successful and unsuccessful outcomes. A successful shot could be a goal while a failed pass would be a turnover. We would hypothesize that certain things like position on field and distance of the attempt (long vs short pass) would have different success rates. Like an sport, there are also eb and flows of a competition, we wanted to create a view to get a high level understanding of what occured in the match.")

    st.markdown("""
    * **Chart 1** : *Match Summary Metrics*
    * **Chart 2** : *Pass Maps*
    * **Chart 3** : *Shot Maps*
    * **Chart 4** : *Momentum*
        * *Positive momentum implies team 1 had the advantage in play at that time*
        * *Negative momentum implies team 2 had the advantage in play at that time*
    """)

    # Load the data
    data_path = 'enriched_actions_prem.csv'  # Update path if needed
    data = load_data(data_path)
    match_data_path = 'match_details.csv'  # Update path if needed
    match_data = load_data(match_data_path)

    # Sidebar - Game selection
    st.sidebar.header('Game Selection')
    sorted_unique_teams = sorted(match_data['team_1'].unique())
    team_1 = st.sidebar.selectbox('Choose Team 1', sorted_unique_teams)
    filtered_team2 = match_data[match_data['team_1'] == team_1]
    sorted_unique_opponents = sorted(filtered_team2['team_2'].unique())
    team_2 = st.sidebar.selectbox('Choose Team 2', sorted_unique_opponents)
    
    # Get a sorted list of match dates where team_1 played against team_2
    filtered_matches = match_data[(match_data['team_1'] == team_1) & (match_data['team_2'] == team_2)]
    sorted_match_dates = sorted(filtered_matches['game_date'].unique())
    match_date = st.sidebar.selectbox('Choose Match Date', sorted_match_dates)
    
    # Get the game_id for the selected match
    selected_game = filtered_matches[filtered_matches['game_date'] == match_date]['game_id'].iloc[0]
    
    # Filter data based on selection
    game_data = data[data['game_id'] == selected_game]


    # Display game statistics
    st.header('Game Statistics')
    display_game_statistics(game_data)
    
    # Team selection toggle for pass map
    st.header('Passing Map')
    teams = [team_1,team_2]
    if len(teams) > 1:  # Ensure there are at least two teams
        selected_team = st.radio('Choose a team to view passes', options=teams)
        selected_team_data = game_data[game_data['team_name'] == selected_team]
        selected_team_id = selected_team_data.iloc[0]['team_id']
        # Get list of players from the selected team
        players = selected_team_data['player_name'].dropna().unique()

        # Extract last names from player names
        last_names = [name.split('. ')[-1] for name in players]
        
        # Sort players based on last names
        sorted_players = [name for _, name in sorted(zip(last_names, players))]
        
        # Add an option to select all players
        sorted_players = np.insert(sorted_players, 0, 'All Players')
        players_display = [name.encode('utf-8').decode('unicode_escape') for name in sorted_players]

                
        # Allow user to select a player from the team
        selected_player = st.selectbox('Select a player (optional)', players_display)
    
        # Filter data based on selected player if a specific player is chosen
        if selected_player != 'All Players':
            selected_team_data = selected_team_data[selected_team_data['player_name'] == selected_player]
        # Create a passing map for the selected team
        passing_map_chart = create_passing_map(selected_team_data, selected_team_id)
        st.altair_chart(passing_map_chart, use_container_width=True)
    
    else:
        st.write("Not enough teams to toggle between.")
        
    # Team selection toggle for shot map
    st.header('Shot Map')
    if len(teams) > 1:
        selected_team_shots = st.radio('Choose a team to view shots', options=teams, key='team_selection_shots')
        selected_team_shots_data = game_data[game_data['team_name'] == selected_team_shots]
        selected_team_shots_id = selected_team_shots_data.iloc[0]['team_id']
        # Create a shot map for the selected team
        shot_map_chart = create_shot_map(game_data, selected_team_shots_id)
        st.altair_chart(shot_map_chart, use_container_width=True)
    else:
        st.write("Not enough teams to toggle between for shots.")
        
    # Calculate and display momentum
    st.header('Match Momentum')
    st.write('By analyzing pass and shot actions as well as the position on the field that they occured, we can understand who was controlling the match at a given time period. ')
    momentum_chart2 = create_momentum_chart(calc_game_momentum(game_data,selected_game))
    st.altair_chart(momentum_chart2, use_container_width=True)


# Function to create a passing map
def calculate_angle(row):
    start_x, start_y = row['start_x'], row['start_y']
    end_x, end_y = row['end_x'], row['end_y']

    # Calculate the angle in radians
    angle_rad = math.atan2(end_y - start_y, end_x - start_x)

    # Ensure the angle is between 0 and 2*pi
    angle_rad = (angle_rad + 2 * math.pi) % (2 * math.pi)

    # Convert the angle to degrees
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg

# Function to create a passing map
def create_passing_map(game_data, selected_team):
    # Filter for 'pass' actions for the selected team
    pass_actions = game_data[(game_data['type_name'] == 'pass') & (game_data['team_id'] == selected_team)]

    # Determine if the pass was successful
    pass_actions['pass_outcome'] = pass_actions['result_name'].apply(lambda x: 'success' if x == 'success' else 'fail')
    pass_actions['angle'] = pass_actions.apply(calculate_angle, axis=1)
    #st.write(pass_actions.head(50))
    # Define field dimensions; you might adjust these based on the coordinate system in your data
    # Store as variables we can easily reuse for the plots
    field_length_min =  0.0
    field_length_max = 105.0
    field_width_min = 0.0
    field_width_max = 68.0

    # Create the base line chart with varying line width for direction
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
        tooltip=['start_x', 'start_y', 'end_x', 'end_y', 'pass_outcome', 'player_name']
    ).properties(
        title='Pass Start and End Points',
        width=700,
        height=400  # Keeping the aspect ratio of the field in mind
    )

    # # Adding arrows to the end of each line
    # # Arrow chart for indicating direction
    # arrow_chart = alt.Chart(pass_actions).mark_point(
    #     shape='arrow', 
    #     filled=True,
    #     size=100  # Adjust size as needed
    # ).encode(
    #     x='end_x:Q',
    #     y='end_y:Q',
    #     angle=alt.Angle('angle', scale=alt.Scale(domain=[0, 360])),
    #     color=alt.condition(
    #         alt.datum.pass_outcome == 'success',
    #         alt.value('green'),  # The pass was successful
    #         alt.value('red')     # The pass was not successful
    #     ),
    #     tooltip=['start_x', 'start_y', 'end_x', 'end_y', 'angle', 'pass_outcome']  # Adding start_x and start_y to tooltip
    # )

    arrow_chart = alt.Chart(pass_actions).mark_point(
    shape='arrow',
    filled=True,
    size=100,  # Adjust size as needed
).encode(
    x='end_x:Q',
    y='end_y:Q',
    theta=alt.Theta('angle', title='Direction'),  # Specify the direction using the angle
    color=alt.condition(
        alt.datum.pass_outcome == 'success',
        alt.value('green'),  # The pass was successful
        alt.value('red')     # The pass was not successful
    ),
    tooltip=['start_x', 'start_y', 'end_x', 'end_y', 'angle', 'pass_outcome']  # Adding start_x and start_y to tooltip
)
    # Combine the line chart and the arrow chart
    combined_chart = pass_chart + arrow_chart
    combined_chart = combined_chart.properties(
        title='Pass Start and End Points',
        width=700,
        height=400
    )

    return combined_chart

def create_shot_map(game_data, selected_team):
    shot_data = game_data[(game_data['type_name'] == 'shot') & (game_data['team_id'] == selected_team)]

    field_length_min =  0.0
    field_length_max = 105.0
    field_width_min = 0.0
    field_width_max = 68.0
    
    minimum_point_size = 50  

    # Create points for shots
    shots = alt.Chart(shot_data).mark_point(filled=True).encode(
    x=alt.X('start_x', scale=alt.Scale(domain=(0, field_length_max))),
    y=alt.Y('start_y', scale=alt.Scale(domain=(0, field_width_max))),
    color='result_name:N',
    size=alt.Size('result_name:N', 
                  scale=alt.Scale(range=[minimum_point_size, 2 * minimum_point_size]), 
                  legend=None),
    tooltip=['player_name', 'time_minutes', 'start_x', 'start_y',  'result_name']
    ).properties(
        width=700,
        height=400
    )

    return shots

def calc_action_weight(result_name, type_name):

    action_weights = {
        "success" : {"pass": 1, "shot": 5},
        "fail" : {"pass": -1, "shot": 1}
    }
    try:
      weight = action_weights[result_name][type_name]
    except:
      weight = 0
    return weight


def calc_game_momentum(game_data, game_id, perspective_team_id = 0, weight_span = 3):

    # Convert time from seconds to minutes for easier processing
    game_data['time_minutes'] = game_data['time_seconds'] // 60 + 45 * (game_data['period_id'] -1)

    # Define action weights
    action_weights = {"pass": 1, "shot": 2}

    # Filter for relevant actions
    relevant_actions = game_data[game_data['type_name'].isin(action_weights.keys())]

    # Avoid SettingWithCopyWarning by creating a new DataFrame instead of modifying a slice
    relevant_actions_fixed = relevant_actions.copy()
    relevant_actions_fixed['action_weight'] = relevant_actions_fixed.apply(lambda x: calc_action_weight(x.result_name, x.type_name), axis=1)

    # Group the data by game, minute, and team to count weighted actions and calculate the average x-coordinate
    weighted_grouped_data = relevant_actions_fixed.groupby(['game_id', 'time_minutes', 'team_name']).agg(
        weighted_actions=pd.NamedAgg(column='action_weight', aggfunc='sum'),
        avg_start_x=pd.NamedAgg(column='start_x', aggfunc='mean')
    ).reset_index()

    # # Calculate momentum
    weighted_grouped_data['momentum'] = ((weighted_grouped_data['avg_start_x'] - 50) / 50) * weighted_grouped_data['weighted_actions']

    # # Dynamically determine the teams based on the data
    teams = weighted_grouped_data['team_name'].unique()
    if len(teams) != 2:
        print("Error: There are not exactly two teams in the game data.")
        return None

    if perspective_team_id == 0:
        team_1_id, team_2_id = teams[0], teams[1]
    else:
        team_1_id = perspective_team_id
        team_2_id = np.setdiff1d(weighted_grouped_data['team_name'].unique(), perspective_team_id)[0]

    # weighted average by teamId
    team1_df = weighted_grouped_data[weighted_grouped_data['team_name'] == team_1_id]
    team2_df = weighted_grouped_data[weighted_grouped_data['team_name'] == team_2_id]
    team1_df['weighted_avg_momentum'] = team1_df.iloc[:,5].ewm(span=weight_span).mean()
    team2_df['weighted_avg_momentum'] = -1 * team2_df.iloc[:,5].ewm(span=weight_span).mean()
    team2_df['momentum'] = -1 * team2_df['momentum']

    # # Adjust momentum calculation considering the team identity.
    weighted_grouped_data = pd.concat([team1_df, team2_df])

    # # Create a DataFrame for momentum difference per minute
    momentum_per_minute = weighted_grouped_data.groupby('time_minutes')[['momentum', 'weighted_avg_momentum']].sum().reset_index()

    # # Normalize the momentum values to be between -1 and 1
    max_momentum = momentum_per_minute['momentum'].abs().max()
    momentum_per_minute['momentum'] = momentum_per_minute['momentum'].apply(lambda x: x / max_momentum)
    momentum_per_minute['weighted_avg_momentum'] = momentum_per_minute['weighted_avg_momentum'].apply(lambda x: x / max_momentum)

    # Assign 'Team 1' or 'Team 2' based on the sign of the momentum
    momentum_per_minute['team'] = momentum_per_minute['momentum'].apply(
        lambda x: team_1_id if x >= 0 else team_2_id
    )
    
    return momentum_per_minute

def create_momentum_chart(game_momentum_df):
    game_momentum_df['pos_momentum'] = game_momentum_df['momentum'].apply(lambda x: max(x, 0))
    game_momentum_df['neg_momentum'] = game_momentum_df['momentum'].apply(lambda x: min(x, 0))

    posChart = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("pos_momentum", scale=alt.Scale(domain=[-1, 1])),
        tooltip=["time_minutes", "pos_momentum", "team"]  # Added team to tooltip

    )

    negChart = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("neg_momentum", scale=alt.Scale(domain=[-1, 1])),
        fill = alt.value("red"),
        tooltip=["time_minutes", "neg_momentum", "team"]  # Added team to tooltip
    )

    game_momentum_df['pos_momentum_weighted'] = game_momentum_df['weighted_avg_momentum'].apply(lambda x: max(x, 0))
    game_momentum_df['neg_momentum_weighted'] = game_momentum_df['weighted_avg_momentum'].apply(lambda x: min(x, 0))

    posChart_w = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("pos_momentum_weighted", title = "Momentum", scale=alt.Scale(domain=[-1, 1])),
        #tooltip=["time_minutes", "pos_momentum_weighted", "team"]  # Added team to tooltip
        fill=alt.ColorValue('#0068c9')

    )

    negChart_w = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("neg_momentum_weighted", title = "Momentum", scale=alt.Scale(domain=[-1, 1])),
        #tooltip=["time_minutes", "neg_momentum_weighted", "team"],
        fill = alt.ColorValue('#83c9ff')
    )

    # Calculate the midpoint of the time range
    midpoint = game_momentum_df['time_minutes'].max() / 2
    
    # Extract the team names
    team1_name = game_momentum_df[game_momentum_df['momentum'] >= 0]['team'].iloc[0]  # Assuming positive momentum indicates Team 1
    team2_name = game_momentum_df[game_momentum_df['momentum'] < 0]['team'].iloc[0]   # Assuming negative momentum indicates Team 2
    
    
    # Text chart for Team 1 (positioned towards the top)
    textChart_team1 = alt.Chart(pd.DataFrame({'time_minutes': [midpoint], 'pos': [0.8]})).mark_text(
        align='center', baseline='middle'
    ).encode(
        x=alt.X('time_minutes:Q', axis=alt.Axis(title="Game Time (Minutes)")),
        y='pos:Q',
        text=alt.value(team1_name)  # Using the actual name of Team 1
    )
    
    # Text chart for Team 2 (positioned towards the bottom)
    textChart_team2 = alt.Chart(pd.DataFrame({'time_minutes': [midpoint], 'neg': [-0.8]})).mark_text(
        align='center', baseline='middle'
    ).encode(
        x=alt.X('time_minutes:Q', axis=alt.Axis(title="Game Time (Minutes)")),
        y='neg:Q',
        text=alt.value(team2_name)  # Using the actual name of Team 2
    )

    return posChart_w + negChart_w + textChart_team1 + textChart_team2

def display_game_statistics(game_data):
    # Ensure there are two teams
    teams = game_data['team_name'].unique()
    if len(teams) != 2:
        st.write("Error: There were not exactly two teams in the selected game data.")
        return
    
    # Aggregating action counts for each team
    # Defining the actions of interest and their respective conditions
    actions_conditions = {
        'dribble': (game_data['type_name'] == 'dribble'),
        'pass': (game_data['type_name'] == 'pass'),
        'shot': (game_data['type_name'] == 'shot'),
        'save': (game_data['type_name'] == 'save'),
        'successful pass': ((game_data['type_name'] == 'pass') & (game_data['result_name'] == 'success')),
        'goal': ((game_data['type_name'] == 'shot') & (game_data['result_name'] == 'success'))
    }
    
    # Aggregating counts for each action
    aggregated_data = pd.DataFrame()
    for action_name, condition in actions_conditions.items():
        action_data = game_data[condition].groupby('team_name').size().reset_index(name='Count')
        action_data['type_name'] = action_name
        aggregated_data = pd.concat([aggregated_data, action_data])
    
    # Pivoting the data for visualization
    pivot_data = aggregated_data.pivot(index='type_name', columns='team_name', values='Count').reset_index()
    pivot_data.columns.name = None
    
    # Renaming the columns to match the sample data structure
    team_names = pivot_data.columns[1:]
    pivot_data.rename(columns={team_names[0]: team_names[0], team_names[1]: team_names[1]}, inplace=True)
    
    # Melt the DataFrame to prepare the data
    df_melted = pivot_data.melt(id_vars='type_name', var_name='Team', value_name='Count')
    
    # Calculate percentages
    total_counts = df_melted.groupby('type_name')['Count'].transform('sum')
    df_melted['Percentage'] = df_melted['Count'] / total_counts * 100

    # Create the base chart
    base = alt.Chart(df_melted).encode(
        y=alt.Y('type_name:N', axis=alt.Axis(title='', labels=True), sort=df_melted['type_name'].unique().tolist()),
        x=alt.X('sum(Percentage):Q', axis=alt.Axis(title='Percentage'), scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('Team:N', legend=alt.Legend(title="Team", orient = 'top')),
        order=alt.Order('Team:N', sort='ascending')
    )
    
    # Create the bar chart with labels
    bars = base.mark_bar().encode(
        tooltip=['type_name:N', 'Team:N', 'Percentage:Q']
    )
     
    # Create labels using mark_text
    labels = base.mark_text(
        #align=alt.condition(alt.datum['Team'] == team_names[0], alt.value('right'), alt.value('left')),
        align = 'center',
        baseline='middle',  # Center the text vertically within the bars
        dx = 0,
        dy=0  # No vertical displacement
    ).encode(
        text=alt.Text('Count:Q', format=','),
        color=alt.value('white'),  # Set the text content color to white
        x='sum(Percentage):Q',  # Position the text at the starting point of the bars
)


   # Create labels for each team
    labels_team1 = base.transform_filter(alt.datum['Team'] == teams[0]).mark_text(
        align='left',
        baseline='middle',
        dx=5,
    ).encode(
        text=alt.Text('Count:Q', format=','),
        color=alt.value('white'),
        x=alt.value(0),  # Set x to 0 for Team 1
    )
    
    labels_team2 = base.transform_filter(alt.datum['Team'] == teams[1]).mark_text(
        align='right',
        baseline='middle',
        dx=200,
    ).encode(
        text=alt.Text('Count:Q', format=','),
        color=alt.value('white'),
        x=alt.value(100),  # Set x to 100 for Team 2
    )
    
    # Layer the bar chart with text
    chart = (bars + labels_team1 + labels_team2).properties(width=400, height=350)

    

    # Layer the bar chart with text
    #chart = (bars + labels).properties(width=600, height=200)
    
    

    
    
    # Layer the bar chart with text
    #chart = bars.properties(width=600, height=200)
    #st.altair_chart(bars.properties(width=600, height=200))

    # Display the chart
    chart
    

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

    playerank_grouping = playerank_grouping[playerank_grouping['minutesPlayed'] >= 100000]

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
    ).transform_filter(selection).properties(width = 400, title='Clearer Examination of Goals Scored')

    bar_2 = alt.Chart(playerank_grouping).mark_bar().encode(
        x = alt.X('minutesPlayed', title='Minutes Played'),
        y = alt.Y('roleCluster', title='Player Roles'),
        color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
        tooltip = ['minutesPlayed:Q']
    ).transform_filter(selection).properties(width = 400, title='Clearer Examination of Minutes Played')

    # ratio of minutes per goal per player role
    bar_3 = alt.Chart(playerank_grouping).mark_bar().encode(
        x = alt.X('minutes_per_goal', title='Ratio of Minutes Per Goal'),
        y = alt.Y('roleCluster', title='Player Roles'),
        color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
        tooltip = ['minutes_per_goal:Q']
    ).transform_filter(selection).properties(width = 400, title='Goal-Scoring Frequency (Larger Values Indicate Less Frequent Scoring)')

    # combining all 3 plots
    combined_plot_2 = alt.vconcat(dot_plot, bar_2, bar_1, bar_3)

    combined_plot_2

    st.write('## Advanced Player Metrics')

    role_stats_2 = load_data('streamlit_stats_2.csv')
    
    clean_positions = sorted(role_stats_2['clean_position'].unique())
    position_choice = st.selectbox('Choose a Player Position:', clean_positions)
    st.write('\n')
    #st.dataframe(role_stats_2)
    
    for position in clean_positions:
        if position_choice == position:
            
            #st.metric(label="Avg Overall", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'potential'].values[0])
            st.write('##### *Monetary Value of This Position*')
            col1, col2 = st.columns(2)
            total_value = '€ {:,.0f}'.format(role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'value_eur'].values[0])
            col1.metric(label="Total Value of Players (Euros)", value=total_value)
            avg_wage = '€ {:,.2f}'.format(role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'wage_eur'].values[0])
            col2.metric(label="Average Wage Per Player Per Game (Euros)", value=avg_wage)
            
            st.write('\n')
            st.write('##### *Athletic Characteristics of This Position*')
            col4, col5, col6 = st.columns(3)
            col4.metric(label="Pace", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'pace'].values[0])
            col5.metric(label="Shooting", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'shooting'].values[0])
            col6.metric(label="Passing", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'passing'].values[0])
            
            col7, col8, col9 = st.columns(3)
            col7.metric(label="Dribbling", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'dribbling'].values[0])
            col8.metric(label="Defending", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'defending'].values[0])
            col9.metric(label="Physic", value=role_stats_2.loc[role_stats_2['clean_position'] == position_choice, 'physic'].values[0])


def create_momentum_comparison_chart(game_momentum_df, team_ids = [674]):

    these_teams_momentum = game_momentum_df[game_momentum_df['team_id'].isin(team_ids)]

    chart = alt.Chart(these_teams_momentum).mark_line().encode(
        x=alt.X("time_minutes", title="Minute"),
        y=alt.Y("weighted_avg_momentum:Q", title="Momentum", scale=alt.Scale(domain=[-.25, .25])),
        color=alt.Color("name:N", title="Team")
    ).configure_mark(opacity=0.75).interactive()

    return chart

def make_team_comparison_bar_chart(team_metrics_df, metric, multi, height=200):
    base_bar = alt.Chart(team_metrics_df, title=metric).mark_bar().encode(
      x="name:N",
      color= "name:N",
      y= alt.Y(metric, axis=alt.Axis(title=None)),
    ).transform_filter(multi).properties(height=height)
    text= base_bar.mark_text(angle = 270, align="center", yOffset=50, fontWeight="bold").encode(text="name:N", color=alt.ColorValue("black"))
    return (base_bar + text)

def create_team_comparison_charts(team_metrics_df, team_metrics, league = 'All'):
    # Europe: center = [-20, 47], scale = 1400
    # France: center = [-20, 47], scale = 3000)
    # England: center = [-22, 52], scale = 4200)
    # Germany: center = [-10, 52], scale = 3700)
    # Spain: center = [-25, 40], scale = 3200)
    # Italy: center = [-8, 42], scale = 3200)
    if league == 'England':
      subset_metrics_df = team_metrics_df[team_metrics_df['Country'] == 'England']
      center = [-22, 52]
      scale = 4200
    elif league == 'France':
      subset_metrics_df = team_metrics_df[team_metrics_df['Country'].isin(['France','Monaco'])]
      center = [-20, 47]
      scale = 3000
    elif league == 'Germany':
      subset_metrics_df = team_metrics_df[team_metrics_df['Country'] == 'Germany']
      center = [-10, 52]
      scale = 3700
    elif league == 'Spain':
      subset_metrics_df = team_metrics_df[team_metrics_df['Country'] == 'Spain']
      center = [-25, 40]
      scale = 3200
    elif league == 'Italy':
      subset_metrics_df = team_metrics_df[team_metrics_df['Country'] == 'Italy']
      center = [-8, 42]
      scale = 3200    
    else:
      subset_metrics_df = team_metrics_df
      center = [-20, 47]
      scale = 1400 
    
    sphere = alt.sphere()
    graticule = alt.graticule(step=[10, 10])
    # lats = alt.sequence(start=-30, stop=71, step=10, as_='lats')
    # lons = alt.sequence(start=-90, stop=91, step=10, as_='lons')

    width = 800
    height = 600

    # Source of land data
    source = alt.topo_feature('https://cdn.jsdelivr.net/npm/vega-datasets@v1.29.0/data/world-110m.json', 'countries')

    # Layering and configuring the components
    base = alt.layer(
        alt.Chart(sphere).mark_geoshape(fill='none'),
        alt.Chart(graticule).mark_geoshape(stroke='gray', strokeWidth=0.5),
        alt.Chart(source).mark_geoshape(fill='lightgray', stroke='gray')
    ).properties(width=width, height=height)

    projections = {
        "Albers": {
            "type": "albers",
            "center": center,
            "rotate": [-20, 0],
            "translate": [width/2, height/2],
            "scale": scale,
            "precision": 0.1
        },
    }
    geo_chart = base.properties(projection=projections['Albers'])

    multi = alt.selection_multi(on='click', nearest=False, empty = 'none', bind='legend', toggle="true")
    geo_points = alt.Chart(subset_metrics_df).mark_circle().encode(
        longitude='longitude:Q',
        latitude='latitude:Q',
        opacity=alt.condition(multi, alt.OpacityValue(1), alt.OpacityValue(0.8)),
        size=alt.condition(multi, alt.value(120),alt.value(40)),
        shape=alt.condition(multi, alt.ShapeValue("diamond"), alt.ShapeValue("circle")),
        tooltip='officialName',
        color= alt.condition(multi, "name:N",alt.ColorValue('black'))
    ).add_selection(
        multi
    )

    barChartProperties = {'height': 200}

    barChart1 = make_team_comparison_bar_chart(subset_metrics_df, team_metrics[0], multi)
    barChart2 = make_team_comparison_bar_chart(subset_metrics_df, team_metrics[1], multi)
    barChart3 = make_team_comparison_bar_chart(subset_metrics_df, team_metrics[2], multi, height=201)

    return alt.vconcat((geo_chart + geo_points), (barChart1 | barChart2 | barChart3), center=True)
    
def main3():
    team_season_momentum = load_data('team_season_momentum.csv')
    team_metrics_df = load_data('team_metrics1.csv')
    

    st.header('Team Momentum')
    st.caption('Momentum estimates how well a team is doing at any point in the game')
    selected_teams = st.multiselect('Choose Teams', team_metrics_df["team_id"], max_selections = 5, format_func=lambda x: team_metrics_df[team_metrics_df['team_id']==x]['name'].values[0])
    
    st.altair_chart(create_momentum_comparison_chart(team_season_momentum, selected_teams), use_container_width=True)

    st.header('Team Comparisons')
    selectedLeague = st.selectbox("League", ['All', 'England', 'France', 'Germany', 'Italy', 'Spain'])
    team_metrics = ["Pass Success Rate", "Crosses / Shot", "Passes / Shot"]

    st.altair_chart(create_team_comparison_charts(team_metrics_df, team_metrics, selectedLeague), use_container_width=True)
    

def main5():
    st.write("## Brian's Page")

def main4():
    st.write("## Introduction")

    st.write(
    """
    Welcome to KickLogic, your premier destination for in-depth insights into the dynamic world of soccer. Dive into the heart of the beautiful game with our cutting-edge platform, where data meets passion to deliver a comprehensive view of every match, player, and team. Unleashing the power of advanced analytics, we transform raw statistics into meaningful narratives, providing fans, analysts, and enthusiasts alike with a rich tapestry of information. Whether you're a dedicated supporter seeking a deeper understanding of your favorite team's performance or a strategic mind looking to unravel the tactical nuances of the game, our dashboard empowers you to explore, analyze, and celebrate the sport you love. Join us on this exhilarating journey through the numbers, where the game comes to life in ways you've never experienced before.
    """
    )

    st.write("## Intended Audience")

    st.write(
        """
        KickLogic is designed to cater to a diverse audience of soccer aficionados.

        1. Fans will find a treasure trove of statistics and visualizations that enhance their enjoyment of the game, offering a deeper understanding of players' contributions and team dynamics.

        2. Coaches and analysts can leverage our platform to dissect performance metrics, track player development, and refine strategic approaches.

        3.  Fantasy football enthusiasts will discover invaluable insights for informed team selection.

        4. Additionally, scouts and professionals within the soccer industry can utilize our advanced analytics to identify emerging talent and make data-driven decisions.

        No matter your connection to the sport, our dashboard is your gateway to a more insightful and immersive soccer experience.
        """
    )
    
    st.write("## Data Sources")
    
    st.markdown("""The dataset utilized to create this interavtive web-app originated from [Kaggle](https://www.kaggle.com/datasets/aleespinosa/soccer-match-event-dataset)""")

    st.write("## Meet The Creators")

    st.markdown("""
    1. **Abel Ninan** *(abelninan@berkeley.edu)*
    2. **Dan Nealon** *(dan.nealon@berkeley.edu)*
    3. **Paul Cooper** *(paul.cooper@berkeley.edu)*
    4. **Brian Tung** *(brianhstung@berkeley.edu)*
    """)

    st.write("## Need Some Help?")
    
    st.markdown("""You can find a video [here](https://www.youtube.com) that will walk you through our website and how to use it to its best ability!""")

def main():
    st.set_page_config(page_title="KickLogic", page_icon=":soccer:", layout = "centered")
    st.title('KickLogic - Soccer Analytics')
    app_choice_2 = st.selectbox('Choose Page to Navigate To:', ['Home', 'Player Role Analysis', 'Match Analysis', 'Player Valuation Analysis', 'Club Analysis'])
    if app_choice_2 == 'Player Role Analysis':
        main2()
    elif app_choice_2 == 'Match Analysis':
        main1()
    elif app_choice_2 == 'Club Analysis':
        main3()
    elif app_choice_2 == 'Home':
        main4()
    elif app_choice_2 == 'Player Valuation Analysis':
        main5()

# def main():
#     st.set_page_config(page_title="KickLogic", page_icon="✨", layout = "centered")

#     # Create tabs at the top
#     tab1,tab2,tab3,tab4,tab5 = st.tabs(["Home", "Player-Positon Analysis", "Match Analysis", "Club Analysis", "Player Valuation Analysis"])

#     # Check which tab is selected and show the corresponding page
#     with tab1:
#         main4()
#     with tab2:
#         main2()
#     with tab3:
#         main1()
#     with tab4:
#         main3()
#     with tab5:
#         main5()

if __name__ == '__main__':
    main()


