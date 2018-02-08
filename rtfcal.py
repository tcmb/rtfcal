from parse_data import html_to_ical


with open("Termine.html") as fp:
    html_to_ical(fp)
