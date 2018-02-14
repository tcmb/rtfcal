# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, make_response
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
    # TODO: kind of ugly that we're passing the same params into two functions here...
    ical = results_to_ical(html_to_result_list(get_rtfs(params=params)), original_params=params)
    response = make_response(ical)
    cd = 'attachment; filename=rtfcal.ics'
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/calendar'

    return response
