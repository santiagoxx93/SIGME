import sys
import psycopg2
from psycopg2 import Error
import re
import os # Importar os para manejo de archivos
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QSizePolicy, QFormLayout, QComboBox, QDateEdit,
    QTextEdit, QGroupBox, QFileDialog # Añadir QFileDialog
)
from PyQt6.QtCore import Qt, QDate, QSize, pyqtSignal # Añadir pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QIntValidator, QPixmap, QImage # Añadir QImage y QPixmap


class DBManager:
    # Modificado: Ahora acepta db_config en el constructor
    def __init__(self, db_config):
        self.host = db_config.get('host')
        self.database = db_config.get('database')
        self.user = db_config.get('user')
        self.password = db_config.get('password')
        self.port = db_config.get('port')
        self.conn = None

    def connect(self):
        """Establece una conexión a la base de datos PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            self.conn.autocommit = True
            print("Conexión a la base de datos exitosa.")
            return True
        except Error as e:
            print(f"Error al conectar a la base de datos: {e}")
            self.conn = None
            return False

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")

    def execute_query(self, query, params=None, fetch_one=False):
        """Ejecuta una consulta SQL y maneja la conexión/errores."""
        if not self.conn or self.conn.closed: # Añadido self.conn.closed para re-conexión robusta
            print("No hay conexión activa a la base de datos. Intentando reconectar...")
            if not self.connect():
                QMessageBox.critical(None, "Error de Conexión",
                                     "No se pudo conectar a la base de datos. Verifique la configuración o que el servidor esté activo.")
                return None

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    if fetch_one:
                        return cur.fetchone()
                    return cur.fetchall()
                else:
                    return True
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            QMessageBox.critical(None, "Error en la Base de Datos",
                                 f"Ocurrió un error al ejecutar la operación en la base de datos:\n{e}\nPor favor, contacte a soporte.")
            # Añadir rollback en caso de error en operaciones DML
            if self.conn:
                self.conn.rollback()
            return None


class MatriculaApp(QMainWindow):
    closed = pyqtSignal() # Señal para indicar que el módulo se cerró

    # Modificado: Ahora acepta db_config y user_data
    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config # Almacenar la configuración de la BD
        self.user_data = user_data # Almacenar los datos del usuario
        self.setWindowTitle("SIGME2 - Gestión de Matrículas")
        
        # Modificado: Pasar db_config a DBManager
        self.db_manager = DBManager(self.db_config)
        if not self.db_manager.connect(): # Verificar conexión al inicio
            sys.exit(1) # Salir si no se puede conectar a la base de datos

        # Inicializar variables para almacenar datos binarios de fotos
        self.student_photo_data = None
        self.representante_photo_data = None

        self.init_ui()
        self.apply_styles()
        self.load_matriculas()
        self.clear_form() # Limpiar al inicio para asegurar el estado inicial

    def init_ui(self):
        """Inicializa los componentes de la interfaz de usuario."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Botón para volver al menú principal
        self.back_to_menu_button = QPushButton("Volver al Menú Principal")
        self.back_to_menu_button.setObjectName("backButton") # Para aplicar estilos específicos
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        main_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # --- QHBoxLayout para contener el formulario, los detalles y las fotos lado a lado ---
        top_section_layout = QHBoxLayout()
        main_layout.addLayout(top_section_layout)

        # --- Formulario de Entrada para Matrícula ---
        form_layout = QFormLayout()
        form_layout.setSpacing(10)  # Add spacing between form rows

        self.input_cedula_estudiante = QLineEdit()
        self.input_cedula_estudiante.setMaximumWidth(300)
        self.input_cedula_estudiante.setToolTip("Ingrese la cédula del estudiante (ej. V-12345678).")
        # Conectar al evento editingFinished para cargar detalles al perder foco
        self.input_cedula_estudiante.editingFinished.connect(lambda: self._load_student_details(self.input_cedula_estudiante.text()))
        form_layout.addRow("Cédula Estudiante:", self.input_cedula_estudiante)

        self.combo_ano_escolar = QComboBox()
        self.combo_ano_escolar.setMaximumWidth(300)
        self.combo_ano_escolar.setToolTip("Seleccione el año escolar de la matrícula.")
        form_layout.addRow("Año Escolar:", self.combo_ano_escolar)
        self.load_anos_escolares()

        self.combo_seccion = QComboBox()
        self.combo_seccion.setMaximumWidth(300)
        self.combo_seccion.setToolTip("Seleccione la sección a la que pertenece el estudiante.")
        form_layout.addRow("Sección:", self.combo_seccion)
        self.load_secciones()

        self.input_cedula_representante = QLineEdit()
        self.input_cedula_representante.setMaximumWidth(300)
        self.input_cedula_representante.setToolTip("Ingrese la cédula del representante legal del estudiante.")
        # Conectar al evento editingFinished para cargar detalles al perder foco
        self.input_cedula_representante.editingFinished.connect(lambda: self._load_representante_details(self.input_cedula_representante.text()))
        form_layout.addRow("Cédula Representante:", self.input_cedula_representante)

        self.date_fecha_matricula = QDateEdit(calendarPopup=True)
        self.date_fecha_matricula.setDate(QDate.currentDate())
        self.date_fecha_matricula.setMaximumWidth(300)
        self.date_fecha_matricula.setToolTip("Seleccione la fecha en que se realizó la matrícula.")
        form_layout.addRow("Fecha Matrícula:", self.date_fecha_matricula)

        self.input_numero_lista = QLineEdit()
        self.input_numero_lista.setValidator(QIntValidator())
        self.input_numero_lista.setMaximumWidth(300)
        self.input_numero_lista.setToolTip("Ingrese el número de lista del estudiante en esta sección (solo números).")
        form_layout.addRow("Número Lista:", self.input_numero_lista)

        self.combo_condicion_ingreso = QComboBox()
        self.combo_condicion_ingreso.addItems(["N=Nuevo", "R=Repitiente", "T=Trasladado", "P=Promovido"])
        self.combo_condicion_ingreso.setMaximumWidth(300)
        self.combo_condicion_ingreso.setToolTip(
            "Indique si el estudiante es Nuevo, Repitiente, Trasladado o Promovido.")
        form_layout.addRow("Condición Ingreso:", self.combo_condicion_ingreso)

        self.input_procedencia = QLineEdit()
        self.input_procedencia.setMaximumWidth(300)
        self.input_procedencia.setToolTip("Indique la institución o lugar de procedencia del estudiante.")
        form_layout.addRow("Procedencia:", self.input_procedencia)

        self.input_ano_cursa = QLineEdit()
        self.input_ano_cursa.setValidator(QIntValidator(1, 6))
        self.input_ano_cursa.setMaximumWidth(300)
        self.input_ano_cursa.setToolTip("Ingrese el año que el estudiante cursa actualmente (ej. 1, 2, 3).")
        form_layout.addRow("Año que Cursa:", self.input_ano_cursa)

        self.input_ano_inicio_cursante = QLineEdit()
        self.input_ano_inicio_cursante.setValidator(QIntValidator(1900, 2100))
        self.input_ano_inicio_cursante.setMaximumWidth(300)
        self.input_ano_inicio_cursante.setToolTip("Ingrese el año de inicio del cursante (ej. 2023).")
        form_layout.addRow("Año Inicio Cursante:", self.input_ano_inicio_cursante)

        self.combo_estado_matricula = QComboBox()
        self.combo_estado_matricula.addItems(["A=Activa", "R=Retirada"])
        self.combo_estado_matricula.setMaximumWidth(300)
        self.combo_estado_matricula.setToolTip("Define el estado actual de la matrícula: Activa o Retirada.")
        self.combo_estado_matricula.currentIndexChanged.connect(self._handle_estado_matricula_change) # Conectar para habilitar/deshabilitar campos de retiro
        form_layout.addRow("Estado Matrícula:", self.combo_estado_matricula)

        self.input_observaciones = QTextEdit()
        self.input_observaciones.setFixedHeight(50)
        self.input_observaciones.setMaximumWidth(300)
        self.input_observaciones.setToolTip("Notas adicionales o comentarios sobre la matrícula.")
        form_layout.addRow("Observaciones:", self.input_observaciones)

        self.date_fecha_retiro = QDateEdit(calendarPopup=True)
        self.date_fecha_retiro.setSpecialValueText("No Retirado")
        self.date_fecha_retiro.setDate(QDate(2000, 1, 1))
        self.date_fecha_retiro.setEnabled(False)
        self.date_fecha_retiro.setMaximumWidth(300)
        self.date_fecha_retiro.setToolTip("Fecha en la que el estudiante fue retirado de la matrícula.")
        form_layout.addRow("Fecha Retiro:", self.date_fecha_retiro)

        self.input_motivo_retiro = QLineEdit()
        self.input_motivo_retiro.setEnabled(False)
        self.input_motivo_retiro.setMaximumWidth(300)
        self.input_motivo_retiro.setToolTip("Motivo por el cual el estudiante fue retirado de la matrícula.")
        form_layout.addRow("Motivo Retiro:", self.input_motivo_retiro)

        top_section_layout.addLayout(form_layout)
        top_section_layout.addStretch() # MODIFICADO: Agrega espacio elástico antes del cuadro de detalles


        # --- QGroupBox para Detalles del Estudiante y Representante ---
        self.details_group_box = QGroupBox("DETALLES")
        self.details_group_box.setObjectName("details_group_box")
        details_layout = QVBoxLayout(self.details_group_box)
        details_layout.setSpacing(3) # Adjusted spacing for labels inside the group box
        self.details_group_box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.details_group_box.setMinimumWidth(350)
        self.details_group_box.setMaximumWidth(400)
        self.details_group_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Título y etiquetas para Detalles del Estudiante
        student_details_title = QLabel("ESTUDIANTE")
        student_details_title.setObjectName("student_details_title") # Add object name for specific styling
        details_layout.addWidget(student_details_title, alignment=Qt.AlignmentFlag.AlignCenter) # Centered
        self.label_estudiante_nombre = QLabel("Nombre: ")
        self.label_estudiante_genero = QLabel("Género: ")
        self.label_estudiante_fecha_nac = QLabel("Fecha Nac.: ")
        self.label_estudiante_telefono = QLabel("Teléfono: ")
        self.label_estudiante_correo = QLabel("Correo: ")
        self.label_estudiante_direccion = QLabel("Dirección: ")

        details_layout.addWidget(self.label_estudiante_nombre)
        details_layout.addWidget(self.label_estudiante_genero)
        details_layout.addWidget(self.label_estudiante_fecha_nac)
        details_layout.addWidget(self.label_estudiante_telefono)
        details_layout.addWidget(self.label_estudiante_correo)
        details_layout.addWidget(self.label_estudiante_direccion)
        details_layout.addSpacing(8) # Adjusted space between student and representative details

        # Título y etiquetas para Detalles del Representante
        representante_details_title = QLabel("REPRESENTANTE")
        representante_details_title.setObjectName("representante_details_title") # Add object name for specific styling
        details_layout.addWidget(representante_details_title, alignment=Qt.AlignmentFlag.AlignCenter) # Centered
        self.label_representante_nombre = QLabel("Nombre: ")
        self.label_representante_parentesco = QLabel("Parentesco: ")
        self.label_representante_telefono = QLabel("Teléfono: ")
        self.label_representante_correo = QLabel("Correo: ")
        self.label_representante_ocupacion = QLabel("Ocupación: ")

        details_layout.addWidget(self.label_representante_nombre)
        details_layout.addWidget(self.label_representante_parentesco)
        details_layout.addWidget(self.label_representante_telefono)
        details_layout.addWidget(self.label_representante_correo)
        details_layout.addWidget(self.label_representante_ocupacion)

        top_section_layout.addWidget(self.details_group_box)
        top_section_layout.addStretch() # Ya estaba aquí, empuja las fotos a la derecha


        # --- QGroupBox para Fotos del Estudiante y Representante ---
        self.photo_group_box = QGroupBox("FOTOS")
        self.photo_group_box.setObjectName("photo_group_box")
        photo_layout = QVBoxLayout(self.photo_group_box)
        photo_layout.setSpacing(8) # Spacing between elements within the photo group box
        self.photo_group_box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.photo_group_box.setMinimumWidth(250)
        self.photo_group_box.setMaximumWidth(300) # Adjusted max width for photos
        self.photo_group_box.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding) # Fixed width, expanding height

        # Foto del Estudiante
        student_photo_title = QLabel("Estudiante")
        student_photo_title.setObjectName("student_photo_title") # Add object name for specific styling
        student_photo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_layout.addWidget(student_photo_title)

        self.label_student_photo = QLabel("No Photo")
        self.label_student_photo.setFixedSize(200, 200) # Fixed size for the photo display area
        self.label_student_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_student_photo.setStyleSheet("background-color: #f0f0f0; border: 1px dashed #ccc; color: #888;")
        photo_layout.addWidget(self.label_student_photo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_upload_student_photo = QPushButton("Subir Foto Estudiante")
        self.btn_upload_student_photo.clicked.connect(lambda: self._upload_photo(self.label_student_photo, 'student'))
        photo_layout.addWidget(self.btn_upload_student_photo)

        photo_layout.addSpacing(10) # Adjusted space between student and representative photos

        # Foto del Representante
        representante_photo_title = QLabel("Representante")
        representante_photo_title.setObjectName("representante_photo_title") # Add object name for specific styling
        representante_photo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_layout.addWidget(representante_photo_title)

        self.label_representante_photo = QLabel("No Photo")
        self.label_representante_photo.setFixedSize(200, 200) # Fixed size for the photo display area
        self.label_representante_photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_representante_photo.setStyleSheet("background-color: #f0f0f0; border: 1px dashed #ccc; color: #888;")
        photo_layout.addWidget(self.label_representante_photo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_upload_representante_photo = QPushButton("Subir Foto Representante")
        self.btn_upload_representante_photo.clicked.connect(lambda: self._upload_photo(self.label_representante_photo, 'representante'))
        photo_layout.addWidget(self.btn_upload_representante_photo)

        photo_layout.addStretch() # Pushes content to the top

        top_section_layout.addWidget(self.photo_group_box)


        # --- Botones de Acción ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15) # Add spacing between buttons
        self.btn_agregar = QPushButton("Agregar Matrícula")
        self.btn_agregar.clicked.connect(self.add_matricula)
        self.btn_agregar.setToolTip("Añade una nueva matrícula a la base de datos.")
        button_layout.addWidget(self.btn_agregar)

        self.btn_actualizar = QPushButton("Actualizar Matrícula")
        self.btn_actualizar.clicked.connect(self.update_matricula)
        self.btn_actualizar.setEnabled(False)
        self.btn_actualizar.setToolTip("Actualiza la matrícula seleccionada en la tabla.")
        button_layout.addWidget(self.btn_actualizar)

        self.btn_eliminar = QPushButton("Eliminar Matrícula")
        self.btn_eliminar.clicked.connect(self.delete_matricula)
        self.btn_eliminar.setEnabled(False)
        self.btn_eliminar.setToolTip("Elimina la matrícula seleccionada de la base de datos.")
        button_layout.addWidget(self.btn_eliminar)

        self.btn_activar_retiro = QPushButton("Activar Retiro")
        self.btn_activar_retiro.clicked.connect(self._activate_retiro_mode)
        self.btn_activar_retiro.setToolTip("Habilita los campos de Fecha y Motivo de Retiro.")
        button_layout.addWidget(self.btn_activar_retiro)

        self.btn_limpiar = QPushButton("Limpiar Campos")
        self.btn_limpiar.clicked.connect(self.clear_form)
        self.btn_limpiar.setToolTip("Borra todo el contenido del formulario.")
        button_layout.addWidget(self.btn_limpiar)

        main_layout.addLayout(button_layout)
        main_layout.addSpacing(15) # Add space between buttons and table

        # --- Tabla de Matrículas ---
        self.table_widget = QTableWidget()
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_widget.itemSelectionChanged.connect(self.on_table_selection_changed)

        self.table_widget.setColumnCount(17) # Aumentar el conteo de columnas para las 2 fotos
        self.table_widget.setHorizontalHeaderLabels([
            "ID", "Cédula Est.", "Año Escolar", "Sección", "Cédula Repr.", "Fecha Mat.",
            "Nro. Lista", "Condición Ingreso", "Procedencia", "Año Cursa",
            "Año Inicio Curs.", "Estado Mat.", "Observaciones", "Fecha Retiro", "Motivo Retiro",
            "Foto Estudiante (Oculta)", "Foto Representante (Oculta)" # Nombres para las columnas ocultas
        ])
        self.table_widget.setColumnHidden(0, True) # Ocultar la columna ID
        # Ocultar las columnas de las fotos, ya que solo almacenan datos binarios
        self.table_widget.setColumnHidden(15, True) # Columna Foto Estudiante
        self.table_widget.setColumnHidden(16, True) # Columna Foto Representante

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.setColumnWidth(0, 0)

        main_layout.addWidget(self.table_widget)

        # Conectar señales para actualizar los detalles dinámicamente
        # Ya no necesitamos estas conexiones directas si usamos editingFinished en los QLineEdits
        # self.input_cedula_estudiante.textChanged.connect(self._update_student_and_rep_details_from_input)
        # self.input_cedula_representante.textChanged.connect(self._update_student_and_rep_details_from_input)

    def apply_styles(self):
        """Aplica los estilos visuales a la ventana y sus widgets."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#e4eaf4"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1c355b"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1c355b"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#7089a7"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

        self.setPalette(palette)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #e4eaf4;
            }
            QLabel {
                color: #1c355b;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                border: 1px solid #b3cbdc;
                border-radius: 4px;
                padding: 5px;
                background-color: #FFFFFF;
                color: #1c355b;
            }
            QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QTextEdit:disabled {
                background-color: #e0e0e0;
                color: #6a6a6a;
            }
            QPushButton {
                background-color: #1c355b;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7089a7;
            }
            QPushButton:disabled {
                background-color: #b3cbdc;
                color: #AAAAAA;
            }
            QTableWidget {
                border: 1px solid #b3cbdc;
                gridline-color: #b3cbdc;
                background-color: #FFFFFF;
                selection-background-color: #b3cbdc;
                color: #1c355b;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget QHeaderView::section {
                background-color: #1c355b;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #b3cbdc;
                font-weight: bold;
            }
            /* Estilo para el QGroupBox de Detalles (el "cuadro negro") */
            QGroupBox#details_group_box { /* Use ID selector for specificity */
                background-color: #1c355b;
                border: 2px solid #7089a7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 20px;
                padding-left: 10px;
                padding-right: 10px;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
            }
            QGroupBox#details_group_box::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
                background-color: #7089a7;
                color: #FFFFFF;
                border-radius: 5px;
            }
            /* Estilo para las etiquetas dentro del QGroupBox de Detalles para asegurar el color blanco */
            QGroupBox#details_group_box QLabel {
                color: #FFFFFF;
                font-size: 13px; /* Aumentar el tamaño de la fuente */
                font-weight: bold; /* Poner en negrita */
            }
            /* Estilo específico para los títulos dentro de details_group_box */
            QLabel#student_details_title, QLabel#representante_details_title {
                font-size: 14px;
                font-weight: bold;
                border-bottom: 1px solid #7089a7; /* Discreto borde inferior */
                padding-bottom: 3px; /* Espacio entre texto y borde */
                margin-bottom: 5px; /* Espacio después del borde */
            }

            /* Estilo para el QGroupBox de Fotos */
            QGroupBox#photo_group_box { /* Use ID selector for specificity */
                background-color: #e4eaf4; /* Lighter background for the photo box */
                border: 2px solid #b3cbdc;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 20px;
                padding-left: 10px;
                padding-right: 10px;
                color: #1c355b; /* Dark text for title */
                font-size: 16px;
                font-weight: bold;
            }
            QGroupBox#photo_group_box::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
                background-color: #b3cbdc; /* Lighter background for title */
                color: #1c355b;
                border-radius: 5px;
            }
            QGroupBox#photo_group_box QLabel {
                color: #1c355b; /* Darker text for labels inside photo group box */
                font-weight: normal; /* Keep normal weight for image labels */
            }
            /* Estilo específico para los títulos dentro de photo_group_box */
            QLabel#student_photo_title, QLabel#representante_photo_title {
                font-size: 13px; /* Slightly increased font size for distinction */
                font-weight: bold;
                border-bottom: 1px solid #b3cbdc; /* Discreto borde inferior */
                padding-bottom: 3px; /* Espacio entre texto y borde */
                margin-bottom: 5px; /* Espacio después del borde */
            }
            QPushButton#backButton {
                background-color: #5B9BD5; /* Un azul diferente para destacarlo */
                color: white;
                border-radius: 8px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 120px;
                margin-bottom: 10px; /* Espacio debajo del botón */
            }

            QPushButton#backButton:hover {
                background-color: #4A8BCD;
            }

            QPushButton#backButton:pressed {
                background-color: #3C7DBA;
            }
        """)


    def _prepare_cedula_for_db(self, cedula_input):
        """
        Prepara la cédula para ser usada en consultas de base de datos.
        Asegura que el formato sea 'V-XXXXXXXX' (o 'E-XXXXXXXX')
        normalizando el prefijo y eliminando cualquier formato adicional (puntos, espacios).
        """
        if not cedula_input:
            return None

        cleaned_cedula = re.sub(r'[.\s]', '', cedula_input).upper()

        if re.match(r'^[VE]-', cleaned_cedula):
            return cleaned_cedula
        elif cleaned_cedula.isdigit():
            # Si solo son dígitos, asume prefijo 'V-'
            return 'V-' + cleaned_cedula
        else:
            return None

    def _format_cedula_for_display(self, cedula_digits):
        """Formatea los dígitos de la cédula para visualización (V-XX.XXX.XXX)."""
        if not cedula_digits or not isinstance(cedula_digits, str):
            return cedula_digits

        # Eliminar cualquier formato existente para trabajar solo con números y el prefijo
        cleaned_cedula = re.sub(r'[.\s-]', '', cedula_digits).upper()

        if not cleaned_cedula:
            return ""

        prefix = ""
        if cleaned_cedula.startswith('V') or cleaned_cedula.startswith('E'):
            prefix = cleaned_cedula[0] + '-'
            digits_only = cleaned_cedula[1:]
        else:
            # Si no hay prefijo inicial, asumir 'V-'
            prefix = 'V-'
            digits_only = cleaned_cedula

        if len(digits_only) > 3:
            # Formato con puntos
            formatted_digits = '.'.join([digits_only[i:i + 3] for i in range(0, len(digits_only), 3)])
            return f"{prefix}{formatted_digits}"
        else:
            return f"{prefix}{digits_only}"


    def load_anos_escolares(self):
        """Carga los años escolares desde la base de datos en el QComboBox."""
        # Modificado: Se asume que db_manager ya está conectado
        query = "SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC;"
        anos = self.db_manager.execute_query(query)
        if anos:
            self.combo_ano_escolar.clear()
            for codigo, descripcion in anos:
                self.combo_ano_escolar.addItem(descripcion, codigo)

    def load_secciones(self):
        """Carga las secciones desde la base de datos en el QComboBox."""
        # Modificado: Se asume que db_manager ya está conectado
        query = "SELECT s.codigo, g.nombre || ' ' || s.letra FROM SECCION s JOIN GRADO g ON s.codigo_grado = g.codigo ORDER BY g.nombre, s.letra;"
        secciones = self.db_manager.execute_query(query)
        if secciones:
            self.combo_seccion.clear()
            for codigo, display_name in secciones:
                self.combo_seccion.addItem(display_name, codigo)

    def _load_student_details(self, cedula_estudiante_raw):
        self.label_estudiante_nombre.setText("Nombre: ")
        self.label_estudiante_genero.setText("Género: ")
        self.label_estudiante_fecha_nac.setText("Fecha Nac.: ")
        self.label_estudiante_telefono.setText("Teléfono: ")
        self.label_estudiante_correo.setText("Correo: ")
        self.label_estudiante_direccion.setText("Dirección: ")

        cedula_estudiante = self._prepare_cedula_for_db(cedula_estudiante_raw)
        if not cedula_estudiante:
            return

        query = """
            SELECT nombres, apellidos, genero, fecha_nacimiento, telefono, correo, direccion
            FROM ESTUDIANTE
            WHERE cedula = %s;
        """
        student_data = self.db_manager.execute_query(query, (cedula_estudiante,), fetch_one=True)
        if student_data:
            nombres, apellidos, genero, fecha_nacimiento, telefono, correo, direccion = student_data
            self.label_estudiante_nombre.setText(
                f"Nombre: {nombres if nombres else ''} {apellidos if apellidos else ''}")
            self.label_estudiante_genero.setText(f"Género: {genero if genero else 'N/A'}")
            self.label_estudiante_fecha_nac.setText(
                f"Fecha Nac.: {fecha_nacimiento.strftime('%Y-%m-%d') if fecha_nacimiento else 'N/A'}")
            self.label_estudiante_telefono.setText(f"Teléfono: {telefono if telefono else 'N/A'}")
            self.label_estudiante_correo.setText(f"Correo: {correo if correo else 'N/A'}")
            self.label_estudiante_direccion.setText(f"Dirección: {direccion if direccion else 'N/A'}")

    def _load_representante_details(self, cedula_representante_raw):
        self.label_representante_nombre.setText("Nombre: ")
        self.label_representante_parentesco.setText("Parentesco: ")
        self.label_representante_telefono.setText("Teléfono: ")
        self.label_representante_correo.setText("Correo: ")
        self.label_representante_ocupacion.setText("Ocupación: ")

        cedula_representante = self._prepare_cedula_for_db(cedula_representante_raw)
        if not cedula_representante:
            return

        query = """
            SELECT nombres, apellidos, parentesco, telefono, correo, ocupacion
            FROM REPRESENTANTE
            WHERE cedula = %s;
        """
        representante_data = self.db_manager.execute_query(query, (cedula_representante,), fetch_one=True)
        if representante_data:
            nombres, apellidos, parentesco, telefono, correo, ocupacion = representante_data
            self.label_representante_nombre.setText(
                f"Nombre: {nombres if nombres else ''} {apellidos if apellidos else ''}")
            self.label_representante_parentesco.setText(f"Parentesco: {parentesco if parentesco else 'N/A'}")
            self.label_representante_telefono.setText(f"Teléfono: {telefono if telefono else 'N/A'}")
            self.label_representante_correo.setText(f"Correo: {correo if correo else 'N/A'}")
            self.label_representante_ocupacion.setText(f"Ocupación: {ocupacion if ocupacion else 'N/A'}")

    def _handle_estado_matricula_change(self, index):
        selected_text = self.combo_estado_matricula.currentText()
        if selected_text.startswith('R'): # Retirada
            self.date_fecha_retiro.setEnabled(True)
            self.input_motivo_retiro.setEnabled(True)
        else:
            self.date_fecha_retiro.setEnabled(False)
            self.input_motivo_retiro.setEnabled(False)
            self.date_fecha_retiro.setDate(QDate(2000, 1, 1)) # Fecha ficticia para cuando no aplica
            self.input_motivo_retiro.clear()

    def _upload_photo(self, target_label: QLabel, photo_type: str):
        """
        Permite al usuario subir una foto y la muestra en el QLabel especificado,
        y almacena los datos binarios en la variable de instancia correspondiente.
        """
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Seleccionar Foto", "", "Imágenes (*.png *.jpg *.jpeg *.gif)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                target_label.setPixmap(pixmap.scaled(
                    target_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                ))
                target_label.setText("") # Clear "No Photo" text

                # Convertir la imagen a bytes y almacenarla
                try:
                    with open(file_path, 'rb') as f:
                        photo_bytes = f.read()

                    if photo_type == 'student':
                        self.student_photo_data = photo_bytes
                    elif photo_type == 'representante':
                        self.representante_photo_data = photo_bytes
                except Exception as e:
                    QMessageBox.warning(self, "Error de Archivo", f"No se pudo leer la imagen: {e}")
                    # Reiniciar los datos si hubo un error al leer
                    if photo_type == 'student':
                        self.student_photo_data = None
                    elif photo_type == 'representante':
                        self.representante_photo_data = None
            else:
                QMessageBox.warning(self, "Error de Carga", "No se pudo cargar la imagen seleccionada.")

    def _clear_photos(self):
        """Limpia las etiquetas de visualización de fotos y los datos binarios almacenados."""
        self.label_student_photo.clear()
        self.label_student_photo.setText("No Photo")
        self.label_representante_photo.clear()
        self.label_representante_photo.setText("No Photo")
        self.student_photo_data = None
        self.representante_photo_data = None

    def _load_photo_from_bytes(self, photo_bytes, target_label: QLabel):
        """Carga una QPixmap desde datos binarios y la muestra en el QLabel."""
        if photo_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(photo_bytes):
                target_label.setPixmap(pixmap.scaled(
                    target_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                ))
                target_label.setText("")
            else:
                target_label.setText("Error al cargar foto")
                print("Error al cargar QPixmap desde datos binarios.")
        else:
            target_label.clear()
            target_label.setText("No Photo")


    def _activate_retiro_mode(self):
        """Activa la opción de retiro de matrícula."""
        self.date_fecha_retiro.setEnabled(True)
        self.input_motivo_retiro.setEnabled(True)
        index = self.combo_estado_matricula.findText("R=Retirada")
        if index != -1:
            self.combo_estado_matricula.setCurrentIndex(index)

        if self.date_fecha_retiro.date() == QDate(2000, 1, 1) or self.date_fecha_retiro.date().isNull():
            self.date_fecha_retiro.setDate(QDate.currentDate())

        QMessageBox.information(self, "Activación", "Se activó la opción de retirar matrícula.")

    def clear_form(self):
        """Limpia todos los campos del formulario y restablece el estado de los botones."""
        self.input_cedula_estudiante.clear()
        self.input_cedula_representante.clear()

        self.label_estudiante_nombre.setText("Nombre: ")
        self.label_estudiante_genero.setText("Género: ")
        self.label_estudiante_fecha_nac.setText("Fecha Nac.: ")
        self.label_estudiante_telefono.setText("Teléfono: ")
        self.label_estudiante_correo.setText("Correo: ")
        self.label_estudiante_direccion.setText("Dirección: ")
        self.label_representante_nombre.setText("Nombre: ")
        self.label_representante_parentesco.setText("Parentesco: ")
        self.label_representante_telefono.setText("Teléfono: ")
        self.label_representante_correo.setText("Correo: ")
        self.label_representante_ocupacion.setText("Ocupación: ")

        # Restablecer los combobox
        self.combo_ano_escolar.setCurrentIndex(0)
        self.combo_seccion.setCurrentIndex(0)

        self.date_fecha_matricula.setDate(QDate.currentDate())
        self.input_numero_lista.clear()
        self.combo_condicion_ingreso.setCurrentIndex(0)
        self.input_procedencia.clear()
        self.input_ano_cursa.clear()
        self.input_ano_inicio_cursante.clear()

        index_activa = self.combo_estado_matricula.findText("A=Activa")
        if index_activa != -1:
            self.combo_estado_matricula.setCurrentIndex(index_activa)

        self.input_observaciones.clear()
        self.date_fecha_retiro.setDate(QDate(2000, 1, 1))
        self.date_fecha_retiro.setEnabled(False)
        self.input_motivo_retiro.clear()
        self.input_motivo_retiro.setEnabled(False)

        self._clear_photos() # Clear photos when clearing the form

        self.btn_agregar.setEnabled(True)
        self.btn_actualizar.setEnabled(False)
        self.btn_eliminar.setEnabled(False)
        self.table_widget.clearSelection()

    def load_matriculas(self):
        """Carga las matrículas existentes desde la base de datos y las muestra en la tabla."""
        self.table_widget.setRowCount(0)
        query = """
            SELECT
                m.id,
                m.cedula_estudiante,
                ae.descripcion AS ano_escolar_desc,
                g.nombre || ' ' || s.letra AS seccion_desc,
                m.cedula_representante,
                m.fecha_matricula,
                m.numero_lista,
                m.condicion_ingreso,
                m.procedencia,
                m.ano_que_cursa,
                m.ano_inicio_cursante,
                m.estado_matricula,
                m.observaciones,
                m.fecha_retiro,
                m.motivo_retiro,
                m.foto_estudiante,         -- Seleccionar foto de estudiante
                m.foto_representante       -- Seleccionar foto de representante
            FROM MATRICULA m
            LEFT JOIN ANO_ESCOLAR ae ON m.codigo_ano_escolar = ae.codigo
            LEFT JOIN SECCION s ON m.codigo_seccion = s.codigo
            LEFT JOIN GRADO g ON s.codigo_grado = g.codigo
            ORDER BY m.fecha_matricula DESC;
        """
        matriculas = self.db_manager.execute_query(query)
        if matriculas:
            self.table_widget.setRowCount(len(matriculas))
            for row_idx, row_data in enumerate(matriculas):
                # Los índices 15 y 16 son para foto_estudiante y foto_representante
                # No se muestran directamente en la tabla, pero se guardan para la selección
                foto_estudiante_bytes = row_data[15]
                foto_representante_bytes = row_data[16]

                # Guarda los datos binarios de las fotos en el UserRole del item ID (columna 0)
                item_id = QTableWidgetItem(str(row_data[0]))
                item_id.setData(Qt.ItemDataRole.UserRole, {
                    'foto_estudiante': foto_estudiante_bytes,
                    'foto_representante': foto_representante_bytes
                })
                item_id.setFlags(item_id.flags() & ~Qt.ItemFlag.ItemIsEditable) # Hacer no editable
                self.table_widget.setItem(row_idx, 0, item_id)


                # Llenar las otras columnas visibles de la tabla
                for col_idx in range(1, 15): # Columnas visibles (excluyendo el ID y las fotos)
                    data = row_data[col_idx]
                    item_text = ""
                    if col_idx in [1, 4]: # Cédulas
                        item_text = self._format_cedula_for_display(str(data)) if data else ""
                    elif isinstance(data, QDate):
                        item_text = data.toString(Qt.DateFormat.ISODate)
                    elif data is None:
                        item_text = ""
                    else:
                        item_text = str(data)

                    item = QTableWidgetItem(item_text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table_widget.setItem(row_idx, col_idx, item)


        self.table_widget.setColumnHidden(0, True) # Mantener el ID oculto
        self.table_widget.setColumnHidden(15, True) # Mantener Foto Estudiante oculta
        self.table_widget.setColumnHidden(16, True) # Mantener Foto Representante oculta

    def add_matricula(self):
        """Agrega una nueva matrícula a la base de datos."""
        cedula_estudiante_input = self.input_cedula_estudiante.text().strip()
        cedula_estudiante = self._prepare_cedula_for_db(cedula_estudiante_input)

        codigo_ano_escolar = self.combo_ano_escolar.currentData()
        codigo_seccion = self.combo_seccion.currentData()

        cedula_representante_input = self.input_cedula_representante.text().strip()
        cedula_representante = self._prepare_cedula_for_db(cedula_representante_input)

        fecha_matricula = self.date_fecha_matricula.date().toString(Qt.DateFormat.ISODate)
        numero_lista = self.input_numero_lista.text().strip()
        condicion_ingreso_display = self.combo_condicion_ingreso.currentText()
        condicion_ingreso = condicion_ingreso_display[0]
        procedencia = self.input_procedencia.text().strip()
        ano_cursa = self.input_ano_cursa.text().strip()
        ano_inicio_cursante = self.input_ano_inicio_cursante.text().strip()
        estado_matricula_display = self.combo_estado_matricula.currentText()
        estado_matricula = estado_matricula_display[0]
        observaciones = self.input_observaciones.toPlainText().strip()

        fecha_retiro = self.date_fecha_retiro.date().toString(Qt.DateFormat.ISODate)
        if self.date_fecha_retiro.date() == QDate(2000, 1,
                                                 1) or self.date_fecha_retiro.date().isNull() or not self.date_fecha_retiro.isEnabled():
            fecha_retiro = None
        motivo_retiro = self.input_motivo_retiro.text().strip()
        if not motivo_retiro:
            motivo_retiro = None

        # Validaciones
        if not (cedula_estudiante and codigo_ano_escolar and codigo_seccion and cedula_representante and
                fecha_matricula and numero_lista and condicion_ingreso and procedencia and ano_cursa and ano_inicio_cursante):
            QMessageBox.warning(self, "Campos Incompletos", "Por favor, complete todos los campos obligatorios.")
            return

        # Verificar existencia de estudiante y representante antes de insertar
        if not self.db_manager.execute_query("SELECT 1 FROM ESTUDIANTE WHERE cedula = %s", (cedula_estudiante,),
                                             fetch_one=True):
            QMessageBox.warning(self, "Validación",
                                 "La cédula del estudiante no existe. Por favor, registre al estudiante primero.")
            return
        if not self.db_manager.execute_query("SELECT 1 FROM REPRESENTANTE WHERE cedula = %s", (cedula_representante,),
                                             fetch_one=True):
            QMessageBox.warning(self, "Validación",
                                 "La cédula del representante no existe. Por favor, registre al representante primero.")
            return

        # Prepara los datos de las fotos (si no hay foto, envía None)
        foto_estudiante_bytes = self.student_photo_data
        foto_representante_bytes = self.representante_photo_data

        query = """
            INSERT INTO MATRICULA (
                cedula_estudiante, codigo_ano_escolar, codigo_seccion, cedula_representante,
                fecha_matricula, numero_lista, condicion_ingreso, procedencia,
                ano_que_cursa, ano_inicio_cursante, estado_matricula, observaciones,
                fecha_retiro, motivo_retiro, foto_estudiante, foto_representante
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (
            cedula_estudiante, codigo_ano_escolar, codigo_seccion, cedula_representante,
            fecha_matricula, int(numero_lista), condicion_ingreso, procedencia,
            int(ano_cursa), int(ano_inicio_cursante), estado_matricula, observaciones,
            fecha_retiro, motivo_retiro, foto_estudiante_bytes, foto_representante_bytes
        )

        if self.db_manager.execute_query(query, params):
            QMessageBox.information(self, "Éxito", "Matrícula agregada correctamente.")
            self.clear_form()
            self.load_matriculas()
        else:
            QMessageBox.critical(self, "Error", "No se pudo agregar la matrícula.")

    def update_matricula(self):
        """Actualiza una matrícula existente en la base de datos."""
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Actualizar Matrícula", "Por favor, seleccione una matrícula para actualizar.")
            return

        row_idx = selected_rows[0].row()
        matricula_id = self.table_widget.item(row_idx, 0).text()

        cedula_estudiante_input = self.input_cedula_estudiante.text().strip()
        cedula_estudiante = self._prepare_cedula_for_db(cedula_estudiante_input)

        codigo_ano_escolar = self.combo_ano_escolar.currentData()
        codigo_seccion = self.combo_seccion.currentData()

        cedula_representante_input = self.input_cedula_representante.text().strip()
        cedula_representante = self._prepare_cedula_for_db(cedula_representante_input)

        fecha_matricula = self.date_fecha_matricula.date().toString(Qt.DateFormat.ISODate)
        numero_lista = self.input_numero_lista.text().strip()
        condicion_ingreso_display = self.combo_condicion_ingreso.currentText()
        condicion_ingreso = condicion_ingreso_display[0]
        procedencia = self.input_procedencia.text().strip()
        ano_cursa = self.input_ano_cursa.text().strip()
        ano_inicio_cursante = self.input_ano_inicio_cursante.text().strip()
        estado_matricula_display = self.combo_estado_matricula.currentText()
        estado_matricula = estado_matricula_display[0]
        observaciones = self.input_observaciones.toPlainText().strip()

        fecha_retiro = self.date_fecha_retiro.date().toString(Qt.DateFormat.ISODate)
        if self.date_fecha_retiro.date() == QDate(2000, 1,
                                                 1) or self.date_fecha_retiro.date().isNull() or not self.date_fecha_retiro.isEnabled():
            fecha_retiro = None
        motivo_retiro = self.input_motivo_retiro.text().strip()
        if not motivo_retiro:
            motivo_retiro = None

        # Validaciones
        if not (cedula_estudiante and codigo_ano_escolar and codigo_seccion and cedula_representante and
                fecha_matricula and numero_lista and condicion_ingreso and procedencia and ano_cursa and ano_inicio_cursante):
            QMessageBox.warning(self, "Campos Incompletos", "Por favor, complete todos los campos obligatorios.")
            return

        # Prepara los datos de las fotos (si no hay foto, envía None)
        foto_estudiante_bytes = self.student_photo_data
        foto_representante_bytes = self.representante_photo_data

        query = """
            UPDATE MATRICULA SET
                cedula_estudiante = %s,
                codigo_ano_escolar = %s,
                codigo_seccion = %s,
                cedula_representante = %s,
                fecha_matricula = %s,
                numero_lista = %s,
                condicion_ingreso = %s,
                procedencia = %s,
                ano_que_cursa = %s,
                ano_inicio_cursante = %s,
                estado_matricula = %s,
                observaciones = %s,
                fecha_retiro = %s,
                motivo_retiro = %s,
                foto_estudiante = %s,
                foto_representante = %s
            WHERE id = %s;
        """
        params = (
            cedula_estudiante, codigo_ano_escolar, codigo_seccion, cedula_representante,
            fecha_matricula, int(numero_lista), condicion_ingreso, procedencia,
            int(ano_cursa), int(ano_inicio_cursante), estado_matricula, observaciones,
            fecha_retiro, motivo_retiro,
            foto_estudiante_bytes, foto_representante_bytes,
            int(matricula_id)
        )

        if self.db_manager.execute_query(query, params):
            QMessageBox.information(self, "Éxito", "Matrícula actualizada correctamente.")
            self.clear_form()
            self.load_matriculas()
        else:
            QMessageBox.critical(self, "Error", "No se pudo actualizar la matrícula.")

    def delete_matricula(self):
        """Elimina una matrícula de la base de datos."""
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Eliminar Matrícula", "Por favor, seleccione una matrícula para eliminar.")
            return

        row_idx = selected_rows[0].row()
        matricula_id = self.table_widget.item(row_idx, 0).text()

        reply = QMessageBox.question(self, "Confirmar Eliminación",
                                     "¿Está seguro de que desea eliminar esta matrícula?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            query = "DELETE FROM MATRICULA WHERE id = %s;"
            if self.db_manager.execute_query(query, (int(matricula_id),)):
                QMessageBox.information(self, "Éxito", "Matrícula eliminada correctamente.")
                self.clear_form()
                self.load_matriculas()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar la matrícula. "
                                                     "Asegúrese de que no haya registros dependientes.")

    def on_table_selection_changed(self):
        """Maneja el evento de selección de fila en la tabla, poblando el formulario."""
        selected_rows = self.table_widget.selectionModel().selectedRows()
        if selected_rows:
            row_idx = selected_rows[0].row()

            # Obtener los datos binarios de las fotos desde el UserRole del item ID
            item_id = self.table_widget.item(row_idx, 0)
            photo_data_dict = item_id.data(Qt.ItemDataRole.UserRole)

            if photo_data_dict:
                self.student_photo_data = photo_data_dict.get('foto_estudiante')
                self.representante_photo_data = photo_data_dict.get('foto_representante')
            else:
                self.student_photo_data = None
                self.representante_photo_data = None

            # Cargar los datos del formulario (columnas visibles)
            self.input_cedula_estudiante.setText(self.table_widget.item(row_idx, 1).text())
            # Cargar los detalles de estudiante/representante para asegurar que los campos de nombre/apellido se llenen
            self._load_student_details(self.input_cedula_estudiante.text())

            ano_escolar_desc = self.table_widget.item(row_idx, 2).text()
            index = self.combo_ano_escolar.findText(ano_escolar_desc)
            if index != -1:
                self.combo_ano_escolar.setCurrentIndex(index)

            seccion_desc = self.table_widget.item(row_idx, 3).text()
            index = self.combo_seccion.findText(seccion_desc)
            if index != -1:
                self.combo_seccion.setCurrentIndex(index)

            self.input_cedula_representante.setText(self.table_widget.item(row_idx, 4).text())
            self._load_representante_details(self.input_cedula_representante.text())

            fecha_matricula_str = self.table_widget.item(row_idx, 5).text()
            if fecha_matricula_str:
                self.date_fecha_matricula.setDate(QDate.fromString(fecha_matricula_str, Qt.DateFormat.ISODate))
            else:
                self.date_fecha_matricula.setDate(QDate.currentDate())

            self.input_numero_lista.setText(self.table_widget.item(row_idx, 6).text())

            condicion_ingreso_char = self.table_widget.item(row_idx, 7).text()
            for i in range(self.combo_condicion_ingreso.count()):
                if self.combo_condicion_ingreso.itemText(i).startswith(condicion_ingreso_char):
                    self.combo_condicion_ingreso.setCurrentIndex(i)
                    break

            self.input_procedencia.setText(self.table_widget.item(row_idx, 8).text())
            self.input_ano_cursa.setText(self.table_widget.item(row_idx, 9).text())
            self.input_ano_inicio_cursante.setText(self.table_widget.item(row_idx, 10).text())

            estado_matricula_char = self.table_widget.item(row_idx, 11).text()
            for i in range(self.combo_estado_matricula.count()):
                if self.combo_estado_matricula.itemText(i).startswith(estado_matricula_char):
                    self.combo_estado_matricula.setCurrentIndex(i)
                    break
            # Disparar el handler para habilitar/deshabilitar campos de retiro basado en el estado cargado
            self._handle_estado_matricula_change(self.combo_estado_matricula.currentIndex())


            self.input_observaciones.setText(self.table_widget.item(row_idx, 12).text())

            fecha_retiro_str = self.table_widget.item(row_idx, 13).text()
            if fecha_retiro_str:
                self.date_fecha_retiro.setDate(QDate.fromString(fecha_retiro_str, Qt.DateFormat.ISODate))

            self.input_motivo_retiro.setText(self.table_widget.item(row_idx, 14).text())

            # Cargar y mostrar las fotos desde los datos binarios
            self._load_photo_from_bytes(self.student_photo_data, self.label_student_photo)
            self._load_photo_from_bytes(self.representante_photo_data, self.label_representante_photo)


            self.btn_agregar.setEnabled(False)
            self.btn_actualizar.setEnabled(True)
            self.btn_eliminar.setEnabled(True)
        else:
            self.clear_form() # Limpiar formulario si no hay selección

    def go_back_to_menu(self):
        """
        Cierra la ventana actual y emite la señal 'closed' para que
        la ventana principal (GeneralMainWindow) pueda volver a mostrarse.
        """
        self.closed.emit()
        self.close()

    def closeEvent(self, event):
        """
        Sobrescribe el evento de cierre para emitir la señal 'closed' y cerrar la conexión a la BD.
        """
        if self.db_manager:
            self.db_manager.close()
        self.closed.emit() # Emitir la señal antes de cerrar la ventana
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Simular una configuración de DB y datos de usuario para probar
    test_db_config = {
        'host': 'localhost',
        'database': 'Sigme2', # Asegúrate de que esta DB exista y el usuario tenga permisos
        'user': 'postgres',
        'password': 'Diego-78', # ¡IMPORTANTE! Reemplaza con tu contraseña real
        'port': '5432'
    }

    test_user_data = {
        'id': 1,
        'username': 'testuser',
        'role': 'admin'
    }

    window = MatriculaApp(test_db_config, test_user_data)
    window.showMaximized() # Usar showMaximized para una mejor visualización inicial
    sys.exit(app.exec())
