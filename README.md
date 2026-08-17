# WiGLE CSV Processor

OPSEC and analysis tool for WiGLE CSV files.

Your drive starts and ends at your house, and every AP heard while you were parked is in the
file. The densest, most-repeated cluster is where you sleep. This strips that out, then shows
you what else the drive picked up.

Python 3.10+, standard library only.

```bash
git clone https://github.com/lukeswitz/wigle-processor.git
cd wigle-processor
python3 wigle_processor.py
```

## Get started

Export the CSV out of the WiGLE app, drop it in a folder, and run the tool there. It finds the
CSVs on its own and asks what to keep private.

```
CSV files in this folder:
  sample_day1.csv
  sample_day2.csv
Use these? Press Enter for yes, or type a filename or pattern like *.csv:

Loading 2 file(s): sample_day1.csv, sample_day2.csv
Loaded 20 records.

Set up what to keep private now? (recommended before sharing) (Y/n):
Your home latitude (blank to skip):
Your home longitude (blank to skip):
Hide everything within how many meters (default 150)?
MAC addresses of your own devices, comma-separated (blank to skip):
Names (SSIDs) of your own networks, comma-separated (blank to skip):
Saved filter.json.

Results: kept 18 of 20 records, removed 2.
        1  matched a blocked SSID
        1  near your home location
Everything below runs on what's left.
```

Answered once, saved to `filter.json`, reused every run after. The radius is a circle measured
from your coordinates, and it deletes every network inside it — not only your own APs, because
leaving the neighbors in still marks the spot.

Your phone, watch, headunit and tags ride along and appear at every stop, which is a movement
trace of you. Option 2 finds them, and their MACs belong in `blocked_macs`.

Then pick from the menu. Each option is walked through below, using the two synthetic files
`make_sample.py` generates.

## 1 — Clean this drive for sharing

```
Save cleaned copies where (default cleaned):
Cleaned sample_day1.csv -> cleaned/sample_day1.csv (10/12 kept)
Cleaned sample_day2.csv -> cleaned/sample_day2.csv (8/8 kept)
Upload the files in that folder, not your originals.
```

Same WiGLE format and headers, minus what you blocked. Your originals are never written to.
This is the one that matters — do it before anything leaves your machine.

## 2 — Who followed me?

One MAC seen at several separate places.

```
Minimum unique locations (default 3):

Locations    Sightings    Vendor                 MAC Address
----------------------------------------------------------------------
6            6            Ubiquiti Inc           DC:9F:DB:DE:AD:99
  0.021900, -0.000200 — ''
  0.031900, -0.010200 — ''
  0.041900, -0.020200 — ''
```

Usually your own gear or a fleet AP on a delivery van. Occasionally something worth a second
look. Block whatever turns out to be yours and run it again.

## 3 — Encryption breakdown

```
Encryption                 Pct     Count / Total
-------------------------------------------------------
[WPA2-PSK-CCMP][ESS]    42.86%        6/14
[OPEN]                  14.29%        2/14
[WPA-PSK-TKIP][ESS]      7.14%        1/14
[WPA3-SAE-CCMP][ESS]     7.14%        1/14
[WEP]                    7.14%        1/14

  Open networks: 4
```

WEP and TKIP still turn up. Counted per unique network, not per sighting.

## 4 — Channel usage

```
Channel    Band             Pct     Count / Total
-------------------------------------------------------
6          2.4 GHz       21.43%        3/14
149        5 GHz         14.29%        2/14
11         2.4 GHz       14.29%        2/14

  Band summary:
    2.4 GHz: 8
    5 GHz: 5
    BLE: 1
```

## 5 — Evil twins / rogue APs

One SSID coming from an open clone of a secured network, or from two different hardware
vendors. Normal dual-band and mesh setups are not flagged.

```
Potential evil twin / rogue AP findings: 1
----------------------------------------------------------------------
  SSID: 'CoffeeShop'
    MACs (3): 24:A4:3C:00:00:10, 94:EB:2C:00:00:11, FF:FF:FF:00:00:16
    Vendors: Google, Inc., Ubiquiti Inc
    Auth modes: [OPEN], [WPA2-EAP-CCMP][ESS], [WPA2-PSK-CCMP][ESS]
    Channels: 11, 149, 6
    Flags: open clone of a secured network; different hardware vendors
```

## 6 — Device makers

MAC prefix against a bundled IEEE table. Shows camera, IoT and infrastructure density along
the route.

```
Vendor                               Pct   Count
-------------------------------------------------------
NETGEAR                           21.43%   3
Ubiquiti Inc                      14.29%   2
Apple, Inc.                        7.14%   1
Belkin International Inc.          7.14%   1
```

## 7 — Busiest times

```
  Total timestamped records: 20
  Peak activity hour: 09:00 (11 networks)
  Most active date:   2026-05-16 (13 networks)

  Hourly distribution:
    08:00  ██ 2
    09:00  ███████████ 11
    10:00  ███████ 7
```

This is a histogram of when you were driving, not when the networks were up.

## 8 — Merge several drives into one

```
Output file (default merged.csv): Merged/deduped: 17 unique -> merged.csv (1 duplicates removed)
```

A duplicate is the same MAC, SSID and position on more than one run.

## 9 — Export a map

```
Format — (k)ml for Google Earth / (g)eojson for QGIS:
Output file (default map.kml): KML export: map.kml (17 geolocated records)
```

Records with no GPS fix are skipped.

## filter.json

First launch writes it. To start from a template instead:

```bash
python3 wigle_processor.py --create-config filter.json
```

```json
{
  "latitude": 0.0,
  "longitude": 0.0,
  "radius_m": 400,
  "blocked_macs": ["AA:BB:CC:DD:EE:FF"],
  "blocked_ssids": ["myssid"],
  "blocked_patterns": ["MyCompany.*"]
}
```

MACs and SSIDs match exactly, patterns are regexes tested against both. If home removal
matches nothing the tool says so — that is almost always a missing minus sign on longitude.

## Skipping the menu

Everything the menu does has a flag, and flags combine into one pass.

```bash
# clean for upload
python3 wigle_processor.py *.csv --scrub

# home coordinates without a config file
python3 wigle_processor.py *.csv --scrub --lat 40.7128 --lon -74.0060

# every analysis at once
python3 wigle_processor.py *.csv --creeps --evil-twins --encryption --channels --vendor-stats --time-analysis

# merge two drives and map the result
python3 wigle_processor.py day1.csv day2.csv --merge all.csv --export-kml map.kml

# open networks and hardware makers, longer tables
python3 wigle_processor.py *.csv --encryption --vendor-stats --top 40

# something that shadowed you at only two stops
python3 wigle_processor.py *.csv --creeps --min-locs 2

# a month of drives into one uploadable file
python3 wigle_processor.py 2026-0*.csv --scrub --merge month.csv
```

| Flag | |
|---|---|
| `--scrub` | Cleaned copies into `cleaned/`. |
| `--keep-home` | Leave the home radius in. Off by default, and the tool warns you when you use it. |
| `--lat`, `--lon` | Home coordinates, overriding the config. |
| `--config FILE` | Default `filter.json`. |
| `--create-config FILE` | Write a template and exit. |
| `--output-dir DIR` | Default `cleaned`. |
| `--creeps` `--evil-twins` `--encryption` `--channels` `--vendor-stats` `--time-analysis` | Menu options 2 through 7. |
| `--min-locs N` | Locations before a device counts as a creep. Default 3. |
| `--merge FILE` | Merge and deduplicate. |
| `--export-kml FILE` `--export-geojson FILE` | Map export. |
| `--top N` | Row limit for creeps, channels and vendors. Default 20. |
| `-i` | Force the menu. |

`WIGLE_OUI_FILE=/path/to/oui.txt` replaces the bundled vendor table.

## Limitations

- **Only the circle comes out.** The road you took to get there is still in the file and it
  points at your door. Set the radius generously.
- **Records with no GPS fix survive the home filter.** They have no position to test, so they
  reach `cleaned/`. Map exports drop them.
- **Blocked SSIDs are case-sensitive.** `MyWiFi` does not block `mywifi`. MACs are matched
  either way. Use `blocked_patterns` when unsure.
- **Creep locations are roughly 1 km grid cells**, not points. Two sightings 500 m apart
  usually count as one, which is what keeps a stationary AP off the list.
- **Hidden and blank SSIDs are invisible to evil-twin detection**, which groups by name.
- **Randomized MACs defeat vendor lookup and creep tracking.** Modern phones rotate their
  address, come back `Unknown`, and never accumulate locations.
- **Deduplication needs an exact position match.** The same AP logged a metre apart on two
  passes stays two records.
- **Two timestamp formats parse** (`YYYY-MM-DD HH:MM:SS` and `MM/DD/YYYY HH:MM:SS`). Anything
  else is skipped by option 7.
- **Evil twins are a heuristic.** A venue running mixed-vendor APs on one SSID looks identical
  to an attack.
- **A published MAC is permanent.** WiGLE and its mirrors do not forget.

## Legal

THE SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE", WITHOUT WARRANTY OF ANY KIND,
EXPRESS, IMPLIED, OR STATUTORY, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, ACCURACY, AND
NON-INFRINGEMENT. THE AUTHORS AND COPYRIGHT HOLDERS MAKE NO REPRESENTATION THAT THE
SOFTWARE IS COMPLETE, ACCURATE, RELIABLE, SECURE, ERROR-FREE, OR LAWFUL FOR YOUR USE
IN YOUR JURISDICTION.

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL THE AUTHORS,
COPYRIGHT HOLDERS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGE, LOSS, COST, OR
OTHER LIABILITY OF ANY KIND WHATSOEVER — WHETHER DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, PUNITIVE, OR CONSEQUENTIAL; WHETHER IN CONTRACT, TORT (INCLUDING
NEGLIGENCE), STRICT LIABILITY, STATUTE, OR ANY OTHER THEORY; AND WHETHER OR NOT
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE — ARISING FROM, OUT OF, OR IN ANY WAY
CONNECTED WITH THE SOFTWARE, ITS USE OR INABILITY TO BE USED, THE DATA IT PROCESSES
OR PRODUCES, OR ANY ACT OR OMISSION UNDERTAKEN IN RELIANCE ON IT. THIS INCLUDES,
WITHOUT LIMITATION, ANY LOSS OF DATA, LOSS OF PRIVACY, PROPERTY DAMAGE, PERSONAL
INJURY, BUSINESS INTERRUPTION, LOST PROFITS, REGULATORY ACTION, FINES, OR THIRD-PARTY
CLAIMS.

YOU, THE USER, ASSUME ALL RISK ARISING FROM YOUR USE OF THE SOFTWARE AND THE DATA YOU
CHOOSE TO PROCESS, STORE, EXPORT, PUBLISH, OR UPLOAD. YOU ALONE ARE RESPONSIBLE FOR
DETERMINING AND COMPLYING WITH ALL LAWS, REGULATIONS, LICENSES, AND THIRD-PARTY TERMS
(INCLUDING THOSE OF ANY SERVICE YOU UPLOAD TO) THAT APPLY TO YOU. YOU AGREE TO
INDEMNIFY, DEFEND, AND HOLD HARMLESS THE AUTHORS, COPYRIGHT HOLDERS, AND CONTRIBUTORS
FROM AND AGAINST ANY AND ALL CLAIMS, LIABILITIES, DAMAGES, LOSSES, AND EXPENSES
(INCLUDING REASONABLE LEGAL FEES) ARISING FROM OR RELATED TO YOUR USE OF THE SOFTWARE
OR YOUR VIOLATION OF ANY LAW OR THIRD-PARTY RIGHT.

BY USING THE SOFTWARE YOU ACCEPT THESE TERMS. IF YOU DO NOT AGREE, DO NOT USE IT.
WHERE ANY LIMITATION ABOVE IS HELD UNENFORCEABLE, IT SHALL APPLY TO THE MAXIMUM
EXTENT PERMITTED, AND THE REMAINDER SHALL REMAIN IN FULL FORCE.
