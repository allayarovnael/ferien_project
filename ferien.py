import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import itertools
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

FERIEN_NAMES = {
    'Winterferien': 'WF', 
    'Osterferien': 'OF', 
    'Pfingstferien': 'PF', 
    'Sommerferien': 'SF', 
    'Herbstferien': 'HF', 
    'Weihnachtsferien': 'WF',
}

BUNDESLAENDER = {
    'Bayern': 'BY',
    'Baden-Württemberg': 'BW',
    'Berlin': 'BE',
    'Brandenburg': 'BB',
    'Bremen': 'HB',
    'Hamburg': 'HH',
    'Hessen': 'HE',
    'Mecklenburg-Vorpommern': 'MV',
    'Niedersachsen': 'NI',
    'Nordrhein-Westfalen': 'NW',
    'Rheinland-Pfalz' : 'RP',
    'Saarland': 'SL',
    'Sachsen': 'SN',
    'Sachsen-Anhalt': 'ST',
    'Schleswig-Holstein': 'SH',
    'Thüringen': 'TH',
}

def get_raw_yearly_ferien_data(year: int):
    '''
    for a given year scrape the ferien data from https://www.ferienwiki.de/
    in a form of list of list (separate for individual bundesland).
    the order of ferien types is fixed and the same as in HOLIDAYS dict.
    '''
    raw_html = requests.get('https://www.ferienwiki.de/ferienkalender/{}/de'.format(year))
    soup = bs(raw_html.text, "html.parser")
    table = soup.find("table", attrs={"class": "table table-condensed table-striped table-bordered table-hover" })
    data = []
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [element.text.strip() for element in cols]
        data.append([element for element in cols]) 
    return data

def parse_time_interval(interval: str, year: int):
    '''
    helper function for parsing and formatting the raw data from the website. 
    see examples of data by calling get_raw_yearly_ferien_data.
    '''
    if not interval: 
        return []                                      # return empty list in case of empty interval string 
    interval = interval.replace(' ', '').split(',')    # date intervals are separated by comma - split and remove spaces
    interval_formatted = []
    for dates in interval:
        if '-' in dates:
            dates = dates.split('-')
            start = date(year, int(dates[0][3:5]), int(dates[0][:2]))
            end   = date(year, int(dates[1][3:5]), int(dates[1][:2]))
            if start > end:                                               
                end = end + relativedelta(years=1)      # in case of "Winterferien"
                
            # create a date range within given ranges:
            dates = [date.fromordinal(i) for i in range(start.toordinal(), end.toordinal()+1)] 
        else:
            dates = [date(year, int(dates[3:5]), int(dates[:2]))]
        interval_formatted.append(dates)           

    return list(itertools.chain.from_iterable(interval_formatted))  # flattens list

def parse_table_data(years=list(range(2014, 2024))):
    '''
    iteratively parse the raw data for a given list of years.
    '''
    ferien_names_list = list(FERIEN_NAMES.keys())
    ferien_data =  dict()
    for year in years:
        ferien_data[year] = dict()
        data = get_raw_yearly_ferien_data(year)
        for row in data:
            bundesland = row[0]
            ferien_data[year][bundesland] = dict()
            for index, ferientype in enumerate(ferien_names_list):
                ferien_data[year][bundesland][ferientype] = parse_time_interval(row[index+1], year)
    return ferien_data

def create_df_from_crawled_data(years = list(range(2014, 2024))):
    
    bl_names_list = list(BUNDESLAENDER.keys())
    ferien_names_list = list(FERIEN_NAMES.keys())
    ferien_data = parse_table_data(years=years)
    timeline =  pd.date_range(date(years[0],1,1), date(years[-1],12,31))
    
    outlist = [ (i, j, k)
        for i in bl_names_list
        for j in ferien_names_list
        for k in timeline
    ]
    
    df = pd.DataFrame(data=outlist, columns=['bundesland','ferien_type','date'])
    df['index'] = 0
    
    for year in years:
        for bundesland in bl_names_list:
            for ferien_type in ferien_names_list:
                data_temp = ferien_data[year][bundesland][ferien_type]
                mask = (df['bundesland']==bundesland) & (df['ferien_type']==ferien_type) & (df['date'].isin(data_temp))
                df.loc[mask,'index'] = 1
    return df           

# Collect all available historical data:
ferien_data_2014_2023 = create_df_from_crawled_data()

# Let's reshape data using more friendly format:
ferien_data_2014_2023 = ferien_data_2014_2023.pivot(index=['bundesland','date'], columns='ferien_type', values='index')
ferien_data_2014_2023.head()