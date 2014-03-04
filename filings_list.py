from pprint import pprint
import re
import time
import urllib
import urllib2
from xml.dom import minidom
import xml.etree.ElementTree as ET

ROOT = "http://www.sec.gov/"
SEARCH_PATH = "cgi-bin/browse-edgar/?"
DATA_PATH = "Archives/edgar/data/"
params = dict(action="getcompany", count=100)

def unescape(text):
    def fixup(m):
        old = m.groups(0)[0]
        new = htmlentitydefs.entitydefs[old]
        return new
    return re.sub("&(\w+);", fixup, text)


def get_filings_list_minidom(ticker):

    params['output'] = 'atom'
    params['ticker'] = ticker

    filings_list = []
    
    for form in ['10-', '20-']:
        params['type'] = form
        enc_params = urllib.urlencode(params)
        url = "{}{}{}".format(ROOT, SEARCH_PATH, enc_params)
        
        _file = urllib2.urlopen(url)
        xml = minidom.parse(_file)

        name = xml.getElementsByTagName('conformed-name')[0]
        name = unescape(name.firstChild.nodeValue).upper()
        cik = xml.getElementsByTagName('cik')[0].firstChild.nodeValue

        # Thanks to https://github.com/fernavid/
        docs_list = xml.getElementsByTagName('entry')
        for doc in docs_list:
            try:
                doc.getElementsByTagName('content')[0]
                doc.getElementsByTagName('xbrl_href')[0]
                
            except IndexError:
                continue

            ix_url = doc.getElementsByTagName('filing-href')[0].firstChild.nodeValue
            f_date = doc.getElementsByTagName('filing-date')[0].firstChild.nodeValue

            
            _file = urllib2.urlopen(ix_url)
            source = _file.read()

            xml_slug = re.findall(r'{}.*?\d{{8}}\.xml'.format(DATA_PATH), source)[0]

            f_url = "{}{}".format(ROOT, xml_slug)
            
            filings_list.append((f_date, f_url))

    return filings_list

def get_filings_list_text(ticker):

    params['ticker']= ticker

    name_p = re.compile(r'"companyName">([\s\S]*?)<')
    cik_p = re.compile(r'CIK=(\d{10})')
    row_p = re.compile(r'<tr[\s\S]*?>[\s\S]*?</tr>')
    slug_p = re.compile(r'href="(\S*index.html?)"')
    date_p = re.compile(r'<td>(\d{4}-\d{2}-\d{2})</td>')
    xml_p = re.compile(r'{}.*?\d{{8}}\.xml'.format(DATA_PATH))

    filings_list = []
    
    for form in ['10-', '20-']:
        params['type'] = form
        enc_params = urllib.urlencode(params)
        url = "{}{}{}".format(ROOT, SEARCH_PATH, enc_params)
        
        _file = urllib2.urlopen(url)
        source = _file.read()
        name = name_p.findall(source)[0]
        name = unescape(name).upper()
        cik = cik_p.findall(source)[0]

        rows = row_p.findall(source)
        rows = filter(lambda x: x.find('interactiveDataBtn') <> -1, rows)

        urls = map(lambda x: "{}{}".format(ROOT[:-1], slug_p.findall(x)[0]), rows)
        dates = map(lambda x: date_p.findall(x)[0], rows)
                
        for ix, url in enumerate(urls):

            f_date = dates[ix]
            _file = urllib2.urlopen(url)
            f_source = _file.read()
            xml_slug = xml_p.findall(f_source)[0]
            f_url = "{}{}".format(ROOT, xml_slug)
            filings_list.append((f_date, f_url))

    return filings_list

#   get_filings_list_minidom('crox')
print get_filings_list_text('crox')
