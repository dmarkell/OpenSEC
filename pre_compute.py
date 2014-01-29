
import urllib
import urllib2


def pre_computer_manager(manager):
    import bs4

    print "Adding {} ".format(manager),

    base = 'http://edgar-dash.appspot.com'
    params = urllib.urlencode(dict(manager=manager))
    soup = bs4.BeautifulSoup(urllib2.urlopen(base, params))
    
    slugs = map(lambda x: x['value'], soup.findAll('option'))
    print "({} filings)".format(len(slugs))

    for slug in slugs:
        print "\tCalling {}...".format(slug)
        params = urllib.urlencode(dict(filing_slug=slug))
        page = urllib2.urlopen(base, params)

    print "Done."


def main():
    managers = raw_input("Manager Names separated by pipes: ").split("|")
    for manager in managers:
        pre_computer_manager(manager)

if __name__ == "__main__":
    main()
