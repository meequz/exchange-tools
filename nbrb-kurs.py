#! /usr/bin/env python3
# coding: utf-8
import os
import sys
import time
import datetime
import argparse
import pylab
import urllib.request
from bs4 import BeautifulSoup


def print_inplace(string):
    string = str(string) + '\r'
    sys.stdout.write(string)
    sys.stdout.flush()


URL = 'http://www.nbrb.by/Services/XmlExRates.aspx?ondate='

# arguments
parser = argparse.ArgumentParser()
parser.add_argument('-d', dest='dates',
                    help='A date or the date range. If not specified,' +
                    ' two last months will be showed.')
parser.add_argument('-c', dest='currencies',
                    help='ISO 4217 code of currency or currencies.' +
                    ' If not specified, EUR and USD will be showed.')
parser.add_argument('-e', action='store_true', help='See usage examples.')
args = parser.parse_args()


# parse e
if args.e:
    message = 'How to use:\n'
    message += 'python nbrb-kurs.py\n' + \
            '\t- see USD and EUR for two last months\n'
    message += 'python nbrb-kurs.py -c XDR,USD,EUR\n' + \
            '\t- see XDR, USD and EUR for two last months\n'
    message += 'python nbrb-kurs.py -d 20140101 -c USD,XDR,EUR\n' + \
            '\t- see XDR, USD and EUR from 1 Jan 2014 to 2 Jan 2014\n'
    message += 'python nbrb-kurs.py -d 20140101-20150325 -c USD,UAH\n' + \
            '\t- see USD and UAH from 1 Jan 2014 to 25 March 2015\n'
    message += 'python nbrb-kurs.py -d 20140101-today -c UAH,RUB\n' + \
            '\t- see UAH and RUB from 1 Jan 2014 to today\n'
    message += 'python nbrb-kurs.py -d 20140101-today\n' + \
            '\t- see USD and EUR from 1 Jan 2014 to today\n'
    print(message)
    exit()


# parse dates
if args.dates is None:
    start = datetime.datetime.now() - datetime.timedelta(days=60)
    plot_dates = [start + datetime.timedelta(days=i) for i in range(60)]
else:
    if '-' in args.dates:
        splitted = args.dates.split('-')
        start = datetime.datetime.strptime(splitted[0], '%Y%m%d')
        if splitted[1] != 'today':
            end = datetime.datetime.strptime(splitted[1], '%Y%m%d')
        else:
            end = datetime.datetime.now()
        end += datetime.timedelta(days=1)
        delta = end - start
        plot_dates = [start + datetime.timedelta(days=i) for i in range(delta.days)]
    elif args.dates == 'today':
        start = datetime.datetime.now()
        end = start + datetime.timedelta(days=1)
        plot_dates = [start, end]
    else:
        start = datetime.datetime.strptime(args.dates, '%Y%m%d')
        end = start + datetime.timedelta(days=1)
        plot_dates = [start, end]
dates = [date.strftime('%m/%d/%Y') for date in plot_dates]


# parse currencies
if args.currencies is None:
    currencies = ['EUR', 'USD']
else:
    currencies = args.currencies.split(',')
    currencies = [currency.strip() for currency in currencies]
plot_currencies = {currency: [] for currency in currencies}


# check if path exists
directory = 'xmls'
if not os.path.exists(directory):
    os.makedirs(directory)


# collect data
for idx, date in enumerate(dates):
    # get xml
    xml_filename = plot_dates[idx].strftime('%Y-%m-%d.xml')
    full_filename = directory + '/' + xml_filename
    
    # report
    print_inplace('processing ' + full_filename)
    
    # download if no such file
    if not os.path.exists(full_filename):
        print_inplace('downloading {}    '.format(xml_filename))
        page = urllib.request.urlopen(URL + date)
        xml = page.read().decode(encoding='UTF-8')
        if 'html' in xml:
            message = 'Too many requests. Wait for 5 minutes and try again. It is {} now. URL: {}'
            print(message.format(datetime.datetime.now().strftime('%H:%M:%S'), URL+date))
            exit()
        with open(full_filename, 'w') as xml_file:
            xml_file.write(xml)
        time.sleep(1)
    
    # read the file
    with open(full_filename) as xml_file:
        xml = ''.join(xml_file.readlines())
    # if it is not an xml or there is no data in it, delete the wrong file and restart
    if 'html' in xml or\
       not 'CharCode' in xml:
        message = 'Wrong file: {}. It has been deleted. Please restart the script to redownload it.'
        print(message.format(full_filename))
        os.remove(full_filename)
        exit()
    
    # parse xml
    soup = BeautifulSoup(xml)
    charcodes = [item.contents[0] for item in soup.find_all('charcode')]
    rates = [float(item.contents[0]) for item in soup.find_all('rate')]
    
    # collect the data
    for currency in currencies:
        replace_currency = currency
        
        # hack for russian ruble
        if currency == 'RUR' and \
           plot_dates[idx] >= datetime.datetime.strptime('20030101', '%Y%m%d'):
            replace_currency = 'RUB'
        if currency == 'RUB' and \
           plot_dates[idx] < datetime.datetime.strptime('20030101', '%Y%m%d'):
            replace_currency = 'RUR'
        
        # hack for polish zloty
        if currency == 'PLZ' and \
           plot_dates[idx] >= datetime.datetime.strptime('20030104', '%Y%m%d'):
            replace_currency = 'PLN'
        if currency == 'PLN' and \
           plot_dates[idx] < datetime.datetime.strptime('20030101', '%Y%m%d'):
            replace_currency = 'PLZ'
        
        try:
            currency_idx = charcodes.index(replace_currency)
        except ValueError:
            message = 'problem with currency {} in {}. Empty point added. URL: {}'
            print(message.format(replace_currency, full_filename, URL+date))
            plot_currencies[currency].append(None)
            continue
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
