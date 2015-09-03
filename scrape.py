#!/usr/bin/env python
#
# SCRAPE EM
#

import sys
from optparse import OptionParser
import urllib2
import itertools
import time
import random
import os

from bs4 import BeautifulSoup

mainurl = 'http://dating.famousfix.com/?tab=&pageno=%d'

def getcelebs(pageindex):
    """yield celebrity name, celeb profile image url, and their profile URL
    as a tuple for all celebrities on `pageindex`."""
    soup = BeautifulSoup(urllib2.urlopen(mainurl % pageindex), 'html.parser')
    for celebli in soup.find(id='container').find_all('li'):
        name = celebli.a['title']
        imgurl = celebli.a.img['src']
        profileurl = celebli.div.a['href']
        yield name, imgurl, profileurl

def _extractdatees(celeblis):
    for celebli in celeblis:
        datee_profileurl = celebli.a['href']
        rumorp = len(celebli.find_all('span')) == 2
        relationshiptype = celebli.find_all('img')[2]['src'].split('/')[-1].split('.')[0].lower()
        relationshipurl = celebli.find_all('a')[-1]['href']
        datee_name = celebli.img['alt']

        yield {'datee_name': datee_name,
               'datee_profileurl': datee_profileurl,
               'rumorp': rumorp,
               'relationshiptype': relationshiptype,
               'relationshipurl': relationshipurl,
               }

def parserelationship(relationshipurl):
    soup = BeautifulSoup(urllib2.urlopen(relationshipurl), 'html.parser')
    return dict(zip([x.text.lower() for x in soup.find_all(class_='w33pc posl')], [x.text.lower() for x in soup.find_all(class_='w60pc posr')]))

def parseceleb(profileurl):
    """extract a dictionary of celebrity dating properties given their profile"""
    soup = BeautifulSoup(urllib2.urlopen(profileurl), 'html.parser')
    numcomments, numlikes = [int(x.text.split(' ')[0].replace(',', '')) for x in
                             soup.find(class_='statsbox').find_all('a')[:2]]
    starsign = soup.find(class_='posr italic').a['title'].lower()
    celeblis = soup.find(class_='datingb').find_all('li')
    datees = list(_extractdatees(celeblis))
    relationshipdeets = [parserelationship(x['relationshipurl']) for x in datees]
    assert(len(datees) == len(relationshipdeets))

    return {'numcomments': numcomments,
            'numlikes': numlikes,
            'starsign': starsign,
            'numdatees': len(celeblis),
            'datees': datees,
            'relationshipdeets': relationshipdeets,
            }

def _parse_numbars(s):
    if '-' in s:
        x, y = map(int, s.split('-'))
        return range(x, y + 1)
    else:
        return [int(s)]

def dbpoop(celeb):
    pass

def saveimage(celeb):
    pass

def main():
    """main function for standalone usage"""
    usage = "usage: %prog [options] 1,2,4-7,9"
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', action='store_true', default=False)
    parser.add_option('-i', '--img-dir', default='profiles', help='[default: %default]')
    parser.add_option('-s', '--skip-n-celebs', default=0, type='int')

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        return 2

    try:
        os.mkdir(options.img_dir)
    except OSError:
        pass

    # do stuff
    celebnum = 0
    for pageindex in itertools.chain(*map(_parse_numbars, args[0].split(','))):

        if options.verbose:
            print('Page #%d' % pageindex)
        for celebname, imgurl, profileurl in getcelebs(pageindex):

            celebnum += 1
            if options.skip_n_celebs > 0:
                options.skip_n_celebs -= 1
                continue

            if options.verbose:
                print('== %s ==' % celebname)
                print('celeb #%d' % celebnum)

            celeb = parseceleb(profileurl)
            celeb['name'] = celebname
            celeb['profileimgpath'] = os.path.join(options.img_dir, '%s.jpg' %
                                                   celebname.lower().replace(' ', ''))
            if options.verbose:
                print('%d datees' % celeb['numdatees'])

            dbpoop(celeb)
            saveimage(celeb)

            time.sleep(random.randint(0, 7))

if __name__ == '__main__':
    sys.exit(main())
