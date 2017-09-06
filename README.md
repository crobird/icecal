icecal
======

CalDAV hosting of SIAHL calendars

New season steps:
	- Reload team associations:
		python schedule_parser.py --league siahl --out siahl.txt
		cp siahl.txt ../haikudog.com/icecal/

Then run the crontab cmd to make an immediate push:
	./cron.sh
