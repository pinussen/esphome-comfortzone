# Protocol 170: överlappande läsningar och fler avkodade värden

Analys 2026-10-24 av pump `656fde02`, genom ESP32 `08:B6:1F:38:5A:C0`.
Denna undersökning var passiv: inga pumpinställningar ändrades och ingen OTA gjordes.

## Underlag och begränsningar

- Marsfångsterna: `/home/bjwl/comfortzone-debug-{1,2,3}.pcap`.
- Tidigare färsk fångst: `/home/bjwl/comfortzone-write-probe-2026-10-24-idle-edge/capture.pcap`.
- Ny fyraminutersfångst: `/home/bjwl/comfortzone-passive-decode-2026-10-24/`.
  Där finns `capture.pcap`, `device.log`, `events.json` (API-värden),
  `decoded.json` (avkodning och registerstatistik), `events.csv` (pumpens historik)
  och `capture_readonly.py` (det använda insamlingsskriptet).

Den nya fångsten innehåller 763 CRC-giltiga ramar, 374 läsfrågor och 389 lässvar,
fördelade på 35 lästa registeradresser. UDP-forwarding garanterar inte att varje
busstransaktion finns med; antalet frågor och svar skiljer sig också i fångsten.
Pumpens minneskortsstatus antecknades inte. Inga slutsatser om exakt vilka
register som försvinner utan kort kan dras ännu.

## Tre olika sorters upprepning

1. **Gamla debug-dubletter.** Marsfångsterna har 22 839 giltiga ramar, varav
   21 687 är identiska med föregående ram inom 100 ms (95,0 procent).
   Detta stämmer med det tidigare hittade felet där debug-forwardingen skickade
   samma mottagningsbuffert flera gånger. Den nya fångsten har noll sådana
   snabba upprepningar. Måttet ensamt bevisar inte orsaken till en dublett.
2. **Återkommande läsning av oförändrade värden.** Historik och inställningar
   läses om även när innehållet inte har ändrats. De tre historikblockens
   8 176 databytes utgör 26,0 procent av svarens totalt 31 482 databytes.
   Detta är andel av fångade svarsdata, inte andel av all trafik på ledningen.
3. **Överlappande adressområden.** Små block och stora block delar samma bytes.
   Registrets sista tre bytes tolkas som bank, adressens låga byte, höga byte.
   Adressen är en byteadress inom banken. Det gäller de jämförda områdena;
   bitkommandon i andra banker ska inte automatiskt tolkas likadant.

Exempel med oförändrade inställningsbytes i den nya fångsten:

| Bank | Blockens startadresser | Gemensamma bytes per jämförelse | Helt lika jämförelser |
| --- | --- | ---: | ---: |
| 00 | 0214 / 029d | 23 | 3/3 |
| 00 | 02c6 / 0320 | 87 | 4/4 |
| 00 | 0320 / 0377 | 84 | 6/6 |
| 00 | 0377 / 03d2 | 87 | 4/4 |
| 00 | 0429 / 049e | 60 | 8/8 |
| 00 | 049e / 04da | 55 | 8/8 |

Jämförelserna använder svar högst tio sekunder från varandra. Nollfyllda
områden redovisas också i JSON men räcker inte som bevis för adressmodellen.
Levande temperaturer, räknare och klockslag kan ändras mellan två läsningar.

## Avkodade områden

Adresser nedan är hexadecimala byteadresser. Värdena är exempel från fångsterna,
inte löften om aktuella värden efter undersökningen.

| Bank:adress | Tolkning | Format / exempel | Stöd |
| --- | --- | --- | --- |
| 00:02a5 | Värmekurva | uint8, 5 | Tidigare paneländringar dokumenterade i biblioteket; finns även i överlappande block |
| 00:02a6 | Befintligt värmebörvärde | LE16 / 10, 30,0 °C | Befintlig avkodning och återläsning |
| 00:0373 | Varmvattenbörvärde | LE16 / 10, 53,1 °C | Tidigare panelbekräftat; syns också i 00:c602 |
| 00:0419 | Dagar till filterbyte | LE16, 55 | Befintlig avkodning, båda överlappande block |
| 01:0004 | Pumpens klocka | Binära byte: timme, minut, sekund, dag, månad, år sedan 2000, veckodag | Kalendergiltiga datum och löpande tid |
| 01:0032 + 2×n | Givarfält TEn | Signed LE16 / 10 | Samma bytes i stora och korta ramar; befintliga givarnamn behålls |
| 01:0062 | TE24, varmvatten | Signed LE16 / 10 | Sista två databytes i korta temperatursvaret |
| 05:002c, 0030, 0034 | Kompressor-, tillsats-, varmvattenenergi | LE32 / 100 kWh | Exakt samma fält som i befintlig lång avkodning |
| 05:0038, 003c | Kompressor-/total drifttid | LE32 minuter | Samma fält som i befintlig lång avkodning |

Offlineverktyget visar även TE10 (26,1 °C i dessa fångster), utan att gissa
vilken fysisk givare den motsvarar. Det markerar -990/-999 som saknade
temperaturvärden; råbytes finns kvar i PCAP. Det ändrar inte sensorer i HA.

Om pumpens klocka tolkas som Europe/Stockholm ligger den cirka 4 minuter och
8 sekunder före fångstdatorns tidsstämplar (247–248 sekunder i samtliga
avkodade klocksvar). Ingen klocka ändrades. Historikens tider återges som
pumpen lagrat dem, utan automatisk korrigering av denna skillnad.

## Daterad historik: bank 03, adress 0d15

Blocken `03 15 0d`, `03 c7 0d` och början av `03 79 0e` bildar ett
sammanhängande område på 422 bytes:

- En inledande byte, 26 i den nya fångsten.
- 30 poster à 14 bytes: dag, månad, år sedan 2000, timme, minut, sekund,
  två ännu inte namngivna kodbyte samt sex ytterligare bytes.
- En avslutande byte. Dess betydelse är okänd.

Alla 30 poster har giltiga datum. Den nya fångstens datum sträcker sig från
2026-03-22 till 2026-10-16. Marsfångsterna ger samma struktur med datum från
2026-01-06 till 2026-02-27. Poster passerar ramgränser, så varje ram kan inte
avkodas oberoende som en hel lista.

Exempel, de två kodbytena återges utan att tillskrivas en obekräftad betydelse:

| Datum enligt pumpen | Kodbyte 1 | Kodbyte 2 |
| --- | ---: | ---: |
| 2026-09-20 10:27:33 | 1 | 18 |
| 2026-09-20 10:27:38 | 2 | 18 |
| 2026-09-20 10:27:40 | 3 | 18 |
| 2026-10-16 07:50:45 | 0 | 0 |

Ordningen och huvudbyten är förenliga med en ringbuffert: nästa skrivplats
skulle vara plats 26 (nollbaserat). Kod 18 och 1 återkommer i sekvenserna
1→2→3. Det liknar larmhändelser med tillståndsövergångar, men betydelser som
"aktiverat", "kvitterat" eller "återställt" är **inte bekräftade**.
Historiken kan vara lagrad internt även om minneskortet orsakar extra läsningar.

## Två temperaturserier i flyttalsformat

Bank 01 vid adresserna `00e1` och `0111` innehåller vardera 12 little-endian
float32-värden. Delat med tio ger de temperaturer som ligger mycket nära
givarfälten. De återfinns i blocket `01 b2 00`.

Exempel från tidigare fångst:

| Index | Serie 00e1 | Serie 0111 | Trolig motsvarighet |
| --- | ---: | ---: | --- |
| 0 | 10,300 | 10,300 | TE0 |
| 1 | 36,201 | 36,206 | TE1 |
| 2 | 26,600 | 26,600 | TE2 |
| 3 | 23,900 | 23,900 | TE3 |
| 4 | 43,723 | 44,060 | TE4 |
| 5 | 36,540 | 36,582 | TE5 |
| 6 | 7,400 | 7,001 | TE6 |
| 7 | 51,700 | 51,700 | TE24 |
| 8 | 5,616 | 4,628 | TE7 |
| 9–10 | 0 | 0 | Okänt |
| 11 | 26,100 | 26,100 | TE10 |

Seriernas skillnader kan bero på filtrering eller olika uppdateringstid.
Det är inte fastställt vilken som är rå, filtrerad eller tidigare avläsning.
Fler decimaler innebär inte att givarna mäter mer exakt. Dessa fält finns
enbart som tydligt märkta kandidater i offlineanalysen.

## Ändring i avkodaren

Två tidigare outnyttjade korta svar har nu riktiga avkodare:

- `01 04 00`, 118 bytes totalt: nio befintliga temperaturgivare.
- `05 2c 00`, 42 bytes totalt: fem befintliga energi-/drifttidsräknare.

Under fyra minuter fångades 17 sådana temperatursvar men bara tre fulla
temperaturblock, samt 13 korta räknarsvar men bara två fulla energiblock.
I tidigare fångst kom korta svar ungefär var sjunde sekund; i den nya fångsten
är intervallen ojämnare. Samma temperaturadress används även för ett 28-byte
klocksvar. Detta ska inte tolkas som ett temperatursvar.

Denna ändring gör läsningen mindre beroende av de stora blocken, vilket är
relevant för minneskortshypotesen. Den löser inte den ännu öppna skrivfrågan.

Validering: fem Python-tester med fångade ramar, hosttester under ASan/UBSan
med 23 241 återspelade ramar, samt lyckat ESPHome 2026.10.0 / ESP-IDF 5.5.6-bygge.
Testerna täcker bland annat korta svar utan föregående stort block, avklippt
TE24, annan protokollversion, CRC-fel, blockgränser i historiken och för gamla
eller saknade historikdelar.

**Uppdatering 2026-10-25:** avkodarna är nu installerade tillsammans med
DE-pulstestet i bygget `2026-10-25 00:39:02 +0200`, SHA-256
`6bb51144ac49433c3ba66de7002313c61579b89b922238bc25900fcd56bb9c4f`.
Se `DIAGNOSTIK.md` för installation och uppföljning.

Den ursprungliga separata testbinären (inte installerad som sådan) finns som
`/home/bjwl/comfortzone-passive-decode-2026-10-24/firmware-short-decoders.ota.bin`,
SHA-256 `d1fc006e5133ee8d0834f07a01bb4ec970d86a4f61f1322116af596cddc68c36`.
Det inkrementella bygget behåller tidigare build_time_str; använd hashen för
att identifiera denna äldre testbinär.

## Köra analysen igen

```bash
python3 pcap_decode_v170.py capture.pcap --output decoded.json
python3 tests/test_pcap_decode_v170.py
python3 tests/run_host_tests.py --fastcrc /tmp/comfortzone-FastCRC capture.pcap
```

Verktyget gör ingen nätverksanslutning. Det kontrollerar ramstorlek och båda
adress-CRC samt ram-CRC, håller banker och pumpadresser åtskilda, redovisar
överlappar och avkodar historik endast när delarna ligger inom tio sekunder.

Nästa särskiljande mätning är två lika långa passiva fångster med dokumenterad
minneskortsstatus, samma panelsida och utan samtidigt skrivtest. Jämför antal
läsningar per minut, adresser och svarslängder. Då kan vi avgöra vilka stora
block som faktiskt beror på kortet. Ett foto av pumpens händelse-/larmlista
kan samtidigt ge namn åt historikens numeriska koder.

## Implementationsuppdatering 2026-10-25

Firmware använder nu `comfortzone_decoder_v170.cpp` för hela bank-/adressområden,
inte endast namngivna paketstarter. En kortare ram kan fortfarande uppdatera de
fält som finns fullständigt i ramen. Två avklippta halvor kombineras aldrig.
`00:0373` fungerar därför även när samma inställningsbytes kommer från ett annat
överlappande block än den tidigare 193-byte-ramen.

TE10, pumpklocka, råa larmmasker och fler inställningar kan nu publiceras i HA via
`comfortzone-protocol170.yaml`. Den ursprungliga texten ovan beskriver den passiva
undersökningen den 24 oktober; dessa firmwareändringar är ett senare steg.
Ärvda parameternamn och menyprioritering finns i [CODE-REVIEW.md](CODE-REVIEW.md).

Värmeregistret `00:02a6` återlästes den 25 oktober som 29,1 °C efter tidigare
32,0 °C. Användaren bekräftade därefter att sänkningen gjordes avsiktligt från HA.
Detta är alltså en lyckad återläsning av HA-ändringen, inte belägg för en
spontan ändring eller återställning i pumpen.

## Drift- och frekvenskandidater, 2026-10-25 kväll

Ny passiv fångst 18:51–18:54 lokal tid från ersättningskortet, med oförändrad
firmware byggd 15:36:20 och bibliotek `42fc53447755`:
`/home/bjwl/comfortzone-frequency-mode-20261025-185102/`.
564 fullständiga CRC-giltiga ramar mottogs under tre minuter. UDP-fångsten kan
ändå ha luckor. Ingen pumpinställning eller firmware ändrades.

Användaren rapporterade stabil kompressorfrekvens **28,3 Hz** under fångsten;
exakt avläsningstid och driftläge var inte kända. Råvärdet 283 finns bland annat
18:52:35 och 18:52:49. Flera närliggande fält följs åt under stabil drift, så
denna kontroll skiljer inte faktiskt varvtal från begärt varvtal.

Tabellen visar råa heltal i bank 01. Frekvenshypoteserna använder skalan /10.
Intervallen är från respektive fångst; kolumnerna ska inte tolkas som samtidiga
värden från ett gemensamt ögonblick.

| Fångst | Statusbyte 0018 | 02d5 | 02d7 | 02d9 | 02e9 |
| --- | --- | --- | --- | --- | --- |
| `comfortzone-debug-2026-10-24-target.pcap` | 0x2A | 346–349 | 0 | 346–349 | 309 |
| `comfortzone-passive-decode-2026-10-24/capture.pcap` | 0x2C | 0 | 300 | 300 | 300 |
| `comfortzone-review-live-2026-10-25/capture.pcap` | 0x08 | 0 | 0 | 0 | 0 |
| Ny kvällsfångst | 0x2A | 282–288 | 0 | 282–288 | 282–288 |

Det befintliga frekvensfältet `01:02d5` är alltså **inte alltid noll**. En hypotes
är att det hör till värmedrift, medan `01:02d7` hör till varmvatten och `01:02d9`
är en gemensam frekvens efter ytterligare villkor. `01:02e9` är en kandidat till
faktisk frekvens, eftersom det avviker från 02d5/02d9 i målfångsten men följer
dem i den stabila kvällsfångsten. Dessa benämningar är ännu inte verifierade.

Ett viktigt motexempel finns i `comfortzone-debug-2.pcap`: i 13 av 19 avduplicerade
svar är `02d7 = 300` medan `02d9 = 0`. Den gemensamma frekvensen kan därför
**inte generellt ersättas med max(02d5, 02d7)**. Råfångster behövs också vid
start, stopp och avfrostning, inte bara under stabil kompressordrift.

Statusbytet `01:0018` ligger på samma byteadress som `unknown3[9]` i den äldre
1.80-strukturen. Där tolkas bitarna 1–2 som driftval och 4–5 som kompressorstatus.
Den tolkningen skulle ge värme/körning för 0x2A, varmvatten/körning för 0x2C
och vila/stopp för 0x08. Detta passar observerade effekt- och temperaturförlopp,
men är en **hypotes för 170**, inte skäl att återanvända hela 1.80-avkodaren.

`01:02cb` varierar också i ett numeriskt rimligt frekvensintervall, men följer
temperaturnivåer och har den ärvda benämningen kondenseringstemperatur. Att ett
tal ser ut som Hz räcker alltså inte för att flytta frekvensavkodningen dit.

Nästa kontroll: panelens driftläge och frekvens under en naturlig övergång
mellan husvärme och varmvatten, med tidsmatchad fångst av 0018 och området
02d5–02eb. Dokumentera även effekt och faktisk/förväntad frekvens vid övergången.
Enligt [EX50-manualen, sida 5](https://www.vvsbutiken.nu/dokument/cz06025_manual__ex35_ex50_ex65_b.pdf#page=5)
visas driftläge, husvärme och varmvatten under Driftinformation.

Analysen kan upprepas med `analyze_fields.py` i fångstkatalogen; `comparison.json`
innehåller fångsthashar, separata enheter, råramar, tidsstämplar, intervall och
kontroller inom samma ram. Snabba identiska efterföljande lässvar (<100 ms)
räknas separat. Ett litet urval av 14 CRC-kontrollerade råramar med ursprung
finns i [tests/v170_operating_candidates.json](tests/v170_operating_candidates.json).
Ingen ny registerbetydelse har aktiverats i firmware på grundval av dessa kandidater.

### Panelbekräftelse: husvärme

Användaren bekräftade därefter **Husvärme**, först 28,5 Hz / 2268 W / 0 W tillsats,
sedan 28,7 Hz / 2282 W och 28,6 Hz / 2275 W. En ny passiv minut fångades i
`/home/bjwl/comfortzone-panel-heating-20261025-185925/` med 180 UDP-payloads.
Exakta paneltidsstämplar saknas, men båda senare värdeparen finns i fångsten:

| Lokal fångsttid | 02d5 / 10 | 0313 | 0317 | Närmast föregående 0018 |
| --- | --- | --- | --- | --- |
| 18:59:28,865 | 28,7 Hz | 2282 W | 0 W | 0x2A, 0,329 s tidigare |
| 19:00:11,112 | 28,6 Hz | 2275 W | 0 W | 0x2A, 0,330 s tidigare |

Detta ger panelstöd för **0018 = 0x2A vid pågående husvärme** och för att de
befintliga frekvens-/effektfälten matchar panelen i detta driftfall. Det första
värdeparet 28,5 / 2268 har inte matchats i denna fångst som startade efter rapporten.
Eftersom 02d5, 02d9 och 02e9 är lika här skiljer mätningen inte faktisk frekvens
från begärd frekvens. Vid 0 W tillsats är även 0313 och 0319 lika, så deras
respektive betydelse måste kontrolleras vid tillsatsdrift.

Råramar och panelobservationer finns i
[tests/v170_panel_heating_fixtures.json](tests/v170_panel_heating_fixtures.json)
och ingår i offline-regressionstesterna. Nästa kontroll är samma panelavläsning
under varmvattenproduktion och vid driftväxling. Ingen generell statusbitstolkning
eller ny firmware har aktiverats utifrån bara husvärmefallet.

### Kontrollerad extra-varmvattensekvens och frekvensfix

Fångst `/home/bjwl/comfortzone-panel-extra-hw-20261025-190250/`, sex minuter,
1675 mottagna CRC-giltiga UDP-payloads: 839 R, 834 r, en W och en w.
Råfilens SHA256: `f15d1da23147fd491f8c59bd084c1dc4bde3f3e74b22f622bb63c81e497cdf66`.
Alla mottagna ramar klarar CRC; att antalen frågor/svar skiljer sig visar att
detta inte är en garanterat komplett bussfångst.

Användaren slog på Extra varmvatten, bekräftade varmvattenläge och **30 Hz /
2376 W**, slog av funktionen och såg sedan nedvarvning, blinkande snöflinga
med droppar och nollvärden. Symbolen är förenlig med avfrostning, men dess
betydelse fastställdes inte genom manualens sökbara text. Detta är inte belägg
för att avstängningen av extrafunktionen orsakade avfrostningen.

| Lokal tid | Händelse / observation | 0017 | 0018 | 001b |
| --- | --- | --- | --- | --- |
| 19:03:03 | Husvärme före testet | 28 | 2A | 10 |
| 19:03:13,056 | Panelens W: `81:0017`, mask `01 00` | — | — | — |
| 19:03:14 | Extra varmvatten aktivt, panelen bekräftar varmvatten | 2B | 2E | 10 |
| 19:04:09,742 | w till panelen: `41:0017`, returbyte `2E` | — | — | — |
| 19:04:29 | Extra av, produktion fortsätter | 28 | 2E | 10 |
| 19:05:04 | Övergång | 28 | AE | 10 |
| 19:05:11 | Nedvarvning | 28 | BE | 10 |
| 19:05:18 och framåt | Noll frekvens/effekt, snöflingesymbol rapporterad | 28 | 1E | 16 |

Själva W för avstängningen och w för aktiveringen saknas i UDP-fångsten;
de två fångade skrivramarna ska därför inte redovisas som ett komplett par.
Ändringen `2B -> 28` i 0017 stödjer att extrafunktionen stängdes av. Status
0018 och pågående varmvattenproduktion kvarstod därefter. Lägesbitarna kan
beskriva samtidiga begäranden snarare än uteslutande aktuell värmeleverans.
`0x2E` får alltså inte utan vidare klassas som både faktisk husvärme och varmvatten.

| Råram | Äldre fält 02d5 | Kandidat begärd 02d9 | Faktisk 02e9 | Effekt 0313 |
| --- | --- | --- | --- | --- |
| Husvärme | 29,2 Hz | 29,2 Hz | 29,2 Hz | 2319 W |
| Uppvarvning efter Extra på | 29,3 Hz | 30,0 Hz | 29,7 Hz | 2355 W |
| Panelbekräftat varmvatten | 29,3 Hz | 30,0 Hz | 30,0 Hz | 2376 W |
| Panelbekräftade nollvärden | 29,3 Hz | 0 Hz | 0 Hz | 0 W |

**Frekvensavkodningen ändras till 01:02e9, LE16 / 10**, i både den generella
170-avkodaren och den äldre Status 06-strukturen samt offlineverktyget.
En statisk offsetkontroll skyddar strukturens fältplacering. Råramarna finns i
[tests/v170_frequency_fixtures.json](tests/v170_frequency_fixtures.json).
Hosttesterna kontrollerar hela sekvensen, den äldre avkodningsvägen och
avklippta frekvensfält. Driftläge, CoP-fördelning och avfrostningsbitar aktiveras
inte genom denna ändring; de behöver separat validering av begäran kontra drift.

Validering: nio Python-tester, hosttester under ASan/UBSan inklusive återspelning
av samtliga 1675 fångade payloads, samt gränstester för 160/180/221 (200
registeradresser × 234 längder per version). ESPHome 2026.10.0 / ESP-IDF 5.5.6
byggde TX26-konfigurationen 2026-10-25 19:10:17 utan C++-varningar, med
bibliotekssnapshot `9d607b7161fbe2282a4a89607ff4f9772d9ef2fc`.
Ingen OTA utfördes under denna kontroll; installation via HA kan hämta fixen
från samma arbetsgren.
