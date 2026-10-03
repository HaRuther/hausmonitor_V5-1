# Hausmonitor V5.2

Erweiterung von V5 mit den wiederhergestellten Bearbeitungs- und Rohdatenfunktionen.

## Neu bzw. wiederhergestellt

- Fotos direkt je Nivellement-Messreihe hochladen und anzeigen
- Nivellement-Metadaten nachträglich bearbeiten
- alle Nivellement-Rohablesungen SW, SO, ANB, TSW und TSO anzeigen und bearbeiten
- Rissmessstellen nachträglich bearbeiten
- jede Rissmessung nachträglich bearbeiten
- bestehendes Rissfoto beim Bearbeiten behalten oder durch ein neues ersetzen
- vollständige Rohmesswerttabellen für Nivellement und Rissmonitoring
- CSV-Exporte für beide Module
- App-Icon, PWA, Geräte- und Grenzwertfelder bleiben enthalten

## Installation

```bash
cp .env.example .env
nano .env
docker-compose up -d --build
```

## Update

```bash
cd /root/hausmonitor
cp -a data /root/hausmonitor-data-backup
cp .env /root/hausmonitor-env-backup
docker-compose down
```

Neue Dateien einspielen und danach:

```bash
docker-compose up -d --build
docker logs --tail=100 hausmonitor-v5
```

Die Datenbankmigration ist additiv. Der Ordner `data/` enthält Datenbank und Fotos.

## Fehlerband und Rauschdarstellung

Die Startseite zeigt nun die Nivellement-Änderung zusammen mit einem hellblauen Fehlerband von ± einem kombinierten Standardfehler. Ein zweites Diagramm zeigt die Standardabweichungen der Einzelablesungen an SW und SO. Die Kennzahlen zeigen zusätzlich Standardfehler, Signal-Rausch-Verhältnis und Bewertung.

Das Fehlerband beschreibt die rechnerische Streuung innerhalb einer Kampagne. Es ersetzt nicht die langfristige Wiederholunsicherheit durch Neuaufstellung, Maßstabeinsetzen, Beleuchtung und Temperatur.
