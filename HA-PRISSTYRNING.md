# Förberedd prisstyrning för husvärme

Status 2026-10-26: blueprinten är förberedd och dess beslutsmallar testade offline.
Den är **inte installerad eller körd i användarens HA**, som vi saknar åtkomst till.
Temperaturgränser och prissignal måste väljas innan den aktiveras.

Filen är [blueprints/automation/comfortzone_price_setback.yaml](blueprints/automation/comfortzone_price_setback.yaml).
Importera dess GitHub-URL som en blueprint i HA och skapa därefter en automation.
Det här är en första sänkning vid dyr el, inte en optimerare med prisprognos eller
förvärmning. Varmvatten, ventilation, värmekurva och kompressorgränser ändras inte.

## Val som behövs

- Husvärmens climate-entitet, inte varmvattenentiteten.
- En ny hjälpbrytare (`input_boolean`) för att slå prisstyrningen på/av. Börja med av.
- En `binary_sensor` som är `on` när elen är dyr och `off` annars. Den kan byggas
  från den prisintegration som används; blueprinten antar ingen valuta, enhet eller
  ett visst Nordpool-entitetsnamn. Prissignalens aktualitet måste skötas av dess källa.
- En tillförlitlig aktuell inomhustemperatur.
- Normalt börvärde, sänkt börvärde och lägsta önskade rumstemperatur. Inga
  temperaturer är förvalda. Pumpens nuvarande börvärde 29,1 °C är inte samma sak
  som dess uppmätta rumstemperatur och används inte som en gissad komfortgräns.

## Beteende och återkoppling

Dyr el med tillräcklig rumstemperatur väljer det sänkta börvärdet. Annars används
normalvärdet. Saknad prissignal eller rumstemperatur väljer normalvärdet när
styrningen är på. Ett för gammalt men fortfarande tillgängligt värde kan inte
identifieras enbart från dess siffra; källan behöver markera det som otillgängligt.
Börvärden utanför climate-entitetens gränser eller sänkt värde över normalvärdet
blockeras. Saknat aktuellt börvärde blockerar skrivning.

Automationen reagerar på ändrad signal/rumstemperatur/hjälpbrytare och stämmer
av var femtonde minut samt när HA startar. Prissignalen får stabilisera sig i
30 sekunder. Den skickar bara om börvärdet behöver ändras. Efter ett kommando
väntar den högst 30 sekunder på matchande climate-börvärde; annars visas ett
beständigt meddelande. Ingen omedelbar omsändning sker, men en senare utlösning
kan göra ett nytt försök. Körningar köas för att ett avslag på hjälpbrytaren inte
ska tappas medan en tidigare skrivning väntar på bekräftelse.

Climate-börvärdet uppdateras redan efter matchande pump-ACK i dagens integration.
Blueprintens kontroll är därför **ACK-baserad bekräftelse**, inte bevis på en
oberoende registeråterläsning. Pumpens senare lässvar uppdaterar också börvärdet.
Tidssynken har en separat, striktare kontroll med oberoende återläsning.

Stäng av **hjälpbrytaren** för att återgå till konfigurerat normalvärde. Att stänga
av själva automationen kör inga återställningsåtgärder. Om HA eller pumpen är
otillgänglig kan inget börvärde återställas då; kontrollera normalvärdet när
kontakten återkommer. Med hjälpbrytaren av görs ingen regelbunden skrivning, så
att manuell styrning kan användas. Med den på kan nästa avstämning ersätta en
manuell ändring.

Referenser: Home Assistants [blueprint-schema](https://www.home-assistant.io/docs/blueprint/schema/),
[automationstriggers](https://www.home-assistant.io/docs/automation/trigger/) och
[climate-åtgärder](https://www.home-assistant.io/integrations/climate/).
