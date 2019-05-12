import re
import json

ifhandle = open('robots.txt')
ofhandle = open('robots.json', 'w')

robots = list()
found_new_agent = False

for line in ifhandle:
    line = line.rstrip()
    agent = re.findall('^User-agent: (.+)', line)
    if len(agent) != 0:
        if found_new_agent is True:
            robots.append(agent_dict)
        agent_dict = dict()
        agent_dict['User-agent'] = agent[0]
        found_new_agent = True
    disallow = re.findall('^Disallow: (.*)', line)
    if len(disallow) != 0:
        if 'Disallow' not in agent_dict:
            agent_dict['Disallow'] = list()
        agent_dict['Disallow'].append(disallow[0])
    allow = re.findall('^Allow: (.*)', line)
    if len(allow) != 0:
        if 'Allow' not in agent_dict:
            agent_dict['Allow'] = list()
        agent_dict['Allow'].append(allow[0])
robots.append(agent_dict)

json.dump(robots, ofhandle, indent=4)
