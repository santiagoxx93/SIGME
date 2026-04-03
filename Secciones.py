import sys
import psycopg2
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QMessageBox, QFormLayout, QProgressDialog,
                             QGridLayout, QSizePolicy)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QTimer # Importar QTimer

# --- Configuración de Logging ---
import logging
import os
from datetime import datetime

log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

log_filename = os.path.join(log_directory, f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout) # También imprime en consola para depuración
    ]
)
logger = logging.getLogger(__name__)
# --- Fin Configuración de Logging ---

class WorkerSignals(QObject):
    """
    Define las señales disponibles de un hilo de trabajo.
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int, str)

class DBWorker(QRunnable):
    """
    Hilo de trabajo para operaciones de base de datos.
    """
    def __init__(self, fn, *args, **kwargs):
        super(DBWorker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """
        Inicializa la función de trabajo con los argumentos y señales.
        """
        try:
            result = self.fn(self.signals.progress, *self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            import traceback
            exctype, value = sys.exc_info()[:2]
            logger.error(f"Error en DBWorker: {value}", exc_info=True)
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

def conectar_db(db_params): # Ahora acepta db_params como argumento
    """
    Establece una conexión a la base de datos PostgreSQL.
    """
    try:
        conn = psycopg2.connect(**db_params)
        conn.set_client_encoding('UTF8')
        return conn
    except psycopg2.Error as e:
        logger.critical(f"Error al conectar a la base de datos: {e}", exc_info=True)
        raise Exception(f"No se pudo conectar a la base de datos. Por favor, verifique la configuración y el estado del servidor.")

class ModuloInstitucion(QWidget):
    closed = pyqtSignal() # Señal para indicar que el módulo se cerró

    def __init__(self, db_config, user_data): # Aceptar db_config y user_data
        super().__init__()
        self.db_config = db_config # Almacenar la configuración de la BD
        self.user_data = user_data # Almacenar los datos del usuario

        self.setWindowTitle("SIGME2 | Gestión de Secciones y Aulas")
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #e4eaf4;
                font-family: 'Segoe UI', sans-serif;
                color: #333333;
            }
            QLabel {
                color: #1c355b;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #a0b4c8;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #b3cbdc;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #1c355b;
            }
            QPushButton {
                background-color: #1c355b;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #2a4e7c;
            }
            QPushButton:pressed {
                background-color: #152b4a;
            }
            QPushButton#ClearButton {
                background-color: #708fa7;
            }
            QPushButton#ClearButton:hover {
                background-color: #8da7bd;
            }
            QPushButton#ClearButton:pressed {
                background-color: #5c7a91;
            }
            QPushButton#EditButton {
                background-color: #28a745; /* Verde para editar */
            }
            QPushButton#EditButton:hover {
                background-color: #218838;
            }
            QPushButton#EditButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton#DeleteButton {
                background-color: #dc3545; /* Rojo para eliminar */
            }
            QPushButton#DeleteButton:hover {
                background-color: #c82333;
            }
            QPushButton#DeleteButton:pressed {
                background-color: #bd2130;
            }
            QPushButton#CancelEditButton {
                background-color: #ffc107; /* Amarillo para cancelar */
                color: #333333;
            }
            QPushButton#CancelEditButton:hover {
                background-color: #e0a800;
            }
            QPushButton#CancelEditButton:pressed {
                background-color: #d39e00;
            }
            /* Estilos para botones de paginación */
            QPushButton.PaginationButton {
                background-color: #1c355b;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: normal;
            }
            QPushButton.PaginationButton:hover {
                background-color: #2a4e7c;
            }
            QPushButton.PaginationButton:disabled {
                background-color: #a0b4c8;
                color: #e0e0e0;
            }

            QTableWidget {
                background-color: white;
                border: 1px solid #b3cbdc;
                border-radius: 8px;
                gridline-color: #e0e0e0;
                selection-background-color: #d0e0f0;
                selection-color: #333333;
            }
            QHeaderView::section {
                background-color: #1c355b;
                color: white;
                padding: 8px;
                border: 1px solid #1c355b;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #b3cbdc;
                border-radius: 8px;
                background-color: #f0f5fa;
            }
            QTabBar::tab {
                background: #d0e0f0;
                border: 1px solid #b3cbdc;
                border-bottom-color: #b3cbdc;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 8px;
                color: #1c355b;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #f0f5fa;
                border-color: #b3cbdc;
                border-bottom-color: #f0f5fa;
            }
            QTabBar::tab:hover {
                background: #e0effa;
            }
        """)
        self.threadpool = QThreadPool()
        print(f"Multithreading con un máximo de {self.threadpool.maxThreadCount()} hilos")
        self.progress_dialog = None
        self.seccion_editando_codigo = None # Variable para controlar el modo edición

        # Variables de paginación y búsqueda
        self.current_page = 1
        self.page_size = 10
        self.total_records = 0
        self.total_pages = 0
        self.search_term = ""
        self.search_timer = QTimer(self) # Timer para búsqueda con retraso
        self.search_timer.setSingleShot(True)
        # Conectar el timer a perform_search (ahora definido antes)
        self.search_timer.timeout.connect(self.perform_search) 

        self.init_ui()
        self.cargar_secciones(show_progress_dialog=False)
        self.cargar_docentes(show_progress_dialog=False)
        self._update_buttons_state() # Actualizar estado inicial de los botones

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Botón para volver al menú principal
        self.back_to_menu_button = QPushButton("Volver al Menú Principal")
        self.back_to_menu_button.setObjectName("backButton") # Para aplicar estilos específicos
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        main_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.tabs = QTabWidget()
        self.tab_secciones = QWidget()
        self.setup_secciones_ui()
        self.tabs.addTab(self.tab_secciones, "Gestión de Secciones")
        
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def setup_secciones_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Gestión de Secciones Escolares")
        header.setStyleSheet("""
            color: #1c355b;
            font-size: 28px;
            font-weight: bold;
            padding: 15px;
            background-color: #d0e0f0;
            border-radius: 10px;
            margin-bottom: 20px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        form_container = QWidget()
        form_layout = QGridLayout(form_container)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)

        label_style = "font-weight: bold; color: #1c355b;"

        self.input_grado = QLineEdit()
        self.input_grado.setPlaceholderText("Ej: 1, 2, 3...")
        self.input_grado.textChanged.connect(lambda: self._clear_error_style(self.input_grado))

        self.input_letra = QComboBox()
        self.input_letra.addItems(["A", "B", "C", "D", "E"])

        self.input_turno = QComboBox()
        self.input_turno.addItems(["Mañana (M)", "Tarde (T)"])

        self.input_docente_combo = QComboBox()
        self.input_docente_combo.setPlaceholderText("Seleccione un docente")
        self.input_docente_combo.currentIndexChanged.connect(lambda: self._clear_error_style(self.input_docente_combo))

        self.input_capacidad_maxima = QLineEdit()
        self.input_capacidad_maxima.setPlaceholderText("Ej: 30, 35, 40")
        self.input_capacidad_maxima.textChanged.connect(lambda: self._clear_error_style(self.input_capacidad_maxima))

        self.input_aula = QLineEdit()
        self.input_aula.setPlaceholderText("Ej: 101, 202, o dejar vacío para asignar automáticamente")

        form_layout.addWidget(QLabel("Grado:", styleSheet=label_style), 0, 0)
        form_layout.addWidget(self.input_grado, 0, 1)

        form_layout.addWidget(QLabel("Letra:", styleSheet=label_style), 1, 0)
        form_layout.addWidget(self.input_letra, 1, 1)

        form_layout.addWidget(QLabel("Turno:", styleSheet=label_style), 2, 0)
        form_layout.addWidget(self.input_turno, 2, 1)

        form_layout.addWidget(QLabel("Docente Guía:", styleSheet=label_style), 0, 2)
        form_layout.addWidget(self.input_docente_combo, 0, 3)

        form_layout.addWidget(QLabel("Capacidad Máxima:", styleSheet=label_style), 1, 2)
        form_layout.addWidget(self.input_capacidad_maxima, 1, 3)

        form_layout.addWidget(QLabel("Aula (opcional):", styleSheet=label_style), 2, 2)
        form_layout.addWidget(self.input_aula, 2, 3)

        main_layout.addWidget(form_container)

        # Botones de acción (Asignar/Actualizar, Limpiar, Cancelar Edición)
        btn_action_layout = QHBoxLayout()
        btn_action_layout.setSpacing(15)
        btn_action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_asignar_actualizar = QPushButton("Asignar Sección")
        self.btn_asignar_actualizar.clicked.connect(self.asignar_o_actualizar_seccion)
        self.btn_asignar_actualizar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_asignar_actualizar.setMinimumWidth(150)

        self.btn_limpiar = QPushButton("Limpiar Formulario")
        self.btn_limpiar.setObjectName("ClearButton")
        self.btn_limpiar.clicked.connect(self.limpiar_formulario)
        self.btn_limpiar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_limpiar.setMinimumWidth(150)

        self.btn_cancelar_edicion = QPushButton("Cancelar Edición")
        self.btn_cancelar_edicion.setObjectName("CancelEditButton")
        self.btn_cancelar_edicion.clicked.connect(self.cancelar_edicion)
        self.btn_cancelar_edicion.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_cancelar_edicion.setMinimumWidth(150)
        self.btn_cancelar_edicion.setVisible(False) # Ocultar inicialmente

        btn_action_layout.addWidget(self.btn_asignar_actualizar)
        btn_action_layout.addWidget(self.btn_limpiar)
        btn_action_layout.addWidget(self.btn_cancelar_edicion)
        main_layout.addLayout(btn_action_layout)

        # Barra de búsqueda
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 10, 0, 10)
        search_layout.addWidget(QLabel("Buscar:"))
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Buscar por código, grado, letra, docente o aula...")
        self.input_search.textChanged.connect(self.delayed_search) # Conectar al timer
        search_layout.addWidget(self.input_search)
        main_layout.addLayout(search_layout)

        # Tabla de secciones
        self.tabla_secciones = QTableWidget()
        self.tabla_secciones.setColumnCount(7)
        self.tabla_secciones.setHorizontalHeaderLabels([
            "Código", "Grado", "Letra", "Turno", "Aula", "Docente", "Capacidad Máxima"
        ])
        self.tabla_secciones.verticalHeader().setVisible(False)
        self.tabla_secciones.horizontalHeader().setStretchLastSection(True)
        self.tabla_secciones.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_secciones.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tabla_secciones.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_secciones.itemSelectionChanged.connect(self._update_buttons_state)
        self.tabla_secciones.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout.addWidget(self.tabla_secciones)

        # Controles de paginación
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 10, 0, 10)
        pagination_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_first_page = QPushButton("<<")
        self.btn_first_page.setObjectName("PaginationButton")
        self.btn_first_page.clicked.connect(self.go_to_first_page)
        self.btn_prev_page = QPushButton("<")
        self.btn_prev_page.setObjectName("PaginationButton")
        self.btn_prev_page.clicked.connect(self.go_to_prev_page)

        self.lbl_page_info = QLabel("Página 1 de 1")
        self.lbl_page_info.setStyleSheet("font-weight: bold;")

        self.btn_next_page = QPushButton(">")
        self.btn_next_page.setObjectName("PaginationButton")
        self.btn_next_page.clicked.connect(self.go_to_next_page)
        self.btn_last_page = QPushButton(">>")
        self.btn_last_page.setObjectName("PaginationButton")
        self.btn_last_page.clicked.connect(self.go_to_last_page)

        pagination_layout.addWidget(self.btn_first_page)
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.lbl_page_info)
        pagination_layout.addWidget(self.btn_next_page)
        pagination_layout.addWidget(self.btn_last_page)
        main_layout.addLayout(pagination_layout)

        # Botones de edición/eliminación de la tabla
        btn_table_layout = QHBoxLayout()
        btn_table_layout.setSpacing(15)
        btn_table_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.btn_editar = QPushButton("Editar Sección")
        self.btn_editar.setObjectName("EditButton")
        self.btn_editar.clicked.connect(self.editar_seccion)
        self.btn_editar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_editar.setMinimumWidth(150)

        self.btn_eliminar = QPushButton("Eliminar Sección")
        self.btn_eliminar.setObjectName("DeleteButton")
        self.btn_eliminar.clicked.connect(self.eliminar_seccion)
        self.btn_eliminar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_eliminar.setMinimumWidth(150)

        btn_table_layout.addWidget(self.btn_editar)
        btn_table_layout.addWidget(self.btn_eliminar)
        main_layout.addLayout(btn_table_layout)

        self.tab_secciones.setLayout(main_layout)

    def _set_error_style(self, widget):
        widget.setStyleSheet(widget.styleSheet() + "border: 2px solid red;")

    def _clear_error_style(self, widget):
        if isinstance(widget, QLineEdit):
            widget.setStyleSheet("""
                padding: 8px;
                border: 1px solid #a0b4c8;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #b3cbdc;
            """)
        elif isinstance(widget, QComboBox):
            widget.setStyleSheet("""
                padding: 8px;
                background-color: white;
                border: 1px solid #a0b4c8;
                border-radius: 5px;
            """)

    def delayed_search(self):
        """Inicia un temporizador para ejecutar la búsqueda después de un breve retraso."""
        self.search_timer.start(500) # 500 ms de retraso

    def perform_search(self):
        """Ejecuta la búsqueda y recarga la tabla."""
        new_search_term = self.input_search.text().strip()
        if new_search_term != self.search_term:
            self.search_term = new_search_term
            self.current_page = 1 # Resetear a la primera página en una nueva búsqueda
            self.cargar_secciones()

    def _run_db_operation(self, func, success_slot, error_slot, show_progress_dialog=True, *args, **kwargs):
        self._set_ui_enabled(False)
        
        if show_progress_dialog:
            self.progress_dialog = QProgressDialog("Realizando operación...", "Cancelar", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setWindowTitle("Procesando...")
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.setValue(0)
            self.progress_dialog.show()
        else:
            self.progress_dialog = None

        worker = DBWorker(func, *args, **kwargs)
        worker.signals.result.connect(success_slot)
        worker.signals.error.connect(error_slot)
        if show_progress_dialog:
            worker.signals.progress.connect(self._update_progress_dialog)
        worker.signals.finished.connect(lambda: self._operation_finished())
        self.threadpool.start(worker)

    def _update_progress_dialog(self, value, message):
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    def _operation_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self._set_ui_enabled(True)
        self._update_buttons_state() # Asegurarse de que los botones se actualicen al finalizar

    def _set_ui_enabled(self, enabled):
        self.btn_asignar_actualizar.setEnabled(enabled)
        self.btn_limpiar.setEnabled(enabled)
        self.input_grado.setEnabled(enabled)
        self.input_letra.setEnabled(enabled)
        self.input_turno.setEnabled(enabled)
        self.input_docente_combo.setEnabled(enabled)
        self.input_capacidad_maxima.setEnabled(enabled)
        self.input_aula.setEnabled(enabled)
        self.input_search.setEnabled(enabled) # Habilitar/deshabilitar búsqueda
        # Los botones de editar/eliminar/paginación se controlan por _update_buttons_state

    def _update_buttons_state(self):
        selected_rows = self.tabla_secciones.selectionModel().selectedRows()
        num_selected_rows = len(selected_rows)

        # Botones de la tabla (Editar/Eliminar)
        # Solo habilitados si NO estamos en modo edición
        if self.seccion_editando_codigo is None:
            self.btn_editar.setEnabled(num_selected_rows == 1)
            self.btn_eliminar.setEnabled(num_selected_rows >= 1)
        else:
            self.btn_editar.setEnabled(False)
            self.btn_eliminar.setEnabled(False)

        # Botones del formulario (Asignar/Actualizar, Cancelar Edición)
        if self.seccion_editando_codigo is None: # Modo Asignar
            self.btn_asignar_actualizar.setText("Asignar Sección")
            self.btn_cancelar_edicion.setVisible(False)
            self.input_grado.setEnabled(True) # Grado, Letra, Turno editables en modo asignación
            self.input_letra.setEnabled(True)
            self.input_turno.setEnabled(True)
        else: # Modo Actualizar
            self.btn_asignar_actualizar.setText("Actualizar Sección")
            self.btn_cancelar_edicion.setVisible(True)
            # Grado, Letra, Turno no editables en modo edición (son parte del código de la sección)
            self.input_grado.setEnabled(False)
            self.input_letra.setEnabled(False)
            self.input_turno.setEnabled(False)

        # Botones de paginación
        self.btn_first_page.setEnabled(self.current_page > 1)
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < self.total_pages)
        self.btn_last_page.setEnabled(self.current_page < self.total_pages)
        self.lbl_page_info.setText(f"Página {self.current_page} de {self.total_pages}")


    def cargar_docentes(self, show_progress_dialog=True):
        self._run_db_operation(
            self._perform_cargar_docentes,
            self._handle_cargar_docentes_result,
            self._handle_db_error,
            show_progress_dialog=show_progress_dialog,
            db_config=self.db_config # Pasar db_config
        )

    def _perform_cargar_docentes(self, progress_callback, db_config): # Aceptar db_config
        conn = None
        try:
            conn = conectar_db(db_config) # Pasar db_config
            cursor = conn.cursor()
            progress_callback.emit(10, "Cargando docentes...")
            cursor.execute("SELECT cedula, nombres, apellidos FROM PERSONAL ORDER BY nombres, apellidos")
            docentes = cursor.fetchall()
            progress_callback.emit(100, "Docentes cargados.")
            return docentes
        finally:
            if conn:
                conn.close()

    def _handle_cargar_docentes_result(self, docentes):
        self.input_docente_combo.clear()
        self.input_docente_combo.addItem("Seleccione un docente", userData=None)
        for cedula, nombres, apellidos in docentes:
            display_text = f"{nombres} {apellidos} ({cedula})"
            self.input_docente_combo.addItem(display_text, userData=cedula)

    def asignar_o_actualizar_seccion(self):
        grado = self.input_grado.text().strip()
        letra = self.input_letra.currentText()
        turno = self.input_turno.currentText()[0]
        docente = self.input_docente_combo.currentData()
        aula_manual = self.input_aula.text().strip()
        capacidad_maxima_str = self.input_capacidad_maxima.text().strip()

        # Validaciones de entrada
        has_error = False
        if not grado:
            self._set_error_style(self.input_grado)
            has_error = True
        if docente is None:
            self._set_error_style(self.input_docente_combo)
            has_error = True
        if not capacidad_maxima_str:
            self._set_error_style(self.input_capacidad_maxima)
            has_error = True

        if has_error:
            QMessageBox.warning(self, "Campos Requeridos", "Por favor, complete todos los campos obligatorios.")
            return

        try:
            grado_int = int(grado)
            if grado_int < 1 or grado_int > 6:
                self._set_error_style(self.input_grado)
                QMessageBox.warning(self, "Grado Inválido", "El grado debe ser un número entero entre 1 y 6.")
                return
        except ValueError:
            self._set_error_style(self.input_grado)
            QMessageBox.warning(self, "Grado Inválido", "El grado debe ser un número entero.")
            return
        
        try:
            capacidad_maxima = int(capacidad_maxima_str)
            if capacidad_maxima <= 0:
                self._set_error_style(self.input_capacidad_maxima)
                QMessageBox.warning(self, "Capacidad Máxima Inválida", "La capacidad máxima debe ser un número entero positivo.")
                return
        except ValueError:
            self._set_error_style(self.input_capacidad_maxima)
            QMessageBox.warning(self, "Capacidad Máxima Inválida", "La capacidad máxima debe ser un número entero.")
            return

        if self.seccion_editando_codigo is None: # Modo Asignar
            self._run_db_operation(
                self._perform_asignar_seccion,
                self._handle_asignar_seccion_result,
                self._handle_db_error,
                grado=grado, letra=letra, turno=turno, docente=docente, aula_manual=aula_manual, capacidad_maxima=capacidad_maxima,
                db_config=self.db_config # Pasar db_config
            )
        else: # Modo Actualizar
            self._run_db_operation(
                self._perform_actualizar_seccion,
                self._handle_actualizar_seccion_result,
                self._handle_db_error,
                codigo_seccion=self.seccion_editando_codigo,
                grado=grado, letra=letra, turno=turno, docente=docente, aula_manual=aula_manual, capacidad_maxima=capacidad_maxima,
                db_config=self.db_config # Pasar db_config
            )

    def _perform_asignar_seccion(self, progress_callback, grado, letra, turno, docente, aula_manual, capacidad_maxima, db_config): # Aceptar db_config
        conn = None
        try:
            conn = conectar_db(db_config) # Pasar db_config
            cursor = conn.cursor()

            progress_callback.emit(10, "Verificando año escolar activo...")
            cursor.execute("SELECT codigo FROM ANO_ESCOLAR WHERE activo = TRUE LIMIT 1")
            resultado = cursor.fetchone()
            if not resultado:
                raise ValueError("No hay un año escolar activo registrado. Por favor, configure uno.")
            codigo_ano_escolar = resultado[0]

            progress_callback.emit(30, "Verificando sección existente...")
            cursor.execute("""
                SELECT 1 FROM SECCION
                WHERE codigo_grado = %s AND letra = %s AND turno = %s AND codigo_ano_escolar = %s
            """, (grado, letra, turno, codigo_ano_escolar))
            if cursor.fetchone():
                raise ValueError(f"Ya existe una sección {grado}{letra} en el turno {turno} para el año escolar actual.")

            progress_callback.emit(40, "Verificando asignación de docente...")
            cursor.execute("""
                SELECT codigo FROM SECCION
                WHERE cedula_docente_guia = %s AND codigo_ano_escolar = %s
            """, (docente, codigo_ano_escolar))
            docente_asignado = cursor.fetchone()
            if docente_asignado:
                raise ValueError(f"Este docente ya está asignado a la sección {docente_asignado[0]} para el año escolar actual.")

            aula = None
            if aula_manual:
                progress_callback.emit(50, "Verificando aula manual...")
                cursor.execute("""
                    SELECT 1 FROM SECCION
                    WHERE aula_asignada = %s AND codigo_grado = %s AND turno = %s AND codigo_ano_escolar = %s
                """, (aula_manual, grado, turno, codigo_ano_escolar))
                if cursor.fetchone():
                    raise ValueError(f"El aula {aula_manual} ya está asignada en este grado y turno para el año escolar actual.")
                aula = aula_manual
            else:
                progress_callback.emit(60, "Buscando aula disponible automáticamente...")
                aula = self._get_available_aula_db(grado, cursor)
                if aula is None:
                    raise ValueError("No hay aulas disponibles para este grado. Considere asignar una manualmente.")

            codigo_seccion = f"{grado}{letra}-{turno}"

            progress_callback.emit(80, "Insertando nueva sección...")
            cursor.execute("""
                INSERT INTO SECCION (
                    codigo, letra, codigo_grado, turno,
                    cedula_docente_guia, aula_asignada,
                    capacidad_maxima, total_estudiantes,
                    estudiantes_varones, estudiantes_hembras,
                    codigo_ano_escolar
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0, %s)
            """, (
                codigo_seccion, letra, grado, turno,
                docente, aula,
                capacidad_maxima,
                codigo_ano_escolar
            ))

            conn.commit()
            progress_callback.emit(100, "Sección asignada correctamente.")
            return {"codigo_seccion": codigo_seccion, "aula": aula}

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de PostgreSQL al asignar sección: {e}", exc_info=True)
            raise Exception(f"Error en la base de datos al asignar la sección: {e.pgerror or e}")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error inesperado al asignar sección: {e}", exc_info=True)
            raise Exception(f"Ocurrió un error inesperado: {e}")
        finally:
            if conn:
                conn.close()

    def _handle_asignar_seccion_result(self, result):
        QMessageBox.information(self, "Éxito",
                                 f"Sección asignada correctamente:\nCódigo: {result['codigo_seccion']}\nAula: {result['aula']}")
        self.limpiar_formulario()
        self.cargar_secciones()

    def _perform_actualizar_seccion(self, progress_callback, codigo_seccion, grado, letra, turno, docente, aula_manual, capacidad_maxima, db_config): # Aceptar db_config
        conn = None
        try:
            conn = conectar_db(db_config) # Pasar db_config
            cursor = conn.cursor()

            progress_callback.emit(10, "Verificando año escolar activo...")
            cursor.execute("SELECT codigo FROM ANO_ESCOLAR WHERE activo = TRUE LIMIT 1")
            resultado = cursor.fetchone()
            if not resultado:
                raise ValueError("No hay un año escolar activo registrado. Por favor, configure uno.")
            codigo_ano_escolar = resultado[0]

            # Verificar si el docente ya está asignado a otra sección (excluyendo la sección actual)
            progress_callback.emit(20, "Verificando asignación de docente...")
            cursor.execute("""
                SELECT codigo FROM SECCION
                WHERE cedula_docente_guia = %s AND codigo_ano_escolar = %s AND codigo != %s
            """, (docente, codigo_ano_escolar, codigo_seccion))
            docente_asignado = cursor.fetchone()
            if docente_asignado:
                raise ValueError(f"Este docente ya está asignado a la sección {docente_asignado[0]} para el año escolar actual.")

            aula_to_update = aula_manual if aula_manual else None

            progress_callback.emit(30, "Verificando aula manual (si aplica)...")
            if aula_to_update:
                cursor.execute("""
                    SELECT 1 FROM SECCION
                    WHERE aula_asignada = %s AND codigo_grado = %s AND turno = %s AND codigo_ano_escolar = %s AND codigo != %s
                """, (aula_to_update, grado, turno, codigo_ano_escolar, codigo_seccion))
                if cursor.fetchone():
                    raise ValueError(f"El aula {aula_to_update} ya está asignada en este grado y turno para el año escolar actual (otra sección).")

            progress_callback.emit(80, "Actualizando sección...")
            cursor.execute("""
                UPDATE SECCION SET
                    cedula_docente_guia = %s,
                    aula_asignada = %s,
                    capacidad_maxima = %s
                WHERE codigo = %s AND codigo_ano_escolar = %s
            """, (
                docente, aula_to_update, capacidad_maxima,
                codigo_seccion, codigo_ano_escolar
            ))

            if cursor.rowcount == 0:
                raise ValueError(f"No se encontró la sección {codigo_seccion} para actualizar o no hubo cambios.")

            conn.commit()
            progress_callback.emit(100, "Sección actualizada correctamente.")
            return {"codigo_seccion": codigo_seccion}

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de PostgreSQL al actualizar sección: {e}", exc_info=True)
            raise Exception(f"Error en la base de datos al actualizar la sección: {e.pgerror or e}")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error inesperado al actualizar sección: {e}", exc_info=True)
            raise Exception(f"Ocurrió un error inesperado: {e}")
        finally:
            if conn:
                conn.close()

    def _handle_actualizar_seccion_result(self, result):
        QMessageBox.information(self, "Éxito",
                                 f"Sección {result['codigo_seccion']} actualizada correctamente.")
        self.cancelar_edicion() # Volver al modo asignación y limpiar
        self.cargar_secciones()

    def editar_seccion(self):
        selected_rows = self.tabla_secciones.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Vacía", "Por favor, seleccione una sección de la tabla para editar.")
            return
        if len(selected_rows) > 1:
            QMessageBox.warning(self, "Múltiples Selecciones", "Solo puede editar una sección a la vez. Por favor, seleccione solo una fila.")
            return

        row = selected_rows[0].row()
        codigo_seccion = self.tabla_secciones.item(row, 0).text() # Columna 0 es el código

        self._run_db_operation(
            self._perform_cargar_seccion_para_edicion,
            self._handle_cargar_seccion_para_edicion_result,
            self._handle_db_error,
            codigo_seccion=codigo_seccion,
            db_config=self.db_config # Pasar db_config
        )

    def _perform_cargar_seccion_para_edicion(self, progress_callback, codigo_seccion, db_config): # Aceptar db_config
        conn = None
        try:
            conn = conectar_db(db_config) # Pasar db_config
            cursor = conn.cursor()
            progress_callback.emit(10, "Cargando datos de la sección...")
            cursor.execute("""
                SELECT codigo_grado, letra, turno, cedula_docente_guia, aula_asignada, capacidad_maxima
                FROM SECCION
                WHERE codigo = %s
            """, (codigo_seccion,))
            seccion_data = cursor.fetchone()
            if not seccion_data:
                raise ValueError(f"No se encontró la sección con código {codigo_seccion}.")
            progress_callback.emit(100, "Datos de la sección cargados.")
            return {"codigo_seccion": codigo_seccion, "data": seccion_data}
        finally:
            if conn:
                conn.close()

    def _handle_cargar_seccion_para_edicion_result(self, result):
        codigo_seccion = result["codigo_seccion"]
        grado, letra, turno, docente_cedula, aula, capacidad_maxima = result["data"]

        self.input_grado.setText(str(grado))
        self.input_letra.setCurrentText(letra)
        self.input_turno.setCurrentText("Mañana (M)" if turno == 'M' else "Tarde (T)")
        self.input_capacidad_maxima.setText(str(capacidad_maxima))
        self.input_aula.setText(aula if aula else "")

        # Seleccionar el docente en el ComboBox
        index = self.input_docente_combo.findData(docente_cedula)
        if index != -1:
            self.input_docente_combo.setCurrentIndex(index)
        else:
            # Si el docente no está en la lista (ej. fue eliminado), seleccionar la opción por defecto
            self.input_docente_combo.setCurrentIndex(0)
            QMessageBox.warning(self, "Docente no encontrado", f"El docente con cédula {docente_cedula} no se encontró en la lista. Por favor, seleccione uno nuevo.")

        self.seccion_editando_codigo = codigo_seccion
        self._update_buttons_state() # Actualizar UI al modo edición

    def cancelar_edicion(self):
        self.seccion_editando_codigo = None
        self.limpiar_formulario()
        self._update_buttons_state() # Volver al modo asignación

    def eliminar_seccion(self):
        selected_rows = self.tabla_secciones.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Vacía", "Por favor, seleccione al menos una sección de la tabla para eliminar.")
            return

        codigos_a_eliminar = []
        for row_index in selected_rows:
            codigos_a_eliminar.append(self.tabla_secciones.item(row_index.row(), 0).text())

        if len(codigos_a_eliminar) == 1:
            msg_text = f"¿Está seguro de que desea eliminar la sección '{codigos_a_eliminar[0]}'? Esta acción no se puede deshacer."
        else:
            msg_text = f"¿Está seguro de que desea eliminar las {len(codigos_a_eliminar)} secciones seleccionadas? Esta acción no se puede deshacer."

        reply = QMessageBox.question(self, "Confirmar Eliminación",
                                     msg_text,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self._run_db_operation(
                self._perform_eliminar_seccion,
                self._handle_eliminar_seccion_result,
                self._handle_db_error,
                codigos_seccion=codigos_a_eliminar, # Pasar la lista de códigos
                db_config=self.db_config # Pasar db_config
            )

    def _perform_eliminar_seccion(self, progress_callback, codigos_seccion, db_config): # Aceptar db_config
        conn = None
        try:
            conn = conectar_db(db_config) # Pasar db_config
            cursor = conn.cursor()
            
            deleted_count = 0
            failed_deletions = []

            for i, codigo in enumerate(codigos_seccion):
                progress_callback.emit(int((i / len(codigos_seccion)) * 100), f"Eliminando sección {codigo}...")
                try:
                    cursor.execute("DELETE FROM SECCION WHERE codigo = %s", (codigo,))
                    if cursor.rowcount > 0:
                        deleted_count += 1
                    else:
                        failed_deletions.append(f"Sección {codigo} no encontrada.")
                except psycopg2.Error as e:
                    # Capturar errores individuales de eliminación (ej. FK)
                    if "violates foreign key constraint" in str(e):
                        failed_deletions.append(f"Sección {codigo}: No se puede eliminar porque tiene datos relacionados. ({e.pgcode})")
                    else:
                        failed_deletions.append(f"Sección {codigo}: Error de base de datos. ({e.pgcode})")
                    logger.error(f"Error al eliminar sección {codigo}: {e}", exc_info=True)
                    # No hacer rollback aquí, para intentar eliminar las demás
            
            conn.commit() # Commit al final de todas las operaciones
            progress_callback.emit(100, "Operación de eliminación completada.")

            if failed_deletions:
                error_msg = "Algunas secciones no pudieron ser eliminadas:\n" + "\n".join(failed_deletions)
                raise Exception(error_msg)
            
            return {"deleted_count": deleted_count}

        except Exception as e:
            if conn:
                conn.rollback() # Rollback si hay un error general o si se lanza una excepción personalizada
            logger.error(f"Error inesperado al eliminar secciones: {e}", exc_info=True)
            raise Exception(f"Ocurrió un error inesperado durante la eliminación: {e}")
        finally:
            if conn:
                conn.close()

    def _handle_eliminar_seccion_result(self, result):
        deleted_count = result.get("deleted_count", 0)
        QMessageBox.information(self, "Éxito",
                                 f"{deleted_count} sección(es) eliminada(s) correctamente.")
        self.cargar_secciones() # Recargar la tabla

    def _get_available_aula_db(self, grado, cursor):
        """
        Obtiene un aula disponible para el grado especificado usando el cursor proporcionado.
        """
        rango_base = int(grado) * 100
        rango_min = rango_base
        rango_max = rango_base + 99

        cursor.execute("""
            SELECT aula_asignada FROM SECCION
            WHERE aula_asignada BETWEEN %s AND %s
            ORDER BY aula_asignada DESC LIMIT 1
        """, (str(rango_min), str(rango_max)))

        ultima_aula = cursor.fetchone()
        if ultima_aula is None:
            return str(rango_min)
        else:
            nueva_aula = int(ultima_aula[0]) + 1
            return str(nueva_aula) if nueva_aula <= rango_max else None

    def go_to_first_page(self):
        if self.current_page > 1:
            self.current_page = 1
            self.cargar_secciones()

    def go_to_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.cargar_secciones()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.cargar_secciones()

    def go_to_last_page(self):
        if self.current_page < self.total_pages:
            self.current_page = self.total_pages
            self.cargar_secciones()

    def cargar_secciones(self, show_progress_dialog=True):
        offset = (self.current_page - 1) * self.page_size
        limit = self.page_size
        search_term = self.search_term

        self._run_db_operation(
            self._perform_cargar_secciones,
            self._handle_cargar_secciones_result,
            self._handle_db_error,
            show_progress_dialog=show_progress_dialog,
            offset=offset, limit=limit, search_term=search_term,
            db_config=self.db_config # Pasar db_config
        )

    def _perform_cargar_secciones(self, progress_callback, offset, limit, search_term, db_config): # Aceptar db_config
        conn = None
        try:
            conn = conectar_db(db_config) # Pasar db_config
            cursor = conn.cursor()
            
            # Construir la cláusula WHERE para la búsqueda
            where_clause = ""
            params = []
            if search_term:
                search_pattern = f"%{search_term}%"
                where_clause = """
                    WHERE s.codigo ILIKE %s OR s.codigo_grado::text ILIKE %s OR s.letra ILIKE %s OR s.aula_asignada ILIKE %s OR p.nombres ILIKE %s OR p.apellidos ILIKE %s
                """
                params = [search_pattern] * 6 # Repetir el patrón para cada columna

            # Consulta para obtener el total de registros (para paginación)
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM SECCION s
                JOIN PERSONAL p ON s.cedula_docente_guia = p.cedula
                {where_clause}
            """, params)
            total_records = cursor.fetchone()[0]

            progress_callback.emit(20, "Cargando secciones...")
            # Consulta para obtener los registros de la página actual
            cursor.execute(f"""
                SELECT s.codigo, s.codigo_grado, s.letra, s.turno, s.aula_asignada, 
                        p.nombres || ' ' || p.apellidos || ' (' || s.cedula_docente_guia || ')' as docente_info,
                        s.capacidad_maxima
                FROM SECCION s
                JOIN PERSONAL p ON s.cedula_docente_guia = p.cedula
                {where_clause}
                ORDER BY s.codigo_grado, s.letra
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            secciones = cursor.fetchall()
            
            progress_callback.emit(100, "Secciones cargadas.")
            return {"secciones": secciones, "total_records": total_records}
        except psycopg2.Error as e:
            logger.error(f"Error de PostgreSQL al cargar secciones: {e}", exc_info=True)
            raise Exception(f"Error en la base de datos al cargar las secciones: {e.pgerror or e}")
        except Exception as e:
            logger.error(f"Error inesperado al cargar secciones: {e}", exc_info=True)
            raise Exception(f"Ocurrió un error inesperado al cargar las secciones: {e}")
        finally:
            if conn:
                conn.close()

    def _handle_cargar_secciones_result(self, result):
        secciones = result["secciones"]
        self.total_records = result["total_records"]
        self.total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if self.total_pages == 0: # Si no hay registros, al menos 1 página
            self.total_pages = 1
            self.current_page = 1 # Asegurarse de que la página actual sea 1

        self.tabla_secciones.setRowCount(len(secciones))
        for row_idx, row_data in enumerate(secciones):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(str(col_data))
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.tabla_secciones.setItem(row_idx, col_idx, item)
        
        self._update_buttons_state() # Actualizar estado de botones de paginación y otros

    def _handle_db_error(self, error_tuple):
        exctype, value, traceback_str = error_tuple
        QMessageBox.critical(self, "Error de Operación", f"Ha ocurrido un error durante la operación:\n\n{value}\n\nLos detalles técnicos han sido registrados en el archivo de log.")

    def limpiar_formulario(self):
        self.input_grado.clear()
        self.input_letra.setCurrentIndex(0)
        self.input_turno.setCurrentIndex(0)
        self.input_docente_combo.setCurrentIndex(0)
        self.input_capacidad_maxima.clear()
        self.input_aula.clear()
        self._clear_error_style(self.input_grado)
        self._clear_error_style(self.input_docente_combo)
        self._clear_error_style(self.input_capacidad_maxima)

    def go_back_to_menu(self):
        """
        Cierra la ventana actual y emite la señal 'closed' para que
        la ventana principal (GeneralMainWindow) pueda volver a mostrarse.
        """
        self.closed.emit()
        self.close()

    def closeEvent(self, event):
        """
        Sobrescribe el evento de cierre para emitir la señal 'closed'.
        """
        self.closed.emit()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Simular una configuración de DB y datos de usuario para probar
    test_db_config = {
        'host': 'localhost',
        'database': 'bd', # Asegúrate de que esta DB exista y el usuario tenga permisos
        'user': 'postgres',
        'password': '12345678', # ¡IMPORTANTE! Reemplaza con tu contraseña real
        'port': '5432'
    }

    test_user_data = {
        'id': 1,
        'username': 'testuser',
        'role': 'admin'
    }

    # NOTA: La función setup_database_grupo_actividad() no está en este archivo.
    # Si es necesaria para la configuración inicial de la BD, debe ser importada o definida aquí.
    # Para la ejecución de este módulo de forma independiente, asegúrate de que las tablas existan.

    ventana = ModuloInstitucion(test_db_config, test_user_data)
    ventana.show()
    sys.exit(app.exec())
