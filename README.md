# WiGLE CSV Processor

Strips your home and your own devices out of WiGLE wardrive CSVs before you share them, then
reports creeps, evil twins, encryption, channels, vendors, and busiest times.

Python 3.10+, standard library only.

## Install

```bash
git clone https://github.com/lukeswitz/wigle-processor.git
cd wigle-processor
python3 wigle_processor.py
```

## Use it

```bash
python3 wigle_processor.py                       # menu
python3 wigle_processor.py day1.csv day2.csv     # or pick files
```

The first run asks for your home coordinates and your own device MACs and saves them to
`filter.json`. After that every run applies them.

```
   1) Clean this drive for sharing   (remove your home + your devices)
   2) Who followed me?               (same device seen at many stops)
   3) Encryption breakdown
   4) Channel usage
   5) Evil twins / rogue APs
   6) Device makers (vendors)
   7) Busiest times
   8) Merge several drives into one
   9) Export a map (KML for Google Earth, GeoJSON for QGIS)
```

Option 1 writes cleaned copies into `cleaned/` and leaves your originals alone. Upload those.

Option 2 on the sample data:

```
Locations    Sightings    Vendor                 MAC Address
----------------------------------------------------------------------
6            6            Ubiquiti Inc           DC:9F:DB:DE:AD:99
```

## Before you upload

Your drive starts and ends at your house, and every AP heard while parked is in the file.
The densest, most-repeated cluster is where you sleep.

The home filter removes **every network within the radius**, not just your own APs — leaving
the neighbors in still marks the spot. It is a true circle; 350 m means 350 m in every
direction.

Your phone, watch, headunit and tags ride along and appear at every stop, which is a movement
trace of you. Option 2 finds them. Put their MACs in `blocked_macs`.

WiGLE and its mirrors do not forget a published MAC.

## filter.json

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

MACs and SSIDs match exactly. Patterns are regexes tested against both. If home removal
matches nothing, check for a missing minus sign on longitude.

## Command line

```bash
# clean for upload
python3 wigle_processor.py *.csv --scrub --exclude-home

# coordinates without a config file
python3 wigle_processor.py *.csv --scrub --exclude-home --lat 40.7128 --lon -74.0060

# every analysis at once
python3 wigle_processor.py *.csv --creeps --evil-twins --encryption --channels --vendor-stats --time-analysis

# merge two drives and map the result
python3 wigle_processor.py day1.csv day2.csv --merge all.csv --export-kml map.kml
```

| Flag | |
|---|---|
| `--scrub` | Cleaned copies into `cleaned/`. |
| `--exclude-home` | With `--scrub`, also drop the home radius. |
| `--lat`, `--lon` | Overrides the config coordinates. |
| `--config FILE` | Default `filter.json`. |
| `--create-config FILE` | Write a template and exit. |
| `--output-dir DIR` | Default `cleaned`. |
| `--creeps` `--evil-twins` `--encryption` `--channels` `--vendor-stats` `--time-analysis` | Analysis. |
| `--min-locs N` | Locations before a device counts as a creep. Default 3. |
| `--merge FILE` | Merge and deduplicate. |
| `--export-kml FILE` `--export-geojson FILE` | Map export, skipping records with no GPS fix. |
| `--top N` | Rows per table. Default 20. |
| `-i` | Force the menu. |

Vendor lookup uses a bundled IEEE table. `WIGLE_OUI_FILE=/path/to/oui.txt` replaces it.

`python3 make_sample.py` writes two synthetic CSVs with a planted home, a creep, an evil twin,
and a record with no GPS.

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
