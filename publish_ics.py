#!/usr/bin/python

from datetime import datetime
import caldav
from caldav.elements import dav, cdav
from optparse import OptionParser
import re

usage  = "usage: %prog [options]"
parser = OptionParser(usage=usage)
parser.add_option('-f', '--file', dest='file', help='ICS file to upload')
parser.add_option('-n', '--name', dest='name', help='Name for calendar file')
(options,args) = parser.parse_args()

if not options.file:
    parser.error("Missing required param --file")
    
if not options.name:
    options.name = options.file

# Principal url
url = "http://beejay:vomit@haikudog.com/ical/"

# Read in ICAL data from the provided file
ics_file = open(options.file, "r")
ics_data = ''
for line in ics_file:
    # Have to work around some wonky issues with caldav rejecting these lines
    if re.match(r'^(LAST-MODIFIED|DTSTAMP):', line):
        continue
    ics_data += line
ics_file.close()

client = caldav.DAVClient(url)
# principal = caldav.Principal(client, url)
# calendars = principal.calendars()
calendar = caldav.Calendar(client, url).save()
event = caldav.Event(client, url=url+options.name, data=ics_data, parent=calendar).save()