import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import azure.functions as func
import pyodbc
import requests


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

IRAIL_URL = "https://api.irail.be/liveboard/"

DEFAULT_STATION = "Brussel-Centraal/Bruxelles-Central"
COLLECTION_STATIONS = [DEFAULT_STATION]
TIMER_SCHEDULE = "0 */15 * * * *"  # every 15 minutes
DEFAULT_RETENTION_DAYS = 30


def get_sql_connection() -> pyodbc.Connection:
    connection_string = os.environ.get("SQL_CONNECTION_STRING")

    if not connection_string:
        raise RuntimeError(
            "SQL_CONNECTION_STRING environment variable is missing."
        )

    return pyodbc.connect(connection_string)


def parse_unix_datetime(value: Any) -> datetime | None:
    """
    iRail normally returns departure time as a Unix timestamp string.
    Convert it to a timezone-aware UTC datetime.
    """
    if value is None or value == "":
        return None

    try:
        return datetime.fromtimestamp(
            int(value),
            tz=timezone.utc,
        )
    except (TypeError, ValueError, OverflowError):
        return None


def to_optional_str(value: Any) -> str | None:
    if value is None:
        return None

    return str(value)


def to_optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_optional_text_from_mapping(value: Any, *keys: str) -> str | None:
    if isinstance(value, dict):
        for key in keys:
            text = to_optional_str(value.get(key))

            if text:
                return text

        return None

    return to_optional_str(value)


def extract_station(data: dict[str, Any]) -> dict[str, Any]:
    station_info = data.get("stationinfo")

    if not isinstance(station_info, dict):
        station_info = {}

    station_id = (
        to_optional_str(station_info.get("id"))
        or to_optional_str(data.get("station"))
        or "UNKNOWN_STATION"
    )
    station_name = (
        to_optional_str(station_info.get("name"))
        or to_optional_str(data.get("station"))
        or "Unknown station"
    )

    return {
        "station_id": station_id,
        "station_name": station_name,
        "standard_name": to_optional_str(
            station_info.get("standardname")
        ),
        "longitude": to_optional_float(station_info.get("locationX")),
        "latitude": to_optional_float(station_info.get("locationY")),
        "station_link": to_optional_str(station_info.get("@id")),
    }


def extract_departures(data: dict[str, Any]) -> list[dict[str, Any]]:
    departures_container = data.get("departures") or {}
    departures = departures_container.get("departure") or []

    if isinstance(departures, dict):
        departures = [departures]

    return departures


def extract_destination(departure: dict[str, Any]) -> str | None:
    return to_optional_text_from_mapping(
        departure.get("station"),
        "name",
        "standardname",
        "id",
    )


def extract_platform(departure: dict[str, Any]) -> str | None:
    return to_optional_text_from_mapping(
        departure.get("platform"),
        "name",
        "number",
    )


def extract_vehicle_from_departure(
    departure: dict[str, Any],
) -> dict[str, str | None] | None:
    vehicle_info = departure.get("vehicleinfo")

    if not isinstance(vehicle_info, dict):
        return None

    vehicle_id = vehicle_info.get("name")

    if not vehicle_id:
        return None

    return {
        "id": str(vehicle_id),
        "link": to_optional_str(vehicle_info.get("@id")),
        "short_name": to_optional_str(
            vehicle_info.get("shortname")
        ),
        "vehicle_type": to_optional_str(
            vehicle_info.get("type")
        ),
        "vehicle_number": to_optional_str(
            vehicle_info.get("number")
        ),
    }


def extract_vehicle_class_code(vehicle_type: str | None) -> str | None:
    if not vehicle_type:
        return None

    class_match = re.match(r"[A-Za-z]+", vehicle_type.strip())

    if not class_match:
        return None

    return class_match.group(0).upper()


def upsert_station(cursor: pyodbc.Cursor, station: dict[str, Any]) -> None:
    cursor.execute(
        """
        MERGE dbo.stations AS target
        USING (VALUES (?, ?, ?, ?, ?, ?)) AS source (
            station_id,
            station_name,
            standard_name,
            longitude,
            latitude,
            link
        )
        ON target.station_id = source.station_id
        WHEN MATCHED AND (
            ISNULL(target.station_name, '') <> ISNULL(source.station_name, '')
            OR ISNULL(target.standard_name, '') <> ISNULL(source.standard_name, '')
            OR ISNULL(target.longitude, -999.0) <> ISNULL(source.longitude, -999.0)
            OR ISNULL(target.latitude, -999.0) <> ISNULL(source.latitude, -999.0)
            OR ISNULL(target.link, '') <> ISNULL(source.link, '')
        ) THEN
            UPDATE SET
                station_name = source.station_name,
                standard_name = source.standard_name,
                longitude = source.longitude,
                latitude = source.latitude,
                link = source.link
        WHEN NOT MATCHED THEN
            INSERT (
                station_id,
                station_name,
                standard_name,
                longitude,
                latitude,
                link
            )
            VALUES (
                source.station_id,
                source.station_name,
                source.standard_name,
                source.longitude,
                source.latitude,
                source.link
            );
        """,
        station["station_id"],
        station["station_name"],
        station["standard_name"],
        station["longitude"],
        station["latitude"],
        station["station_link"],
    )


def upsert_vehicle(cursor: pyodbc.Cursor, vehicle: dict[str, str | None]) -> None:
    cursor.execute(
        """
        MERGE dbo.vehicles AS target
        USING (VALUES (?, ?, ?, ?, ?, ?)) AS source (
            id,
            short_name,
            vehicle_type,
            vehicle_class_code,
            vehicle_number,
            link
        )
        ON target.id = source.id
        WHEN MATCHED AND (
            ISNULL(target.short_name, '') <> ISNULL(source.short_name, '')
            OR ISNULL(target.vehicle_type, '') <> ISNULL(source.vehicle_type, '')
            OR ISNULL(target.vehicle_class_code, '') <> ISNULL(source.vehicle_class_code, '')
            OR ISNULL(target.vehicle_number, '') <> ISNULL(source.vehicle_number, '')
            OR ISNULL(target.link, '') <> ISNULL(source.link, '')
        ) THEN
            UPDATE SET
                short_name = source.short_name,
                vehicle_type = source.vehicle_type,
                vehicle_class_code = source.vehicle_class_code,
                vehicle_number = source.vehicle_number,
                link = source.link
        WHEN NOT MATCHED THEN
            INSERT (
                id,
                short_name,
                vehicle_type,
                vehicle_class_code,
                vehicle_number,
                link
            )
            VALUES (
                source.id,
                source.short_name,
                source.vehicle_type,
                source.vehicle_class_code,
                source.vehicle_number,
                source.link
            );
        """,
        vehicle["id"],
        vehicle["short_name"],
        vehicle["vehicle_type"],
        extract_vehicle_class_code(vehicle["vehicle_type"]),
        vehicle["vehicle_number"],
        vehicle["link"],
    )


def upsert_liveboard_record(
    cursor: pyodbc.Cursor,
    station_id: str,
    vehicle_id: str,
    destination: str | None,
    scheduled_departure: datetime | None,
    delay_seconds: int,
    platform: str | None,
    canceled: bool,
) -> None:
    cursor.execute(
        """
        MERGE dbo.liveboard_records AS target
        USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source (
            station_id,
            vehicle_id,
            destination,
            scheduled_departure,
            delay_seconds,
            platform,
            canceled
        )
        ON target.station_id = source.station_id
           AND target.vehicle_id = source.vehicle_id
           AND target.scheduled_departure = source.scheduled_departure
        WHEN MATCHED AND (
            ISNULL(target.destination, '') <> ISNULL(source.destination, '')
            OR ISNULL(target.delay_seconds, -1) <> ISNULL(source.delay_seconds, -1)
            OR ISNULL(target.platform, '') <> ISNULL(source.platform, '')
            OR target.canceled <> source.canceled
        ) THEN
            UPDATE SET
                destination = source.destination,
                delay_seconds = source.delay_seconds,
                platform = source.platform,
                canceled = source.canceled
        WHEN NOT MATCHED THEN
            INSERT (
                station_id,
                vehicle_id,
                destination,
                scheduled_departure,
                delay_seconds,
                platform,
                canceled
            )
            VALUES (
                source.station_id,
                source.vehicle_id,
                source.destination,
                source.scheduled_departure,
                source.delay_seconds,
                source.platform,
                source.canceled
            );
        """,
        station_id,
        vehicle_id,
        destination,
        scheduled_departure,
        delay_seconds,
        platform,
        canceled,
    )


def get_retention_days() -> int:
    raw_value = os.environ.get(
        "LIVEBOARD_RETENTION_DAYS",
        str(DEFAULT_RETENTION_DAYS),
    )

    try:
        retention_days = int(raw_value)
    except ValueError:
        logging.warning(
            "Invalid LIVEBOARD_RETENTION_DAYS=%s. Using default=%s.",
            raw_value,
            DEFAULT_RETENTION_DAYS,
        )
        return DEFAULT_RETENTION_DAYS

    if retention_days < 0:
        logging.warning(
            "LIVEBOARD_RETENTION_DAYS cannot be negative. Using default=%s.",
            DEFAULT_RETENTION_DAYS,
        )
        return DEFAULT_RETENTION_DAYS

    return retention_days


def purge_old_liveboard_records(
    cursor: pyodbc.Cursor,
    retention_days: int,
) -> int:
    if retention_days == 0:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    cursor.execute(
        """
        DELETE FROM dbo.liveboard_records
        WHERE scheduled_departure < ?;
        """,
        cutoff,
    )

    return max(cursor.rowcount, 0)


def save_liveboard_to_sql(data: dict[str, Any]) -> dict[str, int]:
    station = extract_station(data)
    departures = extract_departures(data)

    connection = get_sql_connection()
    cursor = connection.cursor()

    processed_records = 0
    processed_vehicles = 0
    retention_days = get_retention_days()
    records_deleted_by_retention = 0

    try:
        upsert_station(cursor, station)

        for departure in departures:
            vehicle = extract_vehicle_from_departure(departure)

            if not vehicle:
                logging.warning(
                    "Skipping departure because vehicleinfo is missing required data."
                )
                continue

            vehicle_id = vehicle["id"]

            upsert_vehicle(cursor, vehicle)

            processed_vehicles += 1

            scheduled_departure = parse_unix_datetime(
                departure.get("time")
            )

            try:
                delay_seconds = int(departure.get("delay") or 0)
            except (TypeError, ValueError):
                delay_seconds = 0

            canceled_value = departure.get("canceled", "0")
            canceled = str(canceled_value).lower() in {
                "1",
                "true",
                "yes",
            }

            upsert_liveboard_record(
                cursor=cursor,
                station_id=station["station_id"],
                vehicle_id=vehicle_id,
                destination=extract_destination(departure),
                scheduled_departure=scheduled_departure,
                delay_seconds=delay_seconds,
                platform=extract_platform(departure),
                canceled=canceled,
            )

            processed_records += 1

        records_deleted_by_retention = purge_old_liveboard_records(
            cursor,
            retention_days,
        )

        connection.commit()

        return {
            "stations_processed": 1,
            "vehicles_processed": processed_vehicles,
            "records_processed": processed_records,
            "records_deleted_by_retention": records_deleted_by_retention,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def fetch_liveboard(station: str) -> dict[str, Any]:
    """Fetch the current departure liveboard for one station."""
    params = {
        "station": station,
        "format": "json",
        "lang": "en",
        "arrdep": "departure",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "RailPulseChallenge/1.0",
    }

    response = requests.get(
        IRAIL_URL,
        params=params,
        headers=headers,
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("exception"):
        raise RuntimeError(f"iRail returned an exception payload: {data}")

    return data


def collect_station(station: str) -> dict[str, int]:
    """
    Fetch the current liveboard and upsert it into Azure SQL.

    Existing services are updated by the MERGE key
    (station_id, vehicle_id, scheduled_departure), so repeated timer runs
    refresh delay/platform/canceled instead of creating duplicate rows.
    """
    logging.info("Collecting current liveboard for %s.", station)
    data = fetch_liveboard(station)
    departures_count = len(extract_departures(data))
    database_result = save_liveboard_to_sql(data)

    return {
        "api_departures_received": departures_count,
        "records_processed": database_result["records_processed"],
        "vehicles_processed": database_result["vehicles_processed"],
    }


@app.route(
    route="GetLiveboard",
    methods=["GET"],
)
def get_liveboard(req: func.HttpRequest) -> func.HttpResponse:
    """Manual ingestion endpoint for a single station."""
    logging.info("Manual GetLiveboard pipeline started.")
    station = req.params.get("station", DEFAULT_STATION)

    try:
        result = collect_station(station)

        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": True,
                    "station_requested": station,
                    "source": "iRail liveboard",
                    **result,
                },
                ensure_ascii=False,
                default=str,
            ),
            status_code=200,
            mimetype="application/json",
        )

    except requests.exceptions.Timeout:
        logging.exception("iRail request timed out for %s.", station)
        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "station_requested": station,
                    "error": "iRail request timed out.",
                }
            ),
            status_code=504,
            mimetype="application/json",
        )

    except requests.exceptions.RequestException as exc:
        logging.exception("Could not retrieve iRail data for %s.", station)
        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "station_requested": station,
                    "error": "Could not retrieve iRail data.",
                    "details": str(exc),
                }
            ),
            status_code=502,
            mimetype="application/json",
        )

    except pyodbc.Error as exc:
        logging.exception("Azure SQL operation failed.")
        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "station_requested": station,
                    "error": "Azure SQL operation failed.",
                    "details": str(exc),
                }
            ),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as exc:
        logging.exception("Unexpected manual ingestion error.")
        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "station_requested": station,
                    "error": "Unexpected pipeline error.",
                    "details": str(exc),
                }
            ),
            status_code=500,
            mimetype="application/json",
        )


@app.timer_trigger(
    schedule=TIMER_SCHEDULE,
    arg_name="timer",
    run_on_startup=False,
)
def liveboard_timer(timer: func.TimerRequest) -> None:
    """
    Automatically collect the current liveboard every 15 minutes.

    This builds full-day coverage over time using real liveboard observations,
    rather than querying all 24 historical clock hours in one execution.
    """

    enable_update = os.environ.get(
        "ENABLE_DB_UPDATE",
        "false"
    ).lower() == "true"

    if not enable_update:
        logging.info("Database update is DISABLED.")
        return

    if timer.past_due:
        logging.warning("Liveboard timer is running later than scheduled.")

    logging.info(
        "Scheduled liveboard ingestion started for %s station(s).",
        len(COLLECTION_STATIONS),
    )

    total_api_departures = 0
    total_records_processed = 0
    failed_stations: list[str] = []

    for station in COLLECTION_STATIONS:
        try:
            result = collect_station(station)
            total_api_departures += result["api_departures_received"]
            total_records_processed += result["records_processed"]

            logging.info(
                "%s: received %s departures and processed %s database records.",
                station,
                result["api_departures_received"],
                result["records_processed"],
            )

        except Exception:
            failed_stations.append(station)
            logging.exception("Scheduled collection failed for %s.", station)

    logging.info(
        "Scheduled ingestion complete. API departures=%s, records processed=%s, failed stations=%s.",
        total_api_departures,
        total_records_processed,
        failed_stations,
    )
