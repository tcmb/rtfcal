# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, make_response, abort
from rtfcal import get_rtfs, results_to_ical, get_default_params, ZIP_CODE_PATTERN
from dateparser import parse
import logging


logging.basicConfig(level=logging.WARN)


application = Flask(__name__)
app = application


def get_search_params(req):
    return {
        "startdate": req.form['startdate'],
        "enddate": req.form['enddate'],
        "art": req.form['art'],
        "umkreis": req.form['umkreis'],
        "plz": req.form['plz'],
    }


def validate_dates(startdate, enddate):

    def date_format(start, end):
        return start.strftime('%d.%m.%Y'), end.strftime('%d.%m.%Y')

    startdate = parse(startdate)
    # parse() just silently returns None for invalid dates like 31.06.2018
    assert startdate is not None, "Invalid start date"
    startdate = startdate.date()
    enddate = parse(enddate)
    assert enddate is not None, "Invalid end date"
    enddate = enddate.date()
    assert startdate is not None and enddate is not None, "Error parsing start or end date"
    assert startdate <= enddate, "Start date must be before end date"
    return date_format(startdate, enddate)


def check_plz_and_umkreis(params):
    """
    If either plz or umkreis are given in parameters, the other must be there as well.
    Umkreis of '-1' is interpreted as a non-value.
    """
    plz = params.get('plz').strip()
    umkreis = params.get('umkreis').strip()
    if (plz or umkreis) and umkreis != '-1':
        assert plz and umkreis, "PLZ and Umkreis require each other"


def validate_search_params(params):
    startdate, enddate = validate_dates(params['startdate'], params['enddate'])
    assert params['plz'].strip() == "" or ZIP_CODE_PATTERN.match(params['plz'].strip()), \
        "Zip code must be five-digit numeric"
    valid_kategorien = ['-1', '12', '14', '16']
    valid_kategorien.extend([str(i) for i in range(1, 11)])
    assert params['art'].strip() == "" or params['art'].strip() in valid_kategorien, "Invalid Art parameter"
    assert params['umkreis'].strip() == "" or params['umkreis'].strip() in ['-1', '20', '50', '100', '200', '400'], \
        "Invalid Umkreis parameter"
    check_plz_and_umkreis(params)
    params['startdate'] = startdate
    params['enddate'] = enddate
    default_params = get_default_params()
    default_params.update(params)
    return default_params


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    search_params = None
    try:
        search_params = get_search_params(request)
        search_params = validate_search_params(search_params)
    except (KeyError, ValueError, AssertionError) as e:
        # Defo the user's fault
        abort(400, unicode(e))
    ical = results_to_ical(get_rtfs(params=search_params), write_file=False)

    response = make_response(ical)
    cd = 'attachment; filename=rtfcal.ics'
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/calendar'

    return response
