from bs4 import BeautifulSoup
from dateparser import parse
from icalendar import Calendar, Event
from pytz import timezone
from datetime import datetime, timedelta
from uuid import uuid4


def pretty_print(rtf_dict):
    print unicode(rtf_dict) + '\n'


def string_format(str):
    return str.strip()


def get_date_and_distance(cell):
    day_and_date = cell.contents[0]
    # Not sure how to set all day events, and event visibility is bad when it starts at midnight,
    # so we let every RTF start at 8am
    date_and_time = parse(day_and_date).replace(hour=8)
    tz_aware_date_and_time = date_and_time.replace(tzinfo=timezone('Europe/Berlin'))
    dist_from_home = cell.contents[2]
    return tz_aware_date_and_time, dist_from_home[1:-1]


def create_description(rtf_attributes):
    description = rtf_attributes.get('rtf_type')
    if rtf_attributes.get('rtf_club'):
        description += '\n' + rtf_attributes['rtf_club']
    if rtf_attributes.get('rtf_lengths'):
        description += '\n' + rtf_attributes['rtf_lengths']
    return description


def html_to_ical(html):
    """
    TODO: multi-page results
    TODO: add reminder to events
    TODO: Add URI
    TODO: Add lengths in description
    """

    cal = Calendar()
    cal.add('prodid', '-//RTF Calendar//rtfcal.io//')
    cal.add('version', '2.0')

    soup = BeautifulSoup(html, 'lxml')
    results = soup.find_all('a', class_='terminlink')

    for e in results:

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

        pretty_print(rtf_attributes)

        event = Event()
        event.add('summary', rtf_attributes['rtf_name'])
        event.add('uid', uuid4())
        event.add('dtstart', date_and_time)
        event.add('dtend', date_and_time + timedelta(hours=1))
        event.add('dtstamp', datetime.now())
        event.add('url', rtf_attributes['rtf_link'])
        event.add('description', create_description(rtf_attributes))

        cal.add_component(event)

    print cal.to_ical()

    with open('rtfcal.ics', 'w') as cal_file:
        cal_file.write(cal.to_ical())
