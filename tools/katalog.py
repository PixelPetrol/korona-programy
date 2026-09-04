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
    "office.bin":       m("K-OS Office",     "notatnik, kalkulator, kalendarz, pliki, QR, kursy", "1.2.0", A, "Piotr Korona",
                          "Pakiet biurowy pod palec, po polsku i po angielsku. Notatnik pisany takze Z KLAWIATURY KOMPUTERA: Office podnosi na czas tego ekranu maly serwer i pokazuje adres oraz kod QR, wiec dlugi tekst piszesz w przegladarce, a laduje na karcie. Dalej: kalkulator z tasma i kolejnoscia dzialan, kalendarz z zegarem NTP i notatkami dnia, DWUPANELOWY menedzer plikow w duchu Total Commandera (panele jeden nad drugim, bo ekran jest waski: zaznaczanie wielu, kopiowanie z paskiem postepu i przerwaniem, przenoszenie, kasowanie drzewa po przeliczeniu; /korona tylko do czytania, kasowania .bin z /programy odmawia, zeby nie zostawiac sierot po migawkach), kody QR (takze WIFI: dla gosci), stoper z minutnikiem, konwerter jednostek i liczb oraz kursy walut z NBP po zwyklym HTTP (bez TLS, dziala offline z karty). Motyw i jezyk bierze z ustawien K-OS, nie pyta o haslo do sieci ani o kalibracje dotyku. Dane w /office/ na karcie. Sprawdzone na sprzecie: start, migracja danych ze starej nazwy, motyw i jezyk z K-OS, kalibracja z karty, powrot do K-OS po RST; modulow nie sprawdzano jeszcze palcem. 1.2.0: ZAPIS, KTORY NIE TRACI DANYCH - piec miejsc pisalo na karte bez sprawdzenia wyniku albo kasowalo jedyna ocalala kopie pliku (najgorsze: notatnik mowil 'zapisane' przy pelnej karcie, a notatki nie bylo nigdzie); wszystkie przepisane na jeden wspolny wzorzec: plik roboczy, sprawdzony kazdy zapis i fclose, podmiana przez .bak, przy niepowodzeniu stara tresc wraca i nic sie nie kasuje. Wzorzec nie rusza pliku, ktory nie jest jego (.part i .bak to legalne nazwy na FAT), a po zaniku zasilania w polowie podmiany oddaje plik na swoje miejsce przy nastepnym starcie i mowi o tym na ekranie. Do tego dioda RGB (cztery sygnaly: alarm minutnika, koniec kopiowania, blad zapisu, dzialajacy serwer notatek), zegar NTP w kalendarzu (dotad nie synchronizowal sie wcale, jesli nie wszedles wczesniej w kursy albo notatki przez www), krotsze czekanie na siec (6 s na siec zamiast 9 s, dotyk przerywa) i uczciwe komunikaty, gdy K-OS nie udostepnia sieci programom. Wersja 1.1.1 (sam numer w binarce, kod jak 1.1.0) nie byla wydana osobno - weszla w 1.2.0."),
    "meteo-pion.bin":   m("Meteo K-OS pion",  "pogoda, radar opadow IMGW, 4 widoki", "0.1.1", A, "Piotr Korona",
                          "Stacja pogodowa pod palec, po polsku i po angielsku, w orientacji PIONOWEJ. Cztery widoki przelaczane w menu (domyslnie Konsola, dalej Kafelki, Radar i Zegar) - wybor wraca po restarcie. Pogoda z Open-Meteo jednym zapytaniem CSV po zwyklym HTTP, bez klucza: stan biezacy, 5 dni, 24 godziny, nowcast co kwadrans, wschod i zachod slonca oraz faza ksiezyca. Radar opadow to siatka IMGW-PIB 64x64 o zasiegu 119 km, brana z tego samego serwera co zdjecia w SkyCYD - pod opadami rysowane sa rzeki, granice i nazwy okolicznych miejscowosci z pliku wektorowego na karcie (Natural Earth, domena publiczna, oraz GeoNames na CC BY 4.0 - atrybucja na ekranie 'o programie'). Miejscowosc wpisuje sie klawiatura ekranowa, a nazwy z sieci sa transliterowane, bo czcionki maja tylko ASCII. Motyw i jezyk bierze z ustawien K-OS albo mozna wybrac jeden z trzech wlasnych (Burza, Swit, Neon). Dziala bez sieci - pokazuje ostatnie dane z karty z data. Wskaznik baterii pojawia sie WYLACZNIE wtedy, gdy ktos sam przylutuje dzielnik napiecia do GPIO35 i odczyt jest wiarygodny; sam dzielnik tylko MIERZY, zasilania plytki z ogniwa ten program nie rozwiazuje. Dane w /meteo/ na karcie. SPRAWDZONE NA SPRZECIE 04.09.2026: start, motyw i jezyk z K-OS, kalibracja z karty, polaczenie z siecia, pobranie pogody (5 blokow) i klatki radaru IMGW, zapis do trybu offline, powrot do K-OS po RST. 0.1.1 naprawia urwany adres zapytania (bufor 560 znakow na adres dlugi na 589 - serwer oddawal HTTP 400 i pogody nie bylo wcale). PLIK MAPY /meteo/mapa.bin trzeba wgrac osobno na karte - bez niego radar dziala, ale bez rzek i nazw."),
    "meteo-poziom.bin": m("Meteo K-OS poziom", "pogoda, radar opadow IMGW; NIESPRAWDZONE", "0.1.1", A, "Piotr Korona",
                          "Ta sama stacja pogodowa co Meteo K-OS pion, ale w orientacji POZIOMEJ 320x240. Radar ma tu kwadratowa siatke przy lewej krawedzi i panel boczny z najsilniejsza komorka opadu, legenda i wiekiem klatki (na czerwono, gdy klatka ma ponad 10 minut). Konsola pokazuje ikone pogody i trzy pola szczegolow. UWAGA: kalibracja dotyku w TFT_eSPI jest wazna tylko dla obrotu, w ktorym ja zrobiono, wiec przy pierwszym uruchomieniu program proponuje kalibracje przeliczona z ustawien K-OS i pokazuje ekran sprawdzajacy z krzyzykiem - trzeba go dotknac. Jesli nie trafia, przechodzi do pelnej kalibracji czterech rogow i zapisuje wynik osobno, w /meteo/dotyk-poziom.txt oraz w migawce K-OS. Pliku kalibracji systemu nie nadpisuje. NIESPRAWDZONE NA SPRZECIE - zbudowane z tego samego zrodla co wersja pionowa, ktora sprawdzono."),
    "gry-vol1.bin":     m("K-OS Gry vol. 1", "2048 i Lunar Lander; WCZESNA WERSJA", "0.1.0", A, "Piotr Korona",
                          "Pierwszy tom gier dla K-OS, po polsku i po angielsku, orientacja pionowa. Dwie gry: 2048 w wersji K-OS oraz LUNAR LANDER z 30 poziomami nazwanymi od prawdziwych miejsc na Ksiezycu i dalej w ukladzie slonecznym - fizyka lotu z grawitacja, wiatrem, obrotem i paliwem, silnik glowny i dwa silniczki RCS pod palcem, warunki ladowania jak w oryginale (predkosc pionowa, pozioma i kat). Silnik gier rysuje do bufora 4-bitowego obejmujacego SAMA arene, wiec pasek stanu i strefa dotykowa nie kosztuja klatek; dotyk czytany wprost z XPT2046, bo getTouch z TFT_eSPI zabiera tyle czasu co cala klatka. Wyniki i postep na karcie w /gry/. Motyw i jezyk z ustawien K-OS. WCZESNA WERSJA: menu tomu to na razie zwykla lista - docelowy wyglad kafelkow i maskotka czekaja na decyzje. Poziomy od 15 w gore sa bardzo trudne albo niemozliwe przy oryginalnej tabeli wiatru (przy kacie ladowania +-0,15 rad ladownik rownowazy tylko czesc znoszenia, wiec cale dotkniecie musi zmiescic sie w oknie krotszym niz 2 sekundy) - w kodzie jest gotowa galka LL_WIND_SCALE do zlagodzenia, domyslnie wylaczona, bo tabela poziomow zostaje taka, jak zostala zaprojektowana. Sprawdzone testami na hoscie: 2,19 mln sprawdzen, zero bledow, w tym przechodzalnosc wszystkich 30 poziomow przez wyszukiwanie i 360 przebiegow losowego trzaskania w przyciski. NIESPRAWDZONE NA SPRZECIE - liczba klatek na sekunde jest na razie modelem, nie pomiarem."),
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
