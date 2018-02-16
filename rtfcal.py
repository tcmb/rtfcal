# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from dateparser import parse
from icalendar import Calendar, Event, Timezone, TimezoneDaylight, TimezoneStandard, Alarm
from pytz import timezone
from datetime import datetime, timedelta
from uuid import uuid4
from copy import deepcopy
from re import compile
from requests import get


BASE_URL = 'http://breitensport.rad-net.de/breitensportkalender'

DEFAULT_PARAMS = {
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, '
                  'like Gecko) Chrome/64.0.3282.167 Safari/537.36'
}

MORE_RESULTS_PATTERN = compile('Weitere Ergebnisse.*')
PAGINATION_NODE_PATTERN = compile('\d+-\d+')


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


def get_pagination_nodes(tag):
    """
    Returns all the pagination nodes. A pagination node is a sibling of the "Weitere Ergebnisse" element that
    contains a string like "1-30" or "31-60"
    """
    def is_pagination_node(elem):
        # We need the explicit cast to unicode because tag.string can be None
        return elem.string and PAGINATION_NODE_PATTERN.match(unicode(elem.string))

    return [t for t in tag.next_siblings if is_pagination_node(t)]


def on_last_page(tags):
    # Pagination nodes are either plain text (for the current page) or anchor tags (for previous and subsequent pages).
    # We know we're on the last page if the last element in the list of pagination links is a plain text element
    # instead of a hyperlink
    return isinstance(tags[-1], NavigableString)


def has_more_results(html):
    """
    There's more results if we find the 'Weitere Ergebnisse' element and we're not on the last page of results
    """
    def has_more_results_text(tag):
        return tag.string and MORE_RESULTS_PATTERN.match(tag.string)

    soup = BeautifulSoup(html, 'lxml')
    more_results_node = soup.find(has_more_results_text)
    if more_results_node:
        pagination_nodes = get_pagination_nodes(more_results_node)
        is_last_page = on_last_page(pagination_nodes)
        return more_results_node and not is_last_page
    return False


def get_rtfs(lstart=None, results=None, params=None):

    lstart = lstart or 0
    results = results or []
    params = params or deepcopy(DEFAULT_PARAMS)

    print "getting rtfs with lstart %s, params %s and %s previous results" % (lstart, params, len(results))

    html = get(BASE_URL, headers=HEADERS, params=params).content
    results.extend(html_to_result_list(html))

    if has_more_results(html):
        print "page has more results, calling again"
        lstart += 30
        params.update({'lstart': lstart})
        get_rtfs(lstart=lstart, results=results, params=params)

    return results


def html_to_result_list(html):
    soup = BeautifulSoup(html, 'lxml')
    return soup.find_all('a', class_='terminlink')


def results_to_ical(result_list):

    print "Transforming %s results to iCal format" % len(result_list)

    cal = create_calendar()

    print "Got %s results:\n%s" % (len(result_list), result_list)

    for e in result_list:
        event = create_event(e)
        cal.add_component(event)

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
        results_to_ical(get_rtfs())
