#!/usr/bin/env python
"""
void-sniffer 0.2

Searches for FITS files without a custom header and outputs their paths.

Usage:
  void-sniffer SEARCH_DIR [--tmin=TIME_MIN] [--tmax=TIME_MAX] \
[--maxn=N] [--flag=HEADER | --noflag] [--verbosity=V]
  void-sniffer -v | --version
  void-sniffer -h | --help

Options:
  -i --tmin=TIME_MIN  Low time threshold
  -a --tmax=TIME_MAX  High time threshold
  -n --maxn=N         Stop after outputing N images
  -f --flag=HEADER    Name of the header to look for, [default: VISNJAN]
  -n --noflag         Skip header flag check
  -V --verbosity=V    Logging verbosity, 0 to 4 [default: 2]
  -h --help           Show this help screen
  -v --version        Show program name and version number
"""
# TODO versioning individual scripts?

import logging
import os
import sys

import docopt
from astropy.time import Time
from astropy.io import fits

import void.common as common

log = logging.getLogger(__name__)


class Sniffer:
    DISABLED_FLAG: str = '0'

    def __init__(
            self,
            search_dir: str,
            maxn: int,
            tmin: str,
            tmax: str,
            flag_name: str):
        self.search_dir = search_dir
        self.maxn = maxn
        self.tmin = tmin
        self.tmax = tmax
        if flag_name == self.DISABLED_FLAG:
            self.flag_name = None
        else:
            self.flag_name = flag_name
        self.count = 0

        self._filter_method = self._filter_always_true
        if self.tmin and self.tmax:
            self.time_first = self.parse_time(self.tmin)
            self.time_last = self.parse_time(self.tmax)
            self._filter_method = self._filter_within
        elif self.tmin:
            self.time_thresh = self.parse_time(self.tmin)
            self._filter_method = self._filter_after
        elif self.tmax:
            self.time_thresh = self.parse_time(self.tmax)
            self._filter_method = self._filter_before
        log.debug('init done')

    def check_flag(self, fits_fname):
        log.debug('checking flag %s', fits_fname)
        with fits.open(fits_fname) as hdul:
            header_dict = hdul[0].header
            if header_dict.get(self.flag_name, '').strip():
                log.debug('true: %s', fits_fname)
                return True
        log.debug('false: %s', fits_fname)
        return False

    def find_fits(self):
        for root, _, files in os.walk(self.search_dir):
            for file in files:
                abs_fname = os.path.normpath(os.path.join(root, file))
                if self.validate_file(abs_fname):
                    yield abs_fname

    @staticmethod
    def parse_time(time_str):
        if 'T' not in time_str:
            time_str += 'T00:00:00.00'
        return Time(time_str, format='fits')

    def get_fits_time(self, fits_fname):
        with fits.open(fits_fname) as hdul:
            time_str = hdul[0].header['DATE-OBS']
            return self.parse_time(time_str)

    def validate_file(self, fname):
        if not fname.endswith('.fits') and not fname.endswith('.fit'):
            return False
        if self.flag_name and not self.check_flag(fname):
            return False
        if not self.filter_fits(fname):
            return False
        if self.maxn is not None and self.count >= self.maxn:
            raise StopIteration
        self.count += 1
        # TODO self.flag_file(file)
        return True

    def filter_fits(self, fname_i):
        """
        Check if the string is a range or something else
        """
        time_fits = self.get_fits_time(fname_i)
        filter_value = self._filter_method(time_fits)
        log.debug(f'filter_value: {filter_value}')
        return filter_value

    def _filter_within(self, time_fits):
        log.debug('_filter_within %s', time_fits)
        return self.time_first < time_fits < self.time_last

    def _filter_before(self, time_fits):
        log.debug(f'_filter_before {time_fits}')
        return time_fits < self.time_thresh

    def _filter_after(self, time_fits):
        log.debug(f'_filter_after {time_fits}')
        return time_fits > self.time_thresh

    @staticmethod
    def _filter_always_true(time_fits):
        log.debug(f'_filter_always_true {time_fits}')
        return True



def main():
    name_and_version = __doc__.strip().splitlines()[0]
    arguments = docopt.docopt(__doc__, help=True, version=name_and_version)
    common._configure_log(arguments['--verbosity'])
    log.debug('initialising')
    sniffer = Sniffer(
        search_dir=arguments['SEARCH_DIR'],
        tmin=arguments['--tmin'],
        tmax=arguments['--tmax'],
        maxn=arguments['--maxn'],
        flag_name=arguments['--flag'],
    )
    for fname_i in sniffer.find_fits():
        sys.stdout.write(f'{fname_i}\n')


if __name__ == '__main__':
    main()
