from parse_data import html_to_ical


if __name__ == '__main__':
    from sys import argv
    if (len(argv) < 2) or not ('-l' in argv or '-r' in argv):
        print 'Please say -l or -r for local or remote data source.'
    elif argv[1] == '-l':
        with open("Termine_long.html") as fp:
            html_to_ical(fp)
    elif argv[1] == '-r':
        from get_data import get_rtfs
        html_to_ical(get_rtfs())
