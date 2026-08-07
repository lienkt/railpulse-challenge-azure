# RailPulse Challenge – Azure Functions

## Overview

This project demonstrates a complete serverless data pipeline using **Azure Functions**, **Azure SQL Database**, and the **iRail (SNCB/NMBS) Liveboard API**.

The Azure Function retrieves live train departure information from the iRail API, processes the returned data, and stores normalized records in Azure SQL Database.

---

# Project Architecture

```
HTTP Request
        │
        ▼
Azure Function (Python)
        │
        ▼
iRail / SNCB Liveboard API
        │
        ▼
Data Processing
        │
        ▼
Azure SQL Database
        │
        ├── stations
        ├── vehicles
        └── liveboard_records
```

---

## Data Flow

The project processes train data through the following pipeline:

```text
HTTP Client
    |
    v
Azure Function: GetLiveboard
    |
    v
iRail Liveboard API
    |
    v
JSON Validation and Transformation
    |
    v
Azure SQL Database
    |
    +-- stations
    +-- vehicles
    +-- liveboard_records
```

### 1. HTTP Request

The process starts when a client sends an HTTP request to the `GetLiveboard` Function.

Example:

```bash
curl -sS -G \
  "http://localhost:7071/api/GetLiveboard" \
  --data-urlencode "station=Gent-Sint-Pieters"
```

The station name is provided through the `station` query parameter.

When no station is provided, the Function uses `Brussel-Centraal/Bruxelles-Central` as the default station.

### 2. iRail API Request

The Azure Function sends a request to the iRail liveboard endpoint:

```text
https://api.irail.be/liveboard/
```

The request includes parameters such as:

```text
station
format=json
lang=en
arrdep=departure
```

Example Python logic:

```python
response = requests.get(
    "https://api.irail.be/liveboard/",
    params={
        "station": station_name,
        "format": "json",
        "lang": "en",
        "arrdep": "departure"
    },
    timeout=30
)

data = response.json()
```

The iRail API returns live station and departure information as JSON.

### 3. Data Transformation

The Function does not store the complete API response as one large JSON object.

Instead, it extracts the required fields and separates them into three entities:

```text
Station
Vehicle
Liveboard record
```

The main field mapping is:

| iRail data            | Azure SQL column                        |
| --------------------- | --------------------------------------- |
| Station ID            | `stations.station_id`                   |
| Station name          | `stations.station_name`                 |
| Standard station name | `stations.standard_name`                |
| Longitude             | `stations.longitude` (DECIMAL(10,6))    |
| Latitude              | `stations.latitude` (DECIMAL(10,6))     |
| Station link (`@id`)  | `stations.link`                         |
| Vehicle ID            | `vehicles.id`                           |
| Vehicle short name    | `vehicles.short_name`                   |
| Vehicle type          | `vehicles.vehicle_type`                 |
| Vehicle class code    | `vehicles.vehicle_class_code`           |
| Vehicle number        | `vehicles.vehicle_number`               |
| Vehicle link (`@id`)  | `vehicles.link`                         |
| Destination           | `liveboard_records.destination`         |
| Departure time        | `liveboard_records.scheduled_departure` |
| Delay                 | `liveboard_records.delay_seconds`       |
| Platform              | `liveboard_records.platform`            |
| Canceled status       | `liveboard_records.canceled`            |

Unix timestamps returned by iRail are converted into SQL-compatible date and time values before insertion.

### 4. Database Connection

The Function reads the Azure SQL connection string from an environment variable:

```python
connection_string = os.environ["SQL_CONNECTION_STRING"]
```

During local development, the value is stored in:

```text
local.settings.json
```

After deployment, the value is configured in:

```text
Azure Function App
→ Settings
→ Environment variables
```

The SQL password is never hardcoded in the source code.

### 5. Normalized Database Storage

The transformed data is stored in three normalized tables.

#### `stations`

Stores one row for each station.

#### `vehicles`

Stores one row for each train vehicle.

#### `liveboard_records`

Stores individual departure observations and references the station and vehicle through foreign keys. Duplicate rows are prevented with a unique key on `(station_id, vehicle_id, scheduled_departure)`.

The relationships are:

```text
stations
    1
    |
    | station_id
    |
    n
liveboard_records
    n
    |
    | vehicle_id
    |
    1
vehicles
```

This design reduces duplicated station and vehicle information.

### 6. HTTP Response

After the SQL transaction is completed, the Function returns a JSON response similar to:

```json
{
  "success": true,
  "station_requested": "Gent-Sint-Pieters",
  "source": "iRail",
  "database": {
    "stations_processed": 1,
    "vehicles_processed": 20,
    "records_inserted": 20
  }
}
```

The exact number of departures depends on the current iRail liveboard response.

### Complete Flow

```text
1. Client sends station name
2. Azure Function receives the request
3. Function calls the iRail API
4. iRail returns liveboard JSON
5. Function validates and transforms the data
6. Function reads the SQL connection string from the environment
7. Station data is inserted or updated
8. Vehicle data is inserted or updated
9. Departure records are inserted or updated
10. The SQL transaction is committed
11. Function returns a JSON result
```

# Technologies

- Python 3.10+
- Azure Functions
- Azure SQL Database
- Azure Functions Core Tools v4
- Azure CLI
- pyodbc
- requests

---

# Project Structure

```
railpulse-challenge-azure/
├── .github/
│   └── workflows/
│       └── deploy-function.yml
├── function_app.py
├── host.json
├── local.settings.json
├── requirements.txt
├── migrations/
│   └── sql_reset_and_recreate.sql
├── .venv/
└── README.md
```

---

# Azure Resources

The project uses the following Azure resources:

- Resource Group: **railpulse-rg**
- Azure SQL Server: **railpulse-server**
- Azure SQL Database: **railpulse-db**
- Azure Function App
- Hosting Plan: **Flex Consumption**
- Runtime: **Python 3.10+**

---

# Database Schema

The database is normalized into three tables.

## stations

Stores station information.

| Column        | Description                |
| ------------- | -------------------------- |
| station_id    | Primary Key from iRail     |
| station_name  | Station display name       |
| standard_name | Official multilingual name |
| longitude     | Longitude                  |
| latitude      | Latitude                   |
| link          | iRail station `@id` URL    |

---

## vehicles

Stores train information.

| Column             | Description                            |
| ------------------ | -------------------------------------- |
| id                 | Primary Key from `vehicleinfo.name`    |
| short_name         | Train short name                       |
| vehicle_type       | Raw train type from iRail              |
| vehicle_class_code | Normalized class code (`S`, `IC`, ...) |
| vehicle_number     | Train number from iRail                |
| link               | iRail vehicle `@id` URL                |

---

## liveboard_records

Stores live departure records.

| Column              | Description              |
| ------------------- | ------------------------ |
| record_id           | Primary Key              |
| station_id          | Foreign Key → stations   |
| vehicle_id          | Foreign Key → vehicles   |
| destination         | Destination station      |
| scheduled_departure | Scheduled departure time |
| delay_seconds       | Delay in seconds         |
| platform            | Platform number          |
| canceled            | Cancellation status      |

The table is protected by a unique index on `(station_id, vehicle_id, scheduled_departure)` so repeated calls update the same departure instead of inserting duplicates.

This schema avoids duplicated station and vehicle information by storing them only once and referencing them using foreign keys.

---

# Installation

## 1. Install Azure Functions Core Tools (macOS)

```bash
brew tap azure/functions
brew trust azure/functions
brew install azure-functions-core-tools@4
```

If Homebrew asks you to trust the tap first, run:

```bash
brew trust azure/functions
```

---

## 2. Create Azure Functions Project

```bash
func init
```

Choose:

```
4. Python
```

Create a new function:

```bash
func new
```

Select:

```
11. HTTP Trigger
```

Function name:

```
GetLiveboard
```

Authentication level:

```
ANONYMOUS
```

---

## 3. Install Python Dependencies

Create and activate a virtual environment if needed.

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Do **not** run:

```bash
pip freeze > requirements.txt
```

during normal development because it may include many unnecessary packages.

If starting from scratch, install the required packages:

```bash
pip install requests pyodbc azure-functions python-dotenv
```

---

# Install SQL Server ODBC Driver

Install unixODBC:

```bash
brew install unixodbc
```

Install Microsoft's ODBC Driver 18:

```bash
brew tap microsoft/mssql-release
brew trust microsoft/mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install microsoft/mssql-release/msodbcsql18
```

Verify installation:

```bash
odbcinst -q -d
```

Expected output:

```
[ODBC Driver 18 for SQL Server]
```

Verify with Python:

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
```

The output should include:

```
ODBC Driver 18 for SQL Server
```

---

# Local Configuration

Edit **local.settings.json**

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SQL_CONNECTION_STRING": "Driver={ODBC Driver 18 for SQL Server};Server=tcp:railpulse-server.database.windows.net,1433;Database=railpulse-db;Uid=YOUR_SQL_USERNAME;Pwd=YOUR_SQL_PASSWORD;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
  }
}
```

Replace:

- `YOUR_SQL_USERNAME`
- `YOUR_SQL_PASSWORD`

with your own Azure SQL credentials.

> **Important:** Never commit `local.settings.json` to GitHub.

---

# Run the Function Locally

Start the Azure Function:

```bash
func start
```

Expected output:

```
Functions:

    GetLiveboard: [GET,POST]
    http://localhost:7071/api/GetLiveboard
```

---

# Test the HTTP Endpoint

Request a liveboard for Brussels-Central:
Get the station standard name from here: https://api.irail.be/v1/stations
Then check the result with this: https://api.irail.be/v1/liveboard?station=Gent-Sint-Pieters&format=json

```bash
curl "http://localhost:7071/api/GetLiveboard?station=Brussels-Central"
```

Pretty-print the JSON:

```bash
curl -s "http://localhost:7071/api/GetLiveboard?station=Brussels-Central" | python3 -m json.tool
```

Other stations can also be tested:

```bash
curl -s "http://localhost:7071/api/GetLiveboard?station=Gent-Sint-Pieters" | python3 -m json.tool
```

```bash
curl -s "http://localhost:7071/api/GetLiveboard?station=Antwerpen-Centraal" | python3 -m json.tool
```

### Batch Update for Major Belgian Stations

You can trigger updates in batch for major stations by looping over a station list.

```bash
BASE_URL="http://localhost:7071/api/GetLiveboard"

stations=(
  "Brussel-Centraal/Bruxelles-Central"
  "Brussel-Zuid/Bruxelles-Midi"
  "Brussel-Noord/Bruxelles-Nord"
  "Antwerpen-Centraal"
  "Gent-Sint-Pieters"
  "Leuven"
  "Liege-Guillemins"
  "Brugge"
  "Namur"
  "Mechelen"
)

for station in "${stations[@]}"; do
  echo "Updating: $station"
  curl -sS -G "$BASE_URL" \
    --data-urlencode "station=$station" \
    | python3 -m json.tool

  # Small delay to avoid sending bursts.
  sleep 1
done
```

If you want to run the same update against your deployed Function App, replace `BASE_URL` with your Azure URL:

```bash
BASE_URL="https://<YOUR_FUNCTION_APP>.azurewebsites.net/api/GetLiveboard"
```

Current deployed endpoint example:

```bash
https://railpulse-function-fjb6akbnbhbubuhv.swedencentral-01.azurewebsites.net/api/GetLiveboard?station=Brussel-Zuid/Bruxelles-Midi
```

Use this deployed base URL for batch updates:

```bash
BASE_URL="https://railpulse-function-fjb6akbnbhbubuhv.swedencentral-01.azurewebsites.net/api/GetLiveboard"
```

---

# Development Pipeline

The complete workflow of the project is:

1. Receive an HTTP request.
2. Call the iRail/SNCB Liveboard API.
3. Parse the returned JSON.
4. Connect securely to Azure SQL Database.
5. Insert or update station information.
6. Insert or update vehicle information.
7. Store live departure records.
8. Return a JSON response to the client.

---

# Security

Sensitive information is **never hardcoded**.

The SQL connection string is stored as an environment variable:

```
SQL_CONNECTION_STRING
```

When deployed to Azure, this value should be configured in:

```
Function App
→ Settings
→ Environment Variables
→ App Settings
```

---

# VS Code

Enable the `code` command in the terminal.

Open VS Code.

Press:

```
Command + Shift + P
```

Search for:

```
Shell Command:
Install 'code' command in PATH
```

---

# Deploy to Azure

Install Azure CLI:

```bash
brew install azure-cli
```

Login:

```bash
az login
```

Publish the Function App:

```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

---

# Deliverables

This project delivers:

- Azure Function App with an HTTP endpoint
- Azure SQL Database with normalized tables
- Secure environment variable configuration
- Live train departure data retrieved from the iRail API
- Data persisted into Azure SQL Database

---

# Notes

During development, different stations were tested through the iRail API, including:

- Brussels-Central
- Gent-Sint-Pieters
- Antwerpen-Centraal

The Function accepts the station name as an HTTP query parameter, making it easy to retrieve liveboard information for different railway stations without changing the source code.
