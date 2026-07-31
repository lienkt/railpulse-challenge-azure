# RailPulse Cloud — Azure Functions Challenge

## 1. Project Overview

RailPulse Cloud is a serverless data pipeline built with:

- Python
- Azure Functions
- Azure SQL Database
- iRail/SNCB Liveboard API
- Azure Functions Core Tools
- Azure CLI

The project exposes an HTTP endpoint that:

1. Receives a railway station name.
2. Calls the iRail liveboard API.
3. Extracts train departure data.
4. Normalizes station, vehicle, and departure information.
5. Stores the results in Azure SQL Database.
6. Returns a JSON response showing the result of the operation.

---

## 2. Architecture

```text
HTTP Client
    |
    v
Azure Function
    |
    v
iRail / SNCB Liveboard API
    |
    v
Data Transformation
    |
    v
Azure SQL Database
    |
    +-- stations
    +-- vehicles
    +-- liveboard_records
```

---

## 3. Azure Resources

The project uses the following Azure resources:

| Resource           | Value                                                            |
| ------------------ | ---------------------------------------------------------------- |
| Subscription       | Azure for Students                                               |
| Resource Group     | `railpulse-rg`                                                   |
| Azure SQL Database | `railpulse-db`                                                   |
| Azure SQL Server   | Your unique Azure SQL server name                                |
| Region             | Sweden Central or another region allowed by Azure Student policy |
| Function App plan  | Flex Consumption                                                 |
| Function runtime   | Python 3.10+                                                     |
| Storage redundancy | LRS                                                              |

Do not publish SQL passwords, connection strings, subscription IDs, or the content of `local.settings.json`.

---

# 4. Azure Resource Setup

## 4.1 Create the Resource Group

In Azure Portal, create a Resource Group with:

| Field               | Value                                |
| ------------------- | ------------------------------------ |
| Subscription        | Azure for Students                   |
| Resource Group name | `railpulse-rg`                       |
| Region              | A region allowed by the subscription |

The Resource Group contains all project resources and makes it easier to manage or delete the project later.

---

## 4.2 Create Azure SQL Database

Create an Azure SQL Database with:

| Field                | Value                        |
| -------------------- | ---------------------------- |
| Resource Group       | `railpulse-rg`               |
| Database name        | `railpulse-db`               |
| Workload environment | Development                  |
| Service tier         | General Purpose              |
| Compute tier         | Serverless                   |
| Hardware             | Standard-series              |
| Storage              | Small development allocation |
| Zone redundancy      | Disabled                     |
| Connectivity         | Public endpoint              |
| Minimum TLS version  | TLS 1.2                      |

Create a new SQL Server when prompted.

Use:

| Field          | Value                                     |
| -------------- | ----------------------------------------- |
| Server name    | A globally unique name                    |
| Authentication | SQL Authentication                        |
| Admin login    | A username created by you                 |
| Password       | A strong password stored securely         |
| Location       | Same or nearby region as the Function App |

For a student challenge, avoid unnecessary paid features such as:

- Hyperscale
- Zone redundancy
- Microsoft Defender for SQL
- Advanced auditing
- Ledger

Always confirm the estimated monthly cost before creating the database.

---

## 4.3 Configure SQL Networking

Open:

```text
Azure Portal
→ SQL Server
→ Networking
```

Configure:

```text
Public network access: Selected networks
```

Enable:

```text
Allow Azure services and resources to access this server
```

Add the current local client IP address.

This allows:

- The local development machine to connect to Azure SQL.
- The Azure Function App to connect to Azure SQL.

Keep the connection policy at its default value.

---

## 4.4 Create a Storage Account

Create a Storage Account with:

| Field                | Value                                  |
| -------------------- | -------------------------------------- |
| Resource Group       | `railpulse-rg`                         |
| Storage account name | A globally unique lowercase name       |
| Region               | Same as the Function App when possible |
| Performance          | Standard                               |
| Redundancy           | LRS                                    |

The storage account is used by Azure Functions for runtime operations.

---

## 4.5 Create the Function App

Create a Function App with:

| Field            | Value                               |
| ---------------- | ----------------------------------- |
| Resource Group   | `railpulse-rg`                      |
| Hosting plan     | Flex Consumption                    |
| Runtime          | Python                              |
| Python version   | 3.10 or later                       |
| Memory           | 512 MB or suitable development size |
| Zone redundancy  | Disabled                            |
| Public access    | Enabled                             |
| VNet integration | Disabled                            |
| Storage          | Project storage account             |

Use the exact configuration currently supported by the Azure Portal. Azure options can differ by region and subscription.

---

# 5. Local Development Setup

## 5.1 Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd railpulse-challenge-azure
```

---

## 5.2 Create a Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

When activated, the terminal should show:

```text
(.venv)
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

---

## 5.3 Install Azure Functions Core Tools on macOS

Run:

```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

If Homebrew blocks the external tap, trust it first:

```bash
brew trust azure/functions
brew install azure-functions-core-tools@4
```

Verify:

```bash
func --version
```

The installed version should be Azure Functions Core Tools v4.

---

## 5.4 Create the Azure Functions Project

From the project directory:

```bash
func init
```

Select:

```text
Python
```

Create the HTTP-triggered function:

```bash
func new
```

Select:

```text
HTTP trigger
```

Enter the function name:

```text
GetLiveboard
```

Select the authentication level:

```text
ANONYMOUS
```

Depending on the Azure Functions Python programming model, the project may use either:

```text
function_app.py
```

or a function folder containing:

```text
GetLiveboard/
├── function.json
└── __init__.py
```

This project uses the structure generated by the currently installed Azure Functions Core Tools.

---

## 5.5 Enable the `code` Command

In Visual Studio Code:

```text
Command + Shift + P
```

Search for:

```text
Shell Command: Install 'code' command in PATH
```

Then open the project from Terminal:

```bash
code .
```

---

# 6. Python Dependencies

The project requires:

```text
azure-functions
requests
pyodbc
```

Optional development packages may include:

```text
python-dotenv
```

Install dependencies:

```bash
pip install -r requirements.txt
```

A minimal `requirements.txt` can contain:

```text
azure-functions
requests
pyodbc
```

Avoid repeatedly running:

```bash
pip freeze > requirements.txt
```

inside a large development environment because it may add unrelated packages.

---

# 7. Install Microsoft ODBC Driver on macOS

Install unixODBC:

```bash
brew install unixodbc
```

Add the official Microsoft tap:

```bash
brew tap microsoft/mssql-release
```

If required by Homebrew:

```bash
brew trust microsoft/mssql-release
```

Install Microsoft ODBC Driver 18:

```bash
HOMEBREW_ACCEPT_EULA=Y \
brew install microsoft/mssql-release/msodbcsql18
```

Verify the installed ODBC drivers:

```bash
odbcinst -q -d
```

Expected output includes:

```text
[ODBC Driver 18 for SQL Server]
```

Verify through Python:

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
```

The output must contain:

```text
ODBC Driver 18 for SQL Server
```

---

# 8. Database Schema

The database uses three normalized tables:

- `stations`
- `vehicles`
- `liveboard_records`

Only the latest schema below should be used.

Create a file:

```text
database/schema.sql
```

Add:

```sql
DROP TABLE IF EXISTS dbo.liveboard_records;
DROP TABLE IF EXISTS dbo.vehicles;
DROP TABLE IF EXISTS dbo.stations;
GO

CREATE TABLE dbo.stations (
    station_id VARCHAR(50) NOT NULL,
    station_name VARCHAR(255) NOT NULL,
    standard_name VARCHAR(255) NULL,
    longitude DECIMAL(10, 6) NULL,
    latitude DECIMAL(10, 6) NULL,
    created_at DATETIME2 NOT NULL
        DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_stations
        PRIMARY KEY (station_id)
);
GO

CREATE TABLE dbo.vehicles (
    vehicle_id VARCHAR(100) NOT NULL,
    vehicle_name VARCHAR(255) NULL,
    created_at DATETIME2 NOT NULL
        DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_vehicles
        PRIMARY KEY (vehicle_id)
);
GO

CREATE TABLE dbo.liveboard_records (
    record_id INT IDENTITY(1,1) NOT NULL,
    station_id VARCHAR(50) NOT NULL,
    vehicle_id VARCHAR(100) NOT NULL,
    destination VARCHAR(255) NULL,
    scheduled_departure DATETIME2 NULL,
    delay_seconds INT NOT NULL DEFAULT 0,
    platform VARCHAR(20) NULL,
    canceled BIT NOT NULL DEFAULT 0,
    fetched_at DATETIME2 NOT NULL
        DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_liveboard_records
        PRIMARY KEY (record_id),

    CONSTRAINT FK_liveboard_station
        FOREIGN KEY (station_id)
        REFERENCES dbo.stations(station_id),

    CONSTRAINT FK_liveboard_vehicle
        FOREIGN KEY (vehicle_id)
        REFERENCES dbo.vehicles(vehicle_id)
);
GO

CREATE INDEX IX_liveboard_station
ON dbo.liveboard_records(station_id);
GO

CREATE INDEX IX_liveboard_vehicle
ON dbo.liveboard_records(vehicle_id);
GO

CREATE INDEX IX_liveboard_departure
ON dbo.liveboard_records(scheduled_departure);
GO
```

Run the script through the Azure SQL Query Editor or another SQL client.

Verify the tables:

```sql
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'dbo';
```

Expected tables:

```text
stations
vehicles
liveboard_records
```

---

## 8.1 Why the Schema Is Normalized

A liveboard response may contain repeated station and vehicle information.

Instead of storing all information in one table:

- `stations` stores one row per station.
- `vehicles` stores one row per train vehicle.
- `liveboard_records` stores individual departure observations.

The `liveboard_records` table references stations and vehicles using foreign keys.

This reduces duplicated data and keeps the relationships consistent.

---

# 9. iRail API

The Function uses the iRail liveboard endpoint:

```text
https://api.irail.be/liveboard/
```

Example request:

```bash
curl -sS -L -G \
  "https://api.irail.be/liveboard/" \
  -H "Accept: application/json" \
  -H "User-Agent: RailPulseChallenge/1.0" \
  --data-urlencode "station=Gent-Sint-Pieters" \
  --data-urlencode "format=json" \
  --data-urlencode "lang=en" \
  --data-urlencode "arrdep=departure" \
  | python3 -m json.tool
```

The pipeline primarily extracts:

- Station ID
- Station name
- Standard station name
- Coordinates
- Vehicle ID
- Destination
- Scheduled departure
- Delay
- Platform
- Cancellation status

---

# 10. Local Environment Variables

Open:

```bash
open local.settings.json
```

Use:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SQL_CONNECTION_STRING": "Driver={ODBC Driver 18 for SQL Server};Server=tcp:<SQL_SERVER>.database.windows.net,1433;Database=railpulse-db;Uid=<SQL_USERNAME>;Pwd=<SQL_PASSWORD>;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
  }
}
```

Replace:

```text
<SQL_SERVER>
<SQL_USERNAME>
<SQL_PASSWORD>
```

with the real local development values.

Never place the real connection string in:

- `function_app.py`
- `README.md`
- GitHub
- Commit history

---

## 10.1 Protect `local.settings.json`

Check `.gitignore`:

```bash
grep local.settings.json .gitignore
```

If missing:

```bash
echo "local.settings.json" >> .gitignore
```

A recommended `.gitignore` includes:

```text
.venv/
__pycache__/
*.pyc
local.settings.json
.env
.vscode/
```

Before committing:

```bash
git status
```

Make sure `local.settings.json` is not staged.

---

# 11. Function Security

The Function must load its SQL configuration using an environment variable:

```python
import os

connection_string = os.environ["SQL_CONNECTION_STRING"]
```

Do not hardcode:

```python
password = "my-real-password"
```

Do not commit secrets into GitHub.

---

# 12. Run the Function Locally

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Azure Functions:

```bash
func start
```

Expected output:

```text
Functions:

    GetLiveboard: [GET,POST]
    http://localhost:7071/api/GetLiveboard
```

---

# 13. Test the Local Endpoint

Open a second Terminal window.

Test the default working station:

```bash
curl -sS -G \
  "http://localhost:7071/api/GetLiveboard" \
  --data-urlencode "station=Brussel-Centraal/Bruxelles-Central" \
  | python3 -m json.tool
```

```bash
curl -sS -G \
  "http://localhost:7071/api/GetLiveboard" \
  --data-urlencode "station=Gent-Sint-Pieters" \
  | python3 -m json.tool
```

You can also test:

```bash
curl -sS -G \
  "http://localhost:7071/api/GetLiveboard" \
  --data-urlencode "station=Antwerpen-Centraal" \
  | python3 -m json.tool
```

An expected successful response is similar to:

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

The record counts depend on the current liveboard response.

---

# 14. Verify Data in Azure SQL

Open:

```text
Azure Portal
→ Azure SQL Database
→ Query editor
```

Check stations:

```sql
SELECT *
FROM dbo.stations;
```

Check vehicles:

```sql
SELECT TOP 50 *
FROM dbo.vehicles
ORDER BY created_at DESC;
```

Check departure records:

```sql
SELECT TOP 50
    record_id,
    station_id,
    vehicle_id,
    destination,
    scheduled_departure,
    delay_seconds,
    platform,
    canceled,
    fetched_at
FROM dbo.liveboard_records
ORDER BY record_id DESC;
```

Check row counts:

```sql
SELECT COUNT(*) AS station_count
FROM dbo.stations;

SELECT COUNT(*) AS vehicle_count
FROM dbo.vehicles;

SELECT COUNT(*) AS liveboard_count
FROM dbo.liveboard_records;
```

If all three tables contain valid data, the local pipeline is working.

---

# 15. Configure Azure Environment Variables

Open:

```text
Azure Portal
→ Function App
→ Settings
→ Environment variables
→ App settings
```

Add:

```text
Name:
SQL_CONNECTION_STRING
```

Value:

```text
Driver={ODBC Driver 18 for SQL Server};Server=tcp:<SQL_SERVER>.database.windows.net,1433;Database=railpulse-db;Uid=<SQL_USERNAME>;Pwd=<SQL_PASSWORD>;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

Select:

```text
Apply
```

Restart the Function App if required.

Do not publish this value in the repository.

---

# 16. Azure CLI Setup

Install Azure CLI:

```bash
brew install azure-cli
```

Verify:

```bash
az --version
```

Sign in:

```bash
az login
```

Check the active subscription:

```bash
az account show --output table
```

List available subscriptions if needed:

```bash
az account list --output table
```

Select a subscription only when the correct one is not already active:

```bash
az account set \
  --subscription "<SUBSCRIPTION_NAME_OR_ID>"
```

Do not add a real Subscription ID to this README.

---

# 17. Deploy the Azure Function

List existing Function Apps:

```bash
az functionapp list \
  --query "[].{Name:name,ResourceGroup:resourceGroup,State:state,Host:defaultHostName}" \
  --output table
```

Publish the project:

```bash
func azure functionapp publish <FUNCTION_APP_NAME>
```

Example:

```bash
func azure functionapp publish railpulse-function
```

Use the exact Function App name shown in Azure Portal.

A successful deployment should show:

```text
Deployment successful
```

and list the deployed `GetLiveboard` function.

---

# 18. Test the Public Azure Endpoint

The public URL has a format similar to:

```text
https://<FUNCTION_APP_HOST>/api/GetLiveboard
```

Test it:

```bash
curl -sS -G \
  "https://<FUNCTION_APP_HOST>/api/GetLiveboard" \
  --data-urlencode "station=Gent-Sint-Pieters" \
  | python3 -m json.tool
```

Then run the SQL verification queries again.

A new row with a recent `fetched_at` value confirms that the deployed Azure Function wrote data into Azure SQL.

---

# 19. Project Structure

A simple project structure is:

```text
railpulse-challenge-azure/
├── function_app.py
├── host.json
├── local.settings.json
├── requirements.txt
├── README.md
├── .gitignore
└── database/
    └── schema.sql
```

For a larger implementation, the code can later be separated into:

```text
railpulse-challenge-azure/
├── function_app.py
├── database/
│   └── schema.sql
├── utils/
│   ├── api.py
│   ├── transform.py
│   └── db.py
├── requirements.txt
├── host.json
├── README.md
└── .gitignore
```

The smaller structure is sufficient for the MVP.

---

# 20. Error Handling

The Function should handle:

- Missing environment variables
- iRail request timeout
- Invalid API response
- Upstream iRail exceptions
- SQL connection errors
- SQL transaction failures
- Missing station or vehicle information

SQL transactions should be committed only after successful processing.

If an error occurs, the transaction should be rolled back.

---

# 21. MVP Deliverables

The project satisfies the Must-Have requirements when all items below are complete:

- [ ] Azure SQL Database exists.
- [ ] SQL firewall allows the local IP.
- [ ] Azure services are allowed to access the SQL Server.
- [ ] The normalized database schema exists.
- [ ] The Function calls the iRail API.
- [ ] The Function reads the SQL connection string from an environment variable.
- [ ] No credentials are hardcoded.
- [ ] The Function stores stations in Azure SQL.
- [ ] The Function stores vehicles in Azure SQL.
- [ ] The Function stores liveboard records in Azure SQL.
- [ ] The Function runs locally.
- [ ] The Function is deployed to Azure.
- [ ] The public HTTP endpoint works.
- [ ] Azure SQL contains live data.
- [ ] The README explains the schema and setup.

---

# 22. Nice-to-Have Improvements

## 22.1 Timer Trigger

A Timer Trigger can run the pipeline automatically every 15 minutes.

Example CRON schedule:

```text
0 */15 * * * *
```

This can be added after the HTTP-triggered MVP is complete.

---

## 22.2 Duplicate Prevention

Repeated requests can produce duplicate liveboard observations.

Possible solutions:

- Add a unique constraint.
- Use `IF NOT EXISTS`.
- Use a SQL `MERGE`.
- Check an existing record before inserting.

A possible unique combination is:

```text
station_id
vehicle_id
scheduled_departure
```

The correct design depends on whether repeated snapshots should be preserved.

---

## 22.3 Multiple Stations

The pipeline can be extended to process multiple major stations:

```python
stations = [
    "Brussels-Midi",
    "Antwerpen-Centraal",
    "Gent-Sint-Pieters",
    "Liège-Guillemins",
]
```

Each station can be fetched and stored using the same normalized schema.

Brussels-Central can be added again when the upstream iRail issue is resolved.

---

# 23. Troubleshooting

## Homebrew rejects a tap

Run:

```bash
brew trust azure/functions
```

or:

```bash
brew trust microsoft/mssql-release
```

Then retry the installation.

---

## `code: command not found`

In Visual Studio Code:

```text
Command + Shift + P
```

Select:

```text
Shell Command: Install 'code' command in PATH
```

---

## ODBC Driver is missing

Check:

```bash
odbcinst -q -d
```

and:

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
```

Install `msodbcsql18` if Driver 18 is missing.

---

## SQL login fails

Check:

- SQL username
- SQL password
- Server hostname
- Database name
- Client firewall IP
- `Allow Azure services and resources to access this server`
- Connection string formatting

---

## Function works locally but fails in Azure

Check:

- `SQL_CONNECTION_STRING` exists in Azure Environment Variables.
- SQL networking allows Azure services.
- `pyodbc` is present in `requirements.txt`.
- The Azure deployment completed successfully.
- Function App logs show the actual error.
- The Function App was restarted after configuration changes.

---

## iRail returns `NullPointerException`

Try another major station such as:

```text
Gent-Sint-Pieters
Antwerpen-Centraal
Brussels-Midi
```

An upstream iRail error does not necessarily indicate a problem in the Azure Function.

---

# 24. Security Checklist

Before pushing to GitHub:

```bash
git status
```

Check for exposed connection strings:

```bash
grep -R "Pwd=" . \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude=local.settings.json
```

Do not commit:

```text
local.settings.json
.env
SQL passwords
SQL connection strings
Subscription IDs
Access tokens
Function keys
```

Commit only safe project files:

```bash
git add \
  function_app.py \
  requirements.txt \
  host.json \
  database/schema.sql \
  README.md \
  .gitignore
```

Then:

```bash
git commit -m "Build Azure Function liveboard SQL pipeline"
git push origin main
```

---

# 25. Final Result

When complete, the project provides:

- A public Azure Function HTTP endpoint.
- Live train information retrieved from iRail.
- Secure SQL configuration through environment variables.
- A normalized Azure SQL Database.
- Persisted station, vehicle, and departure records.
- A repeatable local and Azure deployment process.
- Documentation explaining the architecture and database design.
