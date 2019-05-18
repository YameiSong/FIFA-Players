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
root_url = 'https://sofifa.com'

# find out disallowed links for all user-agents
fhandle = open('robots.json')
js = json.load(fhandle)
for agent in js:
    if agent['User-agent'] == '*':
        disallowedLinks += agent['Disallow']

# open sqlite
conn = sqlite3.connect('./dataset/playerlinks.sqlite')
cur = conn.cursor()
try:
    cur.execute('SELECT age FROM PlayerLinks')
except:
    cur.executescript('''
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS age INTEGER;
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS overall_rating INTEGER;
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS potential INTEGER;
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS value TEXT;
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS wage TEXT;
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS club TEXT;
    ALTER TABLE PlayerLinks ADD COLUMN IF NOT EXISTS country TEXT;
    ''')


def LookForPlayerInfo(myUrl, myId):
    # specify user-agent to adress this error:
    # urllib.error.HTTPError: HTTP Error 403: Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Mobile Safari/537.36'}
    req = urllib.request.Request(url=myUrl, headers=headers)
    html_doc = urllib.request.urlopen(req)
    soup = BeautifulSoup(html_doc, 'html.parser')

    # find out player's age, overall rating, potential, value, wage, club, country
    foundAge = False
    foundOverallRating = False
    foundPotential = False
    foundValue = False
    foundWage = False
    foundClub = False
    foundcountry = False
    
    divTags = soup.find_all('div', class_='top-gap block')
    children = divTags[0].find_all('div')
    club = divTags[1].find_all('a')[0].contents[0]
    foundClub = True
    try:
        country = divTags[2].find_all('a')[0].contents[0]
        foundcountry = True
    except:
        print('No country information about this player')

    divChildren1 = children[0].contents
    for i, child in enumerate(divChildren1):

        if hasattr(child, 'contents') and len(child.contents) > 0:
            if foundOverallRating is False and child.contents[0] == 'Overall Rating':
                overallRate = divChildren1[i+1].contents[0]
                foundOverallRating = True

            if foundPotential is False and child.contents[0] == 'Potential':
                potential = divChildren1[i+1].contents[0]
                foundOverallRating = True

    divChildren2 = children[1].contents
    for i, child in enumerate(divChildren2):

        if foundAge is False and isinstance(child, str):
            ageList = re.findall(r'([0-9]+)y.o.', child)
            if len(ageList) > 0:
                age = ageList[0]
                foundAge = True

        if hasattr(child, 'contents') and len(child.contents) > 0:
            if foundValue is False and child.contents[0] == 'Value':
                value = divChildren2[i+1]
                foundValue = True

            if foundWage is False and child.contents[0] == 'Wage':
                wage = divChildren2[i+1]
                foundWage = True

    # add info to database
    try:
        cur.execute('''UPDATE PlayerLinks 
                   SET age = ?, overall_rating = ?, potential = ?, value = ?, wage = ?, club = ?
                   WHERE id = ?''', (age, overallRate, potential, value, wage, club, myId))
    except:
        print('Some attribute may have not found yet.')

    if foundcountry is True:
        cur.execute('UPDATE PlayerLinks SET country = ? WHERE id = ?', (country, myId))

# find out the total number of players
cur.execute('SELECT max(id) FROM PlayerLinks')
row = cur.fetchone()
total = int(row[0])

while count < total:
    try:
        # Pick up where we left off
        cur.execute(
            'SELECT max(id), url FROM PlayerLinks WHERE age IS NOT NULL')
        try:
            row = cur.fetchone()
            # Next one's age should be NULL
            thisId = int(row[0])+1
        except:
            thisId = 1
            print('Start from the first')

        while True:
            try:
                cur.execute('SELECT url FROM PlayerLinks WHERE id = ?', (thisId, ))
                row = cur.fetchone()
                print(thisId, ': Retrieving', row[0], '...')
                if thisId > 1:
                    if row[0] in disallowedLinks:
                        print('Error: this url is not allowed to visit')
                        exit()
                break
            except:
                # some id doesn't exist, add 1 to skip
                thisId += 1
        
        thisUrl = root_url + row[0]
        LookForPlayerInfo(thisUrl, thisId)
        count += 1
        if count % 5 == 0:
            conn.commit()
    except KeyboardInterrupt:
        print('Program interrupted by user...')
        break

conn.commit()
conn.close()
