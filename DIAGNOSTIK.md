# ComfortZone Diagnostik

## Aktuellt: TX flyttad till GPIO26 på lödda inre raden, 2026-10-25

**Faktisk ändring 30,0 → 32,0 °C verifierad via protokollet.** Användaren bad
uttryckligen om 32 °C för kontroll på pumpens panel. En skrivning skickades,
kvitterades efter 39,415 ms och följdes av tre CRC-giltiga registerläsningar
med 32,0 °C (före skrivningen 30,0). Varmvatten kvar 53,1 °C, CRC-fel 0 och
uptime ökade från 263 till 303 s utan omstart. **Börvärdet lämnat på 32,0 °C
enligt användarens begäran; panelbekräftelse återstår.**
Fångst: `~/comfortzone-set32-2026-10-25/`. UDP-spåret har 176 sekvensluckor,
men både komplett CRC-giltig TX, kvittens och de tre återläsningarna finns.
Inga tappade spårposter rapporterades av ESP32. Testanslutningen är avslutad.

**Första skrivkvittensen från pumpen verifierad efter fysisk omkoppling till
GPIO26.** En enda skrivning av befintliga 30,0 °C skickades via klimatentiteten.
Pumpen svarade med CRC-giltig `w`-kvittens efter 45,296 ms från DE låg:

```text
TX: 65 6f de 02 d3 5e 45 72 69 63 18 57 01 02 03 04 0b 08 00 a6 02 2c 01 ad
RX: 45 72 69 63 ae 23 65 6f de 02 17 77 01 02 03 04 0b 08 00 a6 02 01 d0
```

Register 00:a602, avsändare Eric, värde 0x012c=300; kvittensbyte 01 stämmer
med den rättade högbyteskontrollen. Komponenten loggade `Write succeeded:
Pump acknowledged write`. Fyra senare CRC-giltiga registerläsningar bekräftade
30,0 °C, cirka 5,2/12,2/23,5/30,5 s efter sändningen. Varmvatten kvar 53,1 °C.
Ingen omstart: uptime ökade från 113 till 163 s, CRC-fel fortsatt 0. Detta
verifierade först en kvitterad skrivning av samma värde. Den faktiska ändringen
verifierades därefter enligt ovan; långvarig automatisk styrning återstår.

Underlag: `~/comfortzone-tx26-live-write-2026-10-25/`, inklusive `summary.json`,
råspår och logg. 258 giltiga ramar; sex UDP-sekvensluckor men inga rapporterade
tappade spårposter i ESP32. Både skrivning, kvittens och efterföljande avläsningar
finns i fångsten. Testanslutningen avslutad och råspårning tidsbegränsad till slut.

Användaren har bara den inre raden lödd: 22, 21, 17, 16, 26, 18, 19, 23, 5.
GPIO26 valdes som ledig TX-pin och verifierades på samma frikopplade ESP32.

- **Installerad firmware: TX=GPIO26, RX=GPIO16, DE=/RE=GPIO21.**
  Konfiguration `comfortzone-tx26-test.yaml`, byggtid **2026-10-25 13:32:14 +0100**.
  OTA SHA-256 `b2e0d5fd212265b73b16ef0ff71ead5abab50fe979261effc81bef62784909c8`.
  Enhet fortsatt `08:B6:1F:38:5A:C0` på `192.168.3.179`.
- GPIO26 klarade alla tre LOW/HIGH-test (0/1), även efter hold_dis och med
  tvingad GPIO output-enable. Intern loopback: 23/23 byte vid alla tre försök.
- Vanlig UART-sändning med 23 byte gav 124 ISR-flanker, 1281 låga/1448 höga
  prover och 106 samplade övergångar. DE återställdes låg. Kortet var frikopplat;
  pumpens skrivkvittens verifierades därefter enligt ovan.
- OTA lyckades och rätt byggtid verifierades via API. Underlag och binär finns i
  `~/comfortzone-bare-pad-20261025-133419/`.
  Starten markerades lyckad och uptime nådde 81,6 s utan brownout eller ny
  omstart. Testanslutningen är avslutad, UART återställd och DE låg.

Användaren har nu flyttat ledningen från ESP32 **GPIO17 till GPIO26**,
med andra änden fortsatt på MAX485 **DI**. Tidigare instruktion om GPIO25 är
ersatt. Använd `comfortzone-tx26-test.yaml` för fortsatta byggen; basfilen
`comfortzone-recovery.yaml` har fortfarande GPIO17 för den gamla kopplingen.

## Historik: frikopplat ESP32-kort, GPIO17 jämfört med GPIO25, 2026-10-25

Användaren har lossat ESP32 från RS485-kortet. **GPIO17 kan fortfarande inte
läsas låg, men GPIO25 fungerar med samma firmwarekod.** Detta pekar starkt på
ett fel i eller kring GPIO17 på ESP32-kortet. En extern spänningsmätning behövs
för att särskilja skadad utgång, ingångsavläsning eller fysisk förbindelse på kortet.

- GPIO17: tre försök med gamla 01:01-bygget och tre med 01:05:53-bygget gav
  LOW/HIGH-avläsning 1/1. Även tvingad GPIO output-enable gav 1/1.
  UART intern loopback klarade 23/23 byte vid samtliga sex försök.
- GPIO25: separat YAML ändrar enbart TX-pin och byggmetadata från recovery.
  Samma testkod gav korrekt 0/1 vid samtliga tre försök, även efter hold_dis
  och med tvingad GPIO output-enable. Intern loopback klarade 23/23 varje gång.
- En fast 23-byte läsförfrågan sändes på GPIO25 medan kortet var frikopplat:
  123 ISR-flanker, 1299 låga/1530 höga samples, 114 samplade övergångar.
  Därmed fungerar även vanlig UART-sändning enligt pinavläsningen. Inget
  pumpsvar kan förväntas i detta test; skrivning till pumpen återstår att prova.
- Båda OTA-uppdateringarna gick igenom på det frikopplade kortet. Ingen ny
  brownout observerad. Det första bygget verifierades över 60 s uptime.
  GPIO25-bygget nådde 80 s uptime och markerade starten som lyckad; testet
  avslutades med UART återställd och DE låg.
- **Installerad firmware använder nu TX=GPIO25**, RX=GPIO16, DE=/RE=GPIO21.
  MAC `08:B6:1F:38:5A:C0`, IP `192.168.3.179`.
  Konfiguration: `comfortzone-tx25-test.yaml`.
  Byggtid **2026-10-25 13:24:20 +0100**,
  OTA SHA-256 `5f8cdb88777cfa75309b1a9d9ed47d3dcce3e95f5bb7b6b842b2e7f6bcc71534`.
  `comfortzone-recovery.yaml` använder fortfarande GPIO17; använd rätt YAML
  vid nästa bygge så att pinbytet inte oavsiktligt återställs.
- Underlag: `~/comfortzone-bare-pad-20261025-132236/` (gamla GPIO17-testet),
  `~/comfortzone-bare-pad-20261025-132327/` (utökade GPIO17-testet),
  `~/comfortzone-bare-pad-20261025-132644/` (GPIO25 och UART-sändning).

Nästa fysiska steg är att strömlöst flytta anslutningen från ESP32 GPIO17 till
GPIO25, med andra änden fortsatt på RS485-modulens DI. Därefter kan pumpens
mottagning och skrivkvittens provas igen. Elektrisk nivåanpassning och varför
GPIO17 beter sig fel är ännu inte klarlagda.

## Historik: efter nattfelsökning 2026-10-25

**Skrivning ännu inte fungerande. Ett tydligt felspår är GPIO17/TX och dess
elektriska anslutning; vilken fysisk del som orsakar det är inte fastställt.**

- På ersättningskortet `08:B6:1F:38:5A:C0` (`192.168.3.179`) rapporterar
  GPIO17 konstant hög nivå. Sex UART-läsförsök gav 0 TX-flanker. Oberoende
  direkt sampling gav 0 låga och 2876 höga prover under 15 ms; UART-anropet
  tog bara 89 us att köa, så samplingen täckte själva sändningen.
- Även vanlig GPIO-styrning med DE låg gav läsning **1/1 när 0/1 begärdes**.
  `gpio_hold_dis` ändrade inte detta. Konfigurationen bekräftade lyckade
  API-anrop, utgångslatch 0, GPIO-funktion (mux=2, signal=256), IE=1 och OE=1,
  men input=1. Detta är ESP32:ans digitala padavläsning, inte en extern
  spänningsmätning; extern last, kortfel eller avläsningsfel kan inte särskiljas här.
- UART intern loopback med den fysiska TX-utgången avstängd gav **23/23 exakt
  rätt byte** i första isoleringstestet. En senare upprepning gav 23 byte men
  annan data. Kvarvarande externa RX-byte är en möjlig felkälla; den förberedda
  versionen tömmer därför hårdvaru-/drivrutinsbuffert och ESPHome-cache efter
  att loopback kopplats in. Den korrigerade mätningen är ännu inte körd.
- Ett extra test som tvingar GPIO-styrd output-enable är byggt, men **inte
  verifierat på hårdvaran**. Vid OTA av 01:03:09 rapporterade kortet brownout
  och återgång från app0. Inga fler OTA-försök eller bussändningar gjordes.
  Orsaken till denna brownout är inte fastställd.
- Aktiv firmware efter rollback: **2026-10-25 01:01:00 +0200**,
  SHA-256 `7b3d259a3bfab194bfa3403e10659b838eefebc09e190d42d237d262efb6c8ed`.
  Kvittensfixen och de korta temperatur-/räknaravkodarna ingår i denna version.
  UART återställd, DE låg och normal pumpmottagning återupptagen.
  Slutkontrollen nådde **205 s uptime**, 630 mottagna ramar och 0 CRC-fel,
  utan ytterligare omstart. Börvärden kvar på **30,0 och 53,1 °C**.
  Råspårning och testanslutning avslutade; inga tester lämnas körande.
- Senaste lokala bygge, **inte installerat**: 2026-10-25 01:05:53 +0200,
  SHA-256 `9152f316c6e14e72123dca76cc679b9ed615be15b64e680b17b10683e51bd8c0`.
  Binär: `~/comfortzone-replacement-2026-10-24/firmware-diagnostics-prepared-2026-10-25.ota.bin`.
- Underlag: `~/comfortzone-tx-pad-2026-10-25/`, `~/comfortzone-tx-selftest-2026-10-25/`,
  `~/comfortzone-tx-isolation-2026-10-25/` och `~/comfortzone-tx-final-2026-10-25/`.

Nästa särskiljande fysiska kontroll: strömlöst lossa ESP32-kortet från
RS485-kopplingen/sockeln och kör ESP32 ensamt på USB. Kör om TX-padtestet
(ingen pumpanslutning behövs). Om GPIO17 då kan växla 0/1 ligger felet i
anslutningen/modulen eller dess last. Om det kvarstår behöver kort/pin och
extern mätning undersökas; en annan TX-pin kan därefter provas med omkoppling.
Kontrollera särskilt GPIO17→DI och eventuell oavsiktlig förbindelse till VCC.

## 2026-10-25: kvittensfel hittat, läsförfrågningar och TX-undersökning

- Användaren godkände fortsatt självständig felsökning och tillfälliga
  trafikstörningar under natten. Inga nya börvärden ska lämnas i pumpen.
- Värmesettern för protokoll 170 förväntade alltid kvittensbyte 00.
  Marsfångsten visar 27,0 → 01. Användarens ursprungliga publicerade fångst
  visar dessutom 25,0 → 00, 26,0 → 01 och 24,0 → 00, med läsåterkoppling.
  Kvittensen följer högbyten i 16-bitarsvärdet. Rättat bara för 170;
  CRC, adress, register, storlek och tidsgräns kontrolleras fortfarande.
  Källa: https://github.com/qix67/comfortzone_heatpump/issues/2#issuecomment-1826360048
- ASan/UBSan-hosttester passerar, inklusive verklig 27,0-kvittens och
  avvisning av 00 för 30,0. 13 293 gamla ramar återspelade. Nytt test jämför
  diagnostikens läspaket byte för byte med panelens fångade R-paket.
- Ny `debug_read_probe(mode)` skickar EN fast läsförfrågan för 2 byte vid
  00:a602. Lägen 0/2/4 använder Eric, 1/3/5 använder ADDR; väntetid med DE
  hög före UART är 0/20/100 ms. Väntar först upp till 5 s på fysisk stillhet,
  sänder därefter även om bussen inte är stilla (uttryckligt störningstest).
  Inga W-paket, inga godtyckliga register eller payloads, inga automatiska
  omsändningar. Mottagarläget återställs efter UART-flush; test klart efter 3 s.
- Sex tester kördes i bygge 00:51:48. Samtliga programvarupaket hade korrekt
  CRC men **ingen matchande läsrespons**. Fångsten har 304 giltiga ramar,
  inga UDP-sekvensluckor och inga borttappade spårposter. Vanliga data fortsatte,
  0 rapporterade CRC-fel, rumsmål 30,0, varmvattenmål 53,1, ingen ny omstart.
- GPIO17:s extra flankräknare rapporterade 0 vid alla sex sändningar trots
  cirka 12 ms UART-tid. Detta måste verifieras oberoende innan det tolkas som
  saknad fysisk TX-signal. Ny diagnostik samplar även pinnen direkt under 15 ms
  och läser IOMUX/utgångskonfigurationen.
- Fångst och `summary.json`: `/home/bjwl/comfortzone-read-probes-2026-10-25/`.
  Publika upstream-kommentarer sparade i `/tmp/comfortzone-upstream-rs485-comments.jsonl`.

## 2026-10-25: två sekunder med DE hög

- Användaren godkände uttryckligen ett längre avbrott i pumptrafiken.
  `debug_direction` ändrades till ett fast tvåsekunderstest utan UART-sändning.
  Huvudloopen fortsätter läsa UART och avkoda; ingen blockerande väntan.
  Nya skrivningar/tester avvisas under testet. Lokal tidsgräns och shutdown
  återställer mottagarläget utan beroende av API-klienten.
- Första 100 ms undantas från byte-/nivåräkning för att låta redan
  buffrade byte tömmas. Firmware räknar UART-byte även när råspårning är av.
- Bygge och OTA lyckades. Installerat bygge `2026-10-25 00:43:30 +0200`,
  SHA-256 `7e3196e7082eaaf5394699125b48fcf28f312fdefaa261afbda94d5ba6f9e85e`.
  Samma ersättningskort, MAC `08:B6:1F:38:5A:C0`, IP `192.168.3.179`.
- Ett test kördes: DE återställdes efter **2003 ms**. Efter insvängning
  kom **0 UART-byte**, och RX var låg vid 0 och hög vid **111** avläsningar.
  Detta stödjer att mottagaren stängs av av styrsignalen. Det bevisar
  fortfarande inte att DI/sändardelen driver A/B med rätt data.
- Råfångsten innehåller 24 CRC-giltiga ramar före, 0 under mätfönstret
  och 37 efter testet. Första giltiga ramen efter återgång började läsas
  efter cirka 391 ms. Under mätfönstret var det 0 byte och 0 låga RX-prov.
- Efter testet steg ramräknaren från 74 till 161 med fortsatt 0 CRC-fel.
  `Boot seems successful` bekräftade drift över 60 sekunder efter OTA,
  utan ytterligare omstart. Råspårningen avslutades och API-frånkoppling lyckades.
- Underlag: `/home/bjwl/comfortzone-direction-hold-2026-10-25/`.
  Binär: `comfortzone-replacement-2026-10-24/firmware-direction-hold-2026-10-25.ota.bin`.

## 2026-10-25: kort manuell DE-/RE-puls

- Användaren bekräftade pumpanslutning och inkommande data. Ett första
  försök att skriva tillbaka oförändrat värde 30,0 avbröts före sändning:
  `No safe bus gap within 5 seconds`. Ingen DE-puls i det försöket.
- Tillagt API-anrop `debug_direction`: fast cirka 2 ms hög DE, inga UART-byte,
  direkt återställning till mottagarläge innan loggning/nätverksarbete.
  Avvisar testet om en skrivning pågår eller RX-pinnen saknas. Testet kan
  störa en samtidig ram och ska inte användas som periodisk automation.
- Bygge och OTA lyckades. Installerad version `2026-10-25 00:39:02 +0200`,
  MAC `08:B6:1F:38:5A:C0`, IP `192.168.3.179`.
  SHA-256: `6bb51144ac49433c3ba66de7002313c61579b89b922238bc25900fcd56bb9c4f`.
  Även tidigare testade korta temperatur-/räknaravkodare ingår nu.
- Ett puls-anrop kördes: loggad varaktighet 2089 us, RX före=1,
  under=1/1, efter=0. Eftersom RX redan var hög före testet bevisar det
  inte mottagaravstängning. Att programvaran återställde DE bevisar inte
  heller den elektriska nivån på DE eller korrekt sändning på A/B.
- Fångsten innehåller 22 CRC-giltiga ramar före och 19 efter pulsen.
  Firmware rapporterade 97 ramar och ett CRC-fel efteråt; felet kan bero
  på att pulsen avbröt en ram, men orsaken är inte fastställd.
- Återanslutning efter testet bekräftade samma firmware, uptime över 60 s,
  rumsmål 30,0 och varmvattenmål 53,1. Ingen ytterligare omstart noterad.
  API-frånkopplingen för fångstskriptet fick timeout; råspårningen har
  tidsgräns och en separat API-anslutning fungerade efteråt.
- Underlag: `/home/bjwl/comfortzone-direction-pulse-2026-10-25/`;
  föregående avbrutna skrivtest: `comfortzone-uart-trace-2026-10-25-direction/`.
  Binär sparad i `comfortzone-replacement-2026-10-24/firmware-direction-pulse-2026-10-25.ota.bin`.

## 2026-10-25: USB-matning, förtydligande och spänningsmätning

- Användaren förtydligar att matningen kommer från ESP32-kortets USB och
  att det var pumpkabeln som var bortkopplad. Tidigare slutsats om matning
  från pumpen utan USB var ett missförstånd och ska inte användas.
- 4,65 V uppmätt direkt på kortet; med annan matning blev värdet 4,59 V.
  Multimeterns noggrannhet är okänd. Spänningsfall i USB-kabel, kontakt
  eller eventuell skyddsdiod är möjliga men inte verifierade orsaker.
- Användaren minns högre spänning från pumpen, möjligen omkring 14 V, och
  en tidigare step-down-modul som tagits bort under felsökning. **14 V är
  ännu inte uppmätt eller bekräftat.** Var/hur modulen satt är okänt.
- Bibliotekets originaldokumentation för EX50 anger separat 24 V-matning
  (25 V obelastad) i pumpkontakten samt RS485 A/B och GND. Detta är inte
  en mätning av användarens pump. A/B-signalerna kräver inte 14/24 V.
  Källa: https://github.com/qix67/comfortzone_heatpump/blob/master/README.txt
- MAX485 ska matas med 5 V enligt databladet, inte 14/24 V. Mätvärdena
  ligger under specificerade 4,75–5,25 V men bevisar inte orsaken till
  utebliven skrivkvittens. Ingen OTA, sändning eller omkoppling genomförd.

## 2026-10-25: transceiver identifierad av användaren

- Användaren har nu mätt **4,65 V mellan RS485-modulens VCC och GND**.
  Detta ligger under databladets specificerade 4,75–5,25 V. Mätningen
  bevisar inte att underspänning orsakar uteblivet svar; mätosäkerhet och
  dynamiska spänningsfall är inte fastställda. Inga nivåer på RO uppmätta.
- Användaren minns att matning även kan komma från pumpen. Pumpkontaktens
  matningsstift och anslutning till kortets VCC är ännu inte verifierade.
  Nästa enkla isolering är att koppla ur USB och kontrollera om kortet
  fortfarande är matat via pumpkabeln; mät VCC–GND igen. Ingen uppmaning
  att parallellkoppla två matningar eller flytta anslutningar.
- Användaren läser märkningen `MAX485 CSA +2083D`. Behandla modulen som
  MAX485CSA, alltså 5 V-varianten.
- MAX485 är specificerad för VCC 5 V ±5 %. DI/DE-/RE-ingångarnas logiska
  högtröskel är 2,0 V, så ESP32:s 3,3 V-styrning är i sig kompatibel.
  RO-utgången är däremot inte garanterat begränsad till ESP32:s 3,3 V-nivå.
- Nästa mätning: multimeter i likspänningsläge, svart på modulens GND och
  röd på VCC. Om 3,3 V uppmäts körs MAX485 utanför specifikationen; om
  cirka 5 V uppmäts ska RO→GPIO16-nivåanpassningen kontrolleras.
  Ändra inte matningen till 5 V utan att först kontrollera denna signalväg.
- Inget hårdvarufel, orsak till brownout eller orsak till utebliven kvittens
  är ännu bevisad av kretsidentifieringen. Inga nya skrivtester eller OTA.

## 2026-10-24: granskning av hårdvarubilder

- Fyra originalbilder finns i `/home/bjwl/esp32-rs485/`.
- ESP32-kortet är märkt AZ-Delivery ESP32-WROOM-32 och har D1 Mini-format.
  RS485-modulen har separat RO, /RE, DE och DI, en åttabent transceiver,
  skruvplint och fyra anslutningar på buss-/matningssidan.
- Bilden `PXL_20261024_214333969.jpg` visar en till synes hoplödd förbindelse
  mellan de två mellersta styrstiften (/RE och DE). Grön ledning tycks gå
  till denna förbindelse, gul till DI och en förtennad tråd till RO.
  Detta är visuell spårning, inte uppmätt elektrisk kontinuitet.
- Mot AZ-Deliverys pinout ser placeringen ut att stämma med GPIO17→DI,
  GPIO16←RO och GPIO21→DE+/RE. Ingen säker felkoppling hittad i bilderna.
  Fortsatt kontroll: kontinuitetsmät dessa förbindelser strömlöst och
  med pumpkabeln urkopplad. Lödningar/ledare överlappar visuellt på flera ställen.
- Kretsens märkning går inte att identifiera säkert. Kortlayouten ensam
  skiljer inte MAX485 från pin-kompatibla varianter. Matningen är inte uppmätt.
  Fråga till användaren skickad om kretsbeteckning och tillgång till multimeter
  för VCC–GND. Ingen firmware eller koppling ändrad i denna granskning.
- Om kretsen är MAX485 kräver den 5 V; mottagarutgången RO kan då överstiga
  ESP32:s tillåtna ingångsnivå. Ingen separat nivåanpassning syns på bilderna,
  men detta behöver kontrolleras innan en faktisk nivåkonflikt kan fastslås.
  Dra ingen slutsats om orsaken till gamla kortets brownout från fotona.
- Primärkällor:
  [AZ-Delivery pinout](https://cdn.shopify.com/s/files/1/1509/1638/files/D1_Mini_ESP32_-_pinout.pdf?v=1604068668),
  [MAX485 datablad](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX1487-MAX491.pdf),
  [ESP32 elektriska data](https://documentation.espressif.com/esp32_datasheet_en.html).

## 2026-10-24: passiv avkodning under väntan på hårdvarubilder

- Se [PROTOKOLL-170.md](PROTOKOLL-170.md) för adressöverlappar, historik med
  30 daterade poster, flyttalskandidater och mätunderlag.
- Ny fångst: `/home/bjwl/comfortzone-passive-decode-2026-10-24/`, 763 giltiga
  ramar under fyra minuter. Inga pumpinställningar ändrade, ingen OTA.
- Lokalt tillagt stöd för korta temperatur- och räknarsvar. Hosttester,
  fem Python-tester och ESP32-bygge godkända. Den nya binären är sparad i
  fångstkatalogen men **inte installerad**. Installerad version/hash nedan gäller.
- Sambandet mellan registertrafiken och minneskortet behöver fortfarande en
  jämförelse med känd kortstatus. Skrivproblemet är fortsatt öppet.

## 2026-10-24 23:33: sändning fungerar i programvaran, ingen pumpkvittens

- Aktuell installerad firmware: `2026-10-24 23:31:51 +0200`, ESPHome 2026.10.0,
  IP `192.168.3.179`, MAC `08:B6:1F:38:5A:C0`.
  SHA-256 OTA: `0518851a3351205ac2e79702f4467c58507798a5ca29b802fd9c164faea5b276`.
- Fysisk RX-flankdetektering löste blockeringen före sändning. Fyra kontrollerade
  försök med befintligt värde 30,0 °C har nu nått UART, utan matchande kvittens.
  Ingen faktisk ändring av inställningen är verifierad; återläsning visar 30,0 °C.
- Både avsändaren Eric (`45726963`) och paneladressen ADDR (`41444452`) provades.
  Båda gav korrekt CRC i den programvarufångade sändningen, men ingen svarstrafik
  annat än nollbyte under följande två sekunder. Standardadressen Eric är återställd.
- Senaste riktningstestet: DE på före UART-write, flush klar efter 12,728 ms,
  RX/GPIO16 samplad **hög** vid 12,730 ms medan DE fortfarande var på,
  mottagarläge återaktiverat vid 12,735 ms; RX åter **låg** vid 18,548 ms.
  Detta är förenligt med att mottagarens enable-styrning reagerar. Det bevisar
  inte att DI/DE eller den differentiella sändaren fungerar på A/B.
- Senaste avslutade mätning: uptime 112,94 s utan oavsiktlig reset; normal
  avläsning 30,0 °C värme / 53,1 °C varmvatten. Sista räknarraden 508 ramar,
  0 CRC-fel. Denna korta observation är ingen långtidsverifiering.
- Råspår: `/home/bjwl/comfortzone-uart-trace-2026-10-24-write/`,
  `...-panel-address/`, `...-direction/`. Vanliga ramar och API-händelser:
  `/home/bjwl/comfortzone-write-probe-2026-10-24-idle-edge/`.
- Bygget och ASan/UBSan-regressionstester godkända; 22 903 tidigare fångade ramar
  återspelade. Testfall täcker fysisk stillhet kontra pågående/ofullständig
  trafik samt konfigurerbar avsändaradress. Inga kvittenskoder har gissats om.
- Nästa underlag från användaren: adaptermodell/krets, matning 3,3 eller 5 V,
  och hur GPIO17 (TX), GPIO16 (RX), GPIO21 (DE/RE) är kopplade till adaptern.
  Kontrollera därefter faktisk sändsignal på DI/A/B. Skrivregistret och
  kvittensbetydelsen återstår att verifiera innan fungerande värmestyrning kan hävdas.

## 2026-10-24: rå UART-mätning och låg vilonivå på RX

- Lade till tidsbegränsad API-tjänst `debug_uart(ip, port, timeout, rx_pin)`.
  Den fångar byte direkt i ESPHome-RS485-adaptern före protokollavkodning och
  samplar angiven GPIO som ingång utan att ändra dess konfiguration.
- UDP-format `CZRX`: 4-byte markör, uint32 sekvensnummer, uint32 ackumulerat antal
  tappade poster; därefter poster med uint32 mikrosekunder + int16 värde, little
  endian. 0..255 är RX-byte, -1 läsfel, 0x100..0x1ff TX-byte, 0x200 DE på,
  0x201 RX på, 0x202 flush klar, 0x300/0x301 samplad RX låg/hög.
  Tidpunkten är programvarans lästid och inte den exakta tiden på ledningen.
  Bufferten har 192 poster; inget logg- eller nätverksanrop görs per läst byte.
- Passiv 40-sekundersfångst: 34 599 läsningar, 127 kompletta CRC-giltiga ramar,
  23 871 nollbyte utanför dessa. Ett UDP-sekvenshopp, ingen rapporterad lokal
  buffertförlust. Under flera pauser ungefär 950 nollbyte/s.
- Ytterligare 30 sekunder med GPIO16-sampling: 168 kompletta ramar, 254 nollbyte
  utanför ramar; inga sekvensluckor/buffertförluster. RX låg vid samtliga prover
  under flera hela sekunder mellan frågecyklerna. Antalet skräpbyte varierar
  kraftigt mellan mätningarna; båda visar låg vilonivå och kvarvarande nollbyte.
- Explicit intern pull-up på GPIO16 provades i bygge 23:13:39. RX förblev låg
  under pauserna; 219 nollbyte utanför kompletta ramar under nästa 30 sekunder.
  Pull-up ensam löste alltså inte problemet.
- ESP-IDF 5.5.6:s `uart_ll_discard_error_data` kan slå på hårdvarans
  `UART_ERR_WR_MASK`, så tecken med UART-fel inte skickas vidare som data.
  Testet med bygge 23:17:12 misslyckades: panelens frågor förlorade bland annat
  sista CRC-byten. Parsern tog då nästa svars första byte som frågans CRC och
  tappade synkronisering. Råfångsten innehöll fortfarande CRC-giltiga svar, men
  den löpande avkodaren rapporterade många fel och saknade temperaturer.
  Hårdvarufiltret och dess hjälpkod togs därför bort igen; inte en fungerande fix.
- Nästa implementation är valbar `detect_idle_break: true`. RX-pin hämtas från
  det validerade UART-busobjektet; GPIO-avbrott på båda flanker tidsstämplar
  verkliga nivåväxlingar. Nollsvans efter giltigt svar får rensas enbart efter
  100 ms fysisk stillhet och låg RX. Partiella meddelanden med andra byte
  blockeras fortsatt. Den vanliga bytekontrollen kvarstår för andra adaptrar.
  Hosttester verifierar både öppning vid fysisk stillhet och blockering utan
  sådan observation/vid möjlig påbörjad fråga. ASan/UBSan och 22 903 ramar passerade.
- Bygge 23:24:09 bekräftade fysisk flankdetektering aktiv på GPIO16 och normala
  temperaturer/CRC-räknare igen. Två försök med samma 30,0 °C nådde nu UART men
  fick ingen matchande kvittens. Råspår bekräftar exakt TX-paket med korrekt CRC:
  `65 6f de 02 d3 5e 45 72 69 63 18 57 01 02 03 04 0b 08 00 a6 02 2c 01 ad`.
  DE aktiverades före sändning, flush avslutades 12,7 ms senare och mottagning
  aktiverades därefter. Ingen svarstrafik utom nollbyte under följande två sekunder.
  Detta bekräftar programvarans UART-anrop, inte signalen på RS485 A/B.
- Gamla fångstens skrivningar har avsändare `41 44 44 52` (ADDR), medan biblioteket
  använder `45 72 69 63` (Eric). Lade till konfigurerbar `controller_address`
  med oförändrad standardadress; testar nu paneladressen separat.
- Mätningar: `/home/bjwl/comfortzone-uart-trace-2026-10-24-{passive,pin,pullup,error-filter}/`.
  Kör- och analysskript sparade i motsvarande `...-tools/` (inga hemligheter).
- Originalexemplet anger Teensy 3.2/Serial3. Teensys serial3-kod aktiverar
  pull-up på RX: https://github.com/PaulStoffregen/cores/blob/master/teensy3/serial3.c
- Kvittenshypotes att kontrollera separat: värmesettern förväntar konstant 0,
  varmvatten konstant 1 och enbytesvärden sitt skrivna värde. I gammal PCAP
  gav värmeskrivning `0e 01` (27 °C) svaret `01`. Möjligen återges sista
  värdebyten; detta är ännu inte bevisat och kvittenskontrollen har inte ändrats.

## 2026-10-24: kontrollerade skrivförsök på ersättningskortet

- Användaren bad uttryckligen om skrivtest och varnade för experimentell äldre
  skrivkod. Testvärdet är samma 30,0 °C som både klimatentiteten och en färsk
  CRC-giltig registeravläsning visar, utan avsiktlig ändring av pumpinställningen.
- Första försöket nådde aldrig bussen: `No safe bus gap within 5 seconds`.
  Diagnostikbygget 22:47:09 visade 20 nollbyte kvar i parserns mottagningsbuffert,
  även när UART var tom. Parsern väntade på 21 byte innan den kunde förkasta en
  felaktig header och kunde därför blockera skrivning obegränsat.
- Ny parser tömmer ofullständiga ramar efter 100 ms utan nya byte. En möjlig
  giltig adressprefix upphäver dessutom tillåtelsen att sända efter föregående
  svar; det krävs då ett nytt giltigt svar. Alla mottagna byte räknas som trafik.
- Regressionstest reproducerade det blockerade skrivförsöket före fixen och
  passerade efteråt. ASan/UBSan och återspelning av 23 574 ramar passerade.
- Bygge 22:53:40 kunde fortfarande inte sända. Fångsten visade nu bara frågor,
  inga kompletta svar för slutregistret `05 2c 00`, följt av cirka fem sekunders
  paus. En möjlig bieffekt av timeouten/buffringen måste därför undersökas;
  CRC-fel noll bevisar inte att inga ramar tappats.
- Nästa kontrollerade försök använder `uart.rx_full_threshold: 1` i lokal
  återställningskonfiguration, så hårdvaran kan lämna varje byte vidare direkt.
  Bygge `2026-10-24 22:57:15 +0200` installerades och verifierades på rätt MAC.
  OTA-SHA-256: `399f48962bc9e48cdd8f597d1e00674848940943b25e197be46ff29562fcb5d5`.
- Med direkt byteleverans kommer kompletta svar på `05 2c 00` åter fram. Fjärde
  försöket avbröts ändå utan sändning: `Quiet reply age=99 ms, partial=1, uart=0;
  bytes: 00`. Ett så kort prefix kan inte CRC-kontrolleras; spärren behålls.
  Det är ännu inte fastställt om nollbyten kommer från ledningen/adaptern eller
  mottagningsmjukvaran. Nästa undersökning är tidsstämplad rå UART-mottagning.
- Efter sista försöket fortsatte enheten cirka 60 sekunder utan omstart.
  Drifttiden ökade till 150 s, RS485 rapporterade 802 ramar och 0 CRC-fel.
  Värmebörvärdet var fortsatt 30,0 °C och varmvattenbörvärdet 53,1 °C.
  Ingen skrivning nådde bussen, så pumpens skrivregister och kvittensformat är
  fortfarande overifierade. Det äldre `0x01`-svaret i PCAP antas inte vara framgång.
- Samtliga fyra avslutade skrivförsök rapporterade uttryckligen att inget
  sänts. ESP32 fortsatte publicera värden och drifttid utan observerad omstart.
- Fångster och händelser finns under `/home/bjwl/comfortzone-write-probe-2026-10-24-*`.
  PCAP-filerna innehåller mottagna UDP-debugpayloads med syntetiska Ethernet/IP-
  headers och mottagningstid på VM:n; de mäter inte exakta tidpunkter på RS485.

## 2026-10-24: kontroll efter rapporterat glapp i nätverksswitchens kabel

- Användaren rapporterade tappad kontakt och kabelglapp vid switchen.
- Ny API-kontroll på ersättningskortet visade samma rättade firmware och drifttid
  cirka 452 → 512 sekunder, jämfört med cirka 302 sekunder vid förra kontrollen.
  Resetorsaken var fortsatt `power-on event`; ingen omstart observerades.
- Under 65 sekunders kontroll fortsatte HW-inställningen publiceras som 53,1 °C
  och uppmätt varmvatten som 51,9 °C. RS485-räknare 2306 → 2486, CRC-fel noll.
- Wi-Fi-signalen var cirka −79 dBm efter flytten till pumpen. Nätverksglappet
  kan inte lokaliseras säkert av dessa data, men ESP32 fortsatte sin drift.
  Detta är en kort observation och ingen långtidsverifiering.
- Loggar: `/tmp/comfortzone-stability-after-network.log` och motsvarande `.json`.

## 2026-10-24: ersättningskort migrerat i HA och pumpdata verifierade

- Användaren bekräftade att nya MAC `08:B6:1F:38:5A:C0` är kopplad till
  ComfortZone i HA efter att den gamla BT Proxy-registreringen hanterats.
- USB-logg från manuell reset 22:11:57 visar nya bygget, Wi-Fi-start utan
  brownout, resetorsak `power-on event` och godkänd uppstart 22:12:57.
- Efter återanslutning till pumpen verifierades enheten på `192.168.3.179` via
  krypterat API med rätt MAC och byggversion `2026-10-24 00:42:24 +0200`.
- Under 70 sekunders observation publicerades HW-inställningen upprepade gånger
  som 53,1 °C, samma värde som användaren tidigare bekräftat på pumpen.
  Uppmätt varmvatten: 51,9–52,0 °C. Senaste övriga avläsningar: ute 10,7 °C,
  inne 23,8 °C, framledning 36,2 °C, retur 26,5 °C, värmebörvärde 30,0 °C.
- RS485-räknaren ökade från 1161 till 1319 ramar mellan två 30-sekundersrapporter;
  CRC-fel var noll i båda. Okända register ökade 757 → 851 och återstår att kartlägga.
- Drifttiden ökade från cirka 242 till 302 sekunder utan omstart. Resetorsaken
  var `power-on event`. Inga pumpinställningar ändrades under kontrollen.
- Temperaturavkodningsfixen är nu verifierad på ansluten hårdvara. Skrivning till
  pumpen är ännu inte verifierad. Loggar: `/tmp/comfortzone-connected-replacement.log`
  och `/tmp/comfortzone-connected-replacement-states.json`.

## 2026-10-24 cirka 22:09–22:11: korrigerad firmware fungerar på annat kort

- Användaren erbjöd ett annat ESP32 rev3.0/4 MB-kort för OTA-test. Före upload
  verifierades API-identiteten: `esphome-web-385ac0`, MAC `08:B6:1F:38:5A:C0`,
  IP `192.168.3.179`, ESPHome 2026.9.1 / esphome.web. Användarens USB-logg visade
  bootloader ESP-IDF 5.5.5 och lyckad Wi-Fi-start utan brownout.
- Exakt samma korrigerade binär som misslyckades på det gamla kortet laddades upp:
  SHA-256 `2564b5137bc34b7880ecfa77d32b1b0da4a848a6eb5f73ea73107b5221504564`.
  OTA lyckades på cirka 8,4 sekunder.
- Efter upload: ESPHome 2026.10.0, byggd `2026-10-24 00:42:24 +0200`,
  ny HW-avkodningsmarkör och resetorsak `software via esp_restart`.
  MAC verifierades vid varje kontroll. Drifttid ökade från cirka 12 till 92 sekunder
  med samma nya byggversion; ingen brownout eller rollback observerades.
- Enheten heter nu `comfortzone`, men behöll IP `192.168.3.179` under kontrollen.
  Den använder återställningskonfigurationens pinnar 17/16/21 och protokoll 170.
- Inga RS485-ramar mottogs och HW-inställningen saknade värde. Pumpkommunikation
  och skrivning är alltså ännu inte verifierade med ersättningskortet.
- Detta visar att samma firmware kan starta på ett annat kort. Hårdvara,
  bootloader och sparat flashinnehåll skiljer sig; en exakt fysisk felorsak på
  gamla kortet är inte därmed fastställd.
- Loggar/resultat: `/home/bjwl/comfortzone-replacement-2026-10-24/`.

## 2026-10-24 21:45: USB-logg visar faktisk brownout under Wi-Fi-start

- Användaren fångade seriell logg på Windows-laptop via ESPHome Web och reset.
  Vid 21:45:31 laddar bootloadern app1 (`0x1d0000`). Vid 21:45:32 följer:

  ```text
  [C][wifi:690]: Starting
  E BOD: Brownout detector was triggered
  rst:0x3 (SW_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
  ```

- Detta är direkt evidens för att brownoutdetektorn utlöst en reset, inte bara
  den historiska rollback-varningen. ESP-IDF 5.5.6:s brownout-ISR sparar reset-hint
  och anropar mjukvarureset; `SW_RESET` motsäger därför inte brownout.
- Även nästa start laddar app1 och identifierar gamla bygget
  `2026-10-23 21:52:07 +0200`. Wi-Fi ansluter 21:45:36 och HA 21:45:56.
  Ramar från RS485 är noll vid 21:46:02. Ingen panic/backtrace syns i utdraget.
- Felet kan alltså inträffa även vid vanlig omstart av gamla firmwaren, utan OTA.
  USB-utdraget visar inte en ny rollback mellan de två starterna.
- Bootloadern är ESP-IDF 5.5.2 från 4 mars, appen ESP-IDF 5.5.6. Detta är en
  observation; versionsskillnaden är inte belagd som felorsak.
- Nästa fysiska isolering: säkerställ endast USB-matat ESP32 utan RS485-adapter
  eller annan kringutrustning, testa annan USB-datakabel/port och fånga reset igen.
  Det är ännu inte fastställt om spänningsfallet beror på kabel, kontakt, matning,
  extern last eller kortets regulator/kondensatorer.
- Referens: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/fatal-errors.html#brownout

## 2026-10-24 cirka 21:38: HA-byggets FastCRC-fel och verifierat lokalt paket

- Användarens HA-logg visar ESPHome 2026.10.0, paket från
  `fix/api-service-crash-guard` men komponent från `main`. Bygget stoppar i
  det separat hämtade `comfortzone_heatpump` med saknad `FastCRC.h`.
- Den lokalt bundlade biblioteksversionen deklarerar redan FastCRC som beroende
  i `library.json`. Lokala kompatibilitets- och avkodningsfixar är inte publicerade
  på GitHub och kommer därför inte med i användarens befintliga konfiguration.
- Skapade `/home/bjwl/comfortzone-ha-local-2026-10-24.zip` (34 filer, 109984 byte),
  med lokala källor, YAML-exempel, licenser och installationsinstruktioner.
  SHA-256: `8a65bd3732416ccb6adff063321a98df04a43298bc0467a7f85520043d0256bf`.
- Provbyggde paketets YAML och källor i separat katalog med tillfälliga testhemligheter:
  ESPHome 2026.10.0 / ESP-IDF 5.5.6, `Successfully compiled program`.
  Kompilatorns include-flaggor innehåller FastCRC för värmepumpsbiblioteket.
  Arkivets filer jämfördes byte för byte mot provbyggets ingångsfiler.
- Inga hemligheter eller firmwarebinärer finns i arkivet. Provbyggets binär ska
  inte installeras eftersom den använder testuppgifter. HA ska bygga med sina
  befintliga hemligheter. Bygglogg: `/tmp/comfortzone-ha-bundle-build.log`.
- Ingen OTA gjordes under denna kontroll. Kortets uppstartsproblem är fortfarande olöst.

## 2026-10-24 cirka 18:08: ytterligare OTA-försök på begäran

- Samma korrigerade binär (SHA-256 `2564b5137bc34b7880ecfa77d32b1b0da4a848a6eb5f73ea73107b5221504564`)
  laddades upp; överföringen lyckades på cirka 7,4 sekunder.
- Efter omstarten rapporterades åter gamla byggversionen
  `2026-10-23 21:52:07 +0200` och `Last restart reason = brownout`.
- Kontroller vid cirka 4, 24, 44, 64 och 84 sekunders drifttid gav samma resultat.
  Enheten lämnades online; ingen USB-enhet var ansluten vid försöket enligt användaren.
- RS485-räknaren visade noll ramar och HW-givaren saknade värde.
- Temperaturfixen är fortfarande inte aktiv. Detta fastställer inte om kortet
  är defekt; seriell startlogg saknas fortfarande.
- Loggar och status: `/tmp/comfortzone-final-retry-upload.log`,
  `/tmp/comfortzone-final-retry-device.log`, `/tmp/comfortzone-final-retry-results.json`.

## 2026-10-24: manuell omstart och paus inför USB-felsökning

- Efter användarens manuella omstart återkom `192.168.3.2` med rätt MAC-adress
  `08:b6:1f:38:0b:f8`. Ping svarade och OTA-port 3232 var öppen.
- API-port 6053 avvisade anslutningar; därför kunde byggversion och resetorsak
  inte läsas. Detta är förenligt med safe mode, men inte bekräftat utan startlogg.
- Ingen ny uppladdning gjordes efter den manuella omstarten.
- Användaren vill fortsätta med kabel efter middagen. Nätverksbevakningen stoppades.
- Vid fortsättning: fånga seriell bootlogg före eventuell omflashning, så att
  bootval, tidig krasch/reset och eventuell safe mode kan identifieras.

## 2026-10-24: nytt försök efter byte av matning

- Användaren meddelade byte av matning. Före uppladdningen svarade enheten med
  gamla byggversionen, cirka 21 sekunders uptime och resetorsaken `brownout`.
  Den resetorsaken kan inte knytas till den efterföljande OTA-omstarten.
- Samma korrigerade binär överfördes igen; OTA rapporterade lyckat resultat.
- Efter uppladdningen uteblev svar på API och ping under flera minuter.
  ARP-grannen för `192.168.3.2` rapporterades `FAILED`; mDNS gav ingen adress.
  Aktiv byggversion och senaste resetorsak efter detta försök är därför okända.
- Användaren tillfrågades om aktuell matning och lysdiodstatus. Försöket visar
  ännu inte om bytet hjälpte. Uppladdningslogg: `/tmp/comfortzone-new-power-upload.log`.

## 2026-10-24: OTA med anslutningen till värmepumpen bortkopplad

- Användaren kopplade loss enheten från värmepumpen; samma korrigerade binär
  laddades upp igen. SHA-256 kontrollerades och OTA rapporterade lyckad överföring.
- Även detta försök gav gammal byggversion `2026-10-23 21:52:07 +0200` och
  `Last restart reason = brownout` efter omstart. Enheten var fortsatt online
  efter kontrolltiden på 60 sekunder. HW-givaren saknade värde efter denna boot.
- Felet reproduceras alltså även med pumpanslutningen bortkopplad enligt användaren.
  Det fastställer inte om grundorsaken är matning, kort eller uppstartsprogramvara.
- Loggar: `/tmp/comfortzone-disconnected-upload.log`,
  `/tmp/comfortzone-disconnected-device.log`, `/tmp/comfortzone-disconnected-results.json`.

## 2026-10-24 00:58–01:15: tio ytterligare OTA-försök

- På användarens begäran gjordes exakt tio försök med samma korrigerade binär
  (byggd 00:42:24; SHA-256 kontrollerad före serien).
- Alla tio OTA-överföringar lyckades. Ingen fick den nya versionen att bli aktiv
  vid efterföljande API-kontroller.
- Efter samtliga omstarter rapporterades byggversion `2026-10-23 21:52:07 +0200`
  och `Last restart reason = brownout`. Varje uppstart följdes till minst
  80 sekunders drifttid innan nästa uppladdning.
- Efter sista försöket var enheten online vid 82,7 sekunders drifttid och
  publicerade fortfarande pumpdata med den gamla, felaktiga HW-avkodaren.
- Inga pumpinställningar ändrades. Ingen ändring gjordes av brownoutdetektor,
  rollback-skydd eller firmware mellan försöken. Fysisk felorsak är fortsatt okänd.
- Överföringsloggar, enhetsloggar och `results.json` finns i
  `/home/bjwl/comfortzone-ota-2026-10-24-ten-attempts/`.

## 2026-10-24: förtydligande om omstartsorsaken

- Källkodskontroll: ESPHomes rollback-varning skrivs när en ogiltig OTA-partition
  finns kvar. Varningen ensam bevisar därför inte en ny rollback vid varje boot.
- Efter senaste OTA-försöket visade en ny API-anslutning fortfarande gammal
  byggversion, cirka 15 sekunders uptime och `Last restart reason = brownout`.
  Det är separat evidens från den kvarliggande rollback-varningen.
- ESP-IDF läser resetorsaken vid uppstart och rensar därefter eventuell RTC-hint.
  Debugsensorn återger denna uppstartsorsak, inte en historisk NVS-text för brownout.
- Nätverksloggen saknar de tidigaste startögonblicken innan Wi-Fi/API fungerar.
  Att ingen brownout-rad syns då utesluter därför inte att detektorn utlösts.
- Orsaken är inte lokaliserad till nätaggregat eller kabel; tidigare formuleringar
  om ett konstaterat matningsfel var för säkra. Fortsatt felsökning måste skilja
  rapporterad resetorsak från den fysiska orsaken och kontrollera OTA-starten.

## 2026-10-24 cirka 00:49: tredje försök på användarens begäran

- Samma korrigerade binär laddades upp igen med lyckad OTA-överföring.
- Efter omstarten rapporterade enheten åter byggversion
  `2026-10-23 21:52:07 +0200`, `Last restart reason = brownout` och gamla
  felvärden som 2739.1 °C. Korrigeringen är alltså fortfarande inte aktiv.
- Matningen är enligt användaren separat från pumpen. Orsaken till den
  rapporterade underspänningen är inte fastställd genom mätning.

## 2026-10-24 cirka 00:47: HW-avkodning rättad, OTA gör rollback

- Användaren hittade glapp i RS485-kabeln. Pumpdata kommer nu in; ESP32 har
  separat strömförsörjning. Matningens faktiska stabilitet är inte uppmätt.
- Pumpens panel visar **HW setting = 53.1 °C**. Detta bekräftar `13 02` vid
  ramoffset 104-105 i det 193 byte långa svaret för `00 20 03`.
- Lokal kod har en separat protokoll-170-avkodare för detta fält. Den gamla
  protokoll-180-avkodaren läste offset 123-124 (`FF 6A`) som 2739.1 °C.
- Dessutom var strukturen för `00 D2 03` för stor för den 121 byte långa ramen.
  Den läste kvarvarande byte från tidigare ramar. Layouten är återställd till
  121 byte, längden kontrolleras och ramen skriver inte längre över HW-börvärdet.
- Minnes- och regressionstester passerar med 22 903 inspelade ramar, inklusive
  64 nya ramar. Ny infångning: `~/comfortzone-debug-2026-10-24-target.pcap`.
  UDP-payload och mottagningstid är infångade; Ethernet/IP-huvuden är syntetiska.
- Korrigerad firmware byggd **2026-10-24 00:42:24 +0200**. SHA-256 för OTA-binär:
  `2564b5137bc34b7880ecfa77d32b1b0da4a848a6eb5f73ea73107b5221504564`.
- Två OTA-överföringar rapporterade lyckat resultat, men korrigeringen blev
  inte kvar. Efter omstarterna rapporteras fortfarande byggversionen
  **2026-10-23 21:52:07 +0200** och gamla, felaktiga HW-värden.
- Loggen visar `OTA rollback detected! Rolled back from partition 'app0'`,
  `The device reset before the boot was marked successful` och `brownout`.
  Efter det andra försöket godkändes den återställda gamla uppstarten vid 60 s.
- Nästa steg: kontrollera kortets matning/strömkabel och omstartsförlopp innan
  ytterligare OTA-försök. Brownoutdetektor och rollback-skydd är inte avstängda.
- Inga pumpinställningar ändrades under felsökningen.

## Uppföljning 2026-10-24: återställningsversion installerad

- OTA-installation av `comfortzone-recovery.yaml` till `192.168.3.2` lyckades.
- Enheten rapporterar ESPHome 2026.10.0, byggd 2026-10-23 21:52:07 +0200,
  protokoll 170 och `asynchronous writes`.
- Uppstarten godkändes efter 60 sekunder: `Boot seems successful; resetting boot loop counter`.
- Vid både 30 och 60 sekunders drifttid: `RS485: frames=0 CRC errors=0 unknown registers=0`.
  Detta visar att inga kompletta ramar nått avkodaren; räknaren mäter inte råa UART-byte.
- `Last restart reason` och `Uptime` finns i återställningsversionen. Omstartsorsaken
  efter OTA var `software via esp_restart`, vilket är väntat efter installationen.
- Inga pumpinställningar ändrades under installationskontrollen.
- Tidigare firmware (2026.2.2, byggd 24 mars) innehöll även tre Inkbird-givare.
  De ingår inte i den installerade återställningsversionen.
- Nästa felsökningssteg är mottagningen: kontrollera anslutningen mellan pump,
  RS485-adapter och ESP32 och vid behov mäta/logga råa UART-byte.

## Tidigare anteckningar 2026-03-24

## Status
✅ ESPHome kompilerar och laddar upp korrekt
✅ WiFi anslutning fungerar
✅ Logger visar "Comfortzone initialized"
❌ INGEN RS485-kommunikation alls

## Testat
1. Loop()-spam borttaget (kommer från heatpump_->process())
2. VERY_VERBOSE loggning - inga UART/rx/tx/read/write meddelanden
3. Koden verkar helt korrekt - ESPHome RS485 interface fungerar

## Teori: Hårdvaruproblem
- RS485 A/B kan vara vänd
- RE/DE pinnen (GPIO 21) kan ha lossnat
- RS485-transceivern kan sakna ström (V5/GND)
- Värme pumpen kanske inte skickar data om ingen kontrollpanel är kopplad

## Att testa imorgon
1. Byt A/B på RS485-trancievern
2. Kontrollera att RE/DE (GPIO 21) faktiskt togglar med multimeter
3. Koppla in en USB-RS485-dongle för att sniffa trafik
4. Kolla om värme pumpen kräver att en kontrollpanel är ansluten

## Filändringar
- ~/esphome-comfortzone/components/comfortzone/comfortzone_esphome.cpp rad 54 borttagen (loop() called)
- comfortzone-bjwl-debug.yaml skapad för felsökning

## 2026-10-25: utökad avkodning och nya reglage

Källgenomgång och manualprioritering finns i `CODE-REVIEW.md`. Bibliotekets
snapshot finns i `comfortzone_heatpump.lock.json`; biblioteket och ESPHome har
arbetsgrenen `feature/ex50-register-controls`.

Slutligt livebygge: ESPHome 2026.10.0 / ESP-IDF 5.5.6,
kompilering `2026-10-25 14:27:21 +0100`, TX26/RX16/DE21.
OTA lyckades, med cirka tio sekunders överföring. Samma ersättningskort som
tidigare, MAC `08:B6:1F:38:5A:C0`. Inga oplanerade omstarter eller CRC-fel
sågs under de följande försöken; detta är ett kort funktionstest, inte ett
långtidstest av prisstyrning.

### Observerade värden

Kurva 5, fläktläge Low, normalfläktinställning 87 %, VV maxkörning/paus 30/20 min,
VV kompressorfrekvensgränser 30/55 Hz, extra VV 70 °C/180 min, TE10 26,1 °C,
larmmasker 0/0 och löpande pumpklocka publiceras nu i HA.
De ärvda servicemenynamnen har ännu inte alla jämförts med panelen.

**Värmebörvärdet var redan 29,1 °C före nya skrivningar.** Flera korta `00:029d`
och långa `00:0214` svar visar samma bytes `23 01` på `00:02a6`. Ingen ny
värmeskrivning gjordes och ingen automatisk återställning till tidigare 32 °C.
Det kan vara ett beräknat börvärde eller en ändring utanför denna undersökning;
användarens panel/reglerläge behöver jämföras. Äldre lyckade ACK/återläsningar
visar att registret är skrivbart, inte att ändringen alltid är beständig.

### Skrivprov med oförändrade värden

- Två tidiga VV-försök avbröt efter fem sekunder utan säker busslucka; inget
  skickades. Ingen omstart. Detta dokumenteras också som ett faktiskt testutfall.
- VV 53,1 → 53,1 °C lyckades i slutbygget. CRC-giltigt W:
  `656fde02d35e457269631857010203040b08007303130251`.
  CRC-giltigt ACK efter 45,203 ms från sändningens slut:
  `45726963ae23656fde021777010203040b0800730302da`.
  Fem senare självständiga lässvar gav 53,1 °C, cirka 4,8–32,9 s efter skrivningen.
- Fläktläge Low → Low och värmekurva 5 → 5 kvitterades av pumpen.
  Regleringen sköts via de nya select/number-entiteterna, inte råa API-kommandon.
- Extra-varmvattenknapparna har testats mot värddatorns simulerade buss och
  tidigare fångade kommandomappningar. Boost aktiverades inte i liveproven.

Rådebug skickade tidigare mycket små UDP-datagram och förlorade 794 sekvenssteg
i ett av försöken. Paket byggs nu ihop under högst 20 ms eller tills bufferten
närmar sig full. Den lyckade VV-fångsten har 221 CRC-giltiga ramar, noll
sekvensluckor och noll rapporterade överfulla trace-buffertar. Det bevisar inte
att UDP alltid är förlustfritt. Skrivtimeouten visar nu även bussens senaste
ramålder, RX-ålder och buffertläge för fortsatt diagnostik.

Artefakter utanför git (inga hemligheter incheckade):

- `/home/bjwl/comfortzone-review-live-2026-10-25/`: första passiva kontrollen.
- `/home/bjwl/comfortzone-review-writes-2026-10-25/`: första buss-timeouten.
- `/home/bjwl/comfortzone-review-hw-raw-2026-10-25/`: råfångst med UDP-förluster.
- `/home/bjwl/comfortzone-review-final-hw-2026-10-25/`: lyckat VV-prov, rådata,
  firmware med SHA256, ACK-analys och fem återläsningar.
- `/home/bjwl/comfortzone-review-fan-curve-2026-10-25/`: fläkt-/kurvprov med PCAP.

### Tester och byggkontroller

ASan/UBSan passerar för skrivmotorn, fältgränser, felaktiga/avklippta ramar,
kalenderkontroll och 32-bitarsräknare. 24 093 fångade UDP-payloads från tre äldre
PCAP-filer och den passiva oktoberfångsten har spelats igenom C++-koden.
Ett riktigt VV-ACK från ovan ingår nu i regressionstestet.
Protokoll 160/180/221 kompilerar och passerar vardera 200 registeradresser × 234
ramlängder; inga andra fysiska pumpversioner har testats. Sju Python-tester
passerar. Både fullt TX26-bygge och climate utan sensor/text/binary-plattformar
har kompilerats. CI kör värddatortesterna för båda repona.
