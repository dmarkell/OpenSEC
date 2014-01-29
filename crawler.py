from xml.dom import minidom

import urllib
from google.appengine.api import urlfetch
import re
        
def crawl_txt(filing_url):

    url = filing_url.replace("-index.html",".txt").replace("-index.htm",".txt")
    r = urlfetch.fetch(url).content
    lines = r.split('\n')
    #INPUT: list of lines of text leading to filing in .txt format
    #OUTPUT: list of holdings as list and reported total mkt val and count
    #Looks for a CUSIP using a regexp and builds the line off that
    mv_rep = ct_rep = None
    last_used = 0
    holdings = []
    cus_re = r'((?:[a-zA-Z]\w{2}\d)|(?:9\w{3})|(?:0[a-zA-Z]\d\d)|\d{4})(\w{2}[-\s]?\w{2}[-\s]?\d)\s'
    #old cusip re: r'(\w{6})[-\s]?(\w{2})[-\s]?(\d)\s'
    cusip_p = re.compile(cus_re)
    numer_p = re.compile(r'-|\d+,?\d*,?\d*(?:.00)?')
    option_p = re.compile('CALL|PUT', re.IGNORECASE)
    issuer_p = re.compile(r'\s*\w+\s')
    head_p = re.compile(r'ISSUER', re.IGNORECASE)
    
    for index, line in enumerate(lines):
        try:
            issuer = cusip = value = shares = option = None
            #Get reported positions count and total mv
            match = re.search('Information Table Entry Total:[\s$]*([\d,]+)',
                              line)
            if match: ct_rep = int(''.join(match.groups()).replace(',',''))
            match = re.search('Information Table Value Total:[\s$]*([\d,]+)',
                              line)
            if match: mv_rep = int(''.join(match.groups()).replace(',',''))
            #TODO: below RE needs to exclude where preceded by "CIK", "IRS"
            #Current version catches "NASDAQ 100"
            match = cusip_p.search(line)
            if match:
                cusip = ''.join(match.groups()) 
                
                issuer = line[:match.start()].strip()
                for delim in ['  ', '...', '\t']:
                    issuer = issuer.split(delim)[0]
                issuer = issuer.strip()
                if issuer[:2] == "D ":
                    issuer = issuer[2:]
                
                #Below loop checks backwards over any skipped lines for issuer
                #name breaking onto 2 lines
                
                for skipped in range(index - 1, last_used, - 1):
                    frag = lines[skipped]
                    #Loop terminates at first preceding line that included 
                    #a cusip or contains no text. Note: CUSIP re pattern is 
                    #used here because it is possible that a zero-value
                    #holding (which has a CUSIP) was skipped but won't contain title
                    if cusip_p.search(frag) or head_p.search(frag) or not issuer_p.search(frag):
                        break
                    
                    frag = frag.strip()
                    for delim in ['  ', '...', '\t']:
                        frag = frag.split(delim)[0]
                    issuer = frag + ' ' + issuer                
                
                remainder = line[match.end():]

                match = numer_p.search(remainder)
                if match:
                    value = int(match.group().replace(',','').replace('-','0'))
                    match = numer_p.search(remainder[match.end():])
                    if match:
                        shares = match.group()
                        for old, new in ((',', ''), ('.00', ''), ('-', '0')):
                            shares = shares.replace(old, new)
                        shares = int(shares)
                        match = option_p.search(remainder[match.end():])
                        if match:
                            option = match.group()
                
                if value:#TODO: band-aid until above REGEX change is made
                    holdings.append([issuer, cusip, value, shares, option])
                    last_used = index
        
        except ValueError:
            continue
                
    return holdings, mv_rep, ct_rep

def crawl_xml(filing_url):
    """Crawls XML filing
    INPUT: filing_url to Primary and Information Table
    OUTPUT: list of holdings as list, and '_diff' variables reflecting differences in reported mkt val and coun
    """
    
    mv_rep = ct_rep = None

    page = urlfetch.fetch(filing_url).content
    slug_regexp = r'/Archives/edgar/data/[^/]*/[^/]*'
    slug = re.search(slug_regexp, filing_url).group()
    slugs = re.findall(r'{}{}'.format(slug, r'/[^/"]*.xml'), page)
    prim_url, info_url = ["http://www.sec.gov{}".format(slug) for slug in slugs]

    # Crawl "Information Table" page for holdings list
    holdings = []

    r = urlfetch.fetch(info_url).content
    xml = minidom.parseString(r)
    rows = xml.getElementsByTagName('infoTable')
    
    for row in rows:
        issuer = row.getElementsByTagName('nameOfIssuer')[0].firstChild.data
        cusip = row.getElementsByTagName('cusip')[0].firstChild.data
        value = row.getElementsByTagName('value')[0].firstChild.data
        value = int(value.replace(',', '').replace('-', ''))
        shares = row.getElementsByTagName('shrsOrPrnAmt')[0]
        shares = int(shares.getElementsByTagName('sshPrnamt')[0].firstChild.data)
        option = row.getElementsByTagName('putCall')
        option = str(option[0].firstChild.data).upper() if option else ''
        holdings.append([issuer, cusip, value, shares, option])

    #Crawl primary_doc page for reported mkt value and # position
    r = urlfetch.fetch(prim_url).content
    xml = minidom.parseString(r)
    summary = xml.getElementsByTagName('summaryPage')[0]
    ct = int(summary.getElementsByTagName('tableEntryTotal')[0].firstChild.data)
    mv = int(summary.getElementsByTagName('tableValueTotal')[0].firstChild.data)

    return holdings, mv, ct

def crawl_filing(filing_url):
    
    holdings = mv_rep = ct_rep = None
    
    doc_page = urlfetch.fetch(filing_url).content
    loc = doc_page.find("Period of Report")+50
    as_of = doc_page[loc:loc+10]
    
    #NOTE: this still isn't complete because the url to the actual file
    #should be saved to the db rather than url to the filing index; but should
    #be easy to later write a scraper of all filings at the approporaite filing
    #index (or even use ftp instead with CIK & accession number)

    if doc_page.find(">INFORMATION TABLE<") == -1:#Then it's a .txt file
        holdings, mv_rep, ct_rep = crawl_txt(filing_url)
    else:
        holdings, mv_rep, ct_rep = crawl_xml(filing_url)
    
    return holdings, as_of, mv_rep, ct_rep

def get_filings_list(url):
    """Uses URL to filings list to create list of filings with metadata
    INPUT: url to list of filings
    OUTPUT: manager name, cik and list of filing urls"""

    page = urlfetch.fetch(url).content
    
    # Get metadata
    manager_pattern = re.compile(r'<span class="companyName">([^<]*)')
    manager = manager_pattern.search(page).groups()[0].strip()
    cik = re.search(r'CIK=\d{10}', page).group()

    # Create table of filing urls and filing dates
    slugs = re.findall(r'([^"]*)"\s*id="documentsbutton"', page)
    dates = re.findall(r'<td>(\d{4}-\d{2}-\d{2})</td>', page)
    
    filings = []
    for ix, slug in enumerate(slugs):
        filing = [slug, dates[ix]]
        filings.append(filing)
    
    return manager, cik, filings

def get_manager(manager_raw):
    """Returns url to manager filings
    INPUT: (string) CIK or manger_name
    OUTPUT: (string) URL to list of 13F filings
    NOTES: If multiple matches (to manager name),
    list of matching possible managers is offered for selection.
    """
    
    cik = managerName = ''
    
    if re.match(r'\d{10}', manager_raw):
        cik = manager_raw
    else:
        managerName = manager_raw

    base = "http://www.sec.gov/cgi-bin/browse-edgar?"
    params = dict(company=managerName, CIK=cik,
        type='13f-hr', action='getcompany', count=100)
    params = urllib.urlencode(params)
    url = base + params
    
    # for development:
    #import urllib2
    #page = urllib2.urlopen(url).read()
    page = urlfetch.fetch(url).content
    
    # Return url; if multiple matches, redirect to choose_manager.
    # If no mathes return None
    if page.find("documentsbutton") <> -1:
        return url
    elif page.find('span class="companyMatch"') <> -1:
        return get_managers(page)
    else:
        return None

def get_managers(page):
    """List of matches for selection
    INPUT is page contents
    OUTPUT is urls to manager filings"""

    p = re.compile(r'href="([^"]*)">\d{10}</a></td>\n\s*<td[^>]*>([^<]*)')

    matches = p.findall(page)
    results = []
    for match in matches:
        result = list(match)
        result[0] = "http://www.sec.gov{}".format(result[0]) 
        results.append(result)

    return results