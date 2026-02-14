
import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import configparser
import psycopg2

# Корректировка пути Python для возможности импорта модулей из структуры проекта.
# Предполагается, что каталог tests находится по адресу arbitration_checker/tests.
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

from database.db_manager import DBManager

# Мокируем psycopg2.connect, чтобы избежать реального подключения к базе данных
@pytest.fixture
def mock_psycopg2_connect():
    """Фикстура для мокирования psycopg2.connect и его зависимостей."""
    with patch('psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        yield mock_connect, mock_conn, mock_cursor

@pytest.fixture
def db_manager_instance():
    """Фикстура для создания экземпляра DBManager с фиктивным файлом настроек."""
    # Создать фиктивный settings.ini для целей тестирования
    test_settings_dir = os.path.join(project_root_path, 'core')
    os.makedirs(test_settings_dir, exist_ok=True)
    test_settings_path = os.path.join(test_settings_dir, 'test_settings.ini')
    with open(test_settings_path, 'w') as f:
        f.write("""
[DATABASE]
host = test_host
port = 5432
dbname = test_db
user = test_user
password = test_password
""")

    manager = DBManager(config_path=test_settings_path)
    yield manager
    # Очистить фиктивный settings.ini
    os.remove(test_settings_path)
    os.rmdir(test_settings_dir) # Удаляем каталог, если он пуст


@pytest.fixture
def mock_sql_script_path():
    """Фикстура для создания фиктивного SQL-скрипта."""
    # Создать фиктивный SQL-скрипт для целей тестирования
    dummy_sql_dir = os.path.join(project_root_path, 'database')
    os.makedirs(dummy_sql_dir, exist_ok=True)
    path = os.path.join(dummy_sql_dir, 'test_init_db.sql')
    with open(path, 'w') as f:
        f.write("CREATE TABLE test_table (id INT);")
    yield path
    os.remove(path)
    os.rmdir(dummy_sql_dir) # Удаляем каталог, если он пуст

class TestDBManager:
    """Набор тестов для класса DBManager."""

    def test_get_connection_success(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет успешное получение соединения с базой данных."""
        mock_connect, mock_conn, _ = mock_psycopg2_connect
        conn = db_manager_instance._get_connection()
        assert conn == mock_conn
        mock_connect.assert_called_once_with(
            host='test_host', port='5432', database='test_db', user='test_user', password='test_password'
        )

    def test_get_connection_failure(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет случай, когда получение соединения с базой данных завершается неудачей."""
        mock_connect, _, _ = mock_psycopg2_connect
        mock_connect.side_effect = psycopg2.OperationalError("Ошибка соединения")
        conn = db_manager_instance._get_connection()
        assert conn is None

    def test_create_table(self, mock_psycopg2_connect, db_manager_instance, mock_sql_script_path):
        """Проверяет создание таблицы с использованием SQL-скрипта."""
        _, mock_conn, mock_cursor = mock_psycopg2_connect
        result = db_manager_instance.create_table(sql_script_path=mock_sql_script_path)
        assert result is True
        mock_cursor.execute.assert_called_once_with("CREATE TABLE test_table (id INT);")
        mock_conn.commit.assert_called_once()

    def test_insert_case_new(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет вставку нового дела в базу данных."""
        _, mock_conn, mock_cursor = mock_psycopg2_connect
        mock_cursor.rowcount = 1 # Симулируем новую вставку
        result = db_manager_instance.insert_case('CASE-001', '2023-01-15', '1234567890')
        assert result is True
        insert_query = """
                    INSERT INTO arbitration_cases (case_number, case_date, inn)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (case_number) DO NOTHING;
                """.strip().replace('                    ', '') # Нормализация пробелов для сравнения
        mock_cursor.execute.assert_called_once_with(insert_query, ('CASE-001', '2023-01-15', '1234567890'))
        mock_conn.commit.assert_called_once()

    def test_insert_case_duplicate(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет, что дубликат дела не вставляется."""
        _, mock_conn, mock_cursor = mock_psycopg2_connect
        mock_cursor.rowcount = 0 # Симулируем отсутствие вставки из-за конфликта
        result = db_manager_instance.insert_case('CASE-001', '2023-01-15', '1234567890')
        assert result is True # Метод возвращает True, даже если пропущен из-за корректной обработки
        mock_conn.commit.assert_called_once()

    def test_case_exists_true(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет, что case_exists возвращает True, если дело существует."""
        _, _, mock_cursor = mock_psycopg2_connect
        mock_cursor.fetchone.return_value = (1,) # Симулируем найденное дело
        result = db_manager_instance.case_exists('CASE-001')
        assert result is True
        mock_cursor.execute.assert_called_once_with("SELECT 1 FROM arbitration_cases WHERE case_number = %s;", ('CASE-001',))

    def test_case_exists_false(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет, что case_exists возвращает False, если дело не существует."""
        _, _, mock_cursor = mock_psycopg2_connect
        mock_cursor.fetchone.return_value = None # Симулируем ненайденное дело
        result = db_manager_instance.case_exists('NON-EXISTENT-CASE')
        assert result is False

    def test_get_all_cases(self, mock_psycopg2_connect, db_manager_instance):
        """Проверяет получение всех дел из базы данных."""
        _, _, mock_cursor = mock_psycopg2_connect
        mock_cursor.fetchall.return_value = [('CASE-001', '2023-01-15', '1234567890'), ('CASE-002', '2023-01-16', '0987654321')]
        cases = db_manager_instance.get_all_cases()
        assert len(cases) == 2
        assert cases[0] == ('CASE-001', '2023-01-15', '1234567890')
        mock_cursor.execute.assert_called_once_with("SELECT case_number, case_date, inn FROM arbitration_cases;")

