import sys
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor # Para obtener resultados como diccionarios
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QCheckBox, QDateEdit, QComboBox, 
                             QGroupBox, QFormLayout, QFrame) # Importar QFrame
from PyQt6.QtCore import Qt, QDate, pyqtSignal # Importar pyqtSignal
from PyQt6.QtGui import QFont # QIcon no se usa, se puede quitar

# --- Definición de la Paleta de Colores (Centralizada) ---
PRIMARY_COLOR = '#1c355b' # Azul oscuro fuerte
ACCENT_COLOR = '#7089a7'  # Azul grisáceo medio
LIGHT_BACKGROUND = '#e4eaf4' # Azul muy claro para fondos
TEXT_COLOR = '#333333' # Gris oscuro para texto
WHITE_COLOR = '#FFFFFF'
SUCCESS_COLOR = '#16a34a' # Verde
ERROR_COLOR = '#dc2626'   # Rojo
FONT_FAMILY = 'Arial'


# --- Clase para Manejo de la Base de Datos (Reutilizada de módulos anteriores) ---
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
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor) # Usar RealDictCursor
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
    
    def fetch_one(self, query, params=None):
        """Obtiene un solo resultado de una consulta"""
        if not self.connection or self.connection.closed:
            if not self.connect():
                QMessageBox.critical(None, "Error de Conexión", "No hay conexión activa a la base de datos.")
                return None
        
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Error obteniendo un dato: {e}")
            QMessageBox.critical(None, "Error de Base de Datos", f"Error al obtener un dato:\n{e}")
            return None


# --- Clase para el Modelo de Datos ---
class RepresentanteModel:
    def __init__(self, db_connection):
        self.db = db_connection # Recibe una instancia de DatabaseConnection

    def get_all_representantes(self):
        query = "SELECT cedula, nacionalidad, nombres, apellidos, parentesco, ocupacion, direccion, telefono, correo, fecha_nacimiento, genero, es_madre, es_padre, es_representante_legal FROM representante ORDER BY apellidos, nombres"
        return self.db.fetch_all(query)

    def get_representante_by_cedula(self, cedula):
        query = "SELECT cedula, nacionalidad, nombres, apellidos, parentesco, ocupacion, direccion, telefono, correo, fecha_nacimiento, genero, es_madre, es_padre, es_representante_legal FROM representante WHERE cedula = %s"
        return self.db.fetch_one(query, (cedula,))

    def add_representante(self, data):
        query = """
        INSERT INTO representante (
            cedula, nacionalidad, nombres, apellidos, parentesco, ocupacion,
            direccion, telefono, correo, fecha_nacimiento, genero,
            es_madre, es_padre, es_representante_legal
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        # data es una tupla o lista con los valores en el orden correcto
        return self.db.execute_query(query, data)

    def update_representante(self, cedula, data):
        query = """
        UPDATE representante SET
            nacionalidad = %s, nombres = %s, apellidos = %s, parentesco = %s,
            ocupacion = %s, direccion = %s, telefono = %s, correo = %s,
            fecha_nacimiento = %s, genero = %s, es_madre = %s, es_padre = %s,
            es_representante_legal = %s
        WHERE cedula = %s
        """
        # data es una tupla o lista con los valores en el orden correcto
        return self.db.execute_query(query, data + (cedula,)) # Concatenar la cédula al final para el WHERE

    def delete_representante(self, cedula):
        # Primero, desvincular estudiantes de este representante
        query_update_matricula = "UPDATE matricula SET cedula_representante = NULL WHERE cedula_representante = %s"
        if not self.db.execute_query(query_update_matricula, (cedula,)):
            QMessageBox.warning(None, "Advertencia", "No se pudieron desvincular los estudiantes. Intente eliminar manualmente las matrículas asociadas si la eliminación falla.")
            return False # No continuar si la desvinculación falla gravemente

        # Luego, eliminar el representante
        query_delete_representante = "DELETE FROM representante WHERE cedula = %s"
        return self.db.execute_query(query_delete_representante, (cedula,))

    def search_representantes(self, search_term):
        search_pattern = f"%{search_term}%"
        query = """
        SELECT cedula, nacionalidad, nombres, apellidos, parentesco, ocupacion, direccion, telefono, correo, fecha_nacimiento, genero, es_madre, es_padre, es_representante_legal
        FROM representante
        WHERE cedula ILIKE %s OR nombres ILIKE %s OR apellidos ILIKE %s
        ORDER BY apellidos, nombres
        """
        return self.db.fetch_all(query, (search_pattern, search_pattern, search_pattern))

    def get_students_by_representante_cedula(self, cedula_representante):
        query = """
        SELECT
            e.cedula, e.nombres, e.apellidos, e.fecha_nacimiento,
            m.codigo_ano_escolar, m.codigo_seccion
        FROM estudiante AS e
        JOIN matricula AS m ON e.cedula = m.cedula_estudiante
        WHERE m.cedula_representante = %s
        ORDER BY e.apellidos, e.nombres
        """
        return self.db.fetch_all(query, (cedula_representante,))


# --- Clase para la Vista (Interfaz Gráfica) ---
class RepresentanteApp(QMainWindow): # Cambiado a QMainWindow para tener barra de título y menú
    closed = pyqtSignal() # Señal para indicar que la ventana se ha cerrado

    def __init__(self, db_config, user_data): # Recibe db_config y user_data
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db = DatabaseConnection(self.db_config) # Pasa la configuración de la DB
        self.model = RepresentanteModel(self.db) # Pasa la instancia de DatabaseConnection al modelo

        self.setWindowTitle("SIGME - Gestión de Representantes")
        # self.setGeometry(100, 100, 1200, 800) # Se usará showFullScreen()
        
        self.init_db_connection_and_tables() # Inicializar DB y tablas
        self.init_ui()
        self.apply_styles() # Aplicar estilos después de inicializar la UI
        self.load_representantes() # Cargar datos al inicio
        self.showFullScreen() # Mostrar en pantalla completa

    def init_db_connection_and_tables(self):
        """
        Intenta conectar a la base de datos y crear las tablas necesarias si no existen.
        """
        print("Iniciando conexión y configuración de tablas para Representantes...")
        if not self.db.connect():
            print("Fallo la conexión inicial a la base de datos.")
            return False

        print("Conexión exitosa, verificando/creando tablas...")
        
        # Tabla representante
        create_representante_query = """
        CREATE TABLE IF NOT EXISTS representante (
            cedula VARCHAR(20) PRIMARY KEY,
            nacionalidad CHAR(1) NOT NULL,
            nombres VARCHAR(100) NOT NULL,
            apellidos VARCHAR(100) NOT NULL,
            parentesco VARCHAR(50),
            ocupacion VARCHAR(100),
            direccion TEXT,
            telefono VARCHAR(20),
            correo VARCHAR(100),
            fecha_nacimiento DATE,
            genero CHAR(1),
            es_madre BOOLEAN DEFAULT FALSE,
            es_padre BOOLEAN DEFAULT FALSE,
            es_representante_legal BOOLEAN DEFAULT FALSE
        );
        """
        if not self.db.execute_query(create_representante_query):
            print("Error al crear la tabla 'representante'.")
            self.db.disconnect()
            return False

        # Tabla estudiante (solo si no existe, para la relación)
        create_estudiante_query = """
        CREATE TABLE IF NOT EXISTS estudiante (
            cedula VARCHAR(20) PRIMARY KEY,
            nombres VARCHAR(100) NOT NULL,
            apellidos VARCHAR(100) NOT NULL,
            fecha_nacimiento DATE,
            -- Otras columnas de estudiante que puedas tener
            estado CHAR(1) DEFAULT 'A'
        );
        """
        if not self.db.execute_query(create_estudiante_query):
            print("Error al crear la tabla 'estudiante'.")
            self.db.disconnect()
            return False

        # Tabla matricula (solo si no existe, para la relación)
        create_matricula_query = """
        CREATE TABLE IF NOT EXISTS matricula (
            id SERIAL PRIMARY KEY,
            cedula_estudiante VARCHAR(20) NOT NULL,
            cedula_representante VARCHAR(20), -- Puede ser NULL si se desvincula
            codigo_ano_escolar VARCHAR(20),
            codigo_seccion VARCHAR(20),
            FOREIGN KEY (cedula_estudiante) REFERENCES estudiante (cedula),
            FOREIGN KEY (cedula_representante) REFERENCES representante (cedula) ON DELETE SET NULL
            -- Otras FOREIGN KEY para ano_escolar y seccion si existen
        );
        """
        if not self.db.execute_query(create_matricula_query):
            print("Error al crear la tabla 'matricula'.")
            self.db.disconnect()
            return False

        print("Todas las tablas verificadas/creadas correctamente para Representantes.")
        return True

    def init_ui(self):
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

        title_label = QLabel("MÓDULO DE GESTIÓN DE REPRESENTANTES")
        title_label.setFont(QFont(FONT_FAMILY, 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {WHITE_COLOR}; background-color: {PRIMARY_COLOR};")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.back_to_menu_button = QPushButton('Volver al Menú')
        self.back_to_menu_button.setObjectName('backButton')
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        header_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(header_frame)

        # Contenedor principal para el formulario y las tablas
        content_layout = QHBoxLayout() # Usar QHBoxLayout para el diseño lado a lado
        content_layout.setSpacing(15)

        # --- Columna Izquierda: Formulario de Entrada (CRUD) ---
        left_column_widget = QWidget()
        left_column_layout = QVBoxLayout(left_column_widget)
        left_column_layout.setContentsMargins(0,0,0,0) # Resetear márgenes internos

        input_form_group = QGroupBox("Datos del Representante")
        input_form_group.setObjectName("formGroupBox") # Para aplicar estilos
        form_layout = QFormLayout()
        form_layout.setContentsMargins(15,15,15,15)
        form_layout.setSpacing(10)

        self.le_cedula = QLineEdit()
        self.le_cedula.setPlaceholderText("Cédula (ej. V-12345678)")
        self.le_cedula.setToolTip("Cédula del representante")
        self.le_cedula.setObjectName("inputField")
        form_layout.addRow(QLabel("Cédula:"), self.le_cedula)

        self.cb_nacionalidad = QComboBox()
        self.cb_nacionalidad.addItems(["V", "E"])
        self.cb_nacionalidad.setObjectName("inputField")
        form_layout.addRow(QLabel("Nacionalidad:"), self.cb_nacionalidad)

        self.le_nombres = QLineEdit()
        self.le_nombres.setPlaceholderText("Nombres del representante")
        self.le_nombres.setObjectName("inputField")
        form_layout.addRow(QLabel("Nombres:"), self.le_nombres)

        self.le_apellidos = QLineEdit()
        self.le_apellidos.setPlaceholderText("Apellidos del representante")
        self.le_apellidos.setObjectName("inputField")
        form_layout.addRow(QLabel("Apellidos:"), self.le_apellidos)

        self.le_parentesco = QLineEdit()
        self.le_parentesco.setPlaceholderText("Parentesco (ej. Padre, Madre, Tutor)")
        self.le_parentesco.setObjectName("inputField")
        form_layout.addRow(QLabel("Parentesco:"), self.le_parentesco)

        self.le_ocupacion = QLineEdit()
        self.le_ocupacion.setPlaceholderText("Ocupación")
        self.le_ocupacion.setObjectName("inputField")
        form_layout.addRow(QLabel("Ocupación:"), self.le_ocupacion)

        self.le_direccion = QLineEdit()
        self.le_direccion.setPlaceholderText("Dirección completa")
        self.le_direccion.setObjectName("inputField")
        form_layout.addRow(QLabel("Dirección:"), self.le_direccion)

        self.le_telefono = QLineEdit()
        self.le_telefono.setPlaceholderText("Número de teléfono")
        self.le_telefono.setObjectName("inputField")
        form_layout.addRow(QLabel("Teléfono:"), self.le_telefono)

        self.le_correo = QLineEdit()
        self.le_correo.setPlaceholderText("Correo electrónico")
        self.le_correo.setObjectName("inputField")
        form_layout.addRow(QLabel("Correo:"), self.le_correo)

        self.de_fecha_nacimiento = QDateEdit()
        self.de_fecha_nacimiento.setCalendarPopup(True)
        self.de_fecha_nacimiento.setDate(QDate.currentDate())
        self.de_fecha_nacimiento.setObjectName("inputField")
        form_layout.addRow(QLabel("Fecha Nacimiento:"), self.de_fecha_nacimiento)

        self.cb_genero = QComboBox()
        self.cb_genero.addItems(["", "M", "F"])
        self.cb_genero.setObjectName("inputField")
        form_layout.addRow(QLabel("Género:"), self.cb_genero)

        self.chk_es_madre = QCheckBox("Es Madre")
        self.chk_es_madre.setObjectName("checkBox")
        form_layout.addRow(self.chk_es_madre)

        self.chk_es_padre = QCheckBox("Es Padre")
        self.chk_es_padre.setObjectName("checkBox")
        form_layout.addRow(self.chk_es_padre)

        self.chk_es_representante_legal = QCheckBox("Es Representante Legal")
        self.chk_es_representante_legal.setObjectName("checkBox")
        form_layout.addRow(self.chk_es_representante_legal)

        input_form_group.setLayout(form_layout)
        left_column_layout.addWidget(input_form_group)

        # Botones de Acción para el formulario
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Añadir")
        self.btn_add.setObjectName("addButton")
        self.btn_add.clicked.connect(self.add_representante)
        button_layout.addWidget(self.btn_add)

        self.btn_update = QPushButton("✏️ Actualizar")
        self.btn_update.setObjectName("updateButton")
        self.btn_update.clicked.connect(self.update_representante)
        self.btn_update.setEnabled(False)
        button_layout.addWidget(self.btn_update)

        self.btn_delete = QPushButton("🗑️ Eliminar")
        self.btn_delete.setObjectName("deleteButton")
        self.btn_delete.clicked.connect(self.delete_representante)
        self.btn_delete.setEnabled(False)
        button_layout.addWidget(self.btn_delete)

        self.btn_clear = QPushButton("🧹 Limpiar")
        self.btn_clear.setObjectName("clearButton")
        self.btn_clear.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.btn_clear)

        left_column_layout.addLayout(button_layout)
        left_column_layout.addStretch() # Empuja el formulario y botones hacia arriba

        content_layout.addWidget(left_column_widget, 1) # Proporción 1 para la columna izquierda

        # --- Columna Derecha: Tablas de Representantes y Estudiantes ---
        right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(right_column_widget)
        right_column_layout.setContentsMargins(0,0,0,0) # Resetear márgenes internos

        # Búsqueda
        search_group = QGroupBox("Buscar Representante")
        search_group.setObjectName("searchGroupBox")
        search_layout = QHBoxLayout(search_group)
        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("Buscar por Cédula, Nombres o Apellidos")
        self.le_search.setObjectName("inputField")
        self.le_search.textChanged.connect(self.search_representantes) # Búsqueda en tiempo real
        search_layout.addWidget(self.le_search)
        # self.btn_search = QPushButton("Buscar") # El botón de búsqueda ya no es necesario con textChanged
        # self.btn_search.setObjectName("searchButton")
        # self.btn_search.clicked.connect(self.search_representantes)
        # search_layout.addWidget(self.btn_search)
        right_column_layout.addWidget(search_group)

        # Tabla de Representantes
        representantes_group = QGroupBox("Lista de Representantes")
        representantes_group.setObjectName("tableGroupBox")
        representantes_layout = QVBoxLayout(representantes_group)
        self.table_representantes = QTableWidget()
        self.table_representantes.setObjectName("dataTable")
        self.table_representantes.setColumnCount(14)
        self.table_representantes.setHorizontalHeaderLabels([
            "Cédula", "Nacionalidad", "Nombres", "Apellidos", "Parentesco",
            "Ocupación", "Dirección", "Teléfono", "Correo", "Fecha Nac.",
            "Género", "¿Madre?", "¿Padre?", "¿Rep. Legal?"
        ])
        self.table_representantes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_representantes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_representantes.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_representantes.itemSelectionChanged.connect(self.load_representante_to_form)
        representantes_layout.addWidget(self.table_representantes)
        right_column_layout.addWidget(representantes_group, 2) # Proporción 2 para la tabla de representantes

        # Tabla de Estudiantes Asociados
        student_group = QGroupBox("Estudiantes Asociados")
        student_group.setObjectName("tableGroupBox")
        student_layout = QVBoxLayout(student_group)
        self.table_students = QTableWidget()
        self.table_students.setObjectName("dataTable")
        self.table_students.setColumnCount(6) # Cédula Est., Nombres Est., Apellidos Est., Fecha Nac. Est., Año Escolar, Sección
        self.table_students.setHorizontalHeaderLabels([
            "Cédula Est.", "Nombres Est.", "Apellidos Est.", "Fecha Nac. Est.", "Año Escolar", "Sección"
        ])
        self.table_students.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        student_layout.addWidget(self.table_students)
        student_group.setLayout(student_layout)
        right_column_layout.addWidget(student_group, 1) # Proporción 1 para la tabla de estudiantes

        content_layout.addWidget(right_column_widget, 2) # Proporción 2 para la columna derecha (tablas)

        main_layout.addLayout(content_layout) # Añadir el layout de contenido al layout principal

        # Barra de estado
        self.status_bar = QLabel("Listo.")
        self.status_bar.setStyleSheet(f"background-color: {LIGHT_BACKGROUND}; color: {TEXT_COLOR}; border-top: 1px solid {ACCENT_COLOR}; padding: 5px;")
        self.status_bar.setFont(QFont(FONT_FAMILY, 9))
        main_layout.addWidget(self.status_bar)

    def apply_styles(self):
        """Aplica los estilos CSS a los widgets de la aplicación."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {LIGHT_BACKGROUND};
            }}
            QGroupBox {{
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
                color: {PRIMARY_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                background-color: {ACCENT_COLOR};
                color: {WHITE_COLOR};
                border-radius: 4px;
            }}
            QLabel {{
                color: {PRIMARY_COLOR};
                font-weight: normal;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QLineEdit, QDateEdit, QComboBox {{
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
                color: {TEXT_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {{
                border-color: {PRIMARY_COLOR};
                outline: none;
            }}
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                border: none;
                border-radius: 8px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 100px;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_COLOR};
            }}
            QPushButton:pressed {{
                background-color: #1a2e4d;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
            QPushButton#backButton {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton#backButton:hover {{
                background-color: #1a2e4d;
            }}
            QPushButton#backButton:pressed {{
                background-color: #10203a;
            }}
            QTableWidget {{
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 8px;
                gridline-color: {LIGHT_BACKGROUND};
                selection-background-color: {ACCENT_COLOR};
                selection-color: {WHITE_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
                color: {TEXT_COLOR};
            }}
            QHeaderView::section {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                padding: 8px;
                border: 1px solid {LIGHT_BACKGROUND};
                font-weight: bold;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background-color: {ACCENT_COLOR};
                color: {WHITE_COLOR};
            }}
            QCheckBox {{
                color: {PRIMARY_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {ACCENT_COLOR};
                border-radius: 3px;
                background-color: {WHITE_COLOR};
            }}
            QCheckBox::indicator:checked {{
                background-color: {PRIMARY_COLOR};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIuNSAzLjk5OTk5TDQuNzUgNi4yNUw5LjUgMS41IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEuNSUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }}
        """)

    def load_representantes(self):
        representantes = self.model.get_all_representantes()
        self.table_representantes.setRowCount(0)
        if representantes:
            self.table_representantes.setRowCount(len(representantes))
            for row_idx, row_data in enumerate(representantes):
                # Acceder a los datos por clave de diccionario
                self.table_representantes.setItem(row_idx, 0, QTableWidgetItem(str(row_data.get('cedula', ''))))
                self.table_representantes.setItem(row_idx, 1, QTableWidgetItem(str(row_data.get('nacionalidad', ''))))
                self.table_representantes.setItem(row_idx, 2, QTableWidgetItem(str(row_data.get('nombres', ''))))
                self.table_representantes.setItem(row_idx, 3, QTableWidgetItem(str(row_data.get('apellidos', ''))))
                self.table_representantes.setItem(row_idx, 4, QTableWidgetItem(str(row_data.get('parentesco', ''))))
                self.table_representantes.setItem(row_idx, 5, QTableWidgetItem(str(row_data.get('ocupacion', ''))))
                self.table_representantes.setItem(row_idx, 6, QTableWidgetItem(str(row_data.get('direccion', ''))))
                self.table_representantes.setItem(row_idx, 7, QTableWidgetItem(str(row_data.get('telefono', ''))))
                self.table_representantes.setItem(row_idx, 8, QTableWidgetItem(str(row_data.get('correo', ''))))
                
                fecha_nac = row_data.get('fecha_nacimiento')
                self.table_representantes.setItem(row_idx, 9, QTableWidgetItem(fecha_nac.strftime("%Y-%m-%d") if fecha_nac else ""))
                
                self.table_representantes.setItem(row_idx, 10, QTableWidgetItem(str(row_data.get('genero', ''))))
                self.table_representantes.setItem(row_idx, 11, QTableWidgetItem("Sí" if row_data.get('es_madre') else "No"))
                self.table_representantes.setItem(row_idx, 12, QTableWidgetItem("Sí" if row_data.get('es_padre') else "No"))
                self.table_representantes.setItem(row_idx, 13, QTableWidgetItem("Sí" if row_data.get('es_representante_legal') else "No"))
        self.clear_fields()
        self.status_bar.setText(f"Total de representantes: {len(representantes)}")

    def add_representante(self):
        cedula = self.le_cedula.text().strip()
        nacionalidad = self.cb_nacionalidad.currentText()
        nombres = self.le_nombres.text().strip()
        apellidos = self.le_apellidos.text().strip()
        parentesco = self.le_parentesco.text().strip()
        ocupacion = self.le_ocupacion.text().strip()
        direccion = self.le_direccion.text().strip()
        telefono = self.le_telefono.text().strip()
        correo = self.le_correo.text().strip()
        fecha_nacimiento = self.de_fecha_nacimiento.date().toPyDate() # Obtener como objeto date
        genero = self.cb_genero.currentText()
        es_madre = self.chk_es_madre.isChecked()
        es_padre = self.chk_es_padre.isChecked()
        es_representante_legal = self.chk_es_representante_legal.isChecked()

        if not cedula or not nombres or not apellidos:
            QMessageBox.warning(self, "Advertencia", "Cédula, Nombres y Apellidos son campos obligatorios.")
            return

        data = (
            cedula, nacionalidad, nombres, apellidos, parentesco, ocupacion,
            direccion, telefono, correo, fecha_nacimiento, genero,
            es_madre, es_padre, es_representante_legal
        )
        if self.model.add_representante(data):
            QMessageBox.information(self, "Éxito", "Representante añadido correctamente.")
            self.load_representantes()
            self.status_bar.setText(f"Representante {nombres} {apellidos} añadido.")
        else:
            self.status_bar.setText("Error al añadir representante.")

    def update_representante(self):
        original_cedula = self.le_cedula.text().strip()

        selected_items = self.table_representantes.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un representante de la tabla para actualizar.")
            return

        row_index = selected_items[0].row()
        cedula_from_selected_item = self.table_representantes.item(row_index, 0).text()

        if cedula_from_selected_item != original_cedula:
            QMessageBox.critical(self, "Error Lógico", "La cédula en el formulario no coincide con la fila seleccionada. Recargue la selección.")
            return

        nacionalidad = self.cb_nacionalidad.currentText()
        nombres = self.le_nombres.text().strip()
        apellidos = self.le_apellidos.text().strip()
        parentesco = self.le_parentesco.text().strip()
        ocupacion = self.le_ocupacion.text().strip()
        direccion = self.le_direccion.text().strip()
        telefono = self.le_telefono.text().strip()
        correo = self.le_correo.text().strip()
        fecha_nacimiento = self.de_fecha_nacimiento.date().toPyDate()
        genero = self.cb_genero.currentText()
        es_madre = self.chk_es_madre.isChecked()
        es_padre = self.chk_es_padre.isChecked()
        es_representante_legal = self.chk_es_representante_legal.isChecked()

        if not nombres or not apellidos:
            QMessageBox.warning(self, "Advertencia", "Nombres y Apellidos son campos obligatorios.")
            return

        data = (
            nacionalidad, nombres, apellidos, parentesco, ocupacion,
            direccion, telefono, correo, fecha_nacimiento, genero,
            es_madre, es_padre, es_representante_legal
        )

        if self.model.update_representante(original_cedula, data):
            QMessageBox.information(self, "Éxito", "Representante actualizado correctamente.")
            self.load_representantes()
            self.status_bar.setText(f"Representante {nombres} {apellidos} actualizado.")
        else:
            self.status_bar.setText("Error al actualizar representante.")

    def delete_representante(self):
        selected_items = self.table_representantes.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un representante de la tabla para eliminar.")
            return

        row = selected_items[0].row()
        cedula_to_delete = self.table_representantes.item(row, 0).text()
        nombre_completo = f"{self.table_representantes.item(row, 2).text()} {self.table_representantes.item(row, 3).text()}"

        reply = QMessageBox.question(self, "Confirmar Eliminación",
                                     f"¿Está seguro de que desea eliminar al representante '{nombre_completo}' (Cédula: {cedula_to_delete})?\n"
                                     "Los estudiantes asociados a él quedarán sin representante vinculado.\n"
                                     "Esta acción es irreversible.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.model.delete_representante(cedula_to_delete):
                QMessageBox.information(self, "Éxito", "Representante eliminado correctamente.")
                self.load_representantes()
                self.status_bar.setText(f"Representante {cedula_to_delete} eliminado.")
            else:
                self.status_bar.setText(f"Error al eliminar representante {cedula_to_delete}.")

    def search_representantes(self):
        search_term = self.le_search.text().strip()
        
        if not search_term:
            self.load_representantes() # Recargar todos si la búsqueda está vacía
            return

        results = self.model.search_representantes(search_term)
        self.table_representantes.setRowCount(0)
        if results:
            self.table_representantes.setRowCount(len(results))
            for row_idx, row_data in enumerate(results):
                # Acceder a los datos por clave de diccionario
                self.table_representantes.setItem(row_idx, 0, QTableWidgetItem(str(row_data.get('cedula', ''))))
                self.table_representantes.setItem(row_idx, 1, QTableWidgetItem(str(row_data.get('nacionalidad', ''))))
                self.table_representantes.setItem(row_idx, 2, QTableWidgetItem(str(row_data.get('nombres', ''))))
                self.table_representantes.setItem(row_idx, 3, QTableWidgetItem(str(row_data.get('apellidos', ''))))
                self.table_representantes.setItem(row_idx, 4, QTableWidgetItem(str(row_data.get('parentesco', ''))))
                self.table_representantes.setItem(row_idx, 5, QTableWidgetItem(str(row_data.get('ocupacion', ''))))
                self.table_representantes.setItem(row_idx, 6, QTableWidgetItem(str(row_data.get('direccion', ''))))
                self.table_representantes.setItem(row_idx, 7, QTableWidgetItem(str(row_data.get('telefono', ''))))
                self.table_representantes.setItem(row_idx, 8, QTableWidgetItem(str(row_data.get('correo', ''))))
                
                fecha_nac = row_data.get('fecha_nacimiento')
                self.table_representantes.setItem(row_idx, 9, QTableWidgetItem(fecha_nac.strftime("%Y-%m-%d") if fecha_nac else ""))
                
                self.table_representantes.setItem(row_idx, 10, QTableWidgetItem(str(row_data.get('genero', ''))))
                self.table_representantes.setItem(row_idx, 11, QTableWidgetItem("Sí" if row_data.get('es_madre') else "No"))
                self.table_representantes.setItem(row_idx, 12, QTableWidgetItem("Sí" if row_data.get('es_padre') else "No"))
                self.table_representantes.setItem(row_idx, 13, QTableWidgetItem("Sí" if row_data.get('es_representante_legal') else "No"))
        else:
            self.table_students.setRowCount(0) # Limpiar tabla de estudiantes si no hay resultados
            self.status_bar.setText("No se encontraron representantes con ese criterio.")
        self.clear_fields() # Limpiar el formulario después de la búsqueda

    def load_representante_to_form(self):
        selected_items = self.table_representantes.selectedItems()

        if selected_items:
            row = selected_items[0].row()
            # Obtener la cédula de la tabla para buscar los datos completos del representante
            cedula = self.table_representantes.item(row, 0).text()
            representante_data = self.model.get_representante_by_cedula(cedula)

            if representante_data:
                self.le_cedula.setText(representante_data.get('cedula', ''))
                self.le_cedula.setReadOnly(True) # No permitir editar la cédula en modo edición
                self.cb_nacionalidad.setCurrentText(representante_data.get('nacionalidad', ''))
                self.le_nombres.setText(representante_data.get('nombres', ''))
                self.le_apellidos.setText(representante_data.get('apellidos', ''))
                self.le_parentesco.setText(representante_data.get('parentesco', ''))
                self.le_ocupacion.setText(representante_data.get('ocupacion', ''))
                self.le_direccion.setText(representante_data.get('direccion', ''))
                self.le_telefono.setText(representante_data.get('telefono', ''))
                self.le_correo.setText(representante_data.get('correo', ''))

                fecha_nacimiento = representante_data.get('fecha_nacimiento')
                if fecha_nacimiento:
                    self.de_fecha_nacimiento.setDate(QDate(fecha_nacimiento.year, fecha_nacimiento.month, fecha_nacimiento.day))
                else:
                    self.de_fecha_nacimiento.clear()

                self.cb_genero.setCurrentText(representante_data.get('genero', ''))
                self.chk_es_madre.setChecked(representante_data.get('es_madre', False))
                self.chk_es_padre.setChecked(representante_data.get('es_padre', False))
                self.chk_es_representante_legal.setChecked(representante_data.get('es_representante_legal', False))

                self.btn_update.setEnabled(True)
                self.btn_delete.setEnabled(True)
                self.btn_add.setEnabled(False)

                self.load_students_for_representante(cedula)
                self.status_bar.setText(f"Representante {representante_data.get('nombres')} {representante_data.get('apellidos')} cargado para edición.")
            else:
                QMessageBox.warning(self, "Error", "No se pudieron cargar los datos del representante seleccionado.")
                self.clear_fields()
        else:
            self.clear_fields() # Si no hay selección, limpiar el formulario

    def clear_fields(self):
        self.le_cedula.clear()
        self.le_cedula.setReadOnly(False) # Habilitar edición de cédula para nueva entrada
        self.cb_nacionalidad.setCurrentIndex(0)
        self.le_nombres.clear()
        self.le_apellidos.clear()
        self.le_parentesco.clear()
        self.le_ocupacion.clear()
        self.le_direccion.clear()
        self.le_telefono.clear()
        self.le_correo.clear()
        self.de_fecha_nacimiento.setDate(QDate.currentDate())
        self.cb_genero.setCurrentIndex(0)
        self.chk_es_madre.setChecked(False)
        self.chk_es_padre.setChecked(False)
        self.chk_es_representante_legal.setChecked(False)

        self.btn_update.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_add.setEnabled(True)
        self.table_students.setRowCount(0) # Limpiar tabla de estudiantes asociados
        self.status_bar.setText("Formulario limpiado. Listo para nueva entrada.")
        self.table_representantes.clearSelection() # Deseleccionar filas en la tabla principal

    def load_students_for_representante(self, cedula_representante):
        students = self.model.get_students_by_representante_cedula(cedula_representante)
        self.table_students.setRowCount(0)
        if students:
            self.table_students.setRowCount(len(students))
            for row_idx, row_data in enumerate(students):
                self.table_students.setItem(row_idx, 0, QTableWidgetItem(str(row_data.get('cedula', ''))))
                self.table_students.setItem(row_idx, 1, QTableWidgetItem(str(row_data.get('nombres', ''))))
                self.table_students.setItem(row_idx, 2, QTableWidgetItem(str(row_data.get('apellidos', ''))))
                
                fecha_nac_est = row_data.get('fecha_nacimiento')
                self.table_students.setItem(row_idx, 3, QTableWidgetItem(fecha_nac_est.strftime("%Y-%m-%d") if fecha_nac_est else ""))
                
                self.table_students.setItem(row_idx, 4, QTableWidgetItem(str(row_data.get('codigo_ano_escolar', ''))))
                self.table_students.setItem(row_idx, 5, QTableWidgetItem(str(row_data.get('codigo_seccion', ''))))
        else:
            self.status_bar.setText("No hay estudiantes asociados a este representante.")

    def go_back_to_menu(self):
        """Cierra esta ventana y emite una señal para que el menú principal se muestre."""
        self.close()

    def closeEvent(self, event):
        """Sobrescribe el evento de cierre para desconectar la base de datos y emitir la señal."""
        self.db.disconnect()
        self.closed.emit()
        super().closeEvent(event)

# Bloque para ejecutar la aplicación (solo para pruebas directas del módulo)
# if __name__ == "__main__":
#     app = QApplication(sys.argv)

#     test_db_config = {
#         "host": "localhost",
#         "database": "SIGME2", # Asegúrate de que esta DB exista y tenga las tablas
#         "user": "postgres",
#         "password": "1234",
#         "port": "5432"
#     }
#     test_user_data = {
#         'id': '1',
#         'codigo_usuario': 'testuser',
#         'cedula_personal': 'V-12345678',
#         'rol': 'control de estudio',
#         'estado': 'activo',
#         'debe_cambiar_clave': False
#     }

#     window = RepresentanteApp(db_config=test_db_config, user_data=test_user_data)
#     window.show()
#     sys.exit(app.exec())
