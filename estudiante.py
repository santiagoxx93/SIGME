import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QMessageBox, 
                             QFormLayout, QTextEdit, QHeaderView, QFrame, 
                             QComboBox, QStackedWidget, QCheckBox, QDateEdit,
                             QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QRegularExpression
from PyQt6.QtGui import QFont, QPalette, QColor, QRegularExpressionValidator
from datetime import datetime
import re # Importar el módulo re para expresiones regulares

# --- Definición de la Paleta de Colores (Centralizada) ---
PRIMARY_COLOR = '#1c355b' # Azul oscuro fuerte
ACCENT_COLOR = '#7089a7'  # Azul grisáceo medio
LIGHT_BACKGROUND = '#e4eaf4' # Azul muy claro para fondos
TEXT_COLOR = '#333333' # Gris oscuro para texto
WHITE_COLOR = '#FFFFFF'
SUCCESS_COLOR = '#16a34a' # Verde
ERROR_COLOR = '#dc2626'   # Rojo
FONT_FAMILY = 'Arial'

# --- Definición de los Campos del Estudiante (Modelo de Datos) ---
STUDENT_FIELDS = [
    # DATOS PERSONALES
    ('cedula', {'label': 'Cédula:', 'type': 'entry', 'validation': 'cedula', 'required': True}),
    ('nacionalidad', {'label': 'Nacionalidad:', 'type': 'combo', 'options': ['V - Venezolano', 'E - Extranjero'], 'default': 'V - Venezolano'}),
    ('nombres', {'label': 'Nombres:', 'type': 'entry', 'required': True}),
    ('apellidos', {'label': 'Apellidos:', 'type': 'entry', 'required': True}),
    ('genero', {'label': 'Género:', 'type': 'combo', 'options': ['M - Masculino', 'F - Femenino'], 'default': 'M - Masculino'}),
    ('fecha_nacimiento', {'label': 'Fecha Nacimiento (DD/MM/AAAA):', 'type': 'date_edit', 'validation': 'date'}), 
    ('lugar_nacimiento', {'label': 'Lugar Nacimiento:', 'type': 'entry'}),
    ('estado_nacimiento', {'label': 'Estado Nacimiento:', 'type': 'entry'}),
    ('municipio_nacimiento', {'label': 'Municipio Nacimiento:', 'type': 'entry'}),

    # DATOS DE CONTACTO
    ('direccion', {'label': 'Dirección:', 'type': 'text_area'}),
    ('telefono', {'label': 'Teléfono:', 'type': 'entry', 'validation': 'phone'}),
    ('correo', {'label': 'Correo:', 'type': 'entry', 'validation': 'email'}),

    # DATOS FÍSICOS
    ('estatura', {'label': 'Estatura (cm):', 'type': 'entry', 'validation': 'float'}),
    ('peso', {'label': 'Peso (kg):', 'type': 'entry', 'validation': 'float'}),
    ('talla_camisa', {'label': 'Talla Camisa:', 'type': 'entry'}),
    ('talla_pantalon', {'label': 'Talla Pantalón:', 'type': 'entry'}),
    ('talla_zapatos', {'label': 'Talla Zapatos:', 'type': 'entry'}),

    # DATOS MÉDICOS
    ('condiciones_medicas', {'label': 'Condiciones Médicas:', 'type': 'text_area'}),
    ('medicamentos', {'label': 'Medicamentos:', 'type': 'text_area'}),

    # DATOS ACADÉMICOS
    ('plantel_procedencia', {'label': 'Plantel Procedencia:', 'type': 'entry'}),
    ('fecha_ingreso', {'label': 'Fecha Ingreso (DD/MM/AAAA):', 'type': 'date_edit', 'validation': 'date'}), 
    ('estado_estudiante', {'label': 'Estado:', 'type': 'combo', 'options': ['ACTIVO', 'INACTIVO', 'RETIRADO'], 'default': 'ACTIVO'}),
    ('fecha_retiro', {'label': 'Fecha Retiro (DD/MM/AAAA):', 'type': 'date_edit', 'validation': 'date', 'optional': True}),
    ('motivo_retiro', {'label': 'Motivo Retiro:', 'type': 'text_area', 'optional': True})
]

# Agrupación de campos por sección para la UI
FORM_SECTIONS = [
    ("DATOS PERSONALES", ['cedula', 'nacionalidad', 'nombres', 'apellidos', 'genero', 'fecha_nacimiento',
                            'lugar_nacimiento', 'estado_nacimiento', 'municipio_nacimiento']),
    ("DATOS DE CONTACTO", ['direccion', 'telefono', 'correo']),
    ("DATOS FÍSICOS", ['estatura', 'peso', 'talla_camisa', 'talla_pantalon', 'talla_zapatos']),
    ("DATOS MÉDICOS", ['condiciones_medicas', 'medicamentos']),
    ("DATOS ACADÉMICOS", ['plantel_procedencia', 'fecha_ingreso', 'estado_estudiante', 'fecha_retiro', 'motivo_retiro'])
]


class DatabaseConnection:
    """Maneja la conexión a la base de datos PostgreSQL"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establece conexión con la base de datos usando la configuración proporcionada"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            return True
        except psycopg2.Error as e:
            print(f"Error conectando a la base de datos: {e}")
            self.connection = None
            self.cursor = None
            return False
    
    def disconnect(self):
        """Cierra la conexión a la base de datos"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query, params=None):
        """Ejecuta una consulta SQL"""
        if not self.connection or self.connection.closed:
            if not self.connect():
                QMessageBox.critical(None, "Error de Conexión", "No hay conexión activa a la base de datos.")
                return False
        
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Error ejecutando consulta: {e}")
            QMessageBox.critical(None, "Error de Base de Datos", f"Error al ejecutar consulta:\n{e}")
            self.connection.rollback()
            return False
    
    def fetch_all(self, query, params=None):
        """Obtiene todos los resultados de una consulta"""
        if not self.connection or self.connection.closed:
            if not self.connect():
                QMessageBox.critical(None, "Error de Conexión", "No hay conexión activa a la base de datos.")
                return []
        
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error obteniendo datos: {e}")
            QMessageBox.critical(None, "Error de Base de Datos", f"Error al obtener datos:\n{e}")
            return []


class EstudianteApp(QMainWindow):
    """
    Ventana para la gestión de Estudiantes.
    Permite visualizar, agregar, modificar y eliminar registros de estudiantes.
    """
    closed = pyqtSignal()

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db = DatabaseConnection(self.db_config)
        
        self.info_label = QLabel("Estado de la conexión...")
        self.info_label.setObjectName("infoLabel")
        self.btn_save = QPushButton() # Referencia para el botón de guardar
        self.btn_guardar_cambios = QPushButton() # Referencia para el botón de guardar cambios
        self.btn_clear = QPushButton() # Referencia para el botón de limpiar
        self.btn_eliminar = QPushButton() # Referencia para el botón de eliminar

        self.current_student_cedula = None
        self.edit_mode = False

        self.init_db_connection_and_table()
        self.setup_ui()
        self.apply_styles()
        
        if self.db.connection and not self.db.connection.closed:
            self.load_students()
        else:
            self.mostrar_mensaje_sin_bd()
        
        self.showFullScreen()

    def init_db_connection_and_table(self):
        """
        Intenta conectar a la base de datos y crear la tabla 'estudiante' si no existe.
        """
        print("Iniciando conexión y configuración de tabla 'estudiante'...")
        if not self.db.connect():
            print("Fallo la conexión inicial a la base de datos.")
            return False

        print("Conexión exitosa, verificando/creando tabla 'estudiante'...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS estudiante (
            cedula VARCHAR(20) PRIMARY KEY,
            nacionalidad CHAR(1) NOT NULL,
            nombres VARCHAR(100) NOT NULL,
            apellidos VARCHAR(100) NOT NULL,
            genero CHAR(1),
            fecha_nacimiento DATE,
            lugar_nacimiento VARCHAR(100),
            estado_nacimiento VARCHAR(100),
            municipio_nacimiento VARCHAR(100),
            direccion TEXT,
            telefono VARCHAR(20),
            correo VARCHAR(100),
            estatura NUMERIC(5,2),
            peso NUMERIC(5,2),
            talla_camisa VARCHAR(10),
            talla_pantalon VARCHAR(10),
            talla_zapatos VARCHAR(10),
            condiciones_medicas TEXT,
            medicamentos TEXT,
            plantel_procedencia VARCHAR(255),
            fecha_ingreso DATE,
            estado_estudiante VARCHAR(20),
            fecha_retiro DATE,
            motivo_retiro TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        if self.db.execute_query(create_table_query):
            print("Tabla 'estudiante' verificada/creada correctamente.")
            return True
        else:
            print("Error al crear la tabla 'estudiante'.")
            self.db.disconnect()
            return False

    def mostrar_mensaje_sin_bd(self):
        """Muestra un mensaje cuando no hay conexión a la base de datos"""
        self.info_label.setText("Sin conexión a base de datos - No se pueden cargar/gestionar estudiantes.")
        self.btn_save.setEnabled(False)
        self.btn_guardar_cambios.setEnabled(False)
        self.btn_eliminar.setEnabled(False)
        self.btn_clear.setEnabled(False)


    def setup_ui(self):
        self.setWindowTitle("SIGME - Gestión de Estudiantes")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15) # Margenes generales
        main_layout.setSpacing(10)

        # --- Título Principal y Botón Volver al Menú ---
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {PRIMARY_COLOR}; border-radius: 5px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel("MÓDULO DE GESTIÓN DE ESTUDIANTES")
        title_label.setFont(QFont(FONT_FAMILY, 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {WHITE_COLOR}; background-color: {PRIMARY_COLOR};")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.back_to_menu_button = QPushButton('Volver al Menú')
        self.back_to_menu_button.setObjectName('backButton')
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        header_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(header_frame)

        # --- Contenido Principal (Lista de Estudiantes y Formulario) ---
        content_frame = QFrame()
        content_frame.setStyleSheet(f"background-color: {LIGHT_BACKGROUND};")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # Frame Izquierdo (Lista de Estudiantes y Botones)
        left_panel_widget = QWidget()
        left_panel_widget.setStyleSheet(f"background-color: {LIGHT_BACKGROUND};")
        left_layout = QVBoxLayout(left_panel_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        list_title_label = QLabel("Lista de Estudiantes")
        list_title_label.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        list_title_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        left_layout.addWidget(list_title_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Barra de búsqueda
        search_frame = QFrame()
        search_frame.setStyleSheet(f"background-color: {LIGHT_BACKGROUND};")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_label = QLabel("Buscar:")
        search_label.setFont(QFont(FONT_FAMILY, 10))
        search_label.setStyleSheet(f"color: {TEXT_COLOR};") # Color oscuro para el texto de la etiqueta de búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por cédula o nombre")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 14px; padding: 5px; border: 1px solid {ACCENT_COLOR}; border-radius: 5px; color: {TEXT_COLOR};") # Color oscuro para el texto del input de búsqueda

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        left_layout.addWidget(search_frame)

        # Treeview (QTableWidget) para la lista de estudiantes
        self.tabla = QTableWidget()
        self.tabla.setObjectName('dataTable')
        table_columns = ('Cédula', 'Nombres', 'Apellidos', 'Estado')
        self.tabla.setColumnCount(len(table_columns))
        self.tabla.setHorizontalHeaderLabels(table_columns)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.itemDoubleClicked.connect(self.edit_student_from_table)
        self.tabla.setStyleSheet(f"""
            QTableWidget {{
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 8px;
                selection-background-color: {ACCENT_COLOR};
                selection-color: {WHITE_COLOR};
                font-family: {FONT_FAMILY};
                font-size: 13px;
                color: {TEXT_COLOR}; /* Color oscuro para el texto de las celdas */
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                padding: 8px;
                border: 1px solid {PRIMARY_COLOR};
                font-weight: bold;
                font-family: {FONT_FAMILY};
                font-size: 11px;
            }}
        """)
        left_layout.addWidget(self.tabla)

        # Botones de acción (Nuevo, Editar, Eliminar)
        button_frame_left = QFrame()
        button_frame_left.setStyleSheet(f"background-color: {LIGHT_BACKGROUND};")
        button_layout_left = QHBoxLayout(button_frame_left)
        button_layout_left.setContentsMargins(0, 0, 0, 0)
        button_layout_left.setSpacing(8)

        self.btn_new = QPushButton("➕ Nuevo (Ctrl+N)")
        self.btn_new.setObjectName('NewButton')
        self.btn_new.clicked.connect(self.new_student)
        button_layout_left.addWidget(self.btn_new)

        self.btn_edit = QPushButton("✏️ Editar (Ctrl+E)")
        self.btn_edit.setObjectName('EditButton')
        self.btn_edit.clicked.connect(self.edit_student)
        button_layout_left.addWidget(self.btn_edit)

        self.btn_eliminar = QPushButton("🗑️ Eliminar (Ctrl+D)")
        self.btn_eliminar.setObjectName('DeleteButton')
        self.btn_eliminar.clicked.connect(self.delete_student)
        button_layout_left.addWidget(self.btn_eliminar)
        
        left_layout.addWidget(button_frame_left)
        content_layout.addWidget(left_panel_widget, 3) # <--- Cambiado a 3 para hacerlo más grande

        # Frame Derecho (Formulario de Estudiante)
        right_panel_widget = QFrame()
        right_panel_widget.setObjectName("BorderedFrame") # Para aplicar borde y fondo
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setContentsMargins(15, 15, 15, 15)
        right_panel_layout.setSpacing(10)

        form_title_label = QLabel("Datos del Estudiante")
        form_title_label.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        form_title_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        right_panel_layout.addWidget(form_title_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Línea divisoria
        line_divider = QFrame()
        line_divider.setFrameShape(QFrame.Shape.HLine)
        line_divider.setFrameShadow(QFrame.Shadow.Sunken)
        line_divider.setStyleSheet(f"background-color: {ACCENT_COLOR}; height: 2px;")
        right_panel_layout.addWidget(line_divider)

        # Contenido del formulario con scroll
        self.form_scroll_area = QScrollArea()
        self.form_scroll_area.setWidgetResizable(True)
        form_content_widget = QWidget()
        self.form_scroll_area.setWidget(form_content_widget)
        self.form_layout = QVBoxLayout(form_content_widget)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(10)

        self.form_widgets = {}
        self.form_data_map = {}

        for section_title, field_names in FORM_SECTIONS:
            section_frame = QFrame()
            section_frame.setObjectName("SectionFrame") # Para estilos específicos de sección
            section_layout = QVBoxLayout(section_frame)
            section_layout.setContentsMargins(10, 5, 10, 5) # Padding dentro de cada sección
            
            section_label = QLabel(section_title)
            section_label.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
            section_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
            section_layout.addWidget(section_label, alignment=Qt.AlignmentFlag.AlignLeft)
            
            section_line = QFrame()
            section_line.setFrameShape(QFrame.Shape.HLine)
            section_line.setFrameShadow(QFrame.Shadow.Sunken)
            section_line.setStyleSheet(f"background-color: {ACCENT_COLOR}; height: 1px;")
            section_layout.addWidget(section_line)

            grid_layout = QFormLayout()
            grid_layout.setSpacing(8)
            grid_layout.setContentsMargins(0, 5, 0, 5)

            for field_name in field_names:
                field_info_tuple = next(item for item in STUDENT_FIELDS if item[0] == field_name)
                field_info_dict = field_info_tuple[1]
                
                label_text = field_info_dict['label']
                field_type = field_info_dict['type']
                options = field_info_dict.get('options')
                validation_type = field_info_dict.get('validation')

                label = QLabel(label_text)
                label.setFont(QFont(FONT_FAMILY, 9))
                label.setStyleSheet(f"color: {PRIMARY_COLOR};") # Asegura color oscuro para las etiquetas
                widget_instance = None

                if field_type == 'entry':
                    widget_instance = QLineEdit()
                    widget_instance.setFont(QFont(FONT_FAMILY, 9))
                    widget_instance.setStyleSheet(f"background-color: {WHITE_COLOR}; color: {TEXT_COLOR}; border: 1px solid {ACCENT_COLOR}; border-radius: 3px; padding: 3px;")
                    if validation_type == 'cedula':
                        pass
                    elif validation_type == 'phone':
                        # Se ha eliminado la máscara de entrada para permitir cualquier formato de teléfono
                        # widget_instance.setInputMask("(9999)-999-99-99;_") 
                        pass # La validación de 11 dígitos se manejará a nivel de base de datos si existe una restricción CHECK
                    elif validation_type == 'float':
                        regex = QRegularExpression(r"^\d*\.?\d*$")
                        validator = QRegularExpressionValidator(regex)
                        widget_instance.setValidator(validator)
                    elif validation_type == 'email':
                        regex = QRegularExpression(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
                        validator = QRegularExpressionValidator(regex)
                        widget_instance.setValidator(validator)
                elif field_type == 'combo':
                    widget_instance = QComboBox()
                    widget_instance.addItems(options)
                    widget_instance.setFont(QFont(FONT_FAMILY, 9))
                    widget_instance.setStyleSheet(f"""
                        QComboBox {{
                            background-color: {WHITE_COLOR};
                            color: {TEXT_COLOR}; /* Asegura color oscuro para el texto del combobox */
                            border: 1px solid {ACCENT_COLOR};
                            border-radius: 3px;
                            padding: 3px;
                        }}
                        QComboBox::drop-down {{
                            border-left: 1px solid {ACCENT_COLOR};
                            width: 20px;
                        }}
                        QComboBox QAbstractItemView {{
                            background-color: {WHITE_COLOR};
                            selection-background-color: {ACCENT_COLOR};
                            color: {TEXT_COLOR}; /* Asegura color oscuro para los ítems del combobox */
                        }}
                    """)
                    if field_name == 'nacionalidad':
                        widget_instance.currentIndexChanged.connect(self._update_cedula_prefix)
                elif field_type == 'text_area':
                    widget_instance = QTextEdit()
                    widget_instance.setPlaceholderText(f"Ingrese {label_text.lower().replace(':', '')} aquí...")
                    widget_instance.setFont(QFont(FONT_FAMILY, 9))
                    widget_instance.setStyleSheet(f"background-color: {WHITE_COLOR}; color: {TEXT_COLOR}; border: 1px solid {ACCENT_COLOR}; border-radius: 3px; padding: 3px;")
                    widget_instance.setFixedHeight(60)
                elif field_type == 'date_edit':
                    widget_instance = QDateEdit(calendarPopup=True)
                    widget_instance.setDisplayFormat("dd/MM/yyyy")
                    widget_instance.setDate(QDate.currentDate())
                    widget_instance.setFont(QFont(FONT_FAMILY, 9))
                    widget_instance.setStyleSheet(f"background-color: {WHITE_COLOR}; color: {TEXT_COLOR}; border: 1px solid {ACCENT_COLOR}; border-radius: 3px; padding: 3px;")
                
                if widget_instance:
                    grid_layout.addRow(label, widget_instance)
                    self.form_widgets[field_name] = widget_instance
                    self.form_data_map[field_name] = widget_instance

            section_layout.addLayout(grid_layout)
            self.form_layout.addWidget(section_frame)
        
        self.form_layout.addStretch(1)

        right_panel_layout.addWidget(self.form_scroll_area)

        # Botones del formulario (Guardar, Limpiar)
        button_form_frame = QFrame()
        button_form_frame.setStyleSheet(f"background-color: {LIGHT_BACKGROUND};")
        button_form_layout = QHBoxLayout(button_form_frame)
        button_form_layout.setContentsMargins(0, 0, 0, 0)
        button_form_layout.setSpacing(10)
        
        self.btn_save = QPushButton("💾 Guardar (Ctrl+S)")
        self.btn_save.setObjectName('SaveButton')
        self.btn_save.clicked.connect(self.save_student)
        button_form_layout.addWidget(self.btn_save)
        
        self.btn_guardar_cambios = QPushButton("💾 Guardar Cambios")
        self.btn_guardar_cambios.setObjectName('SaveButton') # Reutiliza el estilo de SaveButton
        self.btn_guardar_cambios.setVisible(False)
        self.btn_guardar_cambios.clicked.connect(self.save_changes)
        button_form_layout.addWidget(self.btn_guardar_cambios)

        self.btn_clear = QPushButton("🧹 Limpiar")
        self.btn_clear.setObjectName('ClearButton')
        self.btn_clear.clicked.connect(self.clear_form)
        button_form_layout.addWidget(self.btn_clear)

        right_panel_layout.addWidget(button_form_frame)
        content_layout.addWidget(right_panel_widget, 2) # <--- Cambiado a 2 para hacerlo más pequeño

        main_layout.addWidget(content_frame)

        # Barra de estado
        self.status_bar = QLabel("Listo.")
        self.status_bar.setStyleSheet(f"background-color: {LIGHT_BACKGROUND}; color: {TEXT_COLOR}; border-top: 1px solid {ACCENT_COLOR}; padding: 5px;")
        self.status_bar.setFont(QFont(FONT_FAMILY, 9))
        main_layout.addWidget(self.status_bar)

        self._set_default_values()
        self._set_form_state(False) # Inicia en modo de solo lectura
        self.search_input.setFocus() # Foco inicial en la barra de búsqueda

    def apply_styles(self):
        """Aplica los estilos QSS a la ventana y sus widgets."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {LIGHT_BACKGROUND};
            }}
            QLabel {{
                font-family: '{FONT_FAMILY}', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {PRIMARY_COLOR};
            }}
            #searchLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {PRIMARY_COLOR};
            }}
            QLineEdit, QDateEdit {{
                padding: 5px;
                border: 1px solid {ACCENT_COLOR};
                border-radius: 3px;
                font-family: '{FONT_FAMILY}', sans-serif;
                font-size: 14px;
                background-color: {WHITE_COLOR};
                color: {TEXT_COLOR}; /* Asegura color oscuro para el texto del QLineEdit y QDateEdit */
            }}
            QLineEdit:focus, QDateEdit:focus {{
                border-color: {PRIMARY_COLOR};
                outline: none;
            }}
            QTextEdit {{
                padding: 5px;
                border: 1px solid {ACCENT_COLOR};
                border-radius: 3px;
                font-family: '{FONT_FAMILY}', sans-serif;
                font-size: 14px;
                background-color: {WHITE_COLOR};
                color: {TEXT_COLOR}; /* Asegura color oscuro para el texto del QTextEdit */
            }}
            QTextEdit:focus {{
                border-color: {PRIMARY_COLOR};
                outline: none;
            }}
            QPushButton {{
                font-family: '{FONT_FAMILY}', sans-serif;
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 15px;
                border-radius: 5px;
                border: none;
            }}
            #NewButton {{
                background-color: {PRIMARY_COLOR};
                color: {TEXT_COLOR};
            }}
            #NewButton:hover {{
                background-color: #1a2e4d; /* Un tono más oscuro */
            }}
            #EditButton {{
                background-color: {PRIMARY_COLOR}; /* Cambiado a azul oscuro */
                color: {TEXT_COLOR};
            }}
            #EditButton:hover {{
                background-color: #1a2e4d; /* Un tono más oscuro */
            }}
            #DeleteButton {{
                background-color: {ERROR_COLOR};
                color: {TEXT_COLOR};
            }}
            #DeleteButton:hover {{
                background-color: #c02121; /* Un tono más oscuro */
            }}
            #SaveButton {{
                background-color: {PRIMARY_COLOR}; /* Cambiado a azul oscuro */
                color: {TEXT_COLOR};
            }}
            #SaveButton:hover {{
                background-color: #1a2e4d; /* Un tono más oscuro */
            }}
            #ClearButton {{
                background-color: {PRIMARY_COLOR}; /* Cambiado a azul oscuro */
                color: {TEXT_COLOR};
            }}
            #ClearButton:hover {{
                background-color: #1a2e4d; /* Un tono más oscuro */
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
            #backButton {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            #backButton:hover {{
                background-color: #1a2e4d;
            }}
            #backButton:pressed {{
                background-color: #10203a;
            }}
            #dataTable {{
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 8px;
                selection-background-color: {ACCENT_COLOR};
                selection-color: {WHITE_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
                font-size: 13px;
                color: {TEXT_COLOR};
            }}
            #dataTable::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                padding: 8px;
                border: 1px solid {PRIMARY_COLOR};
                font-weight: bold;
                font-family: {FONT_FAMILY};
                font-size: 11px;
            }}
            #infoLabel {{
                color: {TEXT_COLOR}; /* Asegura color oscuro para la barra de estado */
                font-weight: bold;
                padding: 5px;
            }}
            #BorderedFrame {{
                border: 1px solid {ACCENT_COLOR};
                border-radius: 8px;
                background-color: {LIGHT_BACKGROUND};
            }}
            #SectionFrame {{
                border: 1px solid {ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
                margin-bottom: 10px;
                background-color: {LIGHT_BACKGROUND};
            }}
            #SectionTitleLabel {{
                font-size: 12px;
                font-weight: bold;
                color: {PRIMARY_COLOR};
                margin-bottom: 5px;
            }}
        """)

    def _set_default_values(self):
        """Establece los valores por defecto definidos en STUDENT_FIELDS."""
        for field_name, field_info in STUDENT_FIELDS:
            widget = self.form_widgets.get(field_name)
            if widget and 'default' in field_info:
                if isinstance(widget, QLineEdit):
                    widget.setText(field_info['default'])
                elif isinstance(widget, QComboBox):
                    index = widget.findText(field_info['default'])
                    if index != -1:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QTextEdit):
                    widget.setText(field_info['default'])
                elif isinstance(widget, QDateEdit):
                    try:
                        date_parts = field_info['default'].split('/')
                        qdate = QDate(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                        widget.setDate(qdate)
                    except (ValueError, IndexError):
                        widget.setDate(QDate.currentDate())
            elif widget and field_name in ['fecha_retiro', 'motivo_retiro'] and field_info.get('optional'):
                if isinstance(widget, QDateEdit):
                    widget.clear()
                elif isinstance(widget, QTextEdit):
                    widget.clear()

    def _set_form_state(self, enabled):
        """Habilita o deshabilita los campos del formulario y los botones de acción."""
        self.edit_mode = enabled
        for field_name, widget in self.form_widgets.items():
            if field_name == 'cedula':
                widget.setReadOnly(not enabled or (enabled and self.current_student_cedula is not None))
            elif isinstance(widget, QLineEdit) or isinstance(widget, QDateEdit) or isinstance(widget, QTextEdit):
                widget.setReadOnly(not enabled)
            elif isinstance(widget, QComboBox):
                widget.setEnabled(enabled)
                if not enabled:
                    widget.setEditable(False) # Para que no se pueda escribir en el combobox
                else:
                    # Si el combobox es de solo selección, se mantiene no editable
                    # Si fuera un combobox con entrada libre y se desea que sea editable,
                    # se debería añadir una condición aquí.
                    pass
        
        self.btn_save.setVisible(enabled and self.current_student_cedula is None)
        self.btn_guardar_cambios.setVisible(enabled and self.current_student_cedula is not None)
        self.btn_clear.setEnabled(enabled)

        # Los botones de la izquierda (Nuevo, Editar, Eliminar) se gestionan por separado
        # Habilitar/deshabilitar según si hay conexión a DB
        has_db_connection = self.db.connection and not self.db.connection.closed
        self.btn_new.setEnabled(has_db_connection)
        self.btn_edit.setEnabled(has_db_connection and self.current_student_cedula is not None)
        self.btn_eliminar.setEnabled(has_db_connection and self.current_student_cedula is not None)


    def _update_cedula_prefix(self):
        """Actualiza el prefijo de la cédula basado en la nacionalidad seleccionada."""
        if not self.edit_mode:
            return

        nacionalidad_text = self.form_widgets['nacionalidad'].currentText()
        current_cedula = self.form_widgets['cedula'].text()
        
        prefix = ''
        if nacionalidad_text.startswith('V'):
            prefix = 'V-'
        elif nacionalidad_text.startswith('E'):
            prefix = 'E-'
        
        numeric_part = re.sub(r'^[VE]-', '', current_cedula)
        
        if not self.form_widgets['cedula'].isReadOnly():
            self.form_widgets['cedula'].setText(prefix + numeric_part)
            self.form_widgets['cedula'].setCursorPosition(len(prefix + numeric_part))

    def new_student(self):
        """Prepara el formulario para un nuevo estudiante."""
        self.clear_form()
        self._set_form_state(True)
        self.current_student_cedula = None
        self.form_widgets['cedula'].setReadOnly(False)
        self.status_bar.setText("Formulario listo para un nuevo estudiante.")
        self.form_widgets['cedula'].setFocus()

    def edit_student(self):
        """Habilita el formulario para editar el estudiante actualmente seleccionado."""
        if self.current_student_cedula is None:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un estudiante de la tabla para editar.")
            return
        # No es necesario llamar a mostrar_formulario() ya que el layout es side-by-side
        self._set_form_state(True)
        self.form_widgets['cedula'].setReadOnly(True)
        self.status_bar.setText(f"Modo: Editando Estudiante ({self.current_student_cedula})")
        self.form_widgets['nombres'].setFocus()

    def save_student(self):
        """Guarda un nuevo estudiante en la base de datos."""
        data = self._get_form_data()
        if not self._validate_form_data(data):
            return

        data['nacionalidad'] = data['nacionalidad'][0]
        data['genero'] = data['genero'][0]
        data['estado_estudiante'] = data['estado_estudiante'][0] # 'A', 'I', 'R'

        query = """
        INSERT INTO estudiante (cedula, nacionalidad, nombres, apellidos, genero, fecha_nacimiento,
        lugar_nacimiento, estado_nacimiento, municipio_nacimiento, direccion, telefono, correo,
        estatura, peso, talla_camisa, talla_pantalon, talla_zapatos, condiciones_medicas, medicamentos,
        plantel_procedencia, fecha_ingreso, estado_estudiante, fecha_retiro, motivo_retiro)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (
            data['cedula'], data['nacionalidad'], data['nombres'], data['apellidos'], data['genero'],
            data['fecha_nacimiento'], data['lugar_nacimiento'], data['estado_nacimiento'],
            data['municipio_nacimiento'], data['direccion'], data['telefono'], data['correo'],
            data['estatura'], data['peso'], data['talla_camisa'], data['talla_pantalon'],
            data['talla_zapatos'], data['condiciones_medicas'], data['medicamentos'],
            data['plantel_procedencia'], data['fecha_ingreso'], data['estado_estudiante'],
            data['fecha_retiro'], data['motivo_retiro']
        )

        if self.db.execute_query(query, params):
            QMessageBox.information(self, "Éxito", "Estudiante registrado exitosamente.")
            self.clear_form()
            self.load_students()
            self.status_bar.setText("Estudiante registrado exitosamente.")
        else:
            self.status_bar.setText("Error al registrar estudiante.")

    def save_changes(self):
        """Guarda los cambios de un estudiante existente en la base de datos."""
        if self.current_student_cedula is None:
            QMessageBox.warning(self, "Error", "No hay estudiante seleccionado para guardar cambios.")
            return

        data = self._get_form_data()
        if not self._validate_form_data(data):
            return

        data['nacionalidad'] = data['nacionalidad'][0]
        data['genero'] = data['genero'][0]
        data['estado_estudiante'] = data['estado_estudiante'][0]

        query = """
        UPDATE estudiante SET
            nacionalidad = %s, nombres = %s, apellidos = %s, genero = %s, fecha_nacimiento = %s,
            lugar_nacimiento = %s, estado_nacimiento = %s, municipio_nacimiento = %s,
            direccion = %s, telefono = %s, correo = %s, estatura = %s, peso = %s,
            talla_camisa = %s, talla_pantalon = %s, talla_zapatos = %s,
            condiciones_medicas = %s, medicamentos = %s, plantel_procedencia = %s,
            fecha_ingreso = %s, estado_estudiante = %s, fecha_retiro = %s, motivo_retiro = %s
        WHERE cedula = %s;
        """
        params = (
            data['nacionalidad'], data['nombres'], data['apellidos'], data['genero'],
            data['fecha_nacimiento'], data['lugar_nacimiento'], data['estado_nacimiento'],
            data['municipio_nacimiento'], data['direccion'], data['telefono'], data['correo'],
            data['estatura'], data['peso'], data['talla_camisa'], data['talla_pantalon'],
            data['talla_zapatos'], data['condiciones_medicas'], data['medicamentos'],
            data['plantel_procedencia'], data['fecha_ingreso'], data['estado_estudiante'],
            data['fecha_retiro'], data['motivo_retiro'], self.current_student_cedula
        )

        if self.db.execute_query(query, params):
            QMessageBox.information(self, "Éxito", "Cambios guardados exitosamente.")
            self.clear_form()
            self.load_students()
            self.status_bar.setText(f"Cambios guardados para {self.current_student_cedula}.")
        else:
            self.status_bar.setText("Error al guardar cambios.")

    def delete_student(self):
        """Elimina el estudiante seleccionado de la base de datos."""
        selected_rows = self.tabla.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un estudiante de la tabla para eliminar.")
            return
        
        cedula_to_delete = self.tabla.item(selected_rows[0].row(), 0).text()
        nombre_completo = f"{self.tabla.item(selected_rows[0].row(), 1).text()} {self.tabla.item(selected_rows[0].row(), 2).text()}"

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Está seguro de que desea eliminar al estudiante '{nombre_completo}' (Cédula: {cedula_to_delete})?\n"
                                     "Esta acción es irreversible.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            query = "DELETE FROM estudiante WHERE cedula = %s;"
            if self.db.execute_query(query, (cedula_to_delete,)):
                QMessageBox.information(self, "Éxito", "Estudiante eliminado correctamente.")
                self.clear_form()
                self.load_students()
                self.status_bar.setText(f"Estudiante '{cedula_to_delete}' eliminado.")
            else:
                self.status_bar.setText(f"Error al eliminar estudiante '{cedula_to_delete}'.")

    def load_students(self):
        """Carga todos los estudiantes desde la base de datos y los muestra en la tabla."""
        students = self.db.fetch_all("SELECT * FROM estudiante ORDER BY apellidos, nombres ASC")
        
        display_columns_names = [field_name for field_name, field_info in STUDENT_FIELDS if field_name not in ['condiciones_medicas', 'medicamentos', 'direccion', 'motivo_retiro']]
        
        self.tabla.setColumnCount(len(display_columns_names))
        self.tabla.setHorizontalHeaderLabels([next(item[1]['label'].replace(':', '') for item in STUDENT_FIELDS if item[0] == col) for col in display_columns_names])

        self.tabla.setRowCount(len(students))
        for row_idx, student in enumerate(students):
            col_idx = 0
            for field_name in display_columns_names:
                value = student.get(field_name)
                item_text = ""

                if value is None:
                    item_text = ""
                elif isinstance(value, datetime):
                    item_text = value.strftime('%d/%m/%Y')
                elif field_name == 'nacionalidad':
                    item_text = value
                elif field_name == 'genero':
                    item_text = value
                elif field_name == 'estado_estudiante':
                    if value == 'A': item_text = 'ACTIVO'
                    elif value == 'I': item_text = 'INACTIVO'
                    elif value == 'R': item_text = 'RETIRADO'
                    else: item_text = str(value)
                else:
                    item_text = str(value)
                
                self.tabla.setItem(row_idx, col_idx, QTableWidgetItem(item_text))
                col_idx += 1
        
        self.status_bar.setText(f"Total de estudiantes: {len(students)}")
        self.btn_eliminar.setEnabled(False) # Asegurarse de que el botón de eliminar esté deshabilitado inicialmente

    def _on_search(self):
        """Filtra los registros de la tabla según el texto de búsqueda."""
        search_text = self.search_input.text().strip().lower()
        
        if not search_text:
            self.load_students()
            return

        found_match = False
        for i in range(self.tabla.rowCount()):
            cedula = self.tabla.item(i, 0).text().lower() if self.tabla.item(i, 0) else ""
            nombres = self.tabla.item(i, 1).text().lower() if self.tabla.item(i, 1) else ""
            apellidos = self.tabla.item(i, 2).text().lower() if self.tabla.item(i, 2) else ""
            
            match = search_text in cedula or search_text in nombres or search_text in apellidos
            self.tabla.setRowHidden(i, not match)
            
            if match and not found_match:
                self.tabla.selectRow(i)
                self.edit_student_from_table(self.tabla.item(i, 0))
                found_match = True
        
        if not found_match:
            self.status_bar.setText("No se encontraron coincidencias.")
            self.clear_form()

    def edit_student_from_table(self, item):
        """Carga los datos del estudiante seleccionado de la tabla en el formulario para edición."""
        row = item.row()
        cedula = self.tabla.item(row, 0).text()
        self.current_student_cedula = cedula
        
        student_data = self.db.fetch_all("SELECT * FROM estudiante WHERE cedula = %s", (cedula,))
        if student_data:
            student = student_data[0]
            self._set_form_state(True)
            self.form_widgets['cedula'].setReadOnly(True)

            for field_name, field_info in STUDENT_FIELDS:
                widget = self.form_widgets.get(field_name)
                if widget:
                    value = student.get(field_name)
                    if value is None:
                        if isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit):
                            widget.clear()
                        elif isinstance(widget, QDateEdit):
                            widget.clear()
                        elif isinstance(widget, QComboBox):
                            widget.setCurrentIndex(0)
                    elif isinstance(widget, QLineEdit):
                        if field_name == 'cedula':
                            nacionalidad_char = student.get('nacionalidad')
                            prefix = 'V-' if nacionalidad_char == 'V' else 'E-' if nacionalidad_char == 'E' else ''
                            widget.setText(prefix + str(value))
                        else:
                            widget.setText(str(value))
                    elif isinstance(widget, QComboBox):
                        display_text = ""
                        if field_name == 'nacionalidad':
                            display_text = f"{value} - {'Venezolano' if value == 'V' else 'Extranjero'}"
                        elif field_name == 'genero':
                            display_text = f"{value} - {'Masculino' if value == 'M' else 'Femenino'}"
                        elif field_name == 'estado_estudiante':
                            if value == 'A': display_text = 'ACTIVO'
                            elif value == 'I': display_text = 'INACTIVO'
                            elif value == 'R': display_text = 'RETIRADO'
                            else: display_text = str(value)
                        else:
                            display_text = str(value)
                        
                        index = widget.findText(display_text)
                        if index != -1:
                            widget.setCurrentIndex(index)
                        else:
                            widget.setEditText(str(value))
                    elif isinstance(widget, QTextEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QDateEdit):
                        if isinstance(value, datetime):
                            widget.setDate(QDate(value.year, value.month, value.day))
                        else:
                            widget.clear()
            
            self.status_bar.setText(f"Modo: Editando Estudiante ({cedula})")
            self.btn_eliminar.setEnabled(True)

    def clear_form(self):
        """Limpia todos los campos del formulario y restablece el estado."""
        for field_name, widget in self.form_widgets.items():
            if isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
        
        self.current_student_cedula = None
        self._set_default_values()
        self._set_form_state(True) # Se habilita para nueva entrada después de limpiar
        self.search_input.clear()
        self.status_bar.setText("Formulario limpiado. Listo para una nueva entrada.")
        self.tabla.clearSelection()
        self.btn_eliminar.setEnabled(False)

    def mostrar_formulario(self):
        """Este método ya no es necesario con el layout side-by-side, pero se mantiene por si se reutiliza."""
        pass

    def mostrar_tabla(self):
        """Este método ya no es necesario con el layout side-by-side, pero se mantiene por si se reutiliza."""
        self.load_students() # Solo para asegurar que la tabla esté actualizada

    def _get_form_data(self):
        """Recopila los datos del formulario."""
        data = {}
        for field_name, field_info in STUDENT_FIELDS:
            widget = self.form_widgets.get(field_name)
            if widget:
                if isinstance(widget, QLineEdit):
                    data[field_name] = widget.text().strip()
                elif isinstance(widget, QComboBox):
                    data[field_name] = widget.currentText().strip()
                elif isinstance(widget, QTextEdit):
                    data[field_name] = widget.toPlainText().strip()
                elif isinstance(widget, QDateEdit):
                    qdate = widget.date()
                    data[field_name] = qdate.toPyDate() if qdate.isValid() else None
            else:
                data[field_name] = None
        return data

    def _validate_form_data(self, data):
        """Valida los datos del formulario antes de guardar/actualizar."""
        for field_name, field_info in STUDENT_FIELDS:
            if field_info.get('required') and not data.get(field_name):
                QMessageBox.warning(self, "Validación", f"El campo '{field_info['label'].replace(':', '')}' es obligatorio.")
                return False
            
            if field_info.get('optional') and not data.get(field_name):
                data[field_name] = None
            
        # La siguiente línea ha sido eliminada para quitar la validación del formato de cédula.
        # cedula_full = data.get('cedula', '')
        # if not re.fullmatch(r'^[VE]-\d{7,9}$', cedula_full):
        #     QMessageBox.warning(self, "Validación", "Formato de Cédula inválido. Use V-XXXXXXXX o E-XXXXXXXX.")
        #     return False

        if data.get('correo') and not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['correo']):
            QMessageBox.warning(self, "Validación", "Formato de Correo Electrónico inválido.")
            return False

        fecha_nacimiento = data.get('fecha_nacimiento')
        fecha_ingreso = data.get('fecha_ingreso')
        fecha_retiro = data.get('fecha_retiro')

        if fecha_nacimiento and fecha_ingreso and fecha_ingreso < fecha_nacimiento:
            QMessageBox.warning(self, "Validación", "La fecha de ingreso no puede ser anterior a la fecha de nacimiento.")
            return False
        
        if fecha_retiro and fecha_ingreso and fecha_retiro < fecha_ingreso:
            QMessageBox.warning(self, "Validación", "La fecha de retiro no puede ser anterior a la fecha de ingreso.")
            return False

        return True

    def go_back_to_menu(self):
        """Cierra esta ventana y emite una señal para que el menú principal se muestre."""
        self.close()

    def closeEvent(self, event):
        """Sobrescribe el evento de cierre para desconectar la base de datos y emitir la señal."""
        self.db.disconnect()
        self.closed.emit()
        super().closeEvent(event)

# Bloque para ejecutar la aplicación (solo para pruebas directas del módulo)
# if __name__ == '__main__':
#     app = QApplication(sys.argv)

#     test_db_config = {
#         'host': 'localhost',
#         'database': 'SIGME2', 
#         'user': 'postgres',
#         'password': '1234',
#         'port': '5432'
#     }
#     test_user_data = {
#         'id': '1',
#         'codigo_usuario': 'testuser',
#         'cedula_personal': 'V-12345678',
#         'rol': 'control de estudio',
#         'estado': 'activo',
#         'debe_cambiar_clave': False
#     }

#     estudiante_app = EstudianteApp(db_config=test_db_config, user_data=test_user_data)
#     estudiante_app.show()

#     sys.exit(app.exec())
