# Portal instalacyjny KORONY — jak to wypuścić

Statyczna strona, która wgrywa ładowarkę **KORONA** na płytkę CYD wprost z przeglądarki
(WebSerial, przez [ESP Web Tools](https://esphome.github.io/esp-web-tools/)). Zero backendu —
kilka plików na GitHub Pages.

Autor: Piotr Korona.

---

## 1. Co tu leży

```
index.html            strona (bez frameworków; jedyny skrypt to ESP Web Tools z unpkg)
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
