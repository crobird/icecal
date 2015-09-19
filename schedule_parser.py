#!/usr/bin/env python

import re
import uuid
import json
import urllib2
from bs4 import BeautifulSoup

# We want to fiter these tags for processing:
#
# Adult level names:
#   <a name="56">Senior A</a>
#
# JSHL level names:
#   <a href="display-schedule.php?league=2&amp;level=12&amp;season=30&amp;conf=2" name="12">Bantam IH Silver</a>
#
# Team pages:
#   <a href="display-schedule.php?team=1463&amp;season=30&amp;tlev=0&amp;tseq=0&amp;league=2">Ranger Blue </a>

def levels_and_teams(tag):
    if tag.name == "a":
        if "name" in tag.attrs:
            return True
        elif "href" in tag.attrs and re.match("display-schedule.php", tag.attrs["href"]):
            return True

def clean_id(bits):
    new_id = ".".join(bits)
    return re.sub(r'[^\w\.]+', '_', new_id)

def new_team_obj(league, level, team, href=None, relcalid=None):
    team_id = clean_id([league, level, team])
    new_team = {
        "mtime": "",
        "filename": "{}.ics".format(team_id),
    }
    new_team["relcalid"] = relcalid if relcalid else str(uuid.uuid5(uuid.NAMESPACE_DNS, str(team_id)))
    if href:
        new_team["url"] = href
    return new_team

class League(object):
    def __init__(self, name, url=None, level_transform=None):
        self.name = name
        self.url  = url
        self.html = None
        self.level_transform = level_transform

    def load(self, html_file=None):
        # TODO: Check for valid file
        infile = open(html_file, "r")
        self.html = infile.read()
        infile.close()

    def fetch(self):
        if self.url is None:
            return
        response = urllib2.urlopen(self.url)
        self.html = response.read()

    def fix_level(self, level_string):
        s = level_string if self.level_transform is None else re.sub(self.level_transform[0], self.level_transform[1], level_string)
        return str(s).rstrip()

    def fix_team(self, team_string):
        return str(team_string).rstrip()

    def fix_team_link(self, href):
        return re.sub(r'^display-schedule\.php\?', '', href)

    def parse(self, relcal_map=None):
        if self.html is None:
            return
        bs = BeautifulSoup(self.html)
        filter_tags = bs.findAll(levels_and_teams)
        levels = {}
        level = None
        for tag in filter_tags:
            # Order here is important since JSHL levels also have hrefs, but we want to match on name
            # {"CC":{"Blueline":{"mtime":"","url":"team=534&season=30&tlev=0&tseq=0&league=1"},
            if tag.text.strip().lower() == self.name.lower():
                # If the league name is a link, skip it
                continue
            if "name" in tag.attrs:
                level = self.fix_level(tag.text)
                if level in levels:
                    raise Exception("Level is defined twice, we got parser troubles, friend")
                levels[level] = {}
            elif "href" in tag.attrs:
                team = self.fix_team(tag.text)
                if level is None:
                    raise Exception("Got a team before a level, something is wrong")
                relcalid = None
                if relcal_map is not None:
                    if level in relcal_map and team in relcal_map[level] and \
                        "relcalid" in relcal_map[level][team]:
                        relcalid = relcal_map[level][team]["relcalid"]
                levels[level][team] = new_team_obj(self.name, level, team, 
                    href=self.fix_team_link(tag.attrs["href"]), relcalid=relcalid)

        return levels


LEAGUES = [
    League("siahl", "http://stats.liahl.org/display-stats.php?league=1", level_transform=[r"^Senior ", ""]),
    League('jshl', "http://stats.liahl.org/display-stats.php?league=2"),
    League("over35", "http://stats.liahl.org/display-schedule.php?league=4"),
]

LEAGUE_LOOKUP = { l.name: l for l in LEAGUES }


if __name__ == '__main__':


    import argparse

    parser = argparse.ArgumentParser(description="Parse SIAHL site for team list")
    parser.add_argument("--html", dest="html", help="HTML to parse")
    parser.add_argument("--league", dest="league", help="League to parse, one of: {}".format(LEAGUE_LOOKUP.keys()))
    parser.add_argument("--out", dest="outfile", help="Ouput filename")
    parser.add_argument("--relcal_json", dest="relcal", help="Existing JSON file to pull relcal IDs from")
    args = parser.parse_args()

    if args.league is None:
        parser.error("--league is required")
    elif args.league not in LEAGUE_LOOKUP:
        parser.error("league '{}' is invalid, should be one of {}".format(args.league, LEAGUE_LOOKUP.keys()))

    league = LEAGUE_LOOKUP[args.league]
    if args.html:
        league.load(args.html)
    else:
        league.fetch()

    parse_args = {}

    # If they gave us a file of existing relcal IDs, parse it and pass it along
    if args.relcal:
        rfile = open(args.relcal, "r")
        relcal_data = rfile.read()
        rfile.close()
        parse_args["relcal_map"] = json.loads(relcal_data)

    parsed_league = league.parse(**parse_args)

    json_txt = json.dumps(parsed_league,sort_keys=True, indent=4, separators=(',', ': '))

    if args.outfile:
        outfile = open(args.outfile, "w")
        outfile.write(json_txt)
        outfile.close()
    else:
        print json_txt
