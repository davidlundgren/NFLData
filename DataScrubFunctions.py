import urllib.request as request
import re
import time
from bs4 import BeautifulSoup
import csv
import sys
import numpy as np
import pandas as pd
import re
import os.path

def cell_text(cell):
    return " ".join(cell.stripped_strings)

def dateName2Num(date, dateDict):
    if date != date:
        return -1, -1
    else:
        dateArr = re.split(' ', date)
        month = np.int64(dateDict[dateArr[0]])
        day = np.int64(dateArr[1])
        return month, day
    
def add_team_season(team_full, team_short, season, outfile, dateDict):
    url = 'http://www.pro-football-reference.com/teams/%s/%d.htm#team_gamelogs::none' % (team_short, season)
    response = request.urlopen(url)
    html = response.read()
    # we need to figure out which league this is
    # in each page there is a sentence "<season> <league> Season Summary'
    league = re.split(' ', re.split(' Season Summary', str(html))[0])[-1]
    soup = BeautifulSoup(html, 'lxml')
    fileExists = False
    if os.path.isfile(outfile):
        fileExists = True
    csvfile = open(outfile, 'a')
    output = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    if not fileExists:
        output.writerow(['League', 'Season', 'Stadium', 'Weather', 'Year', 'Week', 'Playoffs?', 'Week_Day', 'Month', 'Day', \
                         'OT', 'HomeTeam', 'AwayTeam', 'HomeScore', 'AwayScore', 'ScoreDiff', 'Home1stD', 'HomeTotYd', \
                         'HomePassY', 'HomeRushY', 'HomeTO', 'Away1stD', 'AwayTotYd', 'AwayPassY', 'AwayRushY', 'AwayTO'])
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            output_list = GetFields2Write(season, team_full, row, league, dateDict)
            if output_list:
                output.writerow(output_list)

def WeekDayAbr2Number(day):
    d = {'mon': 0, 'tue': 1, 'wed':2, 'thu':3, 'fri':4, 'sat':5, 'sun':6}
    return d[day.lower()]

def GetFields2Write(season, team_full, row, league, dateDict):
    output_list = [league, season]
    if '>boxscore<' in str(row) and \
        not '>Rec<' in str(row):
        gameLink = re.split('a href="/boxscores/(.*?)">', str(row.find_all('td')[3]))[1]
        #print(row, gameLink)
        stadium, weather = game2StadiumWeather(gameLink)
        AddTag(output_list, stadium)
        AddTag(output_list, weather)
        rows_list = row.find_all('td')
        if 'January' in rows_list[2].contents[0] or \
               'February' in rows_list[2].contents[0]: # this game took place the following calendar year
            year = season + 1
        else:
            year = season
        output_list.append(year)
        # we're only going to record the game for the home team so each game is recorded once
        if rows_list[7].contents:
            if rows_list[7].contents[0] == '@' or \
               (rows_list[7].contents[0] and rows_list[4].contents[0] == 'L'):
                    # no home team in the superbowl, we use the winner instead
                    return None
        for i, col in enumerate(rows_list):
            if i == 0:
                # week numbers have at most two digits
                # playoff week have names, 'Division', 'SuperBowl', etc.
                if len(col.contents[0]) <= 2:
                    AddTag(output_list, col)
                    AddTag(output_list, 'False')
                else:
                    # playoff games will get week numbers with the last week
                    # of the regular season + 1
                    regSeasonWeeks = GetRegularSeasonLength(season, league)
                    if col.contents[0] == 'WildCard':
                        AddTag(output_list, regSeasonWeeks + 1)
                    elif col.contents[0] == 'Division':
                        if season < 1978:
                            AddTag(output_list, regSeasonWeeks + 1)
                        else:
                            AddTag(output_list, regSeasonWeeks + 2)
                    elif col.contents[0] == 'ConfChamp':
                        if season < 1978:
                            AddTag(output_list, regSeasonWeeks + 2)
                        else:
                            AddTag(output_list, regSeasonWeeks + 3)
                    elif col.contents[0] == 'SuperBowl':
                        regSeasonWeeks = max(GetRegularSeasonLength(season, 'NFL'), GetRegularSeasonLength(season, 'AFL'))
                        if season < 1960:
                            AddTag(output_list, regSeasonWeeks + 2)
                        elif season in np.arange(1960, 1968):
                            regSeasonWeeks = max(GetRegularSeasonLength(season, 'NFL'), \
                                                 GetRegularSeasonLength(season, 'AFL'))
                            AddTag(output_list, regSeasonWeeks + 2)
                        elif season in np.arange(1969, 1978):
                            AddTag(output_list, regSeasonWeeks + 3)
                        else:
                            AddTag(output_list, regSeasonWeeks + 4)
                    elif col.contents[0] == 'Championship':
                        if season in [1941, 1967, 1968, 1969]:
                            AddTag(output_list, regSeasonWeeks + 2)
                        else:
                            AddTag(output_list, regSeasonWeeks + 1)
                    else:
                        AddTag(output_list, 25) # I'll look for failed cases and fix them
                    AddTag(output_list, 'True')
            elif i == 1:
                if len(row.find_all('td')[0].contents[0]) > 2:
                    AddTag(output_list, 999)
                else:
                    AddTag(output_list, WeekDayAbr2Number(col.contents[0]))
            elif i == 2:
                dateNums = dateName2Num(col.contents[0], dateDict)
                AddTag(output_list, dateNums[0])
                AddTag(output_list, dateNums[1])
            elif i == 5:
                if col.contents:
                    AddTag(output_list, True)
                else:
                    AddTag(output_list, False)
            elif i == 8:
                AddTag(output_list, team_full)
                AddTag(output_list, col.contents[0])
            elif i == 10:
                AddTag(output_list, col)
                AddTag(output_list, int(rows_list[9].contents[0]) - int(col.contents[0]))
            elif i == 15:
                if col.contents:
                    AddTag(output_list, col)
                else:
                    AddTag(output_list, 0)
            elif i == 20:
                if col.contents:
                    AddTag(output_list, col)
                else:
                    AddTag(output_list, 0)
            elif i not in [3, 4, 6, 7]:
                if i > 20:
                    break
                if col.contents:
                    AddTag(output_list, col)
                else:
                    AddTag(output_list, None)
    else:
        output_list = None
    return output_list

def GetRegularSeasonLength(year, league = 'NFL'):
    if year in [1933, 1934] or \
       ((year in [1947, 1948, 1950, 1960]) and league == 'NFL'):
        return 13
    elif year in np.arange(1933, 1937) or \
         year in np.arange(1938, 1941) or \
         year in np.arange(1942, 1946) or \
        year in np.arange(1951, 1959) or \
         ((year in [1946, 1949]) and league == 'NFL'):
        return 12
    elif ((year in [1946, 1949]) and league == 'AAFC') or \
         ((year in [1968, 1969]) and league == 'AFL') or \
         ((year in np.arange(1961, 1966) or year in [1937, 1941, 1967]) and league == 'NFL') or \
        (year in np.arange(1968, 1978)):
        return 14
    elif ((year in [1947, 1948]) and league == 'AAFC') or \
         ((year in [1960, 1961, 1962, 1964, 1965]) and league == 'AFL') or \
         (year in [1966] and league == 'NFL'):
        return 15
    elif ((year in [1963, 1966]) and league == 'AFL') or \
         (year in np.arange(1978, 1990) and year != 1982):
        return 16
    elif (year == 1982) or \
         (year >= 1990 and year != 1993) or \
         (year in [1967] and league == 'AFL'):
        return 17
    elif year in [1993]:
        return 18
    else:
        return 20

def AddTag(output_list, tag):
    try:
        output_list.append(tag.contents[0])
    except AttributeError:
        output_list.append(tag)

def add_team_history(team_short, outfile):
    url = 'http://www.pro-football-reference.com/teams/%s/' % (team_short)
    response = request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'lxml')
    fileExists = False
    if os.path.isfile(outfile):
        fileExists = True
    csvfile = open(outfile, 'a')
    output = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    if not fileExists:
        output.writerow(['Year', 'Lg', 'Tm', 'Abr'])
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            if '>NFL<' in str(row) or \
            '>AFL<' in str(row) or \
            '>AAFC<' in str(row) or \
            '>APFA<' in str(row):
                outList = []
                for col in row.find_all('td')[0:3]:
                    outList.append(col.contents[0].contents[0])
                outList.append(team_short)
                output.writerow(outList[0:4])

def game2Stadium(gameLink):
    url = 'http://www.pro-football-reference.com/boxscores/%s' % (gameLink)
    response = request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'lxml')
    stadium = None
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            if 'Stadium' in str(row):
                stadium = row.find_all('td')[1].contents[0].contents[0] 
    return stadium

def game2StadiumWeather(gameLink):
    url = 'http://www.pro-football-reference.com/boxscores/%s' % (gameLink)
    response = request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'lxml')
    stadium = None
    weather = None
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            if '>Stadium<' in str(row):
                stadium = row.find_all('td')[1].contents[0].contents[0]
            if '>Weather<' in str(row):
                try:
                    weather = row.find_all('td')[1].contents[0].contents[0]
                except AttributeError:
                    weather = row.find_all('td')[1].contents[0]
    return stadium, weather

def MakeTeamHistories(teamAbr, \
                      outfile = '/Users/dekedor/Programming/Kaggle/iPythonNotebooks/NFLDB/Team_Histories.csv'):
    for code in teamAbr.keys():
        for item in teamAbr[code]:
            add_team_history(item, outfile)    

def GetTeamAbreviations():
    teamAbr = {'Arizona Cardinals':['crd'],
    'Atlanta Falcons':['atl'],
    'Baltimore Ravens':['rav'],
    'Buffalo Bills':['buf', 'bba'],
    'Carolina Panthers':['car'],
    'Chicago Bears':['chi'],
    'Cincinnati Bengals':['cin'],
    'Cleveland Browns':['cle'],
    'Dallas Cowboys':['dal'],
    'Denver Broncos':['den'],
    'Detroit Lions':['det'],
    'Green Bay Packers':['gnb'],
    'Houston Texans':['htx'],
    'Indianapolis Colts':['clt'],
    'Jacksonville Jaguars':['jax'],
    'Kansas City Chiefs':['kan'],
    'Miami Dolphins':['mia'],
    'Minnesota Vikings':['min'],
    'New England Patriots':['nwe'],
    'New Orleans Saints':['nor'],
    'New York Giants':['nyg'],
    'New York Jets':['nyj'],
    'Oakland Raiders':['rai'],
    'Philadelphia Eagles':['phi'],
    'Pittsburgh Steelers':['pit'],
    'San Diego Chargers':['sdg'],
    'San Francisco 49ers':['sfo'],
    'Seattle Seahawks':['sea'],
    'St. Louis Rams':['ram'],
    'Tampa Bay Buccaneers':['tam'],
    'Tennessee Titans':['oti'],
    'Washington Redskins':['was'],
    'Akron Indians':['akr'],
    'Baltimore Colts':['bcl'],
    'Boston Bulldogs':['ptb'],
    'Boston Yanks':['byk'],
    'Brooklyn Dodgers':['bda'],
    'Brooklyn Lions':['brl'],
    'Brooklyn Tigers':['bkn'],
    'Buffalo Bisons':['bff'],
    'Canton Bulldogs':['cbd'],
    'Chicago Hornets':['cra'],
    'Chicago Tigers':['cht'],
    'Cincinnati Celts':['ccl'],
    'Cincinnati Reds':['red'],
    'Cleveland Bulldogs':['cib'],
    'Cleveland Indians':['cti'],
    'Cleveland Indians':['cli'],
    'Columbus Tigers':['col'],
    'Dallas Texans':['dtx'],
    'Dayton Triangles':['day'],
    'Detroit Heralds':['dhr'],
    'Detroit Panthers':['dpn'],
    'Detroit Tigers':['dti'],
    'Detroit Wolverines':['dwl'],
    'Duluth Eskimos':['dul'],
    'Evansville Crimson Giants':['ecg'],
    'Frankford Yellow Jackets':['fyj'],
    'Hammond Pros':['ham'],
    'Hartford Blues':['hrt'],
    'Kansas City Cowboys':['kcb'],
    'Kenosha Maroons':['ken'],
    'Los Angeles Buccaneers':['lab'],
    'Los Angeles Dons':['lda'],
    'Louisville Colonels':['lou'],
    'Miami Seahawks':['msa'],
    'Milwaukee Badgers':['mil'],
    'Minneapolis Red Jackets':['mnn'],
    'Muncie Flyers':['mun'],
    'New York Brickley Giants':['ng1'],
    'New York Yankees':['nya', 'naa'],
    'New York Yanks':['nyy'],
    'Newark Tornadoes':['tor'],
    'Oorang Indians':['oor'],
    'Providence Steam Roller':['prv'],
    'Racine Tornadoes':['rac'],
    'Rochester Jeffersons':['rch'],
    'Rock Island Independents':['rii'],
    'St. Louis All-Stars':['sla'],
    'St. Louis Gunners':['gun'],
    'Staten Island Stapletons':['sis'],
    'Toledo Maroons':['tol'],
    'Tonawanda Kardex':['ton'],
    'Washington Senators':['sen']}
    return teamAbr