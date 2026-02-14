
import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import configparser

# Корректировка пути Python для возможности импорта модулей из структуры проекта.
# Предполагается, что каталог тестов находится по адресу arbitration_checker/tests.
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

from scraper.arbitr_scraper import ArbitrScraper
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def mock_webdriver_components():
    """Фикстура для мокирования компонентов WebDriver Selenium.

    Мокирует `selenium.webdriver.Chrome`
    и возвращает фиктивный объект драйвера.
    """
    with patch('selenium.webdriver.Chrome') as mock_chrome:
        with patch('webdriver_manager.chrome.ChromeDriverManager.install') as mock_install:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_install.return_value = '/mock/path/to/chromedriver'
            yield mock_chrome, mock_install, mock_driver

@pytest.fixture
def scraper_instance():
    """Фикстура для создания экземпляра ArbitrScraper с фиктивным файлом настроек.

    Создает временный `settings.ini` для изоляции тестов.
    """
    # Создаем фиктивный settings.ini для целей тестирования
    test_settings_dir = os.path.join(project_root_path, '..')
    os.makedirs(test_settings_dir, exist_ok=True)
    test_settings_path = os.path.join(test_settings_dir, 'test_settings.ini')
    with open(test_settings_path, 'w') as f:
        f.write("""[SELENIUM]webdriver_path = /mock/path/to/chromedriver""")

    scraper = ArbitrScraper(config_path=test_settings_path)
    yield scraper
    # Удаляем фиктивный settings.ini
    os.remove(test_settings_path)
    os.rmdir(test_settings_dir) # Удаляем каталог, если он пуст

class TestArbitrScraper:
    """Набор тестов для класса ArbitrScraper."""

    def test_initialize_webdriver_success(self, mock_webdriver_components, scraper_instance):
        """Тестирует успешную инициализацию WebDriver."""
        mock_chrome, mock_install, mock_driver = mock_webdriver_components
        scraper_instance._initialize_webdriver()
        mock_install.assert_called_once() # Проверяем, что install был вызван
        # Проверяем, что Chrome был вызван с экземпляром Options.
        # Используем mock.ANY для соответствия любому экземпляру Options.
        mock_chrome.assert_called_once_with(options=MagicMock(spec=Options))
        assert scraper_instance.driver == mock_driver

    def test_initialize_webdriver_failure(self, mock_webdriver_components, scraper_instance):
        """Тестирует неудачную инициализацию WebDriver."""
        mock_chrome, mock_install, _ = mock_webdriver_components
        mock_install.side_effect = Exception("Install error") # Симулируем ошибку установки
        scraper_instance._initialize_webdriver()
        assert scraper_instance.driver is None # Драйвер должен быть None при ошибке

    def test_scrape_arbitr_cases_success(self, mock_webdriver_components, scraper_instance):
        """Тестирует успешное скрапинг арбитражных дел."""
        mock_chrome, _, mock_driver = mock_webdriver_components

        # Симулируем успешную инициализацию веб-драйвера внутри scrape_arbitr_cases
        scraper_instance.driver = mock_driver

        # Мокируем элементы WebDriver и их поведение
        mock_inn_input = MagicMock()
        mock_inn_input.send_keys.return_value = None
        mock_search_button = MagicMock()
        mock_search_button.click.return_value = None

        # Мокируем WebDriverWait и EC (Expected Conditions)
        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait,              patch('selenium.webdriver.support.expected_conditions') as mock_ec:
            mock_wait.return_value.until.side_effect = [
                mock_inn_input,      # для EC.presence_of_element_located поля ввода ИНН
                mock_search_button,  # для EC.element_to_be_clickable кнопки поиска
                None                 # для EC.presence_of_element_located блока результатов
            ]

            # Симулируем строку результата
            mock_row1 = MagicMock()
            mock_row1.find_element.side_effect = [
                MagicMock(text='A123-45/2023'), # элемент номера дела
                MagicMock(text='01.01.2023')   # элемент даты дела
            ]

            mock_driver.find_elements.return_value = [mock_row1] # Возвращаем одну мокированную строку

            cases = scraper_instance.scrape_arbitr_cases("1234567890", max_results=1)

            assert len(cases) == 1
            assert cases[0]['case_number'] == 'A123-45/2023'
            assert cases[0]['case_date'] == '2023-01-01'
            assert cases[0]['inn'] == '1234567890'
            mock_driver.get.assert_called_once_with(scraper_instance.base_url)
            mock_inn_input.send_keys.assert_called_once_with("1234567890")
            mock_search_button.click.assert_called_once()
            mock_driver.quit.assert_called_once()

    def test_scrape_arbitr_cases_no_results(self, mock_webdriver_components, scraper_instance):
        """Тестирует скрапинг при отсутствии результатов."""
        mock_chrome, _, mock_driver = mock_webdriver_components
        scraper_instance.driver = mock_driver

        mock_inn_input = MagicMock()
        mock_search_button = MagicMock()

        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait,              patch('selenium.webdriver.support.expected_conditions') as mock_ec:
            mock_wait.return_value.until.side_effect = [
                mock_inn_input,
                mock_search_button,
                None
            ]
            mock_driver.find_elements.return_value = [] # Симулируем отсутствие строк результатов

            cases = scraper_instance.scrape_arbitr_cases("1111111111")
            assert len(cases) == 0
            mock_driver.quit.assert_called_once()

    def test_scrape_arbitr_cases_timeout(self, mock_webdriver_components, scraper_instance):
        """Тестирует скрапинг при возникновении таймаута."""
        mock_chrome, _, mock_driver = mock_webdriver_components
        scraper_instance.driver = mock_driver

        with patch('selenium.webdriver.support.ui.WebDriverWait') as mock_wait,              patch('selenium.webdriver.support.expected_conditions') as mock_ec:
            mock_wait.return_value.until.side_effect = TimeoutException("Timed out") # Симулируем таймаут
            cases = scraper_instance.scrape_arbitr_cases("1234567890")
            assert len(cases) == 0
            mock_driver.quit.assert_called_once()
