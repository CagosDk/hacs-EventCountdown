# Event Countdown

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

En Home Assistant integration der opretter sensorer for kommende begivenheder – fødselsdage, bryllupsdag, og éngangsbegivenheder.

## Installation via HACS

1. Tilføj dette repository som **Custom Repository** i HACS (kategori: Integration)
2. Find "Event Countdown" i HACS og installér
3. Genstart Home Assistant
4. Gå til **Indstillinger → Enheder & tjenester → Tilføj integration** og søg efter "Event Countdown"

## Opsætning

Under opsætning (og efterfølgende via **Konfigurer**) angiver du:

- **Antal sensorer** – hvor mange sensorer der oprettes (standard: 4)
- **Begivenheder (JSON)** – en JSON-liste med dine begivenheder

Integrationerne opdateres automatisk hver time.

## JSON-format

```json
[
  {
    "name": "Frederiks fødselsdag",
    "day": 24,
    "month": 3,
    "year": 2015,
    "type": "fødselsdag",
    "soon": 30,
    "picture": "/local/pic/frederik.jpg"
  },
  {
    "name": "Bryllupsdag",
    "day": 24,
    "month": 9,
    "year": 2016,
    "type": "bryllup",
    "soon": 30
  },
  {
    "name": "Sommerferie",
    "day": 5,
    "month": 7,
    "year": 2026,
    "type": "begivenhed",
    "soon": 60
  }
]
```

### Felter

| Felt | Påkrævet | Beskrivelse |
|------|----------|-------------|
| `name` | Ja | Navn på begivenheden |
| `day` | Ja | Dag (1-31) |
| `month` | Ja | Måned (1-12) |
| `year` | Nej | Fødselsår / stiftelsesår - bruges til at beregne alder |
| `type` | Nej | `fødselsdag` (standard), `bryllup`, eller `begivenhed` |
| `soon` | Nej | Antal dage inden begivenheden markeres som "snart" (standard: 60) |
| `picture` | Nej | Sti til billede, f.eks. `/local/pic/navn.jpg` |
| `disabled` | Nej | Sæt til `true` for at springe begivenheden over |

### Typer

- **`fødselsdag`** – tilbagevendende hvert år, beregner alder automatisk
- **`bryllup`** – tilbagevendende hvert år, beregner årsdag automatisk
- **`begivenhed`** – éngangsbegivenhed, springes over hvis datoen er passeret

## Sensorer

Integrationen opretter N sensorer (f.eks. `sensor.event_countdown_event_1`):

- **State** – antal dage til begivenheden
- **Attributter:**
  - `full_name` – læsevenlig tekst, f.eks. *"Frederik 11 års fødselsdag om 5 dage"*
  - `name` – begivenhedens navn
  - `type` – begivenhedstype
  - `age` – beregnet alder/årsdag
  - `days_remaining` – antal dage tilbage
  - `soon` – `true` hvis inden for tærsklen
  - `soon_threshold` – tærsklen i dage
  - `event_date` – begivenhedens originale dato (YYYY-MM-DD)
  - `entity_picture` – sti til billede

Sensorerne sorteres: "snart"-begivenheder først, derefter stigende efter dage tilbage.
