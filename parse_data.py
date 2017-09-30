from bs4 import BeautifulSoup

with open("Termine.html") as fp:
    soup = BeautifulSoup(fp, 'lxml')

entries = soup.find_all('li', class_='tabzeile')

# for e in entries: url, date, location

# multi-page results
