from flask import Flask, render_template, request
from rtfcal import get_rtfs, html_to_result_list, results_to_ical
from dateparser import parse

application = Flask(__name__)
app = application


def get_search_params(request):
    return {
        "startdate": request.form['startdate'],
        "enddate": request.form['enddate'],
        "art": request.form['art'],
        "umkreis": request.form['umkreis'],
        "plz": request.form['plz'],
    }


def validate_dates(startdate, enddate):
    try:
        startdate = parse(startdate)
        enddate = parse(enddate)
    except:
        print 'AAAAaaaahhhh!'
        return
    assert startdate <= enddate
    return startdate, enddate


def validate_search_params(params):
    """
    TODO: more validation
    """
    startdate, enddate = validate_dates(params['startdate'], params['enddate'])
    params['startdate'] = startdate
    params['enddate'] = enddate
    return params


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    params = get_search_params(request)
    params = validate_search_params(params)
    ical = results_to_ical(html_to_result_list(get_rtfs(params=params)))
    return render_template('ical.html', ical=ical)
