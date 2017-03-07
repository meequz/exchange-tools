#! /usr/bin/env python3
# coding: utf-8
import os
import sys
import io
import time
import datetime
import argparse
import pylab
import http.client
import json


def print_inplace(string):
    string = str(string) + '\r'
    sys.stdout.write(string)
    sys.stdout.flush()


URL_host = 'www.nbrb.by'
URL_path = '/API/ExRates/Rates?Periodicity=0&onDate='

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
directory = 'jsons'
if not os.path.exists(directory):
    os.makedirs(directory)

# create persistent HTTP connection object
conn = http.client.HTTPConnection(URL_host, 80)

# collect data
for idx, plot_date in enumerate(plot_dates):
    # get json
    date_url_formatted = plot_date.strftime('%Y-%m-%d')
    json_filename = plot_date.strftime('%Y-%m-%d.json')
    full_filename = directory + '/' + json_filename
    URL_full = 'http://' + URL_host + URL_path + date_url_formatted

    # report
    print('processing ' + full_filename)

    # download if no such file
    if not os.path.exists(full_filename):
        print('downloading {}    '.format(json_filename))
        print('url: ' + URL_full)
        conn.request('GET', URL_path + date_url_formatted, None, {})
        page = conn.getresponse()
        print('download status: {}; reason: {}'.format(page.status, page.reason))

        jsonText = page.read().decode(encoding='UTF-8')
        if 'html' in jsonText:
            message = 'Too many requests. Wait for 5 minutes and try again. It is {} now. URL: {}'
            print(message.format(datetime.datetime.now().strftime('%H:%M:%S'), URL_full))
            exit()
        with io.open(full_filename, 'w', newline='', encoding='utf-8') as json_file:
            json_file.write(jsonText)

    # read the file
    with io.open(full_filename, 'r', newline='', encoding='utf-8') as json_file:
        jsonText = ''.join(json_file.readlines())
    # if it is not an json or there is no data in it, delete the wrong file and restart
    if 'html' in jsonText or\
       not '[{"Cur_ID":' in jsonText:
        message = 'Wrong file: {}. It has been deleted. Please restart the script to redownload it.'
        print(message.format(full_filename))
        os.remove(full_filename)
        exit()

    # parse json
    jsonData = json.loads(jsonText)
    charcodes = [item['Cur_Abbreviation'] for item in jsonData]
    rates = [float(item['Cur_OfficialRate']) for item in jsonData]

    # collect the data
    for currency in currencies:
        replace_currency = currency

        # hack for russian ruble
        if currency == 'RUR' and \
           plot_date >= datetime.datetime.strptime('20030101', '%Y%m%d'):
            replace_currency = 'RUB'
        if currency == 'RUB' and \
           plot_date < datetime.datetime.strptime('20030101', '%Y%m%d'):
            replace_currency = 'RUR'

        # hack for polish zloty
        if currency == 'PLZ' and \
           plot_date >= datetime.datetime.strptime('20030104', '%Y%m%d'):
            replace_currency = 'PLN'
        if currency == 'PLN' and \
           plot_date < datetime.datetime.strptime('20030101', '%Y%m%d'):
            replace_currency = 'PLZ'

        rate_factor = 1.0
        # hack for belarussian rubble denomination 2016
        if plot_date < datetime.datetime.strptime('20160701', '%Y%m%d'):
            rate_factor = 0.0001

        try:
            currency_idx = charcodes.index(replace_currency)
        except ValueError:
            message = 'problem with currency {} in {}. Empty point added. URL: {}'
            print(message.format(replace_currency, full_filename, URL_full))
            plot_currencies[currency].append(None)
            continue
        rate = rates[currency_idx] * rate_factor
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
