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

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}


def get_rtfs(params=None):
    params = params or default_params
    response = requests.get(BASE_URL, headers=headers, params=params)
    return response.content
