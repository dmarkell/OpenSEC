import os
from pprint import pprint
import re
import time
import xml.etree.ElementTree as ET
import urllib2

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

        pprint(self.fields)

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

url = 'http://www.sec.gov/Archives/edgar/data/34088/000003408813000035/xom-20130630.xml'
filing = Filing(url)





