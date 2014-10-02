#!/usr/bin/perl

use strict;
use warnings;

use lib './lib';

use JSON;
use Getopt::Long;
use Pod::Usage qw(pod2usage);
use Data::Dumper;
use LWP::UserAgent;
use HTTP::Request;
use UUID::Tiny;

my $CAL_URL     = 'http://stats.liahl.org/team-cal.php?';
my $PUBLISH_CMD = './publish_ics.py';
my $SAVE_DIR    = './icsdata';

my %opts;
GetOptions(\%opts,
  'json=s',
  'save', 
  'publish',
  'verbose' 
);

pod2usage('Missing required param --json') unless $opts{json};
pod2usage('One of --save or --publish required') unless defined $opts{publish} || defined $opts{save};

mkdir $SAVE_DIR unless -e $SAVE_DIR;

open(JSON, "< $opts{json}") || die "Can't open $opts{json}: $!";
my $json = <JSON>;
close(JSON);

my $teams = from_json($json);

while (my ($level, $lteams) = each %{$teams}){
    print "Looking at level $level\n" if $opts{verbose};
    while (my ($tname, $tinfo) = each %{$lteams}){
        print "\tLooking at $tname\n" if $opts{verbose};
        my $file = fetch_file($CAL_URL . $tinfo->{url} . '&format=iCal');
        next unless $file;
        
        # Change X-WR-RELCALID to be unique (create if needed)
        unless (defined $tinfo->{relcalid}){
            $tinfo->{relcalid} = get_new_relcalid($tname);
        }
        $file =~ s/X-WR-RELCALID:\s*([\d\w\-]+)/X-WR-RELCALID: $tinfo->{relcalid}/;
        
        my $filename = get_filename($level . '_' . $tname);
        my $outpath = $SAVE_DIR . '/' . $filename;
        open(OUT, ">$outpath") || die "Can't open $outpath: $!";
        print OUT $file;
        close(OUT);
        if ($opts{publish}){
            `$PUBLISH_CMD --file $outpath --name $filename`;
        }
        unlink $outpath unless $opts{save};
        $tinfo->{mtime}    = localtime;
        $tinfo->{filename} = $filename;       
    }
}

open(JSON, "> $opts{json}") || die "Can't open $opts{json} for writing: $!";
print JSON to_json($teams);
close(JSON);

sub get_new_relcalid{
    my $s = shift;
    return create_UUID_as_string(UUID_V5, $s);
}

sub get_filename{
    my $n = shift;
    $n =~ s/[\W]/_/g;
    $n .= '.ics';
    return $n;
}

sub fetch_file{
    my $url = shift;

    my $ua = new LWP::UserAgent;
    my $req = HTTP::Request->new(GET => $url);

    # Pass request to the user agent and get a response back
    my $res = $ua->request($req);

    # Check the outcome of the response
    if ($res->is_success) {
        return $res->content;
    }
    else {
        return undef;
    }
}
