
import logging
import os

def setup_logging(log_file_name='app.log', log_level=logging.INFO):
    """Настраивает систему логирования для вывода в файл и консоль.

    Логирование производится в файл `app.log` в корневой директории проекта
    и в стандартный вывод (консоль). Файловый лог записывает все сообщения
    уровня DEBUG и выше, консольный лог - сообщения, начиная с заданного `log_level`.

    Args:
        log_file_name (str, optional): Имя файла логов. По умолчанию 'app.log'.
        log_level (int, optional): Минимальный уровень логирования для консоли.
                                   По умолчанию logging.INFO.

    Returns:
        logging.Logger: Настроенный экземпляр логгера.
    """

    # Получаем путь к корневой директории проекта. Предполагается, что logger.py
    # находится в arbitration_checker/utils.
    project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Определяем путь к файлу логов
    log_file_path = os.path.join(project_root_path, log_file_name)

    # Создаем экземпляр логгера
    logger = logging.getLogger('arbitration_checker')
    logger.setLevel(logging.DEBUG) # Логируем все сообщения в лог-файл

    # Предотвращаем добавление нескольких обработчиков, если setup_logging вызывается несколько раз
    if not logger.handlers:
        # Обработчик файлов
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG) # Логируем все сообщения в файл

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level) # Логируем в консоль только сообщения уровня log_level и выше

        # Форматировщик
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Добавляем форматировщик к обработчикам
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Добавляем обработчики к логгеру
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Возвращаем настроенный логгер
    return logger

if __name__ == '__main__':
    # Демонстрация функциональности логирования
    my_logger = setup_logging(log_level=logging.DEBUG) # Устанавливаем DEBUG для полной демонстрации

    my_logger.debug("Это отладочное сообщение.")
    my_logger.info("Это информационное сообщение.")
    my_logger.warning("Это предупреждающее сообщение.")
    my_logger.error("Это сообщение об ошибке.")
    my_logger.critical("Это критическое сообщение.")

    print(f"Проверьте 'app.log' в корневой директории проекта для полного вывода логов.")
    print(f"Расположение файла логов: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.log'))}")
