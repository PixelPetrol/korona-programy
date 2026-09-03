# zgloszenia/ - skrzynka na programy uzytkownikow

Tu laduja zgloszenia do sklepu KORONA (kategoria **uzytkownicy**). Po scaleniu PR automat
przenosi je do `bin/<plytka>/uzytkownicy/` i przebudowuje `katalog.json`; ten katalog powinien
byc wiec zwykle pusty (poza tym README).

Jak zglosic - krok po kroku: https://pixelpetrol.github.io/korona-programy/portal/programy.html
(sekcja "jak zglosic do sklepu") albo `../README.md` -> "Programy uzytkownikow".

## Uklad zgloszenia

```
zgloszenia/<id>/<id>.bin     czysty obraz aplikacji ESP32 (magic 0xE9), <= 2 555 904 B
zgloszenia/<id>/meta.json    opis (ponizej)
```

`<id>`: 2-32 znaki, male litery `a-z`, cyfry, `-`, `_`. Zostaje na zawsze (klucz migawki
ustawien na karcie SD).

## meta.json - szablon

```json
{
  "nazwa": "Zegar binarny",
  "opis": "zegar binarny z NTP, 3 motywy",
  "wersja": "1.0.0",
  "autor": "Jan Kowalski",
  "licencja": "MIT",
  "zrodlo": "https://github.com/jkowalski/cyd-binclock",
  "plytka": "cyd24",
  "orientacja": "pion",
  "model_b": true,
  "info": "Pierwszy start: AP 'BinClock' bez hasla, ustawienia na 192.168.4.1. Dotyk: lewa polowa ekranu = motyw, prawa = jasnosc. Czas z pool.ntp.org.",
  "zglaszajacy": "jkowalski"
}
```

* `autor` = autor PROGRAMU. Jesli zglaszasz port cudzego projektu, wpisz oryginalnego autora,
  a siebie w `zglaszajacy`.
* `licencja` GPL/LGPL/AGPL -> `zrodlo` obowiazkowe (URL do zrodel tej wersji).
* `model_b: true` to Twoje oswiadczenie, ze program na poczatku `setup()` kasuje `otadata`
  (albo definiuje `verifyRollbackLater()`), czyli RST wraca do menu. Automat tego **nie
  sprawdzi** - przegladajacy uruchomi program i nacisnie RST.
* Czcionka ladowarki nie ma polskich znakow: `nazwa`, `opis`, `info`, `autor` w ASCII.

Sprawdz lokalnie przed PR: `python3 tools/sprawdz_zgloszenie.py zgloszenia/<id>`.
