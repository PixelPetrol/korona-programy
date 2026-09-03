#!/usr/bin/env python3
"""Generuje katalog.json (format v2, per plytka) z plikow bin/<plytka>/*.bin i tabeli META
oraz z programow uzytkownikow bin/<plytka>/uzytkownicy/*.bin (META z pliku <nazwa>.meta.json obok bina).

Uzycie (z katalogu repo):  python3 tools/katalog.py
Rozmiary sa czytane z plikow; opisy/wersje z tabeli ponizej (programy sklepu) albo z
<nazwa>.meta.json (programy uzytkownikow - te trafiaja tam automatem z zgloszenia/, patrz
tools/przyjmij_zgloszenia.py). Plik bez META nie trafia do katalogu (ostrzezenie na stderr).

Kategorie: "autorskie" (programy K-OS / Piotra), "zewnetrzne" (porty cudzych projektow
robione tu), "uzytkownicy" (zgloszone przez uzytkownikow przez PR do zgloszenia/).
K-OS <= 0.3.6 zna tylko dwie pierwsze i wszystko, co nie jest "autorskie", pokazuje
w "zewnetrzne" (net.cpp progInCat) - stare wersje zobacza wiec programy uzytkownikow tam.
"""
import json, os, sys, hashlib

PLYTKI = [
    ("cyd24", 'CYD 2.4" (ESP32-2432S024)'),
    ("cyd28", 'CYD 2.8" (ESP32-2432S028R)'),
]
UZYTK_DIR = "uzytkownicy"          # bin/<plytka>/uzytkownicy/<nazwa>.bin + <nazwa>.meta.json
# (plytka, plik) albo plik -> dict(nazwa, opis, wersja, kategoria, autor, info); wpis z plytka ma pierwszenstwo.
# kategoria: "autorskie" (programy K-OS / Piotra) albo "zewnetrzne" (porty cudzych projektow).
# Plik bez wpisu -> nie trafia do katalogu (zeby nie wystawiac niesprawdzonych binarek).
A, Z, U = "autorskie", "zewnetrzne", "uzytkownicy"
def m(nazwa, opis, wersja, kategoria, autor, info=""):
    return dict(nazwa=nazwa, opis=opis, wersja=wersja, kategoria=kategoria, autor=autor, info=info)
META = {
    "radar-pion.bin":   m("SkyCYD 4.4.1 pion",   "radar ADS-B, samoloty wokol domu", "4.4.1", A, "Piotr Korona",
                          "Radar lotniczy na CYD: pozycje z adsb.lol przez wlasny Worker, mapa, pogoda, zdjecia samolotow. Ekran pionowo 240x320. Konfiguracja przez portal WiFi (AP przy pierwszym starcie)."),
    "radar-poziom.bin": m("SkyCYD 4.4.1 poziom", "radar ADS-B, ekran poziomo",       "4.4.1", A, "Piotr Korona",
                          "Ta sama aplikacja co SkyCYD pion, ale w orientacji poziomej 320x240 (oryginalny uklad SkyCYD). Kalibracja dotyku osobna od wersji pionowej."),
    "marauder.bin":     m("Marauder",        "audyt WiFi / BLE",                 "1.4.3", Z, "justcallmekoko / Fr4nkFletcher",
                          "ESP32 Marauder w profilu CYD_24: skan sieci i urzadzen BLE, sniffing, testy WLASNEJ sieci. Ustawienia trzyma w SPIFFS - dzieki migawkom K-OS zostaja miedzy startami."),
    "bruce.bin":        m("Bruce (LITE)",    "pentest toolkit WiFi / BLE / IR / RF", "lite", Z, "pr3y",
                          "Bruce - wieloprotokolowy 'pentest toolkit' (WiFi, BLE, IR, RF), wariant LITE. Env KORONA_CYD24: poprawione kolory (INVON). DOTYK: kalibracja jest osobna dla kazdej orientacji ekranu - pierwszy start prosi o cztery rogi w ukladzie poziomym, a po zmianie Config > Orientation Bruce pyta o nie raz dla nowego ukladu i juz go pamieta (K-OS trzyma to w migawce). Bez tego dotyk w pionie nie trafial wcale: TFT_eSPI liczy dotyk z granic kalibracji, ale z wymiarow biezacej rotacji, wiec kalibracja z poziomu dawala w pionie rozciagniecie zamiast obrotu."),
    ("cyd28", "radar-pion.bin"):   m("SkyCYD 4.4.1 pion",   "radar ADS-B; 2.8\" NIETESTOWANE", "4.4.1", A, "Piotr Korona", "Wersja dla CYD 2.8\" (2432S028R) - zbudowana, nie sprawdzona na sprzecie."),
    ("cyd28", "radar-poziom.bin"): m("SkyCYD 4.4.1 poziom", "radar ADS-B; 2.8\" NIETESTOWANE", "4.4.1", A, "Piotr Korona", "Wersja dla CYD 2.8\" (2432S028R) - zbudowana, nie sprawdzona na sprzecie."),
    "btspeaker.bin":    m("BT Speaker",      "glosnik Bluetooth A2DP, DAC 8-bit; NIETESTOWANY", "1.0.0", Z, "pschatzmann (ESP32-A2DP)",
                          "Odbiornik A2DP na bibliotekach ESP32-A2DP i arduino-audio-tools (pschatzmann); szkic K-OS to tylko warstwa ekranu i dotyku. Telefon laczy sie z 'KORONA CYD' i gra przez wbudowany 8-bit DAC na GPIO26 (wzmacniacz, zlacze glosnika). Ekran pionowy: stan, tytul/wykonawca (AVRCP), glosnosc; dotyk = prev/pauza/next/glosnosc. Jakosc ogranicza 8-bitowy DAC - gadzet, nie hi-fi. WiFi wylaczone. Zrodlo: porty/btspeaker (szkic MIT; biblioteka audio GPL-3.0 -> binarka GPL)."),
    "openhasp.bin":     m("openHASP",        "panel dotykowy Home Assistant; NIETESTOWANY", "0.7.0", Z, "Francis Van Roie (fvanroie)",
                          "openHASP zamienia CYD w panel dotykowy Home Assistant: strony/widgety LVGL z pages.jsonl, sterowanie MQTT. Pierwszy start: AP 'HASP-xxxxxx' haslo 'haspadmin', kalibracja 4 rogow, potem WiFi i MQTT przez www 192.168.4.1. Ekran poziomo; rotacje i inwersje zmienia sie w Configuration - Display."),
    "nerdminer.bin":    m("NerdMiner v2",    "kopacz-loteria BTC + kurs i bloki; NIETESTOWANY", "1.8.3", Z, "BitMaker-hub",
                          "Solo-miner Bitcoin na ESP32 (~60 kH/s - loteria i gadzet statystyczny). Pierwszy start: AP 'NerdMinerAP', haslo 'MineYourCoins', portal 192.168.4.1 (pool, adres BTC, jasnosc). Po zapisie ustawien plytka wraca do K-OS - uruchom program ponownie, ustawienia zostaja dzieki migawce."),
    "pogoda.bin":       m("Pogoda",          "prognoza pogody, Open-Meteo bez klucza; NIETESTOWANY", "0.1.36", Z, "nicholaswilde",
                          "Stacja pogodowa na LVGL: duza temperatura, ikona, prognoza 3-dniowa, wykres godzinowy, motywy. Dane z Open-Meteo bez klucza API - lokalizacja po IP albo wspolrzedne. Pierwszy start: AP 'cyd-weather-station-XXXX' (otwarty), portal 192.168.4.1 (WiFi, lokalizacja, strefa); potem http://cyd-weather-station.local/. Po 'zapisz i restart' plytka wraca do K-OS i autostart wznawia aplikacje."),
    "esp32div.bin":     m("ESP32-DIV",       "multitool WiFi/BLE/RF (HaleHound-CYD 2.4\")", "3.3.0", Z, "cifertech / Wontfallo (HaleHound-CYD)",
                          "HaleHound-CYD: skaner WiFi/BLE, deauth, RF, NFC (moduly opcjonalne). Port K-OS dla CYD 2.4\": dotyk XPT2046 przez magistrale LCD (TFT_eSPI, TOUCH_CS 33) zamiast bit-bangu po pinach ekranu, ktory zamrazal plansze startowa. Sprawdzone na sprzecie 03.09.2026: start, menu, dotyk, RST wraca do K-OS."),
}
# Pola z <nazwa>.meta.json, ktore trafiaja do katalogu (w tej kolejnosci). Reszta (np. model_b, plytka) zostaje w pliku.
UZYTK_POLA = ("nazwa", "opis", "wersja", "kategoria", "autor", "info", "licencja", "zrodlo", "orientacja", "zgloszono")


def wpis(pid, rel, data, meta):
    e = {"plik": rel, "rozmiar": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    e.update(meta)
    return e


def meta_uzytkownika(path_json):
    """META programu uzytkownika: <nazwa>.meta.json obok bina. Kategoria zawsze 'uzytkownicy'."""
    with open(path_json, encoding="utf-8") as fh:
        j = json.load(fh)
    j["kategoria"] = U
    out = {k: j[k] for k in UZYTK_POLA if k in j}
    for k in ("nazwa", "opis", "wersja", "autor", "info"):
        out.setdefault(k, "")
    return out


def main():
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
                progs.append(wpis(pid, f"bin/{pid}/{f}", data, meta))
            du = os.path.join(d, UZYTK_DIR)
            if os.path.isdir(du):
                for f in sorted(os.listdir(du)):
                    if not f.lower().endswith(".bin"): continue
                    p = os.path.join(du, f)
                    pj = os.path.join(du, f[:-4] + ".meta.json")
                    if not os.path.isfile(pj): print("UWAGA: brak", pj, "- pomijam", pid, f, file=sys.stderr); continue
                    try:
                        meta = meta_uzytkownika(pj)
                    except (OSError, ValueError) as e:
                        print("UWAGA: zly", pj, e, "- pomijam", file=sys.stderr); continue
                    with open(p, "rb") as fh: data = fh.read()
                    if data[:1] != b"\xe9": print("UWAGA: zly magic (nie obraz ESP32):", p, file=sys.stderr); continue
                    progs.append(wpis(pid, f"bin/{pid}/{UZYTK_DIR}/{f}", data, meta))
        out["plytki"].append({"id": pid, "nazwa": pname, "programy": progs})

    with open(os.path.join(root, "katalog.json"), "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2); fh.write("\n")
    print("katalog.json:", sum(len(p["programy"]) for p in out["plytki"]), "programow")


if __name__ == "__main__":
    main()
