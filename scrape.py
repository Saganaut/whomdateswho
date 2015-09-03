#!/usr/bin/env python
#
# SCRAPE EM
#

import sys
from optparse import OptionParser

from bs4 import BeautifulSoup

mainurl = 'http://dating.famousfix.com/?tab=&pageno=%d'

def getcelebs(pageindex):
    soup = BeautifulSoup(urllib2.urlopen(mainurl % pageindex), 'html.parser')
    for celebli in soup.find(id='container').find_all('li'):
        name = celebli.a['title']
        imgurl = celebli.a.img['src']
        profileurl = celebli.div.a['href']
        yield name, imgurl, profileurl

def main():
    """main function for standalone usage"""
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    (options, args) = parser.parse_args()

    if len(args) != 0:
        parser.print_help()
        return 2

    # do stuff
    pass

if __name__ == '__main__':
    sys.exit(main())
