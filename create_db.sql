-- ============================================================
-- Таблица: Car (Автомобили)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Car" (
    id SERIAL PRIMARY KEY,
    brand_model VARCHAR(100) NOT NULL,
    license_plate VARCHAR(10) NOT NULL UNIQUE,
    status VARCHAR(10) NOT NULL DEFAULT 'free',
    mileage INTEGER NOT NULL DEFAULT 0,
    
    CONSTRAINT chk_car_status CHECK (status IN ('free', 'trip', 'repair')),
    CONSTRAINT chk_car_mileage CHECK (mileage >= 0)
);

-- ============================================================
-- Таблица: Driver (Водители)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Driver" (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    license_number VARCHAR(20) NOT NULL UNIQUE
);

-- ============================================================
-- Таблица: Request (Заявки)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Request" (
    id SERIAL PRIMARY KEY,
    requester_name VARCHAR(100) NOT NULL,
    trip_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'new',
    
    CONSTRAINT chk_request_status CHECK (status IN ('new', 'approved', 'rejected'))
);

-- ============================================================
-- Таблица: Trip (Поездки)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Trip" (
    id SERIAL PRIMARY KEY,
    car_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    request_id INTEGER NULL,
    departure_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    departure_mileage INTEGER NOT NULL,
    return_date TIMESTAMP NULL,
    return_mileage INTEGER NULL,
    
    CONSTRAINT chk_trip_departure_mileage CHECK (departure_mileage >= 0),
    CONSTRAINT chk_trip_return_mileage CHECK (return_mileage >= 0),
    CONSTRAINT chk_trip_mileage_increasing CHECK (
        return_mileage IS NULL OR 
        return_mileage >= departure_mileage
    ),
    
    CONSTRAINT fk_trip_car FOREIGN KEY (car_id) REFERENCES "Car"(id) ON DELETE CASCADE,
    CONSTRAINT fk_trip_driver FOREIGN KEY (driver_id) REFERENCES "Driver"(id) ON DELETE CASCADE,
    CONSTRAINT fk_trip_request FOREIGN KEY (request_id) REFERENCES "Request"(id) ON DELETE SET NULL,
    
    CONSTRAINT uq_trip_request UNIQUE (request_id)
);
