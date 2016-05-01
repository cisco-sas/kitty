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
Tools for testing and manipulating kitty templates.

Usage:
    kitty-tool generate [options] <FILE> <TEMPLATE> ...
    kitty-tool list <FILE>
    kitty-tool --version

Commands:
    generate    generate files with mutated payload
    list        list templates in a file

Options:
    <FILE>                  python file that contains the template
    <TEMPLATE>              template name(s) to generate files from
    --out -o OUTDIR         output directory for the generated mutations [default: out]
    --skip -s SKIP          how many mutations to skip [default: 0]
    --count -c COUNT        end index to generate
    --path -p FIELDPATH     generate mutations only for the field with the given path
    --verbose -v            verbose output
    --filename-format -f FORMAT  format for generated file names [default: %(template)s.%(index)s.bin]
    --version               print version and exit
    --help -h               print this help and exit

File name formats:
    You can control the name of an output file by giving a filename format,
    it follows python's dictionary format string.
    The available keywords are:
        template - the template name
        index - the template index
'''
import os
import sys
import types
import logging
from pkg_resources import get_distribution
from json import dumps
import docopt
from kitty.model import Template


def get_logger(opts):
    logger = logging.getLogger('kitty-tool')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    return logger


class FileIterator(object):

    def __init__(self, filename, handler, logger):
        self.filename = filename
        self.handler = handler
        self.logger = logger

    def check_file(self):
        if not os.path.exists(self.filename):
            raise Exception('File %s does not exist' % self.filename)
        elif not self.filename.endswith('.py'):
            raise Exception('File %s is not python' % self.filename)

    def iterate(self):
        self.check_file()
        self.handler.start()
        dirpath, filename = os.path.split(self.filename)
        modulename = filename[:-3]
        if dirpath in sys.path:
            sys.path.remove(dirpath)
        sys.path.insert(0, dirpath)
        module = __import__(modulename)
        member_names = dir(module)
        for name in member_names:
            attr = getattr(module, name)
            if isinstance(attr, Template):
                self.handler.handle(attr)
            elif isinstance(attr, types.ListType):
                for mem in attr:
                    if isinstance(attr, Template):
                        self.handler.handle(attr)
            elif isinstance(attr, types.DictionaryType):
                for k in attr:
                    if isinstance(attr, Template):
                        self.handler.handle(attr[k])


class Handler(object):

    def __init__(self, logger):
        self.logger = logger

    def start(self):
        pass

    def handle(self, template):
        pass


class FileGeneratorHandler(Handler):

    def __init__(self, opts, logger):
        super(FileGeneratorHandler, self).__init__(logger)
        self.outdir = opts['--out'] or 'out'
        if opts['--skip'] is not None:
            try:
                self.skip = int(opts['--skip'])
            except:
                raise Exception('skip should be a number')
        else:
            self.skip = 0
        self.count = opts['--count']
        if self.count:
            try:
                self.count = int(self.count)
            except:
                raise Exception('count should be a number')
        self.template_names = opts['<TEMPLATE>']
        self.filename_format = opts['--filename-format']
        try:
            self.filename_format % {
                'template': 'hello',
                'index': 1
            }
        except:
            raise Exception('invalid filename template: %s' % (self.filename_format))

    def start(self):
        if os.path.exists(self.outdir):
            raise Exception('cannot create directory %s, already exists' % self.outdir)
        os.mkdir(self.outdir)

    def handle(self, template):
        template_name = template.get_name()
        if template_name in self.template_names:
            self.logger.info('Generating mutation files from template %s into %s' % (template_name, os.path.abspath(self.outdir)))
            template.skip(self.skip)
            self.end_index = template.num_mutations() if not self.count else self.skip + self.count
            self.end_index = min(self.end_index, template.num_mutations()) - 1
            if self.end_index < 0:
                raise Exception('No mutations to generate, are you sure about the count ??')
            if self.skip > template.num_mutations():
                raise Exception('No mutations to generate, you skipped over the entire template')
            self.logger.info('Mutation range: %s-%s' % (self.skip, self.end_index))
            total = (self.end_index - self.skip)
            step = 100.0 / total
#            step = max(step, 2)
            max_line_length = 0
            while template.mutate():
                template_filename = self.filename_format % {'template': template_name, 'index': template._current_index}
                with open(os.path.join(self.outdir, template_filename), 'wb') as f:
                    f.write(template.render().tobytes())
                metadata_filename = template_filename + '.metadata'
                info = template.get_info()
                with open(os.path.join(self.outdir, metadata_filename), 'wb') as f:
                    f.write(dumps(info, indent=4, sort_keys=True))
                out_line = ''
                out_line += '\r%3d%%' % (int((total - (self.end_index - template._current_index)) * step))
                out_line += ' %d/%d' % (template._current_index, self.end_index)
                if 'field/path' in info:
                    out_line += ' %s' % (info['field/path'])
                if len(out_line) > max_line_length:
                    max_line_length = len(out_line)
                else:
                    out_line += ' ' * (max_line_length - len(out_line))
                sys.stdout.write(out_line)
                sys.stdout.flush()
                if template._current_index >= self.end_index:
                    break
            sys.stdout.write('\n')
            sys.stdout.flush()


class ListHandler(Handler):

    def handle(self, template):
        self.logger.info('%-80s %s' % (template.get_name(), template.num_mutations()))


def _main():
    opts = docopt.docopt(__doc__, version=get_distribution('kittyfuzzer').version)
    logger = get_logger(opts)
    try:
        if opts['generate']:
            file_iter = FileIterator(
                opts['<FILE>'],
                FileGeneratorHandler(
                    opts,
                    logger=logger
                ),
                logger
            )
        elif opts['list']:
            file_iter = FileIterator(
                opts['<FILE>'],
                ListHandler(
                    logger
                ),
                logger
            )
        if file_iter:
            file_iter.iterate()
    except Exception as ex:
        logger.error('Error: %s' % ex)
        sys.exit(1)


if __name__ == '__main__':
    _main()
