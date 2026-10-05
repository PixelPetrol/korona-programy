#!/usr/bin/env python3
"""Generuje katalogi sklepu z plikow bin/<plytka>/*.bin i tabeli META oraz z programow
uzytkownikow bin/<plytka>/uzytkownicy/*.bin (META z pliku <nazwa>.meta.json obok bina):
  * katalog-<plytka>.json (format v3, jeden plik na plytke) + plytki.json - czyta je K-OS >= 0.4.7
    i portal/sklep.html; dlugie opisy leza w info/<plytka>/<plik>.<jezyk>.txt,
  * katalog.json (stary wspolny format v2) - TYLKO POLA MINIMALNE (V2_POLA nizej), bo ma twardy
    sufit KATALOG_STOP, a czytaja go juz tylko stare K-OS i strona WWW plytki do 0.7.6.

Uzycie (z katalogu repo):  python3 tools/katalog.py              - generuje i zapisuje
                           python3 tools/katalog.py --sprawdz     - NIC nie zapisuje: mierzy v2
                               i porownuje wszystkie pliki z dyskiem. Kod wyjscia: 0 = w porzadku,
                               1 = v2 ponad KATALOG_STOP, 3 = pliki na dysku sa nieaktualne
                               (ktos zmienil bin/ albo META i nie przegenerowal katalogow).
Rozmiary sa czytane z plikow; opisy/wersje z tabeli ponizej (programy sklepu) albo z
<nazwa>.meta.json (programy uzytkownikow - te trafiaja tam automatem z zgloszenia/, patrz
tools/przyjmij_zgloszenia.py). Plik bez META nie trafia do katalogu (ostrzezenie na stderr).

Pliki danych programow (tabela DANE nizej): DOOM potrzebuje /doom/doom.kwad, Meteo /meteo/mapa.bin.
Leza w dane/<program>/ i ida do katalogu v3 jako pole "pliki" wpisu programu - K-OS >= 0.7.8 pobiera
je na karte razem z programem (po TLS, z kontrola rozmiaru i sha256). Starsze K-OS pole ignoruja,
a stary katalog.json (v2) go NIE dostaje (V2_POLA).

Historia zmian programow (tabela ZMIANY w tools/zmiany.py): pliki info/<plytka>/<plik>.zmiany.<pl|en>.txt
i pole "zmiany" wpisu v3 (jak "info": {"pl": sciezka, "en": sciezka}, tylko gdy tekst istnieje). Czyta je
portal/sklep.html ("co nowego"); K-OS ich nie czyta, stare K-OS pole ignoruja, v2 go NIE dostaje (V2_POLA).

Kategorie: "autorskie" (programy K-OS / Piotra), "zewnetrzne" (porty cudzych projektow
robione tu), "uzytkownicy" (zgloszone przez uzytkownikow przez PR do zgloszenia/).
K-OS <= 0.3.6 zna tylko dwie pierwsze i wszystko, co nie jest "autorskie", pokazuje
w "zewnetrzne" (net.cpp progInCat) - stare wersje zobacza wiec programy uzytkownikow tam.
"""
import json, os, sys, hashlib
from zmiany import ZMIANY   # tools/zmiany.py - historia zmian programow sklepu (pole "zmiany", tylko v3)

PLYTKI = [
    ("cyd24", 'CYD 2.4" (ESP32-2432S024)'),
    ("cyd28", 'CYD 2.8" (ESP32-2432S028R)'),
    # Nowsza rewizja tej samej plytki 2.8": panel ST7789 zamiast ILI9341. Piny, dotyk i
    # podswietlenie IDENTYCZNE - ale sterownik ekranu jest wkompilowany w TFT_eSPI, wiec
    # binarki musza byc osobne i plytka musi miec wlasny identyfikator.
    ("cyd28s", 'CYD 2.8" ST7789 (ESP32-2432S028 "2 USB")'),
]
UZYTK_DIR = "uzytkownicy"          # bin/<plytka>/uzytkownicy/<nazwa>.bin + <nazwa>.meta.json
# (plytka, plik) albo plik -> dict(nazwa, opis, wersja, kategoria, autor, info); wpis z plytka ma pierwszenstwo.
# kategoria: "autorskie" (programy K-OS / Piotra) albo "zewnetrzne" (porty cudzych projektow).
# Plik bez wpisu -> nie trafia do katalogu (zeby nie wystawiac niesprawdzonych binarek).
A, Z, U = "autorskie", "zewnetrzne", "uzytkownicy"
def m(nazwa, opis, wersja, kategoria, autor, info="", opis_en="", info_en=""):
    """opis_en / info_en sa OPCJONALNE i puste az do przetlumaczenia. Pustych NIE wystawiamy
    jako angielskich - K-OS pokaze wtedy polska wersje i napisze, ze to zastepstwo. Wpisanie
    tu polskiego tekstu pod etykieta 'en' byloby gorsze niz brak: uzytkownik nie wiedzialby,
    ze czyta nie ten jezyk."""
    return dict(nazwa=nazwa, opis=opis, wersja=wersja, kategoria=kategoria, autor=autor, info=info,
                opis_en=opis_en, info_en=info_en)
META = {
    "radar-pion.bin":   m("SkyCYD 4.4.2 pion",   "radar samolotow ADS-B; tylko po polsku", "4.4.2", A, "Piotr Korona",
                          "Radar lotniczy: samoloty wokol Twojego domu na mapie, zdjecia samolotow i pogoda. Ekran pionowo 240x320.\n"
                          "Stan: poprawki portalu z tej wersji (wydawanie adresow, nazwa AP) nie byly jeszcze sprawdzone na plytce.\n"
                          "Umie: pozycje samolotow z adsb.lol (przez Worker SkyCYD), mapa okolicy, zdjecia maszyn, pogoda.\n"
                          "Potrzebne: WiFi z internetem. Przy pierwszym starcie plytka wystawia wlasny punkt dostepowy z portalem konfiguracji - tam podajesz siec i ustawienia. Karta SD nie jest uzywana.\n"
                          "Ograniczenia: interfejs tylko po polsku. SkyCYD powstal przed K-OS i nie czyta jego ustawien z karty (motyw, jezyk, kalibracja dotyku) - ma wlasne, ustawiane w swoim portalu.",
                          opis_en="ADS-B aircraft radar; Polish only",
                          info_en="An aircraft radar: the planes around your home on a map, aircraft photos and the weather. Portrait screen 240x320.\n"
                          "Status: the portal fixes in this version (handing out addresses, the AP name) have not been tested on a board yet.\n"
                          "Features: aircraft positions from adsb.lol (through the SkyCYD Worker), a map of the area, aircraft photos, weather.\n"
                          "Needs: WiFi with internet. On the first start the board opens its own access point with a setup portal - you enter the network and settings there. The SD card is not used.\n"
                          "Limits: the interface is in Polish only. SkyCYD predates K-OS and does not read its settings from the card (theme, language, touch calibration) - it has its own, set in its portal."),
    "radar-poziom.bin": m("SkyCYD 4.4.2 poziom", "radar ADS-B, ekran poziomo; tylko po polsku", "4.4.2", A, "Piotr Korona",
                          "Ten sam radar lotniczy co SkyCYD pion, w orientacji poziomej 320x240 - to oryginalny uklad SkyCYD.\n"
                          "Stan: poprawki portalu z tej wersji (wydawanie adresow, nazwa AP) nie byly jeszcze sprawdzone na plytce.\n"
                          "Umie: pozycje samolotow z adsb.lol (przez Worker SkyCYD), mapa okolicy, zdjecia maszyn, pogoda.\n"
                          "Potrzebne: WiFi z internetem. Przy pierwszym starcie plytka wystawia wlasny punkt dostepowy z portalem konfiguracji. Karta SD nie jest uzywana. Kalibracja dotyku jest osobna od wersji pionowej.\n"
                          "Ograniczenia: interfejs tylko po polsku. SkyCYD powstal przed K-OS i nie czyta jego ustawien z karty (motyw, jezyk, kalibracja dotyku) - ma wlasne, ustawiane w swoim portalu.",
                          opis_en="ADS-B radar, landscape; Polish only",
                          info_en="The same aircraft radar as SkyCYD portrait, in landscape 320x240 - the original SkyCYD layout.\n"
                          "Status: the portal fixes in this version (handing out addresses, the AP name) have not been tested on a board yet.\n"
                          "Features: aircraft positions from adsb.lol (through the SkyCYD Worker), a map of the area, aircraft photos, weather.\n"
                          "Needs: WiFi with internet. On the first start the board opens its own access point with a setup portal. The SD card is not used. Touch calibration is separate from the portrait version.\n"
                          "Limits: the interface is in Polish only. SkyCYD predates K-OS and does not read its settings from the card (theme, language, touch calibration) - it has its own, set in its portal."),
    "office.bin":       m("K-OS Office",     "notatnik, kalkulator, pliki; BETA", "1.3.2", A, "Piotr Korona",
                          "Pakiet biurowy pod palec, po polsku i po angielsku: notatnik, kalkulator, kalendarz, menedzer plikow, kody QR, kursy walut.\n"
                          "Stan: BETA - ta wersja nie byla jeszcze uruchomiona na plytce. Wczesniejsza sprawdzona na 2.4\": start, motyw i jezyk z K-OS, kalibracja, powrot RST; modulow palcem nie sprawdzano.\n"
                          "Umie: notatki pisane tez z klawiatury komputera (adres i kod QR na ekranie, piszesz w przegladarce), kalkulator z tasma, kalendarz z zegarem NTP i notatkami dnia, dwupanelowy menedzer plikow (kopiowanie, przenoszenie, kasowanie), kody QR (takze WiFi dla gosci), stoper i minutnik, przelicznik jednostek, kursy NBP (offline z karty).\n"
                          "Potrzebne: karta SD (dane w /office/); WiFi do kursow, zegara i pisania z komputera. Motyw, jezyk, sieci, strefe czasowa i kalibracje bierze z K-OS.\n"
                          "Ograniczenia: /korona tylko do odczytu; programow .bin z /programy nie kasuje. Kursy i strona notatnika ida zwyklym http.",
                          opis_en="notes, calculator, files; BETA",
                          info_en="An office suite for your fingertip, in Polish and English: notes, calculator, calendar, file manager, QR codes, exchange rates.\n"
                          "Status: BETA - this version has not been run on a board yet. An earlier one was tested on 2.4\": start, theme and language from K-OS, calibration, RST return; the modules were not tried by finger.\n"
                          "Features: notes you can also type on a computer keyboard (address and QR code on screen, you type in a browser), a calculator with a tape, a calendar with an NTP clock and day notes, a two-panel file manager (copy, move, delete), QR codes (also WiFi for guests), stopwatch and timer, unit converter, NBP exchange rates (offline from the card).\n"
                          "Needs: an SD card (data in /office/); WiFi for rates, the clock and typing from a computer. Theme, language, networks, time zone and calibration come from K-OS.\n"
                          "Limits: /korona is read-only; it does not delete .bin programs in /programy. Rates and the notes page use plain http."),
    "meteo-pion.bin": m("Meteo K-OS pion", "pogoda i radar opadow IMGW; BETA", "0.2.4", A, "Piotr Korona",
                          "Stacja pogodowa pod palec, po polsku i po angielsku, ekran pionowo: prognoza z Open-Meteo i radar opadow IMGW.\n"
                          "Stan: BETA - ta wersja nie byla jeszcze uruchomiona na plytce. Wczesniejsza sprawdzona na 2.4\" 04.09.2026: start, siec, pogoda, klatka radaru, tryb offline, powrot RST.\n"
                          "Umie: cztery widoki (Konsola, Kafelki, Radar, Zegar); stan biezacy, 5 dni, 24 godziny, prognoza co kwadrans, slonce i ksiezyc; radar IMGW-PIB (119 km) z rzekami, granicami i nazwami miejscowosci; motyw z K-OS albo jeden z trzech wlasnych; bez sieci ostatnie dane z karty.\n"
                          "Potrzebne: WiFi (Open-Meteo bez klucza), karta SD (dane w /meteo/). Mape /meteo/mapa.bin K-OS od 0.7.8 pobiera sam; ze starszym skopiuj ja ze strony sklepu (dane/meteo/), inaczej radar jest bez rzek i nazw. Sieci, jezyk, strefe i kalibracje bierze z K-OS.\n"
                          "Ograniczenia: nazwy miejscowosci bez ogonkow. Wskaznik baterii tylko z wlasnym dzielnikiem napiecia na GPIO35.\n"
                          "Mapa: Natural Earth (domena publiczna), GeoNames (CC BY 4.0).",
                          opis_en="weather and IMGW rain radar; BETA",
                          info_en="A weather station for your fingertip, in Polish and English, portrait screen: an Open-Meteo forecast and the IMGW rain radar.\n"
                          "Status: BETA - this version has not been run on a board yet. An earlier one was tested on 2.4\" on 04.09.2026: start, network, weather, a radar frame, offline mode, RST return.\n"
                          "Features: four views (Console, Tiles, Radar, Clock); current conditions, 5 days, 24 hours, a 15-minute nowcast, sun and moon; an IMGW-PIB radar (119 km) with rivers, borders and town names; the K-OS theme or three of its own; offline the last data from the card.\n"
                          "Needs: WiFi (Open-Meteo, no key), an SD card (data in /meteo/). K-OS 0.7.8 or newer fetches the map /meteo/mapa.bin itself; with an older one copy it from the store website (dane/meteo/), else the radar has no rivers or names. Networks, language, zone and calibration come from K-OS.\n"
                          "Limits: town names without diacritics. A battery gauge only with your own voltage divider on GPIO35.\n"
                          "Map data: Natural Earth, GeoNames (CC BY 4.0)."),
    "meteo-poziom.bin": m("Meteo K-OS poziom", "pogoda i radar, poziomo; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Ta sama stacja pogodowa co Meteo K-OS pion, w orientacji poziomej 320x240, z panelem bocznym radaru.\n"
                          "Stan: BETA, NIESPRAWDZONE - wersji poziomej nikt jeszcze nie uruchomil; jest zbudowana z tego samego zrodla co sprawdzona wersja pionowa.\n"
                          "Umie: to samo co wersja pionowa - prognoza z Open-Meteo, radar IMGW z mapa, tryb offline z karty. Radar ma tu panel boczny z najsilniejszym opadem, legenda i wiekiem klatki; konsola pokazuje ikone pogody i trzy pola szczegolow.\n"
                          "Potrzebne: WiFi, karta SD (dane w /meteo/; mape /meteo/mapa.bin K-OS od 0.7.8 pobiera sam, ze starszym skopiuj ja ze strony sklepu). Przy pierwszym starcie program proponuje kalibracje dotyku przeliczona z K-OS i ekran z krzyzykiem do dotkniecia; gdy nie trafia, prosi o cztery rogi i zapisuje wynik osobno (/meteo/dotyk-poziom.txt), bez ruszania kalibracji systemu.\n"
                          "Mapa: Natural Earth (domena publiczna), GeoNames (CC BY 4.0).",
                          opis_en="weather and radar, landscape; BETA, UNTESTED",
                          info_en="The same weather station as Meteo K-OS portrait, in landscape 320x240, with a radar side panel.\n"
                          "Status: BETA, UNTESTED - nobody has run the landscape version yet; it is built from the same source as the tested portrait version.\n"
                          "Features: the same as the portrait version - an Open-Meteo forecast, the IMGW radar with a map, offline mode from the card. The radar has a side panel with the strongest rainfall, a legend and the frame age; the console shows a weather icon and three detail fields.\n"
                          "Needs: WiFi, an SD card (data in /meteo/; K-OS 0.7.8 or newer fetches the map /meteo/mapa.bin itself, with an older one copy it from the store website). On the first start the program offers a touch calibration converted from K-OS and a crosshair screen to touch; if it misses, it asks for four corners and saves the result separately (/meteo/dotyk-poziom.txt) without touching the system calibration.\n"
                          "Map: Natural Earth (public domain), GeoNames (CC BY 4.0)."),
    "ropeburn-mini.bin": m("Ropeburn Mini", "skakanka w rytm, skaczesz Ty; BETA, NIESPRAWDZONE", "0.3.0", A, "Piotr Korona",
                          "Gra zrecznosciowa na rytm, ekran pionowy: lina kreci sie coraz szybciej, a Ty skaczesz - kazde dotkniecie ekranu to skok, ktory musi trafic w okno.\n"
                          "Stan: BETA, NIESPRAWDZONE - ta wersja nie byla jeszcze uruchomiona na plytce, tylko testowana na komputerze.\n"
                          "Umie: trzy zycia, premia x5 za trafienie w sam srodek okna, mnoznik rosnacy co 20 skokow do x32, karty ulepszen w biegu (wybierasz dotknieciem, gra sie nie zatrzymuje), metronom na brzeczyku, rekordy z inicjalami. Dobry bieg trwa 70-90 s. Kolejne poziomy i dodatkowe zycia odblokowuje sama gra, bez sklepu i waluty.\n"
                          "Potrzebne: nic poza plytka - bez sieci. Postep zapisuje w pamieci plytki; na karcie SD (jesli jest) kladzie czytelna kopie w /ropeburn/.\n"
                          "Ograniczenia: gotowa 1 postac z 5 i 2 poziomy z 5 (Podworko i Wiatr).",
                          opis_en="rhythm jump rope, you jump; BETA, UNTESTED",
                          info_en="A rhythm skill game, portrait screen: the rope turns faster and faster and you jump - every touch of the screen is a jump that must land in the window.\n"
                          "Status: BETA, UNTESTED - this version has not been run on a board yet, only tested on a computer.\n"
                          "Features: three lives, x5 for hitting the exact centre of the window, a multiplier that grows every 20 jumps up to x32, upgrade cards during the run (you pick with a touch, the game never pauses), a metronome on the buzzer, records with initials. A good run lasts 70-90 s. The game itself unlocks further levels and extra lives, with no shop and no currency.\n"
                          "Needs: nothing but the board - no network. Progress is kept in the board memory; on the SD card (if present) it puts a readable copy in /ropeburn/.\n"
                          "Limits: 1 character of 5 and 2 levels of 5 are ready (Backyard and Wind)."),
    ("cyd28", "ropeburn-mini.bin"): m("Ropeburn Mini", "skakanka w rytm, skaczesz Ty; BETA, NIESPRAWDZONE", "0.3.0", A, "Piotr Korona",
                          "Gra zrecznosciowa na rytm, ekran pionowy: lina kreci sie coraz szybciej, a Ty skaczesz - kazde dotkniecie ekranu to skok, ktory musi trafic w okno.\n"
                          "Stan: BETA, NIESPRAWDZONE - na tej plytce gra nie byla uruchomiona ani razu.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: to samo co na 2.4\" - trzy zycia, premia za srodek okna, mnoznik do x32, karty ulepszen w biegu, metronom, rekordy z inicjalami, odblokowania bez sklepu i waluty.\n"
                          "Potrzebne: nic poza plytka - bez sieci. Kalibracje dotyku bierze z K-OS (/korona/cyd28/dotyk.txt); bez niej uzywa zmierzonej domyslnej. Postep w pamieci plytki, czytelna kopia na karcie w /ropeburn/.\n"
                          "Ograniczenia: gotowa 1 postac z 5 i 2 poziomy z 5.",
                          opis_en="rhythm jump rope, you jump; BETA, UNTESTED",
                          info_en="A rhythm skill game, portrait screen: the rope turns faster and faster and you jump - every touch of the screen is a jump that must land in the window.\n"
                          "Status: BETA, UNTESTED - the game has not been run on this board even once.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: the same as on 2.4\" - three lives, a bonus for the window centre, a multiplier up to x32, upgrade cards during the run, a metronome, records with initials, unlocks with no shop and no currency.\n"
                          "Needs: nothing but the board - no network. Touch calibration comes from K-OS (/korona/cyd28/dotyk.txt); without it a measured default is used. Progress in the board memory, a readable copy on the card in /ropeburn/.\n"
                          "Limits: 1 character of 5 and 2 levels of 5 are ready."),
    ("cyd28s", "ropeburn-mini.bin"): m("Ropeburn Mini", "skakanka w rytm, skaczesz Ty; BETA, NIESPRAWDZONE", "0.3.0", A, "Piotr Korona",
                          "Gra zrecznosciowa na rytm, ekran pionowy: lina kreci sie coraz szybciej, a Ty skaczesz - kazde dotkniecie ekranu to skok, ktory musi trafic w okno.\n"
                          "Stan: BETA, NIESPRAWDZONE - na tej plytce gra nie byla uruchomiona ani razu. Jesli obraz wyjdzie negatywem albo z zamienionym czerwonym i niebieskim, napisz - to poprawka jednej flagi.\n"
                          "Plytka: CYD 2.8\" z panelem ST7789 (dwa gniazda USB).\n"
                          "Umie: to samo co na 2.4\" - trzy zycia, premia za srodek okna, mnoznik do x32, karty ulepszen w biegu, metronom, rekordy z inicjalami, odblokowania bez sklepu i waluty.\n"
                          "Potrzebne: nic poza plytka - bez sieci. Kalibracje dotyku bierze z K-OS (/korona/cyd28s/dotyk.txt); bez niej uzywa zmierzonej domyslnej. Postep w pamieci plytki, czytelna kopia na karcie w /ropeburn/.\n"
                          "Ograniczenia: gotowa 1 postac z 5 i 2 poziomy z 5.",
                          opis_en="rhythm jump rope, you jump; BETA, UNTESTED",
                          info_en="A rhythm skill game, portrait screen: the rope turns faster and faster and you jump - every touch of the screen is a jump that must land in the window.\n"
                          "Status: BETA, UNTESTED - the game has not been run on this board even once. If the picture comes out as a negative or with red and blue swapped, tell us - it is a one-flag fix.\n"
                          "Board: CYD 2.8\" with the ST7789 panel (two USB sockets).\n"
                          "Features: the same as on 2.4\" - three lives, a bonus for the window centre, a multiplier up to x32, upgrade cards during the run, a metronome, records with initials, unlocks with no shop and no currency.\n"
                          "Needs: nothing but the board - no network. Touch calibration comes from K-OS (/korona/cyd28s/dotyk.txt); without it a measured default is used. Progress in the board memory, a readable copy on the card in /ropeburn/.\n"
                          "Limits: 1 character of 5 and 2 levels of 5 are ready."),
    "doom.bin": m("DOOM (BETA)", "DOOM z plansza Freedoom; NIESPRAWDZONE", "0.1.1-beta", Z, "id Software, doomhack (GBADoom), HenrysCat (cyd-doom) / port K-OS: Piotr Korona",
                          "Silnik gry DOOM (GBADoom/PrBoom) jako program K-OS, z darmowa plansza Freedoom ze sklepu.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byla jeszcze uruchomiona na plytce.\n"
                          "Umie: dotyk, jasnosc, kolory i jezyk z K-OS, zapisy na karcie, RST wraca do K-OS. Lewa polowa - chodzenie, prawa - uzyj i strzal, rogi u gory - menu i mapa.\n"
                          "Potrzebne: karta SD i dane /doom/doom.kwad (1,75 MB). K-OS od 0.7.8 pobiera je razem z programem (wlasny plik nadpisze tylko po pytaniu). Ze starszym K-OS pobierz doom.kwad ze strony sklepu (dane/doom/) i skopiuj do /doom/ na karcie.\n"
                          "Ograniczenia: jedna plansza (E1M1) w polowie rozdzielczosci poziomej, bez dzwieku. Wlasny doom1.wad przerobisz skryptem wad2kos.py (github.com/PixelPetrol/cyd-doom-kos).\n"
                          "Autorzy: id Software (DOOM), doomhack (GBADoom), HenrysCat (cyd-doom); port do K-OS: Piotr Korona. Silnik GPL-2.0, dane Freedoom BSD-3-Clause. DOOM to znak towarowy id Software.",
                          opis_en="DOOM with a Freedoom level; UNTESTED",
                          info_en="The DOOM game engine (GBADoom/PrBoom) as a K-OS program, with a free Freedoom level from the store.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet.\n"
                          "Features: touch, brightness, colours and language from K-OS, saves on the card, RST returns to K-OS. Left half - walk, right half - use and fire, top corners - menu and map.\n"
                          "Needs: an SD card and the data /doom/doom.kwad (1.75 MB). K-OS 0.7.8 or newer downloads it with the program (your own file is replaced only after a question). With an older K-OS copy doom.kwad from the store website (dane/doom/) to /doom/ on the card.\n"
                          "Limits: one level (E1M1) at half horizontal resolution, no sound. Convert your own doom1.wad with wad2kos.py (github.com/PixelPetrol/cyd-doom-kos).\n"
                          "Authors: id Software (DOOM), doomhack (GBADoom), HenrysCat (cyd-doom); K-OS port: Piotr Korona. Engine GPL-2.0, Freedoom data BSD-3-Clause. DOOM is a trademark of id Software."),
    ("cyd28", "doom.bin"): m("DOOM (BETA)", "DOOM z plansza Freedoom; NIESPRAWDZONE", "0.1.1-beta", Z, "id Software, doomhack (GBADoom), HenrysCat (cyd-doom) / port K-OS: Piotr Korona",
                          "Silnik gry DOOM (GBADoom/PrBoom) jako program K-OS, z darmowa plansza Freedoom ze sklepu.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byla jeszcze uruchomiona na plytce.\n"
                          "Plytka: CYD 2.8\" ILI9341.\n"
                          "Umie: dotyk, jasnosc, kolory i jezyk z K-OS, zapisy na karcie, RST wraca do K-OS. Lewa polowa - chodzenie, prawa - uzyj i strzal, rogi u gory - menu i mapa.\n"
                          "Potrzebne: karta SD i dane /doom/doom.kwad (1,75 MB). K-OS od 0.7.8 pobiera je razem z programem (wlasny plik nadpisze tylko po pytaniu). Ze starszym K-OS pobierz doom.kwad ze strony sklepu (dane/doom/) i skopiuj do /doom/ na karcie.\n"
                          "Ograniczenia: jedna plansza (E1M1) w polowie rozdzielczosci poziomej, bez dzwieku. Wlasny doom1.wad przerobisz skryptem wad2kos.py (github.com/PixelPetrol/cyd-doom-kos).\n"
                          "Autorzy: id Software (DOOM), doomhack (GBADoom), HenrysCat (cyd-doom); port do K-OS: Piotr Korona. Silnik GPL-2.0, dane Freedoom BSD-3-Clause. DOOM to znak towarowy id Software.",
                          opis_en="DOOM with a Freedoom level; UNTESTED",
                          info_en="The DOOM game engine (GBADoom/PrBoom) as a K-OS program, with a free Freedoom level from the store.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet.\n"
                          "Board: CYD 2.8\" ILI9341.\n"
                          "Features: touch, brightness, colours and language from K-OS, saves on the card, RST returns to K-OS. Left half - walk, right half - use and fire, top corners - menu and map.\n"
                          "Needs: an SD card and the data /doom/doom.kwad (1.75 MB). K-OS 0.7.8 or newer downloads it with the program (your own file is replaced only after a question). With an older K-OS copy doom.kwad from the store website (dane/doom/) to /doom/ on the card.\n"
                          "Limits: one level (E1M1) at half horizontal resolution, no sound. Convert your own doom1.wad with wad2kos.py (github.com/PixelPetrol/cyd-doom-kos).\n"
                          "Authors: id Software (DOOM), doomhack (GBADoom), HenrysCat (cyd-doom); K-OS port: Piotr Korona. Engine GPL-2.0, Freedoom data BSD-3-Clause. DOOM is a trademark of id Software."),
    ("cyd28s", "doom.bin"): m("DOOM (BETA)", "DOOM z plansza Freedoom; NIESPRAWDZONE", "0.1.1-beta", Z, "id Software, doomhack (GBADoom), HenrysCat (cyd-doom) / port K-OS: Piotr Korona",
                          "Silnik gry DOOM (GBADoom/PrBoom) jako program K-OS, z darmowa plansza Freedoom ze sklepu.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byla jeszcze uruchomiona na plytce.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB) - najblizsza plytce autora oryginalu.\n"
                          "Umie: dotyk, jasnosc, kolory i jezyk z K-OS, zapisy na karcie, RST wraca do K-OS. Lewa polowa - chodzenie, prawa - uzyj i strzal, rogi u gory - menu i mapa.\n"
                          "Potrzebne: karta SD i dane /doom/doom.kwad (1,75 MB). K-OS od 0.7.8 pobiera je razem z programem (wlasny plik nadpisze tylko po pytaniu). Ze starszym K-OS pobierz doom.kwad ze strony sklepu (dane/doom/) i skopiuj do /doom/ na karcie.\n"
                          "Ograniczenia: jedna plansza (E1M1) w polowie rozdzielczosci poziomej, bez dzwieku. Wlasny doom1.wad przerobisz skryptem wad2kos.py (github.com/PixelPetrol/cyd-doom-kos).\n"
                          "Autorzy: id Software (DOOM), doomhack (GBADoom), HenrysCat (cyd-doom); port do K-OS: Piotr Korona. Silnik GPL-2.0, dane Freedoom BSD-3-Clause. DOOM to znak towarowy id Software.",
                          opis_en="DOOM with a Freedoom level; UNTESTED",
                          info_en="The DOOM game engine (GBADoom/PrBoom) as a K-OS program, with a free Freedoom level from the store.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets) - closest to the original author's board.\n"
                          "Features: touch, brightness, colours and language from K-OS, saves on the card, RST returns to K-OS. Left half - walk, right half - use and fire, top corners - menu and map.\n"
                          "Needs: an SD card and the data /doom/doom.kwad (1.75 MB). K-OS 0.7.8 or newer downloads it with the program (your own file is replaced only after a question). With an older K-OS copy doom.kwad from the store website (dane/doom/) to /doom/ on the card.\n"
                          "Limits: one level (E1M1) at half horizontal resolution, no sound. Convert your own doom1.wad with wad2kos.py (github.com/PixelPetrol/cyd-doom-kos).\n"
                          "Authors: id Software (DOOM), doomhack (GBADoom), HenrysCat (cyd-doom); K-OS port: Piotr Korona. Engine GPL-2.0, Freedoom data BSD-3-Clause. DOOM is a trademark of id Software."),
    "control.bin": m("K-OS Control", "klawiatura, mysz i pilot BT; BETA, NIESPRAWDZONE", "0.2.1-beta", A, "Piotr Korona",
                          "Plytka jako klawiatura, mysz (touchpad) i pilot TV po Bluetooth dla Windows, Androida, iPhone'a, iPada i Google TV - bez sterownikow, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byla jeszcze uruchomiona na plytce.\n"
                          "Umie: touchpad pionowo (stukniecie = klik, przytrzymanie = przeciaganie), klawiatura ekranowa, pilot TV, siatka skrotow 3x4 z profilami (m.in. Windows, Zoom, YouTube na TV) i kafelkami tekst/makro, pisanie tekstu z telefonu. Profil wybiera sie sam po urzadzeniu. Skroty edytujesz na plytce albo z telefonu (QR i kod sesji). Do 4 urzadzen, jedno naraz; parowanie z potwierdzeniem na plytce.\n"
                          "Potrzebne: karta SD (profile; bez niej parowanie nie zostanie zapamietane); WiFi z K-OS tylko do edycji z telefonu.\n"
                          "Ograniczenia: plytka wysyla kody klawiszy, wiec uklad klawiatury ustawiasz dla kazdego urzadzenia; touchpad na jeden palec; na iPhonie mysz tylko z AssistiveTouch; strona edycji to zwykle http. Karta zawiera klucze parowania - chron ja. Tylko dla wlasnych urzadzen.",
                          opis_en="BT keyboard, mouse, remote; BETA, UNTESTED",
                          info_en="The board as a Bluetooth keyboard, mouse (touchpad) and TV remote for Windows, Android, iPhone, iPad and Google TV - no drivers, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet.\n"
                          "Features: portrait touchpad (tap = click, hold = drag), on-screen keyboard, TV remote, a 3x4 shortcut grid with profiles (Windows, Zoom, YouTube on TV and more) and text/macro tiles, typing text from your phone. The profile follows the connected device. You edit shortcuts on the board or from your phone (QR and session code). Up to 4 devices, one at a time; pairing is confirmed on the board.\n"
                          "Needs: an SD card (profiles; without it the pairing is not remembered); WiFi from K-OS only for editing from the phone.\n"
                          "Limits: the board sends key codes, so you set the keyboard layout per device; one-finger touchpad; on iPhone the mouse works only with AssistiveTouch; the editing page is plain http. The card holds the pairing keys - protect it. Only for your own devices."),
    ("cyd28", "control.bin"): m("K-OS Control", "klawiatura, mysz i pilot BT; BETA, NIESPRAWDZONE", "0.2.1-beta", A, "Piotr Korona",
                          "Plytka jako klawiatura, mysz (touchpad) i pilot TV po Bluetooth dla Windows, Androida, iPhone'a, iPada i Google TV - bez sterownikow, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byla jeszcze uruchomiona na plytce, na 2.8\" tez nie.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: touchpad pionowo, klawiatura ekranowa, pilot TV, siatka skrotow 3x4 z profilami i kafelkami tekst/makro, pisanie tekstu z telefonu. Skroty edytujesz na plytce albo z telefonu (QR i kod sesji). Do 4 urzadzen, jedno naraz; parowanie z potwierdzeniem na plytce.\n"
                          "Potrzebne: karta SD (profile; bez niej parowanie nie zostanie zapamietane); WiFi z K-OS tylko do edycji z telefonu. Bez kalibracji z K-OS zaproponuje wlasna przy starcie.\n"
                          "Ograniczenia: plytka wysyla kody klawiszy, wiec uklad klawiatury ustawiasz dla kazdego urzadzenia; touchpad na jeden palec; na iPhonie mysz tylko z AssistiveTouch; strona edycji to zwykle http. Karta zawiera klucze parowania - chron ja. Tylko dla wlasnych urzadzen.",
                          opis_en="BT keyboard, mouse, remote; BETA, UNTESTED",
                          info_en="The board as a Bluetooth keyboard, mouse (touchpad) and TV remote for Windows, Android, iPhone, iPad and Google TV - no drivers, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet, on 2.8\" neither.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: portrait touchpad, on-screen keyboard, TV remote, a 3x4 shortcut grid with profiles and text/macro tiles, typing text from your phone. You edit shortcuts on the board or from your phone (QR and session code). Up to 4 devices, one at a time; pairing is confirmed on the board.\n"
                          "Needs: an SD card (profiles; without it the pairing is not remembered); WiFi from K-OS only for editing from the phone. Without a K-OS calibration it offers its own at start.\n"
                          "Limits: the board sends key codes, so you set the keyboard layout per device; one-finger touchpad; on iPhone the mouse works only with AssistiveTouch; the editing page is plain http. The card holds the pairing keys - protect it. Only for your own devices."),
    ("cyd28s", "control.bin"): m("K-OS Control", "klawiatura, mysz i pilot BT; BETA, NIESPRAWDZONE", "0.2.1-beta", A, "Piotr Korona",
                          "Plytka jako klawiatura, mysz (touchpad) i pilot TV po Bluetooth dla Windows, Androida, iPhone'a, iPada i Google TV - bez sterownikow, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byla jeszcze uruchomiona na plytce, na tej rewizji tez nie.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: touchpad pionowo, klawiatura ekranowa, pilot TV, siatka skrotow 3x4 z profilami i kafelkami tekst/makro, pisanie tekstu z telefonu. Skroty edytujesz na plytce albo z telefonu (QR i kod sesji). Do 4 urzadzen, jedno naraz; parowanie z potwierdzeniem na plytce.\n"
                          "Potrzebne: karta SD (profile; bez niej parowanie nie zostanie zapamietane); WiFi z K-OS tylko do edycji z telefonu. Bez kalibracji z K-OS zaproponuje wlasna przy starcie.\n"
                          "Ograniczenia: plytka wysyla kody klawiszy, wiec uklad klawiatury ustawiasz dla kazdego urzadzenia; touchpad na jeden palec; na iPhonie mysz tylko z AssistiveTouch; strona edycji to zwykle http. Karta zawiera klucze parowania - chron ja. Tylko dla wlasnych urzadzen.",
                          opis_en="BT keyboard, mouse, remote; BETA, UNTESTED",
                          info_en="The board as a Bluetooth keyboard, mouse (touchpad) and TV remote for Windows, Android, iPhone, iPad and Google TV - no drivers, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet, on this revision neither.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: portrait touchpad, on-screen keyboard, TV remote, a 3x4 shortcut grid with profiles and text/macro tiles, typing text from your phone. You edit shortcuts on the board or from your phone (QR and session code). Up to 4 devices, one at a time; pairing is confirmed on the board.\n"
                          "Needs: an SD card (profiles; without it the pairing is not remembered); WiFi from K-OS only for editing from the phone. Without a K-OS calibration it offers its own at start.\n"
                          "Limits: the board sends key codes, so you set the keyboard layout per device; one-finger touchpad; on iPhone the mouse works only with AssistiveTouch; the editing page is plain http. The card holds the pairing keys - protect it. Only for your own devices."),
    "subs.bin": m("K-OS Subs", "licznik subow YouTube; BETA, NIESPRAWDZONE", "0.2.0-beta", A, "Piotr Korona",
                          "Licznik subskrypcji i wyswietlen do pieciu kanalow YouTube na animowanej tablicy klapkowej, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byl jeszcze uruchomiony na plytce.\n"
                          "Umie: cztery widoki (tablica, duzy kanal, cel z paskiem, wykres 7/30 dni), motywy jak K-OS albo Burza, Swit, Neon, przewijanie kanalow; kanaly, klucz i wyglad ustawiasz z telefonu (QR) albo w menu.\n"
                          "Potrzebne: WiFi z K-OS i WLASNY darmowy klucz YouTube Data API v3 (instrukcja krok po kroku na plytce); karta SD na ustawienia i historie. Bez serwera - plytka pyta YouTube sama, co 30 min.\n"
                          "Ograniczenia: klucz lezy na karcie jawnym tekstem i jedzie z telefonu zwyklym http - wpisuj go tylko w zaufanej sieci; YouTube zaokragla liczby subskrypcji; bez Instagrama i TikToka.",
                          opis_en="YouTube subscriber counter; BETA, UNTESTED",
                          info_en="A subscriber and view counter for up to five YouTube channels on an animated split-flap board, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet.\n"
                          "Features: four views (board, big channel, goal with a bar, 7/30-day chart), K-OS theme or Storm, Dawn, Neon, channel rotation; channels, key and look are set from your phone (QR) or in the menu.\n"
                          "Needs: WiFi from K-OS and your OWN free YouTube Data API v3 key (step-by-step guide on the board); an SD card for settings and history. No server - the board asks YouTube itself, every 30 min.\n"
                          "Limits: the key is stored on the card in plain text and travels from the phone over plain http - enter it only on a trusted network; YouTube rounds subscriber counts; no Instagram or TikTok."),
    ("cyd28", "subs.bin"): m("K-OS Subs", "licznik subow YouTube; BETA, NIESPRAWDZONE", "0.2.0-beta", A, "Piotr Korona",
                          "Licznik subskrypcji i wyswietlen do pieciu kanalow YouTube na animowanej tablicy klapkowej, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byl jeszcze uruchomiony na plytce, na 2.8\" tez nie.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: cztery widoki (tablica, duzy kanal, cel z paskiem, wykres 7/30 dni), motywy jak K-OS albo Burza, Swit, Neon, przewijanie kanalow; kanaly, klucz i wyglad ustawiasz z telefonu (QR) albo w menu.\n"
                          "Potrzebne: WiFi z K-OS i WLASNY darmowy klucz YouTube Data API v3 (instrukcja krok po kroku na plytce); karta SD na ustawienia i historie. Bez serwera - plytka pyta YouTube sama, co 30 min.\n"
                          "Ograniczenia: klucz lezy na karcie jawnym tekstem i jedzie z telefonu zwyklym http - wpisuj go tylko w zaufanej sieci; YouTube zaokragla liczby subskrypcji; bez Instagrama i TikToka.",
                          opis_en="YouTube subscriber counter; BETA, UNTESTED",
                          info_en="A subscriber and view counter for up to five YouTube channels on an animated split-flap board, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet, not on the 2.8\" either.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: four views (board, big channel, goal with a bar, 7/30-day chart), K-OS theme or Storm, Dawn, Neon, channel rotation; channels, key and look are set from your phone (QR) or in the menu.\n"
                          "Needs: WiFi from K-OS and your OWN free YouTube Data API v3 key (step-by-step guide on the board); an SD card for settings and history. No server - the board asks YouTube itself, every 30 min.\n"
                          "Limits: the key is stored on the card in plain text and travels from the phone over plain http - enter it only on a trusted network; YouTube rounds subscriber counts; no Instagram or TikTok."),
    ("cyd28s", "subs.bin"): m("K-OS Subs", "licznik subow YouTube; BETA, NIESPRAWDZONE", "0.2.0-beta", A, "Piotr Korona",
                          "Licznik subskrypcji i wyswietlen do pieciu kanalow YouTube na animowanej tablicy klapkowej, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byl jeszcze uruchomiony na plytce, na tej plytce tez nie.\n"
                          "Plytka: CYD 2.8\" z panelem ST7789 (dwa gniazda USB).\n"
                          "Umie: cztery widoki (tablica, duzy kanal, cel z paskiem, wykres 7/30 dni), motywy jak K-OS albo Burza, Swit, Neon, przewijanie kanalow; kanaly, klucz i wyglad ustawiasz z telefonu (QR) albo w menu.\n"
                          "Potrzebne: WiFi z K-OS i WLASNY darmowy klucz YouTube Data API v3 (instrukcja krok po kroku na plytce); karta SD na ustawienia i historie. Bez serwera - plytka pyta YouTube sama, co 30 min.\n"
                          "Ograniczenia: klucz lezy na karcie jawnym tekstem i jedzie z telefonu zwyklym http - wpisuj go tylko w zaufanej sieci; YouTube zaokragla liczby subskrypcji; bez Instagrama i TikToka.",
                          opis_en="YouTube subscriber counter; BETA, UNTESTED",
                          info_en="A subscriber and view counter for up to five YouTube channels on an animated split-flap board, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet, not on this board either.\n"
                          "Board: CYD 2.8\" with the ST7789 panel (two USB sockets).\n"
                          "Features: four views (board, big channel, goal with a bar, 7/30-day chart), K-OS theme or Storm, Dawn, Neon, channel rotation; channels, key and look are set from your phone (QR) or in the menu.\n"
                          "Needs: WiFi from K-OS and your OWN free YouTube Data API v3 key (step-by-step guide on the board); an SD card for settings and history. No server - the board asks YouTube itself, every 30 min.\n"
                          "Limits: the key is stored on the card in plain text and travels from the phone over plain http - enter it only on a trusted network; YouTube rounds subscriber counts; no Instagram or TikTok."),
    "monitor.bin": m("K-OS Monitor", "monitor komputera (LHM); BETA, NIESPRAWDZONE", "0.1.0-beta", A, "Piotr Korona",
                          "Monitor komputera na biurku: CPU, GPU, RAM, dysk i siec z LibreHardwareMonitor (Windows) na kafelkach, wykresach i jako duza liczba, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byl jeszcze uruchomiony na plytce.\n"
                          "Umie: obciazenie, temperatura i takt CPU, GPU z VRAM, RAM, dysk, wysylanie i pobieranie; kolory progow; wykresy 5 min; duza liczba dowolnego czujnika (ulubione). Do 3 komputerow; szukanie LHM w sieci, adres z klawiatury albo z telefonu (QR i kod sesji). Odswiezanie co 1, 2 albo 5 s. Jasny komunikat z instrukcja, gdy PC wylaczony albo LHM bez serwera WWW.\n"
                          "Potrzebne: LibreHardwareMonitor na PC z Options -> Remote Web Server -> Run (port 8085, zgoda zapory Windows), WiFi z K-OS, karta SD na ustawienia.\n"
                          "Ograniczenia: tylko Windows (LHM); zwykle http w Twojej sieci; haslo LHM (jesli wlaczone) lezy na karcie jawnym tekstem.",
                          opis_en="PC monitor (LHM); BETA, UNTESTED",
                          info_en="A desk PC monitor: CPU, GPU, RAM, disk and network from LibreHardwareMonitor (Windows) as tiles, charts and a big number, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet.\n"
                          "Features: CPU load, temperature and clock, GPU with VRAM, RAM, disk, upload and download; threshold colours; 5-minute charts; a big number for any sensor (favourites). Up to 3 computers; LHM search on the network, address from the keyboard or from a phone (QR and session code). Refresh every 1, 2 or 5 s. Clear help when the PC or the LHM web server is off.\n"
                          "Needs: LibreHardwareMonitor on the PC with Options -> Remote Web Server -> Run (port 8085, allowed by the Windows firewall), WiFi from K-OS, an SD card for the settings.\n"
                          "Limits: Windows only (LHM); plain http in your network; the LHM password (if on) is stored on the card as plain text."),
    ("cyd28", "monitor.bin"): m("K-OS Monitor", "monitor komputera (LHM); BETA, NIESPRAWDZONE", "0.1.0-beta", A, "Piotr Korona",
                          "Monitor komputera na biurku: CPU, GPU, RAM, dysk i siec z LibreHardwareMonitor (Windows) na kafelkach, wykresach i jako duza liczba, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byl jeszcze uruchomiony na plytce, na 2.8\" tez nie.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: obciazenie, temperatura i takt CPU, GPU z VRAM, RAM, dysk, wysylanie i pobieranie; kolory progow; wykresy 5 min; duza liczba dowolnego czujnika (ulubione). Do 3 komputerow; szukanie LHM w sieci, adres z klawiatury albo z telefonu (QR i kod sesji). Odswiezanie co 1, 2 albo 5 s. Jasny komunikat z instrukcja, gdy PC wylaczony albo LHM bez serwera WWW.\n"
                          "Potrzebne: LibreHardwareMonitor na PC z Options -> Remote Web Server -> Run (port 8085, zgoda zapory Windows), WiFi z K-OS, karta SD na ustawienia. Bez kalibracji z K-OS zaproponuje wlasna przy starcie.\n"
                          "Ograniczenia: tylko Windows (LHM); zwykle http w Twojej sieci; haslo LHM (jesli wlaczone) lezy na karcie jawnym tekstem.",
                          opis_en="PC monitor (LHM); BETA, UNTESTED",
                          info_en="A desk PC monitor: CPU, GPU, RAM, disk and network from LibreHardwareMonitor (Windows) as tiles, charts and a big number, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet, on 2.8\" neither.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: CPU load, temperature and clock, GPU with VRAM, RAM, disk, upload and download; threshold colours; 5-minute charts; a big number for any sensor (favourites). Up to 3 computers; LHM search on the network, address from the keyboard or from a phone (QR and session code). Refresh every 1, 2 or 5 s. Clear help when the PC or the LHM web server is off.\n"
                          "Needs: LibreHardwareMonitor on the PC with Options -> Remote Web Server -> Run (port 8085, allowed by the Windows firewall), WiFi from K-OS, an SD card for the settings. Without a K-OS calibration it offers its own at start.\n"
                          "Limits: Windows only (LHM); plain http in your network; the LHM password (if on) is stored on the card as plain text."),
    ("cyd28s", "monitor.bin"): m("K-OS Monitor", "monitor komputera (LHM); BETA, NIESPRAWDZONE", "0.1.0-beta", A, "Piotr Korona",
                          "Monitor komputera na biurku: CPU, GPU, RAM, dysk i siec z LibreHardwareMonitor (Windows) na kafelkach, wykresach i jako duza liczba, po polsku i po angielsku.\n"
                          "Stan: BETA, NIESPRAWDZONE - nie byl jeszcze uruchomiony na plytce, na tej rewizji tez nie.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: obciazenie, temperatura i takt CPU, GPU z VRAM, RAM, dysk, wysylanie i pobieranie; kolory progow; wykresy 5 min; duza liczba dowolnego czujnika (ulubione). Do 3 komputerow; szukanie LHM w sieci, adres z klawiatury albo z telefonu (QR i kod sesji). Odswiezanie co 1, 2 albo 5 s. Jasny komunikat z instrukcja, gdy PC wylaczony albo LHM bez serwera WWW.\n"
                          "Potrzebne: LibreHardwareMonitor na PC z Options -> Remote Web Server -> Run (port 8085, zgoda zapory Windows), WiFi z K-OS, karta SD na ustawienia. Bez kalibracji z K-OS zaproponuje wlasna przy starcie.\n"
                          "Ograniczenia: tylko Windows (LHM); zwykle http w Twojej sieci; haslo LHM (jesli wlaczone) lezy na karcie jawnym tekstem.",
                          opis_en="PC monitor (LHM); BETA, UNTESTED",
                          info_en="A desk PC monitor: CPU, GPU, RAM, disk and network from LibreHardwareMonitor (Windows) as tiles, charts and a big number, in Polish and English.\n"
                          "Status: BETA, UNTESTED - it has not been run on a board yet, on this revision neither.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: CPU load, temperature and clock, GPU with VRAM, RAM, disk, upload and download; threshold colours; 5-minute charts; a big number for any sensor (favourites). Up to 3 computers; LHM search on the network, address from the keyboard or from a phone (QR and session code). Refresh every 1, 2 or 5 s. Clear help when the PC or the LHM web server is off.\n"
                          "Needs: LibreHardwareMonitor on the PC with Options -> Remote Web Server -> Run (port 8085, allowed by the Windows firewall), WiFi from K-OS, an SD card for the settings. Without a K-OS calibration it offers its own at start.\n"
                          "Limits: Windows only (LHM); plain http in your network; the LHM password (if on) is stored on the card as plain text."),
    "gry-vol1.bin":     m("K-OS GAME VOL1",  "6 gier: 2048, Lander i inne", "0.9.2", A, "Piotr Korona",
                          "Tom szesciu gier dla K-OS, po polsku i po angielsku, ekran pionowo, z maskotka Chip-K. Gry wybierasz z kafelkow w menu tomu.\n"
                          "Stan: gry sprawdzone testami na komputerze; opis sklepu nie zawiera zapisu o sprawdzeniu tej wersji na plytce, a liczby klatek na plytce nie mierzono.\n"
                          "Gry: 2048; Lunar Lander (30 poziomow, grawitacja, wiatr, paliwo); Overload (biegacz bez konca: dotkniecie - skok, przytrzymanie - slizg); Punch-Through (w stylu Arkanoida); Payload (w stylu Tetrisa, z premia za ciagly obwod); Longshot (jak daleko doleci, z warsztatem ulepszen i trwalym postepem).\n"
                          "Potrzebne: nic poza plytka - bez sieci. Wyniki, postep i odlozone partie na karcie w /gry/ (bez karty gry dzialaja). Motyw i jezyk z K-OS.\n"
                          "Ograniczenia: w Landerze poziomy od 15 sa bardzo trudne albo niemozliwe. Overload i Longshot nie maja zapisu partii. Pelny wyglad kafelkow wymaga K-OS 0.7.1 lub nowszego.",
                          opis_en="6 games: 2048, Lander & more",
                          info_en="A volume of six games for K-OS, in Polish and English, portrait screen, with the Chip-K mascot. You pick games from tiles in the volume menu.\n"
                          "Status: the games are tested on a computer; the store description has no record of this version being tested on a board, and the frame rate on the board has not been measured.\n"
                          "Games: 2048; Lunar Lander (30 levels, gravity, wind, fuel); Overload (an endless runner: tap - jump, hold - slide); Punch-Through (Arkanoid style); Payload (Tetris style, with a bonus for a continuous circuit); Longshot (how far will it fly, with an upgrade workshop and lasting progress).\n"
                          "Needs: nothing but the board - no network. Scores, progress and saved games on the card in /gry/ (the games run without a card). Theme and language from K-OS.\n"
                          "Limits: in Lander the levels from 15 up are very hard or impossible. Overload and Longshot have no saved games. The full tile look needs K-OS 0.7.1 or newer."),
    "mesh.bin":         m("K-OS Handset",    "komunikator MeshCore po BT; BETA", "0.2.4", A, "Piotr Korona",
                          "Komunikator dla Twojego wezla MeshCore: plytka jest sluchawka, a wezel radiem - lacza sie po Bluetooth LE.\n"
                          "Stan: BETA - ta wersja nie byla jeszcze uruchomiona na plytce; kod protokolu sprawdzony testami na komputerze.\n"
                          "Umie: rozmowy prywatne i kanaly, pisanie klawiatura ekranowa, powiadomienie brzeczykiem i dioda, historia rozmow na karcie. Bez wezla pokazuje ostatnie rozmowy i mowi, dlaczego nie ma polaczenia. PIN i wybor wezla w ustawieniach, 'zapomnij parowanie'. Nieudane wyslanie nie kasuje tekstu.\n"
                          "Potrzebne: wlasny wezel MeshCore z Bluetooth, karta SD (historia w /mesh/). Motyw, jezyk, strefe czasowa i kalibracje bierze z K-OS.\n"
                          "Ograniczenia: wezla nie konfiguruje i nie nadpisuje (tylko odczyt). Nie ma jeszcze konfiguracji wezla, map, zarzadzania kanalami ani wersji poziomej. Wiadomosc niewyslana nie czeka w kolejce.",
                          opis_en="MeshCore messenger over BT; BETA",
                          info_en="A messenger for your own MeshCore node: the board is the handset and the node is the radio - they talk over Bluetooth LE.\n"
                          "Status: BETA - this version has not been run on a board yet; the protocol code is tested on a computer.\n"
                          "Features: private chats and channels, typing on an on-screen keyboard, buzzer and LED notification, chat history on the card. Without a node it shows the last chats and says why there is no connection. PIN and node choice in settings, 'forget pairing'. A failed send does not erase your text.\n"
                          "Needs: your own MeshCore node with Bluetooth, an SD card (history in /mesh/). Theme, language, time zone and calibration come from K-OS.\n"
                          "Limits: it never configures or overwrites the node (read only). There is no node configuration, maps, channel management or landscape version yet. An unsent message does not wait in a queue."),
    ("cyd28", "mesh.bin"): m("K-OS Handset",     "komunikator MeshCore po BT; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Komunikator dla Twojego wezla MeshCore: plytka jest sluchawka, a wezel radiem - lacza sie po Bluetooth LE.\n"
                          "Stan: BETA, NIESPRAWDZONE - na 2.8\" nie byla jeszcze uruchomiona; kod protokolu sprawdzony testami na komputerze.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: rozmowy prywatne i kanaly, pisanie klawiatura ekranowa, powiadomienie brzeczykiem i dioda, historia rozmow na karcie. Bez wezla pokazuje ostatnie rozmowy i mowi, dlaczego nie ma polaczenia. PIN i wybor wezla w ustawieniach, 'zapomnij parowanie'. Nieudane wyslanie nie kasuje tekstu.\n"
                          "Potrzebne: wlasny wezel MeshCore z Bluetooth, karta SD (historia w /mesh/). Motyw, jezyk, strefe czasowa i kalibracje bierze z K-OS.\n"
                          "Ograniczenia: wezla nie konfiguruje i nie nadpisuje (tylko odczyt). Nie ma jeszcze konfiguracji wezla, map, zarzadzania kanalami ani wersji poziomej. Wiadomosc niewyslana nie czeka w kolejce.",
                          opis_en="MeshCore messenger over BT; BETA, UNTESTED",
                          info_en="A messenger for your own MeshCore node: the board is the handset and the node is the radio - they talk over Bluetooth LE.\n"
                          "Status: BETA, UNTESTED - it has not been run on 2.8\" yet; the protocol code is tested on a computer.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: private chats and channels, typing on an on-screen keyboard, buzzer and LED notification, chat history on the card. Without a node it shows the last chats and says why there is no connection. PIN and node choice in settings, 'forget pairing'. A failed send does not erase your text.\n"
                          "Needs: your own MeshCore node with Bluetooth, an SD card (history in /mesh/). Theme, language, time zone and calibration come from K-OS.\n"
                          "Limits: it never configures or overwrites the node (read only). There is no node configuration, maps, channel management or landscape version yet. An unsent message does not wait in a queue."),
    ("cyd28s", "mesh.bin"): m("K-OS Handset",    "komunikator MeshCore po BT; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Komunikator dla Twojego wezla MeshCore: plytka jest sluchawka, a wezel radiem - lacza sie po Bluetooth LE.\n"
                          "Stan: BETA, NIESPRAWDZONE - na tej rewizji nie byla jeszcze uruchomiona; kod protokolu sprawdzony testami na komputerze.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: rozmowy prywatne i kanaly, pisanie klawiatura ekranowa, powiadomienie brzeczykiem i dioda, historia rozmow na karcie. Bez wezla pokazuje ostatnie rozmowy i mowi, dlaczego nie ma polaczenia. PIN i wybor wezla w ustawieniach, 'zapomnij parowanie'. Nieudane wyslanie nie kasuje tekstu.\n"
                          "Potrzebne: wlasny wezel MeshCore z Bluetooth, karta SD (historia w /mesh/). Motyw, jezyk, strefe czasowa i kalibracje bierze z K-OS.\n"
                          "Ograniczenia: wezla nie konfiguruje i nie nadpisuje (tylko odczyt). Nie ma jeszcze konfiguracji wezla, map, zarzadzania kanalami ani wersji poziomej. Wiadomosc niewyslana nie czeka w kolejce.",
                          opis_en="MeshCore messenger over BT; BETA, UNTESTED",
                          info_en="A messenger for your own MeshCore node: the board is the handset and the node is the radio - they talk over Bluetooth LE.\n"
                          "Status: BETA, UNTESTED - it has not been run on this revision yet; the protocol code is tested on a computer.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: private chats and channels, typing on an on-screen keyboard, buzzer and LED notification, chat history on the card. Without a node it shows the last chats and says why there is no connection. PIN and node choice in settings, 'forget pairing'. A failed send does not erase your text.\n"
                          "Needs: your own MeshCore node with Bluetooth, an SD card (history in /mesh/). Theme, language, time zone and calibration come from K-OS.\n"
                          "Limits: it never configures or overwrites the node (read only). There is no node configuration, maps, channel management or landscape version yet. An unsent message does not wait in a queue."),
    "marauder.bin":     m("Marauder",        "audyt WiFi / BLE", "1.4.3", Z, "justcallmekoko / Fr4nkFletcher",
                          "ESP32 Marauder - audyt WiFi i Bluetooth LE: skan sieci i urzadzen BLE, podsluch ruchu, testy wlasnej sieci. Program zewnetrzny.\n"
                          "Stan: opis sklepu nie zawiera zapisu o sprawdzeniu tej binarki na plytce.\n"
                          "Potrzebne: nic poza plytka. Ustawienia trzyma w SPIFFS - dzieki migawkom K-OS zostaja miedzy startami.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autorzy: justcallmekoko / Fr4nkFletcher. Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi / BLE auditing",
                          info_en="ESP32 Marauder - WiFi and Bluetooth LE auditing: scanning networks and BLE devices, sniffing, testing your own network. A third-party program.\n"
                          "Status: the store description has no record of this binary being tested on a board.\n"
                          "Needs: nothing but the board. Settings live in SPIFFS - thanks to the K-OS snapshots they survive between starts.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Authors: justcallmekoko / Fr4nkFletcher. Image prepared for K-OS: RST returns to the menu."),
    "bruce.bin":        m("Bruce (LITE)",    "pentest WiFi / BLE / IR / RF", "lite", Z, "pr3y",
                          "Bruce - wieloprotokolowy zestaw do testow bezpieczenstwa (WiFi, BLE, IR, RF), wariant LITE. Program zewnetrzny, zbudowany dla CYD 2.4\" z poprawionymi kolorami.\n"
                          "Stan: opis sklepu nie zawiera zapisu o sprawdzeniu tej binarki na plytce.\n"
                          "Potrzebne: nic poza plytka; moduly IR i RF dokladasz sam. Pierwszy start prosi o kalibracje dotyku w czterech rogach (w poziomie); po zmianie Config > Orientation Bruce pyta o nia raz dla nowego ukladu i ja pamieta (K-OS trzyma to w migawce).\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autor: pr3y (projekt Bruce). Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi / BLE / IR / RF pentest",
                          info_en="Bruce - a multi-protocol security testing toolkit (WiFi, BLE, IR, RF), LITE variant. A third-party program, built for the CYD 2.4\" with corrected colours.\n"
                          "Status: the store description has no record of this binary being tested on a board.\n"
                          "Needs: nothing but the board; you add IR and RF modules yourself. The first start asks for a four-corner touch calibration (landscape); after changing Config > Orientation Bruce asks once for the new layout and remembers it (K-OS keeps it in the snapshot).\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Author: pr3y (the Bruce project). Image prepared for K-OS: RST returns to the menu."),
    ("cyd28", "gry-vol1.bin"): m("K-OS GAME VOL1", "6 gier: 2048, Lander i inne; NIESPRAWDZONE", "0.9.2", A, "Piotr Korona",
                          "Tom szesciu gier dla K-OS, po polsku i po angielsku, ekran pionowo, z maskotka Chip-K.\n"
                          "Stan: NIESPRAWDZONE - tej binarki na 2.8\" nikt jeszcze nie zglosil jako uruchomionej.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Gry: 2048, Lunar Lander, Overload (biegacz), Punch-Through (w stylu Arkanoida), Payload (w stylu Tetrisa), Longshot (jak daleko doleci). Te same co na 2.4\".\n"
                          "Potrzebne: nic poza plytka - bez sieci. Wyniki i postep na karcie w /gry/. Kalibracje dotyku bierze z K-OS; gdy dla tej plytki nie ma jej na karcie, mowi o tym na starcie zamiast zgadywac. Motyw i jezyk z K-OS.\n"
                          "Ograniczenia: pelny wyglad kafelkow wymaga K-OS 0.7.1 lub nowszego.",
                          opis_en="6 games: 2048, Lander & more; UNTESTED",
                          info_en="A volume of six games for K-OS, in Polish and English, portrait screen, with the Chip-K mascot.\n"
                          "Status: UNTESTED - nobody has reported running this binary on 2.8\" yet.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Games: 2048, Lunar Lander, Overload (a runner), Punch-Through (Arkanoid style), Payload (Tetris style), Longshot (how far will it fly). The same as on 2.4\".\n"
                          "Needs: nothing but the board - no network. Scores and progress on the card in /gry/. Touch calibration comes from K-OS; when the card has none for this board, it says so at start instead of guessing. Theme and language from K-OS.\n"
                          "Limits: the full tile look needs K-OS 0.7.1 or newer."),
    ("cyd28", "office.bin"): m("K-OS Office",   "notatnik, kalkulator, pliki; BETA, NIESPRAWDZONE", "1.3.2", A, "Piotr Korona",
                          "Pakiet biurowy pod palec, po polsku i po angielsku: notatnik, kalkulator, kalendarz, menedzer plikow, kody QR, kursy walut.\n"
                          "Stan: BETA, NIESPRAWDZONE - na 2.8\" nie byl jeszcze uruchomiony.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: to samo co na 2.4\" - notatki pisane tez z przegladarki, kalkulator z tasma, kalendarz z zegarem NTP, dwupanelowy menedzer plikow, kody QR, stoper i minutnik, przelicznik jednostek, kursy NBP.\n"
                          "Potrzebne: karta SD (dane w /office/); WiFi do kursow, zegara i pisania z komputera. Motyw, jezyk, sieci, strefe czasowa i kalibracje bierze z K-OS. Bez pliku /korona/cyd28/dotyk.txt pokazuje ostrzezenie i proponuje kalibracje czterech rogow - liczy sie dowolne dotkniecie.\n"
                          "Ograniczenia: /korona tylko do odczytu; programow .bin z /programy nie kasuje. Kursy i strona notatnika ida zwyklym http.",
                          opis_en="notes, calculator, files; BETA, UNTESTED",
                          info_en="An office suite for your fingertip, in Polish and English: notes, calculator, calendar, file manager, QR codes, exchange rates.\n"
                          "Status: BETA, UNTESTED - it has not been run on 2.8\" yet.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: the same as on 2.4\" - notes typed from a browser too, a calculator with a tape, a calendar with an NTP clock, a two-panel file manager, QR codes, stopwatch and timer, unit converter, NBP exchange rates.\n"
                          "Needs: an SD card (data in /office/); WiFi for rates, the clock and typing from a computer. Theme, language, networks, time zone and calibration come from K-OS. Without the file /korona/cyd28/dotyk.txt it shows a warning and offers a four-corner calibration - any touch counts.\n"
                          "Limits: /korona is read-only; it does not delete .bin programs in /programy. Rates and the notes page use plain http."),
    ("cyd28", "meteo-pion.bin"): m("Meteo K-OS pion", "pogoda i radar opadow IMGW; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Stacja pogodowa pod palec, po polsku i po angielsku, ekran pionowo: prognoza z Open-Meteo i radar opadow IMGW.\n"
                          "Stan: BETA, NIESPRAWDZONE - na 2.8\" nie byla jeszcze uruchomiona.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: to samo co na 2.4\" - cztery widoki, stan biezacy, 5 dni, 24 godziny, prognoza co kwadrans, radar IMGW z mapa, tryb offline z karty.\n"
                          "Potrzebne: WiFi (Open-Meteo bez klucza), karta SD (dane w /meteo/; mape /meteo/mapa.bin K-OS od 0.7.8 pobiera sam, ze starszym skopiuj ja ze strony sklepu). Sieci, jezyk, strefe czasowa i kalibracje bierze z K-OS; bez kalibracji dla tej plytki proponuje wlasna.\n"
                          "Mapa: Natural Earth (domena publiczna), GeoNames (CC BY 4.0).",
                          opis_en="weather and IMGW rain radar; BETA, UNTESTED",
                          info_en="A weather station for your fingertip, in Polish and English, portrait screen: an Open-Meteo forecast and the IMGW rain radar.\n"
                          "Status: BETA, UNTESTED - it has not been run on 2.8\" yet.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: the same as on 2.4\" - four views, current conditions, 5 days, 24 hours, a quarter-hourly nowcast, the IMGW radar with a map, offline mode from the card.\n"
                          "Needs: WiFi (Open-Meteo, no key), an SD card (data in /meteo/; K-OS 0.7.8 or newer fetches the map /meteo/mapa.bin itself, with an older one copy it from the store website). Networks, language, time zone and calibration come from K-OS; without a calibration for this board it offers its own.\n"
                          "Map: Natural Earth (public domain), GeoNames (CC BY 4.0)."),
    ("cyd28", "meteo-poziom.bin"): m("Meteo K-OS poziom", "pogoda i radar, poziomo; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Ta sama stacja pogodowa co Meteo K-OS pion, w orientacji poziomej 320x240, z panelem bocznym radaru.\n"
                          "Stan: BETA, NIESPRAWDZONE - na 2.8\" nie byla jeszcze uruchomiona.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: prognoza z Open-Meteo, radar IMGW z mapa, tryb offline z karty.\n"
                          "Potrzebne: WiFi, karta SD (dane w /meteo/; mape /meteo/mapa.bin K-OS od 0.7.8 pobiera sam, ze starszym skopiuj ja ze strony sklepu). Kalibracja dotyku robi sie tu wprost w orientacji poziomej, a nie przez przeliczenie z pionowej.\n"
                          "Mapa: Natural Earth (domena publiczna), GeoNames (CC BY 4.0).",
                          opis_en="weather and radar, landscape; BETA, UNTESTED",
                          info_en="The same weather station as Meteo K-OS portrait, in landscape 320x240, with a radar side panel.\n"
                          "Status: BETA, UNTESTED - it has not been run on 2.8\" yet.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: an Open-Meteo forecast, the IMGW radar with a map, offline mode from the card.\n"
                          "Needs: WiFi, an SD card (data in /meteo/; K-OS 0.7.8 or newer fetches the map /meteo/mapa.bin itself, with an older one copy it from the store website). Touch calibration is done here directly in landscape, not converted from portrait.\n"
                          "Map: Natural Earth (public domain), GeoNames (CC BY 4.0)."),
    ("cyd28", "esp32div.bin"): m("ESP32-DIV",   "multitool WiFi/BLE/RF; NIESPRAWDZONE", "3.3.0", Z, "cifertech / Wontfallo (HaleHound-CYD)",
                          "ESP32-DIV (odmiana HaleHound-CYD): skaner WiFi i BLE, narzedzia RF i NFC. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE - tej binarki nikt jeszcze nie uruchomil; ta sama baza kodu dziala na 2.4\".\n"
                          "Plytka: CYD 2.8\" (2432S028R); obraz z natywnego profilu autora.\n"
                          "Potrzebne: nic poza plytka; moduly RF/NFC dokladasz sam.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autorzy: cifertech / Wontfallo (HaleHound-CYD). Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi/BLE/RF multitool; UNTESTED",
                          info_en="ESP32-DIV (HaleHound-CYD variant): a WiFi and BLE scanner, RF and NFC tools. A third-party program.\n"
                          "Status: UNTESTED - nobody has run this binary yet; the same code base works on 2.4\".\n"
                          "Board: CYD 2.8\" (2432S028R); image from the author's native profile.\n"
                          "Needs: nothing but the board; you add RF/NFC modules yourself.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Authors: cifertech / Wontfallo (HaleHound-CYD). Image prepared for K-OS: RST returns to the menu."),
    ("cyd28", "bruce.bin"): m("Bruce (LITE)",   "pentest WiFi / BLE / IR / RF; NIESPRAWDZONE", "lite", Z, "pr3y",
                          "Bruce - zestaw do testow bezpieczenstwa (WiFi, BLE, IR, RF), wariant LITE. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE - tej binarki nikt jeszcze nie uruchomil. Znane ryzyko: obrot dotyku wzgledem obrazu (kod autora, uzywany przez spolecznosc na 2.8\", u nas niepotwierdzony).\n"
                          "Plytka: CYD 2.8\" (2432S028R); obraz z natywnego profilu autora.\n"
                          "Potrzebne: nic poza plytka; moduly IR i RF dokladasz sam.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autor: pr3y (projekt Bruce). Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi / BLE / IR / RF pentest; UNTESTED",
                          info_en="Bruce - a security testing toolkit (WiFi, BLE, IR, RF), LITE variant. A third-party program.\n"
                          "Status: UNTESTED - nobody has run this binary yet. Known risk: touch rotation versus the picture (the author's code, used by the community on 2.8\", not confirmed by us).\n"
                          "Board: CYD 2.8\" (2432S028R); image from the author's native profile.\n"
                          "Needs: nothing but the board; you add IR and RF modules yourself.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Author: pr3y (the Bruce project). Image prepared for K-OS: RST returns to the menu."),
    ("cyd28", "radar-pion.bin"): m("SkyCYD 4.4.2 pion", "radar samolotow ADS-B; NIESPRAWDZONE; tylko po polsku", "4.4.2", A, "Piotr Korona",
                          "Radar lotniczy: samoloty wokol Twojego domu na mapie, zdjecia samolotow i pogoda. Ekran pionowo 240x320.\n"
                          "Stan: NIESPRAWDZONE - tej binarki nikt jeszcze nie uruchomil. Zewnetrzny tester uzywal na 2432S028R poprzedniej wersji: skan sieci w portalu dziala, wydawania adresow telefonowi nie potwierdzono.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: pozycje samolotow z adsb.lol (przez Worker SkyCYD), mapa okolicy, zdjecia maszyn, pogoda.\n"
                          "Potrzebne: WiFi z internetem. Przy pierwszym starcie plytka wystawia wlasny punkt dostepowy z portalem konfiguracji. Kalibracja dotyku 2.8\" jest w portalu (Siec -> Kalibracja dotyku), z podgladem surowego odczytu. Karta SD nie jest uzywana.\n"
                          "Ograniczenia: interfejs tylko po polsku. SkyCYD powstal przed K-OS i nie czyta jego ustawien z karty (motyw, jezyk, kalibracja dotyku).",
                          opis_en="ADS-B aircraft radar; UNTESTED; Polish only",
                          info_en="An aircraft radar: the planes around your home on a map, aircraft photos and the weather. Portrait screen 240x320.\n"
                          "Status: UNTESTED - nobody has run this binary yet. An outside tester used the previous version on a 2432S028R: the network scan in the portal works, handing out an address to the phone is not confirmed.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: aircraft positions from adsb.lol (through the SkyCYD Worker), a map of the area, aircraft photos, weather.\n"
                          "Needs: WiFi with internet. On the first start the board opens its own access point with a setup portal. The 2.8\" touch calibration is in the portal (Network -> Touch calibration), with a live raw reading. The SD card is not used.\n"
                          "Limits: the interface is in Polish only. SkyCYD predates K-OS and does not read its settings from the card (theme, language, touch calibration)."),
    ("cyd28", "radar-poziom.bin"): m("SkyCYD 4.4.2 poziom", "radar ADS-B, poziomo; NIESPRAWDZONE; tylko po polsku", "4.4.2", A, "Piotr Korona",
                          "Ten sam radar lotniczy co SkyCYD pion, w orientacji poziomej 320x240 (oryginalny uklad SkyCYD).\n"
                          "Stan: NIESPRAWDZONE - tej binarki nikt jeszcze nie uruchomil. Zewnetrzny tester uzywal na 2432S028R poprzedniej wersji: skan sieci w portalu dziala, wydawania adresow telefonowi nie potwierdzono.\n"
                          "Plytka: CYD 2.8\" (2432S028R).\n"
                          "Umie: pozycje samolotow z adsb.lol (przez Worker SkyCYD), mapa okolicy, zdjecia maszyn, pogoda.\n"
                          "Potrzebne: WiFi z internetem. Przy pierwszym starcie plytka wystawia wlasny punkt dostepowy z portalem konfiguracji. Kalibracja dotyku 2.8\" jest w portalu (Siec -> Kalibracja dotyku), osobna od wersji pionowej. Karta SD nie jest uzywana.\n"
                          "Ograniczenia: interfejs tylko po polsku. SkyCYD powstal przed K-OS i nie czyta jego ustawien z karty (motyw, jezyk, kalibracja dotyku).",
                          opis_en="ADS-B radar, landscape; UNTESTED; Polish only",
                          info_en="The same aircraft radar as SkyCYD portrait, in landscape 320x240 (the original SkyCYD layout).\n"
                          "Status: UNTESTED - nobody has run this binary yet. An outside tester used the previous version on a 2432S028R: the network scan in the portal works, handing out an address to the phone is not confirmed.\n"
                          "Board: CYD 2.8\" (2432S028R).\n"
                          "Features: aircraft positions from adsb.lol (through the SkyCYD Worker), a map of the area, aircraft photos, weather.\n"
                          "Needs: WiFi with internet. On the first start the board opens its own access point with a setup portal. The 2.8\" touch calibration is in the portal (Network -> Touch calibration), separate from the portrait version. The SD card is not used.\n"
                          "Limits: the interface is in Polish only. SkyCYD predates K-OS and does not read its settings from the card (theme, language, touch calibration)."),
    ("cyd28s", "gry-vol1.bin"): m("K-OS GAME VOL1", "6 gier: 2048, Lander i inne; NIESPRAWDZONE", "0.9.2", A, "Piotr Korona",
                          "Tom szesciu gier dla K-OS, po polsku i po angielsku, ekran pionowo, z maskotka Chip-K.\n"
                          "Stan: NIESPRAWDZONE - na tej rewizji nikt jeszcze nie uruchomil tej binarki.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Gry: 2048, Lunar Lander, Overload (biegacz), Punch-Through (w stylu Arkanoida), Payload (w stylu Tetrisa), Longshot (jak daleko doleci). Te same co na 2.4\".\n"
                          "Potrzebne: nic poza plytka - bez sieci. Wyniki i postep na karcie w /gry/. Kalibracje dotyku bierze z K-OS (/korona/cyd28s/dotyk.txt); gdy jej nie ma, mowi o tym na starcie zamiast zgadywac. Motyw i jezyk z K-OS.\n"
                          "Ograniczenia: pelny wyglad kafelkow wymaga K-OS 0.7.1 lub nowszego.",
                          opis_en="6 games: 2048, Lander & more; UNTESTED",
                          info_en="A volume of six games for K-OS, in Polish and English, portrait screen, with the Chip-K mascot.\n"
                          "Status: UNTESTED - nobody has run this binary on this revision yet.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Games: 2048, Lunar Lander, Overload (a runner), Punch-Through (Arkanoid style), Payload (Tetris style), Longshot (how far will it fly). The same as on 2.4\".\n"
                          "Needs: nothing but the board - no network. Scores and progress on the card in /gry/. Touch calibration comes from K-OS (/korona/cyd28s/dotyk.txt); when there is none, it says so at start instead of guessing. Theme and language from K-OS.\n"
                          "Limits: the full tile look needs K-OS 0.7.1 or newer."),
    ("cyd28s", "office.bin"): m("K-OS Office",  "notatnik, kalkulator, pliki; BETA, NIESPRAWDZONE", "1.3.2", A, "Piotr Korona",
                          "Pakiet biurowy pod palec, po polsku i po angielsku: notatnik, kalkulator, kalendarz, menedzer plikow, kody QR, kursy walut.\n"
                          "Stan: BETA, NIESPRAWDZONE - na tej rewizji nie byl jeszcze uruchomiony. Jesli obraz wyjdzie negatywem albo z zamienionym czerwonym i niebieskim, napisz - to poprawka jednej flagi.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB, czasem opisywana jako v3).\n"
                          "Umie: to samo co na 2.4\" - notatki pisane tez z przegladarki, kalkulator z tasma, kalendarz z zegarem NTP, dwupanelowy menedzer plikow, kody QR, stoper i minutnik, przelicznik jednostek, kursy NBP.\n"
                          "Potrzebne: karta SD (dane w /office/); WiFi do kursow, zegara i pisania z komputera. Motyw, jezyk, sieci, strefe czasowa i kalibracje (/korona/cyd28s/dotyk.txt) bierze z K-OS.\n"
                          "Ograniczenia: /korona tylko do odczytu; programow .bin z /programy nie kasuje. Kursy i strona notatnika ida zwyklym http.",
                          opis_en="notes, calculator, files; BETA, UNTESTED",
                          info_en="An office suite for your fingertip, in Polish and English: notes, calculator, calendar, file manager, QR codes, exchange rates.\n"
                          "Status: BETA, UNTESTED - it has not been run on this revision yet. If the picture comes out as a negative or with red and blue swapped, tell us - it is a one-flag fix.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets, sometimes sold as v3).\n"
                          "Features: the same as on 2.4\" - notes typed from a browser too, a calculator with a tape, a calendar with an NTP clock, a two-panel file manager, QR codes, stopwatch and timer, unit converter, NBP exchange rates.\n"
                          "Needs: an SD card (data in /office/); WiFi for rates, the clock and typing from a computer. Theme, language, networks, time zone and calibration (/korona/cyd28s/dotyk.txt) come from K-OS.\n"
                          "Limits: /korona is read-only; it does not delete .bin programs in /programy. Rates and the notes page use plain http."),
    ("cyd28s", "meteo-pion.bin"): m("Meteo K-OS pion", "pogoda i radar opadow IMGW; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Stacja pogodowa pod palec, po polsku i po angielsku, ekran pionowo: prognoza z Open-Meteo i radar opadow IMGW.\n"
                          "Stan: BETA, NIESPRAWDZONE - na tej rewizji nie byla jeszcze uruchomiona. Jesli obraz wyjdzie negatywem albo z zamienionym czerwonym i niebieskim, napisz - to poprawka jednej flagi.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: to samo co na 2.4\" - cztery widoki, stan biezacy, 5 dni, 24 godziny, prognoza co kwadrans, radar IMGW z mapa, tryb offline z karty.\n"
                          "Potrzebne: WiFi (Open-Meteo bez klucza), karta SD (dane w /meteo/; mape /meteo/mapa.bin K-OS od 0.7.8 pobiera sam, ze starszym skopiuj ja ze strony sklepu). Sieci, jezyk, strefe czasowa i kalibracje bierze z K-OS.\n"
                          "Mapa: Natural Earth (domena publiczna), GeoNames (CC BY 4.0).",
                          opis_en="weather and IMGW rain radar; BETA, UNTESTED",
                          info_en="A weather station for your fingertip, in Polish and English, portrait screen: an Open-Meteo forecast and the IMGW rain radar.\n"
                          "Status: BETA, UNTESTED - it has not been run on this revision yet. If the picture comes out as a negative or with red and blue swapped, tell us - it is a one-flag fix.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: the same as on 2.4\" - four views, current conditions, 5 days, 24 hours, a quarter-hourly nowcast, the IMGW radar with a map, offline mode from the card.\n"
                          "Needs: WiFi (Open-Meteo, no key), an SD card (data in /meteo/; K-OS 0.7.8 or newer fetches the map /meteo/mapa.bin itself, with an older one copy it from the store website). Networks, language, time zone and calibration come from K-OS.\n"
                          "Map: Natural Earth (public domain), GeoNames (CC BY 4.0)."),
    ("cyd28s", "meteo-poziom.bin"): m("Meteo K-OS poziom", "pogoda i radar, poziomo; BETA, NIESPRAWDZONE", "0.2.4", A, "Piotr Korona",
                          "Ta sama stacja pogodowa co Meteo K-OS pion, w orientacji poziomej 320x240, z panelem bocznym radaru.\n"
                          "Stan: BETA, NIESPRAWDZONE - na tej rewizji nie byla jeszcze uruchomiona.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: prognoza z Open-Meteo, radar IMGW z mapa, tryb offline z karty.\n"
                          "Potrzebne: WiFi, karta SD (dane w /meteo/; mape /meteo/mapa.bin K-OS od 0.7.8 pobiera sam, ze starszym skopiuj ja ze strony sklepu). Kalibracja dotyku robi sie tu wprost w orientacji poziomej, bo kalibracja z pionu dalaby rozciagniecie zamiast obrotu.\n"
                          "Mapa: Natural Earth (domena publiczna), GeoNames (CC BY 4.0).",
                          opis_en="weather and radar, landscape; BETA, UNTESTED",
                          info_en="The same weather station as Meteo K-OS portrait, in landscape 320x240, with a radar side panel.\n"
                          "Status: BETA, UNTESTED - it has not been run on this revision yet.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: an Open-Meteo forecast, the IMGW radar with a map, offline mode from the card.\n"
                          "Needs: WiFi, an SD card (data in /meteo/; K-OS 0.7.8 or newer fetches the map /meteo/mapa.bin itself, with an older one copy it from the store website). Touch calibration is done here directly in landscape, because a portrait calibration would stretch instead of rotate.\n"
                          "Map: Natural Earth (public domain), GeoNames (CC BY 4.0)."),
    ("cyd28s", "radar-pion.bin"): m("SkyCYD 4.4.2 pion", "radar samolotow ADS-B; NIESPRAWDZONE; tylko po polsku", "4.4.2", A, "Piotr Korona",
                          "Radar lotniczy: samoloty wokol Twojego domu na mapie, zdjecia samolotow i pogoda. Ekran pionowo 240x320.\n"
                          "Stan: NIESPRAWDZONE - na tej rewizji nikt jeszcze nie uruchomil SkyCYD. Gdyby obraz wyszedl negatywem, przelaczysz to w menu radaru (ustawienia -> inwersja).\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: pozycje samolotow z adsb.lol (przez Worker SkyCYD), mapa okolicy, zdjecia maszyn, pogoda.\n"
                          "Potrzebne: WiFi z internetem. Przy pierwszym starcie plytka wystawia wlasny punkt dostepowy z portalem konfiguracji. Kalibracja dotyku 2.8\" jest w portalu (Siec -> Kalibracja dotyku). Karta SD nie jest uzywana.\n"
                          "Ograniczenia: interfejs tylko po polsku. SkyCYD powstal przed K-OS i nie czyta jego ustawien z karty (motyw, jezyk, kalibracja dotyku).",
                          opis_en="ADS-B aircraft radar; UNTESTED; Polish only",
                          info_en="An aircraft radar: the planes around your home on a map, aircraft photos and the weather. Portrait screen 240x320.\n"
                          "Status: UNTESTED - nobody has run SkyCYD on this revision yet. If the picture comes out as a negative, you switch it in the radar menu (settings -> inversion).\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: aircraft positions from adsb.lol (through the SkyCYD Worker), a map of the area, aircraft photos, weather.\n"
                          "Needs: WiFi with internet. On the first start the board opens its own access point with a setup portal. The 2.8\" touch calibration is in the portal (Network -> Touch calibration). The SD card is not used.\n"
                          "Limits: the interface is in Polish only. SkyCYD predates K-OS and does not read its settings from the card (theme, language, touch calibration)."),
    ("cyd28s", "radar-poziom.bin"): m("SkyCYD 4.4.2 poziom", "radar ADS-B, poziomo; NIESPRAWDZONE; tylko po polsku", "4.4.2", A, "Piotr Korona",
                          "Ten sam radar lotniczy co SkyCYD pion, w orientacji poziomej 320x240 (oryginalny uklad SkyCYD).\n"
                          "Stan: NIESPRAWDZONE - na tej rewizji nikt jeszcze nie uruchomil SkyCYD. Gdyby obraz wyszedl negatywem, przelaczysz to w menu radaru (ustawienia -> inwersja).\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Umie: pozycje samolotow z adsb.lol (przez Worker SkyCYD), mapa okolicy, zdjecia maszyn, pogoda.\n"
                          "Potrzebne: WiFi z internetem. Przy pierwszym starcie plytka wystawia wlasny punkt dostepowy z portalem konfiguracji. Kalibracja dotyku 2.8\" jest w portalu (Siec -> Kalibracja dotyku), osobna od wersji pionowej. Karta SD nie jest uzywana.\n"
                          "Ograniczenia: interfejs tylko po polsku. SkyCYD powstal przed K-OS i nie czyta jego ustawien z karty (motyw, jezyk, kalibracja dotyku).",
                          opis_en="ADS-B radar, landscape; UNTESTED; Polish only",
                          info_en="The same aircraft radar as SkyCYD portrait, in landscape 320x240 (the original SkyCYD layout).\n"
                          "Status: UNTESTED - nobody has run SkyCYD on this revision yet. If the picture comes out as a negative, you switch it in the radar menu (settings -> inversion).\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Features: aircraft positions from adsb.lol (through the SkyCYD Worker), a map of the area, aircraft photos, weather.\n"
                          "Needs: WiFi with internet. On the first start the board opens its own access point with a setup portal. The 2.8\" touch calibration is in the portal (Network -> Touch calibration), separate from the portrait version. The SD card is not used.\n"
                          "Limits: the interface is in Polish only. SkyCYD predates K-OS and does not read its settings from the card (theme, language, touch calibration)."),
    ("cyd28s", "bruce.bin"): m("Bruce (LITE)",  "pentest WiFi / BLE / IR / RF; NIESPRAWDZONE", "lite", Z, "pr3y",
                          "Bruce - zestaw do testow bezpieczenstwa (WiFi, BLE, IR, RF), wariant LITE. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE - ustawienia ekranu wyprowadzone z kodu biblioteki, nie ze sprawdzenia na plytce. Mozliwe bledy: kolory (negatyw, zamieniony czerwony z niebieskim) albo obraz obrocony o 180 stopni - wtedy dotyk trafia w lustrzane miejsca.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Potrzebne: nic poza plytka; moduly IR i RF dokladasz sam.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autor: pr3y (projekt Bruce). Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi / BLE / IR / RF pentest; UNTESTED",
                          info_en="Bruce - a security testing toolkit (WiFi, BLE, IR, RF), LITE variant. A third-party program.\n"
                          "Status: UNTESTED - the screen settings are derived from the library code, not from a test on a board. Possible faults: colours (negative, red and blue swapped) or a picture rotated by 180 degrees - then touch lands in mirrored places.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Needs: nothing but the board; you add IR and RF modules yourself.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Author: pr3y (the Bruce project). Image prepared for K-OS: RST returns to the menu."),
    ("cyd28s", "esp32div.bin"): m("ESP32-DIV",  "multitool WiFi/BLE/RF; NIESPRAWDZONE", "3.3.0", Z, "cifertech / Wontfallo (HaleHound-CYD)",
                          "ESP32-DIV (odmiana HaleHound-CYD): skaner WiFi i BLE, narzedzia RF i NFC. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE. Negatyw albo zamieniony czerwony z niebieskim to poprawka jednej flagi; dotyk i piny jak w wersji 2.8\".\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB); profil dla tego panelu dopisano tutaj, autor go nie ma.\n"
                          "Potrzebne: nic poza plytka; moduly RF/NFC dokladasz sam.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autorzy: cifertech / Wontfallo (HaleHound-CYD). Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi/BLE/RF multitool; UNTESTED",
                          info_en="ESP32-DIV (HaleHound-CYD variant): a WiFi and BLE scanner, RF and NFC tools. A third-party program.\n"
                          "Status: UNTESTED. A negative picture or swapped red and blue is a one-flag fix; touch and pins as in the 2.8\" version.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets); the profile for this panel was added here, the author does not have one.\n"
                          "Needs: nothing but the board; you add RF/NFC modules yourself.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Authors: cifertech / Wontfallo (HaleHound-CYD). Image prepared for K-OS: RST returns to the menu."),
    ("cyd28", "marauder.bin"): m("Marauder",    "audyt WiFi / BLE; NIESPRAWDZONE", "1.4.3", Z, "justcallmekoko / Fr4nkFletcher",
                          "ESP32 Marauder - audyt WiFi i Bluetooth LE: skan sieci i urzadzen BLE, podsluch ruchu, testy wlasnej sieci. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE - obraz przeszedl tylko kompilacje; kalibracja dotyku do potwierdzenia palcem.\n"
                          "Plytka: CYD 2.8\" (2432S028R) z panelem ILI9341.\n"
                          "Potrzebne: nic poza plytka. Ustawienia w SPIFFS - dzieki migawkom K-OS zostaja miedzy startami.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autorzy: justcallmekoko / Fr4nkFletcher. Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi / BLE auditing; UNTESTED",
                          info_en="ESP32 Marauder - WiFi and Bluetooth LE auditing: scanning networks and BLE devices, sniffing, testing your own network. A third-party program.\n"
                          "Status: UNTESTED - the image has only been compiled; the touch calibration still needs a finger to confirm it.\n"
                          "Board: CYD 2.8\" (2432S028R) with the ILI9341 panel.\n"
                          "Needs: nothing but the board. Settings in SPIFFS - thanks to the K-OS snapshots they survive between starts.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Authors: justcallmekoko / Fr4nkFletcher. Image prepared for K-OS: RST returns to the menu."),
    ("cyd28s", "marauder.bin"): m("Marauder",   "audyt WiFi / BLE; NIESPRAWDZONE", "1.4.3", Z, "justcallmekoko / Fr4nkFletcher",
                          "ESP32 Marauder - audyt WiFi i Bluetooth LE: skan sieci i urzadzen BLE, podsluch ruchu, testy wlasnej sieci. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE. Do obejrzenia: kolory, orientacja obrazu i pasek stanu - Marauder dla ST7789 ma wspolrzedne strojone pod wiekszy ekran, wiec napisy moga byc lekko przesuniete.\n"
                          "Plytka: CYD 2.8\" ST7789 (dwa gniazda USB).\n"
                          "Potrzebne: nic poza plytka. Ustawienia w SPIFFS - dzieki migawkom K-OS zostaja miedzy startami.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autorzy: justcallmekoko / Fr4nkFletcher. Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="WiFi / BLE auditing; UNTESTED",
                          info_en="ESP32 Marauder - WiFi and Bluetooth LE auditing: scanning networks and BLE devices, sniffing, testing your own network. A third-party program.\n"
                          "Status: UNTESTED. Things to look at: colours, image orientation and the status bar - Marauder for the ST7789 uses coordinates tuned for a bigger screen, so text may be slightly shifted.\n"
                          "Board: CYD 2.8\" ST7789 (two USB sockets).\n"
                          "Needs: nothing but the board. Settings in SPIFFS - thanks to the K-OS snapshots they survive between starts.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Authors: justcallmekoko / Fr4nkFletcher. Image prepared for K-OS: RST returns to the menu."),
    "openhasp.bin":     m("openHASP",        "panel Home Assistant, MQTT; NIESPRAWDZONE", "0.7.0", Z, "Francis Van Roie (fvanroie)",
                          "openHASP zamienia plytke w panel dotykowy Home Assistant: strony z przyciskami i widzetami, sterowanie przez MQTT. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE na plytce.\n"
                          "Potrzebne: WiFi i serwer MQTT (zwykle przy Home Assistant). Pierwszy start: punkt dostepowy 'HASP-xxxxxx', haslo 'haspadmin', kalibracja czterech rogow, potem WiFi i MQTT na stronie 192.168.4.1.\n"
                          "Ograniczenia: ekran poziomo; rotacje i inwersje zmienia sie w Configuration - Display. Strony opisuje plik pages.jsonl (LVGL).\n"
                          "Autor: Francis Van Roie (fvanroie), projekt openHASP. Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="Home Assistant touch panel; UNTESTED",
                          info_en="openHASP turns the board into a Home Assistant touch panel: pages with buttons and widgets, control over MQTT. A third-party program.\n"
                          "Status: UNTESTED on a board.\n"
                          "Needs: WiFi and an MQTT server (usually next to Home Assistant). First start: access point 'HASP-xxxxxx', password 'haspadmin', four-corner calibration, then WiFi and MQTT on the page 192.168.4.1.\n"
                          "Limits: landscape screen; rotation and inversion are changed in Configuration - Display. Pages are described in pages.jsonl (LVGL).\n"
                          "Author: Francis Van Roie (fvanroie), the openHASP project. Image prepared for K-OS: RST returns to the menu."),
    "nerdminer.bin":    m("NerdMiner v2",    "kopacz-loteria Bitcoin; NIESPRAWDZONE", "1.8.3", Z, "BitMaker-hub",
                          "NerdMiner v2 - kopacz Bitcoina solo na ESP32 (ok. 60 kH/s): loteria i gadzet ze statystykami, kursem i blokami. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE na plytce.\n"
                          "Potrzebne: WiFi, adres BTC i pool. Pierwszy start: punkt dostepowy 'NerdMinerAP', haslo 'MineYourCoins', portal 192.168.4.1 (pool, adres BTC, jasnosc).\n"
                          "Ograniczenia: po zapisie ustawien plytka wraca do K-OS - uruchom program ponownie; ustawienia zostaja dzieki migawce. Szansa na wykopanie bloku jest znikoma.\n"
                          "Autor: BitMaker-hub (projekt NerdMiner). Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="Bitcoin lottery miner; UNTESTED",
                          info_en="NerdMiner v2 - a solo Bitcoin miner on the ESP32 (about 60 kH/s): a lottery and a statistics gadget with price and blocks. A third-party program.\n"
                          "Status: UNTESTED on a board.\n"
                          "Needs: WiFi, a BTC address and a pool. First start: access point 'NerdMinerAP', password 'MineYourCoins', portal 192.168.4.1 (pool, BTC address, brightness).\n"
                          "Limits: after saving the settings the board goes back to K-OS - start the program again; the settings stay thanks to the snapshot. The chance of mining a block is negligible.\n"
                          "Author: BitMaker-hub (the NerdMiner project). Image prepared for K-OS: RST returns to the menu."),
    "pogoda.bin":       m("Pogoda",          "prognoza pogody, Open-Meteo; NIESPRAWDZONE", "0.1.36", Z, "nicholaswilde",
                          "Stacja pogodowa na LVGL: duza temperatura, ikona pogody, prognoza na 3 dni, wykres godzinowy, motywy. Program zewnetrzny.\n"
                          "Stan: NIESPRAWDZONE na plytce.\n"
                          "Potrzebne: WiFi. Dane z Open-Meteo bez klucza API, lokalizacja po IP albo ze wspolrzednych. Pierwszy start: otwarty punkt dostepowy 'cyd-weather-station-XXXX', portal 192.168.4.1 (WiFi, lokalizacja, strefa czasowa); potem strona http://cyd-weather-station.local/.\n"
                          "Ograniczenia: po 'zapisz i restart' plytka wraca do K-OS, a autostart wznawia aplikacje.\n"
                          "Autor: nicholaswilde. Obraz przygotowany dla K-OS: RST wraca do menu.",
                          opis_en="weather forecast, Open-Meteo; UNTESTED",
                          info_en="A weather station on LVGL: a big temperature, a weather icon, a 3-day forecast, an hourly chart, themes. A third-party program.\n"
                          "Status: UNTESTED on a board.\n"
                          "Needs: WiFi. Data from Open-Meteo without an API key, location by IP or from coordinates. First start: an open access point 'cyd-weather-station-XXXX', portal 192.168.4.1 (WiFi, location, time zone); then the page http://cyd-weather-station.local/.\n"
                          "Limits: after 'save and restart' the board goes back to K-OS and autostart resumes the application.\n"
                          "Author: nicholaswilde. Image prepared for K-OS: RST returns to the menu."),
    "esp32div.bin":     m("ESP32-DIV",       "multitool WiFi/BLE/RF", "3.3.0", Z, "cifertech / Wontfallo (HaleHound-CYD)",
                          "ESP32-DIV w odmianie HaleHound-CYD: skaner WiFi i BLE, deauth, narzedzia RF i NFC (moduly opcjonalne). Program zewnetrzny, port dla CYD 2.4\".\n"
                          "Stan: sprawdzone na plytce 03.09.2026: start, menu, dotyk, RST wraca do K-OS. Poszczegolnych narzedzi nie opisano jako sprawdzonych.\n"
                          "Potrzebne: nic poza plytka; moduly RF/NFC dokladasz sam.\n"
                          "Ograniczenia: uzywaj tylko wobec wlasnych sieci i urzadzen.\n"
                          "Autorzy: cifertech / Wontfallo (HaleHound-CYD). W porcie dla K-OS dotyk czytany jest przez magistrale ekranu (poprzedni sposob zamrazal plansze startowa).",
                          opis_en="WiFi/BLE/RF multitool",
                          info_en="ESP32-DIV in its HaleHound-CYD variant: a WiFi and BLE scanner, deauth, RF and NFC tools (optional modules). A third-party program, ported for the CYD 2.4\".\n"
                          "Status: tested on a board on 03.09.2026: start, menu, touch, RST returns to K-OS. The individual tools are not described as tested.\n"
                          "Needs: nothing but the board; you add RF/NFC modules yourself.\n"
                          "Limits: use it only on your own networks and devices.\n"
                          "Authors: cifertech / Wontfallo (HaleHound-CYD). In the K-OS port touch is read over the screen bus (the previous way froze the start screen)."),
}

# PLIKI DANYCH PROGRAMOW -> pole "pliki" w katalogu v3 (K-OS >= 0.7.8 pobiera je razem z programem).
# Klucz jak w META: (plytka, plik) albo plik (wszystkie plytki); wartosc: lista (plik w repo, cel na karcie).
# rozmiar i sha256 generator liczy z pliku - recznie wpisana suma rozjechalaby sie przy podmianie danych.
# CEL MUSI PRZEJSC ZASADY K-OS (loader/loader/plikilogika.h), inaczej plytka po cichu pominie wpis -
# dlatego generator sprawdza je tu tak samo (pliki_danych) i przy bledzie NIC nie zapisuje:
#   /<katalog>/<plik> albo /<katalog>/<podkatalog>/<plik>, znaki [A-Za-z0-9._-], najwyzej 39 znakow,
#   zaden czlon nie zaczyna sie ani nie konczy kropka, nie /korona i nie /programy (bez wielkosci liter),
#   nie *.part / *.bak; plik w repo 1 B .. 4 MB; najwyzej 4 pliki na program; sciezka w repo
#   tymi samymi znakami, najwyzej 120 znakow.
# Licencje ida RAZEM z danymi na karte: BSD-3-Clause (Freedoom) wymaga dolaczenia tekstu licencji,
# a CC BY 4.0 (GeoNames w mapie Meteo) - atrybucji.
_DOOM_DANE = [("dane/doom/doom.kwad", "/doom/doom.kwad"),
              ("dane/doom/LICENCJA-FREEDOOM.txt", "/doom/LICENCJA-FREEDOOM.txt")]
_METEO_DANE = [("dane/meteo/mapa.bin", "/meteo/mapa.bin"),
               ("dane/meteo/LICENCJA.txt", "/meteo/LICENCJA-MAPA.txt")]
DANE = {
    "doom.bin": _DOOM_DANE,              # cyd24, cyd28, cyd28s - dane gry wspolne dla plytek
    "meteo-pion.bin": _METEO_DANE,       # obie orientacje Meteo czytaja ten sam /meteo/mapa.bin
    "meteo-poziom.bin": _METEO_DANE,
}
DANE_MAX_PLIKOW = 4                      # = PLIKI_MAX w plikilogika.h
DANE_MAX_ROZMIAR = 4 * 1024 * 1024       # = PLIK_ROZMIAR_MAX
DANE_CEL_MAX = 39                        # = PLIK_CEL_MAX
DANE_ZRODLO_MAX = 120                    # = PLIK_ZRODLO_MAX
_SUMY_DANYCH = {}                        # plik -> (rozmiar, sha256); dane DOOM sa wspolne dla 3 plytek


def _czlon_ok(c):
    return bool(c) and c[0] != "." and c[-1] != "." and all(
        ch.isascii() and (ch.isalnum() or ch in "._-") for ch in c)


def sprawdz_cel(cel):
    """Te same zasady co plikCelOk() w loader/loader/plikilogika.h. Zwraca None albo powod."""
    if not cel.startswith("/") or len(cel) > DANE_CEL_MAX:
        return "cel musi zaczynac sie od / i miec najwyzej %d znakow" % DANE_CEL_MAX
    czlony = cel[1:].split("/")
    if not 2 <= len(czlony) <= 3:
        return "cel to /<katalog>/<plik> albo /<katalog>/<podkatalog>/<plik>"
    if not all(_czlon_ok(c) for c in czlony):
        return "znaki spoza [A-Za-z0-9._-], pusty czlon albo kropka na poczatku/koncu czlonu"
    if czlony[0].lower() in ("korona", "programy"):
        return "/korona i /programy naleza do K-OS"
    if czlony[-1].lower().endswith((".part", ".bak")):
        return ".part i .bak to nazwy robocze zapisu K-OS"
    return None


def pliki_danych(pid, f):
    """Pole "pliki" wpisu v3 (albo None). Blad w tabeli DANE = koniec pracy bez zapisu."""
    lista = DANE.get((pid, f), DANE.get(f))
    if not lista:
        return None
    if len(lista) > DANE_MAX_PLIKOW:
        sys.exit("BLAD: DANE %s/%s: %d plikow, K-OS bierze najwyzej %d. NIC NIE ZAPISANO."
                 % (pid, f, len(lista), DANE_MAX_PLIKOW))
    wynik, cele = [], set()
    for plik, cel in lista:
        powod = sprawdz_cel(cel)
        if not powod and cel.lower() in cele:
            powod = "ten sam cel drugi raz"
        if not powod and (plik.startswith("/") or len(plik) > DANE_ZRODLO_MAX
                          or not all(_czlon_ok(c) for c in plik.split("/"))):
            powod = "zla sciezka pliku w repo (%s)" % plik
        if powod:
            sys.exit("BLAD: DANE %s/%s -> %s: %s. NIC NIE ZAPISANO." % (pid, f, cel, powod))
        if plik not in _SUMY_DANYCH:
            sciezka = os.path.join(ROOT, plik)
            if not os.path.isfile(sciezka):
                sys.exit("BLAD: DANE %s/%s: brak pliku %s w repo. NIC NIE ZAPISANO." % (pid, f, plik))
            with open(sciezka, "rb") as fh:
                dane = fh.read()
            if not 0 < len(dane) <= DANE_MAX_ROZMIAR:
                sys.exit("BLAD: DANE %s: %d B (K-OS bierze 1..%d B). NIC NIE ZAPISANO."
                         % (plik, len(dane), DANE_MAX_ROZMIAR))
            _SUMY_DANYCH[plik] = (len(dane), hashlib.sha256(dane).hexdigest())
        rozmiar, sha = _SUMY_DANYCH[plik]
        cele.add(cel.lower())
        wynik.append({"plik": plik, "cel": cel, "rozmiar": rozmiar, "sha256": sha})
    return wynik
# Pola z <nazwa>.meta.json, ktore trafiaja do katalogu (w tej kolejnosci). Reszta (np. model_b, plytka) zostaje w pliku.
UZYTK_POLA = ("nazwa", "opis", "wersja", "kategoria", "autor", "info", "licencja", "zrodlo", "orientacja", "zgloszono")


# ROZMIAR STAREGO katalog.json (v2) JEST OGRANICZENIEM SPRZETOWYM, NIE ESTETYCZNYM.
# K-OS <= 0.4.6 pobiera go W CALOSCI do Stringa, a potem parsuje do JsonDocument - oba zyja
# w RAM naraz, na plytce bez PSRAM. 08.09.2026 katalog urosl z 22,9 kB do 35,1 kB (dlugie opisy
# nowych programow) i SKLEP NA PLYTCE PRZESTAL DZIALAC. Dlatego generator SAM SIE ZATRZYMUJE, gdy
# v2 przekroczy KATALOG_STOP - i wtedy NIE ZAPISUJE NICZEGO, czyli jeden program za duzo
# zatrzymuje publikacje wszystkich. Od 25.09.2026 (D4) v2 dostaje wiec tylko pola z V2_POLA.
# Katalogi v3 (per plytka) tego sufitu nie maja: K-OS >= 0.4.7 laduje je na karte i parsuje
# strumieniem, a dlugie opisy pobiera dopiero przy otwarciu karty programu.
KATALOG_OSTRZEZ = 20000 # B - powyzej tego glosne ostrzezenie
KATALOG_STOP = 26000    # B - powyzej tego generator konczy sie bledem i nie zapisuje pliku
ROOT = ""               # ustawiane w main()
ZAPISUJ = True          # False przy --sprawdz: nic nie trafia na dysk
NIEAKTUALNE = []        # --sprawdz: pliki, ktore generator zapisalby inaczej, niz leza na dysku

# POLA STAREGO KATALOGU v2 - TYLKO TE, KTORE KTOS NAPRAWDE CZYTA (D4 z PROPOZYCJE-2026-09-24).
# Czytelnicy v2 - sprawdzone w zrodlach loader/ ORAZ w kazdym opublikowanym obrazie K-OS
# (portal/obrazy/*/loader.bin z historii tego repo, 0.3.6 ... 0.7.4):
#   * strona WWW plytki (PAGE_HTML w loader/net.cpp), we wszystkich wydanych K-OS: plik, nazwa,
#     opis (wypisywany WPROST - musi byc napisem, nie obiektem), rozmiar, wersja, kategoria,
#     autor, info, od 0.4.3 takze sha256. WERSJA i SHA256 jada w /fetch (?v= trafia do
#     /korona/<plytka>/wersje.txt, ?s= sprawdza plik po pobraniu), KATEGORIA dzieli liste na
#     autorskie / uzytkownicy / zewnetrzne - bez niej programy Piotra wyladowalyby w "zewnetrzne";
#   * sklep na plytce w K-OS <= 0.4.6 (przed katalogami per plytka) - te same pola;
#   * K-OS >= 0.4.7 tylko w drodze awaryjnej, gdy katalog-<plytka>.json odpowie 404;
#   * portal/zglos.js - samo "plik" (kolizja nazwy zgloszenia z programem w sklepie).
# WYPADAJA: "info" (skrot 200 znakow - tylko tekst doklejany pod opisem na stronie plytki i na
# karcie programu w K-OS <= 0.4.6; to ~6,5 kB z 22,7 kB), "info_pelny" (nie czyta go nic - zero
# wystapien w obrazach K-OS) oraz licencja/zrodlo/orientacja/zgloszono z programow uzytkownikow
# (tez zero wystapien). Pelne opisy dalej leza w info/<plytka>/ i czyta je v3.
# "autor" jest takze tylko wyswietlany, ale kosztuje ~38 B na wpis i jest podpisem autorow portow
# na stronie plytki - zostaje. Wyrzucenie go daje miejsce na kolejne ~7 wpisow.
V2_POLA = ("plik", "rozmiar", "sha256", "nazwa", "opis", "wersja", "kategoria", "autor")


def zapisz(rel, tekst):
    """Zapis pliku wyjsciowego (sciezka wzgledem repo). Przy --sprawdz niczego nie zapisuje,
    tylko porownuje z tym, co lezy na dysku, i notuje roznice w NIEAKTUALNE."""
    sciezka = os.path.join(ROOT, rel)
    if not ZAPISUJ:
        try:
            with open(sciezka, encoding="utf-8") as fh:
                if fh.read() == tekst:
                    return
        except OSError:
            pass
        NIEAKTUALNE.append(rel)
        return
    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    with open(sciezka, "w", encoding="utf-8") as fh:
        fh.write(tekst)


# Limit dlugosci pliku opisu. K-OS czyta go do bufora o stalym rozmiarze i powyzej tego
# i tak ucina - lepiej, zeby uciecie bylo tutaj, swiadome, niz tam, w polowie zdania.
INFO_PLIK_MAX = 2500

# --- ANGIELSKIE JEDNOZDANIOWCE ------------------------------------------------------------
# Opisy sa skladane: TRZON + ewentualny przyrostek o stanie sprawdzenia. Tlumaczymy wiec
# jedno i drugie osobno, zamiast trzydziestu gotowych zdan - inaczej kazda zmiana jednego
# slowa w polskim wymagalaby recznego poprawienia kilku wpisow angielskich.
# NIEZNANY TRZON DAJE PUSTY WYNIK, a nie polski tekst pod etykieta "en": lepiej, zeby K-OS
# napisal "opis tylko po polsku", niz zeby czlowiek czytal nie ten jezyk, nie wiedzac o tym.
TRZON_EN = {
    "2048, Lunar Lander, Overload, Punch-Through, Payload i Longshot":
        "2048, Lunar Lander, Overload, Punch-Through, Payload and Longshot",
    "2048, Lunar Lander, Overload, Punch-Through i Payload":
        "2048, Lunar Lander, Overload, Punch-Through and Payload",
    "audyt WiFi / BLE": "WiFi / BLE auditing",
    "komunikator MeshCore po Bluetooth": "MeshCore messenger over Bluetooth",
    "kopacz-loteria BTC + kurs i bloki": "BTC lottery miner, price and blocks",
    'multitool WiFi/BLE/RF (HaleHound-CYD 2.4")': 'WiFi/BLE/RF multitool (HaleHound-CYD 2.4")',
    "multitool WiFi/BLE/RF": "WiFi/BLE/RF multitool",
    "notatnik, kalkulator, kalendarz, pliki, QR, kursy":
        "notes, calculator, calendar, files, QR, rates",
    "panel dotykowy Home Assistant": "Home Assistant touch panel",
    "pentest toolkit WiFi / BLE / IR / RF": "WiFi / BLE / IR / RF pentest toolkit",
    "pogoda, radar opadow IMGW, 4 widoki": "weather, IMGW rain radar, 4 views",
    "pogoda, radar opadow IMGW": "weather, IMGW rain radar",
    "prognoza pogody, Open-Meteo bez klucza": "weather forecast, Open-Meteo, no key",
    "radar ADS-B, ekran poziomo": "ADS-B radar, landscape screen",
    "radar ADS-B, samoloty wokol domu": "ADS-B radar, planes around your home",
    "radar ADS-B": "ADS-B radar",
}
PRZYROSTEK_EN = {
    '2.8" NIESPRAWDZONE': '2.8" UNTESTED',
    '2.8" NIETESTOWANE':  '2.8" UNTESTED',
    "ST7789 NIESPRAWDZONE": "ST7789 UNTESTED",
    "NIESPRAWDZONE": "UNTESTED",
    "NIETESTOWANY": "UNTESTED",
    "NIETESTOWANE": "UNTESTED",
    # Nie kazdy program ma angielski interfejs. Skoro przy dwujezycznych opis to chwali,
    # to przy jednojezycznych musi to powiedziec wprost - inaczej milczenie klamie.
    "tylko po polsku": "Polish only",
}


def opis_en_auto(pl):
    """Opis PL -> opis EN. Format: TRZON["; " PRZYROSTEK]... - przyrostkow moze byc kilka
    (np. stan sprawdzenia i jezyk interfejsu) i kazdy tlumaczy sie osobno."""
    if not pl:
        return ""
    czesci = pl.split("; ")
    en = TRZON_EN.get(czesci[0].strip())
    if not en:
        return ""
    for ogon in czesci[1:]:
        o = PRZYROSTEK_EN.get(ogon.strip())
        if not o:
            return ""          # nieznany przyrostek - wolimy nic niz polowe po polsku
        en += "; " + o
    return en



def zapisz_info(pid, nazwa_pliku, lang, tekst):
    """Pelny opis na dysk: info/<plytka>/<plik>.<jezyk>.txt. Zwraca sciezke wzgledna albo None.
    ASCII bez ogonkow, bez recznego lamania wierszy - K-OS lamie sam do szerokosci ekranu,
    a pojedynczy znak konca linii jest u niego nowym wierszem."""
    if not tekst:
        return None
    if len(tekst) > INFO_PLIK_MAX:
        tekst = tekst[:INFO_PLIK_MAX].rsplit(" ", 1)[0] + " ..."
    rel = "info/%s/%s.%s.txt" % (pid, nazwa_pliku, lang)
    zapisz(rel, tekst + "\n")
    return rel


def zapisz_zmiany(pid, nazwa_pliku, lang, tekst):
    """Historia zmian na dysk: info/<plytka>/<plik>.zmiany.<jezyk>.txt. Zwraca sciezke albo None.
    BEZ ucinania do INFO_PLIK_MAX - tego pliku K-OS nie czyta, tylko strona sklepu."""
    if not tekst:
        return None
    if not tekst.isascii():
        sys.exit("BLAD: ZMIANY %s/%s (%s): znak spoza ASCII. NIC NIE ZAPISANO." % (pid, nazwa_pliku, lang))
    rel = "info/%s/%s.zmiany.%s.txt" % (pid, nazwa_pliku, lang)
    zapisz(rel, tekst + "\n")
    return rel


def wpis(pid, rel, data, meta):
    """Wpis do STAREGO katalogu v2 - jeden wspolny plik, tylko po polsku, TYLKO pola V2_POLA
    (kto co czyta - komentarz przy V2_POLA). "opis" zostaje zwyklym napisem, bo strona WWW plytki
    w K-OS <= 0.7.6 wypisuje p.opis WPROST. Przy okazji odklada dlugie opisy do info/<plytka>/ -
    z nich korzysta v3 (wpis3), wiec to musi sie dziac dalej, choc v2 ich juz nie wskazuje."""
    e = {"plik": rel, "rozmiar": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    e.update({k: v for k, v in meta.items() if k in V2_POLA})
    nazwa = rel.rsplit("/", 1)[-1]
    zapisz_info(pid, nazwa, "pl", meta.get("info", ""))
    zapisz_info(pid, nazwa, "en", meta.get("info_en", ""))
    return e


def wpis3(pid, rel, data, meta, zmiany=None):
    """Wpis do katalogu v3 - JEDEN PLIK NA PLYTKE, opisy dwujezyczne i BEZ dlugiego tekstu.
    Dlugi opis lezy w info/ i K-OS pobiera go dopiero przy otwarciu karty programu, prosto
    na karte SD. Dzieki temu rozmiar katalogu przestal byc granica - a byl: 08.09.2026
    katalog urosl do 35 kB i sklep na plytce przestal dzialac."""
    nazwa = rel.rsplit("/", 1)[-1]
    e = {"plik": rel, "rozmiar": len(data), "sha256": hashlib.sha256(data).hexdigest(),
         "nazwa": meta.get("nazwa", ""),
         # WERSJA MUSI BYC ZAWSZE: K-OS wpisuje ja w nazwe pliku opisu na karcie i to ona
         # uniewaznia opis po aktualizacji programu. Bez niej opis nigdy by sie nie odswiezyl.
         "wersja": meta.get("wersja") or "0",
         "kategoria": meta.get("kategoria", "zewnetrzne"),
         "autor": meta.get("autor", "")}
    opis = {"pl": meta.get("opis", "")}
    en = meta.get("opis_en") or opis_en_auto(meta.get("opis", ""))
    if en:
        opis["en"] = en
    e["opis"] = opis
    # IKONA PROGRAMU: maska alfa 4-bit 32x32, 512 B, ten sam format co ikony wbudowane
    # w K-OS - rysuje ja ta sama funkcja i bierze kolor z motywu. Robi je tools/ikony.py.
    # Gdy pliku nie ma, K-OS pokazuje kafelek z inicjalami nazwy: zastepnika nie moze
    # zabraknac, a inicjaly odrozniaja programy lepiej niz jeden wspolny znak dla wszystkich.
    ico = rel[:-4] + ".ico"
    if os.path.exists(os.path.join(ROOT, ico)):
        e["ikona"] = ico
    info = {}
    if meta.get("info"):
        info["pl"] = "info/%s/%s.pl.txt" % (pid, nazwa)
    if meta.get("info_en"):
        info["en"] = "info/%s/%s.en.txt" % (pid, nazwa)
    if info:
        e["info"] = info
    # HISTORIA ZMIAN (tools/zmiany.py) - TYLKO v3 i tylko programy sklepu (zmiany = (pl, en) albo None).
    if zmiany:
        zm = {}
        for lang, tekst in zip(("pl", "en"), zmiany):
            sc = zapisz_zmiany(pid, nazwa, lang, tekst)
            if sc:
                zm[lang] = sc
        if zm:
            e["zmiany"] = zm
    # PLIKI DANYCH (tabela DANE) - TYLKO v3; wpis() (v2) ich nie zna, wiec rozmiar v2 sie nie zmienia.
    pliki = pliki_danych(pid, nazwa)
    if pliki:
        e["pliki"] = pliki
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
    global ROOT, ZAPISUJ
    argumenty = sys.argv[1:]
    nieznane = [a for a in argumenty if a != "--sprawdz"]
    if nieznane:
        print("nieznany argument: %s (jest tylko --sprawdz)" % " ".join(nieznane), file=sys.stderr)
        sys.exit(2)
    ZAPISUJ = "--sprawdz" not in argumenty
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ROOT = root
    out = {"sklep": "KORONA", "wersja": 2, "plytki": []}
    v3 = {}                       # pid -> lista wpisow do katalog-<plytka>.json
    for pid, pname in PLYTKI:
        d = os.path.join(root, "bin", pid)
        progs = []
        progs3 = []
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if not f.lower().endswith(".bin"): continue
                p = os.path.join(d, f)
                meta = META.get((pid, f), META.get(f))
                if meta is None: print("UWAGA: brak META, pomijam", pid, f, file=sys.stderr); continue
                with open(p, "rb") as fh: data = fh.read()
                if data[:1] != b"\xe9": print("UWAGA: zly magic (nie obraz ESP32):", p, file=sys.stderr)
                progs.append(wpis(pid, f"bin/{pid}/{f}", data, meta))
                progs3.append(wpis3(pid, f"bin/{pid}/{f}", data, meta, ZMIANY.get((pid, f), ZMIANY.get(f))))
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
                    progs3.append(wpis3(pid, f"bin/{pid}/{UZYTK_DIR}/{f}", data, meta))
        out["plytki"].append({"id": pid, "nazwa": pname, "programy": progs})
        v3[pid] = {"sklep": "KORONA", "wersja": 3, "plytka": pid, "nazwa": pname, "programy": progs3}

    tekst = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    rozmiar = len(tekst.encode("utf-8"))
    n2 = sum(len(p["programy"]) for p in out["plytki"])
    if rozmiar > KATALOG_STOP:
        print("BLAD: katalog.json (v2) ma %d B, a limit to %d B. NIC NIE ZAPISANO.\n"
              "      K-OS <= 0.4.6 pobiera go w calosci do RAM - za duzy plik wywala tam sklep.\n"
              "      v2 ma juz tylko pola V2_POLA; nastepny krok to zamrozenie v2 na obecnej liscie\n"
              "      albo wyrzucenie \"autor\" z V2_POLA (komentarz przy V2_POLA)." % (rozmiar, KATALOG_STOP),
              file=sys.stderr)
        sys.exit(1)
    zapisz("katalog.json", tekst)
    # ZAPAS W v2 - ile wpisow jeszcze wejdzie. Sredni wpis liczony z roznicy miedzy katalogiem
    # z wpisami a samym szkieletem (te same plytki, puste listy), wiec obejmuje wciecia i przecinki.
    szkielet = json.dumps({"sklep": "KORONA", "wersja": 2, "plytki": [
        {"id": p["id"], "nazwa": p["nazwa"], "programy": []} for p in out["plytki"]]},
        ensure_ascii=False, indent=2) + "\n"
    sredni = (rozmiar - len(szkielet.encode("utf-8"))) / n2 if n2 else 0
    print("katalog.json (v2, pola minimalne): %d programow, %d B" % (n2, rozmiar))
    if sredni:
        print("  zapas v2: %d B do sufitu %d = ~%d wpisow po ~%.0f B (do progu ostrzegawczego %d: ~%d)"
              % (KATALOG_STOP - rozmiar, KATALOG_STOP, (KATALOG_STOP - rozmiar) // sredni, sredni,
                 KATALOG_OSTRZEZ, max(0, KATALOG_OSTRZEZ - rozmiar) // sredni))
    # --- format v3: JEDEN PLIK NA PLYTKE + maly spis plytek -------------------------------
    # Plytka pobiera odtad TYLKO swoja liste, a nie wszystkie trzy. Dlugie opisy siedza
    # w info/ i schodza na karte dopiero przy otwarciu karty programu.
    for pid, pname in PLYTKI:
        t3 = json.dumps(v3[pid], ensure_ascii=False, indent=2) + "\n"
        zapisz("katalog-%s.json" % pid, t3)
        print("  katalog-%s.json: %d programow, %d B" % (pid, len(v3[pid]["programy"]),
                                                         len(t3.encode("utf-8"))))
    # Spis plytek - potrzebny K-OS do kafelka "inne plytki". Bez niego trzeba by po to
    # dociagac caly stary katalog.json, czyli dokladnie to, od czego uciekamy.
    zapisz("plytki.json", json.dumps([{"id": i, "nazwa": n} for i, n in PLYTKI],
                                     ensure_ascii=False, indent=2) + "\n")

    zm_n = sum(1 for pid, _ in PLYTKI for e in v3[pid]["programy"] if "zmiany" in e)
    if zm_n:
        print("  historia zmian (v3, pole \"zmiany\"): %d wpisow" % zm_n)
    dane_n = sum(len(e.get("pliki", ())) for pid, _ in PLYTKI for e in v3[pid]["programy"])
    if dane_n:
        print("  pliki danych (v3, pole \"pliki\"): %d wpisow, %d roznych plikow, %d B"
              % (dane_n, len(_SUMY_DANYCH), sum(r for r, _ in _SUMY_DANYCH.values())))
    # --- ile opisow czeka na angielski ---------------------------------------------------
    braki = sum(1 for pid, _ in PLYTKI for e in v3[pid]["programy"] if "en" not in e.get("opis", {}))
    ile = sum(len(v3[pid]["programy"]) for pid, _ in PLYTKI)
    if braki:
        print("  angielski: brakuje %d z %d opisow (K-OS pokaze polski i napisze, ze to zastepstwo)"
              % (braki, ile))

    if rozmiar > KATALOG_OSTRZEZ:
        print("UWAGA: katalog ma %d B (prog ostrzegawczy %d, twardy %d). Zbliza sie do granicy,\n"
              "       przy ktorej sklep na plytce przestaje dzialac." % (rozmiar, KATALOG_OSTRZEZ, KATALOG_STOP),
              file=sys.stderr)

    if not ZAPISUJ:
        if NIEAKTUALNE:
            print("SPRAWDZENIE: nic nie zapisano. NIEAKTUALNE na dysku (%d): %s\n"
                  "             -> uruchom python3 tools/katalog.py i przejrzyj git diff"
                  % (len(NIEAKTUALNE), ", ".join(NIEAKTUALNE)), file=sys.stderr)
            sys.exit(3)
        print("SPRAWDZENIE: nic nie zapisano; wszystkie pliki na dysku sa aktualne.")


if __name__ == "__main__":
    main()
