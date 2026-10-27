# Plan: generell ComfortZone-protokollmotor och registerkarta

Planerad 2026-10-25. Detta dokument beskriver kommande arbete; det är inte
en deklaration om att hela protokollet redan är avkodat.

Påbörjat 2026-10-25 kväll: jämfört sju fångster, tagit en ny passiv treminutersfångst
och sparat 14 råfixtures. Första resultatet är en möjlig uppdelning mellan
värmefrekvens, varmvattenfrekvens och faktisk frekvens, samt ett konkret
motexempel mot att bara ta maxvärdet. Se [PROTOKOLL-170.md](PROTOKOLL-170.md).
Den efterföljande paneljämförelsen beskrivs nedan. En första registertabell för
170 har nu införts; en fullständig protokollmotor och övriga profiler återstår.

Senare samma kväll: panelbekräftad husvärme och ett kontrollerat test av Extra
varmvatten gav både uppvarvning och noll frekvens/effekt efter nedvarvning.
Frekvensavkodningen är nu rättad från 01:02d5 till 01:02e9 med fångade
regressionstestfall. Extrafunktionen stängdes av på panelen. Statusbitar för
begäran och faktisk drift måste fortfarande särskiljas innan CoP-fördelningen
kan aktiveras; det gäller särskilt 0x2E och stoppfallet 0x1E.

Nästa genomförda steg samma kväll: 34 befintliga skalära fält har flyttats till
bibliotekets `registers_v170.json`. Samma källa genererar en statisk C++-tabell
och referensdokumentation, och används direkt av offlineanalysen. Firmware
behöver ingen JSON-tolk eller full registercache. Klocka, härledda larmflaggor,
skrivningar och experimentella format är fortsatt separata. Tabellen skiljer
ärvda tolkningar från fångstbelägg och panelobservationer; migreringen tillför
inte nya verifierade registerbetydelser.

Nästa etapp: observerade normallägen för husvärme och varmvatten har fått
avkodning med färskhetskontroll och fullständiga status-/effektpar. Okända
övergångar och avfrostning förblir okända. Fördelad effekt och CoP använder
bara dessa belagda normallägen utan tillskott. Saknade intervall fylls inte
bakåt i de fördelade dygnsenergierna. `status_timeline_v170.py` och fångade
statusfixtures ger en reproducerbar grund för nästa analys.

Nästa protokollsteg efter driftverifieringen är att skilja trafiktyper i
statistiken och kartlägga resterande statusprofiler, särskilt avfrostning och
tillskott. Därefter prioriteras ännu okända nyttiga läsfält och gemensamma
versionsprofiler. Fler skrivbara reglage införs först med verifierad återläsning.

## Mål och utgångsläge

Nya vanliga värden ska kunna läggas till som registerdefinitioner, utan en
specialskriven avkodare för varje paketlängd eller startadress. Samma definition
ska användas av biblioteket, analysverktyget och ESPHome-integrationen.
Historik, bitkommandon och andra sammansatta format kan fortfarande behöva
egna avkodare ovanpå den gemensamma protokollmotorn.

Vi har redan CRC-kontroll, asynkron skrivning och avkodning av sammanhängande
bank-/adressområden för version 170. Överlappande lässvar bekräftar byteadresser
i undersökta områden; detta är inte bevis för att alla kommandon använder dem.
Se [PROTOKOLL-170.md](PROTOKOLL-170.md) för observationerna och
[CODE-REVIEW.md](CODE-REVIEW.md) för kvarvarande osäkerheter.

Protokollmotor, registerdefinitioner och genererade C++-tabeller hör hemma i
`pinussen/comfortzone_heatpump`. ESPHome-entiteter, HA-paket och integrationstester
hör hemma här. Biblioteket importeras som ett låst snapshot enligt
[CONTRIBUTING.md](CONTRIBUTING.md). Befintliga entitets-ID:n ska bevaras.

## Arbetsordning och klarkriterier

### Versionsjämförelse: skilj läsområde från fältlayout

Kodjämförelse 2026-10-25, bibliotek `9d607b7161fb`: de äldre C++-strukturerna
är bibliotekets tolkningar av fångade svar, inte tillverkarens formatspecifikation.
Olika strukturnamn eller paketlängder bevisar därför inte olika protokoll.

- Version 160, 170 och 180 kopplar området `01:0000` till samma funktion
  `reply_r_status_02`. Adressprefixen slutar däremot på `0b07`, `0b08`, `0b09`.
- Version 180 och 221 använder båda `reply_r_status_v180_runtime_and_energy`
  för `05:0028`, trots olika prefix och kommenterade svarslängder.
- Inom 170 kan faktisk frekvens `01:02e9` läsas både i korta svar från
  `01:02b4` och i det äldre blocket från `01:02c7`. Fältets position i svaret
  skiljer sig, men registeradressen är densamma. Detta täcks av regressionstest.
- Biblioteket innehåller också olika parameteradresser: värmebörvärdet anges
  som `00:02a6` för 170 och `00:0290` för 221. Det är skäl att behålla
  versionsprofiler tills motsvarande fält jämförts mot rådata och panel.

Jämför därför alltid `startadress + fältoffset`, bytebredd, skala och bitbetydelse.
Gruppera gemensamma fält först efter belägg; lagra verkliga avvikelser i profiler.
En möjlig förklaring till adressförskjutningar är tillagda interna parametrar,
men detta är en hypotes. Gemensam transport och generiska områdesläsningar
innebär inte att alla fälts betydelse kan upptäckas automatiskt.

Den uppladdade manualen `Manual-ex35-ex50-ex65-g2-2018-11-02.pdf`, CZ06525
Ver G2, anger på omslaget **fr.o.m. SW 1.8 och SN-1815xxxxxx**. Den är en
kompletterande källa för menyer och versionsjämförelse, inte i sig bevis för
funktioner eller register på pumpen med protokoll 170. Avfrostnings-/smältningsfel
behandlas på sidorna 57 och 60; sökbar text bekräftar inte betydelsen av den
blinkande symbol som observerades under paneltestet.

### 1. Beskriv paketformatet och bygg en reproducerbar referens

- Dokumentera ramgränser, längder, kontrollsummornas omfattning, avsändare,
  mottagare, kommandon, hela registeridentifieraren och bekräftade bankadresser.
- Separera transport/parser, transaktioner och fälttolkning. Okända kommandon
  ska kunna sparas och visas utan att deras nyttolast behöver tolkas.
- Samla små anonymiserade råfixtures med källversion, fångsttid, menyvärde,
  kända fångstluckor och förväntad tolkning. Behåll även motexempel och felramar.
- Dela upp trafikstatistik i frågor, svar, ACK, okända kommandon, okända områden,
  delvis avkodade områden och CRC-fel. Nuvarande `unknown registers` är antal
  oklassificerade ramar, inte antal unika register eller ett täckningsmått.

Klart när befintliga fångster kan återspelas med reproducerbara resultat och
varje känd ramtyp har en beskriven struktur samt tester för avklippning,
felaktiga längder, brus, CRC-fel och fel avsändare.

### 2. Skapa registerkartan och migrera befintliga värden

- Inför ett maskinläsbart schema, exempelvis JSON, med stabilt fält-ID,
  protokollversion, adressrymd/prefix, bank, adress, byteantal, datatyp,
  byteordning, skala, enhet, enum/bitar, ogiltighetskoder och läsrättighet.
- Beskriv skrivning separat: kommando/adress kan skilja sig från läsning,
  liksom värdeformat och ACK. Ange intervall, steg, återläsning och belägg.
- Registrera säkerhetsgrad per egenskap: råobservation, kandidat,
  bekräftad läsning och bekräftad skrivning. Ärvt biblioteksnamn är ett belägg
  att undersöka, inte automatiskt en verifierad fysisk betydelse.
- Generera statiska C++-tabeller och referensdokumentation från samma källa.
  Firmware ska inte behöva tolka JSON eller allokera en fullständig minneskarta.
- Migrera kända 170-fält först. Andra versioner får separata profiler;
  gemensamma adresser eller bitbetydelser får inte antas utan belägg.

Klart när den nya avkodaren ger samma verifierade resultat på samma rådata,
även för korta och överlappande svar. Ett fält måste fortfarande vara komplett
i ett färskt svar; gamla fragment får inte blandas till ett nytt mätvärde.
CI ska upptäcka ogiltiga definitioner och genererade filer som inte är uppdaterade.

### 3. Bygg verktyget för systematisk kartläggning

- Utöka PCAP-analysen med täckning per enhet/version/bank/adress, tidsstämplade
  förändringar, pollintervall, råbytes och jämförelse före/efter en menyändring.
- Föreslå datatyper, skalor och bitfält genom flera observationer; märk dem som
  kandidater. Ingen automatisk publicering av gissade givarnamn till HA.
- Skilj verkliga dubletter från upprepad pollning och överlappande block.
- Jämför lika långa fångster med/utan minneskort under dokumenterade driftlägen.
  Försvunnen trafik kan vara historik/loggning; kortets roll måste mätas.
- Sök efter metadata såsom namn, enheter och parameterbeskrivningar. Stöd för
  självbeskrivande parametrar är ännu inte belagt.
- Historik som går över ramgränser får en separat sammanfogning med kontroller
  för adresskontinuitet, tid, källidentitet och luckor.

Klart när verktyget kan visa exakt vilka råfält som ändrades vid en dokumenterad
menyändring och lämna en fixture som går att granska utan tillgång till pumpen.

### 4. Kartlägg driftstatus och de viktigaste återstående värdena

Prioritera sådant som gör elprisstyrning och uppföljning tillförlitliga:

1. Verkligt driftläge: värme, varmvatten, vila och avfrostning samt eventuell
   samtidig drift. Klimatentitetens `HEAT` beskriver inte detta driftläge.
2. Kompressorfrekvens och effektfält. HA-loggen 2026-10-25 visar upprepade
   0 Hz samtidigt med 2376 W angiven effekt och cirka 1131–1140 W eleffekt;
   jämför mot panel och råbytes innan mappningen betraktas som verifierad.
3. Fördelad eleffekt/energi och CoP, först när driftläge och ingående effektfält
   är verifierade. Okänd fördelning ska inte räknas som noll förbrukning.
4. Beräknat framledningsbörvärde, prioritering, tillsatsstatus och larmbitar.
5. Resterande användarmenyer, givare och historik enligt EX50-manualen.

Fånga naturliga driftövergångar och jämför med panelen. Ändra en menyparameter
i taget, dokumentera före/efter, återställ och upprepa. Befintliga versioner
och manualer används för hypoteser; de ersätter inte kontroll på denna version.

Klart per nytt fält när typ, skala och betydelse har oberoende stöd, en
råfixture och tydlig redovisning av vilka driftfall som har observerats.

### 5. Utöka generisk skrivning och HA-stöd

- Återanvänd den fungerande skrivkön och bussarbitreringen; behåll gränserna
  för väntan och ACK samt frånvaron av blind omsändning efter oklart utfall.
- Aktivera nya skrivningar först med belagt kommando, giltiga värden,
  matchande ACK och oberoende återläsning. Skilj skickat, kvitterat och
  återläst i resultatet. Läsbar adress innebär inte skrivbar adress.
- Skapa entiteter från verifierade definitioner. Oklara serviceparametrar
  ligger kvar som rådata/kandidater tills deras funktion är klarlagd.
- Planera versionerade utgåvor där HA-paket och komponent pekar på samma
  revision, så att olika cachelivslängder inte blandar versioner.

Klart när befintliga reglage fortsatt fungerar, nya reglage har dokumenterad
återläsning, hosttester och firmwarebyggen passerar och ändringarna har
verifierats på pumpen. Migreringen sker i små steg med kända fungerande utgåvor.

## Läget efter HA-installationen 2026-10-25

Användarens logg bekräftar firmware byggd 15:36:20, bibliotek `42fc53447755`,
TX26/RX16 och inkommande pumpdata efter OTA. Räknaren når 665 ramar med
0 CRC-fel och 414 oklassificerade ramar. Detta visar fungerande mottagning,
men varken komplett avkodning eller att varje skickad ram fångades.

Fyra beräknade sensorer återkommer som `nan`: eleffekt för värme respektive
varmvatten och deras CoP. Avkodaren saknar verifierat driftläge för fördelningen.
De är inte fyra nya fel vid varje svar. Separata dagliga energisummor för värme
och varmvatten saknar därmed också tillförlitligt underlag. Total eleffekt
och dess dagliga integral är separata från denna fördelning.

Wi-Fi-signalen rapporteras som -91 dB och ett API-avbrott syns. Det är en möjlig
nätverksförklaring, inte bevis för en firmwarekrasch. Protokollanalys ska även
notera logg-/fångstluckor. Den första planversionen ändrade inga pumpinställningar;
efterföljande firmwareinstallationer dokumenteras i PROTOKOLL-170.md.

Tillhörande underhåll: rättade C++-loggformat, tog bort varningar från tomma
debug-makron och undertryckte upprepade `nan` för de fyra härledda sensorerna.
Ett första okänt värde och övergång från känt till okänt publiceras fortfarande;
upprepade ändliga effektvärden behåller sina tidsstämplar för energiintegrering.
Verifierat med sju Python-tester, bibliotekets hosttester under ASan/UBSan,
snapshotkontroll och ESPHome 2026.10.0 / ESP-IDF 5.5.6-bygge av TX26-konfigurationen.
Bygget lyckades utan de rapporterade C++-varningarna. Ingen verifiering av nya
registerbetydelser ingår i dessa underhållstester.

## Genomfört 2026-10-26 och nästa kontroll

- Tre minuters passiv trafik: 985 CRC-giltiga ramar, varav 489 läsfrågor och
  496 lässvar. Nattens synk kan inte styrkas efter en API-relaterad omstart.
- Verifierad ny manuell synk och sparad senaste lyckade synktid i HA-entitet.
  API-timern för omstart utan klient stängs av i det automatiska klockpaketet.
- Totala eleffekten löper nu ut precis som fördelad effekt. Total dygnsenergi
  använder observationsfilter och fyller inte längre bortfall med nästa prov.
- Trafikräknare skiljer transporttyper från avkodade/obehandlade lässvar.
  Generisk inventering av adressområden och byteförändringar tillagd offline.
- `00:000e` prioriteras för nästa paneljämförelse: kandidat till samma
  varmvattenprioritetskoder i 170 och 180. Inte aktiverat som ny skrivfunktion.
- HA-blueprint för prisstyrd värmesänkning förberedd, ännu inte HA-validerad
  eller installerad. Kräver användarens temperaturgränser och prissignal.

Nästa fysiska verifiering är längre fångst av naturliga driftövergångar, särskilt
avfrostning/tillskott, samt panelkontroll vid eldstadsläge och varmvattenprioritet.
Nuvarande stoppfall `20 08 00 00 10` har noll komplett effekt men inget oberoende
panelnamn och ska därför inte ges en ny mode-etikett på chans. De senaste
ändringarna är en etapp, inte en komplett protokollspecifikation.

### Passiv etapp 2026-10-26 kväll

Dygnsinsamling startad 22:23, utan registerskrivningar eller ny OTA. Samlar
API-/uptimehändelser, tidssynkens resultat och råramar med återanslutning.
Avslut planerat 2026-10-27 22:23; resultatet är inte klart vid denna notering.
Driftövergångar och nattens synk bedöms först mot den färdiga fångsten.

30 arkivfångster har inventerats. Marsfilerna överskrider den teoretiska
19200-busskapaciteten med faktor 2,19–2,42 räknat på giltiga rambytes och
PCAP-tid. Tidigare upprepnings- och intervallobservationer måste därför skiljas
från påståenden om fysisk trafik. Ingen automatisk deduplicering införs.
Se [PASSIV-INSAMLING.md](PASSIV-INSAMLING.md) för evidens, kommandon och nästa steg.

HA-metadata rättade för tiondels hertz och filternedräkning. Kodgranskningen
identifierar generell färskhet hos övriga givare och ACK kontra oberoende
återläsning som kvarvarande arbete. 35 Python-tester, 23529 återspelade ramar
under ASan/UBSan och ESPHome-bygget passerar. Metadataändringarna väntar på
nästa installation så att dygnsinsamlingsperioden får oförändrad firmware.

### Status-/effektanalys 2026-10-27

En fryst kopia av pågående dygnsfångst finns lokalt i
`/home/bjwl/comfortzone-status-20261027/`. SHA256 för `capture.pcap`:
`a30aa686f6aa1f09272d2923d14282229f16f3e490b337215b57d463b03a9cb7`.
`observations.json` och `profiles.json` innehåller råramar och tidsavstånd.

8624 kompletta effektobservationer: 7337 har status från samma pump högst två
sekunder tidigare, 1287 saknar ett sådant par. Det är observationsantal, inte
andel drifttid. Nytt verktyg `status_profiles_v170.py` sammanställer detta med
råexempel, skilda enheter och separata räknare för ofullständiga tidspar,
ogiltiga värden, kompletta nollbilder och inkonsekventa effektsummor.

| Rå status | Par inom 2 s | Frekvens, Hz | Eleffekt, W | Tolkning i denna etapp |
| --- | ---: | ---: | ---: | --- |
| `202a000010` | 1723 | 25–43,3 | 515–1193 | Aktiv profil; första byten stöds inte av nuvarande mode-avkodare |
| `282a000010` | 95 | 25–36,2 | 515–1047 | Befintlig värmeprofil |
| `282c000010` | 364 | 25–55 | 773–1643 | Befintlig varmvattenprofil |
| `201a000016` | 688 | 0 | 0 | Alla fem effekt-/frekvensfält noll; fysiskt driftnamn obekräftat |
| `281c000016` | 41 | 0 | 0 | Alla fem effekt-/frekvensfält noll; fysiskt driftnamn obekräftat |
| `2028000010` | 1 | 0 | 697 | Samtidigt 2000 W uteffekt: övergång/motexempel, inte en sammanhängande normaldriftsbild |

Första statusbyten växlar mellan `20` och `28`; det är en skillnad i bit `08`.
Det finns belägg för positiv frekvens även med `20`, så den byten kan inte ensam
användas för att avgöra att kompressorn står. Bitens funktion är fortfarande
okänd. Vi aktiverar därför inte automatiskt samma värme-/CoP-fördelning för
`202a` som för `282a` enbart på liknande effektintervall.

Många för gamla tidspar är omkring 7, 14 och 21 sekunder gamla, alltså ungefär
hela pollcykler. Detta kan bero på saknade statusobservationer i fångsten;
råloggen räcker inte för att fastställa var de försvann. Att utöka parningsfönstret
skulle riskera att blanda effekt från ett nytt driftläge med föregående status.
Tvåsekundersgränsen behålls. Inga tillskott över noll observerades i dessa par.

Tolv nya status-/effektpar har lagts till som regressionstest i båda repona,
inklusive samma status med noll respektive icke-noll värden. Okända profiler
förblir okända. Inga ändringar av pumpinställningar, produktionsavkodare eller
firmwareinstallation gjordes i denna analys. Nästa steg är att spåra flaggan
`08` mot andra register och jämföra observerade statusluckor med enhetens
trafikräknare innan nya mode-etiketter eller längre tidsgränser övervägs.

API-historiken visar oförändrade börvärden 29,1/53,1 °C, kurva 5 och fläkt Low.
Enda registrerade skrivresultatsekvensen är tidssynken 04:10. Det ger inget
stöd för att statusbitens förändring orsakades av dessa användarreglage.
39 Python-tester och C++-regressionstester under ASan/UBSan passerar.
