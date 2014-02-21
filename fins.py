from accounting import AccountingFields
import datetime
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
# Pre-compile index URL pattern data/CIK/[ACC/]ACC_w_dashes/index.htm[l] :
p_index = re.compile("data/(\d+)/(?:\d{18}/)?(\d{10}-\d{2}-\d{6})(-index.html?)")
DUMPS_PATH = '/Users/devinmarkell/Dropbox/Code/edgar/dumps'


def get_filings_list(ticker):

    logging.error("Getting {} filings list...".format(ticker))

    filings = []

    name = cik = ''
    for type in ['10-', '20-']:
        params = dict(action="getcompany", count=100, type=type, ticker=ticker)
        params = urllib.urlencode(params)
        url = "{}{}{}".format(ROOT, SEARCH_PATH, params)
        
        new_name, new_cik = scrape_sec_index(url, filings)
        name = new_name if new_name else name
        cik = new_cik if new_cik else name

    return filings, name, cik

def scrape_sec_index(url, filings):
    
    source = urllib2.urlopen(url).read()
    # Get rows matching <tr ... >innerHTML</tr> pattern, skipping first 3 rowsfins
    name = re.findall(r'companyName">([\s\S]*?)<', source)
    name = name[0].strip() if name else None
    cik = re.findall(r'CIK=(\d{10})', source)
    cik = cik[0].strip() if cik else None
    rows = re.findall(r'<tr[\s\S]*?>[\s\S]*?</tr>', source)[3:]

    for row in rows:
        date = re.findall(r'<td>(\d{4}-\d{2}-\d{2})</td>', row)[0]

        cik_s, acc_l, suffix = p_index.findall(row)[0]
        acc_s = acc_l.replace("-", "")
        base = "{}{}".format(ROOT, DATA_PATH)
        slug_s = '/'.join((cik_s, acc_s))
        slug_l = '/'.join((slug_s, acc_l))

        if row.find("interactiveDataBtn") <> -1:
            # If interactive filing (XML) visit index page
            url = "{}{}{}".format(base, slug_l, suffix)
            source = urllib2.urlopen(url).read()
            # Full xml filing slug ends in "/" + letters + 8-digit date + ".xml" 
            p = re.compile("{}(\d+/{}/\D+-\d{{8}}.xml)".format(DATA_PATH, acc_s))
            url = "{}{}".format(base, p.findall(source)[0])
        else:
            # For non-interactive filing, get full text version
            url = "{}{}.txt".format(base, slug_l)

        # Add (date, url) tuple to filings list
        filings.append((date, url))



    return name, cik

def get_filing(url):

    logging.error("\tRetrieving http://...{}".format(url[-12:]))

    try:
        _file = urllib2.urlopen(url)
    except:
        logging.error("Error opening url!")
        return None

    logging.error("\t\tParsing xml...")

    try:
        xml = minidom.parse(_file)
    except:
        logging.error("Error parsing!")
        return None

    logging.error("\t\t\tCreating Filing object ...")

    schema = Schema(xml)
    xbrl = xml.getElementsByTagName("{}xbrl".format(schema.pre))[0]
    filing = Filing(xbrl, schema)


    return filing


class Filing:

    def __init__(self, xbrl, schema):
        self.schema = schema
        instances = filter(self.is_instance, xbrl.childNodes)
        # Should this be done only as needed?
        self.instances = map(self.account_map, instances) #!!
        self.core_instances = filter(self.is_core, self.instances)
        AccountingFields(self)
        # This should always work but should be replaced:
        self.asof = max([el[0][0] for el in self.fields['Revenues']])

    def is_instance(self, node):

        if node.nodeType <> 1:
            return False
        elif not node.childNodes:
            return False
        elif not node.attributes:
            return False
        elif not node.attributes.has_key('unitRef'):
            return False
        else:
            return True

    def is_core(self, node):
        """Filter function, True if node's context_ref is core """

        # Contexts are already mapped in self.instances
        context_ref = node[-1]
        return  context_ref in self.schema.core_keys

    def account_map(self, node):
        value = float(node.firstChild.nodeValue)
        name = node.tagName.split(":", 1)[1]
        context_ref = node.attributes['contextRef'].nodeValue
        period = self.schema.contexts[context_ref]
       
        # This is useful for showing how it appears in the html, but not needed
        decimals = node.attributes['decimals'].nodeValue

        return name, period, decimals, value, context_ref

    def name_matches(self, query, non_core=False):
 
        regexp = "^{}$".format(query)
        results = self.attr_matches('name', regexp, non_core=non_core)
        matches = [(el[1], el[3]) for el in results]

        return matches

    def attr_matches(self, attr, regexp, non_core=False):
        """ Returns list of instances whose attributes attr match
            regular expression regexp.
            Input: Attribute ('name', 'value', 'period') and regexp string
            to match instance names against.
            Output: List of instances, sorted descending by date (start date, end date)
            Notes: 'period' is a tuple of dates so this is converted to a string in form
            "('YYYY-MM-DD', 'YYYY-MM-DD')" for matching
        """
        attrs = ('name', 'period', 'decimals', 'value', 'context_ref')
        ix = attrs.index(attr)
        p = re.compile(regexp)
        if non_core:
            matches = filter(lambda x: p.match(str(x[ix])), self.instances)
        else:
            matches = filter(lambda x: p.match(str(x[ix])), self.core_instances)
        matches = sorted(matches, key=lambda x: x[1], reverse=True)
        
        return matches


class Schema:

    def __init__(self, xml):
        self.xml = xml
        self.pre = "xbrli:" if xml.getElementsByTagName("xbrli:xbrl") else ""
        contexts = xml.getElementsByTagName("{}context".format(self.pre))
        contexts_detail = map(self.context_map, contexts)
        core = filter(lambda x: x[-1], contexts_detail)
        self.core_keys = map(lambda x: x[0], core)

        # May be a lot slower to map for all contexts--consider doing this step
        # only on demand as needed (i.e. if looking for non-core nodes)
        self.contexts = dict(map(lambda x: x[:-1], contexts_detail))

    # Not used:
    def is_core(self, node):
        """ Returns True if context is core (has no 'segment' tag).
        NOTES:
            - Most gaap data will come from core nodes so these are separated
        """
        seg_tag = "{}segment".format(self.pre)
        return not node.getElementsByTagName(seg_tag)

    # This also checks whether context is core
    def context_map(self, context):

        # Core nodes have no 'segment' tag -- these are separte since most gaap
        # data comes from these
        core = not context.getElementsByTagName("{}segment".format(self.pre))
        context_ref = context.attributes['id'].firstChild.nodeValue
        instant = context.getElementsByTagName("{}instant".format(self.pre))
        if instant:
            period = [instant[0].firstChild.nodeValue for i in xrange(2)]
        else:
            start = context.getElementsByTagName("{}startDate".format(self.pre))
            end = context.getElementsByTagName("{}endDate".format(self.pre))
            period = map(lambda x: x[0].firstChild.nodeValue if x else None, (end, start))

        return context_ref, tuple(period), core


class Company:

    def __init__(self, ticker, disk=DUMPS_PATH, flush=False):
        
        start = time.time()
        logging.error("<--- Building Company instance...")

        self.filings = None
        
        # Get from disk unless flush=True (overwrite)
        if not flush:
            self.filename = "{}/{}.txt".format(disk, ticker)
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    data = json.loads(f.read())
                    self.meta = data.get('meta')
                    self.filings = data.get('filings')
                    self.prices = data.get('prices')

        if not self.filings:
            # TODO: get cik & name from filing(s)
            self.meta = dict(ticker=ticker.upper(), filing_dates=[])
            self.filings = dict() # all fields found by AccountingFields
            self.prices = dict() # TODO: This will contain Yahoo! dataframe

            docs, name, self.meta['cik'] = get_filings_list(ticker)
            self.meta['name'] = name.upper()
            xml_docs = filter(lambda x: x[1].endswith('.xml'), docs)
        
            for date, url in xml_docs:
                filing = get_filing(url)
                self.meta['filing_dates'].append((filing.asof, date))
                self.filings["{}|{}".format(date, url)] = filing.fields

            self.meta['filing_dates'] = sorted(self.meta['filing_dates'],
                reverse=True)

        logging.error("---> Finished. {} seconds".format(str(time.time() - start)))
        
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
        self.metrics['shs'] = self.fmt_shs(shares_out)
        self.metrics['eps_totals'] = map(self.fmt_per_sh, self.metrics['eps_totals'])
        self.metrics['eps'] = [map(self.fmt_per_sh, items) for items in self.metrics['eps']]

        # Add pricing
        self.prices['last'] = 0.0

    def fmt_val(self, value):

        unit = self.metrics['unit'][0]

        return value and "{:,.1f}".format(1. * value / unit)

    def fmt_shs(self, value):

        unit = self.metrics['unit'][0]

        return value and "{:,.3f}".format(1. * value / unit)

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
                    output.append((first[0][:2], func(first[0][-1], second[0][-1])))

        return output

    def to_datetime(self, xbrl_date):

        return datetime.datetime.strptime(xbrl_date, '%Y-%m-%d')

    def get_delta(self, period):

        period = map(self.to_datetime, period)
        delta = reduce(lambda x, y: x - y, period).days

        return delta

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

        # TODO: check that this is always the case for average terms:
        average = 'average' in query.lower()

        filings_items = sorted(self.filings.items(), reverse=True)
        results = [val[query][0] for key, val in filings_items]
        
        values = [el[1] for el in results]

        periods = [el[0] for el in results]
        end_dates = [el[0] for el in periods]

        deltas = [self.get_delta(el) for el in periods]

        values, deltas = self.quarterize(values, deltas, average=average)

        results = self.truncate_hist(end_dates, deltas, values)

        return results

    def truncate_hist(self, end_dates, deltas, values):
        """ Truncates from first period longer than 100 days """

        for i in range(len(deltas)):
            if deltas[i] > 100:
                end_dates = end_dates[:i]
                deltas = deltas[:i]
                values = values[:i]
                break

        return zip(end_dates, deltas, values)

    def quarterize(self, values, deltas, average):
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
        size = len(deltas)
        for i in xrange(size - 1):
            if deltas[i]:
                if average:
                    product = values[i] * deltas[i] 
                j = i + 1
                # 65 used so that three 100-day quarters could be subtracted
                # Not sure if this is the right way to go
                while j < size and deltas[i] - deltas[j] > 65:
                    if average:
                        deltas[i] -= deltas[j]
                        product -= values[j] * deltas[j]
                    else:
                        deltas[i] -= deltas[j]
                        values[i] -= values[j]
                    j += 1
                if average:
                    values[i] = product / deltas[i]

        return values, deltas

