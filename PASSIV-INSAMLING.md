# Passiv insamling och granskning

## Pågående körning 2026-10-26

En fristående process samlar i 24 timmar från kortet `08:B6:1F:38:5A:C0`,
`192.168.3.179`. Start ungefär 22:23 svensk tid, avslut ungefär samma tid
2026-10-27 om VM:n fortsätter köra. Den ändrar inga pumpregister och installerar
ingen firmware. Den befintliga automatiska tidssynken är fortfarande aktiv.

Första arkivdel: `/home/bjwl/comfortzone-passive-20261026/`.
Aktiv del efter införande av diskskydd:
`/home/bjwl/comfortzone-passive-20261026-bounded/`.
PID-fil: `/home/bjwl/comfortzone-passive-20261026.pid`.
Processlogg: `/home/bjwl/comfortzone-passive-20261026-process.log`.

Insamlingen startades om med diskskydd efter cirka 6,1 MiB. Ursprunglig sluttid
behålls. Den nya delen stoppas vid sammanlagt 128 MiB eller mindre än 2048 MiB
ledigt diskutrymme. Storleken kontrolleras före varje bulk-skrivning, ledigt
utrymme högst en gång per sekund under skrivning. 64 KiB reserveras för
slutstatus; stopporsaken sparas i `status.json`. Äldre filer raderas inte.
Gränserna kan anges med `--max-mib` respektive `--min-free-mib`.

- `capture.pcap`: mottagna UDP-payloads med syntetiska Ethernet/IP-huvuden.
  Tiden är mottagning på VM:n, inte seriell sändtid. IP-checksumman är giltig.
- `events.jsonl`: API-värden, anslutningar, fel och förnyade diagnostikperioder.
  Varje rad sparas direkt. Okända/icke ändliga värden blir JSON `null`.
- `device.jsonl`: tidsstämplade enhetsloggar på INFO-nivå.
- `status.json`: atomiskt uppdaterad sammanfattning varje minut; värdena är
  senast mottagna under aktuell anslutning, inte en garanti om färskhet.

API-klienten återansluter efter avbrott och kontrollerar MAC före diagnostik.
Den ger inte enheten tid via API. Den enda begärda tjänsten är `debug_reroute`:
kopiera mottagna ramar till VM:n i 120 sekunder, förnyat varje minut. Vid normal
avslutning kortas perioden till en sekund. Om processen dödas upphör kopieringen
inom två minuter. Förnyelsen öppnar diagnostiksockeln igen och kan ge en liten
fångstlucka. UDP kan även förlora data; dessa begränsningar gäller all analys.
API-prenumerationen kan påverka en firmware med omstartstimer utan klient;
nuvarande firmware har den timern avstängd.

För att stoppa: kontrollera PID-filens process med `ps`, skicka sedan `SIGTERM`
till den processen. Den överlever avslutad terminal men inte en omstart av VM:n.
Ingen schemalagd framtida analys eller automatisk återstart har installerats.

## Återanvändning

Kör från repot med Python-miljön för ESPHome (aioesphomeapi och PyYAML behövs):

```bash
/home/bjwl/.cache/comfortzone/esphome-2026.10/bin/python scripts/passive_monitor.py \
  --host 192.168.3.179 --mac 08:B6:1F:38:5A:C0 --listen 192.168.2.22 \
  --hours 24 --output /home/bjwl/comfortzone-passive-NY-KORNING
```

Utdatakatalogen måste vara ny. API-nyckeln läses från `secrets.yaml` och skrivs
inte i rapporten. Fångster och enhetsloggar hålls lokalt utanför Git.

Analysera en avslutad fångst eller en separat kopia av den pågående:

```bash
python3 traffic_report_v170.py /sokvag/capture.pcap --output /sokvag/traffic.json
python3 register_coverage_v170.py /sokvag/capture.pcap --output /sokvag/coverage.json
python3 status_timeline_v170.py /sokvag/capture.pcap > /sokvag/timeline.csv
```

En kopia som tas mitt i en skrivning kan sluta med en ofullständig PCAP-post;
verktygen avvisar detta i stället för att tyst tolka en trasig fångst.
Trafikrapporten räknar oförändrade svar per källa, mottagare, bank, startadress
och längd. Den sparar statusprofiler och övergångar utan att gissa driftnamn.
Övergångar över mer än 15 sekunders statuslucka märks separat.

## Resultat från arkivgranskningen

30 befintliga fångster inventerades separat. Marsfilerna har vardera endast
ett UDP-flöde från den gamla ESP32-adressen `192.168.3.142` till VM:n.

| Fångst | Fångad tid, s | CRC-giltiga rambytes | Minsta seriella tid vid 19200 8N1, s |
| --- | ---: | ---: | ---: |
| comfortzone-debug-1.pcap | 58,505 | 253060 | 131,802 |
| comfortzone-debug-2.pcap | 132,835 | 558768 | 291,025 |
| comfortzone-debug-3.pcap | 41,800 | 193863 | 100,970 |
| comfortzone-check-20261026-204442 | 179,875 | 61837 | 32,207 |

De gamla filerna innehåller **2,19–2,42 gånger** så mycket ramdata som en enda
19200-buss hinner skicka på fångsttiden, även utan pauser. Därför kan varje
UDP-paket inte utan vidare behandlas som en unik seriell ram med samma tidsaxel.
Möjliga orsaker är upprepad vidarebefordring, buffring eller annan tidsbas.
Orsaken är inte bevisad. Automatisk deduplicering görs inte: genuin upprepad
pollning kan ha exakt samma bytes. Ramarna är fortfarande användbara som
avkodningsfixtures; gamla ankomstintervall är inte säkra belägg för bussluckor.

I treminutersfångsten den 26 oktober är 358 av 496 lässvar oförändrade från
föregående svar på samma område. Detta stödjer att mycket data återkommer,
men bevisar inte att meddelandena eller fälten kan tas bort. Jämförelse av
minneskortets påverkan kräver jämförbara fångster och är ännu inte genomförd.

## Kod- och HA-granskning i denna etapp

- Skrivmotorns befintliga tester omfattar fel källa/mottagare, trasigt CRC,
  fel ACK-värde, för sent ACK och utebliven automatisk omsändning. Återspelning
  av marsfilerna och det nya insamlingstestet: 23529 ramar under ASan/UBSan.
- Aktuell frekvens presenteras nu med en decimal, i linje med avkodningens
  tiondels hertz. Filternedräkningen är `measurement`, inte en ackumulerad
  `total`. Entitetsnamn och registerbindningar är oförändrade.
- Firmwarebygge passerat. Metadataändringarna är **inte OTA-installerade**;
  dygnsfångsten behåller samma firmware för en sammanhängande observation.
- Effektens giltighetstid och okänt driftläge hanteras sedan föregående etapp.
  Temperaturer och andra vanliga läsfält saknar däremot motsvarande generell
  färskhetsmodell vid avbrott på RS485 medan Wi-Fi lever. Det återstår att
  välja tidsgränser efter observerad pollning; HA-anslutning ensam bevisar
  inte att pumpdata är färska. Ingen generell ersättning med noll har införts.
- Fullständig registeråterläsning efter varje reglage saknas fortfarande:
  flera entiteter uppdateras efter ACK. Klockans verifierade återläsning är
  ett separat, starkare besked.

Nästa analys: sammanställ det avslutade dygnet, kontrollera API-/uptimeavbrott,
ny lyckad tidssynk samt status-/effektpar före och efter naturliga övergångar.
Nya statusnamn eller skrivbara fält kräver fortsatt oberoende belägg.
