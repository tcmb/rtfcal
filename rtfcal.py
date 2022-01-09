# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from dateparser import parse
from icalendar import Calendar, Event, Timezone, TimezoneDaylight, TimezoneStandard, Alarm
from datetime import datetime, timedelta
from uuid import uuid4
from re import compile
from requests import get
import logging


logger = logging.getLogger(__name__)


BASE_URL = 'http://breitensport.rad-net.de/breitensportkalender'

#  Rad-net's handling of default params:
# - rad-net requires none of the form parameters and happily searches without any parameters
# - if no dates are given, it assumes startdate = today and enddate = today + 3 months
# - rad-net does all form validation server side. default dates come back into the form and url with the result
# - it allows search without plz and umkreis, but only if both are empty
# - if a plz is given, also an umkreis needs to be given (Umkreis "Alle" is considered invalid if a plz is given)
# - if Umkreis is given, a plz needs to be given as well
# - kategorie can be empty and is treated as -1 ('alle kategorien'), but unlike the default dates, this does not
#   come back in the url
# - Landesverband has the same behavior as kategorie
MY_PARAMS = {
    'startdate': '01.01.2022',
    'enddate': '01.04.2022',
    'umkreis': '20',  # preselections: 20, 50, 100, 200, 400
    'plz': '63263',
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
PAGINATION_NODE_PATTERN = compile(r'\d+-\d+')
ZIP_CODE_PATTERN = compile(r'^\d{5}$')

TWELVE_WEEKS = timedelta(weeks=12)


def get_default_params():
    """
    For setting default start and end dates if none are provided in the form, we'd like to emulate rad-net's behavior
    of defaulting to a timeframe from today to three months from now.
    Python's timedelta doesn't take a 'months' argument. There's a recipe at
    http://code.activestate.com/recipes/577274-subtract-or-add-a-month-to-a-datetimedate-or-datet/
    for adding a month while respecting different number of days in a month. However, for our purposes,
    adding a plain twelve weeks is good enough.
    """
    startdate = datetime.today().date()
    enddate = startdate + TWELVE_WEEKS
    return {
        'startdate': startdate.strftime('%d.%m.%Y'),
        'enddate': enddate.strftime('%d.%m.%Y'),
        'go': 'Termine+suchen',
        'art': '-1',
        'lv': '-1',
    }


def get_date_and_distance(cell):
    day_and_date = cell.contents[0]
    # We make all events all-day events, because the actual time is not contained in Rad-Net's calendar
    startdate = parse(day_and_date, languages=['de']).date()
    enddate = startdate + timedelta(days=1)
    dist_from_home = cell.contents[2][1:-1] if len(cell.contents) > 1 else None
    return startdate, enddate, dist_from_home


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


def create_event(e):

    rtf_link = e.attrs.get('href')
    rtf_cells = e.find_all('div', class_='zelle')

    startdate, enddate, dist_from_home = get_date_and_distance(rtf_cells[1])

    rtf_attributes = {
        'rtf_type': rtf_cells[0].find('div', class_='tooltip').string,
        'rtf_date': startdate,
        'rtf_dist_from_home': dist_from_home,
        'rtf_name': rtf_cells[2].string if rtf_cells[2] else '',
        'rtf_lengths': rtf_cells[3].string if rtf_cells[3] else '',
        'rtf_club': rtf_cells[4].string if rtf_cells[4] else '',
        'rtf_link': rtf_link
    }

    event = Event()
    summary = rtf_attributes['rtf_name']
    if rtf_attributes.get('rtf_dist_from_home'):
        summary += ' (' + rtf_attributes['rtf_dist_from_home'] + ')'
    event.add('summary', summary)
    event.add('uid', uuid4())
    event.add('dtstart', startdate)
    event.add('dtend', enddate)
    event.add('dtstamp', datetime.now())
    event.add('url', rtf_attributes['rtf_link'])
    event.add('description', create_description(rtf_attributes))

    return event


def get_pagination_nodes(tag):
    """
    Returns all the pagination nodes. A pagination node is a sibling of the "Weitere Ergebnisse" element that
    contains a string like "1-30" or "31-60"
    """
    def is_pagination_node(elem):
        # We need the explicit cast to unicode because tag.string can be None, and then also strip() because of
        # leading and trailing newlines
        return elem.string and PAGINATION_NODE_PATTERN.match(str(elem.string).strip())

    return [t for t in tag.next_siblings if is_pagination_node(t)]


def on_last_page(tags):
    # Pagination nodes are either plain text (for the current page) or anchor tags (for previous and subsequent pages).
    # We know we're on the last page if the last element in the list of pagination links is a plain text element
    # instead of a hyperlink
    return isinstance(tags[-1], NavigableString)


def has_more_results(soup):
    """
    There's more results if we find the 'Weitere Ergebnisse' element and we're not on the last page of results
    """
    def has_more_results_text(tag):
        return tag.string and MORE_RESULTS_PATTERN.match(tag.string)

    more_results_node = soup.find(has_more_results_text)
    if more_results_node:
        logger.debug("Found more_results_node")
        pagination_nodes = get_pagination_nodes(more_results_node)
        is_last_page = on_last_page(pagination_nodes)
        logger.debug("is_last_page is %s" % is_last_page)
        return more_results_node and not is_last_page
    return False


def get_rtfs(lstart=None, results=None, params=None, local=False):

    lstart = lstart or 0
    results = results or []
    params = params or get_default_params()

    logger.debug("getting rtfs with lstart %s, params %s and %s previous results" % (lstart, params, len(results)))

    if local:
        with open("/Users/flo/code/rtfcal/Termine02.html") as i:
            html = i.read()
    else:
        html = get(BASE_URL, headers=HEADERS, params=params).content
    soup = BeautifulSoup(html, 'lxml')
    results.extend(find_rtfs(soup))

    if has_more_results(soup):
        logger.debug("page has more results, calling again")
        lstart += 30
        params.update({'lstart': lstart})
        get_rtfs(lstart=lstart, results=results, params=params)

    return results


def find_rtfs(soup):
    return soup.find_all('a', class_='terminlink')


def results_to_ical(result_list, write_file=False):

    logger.debug("Transforming %s results to iCal format" % len(result_list))

    cal = create_calendar()

    logger.debug("Got %s results:\n%s" % (len(result_list), result_list))

    for e in result_list:
        event = create_event(e)
        cal.add_component(event)

    if write_file:
        with open('rtfcal.ics', 'w') as cal_file:
            cal_file.write(cal.to_ical().decode('utf-8'))

    return cal.to_ical().decode('utf-8')


if __name__ == '__main__':
    logging.basicConfig(level=logging.info)
    results_to_ical(get_rtfs(params=MY_PARAMS, local=False), write_file=True)
