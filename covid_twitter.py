import tweepy
import requests
import datetime
import pandas as pd 
import numpy as np 

home_dir = 'C:/Users/Luis/Desktop/personal/github/covid twitter bot' # personal directory for project
ref = pd.read_json(f'{home_dir}/ref.json', typ='series') # twitter 

covid_api = ref['covid_api_key'] # api_key for https://apidocs.covidactnow.org/access/
state_abbrev = 'FL' # state abbreviation
state = 'Florida' # state name

today_dt = datetime.date.today() # current day datetime value
yesterday_iso = (today_dt - datetime.timedelta(days=1)).strftime('%Y-%m-%d') # yesterday's date as ISO string formatted as ex: "2021-02-28"
yesterday = (today_dt - datetime.timedelta(days=1)).strftime('%m/%d/%Y') # yesterday's date as string formatted as ex: "02/28/2021"

# API calls for current panel data and historic time series data
base_url_current = f'https://api.covidactnow.org/v2/states.csv?apiKey={covid_api}' # historic US states covid panel data request
r_current = requests.get(base_url_current)
with open(f'{home_dir}/usa_current.csv', 'wb') as f:
    f.write(r_current.content)

base_url_historic = f'https://api.covidactnow.org/v2/states.timeseries.csv?apiKey={covid_api}' # historic US states covid time series data request
r_historic = requests.get(base_url_historic)
with open(f'{home_dir}/usa_historic.csv', 'wb') as f:
    f.write(r_historic.content)

fl_current_data = pd.read_csv(f'{home_dir}/usa_current.csv', index_col=None)
fl_historic_data = pd.read_csv(f'{home_dir}/usa_historic.csv', index_col='date')

# filter USA data to be FL only and then create rolling difference columns for current hospitalization and deaths
fl_current_data = fl_current_data[fl_current_data['state'] == state_abbrev] # filter panel data to be only FL
fl_historic_data = fl_historic_data[fl_historic_data['state'] == state_abbrev] # filter time series data to be only FL
fl_historic_data['actuals.newHospitalBeds.currentUsageCovid'] = fl_historic_data['actuals.hospitalBeds.currentUsageCovid'].rolling(2).apply(lambda x: x.iloc[1] - x.iloc[0]) # unfortunately there is no rolling difference function, so this custom lambda with rolling is exactly what I need. calculates rolling difference in current hospitalizations with a window of 2
fl_historic_data['actuals.newDeaths'] = fl_historic_data['actuals.deaths'].rolling(2).apply(lambda x: x.iloc[1] - x.iloc[0]) # same as above but for deaths
fl_historic_data['actuals.newVaccinationsCompleted'] = fl_historic_data['actuals.vaccinationsCompleted'].rolling(2).apply(lambda x: x.iloc[1] - x.iloc[0]) # same as above but for completed vaccinations

# fill #N/A historic data rolling difference columns
fl_historic_data['actuals.newDeaths'].fillna(method='ffill', inplace=True)
fl_historic_data['actuals.newHospitalBeds.currentUsageCovid'].fillna(method='ffill', inplace=True)
fl_historic_data['actuals.newVaccinationsCompleted'].fillna(method='ffill', inplace=True)

# stats formatted as an integer using an f string, ex: 115; 7,569; etc.
death_change = f"{int(fl_historic_data.loc[yesterday_iso]['actuals.newDeaths']):,}" 
death_total = f"{int(fl_current_data['actuals.deaths']):,}"

if int(fl_historic_data.loc[yesterday_iso]['actuals.newHospitalBeds.currentUsageCovid']) > 0: # check to make sure that if hospitalized_currently_change is either positive or negative and format accordingly for tweet body
    hospitalized_currently_change = f"+{int(fl_historic_data.loc[yesterday_iso]['actuals.newHospitalBeds.currentUsageCovid']):,}"
else:
    hospitalized_currently_change = f"{int(fl_historic_data.loc[yesterday_iso]['actuals.newHospitalBeds.currentUsageCovid']):,}"
hospitalized_currently = f"{int(fl_current_data['actuals.hospitalBeds.currentUsageCovid']):,}"

cases_change = f"{int(fl_current_data['actuals.newCases']):,}"
cases_total = f"{int(fl_current_data['actuals.cases']):,}"

vaccinations_change = f"{int(fl_historic_data.loc[yesterday_iso]['actuals.newVaccinationsCompleted']):,}"
vaccinations_total = f"{int(fl_current_data['actuals.vaccinationsCompleted']):,}"

# format the message
tweet_body = f'{state} ({state_abbrev}) COVID 19 update: {yesterday}\n\nPositive cases: {cases_total} (+{cases_change})\nCurrent hospitalizations: {hospitalized_currently}\nDeaths: {death_total} (+{death_change})\nVaccinations completed: {vaccinations_total} (+{vaccinations_change})'

# authorize tweepy client
api_key = ref['api_key']
api_key_secret = ref['api_key_secret']
access_token = ref['access_token']
access_token_secret = ref['access_token_secret']

auth = tweepy.OAuthHandler(api_key, api_key_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)
api.update_status(tweet_body) # tweet the message body