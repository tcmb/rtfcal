from bs4 import BeautifulSoup


def pretty_print(rtf_dict):
    print unicode(rtf_dict) + '\n'

def string_format(str):
    return str.strip()

def get_date_and_distance(cell):
    day_and_date = cell.contents[0]
    dist_from_home = cell.contents[2]
    weekday, date = day_and_date.split()
    return weekday[:-1], date, dist_from_home[1:-1]


with open("Termine.html") as fp:
    soup = BeautifulSoup(fp, 'lxml')

results = soup.find_all('a', class_='terminlink')


# entries are search results, rtfs that match the search criteria
for e in results:

    rtf_link = e.attrs.get('href')
    rtf_cells = e.find_all('div', class_='zelle')

    weekday, date, dist_from_home = get_date_and_distance(rtf_cells[1])

    rtf_attributes = {
        'rtf_type': rtf_cells[0].find('div', class_='tooltip').string,
        'rtf_weekday': weekday,
        'rtf_date': date,
        'rtf_dist_from_home': dist_from_home,
        'rtf_name': rtf_cells[2].string,
        'rtf_lengths': rtf_cells[3].string,
        'rtf_club': rtf_cells[4].string,
        'rtf_link': rtf_link
    }

    pretty_print(rtf_attributes)


# multi-page results
