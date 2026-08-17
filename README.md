# WiGLE CSV Processor

#### OPSEC and analysis tool for WiGLE CSV files.

> Your drive starts and ends at your house. This strips that out before you share the file, then
tells you what else the drive picked up.

**Requirements: `Python 3.10+, standard library only`**

## Get started

```bash
git clone https://github.com/lukeswitz/wigle-processor.git
cd wigle-processor
python3 wigle_processor.py
```

- Run it in a folder holding your CSVs, or point to them with the script.
- Use flags or run the script on its own for an interactive menu.

> [!NOTE]
> A `filter.json` file is created on first run, used for every run after (mod it as needed,
> write a fresh template with `--create-config filter.json`):

```
Your home latitude (blank to skip):
Your home longitude (blank to skip):
Hide everything within how many meters (default 150)?
MAC addresses of your own devices, comma-separated (blank to skip):
Names (SSIDs) of your own networks, comma-separated (blank to skip):

Results: kept 18 of 20 records, removed 2.
        1  matched a blocked SSID
        1  near your home location
```

The radius is a circle. It removes every network inside it, not just yours.

Then the menu:

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
   0) Quit
```

### 1 — Clean this drive for sharing

```
Cleaned sample_day1.csv -> cleaned/sample_day1.csv (10/12 kept)
Cleaned sample_day2.csv -> cleaned/sample_day2.csv (8/8 kept)
Upload the files in that folder, not your originals.
```

### 2 — Who followed me?

```
Locations    Sightings    Vendor                 MAC Address
6            6            Ubiquiti Inc           DC:9F:DB:DE:AD:99
```

### 3 — Encryption breakdown

```
Encryption                 Pct     Count / Total
[WPA2-PSK-CCMP][ESS]    33.33%        4/12
[WEP]                    8.33%        1/12

  Open networks: 4
```

### 4 — Channel usage

```
Channel    Band             Pct     Count / Total
11         2.4 GHz       16.67%        2/12
BLE        BLE           16.67%        2/12
36         5 GHz          8.33%        1/12

  Band summary:
    2.4 GHz: 6
    5 GHz: 4
    BLE: 2
```

### 5 — Evil twins / rogue APs

```
  SSID: 'CoffeeShop'
    MACs (3): 24:A4:3C:00:00:10, 94:EB:2C:00:00:11, FF:FF:FF:00:00:16
    Flags: open clone; mixed vendors
```

### 6 — Device makers

```
Vendor                               Pct   Count
NETGEAR                           27.27%   3
Ubiquiti Inc                      18.18%   2

  1 randomized MACs excluded — no vendor to look up.
```

### 7 — Busiest times

```
  Peak activity hour: 09:00 (11 networks)
  Most active date:   2026-05-16 (11 networks)

    09:00  ███████████ 11
    10:00  ███████ 7
```

### 8 — Merge several drives into one

```
Wrote merged.csv: 17 unique networks, 1 duplicate removed.
```

### 9 — Export a map

```
KML export: map.kml (17 geolocated records)
```

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

MACs and SSIDs match exactly. Patterns are regexes, tested against both.

## Without the menu

```bash
python3 wigle_processor.py *.csv --scrub                      # clean for upload
python3 wigle_processor.py *.csv --scrub --lat LAT --lon LON  # coords without a config
python3 wigle_processor.py *.csv --creeps --evil-twins        # flags combine
python3 wigle_processor.py d1.csv d2.csv --merge all.csv --export-kml map.kml
```

Any flag skips the menu.

| Flag | |
|---|---|
| `FILE...` | CSVs to read. Omit for every `.csv` in the current folder. |
| `-i`, `--interactive`, `--menu` | Force the menu even with other flags set. |
| `--scrub` | Cleaned copies into `cleaned/`. Removes the home radius unless `--keep-home`. |
| `--keep-home` | Leave home in. Warns when it does. |
| `--exclude-home`, `--not-here` | Drop the home radius. Now the default; accepted so older commands still run. |
| `--lat`, `--lon` | Home coordinates with a fixed 150 m radius. Overrides the config. |
| `--config FILE` | Load a config. Default `filter.json`. |
| `--create-config FILE` | Write a config template and exit. |
| `--output-dir DIR` | Default `cleaned`. |
| `--creeps` | Menu 2. |
| `--min-locs N` | Stops before a device counts as a creep. Default 3. |
| `--encryption` `--channels` `--evil-twins` `--vendor-stats` `--time-analysis` | Menu 3–7. |
| `--merge FILE` | Merge and deduplicate. |
| `--export-kml FILE` `--export-geojson FILE` | Map export. |
| `--top N` | Row limit for creeps, channels, vendors. Default 20. |

`WIGLE_OUI_FILE=/path/to/oui.txt` replaces the bundled vendor table.
`python3 make_sample.py` writes two synthetic CSVs to practice on.

## Limitations

- The road to your door is still in the file. Set the radius generously.
- Records with no GPS fix survive the home filter. Map exports drop them.
- Blocked SSIDs are case-sensitive; MACs are not.
- Creep locations are ~1 km grid cells, not points.
- Hidden and blank SSIDs are invisible to evil-twin detection.
- Randomized MACs are excluded from vendor stats and never accumulate creep locations.
- Dedup needs an exact position match.
- Option 7 parses `YYYY-MM-DD HH:MM:SS` and `MM/DD/YYYY HH:MM:SS` only.
- Evil twins are a heuristic. A venue with mixed-vendor APs looks the same as an attack.
- A published MAC is permanent. WiGLE and its mirrors do not forget.

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
