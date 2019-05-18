import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
import json
import sqlite3

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

count = 0
disallowedLinks = list()
root_url = 'https://sofifa.com/players'

# find out disallowed links for all user-agents
fhandle = open('robots.json')
js = json.load(fhandle)
for agent in js:
    if agent['User-agent'] == '*':
        disallowedLinks += agent['Disallow']

# open sqlite
conn = sqlite3.connect('./dataset/playerlinks.sqlite')
cur = conn.cursor()
cur.executescript('''
CREATE TABLE IF NOT EXISTS PlayerLinks(
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name    TEXT UNIQUE,
    url TEXT
);

CREATE TABLE IF NOT EXISTS NextLinks(
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    url TEXT
)
''')

# web crawling and put data into sqlite
def AddPlayerLinksToDict(thisUrl):
    # specify user-agent to adress this error:
    # urllib.error.HTTPError: HTTP Error 403: Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Mobile Safari/537.36'}
    req = urllib.request.Request(url=thisUrl, headers=headers)
    html_doc = urllib.request.urlopen(req)

    soup = BeautifulSoup(html_doc, 'html.parser')

    # find out players' own page
    divTags = soup.find_all('div', id=re.compile('^player-'))
    for tag in divTags:
        aTags = tag.find_all('a')
        playerName = aTags[0].text.strip()
        playerLink = aTags[0].get('href', None)
        cur.execute(
            'INSERT OR IGNORE INTO PlayerLinks (name, url) VALUES (?, ?)', (playerName, playerLink))

    # find out link of Next page
    # max: https://sofifa.com/players?offset=18120
    # offset is added by 60
    nextTag = soup.find_all('a', text='Next')
    if len(nextTag) != 0:
        nextLink = nextTag[0].get('href', None)
        cur.execute(
            'INSERT OR IGNORE INTO NextLinks (url) VALUES (?)', (nextLink, ))
    else:
        nextLink = None

while(True):
    try:
        # Pick up where we left off
        cur.execute('SELECT max(id), url FROM NextLinks')
        try:
            row = cur.fetchone()
            if row[1] == 'javascript:void(0);':
                print('Done! All players are retrieved.')
                break
            else:
                nextUrl = 'https://sofifa.com' + row[1]
        except:
            nextUrl = root_url
            print('Start from root')

        if row[1] in disallowedLinks:
            print('Error: this url is not allowed to visit')
            exit()
        else:
            print('Retrieving', row[1], '...')
            AddPlayerLinksToDict(nextUrl)
            count += 1
            if count % 2 == 0:
                conn.commit()
    except KeyboardInterrupt:
        print('Program interrupted by user...')
        break

conn.commit()
conn.close()
