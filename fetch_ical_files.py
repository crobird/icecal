#!/usr/bin/env python

import os
import re
import json
import urllib2
import caldav
import local_settings
from datetime import datetime

# Sample iCal link
# https://stats.sharksice.timetoscore.com/team-cal.php?team=323&tlev=0&tseq=0&season=40&format=iCal
ICAL_URL_TEMPLATE = "https://stats.sharksice.timetoscore.com/team-cal.php?{}&format=iCal"
CALDAV_URL = "http://{}:{}@{}/ical/".format(local_settings.user, local_settings.password, local_settings.hostname)

def is_valid_ical_event(event_lines):
    for l in event_lines:
        # Skip any event that's missing a start time
        if re.match(r'DTSTART:\s*$', l):
            return False
    return True

def cleanup_ical_data(ical_data, relcalid):
    # Save lines per event and only promote events when we know it's valid
    new_ical_lines = []
    event_lines = []
    in_event = False
    for line in ical_data.split("\n"):
        if re.match(r'^(LAST-MODIFIED|DTSTAMP):', line):
            # Have to work around some wonky issues with caldav rejecting these lines
            continue
        elif re.match(r'X-WR-RELCALID:', line):
            # Sharks Ice was using the same relcalid, so we replace it with our unique one
            line = re.sub(r'X-WR-RELCALID:\s*([\d\w\-]+)', 'X-WR-RELCALID: {}'.format(relcalid), line)
        elif line.startswith('END:VEVENT'):
            event_lines.append(line)
            if is_valid_ical_event(event_lines):
                new_ical_lines.extend(event_lines)
            event_lines = []
            in_event = False
            continue # Skip adding the current line anywhere, since we just took care of it
        elif line.startswith('BEGIN:VEVENT'):
            in_event = True
        if in_event:
            event_lines.append(line)
        else:
            new_ical_lines.append(line)
    return "\n".join(new_ical_lines)

def fetch_ical_file(team_data, skip_mods=False):
    url = ICAL_URL_TEMPLATE.format(team_data["url"])
    try:
        f = urllib2.urlopen(url)
        ical_data = f.read()
    except Exception, e:
        raise Exception("Trouble fetching {}: {}".format(url, e))
    if not skip_mods:
        ical_data = clean_up_ical_data(ical_data, team_data["relcalid"])
    return ical_data

def publish_ical_file(team_data, ical_data):
    if not ical_data:
        return
    try:
        client = caldav.DAVClient(CALDAV_URL)
        calendar = caldav.Calendar(client, CALDAV_URL).save()
        event = caldav.Event(client, url="{}{}".format(CALDAV_URL, team_data["filename"]), data=ical_data, parent=calendar).save()
    except Exception, e:
        raise Exception("Trouble publishing ics file '{}': {}".format(team_data["filename"], e))

def process_league(league, save_dir=None, publish=False, limit=None):
    count = 0
    for level in league:
        for team in league[level]:
            team_data = league[level][team]
            ical_data = fetch_ical_file(team_data)
            if save_dir is not None:
                ofile = open(os.path.join(save_dir, team_data["filename"]), "w")
                ofile.write(ical_data)
                ofile.close()
            if publish:
                publish_ical_file(team_data, ical_data)
            team_data["mtime"] = str(datetime.now())
            count += 1
            if limit is not None and count >= limit:
                return


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description="Fetch iCal files from Sharks Ice and publish them")
    parser.add_argument("--json", dest="json", help="JSON file with team info")
    parser.add_argument("--save_dir", dest="save_dir", help="Save iCal files")
    parser.add_argument("--publish", dest="publish", action="store_true", default=False, help="Publish iCal files")
    parser.add_argument("--limit", dest="limit", help="Limit to N teams to process", type=int)
    args = parser.parse_args()

    if args.json is None:
        parser.error("--json is required")

    if args.save_dir is not None and not os.path.exists(args.save_dir):
        # Yeah, kinda lazy to not just make it. TODO
        parser.error("Save directory '{}' doesn't exist. Gotta make it first, bro.".format(args.save_dir))

    infile = open(args.json, "r")
    json_data = infile.read()
    infile.close()

    league = json.loads(json_data)

    process_league(league, save_dir=args.save_dir, publish=args.publish, limit=args.limit)

    # Save league data back out, to include modified times
    try:
        out_json = json.dumps(league, sort_keys=True, indent=4, separators=(',', ': '))
    except Exception, e:
        raise Exception("Unable to dump out league json")
    else:
        outfile = open(args.json, "w")
        outfile.write(out_json)
        outfile.close()
