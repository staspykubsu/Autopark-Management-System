-- Создание базы данных (выполняется отдельно)
-- CREATE DATABASE taxi_fleet_db
--     WITH 
--     OWNER = postgres
--     ENCODING = 'UTF8'
--     CONNECTION LIMIT = -1;

-- ============================================================
-- Таблица: Car (Автомобили)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Car" (
    id SERIAL PRIMARY KEY,
    brand_model VARCHAR(100) NOT NULL,
    license_plate VARCHAR(10) NOT NULL UNIQUE,
    status VARCHAR(10) NOT NULL DEFAULT 'free',
    mileage INTEGER NOT NULL DEFAULT 0,
    
    -- Ограничения целостности
    CONSTRAINT chk_car_status CHECK (status IN ('free', 'trip', 'repair')),
    CONSTRAINT chk_car_mileage CHECK (mileage >= 0)
);

-- Комментарии к таблице и полям
COMMENT ON TABLE "Car" IS 'Автомобили таксопарка';
COMMENT ON COLUMN "Car".id IS 'Уникальный идентификатор автомобиля';
COMMENT ON COLUMN "Car".brand_model IS 'Марка и модель автомобиля';
COMMENT ON COLUMN "Car".license_plate IS 'Государственный номер (уникальный)';
COMMENT ON COLUMN "Car".status IS 'Статус: free-свободна, trip-в рейсе, repair-ремонт';
COMMENT ON COLUMN "Car".mileage IS 'Текущий пробег автомобиля (км)';

-- ============================================================
-- Таблица: Driver (Водители)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Driver" (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    license_number VARCHAR(20) NOT NULL UNIQUE
);

-- Комментарии к таблице и полям
COMMENT ON TABLE "Driver" IS 'Водители таксопарка';
COMMENT ON COLUMN "Driver".id IS 'Уникальный идентификатор водителя';
COMMENT ON COLUMN "Driver".name IS 'ФИО водителя';
COMMENT ON COLUMN "Driver".license_number IS 'Номер водительского удостоверения';

-- ============================================================
-- Таблица: Request (Заявки)
-- ============================================================
CREATE TABLE IF NOT EXISTS "Request" (
    id SERIAL PRIMARY KEY,
    requester_name VARCHAR(100) NOT NULL,
    trip_date DATE NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'new',
    
    -- Ограничения целостности
    CONSTRAINT chk_request_status CHECK (status IN ('new', 'approved', 'rejected'))
);

-- Комментарии к таблице и полям
COMMENT ON TABLE "Request" IS 'Заявки водителей на получение автомобиля';
COMMENT ON COLUMN "Request".id IS 'Уникальный идентификатор заявки';
COMMENT ON COLUMN "Request".requester_name IS 'ФИО заявителя';
COMMENT ON COLUMN "Request".trip_date IS 'Желаемая дата поездки';
COMMENT ON COLUMN "Request".status IS 'Статус: new-новая, approved-одобрена, rejected-отклонена';

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
    
    -- Ограничения целостности
    CONSTRAINT chk_trip_departure_mileage CHECK (departure_mileage >= 0),
    CONSTRAINT chk_trip_return_mileage CHECK (return_mileage >= 0),
    CONSTRAINT chk_trip_mileage_increasing CHECK (
        return_mileage IS NULL OR 
        return_mileage >= departure_mileage
    ),
    
    -- Внешние ключи
    CONSTRAINT fk_trip_car FOREIGN KEY (car_id) REFERENCES "Car"(id) ON DELETE CASCADE,
    CONSTRAINT fk_trip_driver FOREIGN KEY (driver_id) REFERENCES "Driver"(id) ON DELETE CASCADE,
    CONSTRAINT fk_trip_request FOREIGN KEY (request_id) REFERENCES "Request"(id) ON DELETE SET NULL,
    
    -- Уникальность связи с заявкой (одна заявка → одна поездка)
    CONSTRAINT uq_trip_request UNIQUE (request_id)
);

-- Индексы для ускорения поиска
CREATE INDEX idx_trip_car_id ON "Trip"(car_id);
CREATE INDEX idx_trip_driver_id ON "Trip"(driver_id);
CREATE INDEX idx_trip_departure_date ON "Trip"(departure_date);
CREATE INDEX idx_trip_return_date ON "Trip"(return_date);
CREATE INDEX idx_trip_car_departure ON "Trip"(car_id, departure_date);

-- Комментарии к таблице и полям
COMMENT ON TABLE "Trip" IS 'Поездки (смены) водителей';
COMMENT ON COLUMN "Trip".id IS 'Уникальный идентификатор поездки';
COMMENT ON COLUMN "Trip".car_id IS 'Ссылка на автомобиль (внешний ключ)';
COMMENT ON COLUMN "Trip".driver_id IS 'Ссылка на водителя (внешний ключ)';
COMMENT ON COLUMN "Trip".request_id IS 'Ссылка на заявку (опционально)';
COMMENT ON COLUMN "Trip".departure_date IS 'Дата и время выезда';
COMMENT ON COLUMN "Trip".departure_mileage IS 'Показания спидометра при выезде';
COMMENT ON COLUMN "Trip".return_date IS 'Дата и время возврата (NULL - поездка активна)';
COMMENT ON COLUMN "Trip".return_mileage IS 'Показания спидометра при возврате (NULL - поездка активна)';

-- ============================================================
-- Создание представления для активных поездок
-- ============================================================
CREATE OR REPLACE VIEW "ActiveTrips" AS
SELECT 
    t.id,
    c.brand_model AS car_brand_model,
    c.license_plate AS car_license_plate,
    d.name AS driver_name,
    t.departure_date,
    t.departure_mileage
FROM "Trip" t
JOIN "Car" c ON t.car_id = c.id
JOIN "Driver" d ON t.driver_id = d.id
WHERE t.return_date IS NULL;

COMMENT ON VIEW "ActiveTrips" IS 'Активные поездки (без даты возврата)';

-- ============================================================
-- Создание представления для завершенных поездок
-- ============================================================
CREATE OR REPLACE VIEW "CompletedTrips" AS
SELECT 
    t.id,
    c.brand_model AS car_brand_model,
    c.license_plate AS car_license_plate,
    d.name AS driver_name,
    t.departure_date,
    t.departure_mileage,
    t.return_date,
    t.return_mileage,
    (t.return_mileage - t.departure_mileage) AS distance
FROM "Trip" t
JOIN "Car" c ON t.car_id = c.id
JOIN "Driver" d ON t.driver_id = d.id
WHERE t.return_date IS NOT NULL;

COMMENT ON VIEW "CompletedTrips" IS 'Завершенные поездки (с расчетом километража)';

-- ============================================================
-- Функция для автоматического расчета километража
-- ============================================================
CREATE OR REPLACE FUNCTION calculate_trip_distance(
    p_departure_mileage INTEGER,
    p_return_mileage INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_return_mileage IS NULL THEN
        RETURN NULL;
    END IF;
    
    IF p_return_mileage < p_departure_mileage THEN
        RAISE EXCEPTION 'Ошибка: Пробег при возврате (%) не может быть меньше пробега при выезде (%)', 
            p_return_mileage, p_departure_mileage;
    END IF;
    
    RETURN p_return_mileage - p_departure_mileage;
END;
$$;

COMMENT ON FUNCTION calculate_trip_distance IS 'Расчет пройденного километража с проверкой корректности';

-- ============================================================
-- Триггерная функция для обновления пробега автомобиля при завершении поездки
-- ============================================================
CREATE OR REPLACE FUNCTION update_car_mileage_on_trip_complete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Если поездка завершается (заполняется return_date и return_mileage)
    IF NEW.return_date IS NOT NULL AND OLD.return_date IS NULL THEN
        -- Обновляем пробег автомобиля
        UPDATE "Car"
        SET mileage = mileage + (NEW.return_mileage - NEW.departure_mileage)
        WHERE id = NEW.car_id;
        
        -- Меняем статус автомобиля на 'free'
        UPDATE "Car"
        SET status = 'free'
        WHERE id = NEW.car_id;
    END IF;
    
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_update_car_mileage
    AFTER UPDATE OF return_date ON "Trip"
    FOR EACH ROW
    WHEN (NEW.return_date IS NOT NULL AND OLD.return_date IS NULL)
    EXECUTE FUNCTION update_car_mileage_on_trip_complete();

COMMENT ON TRIGGER trg_update_car_mileage ON "Trip" IS 'Триггер автоматического обновления пробега автомобиля при завершении поездки';

-- ============================================================
-- Начальные данные (тестовые)
-- ============================================================

-- Добавление тестовых автомобилей
INSERT INTO "Car" (brand_model, license_plate, status, mileage) VALUES
('Toyota Camry', 'А123ВС', 'free', 150000),
('Hyundai Solaris', 'В456КЕ', 'free', 85000),
('Kia Rio', 'С789МР', 'repair', 120000),
('Renault Logan', 'Е012ТН', 'free', 95000),
('Lada Vesta', 'К345АР', 'free', 45000);

-- Добавление тестовых водителей
INSERT INTO "Driver" (name, license_number) VALUES
('Иванов Иван Иванович', '7712345678'),
('Петров Петр Петрович', '7798765432'),
('Сидоров Сидор Сидорович', '7734567890'),
('Козлова Анна Сергеевна', '7791234567');

-- Добавление тестовых заявок
INSERT INTO "Request" (requester_name, trip_date, status) VALUES
('Иванов И.И.', CURRENT_DATE, 'approved'),
('Петров П.П.', CURRENT_DATE, 'new'),
('Сидоров С.С.', CURRENT_DATE + 1, 'approved'),
('Козлова А.С.', CURRENT_DATE + 2, 'new');

-- Добавление тестовых поездок
INSERT INTO "Trip" (car_id, driver_id, request_id, departure_date, departure_mileage) VALUES
(1, 1, 1, CURRENT_TIMESTAMP, 150000);
