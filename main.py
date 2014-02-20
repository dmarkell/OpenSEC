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

CACHE = dict(
    crox=dict(
        meta=dict(cik='', ticker='crox', name='Crocs, Inc.', filing_dates=[(u'2013-09-30', '2013-10-30'), (u'2013-06-30', '2013-07-30'), (u'2013-03-31', '2013-04-29'), (u'2012-12-31', '2013-02-25'), (u'2012-09-30', '2012-10-30'), (u'2012-06-30', '2012-07-31'), (u'2012-03-31', '2012-05-01'), (u'2011-12-31', '2012-02-23'), (u'2011-09-30', '2011-10-31'), (u'2011-06-30', '2011-08-03')]),
        prices=dict(last=12.470),
        metrics=dict(revenues=[['311,656.0', '363,827.0', '288,524.0', None], ['271,798.0', '330,942.0', '295,569.0', '224,992.0']], revenue_totals=['964,007.0', '1,123,301.0'], eps=[[0.33, 0.4, 0.15, None], [0.31, 0.68, 0.49, -0.04]], eps_totals=[0.88, 1.44], years=[2013, 2012], months=[(3, 'MAR'), (6, 'JUN'), (9, 'SEP'), (12, 'DEC')], unit=(1000, 'thousands'), filedates=[[u'2013-04-29', u'2013-07-30', u'2013-10-30', None], [u'2012-05-01', u'2012-07-31', u'2012-10-30', u'2013-02-25']], shs='8,663.1', numcols=2)
    ),
    aapl=dict(
        meta={u'cik': u'0000320193', u'filing_dates': [[u'2013-12-28', u'2014-01-28'], [u'2013-09-28', u'2013-10-30'], [u'2013-06-29', u'2013-07-24'], [u'2013-03-30', u'2013-04-24'], [u'2012-12-29', u'2013-01-24'], [u'2012-09-29', u'2012-10-31'], [u'2012-06-30', u'2012-07-25'], [u'2012-03-31', u'2012-04-25'], [u'2011-12-31', u'2012-01-25'], [u'2011-09-24', u'2011-10-26'], [u'2011-06-25', u'2011-07-20'], [u'2011-03-26', u'2011-04-21'], [u'2010-12-25', u'2011-01-19'], [u'2010-09-25', u'2010-10-27'], [u'2010-06-26', u'2010-07-21'], [u'2010-03-27', u'2010-04-21'], [u'2009-12-26', u'2010-01-25'], [u'2009-09-26', u'2010-01-25'], [u'2009-09-26', u'2009-10-27'], [u'2009-06-27', u'2009-07-22']], u'ticker': u'aapl', u'name': u'APPLE INC'},
        prices={'last': 0.0},
        metrics={'shs': '892,447.0', 'revenue_totals': ['173,992.0', '164,687.0', '127,841.0', '76,283.0'], 'months': [(3, 'MAR'), (6, 'JUN'), (9, 'SEP'), (12, 'DEC')], 'eps': [[10.09, 7.47, 8.26, 14.5], [12.3, 9.32, 8.67, 13.81], [6.4, 7.79, 7.05, 13.87], [3.33, 3.51, 4.64, 6.43]], 'eps_totals': [40.32, 44.1, 35.11, 17.91], 'years': [2013, 2012, 2011, 2010], 'filedates': [[u'2013-04-24', u'2013-07-24', u'2013-10-30', u'2014-01-28'], [u'2012-04-25', u'2012-07-25', u'2012-10-31', u'2013-01-24'], [u'2011-04-21', u'2011-07-20', u'2011-10-26', u'2012-01-25'], [u'2010-04-21', u'2010-07-21', u'2010-10-27', u'2011-01-19']], 'revenues': [['43,603.0', '35,323.0', '37,472.0', '57,594.0'], ['39,186.0', '35,023.0', '35,966.0', '54,512.0'], ['24,667.0', '28,571.0', '28,270.0', '46,333.0'], ['13,499.0', '15,700.0', '20,343.0', '26,741.0']], 'unit': (1000, 'millions'), 'numcols':4}
    )
)

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

    logging.error(map(lambda x: x[2], clean_filing))

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
            self.render("manager.html", **self.params)


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

class CompanyResults(Handler):

    def get(self, ticker):
        
        # look in cache
        company = CACHE[ticker]

        if not company:
            company = fins.Company(ticker)
        
        self.render("company.html", **company)


app = webapp2.WSGIApplication(
    [
    ('/', Search),
    ('/company/(.+)', CompanyResults)
    ], debug=True)

