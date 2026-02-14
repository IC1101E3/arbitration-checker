
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QAbstractItemView, QFileDialog, QTextEdit
from PyQt5.QtCore import Qt, QTimer # QTimer для неблокирующего UI во время тяжелых операций
import os

class MainWindow(QMainWindow):
    """Главное окно приложения 'Arbitration Checker'.

    Предоставляет пользовательский интерфейс для ввода ИНН, запуска скрапинга,
    фильтрации сохраненных дел и экспорта данных.
    """
    def __init__(self):
        """Инициализирует главное окно приложения."""
        super().__init__()
        self.setWindowTitle("Arbitration Checker")
        self.setGeometry(100, 100, 800, 600) # x, y, ширина, высота

        self._init_ui()

    def _init_ui(self):
        """Настраивает пользовательский интерфейс главного окна."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Область ввода ИНН для скрапинга
        scrape_inn_layout = QHBoxLayout()
        scrape_inn_label = QLabel("ИНН для скрапинга:")
        self.scrape_inn_input = QLineEdit()
        self.scrape_inn_input.setPlaceholderText("Введите ИНН для скрапинга")
        scrape_inn_layout.addWidget(scrape_inn_label)
        scrape_inn_layout.addWidget(self.scrape_inn_input)
        main_layout.addLayout(scrape_inn_layout)

        # Кнопка поиска для скрапинга
        self.search_button = QPushButton("Найти (Скрапинг)")
        main_layout.addWidget(self.search_button)

        # Раздел фильтрации
        main_layout.addWidget(QLabel("--- Фильтровать сохраненные дела:"))

        filter_layout = QVBoxLayout()

        # Фильтр по номеру дела
        case_num_filter_layout = QHBoxLayout()
        case_num_filter_label = QLabel("Фильтр по номеру дела:")
        self.case_num_filter_input = QLineEdit()
        self.case_num_filter_input.setPlaceholderText("Введите часть номера дела")
        case_num_filter_layout.addWidget(case_num_filter_label)
        case_num_filter_layout.addWidget(self.case_num_filter_input)
        filter_layout.addLayout(case_num_filter_layout)

        # Фильтр по ИНН
        inn_filter_layout = QHBoxLayout()
        inn_filter_label = QLabel("Фильтр по ИНН:")
        self.inn_filter_input = QLineEdit()
        self.inn_filter_input.setPlaceholderText("Введите часть ИНН")
        inn_filter_layout.addWidget(inn_filter_label)
        inn_filter_layout.addWidget(self.inn_filter_input)
        filter_layout.addLayout(inn_filter_layout)

        # Фильтр по диапазону дат
        date_filter_layout = QHBoxLayout()
        date_filter_label = QLabel("Диапазон дат (ГГГГ-ММ-ДД):")
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("Начальная дата")
        self.end_date_input = QLineEdit()
        self.end_date_input.setPlaceholderText("Конечная дата")
        date_filter_layout.addWidget(date_filter_label)
        date_filter_layout.addWidget(self.start_date_input)
        date_filter_layout.addWidget(self.end_date_input)
        filter_layout.addLayout(date_filter_layout)

        # Кнопка фильтрации
        self.filter_button = QPushButton("Фильтровать (Поиск сохраненных)")
        filter_layout.addWidget(self.filter_button)

        main_layout.addLayout(filter_layout)

        # Область кнопок экспорта
        export_layout = QHBoxLayout()
        self.export_csv_button = QPushButton("Экспорт в CSV")
        self.export_json_button = QPushButton("Экспорт в JSON")
        export_layout.addWidget(self.export_csv_button)
        export_layout.addWidget(self.export_json_button)
        main_layout.addLayout(export_layout)

        # Область таблицы результатов
        results_label = QLabel("Результаты:")
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(['Номер дела', 'Дата дела', 'ИНН'])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        main_layout.addWidget(results_label)
        main_layout.addWidget(self.results_table)

        # Область отображения статуса (оставлена как QTextEdit для общих обновлений статуса)
        status_label = QLabel("Статус:")
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumHeight(100) # Ограничить высоту для сообщений о статусе
        main_layout.addWidget(status_label)
        main_layout.addWidget(self.status_display)

        # Подключение кнопок к функциям 
        self.search_button.clicked.connect(self._on_search_clicked)
        self.filter_button.clicked.connect(self._on_filter_clicked)
        self.export_csv_button.clicked.connect(self._on_export_csv_clicked)
        self.export_json_button.clicked.connect(self._on_export_json_clicked)

    def _on_search_clicked(self):
        """Обрабатывает нажатие кнопки 'Найти' для запуска скрапинга.

        Получает ИНН из поля ввода, очищает таблицу результатов и
        обновляет статус-дисплей. Фактическая логика скрапинга
        подключается через main.py к ApplicationLogic.
        """
        inn = self.scrape_inn_input.text()
        if inn:
            self.status_display.append(f"Поиск дел для ИНН: {inn}...")
            self.clear_results_table() # Очистить таблицу перед новым поиском
            # Этот вызов будет подключен к ApplicationLogic.start_scraping через main.py
        else:
            self.status_display.append("Пожалуйста, введите ИНН для скрапинга.")

    def _on_filter_clicked(self):
        """Обрабатывает нажатие кнопки 'Фильтровать' для поиска по сохраненным делам.

        Получает параметры фильтрации из соответствующих полей ввода
        и обновляет статус-дисплей. Фактическая логика фильтрации
        подключается через main.py к ApplicationLogic.filter_cases.
        """
        case_num_filter = self.case_num_filter_input.text()
        inn_filter = self.inn_filter_input.text()
        start_date = self.start_date_input.text()
        end_date = self.end_date_input.text()
        self.status_display.append(f"Применение фильтров: Номер дела='{case_num_filter}', ИНН='{inn_filter}', Дата начала='{start_date}', Дата окончания='{end_date}'")
        

    def _on_export_csv_clicked(self):
        """Обрабатывает нажатие кнопки 'Экспорт в CSV'.

        Вызывает логику экспорта CSV, которая будет подключена через main.py
        к ApplicationLogic.
        """
        self.status_display.append("Нажата кнопка Экспорт в CSV. Логика будет интегрирована здесь.")
        # Заглушка для логики экспорта

    def _on_export_json_clicked(self):
        """Обрабатывает нажатие кнопки 'Экспорт в JSON'.

        Вызывает логику экспорта JSON, которая будет подключена через main.py
        к ApplicationLogic.
        """
        self.status_display.append("Нажата кнопка Экспорт в JSON. Логика будет интегрирована здесь.")
        # Заглушка для логики экспорта

    def clear_results_table(self):
        """Очищает все содержимое таблицы результатов."""
        self.results_table.setRowCount(0)
        self.results_table.clearContents() # Также очищает заголовки

    def add_case_to_table(self, case_data):
        """Добавляет одно арбитражное дело в таблицу результатов.

        Args:
            case_data (dict): Словарь, содержащий 'case_number', 'case_date' и 'inn'.
        """
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)
        self.results_table.setItem(row_position, 0, QTableWidgetItem(case_data['case_number']))
        self.results_table.setItem(row_position, 1, QTableWidgetItem(str(case_data['case_date']))) # Преобразовать дату в строку
        self.results_table.setItem(row_position, 2, QTableWidgetItem(case_data['inn']))

    def update_results_table(self, cases):
        """Обновляет таблицу результатов списком дел.

        Args:
            cases (list): Список словарей, каждый из которых представляет арбитражное дело.
        """
        self.clear_results_table()
        for case in cases:
            self.add_case_to_table(case)


if __name__ == '__main__':
    # Точка входа в приложение при непосредственном запуске скрипта.
    # Создает и отображает главное окно PyQt5.
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
