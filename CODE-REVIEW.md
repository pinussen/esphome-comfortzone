# EX50: kodgenomgång och fjärrstyrning, 2026-10-25

Denna genomgång beskriver första etappen. Senare verifieringar, eldstadsknappar,
tidssynk, driftprofiler och energiändringar finns daterade i
[PROTOKOLL-170.md](PROTOKOLL-170.md) och [PROTOKOLL-PLAN.md](PROTOKOLL-PLAN.md).

## Två repon

- `pinussen/comfortzone_heatpump`: protokoll, register, avkodning och skrivmotor.
- `pinussen/esphome-comfortzone`: ESP32-UART, ESPHome/HA-entiteter, konfiguration och fångstverktyg.

ESPHome bygger den incheckade bibliotekskopian under `components/comfortzone/third_party/`.
Att ändra syskonkatalogen påverkar alltså inte automatiskt firmware. Snapshoten
låses till bibliotekets commit och SHA256 per fil. `scripts/sync_library.py`
importerar **committade** källor och verifierar att kopian inte har ändrats.
FastCRC är också låst till den revision som användes i testerna.

## Menyer och prioritering

Underlag: ComfortZones [EX35/EX50/EX65-manual, Ver B 2014](https://www.vvsbutiken.nu/dokument/cz06025_manual__ex35_ex50_ex65_b.pdf),
särskilt sidorna 6–9 och 34, samt [manualen för SW 2.0 och senare, 2020](https://comfortzoneab.s3.amazonaws.com/media/CZ06025_Manual__EX35_EX50_EX65__I2__2020-02-01.pdf).
Menynamn i en senare manual bevisar inte registeradresser för protokoll 170.

| Menyfunktion | Val för fjärrstyrning | Implementation / kvar att verifiera |
| --- | --- | --- |
| Värmebörvärde | Hög prioritet för prisstyrning | Befintlig climate. Register `00:02a6` kan skrivas. Användaren bekräftade att ändringen till 29,1 °C gjordes avsiktligt från HA. |
| Varmvattentemperatur | Hög prioritet | Climate, `00:0373`, samma avkodade mål som panelens tidigare bekräftade 53,1 °C. |
| Extra varmvatten | Tillfällig behovsstyrning | Start/stopp-knappar, befintliga bitkommandon `81/41:0017`. Pumpens timer sköter återgången. |
| Fläktläge | Praktiskt vid frånvaro/forcering | Select Low/Normal/High; `00:03fa`. Lägenas exakta luftflöden beror på injusteringen. |
| Värmekurva | Konfiguration | Number 1–10, `00:02a5`; paneländringar 3–6 finns dokumenterade i råtrafiken. Inte förstahandsval för täta prisändringar. |
| Varmvattenprioritet | Nästa steg | Låg/normal/hög finns i manualen; 170-adress ännu inte belagd. |
| Semestersänkning | Nästa steg | Kräver fångst när panelens värde ändras. |
| Min returtemperatur | Senare, installationsberoende | Menyval finns; register från andra versioner får inte återanvändas utan verifiering. |
| Diodlist | Låg prioritet | Ingen ny fjärrkontroll i denna ändring. |

Kompressorns gränser, givarkalibrering, ventiler och elpatronens effektgränser
läggs inte till som automatiseringsreglage. De läsbara varmvattenparametrarna
visas för diagnostik. Ingen elprisautomation installeras av denna ändring.

## Granskade problem och ändringar

| Område | Fynd | Åtgärd |
| --- | --- | --- |
| API-skrivningar | Synkron väntan blockerade ESPHomes loop | En transaktion i taget, upp till 15 s asynkron bussväntan och 200 ms ACK-väntan, ingen automatisk omsändning efter oklart resultat. |
| RX/parser | Nollbrus och halvfärdiga ramar kunde blockera skrivning | Bunden timeout; fysisk RX-detektering som tillval; möjliga frågor får inte räknas som ledig buss. |
| Protokoll 170 | Återanvända strukturer från andra versioner och paketstorleksberoende gav fel fält | Adressbaserad avkodning. Hela fältet måste finnas i ett CRC-giltigt svar från rätt pump. |
| Äldre statusavkodare | Strukturfält lästes utan att kontrollera ramlängden | Längdskydd vid 53 strukturtolkningar. Andra protokoll har endast värddatortester, inga pumpförsök här. |
| Statuscache | Oinitialiserade värden och publicering redan vid köläggning | Nollinitialisering plus `has_value`; skrivningar bekräftas först med matchande ACK. |
| Temperaturer | Frånkopplade givare kunde bli −99 °C | −990/−999 markeras som saknat värde i HA. TE10 behåller givarnumret eftersom fysisk roll är obekräftad. |
| Räknare | Vänsterskift kunde ske som signed int | Explicit uint32 före skift. Test med `0xffffffff`. |
| Climate | Sensor-entiteter krävdes indirekt; OFF annonserades utan motsvarande kommando | Climate får data direkt från biblioteket och annonserar endast HEAT. HEAT är här tillgängligt reglage, inte bevis på pågående kompressordrift. |
| Härledda effekter/CoP | Division med noll och beroende av andra HA-entiteter | Beräkning från giltig biblioteksstatus, oberoende av vilka entiteter som valts. Okänt/blandat driftläge ger NaN, inte påhittad energifördelning. |
| Debugtid | Väggklockans synkning kunde påverka tidsgränsen | Monoton tidsräkning med hantering av millis-varvning. |
| Extra varmvatten | Ett ACK kan inte visa när boost senare slås av | Knappar och skrivresultat; ingen varaktig 170-status publiceras enbart från ACK. |
| Bygge | FastCRC saknades i bibliotekets egna beroenden i native IDF | Explicit låst beroende även i `library.json`; dokumenterade lokala/pinnade paket. |

## Utökad avkodning

`comfortzone-protocol170.yaml` lägger till elva sensorer, pumpklocka,
skrivresultat, fläktval, värmekurva och två varmvattenknappar.

| Bank:adress | Fält | Evidens |
| --- | --- | --- |
| 00:02a5 | Värmekurva | Äldre dokumenterade panel-W/ACK/återläsningar |
| 00:03fa | Fläktläge | Inspelade W/ACK och överlappande inställningssvar |
| 00:03d2, 03d3 | Max varmvattenkörning / paus, minuter | Namngivna i tidigare 170-struktur; 30/20 i fångst och aktuell trafik |
| 00:03e4, 03e6 | VV min/max kompressorfrekvens | Tidigare 170-struktur; LE16/10, 30/55 Hz |
| 00:03ec, 03ee | Extra VV mål/duration | Tidigare 170-struktur; 70 °C / 180 min |
| 00:03fb | Normalfläktens inställning | Tidigare 170-struktur; 87 procent. Inte samma sak som aktuellt fläktläge. |
| 01:0046 | TE10 | Givarfält, fysisk roll obekräftad |
| 01:001f, 0027 | Råa larmmasker | Tidigare struktur; okända bitar namnges inte |
| 01:0004 | Pumpklocka | Kalenderkontroll, både sex och sju databyte; ingen tidszonskorrigering |

De ärvda parameternamnen är inte alla kontrollerade mot pumpens servicemeny.
Historikens 30 poster och två flyttalsserier är fortsatt offlineanalys, med
okända koders betydelse tydligt markerad. Se [PROTOKOLL-170.md](PROTOKOLL-170.md).

## Uppföljning och kvarstående frågor

- Uppföljning: användaren bekräftade att 29,1 °C var en avsiktlig sänkning från
  HA. Den tidigare osäkerheten om att pumpen själv skulle ha ändrat värdet är
  därmed undanröjd. Återläsningarna stämmer med HA-ändringen.
- Protokoll 170 saknar verifierad tolkning av flera driftbitar. Driftläge,
  avfrostning, varmvattenprioritet och uppdelad värme/VV-CoP ska inte betraktas
  som fungerande bara för att entiteterna finns i gamla paketet.
- Det tidigare brandlägeskommandot har friare ACK-matchning än temperaturer.
  Det lämnas som befintlig diagnostisk API-funktion, utan nytt HA-reglage.
- UDP-fångst är diagnostik och kan förlora paket. Avsaknad av ett fångat ACK
  räcker inte ensam för att hävda att pumpen ignorerade kommandot.

## Tester

- C++ med AddressSanitizer och UndefinedBehaviorSanitizer: skrivtransaktioner,
  felaktiga ACK, timeout, samtidig skrivning, millis-varvning, brus, avklippta
  värden, överlappande fält, kalenderfel, 32-bitars räknare och PCAP-replay.
- Protokoll 160/180/221: 200 registeradresser × 234 ramlängder per bygge under
  samma minneskontroller. Detta bevisar inte fältens semantik på dessa pumpar.
- Sju Python-tester mot fångade temperatur-, inställnings-, räknar- och historikramar.
- ESPHome 2026.10.0 / ESP-IDF 5.5.6: komplett TX26-konfiguration samt separat
  climate-konfiguration utan sensor-, text_sensor- eller binary_sensor-plattformar.

Live: samma-värde-skrivningar av VV 53,1 °C, fläkt Low och kurva 5 kvitterades.
VV hade fem separata återläsningar efter ACK. Två tidigare försök avbröt utan
sändning eftersom busslucka saknades. Extra-VV provades inte på den fysiska pumpen.
Detaljer och fångster redovisas i [DIAGNOSTIK.md](DIAGNOSTIK.md).
