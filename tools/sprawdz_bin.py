#!/usr/bin/env python3
"""sprawdz_bin.py - czy plik .bin nadaje sie do slotu ota_0 ladowarki KORONA.

Uzycie:
  python3 tools/sprawdz_bin.py plik.bin                 czytelny raport
  python3 tools/sprawdz_bin.py plik.bin --json          wynik jako JSON (na stdout)
  python3 tools/sprawdz_bin.py plik.bin --wycinek app.bin
        ze SCALONEGO obrazu (bootloader+tablica+aplikacja) wycina sam obraz aplikacji

Kod wyjscia: 0 = nadaje sie, 1 = nie nadaje sie, 2 = zly plik / brak pliku.

Co sprawdza:
  * czysty obraz aplikacji ESP32 (magic 0xE9 na bajcie 0)  albo  scalony obraz flasha
    (0xE9 pod 0x1000 = bootloader, tablica partycji 0xAA 0x50 pod 0x8000) - ze scalonego
    wycina partycje app pod 0x10000 i dalej ocenia wycinek;
  * dlugosc obrazu liczona z naglowka (segmenty + suma kontrolna + opcjonalny SHA-256),
    a nie z rozmiaru pliku - dlatego wycinek ze scalonego obrazu jest bajt w bajt tym,
    co wyszlo z kompilatora (test: portal/obrazy/cyd24/korona-cyd24-scalony.bin -> loader.bin);
  * rozmiar <= 2 555 904 B (slot ota_0 = 0x270000);
  * uklad docelowy z naglowka (chip_id): musi byc ESP32, nie S2/S3/C3;
  * esp_app_desc_t (offset 0x20): project_name, version, idf_ver, data kompilacji.
    UWAGA: rdzen Arduino wpisuje tu "arduino-lib-builder" i wersje rdzenia, wiec nazwa
    programu MUSI przyjsc z meta.json - z binarki jej nie ma.

Czego NIE sprawdza (bo sie nie da):
  * wymogu "Model B" (kasowanie otadata na poczatku setup(), albo verifyRollbackLater()).
    To kod maszynowy, nie tekst - w binarce nie ma czego szukac. Jedyny test to uruchomic
    program pod KORONA i nacisnac RST: musi wrocic do menu. Raport mowi to wprost.
"""
import sys, os, json, hashlib, struct

OTA0_SIZE = 0x270000          # 2 555 904 B - slot ota_0 z loader/partitions_loader.csv
OFF_BOOT, OFF_PART, OFF_APP = 0x1000, 0x8000, 0x10000
ESP_MAGIC = 0xE9
PART_MAGIC = b"\xaa\x50"
APP_DESC_MAGIC = 0xABCD5432
CHIPS = {0x0000: "ESP32", 0x0002: "ESP32-S2", 0x0005: "ESP32-C3", 0x0009: "ESP32-S3",
         0x000C: "ESP32-C2", 0x000D: "ESP32-C6", 0x0010: "ESP32-H2", 0x0012: "ESP32-P4"}


def _cstr(b):
    return b.split(b"\0", 1)[0].decode("utf-8", "replace")


def image_length(data):
    """Dlugosc obrazu aplikacji ESP32 policzona z naglowka. None, gdy naglowek nie trzyma sie kupy."""
    if len(data) < 24 or data[0] != ESP_MAGIC:
        return None
    nseg, hash_appended = data[1], data[23]
    pos = 24
    for _ in range(nseg):
        if pos + 8 > len(data):
            return None
        _addr, ln = struct.unpack_from("<II", data, pos)
        pos += 8 + ln
        if pos > len(data) or ln > 16 * 1024 * 1024:
            return None
    pos += 1                              # bajt sumy kontrolnej
    pos = (pos + 15) & ~15                # dopelnienie do 16 B (suma jest ostatnim bajtem)
    if hash_appended == 1:
        pos += 32                         # SHA-256 obrazu
    return pos if pos <= len(data) else None


def app_desc(img):
    """esp_app_desc_t z offsetu 0x20 (pierwszy segment .flash.rodata zaczyna sie od niego)."""
    if len(img) < 0x20 + 256:
        return None
    magic, = struct.unpack_from("<I", img, 0x20)
    if magic != APP_DESC_MAGIC:
        return None
    d = img[0x20:]
    return {
        "project_name": _cstr(d[0x30:0x50]),
        "version":      _cstr(d[0x10:0x30]),
        "time":         _cstr(d[0x50:0x60]),
        "date":         _cstr(d[0x60:0x70]),
        "idf_ver":      _cstr(d[0x70:0x90]),
    }


def parse_partitions(data):
    """Tablica partycji pod 0x8000: wpisy po 32 B (magic AA 50, typ, podtyp, offset, rozmiar, etykieta[16], flagi)."""
    parts, pos = [], OFF_PART
    while pos + 32 <= len(data) and pos < OFF_PART + 0xC00:
        e = data[pos:pos + 32]
        if e[:2] != PART_MAGIC:
            break                         # 0xEBEB = wpis MD5, 0xFFFF = koniec
        typ, sub = e[2], e[3]
        off, size = struct.unpack_from("<II", e, 4)
        parts.append({"typ": typ, "podtyp": sub, "offset": off, "rozmiar": size, "etykieta": _cstr(e[12:28])})
        pos += 32
    return parts


def analyze(path):
    r = {"plik": os.path.basename(path), "sciezka": path, "ok": False, "bledy": [], "ostrzezenia": [], "uwagi": []}
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as e:
        r["bledy"].append(f"nie mozna odczytac pliku: {e}")
        return r, None
    r["rozmiar_pliku"] = len(data)
    r["sha256_pliku"] = hashlib.sha256(data).hexdigest()

    img = None
    if len(data) >= 24 and data[0] == ESP_MAGIC:
        r["rodzaj"] = "czysty"
    elif len(data) > OFF_APP and data[OFF_BOOT] == ESP_MAGIC and data[OFF_PART:OFF_PART + 2] == PART_MAGIC:
        r["rodzaj"] = "scalony"
        parts = parse_partitions(data)
        r["partycje"] = parts
        apps = [p for p in parts if p["typ"] == 0]
        app = next((p for p in apps if p["offset"] == OFF_APP), apps[0] if apps else None)
        if app is None:
            r["bledy"].append("scalony obraz bez partycji typu app w tablicy pod 0x8000")
            return r, None
        if app["offset"] != OFF_APP:
            r["ostrzezenia"].append(f"partycja app nie zaczyna sie pod 0x10000 (jest 0x{app['offset']:X})")
        seg = data[app["offset"]:app["offset"] + app["rozmiar"]]
        if len(seg) < 24 or seg[0] != ESP_MAGIC:
            r["bledy"].append(f"pod 0x{app['offset']:X} (partycja '{app['etykieta']}') nie ma obrazu aplikacji (brak 0xE9)")
            return r, None
        r["wycieto_z"] = {"etykieta": app["etykieta"], "offset": app["offset"], "rozmiar_partycji": app["rozmiar"]}
        img = seg
        r["uwagi"].append("scalony obraz flasha: do KORONY idzie tylko wycieta aplikacja, bootloader i tablica partycji sa ignorowane")
    else:
        r["rodzaj"] = "nieznany"
        r["bledy"].append("to nie jest obraz ESP32: brak 0xE9 na bajcie 0 (czysty obraz) ani pod 0x1000 + tablicy AA50 pod 0x8000 (scalony)")
        return r, None
    if img is None:
        img = data

    ln = image_length(img)
    if ln is None:
        r["ostrzezenia"].append("naglowek obrazu nie trzyma sie kupy (segmenty wykraczaja poza plik) - przyjmuje rozmiar pliku")
        if r["rodzaj"] == "scalony":
            img = img.rstrip(b"\xff")     # awaryjnie: obcinamy wypelnienie 0xFF z konca partycji
        ln = len(img)
    else:
        if r["rodzaj"] == "scalony":
            img = img[:ln]
        elif ln < len(img):
            r["uwagi"].append(f"plik ma {len(img) - ln} B za obrazem (wypelnienie) - nieszkodliwe")
    r["segmentow"] = img[1]
    r["sha256_appended"] = bool(img[23] == 1)
    chip = struct.unpack_from("<H", img, 12)[0]
    r["chip"] = CHIPS.get(chip, f"nieznany 0x{chip:04X}")
    if chip != 0:
        r["bledy"].append(f"obraz dla ukladu {r['chip']} - CYD ma zwykly ESP32, to sie nie uruchomi")
    r["rozmiar"] = len(img)
    r["sha256"] = hashlib.sha256(img).hexdigest()
    r["limit_ota0"] = OTA0_SIZE
    if len(img) > OTA0_SIZE:
        r["bledy"].append(f"za duzy: {len(img)} B > {OTA0_SIZE} B (slot ota_0); o {len(img) - OTA0_SIZE} B")
    else:
        r["zapas"] = OTA0_SIZE - len(img)
    d = app_desc(img)
    r["app_desc"] = d
    if d is None:
        r["ostrzezenia"].append("brak esp_app_desc_t pod 0x20 (to nie jest obraz z ESP-IDF/Arduino?)")
    elif d["project_name"] in ("arduino-lib-builder", ""):
        r["uwagi"].append("app_desc z rdzenia Arduino (project_name='arduino-lib-builder') - nazwe i wersje programu bierzemy z meta.json")
    if r["sha256_appended"]:
        calc = hashlib.sha256(img[:-32]).digest()
        if calc != img[-32:]:
            r["bledy"].append("SHA-256 doklejony do obrazu nie zgadza sie z trescia - plik uszkodzony albo zle wyciety")
        else:
            r["uwagi"].append("doklejony SHA-256 obrazu zgadza sie")
    r["model_b"] = "NIE DA SIE SPRAWDZIC Z BINARKI: uruchom program pod KORONA i nacisnij RST - musi wrocic do menu. Bez Modelu B (kasowanie otadata w setup() albo verifyRollbackLater()) plytke odzyskasz tylko po USB."
    r["ok"] = not r["bledy"]
    return r, img


def report(r):
    L = []
    L.append(f"== {r['plik']} ==")
    if "rodzaj" in r:
        L.append(f"rodzaj:        {r['rodzaj']}" + (f"  (wycieto '{r['wycieto_z']['etykieta']}' @0x{r['wycieto_z']['offset']:X})" if r.get("wycieto_z") else ""))
    if "rozmiar" in r:
        L.append(f"rozmiar obrazu: {r['rozmiar']} B  (limit ota_0 {r['limit_ota0']} B" + (f", zapas {r['zapas']} B)" if "zapas" in r else ", ZA DUZY)"))
        L.append(f"sha256 obrazu: {r['sha256']}")
        L.append(f"uklad:         {r['chip']}   segmentow: {r['segmentow']}   sha256 doklejony: {'tak' if r['sha256_appended'] else 'nie'}")
    if r.get("rodzaj") == "scalony":
        L.append(f"plik (scalony): {r['rozmiar_pliku']} B  sha256 {r['sha256_pliku']}")
    d = r.get("app_desc")
    if d:
        L.append(f"app_desc:      project='{d['project_name']}' version='{d['version']}' idf='{d['idf_ver']}' build={d['date']} {d['time']}")
    for x in r["bledy"]:
        L.append(f"BLAD:          {x}")
    for x in r["ostrzezenia"]:
        L.append(f"UWAGA:         {x}")
    for x in r["uwagi"]:
        L.append(f"info:          {x}")
    if "model_b" in r:
        L.append(f"Model B:       {r['model_b']}")
    L.append("WYNIK:         " + ("NADAJE SIE (format) - Model B sprawdz recznie" if r["ok"] else "NIE NADAJE SIE"))
    return "\n".join(L)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    out = None
    if "--wycinek" in argv:
        i = argv.index("--wycinek")
        if i + 1 >= len(argv):
            print("--wycinek wymaga sciezki", file=sys.stderr); return 2
        out = argv[i + 1]
        args = [a for a in args if a != out]
    if len(args) != 1:
        print(__doc__); return 2
    r, img = analyze(args[0])
    if out and img is not None:
        with open(out, "wb") as fh:
            fh.write(img)
        r["wycinek"] = out
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(report(r))
        if out and img is not None:
            print(f"zapisano wycinek: {out} ({len(img)} B)")
    if "rodzaj" not in r or r["rodzaj"] == "nieznany":
        return 2
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
