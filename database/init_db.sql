
-- Удаляем таблицу, если она уже существует, чтобы обеспечить чистую повторную инициализацию
DROP TABLE IF EXISTS arbitration_cases CASCADE;

-- Создаем таблицу arbitration_cases
CREATE TABLE arbitration_cases (
    case_number VARCHAR(255) PRIMARY KEY NOT NULL, -- Уникальный идентификатор дела
    case_date DATE,                                -- Дата дела
    inn VARCHAR(12) NOT NULL                       -- ИНН (Идентификационный номер налогоплательщика), по которому было найдено дело
);

-- Добавляем комментарии для лучшей документации
COMMENT ON TABLE arbitration_cases IS 'Таблица для хранения информации об арбитражных делах.';
COMMENT ON COLUMN arbitration_cases.case_number IS 'Уникальный номер арбитражного дела.';
COMMENT ON COLUMN arbitration_cases.case_date IS 'Дата регистрации арбитражного дела.';
COMMENT ON COLUMN arbitration_cases.inn IS 'ИНН (Идентификационный номер налогоплательщика), связанный с арбитражным делом.';

