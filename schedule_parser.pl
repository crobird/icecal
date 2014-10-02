#!/usr/bin/perl

=head1 NAME 

schedule_parser.pl - Create JSON with team info from SIAHL site

=head1 SYNOPSIS

schedule_parser.pl [--html filepath] [--json filepath]

=head1 OPTIONS

=over 8 

=item B<--html>

Use this HTML file instead of pulling from the SIAHL site.

=item B<--json>

Specifies the output path for the JSON created.

=back

=cut

use strict;
use warnings;

use Getopt::Long;
use LWP::UserAgent;
use HTTP::Request;
use JSON;
use Pod::Usage qw(pod2usage);

my %opts;
GetOptions(\%opts,
    'help',
    'html=s',
    'json=s'
) || pod2usage(-verbose => 0);

pod2usage(-verbose => 1) if $opts{help};

my $html_file = $opts{html};
my $html = "";

$opts{json} ||= 'teams.json';

if  ($html_file){
    open(HTML, "< $html_file") || die;
    foreach (<HTML>){ $html .= $_; }
    close(HTML);
}
else{
    my $league_page = "http://stats.liahl.org/display-stats.php?league=1";

    my $ua = new LWP::UserAgent;

    my $req = HTTP::Request->new(GET => $league_page);

    # Pass request to the user agent and get a response back
    my $res = $ua->request($req);

    # Check the outcome of the response
    if ($res->is_success) {
        $html = $res->content;
    }
    else {
        print $res->status_line, "\n";
    }
}

my $teams = get_teams($html);
open(TEAMS, "> $opts{json}") || die "Can't open $opts{json}: $!";
print TEAMS encode_json($teams);
close(TEAMS);

# <TR bgcolor="#00515a"><th colspan=7><a name=93>Senior EEEE</a></th></tr>
# <TR bgcolor="#00515a"><th colspan=7><a href="display-league-stats.php?league=1&level=93&season=14&conf=0">Player Stats</a></th></tr>
# <TR bgcolor="#00515a"><th colspan=7><a href="display-playoff.php?level=93&league=1&season=14&conf=0">Playoff Tree</a></th></tr>
# <tr bgcolor="#00515a"><th>Team</th><th>GP</th><th>W</th><th>L</th><th>T</th><th>OTL</th><th>PTS</th></tr>
# <tr bgcolor="#b4b4b4">
# <td align=center><a href="display-schedule.php?team=298&season=14&tlev=0&tseq=0&league=1">Re-Habs </a></td><td align=center>6</td><td align=center>4</td><td align=center>1</td><td align=center>1</td><td align=center>0</td><td align=center>9</td></tr>
# <tr bgcolor="#e4e4e4">

# ical link for a team
# http://stats.liahl.org/team-cal.php?team=1789&tlev=0&tseq=0&season=17&format=iCal

sub get_teams{
    my @html = split /\n/, shift;
    my $level = "[undefined]";
    my $teams = {};
    foreach (@html){
        if (/name=(\d+)\>\s*Senior\s*([\w ]+)\</){
            $level = $2;     # $1 is the level ID, which we don't need since it's in the team URL already
            $teams->{$level} = {};
        } 
        elsif (/href="display\-schedule.php\?([^"]+)"\>([^<]+)\s*\</){
            my ($url,$name) = ($1,$2);
            $name =~ s/\s+$//;
            $teams->{$level}->{$name} = { url => $url, mtime => '' }; # Stores the URL with all of the team info in it
        }
    }
    return $teams;
}
