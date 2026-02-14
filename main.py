
import os
import sys
import configparser

# Корректировка пути Python для возможности импорта модулей из структуры проекта.
# project_root_path - это абсолютный путь к каталогу arbitration_checker.
project_root_path = os.path.dirname(os.path.abspath(__file__))

# Убеждаемся, что родительский каталог project_root_path находится в sys.path.
# Это позволяет корректно импортировать модули, такие как 'gui.main_window',
# когда main.py запускается из директории, находящейся выше его собственной.
parent_of_project_root = os.path.abspath(os.path.join(project_root_path, '..'))
if parent_of_project_root not in sys.path:
    sys.path.insert(0, parent_of_project_root)

# Также убеждаемся, что сам project_root_path находится в sys.path.
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

from gui.main_window import MainWindow
from scraper.arbitr_scraper import ArbitrScraper
from database.db_manager import DBManager
from core.application_logic import ApplicationLogic

from PyQt5.QtWidgets import QApplication, QFileDialog

# Определяем путь к файлу settings.ini относительно корня проекта
settings_path = os.path.join(project_root_path, 'settings.ini')

def main_app():
    """Главная функция приложения Arbitration Checker.

    Инициализирует все компоненты приложения (базу данных, скрапер, GUI, логику),
    подключает их друг к другу и запускает основной цикл событий GUI.
    """
    # Инициализируем ConfigParser. Хотя компоненты могут загружать свою собственную конфигурацию,
    # явная передача обеспечивает согласованность.
    config = configparser.ConfigParser()
    config.read(settings_path)

    # 1. Инициализация DBManager и обеспечение существования таблицы
    db_manager = DBManager(config_path=settings_path)
    print("Инициализация таблицы базы данных...")
    # Путь к init_db.sql относительно корня проекта
    sql_script_path = os.path.join(project_root_path, 'database', 'init_db.sql')
    db_manager.create_table(sql_script_path=sql_script_path)
    print("Инициализация таблицы базы данных завершена.")

    # 2. Инициализация ArbitrScraper
    scraper = ArbitrScraper(config_path=settings_path)
    print("ArbitrScraper инициализирован.")

    # 3. Инициализация QApplication и MainWindow
    app = QApplication(sys.argv)
    main_window = MainWindow()
    print("MainWindow инициализировано.")

    # 4. Инициализация ApplicationLogic
    # Передаем методы из main_window для обновления его статусного дисплея и таблицы результатов
    application_logic = ApplicationLogic(
        scraper=scraper,
        db_manager=db_manager,
        gui_status_updater=main_window.status_display.append,
        gui_results_updater=main_window.update_results_table
    )
    print("ApplicationLogic инициализировано.")

    # 5. Подключение элементов GUI к логике приложения
    main_window.search_button.clicked.connect(
        lambda: application_logic.start_scraping(main_window.scrape_inn_input.text())
    )
    print("Кнопка поиска GUI подключена к логике скрапинга.")

    # Подключение кнопки фильтрации к логике приложения
    main_window.filter_button.clicked.connect(
        lambda: application_logic.filter_cases(
            case_number_filter=main_window.case_num_filter_input.text(),
            inn_filter=main_window.inn_filter_input.text(),
            start_date=main_window.start_date_input.text(),
            end_date=main_window.end_date_input.text()
        )
    )
    print("Кнопка фильтрации GUI подключена к логике фильтрации.")

    # Подключение кнопок экспорта к логике приложения
    def export_csv_action():
        """Действие по экспорту данных в CSV-файл."""
        file_path, _ = QFileDialog.getSaveFileName(main_window, "Экспорт CSV", "cases.csv", "CSV Files (*.csv)")
        if file_path:
            application_logic.export_data_to_csv(file_path)

    def export_json_action():
        """Действие по экспорту данных в JSON-файл."""
        file_path, _ = QFileDialog.getSaveFileName(main_window, "Экспорт JSON", "cases.json", "JSON Files (*.json)")
        if file_path:
            application_logic.export_data_to_json(file_path)

    main_window.export_csv_button.clicked.connect(export_csv_action)
    main_window.export_json_button.clicked.connect(export_json_action)
    print("Кнопки экспорта GUI подключены к логике экспорта.")

    # Отображаем главное окно и запускаем цикл обработки событий приложения
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main_app()
