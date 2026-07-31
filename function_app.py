import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import azure.functions as func
import pyodbc
import requests


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

IRAIL_URL = "https://api.irail.be/liveboard/"

DEFAULT_STATION = "Brussel-Centraal/Bruxelles-Central"


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


def extract_station(data: dict[str, Any]) -> dict[str, Any]:
    station_info = data.get("stationinfo") or {}

    station_id = (
        station_info.get("id")
        or data.get("station")
        or "UNKNOWN_STATION"
    )

    return {
        "station_id": str(station_id),
        "station_name": str(
            station_info.get("name")
            or data.get("station")
            or "Unknown station"
        ),
        "standard_name": station_info.get("standardname"),
        "longitude": station_info.get("locationX"),
        "latitude": station_info.get("locationY"),
    }


def extract_departures(data: dict[str, Any]) -> list[dict[str, Any]]:
    departures_container = data.get("departures") or {}
    departures = departures_container.get("departure") or []

    if isinstance(departures, dict):
        departures = [departures]

    return departures


def save_liveboard_to_sql(data: dict[str, Any]) -> dict[str, int]:
    station = extract_station(data)
    departures = extract_departures(data)

    connection = get_sql_connection()
    cursor = connection.cursor()

    inserted_records = 0
    processed_vehicles = 0

    try:
        # Insert or update station.
        cursor.execute(
            """
            UPDATE dbo.stations
            SET
                station_name = ?,
                standard_name = ?,
                longitude = ?,
                latitude = ?
            WHERE station_id = ?;

            IF @@ROWCOUNT = 0
            BEGIN
                INSERT INTO dbo.stations (
                    station_id,
                    station_name,
                    standard_name,
                    longitude,
                    latitude
                )
                VALUES (?, ?, ?, ?, ?);
            END;
            """,
            station["station_name"],
            station["standard_name"],
            station["longitude"],
            station["latitude"],
            station["station_id"],
            station["station_id"],
            station["station_name"],
            station["standard_name"],
            station["longitude"],
            station["latitude"],
        )

        for departure in departures:
            vehicle_value = departure.get("vehicle")

            if isinstance(vehicle_value, dict):
                vehicle_id = (
                    vehicle_value.get("id")
                    or vehicle_value.get("name")
                )
                vehicle_name = (
                    vehicle_value.get("name")
                    or vehicle_value.get("id")
                )
            else:
                vehicle_id = vehicle_value
                vehicle_name = vehicle_value

            if not vehicle_id:
                logging.warning(
                    "Skipping departure because vehicle ID is missing."
                )
                continue

            vehicle_id = str(vehicle_id)
            vehicle_name = (
                str(vehicle_name)
                if vehicle_name is not None
                else vehicle_id
            )

            # Insert or update vehicle.
            cursor.execute(
                """
                UPDATE dbo.vehicles
                SET vehicle_name = ?
                WHERE vehicle_id = ?;

                IF @@ROWCOUNT = 0
                BEGIN
                    INSERT INTO dbo.vehicles (
                        vehicle_id,
                        vehicle_name
                    )
                    VALUES (?, ?);
                END;
                """,
                vehicle_name,
                vehicle_id,
                vehicle_id,
                vehicle_name,
            )

            processed_vehicles += 1

            destination_value = departure.get("station")

            if isinstance(destination_value, dict):
                destination = (
                    destination_value.get("name")
                    or destination_value.get("standardname")
                    or destination_value.get("id")
                )
            else:
                destination = destination_value

            platform_value = departure.get("platform")

            if isinstance(platform_value, dict):
                platform = (
                    platform_value.get("name")
                    or platform_value.get("number")
                )
            else:
                platform = platform_value

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

            cursor.execute(
                """
                INSERT INTO dbo.liveboard_records (
                    station_id,
                    vehicle_id,
                    destination,
                    scheduled_departure,
                    delay_seconds,
                    platform,
                    canceled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                station["station_id"],
                vehicle_id,
                str(destination) if destination else None,
                scheduled_departure,
                delay_seconds,
                str(platform) if platform else None,
                canceled,
            )

            inserted_records += 1

        connection.commit()

        return {
            "stations_processed": 1,
            "vehicles_processed": processed_vehicles,
            "records_inserted": inserted_records,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


@app.route(
    route="GetLiveboard",
    methods=["GET"],
)
def get_liveboard(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("GetLiveboard pipeline started.")

    station = req.params.get("station", DEFAULT_STATION)

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

    try:
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
            return func.HttpResponse(
                body=json.dumps(
                    {
                        "success": False,
                        "station": station,
                        "error": "iRail returned an internal error.",
                        "irail_response": data,
                    },
                    ensure_ascii=False,
                ),
                status_code=502,
                mimetype="application/json",
            )

        database_result = save_liveboard_to_sql(data)

        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": True,
                    "station_requested": station,
                    "source": "iRail",
                    "database": database_result,
                },
                ensure_ascii=False,
                default=str,
            ),
            status_code=200,
            mimetype="application/json",
        )

    except requests.exceptions.Timeout:
        logging.exception("iRail request timed out.")

        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "error": "iRail request timed out.",
                }
            ),
            status_code=504,
            mimetype="application/json",
        )

    except requests.exceptions.RequestException as exc:
        logging.exception("Could not retrieve iRail data.")

        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
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
                    "error": "Azure SQL operation failed.",
                    "details": str(exc),
                }
            ),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as exc:
        logging.exception("Unexpected pipeline error.")

        return func.HttpResponse(
            body=json.dumps(
                {
                    "success": False,
                    "error": "Unexpected pipeline error.",
                    "details": str(exc),
                }
            ),
            status_code=500,
            mimetype="application/json",
        )