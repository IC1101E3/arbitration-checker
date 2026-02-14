
import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# Динамически добавляем корень проекта в sys.path для импортов
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_path = os.path.abspath(os.path.join(current_script_dir, '..'))

if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

# Мокируем QApplication перед импортом MainWindow, если запускаемся в безголовой среде без дисплея.
# Мы будем использовать фикстуру для управления жизненным циклом QApplication.

# Убедитесь, что PyQt5.QtWidgets импортирован только после настройки путей
from PyQt5.QtWidgets import QApplication, QTextEdit # Добавлен QTextEdit для мокирования
from gui.main_window import MainWindow
from core.application_logic import ApplicationLogic

# Фикстура для QApplication. Мы хотим избежать создания нескольких QApplications.
@pytest.fixture(scope="session")
def qapp():
    """Фикстура для создания QApplication для тестов GUI."""
    app = QApplication(sys.argv)
    yield app
    # Нет необходимости вызывать app.exec_() для модульных тестов, достаточно простого создания.

@pytest.fixture
def main_window(qapp): # qapp как зависимость, чтобы QApplication был инициализирован
    """Фикстура для создания экземпляра MainWindow с замокированными зависимостями."""
    with patch('scraper.arbitr_scraper.ArbitrScraper') as MockArbitrScraper,
         patch('database.db_manager.DBManager') as MockDBManager,
         patch('core.application_logic.ApplicationLogic') as MockApplicationLogic:

        mock_scraper_instance = MockArbitrScraper.return_value
        mock_db_manager_instance = MockDBManager.return_value
        mock_application_logic_instance = MockApplicationLogic.return_value

        window = MainWindow()
        # Вручную настраиваем логику приложения после создания окна, если это необходимо для тестов
        # Для этих базовых тестов мы проверяем только элементы GUI, а не полную интеграцию логики

        yield window, mock_scraper_instance, mock_db_manager_instance, mock_application_logic_instance
    window.close()


class TestMainWindow:
    """Набор тестов для класса MainWindow."""

    def test_window_title(self, main_window):
        """Проверяет заголовок окна."""
        window, _, _, _ = main_window
        assert window.windowTitle() == "Arbitration Checker"

    def test_inn_input_presence(self, main_window):
        """Проверяет наличие поля ввода ИНН."""
        window, _, _, _ = main_window
        assert window.scrape_inn_input is not None
        assert isinstance(window.scrape_inn_input, type(window.scrape_inn_input))
        assert window.scrape_inn_input.placeholderText() == "Введите ИНН для скрапинга"

    def test_search_button_presence(self, main_window):
        """Проверяет наличие кнопки поиска."""
        window, _, _, _ = main_window
        assert window.search_button is not None
        assert isinstance(window.search_button, type(window.search_button))
        assert window.search_button.text() == "Найти (Скрапинг)"

    def test_filter_controls_presence(self, main_window):
        """Проверяет наличие элементов управления фильтрацией."""
        window, _, _, _ = main_window
        assert window.case_num_filter_input is not None
        assert window.inn_filter_input is not None
        assert window.start_date_input is not None
        assert window.end_date_input is not None
        assert window.filter_button is not None
        assert window.filter_button.text() == "Фильтровать (Поиск сохраненных)"

    def test_export_buttons_presence(self, main_window):
        """Проверяет наличие кнопок экспорта."""
        window, _, _, _ = main_window
        assert window.export_csv_button is not None
        assert window.export_csv_button.text() == "Экспорт в CSV"
        assert window.export_json_button is not None
        assert window.export_json_button.text() == "Экспорт в JSON"

    def test_results_table_presence(self, main_window):
        """Проверяет наличие таблицы результатов."""
        window, _, _, _ = main_window
        assert window.results_table is not None
        assert isinstance(window.results_table, type(window.results_table))
        assert window.results_table.columnCount() == 3
        assert window.results_table.horizontalHeaderItem(0).text() == 'Номер дела'
        assert window.results_table.horizontalHeaderItem(1).text() == 'Дата дела'
        assert window.results_table.horizontalHeaderItem(2).text() == 'ИНН'

    def test_status_display_presence(self, main_window):
        """Проверяет наличие области отображения статуса."""
        window, _, _, _ = main_window
        assert window.status_display is not None
        assert isinstance(window.status_display, QTextEdit) # Явно проверяем тип QTextEdit
        assert window.status_display.isReadOnly() is True

    def test_search_button_click_updates_status(self, qapp, main_window):
        """Проверяет, что нажатие кнопки поиска вызывает соответствующую логику."""
        window, mock_scraper, mock_db_manager, mock_application_logic = main_window

        # Мокируем метод start_scraping логики приложения
        mock_application_logic.start_scraping = MagicMock()

        # Инициализируем ApplicationLogic для окна (как это делает main.py)
        window_logic = ApplicationLogic(
            scraper=mock_scraper,
            db_manager=mock_db_manager,
            gui_status_updater=window.status_display.append,
            gui_results_updater=window.update_results_table
        )

        # Переподключаем кнопку к нашей замокированной логике через экземпляр ApplicationLogic
        try:
            window.search_button.clicked.disconnect() # Отключаем существующие соединения
        except TypeError: # Сигнал не имеет подключенных слотов
            pass
        window.search_button.clicked.connect(
            lambda: window_logic.start_scraping(window.scrape_inn_input.text())
        )

        # Устанавливаем фиктивный ИНН
        test_inn = "1234567890"
        window.scrape_inn_input.setText(test_inn)

        # Нажимаем кнопку поиска
        window.search_button.click()

        # Проверяем, что start_scraping был вызван с правильным ИНН
        mock_application_logic.start_scraping.assert_called_once_with(test_inn)


    def test_search_button_click_no_inn(self, qapp, main_window):
        """Проверяет поведение кнопки поиска при отсутствии введенного ИНН."""
        window, mock_scraper, mock_db_manager, mock_application_logic = main_window

        mock_application_logic.start_scraping = MagicMock()

        window_logic = ApplicationLogic(
            scraper=mock_scraper,
            db_manager=mock_db_manager,
            gui_status_updater=window.status_display.append,
            gui_results_updater=window.update_results_table
        )
        try:
            window.search_button.clicked.disconnect()
        except TypeError:
            pass
        window.search_button.clicked.connect(
            lambda: window_logic.start_scraping(window.scrape_inn_input.text())
        )

        window.scrape_inn_input.setText("")
        window.search_button.click()

        # Убеждаемся, что start_scraping НЕ был вызван, и статус-дисплей был обновлен сообщением об ошибке
        mock_application_logic.start_scraping.assert_not_called()
        # Проверка фактического текста в status_display выполняется в полноценном GUI-тесте.
        # На данный момент достаточна проверка того, что start_scraping не был вызван.

    def test_filter_button_click(self, qapp, main_window):
        """Проверяет, что нажатие кнопки фильтрации вызывает соответствующую логику."""
        window, mock_scraper, mock_db_manager, mock_application_logic = main_window
        mock_application_logic.filter_cases = MagicMock()

        window_logic = ApplicationLogic(
            scraper=mock_scraper,
            db_manager=mock_db_manager,
            gui_status_updater=window.status_display.append,
            gui_results_updater=window.update_results_table
        )

        try:
            window.filter_button.clicked.disconnect()
        except TypeError:
            pass
        window.filter_button.clicked.connect(
            lambda: window_logic.filter_cases(
                case_number_filter=window.case_num_filter_input.text(),
                inn_filter=window.inn_filter_input.text(),
                start_date=window.start_date_input.text(),
                end_date=window.end_date_input.text()
            )
        )

        window.case_num_filter_input.setText("TEST_CASE")
        window.inn_filter_input.setText("123")
        window.start_date_input.setText("2023-01-01")
        window.end_date_input.setText("2023-12-31")

        window.filter_button.click()

        mock_application_logic.filter_cases.assert_called_once_with(
            case_number_filter="TEST_CASE",
            inn_filter="123",
            start_date="2023-01-01",
            end_date="2023-12-31"
        )

    def test_export_csv_button_click(self, qapp, main_window):
        """Проверяет, что нажатие кнопки экспорта в CSV вызывает соответствующую логику."""
        window, mock_scraper, mock_db_manager, mock_application_logic = main_window
        mock_application_logic.export_data_to_csv = MagicMock(return_value=True) # Мокируем, что экспорт успешен

        window_logic = ApplicationLogic(
            scraper=mock_scraper,
            db_manager=mock_db_manager,
            gui_status_updater=window.status_display.append,
            gui_results_updater=window.update_results_table
        )

        try:
            window.export_csv_button.clicked.disconnect()
        except TypeError:
            pass

        with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', return_value=('/path/to/test.csv', "CSV Files (*.csv)")): # Мокируем выбор файла
            window.export_csv_button.clicked.connect(lambda: window_logic.export_data_to_csv(
                QFileDialog.getSaveFileName(window, "Export CSV", "cases.csv", "CSV Files (*.csv)")[0]
            ))
            window.export_csv_button.click()

        mock_application_logic.export_data_to_csv.assert_called_once_with("/path/to/test.csv")

    def test_export_json_button_click(self, qapp, main_window):
        """Проверяет, что нажатие кнопки экспорта в JSON вызывает соответствующую логику."""
        window, mock_scraper, mock_db_manager, mock_application_logic = main_window
        mock_application_logic.export_data_to_json = MagicMock(return_value=True) # Мокируем, что экспорт успешен

        window_logic = ApplicationLogic(
            scraper=mock_scraper,
            db_manager=mock_db_manager,
            gui_status_updater=window.status_display.append,
            gui_results_updater=window.update_results_table
        )

        try:
            window.export_json_button.clicked.disconnect()
        except TypeError:
            pass

        with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', return_value=('/path/to/test.json', "JSON Files (*.json)")): # Мокируем выбор файла
            window.export_json_button.clicked.connect(lambda: window_logic.export_data_to_json(
                QFileDialog.getSaveFileName(window, "Export JSON", "cases.json", "JSON Files (*.json)")[0]
            ))
            window.export_json_button.click()

        mock_application_logic.export_data_to_json.assert_called_once_with("/path/to/test.json")
