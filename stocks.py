import datetime
import re
import urllib
from google.appengine.api import urlfetch


def get_weekday(date):
    """ Returns nearest weekday in direction and magnitude of offset.
    Expects a datetime.date() object."""

    while date.weekday() > 4:
        date -= datetime.timedelta(days=1)

    return date

def get_prior_month_end(date):
    """Returns last calendar day of previous month
    Expects date as datetime.day() object. """

    return date - datetime.timedelta(days=date.day)

def get_month_end(date):
    """Returns last calendar day of current months
    Expects date as datetime.day() object. """

    next_month = date.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)

def end_of_month(date_str, months):
    """ Last calendar day of month that is 'months' months before date.
    Expects (1) dates as integers or strings in format YYYYMMDD
    or strings in format YYYY-MM-DD and (2) months offset as integer """

    #Convert to datetime.date() object
    format = '%Y%m%d'
    date = str(date_str).replace("-", "")
    date = datetime.datetime.strptime(date, format).date()
    
    #Gets end of current month (for months==0)
    temp = date.replace(day=28) + datetime.timedelta(days=4)
    date = temp - datetime.timedelta(days=temp.day)


    if months < 0:
        #print range(months)
        for i in xrange(abs(months)):
            date = date - datetime.timedelta(days=date.day)
    else:
        for i in xrange(months):
            date += datetime.timedelta(days=1)
            temp = date.replace(day=28) + datetime.timedelta(days=4)
            date = temp - datetime.timedelta(days=temp.day)

    return date

#Need to re-write without Pandas
def get_change(ticker, start_date_str, end_date_str):
    """ Returns % change for ticker, based on Yahoo adj. close, between dates
    Expects dates as integers or strings in format YYYYMMDD
    or strings in format YYYY-MM-DD """

    format = '%Y%m%d'
    start_date = str(start_date_str).replace("-", "")
    end_date = str(end_date_str).replace("-", "")
    start_date = datetime.datetime.strptime(start_date, format).date()
    end_date = datetime.datetime.strptime(end_date, format).date()
    if start_date >= end_date:
        return None
    if end_date == datetime.datetime.today().date():
        end_date += datetime.timedelta(days=-1)
    start_date = get_weekday(start_date)
    end_date = get_weekday(end_date)
    
    try:
        stock = DataReader(ticker, "yahoo", start_date, end_date)
    except IOError:
        return "NA:Sec"
    
    try:
        start_price = stock["Adj Close"][start_date]
    except KeyError:
        return "NA:Beg"
    
    try:
        end_price = stock["Adj Close"][end_date]
    except KeyError:
        return "NA:End"
    
    return 1. * end_price / start_price - 1

def cusip_to_ticker(cusip):

    ticker = ""

    base_url = "http://activequote.fidelity.com/mmnet/SymLookup.phtml?"
    params = {'reqforlookup': 'REQUESTFORLOOKUP', 'for': "stock",
              'by': 'cusip', 'criteria': cusip}
    params = urllib.urlencode(params)
    page = urlfetch.fetch(base_url + params).content

    results = re.findall(r'<a[^>]*SID_VALUE_ID=([^"]*)', page)
    if results:
        ticker = results[0]

    return ticker

