#!/usr/bin/env python3
"""Generate throwaway WiGLE CSVs for trying the processor. No real coordinates:
every point is a small synthetic offset from 0,0 (open ocean)."""
import argparse
import csv
import os

HEADER = ["MAC", "SSID", "AuthMode", "FirstSeen", "Channel", "RSSI",
          "CurrentLatitude", "CurrentLongitude", "AltitudeMeters", "AccuracyMeters", "Type"]
PRE = ("WigleWifi-1.4,appRelease=sample,model=sample,release=1,"
       "device=sample,display=sample,board=sample,brand=sample\n")


def r(mac, ssid, auth, ts, ch, rssi, dlat, dlon, olat, olon, typ="WIFI"):
    return [mac, ssid, auth, ts, ch, rssi,
            f"{olat + dlat:.6f}", f"{olon + dlon:.6f}", "180", "5", typ]


def build(olat, olon):
    day1 = [
        r("00:17:F2:AA:BB:01", "MyHomeWiFi", "[WPA2-PSK-CCMP][ESS]", "2026-05-16 08:14:35", "6", "-42", 0.0001, -0.0001, olat, olon),
        r("E8:9F:80:AA:BB:02", "MyHomeWiFi_5G", "[WPA2-PSK-CCMP][ESS]", "2026-05-16 08:14:36", "149", "-55", -0.0002, 0.0002, olat, olon),
        r("24:A4:3C:00:00:10", "CoffeeShop", "[OPEN]", "2026-05-16 09:01:00", "11", "-70", 0.0219, -0.0002, olat, olon),
        r("94:EB:2C:00:00:11", "CoffeeShop", "[WPA2-PSK-CCMP][ESS]", "2026-05-16 09:01:05", "6", "-72", 0.0220, -0.0003, olat, olon),
        r("44:65:0D:00:00:12", "publicwifi", "[OPEN]", "2026-05-16 09:05:00", "1", "-80", 0.0319, -0.0102, olat, olon),
        r("50:C7:BF:00:00:13", "TP-LINK_5G", "[WPA2-PSK-CCMP][ESS]", "2026-05-16 09:06:00", "36", "-65", 0.0419, -0.0202, olat, olon),
        r("2C:B0:5D:00:00:14", "NETGEAR-Guest", "[WPA-PSK-TKIP][ESS]", "2026-05-16 09:07:00", "44", "-60", 0.0519, -0.0302, olat, olon),
        r("7C:BB:8A:00:00:15", "Echo-Dot", "", "2026-05-16 09:07:30", "0", "-50", 0.0519, -0.0302, olat, olon, "BLE"),
        r("DC:9F:DB:DE:AD:99", "", "", "2026-05-16 09:01:10", "0", "-40", 0.0219, -0.0002, olat, olon),
        r("DC:9F:DB:DE:AD:99", "", "", "2026-05-16 09:05:10", "0", "-42", 0.0319, -0.0102, olat, olon),
        r("DC:9F:DB:DE:AD:99", "", "", "2026-05-16 09:06:10", "0", "-45", 0.0419, -0.0202, olat, olon),
        r("DC:9F:DB:DE:AD:99", "", "", "2026-05-16 09:07:10", "0", "-43", 0.0519, -0.0302, olat, olon),
    ]
    day2 = [
        r("24:A4:3C:00:00:10", "CoffeeShop", "[OPEN]", "2026-05-16 09:01:00", "11", "-70", 0.0219, -0.0002, olat, olon),
        r("FF:FF:FF:00:00:16", "CoffeeShop", "[WPA2-EAP-CCMP][ESS]", "2026-05-17 10:15:00", "149", "-58", 0.0219, -0.0007, olat, olon),
        r("BC:EE:7B:00:00:17", "ASUS_Home", "[WPA3-SAE-CCMP][ESS]", "2026-05-17 10:20:00", "157", "-62", 0.0619, -0.0402, olat, olon),
        r("A0:21:B7:00:00:18", "oldrouter", "[WEP]", "2026-05-17 10:22:00", "3", "-77", 0.0719, -0.0502, olat, olon),
        r("C0:3F:0E:00:00:19", "", "[WPA2-PSK-CCMP][ESS]", "2026-05-17 10:23:00", "6", "-66", 0.0719, -0.0502, olat, olon),
        r("DC:9F:DB:DE:AD:99", "", "", "2026-05-17 10:20:10", "0", "-41", 0.0619, -0.0402, olat, olon),
        r("DC:9F:DB:DE:AD:99", "", "", "2026-05-17 10:22:10", "0", "-44", 0.0719, -0.0502, olat, olon),
        ["34:BE:00:00:00:20", "NoGPSNet", "[WPA2-PSK-CCMP][ESS]", "2026-05-17 10:25:00", "11", "-90",
         "0.000000", "0.000000", "0", "0", "WIFI"],
    ]
    return {"sample_day1.csv": day1, "sample_day2.csv": day2}


def main():
    p = argparse.ArgumentParser(description="Generate throwaway WiGLE sample CSVs (synthetic, no real location).")
    p.add_argument("--out", default=".", help="Output directory (default: current)")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, rows in build(0.0, 0.0).items():
        path = os.path.join(a.out, name)
        with open(path, "w", newline="") as fh:
            fh.write(PRE)
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(rows)
        print(f"wrote {path} ({len(rows)} records)")
    print("Planted: 2 home APs, a device seen at 4+ spots (creep), one SSID on 3 MACs (evil twin), one no-GPS record.")


if __name__ == "__main__":
    main()
