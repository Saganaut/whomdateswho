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
import sqlite3

from bs4 import BeautifulSoup
from dateutil.parser import parse as dateparse

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

def int_or_0(s):
    try:
        return int(s)
    except ValueError:
        return 0

def parseceleb(profileurl):
    """extract a dictionary of celebrity dating properties given their profile"""
    soup = BeautifulSoup(urllib2.urlopen(profileurl), 'html.parser')
    try:
        numcomments, numlikes = [int_or_0(x.text.split(' ')[0].replace(',', '')) for x in
                                 soup.find(class_='statsbox').find_all('a')[:2]]
    except ValueError:
        numcomments, numlikes = 0, 0
    try:
        starsign = soup.find(class_='posr italic').a['title'].lower()
    except AttributeError:
        starsign = None
    celeblis = soup.find(class_='datingb').find_all('li')
    datees = list(_extractdatees(celeblis))
    relationshipdeets = [parserelationship(x['relationshipurl']) for x in datees]
    try:
        imgurl = soup.find(class_='cbox-nav2 banr').img['src']
    except AttributeError:
        imgurl = soup.find(class_='cbox-tmenu').img['src']
    assert(len(datees) == len(relationshipdeets))

    return {'numcomments': numcomments,
            'numlikes': numlikes,
            'starsign': starsign,
            'numdatees': len(celeblis),
            'datees': datees,
            'relationshipdeets': relationshipdeets,
            'profileurl': profileurl,
            'imgurl': imgurl,
            }

def _parse_numbars(s):
    if '-' in s:
        x, y = map(int, s.split('-'))
        return range(x, y + 1)
    else:
        return [int(s)]

def _init_tables(database):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS celebs (name text PRIMARY KEY, starsign text, numdatees integer, numlikes integer, numcomments integer, profileurl text)')
    cur.execute('CREATE TABLE IF NOT EXISTS relationships (name1 text, name2 text, type text, rumor integer, status text, startyear integer, endyear integer, PRIMARY KEY(name1, name2))')
    conn.commit()
    cur.close()

def add_or_update_celeb(celeb, database):
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()

        cur.execute('SELECT * FROM celebs WHERE name = ?', (celeb['name'], ))
        row = cur.fetchone()
        if not row:
            # a celeb being inserted with knowledge only from the relationship
            # will only have 2 entries: name/profileurl (for later parsing)
            if len(celeb) > 2:
                cur.execute('INSERT INTO celebs VALUES (?, ?, ?, ?, ?, ?)',
                            (celeb['name'], celeb['starsign'], celeb['numdatees'], celeb['numlikes'], celeb['numcomments'], celeb['profileurl']))
            else:
                cur.execute('INSERT INTO celebs VALUES (?, ?, ?, ?, ?, ?)',
                            (celeb['name'], None, None, None, None, celeb['profileurl']))
        else:
            if len(celeb) > 2:
                cur.execute('UPDATE celebs SET starsign = ?, numdatees = ?, numlikes = ?, numcomments = ? WHERE name = ?', (celeb['starsign'], celeb['numdatees'], celeb['numlikes'], celeb['numcomments'], celeb['name']))

        conn.commit()
        cur.close()
    except Exception as e:
        sys.stderr.write('Error add/update celeb "%s": %s\n' % (celeb['name'], str(e)))

def parseyears(relationship):
    try:
        startyear = int(relationship['commenced dating'])
        endyear = int(relationship['separated'])
    except ValueError:
        startyear = dateparse(relationship['commenced dating']).year
        endyear = dateparse(relationship['separated']).year
    except KeyError:
        startyear = None
        endyear = None
    finally:
        try:
            return startyear, endyear
        except UnboundLocalError:
            return startyear, None

def add_relationship(relationship, celeb, datee, database):
    startyear, endyear = parseyears(relationship)
    # this is to ensure we don't have duplicate relationships
    # where name1/name2 are just switched.
    name1, name2 = sorted([celeb['name'], datee['datee_name']])
    try:
        conn = sqlite3.connect(database)
        cur = conn.cursor()

        cur.execute('INSERT INTO relationships VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (name1, name2, relationship['relationship type'], datee['rumorp'],
                     relationship.get('relationship status', None), startyear, endyear))

        conn.commit()
        cur.close()
    except Exception as e:
        sys.stderr.write('Error adding relationship %s-%s: %s\n' % (name1, name2, str(e)))

def dbpoop(celeb, database):
    add_or_update_celeb(celeb, database)
    for datee, relationship in zip(celeb['datees'], celeb['relationshipdeets']):
        add_or_update_celeb({'name': datee['datee_name'], 'profileurl': datee['datee_profileurl']},
                            database)
        add_relationship(relationship, celeb, datee, database)

def add_remaining_celebs(database, verbose=False, img_dir='profiles'):
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    # get all incomplete profiles
    cur.execute('SELECT name, profileurl FROM celebs WHERE starsign is NULL')
    for celebname, profileurl in cur.fetchall():
        if verbose:
            print('== %s ==' % celebname)

        celeb = parseceleb(profileurl)
        celeb['name'] = celebname
        celeb['profileimgpath'] = os.path.join(img_dir, '%s.jpg' %
                                               celebname.lower().replace(' ', ''))

        if verbose:
            print('%d datees' % celeb['numdatees'])

        dbpoop(celeb, database)
        saveimage(celeb)

        time.sleep(random.randint(0, 7))
    cur.close()

def saveimage(celeb):
    if not os.path.exists(celeb['profileimgpath']):
        with open(celeb['profileimgpath'], 'wb') as f:
            img = urllib2.urlopen(celeb['imgurl'])
            f.write(img.read())

def main():
    """main function for standalone usage"""
    usage = "usage: %prog [options] 1,2,4-7,9"
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', action='store_true', default=False)
    parser.add_option('-i', '--img-dir', default='profiles', help='[default: %default]')
    parser.add_option('-s', '--skip-n-celebs', default=0, type='int')
    parser.add_option('-d', '--database', default='celebs.db',
                      help='Database to use [default: %default]')
    parser.add_option('-r', '--remaining-celebs', default=False, action='store_true',
                      help='Just crawl/add remaining, incomplete celebrities')

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        return 2

    try:
        os.mkdir(options.img_dir)
    except OSError:
        pass

    if options.remaining_celebs:
        add_remaining_celebs(options.database, options.verbose, options.img_dir)
        sys.exit(0)

    # do stuff
    celebnum = 0
    _init_tables(options.database)
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

            dbpoop(celeb, options.database)
            saveimage(celeb)

            time.sleep(random.randint(0, 7))

        # add incomplete celebs
        add_remaining_celebs(options.database, options.verbose, options.img_dir)

if __name__ == '__main__':
    sys.exit(main())
