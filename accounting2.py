import re
import urllib2


field_map = {
    'Revenues': ["Revenues", "SalesRevenueNet", "SalesRevenueServicesNet", "RevenuesNetOfInterestExpense", "TotalRevenuesAndOtherIncome", "RevenuesNet"],
    'CostOfRevenue': ["CostOfRevenue", "CostOfServices", "CostOfGoodsSold", "CostOfGoodsAndServicesSold"],
    'SharesOutstanding': ['CommonStockSharesOutstanding', 'EntityCommonStockSharesOutstanding'],
    'Assets': ["Assets"],
    'CurrentAssets': ["AssetsCurrent"]
}


class Company:

    def __init__(self, url):
        _file = urllib2.urlopen(url)
        self.source = _file.read()
        self.map_fields()

    def map_fields(self):

        self.fields = {}

        for key in field_map.keys():
            names = field_map.values()
            i = 0
            self.fields[key] = names
            while i < len(names) and not self.find_fields(names[i]):
                i += 1

    def find_field(name):

        regexp = r'<\w*?:{}'.format(name)
        matches = re.findall(regexp, self.source)
        return matches

url = 'http://www.sec.gov/Archives/edgar/data/34088/000003408813000035/xom-20130630.xml'
company = Company(url)

print company.fields
"""
# the following need to be done in order
# if el in second tuple is a string, run name_matches; stop if results found; if el in second tuple is an impute function, run that with given input & sign/function
#impute function should first check that the two impute inputs exist, or not require them to
('SharesOutstanding', ('CommonStockSharesOutstanding', 'EntityCommonStockSharesOutstanding'),
('Assets', 'Assets'),
('CurrentAssets', "AssetsCurrent")
('NoncurrentAssets', 'AssetsNoncurrent', impute(-1, 'Assets', 'CurrentAssets'))
('LiabilitiesAndEquity', ("LiabilitiesAndStockholdersEquity", "LiabilitiesAndPartnersCapital"))
('Liabilities', "Liabilities")
('CurrentLiabilities', "LiabilitiesCurrent")
('NoncurrentLiabilities', "LiabilitiesNoncurrent", impute(-1, 'Liabilities', 'CurrentLiabilities'))
('CommitmentsAndContingencies', "CommitmentsAndContingencies")
                
        #TemporaryEquity
('TemporaryEquity', "TemporaryEquityRedemptionValue",
    "RedeemablePreferredStockCarryingAmount", "TemporaryEquityCarryingAmount",
    "TemporaryEquityValueExcludingAdditionalPaidInCapital", "TemporaryEquityCarryingAmountAttributableToParent",
    "RedeemableNoncontrollingInterestEquityFairValue")

('RedeemableNoncontrollingInterest', ("RedeemableNoncontrollingInterestEquityCarryingAmount", "RedeemableNoncontrollingInterestEquityCommonCarryingAmount")
('TemporaryEquity', self.impute(1, self.filing.fields['TemporaryEquity'], 'RedeemableNoncontrollingInterest'))

('Equity', "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "StockholdersEquity",
    "PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest", "PartnersCapital", "CommonStockholdersEquity",
    "MemberEquity", "AssetsNet")
        
        #EquityAttributableToNoncontrollingInterest
('EquityAttributableToNoncontrollingInterest', "MinorityInterest", 'EquityAttributableToNoncontrollingInterest', "PartnersCapitalAttributableToNoncontrollingInterest")
        
        #EquityAttributableToParent
('EquityAttributableToParent', "StockholdersEquity", "LiabilitiesAndPartnersCapital")

        if not self.filing.fields['Assets']:
            if self.filing.fields['LiabilitiesAndEquity'] and (self.filing.fields['CurrentAssets'] == self.filing.fields['LiabilitiesAndEquity']):
                self.filing.fields['Assets'] = self.filing.fields['CurrentAssets']
            #Why this?
            elif not self.filing.fields['NoncurrentAssets'] and self.filing.fields['LiabilitiesAndEquity']:
                if self.filing.fields['LiabilitiesAndEquity'] == self.impute(1(self.filing.fields['Liabilities'], self.filing.fields['Equity'])):
                    self.filing.fields['Assets'] = self.filing.fields['CurrentAssets']
        
        #? This replaces found NCA-should it be an assert?
        if self.filing.fields['Assets'] and self.filing.fields['CurrentAssets']:
            self.filing.fields['NoncurrentAssets'] = self.impute(-1, self.filing.fields['Assets'], self.filing.fields['CurrentAssets'])

        if not self.filing.fields['LiabilitiesAndEquity'] and self.filing.fields['Assets']:
            self.filing.fields['LiabilitiesAndEquity'] = self.filing.fields['Assets']
        

        #Impute EquityAttributableToParent based on existence of equity and NoncontrollingInterest.        
        if self.filing.fields['Equity']:
            if not self.filing.fields['EquityAttributableToParent']:
                if self.filing.fields['EquityAttributableToNoncontrollingInterest']:
                    self.filing.fields['EquityAttributableToParent'] = self.impute(-1, self.filing.fields['Equity'], self.filing.fields['EquityAttributableToNoncontrollingInterest'])
                else:
                    self.filing.fields['EquityAttributableToParent'] = self.filing.fields['Equity']

        #Impute Equity based on EquityAttributableToParent and NoncontrollingInterest being present
        # Asserts to make sure correct equity not overwritten?
        if self.filing.fields['EquityAttributableToParent']:
            if self.filing.fields['EquityAttributableToNoncontrollingInterest']:
                self.filing.fields['Equity'] = self.impute(1, self.filing.fields['EquityAttributableToParent'], self.filing.fields['EquityAttributableToNoncontrollingInterest'])
            else:
                self.filing.fields['Equity'] = self.filing.fields['EquityAttributableToParent']
        
        
        #if total liabilities is missing, figure it out based on liabilities and equity
        # This might not work right
        if not self.filing.fields['Liabilities']:
            if self.filing.fields['Equity']:
                if self.filing.fields['LiabilitiesAndEquity']:
                    # Problem here: there may be extra equity periods reported in stmt of equity
                    self.filing.fields['Liabilities'] = self.impute(1, self.filing.fields['LiabilitiesAndEquity'], self.filing.fields['Equity'])
                    if self.filing.fields['TemporaryEquity']:
                        self.filing.fields['Liabilities'] = self.impute(1, self.filing.fields['Liabilities'], self.filing.fields['TemporaryEquity'])
                        if self.filing.fields['CommitmentsAndContingencies']:
                            self.filing.fields['Liabilities'] = self.impute(-1, self.filing.fields['Liabilities'], self.filing.fields['CommitmentsAndContingencies'])

        #This seems incorrect because liabilities might not be reported
        if self.filing.fields['Liabilities'] and self.filing.fields['CurrentLiabilities']:
            self.filing.fields['NoncurrentLiabilities'] = self.impute(-1, self.filing.fields['Liabilities'], self.filing.fields['CurrentLiabilities'])
        
        #Added to fix liabilities based on current liabilities
        if not self.filing.fields['Liabilities'] and self.filing.fields['CurrentLiabilities'] and not self.filing.fields['NoncurrentLiabilities']:
            self.filing.fields['Liabilities'] = self.filing.fields['CurrentLiabilities']
               
        self.filing.fields['PPE'] = self.filing.name_matches("PropertyPlantAndEquipmentNet")
        self.filing.fields['Inventory'] = self.filing.name_matches("InventoryNet")
        self.filing.fields['AccountsReceivable'] = self.filing.name_matches("AccountsReceivableNetCurrent")
        self.filing.fields['Goodwill'] = self.filing.name_matches("Goodwill")
        self.filing.fields['IntangiblesExGoodwill'] = self.filing.name_matches("IntangibleAssetsNetExcludingGoodwill")
        self.filing.fields['AccountsPayable'] = self.filing.name_matches("AccountsPayableCurrent")
        self.filing.fields['CashAndCashEquivalents'] = self.filing.name_matches("CashAndCashEquivalentsAtCarryingValue")
        self.filing.fields['LongTermDebtCurrent'] = self.filing.name_matches("LongTermDebtCurrent")
        self.filing.fields['LongTermDebtNonCurrent'] = self.filing.name_matches("LongTermDebtNoncurrent")
        self.filing.fields['OperatingLeasesOneYear'] = self.filing.name_matches("OperatingLeasesFutureMinimumPaymentsDueInOneYear")
        self.filing.fields['OperatingLeasesTwoYear'] = self.filing.name_matches("OperatingLeasesFutureMinimumPaymentsDueInTwoYears")
        self.filing.fields['OperatingLeasesThreeYear'] = self.filing.name_matches("OperatingLeasesFutureMinimumPaymentsDueInThreeYears")
        self.filing.fields['OperatingLeasesFourYear'] = self.filing.name_matches("OperatingLeasesFutureMinimumPaymentsDueInFourYears")
        self.filing.fields['OperatingLeasesFiveYear'] = self.filing.name_matches("OperatingLeasesFutureMinimumPaymentsDueInFiveYears")
        self.filing.fields['OperatingLeasesLongTerm'] = self.filing.name_matches("OperatingLeasesFutureMinimumPaymentsDueThereafter")
        self.filing.fields['ShortTermInvestments'] = self.filing.name_matches("ShortTermInvestments")
        self.filing.fields['LongTermInvestments'] = self.filing.name_matches("LongTermInvestments")
        

        #Income statement
        # Got lazy and replaced "if ... == None:" hereafter with "if ... == []:"; should be "if not... :"

        #Revenues
        self.filing.fields['Revenues'] = self.filing.name_matches("Revenues")
        if not self.filing.fields['Revenues']:
            self.filing.fields['Revenues'] = self.filing.name_matches("SalesRevenueNet")
            if not self.filing.fields['Revenues']:
                self.filing.fields['Revenues'] = self.filing.name_matches("SalesRevenueServicesNet")
                if not self.filing.fields['Revenues']:
                    self.filing.fields['Revenues'] = self.filing.name_matches("RevenuesNetOfInterestExpense")
                    if not self.filing.fields['Revenues']:
                        self.filing.fields['Revenues'] = self.filing.name_matches("RegulatedAndUnregulatedOperatingRevenue")
                        if not self.filing.fields['Revenues']:
                            self.filing.fields['Revenues'] = self.filing.name_matches("HealthCareOrganizationRevenue")
                            if not self.filing.fields['Revenues']:
                                self.filing.fields['Revenues'] = self.filing.name_matches("InterestAndDividendIncomeOperating")
                                if not self.filing.fields['Revenues']:
                                    self.filing.fields['Revenues'] = self.filing.name_matches("RealEstateRevenueNet")
                                    if not self.filing.fields['Revenues']:
                                        self.filing.fields['Revenues'] = self.filing.name_matches("RevenueMineralSales")
                                        if not self.filing.fields['Revenues']:
                                            self.filing.fields['Revenues'] = self.filing.name_matches("OilAndGasRevenue")
                                            if not self.filing.fields['Revenues']:
                                                self.filing.fields['Revenues'] = self.filing.name_matches("FinancialServicesRevenue")
                                                if not self.filing.fields['Revenues']:
                                                    self.filing.fields['Revenues'] = self.filing.name_matches("RegulatedAndUnregulatedOperatingRevenue")
                                                    if not self.filing.fields['Revenues']:
                                                        # non_core?
                                                        self.filing.fields['Revenues'] = self.filing.name_matches("TotalRevenuesAndOtherIncome")
                                                        if not self.filing.fields['Revenues']:
                                                            self.filing.fields['Revenues'] = self.filing.name_matches("RevenuesNet")

        #CostOfRevenue
        self.filing.fields['CostOfRevenue'] = self.filing.name_matches("CostOfRevenue")
        if self.filing.fields['CostOfRevenue'] == []:
            self.filing.fields['CostOfRevenue'] = self.filing.name_matches("CostOfServices")
            if self.filing.fields['CostOfRevenue'] == []:
                self.filing.fields['CostOfRevenue'] = self.filing.name_matches("CostOfGoodsSold")
                if self.filing.fields['CostOfRevenue'] == []:
                    self.filing.fields['CostOfRevenue'] = self.filing.name_matches("CostOfGoodsAndServicesSold")
     
        #GrossProfit
        self.filing.fields['GrossProfit'] = self.filing.name_matches("GrossProfit")
        if self.filing.fields['GrossProfit'] == []:
            self.filing.fields['GrossProfit'] = self.filing.name_matches("GrossProfit")
     
        #OperatingExpenses
        self.filing.fields['OperatingExpenses'] = self.filing.name_matches("OperatingExpenses")
        if self.filing.fields['OperatingExpenses'] == []:
            self.filing.fields['OperatingExpenses'] = self.filing.name_matches("OperatingCostsAndExpenses")  #This concept seems incorrect.

        #CostsAndExpenses
        self.filing.fields['CostsAndExpenses'] = self.filing.name_matches("CostsAndExpenses")
        if self.filing.fields['CostsAndExpenses'] == []:
            self.filing.fields['CostsAndExpenses'] = self.filing.name_matches("CostsAndExpenses")
     
        #OtherOperatingIncome
        self.filing.fields['OtherOperatingIncome'] = self.filing.name_matches("OtherOperatingIncome")
        if self.filing.fields['OtherOperatingIncome'] == []:
            self.filing.fields['OtherOperatingIncome'] = self.filing.name_matches("OtherOperatingIncome")
            
     
        #OperatingIncomeLoss
        self.filing.fields['OperatingIncomeLoss'] = self.filing.name_matches("OperatingIncomeLoss")
        if self.filing.fields['OperatingIncomeLoss'] == []:
            self.filing.fields['OperatingIncomeLoss'] = self.filing.name_matches("OperatingIncomeLoss")
            
     
        #NonoperatingIncomeLoss
        self.filing.fields['NonoperatingIncomeLoss'] = self.filing.name_matches("NonoperatingIncomeExpense")
        if self.filing.fields['NonoperatingIncomeLoss'] == []:
            self.filing.fields['NonoperatingIncomeLoss'] = self.filing.name_matches("NonoperatingIncomeExpense")
            

        #InterestAndDebtExpense
        self.filing.fields['InterestAndDebtExpense'] = self.filing.name_matches("InterestAndDebtExpense")
        if self.filing.fields['InterestAndDebtExpense'] == []:
            self.filing.fields['InterestAndDebtExpense'] = self.filing.name_matches("InterestAndDebtExpense")
            

        #IncomeBeforeEquityMethodInvestments
        self.filing.fields['IncomeBeforeEquityMethodInvestments'] = self.filing.name_matches("IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments")
        if self.filing.fields['IncomeBeforeEquityMethodInvestments'] == []:
            self.filing.fields['IncomeBeforeEquityMethodInvestments'] = self.filing.name_matches("IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments")
     
        #IncomeFromEquityMethodInvestments
        self.filing.fields['IncomeFromEquityMethodInvestments'] = self.filing.name_matches("IncomeLossFromEquityMethodInvestments")
        if self.filing.fields['IncomeFromEquityMethodInvestments'] == []:
            self.filing.fields['IncomeFromEquityMethodInvestments'] = self.filing.name_matches("IncomeLossFromEquityMethodInvestments")
            
     
        #IncomeFromContinuingOperationsBeforeTax
        self.filing.fields['IncomeFromContinuingOperationsBeforeTax'] = self.filing.name_matches("IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments")
        if self.filing.fields['IncomeFromContinuingOperationsBeforeTax'] == []:
            self.filing.fields['IncomeFromContinuingOperationsBeforeTax'] = self.filing.name_matches("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest")
            
     
        #IncomeTaxExpenseBenefit
        self.filing.fields['IncomeTaxExpenseBenefit'] = self.filing.name_matches("IncomeTaxExpenseBenefit")
        if self.filing.fields['IncomeTaxExpenseBenefit'] == []:
            self.filing.fields['IncomeTaxExpenseBenefit'] = self.filing.name_matches("IncomeTaxExpenseBenefitContinuingOperations")
            
     
        #IncomeFromContinuingOperationsAfterTax
        self.filing.fields['IncomeFromContinuingOperationsAfterTax'] = self.filing.name_matches("IncomeLossBeforeExtraordinaryItemsAndCumulativeEffectOfChangeInAccountingPrinciple")
        if self.filing.fields['IncomeFromContinuingOperationsAfterTax'] == []:
            self.filing.fields['IncomeFromContinuingOperationsAfterTax'] = self.filing.name_matches("IncomeLossBeforeExtraordinaryItemsAndCumulativeEffectOfChangeInAccountingPrinciple")
            

        #IncomeFromDiscontinuedOperations
        self.filing.fields['IncomeFromDiscontinuedOperations'] = self.filing.name_matches("IncomeLossFromDiscontinuedOperationsNetOfTax")
        if self.filing.fields['IncomeFromDiscontinuedOperations'] == []:
            self.filing.fields['IncomeFromDiscontinuedOperations'] = self.filing.name_matches("DiscontinuedOperationGainLossOnDisposalOfDiscontinuedOperationNetOfTax")
            if self.filing.fields['IncomeFromDiscontinuedOperations'] == []:
                self.filing.fields['IncomeFromDiscontinuedOperations'] = self.filing.name_matches("IncomeLossFromDiscontinuedOperationsNetOfTaxAttributableToReportingEntity")
            

        #ExtraordaryItemsGainLoss
        self.filing.fields['ExtraordaryItemsGainLoss'] = self.filing.name_matches("ExtraordinaryItemNetOfTax")
        if self.filing.fields['ExtraordaryItemsGainLoss'] == []:
            self.filing.fields['ExtraordaryItemsGainLoss'] = self.filing.name_matches("ExtraordinaryItemNetOfTax")
            

        #NetIncomeLoss
        self.filing.fields['NetIncomeLoss'] = self.filing.name_matches("ProfitLoss")

        if self.filing.fields['NetIncomeLoss'] == []:
            self.filing.fields['NetIncomeLoss'] = self.filing.name_matches("NetIncomeLoss")
            if self.filing.fields['NetIncomeLoss'] == []:
                self.filing.fields['NetIncomeLoss'] = self.filing.name_matches("NetIncomeLossAvailableToCommonStockholdersBasic")
                
                if self.filing.fields['NetIncomeLoss'] == []:
                    self.filing.fields['NetIncomeLoss'] = self.filing.name_matches("IncomeLossFromContinuingOperations")
                    if self.filing.fields['NetIncomeLoss'] == []:
                        self.filing.fields['NetIncomeLoss'] = self.filing.name_matches("IncomeLossAttributableToParent")
                        if self.filing.fields['NetIncomeLoss'] == []:
                            self.filing.fields['NetIncomeLoss'] = self.filing.name_matches("IncomeLossFromContinuingOperationsIncludingPortionAttributableToNoncontrollingInterest")
        

        #NetIncomeAvailableToCommonStockholdersBasic
        self.filing.fields['NetIncomeAvailableToCommonStockholdersBasic'] = self.filing.name_matches("NetIncomeLossAvailableToCommonStockholdersBasic")
        
                
        #PreferredStockDividendsAndOtherAdjustments
        self.filing.fields['PreferredStockDividendsAndOtherAdjustments'] = self.filing.name_matches("PreferredStockDividendsAndOtherAdjustments")
        
                
        #NetIncomeAttributableToNoncontrollingInterest
        self.filing.fields['NetIncomeAttributableToNoncontrollingInterest'] = self.filing.name_matches("NetIncomeLossAttributableToNoncontrollingInterest")
        
                
        #NetIncomeAttributableToParent
        self.filing.fields['NetIncomeAttributableToParent'] = self.filing.name_matches("NetIncomeLoss")
        

        #OtherComprehensiveIncome
        self.filing.fields['OtherComprehensiveIncome'] = self.filing.name_matches("OtherComprehensiveIncomeLossNetOfTax")
        if self.filing.fields['OtherComprehensiveIncome'] == []:
            self.filing.fields['OtherComprehensiveIncome'] = self.filing.name_matches("OtherComprehensiveIncomeLossNetOfTax")
        

        #ComprehensiveIncome
        self.filing.fields['ComprehensiveIncome'] = self.filing.name_matches("ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest")
        if self.filing.fields['ComprehensiveIncome'] == []:
            self.filing.fields['ComprehensiveIncome'] = self.filing.name_matches("ComprehensiveIncomeNetOfTax")
        

        #ComprehensiveIncomeAttributableToParent
        self.filing.fields['ComprehensiveIncomeAttributableToParent'] = self.filing.name_matches("ComprehensiveIncomeNetOfTax")
        if self.filing.fields['ComprehensiveIncomeAttributableToParent'] == []:
            self.filing.fields['ComprehensiveIncomeAttributableToParent'] = self.filing.name_matches("ComprehensiveIncomeNetOfTax")
        
     
        #ComprehensiveIncomeAttributableToNoncontrollingInterest
        self.filing.fields['ComprehensiveIncomeAttributableToNoncontrollingInterest'] = self.filing.name_matches("ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest")
        if self.filing.fields['ComprehensiveIncomeAttributableToNoncontrollingInterest']==None:
            self.filing.fields['ComprehensiveIncomeAttributableToNoncontrollingInterest'] = self.filing.name_matches("ComprehensiveIncomeNetOfTaxAttributableToNoncontrollingInterest")

        #########'Adjustments to income statement information
        #Impute: NonoperatingIncomeLossPlusInterestAndDebtExpense
        self.filing.fields['NonoperatingIncomeLossPlusInterestAndDebtExpense'] = self.impute(1, self.filing.fields['NonoperatingIncomeLoss'], self.filing.fields['InterestAndDebtExpense'])

        #Impute: Net income available to common stockholders  (if it does not exist)
        if not self.filing.fields['NetIncomeAvailableToCommonStockholdersBasic'] and not self.filing.fields['PreferredStockDividendsAndOtherAdjustments'] and self.filing.fields['NetIncomeAttributableToParent']:
            self.filing.fields['NetIncomeAvailableToCommonStockholdersBasic'] = self.filing.fields['NetIncomeAttributableToParent']
                
        #Impute NetIncomeLoss
        if not self.filing.fields['IncomeFromContinuingOperationsAfterTax']:
            if self.filing.fields['NetIncomeLoss']:
                self.filing.fields['IncomeFromContinuingOperationsAfterTax'] = self.filing.fields['NetIncomeLoss']
                if self.filing.fields['IncomeFromDiscontinuedOperations']:
                    self.filing.fields['IncomeFromContinuingOperationsAfterTax'] = self.impute(-1, self.filing.fields['IncomeFromContinuingOperationsAfterTax'], self.filing.fields['IncomeFromDiscontinuedOperations'])
                    if self.filing.fields['ExtraordaryItemsGainLoss']:
                        self.filing.fields['IncomeFromContinuingOperationsAfterTax'] = self.impute(-1, self.filing.fields['IncomeFromContinuingOperationsAfterTax'], self.filing.fields['ExtraordaryItemsGainLoss'])

        #Impute: Net income attributable to parent if it does not exist
        if not self.filing.fields['NetIncomeAttributableToParent'] and not self.filing.fields['NetIncomeAttributableToNoncontrollingInterest'] and self.filing.fields['NetIncomeLoss']:
            self.filing.fields['NetIncomeAttributableToParent'] = self.filing.fields['NetIncomeLoss']

        #Impute: PreferredStockDividendsAndOtherAdjustments
        if not self.filing.fields['PreferredStockDividendsAndOtherAdjustments'] and self.filing.fields['NetIncomeAttributableToParent'] and self.filing.fields['NetIncomeAvailableToCommonStockholdersBasic']:
            self.filing.fields['PreferredStockDividendsAndOtherAdjustments'] = self.impute(-1, self.filing.fields['NetIncomeAttributableToParent'], self.filing.fields['NetIncomeAvailableToCommonStockholdersBasic'])

        #Impute: comprehensive income
        if not self.filing.fields['ComprehensiveIncomeAttributableToParent'] and not self.filing.fields['ComprehensiveIncomeAttributableToNoncontrollingInterest'] and not self.filing.fields['ComprehensiveIncome'] and not self.filing.fields['OtherComprehensiveIncome']:
            self.filing.fields['ComprehensiveIncome'] = self.filing.fields['NetIncomeLoss']
                
        #Impute: other comprehensive income
        if self.filing.fields['ComprehensiveIncome'] and not self.filing.fields['OtherComprehensiveIncome']:
            self.filing.fields['OtherComprehensiveIncome'] = self.impute(-1, self.filing.fields['ComprehensiveIncome'], self.filing.fields['NetIncomeLoss'])

        #Impute: comprehensive income attributable to parent if it does not exist
        if not self.filing.fields['ComprehensiveIncomeAttributableToParent'] and not self.filing.fields['ComprehensiveIncomeAttributableToNoncontrollingInterest'] and self.filing.fields['ComprehensiveIncome']:
            self.filing.fields['ComprehensiveIncomeAttributableToParent'] = self.filing.fields['ComprehensiveIncome']

        #Impute: IncomeFromContinuingOperations*Before*Tax
        if self.filing.fields['IncomeBeforeEquityMethodInvestments'] and self.filing.fields['IncomeFromEquityMethodInvestments'] and not self.filing.fields['IncomeFromContinuingOperationsBeforeTax']:
            self.filing.fields['IncomeFromContinuingOperationsBeforeTax'] = self.impute(1, self.filing.fields['IncomeBeforeEquityMethodInvestments'], self.filing.fields['IncomeFromEquityMethodInvestments'])
                
        #Impute: IncomeFromContinuingOperations*Before*Tax2 (if income before tax is missing)
        if not self.filing.fields['IncomeFromContinuingOperationsBeforeTax'] and self.filing.fields['IncomeFromContinuingOperationsAfterTax']:
            self.filing.fields['IncomeFromContinuingOperationsBeforeTax'] = self.impute(1, self.filing.fields['IncomeFromContinuingOperationsAfterTax'], self.filing.fields['IncomeTaxExpenseBenefit'])
                
        #Impute: IncomeFromContinuingOperations*After*Tax
        if not self.filing.fields['IncomeFromContinuingOperationsAfterTax'] and (self.filing.fields['IncomeTaxExpenseBenefit'] or not self.filing.fields['IncomeTaxExpenseBenefit']) and self.filing.fields['IncomeFromContinuingOperationsBeforeTax']:
            self.filing.fields['IncomeFromContinuingOperationsAfterTax'] = self.impute(-1, self.filing.fields['IncomeFromContinuingOperationsBeforeTax'], self.filing.fields['IncomeTaxExpenseBenefit'])                
                
        #Impute: GrossProfit
        if not self.filing.fields['GrossProfit'] and (self.filing.fields['Revenues'] and self.filing.fields['CostOfRevenue']):
            self.filing.fields['GrossProfit'] = self.impute(-1, self.filing.fields['Revenues'], self.filing.fields['CostOfRevenue'])
                
        #Impute: GrossProfit
        if not self.filing.fields['GrossProfit'] and (self.filing.fields['Revenues'] and self.filing.fields['CostOfRevenue']):
            self.filing.fields['GrossProfit'] = self.impute(-1, self.filing.fields['Revenues'], self.filing.fields['CostOfRevenue'])
                
        #Impute: Revenues
        if self.filing.fields['GrossProfit'] and (not self.filing.fields['Revenues'] and self.filing.fields['CostOfRevenue']):
            self.filing.fields['Revenues'] = self.impute(1, self.filing.fields['GrossProfit'], self.filing.fields['CostOfRevenue'])
                
        #Impute: CostOfRevenue
        if self.filing.fields['GrossProfit'] and (self.filing.fields['Revenues'] and not self.filing.fields['CostOfRevenue']):
            self.filing.fields['CostOfRevenue'] = self.impute(1, self.filing.fields['GrossProfit'], self.filing.fields['Revenues'])
     
        #Impute: CostsAndExpenses (would NEVER have costs and expenses if has gross profit, gross profit is multi-step and costs and expenses is single-step)
        if not self.filing.fields['GrossProfit'] and not self.filing.fields['CostsAndExpenses'] and (self.filing.fields['CostOfRevenue'] and self.filing.fields['OperatingExpenses']):
            self.filing.fields['CostsAndExpenses'] = self.impute(1, self.filing.fields['CostOfRevenue'], self.filing.fields['OperatingExpenses'])
                
        #Impute: CostsAndExpenses based on existance of both costs of revenues and operating expenses
        if not self.filing.fields['CostsAndExpenses'] and self.filing.fields['OperatingExpenses'] and (self.filing.fields['CostOfRevenue']):
            self.filing.fields['CostsAndExpenses'] = self.impute(1, self.filing.fields['CostOfRevenue'], self.filing.fields['OperatingExpenses'])
                
        #Impute: CostsAndExpenses
        if not self.filing.fields['GrossProfit'] and not self.filing.fields['CostsAndExpenses']:
            if self.filing.fields['Revenues']:
                self.filing.fields['CostsAndExpenses'] = self.filing.fields['Revenues']
                if self.filing.fields['OperatingIncomeLoss']:
                    self.filing.fields['CostsAndExpenses'] = self.impute(1, self.filing.fields['CostsAndExpenses'], self.filing.fields['OperatingIncomeLoss'])
                    if self.filing.fields['OtherOperatingIncome']:
                        self.filing.fields['CostsAndExpenses'] = self.impute(-1, self.filing.fields['CostsAndExpenses'], self.filing.fields['OtherOperatingIncome'])
                
        #Impute: OperatingExpenses based on existance of costs and expenses and cost of revenues
        if not self.filing.fields['OperatingExpenses'] and self.filing.fields['CostOfRevenue'] and self.filing.fields['CostsAndExpenses']:
            self.filing.fields['OperatingExpenses'] = self.impute(-1, self.filing.fields['CostsAndExpenses'], self.filing.fields['CostOfRevenue'])
                
        #Impute: CostOfRevenues single-step method
        # ???
        if self.filing.fields['Revenues'] and not self.filing.fields['GrossProfit'] and \
            (self.impute(-1, self.filing.fields['Revenues'], self.filing.fields['CostsAndExpenses'])==self.filing.fields['OperatingIncomeLoss']) and \
            not self.filing.fields['OperatingExpenses'] and not self.filing.fields['OtherOperatingIncome']:
            self.filing.fields['CostOfRevenue'] = self.impute(-1, self.filing.fields['CostsAndExpenses'], self.filing.fields['OperatingExpenses'])

        #Impute: IncomeBeforeEquityMethodInvestments
        if not self.filing.fields['IncomeBeforeEquityMethodInvestments'] and self.filing.fields['IncomeFromContinuingOperationsBeforeTax']:
            self.filing.fields['IncomeBeforeEquityMethodInvestments'] = self.impute(-1, self.filing.fields['IncomeFromContinuingOperationsBeforeTax'], self.filing.fields['IncomeFromEquityMethodInvestments'])
                
        #Impute: InterestAndDebtExpense
        if not self.filing.fields['InterestAndDebtExpense']:
            if self.filing.fields['OperatingIncomeLoss'] and self.filing.fields['NonoperatingIncomeLoss'] and self.filing.fields['IncomeBeforeEquityMethodInvestments']:
                self.filing.fields['InterestAndDebtExpense'] = self.impute(-1, self.filing.fields['IncomeBeforeEquityMethodInvestments'], self.impute(1, self.filing.fields['OperatingIncomeLoss'], self.filing.fields['NonoperatingIncomeLoss']))
        
        #Impute: OtherOperatingIncome
        if self.filing.fields['GrossProfit'] and (self.filing.fields['OperatingExpenses'] and self.filing.fields['OperatingIncomeLoss']):
            self.filing.fields['OtherOperatingIncome'] = self.impute(-1, self.filing.fields['OperatingIncomeLoss'], self.impute(-1, self.filing.fields['GrossProfit'], self.filing.fields['OperatingExpenses']))

        #Move IncomeFromEquityMethodInvestments
        if self.filing.fields['IncomeFromEquityMethodInvestments'] and self.filing.fields['IncomeBeforeEquityMethodInvestments'] and \
          self.filing.fields['IncomeBeforeEquityMethodInvestments']!=self.filing.fields['IncomeFromContinuingOperationsBeforeTax']:
            self.filing.fields['IncomeBeforeEquityMethodInvestments'] = self.impute(-1, self.filing.fields['IncomeFromContinuingOperationsBeforeTax'], self.filing.fields['IncomeFromEquityMethodInvestments'])
            self.filing.fields['OperatingIncomeLoss'] = self.impute(-1, self.filing.fields['OperatingIncomeLoss'], self.filing.fields['IncomeFromEquityMethodInvestments'])
        
        #DANGEROUS!!  May need to turn off. IS3 had 2085 PASSES WITHOUT this imputing. if it is higher,: keep the test
        #Impute: OperatingIncomeLoss
        if not self.filing.fields['OperatingIncomeLoss'] and self.filing.fields['IncomeBeforeEquityMethodInvestments']:
            self.filing.fields['OperatingIncomeLoss'] = self.impute(1, self.filing.fields['IncomeBeforeEquityMethodInvestments'], self.impute(-1, self.filing.fields['NonoperatingIncomeLoss'], self.filing.fields['InterestAndDebtExpense']))

        # Description?                       
        self.filing.fields['NonoperatingIncomePlusInterestAndDebtExpensePlusIncomeFromEquityMethodInvestments'] = self.impute(-1, self.filing.fields['IncomeFromContinuingOperationsBeforeTax'], self.filing.fields['OperatingIncomeLoss'])
        
        #NonoperatingIncomeLossPlusInterestAndDebtExpense
        if not self.filing.fields['NonoperatingIncomeLossPlusInterestAndDebtExpense'] and self.filing.fields['NonoperatingIncomePlusInterestAndDebtExpensePlusIncomeFromEquityMethodInvestments'] and self.filing.fields['IncomeFromEquityMethodInvestments']:
            self.filing.fields['NonoperatingIncomeLossPlusInterestAndDebtExpense'] = self.impute(-1, self.filing.fields['NonoperatingIncomePlusInterestAndDebtExpensePlusIncomeFromEquityMethodInvestments'], self.filing.fields['IncomeFromEquityMethodInvestments'])

        # Tries non-core nodes if WAV not present in core tables
        self.filing.fields['WeightedAverageDilutedShares'] = self.collapse(self.filing.name_matches('WeightedAverageNumberOfDilutedSharesOutstanding'))
        if not self.filing.fields['WeightedAverageDilutedShares']:
            self.filing.fields['WeightedAverageDilutedShares'] = self.collapse(self.filing.name_matches('WeightedAverageNumberOfDilutedSharesOutstanding'))
            if not self.filing.fields['WeightedAverageDilutedShares']:
                self.filing.fields['WeightedAverageDilutedShares'] = self.collapse(self.filing.name_matches('WeightedAverageNumberBasicDilutedSharesOutstanding'))
                if not self.filing.fields['WeightedAverageDilutedShares']:
                    self.collapse(self.filing.name_matches('WeightedAverageNumberBasicDilutedSharesOutstanding', non_core=True))
            
        self.filing.fields['EarningsPerShare'] = self.filing.name_matches('EarningsPerShareDiluted')
        if not self.filing.fields['EarningsPerShare']:
            self.filing.fields['EarningsPerShare'] = self.filing.name_matches('EarningsPerShareBasicAndDiluted')
            if not self.filing.fields['EarningsPerShare']:
                self.filing.fields['EarningsPerShare'] = self.filing.name_matches('BasicDilutedEarningsPerShareNetIncome', non_core=True)
                if not self.filing.fields['EarningsPerShare']:
                    self.filing.fields['EarningsPerShare'] = self.filing.name_matches('BasicAndDilutedLossPerShare')

        # If wtd avg shares above didn't work, impute from earnings per share
        if not self.filing.fields['WeightedAverageDilutedShares']:
            if self.filing.fields['EarningsPerShare'] and self.filing.fields['NetIncomeLoss']:
                self.filing.fields['WeightedAverageDilutedShares'] = self.impute(1, self.filing.fields['NetIncomeLoss'], self.filing.fields['EarningsPerShare'], func=self.divide)
        

        self.filing.fields['ResearchAndDevelopment'] = self.filing.name_matches('ResearchAndDevelopmentExpense')
        if not self.filing.fields['ResearchAndDevelopment']:
            self.filing.fields['ResearchAndDevelopment'] = self.filing.name_matches('TechnologyServicesCosts')

        self.filing.fields['SellingGeneralAndAdministrative'] = self.filing.name_matches('SellingGeneralAndAdministrativeExpense')
        if not self.filing.fields['SellingGeneralAndAdministrative']:
            self.filing.fields['SellingGeneralAndAdministrative'] = self.filing.name_matches('SellingAndMarketingExpense')

        self.filing.fields['InterestExpense'] = self.filing.name_matches('InterestExpense')
        self.filing.fields['InvestmentIncomeInterest'] = self.filing.name_matches('InterestExpense')

        

        ###Cash flow statement

        #NetCashFlow
        self.filing.fields['NetCashFlow'] = self.filing.name_matches("CashAndCashEquivalentsPeriodIncreaseDecrease")
        if self.filing.fields['NetCashFlow'] == []:
            self.filing.fields['NetCashFlow'] = self.filing.name_matches("CashPeriodIncreaseDecrease")
            if self.filing.fields['NetCashFlow'] == []:
                self.filing.fields['NetCashFlow'] = self.filing.name_matches("NetCashProvidedByUsedInContinuingOperations")
                
        #NetCashFlowsOperating
        self.filing.fields['NetCashFlowsOperating'] = self.filing.name_matches("NetCashProvidedByUsedInOperatingActivities")
    
        #NetCashFlowsInvesting
        self.filing.fields['NetCashFlowsInvesting'] = self.filing.name_matches("NetCashProvidedByUsedInInvestingActivities")
                
        #NetCashFlowsFinancing
        self.filing.fields['NetCashFlowsFinancing'] = self.filing.name_matches("NetCashProvidedByUsedInFinancingActivities")
                
        #NetCashFlowsOperatingContinuing
        self.filing.fields['NetCashFlowsOperatingContinuing'] = self.filing.name_matches("NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")
                
        #NetCashFlowsInvestingContinuing
        self.filing.fields['NetCashFlowsInvestingContinuing'] = self.filing.name_matches("NetCashProvidedByUsedInInvestingActivitiesContinuingOperations")
                
        #NetCashFlowsFinancingContinuing
        self.filing.fields['NetCashFlowsFinancingContinuing'] = self.filing.name_matches("NetCashProvidedByUsedInFinancingActivitiesContinuingOperations")
        
        #NetCashFlowsOperatingDiscontinued
        self.filing.fields['NetCashFlowsOperatingDiscontinued'] = self.filing.name_matches("CashProvidedByUsedInOperatingActivitiesDiscontinuedOperations")
                
        #NetCashFlowsInvestingDiscontinued
        self.filing.fields['NetCashFlowsInvestingDiscontinued'] = self.filing.name_matches("CashProvidedByUsedInInvestingActivitiesDiscontinuedOperations")
                
        #NetCashFlowsFinancingDiscontinued
        self.filing.fields['NetCashFlowsFinancingDiscontinued'] = self.filing.name_matches("CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations")
                        
        #NetCashFlowsDiscontinued
        self.filing.fields['NetCashFlowsDiscontinued'] = self.filing.name_matches("NetCashProvidedByUsedInDiscontinuedOperations")
        
        #ExchangeGainsLosses
        self.filing.fields['ExchangeGainsLosses'] = self.filing.name_matches("EffectOfExchangeRateOnCashAndCashEquivalents")
        if self.filing.fields['ExchangeGainsLosses'] == []:
            self.filing.fields['ExchangeGainsLosses'] = self.filing.name_matches("EffectOfExchangeRateOnCashAndCashEquivalentsContinuingOperations")
            if self.filing.fields['ExchangeGainsLosses'] == []:
                self.filing.fields['ExchangeGainsLosses'] = self.filing.name_matches("CashProvidedByUsedInFinancingActivitiesDiscontinuedOperations")


        self.filing.fields['DepreciationAndAmortization'] = self.filing.name_matches('DepreciationAndAmortization')
        if not self.filing.fields['DepreciationAndAmortization']:
            self.filing.fields['DepreciationAndAmortization'] = self.filing.name_matches('DepreciationAmortizationAndAccretionNet')
        
        self.filing.fields['CapitalExpenditure'] = self.filing.name_matches('PaymentsToAcquirePropertyPlantAndEquipment')
        if not self.filing.fields['CapitalExpenditure']:
            self.filing.fields['CapitalExpenditure'] = self.filing.name_matches('PaymentsToAcquireProductiveAssets')
            if not self.filing.fields['CapitalExpenditure']:
                self.filing.fields['CapitalExpenditure'] = self.filing.name_matches('PaymentsToAcquireProductiveAssetsAndBuisness', non_core=True)
                

        ####Adjustments

        #Impute: total net cash flows discontinued if not reported
        if not self.filing.fields['NetCashFlowsDiscontinued']:
            self.filing.fields['NetCashFlowsDiscontinued'] = self.filter_agg_sum(self.filing.fields['NetCashFlowsOperatingDiscontinued'], self.filing.fields['NetCashFlowsInvestingDiscontinued'], self.filing.fields['NetCashFlowsFinancingDiscontinued'])

        #Impute: cash flows from continuing
        # These ones are breaky
        if not self.filing.fields['NetCashFlowsOperatingContinuing']:
            if self.filing.fields['NetCashFlowsOperating']:
                self.filing.fields['NetCashFlowsOperatingContinuing'] = self.filing.fields['NetCashFlowsOperating']
                if self.filing.fields['NetCashFlowsOperatingDiscontinued']:
                    self.filing.fields['NetCashFlowsOperatingContinuing'] = self.impute(-1, self.filing.fields['NetCashFlowsOperatingContinuing'], self.filing.fields['NetCashFlowsOperatingDiscontinued'])
            # This logic is confusing but was originally separated out below and can join this if loop
            elif not self.filing.fields['NetCashFlowsOperatingDiscontinued']:
                if self.filing.fields['NetCashFlowsOperatingContinuing']:
                    self.filing.fields['NetCashFlowsOperating'] = self.filing.fields['NetCashFlowsOperatingContinuing']

        if not self.filing.fields['NetCashFlowsInvestingContinuing']:
            if self.filing.fields['NetCashFlowsInvesting']:
                self.filing.fields['NetCashFlowsInvestingContinuing'] = self.filing.fields['NetCashFlowsInvesting']
                if self.filing.fields['NetCashFlowsInvestingDiscontinued']:
                    self.filing.fields['NetCashFlowsInvestingContinuing'] = self.impute(-1, self.filing.fields['NetCashFlowsInvestingContinuing'], self.filing.fields['NetCashFlowsInvestingDiscontinued'])
            elif not self.filing.fields['NetCashFlowsInvestingDiscontinued']:
                if self.filing.fields['NetCashFlowsInvestingContinuing']:
                    self.filing.fields['NetCashFlowsInvesting'] = self.filing.fields['NetCashFlowsInvestingContinuing']
        
        if not self.filing.fields['NetCashFlowsFinancingContinuing']:
            if self.filing.fields['NetCashFlowsFinancing']:
                self.filing.fields['NetCashFlowsFinancingContinuing'] = self.filing.fields['NetCashFlowsFinancing']
                if self.filing.fields['NetCashFlowsFinancingDiscontinued']:
                  self.filing.fields['NetCashFlowsFinancingContinuing'] = self.impute(-1, self.filing.fields['NetCashFlowsFinancingContinuing'], self.filing.fields['NetCashFlowsFinancingDiscontinued'])
        elif not self.filing.fields['NetCashFlowsFinancingDiscontinued']:
            if self.filing.fields['NetCashFlowsFinancingContinuing']:
                self.filing.fields['NetCashFlowsFinancing'] = self.filing.fields['NetCashFlowsFinancingContinuing']
        
        self.filing.fields['NetCashFlowsContinuing'] = self.filter_agg_sum(self.filing.fields['NetCashFlowsOperatingContinuing'], self.filing.fields['NetCashFlowsInvestingContinuing'], self.filing.fields['NetCashFlowsFinancingContinuing'])

        #Impute: if net cash flow is missing,: this tries to figure out the value by adding up the detail
        if not self.filing.fields['NetCashFlow']:
            self.filing.fields['NetCashFlow'] = self.filter_agg_sum(self.filing.fields['NetCashFlowsOperating'], self.filing.fields['NetCashFlowsInvesting'], self.filing.fields['NetCashFlowsFinancing'])

"""