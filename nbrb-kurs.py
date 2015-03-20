#! /usr/bin/env python3
# coding: utf-8
import os
import time
import datetime
import argparse
import pylab
import urllib.request
from bs4 import BeautifulSoup


URL = 'http://www.nbrb.by/Services/XmlExRates.aspx?ondate='

# arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', dest='dates', help='A date or the date range.')
parser.add_argument('-c', dest='currencies', help='Currency or currencies.')
args = parser.parse_args()


# parse dates
if '-' in args.dates:
    splitted = args.dates.split('-')
    start = datetime.datetime.strptime(splitted[0], '%Y%m%d')
    end = datetime.datetime.strptime(splitted[1], '%Y%m%d')
    end += datetime.timedelta(days=1)
    delta = end - start
    plot_dates = [start + datetime.timedelta(days=i) for i in range(delta.days)]
    dates = [date.strftime('%m/%d/%Y') for date in plot_dates]
else:
    start = datetime.datetime.strptime(args.dates, '%Y%m%d')
    end = start + datetime.timedelta(days=1)
    plot_dates = [start, end]
    dates = [date.strftime('%m/%d/%Y') for date in plot_dates]


# parse currencies
currencies = args.currencies.split(',')
plot_currencies = {}
for currency in currencies:
    plot_currencies[currency] = []


# check if path exists
directory = 'xmls'
if not os.path.exists(directory):
    os.makedirs(directory)


# collect data
for idx, date in enumerate(dates):
    # get xml
    xml_filename = plot_dates[idx].strftime('%Y-%m-%d.xml')
    full_filename = directory + '/' + xml_filename
    
    # download if no such file
    if not os.path.exists(full_filename):
        print('downloading {}'.format(xml_filename))
        page = urllib.request.urlopen(URL + date)
        xml = page.read().decode(encoding='UTF-8')
        if 'html' in xml:
            print('Too many requests. Wait some time and try again. URL:', URL+date)
            exit()
        with open(full_filename, 'w') as xml_file:
            xml_file.write(xml)
        time.sleep(0.35)
    
    # read the file
    with open(full_filename) as xml_file:
        xml = ''.join(xml_file.readlines())
    if 'html' in xml:
        print('Please restart the script.')
        os.remove(full_filename)
        exit()
    
    # parse xml
    soup = BeautifulSoup(xml)
    charcodes = [item.contents[0] for item in soup.find_all('charcode')]
    rates = [float(item.contents[0]) for item in soup.find_all('rate')]
    
    # collect the data
    for currency in currencies:
        hack_currency = currency
        
        # hack for russian ruble
        if currency == 'RUR' and \
           plot_dates[idx] >= datetime.datetime.strptime('20030101', '%Y%m%d'):
            hack_currency = 'RUB'
        if currency == 'RUB' and \
           plot_dates[idx] < datetime.datetime.strptime('20030101', '%Y%m%d'):
            hack_currency = 'RUR'
        
        try:
            currency_idx = charcodes.index(hack_currency)
        except ValueError:
            print('problem with currency {} in {}. URL: {}'.format(hack_currency, full_filename, URL+date))
            exit()
        rate = rates[currency_idx]
        plot_currencies[currency].append(rate)


# plot data
for currency, rates in plot_currencies.items():
    pylab.xticks(rotation=30)
    pylab.plot(plot_dates, rates, label=currency)

# legend
legend = pylab.legend(loc='best', shadow=True, ncol=len(currencies)*2, prop={'size':12})
for label in legend.get_lines():
    label.set_linewidth(4)

# show the plot
pylab.grid()
pylab.show()
