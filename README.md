icecal
======

CalDAV hosting of SIAHL calendars



New season steps:
	- Reload team associations:
		./schedule_parser.pl --json teams.json
		cp teams.json ../$SITE/icecal/teams.json 

Then run the crontab cmd to make an immediate push:
	./fetch_ical_files.pl --json /home/$USER/$SITE/icecal/teams.json --publish
