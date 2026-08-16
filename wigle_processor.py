#!/usr/bin/env python3
"""
WiGLE CSV Processor — wardriving analysis toolkit

Multi-CSV merge/dedup, OUI vendor lookup, creep/evil-twin detection,
KML/GeoJSON/JSON/CSV export, encryption+channel stats, time-on-air analysis.

Flags combine — do several things in one run.

EXAMPLES:
  # interactive menu (no flags)
  python3 wigle_processor.py

  # clean before upload: strip home + block your own devices (home coords live in filter.json)
  python3 wigle_processor.py *.csv --scrub --exclude-home --config filter.json

  # same, but give the home coords inline instead of a config file
  python3 wigle_processor.py *.csv --scrub --exclude-home --lat YOUR_LAT --lon YOUR_LON

  # one analysis pass: creeps, evil twins, and every stat
  python3 wigle_processor.py *.csv --creeps --evil-twins --encryption --channels --vendor-stats --time-analysis

  # merge drives, dedup, and export a map in one command
  python3 wigle_processor.py day1.csv day2.csv --merge all.csv --export-kml drive.kml --export-geojson drive.geojson

  # make a block-list template to edit
  python3 wigle_processor.py --create-config filter.json
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
import io


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class WiGLERecord:
    mac: str
    ssid: str
    auth_mode: str
    first_seen: str
    channel: str
    rssi: str
    latitude: float
    longitude: float
    altitude: str
    accuracy: str
    network_type: str
    source_file: str = ""

    @classmethod
    def from_csv_row(cls, row: list[str], source_file: str = "") -> Optional["WiGLERecord"]:
        if not row or not row[0].strip():
            return None
        try:
            lat = float(row[6]) if len(row) > 6 and row[6].strip() else 0.0
            lon = float(row[7]) if len(row) > 7 and row[7].strip() else 0.0
            return cls(
                mac=row[0].strip().upper(),
                ssid=row[1].strip() if len(row) > 1 else "",
                auth_mode=row[2].strip() if len(row) > 2 else "",
                first_seen=row[3].strip() if len(row) > 3 else "",
                channel=row[4].strip() if len(row) > 4 else "",
                rssi=row[5].strip() if len(row) > 5 else "0",
                latitude=lat,
                longitude=lon,
                altitude=row[8].strip() if len(row) > 8 else "0",
                accuracy=row[9].strip() if len(row) > 9 else "0",
                network_type=row[10].strip() if len(row) > 10 else "WIFI",
                source_file=source_file,
            )
        except (ValueError, IndexError):
            return None

    def to_row(self) -> list:
        return [
            self.mac, self.ssid, self.auth_mode,
            self.first_seen, self.channel, self.rssi,
            self.latitude, self.longitude, self.altitude,
            self.accuracy, self.network_type,
        ]

    @property
    def has_gps(self) -> bool:
        return not (self.latitude == 0.0 and self.longitude == 0.0)

    @property
    def rssi_int(self) -> int:
        try:
            return int(self.rssi)
        except (ValueError, TypeError):
            return 0

    @property
    def oui(self) -> str:
        return self.mac[:8].upper()


# ---------------------------------------------------------------------------
# OUI vendor lookup (stdlib-only, cached in memory)
# ---------------------------------------------------------------------------

_OUI_CACHE: dict[str, str] = {}
_OUI_LOADED = False
_OUI_BUNDLED: dict[str, str] = {
    "00:00:0C": "Cisco", "00:50:56": "VMware", "00:0C:29": "VMware",
    "FC:FB:FB": "Cisco Meraki", "E8:9F:80": "Ubiquiti", "04:18:D6": "Ubiquiti",
    "DC:9F:DB": "Ubiquiti", "24:A4:3C": "Ubiquiti", "78:8A:20": "Ubiquiti",
    "80:2A:A8": "Ubiquiti", "00:27:22": "Ubiquiti", "18:E8:29": "Ubiquiti",
    "44:D9:E7": "Ubiquiti", "F0:9F:C2": "Ubiquiti",
    "00:17:F2": "Apple", "00:1C:B3": "Apple", "00:1D:4F": "Apple",
    "00:1E:52": "Apple", "00:1E:C2": "Apple", "00:21:E9": "Apple",
    "00:22:41": "Apple", "00:23:12": "Apple", "00:23:32": "Apple",
    "00:23:6C": "Apple", "00:24:36": "Apple", "00:25:00": "Apple",
    "00:25:4B": "Apple", "00:25:BC": "Apple", "00:26:08": "Apple",
    "00:26:4A": "Apple", "00:26:B9": "Apple", "00:26:BB": "Apple",
    "00:30:65": "Apple",
    "00:1A:11": "Google", "94:EB:2C": "Google", "F4:F5:E8": "Google",
    "54:60:09": "Google",
    "00:03:7F": "Atheros", "00:17:88": "Philips Hue",
    "00:1B:11": "D-Link", "1C:7E:E5": "D-Link", "28:10:7B": "D-Link",
    "B0:C5:54": "D-Link", "C8:BE:19": "D-Link",
    "00:1E:2A": "Netgear", "20:4E:7F": "Netgear", "2C:B0:5D": "Netgear",
    "A0:21:B7": "Netgear", "C0:3F:0E": "Netgear",
    "00:14:BF": "Linksys", "00:16:B6": "Linksys", "00:18:39": "Linksys",
    "00:1A:70": "Linksys", "00:1C:10": "Linksys",
    "00:19:70": "Belkin", "94:44:52": "Belkin", "EC:1A:59": "Belkin",
    "00:07:40": "Motorola", "00:22:12": "Motorola",
    "00:60:2F": "Cisco", "00:E0:1E": "Cisco",
    "00:09:5B": "Netgear", "00:0F:B5": "Netgear",
    "00:1D:73": "TP-Link", "14:CF:92": "TP-Link", "50:BD:5F": "TP-Link",
    "84:16:F9": "TP-Link", "A0:F3:C1": "TP-Link", "EC:08:6B": "TP-Link",
    "F4:EC:38": "TP-Link", "00:27:19": "TP-Link", "18:D6:C7": "TP-Link",
    "50:C7:BF": "TP-Link", "C4:E9:84": "TP-Link",
    "00:18:4D": "Netopia", "00:50:BA": "D-Link",
    "8C:DC:D4": "Asustek", "00:1A:92": "Asustek", "10:02:B5": "Asustek",
    "2C:FD:A1": "Asustek", "30:85:A9": "Asustek", "50:46:5D": "Asustek",
    "AC:22:0B": "Asustek", "BC:EE:7B": "Asustek",
    "00:26:F2": "Netgear", "C4:3D:C7": "Netgear",
    "00:13:F7": "Actiontec", "00:18:01": "Actiontec",
    "00:22:6B": "Cisco-Linksys", "C0:C1:C0": "Cisco-Linksys",
    "00:24:A5": "Buffalo", "10:6F:3F": "Buffalo",
    "00:13:10": "Linksys-Cisco", "00:1F:33": "Netgear",
    "44:32:C8": "Samsung", "00:15:B9": "Samsung", "CC:3A:61": "Samsung",
    "34:BE:00": "Samsung", "00:23:C2": "Samsung",
    "7C:BB:8A": "Amazon", "F0:27:2D": "Amazon", "FC:A1:83": "Amazon",
    "44:65:0D": "Amazon", "74:75:48": "Amazon",
}


def _load_oui_bundled_csv() -> dict[str, str]:
    path = Path(__file__).with_name("data") / "oui.csv"
    result: dict[str, str] = {}
    if not path.exists():
        return result
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 3:
                    continue
                a = row[1].strip().upper()
                if len(a) < 6:
                    continue
                result[f"{a[0:2]}:{a[2:4]}:{a[4:6]}"] = row[2].strip()
    except OSError:
        pass
    return result


def _load_oui_cache_from_env() -> dict[str, str]:
    oui_file = os.environ.get("WIGLE_OUI_FILE", "")
    result: dict[str, str] = {}
    if not oui_file or not os.path.exists(oui_file):
        return result
    try:
        with open(oui_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 2)
                if len(parts) >= 3 and parts[1].upper() == "(HEX)":
                    raw = parts[0].replace("-", ":").upper()
                    vendor = parts[2].strip()
                    result[raw] = vendor
    except OSError:
        pass
    return result


def lookup_vendor(mac: str) -> str:
    global _OUI_LOADED
    if not _OUI_LOADED:
        _OUI_CACHE.update(_OUI_BUNDLED)
        _OUI_CACHE.update(_load_oui_bundled_csv())
        _OUI_CACHE.update(_load_oui_cache_from_env())
        _OUI_LOADED = True
    oui = mac[:8].upper()
    return _OUI_CACHE.get(oui, "Unknown")


# ---------------------------------------------------------------------------
# Geo helpers
# ---------------------------------------------------------------------------

_EARTH_RADIUS_M = 6_371_000.0
_M_PER_DEG = 111_320.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Analyzers — all original method names preserved exactly
# ---------------------------------------------------------------------------

class ChannelAnalyzer:
    def __init__(self) -> None:
        self.channel_counts: Counter = Counter()
        self.unique_networks: set[str] = set()
        self._band_map: dict[str, list[str]] = {}

    def add_record(self, record: WiGLERecord) -> None:
        network_id = f"{record.mac} {record.ssid}"
        if network_id in self.unique_networks:
            return
        self.unique_networks.add(network_id)

        ch = record.channel
        if ch == "0":
            ch = "BLE" if record.network_type.upper() not in ("WIFI", "") else "0"

        self.channel_counts[ch] += 1

        try:
            ch_int = int(ch)
            band = "2.4 GHz" if ch_int <= 14 else "5 GHz"
        except ValueError:
            band = ch
        self._band_map.setdefault(band, []).append(ch)

    def get_stats(self, top_n: int = 20) -> dict[str, dict[str, float]]:
        total = sum(self.channel_counts.values())
        if total == 0:
            return {}
        stats: dict[str, dict[str, float]] = {}
        for channel, count in self.channel_counts.most_common(top_n):
            try:
                ch_int = int(channel)
                band = "2.4 GHz" if ch_int <= 14 else "5 GHz"
            except ValueError:
                band = channel
            stats[channel] = {
                "count": count,
                "percentage": (count / total) * 100,
                "total": total,
                "band": band,
            }
        return stats

    def band_summary(self) -> dict[str, int]:
        summary: dict[str, int] = defaultdict(int)
        for ch, count in self.channel_counts.items():
            try:
                ch_int = int(ch)
                band = "2.4 GHz" if ch_int <= 14 else "5 GHz"
            except ValueError:
                band = ch
            summary[band] += count
        return dict(summary)


class EncryptionAnalyzer:
    def __init__(self) -> None:
        self.encryption_counts: Counter = Counter()
        self.unique_networks: set[str] = set()

    def add_record(self, record: WiGLERecord) -> None:
        network_id = f"{record.mac} {record.ssid}"
        if network_id in self.unique_networks:
            return
        self.unique_networks.add(network_id)
        self.encryption_counts[record.auth_mode or "OPEN"] += 1

    def get_stats(self) -> dict[str, dict[str, float]]:
        total = sum(self.encryption_counts.values())
        if total == 0:
            return {}
        stats: dict[str, dict[str, float]] = {}
        for enc_type, count in self.encryption_counts.items():
            stats[enc_type] = {
                "count": count,
                "percentage": (count / total) * 100,
                "total": total,
            }
        return stats

    def open_count(self) -> int:
        return sum(v for k, v in self.encryption_counts.items() if "OPEN" in k.upper() or k == "")


class CreepDetector:
    def __init__(self, fudge_factor: int = 100) -> None:
        self.fudge_factor = fudge_factor
        self.mac_locations: dict[str, set[str]] = defaultdict(set)
        self.mac_total_sightings: dict[str, int] = defaultdict(int)
        self.mac_ssids: dict[str, set[str]] = defaultdict(set)
        self.mac_records: dict[str, list[WiGLERecord]] = defaultdict(list)

    def add_record(self, record: WiGLERecord) -> None:
        if not record.has_gps:
            return
        lat = int((record.latitude * self.fudge_factor) + 0.5) / self.fudge_factor
        lon = int((record.longitude * self.fudge_factor) - 0.5) / self.fudge_factor
        location = f"{lat:.2f} {lon:.2f}"
        self.mac_locations[record.mac].add(location)
        self.mac_total_sightings[record.mac] += 1
        self.mac_ssids[record.mac].add(record.ssid)
        self.mac_records[record.mac].append(record)

    def get_multi_location_devices(self, min_locations: int = 3) -> list[tuple[int, int, str]]:
        results: list[tuple[int, int, str]] = []
        for mac, locations in self.mac_locations.items():
            if len(locations) >= min_locations:
                sightings = self.mac_total_sightings[mac]
                results.append((len(locations), sightings, mac))
        return sorted(results, reverse=True)

    def get_creep_report(self, min_locations: int = 3) -> list[dict]:
        report = []
        for loc_count, sighting_count, mac in self.get_multi_location_devices(min_locations):
            recs = self.mac_records[mac]
            report.append({
                "mac": mac,
                "vendor": lookup_vendor(mac),
                "unique_locations": loc_count,
                "total_sightings": sighting_count,
                "ssids": sorted(self.mac_ssids[mac]),
                "sample_coords": [
                    {"lat": r.latitude, "lon": r.longitude, "ssid": r.ssid}
                    for r in recs[:5]
                ],
            })
        return report


# ---------------------------------------------------------------------------
# OUI / vendor stats
# ---------------------------------------------------------------------------

class VendorAnalyzer:
    def __init__(self) -> None:
        self.vendor_counts: Counter = Counter()
        self.seen: set[str] = set()

    def add_record(self, record: WiGLERecord) -> None:
        if record.mac in self.seen:
            return
        self.seen.add(record.mac)
        self.vendor_counts[lookup_vendor(record.mac)] += 1

    def get_stats(self, top_n: int = 20) -> dict[str, dict]:
        total = sum(self.vendor_counts.values())
        stats: dict[str, dict] = {}
        for vendor, count in self.vendor_counts.most_common(top_n):
            stats[vendor] = {"count": count, "percentage": (count / total) * 100 if total else 0}
        return stats


# ---------------------------------------------------------------------------
# Evil-twin / rogue heuristics
# ---------------------------------------------------------------------------

def _is_locally_administered(mac: str) -> bool:
    try:
        return bool(int(mac[0:2], 16) & 0x02)
    except ValueError:
        return False


def _is_open_auth(auth: str) -> bool:
    a = auth.upper()
    return a == "" or ("OPEN" in a) or ("WEP" in a)


class RogueDetector:
    def __init__(self) -> None:
        self.ssid_map: dict[str, list[WiGLERecord]] = defaultdict(list)

    def add_record(self, record: WiGLERecord) -> None:
        if record.ssid:
            self.ssid_map[record.ssid].append(record)

    def find_evil_twins(self) -> list[dict]:
        findings: list[dict] = []
        for ssid, records in self.ssid_map.items():
            macs = {r.mac for r in records}
            if len(macs) < 2:
                continue
            auths = {r.auth_mode for r in records}
            channels = {r.channel for r in records}

            has_open = any(_is_open_auth(a) for a in auths)
            has_secured = any(not _is_open_auth(a) for a in auths)

            global_vendors = {
                lookup_vendor(m) for m in macs
                if not _is_locally_administered(m) and lookup_vendor(m) != "Unknown"
            }

            suspicion = []
            if has_open and has_secured:
                suspicion.append("open clone of a secured network")
            if len(global_vendors) > 1:
                suspicion.append(f"different hardware vendors ({', '.join(sorted(global_vendors))})")
            if not suspicion:
                continue

            findings.append({
                "ssid": ssid,
                "mac_count": len(macs),
                "macs": sorted(macs),
                "vendors": sorted(global_vendors) or ["Unknown"],
                "auth_modes": sorted(auths),
                "channels": sorted(channels),
                "suspicion_flags": suspicion,
            })
        return sorted(findings, key=lambda x: x["mac_count"], reverse=True)


# ---------------------------------------------------------------------------
# Time-on-air analysis
# ---------------------------------------------------------------------------

class TimeAnalyzer:
    _FMT = "%Y-%m-%d %H:%M:%S"
    _FMT_ALT = "%m/%d/%Y %H:%M:%S"

    def __init__(self) -> None:
        self.by_hour: Counter = Counter()
        self.by_date: Counter = Counter()
        self.total = 0

    def _parse(self, ts: str) -> Optional[datetime]:
        for fmt in (self._FMT, self._FMT_ALT):
            try:
                return datetime.strptime(ts.strip(), fmt)
            except ValueError:
                continue
        return None

    def add_record(self, record: WiGLERecord) -> None:
        dt = self._parse(record.first_seen)
        if dt:
            self.by_hour[dt.hour] += 1
            self.by_date[dt.strftime("%Y-%m-%d")] += 1
            self.total += 1

    def get_stats(self) -> dict:
        if not self.total:
            return {}
        peak_hour = self.by_hour.most_common(1)[0] if self.by_hour else (None, 0)
        peak_date = self.by_date.most_common(1)[0] if self.by_date else (None, 0)
        return {
            "total_timestamped": self.total,
            "peak_hour": peak_hour[0],
            "peak_hour_count": peak_hour[1],
            "peak_date": peak_date[0],
            "peak_date_count": peak_date[1],
            "by_hour": dict(self.by_hour),
            "by_date": dict(self.by_date),
        }


# ---------------------------------------------------------------------------
# Location filter
# ---------------------------------------------------------------------------

class LocationFilter:
    def __init__(self, my_lat: float, my_long: float, delta: float = 0.001) -> None:
        self.my_lat = my_lat
        self.my_long = my_long
        self.delta = delta
        self.lat_min = my_lat - delta
        self.lat_max = my_lat + delta
        self.long_min = my_long - delta
        self.long_max = my_long + delta

    def is_here(self, record: WiGLERecord) -> bool:
        if not record.has_gps:
            return False
        return (self.lat_min <= record.latitude <= self.lat_max and
                self.long_min <= record.longitude <= self.long_max)

    def is_not_here(self, record: WiGLERecord) -> bool:
        if not record.has_gps:
            return True
        return not self.is_here(record)


# ---------------------------------------------------------------------------
# Filter config — original method names preserved exactly
# ---------------------------------------------------------------------------

class FilterConfig:
    def __init__(self, config_file: Optional[str] = None) -> None:
        self.blocked_macs: set[str] = set()
        self.blocked_ssids: set[str] = set()
        self.blocked_patterns: list[re.Pattern] = []
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.radius_m: float = 400.0

        if config_file and os.path.exists(config_file):
            self.load_config(config_file)

    def load_config(self, config_file: str) -> None:
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            self.blocked_macs = {m.upper() for m in config.get("blocked_macs", [])}
            self.blocked_ssids = set(config.get("blocked_ssids", []))
            self.latitude = config.get("latitude")
            self.longitude = config.get("longitude")
            self.radius_m = config.get("radius_m", 400.0)
            for pattern in config.get("blocked_patterns", []):
                try:
                    self.blocked_patterns.append(re.compile(pattern))
                except re.error as e:
                    print(f"Warning: Invalid regex pattern '{pattern}': {e}")
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"\n!! ERROR: could not read {config_file} ({e}).")
            print("   Nothing will be blocked from this config. Fix the file and re-run.")

    def filter_reason(self, record: WiGLERecord) -> Optional[str]:
        if record.mac.upper() in self.blocked_macs:
            return "blocked_mac"
        if record.ssid in self.blocked_ssids:
            return "blocked_ssid"
        for pattern in self.blocked_patterns:
            if pattern.search(record.ssid) or pattern.search(record.mac):
                return "blocked_pattern"
        return None

    def should_filter(self, record: WiGLERecord) -> bool:
        return self.filter_reason(record) is not None

    def create_sample_config(self, config_file: str) -> None:
        sample = {
            "latitude": 0.0,
            "longitude": 0.0,
            "radius_m": 400,
            "blocked_macs": ["FF:FF:FF:FF:FF:FF", "AA:BB:CC:DD:EE:FF"],
            "blocked_ssids": ["myssid", "wardriver.uk"],
            "blocked_patterns": ["MyCompany.*", ".*test.*"],
        }
        with open(config_file, "w") as f:
            json.dump(sample, f, indent=2)
        print(f"Sample configuration created: {config_file}")


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_csv(records: list[WiGLERecord], path: str) -> None:
    header = ["MAC", "SSID", "AuthMode", "FirstSeen", "Channel", "RSSI",
              "CurrentLatitude", "CurrentLongitude", "AltitudeMeters", "AccuracyMeters", "Type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in records:
            writer.writerow(r.to_row())
    print(f"CSV export: {path} ({len(records)} records)")


def export_json(records: list[WiGLERecord], path: str) -> None:
    data = [asdict(r) for r in records]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"JSON export: {path} ({len(records)} records)")


def export_geojson(records: list[WiGLERecord], path: str) -> None:
    features = []
    for r in records:
        if not r.has_gps:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r.longitude, r.latitude]},
            "properties": {
                "mac": r.mac,
                "ssid": r.ssid,
                "auth": r.auth_mode,
                "channel": r.channel,
                "rssi": r.rssi_int,
                "first_seen": r.first_seen,
                "type": r.network_type,
                "vendor": lookup_vendor(r.mac),
            },
        })
    fc = {"type": "FeatureCollection", "features": features}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2)
    print(f"GeoJSON export: {path} ({len(features)} geolocated records)")


def export_kml(records: list[WiGLERecord], path: str) -> None:
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, "Document")
    name_el = ET.SubElement(doc, "name")
    name_el.text = "WiGLE Export"

    for r in records:
        if not r.has_gps:
            continue
        pm = ET.SubElement(doc, "Placemark")
        n = ET.SubElement(pm, "name")
        n.text = r.ssid or r.mac
        desc = ET.SubElement(pm, "description")
        desc.text = (f"MAC: {r.mac}\nAuth: {r.auth_mode}\n"
                     f"Channel: {r.channel}\nRSSI: {r.rssi}\n"
                     f"Vendor: {lookup_vendor(r.mac)}\nSeen: {r.first_seen}")
        pt = ET.SubElement(pm, "Point")
        coords = ET.SubElement(pt, "coordinates")
        coords.text = f"{r.longitude},{r.latitude},{r.altitude or 0}"

    tree = ET.ElementTree(kml)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    gps_count = sum(1 for r in records if r.has_gps)
    print(f"KML export: {path} ({gps_count} geolocated records)")


# ---------------------------------------------------------------------------
# Core processor
# ---------------------------------------------------------------------------

class WiGLEProcessor:
    def __init__(self) -> None:
        self.location_filter: Optional[LocationFilter] = None
        self.filter_config: Optional[FilterConfig] = None

    def set_location_filter(self, lat: float, lon: float, delta: float = 0.001) -> None:
        self.location_filter = LocationFilter(lat, lon, delta)

    def set_filter_config(self, config_file: str) -> None:
        self.filter_config = FilterConfig(config_file)

    def read_csv_file(self, filename: str) -> tuple[list[str], list[WiGLERecord]]:
        headers: list[str] = []
        records: list[WiGLERecord] = []
        delimiter = ","

        try:
            with open(filename, "r", encoding="utf-8", errors="replace", newline="") as f:
                lines = f.readlines()

            data_start = 0
            for i, line in enumerate(lines):
                if "MAC" in line:
                    delimiter = "\t" if "\t" in line else ","
                    data_start = i + 1
                    headers = lines[:data_start]
                    break

            if data_start == 0:
                print(f"Error: Could not find MAC header in {filename}")
                return headers, records

            reader = csv.reader(lines[data_start:], delimiter=delimiter)
            for row in reader:
                if not row or not row[0].strip():
                    continue
                record = WiGLERecord.from_csv_row(row, source_file=filename)
                if record:
                    records.append(record)

        except (FileNotFoundError, OSError) as e:
            print(f"Error reading file {filename}: {e}")

        return headers, records

    def filter_records(self, records: list[WiGLERecord],
                       location_mode: Optional[str] = None,
                       stats: Optional[Counter] = None) -> list[WiGLERecord]:
        filtered: list[WiGLERecord] = []
        for record in records:
            reason = self.filter_config.filter_reason(record) if self.filter_config else None
            if reason is None and self.location_filter and location_mode == "not_here":
                if not self.location_filter.is_not_here(record):
                    reason = "home"
            if reason is not None:
                if stats is not None:
                    stats[reason] += 1
                continue
            filtered.append(record)
        return filtered

    def write_csv_file(self, filename: str, headers: list[str], records: list[WiGLERecord]) -> None:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        delimiter = "\t" if headers and "\t" in headers[0] else ","
        with open(filename, "w", newline="", encoding="utf-8") as f:
            f.writelines(headers)
            writer = csv.writer(f, delimiter=delimiter)
            for record in records:
                writer.writerow(record.to_row())

    def merge_and_dedup(self, all_records: list[WiGLERecord]) -> list[WiGLERecord]:
        seen: set[str] = set()
        merged: list[WiGLERecord] = []
        for r in all_records:
            key = f"{r.mac}|{r.ssid}|{r.latitude:.6f}|{r.longitude:.6f}"
            if key not in seen:
                seen.add(key)
                merged.append(r)
        return merged


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------

def print_separator(width: int = 60) -> None:
    print("-" * width)


def print_creeps(detector: CreepDetector, all_records: list[WiGLERecord],
                 min_locations: int = 3, top: int = 20) -> None:
    multi = detector.get_multi_location_devices(min_locations)
    if not multi:
        print("No multi-location devices found.")
        return

    print(f"\n{'Locations':<12} {'Sightings':<12} {'Vendor':<22} {'MAC Address'}")
    print_separator(70)
    for loc_count, sighting_count, mac in multi[:top]:
        vendor = lookup_vendor(mac)
        print(f"{loc_count:<12} {sighting_count:<12} {vendor:<22} {mac}")
        sample = 0
        for record in all_records:
            if record.mac == mac and sample < 3:
                print(f"  {record.latitude:.6f}, {record.longitude:.6f} — {record.ssid!r}")
                sample += 1
        print()


def print_encryption(analyzer: EncryptionAnalyzer) -> None:
    stats = analyzer.get_stats()
    if not stats:
        print("No encryption data.")
        return
    print(f"\n{'Encryption':<20} {'Pct':>9}   {'Count':>7} / Total")
    print_separator(55)
    for enc_type, data in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"{enc_type:<20} {data['percentage']:>8.2f}%   {data['count']:>6}/{int(data['total'])}")
    print(f"\n  Open networks: {analyzer.open_count()}")


def print_channels(analyzer: ChannelAnalyzer, top_n: int = 20) -> None:
    stats = analyzer.get_stats(top_n)
    if not stats:
        print("No channel data.")
        return
    print(f"\n{'Channel':<10} {'Band':<10} {'Pct':>9}   {'Count':>7} / Total")
    print_separator(55)
    for channel, data in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
        band = data.get("band", "")
        print(f"{channel:<10} {band:<10} {data['percentage']:>8.2f}%   {data['count']:>6}/{int(data['total'])}")
    band_sum = analyzer.band_summary()
    print("\n  Band summary:")
    for band, cnt in sorted(band_sum.items()):
        print(f"    {band}: {cnt}")


def print_vendor_stats(analyzer: VendorAnalyzer, top_n: int = 20) -> None:
    stats = analyzer.get_stats(top_n)
    if not stats:
        print("No vendor data.")
        return
    print(f"\n{'Vendor':<30} {'Pct':>9}   Count")
    print_separator(55)
    for vendor, data in stats.items():
        print(f"{vendor:<30} {data['percentage']:>8.2f}%   {data['count']}")


def print_evil_twins(detector: RogueDetector) -> None:
    findings = detector.find_evil_twins()
    if not findings:
        print("No potential evil twins detected.")
        return
    print(f"\nPotential evil twin / rogue AP findings: {len(findings)}")
    print_separator(70)
    for f in findings:
        print(f"  SSID: {f['ssid']!r}")
        print(f"    MACs ({f['mac_count']}): {', '.join(f['macs'][:6])}")
        print(f"    Vendors: {', '.join(f['vendors'][:4])}")
        print(f"    Auth modes: {', '.join(f['auth_modes'])}")
        print(f"    Channels: {', '.join(f['channels'])}")
        print(f"    Flags: {'; '.join(f['suspicion_flags'])}")
        print()


def print_time_analysis(analyzer: TimeAnalyzer) -> None:
    stats = analyzer.get_stats()
    if not stats:
        print("No parseable timestamps found.")
        return
    print(f"\n  Total timestamped records: {stats['total_timestamped']}")
    print(f"  Peak activity hour: {stats['peak_hour']:02d}:00 ({stats['peak_hour_count']} networks)")
    print(f"  Most active date:   {stats['peak_date']} ({stats['peak_date_count']} networks)")
    if stats.get("by_hour"):
        print("\n  Hourly distribution:")
        for hour in sorted(stats["by_hour"]):
            bar = "█" * min(40, stats["by_hour"][hour] // max(1, stats["total_timestamped"] // 40))
            print(f"    {hour:02d}:00  {bar} {stats['by_hour'][hour]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _ask(prompt: str, default: str = "") -> str:
    try:
        val = input(prompt).strip()
    except EOFError:
        return default
    return val or default


def _ask_float(prompt: str) -> Optional[float]:
    while True:
        v = _ask(prompt)
        if v == "":
            return None
        try:
            return float(v)
        except ValueError:
            print("  Enter a number, or leave blank to skip.")


def _ask_yn(prompt: str, default: bool = False) -> bool:
    v = _ask(f"{prompt} ({'Y/n' if default else 'y/N'}): ").lower()
    return default if v == "" else v.startswith("y")


def _resolve_files(args) -> list[str]:
    if args.files:
        return [str(f) for f in args.files]
    found = sorted(str(p) for p in Path(".").glob("*.csv"))
    if found:
        print("CSV files in this folder:")
        for f in found:
            print(f"  {f}")
        entry = _ask("Use these? Press Enter for yes, or type a filename or pattern like *.csv: ")
    else:
        entry = _ask("No CSV files here. Type a filename or pattern like *.csv: ")
    if entry:
        globbed = sorted(str(p) for p in Path(".").glob(entry))
        return globbed or ([entry] if os.path.exists(entry) else [])
    return found


MENU = """
What do you want to do?
   1) Clean this drive for sharing   (remove your home + your devices)
   2) Who followed me?               (same device seen at many stops)
   3) Encryption breakdown
   4) Channel usage
   5) Evil twins / rogue APs
   6) Device makers (vendors)
   7) Busiest times
   8) Merge several drives into one
   9) Export to a map / JSON / CSV
   0) Quit
"""


def _home_leak(records: list[WiGLERecord], lat: float, lon: float, radius_m: float) -> int:
    lf = LocationFilter(lat, lon, radius_m / _M_PER_DEG)
    return sum(1 for r in records if lf.is_here(r))


def _warn_home_leak(count: int, radius_m: float) -> None:
    print(f"\n!! WARNING: {count} network(s) within ~{int(radius_m)} m of your home are still in "
          f"this output. Use --exclude-home (menu option 1) before sharing or uploading.")


_REMOVAL_LABELS = {
    "home": "near your home location",
    "blocked_mac": "matched a blocked MAC",
    "blocked_ssid": "matched a blocked SSID",
    "blocked_pattern": "matched a blocked name pattern",
}


def _print_removal_stats(stats: Counter, kept: int, total: int) -> None:
    removed = sum(stats.values())
    print(f"\nResults: kept {kept} of {total} records, removed {removed}.")
    for reason, n in stats.most_common():
        print(f"  {n:>7}  {_REMOVAL_LABELS.get(reason, reason)}")


def _warn_home_nomatch(removed_home: int, total: int) -> None:
    if total and removed_home == 0:
        print("\n!! Home removed 0 records. Check your latitude/longitude — a missing minus "
              "sign on longitude, or swapped lat/lon, puts the point on the wrong side of the planet.")


def _setup_privacy(processor: "WiGLEProcessor") -> Optional[tuple]:
    if os.path.exists("filter.json"):
        processor.set_filter_config("filter.json")
        c = processor.filter_config
        print("\nUsing your saved privacy settings (filter.json).")
        if c.latitude is not None and c.longitude is not None:
            return (c.latitude, c.longitude, c.radius_m)
        return None

    if not _ask_yn("\nSet up what to keep private now? (recommended before sharing)", True):
        return None
    print("Saved to filter.json for next time.")
    home = None
    lat = _ask_float("Your home latitude (blank to skip): ")
    lon = _ask_float("Your home longitude (blank to skip): ") if lat is not None else None
    radius = 150.0
    if lat is not None and lon is not None:
        radius = _ask_float("Hide everything within how many meters (default 150)? ") or 150.0
        home = (lat, lon, radius)
    macs = [m.strip().upper() for m in
            _ask("MAC addresses of your own devices, comma-separated (blank to skip): ").split(",") if m.strip()]
    ssids = [s.strip() for s in
             _ask("Names (SSIDs) of your own networks, comma-separated (blank to skip): ").split(",") if s.strip()]
    cfg = {
        "latitude": lat if lat is not None else 0.0,
        "longitude": lon if lon is not None else 0.0,
        "radius_m": radius,
        "blocked_macs": macs,
        "blocked_ssids": ssids,
        "blocked_patterns": [],
    }
    with open("filter.json", "w") as fh:
        json.dump(cfg, fh, indent=2)
    print("Saved filter.json.")
    processor.set_filter_config("filter.json")
    return home


def _clean_drive(processor: "WiGLEProcessor", files: list[str], home: Optional[tuple]) -> None:
    location_mode = "not_here" if home else None
    if home:
        processor.set_location_filter(home[0], home[1], home[2] / _M_PER_DEG)
    out_dir = _ask("Save cleaned copies where (default ./cleaned): ", "./cleaned")
    stats: Counter = Counter()
    kept = total = 0
    for f in files:
        headers, recs = processor.read_csv_file(f)
        filtered = processor.filter_records(recs, location_mode, stats)
        kept += len(filtered)
        total += len(recs)
        out_file = Path(out_dir) / Path(f).name
        processor.write_csv_file(str(out_file), headers, filtered)
        print(f"Cleaned {f} -> {out_file} ({len(filtered)}/{len(recs)} kept)")
    _print_removal_stats(stats, kept, total)
    if location_mode == "not_here":
        _warn_home_nomatch(stats["home"], total)
    print("Upload the files in that folder, not your originals.")


def _menu_export(records: list[WiGLERecord]) -> None:
    fmt = _ask("Format — (k)ml / (g)eojson / (j)son / (c)sv: ").lower()
    if fmt.startswith("k"):
        export_kml(records, _ask("Output file (default out.kml): ", "out.kml"))
    elif fmt.startswith("g"):
        export_geojson(records, _ask("Output file (default out.geojson): ", "out.geojson"))
    elif fmt.startswith("j"):
        export_json(records, _ask("Output file (default out.json): ", "out.json"))
    elif fmt.startswith("c"):
        export_csv(records, _ask("Output file (default out.csv): ", "out.csv"))
    else:
        print("  Unknown format.")


def interactive_session(args) -> None:
    files = _resolve_files(args)
    if not files:
        print("No CSV files found. Nothing to do.")
        return

    print(f"\nLoading {len(files)} file(s): {', '.join(Path(f).name for f in files)}")
    processor = WiGLEProcessor()
    all_records: list[WiGLERecord] = []
    for f in files:
        _, recs = processor.read_csv_file(f)
        all_records.extend(recs)
    print(f"Loaded {len(all_records)} records.")
    if not all_records:
        return

    session_home = _setup_privacy(processor)

    while True:
        print(MENU)
        try:
            choice = input("Choice: ").strip().lower()
        except EOFError:
            print()
            return
        if choice in ("0", "q", "quit", "exit"):
            print("Done.")
            return
        if choice == "1":
            _clean_drive(processor, files, session_home)
        elif choice == "2":
            n = _ask_float("Minimum unique locations (default 3): ")
            det = CreepDetector()
            for r in all_records:
                det.add_record(r)
            print_creeps(det, all_records, min_locations=int(n) if n else 3)
        elif choice == "3":
            a = EncryptionAnalyzer()
            for r in all_records:
                a.add_record(r)
            print_encryption(a)
        elif choice == "4":
            a = ChannelAnalyzer()
            for r in all_records:
                a.add_record(r)
            print_channels(a)
        elif choice == "5":
            d = RogueDetector()
            for r in all_records:
                d.add_record(r)
            print_evil_twins(d)
        elif choice == "6":
            a = VendorAnalyzer()
            for r in all_records:
                a.add_record(r)
            print_vendor_stats(a)
        elif choice == "7":
            a = TimeAnalyzer()
            for r in all_records:
                a.add_record(r)
            print_time_analysis(a)
        elif choice == "8":
            out = _ask("Output file (default merged.csv): ", "merged.csv")
            merged = processor.merge_and_dedup(all_records)
            header = ["MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
                      "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"]
            processor.write_csv_file(out, header, merged)
            print(f"Merged/deduped: {len(merged)} unique -> {out} "
                  f"({len(all_records) - len(merged)} duplicates removed)")
            if session_home:
                leak = _home_leak(merged, *session_home)
                if leak:
                    _warn_home_leak(leak, session_home[2])
        elif choice == "9":
            _menu_export(all_records)
            if session_home:
                leak = _home_leak(all_records, *session_home)
                if leak:
                    _warn_home_leak(leak, session_home[2])
        else:
            print("  Unknown option.")
        _ask("\nPress Enter to continue...")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WiGLE CSV Processor — wardriving analysis toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__[__doc__.find("Flags combine"):] if "Flags combine" in __doc__ else None,
    )
    parser.add_argument("files", nargs="*", help="WiGLE CSV files to process")
    parser.add_argument("-i", "--interactive", "--menu", dest="menu", action="store_true",
                        help="Interactive walkthrough menu (default when no operation is given)")

    ops = parser.add_argument_group("operations")
    ops.add_argument("--scrub", action="store_true", help="Write cleaned copies to ./cleaned/ (home/own devices removed)")
    ops.add_argument("--creeps", action="store_true", help="Find MACs seen at multiple locations")
    ops.add_argument("--encryption", action="store_true", help="Show encryption type breakdown")
    ops.add_argument("--channels", action="store_true", help="Show channel usage statistics")
    ops.add_argument("--evil-twins", action="store_true", help="Heuristic evil-twin / rogue AP detection")
    ops.add_argument("--vendor-stats", action="store_true", help="OUI vendor breakdown")
    ops.add_argument("--time-analysis", action="store_true", help="Time-on-air / temporal analysis")

    geo = parser.add_argument_group("location (hide where you live / were)")
    geo.add_argument("--exclude-home", "--not-here", dest="not_here", action="store_true",
                     help="Drop networks near --lat/--lon (hide your home before sharing)")
    geo.add_argument("--lat", type=float, help="Your reference latitude (e.g. home)")
    geo.add_argument("--lon", type=float, help="Your reference longitude (e.g. home)")

    flt = parser.add_argument_group("filtering")
    flt.add_argument("--config", help="JSON filter config file (blocked MACs/SSIDs/patterns)")
    flt.add_argument("--create-config", metavar="FILE", help="Generate a sample filter.json")
    flt.add_argument("--min-locs", type=int, default=3,
                     help="Minimum unique locations for creep detection (default: 3)")
    flt.add_argument("--top", type=int, default=20, help="Number of top results to show (default: 20)")

    out = parser.add_argument_group("output")
    out.add_argument("--output-dir", default="./cleaned", help="Folder for cleaned copies (default: ./cleaned)")
    out.add_argument("--merge", metavar="FILE", help="Merge all inputs, dedup, write to FILE")
    out.add_argument("--export-csv", metavar="FILE", help="Export all (filtered) records as CSV")
    out.add_argument("--export-json", metavar="FILE", help="Export all records as JSON")
    out.add_argument("--export-geojson", metavar="FILE", help="Export as GeoJSON FeatureCollection")
    out.add_argument("--export-kml", metavar="FILE", help="Export as KML (Google Earth)")

    args = parser.parse_args()

    if args.create_config:
        FilterConfig().create_sample_config(args.create_config)
        print("Edit it with your blocked MACs, SSIDs, and patterns, then re-run.")
        return

    op_selected = any([
        args.scrub, args.creeps, args.encryption, args.channels, args.evil_twins,
        args.vendor_stats, args.time_analysis, args.merge,
        args.export_csv, args.export_json, args.export_geojson, args.export_kml,
    ])
    if args.menu or not op_selected:
        interactive_session(args)
        return

    config_file = args.config
    if not config_file:
        config_file = "filter.json"

    config_to_use: Optional[str] = None
    if not os.path.exists(config_file):
        print(f"Config file '{config_file}' not found.")
        try:
            response = input(f"Create a sample {config_file}? (y/n): ").strip().lower()
        except EOFError:
            response = "n"
        if response == "y":
            FilterConfig().create_sample_config(config_file)
            print("Edit it, then re-run.")
            return
        else:
            print(f"Proceeding without MAC/SSID filtering.")
    else:
        print(f"Using config: {config_file}")
        config_to_use = config_file

    input_files: list[str] = [str(f) for f in args.files]
    if not input_files:
        input_files = [str(p) for p in Path(".").glob("*.csv")]

    if not input_files:
        print("No CSV files found. Use --help for usage.")
        return

    processor = WiGLEProcessor()

    if args.lat is not None and args.lon is not None:
        processor.set_location_filter(args.lat, args.lon, 150.0 / _M_PER_DEG)

    if config_to_use:
        processor.set_filter_config(config_to_use)
        cfg = processor.filter_config
        print(f"Config: lat={cfg.latitude}, lon={cfg.longitude}, radius={cfg.radius_m}m")
        if cfg.latitude is not None and cfg.longitude is not None:
            if processor.location_filter is None:
                processor.set_location_filter(cfg.latitude, cfg.longitude, cfg.radius_m / _M_PER_DEG)
            print("Location filter set from config.")

    all_records: list[WiGLERecord] = []
    canonical_headers: list[str] = []
    scrub_stats: Counter = Counter()
    scrub_kept = 0
    scrub_total = 0

    for filename in input_files:
        print(f"Reading {filename}...")
        headers, records = processor.read_csv_file(filename)
        if headers and not canonical_headers:
            canonical_headers = headers
        all_records.extend(records)

        if args.scrub:
            location_mode = "not_here" if args.not_here else None
            filtered = processor.filter_records(records, location_mode, scrub_stats)
            scrub_kept += len(filtered)
            scrub_total += len(records)
            out_file = Path(args.output_dir) / Path(filename).name
            processor.write_csv_file(str(out_file), headers, filtered)
            print(f"Scrubbed {filename} -> {out_file} ({len(filtered)}/{len(records)} records)")

    if args.scrub:
        _print_removal_stats(scrub_stats, scrub_kept, scrub_total)
        if args.not_here and processor.location_filter is not None:
            _warn_home_nomatch(scrub_stats["home"], scrub_total)

    print(f"\nTotal records loaded: {len(all_records)}")

    if args.merge:
        merged = processor.merge_and_dedup(all_records)
        header_line = canonical_headers if canonical_headers else [
            "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
            "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
        ]
        processor.write_csv_file(args.merge, header_line, merged)
        print(f"Merged/deduped: {len(merged)} unique records -> {args.merge}")
        print(f"  Duplicates removed: {len(all_records) - len(merged)}")

    if args.export_csv:
        export_csv(all_records, args.export_csv)

    if args.export_json:
        export_json(all_records, args.export_json)

    if args.export_geojson:
        export_geojson(all_records, args.export_geojson)

    if args.export_kml:
        export_kml(all_records, args.export_kml)

    if args.creeps:
        print("\nRunning creep detection...")
        detector = CreepDetector()
        for record in all_records:
            detector.add_record(record)
        print_creeps(detector, all_records, min_locations=args.min_locs, top=args.top)

    if args.encryption:
        print("\nAnalyzing encryption types...")
        enc_analyzer = EncryptionAnalyzer()
        for record in all_records:
            enc_analyzer.add_record(record)
        print_encryption(enc_analyzer)

    if args.channels:
        print("\nAnalyzing channel usage...")
        ch_analyzer = ChannelAnalyzer()
        for record in all_records:
            ch_analyzer.add_record(record)
        print_channels(ch_analyzer, top_n=args.top)

    if args.evil_twins:
        print("\nRunning evil-twin / rogue AP heuristics...")
        rogue = RogueDetector()
        for record in all_records:
            rogue.add_record(record)
        print_evil_twins(rogue)

    if args.vendor_stats:
        print("\nVendor (OUI) analysis...")
        vendor_a = VendorAnalyzer()
        for record in all_records:
            vendor_a.add_record(record)
        print_vendor_stats(vendor_a, top_n=args.top)

    if args.time_analysis:
        print("\nTime-on-air / temporal analysis...")
        time_a = TimeAnalyzer()
        for record in all_records:
            time_a.add_record(record)
        print_time_analysis(time_a)

    home_lat = home_lon = None
    home_r = 150.0
    if args.lat is not None and args.lon is not None:
        home_lat, home_lon = args.lat, args.lon
    elif processor.filter_config and processor.filter_config.latitude is not None \
            and processor.filter_config.longitude is not None:
        home_lat = processor.filter_config.latitude
        home_lon = processor.filter_config.longitude
        home_r = processor.filter_config.radius_m

    shared_output = bool(
        args.merge or args.export_csv or args.export_json
        or args.export_geojson or args.export_kml
        or (args.scrub and not args.not_here)
    )
    if home_lat is not None and shared_output:
        leak = _home_leak(all_records, home_lat, home_lon, home_r)
        if leak:
            _warn_home_leak(leak, home_r)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(130)
