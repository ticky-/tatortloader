#!/usr/bin/python
import sys, codecs, locale
import urlparse
from urllib import urlopen, urlretrieve
import json
import os
import signal
import time
import datetime

def sizeString(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def reporthook(count, block_size, total_size):
    actualSize = count * block_size
    percent = (actualSize * 100.0 / total_size)
    timeNow = time.time() 
    delta = int(timeNow - startTime)
    if percent > 0.1:
        timeLeft = ((timeNow - startTime) / percent) * (100 - percent)
        timeLeft = str(datetime.timedelta(seconds=int(timeLeft)))
        timeLeft = ':'.join(str(timeLeft).split(':')[:2])
    else:
        timeLeft = "-"
    delta = str(datetime.timedelta(seconds=delta))
    sys.stdout.write("\r%.2f%%  ----  %s / %s  ----  %s / time left: %s [h:min]      " % (percent, sizeString(actualSize), sizeString(total_size), delta, timeLeft))
    sys.stdout.flush()


def signal_handler(signal, frame):
    print "\n\n... goodbye!\n"
    sys.exit(0)

#catch Strg+C interrupt
signal.signal(signal.SIGINT, signal_handler)

#Wrap sysout so we don't run into problems when printing unicode characters to the console.
#This would otherwise be a problem when we are invoked on Debian using cron: 
#Console will have encoding NONE and fail to print some titles with umlauts etc
#might also fix printing on Windows consoles
#see https://wiki.python.org/moin/PrintFails
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout);

#get URL from user
print ""
print "tatortloader benoetigt die Adresse des unter www.ardmediathek.de eingestellten Tatorts." 
print "Ueber die Suchfunktion ist die Seite meist ab ca. 20:30-21:00 auffindbar - davor nur der Livestream."
print "(Download von www.daserste.de funktioniert mit diesem Skript nicht.)"
print "Die Videodatei wird in den Ordner dieses Skipts gespeichert..."
print ""
url = raw_input('Bitte URL hier einfuegen: ')
print ""

#see, if its working
parsed = urlparse.urlparse(url)
try:
    docId = urlparse.parse_qs(parsed.query)['documentId']
except KeyError as e:
    print "Couldn't get any documentId from the given URL: " + url
    print "Please check the URL and try again...\n"
    sys.exit(0)

docUrl = 'http://www.ardmediathek.de/play/media/' + docId[0] + '?devicetype=pc&features=flash'

response = urlopen(docUrl)
html = response.read()

if 'http://www.ardmediathek.de/-/stoerung' == response.geturl():
    print "Could not get the movie in '" + url + "'. Got redirected to '" + response.geturl() + "'.'\n"
    sys.exit(0)

try:
    media = json.loads(html)
except ValueError as e:
    print e
    print "Could not download '" + "'. Original item link is '" + link + "' and parsed docId[0] is '" + docId[0] + "', but html response from '" + docUrl + "' was '" + html + "'\n"
    sys.exit(0)

if '_mediaArray' not in media or len(media["_mediaArray"]) == 0:
    print "Sorry -  no mediafiles could be found under the given url - please check and try again.\n"
    sys.exit(0)


#everything seems ok... so check size of file in different qualities

mediaLinks = media["_mediaArray"][1]["_mediaStreamArray"]
print "\nfine... let's see what you could get:\n"
count = 0  
for mediaLink in mediaLinks:
    f = urlopen(mediaLink["_stream"])
    print "Quality %d would be %s \n" % (count, sizeString(int(f.headers["Content-Length"])))
    count += 1
quality = raw_input('\nWhich quality do you want [Enter = 2]: ')

try:
    quality = int(quality)
    if quality not in [0, 1, 2, 3]:
        raise ValueError
except ValueError:
    print "___ just taking quality = 2\n"
    quality = 2

print ""

for mediaLink in mediaLinks:
    if quality == mediaLink["_quality"]:
        mediaURL = mediaLink["_stream"]
        fileName = url
        for s in ['/Tatort', '.de', '/tv', 'ard', 'media', 'thek', 'www', 'http', 'documentId', 'Das-Erste', 'Video', 'bcastId']:
            fileName = fileName.replace(s, "") 
        fileName = "".join([x if x.isalpha() or x in "-" else "" for x in fileName])
        fullPath = os.path.dirname(os.path.abspath(__file__)) + "/Tatort__" + fileName + ".mp4"
        print "Downloading to: " + fullPath + "\n"
        startTime = time.time()
        urlretrieve(mediaURL, fullPath, reporthook)
        print "\n...ready!\n"
