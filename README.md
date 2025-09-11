# 🚲 WRM Forecast API

Aplikacja do pobierania danych o stacjach **Wrocławskiego Roweru Miejskiego (WRM)** i generowania prognoz dostępności rowerów.  
Projekt realizowany w ramach zajęć z wykorzystaniem otwartych danych miejskich (**Open Data**).

---

## 📊 Źródła danych

Dane pochodzą z **GBFS (General Bikeshare Feed Specification)** udostępnianych przez operatora Nextbike:

- **Informacje o stacjach:**  
  `https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/en/station_information.json`
- **Status stacji:**  
  `https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/en/station_status.json`
- **Regiony systemu:**  
  `https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/en/system_regions.json`

Projekt filtruje dane tylko dla regionu **Wrocław**.

---

## 🧩 Scenariusz użycia

System automatycznie pobiera dane o dostępności rowerów z WRM i:

1. Aktualizuje dane o liczbie rowerów na stacjach w czasie rzeczywistym.  
2. Zapisuje historię zmian dostępności rowerów.  
3. Generuje **prognozy** liczby dostępnych rowerów na podstawie danych historycznych.  
4. Udostępnia API oraz WebSocket z prognozami, aby inne aplikacje mogły korzystać z danych w czasie rzeczywistym.  

**Przykład**: użytkownik może zapytać, ile rowerów będzie dostępnych na danej stacji w ciągu kolejnych 60 minut.

---

## ⚙️ Wymagania

- Python **3.10+**  
- PowerShell (Windows) lub bash (Linux/Mac)  
- `pip` (instalator paczek Pythona)

---

## 🚀 Instalacja i uruchomienie

```bash
# 1. Stworzenie i aktywacja środowiska wirtualnego
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# lub
source .venv/bin/activate    # Linux/Mac

# 2. Instalacja zależności
pip install -r requirements.txt

# 3. Ustawienie zmiennych środowiskowych
setx GBFS_STATION_INFO_URL "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/en/station_information.json"
setx GBFS_STATION_STATUS_URL "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/en/station_status.json"
setx GBFS_REGIONS_URL "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/en/system_regions.json"
setx WRM_REGION_NAME "Wroclaw"

# 4. Uruchomienie serwera API
uvicorn src.serve_api:app --reload
