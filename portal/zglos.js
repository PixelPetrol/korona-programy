/* zglos.js - sprawdzanie pliku .bin i sklejanie zgloszenia, w calosci w przegladarce.
 *
 * =====================================================================================
 *  ZRODLEM PRAWDY JEST  tools/sprawdz_bin.py  (a dla meta.json - tools/sprawdz_zgloszenie.py)
 *  z repozytorium korona-programy. Ten plik jest ich RECZNIE PRZEPISANA kopia w JS,
 *  zeby strona na GitHub Pages mogla dac odpowiedz bez serwera.
 *
 *  Zmieniasz reguly w tamtych skryptach -> MUSISZ ruszyc oba miejsca.
 *  Zeby to nie zostalo na dobrej woli, jest maly straznik:
 *
 *      python3 tools/sprawdz_zgodnosc_js.py
 *
 *  porownuje liczby i limity z bloku REGULY nizej z tym, co naprawde siedzi
 *  w sprawdz_bin.py / sprawdz_zgloszenie.py, i konczy sie kodem 1, gdy sie rozjada.
 *  W tym projekcie kopie kodu juz raz sie rozjechaly - stad ten straznik.
 *
 *  Czego ta strona NIE sprawdza (bo sie nie da, dokladnie jak w sprawdz_bin.py):
 *  wymogu "Model B" - kasowania otadata na poczatku setup(). To kod maszynowy, nie tekst.
 *  Jedyny test to uruchomic program pod K-OS i nacisnac RST.
 *
 *  Plik uzytkownika NIGDZIE SIE NIE WYSYLA: FileReader czyta go lokalnie, sha256 liczy
 *  crypto.subtle (albo zapasowa implementacja nizej, gdy strona idzie z file://).
 * =====================================================================================
 */
(function (global) {
'use strict';

/* ===== POCZATEK REGUL (parsowane przez tools/sprawdz_zgodnosc_js.py - nie zmieniaj ukladu linii) ===== */
var REGULY = {
  OTA0_SIZE:      0x270000,     // slot ota_0 z loader/partitions_loader.csv = 2 555 904 B
  OFF_BOOT:       0x1000,       // bootloader w obrazie scalonym
  OFF_PART:       0x8000,       // tablica partycji w obrazie scalonym
  OFF_APP:        0x10000,      // partycja aplikacji w obrazie scalonym
  ESP_MAGIC:      0xE9,         // pierwszy bajt obrazu aplikacji ESP32
  APP_DESC_MAGIC: 0xABCD5432,   // esp_app_desc_t.magic_word pod offsetem 0x20
  LIM_nazwa:      40,
  LIM_opis:       60,
  LIM_wersja:     16,
  LIM_autor:      60,
  LIM_licencja:   40,
  LIM_zrodlo:     200,
  LIM_info:       600,
  LIM_zglaszajacy: 60,
  ID_RE_SRC:      "^[a-z0-9][a-z0-9_-]{1,31}$",
  PLYTKI:         ["cyd24", "cyd28"],
  ORIENT:         ["pion", "poziom"],
  WYMAGANE:       ["nazwa", "opis", "wersja", "autor", "licencja", "zrodlo", "plytka", "orientacja", "model_b", "info"]
};
/* ===== KONIEC REGUL ===== */

var PART_MAGIC = [0xAA, 0x50];
var CHIPS = {
  0x0000: "ESP32", 0x0002: "ESP32-S2", 0x0005: "ESP32-C3", 0x0009: "ESP32-S3",
  0x000C: "ESP32-C2", 0x000D: "ESP32-C6", 0x0010: "ESP32-H2", 0x0012: "ESP32-P4"
};
var ID_RE = new RegExp(REGULY.ID_RE_SRC);
var GPL_RE = /GPL|AGPL|LGPL/i;
var URL_RE = /^https?:\/\/[^\s]+$/;

var MODEL_B_PL = "NIE DA SIE SPRAWDZIC Z BINARKI: uruchom program pod K-OS i nacisnij RST - musi wrocic menu. " +
                 "Bez Modelu B (kasowanie otadata w setup() albo verifyRollbackLater()) plytke odzyskasz tylko po USB.";
var MODEL_B_EN = "CANNOT BE CHECKED FROM A BINARY: run the program under K-OS and press RST - the menu must come back. " +
                 "Without Model B (erasing otadata in setup(), or verifyRollbackLater()) the board is only recoverable over USB.";

/* ---------------------------------------------------------------- sha256 */
var K256 = [
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
];
function rotr(x, n) { return ((x >>> n) | (x << (32 - n))) >>> 0; }

/* Zapasowa implementacja - crypto.subtle nie zawsze jest, gdy strone otwiera sie z file://. */
function sha256js(bytes) {
  var H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  var l = bytes.length, total = ((l + 9 + 63) >> 6) << 6;
  var buf = new Uint8Array(total);
  buf.set(bytes); buf[l] = 0x80;
  var dv = new DataView(buf.buffer);
  dv.setUint32(total - 8, Math.floor(l / 536870912));          // gorne 32 bity z l*8
  dv.setUint32(total - 4, ((l % 536870912) * 8) >>> 0);
  var w = new Uint32Array(64), i, t;
  for (i = 0; i < total; i += 64) {
    for (t = 0; t < 16; t++) w[t] = dv.getUint32(i + t * 4);
    for (t = 16; t < 64; t++) {
      var s0 = rotr(w[t-15], 7) ^ rotr(w[t-15], 18) ^ (w[t-15] >>> 3);
      var s1 = rotr(w[t-2], 17) ^ rotr(w[t-2], 19) ^ (w[t-2] >>> 10);
      w[t] = (w[t-16] + s0 + w[t-7] + s1) >>> 0;
    }
    var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
    for (t = 0; t < 64; t++) {
      var S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      var ch = (e & f) ^ ((~e) & g);
      var t1 = (h + S1 + ch + K256[t] + w[t]) >>> 0;
      var S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      var maj = (a & b) ^ (a & c) ^ (b & c);
      var t2 = (S0 + maj) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    H[0] = (H[0]+a)>>>0; H[1] = (H[1]+b)>>>0; H[2] = (H[2]+c)>>>0; H[3] = (H[3]+d)>>>0;
    H[4] = (H[4]+e)>>>0; H[5] = (H[5]+f)>>>0; H[6] = (H[6]+g)>>>0; H[7] = (H[7]+h)>>>0;
  }
  var out = "";
  for (i = 0; i < 8; i++) out += ("00000000" + H[i].toString(16)).slice(-8);
  return out;
}

function sha256hex(bytes) {
  var subtle = (global.crypto && global.crypto.subtle) || null;
  if (!subtle) return Promise.resolve(sha256js(bytes));
  // kopia do wlasnego bufora: Uint8Array z FileReadera bywa widokiem na wiekszy ArrayBuffer
  var copy = bytes.slice();
  return subtle.digest("SHA-256", copy.buffer).then(function (d) {
    var v = new Uint8Array(d), s = "";
    for (var i = 0; i < v.length; i++) s += ("0" + v[i].toString(16)).slice(-2);
    return s;
  }).catch(function () { return sha256js(bytes); });
}

/* ------------------------------------------------------- czytanie naglowkow */
function cstr(bytes, from, to) {
  var end = from;
  while (end < to && bytes[end] !== 0) end++;
  var s = "";
  for (var i = from; i < end; i++) s += String.fromCharCode(bytes[i]);
  try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
}
function u32(bytes, off) { return (bytes[off] | (bytes[off+1] << 8) | (bytes[off+2] << 16) | (bytes[off+3] << 24)) >>> 0; }
function u16(bytes, off) { return (bytes[off] | (bytes[off+1] << 8)) >>> 0; }

/* Dlugosc obrazu aplikacji ESP32 policzona z naglowka. null, gdy naglowek nie trzyma sie kupy. */
function imageLength(data) {
  if (data.length < 24 || data[0] !== REGULY.ESP_MAGIC) return null;
  var nseg = data[1], hashAppended = data[23], pos = 24;
  for (var i = 0; i < nseg; i++) {
    if (pos + 8 > data.length) return null;
    var ln = u32(data, pos + 4);
    pos += 8 + ln;
    if (pos > data.length || ln > 16 * 1024 * 1024) return null;
  }
  pos += 1;                       // bajt sumy kontrolnej
  pos = (pos + 15) & ~15;         // dopelnienie do 16 B
  if (hashAppended === 1) pos += 32;
  return pos <= data.length ? pos : null;
}

/* esp_app_desc_t z offsetu 0x20 */
function appDesc(img) {
  if (img.length < 0x20 + 256) return null;
  if (u32(img, 0x20) !== REGULY.APP_DESC_MAGIC) return null;
  var d = 0x20;
  return {
    project_name: cstr(img, d + 0x30, d + 0x50),
    version:      cstr(img, d + 0x10, d + 0x30),
    time:         cstr(img, d + 0x50, d + 0x60),
    date:         cstr(img, d + 0x60, d + 0x70),
    idf_ver:      cstr(img, d + 0x70, d + 0x90)
  };
}

function parsePartitions(data) {
  var parts = [], pos = REGULY.OFF_PART;
  while (pos + 32 <= data.length && pos < REGULY.OFF_PART + 0xC00) {
    if (data[pos] !== PART_MAGIC[0] || data[pos+1] !== PART_MAGIC[1]) break;  // EBEB = MD5, FFFF = koniec
    parts.push({
      typ: data[pos+2], podtyp: data[pos+3],
      offset: u32(data, pos + 4), rozmiar: u32(data, pos + 8),
      etykieta: cstr(data, pos + 12, pos + 28)
    });
    pos += 32;
  }
  return parts;
}

function hex(n) { return "0x" + n.toString(16).toUpperCase(); }
function liczba(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }

/* ------------------------------------------------------------- analiza .bin */
/* Zwraca Promise z obiektem o polach jak w sprawdz_bin.py analyze():
   rodzaj, rozmiar, sha256, chip, app_desc, bledy[], ostrzezenia[], uwagi[], ok, obraz (Uint8Array). */
function analizuj(nazwaPliku, data) {
  var r = {
    plik: nazwaPliku, ok: false, bledy: [], ostrzezenia: [], uwagi: [],
    rozmiar_pliku: data.length, limit_ota0: REGULY.OTA0_SIZE, obraz: null
  };
  var E = function (pl, en) { r.bledy.push({ pl: pl, en: en }); };
  var W = function (pl, en) { r.ostrzezenia.push({ pl: pl, en: en }); };
  var I = function (pl, en) { r.uwagi.push({ pl: pl, en: en }); };

  return sha256hex(data).then(function (shaPliku) {
    r.sha256_pliku = shaPliku;
    var img = null;

    if (data.length >= 24 && data[0] === REGULY.ESP_MAGIC) {
      r.rodzaj = "czysty";
    } else if (data.length > REGULY.OFF_APP && data[REGULY.OFF_BOOT] === REGULY.ESP_MAGIC &&
               data[REGULY.OFF_PART] === PART_MAGIC[0] && data[REGULY.OFF_PART+1] === PART_MAGIC[1]) {
      r.rodzaj = "scalony";
      var parts = parsePartitions(data);
      r.partycje = parts;
      var apps = parts.filter(function (p) { return p.typ === 0; });
      var app = null;
      for (var i = 0; i < apps.length; i++) if (apps[i].offset === REGULY.OFF_APP) { app = apps[i]; break; }
      if (!app) app = apps.length ? apps[0] : null;
      if (!app) {
        E("scalony obraz bez partycji typu app w tablicy pod 0x8000",
          "merged image with no app-type partition in the table at 0x8000");
        return r;
      }
      if (app.offset !== REGULY.OFF_APP) {
        W("partycja app nie zaczyna sie pod 0x10000 (jest " + hex(app.offset) + ")",
          "the app partition does not start at 0x10000 (it is at " + hex(app.offset) + ")");
      }
      var seg = data.subarray(app.offset, app.offset + app.rozmiar);
      if (seg.length < 24 || seg[0] !== REGULY.ESP_MAGIC) {
        E("pod " + hex(app.offset) + " (partycja '" + app.etykieta + "') nie ma obrazu aplikacji (brak 0xE9)",
          "no application image at " + hex(app.offset) + " (partition '" + app.etykieta + "'): 0xE9 missing");
        return r;
      }
      r.wycieto_z = { etykieta: app.etykieta, offset: app.offset, rozmiar_partycji: app.rozmiar };
      img = seg;
      I("scalony obraz flasha: do K-OS idzie tylko wycieta aplikacja, bootloader i tablica partycji sa ignorowane",
        "merged flash image: only the extracted application goes to K-OS, the bootloader and partition table are ignored");
    } else {
      r.rodzaj = "nieznany";
      E("to nie jest obraz ESP32: brak 0xE9 na bajcie 0 (czysty obraz) ani pod 0x1000 + tablicy AA50 pod 0x8000 (scalony)",
        "this is not an ESP32 image: no 0xE9 at byte 0 (plain image), and no 0xE9 at 0x1000 + AA50 table at 0x8000 (merged)");
      return r;
    }
    if (img === null) img = data;

    var ln = imageLength(img);
    if (ln === null) {
      W("naglowek obrazu nie trzyma sie kupy (segmenty wykraczaja poza plik) - przyjmuje rozmiar pliku",
        "the image header does not add up (segments run past the file) - falling back to the file size");
      if (r.rodzaj === "scalony") {
        var end = img.length;
        while (end > 0 && img[end - 1] === 0xFF) end--;    // awaryjnie: obcinamy wypelnienie 0xFF
        img = img.subarray(0, end);
      }
      ln = img.length;
    } else if (r.rodzaj === "scalony") {
      img = img.subarray(0, ln);
    } else if (ln < img.length) {
      I("plik ma " + (img.length - ln) + " B za obrazem (wypelnienie) - nieszkodliwe",
        "the file has " + (img.length - ln) + " B past the image (padding) - harmless");
    }

    r.segmentow = img[1];
    r.sha256_appended = img[23] === 1;
    var chip = u16(img, 12);
    r.chip = CHIPS[chip] || ("nieznany 0x" + ("0000" + chip.toString(16).toUpperCase()).slice(-4));
    if (chip !== 0) {
      E("obraz dla ukladu " + r.chip + " - CYD ma zwykly ESP32, to sie nie uruchomi",
        "image built for " + r.chip + " - the CYD has a plain ESP32, this will not boot");
    }
    r.rozmiar = img.length;
    r.obraz = img;
    if (img.length > REGULY.OTA0_SIZE) {
      E("za duzy: " + img.length + " B > " + REGULY.OTA0_SIZE + " B (slot ota_0); o " + (img.length - REGULY.OTA0_SIZE) + " B",
        "too big: " + img.length + " B > " + REGULY.OTA0_SIZE + " B (the ota_0 slot); by " + (img.length - REGULY.OTA0_SIZE) + " B");
    } else {
      r.zapas = REGULY.OTA0_SIZE - img.length;
    }
    var d = appDesc(img);
    r.app_desc = d;
    if (!d) {
      W("brak esp_app_desc_t pod 0x20 (to nie jest obraz z ESP-IDF/Arduino?)",
        "no esp_app_desc_t at 0x20 (is this really an ESP-IDF/Arduino image?)");
    } else if (d.project_name === "arduino-lib-builder" || d.project_name === "") {
      I("app_desc z rdzenia Arduino (project_name='arduino-lib-builder') - nazwe i wersje programu bierzemy z meta.json",
        "app_desc comes from the Arduino core (project_name='arduino-lib-builder') - the program name and version come from meta.json");
    }
    r.model_b = { pl: MODEL_B_PL, en: MODEL_B_EN };

    return sha256hex(img).then(function (shaObrazu) {
      r.sha256 = shaObrazu;
      if (!r.sha256_appended) { r.ok = !r.bledy.length; return r; }
      return sha256hex(img.subarray(0, img.length - 32)).then(function (calc) {
        var dolaczony = "";
        for (var i = img.length - 32; i < img.length; i++) dolaczony += ("0" + img[i].toString(16)).slice(-2);
        if (calc !== dolaczony) {
          E("SHA-256 doklejony do obrazu nie zgadza sie z trescia - plik uszkodzony albo zle wyciety",
            "the SHA-256 appended to the image does not match its content - the file is damaged or badly extracted");
        } else {
          I("doklejony SHA-256 obrazu zgadza sie", "the appended image SHA-256 checks out");
        }
        r.ok = !r.bledy.length;
        return r;
      });
    });
  });
}

/* -------------------------------------------------------- meta.json / <id> */
function sprawdzId(zid, zajete) {
  var b = [], w = [];
  if (!zid) {
    b.push({ pl: "podaj <id> - to nazwa katalogu zgloszenia i pliku .bin",
             en: "give an <id> - it is the submission folder and .bin file name" });
  } else if (!ID_RE.test(zid)) {
    b.push({ pl: "zle <id> '" + zid + "': 2-32 znaki, male litery a-z, cyfry, '-' i '_' (pierwszy znak: litera albo cyfra)",
             en: "bad <id> '" + zid + "': 2-32 chars, lowercase a-z, digits, '-' and '_' (first char: a letter or a digit)" });
  }
  if (zid && zajete && zajete.indexOf(zid) >= 0) {
    b.push({ pl: "nazwa '" + zid + "' jest juz zajeta przez program w sklepie - wybierz inna",
             en: "the name '" + zid + "' is already taken by a program in the store - pick another one" });
  }
  return { bledy: b, ostrzezenia: w };
}

/* Walidacja pol meta.json - te same reguly co tools/sprawdz_zgloszenie.py. */
function sprawdzMeta(meta) {
  var b = [], w = [];
  var E = function (pl, en) { b.push({ pl: pl, en: en }); };
  var W = function (pl, en) { w.push({ pl: pl, en: en }); };

  REGULY.WYMAGANE.forEach(function (k) {
    if (!(k in meta)) E("meta.json: brak pola '" + k + "'", "meta.json: field '" + k + "' is missing");
  });
  Object.keys(REGULY).forEach(function (rk) {
    if (rk.indexOf("LIM_") !== 0) return;
    var k = rk.slice(4), lim = REGULY[rk], v = meta[k];
    if (v === undefined || v === null) return;
    if (typeof v !== "string") { E("meta.json: '" + k + "' ma byc tekstem", "meta.json: '" + k + "' must be text"); return; }
    if (!v.trim() && REGULY.WYMAGANE.indexOf(k) >= 0) E("meta.json: '" + k + "' jest puste", "meta.json: '" + k + "' is empty");
    if (v.length > lim) E("meta.json: '" + k + "' za dlugie (" + v.length + " > " + lim + " znakow)",
                          "meta.json: '" + k + "' too long (" + v.length + " > " + lim + " chars)");
    if (["nazwa", "opis", "info", "autor"].indexOf(k) >= 0 && /[^\x00-\x7e]/.test(v)) {
      W("meta.json: '" + k + "' ma znaki poza ASCII - czcionka K-OS ich nie narysuje (zamien np. 'l' zamiast 'ł')",
        "meta.json: '" + k + "' has non-ASCII characters - the K-OS font cannot draw them");
    }
    if (v.indexOf("\n") >= 0 && k !== "info") E("meta.json: '" + k + "' ma byc jedna linia", "meta.json: '" + k + "' must be a single line");
  });
  if (REGULY.PLYTKI.indexOf(meta.plytka) < 0) {
    E("meta.json: 'plytka' musi byc jedna z " + REGULY.PLYTKI.join(", "), "meta.json: 'plytka' must be one of " + REGULY.PLYTKI.join(", "));
  }
  if (REGULY.ORIENT.indexOf(meta.orientacja) < 0) {
    E("meta.json: 'orientacja' musi byc jedna z " + REGULY.ORIENT.join(", "), "meta.json: 'orientacja' must be one of " + REGULY.ORIENT.join(", "));
  }
  if (meta.model_b !== true) {
    E("meta.json: 'model_b' musi byc true - oswiadczenie, ze program kasuje otadata w setup() (albo ma verifyRollbackLater()). Bez tego RST nie wraca do menu.",
      "meta.json: 'model_b' must be true - your declaration that the program erases otadata in setup() (or has verifyRollbackLater()). Without it RST does not return to the menu.");
  }
  var z = meta.zrodlo;
  if (typeof z === "string" && z && !URL_RE.test(z)) {
    E("meta.json: 'zrodlo' ma byc adresem http(s)", "meta.json: 'zrodlo' must be an http(s) address");
  }
  if (typeof meta.licencja === "string" && GPL_RE.test(meta.licencja) && !(typeof z === "string" && z.indexOf("http") === 0)) {
    E("meta.json: licencja GPL wymaga podania 'zrodlo' (URL do zrodel tej wlasnie wersji)",
      "meta.json: a GPL licence requires 'zrodlo' (a URL to the sources of this very build)");
  }
  if (typeof meta.nazwa === "string" && ["test", "program", "app"].indexOf(meta.nazwa.trim().toLowerCase()) >= 0) {
    W("meta.json: 'nazwa' bardzo ogolna - w menu K-OS widac tylko ja", "meta.json: 'nazwa' is very generic - the K-OS menu shows nothing else");
  }
  return { bledy: b, ostrzezenia: w };
}

function metaJson(meta) {
  var kol = ["nazwa", "opis", "wersja", "autor", "licencja", "zrodlo", "plytka", "orientacja", "model_b", "info", "zglaszajacy"];
  var o = {};
  kol.forEach(function (k) {
    var v = meta[k];
    if (v === undefined || v === null) return;
    if (typeof v === "string" && !v.trim() && k === "zglaszajacy") return;
    o[k] = v;
  });
  return JSON.stringify(o, null, 2);
}

var API = {
  REGULY: REGULY, analizuj: analizuj, imageLength: imageLength, appDesc: appDesc,
  parsePartitions: parsePartitions, sha256hex: sha256hex, sha256js: sha256js,
  sprawdzId: sprawdzId, sprawdzMeta: sprawdzMeta, metaJson: metaJson, liczba: liczba
};
if (typeof module !== "undefined" && module.exports) module.exports = API;
global.KOS_ZGLOS = API;

/* ============================================================== strona ==== */
if (typeof document === "undefined") return;

var REPO = "https://github.com/PixelPetrol/korona-programy";
var ISSUES_URL = REPO + "/issues/new";     // jak ISSUES_URL w loader/loader/settings.cpp

document.addEventListener("DOMContentLoaded", function () {
  var $ = function (id) { return document.getElementById(id); };
  var stan = { raport: null, nazwaPliku: null, zajete: null };

  /* --- dwujezyczne komunikaty: ten sam mechanizm co reszta portalu (span[lang]) --- */
  function dwa(msg, tag) {
    var el = document.createElement(tag || "span");
    var pl = document.createElement("span"); pl.setAttribute("lang", "pl"); pl.textContent = msg.pl;
    var en = document.createElement("span"); en.setAttribute("lang", "en"); en.textContent = msg.en || msg.pl;
    el.appendChild(pl); el.appendChild(en);
    return el;
  }
  function jezyk() { return document.documentElement.getAttribute("data-lang") === "en" ? "en" : "pl"; }
  function lista(ul, msgs, klasa) {
    msgs.forEach(function (m) {
      var li = dwa(m, "li");
      if (klasa) li.className = klasa;
      ul.appendChild(li);
    });
  }

  /* --- katalog sklepu: gdy strona idzie z Pages, sprawdzamy kolizje <id> od razu --- */
  (function () {
    if (!global.fetch) return;
    fetch("../katalog.json").then(function (o) { return o.ok ? o.json() : null; }).then(function (k) {
      if (!k || !k.plytki) return;
      var ids = [];
      k.plytki.forEach(function (p) {
        (p.programy || []).forEach(function (pr) {
          var m = /([^/]+)\.bin$/.exec(pr.plik || "");
          if (m && ids.indexOf(m[1]) < 0) ids.push(m[1]);
        });
      });
      stan.zajete = ids;
    }).catch(function () { /* file:// albo brak sieci - trudno, automat sprawdzi to w PR */ });
  })();

  /* ------------------------------------------------------------- plik .bin */
  function pokazBlad(msg) {
    var wyn = $("wynik");
    wyn.hidden = false;
    wyn.innerHTML = "";
    var box = document.createElement("div");
    box.className = "warnbox err";
    box.appendChild(dwa(msg, "b"));
    wyn.appendChild(box);
  }

  function wczytaj(file) {
    if (!file) return;
    stan.raport = null; stan.nazwaPliku = file.name;
    $("krok2").hidden = true;
    $("nazwapliku").textContent = file.name + " · " + liczba(file.size) + " B";
    if (file.size > 32 * 1024 * 1024) {
      pokazBlad({ pl: "plik ma " + liczba(file.size) + " B - to na pewno nie jest obraz dla ESP32",
                  en: "the file is " + liczba(file.size) + " B - that is certainly not an ESP32 image" });
      return;
    }
    var wyn = $("wynik");
    wyn.hidden = false;
    wyn.innerHTML = "";
    wyn.appendChild(dwa({ pl: "sprawdzam...", en: "checking..." }, "p"));
    var fr = new FileReader();
    fr.onerror = function () {
      pokazBlad({ pl: "nie da sie odczytac pliku (" + (fr.error && fr.error.name) + ")",
                  en: "cannot read the file (" + (fr.error && fr.error.name) + ")" });
    };
    fr.onload = function () {
      analizuj(file.name, new Uint8Array(fr.result)).then(function (r) {
        stan.raport = r;
        rysujRaport(r);
        if (r.ok) {
          $("krok2").hidden = false;
          if (!$("f_wersja").value && r.app_desc && r.app_desc.version &&
              r.app_desc.version.length <= REGULY.LIM_wersja && r.app_desc.version !== "1") {
            $("f_wersja").value = r.app_desc.version;
          }
          odswiezMeta();
        }
      }).catch(function (e) {
        pokazBlad({ pl: "blad sprawdzania: " + e, en: "check failed: " + e });
      });
    };
    fr.readAsArrayBuffer(file);
  }

  function wiersz(tab, etyk, wartosc, klasa) {
    var tr = document.createElement("tr");
    var th = document.createElement("th");
    th.appendChild(dwa(etyk));
    var td = document.createElement("td");
    if (typeof wartosc === "string") td.textContent = wartosc; else td.appendChild(wartosc);
    if (klasa) td.className = klasa;
    tr.appendChild(th); tr.appendChild(td); tab.appendChild(tr);
  }

  function rysujRaport(r) {
    var wyn = $("wynik");
    wyn.innerHTML = "";
    wyn.hidden = false;

    var head = document.createElement("p");
    head.className = "wynik-nag";
    var tag = document.createElement("span");
    tag.className = "tag " + (r.ok ? "ok" : "no");
    tag.appendChild(dwa(r.ok ? { pl: "format OK", en: "format OK" } : { pl: "nie nadaje sie", en: "not usable" }));
    head.appendChild(tag);
    head.appendChild(document.createTextNode(" " + r.plik));
    wyn.appendChild(head);

    var tw = document.createElement("div"); tw.className = "tw";
    var tab = document.createElement("table"); tw.appendChild(tab); wyn.appendChild(tw);

    var rodzaje = {
      czysty:   { pl: "czysty obraz aplikacji", en: "plain application image" },
      scalony:  { pl: "scalony obraz flasha", en: "merged flash image" },
      nieznany: { pl: "nierozpoznany", en: "unrecognised" }
    };
    wiersz(tab, { pl: "rodzaj", en: "kind" }, dwa(rodzaje[r.rodzaj] || { pl: r.rodzaj, en: r.rodzaj }));
    if (r.wycieto_z) {
      wiersz(tab, { pl: "wyciete z", en: "extracted from" },
             "'" + r.wycieto_z.etykieta + "' @ " + hex(r.wycieto_z.offset) + " (" + liczba(r.wycieto_z.rozmiar_partycji) + " B)");
    }
    wiersz(tab, { pl: "plik", en: "file" }, liczba(r.rozmiar_pliku) + " B · sha256 " + r.sha256_pliku);
    if (r.rozmiar !== undefined) {
      var zap = document.createElement("span");
      if (r.zapas !== undefined) {
        zap.appendChild(dwa({ pl: liczba(r.rozmiar) + " B  z  " + liczba(r.limit_ota0) + " B",
                              en: liczba(r.rozmiar) + " B  of  " + liczba(r.limit_ota0) + " B" }));
        var mala = document.createElement("small");
        mala.appendChild(dwa({ pl: "  zapas " + liczba(r.zapas) + " B (" + (100 * r.zapas / r.limit_ota0).toFixed(1) + " %)",
                               en: "  headroom " + liczba(r.zapas) + " B (" + (100 * r.zapas / r.limit_ota0).toFixed(1) + " %)" }));
        zap.appendChild(mala);
      } else {
        zap.className = "zle";
        zap.textContent = liczba(r.rozmiar) + " B  >  " + liczba(r.limit_ota0) + " B";
      }
      wiersz(tab, { pl: "obraz / slot ota_0", en: "image / ota_0 slot" }, zap);
      wiersz(tab, { pl: "sha256 obrazu", en: "image sha256" }, r.sha256 || "");
      wiersz(tab, { pl: "uklad", en: "chip" }, r.chip, r.chip === "ESP32" ? "" : "zle");
      wiersz(tab, { pl: "segmentow", en: "segments" },
             dwa({ pl: String(r.segmentow) + (r.sha256_appended ? " · sha256 doklejony do obrazu" : ""),
                   en: String(r.segmentow) + (r.sha256_appended ? " · sha256 appended to the image" : "") }));
    }
    var d = r.app_desc;
    if (d) {
      wiersz(tab, { pl: "app_desc: project_name", en: "app_desc: project_name" }, d.project_name || "—");
      wiersz(tab, { pl: "app_desc: version", en: "app_desc: version" }, d.version || "—");
      wiersz(tab, { pl: "app_desc: idf_ver", en: "app_desc: idf_ver" }, d.idf_ver || "—");
      wiersz(tab, { pl: "app_desc: kompilacja", en: "app_desc: built" }, ((d.date || "") + " " + (d.time || "")).trim() || "—");
    }

    if (r.bledy.length) {
      var h = dwa({ pl: "BLEDY", en: "ERRORS" }, "p"); h.className = "lbl zle"; wyn.appendChild(h);
      var ul = document.createElement("ul"); ul.className = "msg zle"; lista(ul, r.bledy); wyn.appendChild(ul);
    }
    if (r.ostrzezenia.length) {
      var h2 = dwa({ pl: "UWAGI", en: "WARNINGS" }, "p"); h2.className = "lbl ostrz"; wyn.appendChild(h2);
      var ul2 = document.createElement("ul"); ul2.className = "msg ostrz"; lista(ul2, r.ostrzezenia); wyn.appendChild(ul2);
    }
    if (r.uwagi.length) {
      var h3 = dwa({ pl: "info", en: "info" }, "p"); h3.className = "lbl"; wyn.appendChild(h3);
      var ul3 = document.createElement("ul"); ul3.className = "msg"; lista(ul3, r.uwagi); wyn.appendChild(ul3);
    }

    /* obraz scalony -> zaproponuj czysty */
    if (r.rodzaj === "scalony" && r.obraz) {
      var box = document.createElement("div");
      box.className = "warnbox";
      box.appendChild(dwa({
        pl: "To jest scalony obraz calego flasha. Do sklepu i tak trafi tylko wycieta z niego aplikacja - zglos od razu czysty obraz aplikacji (Arduino IDE: *.ino.bin, NIE *.ino.merged.bin; PlatformIO: firmware.bin). Jesli nie masz go pod reka, pobierz wycinek ponizej - to bajt w bajt to, co zrobi z Twoim plikiem automat.",
        en: "This is a merged image of the whole flash. Only the application extracted from it goes to the store - submit the plain application image instead (Arduino IDE: *.ino.bin, NOT *.ino.merged.bin; PlatformIO: firmware.bin). If you do not have it at hand, download the extract below - it is byte for byte what the automation will make of your file."
      }, "p"));
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "btn";
      btn.appendChild(dwa({ pl: "pobierz wycieta aplikacje (.bin)", en: "download the extracted application (.bin)" }));
      btn.addEventListener("click", function () {
        var zid = ($("f_id").value || "").trim();
        pobierz(new Blob([r.obraz.slice()], { type: "application/octet-stream" }),
                (ID_RE.test(zid) ? zid : "aplikacja") + ".bin");
      });
      box.appendChild(btn);
      wyn.appendChild(box);
    }

    /* ostrzezenie o Modelu B - przy KAZDYM pliku, takze poprawnym */
    var mb = document.createElement("div");
    mb.className = "warnbox modelb";
    mb.appendChild(dwa({ pl: "Czego ta strona NIE sprawdzila: Model B", en: "What this page did NOT check: Model B" }, "b"));
    mb.appendChild(dwa({
      pl: " Z binarki nie da sie wyczytac, czy program na poczatku setup() kasuje otadata. To kod maszynowy, nie tekst - nie udaje, ze to sprawdzilem. Bez Modelu B RST nie wraca do menu K-OS i plytke odzyskasz tylko kablem USB. Jedyny test: wgraj .bin na karte, uruchom pod K-OS, nacisnij RST - musi wrocic menu.",
      en: " A binary cannot tell whether the program erases otadata at the start of setup(). That is machine code, not text - I am not pretending to have checked it. Without Model B, RST does not return to the K-OS menu and the board is only recoverable over a USB cable. The only test: copy the .bin to the card, run it under K-OS, press RST - the menu must come back."
    }, "p"));
    var pl2 = document.createElement("p");
    var a1 = document.createElement("a"); a1.href = "programy.html#modelb";
    a1.appendChild(dwa({ pl: "jak dopisac Model B (6 linii)", en: "how to add Model B (6 lines)" }));
    var a2 = document.createElement("a"); a2.href = "programy.html#test";
    a2.appendChild(dwa({ pl: "test na plytce", en: "test on the board" }));
    pl2.appendChild(a1); pl2.appendChild(document.createTextNode(" · ")); pl2.appendChild(a2);
    mb.appendChild(pl2);
    wyn.appendChild(mb);
  }

  function pobierz(blob, nazwa) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nazwa;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  /* ------------------------------------------------------------- formularz */
  function zbierz() {
    return {
      nazwa: $("f_nazwa").value.trim(),
      opis: $("f_opis").value.trim(),
      wersja: $("f_wersja").value.trim(),
      autor: $("f_autor").value.trim(),
      licencja: $("f_licencja").value.trim(),
      zrodlo: $("f_zrodlo").value.trim(),
      plytka: $("f_plytka").value,
      orientacja: $("f_orientacja").value,
      model_b: $("f_modelb").checked,
      info: $("f_info").value.trim(),
      zglaszajacy: $("f_zglaszajacy").value.trim()
    };
  }

  function odswiezMeta() {
    var zid = $("f_id").value.trim();
    var meta = zbierz();
    var wid = sprawdzId(zid, stan.zajete);
    var wm = sprawdzMeta(meta);
    var bledy = wid.bledy.concat(wm.bledy), ostrz = wid.ostrzezenia.concat(wm.ostrzezenia);

    var box = $("metabledy");
    box.innerHTML = "";
    if (bledy.length) { var u = document.createElement("ul"); u.className = "msg zle"; lista(u, bledy); box.appendChild(u); }
    if (ostrz.length) { var u2 = document.createElement("ul"); u2.className = "msg ostrz"; lista(u2, ostrz); box.appendChild(u2); }

    var json = metaJson(meta);
    $("metajson").textContent = json;
    var gotowe = !bledy.length && stan.raport && stan.raport.ok;
    $("btn-issue").disabled = !gotowe;
    $("btn-meta").disabled = !gotowe;
    $("btn-kopiuj").disabled = !gotowe;
    $("sciezki").textContent = gotowe
      ? "zgloszenia/" + zid + "/" + zid + ".bin\nzgloszenia/" + zid + "/meta.json"
      : "zgloszenia/<id>/<id>.bin\nzgloszenia/<id>/meta.json";
    return { zid: zid, meta: meta, json: json, gotowe: gotowe };
  }

  /* ------------------------------------------------------- tresc zgloszenia */
  function trescZgloszenia(zid, json) {
    var r = stan.raport, pl = jezyk() === "pl";
    var d = r.app_desc || {};
    var L = [];
    if (pl) {
      L.push("### Zgloszenie programu do sklepu K-OS: `" + zid + "`");
      L.push("");
      L.push("Sprawdzone w przegladarce na portalu (`portal/zglos.html`, reguly przepisane z `tools/sprawdz_bin.py`):");
      L.push("");
      L.push("- plik: `" + r.plik + "`, " + r.rodzaj + ", " + r.rozmiar_pliku + " B");
      L.push("- obraz aplikacji: **" + r.rozmiar + " B** z " + r.limit_ota0 + " B (zapas " + (r.zapas || 0) + " B), uklad " + r.chip);
      L.push("- sha256 obrazu: `" + r.sha256 + "`");
      if (r.rodzaj === "scalony") L.push("- sha256 calego pliku: `" + r.sha256_pliku + "`");
      if (r.app_desc) L.push("- app_desc: `" + d.project_name + "` `" + d.version + "` idf `" + d.idf_ver + "` (" + d.date + " " + d.time + ")");
      L.push("");
      L.push("```json");
      L.push(json);
      L.push("```");
      L.push("");
      L.push("**Model B** (tego strona sprawdzic nie umie - to kod, nie tekst):");
      L.push("");
      L.push("- [ ] uruchomilem program pod K-OS i nacisnalem RST - wrocilo menu K-OS");
      L.push("");
      L.push("**Plik `.bin`** (GitHub nie przyjmuje zalacznikow `.bin`):");
      L.push("");
      L.push("- [ ] spakowany do `.zip` i przeciagniety do tego zgloszenia, albo");
      L.push("- [ ] link do wydania/repozytorium: ");
      L.push("");
      L.push("Docelowo zgloszenie to Pull Request z katalogiem `zgloszenia/" + zid + "/`");
      L.push("(`" + zid + ".bin` + `meta.json`) - patrz [instrukcja](https://pixelpetrol.github.io/korona-programy/portal/programy.html#sklep).");
    } else {
      L.push("### Program submission for the K-OS store: `" + zid + "`");
      L.push("");
      L.push("Checked in the browser on the portal (`portal/zglos.html`, rules transcribed from `tools/sprawdz_bin.py`):");
      L.push("");
      L.push("- file: `" + r.plik + "`, " + r.rodzaj + ", " + r.rozmiar_pliku + " B");
      L.push("- application image: **" + r.rozmiar + " B** of " + r.limit_ota0 + " B (headroom " + (r.zapas || 0) + " B), chip " + r.chip);
      L.push("- image sha256: `" + r.sha256 + "`");
      if (r.rodzaj === "scalony") L.push("- whole-file sha256: `" + r.sha256_pliku + "`");
      if (r.app_desc) L.push("- app_desc: `" + d.project_name + "` `" + d.version + "` idf `" + d.idf_ver + "` (" + d.date + " " + d.time + ")");
      L.push("");
      L.push("```json");
      L.push(json);
      L.push("```");
      L.push("");
      L.push("**Model B** (the page cannot check this - it is code, not text):");
      L.push("");
      L.push("- [ ] I ran the program under K-OS and pressed RST - the K-OS menu came back");
      L.push("");
      L.push("**The `.bin` file** (GitHub does not accept `.bin` attachments):");
      L.push("");
      L.push("- [ ] zipped and dragged into this issue, or");
      L.push("- [ ] link to a release/repository: ");
      L.push("");
      L.push("The final submission is a Pull Request with the `zgloszenia/" + zid + "/` folder");
      L.push("(`" + zid + ".bin` + `meta.json`) - see the [instructions](https://pixelpetrol.github.io/korona-programy/portal/programy.html#sklep).");
    }
    return L.join("\n");
  }

  /* --------------------------------------------------------------- klikanie */
  var wej = $("plik");
  $("wybierz").addEventListener("click", function () { wej.click(); });
  wej.addEventListener("change", function () { wczytaj(wej.files[0]); });

  var strefa = $("strefa");
  ["dragenter", "dragover"].forEach(function (t) {
    strefa.addEventListener(t, function (e) { e.preventDefault(); strefa.classList.add("nad"); });
  });
  ["dragleave", "drop"].forEach(function (t) {
    strefa.addEventListener(t, function (e) { e.preventDefault(); strefa.classList.remove("nad"); });
  });
  strefa.addEventListener("drop", function (e) {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) wczytaj(e.dataTransfer.files[0]);
  });

  ["f_id", "f_nazwa", "f_opis", "f_wersja", "f_autor", "f_licencja", "f_zrodlo", "f_plytka",
   "f_orientacja", "f_modelb", "f_info", "f_zglaszajacy"].forEach(function (id) {
    var el = $(id);
    el.addEventListener("input", odswiezMeta);
    el.addEventListener("change", odswiezMeta);
  });

  $("btn-meta").addEventListener("click", function () {
    var s = odswiezMeta();
    if (!s.gotowe) return;
    pobierz(new Blob([s.json + "\n"], { type: "application/json" }), "meta.json");
  });

  $("btn-kopiuj").addEventListener("click", function () {
    var s = odswiezMeta();
    if (!s.gotowe) return;
    var t = $("metajson").textContent;
    var ok = function () {
      var b = $("btn-kopiuj");
      b.classList.add("zrobione");
      setTimeout(function () { b.classList.remove("zrobione"); }, 1500);
    };
    if (global.navigator && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(t).then(ok, function () { zaznacz($("metajson")); });
    } else {
      zaznacz($("metajson"));
    }
  });

  function zaznacz(el) {
    var rng = document.createRange(); rng.selectNodeContents(el);
    var sel = global.getSelection(); sel.removeAllRanges(); sel.addRange(rng);
  }

  $("btn-issue").addEventListener("click", function () {
    var s = odswiezMeta();
    if (!s.gotowe) return;
    var tytul = "zgloszenie: " + s.zid + " " + s.meta.wersja + " (" + s.meta.plytka + ")";
    var tresc = trescZgloszenia(s.zid, s.json);
    var url = ISSUES_URL + "?title=" + encodeURIComponent(tytul) + "&body=" + encodeURIComponent(tresc);
    if (url.length > 7500) {           // dluzsze adresy GitHub potrafi uciac
      $("dlugie").hidden = false;
      $("dlugatresc").textContent = tresc;
      return;
    }
    $("dlugie").hidden = true;
    global.open(url, "_blank", "noopener");
  });
});

})(typeof window !== "undefined" ? window : globalThis);
