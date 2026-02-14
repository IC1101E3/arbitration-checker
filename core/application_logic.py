
import os
import logging
import csv
import json
import datetime
import sys # Добавлен импорт sys для манипуляции путем импорта

# Импорт компонентов
# Динамическая настройка пути Python для возможности импорта модулей из структуры проекта.
# Этот путь относится к месту расположения этого скрипта (application_logic.py).
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_for_imports = os.path.abspath(os.path.join(current_script_dir, '..'))
if project_root_for_imports not in sys.path:
    sys.path.insert(0, project_root_for_imports)

from scraper.arbitr_scraper import ArbitrScraper
from database.db_manager import DBManager
from utils.logger import setup_logging 

# Настройка логирования для ApplicationLogic с использованием функции setup_logging
logger = setup_logging()

class ApplicationLogic:
    """Класс ApplicationLogic координирует работу GUI, Scraper и DBManager.

    Реализует бизнес-логику: получение ИНН из GUI, передача его скраперу,
    получение данных, сохранение их в БД через DBManager и обновление статуса в GUI.
    Также включает функционал фильтрации и экспорта данных.
    """
    def __init__(self, scraper: ArbitrScraper, db_manager: DBManager, gui_status_updater, gui_results_updater):
        """Инициализирует ApplicationLogic с зависимостями.

        Args:
            scraper (ArbitrScraper): Экземпляр веб-скрапера.
            db_manager (DBManager): Экземпляр менеджера базы данных.
            gui_status_updater (callable): Метод GUI для обновления текстового статуса.
            gui_results_updater (callable): Метод GUI для обновления таблицы QTableWidget.
        """
        self.scraper = scraper
        self.db_manager = db_manager
        self.gui_status_updater = gui_status_updater # Метод GUI для обновления текстового статуса
        self.gui_results_updater = gui_results_updater # Метод GUI для обновления QTableWidget
        logger.info("ApplicationLogic инициализирован.")

    def _update_status(self, message, level=logging.INFO):
        """Вспомогательный метод для обновления текстового статуса GUI и логирования сообщения.

        Args:
            message (str): Сообщение для отображения и логирования.
            level (int, optional): Уровень логирования (e.g., logging.INFO, logging.ERROR). По умолчанию logging.INFO.
        """
        if self.gui_status_updater:
            self.gui_status_updater(message)
        if level == logging.ERROR:
            logger.error(message)
        elif level == logging.WARNING:
            logger.warning(message)
        else:
            logger.info(message)

    def start_scraping(self, inn: str):
        """Координирует скрапинг и сохранение арбитражных дел.

        Args:
            inn (str): ИНН для поиска арбитражных дел.
        """
        self._update_status(f"Запускаю скрапинг для ИНН: {inn}...")

        # 1. Валидация ИНН
        if not inn or not inn.isdigit() or len(inn) not in [10, 12]:
            self._update_status("Ошибка: Неверный ИНН. Пожалуйста, введите корректный ИНН (только цифры, 10 или 12 знаков).", level=logging.ERROR)
            return

        scraped_cases = []
        # 2. Скрапинг дел
        try:
            self._update_status("Начинаю процесс веб-скрапинга...")
            scraped_cases = self.scraper.scrape_arbitr_cases(inn)
            if not scraped_cases:
                self._update_status(f"Скрапинг завершен. Новые дела для ИНН {inn} не найдены или произошла ошибка.")
            else:
                self._update_status(f"Скрапинг завершен. Найдено {len(scraped_cases)} дел для ИНН {inn}.")
        except TimeoutException:
            self._update_status("Ошибка: Сайт недоступен или слишком долго отвечает. Попробуйте еще раз позже.", level=logging.ERROR)
            logger.exception("Таймаут во время скрапинга.")
            return
        except WebDriverException as e:
            self._update_status(f"Ошибка WebDriver: {e}. Возможно, проблема с настройкой Chrome/ChromeDriver или превышено количество запросов.", level=logging.ERROR)
            logger.exception("Ошибка WebDriver во время скрапинга.")
            return
        except Exception as e:
            self._update_status(f"Неожиданная ошибка во время скрапинга: {e}.", level=logging.ERROR)
            logger.exception("Неожиданная ошибка во время скрапинга.")
            return

        # 3. Обновление таблицы результатов GUI
        if self.gui_results_updater:
            self._update_status("Обновляю таблицу результатов GUI...")
            self.gui_results_updater(scraped_cases)

        # 4. Сохранение дел в базу данных
        if scraped_cases:
            self._update_status("Сохраняю полученные дела в базу данных...")
            inserted_count = 0
            try:
                # Сначала убедимся, что таблица существует 
                self.db_manager.create_table()
                for case in scraped_cases:
                    if self.db_manager.insert_case(case['case_number'], case['case_date'], case['inn']):
                        inserted_count += 1
                self._update_status(f"Успешно вставлено {inserted_count} новых дел (пропущены существующие).", level=logging.INFO)
            except OperationalError as e:
                self._update_status(f"Ошибка подключения к базе данных: {e}. Проверьте настройки и запущен ли PostgreSQL.", level=logging.ERROR)
                logger.exception("Ошибка операции с базой данных во время сохранения.")
            except Exception as e:
                self._update_status(f"Ошибка при сохранении дел в базу данных: {e}.", level=logging.ERROR)
                logger.exception("Ошибка сохранения дел в базу данных.")
        else:
            self._update_status(f"Нет новых дел для сохранения для ИНН {inn}.")

        self._update_status("Процесс скрапинга и обновления базы данных завершен.")

    def filter_cases(self, case_number_filter=None, inn_filter=None, start_date=None, end_date=None):
        """Извлекает и отображает отфильтрованные дела в таблице GUI.

        Args:
            case_number_filter (str, optional): Часть или полный номер дела для фильтрации.
            inn_filter (str, optional): Часть или полный ИНН для фильтрации.
            start_date (str, optional): Начальная дата (ГГГГ-ММ-ДД) для фильтрации по дате дела.
            end_date (str, optional): Конечная дата (ГГГГ-ММ-ДД) для фильтрации по дате дела.
        """
        self._update_status("Применяю фильтры и обновляю таблицу...")
        try:
            filtered_cases = self.db_manager.get_filtered_cases_as_dicts(
                case_number_filter, inn_filter, start_date, end_date
            )
            self._update_status(f"Найдено {len(filtered_cases)} дел по заданным фильтрам.")
            if self.gui_results_updater:
                self.gui_results_updater(filtered_cases)
        except Exception as e:
            self._update_status(f"Ошибка при фильтрации дел: {e}.", level=logging.ERROR)
            logger.exception("Ошибка фильтрации дел.")

    def export_data_to_csv(self, file_path: str):
        """Экспортирует все сохраненные дела в файл CSV.

        Args:
            file_path (str): Путь к файлу CSV для сохранения данных.

        Returns:
            bool: True, если экспорт успешен, иначе False.
        """
        self._update_status(f"Экспортирую данные в CSV: {file_path}...")
        try:
            cases = self.db_manager.get_all_cases_as_dicts()
            if not cases:
                self._update_status("Нет данных для экспорта в CSV.", level=logging.WARNING)
                return False

            # Убедитесь, что case_date является строкой для совместимости с CSV
            for case in cases:
                if isinstance(case.get('case_date'), datetime.date):
                    case['case_date'] = case['case_date'].isoformat()

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['case_number', 'case_date', 'inn']
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                writer.writerows(cases)
            self._update_status(f"Данные успешно экспортированы в CSV: {file_path}")
            return True
        except Exception as e:
            self._update_status(f"Ошибка при экспорте в CSV: {e}", level=logging.ERROR)
            logger.exception("Ошибка экспорта в CSV.")
            return False

    def export_data_to_json(self, file_path: str):
        """Экспортирует все сохраненные дела в файл JSON.

        Args:
            file_path (str): Путь к файлу JSON для сохранения данных.

        Returns:
            bool: True, если экспорт успешен, иначе False.
        """
        self._update_status(f"Экспортирую данные в JSON: {file_path}...")
        try:
            cases = self.db_manager.get_all_cases_as_dicts()
            if not cases:
                self._update_status("Нет данных для экспорта в JSON.", level=logging.WARNING)
                return False

            # Убедитесь, что case_date является строкой для сериализации в JSON
            for case in cases:
                if isinstance(case.get('case_date'), datetime.date):
                    case['case_date'] = case['case_date'].isoformat()

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cases, f, ensure_ascii=False, indent=4)
            self._update_status(f"Данные успешно экспортированы в JSON: {file_path}")
            return True
        except Exception as e:
            self._update_status(f"Ошибка при экспорте в JSON: {e}", level=logging.ERROR)
            logger.exception("Ошибка экспорта в JSON.")
            return False

