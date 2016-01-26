#!/usr/bin/env python
# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.
'''
Usage:
    kitty_web_client.py (info [-v]|pause|resume) [--host <hostname>] [--port <port>]
    kitty_web_client.py reports store <folder> [--host <hostname>] [--port <port>]
    kitty_web_client.py reports show <file> ...

Retrieve and parse kitty status and reports from a kitty web server

Options:
    -v --verbose            verbose information
    -h --host <hostname>    kitty web server host [default: localhost]
    -p --port <port>        kitty web server port [default: 26000]
'''
import requests
import os
import docopt
import json
import types


class KittyWebApi(object):

    def __init__(self, host, port):
        '''
        :param host: server hostname
        :param port: server port
        :param reports_dir: directory to store reports
        '''
        self.url = 'http://%(host)s:%(port)s' % {'host': host, 'port': port}

    def get_stats(self):
        '''
        Get kitty stats as a dictionary
        '''
        resp = requests.get('%s/api/stats.json' % self.url)
        assert(resp.status_code == 200)
        return resp.json()

    def get_report_list(self):
        '''
        Get list of report ids
        '''
        return self.get_stats()['reports']

    def get_reports(self, report_ids):
        '''
        Get reports by list of ids
        :param report_ids: list of reports ids
        :return dictionary of id/report (json string)
        '''
        res = {}
        for rid in report_ids:
            print('Fetching report %d' % rid)
            resp = requests.get('%s/api/report?report_id=%d' % (self.url, rid))
            if resp.status_code != 200:
                print('[!] failed to fetch report %d' % rid)
            else:
                res[rid] = resp.text
        return res

    def pause(self):
        requests.get('%s/api/action/pause' % (self.url))

    def resume(self):
        requests.get('%s/api/action/resume' % (self.url))


def cmd_report_store(options, web):
    folder = options['<folder>']
    folder = './%s' % folder
    if not os.path.exists(folder):
        os.mkdir(folder)
    ids = web.get_report_list()
    reports = web.get_reports(ids)
    for (rid, report) in reports.items():
        with open('%s/report_%d.json' % (folder, rid), 'w') as f:
            f.write(report)


def cmd_report_show(options):
    filenames = options['<file>']
    for filename in filenames:
        with open(filename, 'r') as f:
            report = json.load(f)['report']
            print_report(report, depth=0)


def indent_print(depth, key, val=None):
    if val is None:
        print(('    ' * depth) + key)
    else:
        pre_len = len(key)
        first = True
        for line in val.split('\n'):
            print(('    ' * depth) + key + line)
            if first:
                key = ' ' * pre_len
                first = False


def format_key(k):
    return k.replace('_', ' ')


def print_report(report, depth):
    name = report['name'].decode('base64')
    del report['name']
    sub_reports = report['sub_reports']
    del report['sub_reports']
    indent_print(depth, '***** Report: %s *****' % name)
    for k in sorted(report.keys()):
        if k not in sub_reports:
            val = report[k]
            if isinstance(val, types.StringTypes):
                val = val.decode('base64')
            key = format_key(k)
            try:
                indent_print(depth + 1, '%-20s' % (key + ':'), '%s' % val)
            except UnicodeDecodeError:
                indent_print(depth + 1, '%-20s' % (key + ':'), '%s' % val.encode('hex'))
    for sr in sorted(sub_reports):
        print_report(report[sr], depth + 1)


def cmd_info(options, web):
    resp = web.get_stats()
    print('--- Stats ---')
    stats = resp['stats']
    for k, v in stats.items():
        print('%s: %s' % (k, v))
    print
    print('--- Current Test Info ---')
    info = resp['current_test']
    max_len = max(len(k) for k in info.keys())
    for k, v in sorted(info.items()):
        pad = ' ' * (max_len - len(k))
        print('%s:%s %s' % (k, pad, v))
    if options['--verbose']:
        reports = resp['reports']
        print
        print('--- Report list ---')
        print(','.join('%s' % i for i in reports))


def _main():
    options = docopt.docopt(__doc__)
    web = KittyWebApi(options['--host'], int(options['--port']))
    if options['reports']:
        if options['store']:
            cmd_report_store(options, web)
        elif options['show']:
            cmd_report_show(options)
    elif options['info']:
        cmd_info(options, web)
    elif options['pause']:
        web.pause()
    elif options['resume']:
        web.resume()


if __name__ == '__main__':
    _main()
