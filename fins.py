import datetime
import htmlentitydefs
import json
import logging
import os
import re
import time
import urllib

from xml.dom import minidom
import xml.etree.ElementTree as ET

try:
    from google.appengine.api import urlfetch
    production = True

except ImportError:
    import urllib2
    production = False


# CONSTANTS
ROOT = "http://www.sec.gov/"
SEARCH_PATH = "cgi-bin/browse-edgar/?"
DATA_PATH = "Archives/edgar/data/"

# simplified version of http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text):
    def fixup(m):
        old = m.groups(0)[0]
        new = htmlentitydefs.entitydefs[old]
        return new
    return re.sub("&(\w+);", fixup, text)

class Filing:

    def __init__(self, url):
        
        self.ACCOUNTING_FIELDS = [
            ('SharesOutstanding', (
                'CommonStockSharesOutstanding',
                'EntityCommonStockSharesOutstanding'), None, True),
            ('Revenues', (
                'Revenues', 'SalesRevenueNet', 'SalesRevenueServicesNet', 
                'RevenuesNetOfInterestExpense', 'TotalRevenuesAndOtherIncome',
                'RevenuesNet', 'SalesRevenueGoodsNet'), None, False),
            ('WeightedAverageDilutedShares', (
                'WeightedAverageNumberOfDilutedSharesOutstanding',
                'WeightedAverageNumberOfDilutedSharesOutstanding',
                'WeightedAverageNumberBasicDilutedSharesOutstanding',
                'WeightedAverageNumberBasicDilutedSharesOutstanding'),
                self.collapse, False),
            ('EarningsPerShare', (
                'EarningsPerShareDiluted', 'EarningsPerShareBasicAndDiluted',
                'BasicDilutedEarningsPerShareNetIncome',
                'BasicAndDilutedLossPerShare'), None, False),
            ('NetIncomeLoss', (
                'ProfitLoss', 'NetIncomeLoss',
                'NetIncomeLossAvailableToCommonStockholdersBasic',
                'IncomeLossFromContinuingOperations',
                'IncomeLossAttributableToParent', 'IncomeLossFromContinuingOperationsIncludingPortionAttributableToNoncontrollingInterest'),
                None, False),
            ('Assets', ('Assets'), None, False),
            ('CurrentAssets', ('AssetsCurrent'), None, False),
            ('PPE', ('PropertyPlantAndEquipmentNet'), None, False),
            ('Inventory', ('InventoryNet'), None, False),
            ('AccountsReceivable', ('AccountsReceivableNetCurrent'), None, False),
            ('Goodwill', ('Goodwill'), None, False),
            ('IntangiblesExGoodwill',
                ('IntangibleAssetsNetExcludingGoodwill'), None, False),
            ('AccountsPayable',
                ('AccountsPayableCurrent'), None, False),
            ('CashAndCashEquivalents',
                ('CashAndCashEquivalentsAtCarryingValue'), None, False),
            ('LongTermDebtCurrent',
                ('LongTermDebtCurrent'), None, False),
            ('LongTermDebtNonCurrent',
                ('LongTermDebtNoncurrent'), None, False),
            ('OperatingLeasesOneYear',
                ('OperatingLeasesFutureMinimumPaymentsDueInOneYear'), None, False),
            ('OperatingLeasesTwoYear',
                ('OperatingLeasesFutureMinimumPaymentsDueInTwoYears'), None, False),
            ('OperatingLeasesThreeYear',
                ('OperatingLeasesFutureMinimumPaymentsDueInThreeYears'), None, False),
            ('OperatingLeasesFourYear',
                ('OperatingLeasesFutureMinimumPaymentsDueInFourYears'), None, False),
            ('OperatingLeasesFiveYear',
                ('OperatingLeasesFutureMinimumPaymentsDueInFiveYears'), None, False),
            ('OperatingLeasesLongTerm',
                ('OperatingLeasesFutureMinimumPaymentsDueThereafter'), None, False),
            ('ShortTermInvestments', ('ShortTermInvestments'), None, False),
            ('LongTermInvestments', ('LongTermInvestments'), None, False)
        ]

        start = time.time()
        print "parsing filing...",
        self._load_root(url)
        print "{} seconds".format(time.time() - start)
        self.fields = {}
        self.get_instances()
        self.get_fields()


    def _load_root(self, url):

        if production:
            data = urlfetch.fetch(url).content
        else:
            data = urllib2.urlopen(url).read()

        root = ET.fromstring(data)

        self.root = root

    def get_fields(self):

        for field, queries, callback, non_core in self.ACCOUNTING_FIELDS:
            i = 0
            matches = self.name_matches(queries[i])
            while i < len(queries) - 1 and not matches:
                i += 1
                matches = self.name_matches(queries[i], non_core=non_core)
                if callback:
                    matches = callback(matches)

            self.fields[field] = matches

    def collapse(self, fields):
        """ Adds values of fields fields with same period
        INPUTS: Fields, list of (period, value) tuples
        OUTPUTS: list of (period, value) tuples
        """

        periods = list(set(map(lambda x: x[0], fields)))
        results = []
        for period in periods:
            values = [el[1] for el in fields if el[0] == period]
            total = sum(values)
            results.append((period, total))

        return sorted(results, reverse=True) 

    def impute(self, sign, field1, field2, func=None):
        """ Adds or subtracts corresponding periods, disregarding periods not
        appearing in both fields.
        INPUTS:
            - Field1 and Field2 are (period, value) tuples.
            - Fields' periods are (end_date, start_date) tuples.
            - Applies function 'func' if provided, otherwise adds if sign == 1
              and subtracts if sign == -1
        OUTPUT:
            - List of (period, value) tuples where values are the sum (diff)
              of the corresponding period input values
        """

        if not func:
            func = lambda x, y: x + sign * y

        periods = list(set(map(lambda x: x[0], field1 + field2)))
        output = []
        for period in periods:
            first = filter(lambda x: x[0] == period, field1)
            if len(first) == 1:
                second = filter(lambda x: x[0] == period, field2)
                if len(second) == 1:
                    output.append((period, func(first[0][-1], second[0][-1])))

        return output

    def get_instances(self):

        """ ET root as input
        Returns list of ('name', 'period', 'value', 'segment') tuples"""

        self.instances = []
        
        for node in self.root.iter():
            # asof from DocumentPeriodEndDate (no unitRef attr):
            if node.tag.endswith('DocumentPeriodEndDate'):
                self.fields['asof'] = node.text
            # nodes with values all have unitRef attrs:
            elif node.attrib.has_key('unitRef') and node.text:

                # Get name and value from tag name and inner text contents
                name = node.tag.split('}')[-1]
                value = float(node.text)
                # Initialize period to empty list and segment to empty string
                period, segment = [], ''
                
                # Get period and segment (if any) from context
                context = self.root.find("*[@id='{}']".format(node.attrib['contextRef']))
                
                for el in context.iter():
                
                    if el.tag.endswith("explicitMember"):
                        segment = el.text
                    if el.tag.endswith("instant"):
                        period = [el.text, el.text]
                    if el.tag.endswith("startDate"):
                        period.append(el.text)
                    if el.tag.endswith("endDate"):
                        period.insert(0, el.text)

                period = tuple(period)

                self.instances.append((name, period, value, segment))


    def name_matches(self, query, non_core=False):
 
        regexp = "^{}$".format(query)
        p = re.compile(regexp)

        matches = filter(lambda x: p.match(str(x[0])), self.instances)
        if not non_core:
            matches = filter(lambda x: not x[-1], matches)

        results = [el[1:3] for el in matches]

        return results

    def accounting_adj(self):
        """Clean ups to accounting fields after all other attempts finished"""
        # If wav shares above didn't work, impute NIL and EPS
        self.fields['WeightedAverageDilutedShares'] = self.impute(
            1, self.fields['NetIncomeLoss'], self.fields['EarningsPerShare'],
            func=self.divide)


class Company:

    def __init__(self, ticker):

        self.filings_list = []
        self.meta = dict(ticker=ticker.upper(), filing_dates=[])
        self.filings = dict() # all fields found by AccountingFields
        self.prices = dict() # TODO: This will contain Yahoo! dataframe
        self.get_filings()

    def get_filings(self):

        if not self.filings_list:
            self.get_filings_list()

        for fdate, furl in self.filings_list:
            key = "{}|{}".format(fdate, furl)
            filing = Filing(furl)
            self.filings[key] = filing.fields
            self.meta['filing_dates'].append((filing.fields['asof'], fdate))

    def get_filings_list(self):

        params = dict(action="getcompany", count=100)
        params['ticker']= self.meta['ticker']

        name_p = re.compile(r'"companyName">([\s\S]*?)<')
        cik_p = re.compile(r'CIK=(\d{10})')
        row_p = re.compile(r'<tr[\s\S]*?</tr>')
        slug_p = re.compile(r'href="(\S*index.html?)"')
        date_p = re.compile(r'<td>(\d{4}-\d{2}-\d{2})</td>')
        xml_p = re.compile(r'{}.*?\d{{8}}\.xml'.format(DATA_PATH))
        
        for form in ['10-', '20-']:
            params['type'] = form
            enc_params = urllib.urlencode(params)
            url = "{}{}{}".format(ROOT, SEARCH_PATH, enc_params)
            
            if production:
                source = urlfetch.fetch(url).content
            else:
                source = urllib2.urlopen(url).read()

            name = name_p.findall(source)[0]
            self.meta['name'] = unescape(name).upper()
            self.meta['cik'] = cik_p.findall(source)[0]

            rows = row_p.findall(source)
            rows = filter(lambda x: x.find('interactiveDataBtn') <> -1, rows)
            
            urls = map(lambda x: "{}{}".format(ROOT[:-1], slug_p.findall(x)[0]), rows)
            dates = map(lambda x: date_p.findall(x)[0], rows)
                
            for ix, url in enumerate(urls):

                f_date = dates[ix]

                if production:
                    f_source = urlfetch.fetch(url).content
                else:
                    f_source = urllib2.urlopen(url).read()

                xml_slug = xml_p.findall(f_source)[0]
                f_url = "{}{}".format(ROOT, xml_slug)
                self.filings_list.append((f_date, f_url))

    def dump(self):

        with open(self.filename, 'w') as f:
            data = dict(meta=self.meta,
                filings=self.filings, prices=self.prices)
            f.write(json.dumps(data))

    def get_metrics(self):
        """ Add metrics for html presentation """ 

        self.metrics = dict() # fields prepared for html templates
        revenues = self.hist_quarters('Revenues')
        logging.error(revenues)
        dates = [el[0][0] for el in revenues]
        dts = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in dates]
        self.metrics['years'] = sorted(list(set([dt.year for dt in dts])),
            reverse=True)[:5]
        self.metrics['months'] = sorted(list(set([(dt.month,
            dt.strftime('%b').upper()) for dt in dts])))
        self.metrics['numcols'] = len(self.metrics['years'])

        # loop the below?
        self.to_array('revenues', revenues)
        self.metrics['revenue_totals'] = map(lambda l: sum(filter(None, l)), self.metrics['revenues'])
        self.to_array('eps', self.hist_quarters('EarningsPerShare'))
        self.metrics['eps_totals'] = map(lambda l: sum(filter(None, l)), self.metrics['eps'])
        
        filing_dates = map(lambda x: (x[0], x[2]), revenues)
        self.to_array('filedates', filing_dates)
        
        self.metrics['unit'] = self.get_unit()
        self.metrics['revenue_totals'] = map(self.fmt_val, self.metrics['revenue_totals'])
        self.metrics['revenues'] = [map(self.fmt_val, items) for items in self.metrics['revenues']]

        shs = sorted(self.filings.items(), reverse=True)[0][1]['SharesOutstanding']
        shs = sorted(shs, reverse=True)[0][1]
        self.metrics['shs'] = self.fmt_val(shs)
        self.metrics['eps_totals'] = map(self.fmt_per_sh, self.metrics['eps_totals'])
        self.metrics['eps'] = [map(self.fmt_per_sh, items) for items in self.metrics['eps']]

        # TODO: add pricing
        self.prices['last'] = 0.0

    def to_array(self, key, fields):

        self.metrics[key] = []

        for yr in self.metrics['years']:
            year = []
            for mo in self.metrics['months']:
                val = filter(lambda x: int(x[0][0][:4]) == yr and int(x[0][0][5:7]) == mo[0], fields)
                year.append(val[0][1] if len(val) == 1 else None)
            self.metrics[key].append(year)

    def fmt_val(self, value):

        unit = self.metrics['unit'][0]

        return value and "{:,.1f}".format(1. * value / unit)

    def fmt_per_sh(self, value):

        return value and "{:.2f}".format(float(value))

    def get_unit(self):

        unit_labels = {1000: 'thousands', 1000000: 'millions',
            1000000000: 'billions'}
        unit = 1000
        top = max(self.metrics['revenue_totals']) / unit
        while top > 1999999: # Values greater than '1,999,999.0' ==> '2,000.0'
            top /= 1000
            unit *= 1000

        unit_label = unit_labels[unit]
        return unit, unit_label

    def hist_ratios(self, field1_name, field2_name):

        fields1, fields2 = map(self.hist_fields, (field1_name, field2_name))
        ratios = self.impute(1, fields1, fields2, func=self.divide)

        return sorted(ratios, reverse=True)

    def divide(self, numer, denom):

        return numer / denom


    def impute(self, sign, field1, field2, func=None):
        """ Adds or subtracts values at corresponding enddates, disregarding
        enddates not occurring in both groups.
        INPUTS:
            - Field1 and Field2 are (enddate, delta, value) tuples.
            - All inputs will be quarterized after the quarterize and truncate functions
            - Applies function 'func' if provided, otherwise adds if sign == 1
              and subtracts if sign == -1
        OUTPUT:
            - List of (period, value) tuples where values are the sum (diff)
              of the corresponding period input values
        """

        if not func:
            func = lambda x, y: x + sign * y

        periods = list(set(map(lambda x: x[0], field1 + field2)))
        output = []
        for period in periods:
            first = filter(lambda x: x[0] == period, field1)
            if len(first) == 1:
                second = filter(lambda x: x[0] == period, field2)
                if len(second) == 1:
                    output.append((first[0][:2], func(first[0][-1], second[0][-1])))

        return output

    def inc_days(self, date, num):

        fmt = '%Y-%m-%d'
        dt = datetime.datetime.strptime(date, fmt)
        dt += datetime.timedelta(days=num)
        date = dt.strftime(fmt)

        return date


    def per_to_delta(self, period):
        """ Takes end_date, start_date list or tuple and delta (# days) '2013-06-29'"""
        
        fmt = '%Y-%m-%d'
        end_date = period[0]
        period = map(lambda x: datetime.datetime.strptime(x, fmt), period)
        delta = reduce(lambda x, y: x - y, period).days
        
        return delta

    def hist_fields(self, query):
        """ Returns the 0th field entry stored at query key in each filing.
        INPUT: query string matching a key in the self.filings dictionaries
        OUTPUT: 
        NOTES:
        """

        average = 'average' in query.lower()

        hist = []
        for key, value in self.filings.items():
            asof = key.split("|")[0]
            fields = value[query]
            fields = [(self.per_to_delta(el[0]),) + el + (asof,) for el in fields]
            hist += fields
        
        hist = list(fields + self.impute_periods(hist, average=average))

        return hist

    def hist_quarters(self, query):

        hist = self.hist_fields(query)
        quarters = [el[1:] for el in filter(lambda x: x[0] < 100, hist)]
        enddates = list(set(map(lambda x: x[0][0], quarters)))
        
        results = []
        for enddate in enddates:
            results.append(filter(lambda x: x[0][0]==enddate, quarters)[0])

        return results

    def truncate_hist(self, fields):
        """ Truncates from first period longer than 100 days """

        for i in xrange(len(fields)):
            if fields[i][1] > 100:
                fields = fields[:i]
                break

    def impute_period(self, outer, inner, sign, average):

        new_delta = outer[0] + sign * inner[0]
        if average:
            product1 = outer[2] * outer[0]
            product2 = inner[2] * inner[0]
            new_value = (product1 + sign * product2) / new_delta
        else:
            new_value = outer[2] + sign * inner[2]
        
        return new_delta, new_value

    def impute_periods(self, fields, average=False):

        imputed = []
        # remove duplicates:
        fields = list(set(fields))
        # iterate backwords to avoid interacting with new items
        for el in fields:
            asof = "{}*".format(el[3])
            # if 'el' non-quarterly, try to impute smaller periods
            if el[0] > 100:
                for other in fields:
                    # same enddate + 'other' starts later => impute earlier
                    if other[1][0] == el[1][0] and other[1][1] > el[1][1]:
                        end = self.inc_days(other[1][1], -1)
                        start = el[1][1]
                        delta, value = self.impute_period(el, other, -1, average)
                        imputed.append((delta, (end, start), value, asof))
                    # same startdate + 'other' ends before => impute later
                    if other[1][1] == el[1][1] and other[1][0] < el[1][0]:
                        end = el[1][0]
                        start = self.inc_days(other[1][0], 1)
                        delta, value = self.impute_period(el, other, -1, average)
                        imputed.append((delta, (end, start), value, asof))

            for other in fields:
                # try to chain 'el' and 'other' if => 1 year or less
                if el[0] + other[0] <= 370:
                    # 'other' startdate == ('el' enddate + 1) => chain periods
                    if other[1][1] == self.inc_days(el[1][0], 1):
                        end = other[1][0]
                        start = el[1][1]
                        delta, value = self.impute_period(el, other, 1, average)
                        imputed.append((delta, (end, start), value, asof))

        # remove duplicates
        imputed = list(set(imputed))

        return imputed
