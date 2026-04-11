CREATE TABLE "Car_Status" (
    id INTEGER PRIMARY KEY,
    status_name VARCHAR(10) NOT NULL UNIQUE
);

INSERT INTO "Car_Status" (id, status_name) VALUES 
(1, 'free'),
(2, 'trip'),
(3, 'repair');

CREATE TABLE "Request_Status" (
    id INTEGER PRIMARY KEY,
    status_name VARCHAR(10) NOT NULL UNIQUE
);

INSERT INTO "Request_Status" (id, status_name) VALUES 
(1, 'new'),
(2, 'approved'),
(3, 'rejected');

CREATE TABLE "Car" (
    id SERIAL PRIMARY KEY,
    brand_model VARCHAR(100) NOT NULL,
    license_plate VARCHAR(10) NOT NULL UNIQUE,
    status_id INTEGER NOT NULL REFERENCES "Car_Status"(id),
    mileage INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT chk_car_mileage CHECK (mileage >= 0)
);

CREATE TABLE "Driver" (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    license_number VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE "Request" (
    id SERIAL PRIMARY KEY,
    requester_name VARCHAR(100) NOT NULL,
    trip_date DATE NOT NULL,
    status_id INTEGER NOT NULL REFERENCES "Request_Status"(id)
);

CREATE TABLE "Trip" (
    id SERIAL PRIMARY KEY,
    car_id INTEGER NOT NULL REFERENCES "Car"(id) ON DELETE CASCADE,
    driver_id INTEGER NOT NULL REFERENCES "Driver"(id) ON DELETE CASCADE,
    request_id INTEGER NOT NULL UNIQUE REFERENCES "Request"(id) ON DELETE RESTRICT,
    departure_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    departure_mileage INTEGER NOT NULL,
    return_date TIMESTAMP NULL,
    return_mileage INTEGER NULL,
    CONSTRAINT chk_trip_departure_mileage CHECK (departure_mileage >= 0),
    CONSTRAINT chk_trip_return_mileage CHECK (return_mileage >= 0),
    CONSTRAINT chk_trip_mileage_increasing CHECK (return_mileage IS NULL OR return_mileage >= departure_mileage)
);
