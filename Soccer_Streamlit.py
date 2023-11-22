#!/usr/bin/env python
# coding: utf-8

# In[2]:
import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
from geopy.geocoders import Nominatim
from ctypes import alignment
from vega_datasets import data

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
    ).transform_filter(selection).properties(width = 400)

    bar_2 = alt.Chart(playerank_grouping).mark_bar().encode(
        x = alt.X('minutesPlayed', title='Minutes Played'),
        y = alt.Y('roleCluster', title='Player Roles'),
        color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
        tooltip = ['minutesPlayed:Q']
    ).transform_filter(selection).properties(width = 400)

    # ratio of minutes per goal per player role
    bar_3 = alt.Chart(playerank_grouping).mark_bar().encode(
        x = alt.X('minutes_per_goal', title='Ratio of Minutes Per Goal'),
        y = alt.Y('roleCluster', title='Player Roles'),
        color = alt.condition(selection, 'roleCluster:N', alt.value('lightgray')),
        tooltip = ['minutes_per_goal:Q']
    ).transform_filter(selection).properties(width = 400)


    # combining all 3 plots
    combined_plot_2 = alt.vconcat(dot_plot, bar_2, bar_1, bar_3)

    combined_plot_2

def get_lat_long(address):
    geolocator = Nominatim(user_agent="My App")
    try:
        x = geolocator.geocode(address)
        return x.latitude, x.longitude
    except:
        return np.nan, np.nan
        
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

def calc_game_momentum(actions, game_id, perspective_team_id = 0, weight_span = 3):

    game_data = actions[actions['game_id'] == game_id]

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
    weighted_grouped_data = relevant_actions_fixed.groupby(['game_id', 'time_minutes', 'team_id']).agg(
        weighted_actions=pd.NamedAgg(column='action_weight', aggfunc='sum'),
        avg_start_x=pd.NamedAgg(column='start_x', aggfunc='mean')
    ).reset_index()

    # # Calculate momentum
    weighted_grouped_data['momentum'] = ((weighted_grouped_data['avg_start_x'] - 50) / 50) * weighted_grouped_data['weighted_actions']

    # # Dynamically determine the teams based on the data
    teams = weighted_grouped_data['team_id'].unique()
    if len(teams) != 2:
        print("Error: There are not exactly two teams in the game data.")
        return None

    if perspective_team_id == 0:
        team_1_id, team_2_id = teams[0], teams[1]
    else:
        team_1_id = perspective_team_id
        team_2_id = np.setdiff1d(weighted_grouped_data['team_id'].unique(), perspective_team_id)[0]

    # weighted average by teamId
    team1_df = weighted_grouped_data[weighted_grouped_data['team_id'] == team_1_id]
    team2_df = weighted_grouped_data[weighted_grouped_data['team_id'] == team_2_id]
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

    return momentum_per_minute

def create_momentum_chart(game_momentum_df):
    game_momentum_df['pos_momentum'] = game_momentum_df['momentum'].apply(lambda x: max(x, 0))
    game_momentum_df['neg_momentum'] = game_momentum_df['momentum'].apply(lambda x: min(x, 0))

    posChart = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("pos_momentum", scale=alt.Scale(domain=[-1, 1]))
    )

    negChart = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("neg_momentum", scale=alt.Scale(domain=[-1, 1])),
        fill = alt.value("red")
    )

    game_momentum_df['pos_momentum_weighted'] = game_momentum_df['weighted_avg_momentum'].apply(lambda x: max(x, 0))
    game_momentum_df['neg_momentum_weighted'] = game_momentum_df['weighted_avg_momentum'].apply(lambda x: min(x, 0))

    posChart_w = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("pos_momentum_weighted", scale=alt.Scale(domain=[-1, 1]))
    )

    negChart_w = alt.Chart(game_momentum_df).mark_area().encode(
        x="time_minutes",
        y=alt.Y("neg_momentum_weighted", scale=alt.Scale(domain=[-1, 1])),
        fill = alt.value("red")
    )

    return posChart_w + negChart_w

def get_games_by_team_id(actions, teamId):
  return actions[actions['team_id'] == teamId]['game_id'].unique()

def calc_team_season_momentum(actions, teamId):
    game_ids = get_games_by_team_id(actions, teamId)

    game_momentums = calc_game_momentum(actions, game_ids[0], teamId, 3)
    for g in game_ids[1:]:
        this_game_momentum = calc_game_momentum(actions, g, teamId, 3)
        game_momentums = pd.concat([game_momentums, this_game_momentum])

    return game_momentums.groupby('time_minutes').agg(
        momentum=pd.NamedAgg(column='momentum', aggfunc='mean'),
        weighted_avg_momentum=pd.NamedAgg(column='weighted_avg_momentum', aggfunc='mean')
    ).reset_index()  
  
# Set up a dataframe with precalculated metrics per team
def pass_success_rate(teamId, actionsGrouped):
    return actionsGrouped[(actionsGrouped["team_id"] == teamId) & (actionsGrouped["type_name"] == "pass") & (actionsGrouped["result_name"] == "success")]["count"].sum() / actionsGrouped[(actionsGrouped["team_id"] == teamId) & (actionsGrouped["type_name"] == "pass")]["count"].sum()

def crosses_per_shot(teamId, actionsGrouped):
      return actionsGrouped[(actionsGrouped["team_id"] == teamId) & (actionsGrouped["type_name"] == "cross")]["count"].sum() / actionsGrouped[(actionsGrouped["team_id"] == teamId) & (actionsGrouped["type_name"] == "shot")]["count"].sum()

def passes_per_shot(teamId, actionsGrouped):
      return actionsGrouped[(actionsGrouped["team_id"] == teamId) & (actionsGrouped["type_name"] == "pass")]["count"].sum() / actionsGrouped[(actionsGrouped["team_id"] == teamId) & (actionsGrouped["type_name"] == "shot")]["count"].sum()

def set_team_metrics_df(actions, teams, team_metrics):

    actions_grouped = actions.groupby(['team_id', 'type_name', 'result_name']).size().reset_index(name="count")

    return pd.DataFrame(
        [[
            t,
            pass_success_rate(t, actions_grouped),
            crosses_per_shot(t, actions_grouped),
            passes_per_shot(t, actions_grouped)
        ] for t in actions_grouped["team_id"].unique()],
        columns = ["team_id"] + team_metrics
    ).join(teams, lsuffix="team_id", rsuffix="wyId")

def make_team_comparison_bar_chart(team_metrics_df, metric, multi, height=200):
    base_bar = alt.Chart(team_metrics_df, title=metric).mark_bar().encode(
      x="name:N",
      color= "name:N",
      y= alt.Y(metric, axis=alt.Axis(title=None)),
    ).transform_filter(multi).properties(height=height)
    text= base_bar.mark_text(angle = 270, align="center", yOffset=50, fontWeight="bold").encode(text="name:N", color=alt.ColorValue("black"))
    return (base_bar + text)

def create_team_comparison_charts(team_metrics_df, team_metrics):
    sphere = alt.sphere()
    graticule = alt.graticule(step=[10, 10])
    # lats = alt.sequence(start=-30, stop=71, step=10, as_='lats')
    # lons = alt.sequence(start=-90, stop=91, step=10, as_='lons')

    width = 800
    height = 600

    # Source of land data
    source = alt.topo_feature(data.world_110m.url, 'countries')

    # Layering and configuring the components
    base = alt.layer(
        alt.Chart(sphere).mark_geoshape(fill='none'),
        alt.Chart(graticule).mark_geoshape(stroke='gray', strokeWidth=0.5),
        alt.Chart(source).mark_geoshape(fill='lightgray', stroke='gray')
    ).properties(width=width, height=height)

    projections = {
        "Albers": {
            "type": "albers",
            "center": [-10, 50],
            "rotate": [-20, 0],
            "translate": [width/2, height/2],
            "scale": 1100,
            "precision": 0.1
        },
    }
    geo_chart = base.properties(projection=projections['Albers'])

    multi = alt.selection_multi(on='click', nearest=False, empty = 'none', bind='legend', toggle=True)
    geo_points = alt.Chart(team_metrics_df).mark_circle().encode(
        longitude='longitude:Q',
        latitude='latitude:Q',
        size=alt.condition(multi, alt.value(60),alt.value(40)),
        shape=alt.condition(multi, alt.ShapeValue("diamond"), alt.ShapeValue("circle")),
        tooltip='officialName',
        color= alt.condition(multi, "name:N",alt.ColorValue('black'))
        # color = alt.Color("name:N", legend=None) I can't figure out how to suppress the legend while keeping the condition?
    ).add_selection(
        multi
    )

    barChartProperties = {'height': 200}

    barChart1 = make_team_comparison_bar_chart(team_metrics_df, team_metrics[0], multi)
    barChart2 = make_team_comparison_bar_chart(team_metrics_df, team_metrics[1], multi)
    barChart3 = make_team_comparison_bar_chart(team_metrics_df, team_metrics[2], multi, height=201)

    return (geo_chart + geo_points) & (barChart1 | barChart2 | barChart3)

def main3():
    actions = load_data('actions_sample.csv')
    teams = load_data('teams.csv')
    
    pd.options.mode.chained_assignment = None

    # Get lat/longs for each city
    teams[['latitude', 'longitude']] = teams.apply(lambda x: get_lat_long(x.city), axis=1, result_type='expand')

    # Sidebar - Team selection
    st.sidebar.header('Team Selection')
    sorted_unique_teams = sorted(teams['wyId'].unique())
    selected_team = st.sidebar.selectbox('Choose a team', sorted_unique_teams)

    st.header('Team Momentum')
    create_momentum_chart(calc_team_season_momentum(actions, selected_team))

    st.header('Team Comparisons')
    team_metrics = ["Pass Success Rate", "Crosses / Shot", "Passes / Shot"]
    team_metrics_df = set_team_metrics_df(actions, teams, team_metrics)

    create_team_comparison_charts(team_metrics_df, team_metrics)

def main():
    st.title('KickLogic - Soccer Analytics')
    app_choice = st.selectbox('Choose your analysis type:', ['Player Role', 'Match', 'Player Valuation', 'Club'])
    if app_choice == 'Player Role':
        main2()
    elif app_choice == 'Match':
        main1()
    elif app_choice == 'Club':
        main3()

if __name__ == '__main__':
    main()


