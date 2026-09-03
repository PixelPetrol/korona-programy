#!/usr/bin/env python3
"""Generuje katalog.json (format v2, per plytka) z plikow bin/<plytka>/*.bin i tabeli META.

Uzycie (z katalogu repo):  python3 tools/katalog.py
Rozmiary sa czytane z plikow; opisy/wersje z tabeli ponizej. Plik bez wpisu w META
dostaje nazwe z pliku i pusty opis (i ostrzezenie na stderr).
"""
import json, os, sys, hashlib

PLYTKI = [
    ("cyd24", 'CYD 2.4" (ESP32-2432S024)'),
    ("cyd28", 'CYD 2.8" (ESP32-2432S028R)'),
]
# (plytka, plik) albo plik -> dict(nazwa, opis, wersja, kategoria, autor, info); wpis z plytka ma pierwszenstwo.
# kategoria: "autorskie" (programy KORONA / Piotra) albo "zewnetrzne" (porty cudzych projektow).
# Plik bez wpisu -> nie trafia do katalogu (zeby nie wystawiac niesprawdzonych binarek).
A, Z = "autorskie", "zewnetrzne"
def m(nazwa, opis, wersja, kategoria, autor, info=""):
    return dict(nazwa=nazwa, opis=opis, wersja=wersja, kategoria=kategoria, autor=autor, info=info)
META = {
    "radar-pion.bin":   m("SkyCYD 4.4.1 pion",   "radar ADS-B, samoloty wokol domu", "4.4.1", A, "Piotr Korona",
                          "Radar lotniczy na CYD: pozycje z adsb.lol przez wlasny Worker, mapa, pogoda, zdjecia samolotow. Ekran pionowo 240x320. Konfiguracja przez portal WiFi (AP przy pierwszym starcie)."),
    "radar-poziom.bin": m("SkyCYD 4.4.1 poziom", "radar ADS-B, ekran poziomo",       "4.4.1", A, "Piotr Korona",
                          "Ta sama aplikacja co SkyCYD pion, ale w orientacji poziomej 320x240 (oryginalny uklad SkyCYD). Kalibracja dotyku osobna od wersji pionowej."),
    "marauder.bin":     m("Marauder",        "audyt WiFi / BLE",                 "1.4.3", Z, "justcallmekoko / Fr4nkFletcher",
                          "ESP32 Marauder w profilu CYD_24: skan sieci i urzadzen BLE, sniffing, testy WLASNEJ sieci. Ustawienia trzyma w SPIFFS - dzieki migawkom KORONA zostaja miedzy startami."),
    "bruce.bin":        m("Bruce (LITE)",    "pentest toolkit WiFi / BLE / IR / RF", "lite", Z, "pr3y",
                          "Bruce - wieloprotokolowy 'pentest toolkit' (WiFi, BLE, IR, RF), wariant LITE. Env KORONA_CYD24: poprawione kolory (INVON). DOTYK: kalibracja jest osobna dla kazdej orientacji ekranu - pierwszy start prosi o cztery rogi w ukladzie poziomym, a po zmianie Config > Orientation Bruce pyta o nie raz dla nowego ukladu i juz go pamieta (KORONA trzyma to w migawce). Bez tego dotyk w pionie nie trafial wcale: TFT_eSPI liczy dotyk z granic kalibracji, ale z wymiarow biezacej rotacji, wiec kalibracja z poziomu dawala w pionie rozciagniecie zamiast obrotu."),
    ("cyd28", "radar-pion.bin"):   m("SkyCYD 4.4.1 pion",   "radar ADS-B; 2.8\" NIETESTOWANE", "4.4.1", A, "Piotr Korona", "Wersja dla CYD 2.8\" (2432S028R) - zbudowana, nie sprawdzona na sprzecie."),
    ("cyd28", "radar-poziom.bin"): m("SkyCYD 4.4.1 poziom", "radar ADS-B; 2.8\" NIETESTOWANE", "4.4.1", A, "Piotr Korona", "Wersja dla CYD 2.8\" (2432S028R) - zbudowana, nie sprawdzona na sprzecie."),
    "btspeaker.bin":    m("BT Speaker",      "glosnik Bluetooth A2DP, DAC 8-bit; NIETESTOWANY", "1.0.0", Z, "pschatzmann (ESP32-A2DP)",
                          "Odbiornik A2DP na bibliotekach ESP32-A2DP i arduino-audio-tools (pschatzmann); szkic KORONA to tylko warstwa ekranu i dotyku. Telefon laczy sie z 'KORONA CYD' i gra przez wbudowany 8-bit DAC na GPIO26 (wzmacniacz, zlacze glosnika). Ekran pionowy: stan, tytul/wykonawca (AVRCP), glosnosc; dotyk = prev/pauza/next/glosnosc. Jakosc ogranicza 8-bitowy DAC - gadzet, nie hi-fi. WiFi wylaczone. Zrodlo: porty/btspeaker (szkic MIT; biblioteka audio GPL-3.0 -> binarka GPL)."),
    "openhasp.bin":     m("openHASP",        "panel dotykowy Home Assistant; NIETESTOWANY", "0.7.0", Z, "Francis Van Roie (fvanroie)",
                          "openHASP zamienia CYD w panel dotykowy Home Assistant: strony/widgety LVGL z pages.jsonl, sterowanie MQTT. Pierwszy start: AP 'HASP-xxxxxx' haslo 'haspadmin', kalibracja 4 rogow, potem WiFi i MQTT przez www 192.168.4.1. Ekran poziomo; rotacje i inwersje zmienia sie w Configuration - Display."),
    "nerdminer.bin":    m("NerdMiner v2",    "kopacz-loteria BTC + kurs i bloki; NIETESTOWANY", "1.8.3", Z, "BitMaker-hub",
                          "Solo-miner Bitcoin na ESP32 (~60 kH/s - loteria i gadzet statystyczny). Pierwszy start: AP 'NerdMinerAP', haslo 'MineYourCoins', portal 192.168.4.1 (pool, adres BTC, jasnosc). Po zapisie ustawien plytka wraca do ladowarki - uruchom program ponownie, ustawienia zostaja dzieki migawce."),
    "pogoda.bin":       m("Pogoda",          "prognoza pogody, Open-Meteo bez klucza; NIETESTOWANY", "0.1.36", Z, "nicholaswilde",
                          "Stacja pogodowa na LVGL: duza temperatura, ikona, prognoza 3-dniowa, wykres godzinowy, motywy. Dane z Open-Meteo bez klucza API - lokalizacja po IP albo wspolrzedne. Pierwszy start: AP 'cyd-weather-station-XXXX' (otwarty), portal 192.168.4.1 (WiFi, lokalizacja, strefa); potem http://cyd-weather-station.local/. Po 'zapisz i restart' plytka wraca do ladowarki i autostart wznawia aplikacje."),
    "esp32div.bin":     m("ESP32-DIV",       "multitool WiFi/BLE/RF; ZAWIESZA SIE - do naprawy", "dev",   Z, "cifertech",
                          "ESP32-DIV (HaleHound): skaner WiFi/BLE, deauth, RF. Build z 02.09 zawiesza sie na ekranie startowym z niebieska dioda i nie reaguje na dotyk - prawdopodobnie zla konfiguracja dotyku/partycji dla CYD 2.4. Zostaje w sklepie do czasu naprawy (plan w SPEC-LADOWARKA.md)."),
}

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = {"sklep": "KORONA", "wersja": 2, "plytki": []}
for pid, pname in PLYTKI:
    d = os.path.join(root, "bin", pid)
    progs = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".bin"): continue
            p = os.path.join(d, f)
            meta = META.get((pid, f), META.get(f))
            if meta is None: print("UWAGA: brak META, pomijam", pid, f, file=sys.stderr); continue
            with open(p, "rb") as fh: data = fh.read()
            if data[:1] != b"\xe9": print("UWAGA: zly magic (nie obraz ESP32):", p, file=sys.stderr)
            e = {"plik": f"bin/{pid}/{f}", "rozmiar": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            e.update(meta)
            progs.append(e)
    out["plytki"].append({"id": pid, "nazwa": pname, "programy": progs})

with open(os.path.join(root, "katalog.json"), "w") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2); fh.write("\n")
print("katalog.json:", sum(len(p["programy"]) for p in out["plytki"]), "programow")
