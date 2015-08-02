#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weather cli - Weather from the command line
Basically the script checks your ip, geolocate the ip and
checks the weather based on that information, so cool!
"""

import os
import sys
import ConfigParser
import argparse
import requests
from requests.exceptions import ConnectionError
from geoip import geolite2
import json
import datetime
from tabletext import to_text


class Weather(object):
    ip_url = 'http://ipecho.net/plain'
    forecast_url = 'https://api.forecast.io/forecast'
    api_key = None
    geo = None

    def magic(self, data_type):
        weather_data = self.get_weather()
        self.output(weather_data, data_type)

    def api_key(self, forecast):
        "set forecast.io api key"
        self.api_key = forecast['key']

    def geolocation(self, geo):
        "set geolocation"
        self.geo = geo

    def get_ip(self):
        "check the external ip"
        result = 0
        try:
            headers = {'Content-type': 'application/json'}
            req = requests.get(
                self.ip_url,
                headers=headers,
            )
            result = req.text
        except ConnectionError, error:
            sys.exit(error)
        return result

    @staticmethod
    def get_geolocation(ipaddress):
        "check latitude and longitude of the ip"
        result = {'lat': 0, ' lon': 0}
        try:
            match = geolite2.lookup(ipaddress)
            result['lat'] = float(match.location[0])
            result['lon'] = float(match.location[1])
        except ValueError as error:
            sys.exit(error)
        return result

    def get_weather(self):
        "request weather based on the location"
        geolocation = self.geo
        # check config key
        if not self.api_key:
            sys.exit('You have to provide a Forecast.io API key')
        forecast_url = '%s/%s/%s,%s/%s' % (
            self.forecast_url,
            self.api_key,
            geolocation['lat'],
            geolocation['lon'],
            '?units=si'
        )
        headers = {'Content-type': 'application/json'}
        # force disable insecure request warning
        requests.packages.urllib3.disable_warnings()
        req = requests.get(
            forecast_url,
            headers=headers,
        )
        try:
            return json.loads(req.text)
        except ConnectionError, error:
            sys.exit(error)

    def output(self, weather, data_type):
        "format and output the weather"
        table = []
        # city name
        city = str(weather['timezone']).replace('_', ' ')
        # hourly limit
        if len(weather['hourly']['data']) > 24:
            hourly = weather['hourly']['data'][0:24]
        else:
            hourly = weather['hourly']['data']
        # current weather
        if data_type == 'now':
            print ''
            print '%s now' % city
            table.append(['summary', 'temp', 'term', 'humidity'])
            table.append([weather['currently']['summary'],
                          self.format_temp(
                              weather['currently']['temperature']),
                          self.format_temp(
                              weather['currently']['apparentTemperature']),
                          self.format_percent(weather['currently']['humidity'])])

        # next 24 hours
        if data_type == 'hourly':
            print ''
            print '%s forecast next %s hours' % (city, len(hourly))
            table.append(['day', 'summary', 'temp', 'term', 'humidity'])
            for data in hourly:
                table.append([self.format_timestamp(data['time'], 'hour'),
                              data['summary'],
                              self.format_temp(data['temperature']),
                              self.format_temp(data['apparentTemperature']),
                              self.format_percent(data['humidity'])])

        # next few days
        if data_type == 'forecast':
            print ''
            print '%s forecast next %s days' % (city, len(weather['daily']['data']))
            table.append(['day', 'summary', 'min', 'max', 'humidity', 'rain'])
            for data in weather['daily']['data']:
                table.append([self.format_timestamp(data['time']),
                              data['summary'],
                              self.format_temp(data['temperatureMin']),
                              self.format_temp(data['temperatureMax']),
                              self.format_percent(data['humidity']),
                              self.format_percent(data['precipProbability'])])
        print to_text(table, header=False, corners='+', hor='-', ver='|',
                      formats=['', '', '>', '>', '>', '>'])

    @staticmethod
    def format_timestamp(timestamp, data_type='day'):
        "transform timestamp to datetime"
        date_timestamp = datetime.datetime.fromtimestamp(timestamp)
        today = datetime.date.today()
        # day
        if date_timestamp.strftime('%Y-%m-%d') == today.strftime('%Y-%m-%d'):
            day = 'Today'
        else:
            day = date_timestamp.strftime('%A')
        # hour
        hour = date_timestamp.strftime('%H:%M')
        # check type
        if data_type == 'hour':
            return hour
        return day

    @staticmethod
    def format_temp(temp):
        "format temperature"
        return str(temp) + ' C'

    @staticmethod
    def format_percent(num):
        "format humidity"
        return str(int(float(num) * 100)) + '%'


def load_config():
    "load configuration"
    script = sys.argv[0]
    script_path = os.path.abspath(os.path.dirname(script))
    if not script_path:
        script_path = os.path.abspath('.')
    filename = r'%s/../config/weather.conf' % script_path
    # check if file exists
    if not os.path.isfile(filename):
        sys.exit(
            'Error: you have to create the config file, run %s --setup' % script)
    # load configuration
    config_parser = ConfigParser.RawConfigParser()
    config_parser.read(filename)
    config = {
        'forecast': {
            'key': config_parser.get('forecast', 'key'),
        },
        'geolocation': {
            'lat': config_parser.get('forecast', 'latitude'),
            'lon': config_parser.get('forecast', 'longitude'),
        }
    }
    return config


def setup():
    "help setup the config file"
    script = sys.argv[0]
    script_path = os.path.abspath(os.path.dirname(script))
    if not script_path:
        script_path = os.path.abspath('.')
    filename = r'%s/../config/weather.conf' % script_path
    # read the input
    print 'required parameters'
    api_key = raw_input('Enter the forecast.io api key:')
    print 'optional parameters'
    lat = raw_input('Enter the latitude: ')
    lon = raw_input('Enter the longitude: ')
    # write configuration
    print 'generating config file...'
    fconfig = open(filename, 'w')
    fconfig.write("[forecast]\n")
    fconfig.write("key = %s\n" % api_key)
    fconfig.write("latitude = %s\n" % lat)
    fconfig.write("longitude = %s\n" % lon)
    fconfig.close()
    sys.exit('setup complete')


def arguments():
    "Parse cli arguments"
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='How is outside? Use the weather cli to figure it out.')
    parser.add_argument(
        '--weather', required=False, type=str, help='What you want to know?',
        default='now', choices=['now', 'hourly', 'forecast'])
    parser.add_argument(
        '--setup', help='setup weather', action='store_true')
    parsed_args = parser.parse_args()
    return parsed_args


def main():
    "entry point"
    weather = Weather()
    args = arguments()
    # check if we have to setup the config file
    if args.setup:
        setup()
    # load configuration
    config = load_config()
    # check if we have a lat and long defined on the config
    if config['geolocation']['lat'] == '' or config['geolocation']['lon'] == '':
        ip_address = weather.get_ip()
        geo = weather.get_geolocation(ip_address)
    else:
        geo = config['geolocation']
    # display weather
    weather.api_key(config['forecast'])
    weather.geolocation(geo)
    weather.magic(args.weather)


if __name__ == '__main__':
    main()
