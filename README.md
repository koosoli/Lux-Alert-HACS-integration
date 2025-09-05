# LU-Alert CAP-LU Python Integration

Dieses Projekt bietet eine Python-Bibliothek und ein Integrations-Skript zum Abrufen und Parsen von Warnmeldungen des luxemburgischen [LU-Alert-Systems](https://data.public.lu/fr/datasets/alertes-du-systeme-lu-alert/), die im CAP-LU-Format (Common Alerting Protocol) veröffentlicht werden.

Das Ziel ist es, eine robuste Alternative zu YAML-basierten Konfigurationen für Systeme wie Home Assistant bereitzustellen.

## Projektstruktur

Das Projekt ist in zwei Hauptteile gegliedert: eine Kernbibliothek (`cap_lu`) und ein ausführbares Integrations-Skript (`integration.py`).

### `cap_lu` Bibliothek

Dies ist eine wiederverwendbare Bibliothek zur Verarbeitung von CAP-LU-Daten.

- **`models.py`**: Enthält Python-`dataclasses` (`Alert`, `Info`, `Area`, `Parameter`), die die Struktur einer CAP-Warnung abbilden.
- **`enums.py`**: Definiert alle in der CAP-LU-Spezifikation festgelegten Enumerationen (z.B. `Status`, `MsgType`, `Severity`).
- **`parser.py`**: Stellt die Funktion `parse_xml` bereit, die eine rohe XML-Zeichenkette in ein `Alert`-Objekt umwandelt.
- **`builder.py`**: Stellt die Funktion `build_xml` bereit, um ein `Alert`-Objekt zurück in eine XML-Zeichenkette zu serialisieren.
- **`validator.py`**: Enthält Geschäftslogik zur Validierung eines `Alert`-Objekts gegen die CAP-LU-Spezifikation (optional, nicht im Hauptskript verwendet).

### `integration.py` Skript

Dieses Skript ist der Einstiegspunkt für die Integration. Es führt die folgenden Aktionen aus:
1.  Kontaktiert die `data.public.lu` API, um die URL der neuesten XML-Warnungsdatei zu finden.
2.  Ruft den Inhalt dieser URL ab.
3.  Verwendet die `cap_lu`-Bibliothek, um den XML-Inhalt zu parsen.
4.  Gibt die relevanten Warnungsinformationen als einzelnes JSON-Objekt auf der Standardausgabe aus.

## Einrichtung

1.  **Abhängigkeiten installieren:**
    Stellen Sie sicher, dass Sie Python 3 installiert haben. Führen Sie dann den folgenden Befehl aus, um die erforderliche `requests`-Bibliothek zu installieren:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Skript ausführen:**
    Um die neueste Warnung abzurufen und die Sensor-Daten im JSON-Format auszugeben, führen Sie das Skript aus:
    ```bash
    python3 integration.py
    ```

## Beispiel-Ausgaben

Die Ausgabe des Skripts ist so gestaltet, dass sie direkt von anderen Systemen, wie z.B. einem Home Assistant `command_line`-Sensor, verarbeitet werden kann.

### Beispiel bei einer aktiven Warnung

```json
{
    "LU-Alert Status": "Actual",
    "LU-Alert Type": "Alert",
    "LU-Alert Certainty": "Observed",
    "LU-Alert Urgency": "Immediate",
    "LU-Alert Severity": "Severe",
    "LU-Alert Event": "Test Event",
    "LU-Alert Headline": "Test Alert Headline",
    "LU-Alert Description": "This is a test description.",
    "LU-Alert Sender": "ctie@etat.lu",
    "LU-Alert Sent": "2025-07-18T14:00:00+02:00",
    "LU-Alert Identifier": "LU-Alert.1721304000.4000.0"
}
```

### Beispiel, wenn keine Warnung aktiv ist

Wenn keine aktive Warnung gefunden wird, gibt das Skript einen Standard-Satz von Werten aus, der einen "alles in Ordnung"-Zustand anzeigt:

```json
{
    "LU-Alert Status": "OK",
    "LU-Alert Type": "Keine",
    "LU-Alert Certainty": "N/A",
    "LU-Alert Urgency": "N/A",
    "LU-Alert Severity": "N/A",
    "LU-Alert Event": "Keine Warnung",
    "LU-Alert Headline": "Keine Warnung",
    "LU-Alert Description": "Derzeit liegt keine aktive Warnung vor.",
    "LU-Alert Sender": "N/A",
    "LU-Alert Sent": "N/A",
    "LU-Alert Identifier": "N/A"
}
```

## Konzeptuelle Home Assistant Integration

Sie können dieses Skript in Home Assistant mit einem [Command-line Sensor](https://www.home-assistant.io/integrations/command_line/) integrieren. Der Sensor würde das Skript in regelmäßigen Abständen ausführen und das zurückgegebene JSON parsen.

Hier ist eine konzeptionelle YAML-Konfiguration:

```yaml
sensor:
  - platform: command_line
    name: LU-Alert Data
    command: "python3 /pfad/zu/ihrem/projekt/integration.py"
    scan_interval: 300 # Alle 5 Minuten
    value_template: "{{ value_json['LU-Alert Status'] }}" # Haupt-Sensor zeigt den Status an
    json_attributes:
      - "LU-Alert Type"
      - "LU-Alert Certainty"
      - "LU-Alert Urgency"
      - "LU-Alert Severity"
      - "LU-Alert Event"
      - "LU-Alert Headline"
      - "LU-Alert Description"
      - "LU-Alert Sender"
      - "LU-Alert Sent"
      - "LU-Alert Identifier"
```

Von diesem Hauptsensor aus können Sie dann Template-Sensoren erstellen, um auf die einzelnen Attribute zuzugreifen, falls erforderlich.
