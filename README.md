# WiGLE CSV Processor

Command-line and interactive tool to clean and analyze WiGLE-format wardrive CSVs. Removes
your home location and your own devices before you share a drive, and reports creeps,
evil-twin APs, encryption, channels, vendors, and activity times. Exports to KML, GeoJSON,
JSON, and CSV.

Python 3.10+ standard library only. No dependencies. Runs offline; it opens no network
connections and associates with no wireless network.

## Contents

1. [Requirements](#requirements)
2. [Install](#install)
3. [How to run](#how-to-run)
4. [Config file](#config-file)
5. [Flag reference](#flag-reference)
6. [Menu options](#menu-options)
7. [How it works](#how-it-works)
8. [Sample data](#sample-data)
9. [Legal](#legal)

## Requirements

- Python 3.10 or newer. No packages to install.

## Install

```bash
git clone https://github.com/lukeswitz/wigle-processor.git && cd wigle-processor
python3 wigle_processor.py --help
```

## How to run

### Guided menu (recommended)

****On first use it walks you through your privacy settings (home location,
your own device MACs and SSIDs) and saves them to `filter.json`; later runs reuse that file.
It then presents a menu.****

```bash
python3 wigle_processor.py            # uses CSVs in the current folder
python3 wigle_processor.py *.csv      # specify one or multiple files to process
```

### Command-line flags

```bash
# clean a drive for upload: remove home (from filter.json) and your own devices
python3 wigle_processor.py *.csv --scrub --exclude-home --config filter.json

# or give home coordinates inline instead of a config file
python3 wigle_processor.py *.csv --scrub --exclude-home --lat 40.7128 --lon -74.0060

# analysis in one pass
python3 wigle_processor.py *.csv --creeps --evil-twins --encryption --channels --vendor-stats --time-analysis

# merge drives, deduplicate, and export a map
python3 wigle_processor.py day1.csv day2.csv --merge all.csv --export-kml drive.kml
```

Cleaned copies are written to `./cleaned/`; your originals are never modified.

## Config file

`filter.json` stores your home location and everything to remove, so you don't retype flags.
Generate a template, edit it, and pass it with `--config`. The interactive setup writes the
same file for you.

```bash
python3 wigle_processor.py --create-config filter.json
```

```json
{
  "latitude": 0.0,
  "longitude": 0.0,
  "radius_m": 400,
  "blocked_macs": ["FF:FF:FF:FF:FF:FF", "AA:BB:CC:DD:EE:FF"],
  "blocked_ssids": ["myssid", "wardriver.uk"],
  "blocked_patterns": ["MyCompany.*", ".*test.*"]
}
```

| Field | Type | Purpose |
|---|---|---|
| `latitude`, `longitude` | number | Location to remove. Applied on the command line only with `--exclude-home`; the interactive menu applies it automatically. |
| `radius_m` | number | Radius around that point to remove, in meters. |
| `blocked_macs` | list | Exact MAC addresses to remove (your phone, watch, car, home APs). |
| `blocked_ssids` | list | Exact network names to remove. |
| `blocked_patterns` | list | Regular expressions tested against each SSID and MAC; a match is removed. |

The `blocked_*` lists apply on every `--scrub`. The location is removed only when
`--exclude-home` is set, so a config can hold your coordinates without always filtering.

## Flag reference

| Flag | Description |
|---|---|
| `files` | One or more WiGLE CSV files. Omit to use `*.csv` in the current folder. |
| `-i`, `--interactive` | Force the interactive menu (also the default when no operation is given). |
| `--scrub` | Write cleaned copies to `./cleaned/`. |
| `--exclude-home` | With `--scrub`, remove networks near `--lat/--lon` or the config location. |
| `--lat`, `--lon` | Reference coordinates. Overrides the config location. |
| `--config FILE` | Load a `filter.json`. |
| `--create-config FILE` | Write a config template and exit. |
| `--output-dir DIR` | Folder for cleaned copies (default `./cleaned`). |
| `--creeps` | Devices (MACs) seen at multiple locations. |
| `--min-locs N` | Minimum distinct locations for `--creeps` (default 3). |
| `--evil-twins` | Same SSID from a suspicious source — an open clone of a secured network, or two genuinely different hardware vendors. Normal dual-band and mesh APs (same vendor, multiple BSSIDs/channels) are not flagged. |
| `--encryption` | Encryption-type breakdown. |
| `--channels` | Channel usage and 2.4/5 GHz split. |
| `--vendor-stats` | MAC OUI to manufacturer breakdown. |
| `--time-analysis` | Activity by hour and date. |
| `--merge FILE` | Merge all inputs, deduplicate, write to FILE. |
| `--export-csv`, `--export-json`, `--export-geojson`, `--export-kml` | Export all records to FILE. |
| `--top N` | Limit rows shown in stats (default 20). |

## Menu options

| # | Action |
|---|---|
| 1 | Clean this drive for sharing (remove home and your devices) |
| 2 | Who followed me? (same device at many stops) |
| 3 | Encryption breakdown |
| 4 | Channel usage |
| 5 | Evil twins / rogue APs |
| 6 | Device makers (vendors) |
| 7 | Busiest times |
| 8 | Merge several drives into one |
| 9 | Export to a map / JSON / CSV |
| 0 | Quit |

## How it works

- Cleaned copies go to `./cleaned/`; originals are untouched.
- After a scrub, a results summary reports how many records were kept and removed, broken
  down by reason (home, blocked MAC, blocked SSID, blocked pattern). If home removal matched
  nothing, it warns you to check your latitude/longitude sign.
- Records without a GPS fix are kept in JSON and CSV exports and omitted from KML and GeoJSON.
- Home-leak warning: if a shareable output (a merge, an export, or a `--scrub` without
  `--exclude-home`) still contains networks near your home, the tool prints a `!! WARNING`
  on completion. Exports run on the full record set, so this catches the case where
  `./cleaned/` is safe but a `--export-*` in the same run still contains home.
- Vendor lookup uses the bundled IEEE OUI database (`data/oui.csv`, ~39,000 entries).
  Replace that file to update it, or set `WIGLE_OUI_FILE` to a standard IEEE `oui.txt` to
  override:
  ```bash
  export WIGLE_OUI_FILE=/path/to/oui.txt
  ```
- Tip: keep one `filter.json` with your home and devices and pass `--config filter.json`
  (or use the interactive menu, which saves and reuses it automatically).

## Sample data

`make_sample.py` writes two test CSVs containing a planted home location, a device seen at
six stops (a creep), one SSID on three MACs (an evil twin), and one record with no GPS. All
coordinates are synthetic offsets from 0,0; no real location is used.

```bash
python3 make_sample.py    # writes sample_day1.csv and sample_day2.csv
```

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
