import sys
import psycopg2
from psycopg2 import sql, Error # Importar Error
from psycopg2.extras import RealDictCursor # Para obtener resultados como diccionarios
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QGroupBox, QSpinBox, QTabWidget,
                             QTextEdit, QHeaderView,QFrame)
from PyQt6.QtCore import Qt, pyqtSignal # Importar pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
import os
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm 
from io import BytesIO # Importar BytesIO para manejar datos de imagen
import base64 # Importar base64 para decodificar imágenes de prueba

# --- Definición de la Paleta de Colores (Centralizada) ---
PRIMARY_COLOR = '#1c355b' # Azul oscuro fuerte
ACCENT_COLOR = '#7089a7'  # Azul grisáceo medio
LIGHT_BACKGROUND = '#e4eaf4' # Azul muy claro para fondos
TEXT_COLOR = '#333333' # Gris oscuro para texto
WHITE_COLOR = '#FFFFFF'
SUCCESS_COLOR = '#16a34a' # Verde
ERROR_COLOR = '#dc2626'   # Rojo
FONT_FAMILY = 'Arial'


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

    def fetch_image_data(self, image_id):
        """
        Obtiene los datos binarios y el tipo MIME de una imagen por su ID.
        Retorna un diccionario con 'datos_imagen' y 'mime_type' o None si no se encuentra.
        """
        if not self.connection or self.connection.closed:
            if not self.connect():
                # No mostrar QMessageBox aquí para no interrumpir la generación del reporte
                return None
        
        try:
            query = "SELECT datos_imagen, mime_type FROM imagenes WHERE id = %s;"
            self.cursor.execute(query, (image_id,))
            return self.cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Error obteniendo datos de imagen para reporte: {e}")
            return None


class AsignacionDocenteWindow(QMainWindow):
    """
    Ventana para la gestión de Asignación Docente.
    Permite asignar materias a docentes, consultar asignaciones y generar reportes.
    """
    closed = pyqtSignal() # Señal para indicar que la ventana se ha cerrado

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db = DatabaseConnection(self.db_config) # Usar la clase DatabaseConnection
        self.init_db_connection_and_tables() # Inicializar DB y tablas
        self.init_ui()
        self.cargar_datos_iniciales()
        self.showFullScreen() # Mostrar la ventana en pantalla completa

    def init_db_connection_and_tables(self):
        """
        Intenta conectar a la base de datos y crear las tablas necesarias si no existen.
        """
        print("Iniciando conexión y configuración de tablas para Asignación Docente...")
        if not self.db.connect():
            print("Fallo la conexión inicial a la base de datos.")
            return False

        print("Conexión exitosa, verificando/creando tablas...")
        
        # Crear tabla ano_escolar si no existe
        create_ano_escolar_query = """
        CREATE TABLE IF NOT EXISTS ano_escolar (
            codigo VARCHAR(20) PRIMARY KEY,
            descripcion VARCHAR(100) NOT NULL,
            activo BOOLEAN DEFAULT TRUE,
            ano_inicio INTEGER,
            ano_fin INTEGER,
            fecha_inicio DATE,
            fecha_fin DATE
        );
        """
        if not self.db.execute_query(create_ano_escolar_query):
            print("Error al crear la tabla 'ano_escolar'.")
            self.db.disconnect()
            return False

        # Crear tabla grado si no existe
        create_grado_query = """
        CREATE TABLE IF NOT EXISTS grado (
            codigo VARCHAR(20) PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            numero_ano INTEGER UNIQUE NOT NULL,
            activo BOOLEAN DEFAULT TRUE
        );
        """
        if not self.db.execute_query(create_grado_query):
            print("Error al crear la tabla 'grado'.")
            self.db.disconnect()
            return False

        # Crear tabla seccion si no existe
        create_seccion_query = """
        CREATE TABLE IF NOT EXISTS seccion (
            codigo VARCHAR(20) PRIMARY KEY,
            letra CHAR(1) NOT NULL,
            codigo_grado VARCHAR(20) NOT NULL,
            codigo_ano_escolar VARCHAR(20) NOT NULL,
            activo BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (codigo_grado) REFERENCES grado (codigo),
            FOREIGN KEY (codigo_ano_escolar) REFERENCES ano_escolar (codigo)
        );
        """
        if not self.db.execute_query(create_seccion_query):
            print("Error al crear la tabla 'seccion'.")
            self.db.disconnect()
            return False

        # Crear tabla materia si no existe
        create_materia_query = """
        CREATE TABLE IF NOT EXISTS materia (
            codigo VARCHAR(20) PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            horas_semanales INTEGER NOT NULL,
            codigo_grado VARCHAR(20) NOT NULL,
            area_formacion VARCHAR(100),
            estado CHAR(1) DEFAULT 'A',
            FOREIGN KEY (codigo_grado) REFERENCES grado (codigo)
        );
        """
        if not self.db.execute_query(create_materia_query):
            print("Error al crear la tabla 'materia'.")
            self.db.disconnect()
            return False

        # Crear tabla personal (docentes) si no existe
        create_personal_query = """
        CREATE TABLE IF NOT EXISTS personal (
            cedula VARCHAR(20) PRIMARY KEY,
            nombres VARCHAR(100) NOT NULL,
            apellidos VARCHAR(100) NOT NULL,
            cargo VARCHAR(50) NOT NULL,
            estado CHAR(1) DEFAULT 'A'
        );
        """
        if not self.db.execute_query(create_personal_query):
            print("Error al crear la tabla 'personal'.")
            self.db.disconnect()
            return False

        # Crear tabla institucion si no existe
        create_institucion_query = """
        CREATE TABLE IF NOT EXISTS institucion (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            codigo_dea VARCHAR(50),
            direccion TEXT,
            municipio VARCHAR(100),
            estado VARCHAR(100)
        );
        """
        if not self.db.execute_query(create_institucion_query):
            print("Error al crear la tabla 'institucion'.")
            self.db.disconnect()
            return False

        # Ensure 'imagenes' table exists (needed for id_imagen FK)
        create_imagenes_query = """
        CREATE TABLE IF NOT EXISTS imagenes (
            id SERIAL PRIMARY KEY,
            nombre_archivo VARCHAR(255) NOT NULL,
            mime_type VARCHAR(50) NOT NULL,
            datos_imagen BYTEA NOT NULL, -- Para almacenar los datos binarios de la imagen
            fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        if not self.db.execute_query(create_imagenes_query):
            print("Error al crear la tabla 'imagenes'.")
            self.db.disconnect()
            return False

        # Crear tabla asignacion_docente si no existe
        create_asignacion_docente_query = """
        CREATE TABLE IF NOT EXISTS asignacion_docente (
            id SERIAL PRIMARY KEY,
            cedula_docente VARCHAR(20) NOT NULL,
            codigo_seccion VARCHAR(20) NOT NULL,
            codigo_materia VARCHAR(20) NOT NULL,
            codigo_ano_escolar VARCHAR(20) NOT NULL,
            horas_asignadas INTEGER NOT NULL,
            turno CHAR(1) NOT NULL,
            id_imagen INTEGER, -- NUEVA COLUMNA
            FOREIGN KEY (cedula_docente) REFERENCES personal (cedula),
            FOREIGN KEY (codigo_seccion) REFERENCES seccion (codigo),
            FOREIGN KEY (codigo_materia) REFERENCES materia (codigo),
            FOREIGN KEY (codigo_ano_escolar) REFERENCES ano_escolar (codigo),
            FOREIGN KEY (id_imagen) REFERENCES imagenes (id), -- FK a la tabla de imágenes
            UNIQUE (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar)
        );
        """
        if not self.db.execute_query(create_asignacion_docente_query):
            print("Error al crear la tabla 'asignacion_docente'.")
            self.db.disconnect()
            return False
        
        # ALTER TABLE para añadir la columna id_imagen si no existe (para actualizaciones de esquema)
        alter_table_query = """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='asignacion_docente' AND column_name='id_imagen') THEN
                ALTER TABLE asignacion_docente ADD COLUMN id_imagen INTEGER;
                ALTER TABLE asignacion_docente ADD CONSTRAINT fk_asignacion_docente_imagen FOREIGN KEY (id_imagen) REFERENCES imagenes(id);
            END IF;
        END
        $$;
        """
        if not self.db.execute_query(alter_table_query):
            print("Error al añadir la columna 'id_imagen' a 'asignacion_docente'.")
            self.db.disconnect()
            return False

        print("Todas las tablas verificadas/creadas correctamente.")
        return True

    def init_ui(self):
        self.setWindowTitle("Asignación Docente - Sistema Académico")
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # --- Título Principal y Botón Volver al Menú ---
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {PRIMARY_COLOR}; border-radius: 5px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel("MÓDULO DE ASIGNACIÓN DOCENTE")
        title_label.setFont(QFont(FONT_FAMILY, 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {WHITE_COLOR}; background-color: {PRIMARY_COLOR};")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.back_to_menu_button = QPushButton('Volver al Menú')
        self.back_to_menu_button.setObjectName('backButton')
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        header_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(header_frame)
        
        # Tabs
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Tab 1: Asignación
        self.tab_asignacion = self.crear_tab_asignacion()
        tab_widget.addTab(self.tab_asignacion, "Asignación Docente")
        
        # Tab 2: Consultas
        self.tab_consultas = self.crear_tab_consultas()
        tab_widget.addTab(self.tab_consultas, "Consultar Asignaciones")
        
        # Tab 3: Reportes
        self.tab_reportes = self.crear_tab_reportes()
        tab_widget.addTab(self.tab_reportes, "Generar Reportes")

        self.apply_styles() # Cambiado de aplicar_estilos a apply_styles para consistencia

    def apply_styles(self): # Renombrado para consistencia
        """Aplica los estilos QSS a la ventana y sus widgets."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {LIGHT_BACKGROUND};
            }}
            QTabWidget::pane {{
                border: 1px solid {ACCENT_COLOR};
                background-color: {LIGHT_BACKGROUND};
                border-radius: 8px;
            }}
            QTabWidget::tab-bar {{
                left: 5px;
            }}
            QTabBar::tab {{
                background-color: {ACCENT_COLOR};
                color: {WHITE_COLOR};
                border: 1px solid {PRIMARY_COLOR};
                padding: 8px 20px;
                margin-right: 2px;
                font-weight: bold;
                min-width: 130px; 
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QTabBar::tab:selected {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                border-color: {PRIMARY_COLOR};
                border-bottom: 2px solid {LIGHT_BACKGROUND}; /* Para que se vea conectado al contenido */
                margin-bottom: -2px;
            }}
            QTabBar::tab:hover {{
                background-color: #5d7490; /* Tono más oscuro de ACCENT_COLOR */
            }}
            QGroupBox {{
                font-weight: bold;
                color: {PRIMARY_COLOR};
                border: 2px solid {ACCENT_COLOR};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {WHITE_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: {ACCENT_COLOR};
                color: {WHITE_COLOR};
                border-radius: 4px;
            }}
            QLabel {{
                color: {PRIMARY_COLOR};
                font-weight: 500;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QLineEdit, QComboBox {{
                border: 2px solid {ACCENT_COLOR};
                border-radius: 6px;
                padding: 6px;
                background-color: {WHITE_COLOR};
                color: {TEXT_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {PRIMARY_COLOR};
                outline: none;
            }}
            QTableWidget {{
                gridline-color: {ACCENT_COLOR};
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 6px;
                font-family: '{FONT_FAMILY}', sans-serif;
                color: {TEXT_COLOR};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {ACCENT_COLOR};
            }}
            QTableWidget::item:selected {{
                background-color: {ACCENT_COLOR};
                color: {WHITE_COLOR};
            }}
            QHeaderView::section {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                padding: 8px;
                border: none;
                font-weight: bold;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QTextEdit {{
                border: 2px solid {ACCENT_COLOR};
                border-radius: 6px;
                background-color: {WHITE_COLOR};
                color: {TEXT_COLOR};
                padding: 8px;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QPushButton {{
                font-family: '{FONT_FAMILY}', sans-serif;
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                border: none; /* Eliminado el borde para usar solo background-color */
                color: {WHITE_COLOR}; /* Color de texto por defecto para botones */
            }}
            QPushButton#backButton {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
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
            /* Estilos específicos para los botones de acción en las tablas */
            QPushButton.actionButtonTable {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
            }}
            QPushButton.actionButtonTable:hover {{
                background-color: {ACCENT_COLOR};
            }}
            QPushButton.actionButtonTable:pressed {{
                background-color: #1a2e4d;
            }}
            QPushButton.deleteButtonTable {{
                background-color: {ERROR_COLOR};
                color: {WHITE_COLOR};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9pt;
            }}
            QPushButton.deleteButtonTable:hover {{
                background-color: #c02121;
            }}
            QPushButton.deleteButtonTable:pressed {{
                background-color: #a51a1a;
            }}
            /* Estilos para los botones principales de Guardar y Limpiar */
            QPushButton {{ /* Estilo general para todos los QPushButton no sobreescritos */
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
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
        """)
    
    def crear_tab_asignacion(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Grupo de filtros
        grupo_filtros = QGroupBox("Seleccionar Período y Sección")
        filtros_layout = QGridLayout()
        
        # Año escolar
        filtros_layout.addWidget(QLabel("Año Escolar:"), 0, 0)
        self.combo_ano = QComboBox()
        filtros_layout.addWidget(self.combo_ano, 0, 1)
        
        # Grado
        filtros_layout.addWidget(QLabel("Grado:"), 0, 2)
        self.combo_grado = QComboBox()
        filtros_layout.addWidget(self.combo_grado, 0, 3)
        
        # Sección
        filtros_layout.addWidget(QLabel("Sección:"), 1, 0)
        self.combo_seccion = QComboBox()
        filtros_layout.addWidget(self.combo_seccion, 1, 1)
        
        # Botón cargar materias
        btn_cargar = QPushButton("Cargar Materias")
        btn_cargar.clicked.connect(self.cargar_materias)
        filtros_layout.addWidget(btn_cargar, 1, 2)
        
        grupo_filtros.setLayout(filtros_layout)
        layout.addWidget(grupo_filtros)
        
        # Tabla de asignaciones
        self.tabla_asignaciones = QTableWidget()
        self.tabla_asignaciones.setColumnCount(8) # Aumentado a 8 columnas para "Imagen"
        self.tabla_asignaciones.setHorizontalHeaderLabels([
            "Materia", "Código", "Horas", "Docente Actual", "Nuevo Docente", "Turno", "Imagen", "Acciones" # Añadida "Imagen"
        ])
        self.tabla_asignaciones.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_asignaciones)
        
        # Botones de acción
        botones_layout = QHBoxLayout()
        
        btn_guardar = QPushButton("Guardar Todas las Asignaciones")
        btn_guardar.clicked.connect(self.guardar_todas_asignaciones)
        botones_layout.addWidget(btn_guardar)
        
        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.clicked.connect(self.limpiar_tabla)
        botones_layout.addWidget(btn_limpiar)
        
        layout.addLayout(botones_layout)
        tab.setLayout(layout)
        return tab
    
    def crear_tab_consultas(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Filtros para consulta
        grupo_consulta = QGroupBox("Filtros de Consulta")
        consulta_layout = QGridLayout()
        
        consulta_layout.addWidget(QLabel("Año Escolar:"), 0, 0)
        self.combo_ano_consulta = QComboBox()
        consulta_layout.addWidget(self.combo_ano_consulta, 0, 1)
        
        consulta_layout.addWidget(QLabel("Docente (Cédula):"), 0, 2)
        self.txt_cedula_consulta = QLineEdit()
        consulta_layout.addWidget(self.txt_cedula_consulta, 0, 3)
        
        btn_consultar = QPushButton("Consultar")
        btn_consultar.clicked.connect(self.consultar_asignaciones)
        consulta_layout.addWidget(btn_consultar, 0, 4)
        
        grupo_consulta.setLayout(consulta_layout)
        layout.addWidget(grupo_consulta)
        
        # Tabla de resultados
        self.tabla_consulta = QTableWidget()
        self.tabla_consulta.setColumnCount(7)
        self.tabla_consulta.setHorizontalHeaderLabels([
            "Docente", "Cédula", "Grado", "Sección", "Materia", "Horas", "Turno"
        ])
        self.tabla_consulta.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_consulta)
        
        tab.setLayout(layout)
        return tab
    
    def crear_tab_reportes(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Selección de reporte
        grupo_reporte = QGroupBox("Generar Reportes")
        reporte_layout = QGridLayout()
        
        reporte_layout.addWidget(QLabel("Año Escolar:"), 0, 0)
        self.combo_ano_reporte = QComboBox()
        reporte_layout.addWidget(self.combo_ano_reporte, 0, 1)
        
        reporte_layout.addWidget(QLabel("Tipo de Reporte:"), 0, 2)
        self.combo_tipo_reporte = QComboBox()
        self.combo_tipo_reporte.addItems([
            "Nómina de Profesores por Sección PDF",
            "Profesores por Área", 
            "Horas por Docente",
            "Carga Horaria PDF"
        ])
        reporte_layout.addWidget(self.combo_tipo_reporte, 0, 3)
        
        btn_generar = QPushButton("Generar Reporte")
        btn_generar.clicked.connect(self.generar_reporte)
        reporte_layout.addWidget(btn_generar, 1, 0)
        
        grupo_reporte.setLayout(reporte_layout)
        layout.addWidget(grupo_reporte)
        
        # Área de vista previa del reporte
        self.texto_reporte = QTextEdit()
        self.texto_reporte.setFont(QFont("Courier", 10))
        layout.addWidget(self.texto_reporte)
        
        tab.setLayout(layout)
        return tab
    
    def cargar_datos_iniciales(self):
        """
        Carga los años escolares y grados disponibles en los ComboBoxes.
        """
        # Cargar años escolares
        query = "SELECT codigo, descripcion, ano_inicio FROM ano_escolar WHERE activo = true ORDER BY ano_inicio DESC"
        anos = self.db.fetch_all(query) # Usar fetch_all
        
        for combo in [self.combo_ano, self.combo_ano_consulta, self.combo_ano_reporte]:
            combo.clear()
            for ano in anos:
                combo.addItem(f"{ano['descripcion']}", ano['codigo']) # Acceder por clave de diccionario
        
        # Cargar grados
        query = "SELECT codigo, nombre FROM grado WHERE activo = true ORDER BY numero_ano"
        grados = self.db.fetch_all(query) # Usar fetch_all
        
        self.combo_grado.clear()
        for grado in grados:
            self.combo_grado.addItem(f"{grado['nombre']}", grado['codigo']) # Acceder por clave de diccionario
        
        # Conectar cambio de grado para cargar secciones
        self.combo_grado.currentTextChanged.connect(self.cargar_secciones)
        self.cargar_secciones() # Cargar secciones inicialmente

    def cargar_secciones(self):
        """
        Carga las secciones disponibles para el grado y año escolar seleccionados.
        """
        if not self.combo_grado.currentData() or not self.combo_ano.currentData():
            self.combo_seccion.clear()
            return
        
        grado_codigo = self.combo_grado.currentData()
        ano_codigo = self.combo_ano.currentData()
        
        query = """
            SELECT codigo, letra 
            FROM seccion 
            WHERE codigo_grado = %s AND codigo_ano_escolar = %s 
            ORDER BY letra
        """
        secciones = self.db.fetch_all(query, (grado_codigo, ano_codigo)) # Usar fetch_all
        
        self.combo_seccion.clear()
        for seccion in secciones:
            self.combo_seccion.addItem(f"{seccion['letra']}", seccion['codigo']) # Acceder por clave de diccionario
    
    def get_all_image_ids(self):
        """Obtiene todos los IDs y nombres de archivo de la tabla imagenes."""
        query = "SELECT id, nombre_archivo FROM imagenes ORDER BY id DESC"
        return self.db.fetch_all(query)

    def cargar_materias(self):
        """
        Carga las materias para la sección seleccionada, incluyendo el docente actual asignado.
        """
        if not self.combo_seccion.currentData():
            QMessageBox.warning(self, "Advertencia", "Seleccione una sección")
            return
        
        grado_codigo = self.combo_grado.currentData()
        seccion_codigo = self.combo_seccion.currentData()
        ano_codigo = self.combo_ano.currentData()
        
        # Obtener materias del grado con información de asignación y el ID de la imagen
        query = """
            SELECT m.codigo, m.nombre, m.horas_semanales,
                   COALESCE(p.nombres || ' ' || p.apellidos, 'Sin asignar') as docente_actual,
                   ad.cedula_docente,
                   COALESCE(ad.turno, 'M') as turno_actual,
                   ad.id_imagen -- Añadido id_imagen
            FROM materia m
            LEFT JOIN asignacion_docente ad ON (m.codigo = ad.codigo_materia 
                                                AND ad.codigo_seccion = %s 
                                                AND ad.codigo_ano_escolar = %s)
            LEFT JOIN personal p ON ad.cedula_docente = p.cedula
            WHERE m.codigo_grado = %s AND m.estado = 'A'
            ORDER BY m.nombre
        """
        
        materias = self.db.fetch_all(query, (seccion_codigo, ano_codigo, grado_codigo)) # Usar fetch_all
        
        self.tabla_asignaciones.setRowCount(len(materias))

        # Cargar los IDs de imagen disponibles una sola vez para poblar los ComboBoxes
        available_image_ids = self.get_all_image_ids()
        
        for i in range(len(materias)):
            self.tabla_asignaciones.setRowHeight(i, 45)

        for row, materia in enumerate(materias):
            # Materia (solo lectura)
            item_materia = QTableWidgetItem(materia['nombre']) # Acceder por clave de diccionario
            item_materia.setFlags(item_materia.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_asignaciones.setItem(row, 0, item_materia)
            
            # Código (solo lectura)
            item_codigo = QTableWidgetItem(materia['codigo']) # Acceder por clave de diccionario
            item_codigo.setFlags(item_codigo.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_asignaciones.setItem(row, 1, item_codigo)
            
            # Horas (solo lectura)
            item_horas = QTableWidgetItem(str(materia['horas_semanales'])) # Acceder por clave de diccionario
            item_horas.setFlags(item_horas.flags() & ~Qt.ItemFlag.ItemIsEditable) # Asegurar que no sea editable
            self.tabla_asignaciones.setItem(row, 2, item_horas)
            
            # Docente actual (solo lectura)
            item_docente_actual = QTableWidgetItem(materia['docente_actual']) # Acceder por clave de diccionario
            item_docente_actual.setFlags(item_docente_actual.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tabla_asignaciones.setItem(row, 3, item_docente_actual)
            
            # ComboBox para nuevo docente
            combo_docente = QComboBox()
            combo_docente.addItem("Sin asignar", "")
            
            # Cargar docentes disponibles
            query_docentes = """
                SELECT cedula, nombres || ' ' || apellidos as nombre_completo
                FROM personal 
                WHERE cargo = 'Docente' AND estado = 'A'
                ORDER BY apellidos, nombres
            """
            docentes = self.db.fetch_all(query_docentes) # Usar fetch_all
            
            for docente in docentes:
                combo_docente.addItem(f"{docente['nombre_completo']} ({docente['cedula']})", docente['cedula']) # Acceder por clave de diccionario
            
            # Si ya tiene docente asignado, seleccionarlo
            if materia['cedula_docente']: # Acceder por clave de diccionario
                index = combo_docente.findData(materia['cedula_docente'])
                if index >= 0:
                    combo_docente.setCurrentIndex(index)
            
            self.tabla_asignaciones.setCellWidget(row, 4, combo_docente)
            
            # ComboBox para turno
            combo_turno = QComboBox()
            combo_turno.addItem("Mañana", "M")
            combo_turno.addItem("Tarde", "T")
            combo_turno.addItem("Noche", "N")
            
            # Seleccionar turno actual
            turno_actual = materia['turno_actual'] if materia['turno_actual'] else "M" # Acceder por clave de diccionario
            index_turno = combo_turno.findData(turno_actual)
            if index_turno >= 0:
                combo_turno.setCurrentIndex(index_turno)
            
            self.tabla_asignaciones.setCellWidget(row, 5, combo_turno)

            # ComboBox para la imagen (Nuevo)
            combo_imagen = QComboBox()
            combo_imagen.addItem("Ninguna (Opcional)", None) # Opción para no asociar imagen
            for img in available_image_ids:
                combo_imagen.addItem(f"ID: {img['id']} - {img['nombre_archivo']}", img['id'])
            
            # Si ya tiene imagen asignada, seleccionarla
            if materia['id_imagen'] is not None:
                index_imagen = combo_imagen.findData(materia['id_imagen'])
                if index_imagen >= 0:
                    combo_imagen.setCurrentIndex(index_imagen)
            
            self.tabla_asignaciones.setCellWidget(row, 6, combo_imagen) # Columna 6 para la imagen
            
            # Layout para botones de acción (ahora en la columna 7)
            widget_acciones = QWidget()
            layout_acciones = QHBoxLayout()
            layout_acciones.setContentsMargins(2, 2, 2, 2)
            
            btn_actualizar = QPushButton("Actualizar")
            btn_actualizar.setObjectName('actionButtonTable') # Usar Object Name para estilos
            btn_actualizar.clicked.connect(lambda checked, r=row: self.actualizar_asignacion(r))
            layout_acciones.addWidget(btn_actualizar)
            
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setObjectName('deleteButtonTable') # Usar Object Name para estilos
            btn_eliminar.clicked.connect(lambda checked, r=row: self.eliminar_asignacion(r))
            layout_acciones.addWidget(btn_eliminar)
            
            widget_acciones.setLayout(layout_acciones)
            self.tabla_asignaciones.setCellWidget(row, 7, widget_acciones) # Columna 7 para acciones

    def actualizar_asignacion(self, row):
        codigo_materia = self.tabla_asignaciones.item(row, 1).text()
        combo_docente = self.tabla_asignaciones.cellWidget(row, 4)
        combo_turno = self.tabla_asignaciones.cellWidget(row, 5)
        combo_imagen = self.tabla_asignaciones.cellWidget(row, 6) # Obtener el combo de imagen
        
        cedula_docente = combo_docente.currentData()
        turno = combo_turno.currentData()
        id_imagen = combo_imagen.currentData() # Obtener el ID de la imagen seleccionada
        
        if not cedula_docente:
            QMessageBox.warning(self, "Advertencia", "Seleccione un docente")
            return
        
        seccion_codigo = self.combo_seccion.currentData()
        ano_codigo = self.combo_ano.currentData()
        
        # VALIDAR HORAS
        try:
            horas_text = self.tabla_asignaciones.item(row, 2).text()
            horas = int(horas_text)
            if horas <= 0:
                QMessageBox.warning(self, "Error", "Las horas deben ser un número positivo")
                return
        except ValueError:
            QMessageBox.warning(self, "Error", "Las horas deben ser un número válido")
            return
        
        # Verificar si ya existe asignación para esta materia, sección y año escolar
        query_check = """
            SELECT id, cedula_docente, horas_asignadas, turno, id_imagen 
            FROM asignacion_docente 
            WHERE codigo_materia = %s AND codigo_seccion = %s AND codigo_ano_escolar = %s
        """
        existing_assignment = self.db.fetch_one(query_check, (codigo_materia, seccion_codigo, ano_codigo))

        if existing_assignment:
            # Si ya existe, actualizamos
            query_update = """
                UPDATE asignacion_docente
                SET cedula_docente = %s, horas_asignadas = %s, turno = %s, id_imagen = %s
                WHERE id = %s
            """
            data = (cedula_docente, horas, turno, id_imagen, existing_assignment['id'])
            if self.db.execute_query(query_update, data):
                QMessageBox.information(self, "Éxito", "Asignación actualizada correctamente.")
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar la asignación.")
        else:
            # Si no existe, insertamos
            query_insert = """
                INSERT INTO asignacion_docente (cedula_docente, codigo_seccion, codigo_materia, 
                                                codigo_ano_escolar, horas_asignadas, turno, id_imagen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            data = (cedula_docente, seccion_codigo, codigo_materia, 
                    ano_codigo, horas, turno, id_imagen)
            if self.db.execute_query(query_insert, data):
                QMessageBox.information(self, "Éxito", "Asignación añadida correctamente.")
            else:
                QMessageBox.critical(self, "Error", "No se pudo añadir la asignación. Es posible que ya exista una combinación idéntica.")
        
        self.cargar_materias() # Recargar la tabla para reflejar los cambios

    def eliminar_asignacion(self, row):
        codigo_materia = self.tabla_asignaciones.item(row, 1).text()
        nombre_materia = self.tabla_asignaciones.item(row, 0).text()
        seccion_codigo = self.combo_seccion.currentData()
        ano_codigo = self.combo_ano.currentData()
        
        # Confirmar eliminación
        respuesta = QMessageBox.question(
            self, 
            "Confirmar Eliminación", 
            f"¿Está seguro que desea eliminar la asignación de la materia '{nombre_materia}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            query = """
                DELETE FROM asignacion_docente 
                WHERE codigo_materia = %s AND codigo_seccion = %s AND codigo_ano_escolar = %s
            """
            parametros = (codigo_materia, seccion_codigo, ano_codigo)
            
            if self.db.execute_query(query, parametros): # Usar execute_query
                QMessageBox.information(self, "Éxito", "Asignación eliminada correctamente")
                self.cargar_materias()  # Recargar para mostrar cambios
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar la asignación")
    
    def guardar_todas_asignaciones(self):
        """Guarda todas las asignaciones que tienen docente seleccionado"""
        if self.tabla_asignaciones.rowCount() == 0:
            QMessageBox.warning(self, "Advertencia", "No hay materias cargadas")
            return
        
        guardadas = 0
        errores = 0
        
        for row in range(self.tabla_asignaciones.rowCount()):
            combo_docente = self.tabla_asignaciones.cellWidget(row, 4)
            combo_turno = self.tabla_asignaciones.cellWidget(row, 5)
            combo_imagen = self.tabla_asignaciones.cellWidget(row, 6) # Obtener el combo de imagen
            
            if combo_docente and combo_docente.currentData():  # Solo si hay docente seleccionado
                try:
                    codigo_materia = self.tabla_asignaciones.item(row, 1).text()
                    cedula_docente = combo_docente.currentData()
                    turno = combo_turno.currentData()
                    id_imagen = combo_imagen.currentData() # Obtener el ID de la imagen seleccionada
                    seccion_codigo = self.combo_seccion.currentData()
                    ano_codigo = self.combo_ano.currentData()
                    
                    # VALIDAR HORAS
                    try:
                        horas_text = self.tabla_asignaciones.item(row, 2).text()
                        horas = int(horas_text)
                        if horas <= 0:
                            print(f"Error en fila {row}: Horas inválidas")
                            errores += 1
                            continue
                    except ValueError:
                        print(f"Error en fila {row}: Horas no es un número")
                        errores += 1
                        continue
                    
                    # Verificar si ya existe asignación
                    query_check = """
                        SELECT id FROM asignacion_docente 
                        WHERE codigo_materia = %s AND codigo_seccion = %s AND codigo_ano_escolar = %s
                    """
                    # Usar fetch_one en lugar de fetch_all si solo esperamos una fila
                    existe_record = self.db.fetch_one(query_check, (codigo_materia, seccion_codigo, ano_codigo)) 
                    
                    if existe_record:
                        # Actualizar
                        query = """
                            UPDATE asignacion_docente 
                            SET cedula_docente = %s, horas_asignadas = %s, turno = %s, id_imagen = %s
                            WHERE codigo_materia = %s AND codigo_seccion = %s AND codigo_ano_escolar = %s
                        """
                        parametros = (cedula_docente, horas, turno, id_imagen, codigo_materia, seccion_codigo, ano_codigo)
                    else:
                        # Insertar
                        query = """
                            INSERT INTO asignacion_docente 
                            (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar, 
                             horas_asignadas, turno, id_imagen)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        parametros = (cedula_docente, seccion_codigo, codigo_materia, ano_codigo, horas, turno, id_imagen)
                    
                    if self.db.execute_query(query, parametros): # Usar execute_query
                        guardadas += 1
                    else:
                        errores += 1
                        
                except Exception as e:
                    print(f"Error procesando fila {row}: {e}")
                    errores += 1
        
        # Recargar datos para mostrar cambios
        self.cargar_materias()
        
        # Mostrar resultado
        mensaje = f"Proceso completado:\n"
        mensaje += f"Asignaciones guardadas: {guardadas}\n"
        if errores > 0:
            mensaje += f"Errores: {errores}"
            QMessageBox.warning(self, "Resultado", mensaje)
        else:
            QMessageBox.information(self, "Éxito", mensaje)
    
    def limpiar_tabla(self):
        self.tabla_asignaciones.setRowCount(0)
        # También limpiar los combos de filtro para una limpieza más completa
        self.combo_ano.setCurrentIndex(-1)
        self.combo_grado.setCurrentIndex(-1)
        self.combo_seccion.clear()
        QMessageBox.information(self, "Limpiar", "Tabla y filtros de asignación limpiados.")
    
    def consultar_asignaciones(self):
        ano_codigo = self.combo_ano_consulta.currentData()
        cedula_filtro = self.txt_cedula_consulta.text().strip()
        
        query = """
            SELECT p.nombres || ' ' || p.apellidos as docente_nombre,
                   p.cedula,
                   g.nombre as grado,
                   s.letra as seccion,
                   m.nombre as materia,
                   ad.horas_asignadas,
                   CASE ad.turno 
                       WHEN 'M' THEN 'Mañana'
                       WHEN 'T' THEN 'Tarde'
                       WHEN 'N' THEN 'Noche'
                       ELSE ad.turno
                   END as turno
            FROM asignacion_docente ad
            JOIN personal p ON ad.cedula_docente = p.cedula
            JOIN materia m ON ad.codigo_materia = m.codigo
            JOIN seccion s ON ad.codigo_seccion = s.codigo
            JOIN grado g ON s.codigo_grado = g.codigo
            WHERE ad.codigo_ano_escolar = %s
        """
        
        parametros = [ano_codigo]
        
        if cedula_filtro:
            query += " AND p.cedula LIKE %s"
            parametros.append(f"%{cedula_filtro}%")
        
        query += " ORDER BY p.apellidos, p.nombres, g.numero_ano, s.letra"
        
        resultados = self.db.fetch_all(query, parametros) # Usar fetch_all
        
        self.tabla_consulta.setRowCount(len(resultados))
        
        for row, resultado in enumerate(resultados):
            self.tabla_consulta.setItem(row, 0, QTableWidgetItem(str(resultado['docente_nombre'])))
            self.tabla_consulta.setItem(row, 1, QTableWidgetItem(str(resultado['cedula'])))
            self.tabla_consulta.setItem(row, 2, QTableWidgetItem(str(resultado['grado'])))
            self.tabla_consulta.setItem(row, 3, QTableWidgetItem(str(resultado['seccion'])))
            self.tabla_consulta.setItem(row, 4, QTableWidgetItem(str(resultado['materia'])))
            self.tabla_consulta.setItem(row, 5, QTableWidgetItem(str(resultado['horas_asignadas'])))
            self.tabla_consulta.setItem(row, 6, QTableWidgetItem(str(resultado['turno'])))
        
        if not resultados:
            QMessageBox.information(self, "Sin Resultados", "No se encontraron asignaciones con los filtros especificados.")

    def generar_reporte(self):
        ano_codigo = self.combo_ano_reporte.currentData()
        tipo_reporte = self.combo_tipo_reporte.currentText()
        
        if not ano_codigo:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un Año Escolar para generar el reporte.")
            return

        if tipo_reporte == "Nómina de Profesores por Sección PDF":
            self.generar_nomina_profesores(ano_codigo)
        elif tipo_reporte == "Profesores por Área":
            self.generar_resumen_final(ano_codigo)
        elif tipo_reporte == "Horas por Docente":
            self.generar_carga_horaria(ano_codigo)
        elif tipo_reporte == "Carga Horaria PDF":
            self.generar_carga_horaria_horizontal(ano_codigo)
    
    
    def generar_nomina_profesores(self, ano_codigo):
        """
        Genera un PDF con la nómina de profesores por sección, incluyendo un logo
        y la imagen asociada a la asignación si existe.
        """
        # Obtener datos del año escolar
        query_ano = "SELECT descripcion FROM ano_escolar WHERE codigo = %s"
        ano_desc_record = self.db.fetch_one(query_ano, (ano_codigo,)) # Usar fetch_one
        ano_texto = ano_desc_record['descripcion'] if ano_desc_record else "Año no encontrado"
        
        # Crear el PDF horizontal con márgenes ajustados
        filename = f"Nomina_Profesores_{ano_texto.replace(' ', '_')}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=(29.7*cm, 21.01*cm), 
                                 topMargin=1*cm,
                                 bottomMargin=1*cm,
                                 leftMargin=1.5*cm,
                                 rightMargin=1.5*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Crear tabla de encabezado con logo y título
        logo_cell = ""
        try:
            # Cargar logo desde la base de datos (ID 2 para el logo principal)
            logo_data = self.db.fetch_image_data(2) 
            if logo_data and logo_data['datos_imagen']:
                logo = Image(BytesIO(logo_data['datos_imagen']), width=1.2*inch, height=1.2*inch)
                logo_cell = logo
            else:
                logo_cell = ""
                print("Advertencia: No se pudo cargar el logo principal (ID 2) desde la base de datos.")
        except Exception as e:
            print(f"Error cargando logo principal desde DB: {e}")
            logo_cell = ""
        
        # Crear estilo para el título con subrayado
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=0,
            spaceBefore=0
        )

        title_text = f"<u>NÓMINA DE PROFESORES {ano_texto.upper()}</u>"
        title_para = Paragraph(title_text, title_style)
        
        # Tabla de encabezado con tamaños ajustados
        header_table = Table([[logo_cell, title_para]], 
                             colWidths=[3*cm, 23*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 20))
        
        # Obtener secciones
        query_secciones = """
            SELECT DISTINCT g.numero_ano, g.nombre as grado_nombre, s.letra, s.codigo as seccion_codigo
            FROM grado g
            JOIN seccion s ON g.codigo = s.codigo_grado
            WHERE s.codigo_ano_escolar = %s
            ORDER BY g.numero_ano, s.letra
        """
        
        secciones = self.db.fetch_all(query_secciones, (ano_codigo,)) # Usar fetch_all
        
        # Agrupar por grado
        grados_dict = {}
        for seccion in secciones:
            grado_num = seccion['numero_ano'] # Acceder por clave de diccionario
            if grado_num not in grados_dict:
                grados_dict[grado_num] = []
            grados_dict[grado_num].append(seccion)
        
        # Generar tabla para cada grado (máximo 3 secciones por fila)
        for grado_num in sorted(grados_dict.keys()):
            secciones_grado = grados_dict[grado_num]
            
            # Procesar secciones de 3 en 3
            for i in range(0, len(secciones_grado), 3):
                secciones_grupo = secciones_grado[i:i+3]
                
                # Crear datos de la tabla
                table_data = []
                num_secciones = len(secciones_grupo)
                
                # Calcular ancho disponible
                ancho_disponible = 26.7 * cm  # Ancho total menos márgenes
                ancho_por_seccion = ancho_disponible / num_secciones

                # Ajustar anchos según número de secciones y contenido
                if num_secciones <= 2:
                    ancho_materia = ancho_por_seccion * 0.4
                    ancho_nombre = ancho_por_seccion * 0.4
                    ancho_imagen = ancho_por_seccion * 0.2 # Espacio para la imagen
                elif num_secciones == 3:
                    ancho_materia = ancho_por_seccion * 0.35
                    ancho_nombre = ancho_por_seccion * 0.35
                    ancho_imagen = ancho_por_seccion * 0.3 # Espacio para la imagen
                else:  # Más de 3 secciones (aunque el código solo procesa hasta 3 en el grupo)
                    ancho_materia = ancho_por_seccion * 0.3
                    ancho_nombre = ancho_por_seccion * 0.3
                    ancho_imagen = ancho_por_seccion * 0.4 # Espacio para la imagen
                
                # Crear colWidths dinámicamente
                col_widths = []
                for j in range(num_secciones):
                    col_widths.extend([ancho_materia, ancho_nombre, ancho_imagen]) # Materia, Nombre, Imagen
                
                # Fila de encabezado con nombres de secciones
                header_row = []
                for j in range(num_secciones):
                    seccion = secciones_grupo[j]
                    numero_grado = self.obtener_numero_ordinal(seccion['numero_ano']) # Acceder por clave de diccionario
                    seccion_texto = f'{numero_grado} "{seccion["letra"]}"' # Acceder por clave de diccionario
                    header_row.extend([seccion_texto, '', '']) # Span para la sección
                table_data.append(header_row)
                
                # Fila "PROFESORES DE AREAS"
                prof_row = []
                for j in range(num_secciones):
                    prof_row.extend(['PROFESORES DE AREAS', '', '']) # Span para profesores de áreas
                table_data.append(prof_row)
                
                # Fila de encabezado columnas
                col_header_row = []
                for j in range(num_secciones):
                    col_header_row.extend(['MATERIA', 'NOMBRE', 'IMAGEN']) # Nuevo encabezado de imagen
                table_data.append(col_header_row)
                
                # Obtener materias para este grado
                materias_grado = self.obtener_materias_por_grado(grado_num)
                
                # Crear filas para cada materia
                for materia in materias_grado:
                    materia_row = []
                    for j in range(num_secciones):
                        if j < len(secciones_grupo):
                            seccion = secciones_grupo[j]
                            # Obtener docente asignado y su imagen
                            asignacion_data = self.obtener_docente_asignado_con_imagen(seccion['seccion_codigo'], materia['codigo'], ano_codigo) # Modificado
                            
                            docente_completo = asignacion_data['docente_nombre'] if asignacion_data else ""
                            id_imagen = asignacion_data['id_imagen'] if asignacion_data else None

                            if not docente_completo:
                                docente_completo = ""
                            
                            # Ajustar texto según número de secciones
                            docente_mostrar = docente_completo
                            if num_secciones >= 3:
                                materia_nombre = self.abreviar_materia(materia['nombre']) # Acceder por clave de diccionario
                            else:
                                materia_nombre = materia['nombre'] # Acceder por clave de diccionario
                            
                            materia_row.extend([materia_nombre.upper(), docente_mostrar.upper()])

                            # Añadir la imagen
                            if id_imagen:
                                image_record = self.db.fetch_image_data(id_imagen)
                                if image_record and image_record['datos_imagen']:
                                    try:
                                        image_buffer = BytesIO(image_record['datos_imagen'])
                                        # Ajustar el tamaño de la imagen para que encaje en la celda
                                        img = Image(image_buffer, width=1.5*cm, height=1.5*cm) 
                                        img.hAlign = 'CENTER'
                                        materia_row.append(img)
                                    except Exception as e:
                                        print(f"Error al procesar imagen para PDF (ID: {id_imagen}): {e}")
                                        materia_row.append(Paragraph("Error", styles['Normal']))
                                else:
                                    materia_row.append(Paragraph("N/A", styles['Normal'])) # No se encontraron datos de imagen
                            else:
                                materia_row.append(Paragraph("N/A", styles['Normal'])) # No hay ID de imagen
                        else:
                            materia_row.extend(['', '', '']) # Celdas vacías para secciones no existentes
                    
                    table_data.append(materia_row)

                row_heights = [0.5*cm] * len(table_data)
                tabla = Table(table_data, colWidths=col_widths, rowHeights=row_heights)
                
                # Aplicar estilos con fuente ajustable según número de secciones
                font_size = 9 if num_secciones <= 2 else (8 if num_secciones == 3 else 7)

                # CORRECCIÓN: Envolver las expresiones generadoras en corchetes []
                tabla.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), font_size),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('WORDWRAP', (0, 0), (-1, -1), True),
                ] + [ # <-- CORRECCIÓN AQUÍ
                    ('SPAN', (j*3, 0), (j*3+2, 0)) for j in range(num_secciones)
                ] + [ # <-- Y AQUÍ
                    ('SPAN', (j*3, 1), (j*3+2, 1)) for j in range(num_secciones)
                ]))

                # Configurar tabla para no dividirse
                tabla.splitByRow = False

                # Agrupar tabla con su espaciado
                tabla_completa = KeepTogether([tabla, Spacer(1, 15)])
                elements.append(tabla_completa)
        
        # Generar PDF
        try:
            doc.build(elements)
            # Mostrar mensaje de éxito
            QMessageBox.information(self, "PDF Generado", f"El archivo {filename} ha sido creado exitosamente")
            # Abrir el archivo
            try:
                os.startfile(filename)  # Windows
            except AttributeError: # os.startfile no existe en todos los OS
                try:
                    os.system(f"open {filename}")  # macOS
                except:
                    os.system(f"xdg-open {filename}") # Linux
        except Exception as e:
            QMessageBox.critical(self, "Error al Generar PDF", f"Ocurrió un error al generar el PDF: {e}")

    def abreviar_materia(self, materia_nombre):
        """Abrevia nombres de materias largas"""
        abreviaciones = {
            'EDUCACIÓN FÍSICA': 'ED. FÍSICA',
            'EDUCACION FISICA': 'ED. FÍSICA',
            'CIENCIAS NATURALES': 'CS.NAT',
            'GEOGRAFÍA, HISTORIA Y CIUDADANÍA': 'GEO/HIST/CIUD',
            'GEOGRAFIA, HISTORIA Y CIUDADANIA': 'GEO/HIST/CIUD',
            'CIENCIAS DE LA TIERRA': 'CS. DE LA TIERRA',
            'FORMACIÓN PARA LA SOBERANÍA': 'SOBERANÍA',
            'FORMACION PARA LA SOBERANIA': 'SOBERANÍA'
        }
        return abreviaciones.get(materia_nombre.upper(), materia_nombre)
    
    def obtener_solo_apellidos(self, nombre_completo):
        """Extrae solo los apellidos del nombre completo"""
        if not nombre_completo:
            return ''
        partes = nombre_completo.split()
        if len(partes) >= 2:
            # Asume que los últimos dos elementos son los apellidos
            return ' '.join(partes[-2:])
        return nombre_completo

    def obtener_numero_ordinal(self, numero):
        """Convierte número a ordinal (1->1ero, 2->2do, etc.)"""
        ordinales = {1: "1ero.", 2: "2do.", 3: "3ero.", 4: "4to.", 5: "5to."}
        return ordinales.get(numero, f"{numero}to.")

    def obtener_materias_por_grado(self, grado_numero):
        """Obtiene las materias de un grado específico"""
        query = """
            SELECT m.codigo, m.nombre
            FROM materia m
            JOIN grado g ON m.codigo_grado = g.codigo
            WHERE g.numero_ano = %s AND m.estado = 'A'
            ORDER BY m.nombre
        """
        return self.db.fetch_all(query, (grado_numero,)) # Usar fetch_all

    def obtener_docente_asignado_con_imagen(self, seccion_codigo, materia_codigo, ano_codigo):
        """
        Obtiene el docente asignado (nombre completo) y el ID de la imagen
        para una materia, sección y año escolar específicos.
        """
        query = """
            SELECT p.nombres || ' ' || p.apellidos AS docente_nombre,
                   ad.id_imagen
            FROM asignacion_docente ad
            JOIN personal p ON ad.cedula_docente = p.cedula
            WHERE ad.codigo_seccion = %s AND ad.codigo_materia = %s AND ad.codigo_ano_escolar = %s
        """
        resultado = self.db.fetch_one(query, (seccion_codigo, materia_codigo, ano_codigo)) # Usar fetch_one
        return resultado # Retorna el diccionario o None
    
    def generar_resumen_final(self, ano_codigo):
        """Genera un reporte de texto de profesores por área de formación."""
        query = """
            SELECT s.codigo, g.nombre || ' "' || s.letra || '"' as seccion_completa,
                   m.area_formacion,
                   m.codigo as codigo_materia,
                   m.nombre as materia,
                   p.nombres, p.apellidos, p.cedula,
                   CASE ad.turno 
                       WHEN 'M' THEN 'Mañana'
                       WHEN 'T' THEN 'Tarde'
                       WHEN 'N' THEN 'Noche'
                       ELSE ad.turno
                   END as turno
            FROM asignacion_docente ad
            JOIN personal p ON ad.cedula_docente = p.cedula
            JOIN materia m ON ad.codigo_materia = m.codigo
            JOIN seccion s ON ad.codigo_seccion = s.codigo
            JOIN grado g ON s.codigo_grado = g.codigo
            WHERE ad.codigo_ano_escolar = %s
            ORDER BY g.numero_ano, s.letra, m.area_formacion, m.nombre
        """
        resultados = self.db.fetch_all(query, (ano_codigo,)) # Usar fetch_all
        
        reporte = "PROFESORES POR ÁREA\n"
        reporte += "=" * 50 + "\n\n"
        
        seccion_actual = ""
        for resultado in resultados:
            if resultado['seccion_completa'] != seccion_actual: # Acceder por clave de diccionario
                seccion_actual = resultado['seccion_completa'] # Acceder por clave de diccionario
                reporte += f"\nSECCIÓN: {seccion_actual}\n"
                reporte += "=" * 40 + "\n"
            
            reporte += f"Área: {resultado['area_formacion'] or 'General'}\n" # Acceder por clave de diccionario
            reporte += f"Código: {resultado['codigo_materia']} - Materia: {resultado['materia']}\n" # Acceder por clave de diccionario
            reporte += f"Profesor: {resultado['nombres']} {resultado['apellidos']}\n" # Acceder por clave de diccionario
            reporte += f"C.I.: {resultado['cedula']}\n" # Acceder por clave de diccionario
            reporte += f"Turno: {resultado['turno']}\n" # Acceder por clave de diccionario
        
        self.texto_reporte.setText(reporte)
        QMessageBox.information(self, "Reporte Generado", "Reporte de Profesores por Área generado en la vista previa.")
    
    def generar_carga_horaria(self, ano_codigo):
        """Genera un reporte de texto de horas asignadas por docente."""
        query = """
            SELECT p.cedula, p.nombres || ' ' || p.apellidos as docente,
                   SUM(ad.horas_asignadas) as total_horas,
                   COUNT(ad.codigo_materia) as total_materias,
                   STRING_AGG(
                       g.nombre || ' "' || s.letra || '" - ' || m.nombre || ' (' || 
                       CASE ad.turno 
                           WHEN 'M' THEN 'Mañana'
                           WHEN 'T' THEN 'Tarde'
                           WHEN 'N' THEN 'Noche'
                           ELSE ad.turno
                       END || '): ' || ad.horas_asignadas || 'h', 
                       E'\n'
                   ) as detalle_materias
            FROM asignacion_docente ad
            JOIN personal p ON ad.cedula_docente = p.cedula
            JOIN materia m ON ad.codigo_materia = m.codigo
            JOIN seccion s ON ad.codigo_seccion = s.codigo
            JOIN grado g ON s.codigo_grado = g.codigo
            WHERE ad.codigo_ano_escolar = %s
            GROUP BY p.cedula, p.nombres, p.apellidos
            ORDER BY p.apellidos, p.nombres
        """
        
        resultados = self.db.fetch_all(query, (ano_codigo,)) # Usar fetch_all

        reporte = "HORAS POR DOCENTE\n"
        reporte += "=" * 50 + "\n\n"
        
        for resultado in resultados:
            reporte += f"Docente: {resultado['docente']}\n" # Acceder por clave de diccionario
            reporte += f"C.I.: {resultado['cedula']}\n" # Acceder por clave de diccionario
            reporte += f"Total Horas: {resultado['total_horas']}\n" # Acceder por clave de diccionario
            reporte += f"Total Materias: {resultado['total_materias']}\n" # Acceder por clave de diccionario
            reporte += f"Detalle de Asignaciones:\n"
            reporte += f"{resultado['detalle_materias']}\n" # Acceder por clave de diccionario
            reporte += "-" * 50 + "\n\n"
        
        self.texto_reporte.setText(reporte)
        QMessageBox.information(self, "Reporte Generado", "Reporte de Horas por Docente generado en la vista previa.")

    def generar_carga_horaria_horizontal(self, ano_codigo):
        """
        Genera un PDF con la carga horaria detallada por docente en formato horizontal.
        """
        # Obtener datos del año escolar
        query_ano = "SELECT descripcion FROM ano_escolar WHERE codigo = %s"
        ano_desc_record = self.db.fetch_one(query_ano, (ano_codigo,)) # Usar fetch_one
        ano_texto = ano_desc_record['descripcion'] if ano_desc_record else "Año no encontrado"
        
        # Crear PDF horizontal
        filename = f"Carga_Horaria_Horizontal_{ano_texto.replace(' ', '_')}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=(31.5*cm, 21.49*cm), 
                                 topMargin=1*cm, bottomMargin=1*cm,
                                 leftMargin=1*cm, rightMargin=1*cm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Encabezado
        self.agregar_encabezado_carga_horizontal(elements, styles, ano_texto)
        
        # Obtener datos de docentes y materias
        datos_docentes = self.obtener_datos_carga_horizontal(ano_codigo)
        
        # Crear tabla principal
        tabla_data = self.construir_tabla_carga_horizontal(datos_docentes)
        
        # Configurar y aplicar estilos a la tabla
        tabla = self.crear_tabla_carga_horizontal(tabla_data)
        
        elements.append(tabla)
        
        # Generar PDF
        try:
            doc.build(elements)
            
            QMessageBox.information(self, "PDF Generado", f"El archivo {filename} ha sido creado exitosamente")
            
            # Abrir archivo
            try:
                os.startfile(filename)
            except AttributeError:
                try:
                    os.system(f"open {filename}")
                except:
                    os.system(f"xdg-open {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Generar PDF", f"Ocurrió un error al generar el PDF: {e}")

    def agregar_encabezado_carga_horizontal(self, elements, styles, ano_texto):
        datos_inst = self.obtener_datos_institucion()
        
        # Logos
        logo_left = ""
        logo_right = ""
        
        try:
            # Logo izquierdo (ID 3 para logo2.png)
            logo2_data = self.db.fetch_image_data(3) 
            if logo2_data and logo2_data['datos_imagen']:
                logo_left = Image(BytesIO(logo2_data['datos_imagen']), width=1.0*inch, height=1.0*inch)
            else:
                logo_left = ""
                print("Advertencia: No se pudo cargar el logo izquierdo (ID 3) desde la base de datos.")
        except Exception as e:
            print(f"Error cargando logo izquierdo desde DB: {e}")
            pass
        
        try:
            # Logo derecho (ID 2 para logo.png)
            logo_data = self.db.fetch_image_data(2)
            if logo_data and logo_data['datos_imagen']:
                logo_right = Image(BytesIO(logo_data['datos_imagen']), width=1.0*inch, height=1.0*inch)
            else:
                logo_right = ""
                print("Advertencia: No se pudo cargar el logo derecho (ID 2) desde la base de datos.")
        except Exception as e:
            print(f"Error cargando logo derecho desde DB: {e}")
            pass
        
        # Estilo para el encabezado institucional
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            leading=12
        )
        
        # Crear texto del encabezado institucional
        header_text = f"""
        República Bolivariana de Venezuela<br/>
        Gobernación del Estado Bolivariano de {datos_inst['estado']}<br/>
        Dirección General de Educación<br/>
        {datos_inst['nombre']} COD-DEA: {datos_inst['codigo_dea']}<br/>
        {datos_inst['direccion']} - Edo. {datos_inst['estado']}
        """
        
        header_para = Paragraph(header_text, header_style)
        
        # Tabla con 3 columnas: logo izquierdo, encabezado institucional, logo derecho
        header_table = Table([[logo_left, header_para, logo_right]], 
                             colWidths=[2.5*cm, 24.5*cm, 2.5*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),    # Logo izquierdo
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Encabezado centrado
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),   # Logo derecho
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 10))
        
        # Título del reporte (separado del encabezado institucional)
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        )
        
        title_text = f"<u>CARGA HORARIA DOCENTE - {ano_texto.upper()}</u>"
        title_para = Paragraph(title_text, title_style)
        
        elements.append(title_para)
        elements.append(Spacer(1, 15))

    def obtener_datos_carga_horizontal(self, ano_codigo):
        # Obtener materias por grado
        query_materias = """
            SELECT DISTINCT g.numero_ano, m.codigo, m.nombre, m.horas_semanales
            FROM materia m
            JOIN grado g ON m.codigo_grado = g.codigo
            WHERE m.estado = 'A'
            ORDER BY g.numero_ano, m.nombre
        """
        materias = self.db.fetch_all(query_materias) # Usar fetch_all
        
        # Obtener docentes y sus asignaciones (solo nombres)
        query_docentes = """
            SELECT p.cedula, p.nombres || ' ' || p.apellidos as nombre_completo,
                   ad.codigo_materia, ad.horas_asignadas,
                   g.numero_ano, s.letra
            FROM personal p
            LEFT JOIN asignacion_docente ad ON p.cedula = ad.cedula_docente AND ad.codigo_ano_escolar = %s
            LEFT JOIN materia m ON ad.codigo_materia = m.codigo
            LEFT JOIN grado g ON m.codigo_grado = g.codigo
            LEFT JOIN seccion s ON ad.codigo_seccion = s.codigo
            WHERE p.cargo = 'Docente' AND p.estado = 'A'
            ORDER BY p.nombres
        """
        docentes = self.db.fetch_all(query_docentes, (ano_codigo,)) # Usar fetch_all
        
        return {'materias': materias, 'docentes': docentes}

    def construir_tabla_carga_horizontal(self, datos):
        materias = datos['materias']
        docentes = datos['docentes']
        
        # Agrupar materias por grado
        materias_por_grado = {}
        for materia in materias:
            grado = materia['numero_ano'] # Acceder por clave de diccionario
            if grado not in materias_por_grado:
                materias_por_grado[grado] = []
            materias_por_grado[grado].append(materia)
        
        # Crear estructura de la tabla
        tabla_data = []
        
        # Fila 1: Encabezados de áreas
        header_areas = ['N°', 'DOCENTE', 'CARGA\nHORARIA']
        for grado in sorted(materias_por_grado.keys()):
            header_areas.extend([f'{grado}° AÑO'] + [''] * (len(materias_por_grado[grado]) - 1))
        header_areas.append('TOTAL\nHORAS')
        tabla_data.append(header_areas)
        
        # Fila 2: Nombres de materias
        header_materias = ['', '', '']
        for grado in sorted(materias_por_grado.keys()):
            for materia in materias_por_grado[grado]:
                # Abreviar materias más agresivamente
                nombre_abrev = self.abrev_materia(materia['nombre']) # Acceder por clave de diccionario
                header_materias.append(nombre_abrev)
        header_materias.append('')
        tabla_data.append(header_materias)
        
        # Fila 3: Horas por materia
        header_horas = ['', '', '']
        for grado in sorted(materias_por_grado.keys()):
            for materia in materias_por_grado[grado]:
                header_horas.append(str(materia['horas_semanales'])) # Acceder por clave de diccionario
        header_horas.append('')
        tabla_data.append(header_horas)
        
        # Procesar docentes
        docentes_procesados = {}
        for docente in docentes:
            cedula = docente['cedula'] # Acceder por clave de diccionario
            if cedula not in docentes_procesados:
                docentes_procesados[cedula] = {
                    'nombre': docente['nombre_completo'], # Acceder por clave de diccionario
                    'asignaciones': {},
                    'total_horas': 0
                }
            
            if docente['codigo_materia']:  # Si tiene materia asignada
                docentes_procesados[cedula]['asignaciones'][docente['codigo_materia']] = docente['horas_asignadas'] # Acceder por clave de diccionario
                docentes_procesados[cedula]['total_horas'] += docente['horas_asignadas'] or 0 # Acceder por clave de diccionario
        
        # Crear filas de docentes
        num_docente = 1
        for cedula, datos_docente in docentes_procesados.items():
            fila = [str(num_docente), datos_docente['nombre'], str(datos_docente['total_horas'])]
            
            # Agregar horas por materia
            for grado in sorted(materias_por_grado.keys()):
                for materia in materias_por_grado[grado]:
                    codigo_materia = materia['codigo'] # Acceder por clave de diccionario
                    horas = datos_docente['asignaciones'].get(codigo_materia, '')
                    fila.append(str(horas) if horas else '')
            
            fila.append(str(datos_docente['total_horas']))
            tabla_data.append(fila)
            num_docente += 1
        
        return tabla_data

    def abrev_materia(self, nombre_materia):
        # Abreviaciones más cortas para carga horaria
        abreviaciones = {
            'Matemática': 'MAT',
            'Matematica': 'MAT',
            'Castellano': 'CAS',
            'Inglés': 'ING',
            'Ingles': 'ING',
            'Educación Física': 'EF',
            'Educación Fisica': 'EF',
            'Arte y Patrimonio': 'AP',
            'Ciencias Naturales': 'CN',
            'Biología': 'BIO',
            'Física': 'FIS',
            'Fisica': 'FIS',
            'Química': 'QUI',
            'Quimica': 'QUI',
            'Ciencias de la Tierra': 'CT',
            'Formación para la Soberanía': 'FS',
            'Geografía, Historia y Ciudadanía': 'GHC',
            'Orientación y Convivencia': 'OC'
        }
        
        if nombre_materia in abreviaciones:
            return abreviaciones[nombre_materia]
        
        # Máximo 3 caracteres para materias no definidas
        palabras = nombre_materia.split()
        if len(palabras) == 1:
            return nombre_materia[:3].upper()
        else:
            return ''.join([p[0].upper() for p in palabras[:3]])

    def crear_tabla_carga_horizontal(self, tabla_data):
        
        num_cols = len(tabla_data[0])
        ancho_total = 29.5 * cm

        # Anchos más pequeños para materias
        col_widths = [0.6*cm, 3.8*cm, 1.0*cm]   # N°, DOCENTE, CARGA HORARIA
        # El -4 es por las 3 primeras columnas fijas y la última columna de TOTAL HORAS
        ancho_restante = ancho_total - sum(col_widths) - 1.0*cm 
        # Asegurarse de que num_cols - 4 no sea cero o negativo
        num_materias_cols = num_cols - 4
        if num_materias_cols > 0:
            ancho_materia = ancho_restante / num_materias_cols
        else:
            ancho_materia = 0 # No hay columnas de materia

        # Completar anchos
        for i in range(3, num_cols - 1):
            col_widths.append(min(ancho_materia, 1.2*cm))   # Máximo 1.2cm por materia
        col_widths.append(1.0*cm) # Ancho para la columna TOTAL HORAS
        
        # Crear tabla
        tabla = Table(tabla_data, colWidths=col_widths)
        
        # Aplicar estilos
        styles = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('FONTNAME', (0, 0), (-1, 2), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 2), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('WORDWRAP', (0, 0), (-1, -1), True),   # Permitir ajuste de texto
        ]
        
        # Aplicar spans para encabezados de grado
        span_inicio = 3
        materias_por_grado = self.obtener_materias_agrupadas()
        for grado in sorted(materias_por_grado.keys()):
            num_materias = len(materias_por_grado[grado])
            if num_materias > 0: # Solo aplicar span si hay materias en el grado
                styles.append(('SPAN', (span_inicio, 0), (span_inicio + num_materias - 1, 0)))
            span_inicio += num_materias
        
        tabla.setStyle(TableStyle(styles))
        return tabla

    def obtener_materias_agrupadas(self):
        query = """
            SELECT g.numero_ano, m.codigo, m.nombre
            FROM materia m
            JOIN grado g ON m.codigo_grado = g.codigo
            WHERE m.estado = 'A'
            ORDER BY g.numero_ano, m.nombre
        """
        materias = self.db.fetch_all(query, ()) # Usar fetch_all
        
        materias_por_grado = {}
        for materia in materias:
            grado = materia['numero_ano'] # Acceder por clave de diccionario
            if grado not in materias_por_grado:
                materias_por_grado[grado] = []
            materias_por_grado[grado].append(materia)
        
        return materias_por_grado
    
    def go_back_to_menu(self):
        """Cierra esta ventana y emite una señal para que el menú principal se muestre."""
        self.close()

    def closeEvent(self, event):
        """Sobrescribe el evento de cierre para desconectar la base de datos y emitir la señal."""
        self.db.disconnect()
        self.closed.emit() # Emitir la señal de cierre
        super().closeEvent(event)

    def obtener_datos_institucion(self):
        """Obtiene los datos de la institución desde la base de datos"""
        query = """
            SELECT nombre, codigo_dea, direccion, municipio, estado
            FROM institucion
            LIMIT 1
        """
        resultado = self.db.fetch_one(query, ()) # Usar fetch_one
        if resultado:
            # Acceder a los resultados como diccionarios
            return {
                'nombre': resultado['nombre'] or 'U.E.E. "Sin Nombre"',
                'codigo_dea': resultado['codigo_dea'] or 'COD-DEA: No definido',
                'direccion': resultado['direccion'] or 'Dirección no definida',
                'municipio': resultado['municipio'] or 'Municipio no definido',
                'estado': resultado['estado'] or 'Estado no definido'
            }
        else:
            # Valores por defecto si no hay datos
            return {
                'nombre': 'U.E.E. "Carmen Ruíz"',
                'codigo_dea': 'OD00221508',
                'direccion': 'Charallave',
                'municipio': 'Cristóbal Rojas',
                'estado': 'Miranda'
            }

# Bloque para ejecutar la aplicación (solo para pruebas directas del módulo)
if __name__ == '__main__':
    app = QApplication(sys.argv)

    test_db_config = {
        'host': 'localhost',
        'database': 'Sigme', # Asegúrate de que esta DB exista
        'user': 'Diego',
        'password': 'Diego-78',
        'port': '5432'
    }
    test_user_data = {
        'id': '1',
        'codigo_usuario': 'testuser',
        'cedula_personal': 'V-12345678',
        'rol': 'control de estudio',
        'estado': 'activo',
        'debe_cambiar_clave': False
    }

    # --- Configuración de tablas para pruebas ---
    conn = None
    try:
        conn = psycopg2.connect(**test_db_config)
        cursor = conn.cursor()

        # Crear tabla ano_escolar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ano_escolar (
                codigo VARCHAR(20) PRIMARY KEY,
                descripcion VARCHAR(100) NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                ano_inicio INTEGER,
                ano_fin INTEGER,
                fecha_inicio DATE,
                fecha_fin DATE
            );
        """)
        # Insertar datos de prueba para ano_escolar
        cursor.execute("""
            INSERT INTO ano_escolar (codigo, descripcion, activo, ano_inicio, ano_fin, fecha_inicio, fecha_fin)
            VALUES ('2024-2025', 'Año Escolar 2024-2025', TRUE, 2024, 2025, '2024-09-16', '2025-07-15')
            ON CONFLICT (codigo) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO ano_escolar (codigo, descripcion, activo, ano_inicio, ano_fin, fecha_inicio, fecha_fin)
            VALUES ('2023-2024', 'Año Escolar 2023-2024', TRUE, 2023, 2024, '2023-09-15', '2024-07-14')
            ON CONFLICT (codigo) DO NOTHING;
        """)

        # Crear tabla grado
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grado (
                codigo VARCHAR(20) PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                numero_ano INTEGER UNIQUE NOT NULL,
                activo BOOLEAN DEFAULT TRUE
            );
        """)
        # Insertar datos de prueba para grado
        cursor.execute("""
            INSERT INTO grado (codigo, nombre, numero_ano, activo)
            VALUES ('1ER', '1er Grado', 1, TRUE)
            ON CONFLICT (codigo) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO grado (codigo, nombre, numero_ano, activo)
            VALUES ('2DO', '2do Grado', 2, TRUE)
            ON CONFLICT (codigo) DO NOTHING;
        """)

        # Crear tabla seccion
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seccion (
                codigo VARCHAR(20) PRIMARY KEY,
                letra CHAR(1) NOT NULL,
                codigo_grado VARCHAR(20) NOT NULL,
                codigo_ano_escolar VARCHAR(20) NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (codigo_grado) REFERENCES grado (codigo),
                FOREIGN KEY (codigo_ano_escolar) REFERENCES ano_escolar (codigo)
            );
        """)
        # Insertar datos de prueba para seccion
        cursor.execute("""
            INSERT INTO seccion (codigo, letra, codigo_grado, codigo_ano_escolar, activo)
            VALUES ('1ER-A-24-25', 'A', '1ER', '2024-2025', TRUE)
            ON CONFLICT (codigo) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO seccion (codigo, letra, codigo_grado, codigo_ano_escolar, activo)
            VALUES ('1ER-B-24-25', 'B', '1ER', '2024-2025', TRUE)
            ON CONFLICT (codigo) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO seccion (codigo, letra, codigo_grado, codigo_ano_escolar, activo)
            VALUES ('2DO-A-24-25', 'A', '2DO', '2024-2025', TRUE)
            ON CONFLICT (codigo) DO NOTHING;
        """)

        # Crear tabla materia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materia (
                codigo VARCHAR(20) PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                horas_semanales INTEGER NOT NULL,
                codigo_grado VARCHAR(20) NOT NULL,
                area_formacion VARCHAR(100),
                estado CHAR(1) DEFAULT 'A',
                FOREIGN KEY (codigo_grado) REFERENCES grado (codigo)
            );
        """)
        # Insertar datos de prueba para materia
        cursor.execute("""
            INSERT INTO materia (codigo, nombre, horas_semanales, codigo_grado, area_formacion, estado)
            VALUES ('MAT1', 'Matemática I', 5, '1ER', 'Científica', 'A')
            ON CONFLICT (codigo) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO materia (codigo, nombre, horas_semanales, codigo_grado, area_formacion, estado)
            VALUES ('LENG1', 'Lenguaje y Comunicación I', 4, '1ER', 'Humanística', 'A')
            ON CONFLICT (codigo) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO materia (codigo, nombre, horas_semanales, codigo_grado, area_formacion, estado)
            VALUES ('MAT2', 'Matemática II', 6, '2DO', 'Científica', 'A')
            ON CONFLICT (codigo) DO NOTHING;
        """)

        # Crear tabla personal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal (
                cedula VARCHAR(20) PRIMARY KEY,
                nombres VARCHAR(100) NOT NULL,
                apellidos VARCHAR(100) NOT NULL,
                cargo VARCHAR(50) NOT NULL,
                estado CHAR(1) DEFAULT 'A'
            );
        """)
        # Insertar datos de prueba para personal
        cursor.execute("""
            INSERT INTO personal (cedula, nombres, apellidos, cargo, estado)
            VALUES ('V-12345678', 'Juan', 'Perez', 'Docente', 'A')
            ON CONFLICT (cedula) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO personal (cedula, nombres, apellidos, cargo, estado)
            VALUES ('V-87654321', 'Maria', 'Gomez', 'Docente', 'A')
            ON CONFLICT (cedula) DO NOTHING;
        """)
        cursor.execute("""
            INSERT INTO personal (cedula, nombres, apellidos, cargo, estado)
            VALUES ('V-11223344', 'Carlos', 'Ruiz', 'Administrativo', 'A')
            ON CONFLICT (cedula) DO NOTHING;
        """)

        # Crear tabla imagenes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imagenes (
                id SERIAL PRIMARY KEY,
                nombre_archivo VARCHAR(255) NOT NULL,
                mime_type VARCHAR(50) NOT NULL,
                datos_imagen BYTEA NOT NULL,
                fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Insertar una imagen de prueba (ejemplo de un pequeño PNG base64)
        # Este es un PNG de 5x5 píxeles, un solo punto rojo.
        test_image_data_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==")
        # Base64 for a small blue square (10x10px) - for logo.png (ID 2)
        blue_square_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mNkYGD4z8DAwMgAAwMgAAQAAgABzXQv2wAAAABJRU5ErkJggg==")
        # Base64 for a small green circle (10x10px) - for logo2.png (ID 3)
        green_circle_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAHElEQVR42mNgYGD4z0AEEwMTAwMDQyMglhMBAA4sBwT54JpGAAAAAElFTkSuQmCC")


        # Usar ON CONFLICT para manejar si la imagen ya existe
        cursor.execute("""
            INSERT INTO imagenes (id, nombre_archivo, mime_type, datos_imagen)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET nombre_archivo = EXCLUDED.nombre_archivo, mime_type = EXCLUDED.mime_type, datos_imagen = EXCLUDED.datos_imagen;
        """, (1, 'test_image.png', 'image/png', test_image_data_bytes))
        cursor.execute("""
            INSERT INTO imagenes (id, nombre_archivo, mime_type, datos_imagen)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET nombre_archivo = EXCLUDED.nombre_archivo, mime_type = EXCLUDED.mime_type, datos_imagen = EXCLUDED.datos_imagen;
        """, (2, 'logo.png', 'image/png', blue_square_data))
        cursor.execute("""
            INSERT INTO imagenes (id, nombre_archivo, mime_type, datos_imagen)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET nombre_archivo = EXCLUDED.nombre_archivo, mime_type = EXCLUDED.mime_type, datos_imagen = EXCLUDED.datos_imagen;
        """, (3, 'logo2.png', 'image/png', green_circle_data))


        # Crear tabla asignacion_docente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asignacion_docente (
                id SERIAL PRIMARY KEY,
                cedula_docente VARCHAR(20) NOT NULL,
                codigo_seccion VARCHAR(20) NOT NULL,
                codigo_materia VARCHAR(20) NOT NULL,
                codigo_ano_escolar VARCHAR(20) NOT NULL,
                horas_asignadas INTEGER NOT NULL,
                turno CHAR(1) NOT NULL,
                id_imagen INTEGER,
                FOREIGN KEY (cedula_docente) REFERENCES personal (cedula),
                FOREIGN KEY (codigo_seccion) REFERENCES seccion (codigo),
                FOREIGN KEY (codigo_materia) REFERENCES materia (codigo),
                FOREIGN KEY (codigo_ano_escolar) REFERENCES ano_escolar (codigo),
                FOREIGN KEY (id_imagen) REFERENCES imagenes (id),
                UNIQUE (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar)
            );
        """)
        # Insertar datos de prueba para asignacion_docente
        cursor.execute("""
            INSERT INTO asignacion_docente (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar, horas_asignadas, turno, id_imagen)
            VALUES ('V-12345678', '1ER-A-24-25', 'MAT1', '2024-2025', 5, 'M', 1)
            ON CONFLICT (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar) DO UPDATE SET horas_asignadas = EXCLUDED.horas_asignadas, turno = EXCLUDED.turno, id_imagen = EXCLUDED.id_imagen;
        """)
        cursor.execute("""
            INSERT INTO asignacion_docente (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar, horas_asignadas, turno, id_imagen)
            VALUES ('V-87654321', '1ER-A-24-25', 'LENG1', '2024-2025', 4, 'T', NULL)
            ON CONFLICT (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar) DO UPDATE SET horas_asignadas = EXCLUDED.horas_asignadas, turno = EXCLUDED.turno, id_imagen = EXCLUDED.id_imagen;
        """)
        cursor.execute("""
            INSERT INTO asignacion_docente (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar, horas_asignadas, turno, id_imagen)
            VALUES ('V-12345678', '2DO-A-24-25', 'MAT2', '2024-2025', 6, 'M', NULL)
            ON CONFLICT (cedula_docente, codigo_seccion, codigo_materia, codigo_ano_escolar) DO UPDATE SET horas_asignadas = EXCLUDED.horas_asignadas, turno = EXCLUDED.turno, id_imagen = EXCLUDED.id_imagen;
        """)

        # Crear tabla institucion
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institucion (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                codigo_dea VARCHAR(50),
                direccion TEXT,
                municipio VARCHAR(100),
                estado VARCHAR(100)
            );
        """)
        # Insertar datos de prueba para institucion
        cursor.execute("""
            INSERT INTO institucion (id, nombre, codigo_dea, direccion, municipio, estado)
            VALUES (1, 'Unidad Educativa Ejemplo', '0000-00-000', 'Calle Principal #123', 'Municipio Prueba', 'Estado Ejemplo')
            ON CONFLICT (id) DO NOTHING;
        """)

        conn.commit()
        print("Datos de prueba insertados/verificados.")

    except psycopg2.Error as e:
        print(f"Error al inicializar tablas y datos de prueba: {e}")
    finally:
        if conn:
            conn.close()

    # Instancia y muestra la ventana
    asignacion_docente_window = AsignacionDocenteWindow(db_config=test_db_config, user_data=test_user_data)
    asignacion_docente_window.show()
    sys.exit(app.exec())
