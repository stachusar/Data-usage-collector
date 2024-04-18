# Instrukcja instalacji i konfiguracji [skryptu](https://github.com/stachusar/Data-usage-collector/blob/collector/collector.py) zbierającego dane o użyciu dysku

## Spis treści:
[Wymagania instalacyjne](#1-wymagania-instalacyjne)  
[Konfiguracja skryptu](#2-konfiguracja-skryptu)  
[Integracja z usługą systemową i timerem](#3-integracja-z-usługą-systemową-i-timerem)  
[Przydatne polecenia systemowe](#4-przydatne-polecenia-systemowe)  
  

## 1. Wymagania instalacyjne:

`Python 3`: Upewnij się, że na swoim systemie jest zainstalowane środowisko Python 3.

`Biblioteki Pythona` : Skrypt korzysta z kilku bibliotek Pythona.  Upewnij się, że masz zainstalowane wszystkie wymagane biblioteki. 
Jeśli nie jesteś pewien możesz doinstalować brakujące elementy

#### Wykonując polecenie:

```bash
pip3 install subprocess os shutil time csv logging datetime pathlib
```
#### Kod w skrypcie: 
```python
import subprocess
import os
import shutil
import time
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
```
## 2. Konfiguracja skryptu:

__Ścieżka danych__: Otwórz skrypt i znajdź zmienną `data_path`. Zmień ścieżkę do katalogu, w którym chcesz przechowywać dane o użyciu dysku.

```python
data_path = '/ścieżka/do/katalogu/danych'
```
__Interwał zbierania danych__: Możesz dostosować interwał zbierania danych, zmieniając wartość `interval_minutes` na preferowaną liczbę minut.

```python
interval_minutes = 5
```
## 3. Integracja z usługą systemową i timerem:

Utwórz plik konfiguracyjny dla usługi: Utwórz plik `.service` w katalogu `/etc/systemd/system/`, np. disk_usage.service.

```bash
sudo nano /etc/systemd/system/disk_usage.service
```
Dodaj konfigurację do pliku `.service`: Oto przykładowa konfiguracja dla usługi:

```plaintext
[Unit]
Description=Skrypt zbierający dane o użyciu dysku

[Service]
Type=simple
ExecStart=/ścieżka/do/interpretera/pythona /ścieżka/do/skryptu.py
WorkingDirectory=/ścieżka/do/katalogu/skryptu
Restart=always

[Install]
WantedBy=multi-user.target
```
Utwórz plik konfiguracyjny dla timera: Utwórz plik `.timer` w katalogu `/etc/systemd/system/`, np. disk_usage.timer.

```bash
sudo nano /etc/systemd/system/disk_usage.timer
```
Dodaj konfigurację do pliku `.timer` przykładowo:

```plaintext
[Unit]
Description=Timer dla skryptu zbierającego dane o użyciu dysku

[Timer]
OnCalendar=*-*-* *:00:00
Unit=disk_usage.service

[Install]
WantedBy=timers.target
```
## 4. Przydatne polecenia systemowe:
* ```sudo systemctl start disk_usage ```: Uruchami ausługę.                         
* ```sudo systemctl stop disk_usage```: Zatrzymuje usługę.
* ```sudo systemctl restart disk_usage```: Restartuje usługę.
* ```sudo systemctl status disk_usage```: Wyświetla status usługi.
* ```sudo systemctl enable disk_usage```: Włącza autostart usługi.
* ```sudo systemctl disable disk_usage```: Wyłącza autostart usługi.
