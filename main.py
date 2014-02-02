import crawler
import datetime
import jinja2
import logging
from operator import itemgetter
import os
import re
import stocks
import webapp2

from google.appengine.ext import ndb

# Template utils
template_dir = os.getcwd() + '/templates'
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir),
    autoescape=True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def secs_key(group = 'default'):
    return ndb.Key('secs', group)

def clean_filing(filing):
    """Adds up market value and percentages column and sorts by market value
    INPUT: list of holdings
    OUPUT: cleaned and sorted list and total market value"""

    clean_filing = []
    mv_tot = ct = pct_tot = 0

    # First pass creates clean list, adds/counts market value and adds tickers
    # TODO: sum over duplicate cusips
    for holding in filing:
        row = []
        row += holding[:2]
        cusip = holding[1]

        # Look in db...
        security = Security.query(
            Security.cusip == cusip, ancestor=secs_key()).get()
        if security:
            ticker = security.ticker
        else:
            # On db miss run cusip_to_ticker...
            ticker = stocks.cusip_to_ticker(cusip)
            if ticker:
                # ... and add to db: 
                security = Security(parent=secs_key())
                security.cusip=cusip
                security.ticker=ticker
                security.put()

        row.append(ticker)
        mv = int(str(holding[2]).replace(",", ""))
        mv_tot += mv
        ct += 1
        row.append(mv)
        row.append('')
        row.append(holding[4])
        clean_filing.append(row)
    
    # Sort on market value
    clean_filing.sort(key=itemgetter(3), reverse=True)

    # 2nd pass adds percentages and formatting
    for row in clean_filing:
        pct = 100. * row[3] / mv_tot
        pct_tot += pct
        row[3] = "{:,}".format(row[3])
        row[4] = "{:.1f}%".format(pct)

    mv_tot = "{:,}".format(mv_tot)
    pct_tot = "{:.1f}%".format(pct_tot)

    return clean_filing, ct, mv_tot, pct_tot

class Handler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render(self, template, **kw):
        self.write(render_str(template, **kw))

class Security(ndb.Model):
    cusip = ndb.StringProperty(required = True)
    ticker = ndb.StringProperty(required = True)

class Filing:

    def __init__(self, slug):
        self.slug = slug
        self.url = "http://www.sec.gov{}".format(self.slug)
        holdings, asof, mv_rep, ct_rep = crawler.crawl_filing(self.url)
        body, ct, mv_tot, pct_tot = clean_filing(holdings)
        meta = dict(asof=asof, count=ct, mv_tot=mv_tot, pct_tot=pct_tot,
                 mv_rep=mv_rep, ct_rep=ct_rep)
        self.body = body
        self.meta = meta
        mv_rep = self.meta['mv_rep']
        self.meta['mv_rep'] = "{:,}".format(mv_rep) if mv_rep else 'None'

class Search(Handler):

    params = dict(enumerate=enumerate, show=20)

    def get(self):
        self.render("search.html")

    def post(self):
        
        """
        User enters manager name.
        * If manager name search returns nothing, error is added and query is
        reset.
            - Next submit restarts the query check
        * If manager name search returns multiple hits, query is reset adding
        a list of manager selections.
            - Next submit restarts the query inserting an explicit mgr_url
        * Else (if manager name search returns a single result), the result
        is assigned to mgr_url.

        mgr_url is used to get list of filings with dates, and form is reset
        including manager name and a selector of dates.
        * selected filing is submitted and script next returns results, and
        resets search form.
        """

        self.filing_slug = self.request.get('filing_slug')

        if self.filing_slug:
            self.params['manager_full'] = self.request.get('manager_full')
            
            filing = Filing(self.filing_slug)

            self.params['filing'] = filing
            self.render("results.html", **self.params)


        else:
            self.mgr_url = self.request.get('mgrurl')
            self.manager = self.request.get('manager')
            if not self.mgr_url:
                self.mgr_url = crawler.get_manager(self.manager)
                if not self.mgr_url:
                    self.render('search.html',
                        **dict(error='No matches found for "{}"'.\
                            format(self.manager)))

                if isinstance(self.mgr_url, list):
                    self.render('search.html', **dict(mgr_matches=self.mgr_url,
                        message='{} matches found for "{}"'.\
                        format(len(self.mgr_url), self.manager)))

            if isinstance(self.mgr_url, basestring):
                manager, cik, filings = crawler.get_filings_list(self.mgr_url)
                size = len(filings)
                self.render('search.html', **dict(manager_full=manager,
                    filings=filings, message='{} filings found for {}'.\
                    format(size, manager)))


app = webapp2.WSGIApplication(
    [
    ('/?.*', Search)
    ], debug=True)