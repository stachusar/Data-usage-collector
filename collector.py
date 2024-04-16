import subprocess
import os
import shutil
import time
import csv
import logging
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler

FORCE_UPDATE = True 



def setup_logging():
    """
    Konfiguruje logowanie, aby wszystkie komunikaty były zapisywane do pliku log z odpowiednią rotacją plików.
    Logi nie będą wyświetlane w konsoli.
    """
    log_directory = '/home/ubuntu/log'
    log_file_path = os.path.join(log_directory, 'collect_data.log')

    # Utworzenie katalogu dla logów, jeśli nie istnieje
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Ustawienie rotacji pliku logów na 5MB na plik z maksymalnie 5 starymi plikami logów
    handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5)

    # Ustawienie formatu logowania
    logging_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=logging_format, datefmt=date_format)
    handler.setFormatter(formatter)

    # Konfiguracja głównego loggera
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Usuwanie wszystkich StreamHandlerów z głównego loggera
    for h in root_logger.handlers[:]:
        if isinstance(h, logging.StreamHandler):
            root_logger.removeHandler(h)
    
    root_logger.addHandler(handler)

    logging.info("Logowanie zostało skonfigurowane.")

def ensure_directory_exists(directory_path):
    """
    Tworzy katalog, jeśli nie istnieje, aby zapewnić miejsce na zapis danych.
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    logging.info(f"Sprawdzono/zapewniono istnienie katalogu: {directory_path}")

def save_to_csv(data_path, data):
    """
    Zapisuje dane do pliku CSV, tworząc katalog, jeśli jest to konieczne.
    """
    ensure_directory_exists(data_path.parent)
    with open(data_path, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(data)
    logging.info(f"Dane zostały zapisane do {data_path}")

def convert_to_bytes(size):
    """
    Konwertuje rozmiar z formatu czytelnego (T, G, M, K) na bajty.
    """
    units = {"T": 1e12, "G": 1e9, "M": 1e6, "K": 1e3, "B": 1}
    try:
        number, unit = float(size[:-1]), size[-1].upper()
    except ValueError:
        # Obsługa przypadku, gdy rozmiar dysku jest nieprawidłowy
        logging.warning(f"Niewłaściwy rozmiar dysku: {size}")
        return 0  # Zwróć zero w przypadku nieprawidłowego rozmiaru dysku
    return int(number * units.get(unit, 1))

def convert_from_bytes(size_in_bytes):
    """
    Konwertuje rozmiar z bajtów na format czytelny (T, G, M, K), zachowując dwa miejsca po przecinku.
    """
    for unit in ["T", "G", "M", "K", "B"]:
        if size_in_bytes >= 1e12 and unit == "T":
            return f"{size_in_bytes/1e12:.2f}{unit}"
        elif size_in_bytes >= 1e9 and unit == "G":
            return f"{size_in_bytes/1e9:.2f}{unit}"
        elif size_in_bytes >= 1e6 and unit == "M":
            return f"{size_in_bytes/1e6:.2f}{unit}"
        elif size_in_bytes >= 1e3 and unit == "K":
            return f"{size_in_bytes/1e3:.2f}{unit}"
    return f"{size_in_bytes:.2f}B"

def calculate_average(values, round_to_integer=True):
    """
    Oblicza średnią z listy wartości w bajtach lub procentach i konwertuje wynik na format czytelny.
    """
    if '%' in values[0]:  # Sprawdzamy typ danych na podstawie pierwszej wartości w liście
        processed_values = []
        for value in values:
            try:
                processed_values.append(float(value.strip('%')))  # Konwertujemy wartość na float, usuwając znak procenta
            except ValueError:
                logging.warning(f"Niewłaściwa wartość procentowa: {value}, pominięto.")
        if processed_values:  # Sprawdzamy, czy są jakiekolwiek przetworzone wartości
            average = f"{sum(processed_values) / len(processed_values):.2f}%"  # Obliczenie średniej dla procentów
        else:
            average = "0%"  # Jeśli brak poprawnych wartości procentowych, ustawiamy średnią na 0%
    else:
        processed_values = []
        for value in values:
            if '.' in value:
                whole, decimal = value.split('.')
                if decimal == '00':
                    processed_values.append(whole)  # Jeśli po przecinku jest "00", dodajemy tylko część całkowitą
                else:
                    processed_values.append(value)
            else:
                processed_values.append(value)
        
        total = sum(convert_to_bytes(value) for value in processed_values)
        average_in_bytes = total / len(processed_values)
        
        if round_to_integer:
            average_in_bytes = round(average_in_bytes)
        
        average = convert_from_bytes(average_in_bytes)
    
    return average

def process_data_file(file_path):
    """
    Przetwarza pojedynczy plik danych, obliczając średnie dla każdej kolumny.
    """
    with open(file_path, 'r') as file:
        data = list(csv.reader(file))
    
    if not data:
        logging.error(f"Brak danych w pliku CSV: {file_path}")
        return None

    averages = []
    for i in range(1, 5):  # Zakładamy, że kolumny danych są od 1 do 4
        column_data = []
        for row in data:
            if len(row) > i:
                column_data.append(row[i])
        if i == 5:  # Dla procentów
            column_data = [value.strip('%') for value in column_data]  # Usunięcie znaków procenta
            average = f"{sum(float(value) for value in column_data) / len(column_data):.2f}%"  # Obliczenie średniej
        else:  # Dla rozmiarów dysku
            average = calculate_average(column_data)
        averages.append(average)

    return [file_path.stem] + averages + [data[0][-1]]  # Zwraca nazwę pliku (godzinę/dzień/miesiąc) i średnie


def collect_data(interval_minutes=5):
    """
    Funkcja zbierająca dane o użyciu dysku w określonych interwałach czasowych.
    
    Args:
        interval_minutes (int): Interwał czasowy w minutach.
    """
    setup_logging()
    next_collection = datetime.now().replace(second=0, microsecond=0)

    while True:
        current_time = datetime.now()
        if current_time >= next_collection:
            hourly_file_path = Path(f"/home/ubuntu/statistic/data/{current_time.strftime('%Y/%m/%d/%H')}.csv")
            logging.info(f"Rozpoczęto zbieranie danych o użyciu dysku: {current_time.strftime('%Y-%m-%d %H:%M')}")

            df_output = subprocess.run(['df', '-h'], capture_output=True, text=True).stdout
            for line in df_output.split('\n'):
                if '/srv/ftp' in line:
                    data = [current_time.strftime('%M')] + line.split()[1:6]
                    save_to_csv(hourly_file_path, data)
                    logging.info(f"Dane o użyciu dysku /srv/ftp zostały zapisane: {data}")

            next_collection += timedelta(minutes=interval_minutes)
            next_collection -= timedelta(minutes=next_collection.minute % interval_minutes)
            next_collection = next_collection.replace(second=0, microsecond=0)

            sleep_time = (next_collection - datetime.now()).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)

def should_create_or_update_file(file_path):
    """
    Decyduje, czy plik powinien zostać utworzony lub zaktualizowany.

    Args:
        file_path (Path): Ścieżka do pliku, który ma być utworzony/zaktualizowany.

    Returns:
        bool: True, jeśli operacja tworzenia/aktualizacji powinna zostać wykonana, w przeciwnym razie False.
    """
    # Sprawdzenie, czy plik już istnieje
    if file_path.exists():
        # Logika dla plików dobowych i godzinowych - nie aktualizujemy, jeśli istnieją
        parts = file_path.parts
        if "data" in parts:
            data_index = parts.index("data")
            if len(parts) > data_index + 3:  # Struktura wskazuje na plik dobowy lub godzinowy
                print(f"Plik {file_path} już istnieje. Pomijanie tworzenia.")
                return False
        # Dla plików miesięcznych i rocznych zawsze zwracamy True
        return True
    else:
        # Plik nie istnieje, więc powinien zostać utworzony
        return True

def generate_missing_summaries(base_path="/home/ubuntu/statistic/data"):
    logging.info("Rozpoczynanie generowania brakujących podsumowań.")

    start_date = datetime(2024, 1, 1)  # Przykładowa data początkowa
    end_date = datetime.now()  # Do bieżącej daty

    # Generowanie podsumowań dziennych tylko dla dni z danymi godzinowymi
    current_date = start_date
    while current_date <= end_date:
        year = current_date.strftime("%Y")
        month = current_date.strftime("%m")
        day = current_date.strftime("%d")

        # Sprawdzanie, czy istnieją dane godzinowe dla danego dnia
        hourly_data_path = Path(base_path) / year / month / day
        if hourly_data_path.exists() and any(hourly_data_path.glob("*.csv")):
            # Jeśli istnieją dane godzinowe, generuj podsumowanie dziennie
            daily_summary_path = hourly_data_path.parent / f"{day}.csv"
            create_daily_summary(year, month, day)

        current_date += timedelta(days=1)

    # Generowanie podsumowań miesięcznych i rocznych tylko na podstawie istniejących danych
    for year in range(start_date.year, end_date.year + 1):
        year_path = Path(base_path) / str(year)
        for month_path in filter(Path.is_dir, year_path.iterdir()):
            month = month_path.name
            # Sprawdzanie, czy istnieją podsumowania dziennie dla danego miesiąca
            if any(month_path.glob("*.csv")):
                # Jeśli istnieją podsumowania dziennie, generuj podsumowanie miesięczne
                create_monthly_summary(str(year), month)

        # Sprawdzanie, czy istnieją podsumowania miesięczne dla danego roku
        if any(filter(lambda p: p.is_file() and p.suffix == '.csv', year_path.iterdir())):
            # Jeśli istnieją podsumowania miesięczne, generuj podsumowanie roczne
            create_yearly_summary(str(year))

    logging.info("Zakończono generowanie brakujących podsumowań.")

def sort_csv_by_first_column(csv_path):
    """
    Sortuje plik CSV według wartości w pierwszej kolumnie.
    """
    with open(csv_path, 'r', newline='') as file:
        reader = csv.reader(file)
        data = list(reader)
    
    sorted_data = sorted(data, key=lambda row: float(row[0]))  # Sortowanie danych

    with open(csv_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(sorted_data)

def create_daily_summary(year, month, day):
    logging.info(f"Tworzenie/aktualizacja podsumowania dziennego dla {year}-{month}-{day}.")
    source_path = Path(f"/home/ubuntu/statistic/data/{year}/{month}/{day}")
    summary_path = source_path.parent / f"{day}.csv"

    if not source_path.exists():
        logging.warning(f"Brak danych godzinowych dla {year}-{month}-{day}, pomijanie.")
        return

    ensure_directory_exists(source_path)

    summary_data = []
    update_required = False

    # Ładowanie istniejącego podsumowania jeśli istnieje
    if summary_path.exists():
        with open(summary_path, 'r', newline='') as file:
            existing_data = {rows[0]: rows[1:] for rows in csv.reader(file)}
    else:
        existing_data = {}

    for file_path in sorted(source_path.glob("*.csv")):
        hour = file_path.stem
        if hour in existing_data:
            continue  # Pomijanie godzin już uwzględnionych w podsumowaniu

        update_required = True
        processed_data = process_data_file(file_path)
        if processed_data:
            summary_data.append(processed_data)

    if update_required:
        with open(summary_path, 'w', newline='') as summary_file:
            writer = csv.writer(summary_file)
            existing_data.update({data[0]: data[1:] for data in summary_data})
            for hour, data in sorted(existing_data.items()):
                writer.writerow([hour] + data)
        logging.info(f"Podsumowanie dziennie dla {year}-{month}-{day} zostało utworzone/zaaktualizowane.")

def create_monthly_summary(year, month):
    logging.info(f"Tworzenie/aktualizacja podsumowania miesięcznego dla {year}-{month}.")
    source_path = Path(f"/home/ubuntu/statistic/data/{year}/{month}")
    summary_path = source_path.parent / f"{month}.csv"

    if not source_path.exists():
        logging.warning(f"Brak katalogu z danymi dla {year}-{month}, pomijanie.")
        return

    ensure_directory_exists(source_path)

    summary_data = []
    update_required = False

    # Ładowanie istniejącego podsumowania jeśli istnieje
    if summary_path.exists():
        with open(summary_path, 'r', newline='') as file:
            existing_data = {rows[0]: rows[1:] for rows in csv.reader(file)}
    else:
        existing_data = {}

    day_files = filter(lambda p: p.is_file() and p.suffix == '.csv', source_path.iterdir())
    for day_file in sorted(day_files, key=lambda x: int(x.stem)):
        day = day_file.stem
        if day in existing_data:
            continue  # Pomijanie dni już uwzględnionych w podsumowaniu

        update_required = True
        processed_data = process_data_file(day_file)
        if processed_data:
            summary_data.append(processed_data)

    if update_required:
        with open(summary_path, 'w', newline='') as file:
            writer = csv.writer(file)
            existing_data.update({data[0]: data[1:] for data in summary_data})
            for day, data in sorted(existing_data.items()):
                writer.writerow([day] + data)
        logging.info(f"Podsumowanie miesięczne dla {year}-{month} zostało utworzone/zaaktualizowane.")

def create_yearly_summary(year):
    logging.info(f"Tworzenie/aktualizacja podsumowania rocznego dla {year}.")
    source_path = Path(f"/home/ubuntu/statistic/data/{year}")
    summary_path = Path(f"/home/ubuntu/statistic/data/{year}.csv")

    if not source_path.exists():
        logging.warning(f"Brak katalogu z danymi dla {year}, pomijanie.")
        return

    ensure_directory_exists(source_path)

    summary_data = []
    update_required = False

    # Ładowanie istniejącego podsumowania jeśli istnieje
    if summary_path.exists():
        with open(summary_path, 'r', newline='') as file:
            existing_data = {rows[0]: rows[1:] for rows in csv.reader(file)}
    else:
        existing_data = {}

    month_files = filter(lambda p: p.is_file() and p.suffix == '.csv', source_path.iterdir())
    for month_file in sorted(month_files, key=lambda x: int(x.stem)):
        month = month_file.stem
        if month in existing_data:
            continue  # Pomijanie miesięcy już uwzględnionych w podsumowaniu

        update_required = True
        processed_data = process_data_file(month_file)
        if processed_data:
            summary_data.append(processed_data)

    if update_required:
        with open(summary_path, 'w', newline='') as file:
            writer = csv.writer(file)
            existing_data.update({data[0]: data[1:] for data in summary_data})
            for month, data in sorted(existing_data.items()):
                writer.writerow([month] + data)
        logging.info(f"Podsumowanie roczne dla {year} zostało utworzone/zaaktualizowane.")

def test_update_all():
    """
    Sprawdza, czy istnieje żądanie natychmiastowej aktualizacji wszystkich podsumowań.
    Jeśli tak, zwraca True.
    """
    # Sprawdzanie flagi w pliku lub zmiennej środowiskowej
    return os.environ.get('FORCE_UPDATE', 'false').lower() == 'true'

def main():
    logging.basicConfig(level=logging.INFO)
    setup_logging()
    logging.info("Uruchomienie głównej funkcji skryptu.")

    # Sprawdzenie i uzupełnienie brakujących podsumowań na starcie
    logging.info("Sprawdzanie i uzupełnianie brakujących podsumowań.")
    generate_missing_summaries()

    # Główna pętla działająca co 5 minut
    while True:
        try:
            # Zbieranie nowych danych
            collect_data(interval_minutes=5)
            logging.info("Zakończono zbieranie danych.")

            # Pobieranie aktualnej daty
            current_time = datetime.now()
            current_year = current_time.strftime("%Y")
            current_month = current_time.strftime("%m")
            current_day = current_time.strftime("%d")

            # Sprawdzenie czy wymagana jest natychmiastowa aktualizacja
            if test_update_all():
                logging.info("Wymuszono natychmiastową aktualizację wszystkich podsumowań.")
                for year in range(int(current_year), int(current_year) + 1):
                    for month in range(1, 13):
                        create_monthly_summary(str(year), f"{month:02}")
                    create_yearly_summary(str(year))

            # Aktualizacja podsumowań zgodnie z harmonogramem
            create_daily_summary(current_year, current_month, current_day)
            if current_time.hour == 0:  # Aktualizacja na koniec dnia
                create_monthly_summary(current_year, current_month)
            if current_time.day == 1 and current_time.hour == 0:  # Aktualizacja na koniec miesiąca
                create_yearly_summary(current_year)

        except Exception as e:
            logging.error(f"Wystąpił błąd podczas wykonywania operacji: {e}")

        # Ustawienie czasu, aby wstrzymać działanie skryptu do następnej 5-minutowej iteracji
        next_run_time = datetime.now() + timedelta(minutes=5 - datetime.now().minute % 5, seconds=-datetime.now().second)
        sleep_time = (next_run_time - datetime.now()).total_seconds()
        if sleep_time > 0:
            logging.info(f"Czekanie {sleep_time} sekund do następnego cyklu zbierania danych.")
            time.sleep(sleep_time)

if __name__ == "__main__":
    main()
