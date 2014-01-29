
header_labels = ["As of", "Manager", "Issuer", "CUSIP",
                 "Value", "% Tot", "MgrsVal", "MgrsCt", "3Mchg"]

def print_html(filings, filename=None):

    """Print filings to html file"""

    if not filename:
        filename = "holdings.html"

    template_file = "templates/template.html"
    head_tags = [['th', ''] for i in xrange(len(header_labels))]
    body_tags = [['td', 'class=date'],
            ['td', 'class=text_left'],
            ['td', 'class=text_left'],
            ['td', 'class=cusip'],
            ['td', 'class=value'],
            ['td', 'class=percent'],
            ['td', 'class=value'],
            ['td', 'class=value'],
            ['td', 'class=percent']]
    footer_tags = head_tags
    header_string = make_html_row(header_labels, head_tags)
    header = "<thead>{}</thead>".format(header_string)
    tables = []

    # header tags for table body
    
    
    for filing in filings:
        filing_ed = []
        mv_tot = pct_tot = tot_3mchg = 0
        for row in filing:
            row = list(row)
            mv = row[4]
            mv_tot += mv
            row[4] = "{:,}".format(mv)
            pct = 100 * row[5]
            pct_tot += pct
            row[5] = "{:.1f}%".format(pct)
            row[6] = "{:,}".format(row[6])
            row[7] = "{:,}".format(row[7])
            pct_chg = row[8]
            if isinstance(pct_chg, str):
                row[8] = pct_chg
            else:
                row[8] = "{:.1f}%".format(100 * pct_chg)
                tot_3mchg += pct * pct_chg
            filing_ed.append(row)
        tot_3mchg *= 100*pct_tot
        body = make_table_body(filing_ed, body_tags)
        
        footer = ['TOTAL', '', '', '', "{:,}".format(mv_tot),
                  "{:.1f}%".format(pct_tot), '', '', "{:1f}%".format(tot_3mchg)]
        footer_string = make_html_row(footer, footer_tags)
        footer = "<tfoot>{}</tfoot>".format(footer_string)
        
        contents = header + body + footer
        table = "<table>{}</table>".format(contents)
        tables.append(table)

    with open(template_file, 'r') as infile:
        template = infile.read()

    html_output = template.replace("{%block%}",''.join(tables))

    with open(filename, 'wb') as outfile:    
        outfile.write(html_output)