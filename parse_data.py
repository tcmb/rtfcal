from bs4 import BeautifulSoup


def pretty_print(rtf_dict):
    print rtf_dict

def string_format(str):
    return str.strip()

with open("Termine.html") as fp:
    soup = BeautifulSoup(fp, 'lxml')

results = soup.find_all('a', class_='terminlink')


# entries are search results, rtfs that match the search criteria
for e in results:

    rtf_link = e.attrs.get('href')
    rtf_cells = e.find_all('div', class_='zelle')

    rtf_attributes = {
        'rtf_type': rtf_cells[0].find('div', class_='tooltip').string,
        'rtf_date_and_distance': rtf_cells[1].string,
        'rtf_name': rtf_cells[2].string,
        'rtf_lengths': rtf_cells[3].string,
        'rtf_club': rtf_cells[4].string,
        'rtf_link': rtf_link
    }

    pretty_print(rtf_attributes)


# multi-page results
