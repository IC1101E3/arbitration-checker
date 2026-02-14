
import psycopg2
from psycopg2 import OperationalError, Error
import configparser
import os
import logging
import datetime 
from utils.logger import setup_logging 

# Настройка логирования для DBManager
logger = setup_logging()

class DBManager:
    """Класс для управления базой данных PostgreSQL.

    Отвечает за установление соединения с PostgreSQL, выполнение операций CRUD
    (Create, Read, Update, Delete) с данными арбитражных дел.
    """
    def __init__(self, config_path=None):
        """Инициализирует менеджер базы данных.

        Args:
            config_path (str, optional): Путь к файлу конфигурации settings.ini.
                                         Если не указан, используется путь по умолчанию.
        """
        self.config = configparser.ConfigParser()
        if config_path:
            self.config.read(config_path)
        else:
            # Путь по умолчанию относительно корня проекта для settings.ini
            default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.ini')
            self.config.read(default_config_path)

        self.db_host = self.config.get('DATABASE', 'host', fallback='localhost')
        self.db_port = self.config.get('DATABASE', 'port', fallback='5432')
        self.db_name = self.config.get('DATABASE', 'dbname', fallback='arbitration_db')
        self.db_user = self.config.get('DATABASE', 'user', fallback='postgres')
        self.db_password = self.config.get('DATABASE', 'password', fallback='')
        logger.info("DBManager инициализирован.")

    def _get_connection(self):
        """Устанавливает и возвращает соединение с базой данных PostgreSQL.

        Returns:
            psycopg2.connection or None: Объект соединения, если успешно,
                                         иначе None.
        """
        connection = None
        try:
            connection = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            logger.info("Соединение с БД PostgreSQL успешно установлено.")
            return connection
        except OperationalError as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            logger.error("Не удалось подключиться к базе данных. Проверьте settings.ini и убедитесь, что PostgreSQL запущен.")
            return None

    def create_table(self, sql_script_path=None):
        """Создает таблицу arbitration_cases на основе SQL-скрипта.

        Args:
            sql_script_path (str, optional): Путь к SQL-скрипту для создания таблицы.
                                             Если не указан, используется путь по умолчанию.

        Returns:
            bool: True, если таблица создана/обновлена успешно, иначе False.
        """
        if not sql_script_path:
            # Путь по умолчанию относительно db_manager.py для init_db.sql
            sql_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'init_db.sql')

        if not os.path.exists(sql_script_path):
            logger.error(f"Ошибка: SQL-скрипт не найден по пути: {sql_script_path}")
            return False

        conn = None
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                with open(sql_script_path, 'r', encoding='utf-8') as f:
                    sql_commands = f.read()
                cursor.execute(sql_commands)
                conn.commit()
                logger.info(f"Таблица(ы) создана/обновлена с использованием {sql_script_path}")
                return True
        except OperationalError as e:
            logger.error(f"Операционная ошибка при выполнении SQL-скрипта: {e}")
        except Error as e:
            logger.error(f"Ошибка базы данных во время создания таблицы: {e}")
        finally:
            if conn:
                conn.close()
        return False

    def insert_case(self, case_number, case_date, inn):
        """Вставляет новое арбитражное дело в базу данных, обрабатывая дубликаты.

        Args:
            case_number (str): Уникальный номер дела.
            case_date (str): Дата дела (в формате 'YYYY-MM-DD').
            inn (str): ИНН, связанный с делом.

        Returns:
            bool: True, если дело вставлено или пропущено как дубликат, иначе False.
        """
        conn = None
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                # Использование ON CONFLICT DO NOTHING для корректной обработки дубликатов case_number
                insert_query = """
                    INSERT INTO arbitration_cases (case_number, case_date, inn)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (case_number) DO NOTHING;
                """
                cursor.execute(insert_query, (case_number, case_date, inn))
                conn.commit()
                if cursor.rowcount == 0:
                    logger.info(f"Дело {case_number} уже существует, вставка пропущена.")
                else:
                    logger.info(f"Дело {case_number} успешно вставлено.")
                return True
        except OperationalError as e:
            logger.error(f"Операционная ошибка при вставке дела {case_number}: {e}")
        except Error as e:
            logger.error(f"Ошибка базы данных во время вставки дела: {e}")
        finally:
            if conn:
                conn.close()
        return False

    def case_exists(self, case_number):
        """Проверяет, существует ли арбитражное дело с заданным номером.

        Args:
            case_number (str): Номер дела для проверки.

        Returns:
            bool: True, если дело существует, иначе False.
        """
        conn = None
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                select_query = "SELECT 1 FROM arbitration_cases WHERE case_number = %s;"
                cursor.execute(select_query, (case_number,))
                return cursor.fetchone() is not None
        except OperationalError as e:
            logger.error(f"Операционная ошибка при проверке существования дела {case_number}: {e}")
        except Error as e:
            logger.error(f"Ошибка базы данных во время проверки существования дела: {e}")
        finally:
            if conn:
                conn.close()
        return False

    def get_all_cases(self):
        """Извлекает все арбитражные дела из базы данных.

        Returns:
            list: Список кортежей, каждый из которых представляет арбитражное дело.
        """
        conn = None
        cases = []
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT case_number, case_date, inn FROM arbitration_cases;")
                cases = cursor.fetchall()
                logger.info(f"Извлечено {len(cases)} дел.")
        except OperationalError as e:
            logger.error(f"Операционная ошибка при извлечении всех дел: {e}")
        except Error as e:
            logger.error(f"Ошибка базы данных во время извлечения всех дел: {e}")
        finally:
            if conn:
                conn.close()
        return cases

    def get_all_cases_as_dicts(self):
        """Извлекает все арбитражные дела из базы данных в виде списка словарей.

        Returns:
            list: Список словарей, каждый из которых представляет арбитражное дело.
        """
        conn = None
        cases_dicts = []
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT case_number, case_date, inn FROM arbitration_cases;")
                columns = [col[0] for col in cursor.description] # Получить имена столбцов
                for row in cursor.fetchall():
                    # Преобразовать объект даты в строку для последующей JSON-сериализации
                    row_list = list(row)
                    if isinstance(row_list[1], (datetime.date, datetime.datetime)):
                        row_list[1] = row_list[1].isoformat()
                    cases_dicts.append(dict(zip(columns, row_list)))
                logger.info(f"Извлечено {len(cases_dicts)} дел в виде словарей.")
        except OperationalError as e:
            logger.error(f"Операционная ошибка при извлечении всех дел в виде словарей: {e}")
        except Error as e:
            logger.error(f"Ошибка базы данных во время извлечения всех дел в виде словарей: {e}")
        finally:
            if conn:
                conn.close()
        return cases_dicts

    def get_filtered_cases_as_dicts(self, case_number_filter=None, inn_filter=None, start_date=None, end_date=None):
        """Извлекает арбитражные дела из базы данных в виде списка словарей с опциями фильтрации.

        Args:
            case_number_filter (str, optional): Часть или полный номер дела для фильтрации.
            inn_filter (str, optional): Часть или полный ИНН для фильтрации.
            start_date (str, optional): Начальная дата (ГГГГ-ММ-ДД) для фильтрации по дате дела.
            end_date (str, optional): Конечная дата (ГГГГ-ММ-ДД) для фильтрации по дате дела.

        Returns:
            list: Список словарей, каждый из которых представляет арбитражное дело.
        """
        conn = None
        cases_dicts = []
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor()
                sql_query = "SELECT case_number, case_date, inn FROM arbitration_cases WHERE 1=1"
                params = []

                if case_number_filter:
                    sql_query += " AND case_number ILIKE %s"
                    params.append(f"%{case_number_filter}%")
                if inn_filter:
                    sql_query += " AND inn ILIKE %s"
                    params.append(f"%{inn_filter}%")
                if start_date:
                    sql_query += " AND case_date >= %s"
                    params.append(start_date)
                if end_date:
                    sql_query += " AND case_date <= %s"
                    params.append(end_date)

                cursor.execute(sql_query, tuple(params))
                columns = [col[0] for col in cursor.description] # Получить имена столбцов
                for row in cursor.fetchall():
                    row_list = list(row)
                    if isinstance(row_list[1], (datetime.date, datetime.datetime)):
                        row_list[1] = row_list[1].isoformat()
                    cases_dicts.append(dict(zip(columns, row_list)))
                logger.info(f"Извлечено {len(cases_dicts)} отфильтрованных дел.")
        except OperationalError as e:
            logger.error(f"Операционная ошибка при извлечении отфильтрованных дел: {e}")
        except Error as e:
            logger.error(f"Ошибка базы данных во время извлечения отфильтрованных дел: {e}")
        finally:
            if conn:
                conn.close()
        return cases_dicts

if __name__ == '__main__':
    # Этот блок предназначен для непосредственного тестирования функциональности DBManager.
    # Он будет выполнен только в случае, если db_manager.py запущен как скрипт.

    logger.info("--- Тестирование DBManager (вероятно, завершится неудачей без запущенной БД PostgreSQL) ---")
    # Настройте config_path, если требуется прямое выполнение из произвольного места.
    # Предполагается, что settings.ini находится по адресу arbitration_checker/settings.ini,
    # а db_manager.py находится по адресу arbitration_checker/database/db_manager.py.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '.'))
    test_config_path = os.path.join(project_root, 'settings.ini')
    test_sql_script_path = os.path.join(script_dir, 'database', 'init_db.sql')

    db_manager = DBManager(config_path=test_config_path)

    # 1. Создать таблицу
    logger.info("Попытка создания таблицы...")
    db_manager.create_table(sql_script_path=test_sql_script_path)

    # 2. Вставить дела
    logger.info("Попытка вставки дел...")
    db_manager.insert_case('CASE-001', '2023-01-15', '1234567890')
    db_manager.insert_case('CASE-002', '2023-01-16', '0987654321')
    db_manager.insert_case('CASE-001', '2023-01-15', '1234567890') # Дубликат

    # 3. Проверить существование дела
    logger.info(f"Проверка существования CASE-001: {db_manager.case_exists('CASE-001')}")
    logger.info(f"Проверка существования NON-EXISTENT-CASE: {db_manager.case_exists('NON-EXISTENT-CASE')}")

    # 4. Получить все дела
    logger.info("Извлечение всех дел:")
    all_cases = db_manager.get_all_cases()
    for case in all_cases:
        logger.info(case)
