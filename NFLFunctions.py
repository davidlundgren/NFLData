import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import re
import datetime
from geopy.distance import vincenty
import dateutil.relativedelta
import math
import warnings
from matplotlib import ticker

def dateName2Num(date, dateDict):
    if date != date:
        return -1, -1
    else:
        dateArr = re.split(' ', date)
        month = np.int64(dateDict[dateArr[0]])
        day = np.int64(dateArr[1])
        return month, day
    
def rec2WinsLosesTies(rec):
    arr = re.split('-', rec)
    if len(arr) == 2:
        return np.int64(arr[0]), np.int64(arr[1]), np.int64(0)
    else:
        return np.int64(arr[0]), np.int64(arr[1]), np.int64(arr[2])

def rec2GameNum(rec):
    wins, loses, ties = rec2WinsLosesTies(rec)
    return wins + loses + ties

def GetDateDict():
    dateDict = {}
    dateDict['January'] = 1
    dateDict['February'] = 2
    dateDict['March'] = 3
    dateDict['April'] = 4
    dateDict['May'] = 5
    dateDict['June'] = 6
    dateDict['July'] = 7
    dateDict['August'] = 8
    dateDict['September'] = 9
    dateDict['October'] = 10
    dateDict['November'] = 11
    dateDict['December'] = 12
    return dateDict

def GetDivision(team, season, df_divisions):
    if season < 1970:
        return None
    df_team_season = df_divisions[(df_divisions['Team'] == team) & (df_divisions['First Season'] <= season) & \
                      (df_divisions['Last Season'] >= season)]
    if df_team_season.empty:
        return None
    return df_team_season['Conference'].values[0] + ' ' + df_team_season['Division'].values[0]

def GetScoresDistRange(scores, dist_min, dist_max, season_min = 1966, playoffs = False):
    df = scores[(scores['TravelDistance'] >= dist_min) & (scores['TravelDistance'] <= dist_max) & \
                (scores['Playoffs?'] == playoffs) & (scores['Season'] >= season_min)]
    home_all = df.groupby('HomeTeam').groups
    home_win = df[(df['ScoreDiff'] > 0)].groupby('HomeTeam').groups
    away_all = df.groupby('AwayTeam').groups
    away_win = df[(df['ScoreDiff'] < 0)].groupby('AwayTeam').groups
    df_teams = pd.DataFrame()
    df_teams['Team'] = home_all.keys()
    df_teams['Home'] = np.array([len(home_all[team]) if team in home_all.keys() else 0 for team in df_teams['Team']])
    df_teams['HomeW'] = np.array([len(home_win[team]) if team in home_win.keys() else 0 for team in df_teams['Team']])
    df_teams['%HomeW'] = 100. * df_teams['HomeW'] / df_teams['Home']
    df_teams['HomeDiff'] = np.array([df.groupby('HomeTeam')['ScoreDiff'].mean()[team] \
                                     if team in df.groupby('HomeTeam').groups else 0 for team in df_teams['Team']])
    df_teams['Away'] = np.array([len(away_all[team]) if team in away_all.keys() else 0 for team in df_teams['Team']])
    df_teams['AwayW'] = np.array([len(away_win[team]) if team in away_win.keys() else 0 for team in df_teams['Team']])
    df_teams['%AwayW'] = 100. * df_teams['AwayW'] / df_teams['Away']
    df_teams['AwayDiff'] = -1. * np.array([df.groupby('AwayTeam')['ScoreDiff'].mean()[team] \
                                     if team in df.groupby('AwayTeam').groups else 0 for team in df_teams['Team']])
    df_teams['Total'] = df_teams['Home'] + df_teams['Away']
    df_teams['Win'] = df_teams['HomeW'] + df_teams['AwayW']
    df_teams['%TotalW'] = 100. * df_teams['Win'] / df_teams['Total']
    df_teams['TotalDiff'] = (df_teams['Home'] * df_teams['HomeDiff'] + df_teams['Away'] * df_teams['AwayDiff']) / \
    (df_teams['Home'] + df_teams['Away'])
    df_teams['%Home - %Away'] = df_teams['%HomeW'] - df_teams['%AwayW']
    df_teams['MeanDistance'] = np.array([df.groupby('AwayTeam')['TravelDistance'].mean()[team] if team in \
                                        df.groupby('AwayTeam')['TravelDistance'].groups else 0 for team in \
                                         df_teams['Team']])
    df_teams['HomeDiff - AwayDiff'] = df_teams['HomeDiff'] - df_teams['AwayDiff']
    df_teams = df_teams.sort_values(by='%Home - %Away', ascending=False)
    return df_teams

def NFLDay(scores):
    t0 = datetime.date(1920, 1, 1)
    scores['NFLDay'] = np.array([(datetime.date(year, month, day) - t0).days \
                             for year, month, day in zip(scores['Year'], scores['Month'], scores['Day'])])

def DaysSinceLastGame(scores):
    scores['DaysSinceLastGameHome'] = [nflDay - \
        scores[((scores['HomeTeam'] == team) | (scores['AwayTeam'] == team)) & 
        (scores['Week'] < week) & (scores['Season'] == season)]['NFLDay'].max() if not \
        scores[((scores['HomeTeam'] == team) | (scores['AwayTeam'] == team)) & \
           (scores['Week'] < week) & (scores['Season'] == season)]['NFLDay'].empty else -1 \
            for nflDay, team, week, season \
                                   in zip(scores['NFLDay'], scores['HomeTeam'], scores['Week'], scores['Season'])]
    scores['DaysSinceLastGameAway'] = [nflDay - \
        scores[((scores['HomeTeam'] == team) | (scores['AwayTeam'] == team)) & 
        (scores['Week'] < week) & (scores['Season'] == season)]['NFLDay'].max() if not \
        scores[((scores['HomeTeam'] == team) | (scores['AwayTeam'] == team)) & \
           (scores['Week'] < week) & (scores['Season'] == season)]['NFLDay'].empty else -1 \
            for nflDay, team, week, season in \
                                   zip(scores['NFLDay'], scores['AwayTeam'], scores['Week'], scores['Season'])]

def DeltaDaysOff(scores):
    scores['DeltaDaysOff'] = scores['DaysSinceLastGameHome'] - scores['DaysSinceLastGameAway']

def Wins(scores):
    scores['HomeWins'] = [scores[(((scores['HomeTeam'] == team) & (scores['ScoreDiff'] > 0)) | \
                              ((scores['AwayTeam'] == team) & (scores['ScoreDiff'] < 0))) & \
                             (scores['Week'] < week)]['NFLDay'].count() \
                      for nflDay, team, week in zip(scores['NFLDay'], scores['HomeTeam'], scores['Week'])]
    scores['AwayWins'] = [scores[(((scores['HomeTeam'] == team) & (scores['ScoreDiff'] > 0)) | \
                              ((scores['AwayTeam'] == team) & (scores['ScoreDiff'] < 0))) & \
                             (scores['Week'] < week)]['NFLDay'].count() \
                      for nflDay, team, week in zip(scores['NFLDay'], scores['AwayTeam'], scores['Week'])]

def Losses(scores):
    scores['HomeLosses'] = [scores[(((scores['HomeTeam'] == team) & (scores['ScoreDiff'] < 0)) | \
                              ((scores['AwayTeam'] == team) & (scores['ScoreDiff'] > 0))) & \
                             (scores['Week'] < week)]['NFLDay'].count() \
                      for nflDay, team, week in zip(scores['NFLDay'], scores['HomeTeam'], scores['Week'])]
    scores['AwayLosses'] = [scores[(((scores['HomeTeam'] == team) & (scores['ScoreDiff'] < 0)) | \
                              ((scores['AwayTeam'] == team) & (scores['ScoreDiff'] > 0))) & \
                             (scores['Week'] < week)]['NFLDay'].count() \
                      for nflDay, team, week in zip(scores['NFLDay'], scores['AwayTeam'], scores['Week'])]

def Ties(scores):
    scores['HomeTies'] = [scores[(((scores['HomeTeam'] == team) & (scores['ScoreDiff'] == 0)) | \
                              ((scores['AwayTeam'] == team) & (scores['ScoreDiff'] == 0))) & \
                             (scores['Week'] < week)]['NFLDay'].count() \
                      for nflDay, team, week in zip(scores['NFLDay'], scores['HomeTeam'], scores['Week'])]
    scores['AwayTies'] = [scores[(((scores['HomeTeam'] == team) & (scores['ScoreDiff'] == 0)) | \
                              ((scores['AwayTeam'] == team) & (scores['ScoreDiff'] == 0))) & \
                             (scores['Week'] < week)]['NFLDay'].count() \
                      for nflDay, team, week in zip(scores['NFLDay'], scores['AwayTeam'], scores['Week'])]

def AwayStadium(scores):
    scores['AwayStadium'] = \
    [scores[(scores['HomeTeam'] == team) & (scores['Season'] == season)]['Stadium'].values[0] \
     if len(scores[(scores['HomeTeam'] == team) & (scores['Season'] == season)]['Stadium']) > 0 else None for \
    team, season in zip(scores['AwayTeam'], scores['Season'])]

def GetStadiumCoords(coords_file = 'NFLStadiumCoordinates.csv'):
    coords = pd.read_csv(coords_file)
    stadiums = coords['Stadium'].unique()
    return coords, stadiums

def GetStadiumAliases(aliases_file = 'NFLTeamStadiums.csv'):
    with open(aliases_file, 'r') as f:
        content = f.readlines()
    d = {}
    all_stad = []
    alias = False
    for line in content:
        if '3Com' not in line:
            line = ''.join(i for i in line if not i.isdigit())
        else:
            line = ''.join(i for i in line)
        if 'Oakland-Alameda' not in line:
            line = line.replace('(–)', '').replace('\xa0', '').replace('()', '').strip()
        else:
            line = line.replace('\xa0', '').replace('()', '').strip()
        if alias:
            d[current].append(line.replace('"', '').replace('\n', ''))
            d[line.replace('"', '').replace('\n', '')] = [current]
            if '"' in line:
                alias = False
        elif '"' in line:
            current = line.replace('"', '').replace('\n', '')
            d[current] = [current]
            alias = True
        else:
            d[line.replace('"', '').replace('\n', '')] = [line.replace('"', '').replace('\n', '')]
        all_stad.append(line.replace('"', '').replace('\n', ''))
    return all_stad, d

def TravelDistance(scores, coords, d):
    scores['GameLatLon'] = \
    np.array([(coords[coords['Stadium'] == d[item][0]][['Latitude', 'Longitude']].values[0]) \
              if (item == item) & (item is not None) else None for item in scores['Stadium']])
    scores['AwayLatLon'] = \
    np.array([coords[coords['Stadium'] == d[item][0]][['Latitude', 'Longitude']].values[0] \
              if (item == item) & (item is not None) else None for item in scores['AwayStadium']])
    scores['TravelDistance'] = np.array([vincenty(home, away).miles if (home is not None and away is not None) \
                                         else None for home, away in \
                                         zip(scores['GameLatLon'], scores['AwayLatLon'])]).astype(float)

def Divisions(scores, divisions_file = 'NFLDivisions.csv'):
    df_divisions = pd.read_csv(divisions_file)
    scores['HomeDivision'] = np.array([GetDivision(team, season, df_divisions) for team, season in \
                                      zip(scores['HomeTeam'], scores['Season'])])
    scores['AwayDivision'] = np.array([GetDivision(team, season, df_divisions) for team, season in \
                                      zip(scores['HomeTeam'], scores['Season'])])
    scores['DivisionGame'] = scores['HomeDivision'] == scores['AwayDivision']