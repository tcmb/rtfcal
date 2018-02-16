# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, make_response
from rtfcal import get_rtfs, results_to_ical, DEFAULT_PARAMS
from dateparser import parse
from copy import deepcopy

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


def date_format(startdate, enddate):
    return startdate.strftime('%d.%m.%Y'), enddate.strftime('%d.%m.%Y')


def validate_dates(startdate, enddate):
    try:
        startdate = parse(startdate).date()
        enddate = parse(enddate).date()
    except:
        print 'AAAAaaaahhhh!'
        return
    assert startdate <= enddate
    return date_format(startdate, enddate)


def validate_search_params(params):
    """
    TODO: more validation
    """
    default_params = deepcopy(DEFAULT_PARAMS)
    startdate, enddate = validate_dates(params['startdate'], params['enddate'])
    params['startdate'] = startdate
    params['enddate'] = enddate
    default_params.update(params)
    return default_params


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    search_params = get_search_params(request)
    search_params = validate_search_params(search_params)
    ical = results_to_ical(get_rtfs(params=search_params))

    response = make_response(ical)
    cd = 'attachment; filename=rtfcal.ics'
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/calendar'

    return response
