# -*- coding: ascii -*-
"""HISTORIA ZMIAN PROGRAMOW SKLEPU - pole "zmiany" w katalogu v3 (wariant A z
_przygotowane/opisy/PROPOZYCJA.md, punkt 3). Czyta to tools/katalog.py.

  * Klucz jak w META: plik (wszystkie plytki) albo (plytka, plik) - wpis z plytka ma pierwszenstwo.
  * Wartosc: z([akapity PL], [akapity EN]) - najnowsza wersja NA GORZE, jedna wersja = jeden akapit.
  * Generator zapisuje info/<plytka>/<plik>.zmiany.<pl|en>.txt i dopisuje do wpisu v3
    "zmiany": {"pl": ..., "en": ...}. Do katalog.json (v2) pole NIE trafia (V2_POLA).
  * K-OS tych plikow nie czyta (czyta je tylko portal/sklep.html, "co nowego"), wiec nie ma tu
    limitu INFO_PLIK_MAX. ASCII bez ogonkow, jak wszystkie opisy sklepu.
  * Material wyjsciowy: dlugie opisy "info" z tools/katalog.py przy e164f4d (05.10.2026) - tam
    byly dziennikiem wersji - oraz dawne opisy z historii gita (K-OS Control 0.1.0, be9867b).
    Znaczniki stanu zostaja przy wersjach tak, jak staly w tamtych tekstach.
  * Programy zewnetrzne nie maja tu wpisow: ich opisy nie prowadzily dziennika wersji.
"""


def z(pl, en):
    return ("\n".join(pl), "\n".join(en))


_SKYCYD = z([
    "4.4.2: portal na cudzej plytce - ze zgloszenia zewnetrznego testera, ktory uruchomil 4.4.1 na wlasnej 2432S028R. "
    "SPRAWDZONE NA SPRZECIE: skan sieci w portalu byl zawsze pusty, bo nieskonfigurowana plytka wlaczala sam punkt dostepowy, a skan wymaga interfejsu klienta (do tego wynik skanu byl ignorowany); teraz radio pracuje jako AP+STA i tester widzi 13 sieci zamiast zera. "
    "POPRAWIONE, ALE NIESPRAWDZONE NA SPRZECIE: punkt dostepowy nie rozdawal adresow (softAP() idzie teraz przed softAPConfig(), serwer DHCP jest wlaczany recznie, gdy nie chodzi, a dzierzawa niesie DNS); nazwa AP wychodzila jako SkyCYD-0000, bo MAC czytal sie za wczesnie; reczne wpisanie SSID i hasla odpowiada od razu zamiast po 18 s. "
    "TAKZE NIESPRAWDZONE: kalibracja dotyku 2.8\" przeniesiona z firmware do portalu (Siec -> Kalibracja dotyku), a ekran w menu plytki pokazuje na zywo surowy odczyt przetwornika.",
], [
    "4.4.2: the portal on someone else's board - from an external tester who ran 4.4.1 on his own 2432S028R. "
    "TESTED ON HARDWARE: the network list in the portal was always empty, because an unconfigured board started the access point only, while scanning needs a client interface (and the scan result was ignored on top of that); the radio now runs AP+STA and the tester sees 13 networks instead of none. "
    "FIXED BUT NOT TESTED ON HARDWARE: the access point handed out no addresses (softAP() now runs before softAPConfig(), the DHCP server is started by hand when it is not running, and the lease carries a DNS server); the AP name came out as SkyCYD-0000 because the MAC was read too early; entering SSID and password by hand answers at once instead of after 18 s. "
    "ALSO NOT TESTED: the 2.8\" touch calibration moved from the firmware into the portal (Network -> Touch calibration), and a screen in the board menu shows the raw ADC reading live.",
])

_METEO_SKLEP = ("Sklep 30.09.2026 (bez zmiany programu): K-OS 0.7.8 i nowszy pobiera mape /meteo/mapa.bin (Natural Earth, GeoNames CC BY 4.0) razem z programem, "
                "z kontrola rozmiaru i sumy, i kladzie obok jej licencje. Ze starszym K-OS mape nadal kopiuje sie na karte samemu - bez niej radar jest bez rzek i nazw.",
                "Store 30.09.2026 (no change to the program): K-OS 0.7.8 or newer downloads the map /meteo/mapa.bin (Natural Earth, GeoNames CC BY 4.0) together with the program, "
                "checking its size and checksum, and puts its licence next to it. With an older K-OS you still copy the map to the card yourself - without it the radar has no rivers or names.")
_METEO_024 = ("0.2.4 (BETA - nie byla jeszcze uruchomiona na plytce): strefa czasowa z ustawien K-OS 0.7.6 - zegar idzie za strefa z K-OS, a prognoza dzieli dni wedlug tej samej strefy "
              "(inaczej dni tygodnia przesuwalyby sie o jeden); ze starszym K-OS jak dotad (CET).",
              "0.2.4 (BETA - not yet run on a board): the time zone from the K-OS 0.7.6 settings - the clock follows the K-OS zone and the forecast splits days by the same zone "
              "(otherwise weekdays would shift by one); with an older K-OS as before (CET).")
_METEO_023 = ("0.2.3: binarka w sklepie miala w srodku numer 0.2.1, choc sklep podawal 0.2.3 (wyrownane w 0.2.4).",
              "0.2.3: the binary in the store carried version 0.2.1 inside, although the store said 0.2.3 (aligned in 0.2.4).")
_METEO_021 = ("0.2.1: kilka sieci WiFi - program bierze z karty cala liste zapamietanych sieci (K-OS pamieta ich do szesciu), najpierw skanuje i probuje tylko widocznych, od najmocniejszej. "
              "Dotad kazda niewidoczna siec kosztowala 12 s czekania na starcie. Sieci z ukrytym SSID probuje na koncu.",
              "0.2.1: several WiFi networks - the program takes the whole list of remembered networks from the card (K-OS remembers up to six), scans first and tries only the visible ones, strongest first. "
              "Until then every invisible network cost 12 s of waiting at start. Networks with a hidden SSID are tried last.")

ZMIANY = {
    "radar-pion.bin": _SKYCYD,
    "radar-poziom.bin": _SKYCYD,

    "office.bin": z([
        "1.3.2 (BETA - nie byla jeszcze uruchomiona na plytce): strefa czasowa z ustawien K-OS 0.7.6 zamiast CET na sztywno - zegar i kalendarz ida za strefa wybrana w K-OS; ze starszym K-OS dziala jak dotad (CET).",
        "1.3.1: kilka sieci WiFi. K-OS pamieta do szesciu sieci, a Office bierze je wszystkie z karty, najpierw skanuje i probuje tylko te, ktore naprawde widac, od najmocniejszej. "
        "Dotad kazda niewidoczna siec kosztowala pelne 12 s, wiec przy czterech zapamietanych sieciach start poza domem potrafil trwac minute. Sieci z ukrytym SSID probuje na koncu.",
        "1.2.0: zapis, ktory nie traci danych. Piec miejsc pisalo na karte bez sprawdzenia wyniku albo kasowalo jedyna kopie pliku (najgorsze: notatnik mowil 'zapisane' przy pelnej karcie). "
        "Teraz jeden wzorzec: plik roboczy, sprawdzony kazdy zapis, podmiana przez .bak, a po zaniku zasilania w polowie podmiany plik wraca na miejsce przy nastepnym starcie i program mowi o tym na ekranie. "
        "Do tego dioda RGB (alarm minutnika, koniec kopiowania, blad zapisu, dzialajacy serwer notatek), zegar NTP w kalendarzu synchronizuje sie sam, krotsze czekanie na siec (6 s zamiast 9 s, dotyk przerywa) "
        "i uczciwe komunikaty, gdy K-OS nie udostepnia sieci programom. Numer 1.1.1 (sam numer w binarce, kod jak 1.1.0) nie byl wydany osobno - wszedl w 1.2.0.",
        "Wczesniejsza wersja byla sprawdzona na plytce 2.4\": start, migracja danych ze starej nazwy, motyw i jezyk z K-OS, kalibracja z karty, powrot do K-OS po RST; modulow nie sprawdzano palcem.",
    ], [
        "1.3.2 (BETA - not yet run on a board): the time zone from the K-OS 0.7.6 settings instead of hard-coded CET - the clock and the calendar follow the zone chosen in K-OS; with an older K-OS it works as before (CET).",
        "1.3.1: several WiFi networks. K-OS remembers up to six networks, and Office takes them all from the card, scans first and tries only those that are really visible, strongest first. "
        "Until then every invisible network cost a full 12 s, so with four remembered networks a start away from home could take a minute. Networks with a hidden SSID are tried last.",
        "1.2.0: writing that does not lose data. Five places wrote to the card without checking the result or deleted a file's only copy (worst: the notepad said 'saved' on a full card). "
        "Now one pattern: a work file, every write checked, a swap through .bak, and after a power loss halfway through the swap the file is put back at the next start and the program says so on screen. "
        "Plus an RGB LED (timer alarm, copy finished, write error, notes server running), the NTP clock in the calendar syncs on its own, a shorter network wait (6 s instead of 9 s, touch aborts) "
        "and honest messages when K-OS does not share the network with programs. Version 1.1.1 (only the number in the binary, code as in 1.1.0) was not released separately - it went into 1.2.0.",
        "An earlier version was tested on a 2.4\" board: start, data migration from the old name, theme and language from K-OS, calibration from the card, return to K-OS after RST; the modules were not tried by finger.",
    ]),

    "meteo-pion.bin": z([
        _METEO_SKLEP[0], _METEO_024[0], _METEO_023[0], _METEO_021[0],
        "0.1.1: naprawiony urwany adres zapytania (bufor 560 znakow na adres dlugi na 589) - serwer oddawal HTTP 400 i pogody nie bylo wcale.",
        "Wczesniejsza wersja byla sprawdzona na plytce 2.4\" 04.09.2026: start, motyw i jezyk z K-OS, kalibracja z karty, polaczenie z siecia, pobranie pogody i klatki radaru IMGW, zapis do trybu offline, powrot do K-OS po RST.",
    ], [
        _METEO_SKLEP[1], _METEO_024[1], _METEO_023[1], _METEO_021[1],
        "0.1.1: fixes a truncated request address (a 560 character buffer for an address 589 long) - the server returned HTTP 400 and there was no weather at all.",
        "An earlier version was tested on a 2.4\" board on 04.09.2026: start, theme and language from K-OS, calibration from the card, connecting to the network, fetching the weather and an IMGW radar frame, saving for offline mode, return to K-OS after RST.",
    ]),
    "meteo-poziom.bin": z([
        _METEO_SKLEP[0], _METEO_024[0], _METEO_023[0], _METEO_021[0],
        "Wersja pozioma powstaje z tego samego zrodla co pionowa, ktora sprawdzono na plytce 2.4\"; sama wersja pozioma nie byla jeszcze uruchomiona.",
    ], [
        _METEO_SKLEP[1], _METEO_024[1], _METEO_023[1], _METEO_021[1],
        "The landscape version is built from the same source as the portrait one, which was tested on a 2.4\" board; the landscape version itself has not been run yet.",
    ]),

    "ropeburn-mini.bin": z([
        "0.3.0 (BETA - nie byla jeszcze uruchomiona na plytce): karty ulepszen w biegu - po 8 skokach i na kazdym progu mnoznika u gory pojawiaja sie 3 kafelki z 5 kart "
        "(Wyzszy skok, Wzmocniona lina, Szybsza lina, Podpalona lina, Rakietowe buty; kazda z kosztem albo ryzykiem, kumuluja sie). Dotkniecie kafelka to jednoczesnie skok i wybor - gra sie nie zatrzymuje; "
        "po 3 obrotach karta losuje sie sama. Na 2.8\": zmierzona zapasowa kalibracja dotyku, gdy na karcie nie ma kalibracji z K-OS.",
        "0.2.0 (BETA - nie byla na plytce): po pierwszym tescie na sprzecie skok przeszedl w rece gracza - w 0.1.0 bohaterka skakala sama, a gracz robil tylko trik. "
        "Do tego wolniejszy start, cale logo, plansza i ilustracje autora. Rekordy z 0.1.0 przepadaja (inna mechanika). 333 testy na komputerze.",
        "0.1.0: pierwsza wersja; jej test na plytce 2.4\" dal zmiany z 0.2.0.",
    ], [
        "0.3.0 (BETA - not yet run on a board): upgrade cards during the run - after 8 jumps and at every multiplier threshold 3 tiles from 5 cards appear at the top "
        "(Higher Jump, Reinforced Rope, Faster Rope, Burning Rope, Rocket Boots; each has a cost or a risk, they stack). Touching a tile is a jump and a choice at once - the game never pauses; "
        "after 3 turns a card is drawn for you. On 2.8\": a measured fallback touch calibration when the card has no K-OS calibration.",
        "0.2.0 (BETA - not on a board): after the first hardware test the jump went into the player's hands - in 0.1.0 the heroine jumped on her own and the player only did a trick. "
        "Plus a slower start, the whole logo, the author's stage and illustrations. 0.1.0 records are wiped (different mechanics). 333 tests on the computer.",
        "0.1.0: the first version; its test on a 2.4\" board led to the changes in 0.2.0.",
    ]),

    "doom.bin": z([
        "Sklep 30.09.2026 (bez zmiany programu): K-OS 0.7.8 i nowszy pobiera dane gry /doom/doom.kwad i licencje Freedoom razem z programem, z kontrola rozmiaru i sumy. "
        "Wlasny plik o tej nazwie nadpisze tylko po pytaniu na ekranie. Ze starszym K-OS plik nadal kopiuje sie ze strony sklepu (dane/doom/).",
        "0.1.1 (BETA - nie byla jeszcze uruchomiona na plytce): poprawiony obraz (bez odbicia lustrzanego na 2.4\") i pierwsze uruchomienie - instalacja danych gry trwa do pol minuty z paskiem postepu, "
        "a kazdy blad jest opisany na ekranie. Zrodlo: github.com/PixelPetrol/cyd-doom-kos, tag kos-0.1.1-beta.",
        "Sklep 28.09.2026: gotowe darmowe dane z Freedoom 0.13.0 (plansza E1M1, licencja BSD-3-Clause, bez danych id Software) do pobrania ze strony sklepu - bez Pythona. "
        "Freedoom 0.13 ma duza grafike, wiec w pliku jest jedna plansza, a sciany i postacie maja polowe rozdzielczosci poziomej.",
        "0.1.0 (BETA - nie byla uruchomiona na plytce): pierwsza wersja - silnik GBADoom/PrBoom z projektu HenrysCat/cyd-doom jako program K-OS (RST wraca do K-OS, dotyk, jasnosc, kolory i jezyk z K-OS, zapisy na karcie). "
        "Dane gry trzeba bylo przerobic samemu skryptem wad2kos.py; z DOOM-a miesci sie czesc epizodu 1.",
    ], [
        "Store 30.09.2026 (no change to the program): K-OS 0.7.8 or newer downloads the game data /doom/doom.kwad and the Freedoom licence together with the program, checking size and checksum. "
        "Your own file of that name is replaced only after a question on screen. With an older K-OS you still copy the file from the store website (dane/doom/).",
        "0.1.1 (BETA - not yet run on a board): fixed picture (no mirror image on the 2.4\") and first start - installing the game data takes up to half a minute with a progress bar, "
        "and every error is explained on screen. Source: github.com/PixelPetrol/cyd-doom-kos, tag kos-0.1.1-beta.",
        "Store 28.09.2026: ready-made free data from Freedoom 0.13.0 (level E1M1, BSD-3-Clause licence, no id Software data) to download from the store website - no Python needed. "
        "Freedoom 0.13 has large graphics, so the file holds one level, and walls and characters are at half horizontal resolution.",
        "0.1.0 (BETA - not run on a board): the first version - the GBADoom/PrBoom engine from the HenrysCat/cyd-doom project as a K-OS program (RST returns to K-OS, touch, brightness, colours and language from K-OS, saves on the card). "
        "You had to convert the game data yourself with wad2kos.py; from DOOM part of episode 1 fits.",
    ]),

    "control.bin": z([
        "0.2.1 (BETA - nie byla jeszcze uruchomiona na plytce): touchpad pionowo, jak reszta programu i K-OS (pole ruchu, pasek przewijania, przyciski lewy / srodkowy / prawy); "
        "napisy PL i EN sprawdzone testem szerokosci, zeby miescily sie w polach.",
        "0.2.0 (nie wydana osobno, weszla w 0.2.1): klawiatura ekranowa (QWERTY, strona ?123, ogonki wedlug ukladu hosta), kafelki 'text' i 'macro' z paskiem PISZE i STOP, "
        "'Pisz tekst' na stronie z telefonu, profil skrotow wybierany sam po polaczonym urzadzeniu.",
        "0.1.0 (BETA - nie byla uruchomiona na plytce): pierwsze wydanie - klawiatura, mysz (touchpad poziomo) i pilot TV po Bluetooth LE dla Windows, Androida, iPhone'a, iPada i Google TV; "
        "siatka skrotow 3x4 z profilami na karcie, edycja skrotow z telefonu (kod QR i kod sesji), do 4 sparowanych urzadzen, parowanie z potwierdzeniem na plytce.",
    ], [
        "0.2.1 (BETA - not yet run on a board): portrait touchpad, like the rest of the program and K-OS (movement area, scroll bar, left / middle / right buttons); "
        "the Polish and English labels are checked by a width test so that they fit their fields.",
        "0.2.0 (not released separately, went into 0.2.1): on-screen keyboard (QWERTY, a ?123 page, diacritics following the host layout), 'text' and 'macro' tiles with a TYPING bar and STOP, "
        "'Type text' on the phone page, the shortcut profile picked automatically for the connected device.",
        "0.1.0 (BETA - not run on a board): the first release - keyboard, mouse (landscape touchpad) and TV remote over Bluetooth LE for Windows, Android, iPhone, iPad and Google TV; "
        "a 3x4 shortcut grid with profiles on the card, editing shortcuts from the phone (QR code and session code), up to 4 paired devices, pairing confirmed on the board.",
    ]),

    "gry-vol1.bin": z([
        "0.9.2: kafelki menu bez szarej plyty (zgloszenie Piotra) - kafelek stoi na tle ekranu, tak jak na ekranie glownym K-OS, a zaznaczony odcina sie od sasiadow ponad dwa razy mocniej "
        "(kontrast 2,4-3,4 zamiast 1,7-2,2). Pelny efekt wymaga K-OS 0.7.1, ktory wysyla na karte kolor plyty dla kazdego motywu.",
        "0.9.1: menu tomu wyglada jak ekran glowny K-OS - twardy cien, gruby obrys, zaokraglone rogi, zaznaczenie przyciemnionym akcentem. Jedna funkcja rysowania paneli zamiast pieciu kopii; "
        "pasek dolny 40 px zamiast 26; przygaszone napisy sa wreszcie czytelne w kazdym motywie (dotad kontrast 1,24 i 1,10).",
        "0.9.0: Longshot dostal warsztat z szescioma ulepszeniami i trwaly postep - krople cyny zbierane w locie, zakupy przezywaja restart. Na starcie nie ma dopalacza; pusty zbiornik blokuje go na 0,8 s, "
        "a strome uderzenie o miedz konczy lot wbiciem w laminat. Balans policzony symulacja (pierwszy przelot ok. 1000 px, cale drzewko na ok. 55 przelotow). Przeglad wylapal 17 bledow, w tym lot bez konca.",
        "0.8.0: szosta gra - Longshot, 'jak daleko doleci'. Pierwsze dotkniecie ustala kat, drugie sile, a przytrzymanie wlacza dopalacz; po drodze cewki, wiatraki, kondensatory i magnesy. "
        "Bez nowej grafiki (cala gra to 13 680 B kodu), bez zapisu partii.",
        "0.7.0: menu tomu na kafelkach (2x3 w pionie) z ikonami rysowanymi z duszkow, ktore juz byly w tomie; oczy maskotki w kolorze akcentu motywu. "
        "Payload: szybkie spadanie to teraz przytrzymanie palca w studni (puszczenie przywraca tempo) zamiast pociagniecia w dol.",
        "0.6.1: odkladanie gry na pozniej - 'zapisz i wyjdz' na ekranie pauzy, przy nastepnym wejsciu pytanie o wznowienie. Zapis znika po wczytaniu (to odlozenie partii, nie punkt kontrolny). "
        "Kazdy plik ma numer formatu i sume kontrolna; brak karty nie wyrzuca z gry. Overload swiadomie nie ma zapisu.",
        "0.5.2: w Payloadzie strzalki na przyciskach byly odwrocone (zgloszenie z plytki).",
        "0.5.1: szesc poprawek z przegladu, w tym krytyczna - po kazdym zablokowaniu klocka auto-powtarzanie bylo martwe i nastepnego klocka nie dalo sie ruszyc.",
        "0.5.0: piata gra - Payload, wariacja Tetrisa z elementami elektronicznymi. Rzad ciagly elektrycznie daje podwojne punkty i ladunek; ciaglosc to premia, nie warunek.",
        "0.3.0: czwarta gra - Punch-Through, wersja Arkanoida: Chip-K jest paletka i odbija pilke ciosem. Pilka liczona krokiem podklatkowym, wiec nie przelatuje przez cegly.",
        "0.2.1: w Overload prog rozroznienia dotkniecia od przytrzymania 264 ms zamiast 132 ms - naturalne stukniecie bylo brane za slizg.",
        "0.2.0: trzecia gra - Overload, biegacz bez konca: dotkniecie to skok, przytrzymanie to slizg; zebrany ladunek daje kilkanascie sekund przemiany.",
        "0.1.1: maskotka Chip-K z arkuszy autora i ekran startowy z animacja przemiany; czytelniejsze cyfry w 2048 (kolor wedlug kontrastu WCAG, najgorszy kontrast z 1,06 do 3,09).",
        "0.1.0: pierwszy tom - 2048 i Lunar Lander (30 poziomow, grawitacja, wiatr, obrot, paliwo); menu bylo zwykla lista. Sprawdzony testami na komputerze (2,19 mln sprawdzen), "
        "na plytce wtedy nie. Poziomy Landera od 15 sa bardzo trudne albo niemozliwe przy oryginalnej tabeli wiatru.",
    ], [
        "0.9.2: menu tiles without the grey plate (Piotr's report) - a tile stands on the screen background like on the K-OS home screen, and the selected one stands out from its neighbours more than twice as strongly "
        "(contrast 2.4-3.4 instead of 1.7-2.2). The full effect needs K-OS 0.7.1, which writes a plate colour for every theme to the card.",
        "0.9.1: the volume menu looks like the K-OS home screen - hard shadow, thick outline, rounded corners, selection in a darkened accent. One panel drawing function instead of five copies; "
        "the bottom bar is 40 px instead of 26; dimmed labels are finally readable in every theme (contrast was 1.24 and 1.10).",
        "0.9.0: Longshot got a workshop with six upgrades and lasting progress - tin drops collected in flight, purchases survive a restart. No booster at the start; an empty tank locks it for 0.8 s, "
        "and a steep hit on the copper ends the flight in the laminate. Balance computed by simulation (first flight about 1000 px, the whole tree in about 55 flights). The review caught 17 bugs, including a flight that never ended.",
        "0.8.0: the sixth game - Longshot, 'how far will it fly'. The first touch sets the angle, the second the power, and holding fires the booster; on the way coils, fans, capacitors and magnets. "
        "No new graphics (the whole game is 13 680 B of code), no saved games.",
        "0.7.0: the volume menu on tiles (2x3 in portrait) with icons drawn from sprites already in the volume; the mascot's eyes in the theme accent colour. "
        "Payload: fast drop is now holding a finger in the well (releasing restores the pace) instead of a downward swipe.",
        "0.6.1: putting a game aside - 'save and exit' on the pause screen, and a resume question at the next entry. The save disappears after loading (a set-aside game, not a checkpoint). "
        "Every file has a format number and a checksum; no card does not throw you out of the game. Overload deliberately has no save.",
        "0.5.2: in Payload the arrows on the buttons were reversed (a report from the board).",
        "0.5.1: six fixes from a review, including a critical one - after every locked piece auto-repeat was dead and the next piece could not be moved.",
        "0.5.0: the fifth game - Payload, a Tetris variation with electronic parts. An electrically continuous row gives double points and charge; continuity is a bonus, not a condition.",
        "0.3.0: the fourth game - Punch-Through, an Arkanoid version: Chip-K is the paddle and hits the ball with a punch. The ball moves in sub-frame steps, so it does not pass through bricks.",
        "0.2.1: in Overload the threshold between a tap and a hold is 264 ms instead of 132 ms - a natural tap was taken as a slide.",
        "0.2.0: the third game - Overload, an endless runner: tap to jump, hold to slide; collected charge gives a dozen seconds of transformation.",
        "0.1.1: the Chip-K mascot from the author's sheets and a start screen with a transformation animation; more readable digits in 2048 (colour by WCAG contrast, worst contrast from 1.06 to 3.09).",
        "0.1.0: the first volume - 2048 and Lunar Lander (30 levels, gravity, wind, rotation, fuel); the menu was a plain list. Tested on a computer (2.19 million checks), "
        "not on a board at the time. Lander levels from 15 up are very hard or impossible with the original wind table.",
    ]),

    "mesh.bin": z([
        "0.2.4 (BETA - nie byla jeszcze uruchomiona na plytce): godziny wiadomosci w strefie czasowej z ustawien K-OS 0.7.6 zamiast CET na sztywno; ze starszym K-OS jak dotad.",
        "0.2.3: stabilnosc lacza. Wysylanie juz dzialalo, ale wezel zrywal polaczenie po chwili pracy, a ekran sie przycinal. Teraz program prosi o wlasne parametry polaczenia "
        "(nadzor 4 s, odstep 30-50 ms), nadaje z moca 9 dBm zamiast 3 i nie wznawia skanu BLE w trakcie polaczenia.",
        "0.2.2: nieudane wyslanie nie kasuje juz wystukanego tekstu - zostaje w szkicu tej rozmowy. Niewyslana wiadomosc nadal nie trafia do rozmowy (bez kolejki, bo w MeshCore znacznik czasu jest czescia tresci). "
        "Komunikat o braku polaczenia pokazuje liczbe rozlaczen i kod powodu.",
        "0.2.1: parowanie z PIN-em naprawde dziala - program zgadza sie na uwierzytelnienie, LE Secure Connections i zapamietanie kluczy; dotad wezel zadajacy PIN-u konczyl polaczenie (kod 531). "
        "Nowe 'zapomnij parowanie' w ustawieniach. Poprawiony blad z 0.1.1: reczne 'polacz od nowa' nie czeka juz na rosnaca przerwe miedzy probami.",
        "0.2.0: PIN i wybor wezla w ustawieniach - PIN z klawiatury (puste pole = bez odpowiedzi na parowanie), lista wezlow w zasiegu zamiast adresu na sztywno ('dowolny' albo Twoj). Zmiana od razu laczy na nowo.",
        "0.1.1: program przestal sie zacinac - proba polaczenia trwa najwyzej 4 s zamiast 10, przerwa miedzy nieudanymi probami rosnie od 1 s do 30 s, skan BLE zajmuje 19 zamiast 60 procent czasu. "
        "Ekran wezla pokazuje liczbe rozlaczen i powod ostatniego.",
        "0.1.0: pierwsza wersja - rozmowy prywatne i kanaly, klawiatura ekranowa, powiadomienia, historia na karcie. Wezla nie konfiguruje: biala lista dziewieciu rozkazow tylko do odczytu, pilnowana testem. "
        "Testy na komputerze: 249 sprawdzen z ASAN i UBSAN; na plytce wtedy niesprawdzona.",
    ], [
        "0.2.4 (BETA - not yet run on a board): message times in the time zone from the K-OS 0.7.6 settings instead of hard-coded CET; with an older K-OS as before.",
        "0.2.3: link stability. Sending already worked, but the node dropped the connection after a while and the screen stuttered. The program now asks for its own connection parameters "
        "(4 s supervision, 30-50 ms interval), transmits at 9 dBm instead of 3 and does not resume the BLE scan during a connection.",
        "0.2.2: a failed send no longer erases what you typed - it stays as a draft in that chat. An unsent message still does not go into the chat (no queue, because in MeshCore the timestamp is part of the content). "
        "The no-connection message shows the number of disconnects and the reason code.",
        "0.2.1: pairing with a PIN really works - the program agrees to authentication, LE Secure Connections and storing the keys; until then a node that asked for a PIN ended the connection (code 531). "
        "New 'forget pairing' in settings. Fixed a bug from 0.1.1: a manual 'reconnect' no longer waits for the growing pause between attempts.",
        "0.2.0: PIN and node choice in settings - the PIN from the keyboard (empty field = no answer to a pairing request), a list of nodes in range instead of a hard-coded address ('any' or yours). A change reconnects at once.",
        "0.1.1: the program stopped freezing - a connection attempt takes at most 4 s instead of 10, the pause between failed attempts grows from 1 s to 30 s, the BLE scan takes 19 instead of 60 percent of the time. "
        "The node screen shows the number of disconnects and the last reason.",
        "0.1.0: the first version - private chats and channels, on-screen keyboard, notifications, history on the card. It does not configure the node: a whitelist of nine read-only commands, guarded by a test. "
        "Tests on a computer: 249 checks with ASAN and UBSAN; not tested on a board at the time.",
    ]),
}
