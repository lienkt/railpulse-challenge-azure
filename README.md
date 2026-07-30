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
│
├── function_app.py
├── host.json
├── local.settings.json
├── requirements.txt
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

---

## vehicles

Stores train information.

| Column       | Description      |
| ------------ | ---------------- |
| vehicle_id   | Primary Key      |
| vehicle_name | Train identifier |

---

## liveboard_records

Stores live departure records.

| Column              | Description                    |
| ------------------- | ------------------------------ |
| record_id           | Primary Key                    |
| station_id          | Foreign Key → stations         |
| vehicle_id          | Foreign Key → vehicles         |
| destination         | Destination station            |
| scheduled_departure | Scheduled departure time       |
| delay_seconds       | Delay in seconds               |
| platform            | Platform number                |
| canceled            | Cancellation status            |
| fetched_at          | Timestamp when data was stored |

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
