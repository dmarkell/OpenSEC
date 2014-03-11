# [OpenSEC](http://open-sec.appspot.com/): An open source dashboard to the SEC Edgar system.

## Overview

The SEC's Electronic Data-Gathering, Analysis, and Retrieval allows automatic and standardized submission of regulatory filings by publicly traded U.S. and foreign U.S.-listed companies and regulated investor entities.

The SEC provides a fast and convenient [interface](http://www.sec.gov/cgi-bin/browse-edgar?) for searching and retrieving company and entity filings. Additionally, several third party companies provide paid or free services for aggregating or viewing filings, including:

- Thomson-Reuters
- Bloomberg
- [S&P Capital IQ](https://www.capitaliq.com/), a part of McGraw Hill Financial
- [EdgarPro](http://pro.edgar-online.com/) by EDGAROnline, Inc., an R.R. Donnelley & Sons Company.
- [Yahoo Finance](http://finance.yahoo.com/)
- [Google Finance](https://www.google.com/finance)

## Why EdgarDash?

This web app is a simple interface for viewing historical reported holdings of institutional investors with easy links to further data on those companies based on their own filings.

## Public Company Filings

Quarterly 10-Q and 10-K filings are parsed for the selected company and summarized.

## Stock prices

Yahoo Finance prices for the selected company stock are presented in an interactive, scrubbable D3.js chart.

## Institutional holders

Quarterly 13F filings are parsed, sorted and summarized, and presented with links to individual company summaries as well as lists of other holders an historical activity for the filing.

# License

Licensed under the [MIT](http://www.opensource.org/licenses/mit-license.php) license.