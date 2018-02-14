# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from dateparser import parse
from icalendar import Calendar, Event, Timezone, TimezoneDaylight, TimezoneStandard, Alarm
from pytz import timezone
from datetime import datetime, timedelta
from uuid import uuid4
from copy import deepcopy
import requests


BASE_URL = 'http://breitensport.rad-net.de/breitensportkalender'

default_params = {
    'startdate': '01.01.2018',
    'enddate': '31.12.2018',
    'umkreis': '50',  # preselections: 20, 50, 100, 200, 400
    'plz': '12055',
    'go': 'Termine+suchen',
    'art': '-1',
    'lv': '-1',
    # 'titel': '',
    # 'tid': '',
    # 'formproof': '',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}


def get_rtfs(params=None):
    # copy or deepcopy shouldn't make a difference for current state of default_params, but you never know what
    # might go in there later.
    print "got handed params %s" % params
    request_params = deepcopy(default_params)
    request_params.update(params or {})
    print "searching with params %s" % request_params
    response = requests.get(BASE_URL, headers=headers, params=request_params)
    return response.content


def get_date_and_distance(cell):
    day_and_date = cell.contents[0]
    # Not sure how to set all day events, and event visibility is bad when it starts at midnight,
    # so we let every RTF start at 8am
    date_and_time = parse(day_and_date).replace(hour=8)
    tz_aware_date_and_time = date_and_time.replace(tzinfo=timezone('Europe/Berlin'))
    # TODO: If searching without an Umkreis, this field is empty (index error).
    dist_from_home = cell.contents[2]
    return tz_aware_date_and_time, dist_from_home[1:-1]


def create_description(rtf_attributes):
    description = rtf_attributes.get('rtf_type')
    if rtf_attributes.get('rtf_club'):
        description += '\n' + rtf_attributes['rtf_club']
    if rtf_attributes.get('rtf_lengths'):
        description += '\n' + rtf_attributes['rtf_lengths'] + 'km'
    return description


def add_timezone(cal):
    """
    copy-pasted from icalendar/tests/test_timezoned.py
    """
    tzc = Timezone()
    tzc.add('tzid', 'Europe/Berlin')
    tzc.add('x-lic-location', 'Europe/Berlin')

    tzs = TimezoneStandard()
    tzs.add('tzname', 'CET')
    tzs.add('dtstart', datetime(1970, 10, 25, 3, 0, 0))
    tzs.add('rrule', {'freq': 'yearly', 'bymonth': 10, 'byday': '-1su'})
    tzs.add('TZOFFSETFROM', timedelta(hours=2))
    tzs.add('TZOFFSETTO', timedelta(hours=1))

    tzd = TimezoneDaylight()
    tzd.add('tzname', 'CEST')
    tzd.add('dtstart', datetime(1970, 3, 29, 2, 0, 0))
    tzs.add('rrule', {'freq': 'yearly', 'bymonth': 3, 'byday': '-1su'})
    tzd.add('TZOFFSETFROM', timedelta(hours=1))
    tzd.add('TZOFFSETTO', timedelta(hours=2))

    tzc.add_component(tzs)
    tzc.add_component(tzd)
    cal.add_component(tzc)
    return cal


def create_calendar():
    cal = Calendar()
    cal.add('prodid', '-//RTF Calendar//rtfcal.io//')
    cal.add('version', '2.0')
    cal = add_timezone(cal)
    return cal


def add_alarm(event):
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alert_time = timedelta(days=-1)
    alarm.add('trigger', alert_time)
    event.add_component(alarm)
    return event


def create_event(e):

    rtf_link = e.attrs.get('href')
    rtf_cells = e.find_all('div', class_='zelle')

    date_and_time, dist_from_home = get_date_and_distance(rtf_cells[1])

    rtf_attributes = {
        'rtf_type': rtf_cells[0].find('div', class_='tooltip').string,
        'rtf_date': date_and_time,
        'rtf_dist_from_home': dist_from_home,
        'rtf_name': rtf_cells[2].string if rtf_cells[2] else '',
        'rtf_lengths': rtf_cells[3].string if rtf_cells[3] else '',
        'rtf_club': rtf_cells[4].string if rtf_cells[4] else '',
        'rtf_link': rtf_link
    }

    event = Event()
    event.add('summary', rtf_attributes['rtf_name'] + ' (' + rtf_attributes['rtf_dist_from_home'] + ')')
    event.add('uid', uuid4())
    event.add('dtstart', date_and_time)
    event.add('dtend', date_and_time + timedelta(hours=1))
    event.add('dtstamp', datetime.now())
    event.add('url', rtf_attributes['rtf_link'])
    event.add('description', create_description(rtf_attributes))

    add_alarm(event)

    return event


def html_to_result_list(html):
    soup = BeautifulSoup(html, 'lxml')
    return soup.find_all('a', class_='terminlink')


def results_to_ical(result_list, original_params=None):

    lstart = 0
    cal = create_calendar()
    original_params = original_params or {}

    print "Got %s results:\n%s" % (len(result_list), result_list)

    while result_list:

        for e in result_list:
            event = create_event(e)
            cal.add_component(event)

        # assuming the RTF page always returns 30 results per page. Haven't seen anything else or a parameter to
        # change it, and it's the simplest way to check for more results.
        # However, it also always does 1 request more than necessary, just to find that there are no more results.
        lstart += 30
        original_params.update({'lstart': lstart})
        html = get_rtfs(params=original_params)
        result_list = html_to_result_list(html)

    with open('rtfcal.ics', 'w') as cal_file:
        cal_file.write(cal.to_ical())

    return cal.to_ical().decode('utf-8')


if __name__ == '__main__':
    from sys import argv
    if (len(argv) < 2) or not ('-l' in argv or '-r' in argv):
        print 'Please say -l or -r for local or remote data source.'
    elif argv[1] == '-l':
        print "This is now broken!!!"
        # with open("Termine_long.html") as fp:
        #     results_to_ical(html_to_result_list(fp))
    elif argv[1] == '-r':
        results_to_ical(html_to_result_list(get_rtfs()))
