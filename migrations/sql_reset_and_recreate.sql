IF OBJECT_ID('dbo.liveboard_records', 'U') IS NOT NULL
BEGIN
    DROP TABLE dbo.liveboard_records;
END;
GO

IF OBJECT_ID('dbo.vehicles', 'U') IS NOT NULL
BEGIN
    DROP TABLE dbo.vehicles;
END;
GO

IF OBJECT_ID('dbo.stations', 'U') IS NOT NULL
BEGIN
    DROP TABLE dbo.stations;
END;
GO

-- Recreate tables from scratch.
CREATE TABLE dbo.stations (
    station_id NVARCHAR(100) NOT NULL PRIMARY KEY,
    station_name NVARCHAR(200) NOT NULL,
    standard_name NVARCHAR(200) NULL,
    longitude DECIMAL(10,6) NULL,
    latitude DECIMAL(10,6) NULL,
    link NVARCHAR(255) NULL
);

CREATE TABLE dbo.vehicles (
    id NVARCHAR(100) NOT NULL PRIMARY KEY,
    short_name NVARCHAR(100) NULL,
    vehicle_type NVARCHAR(50) NULL,
    vehicle_class_code NVARCHAR(20) NULL,
    vehicle_number NVARCHAR(50) NULL,
    link NVARCHAR(255) NULL
);

CREATE TABLE dbo.liveboard_records (
    record_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    station_id NVARCHAR(100) NOT NULL,
    vehicle_id NVARCHAR(100) NOT NULL,
    destination NVARCHAR(200) NULL,
    scheduled_departure DATETIME2 NULL,
    delay_seconds INT NOT NULL DEFAULT 0,
    platform NVARCHAR(50) NULL,
    canceled BIT NOT NULL DEFAULT 0,
    CONSTRAINT FK_liveboard_records_stations
        FOREIGN KEY (station_id)
        REFERENCES dbo.stations (station_id),
    CONSTRAINT FK_liveboard_records_vehicles
        FOREIGN KEY (vehicle_id)
        REFERENCES dbo.vehicles (id)
);

CREATE UNIQUE INDEX UX_liveboard_unique_departure
ON dbo.liveboard_records (station_id, vehicle_id, scheduled_departure);

CREATE INDEX IX_liveboard_records_station_departure
ON dbo.liveboard_records (station_id, scheduled_departure);

CREATE INDEX IX_liveboard_records_vehicle_departure
ON dbo.liveboard_records (vehicle_id, scheduled_departure);

CREATE INDEX IX_vehicles_vehicle_class_code
ON dbo.vehicles (vehicle_class_code);
