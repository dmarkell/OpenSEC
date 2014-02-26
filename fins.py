from accounting import AccountingFields
import datetime
import htmlentitydefs
import json
import logging
import os
import re
import time
import urllib
import urllib2
from xml.dom import minidom


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
            ('Revenues', (
                "Revenues", "SalesRevenueNet", "SalesRevenueServicesNet", 
                "RevenuesNetOfInterestExpense", "TotalRevenuesAndOtherIncome",
                "RevenuesNet"), None),
            ('WeightedAverageDilutedShares', (
                'WeightedAverageNumberOfDilutedSharesOutstanding',
                'WeightedAverageNumberOfDilutedSharesOutstanding',
                'WeightedAverageNumberBasicDilutedSharesOutstanding',
                'WeightedAverageNumberBasicDilutedSharesOutstanding'),
                self.collapse),
            ('EarningsPerShare', (
                'EarningsPerShareDiluted', 'EarningsPerShareBasicAndDiluted',
                'BasicDilutedEarningsPerShareNetIncome',
                'BasicAndDilutedLossPerShare'), None),
            ('NetIncomeLoss', (
                'ProfitLoss', 'NetIncomeLoss',
                'NetIncomeLossAvailableToCommonStockholdersBasic',
                'IncomeLossFromContinuingOperations',
                'IncomeLossAttributableToParent', 'IncomeLossFromContinuingOperationsIncludingPortionAttributableToNoncontrollingInterest'),
                None)
        ]

        self._load_root(url)
        self.get_instances()        
        self.get_fields()
        # needs to be fixed:
        self.fields['asof'] = '2013-06-30'


    def _load_root(self, url):

        filename = url.split("/")[-1]
        try:
            with open("./files/{}".format(filename), 'r') as f:
                root = ET.parse(f).getroot()
                
        except IOError:
            print "Parsing...",
            start = time.time()
            root = ET.parse(urllib2.urlopen(url)).getroot()
            print "{} seconds".format(time.time() - start)

            with open("./files/{}".format(filename), 'w') as f:
                f.write(ET.tostring(root))

        self.root = root

    def get_fields(self):

        self.fields = {}

        for field, queries, callback in self.ACCOUNTING_FIELDS:
            i = 0
            matches = self.name_matches(queries[i])
            while i < len(queries) - 1 and not matches:
                i += 1
                matches = self.name_matches(queries[i])
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
        
        # All nodes with unitRef
        nodes = self.root.findall("*[@unitRef]")

        for node in nodes:

            # Get name and value from tag name and inner text contents
            name, value = node.tag.split('}')[-1], node.text
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
                    period.append(el.text)
            
            
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
        self.fields['WeightedAverageDilutedShares'] = self.impute(1, self.fields['NetIncomeLoss'], self.fields['EarningsPerShare'], func=self.divide)


class Company:

    def __init__(self, ticker):

        self.filings_list = []
        self.meta = dict(ticker=ticker.upper(), filing_dates=[])
        self.filings = dict() # all fields found by AccountingFields
        self.prices = dict() # TODO: This will contain Yahoo! dataframe
        self.get_filings()

    def get_filings(self):

        print 'getting filings...'
        if not self.filings_list:
            self.get_filings_list()

        for fdate, furl in self.filings_list:
            key = "{}|{}".format(fdate, furl)
            filing = Filing(furl)
            self.filings[key] = filing.fields
            self.meta['filing_dates'].append((filing.fields['asof'], fdate))

    def get_filings_list(self):

        params = dict(action="getcompany", count=100, output='atom')
        params['ticker']= self.meta['ticker']
        
        for form in ['10-', '20-']:
            params['type'] = form
            enc_params = urllib.urlencode(params)
            url = "{}{}{}".format(ROOT, SEARCH_PATH, enc_params)
            
            _file = urllib2.urlopen(url)
            
            xml = minidom.parse(_file)
            

            name = xml.getElementsByTagName('conformed-name')[0]
            name = unescape(name.firstChild.nodeValue).upper()
            self.meta['name'] = name
            self.meta['cik'] = xml.getElementsByTagName('cik')[0].firstChild.nodeValue

            # Thanks to https://github.com/fernavid/
            docs_list = xml.getElementsByTagName('entry')
            start=  time.time()
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
                
                self.filings_list.append((f_date, f_url))

            print "\t{} seconds.".format(time.time() - start)
        

    def dump(self):

        with open(self.filename, 'w') as f:
            data = dict(meta=self.meta,
                filings=self.filings, prices=self.prices)
            f.write(json.dumps(data))

    def get_metrics(self):
        """ Add metrics for html presentation """ 

        self.metrics = dict() # fields prepared for html templates
        revenues = self.hist_fields('Revenues')
        dates = [el[0] for el in revenues]
        dts = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in dates]
        self.metrics['years'] = sorted(list(set([dt.year for dt in dts])),
            reverse=True)[:5]
        self.metrics['months'] = sorted(list(set([(dt.month,
            dt.strftime('%b').upper()) for dt in dts])))
        self.metrics['numcols'] = len(self.metrics['years'])

        # loop the below?
        self.to_array('revenues', revenues)
        self.metrics['revenue_totals'] = map(lambda l: sum(filter(None, l)), self.metrics['revenues'])
        self.to_array('eps', self.hist_fields('EarningsPerShare'))
        self.metrics['eps_totals'] = map(lambda l: sum(filter(None, l)), self.metrics['eps'])
        
        self.to_array('filedates', self.meta['filing_dates'])
        
        self.metrics['unit'] = self.get_unit()
        self.metrics['revenue_totals'] = map(self.fmt_val, self.metrics['revenue_totals'])
        self.metrics['revenues'] = [map(self.fmt_val, items) for items in self.metrics['revenues']]
        shares_out = self.hist_fields('SharesOutstanding')[0][-1]
        self.metrics['shs'] = self.fmt_val(shares_out)
        self.metrics['eps_totals'] = map(self.fmt_per_sh, self.metrics['eps_totals'])
        self.metrics['eps'] = [map(self.fmt_per_sh, items) for items in self.metrics['eps']]

        # Add pricing
        self.prices['last'] = 0.0

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

    def to_array(self, key, fields):

        self.metrics[key] = []

        for yr in self.metrics['years']:
            year = []
            for mo in self.metrics['months']:
                val = filter(lambda x: int(x[0][:4]) == yr and int(x[0][5:7]) == mo[0], fields)
                year.append(val[0][-1] if len(val) == 1 else None)
            self.metrics[key].append(year)

    def pct_print(self, decimals):

        return map(lambda x: "{:.1f}%".format(100. * x), decimals)

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

    def impute_periods(self, fields):
        imputed = []
        for el in fields:
            for other in fields:
                # if same enddate and 'other' starts later, 'new' starts earlier
                if other[0][0] == el[0][0] and other[0][1] > el[0][1]:
                    new_end = self.inc_days(other[0][1], -1)
                    new_start = el[0][1]
                    new_value = el[1] - other[1]
                    new = ((new_end, new_start), new_value)
                    imputed.append(new)
                # if same startdate and 'other' ends before, 'new' ends after
                if other[0][1] == el[0][1] and other[0][0] < el[0][0]:
                    new_end = el[0][0]
                    new_start = self.inc_days(other[0][0], 1)
                    new_value = el[1] - other[1]
                    new = ((new_end, new_start), new_value)
                    imputed.append(new)

        return list(set(imputed))

    def per_to_delta(self, period):
        """ Takes end_date, start_date list or tuple and returns end_date, 
        delta (# days) tuple """
        
        end_date = period[0]
        period = map(self.to_dt, period)
        delta = reduce(lambda x, y: x - y, period).days
        
        return end_date, delta

    def all_fields(self, query):

        fields = [value[query] for value in self.filings.values()]
        fields = list(set([item for sublist in fields for item in sublist]))
        imputeds = self.impute_periods(fields)
        total = list(set(fields + imputeds))

        return total

    def hist_fields(self, query):
        """ Returns the 0th field entry stored at query key in each filing.
        INPUT: query string matching a key in the self.filings dictionaries
        OUTPUT: zipped list of (end_date, delta, value) tuples
            - Deltas are # of days between start_date and end_date
            - End_dates are end of period
        NOTES:
            - Quarterize method attempts to convert non-quarterly values to
            quarterly values using previous periods (this will leave some
            periods unconverted, e.g. an annual value not preceded by at least
            three quarterly filings)
            - Field values are sorted descended by periods which are
            (end_date, start_date), so 0th result should be shortest duration
            ending on latest date.
        """

        filings_items = sorted(self.filings.items(), reverse=True)
        fields = [val[query][0] for key, val in filings_items]
        fields = [list(self.per_to_delta(el[0])) + [el[1]] for el in fields]

        # ??: Always the case for average terms?
        average = 'average' in query.lower()
        self.quarterize(fields, average=average)
        self.truncate_hist(fields)

        return fields

    def truncate_hist(self, fields):
        """ Truncates from first period longer than 100 days """

        for i in xrange(len(fields)):
            if fields[i][1] > 100:
                fields = fields[:i]
                break

    def quarterize(self, fields, average):
        """ Converts non-quarterly periods to quarterly
        Assumption is that previous periods are continuous with no jumps:
        e.g. 12-month data would be preceded by quarterly, 6 month or 9 month data
        ending one quarter before the number being adjusted.
        Primary use would be 10-Ks without any quarterly data, and cash flow
        statements showing only YTD periods.
        
        TODO:
            - This method (using the prior period filing for adjustment) should
            be a second resort--the first attempt should impute the quarterly
            value from other periods shown in the filing itself...?
            - Another way to do the below using periods instead of deltas?:
            size = len(deltas)
            for i in xrange(size - 1):
                j = i + 1
                while periods[j][1] >= periods[i][1]:
                    values[i] -= values[j]
        """
        #size = len(deltas)
        size = len(fields)
        for i in xrange(size - 1):
            if fields[i][1]: # delta
                if average:
                    # normalize weighted average (value * #days)
                    product = fields[i][-1] * fields[i][1]
                j = i + 1
                # 65 used so that three 100-day quarters could be subtracted
                while j < size and fields[i][1] - fields[j][1] > 65:
                    fields[i][1] -= fields[j][1] # adjust delta
                    if average:
                        product -= fields[j][-1] * fields[j][1] # adjust product
                    else:
                        fields[i][-1] -= fields[j][-1] # adjust value
                    j += 1
                if average:
                    # de-normalize weighted average (value / #days)
                    fields[i][-1] = product / fields[i][1] # product / delta
