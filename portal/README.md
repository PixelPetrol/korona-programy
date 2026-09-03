# Portal instalacyjny KORONY — jak to wypuścić

Statyczna strona, która wgrywa ładowarkę **KORONA** na płytkę CYD wprost z przeglądarki
(WebSerial, przez [ESP Web Tools](https://esphome.github.io/esp-web-tools/)). Zero backendu —
kilka plików na GitHub Pages.

Autor: Piotr Korona.

---

## 1. Co tu leży

```
index.html            strona (bez frameworków; skrypty: ESP Web Tools z unpkg + esptool-js z jsDelivr
                      ładowany dopiero po kliknięciu „Zrób kopię” — §8)
manifest-cyd24.json   manifest ESP Web Tools — CYD 2.4" (ESP32-2432S024R)
manifest-cyd28.json   manifest ESP Web Tools — CYD 2.8" (ESP32-2432S028R, NIESPRAWDZONA)
zbuduj-obrazy.sh      składa obrazy z wyników builda; NICZEGO NIE WGRYWA na płytkę
                      (skrypt na macOS — patrz §4)
SELF-UPDATE.md        projekt samoaktualizacji ładowarki (osobny temat, bez kodu)
obrazy/               <- generowane skryptem, do wypchnięcia razem ze stroną
  SUMY.txt              rozmiary + SHA-256 wszystkich obrazów
  cyd24/                bootloader.bin, partitions.bin, otadata-pusta.bin, loader.bin,
  cyd28/                korona-<płytka>-scalony.bin
```

`obrazy/` **trzeba wypchnąć do repo** — to z niego przeglądarka pobiera binarki. Nie wpisuj go
do `.gitignore`.

---

## 2. Gdzie te pliki mają wylądować

Kandydat (i chyba jedyny sensowny): repo **`korona-programy`**
(`https://github.com/PixelPetrol/korona-programy`), katalog `portal/`.

Dlaczego tam, a nie w `loader/`:

- `loader/` to repo **lokalne, bez zdalnego** (`git remote -v` nic nie zwraca) — nie ma czego
  publikować,
- `korona-programy` jest już publiczne i już serwuje pliki płytce
  (`STORE_BASE` w `loader/loader/net.cpp` →
  `https://raw.githubusercontent.com/PixelPetrol/korona-programy/main/`),
- dzięki temu **`portal/obrazy/<płytka>/loader.bin` jest jednocześnie źródłem dla
  samoaktualizacji** z `SELF-UPDATE.md` — jeden plik, dwie drogi instalacji.

Skopiowanie tam:

```bash
rsync -av --delete \
  "$HOME/Desktop/CYD wifi radar/portal/" \
  "$HOME/Desktop/CYD wifi radar/korona-programy/portal/"
```

Docelowy adres po włączeniu Pages:

```
https://pixelpetrol.github.io/korona-programy/portal/
```

Ścieżki w manifestach są **relatywne** (`obrazy/cyd24/loader.bin`), a ESP Web Tools rozwiązuje je
względem adresu manifestu — więc podkatalog `portal/` nie wymaga żadnych zmian w plikach.

---

## 3. Co Piotr musi kliknąć sam

Tego nie da się zrobić z wiersza polecenia (a przynajmniej nie bez tokenu), więc zostaje ręcznie:

1. **GitHub → repo `korona-programy` → Settings → Pages**
   - *Source*: **Deploy from a branch**
   - *Branch*: **`main`**, folder **`/ (root)`**
   - **Save**. Pierwszy deploy idzie 1–2 minuty (zakładka *Actions* pokazuje postęp).
2. **Sprawdzić, że repo jest publiczne** (Settings → General → Danger Zone). Pages z gałęzi na
   prywatnym repo wymaga płatnego planu, a raw i tak już działa publicznie — więc powinno być OK,
   ale warto zerknąć.
3. **Opcjonalnie: plik `.nojekyll` w katalogu głównym repo** (`touch .nojekyll`). Nasze nazwy
   plików Jekyllowi nie przeszkadzają, ale bez niego każdy deploy przechodzi przez Jekylla po
   nic — z `.nojekyll` jest szybciej i bez niespodzianek.
4. **Wkleić adres portalu w opis repo** (About → Website) i do `README.md` repo
   `korona-programy`, żeby ktoś to w ogóle znalazł.
5. Otworzyć adres w **Chrome albo Edge** i wgrać na 2.4" — do tego momentu nic nie jest
   sprawdzone na sprzęcie (patrz §6).

Ja niczego nie commitowałem ani nie pushowałem — wszystko leży w drzewie roboczym.

---

## 4. Odświeżenie obrazów po nowej wersji ładowarki

```bash
# 1. kompilacja (to jest osobny krok, w loader/ - skrypt portalu nie kompiluje)
cd "$HOME/Desktop/CYD wifi radar/loader" \
  && ./build.sh \
  && BOARD=28R ./build.sh       # 2.8"  <- łatwo zapomnieć; skrypt niżej to wyłapie

# 2. złożenie obrazów + 3. publikacja - JEDNYM łańcuchem &&:
#    jeśli zbuduj-obrazy.sh przerwie (kod != 0), rsync i git się NIE wykonają
cd ../portal \
  && ./zbuduj-obrazy.sh \
  && rsync -av --delete ./ ../korona-programy/portal/ \
  && cd ../korona-programy && git add -A && git commit -m "portal: KORONA 0.3.x" && git push
```

Nie rozbijaj tego na osobne linie: kod wyjścia skryptu chroni publikację tylko wtedy, gdy
`rsync`/`git` wiszą na nim przez `&&`.

`zbuduj-obrazy.sh` robi wszystko, czego nie chce się pamiętać:

- kopiuje `loader.ino.bin` → `loader.bin` i `loader.ino.bootloader.bin` → `bootloader.bin`,
- generuje `partitions.bin` **z `loader/partitions_loader.csv`** przez `gen_esp32part.py`,
- generuje `otadata-pusta.bin` (8192 × `0xFF`),
- składa `korona-<płytka>-scalony.bin` przez `esptool merge-bin` (`SCALONY=0` wyłącza),
- wpisuje wersję z `loader/loader/version.h` w oba manifesty **i w `index.html`**
  (znacznik `<!--WER-->…<!--/WER-->`),
- liczy SHA-256 i rozmiary do `obrazy/SUMY.txt` — **tylko plików wytworzonych w tym biegu**
  (katalog `obrazy/<płytka>/` jest przed kopiowaniem kasowany w całości, więc stare pliki
  nie zostają),
- **najpierw sprawdza obie płytki, dopiero potem cokolwiek zapisuje**: istnienie builda,
  magic `0xE9`, czy obraz mieści się w `factory` i czy **nie jest starszy niż `version.h`**
  (czyli czy nie zapomniało się przebudować jednej płytki). Każdy z tych błędów **przerywa
  skrypt z kodem 1 zanim** powstaną obrazy, manifesty, wpis w `index.html` i `SUMY.txt` —
  stan portalu na dysku zostaje taki, jaki był. Komunikat mówi, co uruchomić
  (`./build.sh` albo `BOARD=28R ./build.sh`).
- **wymaga `esptool` 5.x** (podkomenda `merge-bin`; bierze najnowszy z
  `~/Library/Arduino15/packages/esp32/tools/esptool_py/`, sortując numery wersji, nie tekst).
  Brak esptool albo esptool 4.x (`merge_bin`) to **błąd i przerwanie**, nie ciche pominięcie —
  strona linkuje `korona-*-scalony.bin`, więc bez niego nie ma czego publikować.
  `SCALONY=0` pomija scalony obraz tylko do lokalnych prób.
- pliki tymczasowe trzyma w `mktemp -d` i sprząta je zawsze, także po błędzie (`trap`).

**Skrypt jest pisany i sprawdzany na macOS.** Rozmiary i daty plików liczy przez `python3`
(nie `stat -f`/`date -r`), więc na Linuksie powinien pójść, ale nikt go tam nie uruchamiał.

**Uwaga na tablicę partycji.** W `.build-*/` leży `loader.ino.partitions.bin`, ale to tablica
**Arduino** (`huge_app`: `app0`=ota_0 pod `0x10000`, 3 MB, bez `factory`). Wgranie jej zamurowałoby
układ KORONY. Skrypt jej **nie używa** — generuje własną z CSV. Nie „upraszczaj” tego przez
skopiowanie pliku z builda.

### Zmierzone (03.09.2026, KORONA 0.3.6)

| | rozmiar | zapas w `factory` (1 441 792 B) | magic |
|---|---|---|---|
| `cyd24/loader.bin` | 1 359 744 B | 82 048 B (5,7 %) | `0xE9` |
| `cyd28/loader.bin` | 1 357 504 B | 84 288 B (5,8 %) | `0xE9` |
| `bootloader.bin` (oba) | 24 992 B | — | — |
| `partitions.bin` (oba) | 3 072 B | — | — |
| `otadata-pusta.bin` (oba) | 8 192 B | — | — |
| `korona-cyd24-scalony.bin` | 1 425 280 B | — | — |
| `korona-cyd28-scalony.bin` | 1 423 040 B | — | — |

Oba obrazy mieszczą się w `factory` z zapasem, ale zapas jest **poniżej 6 %** — kolejna
grafika albo font mogą go zjeść. Gdy obraz przestanie się mieścić, skrypt przerywa **przed**
zapisaniem czegokolwiek do `obrazy/`, manifestów i `index.html`, więc przy publikacji przez
`&&` (wyżej) taki obraz nie ma jak trafić do repo.

Sprawdzone dodatkowo w scalonym obrazie 2.4": `0x0`–`0x1000` samo `0xFF`, magic `0xE9`
pod `0x1000`, wpis tablicy partycji (`AA 50`) pod `0x8000`, **cały zakres `0xe000`–`0x10000` to
samo `0xFF`**, magic `0xE9` pod `0x10000`, koniec pliku dokładnie na `0x10000 + rozmiar obrazu`.

**Scalony obraz nie jest równoważny ścieżce WebSerial.** `merge-bin` wypełnia `0xFF` *wszystkie*
luki między częściami, więc `korona-*-scalony.bin` wgrany pod `0x0` **dodatkowo zeruje partycję
`nvs` aplikacji (`0x9000`–`0xe000`)** — zmierzone: cały ten zakres to `0xFF` w obu scalonych
plikach. Manifest ESP Web Tools pisze tylko cztery części pod ich offsety i `nvs` **nie rusza**.
Skutek praktyczny: po `esptool` ostatnio uruchamiana aplikacja startuje z pustymi ustawieniami
(ładowarka i tak przywraca jej migawkę z karty przed startem, jeśli taka jest), po WebSerial —
z tym, co miała. Partycji `knvs` ładowarki (`0x3FC000`) żadna z dróg nie dotyka.

### Stan obrazów 2.8" w chwili pisania

`loader/.build-28R/` jest zbudowany 03.09.2026 14:07 z `version.h` = 0.3.6 (obraz zawiera ciąg
`0.3.6`, sprawdzone `grep -a`), więc obrazy `cyd28` i `manifest-cyd28.json` są spójne.
Płytka 2.8" nadal jest **niesprawdzona na sprzęcie** (§6).

Gdyby `.build-28R/` kiedyś zniknęło albo zestarzało się względem `version.h`, skrypt **przerwie
z błędem przed zapisem czegokolwiek** — nie ma trybu „pomiń jedną płytkę”, bo strona i oba
manifesty są publikowane razem i przycisk 2.8" bez obrazów pokazywałby błąd pobierania.

---

## 5. Jak to działa (i dlaczego tak, a nie inaczej)

### Cztery kawałki, te same offsety co `flash.sh`

| offset | plik | co to |
|---|---|---|
| `0x1000` | `bootloader.bin` | bootloader ESP32 2. stopnia |
| `0x8000` | `partitions.bin` | tablica partycji KORONY (z CSV) |
| `0x10000` | `loader.bin` | ładowarka, partycja `factory` (1408 KB) |
| `0xe000` | `otadata-pusta.bin` | 8 KB `0xFF` — czysta `otadata` |

Źródło prawdy dla offsetów: `loader/flash.sh`.

### Kasowanie `otadata` — jak to obeszliśmy (i że to nie jest udawanie)

`flash.sh` robi `esptool erase_region 0xe000 0x2000`, żeby po wgraniu wystartowała ładowarka,
a nie stary program leżący w `ota_0`. **Manifest ESP Web Tools nie ma niczego, co kasuje
region** — sprawdzone w źródłach, nie w domysłach:

- typ `Manifest`/`Build` (`esp-web-tools/src/const.ts`) zna tylko `name`, `version`,
  `home_assistant_domain`, `funding_url`, `new_install_skip_erase` (przestarzałe),
  `new_install_prompt_erase`, `new_install_improv_wait_time`, `builds[]`, a w budzie
  `chipFamily`, `parts[{path,offset}]`, `serialType`. Nieznane klucze są **milcząco ignorowane**
  (zwykły `JSON.parse`, brak walidacji i brak opublikowanego schematu JSON).
- `esptool-js` **nie ma** API kasowania regionu: stała `ESP_ERASE_REGION = 0xd1` jest
  zadeklarowana i nigdzie nieużywana; jedyne wejście to `eraseFlash()` = pełne kasowanie kostki
  (opcode `0xd0`).

Obejście, którego użyliśmy, jest **równoważne** kasowaniu, a nie przybliżone:

1. `parts[]` są zapisywane **dosłownie** pod podane offsety — `esptool-js` modyfikuje wsad
   tylko dla obrazu pod offsetem bootloadera i tylko gdy `flashSize/Mode/Freq != "keep"`,
   a ESP Web Tools ustawia wszystkie trzy na `"keep"`. Jedyna operacja to wyrównanie do 4 bajtów.
2. Zapis do flasha **kasuje sektory, w które pisze** (`flashDeflBegin` — *„performs an erase”*).
   `0xe000` i `0x2000` są wielokrotnościami 4096, więc kasowanie nie wychodzi poza `otadata`.
   Efekt: zawartość flasha nieodróżnialna od `erase_region`.
3. Bootloader ESP-IDF przy `otadata` z `ota_seq == 0xFFFFFFFF` w **obu** sektorach wchodzi
   w gałąź *„Defaulting to factory image”* — czyli startuje ładowarkę. Dlatego blob ma
   `0x2000`, nie `0x1000`: bootloader czyta oba sektory i wystarczy jeden ważny wpis, żeby
   pojechał w `ota_0`.

Kolejność `parts[]` jest celowa: `otadata-pusta.bin` jest **ostatnia**. Przerwana instalacja
zostawia wtedy stary wskaźnik rozruchu i płytka nadal coś uruchamia, zamiast wskazywać na
w połowie zapisaną `factory`.

**Czego NIE robić:** nie wgrywać `boot_app0.bin` z katalogu builda pod `0xe000`. Ten plik **nie
jest** pusty — ma `ota_seq = 1` z poprawną sumą CRC, czyli mówi bootloaderowi „startuj `ota_0`”,
dokładnie odwrotnie niż trzeba (rozłożone bajt po bajcie: `01 00 00 00 … 9a 98 43 47`). Dla
domyślnej tablicy Arduino (bez `factory`) to ma sens, dla KORONY jest zabójcze.

### `new_install_prompt_erase: true` — i dlaczego nie `false`

Ta flaga **nie ustawia** żadnego kasowania, tylko przełącza ekran instalatora:

- **brak flagi / `false`** → każda „nowa instalacja” leci z `eraseFirst = true`, czyli
  **pełnym kasowaniem całej kostki**, bez pytania;
- **`true`** → instalator pokazuje pytanie *„Erase device”* z **niezaznaczonym** okienkiem,
  więc domyślną odpowiedzią jest *nie kasuj*.

KORONA nie ma Improv, więc ESP Web Tools **każdą** instalację traktuje jak nową — z `false`
każde ponowne wgranie czyściłoby całą kostkę, a razem z nią partycję `knvs`: sieci WiFi, motyw
i kalibrację dotyku. Dlatego `true`. Nasza pusta `otadata` i tak zapewnia start z `factory`,
więc pełne kasowanie nie jest do niczego potrzebne — zostaje jako świadomy wybór użytkownika
(egzotyczny układ partycji, płytka po innym firmware). Migawki stanu aplikacji leżą **na karcie
SD**, więc ich pełne kasowanie nie dotyka.

### Skrypt ESP Web Tools

```html
<script type="module" src="https://unpkg.com/esp-web-tools@10/dist/web/install-button.js?module"></script>
```

unpkg jest udokumentowanym CDN-em tego projektu (`dist/web/` to gotowa paczka ESM pod CDN).
Przypięta jest **główna wersja 10** (dziś rozwiązuje się na 10.4.0), więc poprawki dochodzą same,
a zmiana niekompatybilna wymagałaby 11. Jeśli wolisz zamrozić: wpisz pełne `esp-web-tools@10.4.0`.

---

## 6. CZEGO PORTAL NIE POTRAFI

Bez owijania:

1. **Nic z tego nie jest sprawdzone na sprzęcie.** Nie tknąłem portu szeregowego (zajmuje go
   inna sesja), więc portal był weryfikowany tylko na hoście: rozmiary, offsety, zawartość
   scalonego obrazu, renderowanie strony i to, że `<esp-web-install-button>` wchodzi w stan
   *aktywny* na `localhost` (`isSupported`/`isAllowed`/`isSecureContext` = `true`, widoczny
   slot `activate`). **Pierwsze prawdziwe wgranie z portalu jest przed Tobą.**
2. **Obrazy 2.8" nigdy nie działały na płytce.** To nie wina portalu — cały profil `28R`
   (`build.sh`, `ui.cpp`) jest przygotowany „w ciemno”. Strona mówi to wprost i przycisk jest
   pomarańczowy, ale portal nie ma jak tego sprawdzić.
3. **Portal nie rozpozna, jaką masz płytkę.** ESP32 nie zdradza modelu obudowy — 2.4" i 2.8"
   są elektronicznie tym samym chipem. Wybór jest ręczny; zły wybór to czarny ekran albo martwy
   dotyk (odkręcalne: wgraj drugi obraz).
4. **Manifest nie umie skasować regionu flasha.** Obejście z 8 KB `0xFF` jest równoważne
   (§5) — ale to jest obejście oparte na tym, *jak* `esptool-js` zapisuje części, a nie na
   udokumentowanej funkcji. Gdyby ESP Web Tools kiedyś przestało kasować sektory przed zapisem,
   trzeba będzie przejść na wariant ze scalonym obrazem: **jedna** część pod offsetem `0x0`
   (plik `korona-<płytka>-scalony.bin` już jest generowany, `merge-bin` wypełnia luki `0xFF` —
   w tym partycję `nvs`, patrz §4).
   To wersja, którą ESPHome serwuje u siebie — tylko cięższa o wypełnienie od `0x0`.
5. **Portal nie kładzie nic na kartę SD.** Wgrywa wyłącznie ładowarkę. Programy dokładasz ze
   sklepu w menu albo z komputera do `/programy/<płytka>/`. Portal nie sprawdzi nawet, czy karta
   jest w środku.
6. **Sumy SHA-256 nie są weryfikowane przez przeglądarkę.** `SUMY.txt` jest dla człowieka;
   ESP Web Tools ignoruje wszelkie pola `md5`/`sha256` w manifeście (ESPHome trzyma je w swoim
   i też ich nie czyta). Uszkodzone pobranie wyjdzie dopiero jako nieudany start płytki.
7. **Safari, iOS, Android — nie.** Żadna przeglądarka na iPhonie/iPadzie nie umie WebSerial
   (wszystkie na silniku Safari); Chrome na Androida udostępnia je tylko dla portów z emulacji
   Bluetooth. Dla nich jedyną drogą jest scalony obraz + `esptool` (opisane na stronie).
   Firefox na komputerze **od wersji 151 już umie** WebSerial — strona o tym mówi, ale u nas
   nie było na czym tego sprawdzić.
8. **Nie ma samoaktualizacji.** Portal to zawsze kabel. Plan aktualizacji przez WiFi jest
   w `SELF-UPDATE.md` i wymaga zmian w `loader/`, których nie zrobiłem.
9. **Nie ma wersjonowania obrazów.** W repo leży jedna, bieżąca wersja; historia gita rośnie
   o ~5,6 MB przy każdym wydaniu (5 plików na płytkę × 2 płytki). Jeśli to zacznie przeszkadzać,
   trzeba przenieść binarki do *Releases* — ale wtedy do sprawdzenia jest CORS na
   `objects.githubusercontent.com`, bo ESP Web Tools pobiera części przez `fetch()`.
10. **Nie sprawdzone z szyfrowaniem flasha ani secure boot.** Gdyby któraś płytka miała to
    włączone, wgranie jawnej `otadata` da śmieć. Na CYD-ach z Aliexpress tego nie ma, ale to
    założenie, nie pomiar.
11. **Portal nie zmieni tablicy partycji istniejącej instalacji „bezpiecznie”.** Zmienia ją
    (pisze pod `0x8000`), co jest w porządku przy wgrywaniu od zera, ale zawartość starych
    partycji danych przestaje wtedy pasować. Po zmianie układu partycji ładowarka i tak migruje
    swoje ustawienia ze starego `nvs` do `knvs` przy pierwszym starcie.

---

## 7. Test lokalny bez publikowania

WebSerial działa na `localhost`, więc portal da się sprawdzić przed pushem:

```bash
cd "$HOME/Desktop/CYD wifi radar/portal"
python3 -m http.server 8731
# potem: http://localhost:8731/  w Chrome
```

`file://` **nie zadziała** — to nie jest bezpieczny kontekst, przycisk pokaże komunikat
o `https://`.

---

## 8. Kopia zapasowa płytki (i przywracanie) — NIE TESTOWANE NA SPRZĘCIE

Sekcja **„Najpierw: kopia zapasowa płytki”** na górze strony (nad kartami płytek) czyta cały
flash ESP32 przez WebSerial i oddaje plik `korona-kopia-YYYYMMDD-HHMM.bin` do pobrania. Pomysł:
zrobić zrzut tego, co siedzi na płytce, **zanim** wgra się KORONĘ (instalacja nadpisuje
bootloader, tablicę partycji i program).

### Co robi

1. `navigator.serial.requestPort()` → `new Transport(port)` → `new ESPLoader({transport,
   baudrate, terminal})` → `loader.main()` (połączenie na 115200 — `romBaudrate` jest w 0.6.1
   stałą, nie opcją — wykrycie chipu, wgranie stuba, zmiana prędkości na wybraną, odczyt flash ID).
2. **Chip musi być `ESP32`** (`loader.chip.CHIP_NAME`); S3/C3/inne → komunikat, reset, koniec.
3. **Rozmiar flasha z ID kostki**: `loader.readFlashId()`, kod `(id>>16)&0xff` →
   `loader.DETECTED_FLASH_SIZES` → `loader.flashSizeBytes()` — to samo, co robi
   `ESPLoader.flashId()/detectFlashSize()` w bibliotece. Gdy kodu nie ma w tabeli: **4 MB jako
   fallback z ostrzeżeniem** w statusie i przy wyniku.
4. `loader.readFlash(0, size, cb)` → `Uint8Array`; callback `(packet, progress, total)` napędza
   pasek, procenty, KB/s i ETA.
5. Weryfikacja: stub esptool po `read_flash` wysyła jeszcze ramkę z 16-bajtowym MD5 (tak czyta ją
   `esptool.py`; esptool-js jej **nie** zdejmuje z bufora) — strona zdejmuje ją `transport.read()`
   i porównuje z MD5 policzonym lokalnie; potem dodatkowo pyta stub wprost `loader.flashMd5sum(0,
   size)`. MD5 jest liczone własną funkcją (Web Crypto nie ma MD5) — sprawdzoną w Node przeciw
   `crypto.createHash('md5')` na wektorach RFC 1321 i buforze 4 MB. Niezgodność = czerwony status
   „kopia uszkodzona”; brak możliwości porównania = żółte „(nie udało się porównać)”.
6. Reset po zakończeniu **dokładnie jak `hardResetDevice()` w esp-web-tools/dist/flash.js**:
   `transport.setRTS(true)`, 100 ms, `loader.after("hard_reset")`. Uwaga: sama klasa `HardReset`
   w esptool-js 0.6.1 tylko *zwalnia* RTS (`setRTS(false)`), więc bez wcześniejszego `setRTS(true)`
   płytka nie dostałaby impulsu. Potem `transport.disconnect()`.
7. Plik: `Blob` + `a[download]`, rozmiar, **SHA-256** (`crypto.subtle.digest`) i MD5.

Biblioteka: **esptool-js 0.6.1** z jsDelivr jako zbundlowany ESM
(`https://cdn.jsdelivr.net/npm/esptool-js@0.6.1/+esm`), ładowana **dopiero po pierwszym kliknięciu**
(`import()`), więc nie obciąża zwykłego wejścia na stronę. Dlaczego jsDelivr, a nie unpkg: `+esm`
rozwiązuje zależności (`pako`, `atob-lite`) i **dynamiczny import JSON ze stubem flashera**
(`lib/targets/stub_flasher/stub_flasher_32.json`) — pod `unpkg ...?module` ten import JSON nie
przejdzie w przeglądarce. ESP Web Tools 10.4.0 deklaruje `"esptool-js": "^0.6.0"`, więc to ta sama
gałąź biblioteki, na której stoi instalator wyżej. Bez SRI — jsDelivr generuje `+esm` dynamicznie.

Prędkość: domyślnie **460800 b/s**, w rozwijanej liście 115200 (CH340 na CYD nie lubi 921600;
ESP Web Tools w ogóle nie zmienia prędkości i pracuje na 115200). Orientacyjnie 4 MB: ~1,5–2 min
przy 460800, ~6–7 min przy 115200.

Stany obsłużone: brak WebSerial (sekcja pokazuje komendę `esptool ... read-flash 0x0 0x400000`),
brak `https://`, anulowanie wyboru portu, port zajęty (`Failed to open`/`NetworkError`), płytka nie
odpowiada (`Failed to connect` → podpowiedź BOOT), zły chip, zniknięcie portu w trakcie (zdarzenie
`disconnect` na `SerialPort` ścigane z `readFlash` przez `Promise.race`), przycisk **Przerwij**
(rzuca w callbacku postępu → `readFlash` odrzuca; potem reset + zamknięcie portu). W `finally`
zawsze: reset RTS + `disconnect()`, żeby płytka nie została w bootloaderze.

### Przywracanie

Akapit z komendą (esptool 5.x / 4.x):

```bash
esptool --chip esp32 --port /dev/cu.usbserial-XXXX --baud 460800 write-flash 0x0 korona-kopia-YYYYMMDD-HHMM.bin
# esptool 4.x: esptool.py ... write_flash 0x0 ...
```

oraz przycisk **„Przywróć z pliku”** — zrobiony, bo da się to poprowadzić przez udokumentowane
API: `loader.writeFlash({fileArray:[{data, address:0x0}], flashSize:"keep", flashMode:"keep",
flashFreq:"keep", eraseAll:false, compress:true, reportProgress, calculateMD5Hash})`. To ta sama
funkcja, którą ESP Web Tools wgrywa manifest. Dlaczego bezpiecznie:

- `_updateImageFlashParams` modyfikuje obraz tylko pod `BOOTLOADER_FLASH_OFFSET` (0x1000 dla ESP32)
  i tylko gdy któryś parametr ≠ `"keep"` — nasz plik pod `0x0` z trzema `"keep"` idzie bajt w bajt;
- `flashDeflBegin` kasuje sektory, w które pisze („performs an erase”), więc `eraseAll:false` nie
  zostawia starych danych w zakresie pliku; zakres **za końcem pliku** zostaje nietknięty (strona
  o tym mówi, gdy plik jest mniejszy niż flash);
- `calculateMD5Hash` sprawia, że `writeFlash` po zapisie woła `flashMd5sum` i **rzuca** przy
  różnicy — weryfikacja za darmo.

Zabezpieczenia: plik musi mieć ≥ 64 KB i bajt `0xE9` pod `0x1000` (magic bootloadera ESP32),
nie może być większy niż wykryty flash; **dwa `confirm()`** („to nadpisze CAŁY flash…”, „na
pewno?”). Przerwanie zapisu daje osobny komunikat: flash zapisany częściowo.

### Ograniczenia

- **Zero testów na sprzęcie** — ani kopii, ani przywracania, ani resetu po zakończeniu. Weryfikacja
  była hostowa: render PL/EN, brak błędów w konsoli, moduł esptool-js ładuje się z jsDelivr,
  anulowanie wyboru portu → „Nie wybrano portu”, walidacja pliku przy przywracaniu, brak
  poziomego przewijania na 375 px.
- Ramka MD5 po `read_flash` to zachowanie **stuba esptool** (C), nie API esptool-js — dlatego jest
  traktowana miękko (brak ramki ≠ błąd), a właściwą weryfikacją jest `flashMd5sum`.
- `readFlash` w 0.6.1 skleja pakiety przez `_appendArray` (O(n²)); dla 4 MB to ułamki sekundy,
  dla 16 MB byłoby wolniej.
- Timeout na pakiet w `readFlash` to 100 s (`FLASH_READ_TIMEOUT`); przy zerwaniu bez zdarzenia
  `disconnect` (np. zawieszony CH340) błąd pojawi się dopiero po tym czasie.
- „Przerwij” działa między pakietami; w trakcie `main()` (kilka sekund) nie ma jak przerwać.
- Płytki z flash encryption / secure boot: zrzut będzie zaszyfrowany, przywracanie na inną
  płytkę nie zadziała — CYD-y tego nie mają.
- Przywracanie **nie sprawdza**, czy plik pochodzi z tej samej płytki; kopia z 2.4" wgrana na
  2.8" da czarny ekran (inny pin podświetlenia), ale nic trwałego.

### Procedura pierwszego testu na sprzęcie

1. Chrome/Edge, `https://pixelpetrol.github.io/korona-programy/portal/` (albo `python3 -m
   http.server 8766 --directory portal` i `http://localhost:8766/`).
2. Płytka na USB, nic innego nie trzyma portu. **Zrób kopię (cały flash)** → wybierz CH340.
3. Oczekiwane: status „Łączę…”, w „Dzienniku połączenia” linie esptool-js: `Connecting...`,
   `Chip is ESP32-D0WD...`, `Uploading stub...`, `Running stub...`, `Changing baudrate to 460800`,
   `Flash ID: ...`, potem `[strona] chip: ESP32`, `[strona] flash ID 0x..., rozmiar 4194304`.
   Pasek rośnie, status „Czytam… N% · … KB/s · zostało ~…”. Na koniec „Sprawdzam MD5 na płytce…”,
   „Resetuję…”, zielone „Gotowe: 4 MB…”, pod spodem przycisk pobrania, SHA-256, MD5
   z „✓ zgodne z sumą policzoną przez płytkę”. **Płytka ma się zrestartować i wrócić do swojego
   programu** (ekran ożywa) — jeśli zostaje w bootloaderze (czarny ekran), zgłoś: reset RTS
   wymaga poprawki.
4. Kontrola krzyżowa: `esptool --chip esp32 --port ... --baud 460800 read-flash 0x0 0x400000 ref.bin`
   i `shasum -a 256 ref.bin korona-kopia-*.bin` — sumy identyczne (o ile program na płytce nie
   pisał w NVS między odczytami).
5. Jeśli 460800 zrywa się („Serial data stream stopped”): 115200 i jeszcze raz.
6. Przywracanie testuj **tylko na płytce, na której nic Ci nie zależy**: wgraj KORONĘ, potem
   „Przywróć z pliku” z kopią z punktu 3 → dwa potwierdzenia → pasek „Piszę…” → „Gotowe: flash
   przywrócony i zweryfikowany (MD5)” → płytka startuje ze starym programem.
