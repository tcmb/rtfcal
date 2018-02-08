import requests

BASE_URL = 'http://breitensport.rad-net.de/breitensportkalender'

default_params = {
    'startdate': '01.01.2018',
    'enddate': '31.12.2018',
    'umkreis': '20', # preselections: 20, 50, 100, 200, 400
    'plz': '12055',
    'go': 'Termine+suchen',
    # 'art': '-1',
    # 'titel': '',
    # 'lv': '-1',
    # 'tid': '',
    # 'formproof': '',
}


def get_rtfs(params=None):
    params = params or default_params
    return requests.get(BASE_URL, params=params)
