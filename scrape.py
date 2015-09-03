#!/usr/bin/env python
#
# SCRAPE EM
#

import sys
from optparse import OptionParser
import urllib2

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
