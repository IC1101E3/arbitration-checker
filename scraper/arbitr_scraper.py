
import os
import configparser
import logging
import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from utils.logger import setup_logging 

# Настройка логирования для ArbitrScraper
logger = setup_logging()

class ArbitrScraper:
    """Класс для веб-скрапинга арбитражных дел с kad.arbitr.ru с использованием Selenium.

    Инкапсулирует логику инициализации WebDriver, ввода ИНН в поле поиска,
    активации кнопки 'Найти', ожидания загрузки результатов и извлечения
    номера дела и даты из найденных результатов.
    """
    def __init__(self, config_path=None):
        """Инициализирует скрапер арбитражных дел.

        Args:
            config_path (str, optional): Путь к файлу конфигурации settings.ini.
                                         Если не указан, используется путь по умолчанию.
        """
        self.config = configparser.ConfigParser()
        if config_path:
            self.config.read(config_path)
            logger.info(f"ArbitrScraper: Используется предоставленный config_path: {config_path}")
        else:
            # Путь по умолчанию относительно корня проекта для settings.ini
            default_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.ini')
            self.config.read(default_config_path)
            logger.info(f"ArbitrScraper: Используется config_path по умолчанию: {default_config_path}")

        logger.info(f"Загруженные секции конфигурации: {self.config.sections()}")
        if self.config.has_section('SELENIUM'):
            logger.info(f"Элементы секции SELENIUM: {list(self.config.items('SELENIUM'))}")
        else:
            logger.warning("Секция SELENIUM не найдена в конфигурации.")

        self.webdriver_path = self.config.get('SELENIUM', 'webdriver_path', fallback='')
        self.base_url = "https://kad.arbitr.ru/"
        self.driver = None
        
        
    def _initialize_webdriver(self):
        """Инициализирует и возвращает экземпляр WebDriver для Chrome.

        Returns:
            webdriver.Chrome or None: Экземпляр WebDriver, если инициализация успешна,
                                      иначе None.
        """

        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox") 
        chrome_options.add_argument("--disable-dev-shm-usage") 
        chrome_options.add_argument("--disable-setuid-sandbox") 
        chrome_options.add_argument("--window-size=1920,1080") 
        chrome_options.add_argument("--disable-gpu") 
        chrome_options.add_argument("--ignore-certificate-errors") 
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.accept_insecure_certs = False
        chrome_options.page_load_strategy = "normal"

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("WebDriver успешно инициализирован.")
            return self.driver
        except WebDriverException as e:
            logger.error(f"Ошибка инициализации WebDriver: {e}")
            if "executable needs to be in PATH" in str(e) and not self.webdriver_path:
                logger.error("Убедитесь, что chromedriver находится в вашем PATH или укажите 'webdriver_path' в settings.ini.")
            self.driver = None
            return None

    def scrape_arbitr_cases(self, inn, max_results=10):
        """Скрапинг арбитражных дел для заданного ИНН с kad.arbitr.ru.

        Args:
            inn (str): Идентификационный номер налогоплательщика для поиска.
            max_results (int): Максимальное количество дел для извлечения.

        Returns:
            list: Список словарей, каждый из которых содержит 'case_number', 'case_date' и 'inn'.
        """
        if not self.driver:
            self._initialize_webdriver()
            if not self.driver:
                return []

        cases_data = []
        try:
            self.driver.get(self.base_url)
            logger.info(f"Переход на {self.base_url}")

            # Поиск поля ввода ИНН и ввод значения
            # Поле ввода ИНН часто идентифицируется по конкретному ID или классу,
            # или по тексту-заполнителю. Используем более надежный XPath.

            inn_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div[1]/dl/dd/div[1]/div/textarea"))
            )
            inn_input.clear()
            inn_input.send_keys(inn)
            logger.info(f"Введен ИНН: {inn}")


            # Поиск и нажатие кнопки 'Найти'
            search_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Найти')]"))
            )
            self.driver.execute_script("arguments[0].click();", search_button)
            logger.info("Нажата кнопка 'Найти' ")
          
            time.sleep(5)

            # Ожидание загрузки результатов поиска (например, наличие конкретного блока результатов)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "b-cases")) 
            )
            logger.info("Результаты поиска загружены.")
            

            # Извлечение данных дел
            # Предполагается, что результаты находятся в строках, и каждая строка содержит номер дела и дату.
            # Этот XPath должен быть адаптирован к фактической HTML-структуре результатов kad.arbitr.ru.
            result_rows = self.driver.find_elements(By.XPATH, 
            "//table[@id='b-cases']//tr[.//a[@class='num_case']]"
            )
                                                    
            for i, row in enumerate(result_rows):
                if len(cases_data) >= max_results:
                    break
    
                    
                try:
                    # Извлечение номера дела
                    # Эта часть сильно зависит от фактической HTML-структуры.
                    # Пример: ссылка с текстом номера дела или конкретный span.
                    # Извлечение даты дела
                    # Пример: span с датой или div, содержащий дату.

                    cells = row.find_elements(By.TAG_NAME, "td")
                
                    if len(cells) >= 4:
                        # Ячейка 1: дата и номер дела
                        first_cell = cells[0]
                        
                        # Извлечение даты 
                        date_element = first_cell.find_element(By.XPATH, ".//*[contains(text(), '.')][1]")
                        case_date_str = date_element.text.strip() if date_element else ""
                    
                        # Извлечение номера дела (ссылка с номером)
                        case_link = first_cell.find_element(By.XPATH, ".//a[contains(@href, '/Card/')]")
                        case_number = case_link.text.strip()
                        
                    # Попытка разобрать строку даты в стандартный формат 
                    try:
                        case_date = datetime.datetime.strptime(case_date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
                    except ValueError:
                        case_date = None #  Или обработать как строку, если разбор не удался
                        logger.warning(f"Не удалось разобрать дату: {case_date_str} для дела {case_number}")

                    if case_number and case_date:
                        cases_data.append({
                            'case_number': case_number,
                            'case_date': case_date,
                            'inn': inn
                        })
                        logger.info(f"Извлечено: Дело {case_number}, Дата {case_date}, ИНН {inn}")

                except NoSuchElementException:
                    logger.warning(f"Не удалось найти элементы номера дела или даты в строке результатов {i+1}. Пропуск.")
                except Exception as ex:
                    logger.warning(f"Ошибка обработки строки результатов {i+1}: {ex}. Пропуск.")

        except TimeoutException:
            logger.error("Таймаут ожидания появления элементов.")
        except NoSuchElementException as e:
            logger.error(f"Элемент не найден: {e}")
        except WebDriverException as e:
            logger.error(f"Ошибка WebDriver во время скрапинга: {e}")
        except Exception as e:
            logger.error(f"Произошла неожиданная ошибка во время скрапинга: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver закрыт.")

        return cases_data

if __name__ == '__main__':
    # Этот блок предназначен для непосредственного тестирования функциональности ArbitrScraper.
    # Он будет выполнен только в случае, если arbitr_scraper.py запущен как скрипт.
    # Этот пример демонстрирует использование, но предполагает соответствующую среду.

    logger.info("--- Тестирование ArbitrScraper ---") # Экранированные символы новой строки

    # Предполагается, что settings.ini находится по адресу arbitration_checker/settings.ini
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '.'))
    test_config_path = os.path.join(project_root, 'settings.ini')

    scraper = ArbitrScraper(config_path=test_config_path)

    test_inn = "0000000000" # Пример ИНН 
    # Примечание: Скрапинг kad.arbitr.ru может быть ограничен по частоте запросов
    # или требовать CAPTCHA. Это базовая реализация и может потребовать дальнейших
    # доработок для повышения надежности.

    logger.info(f"Скрапинг дел для ИНН: {test_inn}")
    cases = scraper.scrape_arbitr_cases(test_inn)

    if cases:
        logger.info(f"Найдено {len(cases)} дел для ИНН {test_inn}:")
        for case in cases:
            logger.info(case)
    else:
        logger.info(f"Дела не найдены или произошла ошибка для ИНН {test_inn}.")

    logger.info("--- Тестирование ArbitrScraper завершено ---") # Экранированные символы новой строки
