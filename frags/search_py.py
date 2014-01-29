def search():#Needs to be adjusted to new format
    """Prints results from DB using Manager, Issuer and/or Asof input"""

    filings = []

    manager = issuer = ''
    manager = raw_input("Manager Name (enter if all): ")
    issuer = raw_input("Issuer (enter for all): ")
    
    default = '2013-09-30'
    asof = raw_input("As of (YYYY-MM-DD) or 'all': %s" %
                     default + chr(8)*len(default))
    if not asof:
        asof = default

    if asof.lower() == 'all':
        #Get all dates for provided parameters
        dates = sql.get_dates(db, manager, issuer)
    else:
        dates = [[asof, ]]

    for date in dates:
        asof = date[0]#each 'date' is a tuple
        holdings = list(sql.sql_query(db, manager, issuer, asof))
        # Adds return data        
        
        for i, holding in enumerate(holdings):
            lagged_date = stocks.end_of_month(asof, -3)
            cusip = holding[3]
            ticker = stocks.cusip_to_ticker(cusip)

            pct_chg = stocks.get_change(ticker, lagged_date, asof)
            holding += (pct_chg,)
            holdings[i] = holding
        filings.append(holdings)

    return filings