import sys
import psycopg2
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QMessageBox,
                             QFrame, QCheckBox, QHeaderView, QComboBox,
                             QGridLayout, QDoubleSpinBox, QDateEdit, QTextEdit,
                             QCompleter, QProgressDialog, QRadioButton, QGroupBox, QFormLayout, QApplication,QFileDialog,QAbstractItemView)
from PyQt6.QtCore import Qt, QSize, QDate, QStringListModel, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
import hashlib
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
import os
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import csv

# --- Definición de la Paleta de Colores ---
COLOR_PRIMARY_BACKGROUND = "#F2F2F2"
COLOR_WHITE = "#FFFFFF"
COLOR_DARK_BLUE = "#1B3659"
COLOR_TEXT_DARK = "#333333"
COLOR_ACCENT_GREEN = "#4CAF50"
COLOR_ACCENT_BLUE = "#2196F3"
COLOR_ACCENT_RED = "#f44336"
COLOR_ACCENT_ORANGE = "#ff9800"
COLOR_PDF_RED = "#D32F2F"
COLOR_SUCCESS_GREEN_LIGHT = "#C8E6C9" # Para fondos de éxito
COLOR_ERROR_RED_LIGHT = "#FFCDD2" # Para fondos de error
COLOR_WARNING_YELLOW_LIGHT = "#FFF9C4" # Para fondos de advertencia

class GestionNotasWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self, db_config, user_data): 
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Notas")
        self.setGeometry(100, 100, 1200, 800)
        
        self.db_config = db_config
        self.user_data = user_data
        self.datos_resumen = []

        self.estudiantes_data = []
        self.estudiante_seleccionado = None
        
        self.apply_global_styles() # Aplicar estilos globales
        self.setup_ui()

    def apply_global_styles(self):
        """Aplica estilos CSS globales a la ventana principal."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_PRIMARY_BACKGROUND};
                font-family: 'Segoe UI', sans-serif;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLOR_DARK_BLUE};
                background-color: {COLOR_WHITE};
                border-radius: 8px;
            }}
            QTabWidget::tab-bar {{
                left: 5px; /* move to the right */
            }}
            QTabBar::tab {{
                background: {COLOR_DARK_BLUE};
                color: {COLOR_WHITE};
                border: 1px solid {COLOR_DARK_BLUE};
                border-bottom-color: {COLOR_DARK_BLUE}; /* same as pane color */
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 15px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {COLOR_WHITE};
                color: {COLOR_DARK_BLUE};
                border-bottom-color: {COLOR_WHITE}; /* make selected tab look like it's part of the pane */
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 {COLOR_DARK_BLUE}, stop: 1 #2A4F7F); /* Lighter hover */
            }}
            QTabBar::tab:selected:hover {{
                background: {COLOR_WHITE};
            }}
            QGroupBox {{
                font-weight: bold;
                color: {COLOR_DARK_BLUE};
                margin-top: 10px;
                border: 1px solid {COLOR_DARK_BLUE};
                border-radius: 8px;
                padding-top: 15px;
                background-color: {COLOR_WHITE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center; /* position at top center */
                padding: 0 3px;
                background-color: {COLOR_DARK_BLUE};
                color: {COLOR_WHITE};
                border-radius: 5px;
            }}
            QLabel {{
                color: {COLOR_TEXT_DARK};
                font-size: 13px;
            }}
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit {{
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 5px;
                background-color: {COLOR_WHITE};
                color: {COLOR_TEXT_DARK};
            }}
            QPushButton {{
                background-color: {COLOR_DARK_BLUE};
                color: {COLOR_WHITE};
                border: none;
                padding: 10px 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #2A4F7F; /* Slightly lighter blue on hover */
            }}
            QPushButton:pressed {{
                background-color: #1A2B40; /* Darker blue when pressed */
            }}
            QTableWidget {{
                border: 1px solid {COLOR_DARK_BLUE};
                border-radius: 8px;
                gridline-color: #DDDDDD;
                background-color: {COLOR_WHITE};
                selection-background-color: #A0C4FF; /* Light blue selection */
                color: {COLOR_TEXT_DARK};
            }}
            QHeaderView::section {{
                background-color: {COLOR_DARK_BLUE};
                color: {COLOR_WHITE};
                padding: 5px;
                border: 1px solid {COLOR_DARK_BLUE};
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QRadioButton {{
                color: {COLOR_TEXT_DARK};
            }}
            QCheckBox {{
                color: {COLOR_TEXT_DARK};
            }}
        """)

    def closeEvent(self, event):
        """
        Sobrescribe el evento de cierre para emitir la señal 'closed'.
        """
        self.closed.emit()
        super().closeEvent(event)

    def convertir_nota_a_literal(self, nota, nombre_materia):
        """Convierte nota numérica a literal para materias OYC y CRP"""
        if nota is None:
            return ""
        
        # Verificar si es materia que requiere literal
        nombre_upper = nombre_materia.upper()
        materias_literales = ['ORIENTACION', 'CONVIVENCIA', 'CRP', 'OYC']
        
        es_materia_literal = any(materia in nombre_upper for materia in materias_literales)
        
        if not es_materia_literal:
            return str(round(nota, 1)) if nota else "" # Redondear a 1 decimal para notas numéricas
        
        # Convertir a literal
        nota_float = float(nota)
        if nota_float >= 18.0:
            return "A"
        elif nota_float >= 15.0:
            return "B"
        elif nota_float >= 12.0:
            return "C"
        elif nota_float >= 10.0:
            return "D"
        else:
            return "E"
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Crear pestañas principales
        self.tab_widget = QTabWidget()
        
        # Pestaña 1: Evaluaciones
        self.tab_evaluaciones = QWidget()
        self.setup_tab_evaluaciones()
        self.tab_widget.addTab(self.tab_evaluaciones, "Momentos")
        
        # Pestaña 2: Docentes
        self.tab_docentes = QWidget()
        self.setup_tab_docentes()
        self.tab_widget.addTab(self.tab_docentes, "Docentes")
        
        # Pestaña 3: Resumen Final
        self.tab_resumen = QWidget()
        self.setup_tab_resumen()
        self.tab_widget.addTab(self.tab_resumen, "Resumen Final")
        
        # Pestaña 4: Boletín
        self.tab_boletin = QWidget()
        self.setup_tab_boletin()
        self.tab_widget.addTab(self.tab_boletin, "Boletín")
        
        # Pestaña 5: Materias Pendientes
        self.tab_pendientes = QWidget()
        self.setup_tab_pendientes()
        self.tab_widget.addTab(self.tab_pendientes, "Momentos Pendientes")
        
        # Pestaña 6: Revisión Académica
        self.tab_revision = QWidget()
        self.setup_tab_revision()
        self.tab_widget.addTab(self.tab_revision, "Revisión Académica")
        
        # Pestaña 7: Estadísticas
        self.tab_estadisticas = QWidget()
        self.setup_tab_estadisticas()
        self.tab_widget.addTab(self.tab_estadisticas, "Estadísticas")
        
        # Layout principal
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)

        # Botón para volver al menú general
        back_button_layout = QHBoxLayout()
        back_button_layout.addStretch() # Empuja el botón a la derecha
        self.btn_back_to_menu = QPushButton("Volver al Menú General")
        self.btn_back_to_menu.setStyleSheet(f"QPushButton {{ background-color: {COLOR_DARK_BLUE}; color: {COLOR_WHITE}; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 14px; min-width: 150px; }} QPushButton:hover {{ background-color: #2A4F7F; }}")
        self.btn_back_to_menu.clicked.connect(self.go_to_general_menu)
        back_button_layout.addWidget(self.btn_back_to_menu)
        layout.addLayout(back_button_layout)

        central_widget.setLayout(layout)
    
    def go_to_general_menu(self):
        """Cierra la ventana actual y emite una señal para volver al menú general."""
        self.close() # Cierra esta ventana. La señal 'closed' se emitirá automáticamente.

    def conectar_db(self):
        """Conecta a la base de datos PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Conexión", f"Error conectando a la base de datos:\n{str(e)}")
            return None
    
    def setup_tab_evaluaciones(self):
        layout = QVBoxLayout()
        
        # Título de la sección
        title = QLabel("Registro de Momentos Evaluativos")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        # Formulario para agregar evaluaciones
        form_group = QGroupBox("Datos de Momento")
        form_layout = QGridLayout()
        
        # Fila 1: Año Escolar únicamente (eliminamos sección)
        form_layout.addWidget(QLabel("Año Escolar:"), 0, 0)
        self.combo_ano_escolar = QComboBox()
        self.combo_ano_escolar.setMinimumWidth(150)
        form_layout.addWidget(self.combo_ano_escolar, 0, 1)
        
        # Fila 2: Estudiante y Materia
        form_layout.addWidget(QLabel("Estudiante:"), 1, 0)
        self.combo_estudiante = QLineEdit()
        self.combo_estudiante.setPlaceholderText("Escriba cédula o nombre del estudiante...")
        self.combo_estudiante.setMinimumWidth(300)

        self.estudiante_completer = QCompleter()
        self.estudiante_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.estudiante_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.estudiante_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_estudiante.setCompleter(self.estudiante_completer)
        self.combo_estudiante.editingFinished.connect(self.validar_estudiante_manual)

        self.combo_estudiante.textChanged.connect(self.filtrar_estudiantes)
        self.estudiante_completer.activated.connect(self.on_estudiante_selected)

        form_layout.addWidget(self.combo_estudiante, 1, 1)
        
        form_layout.addWidget(QLabel("Materia:"), 1, 2)
        self.combo_materia = QComboBox()
        self.combo_materia.setMinimumWidth(200)
        self.combo_materia.currentIndexChanged.connect(self.cargar_docente_materia)
        form_layout.addWidget(self.combo_materia, 1, 3)
        
        # Fila 3: Solo Momento (quitar tipo de evaluación)
        form_layout.addWidget(QLabel("Momento:"), 2, 0)
        self.combo_momento = QComboBox()
        self.combo_momento.addItems(["1", "2", "3"])
        form_layout.addWidget(self.combo_momento, 2, 1)
        
        # Fila 4: Solo Nota y Resultado
        form_layout.addWidget(QLabel("Nota:"), 3, 0)
        self.spin_nota = QDoubleSpinBox()
        self.spin_nota.setRange(0, 20)
        self.spin_nota.setDecimals(1)
        self.spin_nota.setValue(0)
        form_layout.addWidget(self.spin_nota, 3, 1)

        form_layout.addWidget(QLabel("Resultado:"), 3, 2)
        self.combo_resultado = QComboBox()
        self.combo_resultado.addItems(["A", "R"])
        form_layout.addWidget(self.combo_resultado, 3, 3)
        
        # Fila 5: Fecha y Docente
        form_layout.addWidget(QLabel("Fecha:"), 4, 0)
        self.date_evaluacion = QDateEdit()
        self.date_evaluacion.setDate(QDate.currentDate())
        self.date_evaluacion.setCalendarPopup(True)
        form_layout.addWidget(self.date_evaluacion, 4, 1)
        
        form_layout.addWidget(QLabel("Docente:"), 4, 2)
        self.combo_docente = QComboBox()
        self.combo_docente.setMinimumWidth(200)
        form_layout.addWidget(self.combo_docente, 4, 3)
        
        # Fila 6: Observaciones
        form_layout.addWidget(QLabel("Observaciones:"), 5, 0)
        self.text_observaciones = QTextEdit()
        self.text_observaciones.setMaximumHeight(60)
        form_layout.addWidget(self.text_observaciones, 5, 1, 1, 3)
        
        # Fila 7: Solo Checkbox de Revisión (eliminamos reparación)
        form_layout.addWidget(QLabel("Opciones:"), 6, 0)
        self.check_revision = QCheckBox("Es Revisión")
        opciones_layout = QHBoxLayout()
        opciones_layout.addWidget(self.check_revision)
        opciones_layout.addStretch()
        form_layout.addLayout(opciones_layout, 6, 1, 1, 3)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        
        btn_agregar = QPushButton("Agregar Nota Momento")
        btn_agregar.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_GREEN}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_agregar.clicked.connect(self.agregar_evaluacion)
        btn_layout.addWidget(btn_agregar)
        
        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_RED}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_limpiar.clicked.connect(self.limpiar_formulario_evaluacion)
        btn_layout.addWidget(btn_limpiar)
        
        btn_layout.addStretch()
        
        btn_eliminar = QPushButton("Eliminar Nota Momento")
        btn_eliminar.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_ORANGE}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_eliminar.clicked.connect(self.eliminar_evaluacion)
        btn_layout.addWidget(btn_eliminar)

        btn_actualizar = QPushButton("Actualizar Registros")
        btn_actualizar.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_BLUE}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_actualizar.clicked.connect(self.actualizar_registros)
        btn_layout.addWidget(btn_actualizar)
        
        layout.addLayout(btn_layout)
        
        # Tabla de evaluaciones - reducida a 12 columnas
        table_group = QGroupBox("Momentos Registrados")
        table_layout = QVBoxLayout()
        
        self.table_evaluaciones = QTableWidget()
        self.table_evaluaciones.setColumnCount(12)
        self.table_evaluaciones.setHorizontalHeaderLabels([
            "ID", "Cédula", "Estudiante", "Materia", "Año", "Momento", "Nota", 
            "Resultado", "Fecha", "Docente", "Revisión", "Observaciones"
        ])
        
        # Configurar tabla
        self.table_evaluaciones.setAlternatingRowColors(True)
        self.table_evaluaciones.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_evaluaciones.horizontalHeader().setStretchLastSection(True)
        self.table_evaluaciones.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Ajustar anchos de columnas
        header = self.table_evaluaciones.horizontalHeader()
        header.resizeSection(0, 50)
        header.resizeSection(1, 80)
        header.resizeSection(2, 280)
        header.resizeSection(3, 150)
        header.resizeSection(4, 120)
        header.resizeSection(5, 70)
        header.resizeSection(6, 60)
        header.resizeSection(7, 70)
        header.resizeSection(8, 90)
        header.resizeSection(9, 220)
        header.resizeSection(10, 70)

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)
        
        table_layout.addWidget(self.table_evaluaciones)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        self.tab_evaluaciones.setLayout(layout)
        
        # Cargar datos iniciales
        self.cargar_combos_evaluaciones()
        self.cargar_evaluaciones()
        
        self.combo_ano_escolar.currentIndexChanged.connect(self.cargar_estudiantes_ano)
        self.cargar_estudiantes_ano()
        self.spin_nota.valueChanged.connect(self.actualizar_resultado_automatico)
    
    def cargar_combos_evaluaciones(self):
        """Carga los datos iniciales en los comboboxes"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            # Cargar años escolares activos
            cur.execute("""
                SELECT codigo, descripcion
                FROM ano_escolar 
                WHERE activo = true
                ORDER BY descripcion DESC
            """)
            anos = cur.fetchall()

            self.combo_ano_escolar.clear()
            self.combo_ano_escolar.addItem("Seleccionar año...", None)
            ano_activo_index = 0
            for i, ano in enumerate(anos):
                self.combo_ano_escolar.addItem(ano[1], ano[0])
                if i == 0:
                    ano_activo_index = i + 1

            if anos:
                self.combo_ano_escolar.setCurrentIndex(ano_activo_index)
            
            self.combo_materia.clear()
            self.combo_materia.addItem("Seleccionar materia...", None)
            
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando datos:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_combos_resumen(self):
        """Carga los combos para el tab de resumen"""
        if not hasattr(self, 'combo_ano_resumen') or not hasattr(self, 'combo_seccion_resumen'):
            print("Error: Los widgets de combo no han sido creados aún")
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            # Cargar años escolares
            cur.execute("SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC")
            anos = cur.fetchall()
            
            self.combo_ano_resumen.clear()
            self.combo_ano_resumen.addItem("Seleccionar año...", None)
            for ano in anos:
                self.combo_ano_resumen.addItem(ano[1], ano[0])
            
            # Cargar secciones
            cur.execute("""
                SELECT s.codigo, g.nombre || ' - ' || s.letra
                FROM SECCION s
                JOIN GRADO g ON s.codigo_grado = g.codigo
                ORDER BY g.nombre, s.letra
            """)
            secciones = cur.fetchall()
            
            self.combo_seccion_resumen.clear()
            self.combo_seccion_resumen.addItem("Seleccionar sección...", None)
            for seccion in secciones:
                self.combo_seccion_resumen.addItem(seccion[1], seccion[0])
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando combos: {str(e)}")
        finally:
            conn.close()

    def cargar_secciones(self):
        """Carga las secciones según el año escolar seleccionado - CORREGIDO"""
        codigo_ano = self.combo_ano_escolar.currentData()
        if not codigo_ano:
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT s.codigo, g.nombre, s.letra
                FROM seccion s
                JOIN grado g ON s.codigo_grado = g.codigo
                WHERE s.codigo_ano_escolar = %s AND s.estado = 'A'
                ORDER BY g.numero_ano, s.letra
            """, (codigo_ano,))
            secciones = cur.fetchall()
            
            self.combo_estudiante.clear()
            self.estudiante_seleccionado = None
            self.combo_materia.clear()
            self.combo_materia.addItem("Seleccionar materia...", None)
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando secciones:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_estudiantes_seccion(self):
        """Carga los estudiantes de la sección seleccionada"""
        pass

    def cargar_materias_estudiante(self):
        """Carga las materias disponibles para el estudiante seleccionado"""
        if not self.estudiante_seleccionado:
            self.combo_materia.clear()
            self.combo_materia.addItem("Seleccionar materia...", None)
            return
        
        cedula_estudiante = self.estudiante_seleccionado[0]
        codigo_ano = self.combo_ano_escolar.currentData()
        
        if not cedula_estudiante or not codigo_ano:
            self.combo_materia.clear()
            self.combo_materia.addItem("Seleccionar materia...", None)
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT m.codigo, m.nombre
                FROM materia m
                JOIN seccion s ON m.codigo_grado = s.codigo_grado
                JOIN matricula mat ON s.codigo = mat.codigo_seccion
                WHERE mat.cedula_estudiante = %s 
                AND mat.codigo_ano_escolar = %s
                AND mat.estado_matricula = 'A'
                AND m.estado = 'A'
                ORDER BY m.nombre
            """, (cedula_estudiante, codigo_ano))
            materias = cur.fetchall()
            
            self.combo_materia.clear()
            self.combo_materia.addItem("Seleccionar materia...", None)
            for mat in materias:
                self.combo_materia.addItem(mat[1], mat[0])
            
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando materias:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_estudiantes_ano(self):
        """Carga los estudiantes del año escolar seleccionado"""
        codigo_ano = self.combo_ano_escolar.currentData()
        if not codigo_ano:
            self.estudiantes_data = []
            self.combo_estudiante.clear()
            self.cargar_evaluaciones()
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.cedula, e.nombres, e.apellidos, g.nombre, s.letra
                FROM estudiante e
                JOIN matricula m ON e.cedula = m.cedula_estudiante
                JOIN seccion s ON m.codigo_seccion = s.codigo
                JOIN grado g ON s.codigo_grado = g.codigo
                WHERE m.codigo_ano_escolar = %s 
                AND e.estado_estudiante = 'A'
                AND m.estado_matricula = 'A'
                ORDER BY e.apellidos, e.nombres
            """, (codigo_ano,))
            
            self.estudiantes_data = cur.fetchall()
            self.combo_estudiante.clear()
            self.estudiante_seleccionado = None
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando estudiantes:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def filtrar_estudiantes(self, texto):
        """Filtra estudiantes según el texto ingresado"""
        if len(texto) < 1:
            self.estudiante_completer.setModel(QStringListModel([]))
            return
        
        texto = texto.lower().strip()
        opciones = []
        
        for estudiante in self.estudiantes_data:
            cedula, nombres, apellidos, grado, seccion = estudiante
            
            nombres_lower = nombres.lower()
            apellidos_lower = apellidos.lower()
            cedula_str = str(cedula)
            nombre_completo = f"{nombres_lower} {apellidos_lower}"
            
            if (texto in cedula_str or 
                texto in nombres_lower or 
                texto in apellidos_lower or 
                texto in nombre_completo):
                
                display_text = f"{nombres} {apellidos} - {grado} {seccion} (CI: {cedula})"
                opciones.append(display_text)
        
        if opciones:
            model = QStringListModel(opciones)
            self.estudiante_completer.setModel(model)
            self.estudiante_completer.complete()
        else:
            model = QStringListModel([])
            self.estudiante_completer.setModel(model)

    def on_estudiante_selected(self, texto):
        """Maneja la selección de un estudiante"""
        try:
            if "(CI: " in texto:
                cedula = texto.split("(CI: ")[1].split(")")[0]
            else:
                return
            
            self.estudiante_seleccionado = None
            for estudiante in self.estudiantes_data:
                if str(estudiante[0]) == cedula:
                    self.estudiante_seleccionado = estudiante
                    break
            
            if self.estudiante_seleccionado:
                print(f"Estudiante seleccionado: {self.estudiante_seleccionado}")
                self.cargar_materias_estudiante()
                self.filtrar_evaluaciones_estudiante()
            else:
                print(f"No se encontró estudiante con cédula: {cedula}")
                
        except Exception as e:
            print(f"Error al seleccionar estudiante: {str(e)}")

    def validar_estudiante_manual(self):
        """Valida cuando el usuario escribe manualmente y presiona Enter o pierde el foco"""
        texto = self.combo_estudiante.text().strip()
        if not texto:
            self.cargar_evaluaciones()
            return
        
        found = False
        for estudiante in self.estudiantes_data:
            cedula, nombres, apellidos, grado, seccion = estudiante
            display_text = f"{nombres} {apellidos} - {grado} {seccion} (CI: {cedula})"
            
            if texto == display_text:
                self.estudiante_seleccionado = estudiante
                self.cargar_materias_estudiante()
                self.filtrar_evaluaciones_estudiante()
                found = True
                break
        
        if not found:
            self.estudiante_seleccionado = None
            self.combo_materia.clear()
            self.combo_materia.addItem("Seleccionar materia...", None)
            self.cargar_evaluaciones()
            QMessageBox.warning(self, "Advertencia", "Estudiante no encontrado. Seleccione uno de la lista o verifique los datos.")


    def cargar_docente_materia(self):
        """Carga los docentes asignados a la materia seleccionada - CORREGIDO"""
        codigo_materia = self.combo_materia.currentData()
        if not self.estudiante_seleccionado:
            return
        
        cedula_estudiante = self.estudiante_seleccionado[0]
        codigo_ano = self.combo_ano_escolar.currentData()
        
        if not codigo_materia or not cedula_estudiante or not codigo_ano:
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT p.cedula, p.nombres, p.apellidos
                FROM personal p
                JOIN asignacion_docente ad ON p.cedula = ad.cedula_docente
                JOIN matricula m ON ad.codigo_seccion = m.codigo_seccion
                WHERE ad.codigo_materia = %s 
                AND m.cedula_estudiante = %s
                AND m.codigo_ano_escolar = %s
                AND ad.codigo_ano_escolar = %s
                AND p.estado = 'A'
                AND m.estado_matricula = 'A'
                ORDER BY p.apellidos, p.nombres
            """, (codigo_materia, cedula_estudiante, codigo_ano, codigo_ano))
            docentes = cur.fetchall()
            
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            for doc in docentes:
                self.combo_docente.addItem(f"{doc[1]} {doc[2]} (CI: {doc[0]})", doc[0])
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando docentes:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_docentes_disponibles(self, codigo_materia):
        """Carga docentes que pueden evaluar esta materia"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT p.cedula, p.nombres, p.apellidos
                FROM personal p
                JOIN asignacion_docente ad ON p.cedula = ad.cedula_docente
                WHERE ad.codigo_materia = %s 
                AND p.estado = 'A'
                ORDER BY p.apellidos, p.nombres
            """, (codigo_materia,))
            docentes = cur.fetchall()
            
            self.combo_docente.clear()
            self.combo_docente.addItem("Seleccionar docente...", None)
            for doc in docentes:
                self.combo_docente.addItem(f"{doc[1]} {doc[2]} (CI: {doc[0]})", doc[0])
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando docentes:\n{str(e)}")
        finally:
            if conn:
                conn.close()


    def cargar_evaluaciones(self):
        """Carga las evaluaciones en la tabla"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    e.id,
                    est.cedula,
                    est.nombres || ' ' || est.apellidos as estudiante,
                    m.nombre as materia,
                    g.nombre as grado,
                    e.numero_momento,
                    e.nota,
                    e.resultado,
                    e.fecha_evaluacion,
                    p.nombres || ' ' || p.apellidos as docente,
                    CASE WHEN e.es_revision THEN 'Sí' ELSE 'No' END as revision,
                    COALESCE(e.observaciones, '') as observaciones
                FROM evaluacion e
                JOIN estudiante est ON e.cedula_estudiante = est.cedula
                JOIN materia m ON e.codigo_materia = m.codigo
                JOIN matricula mat ON est.cedula = mat.cedula_estudiante AND mat.codigo_ano_escolar = e.codigo_ano_escolar
                JOIN seccion s ON mat.codigo_seccion = s.codigo
                JOIN grado g ON s.codigo_grado = g.codigo
                LEFT JOIN personal p ON e.cedula_docente_evaluador = p.cedula
                ORDER BY e.fecha_evaluacion DESC, est.apellidos, m.nombre
                LIMIT 200
            """)
            
            evaluaciones = cur.fetchall()
            self.table_evaluaciones.setRowCount(len(evaluaciones))
            
            for row, eval_data in enumerate(evaluaciones):
                for col, data in enumerate(eval_data):
                    item = QTableWidgetItem(str(data) if data else "")
                    self.table_evaluaciones.setItem(row, col, item)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando evaluaciones: {str(e)}")
        finally:
            conn.close()

    def filtrar_evaluaciones_estudiante(self):
        """Filtra las evaluaciones para mostrar solo las del estudiante seleccionado"""
        if not self.estudiante_seleccionado:
            self.cargar_evaluaciones()
            return
        
        cedula_estudiante = self.estudiante_seleccionado[0]
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    e.id,
                    est.cedula,
                    est.nombres || ' ' || est.apellidos as estudiante,
                    m.nombre as materia,
                    g.nombre as grado,
                    e.numero_momento,
                    e.nota,
                    e.resultado,
                    e.fecha_evaluacion,
                    p.nombres || ' ' || p.apellidos as docente,
                    CASE WHEN e.es_revision THEN 'Sí' ELSE 'No' END as revision,
                    COALESCE(e.observaciones, '') as observaciones
                FROM evaluacion e
                JOIN estudiante est ON e.cedula_estudiante = est.cedula
                JOIN materia m ON e.codigo_materia = m.codigo
                JOIN matricula mat ON est.cedula = mat.cedula_estudiante AND mat.codigo_ano_escolar = e.codigo_ano_escolar
                JOIN seccion s ON mat.codigo_seccion = s.codigo
                JOIN grado g ON s.codigo_grado = g.codigo
                LEFT JOIN personal p ON e.cedula_docente_evaluador = p.cedula
                WHERE est.cedula = %s
                ORDER BY e.fecha_evaluacion DESC, m.nombre
            """, (cedula_estudiante,))
            
            evaluaciones = cur.fetchall()
            self.table_evaluaciones.setRowCount(len(evaluaciones))
            
            for row, eval_data in enumerate(evaluaciones):
                for col, data in enumerate(eval_data):
                    if data is None:
                        item = QTableWidgetItem("")
                    elif isinstance(data, date):
                        item = QTableWidgetItem(data.strftime("%d/%m/%Y"))
                    else:
                        item = QTableWidgetItem(str(data))
                    
                    # Colorear según resultado
                    if col == 7:
                        if data == 'A':
                            item.setBackground(QColor(COLOR_SUCCESS_GREEN_LIGHT))
                        elif data == 'R':
                            item.setBackground(QColor(COLOR_ERROR_RED_LIGHT))
                    
                    self.table_evaluaciones.setItem(row, col, item)
            
            print(f"Cargadas {len(evaluaciones)} evaluaciones del estudiante")
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando evaluaciones del estudiante:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def agregar_evaluacion(self):
        """Agrega una nueva evaluación a la base de datos"""
        if not all([
            self.estudiante_seleccionado,
            self.combo_materia.currentData(),
            self.combo_docente.currentData(),
            self.spin_nota.value() >= 0
        ]):
            QMessageBox.warning(self, "Error", "Complete todos los campos obligatorios")
            return
        
        cedula_estudiante = self.estudiante_seleccionado[0]
        codigo_materia = self.combo_materia.currentData()
        codigo_ano = self.combo_ano_escolar.currentData()
        numero_momento = int(self.combo_momento.currentText())
        cedula_docente = self.combo_docente.currentData()
        fecha_evaluacion = self.date_evaluacion.date().toPyDate()
        observaciones = self.text_observaciones.toPlainText()
        es_revision = self.check_revision.isChecked()
        nota = self.spin_nota.value()
        resultado = self.combo_resultado.currentText()
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            if es_revision:
                cur.execute("""
                    SELECT id, nota, resultado, fecha_evaluacion, observaciones, cedula_docente_evaluador
                    FROM evaluacion 
                    WHERE cedula_estudiante = %s AND codigo_materia = %s 
                    AND numero_momento = %s AND codigo_ano_escolar = %s
                    AND NOT es_revision
                    ORDER BY fecha_evaluacion DESC
                    LIMIT 1
                """, (cedula_estudiante, codigo_materia, numero_momento, codigo_ano))
                
                resultado_anterior = cur.fetchone()
                if not resultado_anterior:
                    QMessageBox.warning(self, "Error", "No se encontró evaluación anterior para revisar")
                    return
                
                evaluacion_id_anterior, nota_anterior, resultado_anterior_char, fecha_anterior, observaciones_anteriores, docente_anterior = resultado_anterior
                
                cur.execute("""
                    DELETE FROM evaluacion 
                    WHERE id = %s
                """, (evaluacion_id_anterior,))
                
                cur.execute("""
                    INSERT INTO evaluacion (
                        cedula_estudiante, codigo_materia, codigo_ano_escolar,
                        numero_momento, nota, resultado, fecha_evaluacion,
                        cedula_docente_evaluador, observaciones, es_revision
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (cedula_estudiante, codigo_materia, codigo_ano, numero_momento,
                    nota, resultado, fecha_evaluacion, cedula_docente, observaciones,
                    es_revision))
                
                evaluacion_id = cur.fetchone()[0]
                
                cur.execute("""
                    INSERT INTO revision_academica (
                        cedula_estudiante, codigo_materia, codigo_ano_escolar,
                        momento_revision, tipo_revision, fecha_revision,
                        nota_anterior, nota_nueva, resultado_revision,
                        cedula_docente_revisor, justificacion, estado_revision
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (cedula_estudiante, codigo_materia, codigo_ano, numero_momento,
                    'R', fecha_evaluacion, nota_anterior, nota, resultado,
                    cedula_docente, f"Revisión académica. Observaciones anteriores: {observaciones_anteriores}. Nuevas observaciones: {observaciones}", 'A'))
                
            else:
                cur.execute("""
                    SELECT id FROM evaluacion 
                    WHERE cedula_estudiante = %s AND codigo_materia = %s 
                    AND numero_momento = %s AND codigo_ano_escolar = %s
                    AND NOT es_revision
                """, (cedula_estudiante, codigo_materia, numero_momento, codigo_ano))
                
                if cur.fetchone():
                    QMessageBox.warning(self, "Error", "Ya existe evaluación para este momento")
                    return
                
                cur.execute("""
                    INSERT INTO evaluacion (
                        cedula_estudiante, codigo_materia, codigo_ano_escolar,
                        numero_momento, nota, resultado, fecha_evaluacion,
                        cedula_docente_evaluador, observaciones, es_revision
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (cedula_estudiante, codigo_materia, codigo_ano, numero_momento,
                    nota, resultado, fecha_evaluacion, cedula_docente, observaciones,
                    es_revision))
                
            conn.commit()
            QMessageBox.information(self, "Éxito", "Evaluación agregada/actualizada correctamente.")
            self.limpiar_formulario_evaluacion()
            self.filtrar_evaluaciones_estudiante()
            self.cargar_tabla_revisiones()
            self.buscar_materias_pendientes()
            
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de BD", f"Error al agregar/actualizar evaluación:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")
        finally:
            conn.close()

    def eliminar_evaluacion(self):
        """Elimina una evaluación de la base de datos"""
        selected_row = self.table_evaluaciones.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Advertencia", "Seleccione una evaluación para eliminar.")
            return

        evaluacion_id = self.table_evaluaciones.item(selected_row, 0).text()

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Está seguro de que desea eliminar la evaluación con ID {evaluacion_id}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = self.conectar_db()
            if not conn:
                return

            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM evaluacion WHERE id = %s", (evaluacion_id,))
                conn.commit()
                QMessageBox.information(self, "Éxito", "Evaluación eliminada correctamente.")
                self.filtrar_evaluaciones_estudiante()
                self.cargar_tabla_revisiones()
                self.buscar_materias_pendientes()
            except psycopg2.Error as e:
                conn.rollback()
                QMessageBox.critical(self, "Error de BD", f"Error al eliminar evaluación:\n{str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")
            finally:
                if conn:
                    conn.close()

    def limpiar_formulario_evaluacion(self):
        """Limpia todos los campos del formulario de evaluación"""
        self.combo_estudiante.clear()
        self.estudiante_seleccionado = None
        self.combo_materia.clear()
        self.combo_materia.addItem("Seleccionar materia...", None)
        self.combo_momento.setCurrentIndex(0)
        self.spin_nota.setValue(0)
        self.combo_resultado.setCurrentIndex(0)
        self.date_evaluacion.setDate(QDate.currentDate())
        self.combo_docente.clear()
        self.text_observaciones.clear()
        self.check_revision.setChecked(False)
        self.combo_estudiante.setFocus()
        self.cargar_evaluaciones()

    def actualizar_registros(self):
        """Actualiza los registros en la tabla de evaluaciones"""
        self.filtrar_evaluaciones_estudiante()
        QMessageBox.information(self, "Actualización", "Registros de evaluaciones actualizados.")

    def actualizar_resultado_automatico(self):
        """Actualiza el resultado (A/R) basado en la nota ingresada"""
        nota = self.spin_nota.value()
        if nota >= 10:
            self.combo_resultado.setCurrentText("A")
        else:
            self.combo_resultado.setCurrentText("R")

    def setup_tab_docentes(self):
        layout = QVBoxLayout()
        
        title = QLabel("Gestión de Docentes")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        form_group = QGroupBox("Datos del Docente")
        form_layout = QGridLayout()
        
        form_layout.addWidget(QLabel("Cédula:"), 0, 0)
        self.line_cedula_docente = QLineEdit()
        self.line_cedula_docente.setPlaceholderText("Cédula del docente")
        form_layout.addWidget(self.line_cedula_docente, 0, 1)
        
        form_layout.addWidget(QLabel("Nombres:"), 1, 0)
        self.line_nombres_docente = QLineEdit()
        self.line_nombres_docente.setPlaceholderText("Nombres del docente")
        form_layout.addWidget(self.line_nombres_docente, 1, 1)
        
        form_layout.addWidget(QLabel("Apellidos:"), 2, 0)
        self.line_apellidos_docente = QLineEdit()
        self.line_apellidos_docente.setPlaceholderText("Apellidos del docente")
        form_layout.addWidget(self.line_apellidos_docente, 2, 1)

        form_layout.addWidget(QLabel("Correo:"), 3, 0)
        self.line_correo_docente = QLineEdit()
        self.line_correo_docente.setPlaceholderText("Correo electrónico")
        form_layout.addWidget(self.line_correo_docente, 3, 1)
        
        form_layout.addWidget(QLabel("Teléfono:"), 4, 0)
        self.line_telefono_docente = QLineEdit()
        self.line_telefono_docente.setPlaceholderText("Número de teléfono")
        form_layout.addWidget(self.line_telefono_docente, 4, 1)

        form_layout.addWidget(QLabel("Estado:"), 5, 0)
        self.combo_estado_docente = QComboBox()
        self.combo_estado_docente.addItems(["A", "I"])
        form_layout.addWidget(self.combo_estado_docente, 5, 1)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        btn_layout_docentes = QHBoxLayout()
        
        btn_agregar_docente = QPushButton("Agregar Docente")
        btn_agregar_docente.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_GREEN}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_agregar_docente.clicked.connect(self.agregar_docente)
        btn_layout_docentes.addWidget(btn_agregar_docente)
        
        btn_editar_docente = QPushButton("Editar Docente")
        btn_editar_docente.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_BLUE}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_editar_docente.clicked.connect(self.editar_docente)
        btn_layout_docentes.addWidget(btn_editar_docente)
        
        btn_eliminar_docente = QPushButton("Eliminar Docente")
        btn_eliminar_docente.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_RED}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_eliminar_docente.clicked.connect(self.eliminar_docente)
        btn_layout_docentes.addWidget(btn_eliminar_docente) 

        btn_limpiar_docente = QPushButton("Limpiar Campos")
        btn_limpiar_docente.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_ORANGE}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_limpiar_docente.clicked.connect(self.limpiar_formulario_docente)
        btn_layout_docentes.addWidget(btn_limpiar_docente)
        
        btn_layout_docentes.addStretch()
        layout.addLayout(btn_layout_docentes)
        
        table_group_docentes = QGroupBox("Listado de Docentes")
        table_layout_docentes = QVBoxLayout()
        
        self.table_docentes = QTableWidget()
        self.table_docentes.setColumnCount(6)
        self.table_docentes.setHorizontalHeaderLabels(["Cédula", "Nombres", "Apellidos", "Correo", "Teléfono", "Estado"])
        self.table_docentes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_docentes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_docentes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_docentes.itemSelectionChanged.connect(self.cargar_docente_en_formulario)
        
        table_layout_docentes.addWidget(self.table_docentes)
        table_group_docentes.setLayout(table_layout_docentes)
        layout.addWidget(table_group_docentes)
        
        self.tab_docentes.setLayout(layout)
        
        self.cargar_docentes()

    def cargar_docentes(self):
        """Carga los docentes en la tabla de docentes"""
        conn = self.conectar_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            cur.execute("SELECT cedula, nombres, apellidos, correo, telefono, estado FROM personal WHERE tipo_personal = 'Docente' ORDER BY apellidos, nombres")
            docentes = cur.fetchall()

            self.table_docentes.setRowCount(len(docentes))
            for row, doc in enumerate(docentes):
                for col, data in enumerate(doc):
                    item = QTableWidgetItem(str(data) if data else "")
                    self.table_docentes.setItem(row, col, item)
            self.table_docentes.resizeColumnsToContents()
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de BD", f"Error al cargar docentes:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def agregar_docente(self):
        """Agrega un nuevo docente a la base de datos"""
        cedula = self.line_cedula_docente.text().strip()
        nombres = self.line_nombres_docente.text().strip()
        apellidos = self.line_apellidos_docente.text().strip()
        correo = self.line_correo_docente.text().strip()
        telefono = self.line_telefono_docente.text().strip()
        estado = self.combo_estado_docente.currentText()

        if not all([cedula, nombres, apellidos]):
            QMessageBox.warning(self, "Advertencia", "Cédula, Nombres y Apellidos son obligatorios.")
            return

        conn = self.conectar_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            cur.execute("SELECT cedula FROM personal WHERE cedula = %s AND tipo_personal = 'Docente'", (cedula,))
            if cur.fetchone():
                QMessageBox.warning(self, "Advertencia", "Ya existe un docente con esa cédula.")
                return

            cur.execute("""
                INSERT INTO personal (cedula, nombres, apellidos, correo, telefono, tipo_personal, estado)
                VALUES (%s, %s, %s, %s, %s, 'Docente', %s)
            """, (cedula, nombres, apellidos, correo, telefono, estado))
            conn.commit()
            QMessageBox.information(self, "Éxito", "Docente agregado correctamente.")
            self.limpiar_formulario_docente()
            self.cargar_docentes()
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de BD", f"Error al agregar docente:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")
        finally:
            if conn:
                conn.close()

    def editar_docente(self):
        """Edita un docente existente en la base de datos"""
        selected_row = self.table_docentes.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Advertencia", "Seleccione un docente para editar.")
            return

        cedula_original = self.table_docentes.item(selected_row, 0).text()
        
        cedula_nueva = self.line_cedula_docente.text().strip()
        nombres = self.line_nombres_docente.text().strip()
        apellidos = self.line_apellidos_docente.text().strip()
        correo = self.line_correo_docente.text().strip()
        telefono = self.line_telefono_docente.text().strip()
        estado = self.combo_estado_docente.currentText()

        if not all([cedula_nueva, nombres, apellidos]):
            QMessageBox.warning(self, "Advertencia", "Cédula, Nombres y Apellidos son obligatorios.")
            return

        conn = self.conectar_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            if cedula_nueva != cedula_original:
                cur.execute("SELECT cedula FROM personal WHERE cedula = %s AND tipo_personal = 'Docente'", (cedula_nueva,))
                if cur.fetchone():
                    QMessageBox.warning(self, "Advertencia", "La nueva cédula ya está asignada a otro docente.")
                    return

            cur.execute("""
                UPDATE personal SET 
                    cedula = %s,
                    nombres = %s,
                    apellidos = %s,
                    correo = %s,
                    telefono = %s,
                    estado = %s
                WHERE cedula = %s AND tipo_personal = 'Docente'
            """, (cedula_nueva, nombres, apellidos, correo, telefono, estado, cedula_original))
            conn.commit()
            QMessageBox.information(self, "Éxito", "Docente actualizado correctamente.")
            self.limpiar_formulario_docente()
            self.cargar_docentes()
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de BD", f"Error al actualizar docente:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")
        finally:
            if conn:
                conn.close()

    def eliminar_docente(self):
        """Elimina un docente de la base de datos"""
        selected_row = self.table_docentes.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Advertencia", "Seleccione un docente para eliminar.")
            return

        cedula_docente = self.table_docentes.item(selected_row, 0).text()

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Está seguro de que desea eliminar al docente con cédula {cedula_docente}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = self.conectar_db()
            if not conn:
                return

            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM personal WHERE cedula = %s AND tipo_personal = 'Docente'", (cedula_docente,))
                conn.commit()
                QMessageBox.information(self, "Éxito", "Docente eliminado correctamente.")
                self.limpiar_formulario_docente()
                self.cargar_docentes()
            except psycopg2.Error as e:
                conn.rollback()
                QMessageBox.critical(self, "Error de BD", f"Error al eliminar docente:\n{str(e)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")
            finally:
                if conn:
                    conn.close()

    def limpiar_formulario_docente(self):
        """Limpia los campos del formulario de docentes"""
        self.line_cedula_docente.clear()
        self.line_nombres_docente.clear()
        self.line_apellidos_docente.clear()
        self.line_correo_docente.clear()
        self.line_telefono_docente.clear()
        self.combo_estado_docente.setCurrentIndex(0)
        self.line_cedula_docente.setFocus()

    def cargar_docente_en_formulario(self):
        """Carga los datos del docente seleccionado en el formulario para edición"""
        selected_row = self.table_docentes.currentRow()
        if selected_row != -1:
            self.line_cedula_docente.setText(self.table_docentes.item(selected_row, 0).text())
            self.line_nombres_docente.setText(self.table_docentes.item(selected_row, 1).text())
            self.line_apellidos_docente.setText(self.table_docentes.item(selected_row, 2).text())
            self.line_correo_docente.setText(self.table_docentes.item(selected_row, 3).text())
            self.line_telefono_docente.setText(self.table_docentes.item(selected_row, 4).text())
            estado = self.table_docentes.item(selected_row, 5).text()
            self.combo_estado_docente.setCurrentText(estado)

    def setup_tab_resumen(self):
        layout = QVBoxLayout()
        
        title = QLabel("Resumen Final de Notas por Estudiante")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Año Escolar:"))
        self.combo_ano_resumen = QComboBox()
        self.combo_ano_resumen.setMinimumWidth(150)
        self.combo_ano_resumen.currentIndexChanged.connect(self.cargar_resumen_final)
        controls_layout.addWidget(self.combo_ano_resumen)
        
        controls_layout.addWidget(QLabel("Sección:"))
        self.combo_seccion_resumen = QComboBox()
        self.combo_seccion_resumen.setMinimumWidth(150)
        self.combo_seccion_resumen.currentIndexChanged.connect(self.cargar_resumen_final)
        controls_layout.addWidget(self.combo_seccion_resumen)
        
        momento_group = QGroupBox("Incluir Momentos:")
        momento_layout = QVBoxLayout()
        self.radio_momento1 = QRadioButton("I Momento")
        self.radio_momento12 = QRadioButton("I y II Momento")
        self.radio_momento123 = QRadioButton("I, II y III Momento")
        self.radio_final = QRadioButton("Resumen Final")

        self.radio_momento1.toggled.connect(self.cargar_resumen_final)
        self.radio_momento12.toggled.connect(self.cargar_resumen_final)
        self.radio_momento123.toggled.connect(self.cargar_resumen_final)
        self.radio_final.toggled.connect(self.cargar_resumen_final)

        momento_layout.addWidget(self.radio_momento1)
        momento_layout.addWidget(self.radio_momento12)
        momento_layout.addWidget(self.radio_momento123)
        momento_layout.addWidget(self.radio_final)
        momento_group.setLayout(momento_layout)
        controls_layout.addWidget(momento_group)
        
        btn_generar_pdf = QPushButton("Generar PDF")
        btn_generar_pdf.setStyleSheet(f"QPushButton {{ background-color: {COLOR_PDF_RED}; color: {COLOR_WHITE}; padding: 10px; font-weight: bold; border-radius: 8px; }}")
        btn_generar_pdf.clicked.connect(self.generar_pdf_resumen)
        controls_layout.addWidget(btn_generar_pdf)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        self.table_resumen = QTableWidget()
        self.table_resumen.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_resumen.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_resumen.setAlternatingRowColors(True)
        layout.addWidget(self.table_resumen)
        
        self.tab_resumen.setLayout(layout)
        
        self.cargar_combos_resumen()
        self.radio_final.setChecked(True)

    def cargar_resumen_final(self):
        """Carga el resumen final de notas en la tabla"""
        codigo_ano = self.combo_ano_resumen.currentData()
        codigo_seccion = self.combo_seccion_resumen.currentData()

        if not codigo_ano or not codigo_seccion:
            self.table_resumen.clearContents()
            self.table_resumen.setRowCount(0)
            self.datos_resumen = []
            return

        conn = self.conectar_db()
        if not conn:
            return

        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT DISTINCT m.codigo, m.nombre
                FROM MATERIA m
                JOIN SECCION s ON m.codigo_grado = s.codigo_grado
                WHERE s.codigo = %s AND s.codigo_ano_escolar = %s AND m.estado = 'A'
                ORDER BY m.nombre
            """, (codigo_seccion, codigo_ano))
            materias = cur.fetchall()

            cur.execute("""
                SELECT e.cedula, e.nombres, e.apellidos
                FROM ESTUDIANTE e
                JOIN MATRICULA mat ON e.cedula = mat.cedula_estudiante
                WHERE mat.codigo_seccion = %s AND mat.codigo_ano_escolar = %s AND e.estado_estudiante = 'A'
                ORDER BY e.apellidos, e.nombres
            """, (codigo_seccion, codigo_ano))
            estudiantes = cur.fetchall()

            momentos_a_incluir = []
            if self.radio_momento1.isChecked():
                momentos_a_incluir = [1]
            elif self.radio_momento12.isChecked():
                momentos_a_incluir = [1, 2]
            elif self.radio_momento123.isChecked():
                momentos_a_incluir = [1, 2, 3]
            elif self.radio_final.isChecked():
                momentos_a_incluir = [1, 2, 3]

            column_headers = ["N°", "Cédula", "Estudiante"]
            materia_codes = []
            for mat_codigo, mat_nombre in materias:
                column_headers.append(mat_nombre)
                materia_codes.append(mat_codigo)
            column_headers.append("Promedio General")
            column_headers.append("Estado")

            self.table_resumen.setColumnCount(len(column_headers))
            self.table_resumen.setHorizontalHeaderLabels(column_headers)
            self.table_resumen.setRowCount(len(estudiantes))
            
            self.datos_resumen = []

            for row_idx, (cedula_estudiante, nombres, apellidos) in enumerate(estudiantes):
                current_row_data = [
                    str(row_idx + 1), 
                    str(cedula_estudiante), 
                    f"{nombres} {apellidos}"
                ]
                
                total_notas = 0
                materias_contadas = 0
                materias_reprobadas = 0
                
                notas_por_materia = {}
                for mat_codigo in materia_codes:
                    notas_por_materia[mat_codigo] = {}
                    for momento in momentos_a_incluir:
                        cur.execute("""
                            SELECT nota, resultado, es_revision
                            FROM EVALUACION
                            WHERE cedula_estudiante = %s AND codigo_materia = %s
                            AND codigo_ano_escolar = %s AND numero_momento = %s
                            ORDER BY fecha_evaluacion DESC, es_revision DESC
                            LIMIT 1
                        """, (cedula_estudiante, mat_codigo, codigo_ano, momento))
                        
                        resultado_eval = cur.fetchone()
                        if resultado_eval:
                            notas_por_materia[mat_codigo][momento] = (resultado_eval[0], resultado_eval[1], resultado_eval[2])
                        else:
                            notas_por_materia[mat_codigo][momento] = (None, None, None)

                for mat_codigo in materia_codes:
                    materia_notas = []
                    for momento in momentos_a_incluir:
                        nota_info = notas_por_materia[mat_codigo].get(momento)
                        if nota_info and nota_info[0] is not None:
                            materia_notas.append(nota_info[0])
                    
                    materia_promedio = None
                    if materia_notas:
                        materia_promedio = sum(materia_notas) / len(materia_notas)
                        total_notas += materia_promedio
                        materias_contadas += 1

                    if materia_promedio is not None:
                        if self.radio_final.isChecked():
                            nombre_materia_actual = next((mn for mc, mn in materias if mc == mat_codigo), "")
                            display_nota = self.convertir_nota_a_literal(materia_promedio, nombre_materia_actual)
                            if display_nota == 'E' or (isinstance(display_nota, (float, int)) and float(display_nota) < 10):
                                materias_reprobadas += 1
                        else:
                            display_nota = f"{materia_promedio:.1f}"
                            if materia_promedio < 10:
                                materias_reprobadas += 1
                    else:
                        display_nota = ""

                    item_materia = QTableWidgetItem(display_nota)
                    
                    if (isinstance(display_nota, str) and (display_nota == 'R' or display_nota == 'E')) or \
                       (isinstance(display_nota, (float, int)) and float(display_nota) < 10):
                        item_materia.setBackground(QColor(COLOR_ERROR_RED_LIGHT))
                    
                    self.table_resumen.setItem(row_idx, column_headers.index(next(mn for mc, mn in materias if mc == mat_codigo)), item_materia)
                    current_row_data.append(display_nota)

                promedio_general = total_notas / materias_contadas if materias_contadas > 0 else 0
                estado_final = ""
                if self.radio_final.isChecked():
                    puede_promocion, mensaje_promocion = self.verificar_estudiante_puede_ser_promovido(cedula_estudiante, codigo_ano)
                    if puede_promocion:
                        estado_final = "PROMOVIDO"
                    else:
                        if "materias pendientes" in mensaje_promocion:
                            num_pendientes = int(mensaje_promocion.split("Tiene ")[1].split(" ")[0])
                            if num_pendientes <= 2:
                                estado_final = "REVISA"
                            else:
                                estado_final = "REPROBADO"
                        else:
                            estado_final = "REPROBADO"
                else:
                    if materias_reprobadas == 0 and materias_contadas > 0:
                        estado_final = "APROBADO"
                    elif materias_reprobadas > 0:
                        estado_final = "REPROBADO"
                    else:
                        estado_final = ""

                item_promedio_general = QTableWidgetItem(f"{promedio_general:.1f}" if materias_contadas > 0 else "")
                item_estado_final = QTableWidgetItem(estado_final)
                
                if estado_final == "PROMOVIDO":
                    item_estado_final.setBackground(QColor(COLOR_SUCCESS_GREEN_LIGHT))
                elif estado_final == "REVISA":
                    item_estado_final.setBackground(QColor(COLOR_WARNING_YELLOW_LIGHT))
                elif estado_final == "REPROBADO":
                    item_estado_final.setBackground(QColor(COLOR_ERROR_RED_LIGHT))

                self.table_resumen.setItem(row_idx, len(column_headers) - 2, item_promedio_general)
                self.table_resumen.setItem(row_idx, len(column_headers) - 1, item_estado_final)
                
                current_row_data.append(f"{promedio_general:.1f}" if materias_contadas > 0 else "")
                current_row_data.append(estado_final)
                self.datos_resumen.append(current_row_data)

            self.table_resumen.resizeColumnsToContents()
            self.table_resumen.horizontalHeader().setStretchLastSection(True)

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de BD", f"Error al cargar resumen final:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al procesar resumen: {str(e)}")
        finally:
            conn.close()

    def generar_pdf_resumen(self):
        """Genera un PDF con el resumen de notas actual en la tabla."""
        if not self.datos_resumen:
            QMessageBox.warning(self, "Advertencia", "No hay datos en la tabla de resumen para generar el PDF.")
            return

        ano_desc = self.combo_ano_resumen.currentText()
        seccion_desc = self.combo_seccion_resumen.currentText()
        momento_desc = ""
        if self.radio_momento1.isChecked(): momento_desc = "I Momento"
        elif self.radio_momento12.isChecked(): momento_desc = "I y II Momento"
        elif self.radio_momento123.isChecked(): momento_desc = "I, II y III Momento"
        elif self.radio_final.isChecked(): momento_desc = "Final"

        file_name = f"Resumen_Notas_{ano_desc.replace(' ', '_')}_{seccion_desc.replace(' ', '_')}_{momento_desc.replace(' ', '_')}.pdf"
        
        doc = SimpleDocTemplate(file_name, pagesize=A4,
                                rightMargin=cm, leftMargin=cm,
                                topMargin=cm, bottomMargin=cm)
        story = []
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(name='TitleStyle',
                                  parent=styles['h1'],
                                  fontSize=16,
                                  alignment=TA_CENTER,
                                  spaceAfter=6))
        styles.add(ParagraphStyle(name='SubtitleStyle',
                                  parent=styles['h2'],
                                  fontSize=12,
                                  alignment=TA_CENTER,
                                  spaceAfter=4))
        styles.add(ParagraphStyle(name='NormalCenter',
                                  parent=styles['Normal'],
                                  alignment=TA_CENTER))
        styles.add(ParagraphStyle(name='HeaderInfo',
                                  parent=styles['Normal'],
                                  fontSize=10,
                                  leading=12))

        try:
            pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'Arialbd.ttf'))
        except:
            print("Advertencia: Fuentes Arial no encontradas. Usando Helvetica.")
            pdfmetrics.registerFont(TTFont('Helvetica', 'Helvetica.ttf'))
            pdfmetrics.registerFont(TTFont('Helvetica-Bold', 'Helvetica-Bold.ttf'))

        story.append(Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", styles['NormalCenter']))
        story.append(Paragraph("MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN", styles['NormalCenter']))
        story.append(Paragraph("U.E.P. \"JOSÉ MARÍA VARGAS\"", styles['NormalCenter']))
        story.append(Paragraph(f"RESUMEN DE CALIFICACIONES - {momento_desc.upper()}", styles['TitleStyle']))
        story.append(Spacer(1, 0.5*cm))

        info_data = [
            [Paragraph(f"<b>Año Escolar:</b> {ano_desc}", styles['HeaderInfo']), 
             Paragraph(f"<b>Sección:</b> {seccion_desc}", styles['HeaderInfo'])]
        ]
        info_table = Table(info_data, colWidths=[9.5*cm, 9.5*cm])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        table_headers = [Paragraph(header, styles['Normal']) for header in self.table_resumen.horizontalHeaderLabels()]
        data_for_pdf = [table_headers] + [[Paragraph(str(cell), styles['Normal']) for cell in row] for row in self.datos_resumen]

        table = Table(data_for_pdf, colWidths=[1.5*cm, 2.5*cm, 4*cm] + [2*cm]*(len(self.table_resumen.horizontalHeaderLabels()) - 5) + [2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#A0C4FF")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Arial-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 1*cm))

        story.append(Paragraph(f"Fecha de Impresión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))

        try:
            doc.build(story)
            QMessageBox.information(self, "PDF Generado", f"Resumen de calificaciones guardado como {file_name}")
            os.startfile(file_name)
        except Exception as e:
            QMessageBox.critical(self, "Error al Generar PDF", f"Ocurrió un error al generar el PDF: {str(e)}")


    def setup_tab_boletin(self):
        layout = QVBoxLayout()
        
        title = QLabel("Generación de Boletines")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        controls_group = QGroupBox("Opciones de Boletín")
        controls_layout = QGridLayout()
        
        controls_layout.addWidget(QLabel("Año Escolar:"), 0, 0)
        self.combo_ano_boletin = QComboBox()
        self.combo_ano_boletin.setMinimumWidth(150)
        self.combo_ano_boletin.currentIndexChanged.connect(self.cargar_secciones_boletin)
        controls_layout.addWidget(self.combo_ano_boletin, 0, 1)
        
        controls_layout.addWidget(QLabel("Sección:"), 0, 2)
        self.combo_seccion_boletin = QComboBox()
        self.combo_seccion_boletin.setMinimumWidth(150)
        self.combo_seccion_boletin.currentIndexChanged.connect(self.cargar_estudiantes_boletin)
        controls_layout.addWidget(self.combo_seccion_boletin, 0, 3)

        controls_layout.addWidget(QLabel("Estudiante:"), 1, 0)
        self.combo_estudiante_boletin = QComboBox()
        self.combo_estudiante_boletin.setMinimumWidth(250)
        controls_layout.addWidget(self.combo_estudiante_boletin, 1, 1, 1, 3)

        controls_layout.addWidget(QLabel("Momento:"), 2, 0)
        self.combo_momento_boletin = QComboBox()
        self.combo_momento_boletin.addItems(["I Momento", "II Momento", "III Momento", "Final"])
        controls_layout.addWidget(self.combo_momento_boletin, 2, 1)
        
        btn_generar_boletin = QPushButton("Generar Boletín (PDF)")
        btn_generar_boletin.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_BLUE}; color: {COLOR_WHITE}; padding: 10px; font-weight: bold; border-radius: 8px; }}")
        btn_generar_boletin.clicked.connect(self.generar_boletin_pdf)
        controls_layout.addWidget(btn_generar_boletin, 3, 0, 1, 2)

        btn_generar_boletin_seccion = QPushButton("Generar Boletines por Sección")
        btn_generar_boletin_seccion.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_GREEN}; color: {COLOR_WHITE}; padding: 10px; font-weight: bold; border-radius: 8px; }}")
        btn_generar_boletin_seccion.clicked.connect(self.generar_boletines_por_seccion)
        controls_layout.addWidget(btn_generar_boletin_seccion, 3, 2, 1, 2)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        layout.addStretch()
        self.tab_boletin.setLayout(layout)

        self.cargar_combos_boletin()

    def cargar_combos_boletin(self):
        """Carga los combos iniciales para la generación de boletines"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC")
            anos = cur.fetchall()
            self.combo_ano_boletin.clear()
            self.combo_ano_boletin.addItem("Seleccionar año...", None)
            for ano in anos:
                self.combo_ano_boletin.addItem(ano[1], ano[0])
            
            self.combo_seccion_boletin.clear()
            self.combo_seccion_boletin.addItem("Seleccionar sección...", None)
            self.combo_estudiante_boletin.clear()
            self.combo_estudiante_boletin.addItem("Seleccionar estudiante...", None)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando combos de boletín:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_secciones_boletin(self):
        """Carga las secciones para el combo de boletín basado en el año escolar"""
        codigo_ano = self.combo_ano_boletin.currentData()
        self.combo_seccion_boletin.clear()
        self.combo_seccion_boletin.addItem("Seleccionar sección...", None)
        self.combo_estudiante_boletin.clear()
        self.combo_estudiante_boletin.addItem("Seleccionar estudiante...", None)
        
        if not codigo_ano:
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT s.codigo, g.nombre, s.letra
                FROM seccion s
                JOIN grado g ON s.codigo_grado = g.codigo
                WHERE s.codigo_ano_escolar = %s AND s.estado = 'A'
                ORDER BY g.numero_ano, s.letra
            """, (codigo_ano,))
            secciones = cur.fetchall()
            
            for sec in secciones:
                self.combo_seccion_boletin.addItem(f"{sec[1]} {sec[2]}", sec[0])
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando secciones para boletín:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_estudiantes_boletin(self):
        """Carga los estudiantes para el combo de boletín basado en la sección"""
        codigo_seccion = self.combo_seccion_boletin.currentData()
        self.combo_estudiante_boletin.clear()
        self.combo_estudiante_boletin.addItem("Seleccionar estudiante...", None)
        
        if not codigo_seccion:
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.cedula, e.nombres, e.apellidos
                FROM estudiante e
                JOIN matricula m ON e.cedula = m.cedula_estudiante
                WHERE m.codigo_seccion = %s 
                AND e.estado_estudiante = 'A'
                AND m.estado_matricula = 'A'
                ORDER BY e.apellidos, e.nombres
            """, (codigo_seccion,))
            estudiantes = cur.fetchall()
            
            for est in estudiantes:
                self.combo_estudiante_boletin.addItem(f"{est[1]} {est[2]} (CI: {est[0]})", est[0])
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando estudiantes para boletín:\n{str(e)}")
        finally:
            if conn:
                conn.close()
    
    def generar_boletin_pdf(self):
        """Genera un boletín individual para el estudiante seleccionado"""
        cedula_estudiante = self.combo_estudiante_boletin.currentData()
        codigo_ano = self.combo_ano_boletin.currentData()
        momento_seleccionado_texto = self.combo_momento_boletin.currentText()
        
        if not cedula_estudiante or not codigo_ano:
            QMessageBox.warning(self, "Advertencia", "Seleccione Año Escolar, Sección y Estudiante.")
            return
        
        momento_numero = None
        if "I Momento" in momento_seleccionado_texto:
            momento_numero = 1
        elif "II Momento" in momento_seleccionado_texto:
            momento_numero = 2
        elif "III Momento" in momento_seleccionado_texto:
            momento_numero = 3
        elif "Final" in momento_seleccionado_texto:
            momento_numero = 0

        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.nombres, e.apellidos, e.cedula,
                       g.nombre, s.letra, ano.descripcion
                FROM ESTUDIANTE e
                JOIN MATRICULA mat ON e.cedula = mat.cedula_estudiante
                JOIN SECCION s ON mat.codigo_seccion = s.codigo
                JOIN GRADO g ON s.codigo_grado = g.codigo
                JOIN ANO_ESCOLAR ano ON mat.codigo_ano_escolar = ano.codigo
                WHERE e.cedula = %s AND mat.codigo_ano_escolar = %s
            """, (cedula_estudiante, codigo_ano))
            estudiante_info = cur.fetchone()

            if not estudiante_info:
                QMessageBox.warning(self, "Error", "No se encontraron datos del estudiante para el año seleccionado.")
                return

            nombres_est, apellidos_est, cedula_est, grado_est, seccion_est, ano_desc = estudiante_info
            
            query_notas = """
                SELECT 
                    m.nombre as materia,
                    ev.numero_momento,
                    ev.nota,
                    ev.resultado,
                    p.nombres || ' ' || p.apellidos as docente
                FROM EVALUACION ev
                JOIN MATERIA m ON ev.codigo_materia = m.codigo
                LEFT JOIN PERSONAL p ON ev.cedula_docente_evaluador = p.cedula
                WHERE ev.cedula_estudiante = %s AND ev.codigo_ano_escolar = %s
            """
            params_notas = [cedula_estudiante, codigo_ano]

            if momento_numero != 0:
                query_notas += " AND ev.numero_momento = %s"
                params_notas.append(momento_numero)
            
            query_notas += " ORDER BY m.nombre, ev.numero_momento"
            
            cur.execute(query_notas, params_notas)
            notas = cur.fetchall()

            if not notas and momento_numero != 0:
                QMessageBox.warning(self, "Advertencia", f"No se encontraron notas para el {momento_seleccionado_texto}.")
                return
            
            file_name = f"Boletin_{apellidos_est}_{nombres_est}_{ano_desc}_{momento_seleccionado_texto.replace(' ', '_')}.pdf"
            doc = SimpleDocTemplate(file_name, pagesize=A4,
                                    rightMargin=cm, leftMargin=cm,
                                    topMargin=cm, bottomMargin=cm)
            story = []
            styles = getSampleStyleSheet()
            
            styles.add(ParagraphStyle(name='TitleStyle',
                                      parent=styles['h1'],
                                      fontSize=16,
                                      alignment=TA_CENTER,
                                      spaceAfter=6))
            styles.add(ParagraphStyle(name='SubtitleStyle',
                                      parent=styles['h2'],
                                      fontSize=12,
                                      alignment=TA_CENTER,
                                      spaceAfter=4))
            styles.add(ParagraphStyle(name='NormalCenter',
                                      parent=styles['Normal'],
                                      alignment=TA_CENTER))
            styles.add(ParagraphStyle(name='HeaderInfo',
                                      parent=styles['Normal'],
                                      fontSize=10,
                                      leading=12))

            try:
                pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'Arialbd.ttf'))
            except:
                print("Advertencia: Fuentes Arial no encontradas. Usando Helvetica.")
                pdfmetrics.registerFont(TTFont('Helvetica', 'Helvetica.ttf'))
                pdfmetrics.registerFont(TTFont('Helvetica-Bold', 'Helvetica-Bold.ttf'))

            story.append(Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", styles['NormalCenter']))
            story.append(Paragraph("MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN", styles['NormalCenter']))
            story.append(Paragraph("U.E.P. \"JOSÉ MARÍA VARGAS\"", styles['NormalCenter']))
            story.append(Paragraph("CÓDIGO DEA: S04001104", styles['NormalCenter']))
            story.append(Paragraph(f"BOLETÍN DE CALIFICACIONES - {momento_seleccionado_texto.upper()}", styles['TitleStyle']))
            story.append(Spacer(1, 0.5*cm))

            info_data = [
                [Paragraph(f"<b>Año Escolar:</b> {ano_desc}", styles['HeaderInfo']), 
                 Paragraph(f"<b>Grado/Año:</b> {grado_est} Sección: {seccion_est}", styles['HeaderInfo'])],
                [Paragraph(f"<b>Estudiante:</b> {nombres_est} {apellidos_est}", styles['HeaderInfo']), 
                 Paragraph(f"<b>Cédula de Identidad:</b> {cedula_est}", styles['HeaderInfo'])]
            ]
            info_table = Table(info_data, colWidths=[10*cm, 9*cm])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.5*cm))

            table_data = [["Materia", "Momento", "Nota", "Resultado", "Docente"]]
            
            if momento_numero == 0:
                cur.execute("""
                    SELECT DISTINCT m.codigo, m.nombre
                    FROM MATERIA m
                    JOIN SECCION s ON m.codigo_grado = s.codigo_grado
                    JOIN MATRICULA mat ON s.codigo = mat.codigo_seccion
                    WHERE mat.cedula_estudiante = %s AND mat.codigo_ano_escolar = %s AND m.estado = 'A'
                    ORDER BY m.nombre
                """, (cedula_estudiante, codigo_ano))
                materias_actuales_seccion = cur.fetchall()

                for materia_info_tuple in materias_actuales_seccion:
                    materia_nombre_actual = materia_info_tuple[1]
                    materia_codigo_actual = materia_info_tuple[0]
                    
                    cur.execute("""
                        SELECT ev.nota, ev.resultado, ev.numero_momento, ev.es_revision
                        FROM EVALUACION ev
                        WHERE ev.cedula_estudiante = %s AND ev.codigo_materia = %s
                        AND ev.codigo_ano_escolar = %s
                        ORDER BY ev.numero_momento, ev.es_revision DESC
                    """, (cedula_estudiante, materia_codigo_actual, codigo_ano))
                    
                    notas_materia = cur.fetchall()
                    
                    if notas_materia:
                        notas_momentos = {1: None, 2: None, 3: None}
                        for nota, resultado_char, momento, es_revision_flag in notas_materia:
                            if notas_momentos[momento] is None or es_revision_flag:
                                notas_momentos[momento] = (nota, resultado_char)

                        notas_validas = [n for n, _ in notas_momentos.values() if n is not None]
                        
                        if notas_validas:
                            promedio_materia = sum(notas_validas) / len(notas_validas)
                            resultado_materia = "A" if promedio_materia >= 10 else "R"
                            display_nota = self.convertir_nota_a_literal(promedio_materia, materia_nombre_actual)
                            
                            table_data.append([
                                Paragraph(materia_nombre_actual, styles['Normal']),
                                Paragraph("Final", styles['NormalCenter']),
                                Paragraph(str(display_nota), styles['NormalCenter']),
                                Paragraph(resultado_materia, styles['NormalCenter']),
                                Paragraph("", styles['Normal'])
                            ])
                        
            else:
                for materia, momento, nota, resultado_char, docente_nombre in notas:
                    display_nota = self.convertir_nota_a_literal(nota, materia)
                    table_data.append([
                        Paragraph(materia, styles['Normal']),
                        Paragraph(str(momento), styles['NormalCenter']),
                        Paragraph(str(display_nota), styles['NormalCenter']),
                        Paragraph(resultado_char, styles['NormalCenter']),
                        Paragraph(docente_nombre if docente_nombre else "", styles['Normal'])
                    ])

            if len(table_data) == 1:
                 QMessageBox.warning(self, "Advertencia", "No se encontraron notas para generar el boletín. "
                                     "Asegúrese de que el estudiante tenga evaluaciones registradas para el momento y año seleccionados.")
                 return

            table = Table(table_data, colWidths=[6*cm, 2*cm, 2*cm, 2*cm, 7*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#A0C4FF")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Arial-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('TOPPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BOX', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (1,1), (3,-1), 'CENTER'),
            ]))
            story.append(table)
            story.append(Spacer(1, 1*cm))

            if momento_numero == 0:
                promovido, mensaje_promocion = self.verificar_estudiante_puede_ser_promovido(cedula_estudiante, codigo_ano)
                observaciones_finales = f"<b>Estado Final:</b> {mensaje_promocion}"
                story.append(Paragraph(observaciones_finales, styles['Normal']))
                story.append(Spacer(1, 0.5*cm))

            firma_data = [
                [Paragraph("_____________________________", styles['NormalCenter']), Paragraph("_____________________________", styles['NormalCenter'])],
                [Paragraph("Director(a)", styles['NormalCenter']), Paragraph("Docente Guía", styles['NormalCenter'])]
            ]
            firma_table = Table(firma_data, colWidths=[8*cm, 8*cm])
            firma_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,0), 20),
            ]))
            story.append(firma_table)
            story.append(Spacer(1, 1*cm))

            story.append(Paragraph(f"Fecha de Impresión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))

            doc.build(story)
            QMessageBox.information(self, "Boletín Generado", f"Boletín de calificaciones guardado como {file_name}")
            os.startfile(file_name)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Error al generar boletín: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al generar el boletín: {str(e)}")
        finally:
            if conn:
                conn.close()

    def generar_boletines_por_seccion(self):
        """Genera boletines para todos los estudiantes de la sección y momento seleccionados."""
        codigo_seccion = self.combo_seccion_boletin.currentData()
        codigo_ano = self.combo_ano_boletin.currentData()
        momento_seleccionado_texto = self.combo_momento_boletin.currentText()

        if not codigo_seccion or not codigo_ano:
            QMessageBox.warning(self, "Advertencia", "Seleccione Año Escolar y Sección para generar boletines.")
            return

        momento_numero = None
        if "I Momento" in momento_seleccionado_texto:
            momento_numero = 1
        elif "II Momento" in momento_seleccionado_texto:
            momento_numero = 2
        elif "III Momento" in momento_seleccionado_texto:
            momento_numero = 3
        elif "Final" in momento_seleccionado_texto:
            momento_numero = 0

        conn = self.conectar_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT g.nombre, s.letra, ano.descripcion
                FROM SECCION s
                JOIN GRADO g ON s.codigo_grado = g.codigo
                JOIN ANO_ESCOLAR ano ON s.codigo_ano_escolar = ano.codigo
                WHERE s.codigo = %s AND s.codigo_ano_escolar = %s
            """, (codigo_seccion, codigo_ano))
            seccion_info = cur.fetchone()

            if not seccion_info:
                QMessageBox.warning(self, "Error", "No se encontró la información de la sección.")
                return
            
            grado_seccion, letra_seccion, ano_desc_seccion = seccion_info

            cur.execute("""
                SELECT e.cedula, e.nombres, e.apellidos
                FROM ESTUDIANTE e
                JOIN MATRICULA mat ON e.cedula = mat.cedula_estudiante
                WHERE mat.codigo_seccion = %s AND mat.codigo_ano_escolar = %s AND e.estado_estudiante = 'A'
                ORDER BY e.apellidos, e.nombres
            """, (codigo_seccion, codigo_ano))
            estudiantes_seccion = cur.fetchall()

            if not estudiantes_seccion:
                QMessageBox.warning(self, "Advertencia", "No hay estudiantes matriculados en esta sección para el año seleccionado.")
                return

            output_folder = f"Boletines_{grado_seccion}_{letra_seccion}_{ano_desc_seccion}_{momento_seleccionado_texto.replace(' ', '_')}"
            os.makedirs(output_folder, exist_ok=True)

            progress_dialog = QProgressDialog("Generando Boletines...", "Cancelar", 0, len(estudiantes_seccion), self)
            progress_dialog.setWindowTitle("Progreso de Generación")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.show()

            for i, (cedula_estudiante, nombres_est, apellidos_est) in enumerate(estudiantes_seccion):
                if progress_dialog.wasCanceled():
                    QMessageBox.information(self, "Cancelado", "Generación de boletines cancelada.")
                    break

                progress_dialog.setValue(i)
                progress_dialog.setLabelText(f"Generando boletín para {nombres_est} {apellidos_est} ({i+1}/{len(estudiantes_seccion)})")
                QApplication.processEvents()

                file_name = os.path.join(output_folder, f"Boletin_{apellidos_est}_{nombres_est}_{ano_desc_seccion}_{momento_seleccionado_texto.replace(' ', '_')}.pdf")
                doc = SimpleDocTemplate(file_name, pagesize=A4,
                                        rightMargin=cm, leftMargin=cm,
                                        topMargin=cm, bottomMargin=cm)
                story = []
                styles = getSampleStyleSheet()
                
                styles.add(ParagraphStyle(name='TitleStyle', parent=styles['h1'], fontSize=16, alignment=TA_CENTER, spaceAfter=6))
                styles.add(ParagraphStyle(name='SubtitleStyle', parent=styles['h2'], fontSize=12, alignment=TA_CENTER, spaceAfter=4))
                styles.add(ParagraphStyle(name='NormalCenter', parent=styles['Normal'], alignment=TA_CENTER))
                styles.add(ParagraphStyle(name='HeaderInfo', parent=styles['Normal'], fontSize=10, leading=12))

                try:
                    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
                    pdfmetrics.registerFont(TTFont('Arial-Bold', 'Arialbd.ttf'))
                except:
                    pass

                story.append(Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", styles['NormalCenter']))
                story.append(Paragraph("MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN", styles['NormalCenter']))
                story.append(Paragraph("U.E.P. \"JOSÉ MARÍA VARGAS\"", styles['NormalCenter']))
                story.append(Paragraph("CÓDIGO DEA: S04001104", styles['NormalCenter']))
                story.append(Paragraph(f"BOLETÍN DE CALIFICACIONES - {momento_seleccionado_texto.upper()}", styles['TitleStyle']))
                story.append(Spacer(1, 0.5*cm))

                info_data = [
                    [Paragraph(f"<b>Año Escolar:</b> {ano_desc_seccion}", styles['HeaderInfo']), 
                     Paragraph(f"<b>Grado/Año:</b> {grado_seccion} Sección: {letra_seccion}", styles['HeaderInfo'])],
                    [Paragraph(f"<b>Estudiante:</b> {nombres_est} {apellidos_est}", styles['HeaderInfo']), 
                     Paragraph(f"<b>Cédula de Identidad:</b> {cedula_estudiante}", styles['HeaderInfo'])]
                ]
                info_table = Table(info_data, colWidths=[10*cm, 9*cm])
                info_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))
                story.append(info_table)
                story.append(Spacer(1, 0.5*cm))

                table_data = [["Materia", "Momento", "Nota", "Resultado", "Docente"]]
                
                if momento_numero == 0:
                    materias_por_estudiante = {}
                    cur.execute("""
                        SELECT DISTINCT m.codigo, m.nombre
                        FROM MATERIA m
                        JOIN SECCION s ON m.codigo_grado = s.codigo_grado
                        WHERE s.codigo = %s AND s.codigo_ano_escolar = %s AND m.estado = 'A'
                        ORDER BY m.nombre
                    """, (codigo_seccion, codigo_ano))
                    materias_actuales_seccion = cur.fetchall()

                    for materia_info_tuple in materias_actuales_seccion:
                        materia_nombre_actual = materia_info_tuple[1]
                        materia_codigo_actual = materia_info_tuple[0]
                        
                        cur.execute("""
                            SELECT ev.nota, ev.resultado, ev.numero_momento, ev.es_revision
                            FROM EVALUACION ev
                            WHERE ev.cedula_estudiante = %s AND ev.codigo_materia = %s
                            AND ev.codigo_ano_escolar = %s
                            ORDER BY ev.numero_momento, ev.es_revision DESC
                        """, (cedula_estudiante, materia_codigo_actual, codigo_ano))
                        
                        notas_materia = cur.fetchall()
                        
                        if notas_materia:
                            notas_momentos = {1: None, 2: None, 3: None}
                            for nota, resultado_char, momento, es_revision_flag in notas_materia:
                                if notas_momentos[momento] is None or es_revision_flag:
                                    notas_momentos[momento] = (nota, resultado_char)

                            notas_validas = [n for n, _ in notas_momentos.values() if n is not None]
                            
                            if notas_validas:
                                promedio_materia = sum(notas_validas) / len(notas_validas)
                                resultado_materia = "A" if promedio_materia >= 10 else "R"
                                display_nota = self.convertir_nota_a_literal(promedio_materia, materia_nombre_actual)
                                
                                table_data.append([
                                    Paragraph(materia_nombre_actual, styles['Normal']),
                                    Paragraph("Final", styles['NormalCenter']),
                                    Paragraph(str(display_nota), styles['NormalCenter']),
                                    Paragraph(resultado_materia, styles['NormalCenter']),
                                    Paragraph("", styles['Normal'])
                                ])
                else:
                    cur.execute("""
                        SELECT 
                            m.nombre as materia,
                            ev.numero_momento,
                            ev.nota,
                            ev.resultado,
                            p.nombres || ' ' || p.apellidos as docente
                        FROM EVALUACION ev
                        JOIN MATERIA m ON ev.codigo_materia = m.codigo
                        LEFT JOIN PERSONAL p ON ev.cedula_docente_evaluador = p.cedula
                        WHERE ev.cedula_estudiante = %s AND ev.codigo_ano_escolar = %s
                        AND ev.numero_momento = %s
                        ORDER BY m.nombre, ev.numero_momento
                    """, (cedula_estudiante, codigo_ano, momento_numero))
                    notas = cur.fetchall()
                    
                    for materia, momento, nota, resultado_char, docente_nombre in notas:
                        display_nota = self.convertir_nota_a_literal(nota, materia)
                        table_data.append([
                            Paragraph(materia, styles['Normal']),
                            Paragraph(str(momento), styles['NormalCenter']),
                            Paragraph(str(display_nota), styles['NormalCenter']),
                            Paragraph(resultado_char, styles['NormalCenter']),
                            Paragraph(docente_nombre if docente_nombre else "", styles['Normal'])
                        ])

                if len(table_data) > 1:
                    table = Table(table_data, colWidths=[6*cm, 2*cm, 2*cm, 2*cm, 7*cm])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#A0C4FF")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('FONTNAME', (0,0), (-1,0), 'Arial-Bold'),
                        ('BOTTOMPADDING', (0,0), (-1,0), 8),
                        ('TOPPADDING', (0,0), (-1,0), 8),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                        ('BOX', (0,0), (-1,-1), 1, colors.black),
                        ('ALIGN', (1,1), (3,-1), 'CENTER'),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 1*cm))

                    if momento_numero == 0:
                        promovido, mensaje_promocion = self.verificar_estudiante_puede_ser_promovido(cedula_estudiante, codigo_ano)
                        observaciones_finales = f"<b>Estado Final:</b> {mensaje_promocion}"
                        story.append(Paragraph(observaciones_finales, styles['Normal']))
                        story.append(Spacer(1, 0.5*cm))

                    firma_data = [
                        [Paragraph("_____________________________", styles['NormalCenter']), Paragraph("_____________________________", styles['NormalCenter'])],
                        [Paragraph("Director(a)", styles['NormalCenter']), Paragraph("Docente Guía", styles['NormalCenter'])]
                    ]
                    firma_table = Table(firma_data, colWidths=[8*cm, 8*cm])
                    firma_table.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('TOPPADDING', (0,0), (-1,0), 20),
                    ]))
                    story.append(firma_table)
                    story.append(Spacer(1, 1*cm))
                    story.append(Paragraph(f"Fecha de Impresión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
                    
                    doc.build(story)
                else:
                    print(f"No se generó boletín para {nombres_est} {apellidos_est} debido a falta de notas.")
            
            progress_dialog.setValue(len(estudiantes_seccion))
            QMessageBox.information(self, "Boletines Generados", f"Boletines de la sección guardados en la carpeta: {output_folder}")
            os.startfile(output_folder)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Error al generar boletines por sección: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al generar boletines por sección: {str(e)}")
        finally:
            if conn:
                conn.close()

    def setup_tab_pendientes(self):
        """Configuración de la pestaña de materias pendientes"""
        layout = QVBoxLayout()
        
        title = QLabel("Gestión de Momentos Pendientes y Reparaciones")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        filter_group = QGroupBox("Filtrar Materias Pendientes")
        filter_layout = QGridLayout()
        
        filter_layout.addWidget(QLabel("Año Escolar:"), 0, 0)
        self.combo_ano_pendientes = QComboBox()
        self.combo_ano_pendientes.setMinimumWidth(150)
        filter_layout.addWidget(self.combo_ano_pendientes, 0, 1)
        
        filter_layout.addWidget(QLabel("Sección:"), 0, 2)
        self.combo_seccion_pendientes = QComboBox()
        self.combo_seccion_pendientes.setMinimumWidth(150)
        filter_layout.addWidget(self.combo_seccion_pendientes, 0, 3)
        
        filter_layout.addWidget(QLabel("Estudiante:"), 1, 0)
        self.combo_estudiante_pendientes = QComboBox()
        self.combo_estudiante_pendientes.setMinimumWidth(250)
        filter_layout.addWidget(self.combo_estudiante_pendientes, 1, 1, 1, 3)

        btn_buscar_pendientes = QPushButton("Buscar Momentos Pendientes")
        btn_buscar_pendientes.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_BLUE}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_buscar_pendientes.clicked.connect(self.buscar_materias_pendientes)
        filter_layout.addWidget(btn_buscar_pendientes, 2, 0, 1, 4)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        btn_layout_pendientes = QHBoxLayout()
        btn_marcar_aprobada = QPushButton("Marcar como Aprobada")
        btn_marcar_aprobada.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_GREEN}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_marcar_aprobada.clicked.connect(self.marcar_pendiente_como_aprobada)
        btn_layout_pendientes.addWidget(btn_marcar_aprobada)

        btn_eliminar_pendiente = QPushButton("Eliminar Registro Pendiente")
        btn_eliminar_pendiente.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_RED}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_eliminar_pendiente.clicked.connect(self.eliminar_registro_pendiente)
        btn_layout_pendientes.addWidget(btn_eliminar_pendiente)

        btn_layout_pendientes.addStretch()
        layout.addLayout(btn_layout_pendientes)
        
        self.table_pendientes = QTableWidget()
        self.table_pendientes.setColumnCount(6)
        self.table_pendientes.setHorizontalHeaderLabels(["Estudiante", "Materia", "Año", "Momento", "Tipo", "Estado"])
        self.table_pendientes.horizontalHeader().setStretchLastSection(True)
        self.table_pendientes.setColumnWidth(0, 200)
        self.table_pendientes.setColumnWidth(1, 150)
        self.table_pendientes.setColumnWidth(2, 100)
        self.table_pendientes.setColumnWidth(3, 100)
        self.table_pendientes.setColumnWidth(4, 150)
        self.table_pendientes.setColumnWidth(5, 100)

        self.table_pendientes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_pendientes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_pendientes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_pendientes.setAlternatingRowColors(True)
        self.table_pendientes.setSortingEnabled(True)
        self.table_pendientes.setShowGrid(True)
        layout.addWidget(self.table_pendientes)

        self.label_estadisticas_pendientes = QLabel("Total: 0 | Pendientes: 0 | Aprobadas: 0")
        self.label_estadisticas_pendientes.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.label_estadisticas_pendientes)
        
        self.tab_pendientes.setLayout(layout)

        self.combo_ano_pendientes.currentIndexChanged.connect(self.cargar_secciones_pendientes)
        self.combo_seccion_pendientes.currentIndexChanged.connect(self.cargar_estudiantes_pendientes)

        self.inicializar_combos_pendientes()

    def inicializar_combos_pendientes(self):
        """Inicializa los combos de la pestaña pendientes"""
        self.combo_ano_pendientes.clear()
        self.combo_ano_pendientes.addItem("Todos los años...", None)

        self.combo_seccion_pendientes.clear()
        self.combo_seccion_pendientes.addItem("Todas las secciones...", None)

        self.combo_estudiante_pendientes.clear()
        self.combo_estudiante_pendientes.addItem("Todos los estudiantes...", None)

        self.cargar_anos_escolares_pendientes()

    def cargar_anos_escolares_pendientes(self):
        """Carga los años escolares en el combo de pendientes"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC")
            anos = cur.fetchall()
            for codigo, descripcion in anos:
                self.combo_ano_pendientes.addItem(descripcion, codigo)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando años escolares: {str(e)}")
        finally:
            conn.close()

    def cargar_secciones_pendientes(self):
        """Carga las secciones según el año escolar seleccionado"""
        self.combo_seccion_pendientes.clear()
        self.combo_seccion_pendientes.addItem("Todas las secciones...", None)
        self.combo_estudiante_pendientes.clear()
        self.combo_estudiante_pendientes.addItem("Todos los estudiantes...", None)

        ano_codigo = self.combo_ano_pendientes.currentData()
        if not ano_codigo:
            self.cargar_todas_las_secciones()
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT s.codigo, g.nombre || ' - ' || s.letra as seccion_nombre
                FROM SECCION s
                JOIN GRADO g ON s.codigo_grado = g.codigo
                JOIN MATRICULA m ON s.codigo = m.codigo_seccion
                WHERE m.codigo_ano_escolar = %s
                ORDER BY seccion_nombre
            """, (ano_codigo,))
            secciones = cur.fetchall()
            for codigo, nombre in secciones:
                self.combo_seccion_pendientes.addItem(nombre, codigo)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando secciones: {str(e)}")
        finally:
            conn.close()

    def cargar_todas_las_secciones(self):
        """Carga todas las secciones disponibles sin filtro de año."""
        conn = self.conectar_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT s.codigo, g.nombre || ' - ' || s.letra as seccion_nombre
                FROM SECCION s
                JOIN GRADO g ON s.codigo_grado = g.codigo
                ORDER BY seccion_nombre
            """)
            secciones = cur.fetchall()
            for codigo, nombre in secciones:
                self.combo_seccion_pendientes.addItem(nombre, codigo)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando todas las secciones: {str(e)}")
        finally:
            conn.close()

    def cargar_estudiantes_pendientes(self):
        """Carga los estudiantes según la sección y año seleccionados."""
        self.combo_estudiante_pendientes.clear()
        self.combo_estudiante_pendientes.addItem("Todos los estudiantes...", None)
        
        seccion_codigo = self.combo_seccion_pendientes.currentData()
        ano_codigo = self.combo_ano_pendientes.currentData()

        if not seccion_codigo and not ano_codigo:
            self.cargar_todos_los_estudiantes()
            return
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            query = """
                SELECT DISTINCT e.cedula, e.nombres || ' ' || e.apellidos as nombre_completo
                FROM ESTUDIANTE e
                JOIN MATRICULA m ON e.cedula = m.cedula_estudiante
                WHERE e.estado_estudiante = 'A'
            """
            params = []

            if ano_codigo:
                query += " AND m.codigo_ano_escolar = %s"
                params.append(ano_codigo)
            if seccion_codigo:
                query += " AND m.codigo_seccion = %s"
                params.append(seccion_codigo)
            
            query += " ORDER BY e.apellidos, e.nombres"
            
            cur.execute(query, params)
            estudiantes = cur.fetchall()
            for cedula, nombre in estudiantes:
                self.combo_estudiante_pendientes.addItem(nombre, cedula)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando estudiantes: {str(e)}")
        finally:
            conn.close()

    def cargar_todos_los_estudiantes(self):
        """Carga todos los estudiantes sin filtrar por año o sección."""
        conn = self.conectar_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT cedula, nombres || ' ' || apellidos as nombre_completo
                FROM ESTUDIANTE
                WHERE estado_estudiante = 'A'
                ORDER BY apellidos, nombres
            """)
            estudiantes = cur.fetchall()
            for cedula, nombre in estudiantes:
                self.combo_estudiante_pendientes.addItem(nombre, cedula)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando todos los estudiantes: {str(e)}")
        finally:
            conn.close()

    def buscar_materias_pendientes(self):
        """Busca materias pendientes por año escolar, sección o estudiante
        Incluye tanto las registradas en MATERIA_PENDIENTE como las que tienen nota < 10 en EVALUACION
        """
        ano = self.combo_ano_pendientes.currentData()
        seccion = self.combo_seccion_pendientes.currentData()
        estudiante = self.combo_estudiante_pendientes.currentData()

        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            query = """
                SELECT 
                    estudiante_nombre, 
                    materia_nombre, 
                    ano_codigo, 
                    momento, 
                    tipo_pendiente, 
                    estado,
                    id_registro,
                    origen_registro
                FROM (
                    SELECT 
                        e.nombres || ' ' || e.apellidos as estudiante_nombre,
                        m.nombre as materia_nombre,
                        ano.descripcion as ano_codigo,
                        CAST(mp.momento_pendiente AS VARCHAR) as momento,
                        CASE 
                            WHEN mp.tipo_pendiente = 'R' THEN 'Reparación'
                            WHEN mp.tipo_pendiente = 'P' THEN 'Pendiente'
                            ELSE 'Otro'
                        END as tipo_pendiente,
                        CASE WHEN mp.aprobada THEN 'Aprobada' ELSE 'Pendiente' END as estado,
                        mat.codigo_seccion,
                        mp.codigo_ano_escolar,
                        mp.cedula_estudiante,
                        mp.id as id_registro,
                        'MATERIA_PENDIENTE' as origen_registro
                    FROM MATERIA_PENDIENTE mp
                    JOIN ESTUDIANTE e ON mp.cedula_estudiante = e.cedula
                    JOIN MATERIA m ON mp.codigo_materia = m.codigo
                    JOIN ANO_ESCOLAR ano ON mp.codigo_ano_escolar = ano.codigo
                    JOIN MATRICULA mat ON e.cedula = mat.cedula_estudiante AND mat.codigo_ano_escolar = mp.codigo_ano_escolar
                    
                    UNION ALL
                    
                    SELECT 
                        e.nombres || ' ' || e.apellidos as estudiante_nombre,
                        m.nombre as materia_nombre,
                        ano.descripcion as ano_codigo,
                        CAST(ev.numero_momento AS VARCHAR) as momento,
                        'Aplazado (Nota < 10)' as tipo_pendiente,
                        'Pendiente' as estado,
                        mat.codigo_seccion,
                        ev.codigo_ano_escolar,
                        ev.cedula_estudiante,
                        ev.id as id_registro,
                        'EVALUACION' as origen_registro
                    FROM EVALUACION ev
                    JOIN ESTUDIANTE e ON ev.cedula_estudiante = e.cedula
                    JOIN MATERIA m ON ev.codigo_materia = m.codigo
                    JOIN ANO_ESCOLAR ano ON ev.codigo_ano_escolar = ano.codigo
                    JOIN MATRICULA mat ON e.cedula = mat.cedula_estudiante AND mat.codigo_ano_escolar = ev.codigo_ano_escolar
                    WHERE ev.nota < 10.0 
                    AND ev.es_revision = False
                    AND NOT EXISTS (
                        SELECT 1 
                        FROM MATERIA_PENDIENTE mp2 
                        WHERE mp2.cedula_estudiante = ev.cedula_estudiante 
                        AND mp2.codigo_materia = ev.codigo_materia 
                        AND mp2.codigo_ano_escolar = ev.codigo_ano_escolar 
                        AND mp2.momento_pendiente = ev.numero_momento
                        AND mp2.aprobada = True
                    )
                ) as materias_pendientes
                WHERE 1=1
            """
            params = []

            if ano:
                query += " AND codigo_ano_escolar = %s"
                params.append(ano)
            if seccion:
                query += " AND codigo_seccion = %s"
                params.append(seccion)
            if estudiante:
                query += " AND cedula_estudiante = %s"
                params.append(estudiante)

            query += " ORDER BY estudiante_nombre, materia_nombre, momento"
            
            cur.execute(query, params)
            pendientes = cur.fetchall()

            self.table_pendientes.setRowCount(len(pendientes))
            self.table_pendientes.setSortingEnabled(False)
            
            self.table_pendientes.setColumnCount(8)
            self.table_pendientes.setHorizontalHeaderLabels(["Estudiante", "Materia", "Año", "Momento", "Tipo", "Estado", "ID", "Origen"])
            self.table_pendientes.setColumnHidden(6, True)
            self.table_pendientes.setColumnHidden(7, True)

            for row, pend in enumerate(pendientes):
                estudiante_nombre, materia_nombre, ano_codigo, momento, tipo_pendiente, estado, id_registro, origen_registro = pend
                
                visible_data = [
                    estudiante_nombre, 
                    materia_nombre, 
                    ano_codigo, 
                    f"Momento {momento}" if momento else "", 
                    tipo_pendiente, 
                    estado
                ]

                for col, data in enumerate(visible_data):
                    item = QTableWidgetItem(str(data) if data else "")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    
                    if "Aplazado" in tipo_pendiente:
                        item.setBackground(QColor(COLOR_ERROR_RED_LIGHT))
                    elif "Reparación" in tipo_pendiente:
                        item.setBackground(QColor(COLOR_WARNING_YELLOW_LIGHT))
                    elif estado == "Aprobada":
                        item.setBackground(QColor(COLOR_SUCCESS_GREEN_LIGHT))

                    if col in [2, 3, 5]:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_pendientes.setItem(row, col, item)

                self.table_pendientes.setItem(row, 6, QTableWidgetItem(str(id_registro)))
                self.table_pendientes.setItem(row, 7, QTableWidgetItem(origen_registro))

            self.table_pendientes.setSortingEnabled(True) 
            self.table_pendientes.resizeRowsToContents()
            self.table_pendientes.resizeColumnsToContents()

            total_pendientes = len(pendientes)
            aprobadas = sum(1 for p in pendientes if p[5] == "Aprobada")
            por_aprobar = total_pendientes - aprobadas
            
            self.label_estadisticas_pendientes.setText(
                f"Total: {total_pendientes} | Pendientes: {por_aprobar} | Aprobadas: {aprobadas}"
            )
            
            if por_aprobar > 0:
                self.label_estadisticas_pendientes.setStyleSheet(
                    f"font-weight: bold; padding: 5px; color: {COLOR_ACCENT_RED};"
                )
            else:
                self.label_estadisticas_pendientes.setStyleSheet(
                    f"font-weight: bold; padding: 5px; color: {COLOR_ACCENT_GREEN};"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error buscando materias pendientes: {str(e)}")
        finally:
            conn.close()

    def marcar_pendiente_como_aprobada(self):
        """Marca un registro de materia pendiente como aprobada."""
        selected_row = self.table_pendientes.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Advertencia", "Seleccione una materia pendiente de la tabla para marcarla como aprobada.")
            return

        id_registro = self.table_pendientes.item(selected_row, 6).text()
        origen_registro = self.table_pendientes.item(selected_row, 7).text()
        estado_actual = self.table_pendientes.item(selected_row, 5).text()
        
        if estado_actual == "Aprobada":
            QMessageBox.information(self, "Información", "La materia seleccionada ya está marcada como Aprobada.")
            return

        reply = QMessageBox.question(self, 'Confirmar Aprobación',
                                     "¿Está seguro de que desea marcar esta materia como Aprobada?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = self.conectar_db()
            if not conn:
                return

            try:
                cur = conn.cursor()
                if origen_registro == 'MATERIA_PENDIENTE':
                    cur.execute("UPDATE MATERIA_PENDIENTE SET aprobada = TRUE WHERE id = %s", (id_registro,))
                elif origen_registro == 'EVALUACION':
                    estudiante_nombre = self.table_pendientes.item(selected_row, 0).text()
                    materia_nombre = self.table_pendientes.item(selected_row, 1).text()
                    ano_desc = self.table_pendientes.item(selected_row, 2).text()
                    momento_str = self.table_pendientes.item(selected_row, 3).text().replace("Momento ", "")

                    cur.execute("SELECT codigo FROM MATERIA WHERE nombre = %s", (materia_nombre,))
                    codigo_materia = cur.fetchone()[0]
                    cur.execute("SELECT codigo FROM ANO_ESCOLAR WHERE descripcion = %s", (ano_desc,))
                    codigo_ano_escolar = cur.fetchone()[0]
                    cur.execute("SELECT cedula FROM ESTUDIANTE WHERE nombres || ' ' || apellidos = %s", (estudiante_nombre,))
                    cedula_estudiante = cur.fetchone()[0]
                    
                    cur.execute("""
                        SELECT id FROM MATERIA_PENDIENTE 
                        WHERE cedula_estudiante = %s AND codigo_materia = %s 
                        AND codigo_ano_escolar = %s AND momento_pendiente = %s
                    """, (cedula_estudiante, codigo_materia, codigo_ano_escolar, int(momento_str)))
                    
                    if cur.fetchone():
                        cur.execute("""
                            UPDATE MATERIA_PENDIENTE 
                            SET aprobada = TRUE 
                            WHERE cedula_estudiante = %s AND codigo_materia = %s 
                            AND codigo_ano_escolar = %s AND momento_pendiente = %s
                        """, (cedula_estudiante, codigo_materia, codigo_ano_escolar, int(momento_str)))
                    else:
                        cur.execute("""
                            INSERT INTO MATERIA_PENDIENTE (
                                cedula_estudiante, codigo_materia, codigo_ano_escolar,
                                momento_pendiente, tipo_pendiente, aprobada
                            ) VALUES (%s, %s, %s, %s, %s, TRUE)
                        """, (cedula_estudiante, codigo_materia, codigo_ano_escolar, int(momento_str), 'P'))
                        
                conn.commit()
                QMessageBox.information(self, "Éxito", "Materia marcada como Aprobada correctamente.")
                self.buscar_materias_pendientes()
                self.cargar_tabla_revisiones()
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Error", f"Error al marcar como aprobada: {str(e)}")
            finally:
                conn.close()

    def eliminar_registro_pendiente(self):
        """Elimina un registro de materia pendiente (solo los de MATERIA_PENDIENTE)."""
        selected_row = self.table_pendientes.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Advertencia", "Seleccione un registro de materia pendiente de la tabla para eliminar.")
            return

        id_registro = self.table_pendientes.item(selected_row, 6).text()
        origen_registro = self.table_pendientes.item(selected_row, 7).text()
        
        if origen_registro == 'EVALUACION':
            QMessageBox.warning(self, "Advertencia", "No se puede eliminar un registro de 'Aplazado (Nota < 10)' directamente desde aquí. Esta es una evaluación con nota reprobatoria. Debe modificar la evaluación o registrar una revisión.")
            return

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     "¿Está seguro de que desea eliminar este registro de materia pendiente?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = self.conectar_db()
            if not conn:
                return

            try:
                cur = conn.cursor()
                if origen_registro == 'MATERIA_PENDIENTE':
                    cur.execute("DELETE FROM MATERIA_PENDIENTE WHERE id = %s", (id_registro,))
                    conn.commit()
                    QMessageBox.information(self, "Éxito", "Registro de materia pendiente eliminado correctamente.")
                    self.buscar_materias_pendientes()
                    self.cargar_tabla_revisiones()
                else:
                    QMessageBox.warning(self, "Error", "Tipo de registro no eliminable directamente.")
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Error", f"Error al eliminar el registro pendiente: {str(e)}")
            finally:
                conn.close()

    def setup_tab_revision(self):
        """Configuración de la pestaña de revisión académica."""
        layout = QVBoxLayout()
        
        title = QLabel("Revisión Académica de Evaluaciones")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        form_layout = QFormLayout()

        self.combo_estudiante_revision = QLineEdit()
        self.combo_estudiante_revision.setPlaceholderText("Escriba para buscar estudiante...")
        
        self.estudiante_completer_revision = QCompleter()
        self.estudiante_completer_revision.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.estudiante_completer_revision.setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_estudiante_revision.setCompleter(self.estudiante_completer_revision)

        self.estudiante_seleccionado_revision = None
        self.estudiantes_data_revision = []

        self.combo_estudiante_revision.textChanged.connect(self.filtrar_estudiantes_revision)
        self.estudiante_completer_revision.activated.connect(self.on_estudiante_selected_revision)
        self.combo_estudiante_revision.editingFinished.connect(self.validar_estudiante_manual_revision)

        self.combo_materia_revision = QComboBox()
        self.combo_ano_revision = QComboBox()
        self.combo_momento_revision = QComboBox()
        self.combo_momento_revision.addItems(["1", "2", "3"])

        self.spin_nota_anterior = QDoubleSpinBox()
        self.spin_nota_anterior.setRange(0, 20)
        self.spin_nota_anterior.setDecimals(1)
        self.spin_nota_anterior.setReadOnly(True)
        self.spin_nota_anterior.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        self.spin_nota_nueva = QDoubleSpinBox()
        self.spin_nota_nueva.setRange(0, 20)
        self.spin_nota_nueva.setDecimals(1)
        
        self.combo_resultado_revision = QComboBox()
        self.combo_resultado_revision.addItems(["A", "R"])

        self.combo_docente_revisor = QComboBox()
        
        self.text_justificacion = QTextEdit()
        self.text_justificacion.setMaximumHeight(80)

        self.combo_materia_revision.setEnabled(True)
        self.combo_ano_revision.setEnabled(True)
        self.combo_momento_revision.setEnabled(True)
        self.combo_resultado_revision.setEnabled(True)
        self.combo_docente_revisor.setEnabled(True)


        form_layout.addRow("Estudiante:", self.combo_estudiante_revision)
        form_layout.addRow("Materia:", self.combo_materia_revision)
        form_layout.addRow("Año Escolar:", self.combo_ano_revision)
        form_layout.addRow("Momento:", self.combo_momento_revision)
        form_layout.addRow("Nota Anterior:", self.spin_nota_anterior)
        form_layout.addRow("Nota Nueva:", self.spin_nota_nueva)
        form_layout.addRow("Resultado:", self.combo_resultado_revision)
        form_layout.addRow("Docente Revisor:", self.combo_docente_revisor)
        form_layout.addRow("Justificación:", self.text_justificacion)

        btn_procesar_revision = QPushButton("Procesar Revisión")
        btn_procesar_revision.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_GREEN}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_procesar_revision.clicked.connect(self.procesar_revision)
        
        btn_actualizar_revision = QPushButton("Actualizar Lista")
        btn_actualizar_revision.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_BLUE}; color: {COLOR_WHITE}; padding: 8px; border-radius: 8px; }}")
        btn_actualizar_revision.clicked.connect(self.actualizar_datos_revision)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_procesar_revision)
        buttons_layout.addWidget(btn_actualizar_revision)
        buttons_layout.addStretch()

        layout.addLayout(form_layout)
        layout.addLayout(buttons_layout)

        self.table_revisiones = QTableWidget()
        self.table_revisiones.setColumnCount(8)
        self.table_revisiones.setHorizontalHeaderLabels([
            "ID", "Estudiante", "Materia", "Momento", 
            "Nota Anterior", "Nota Nueva", "Resultado", "Fecha"
        ])
        self.table_revisiones.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_revisiones.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_revisiones.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_revisiones.setAlternatingRowColors(True)
        self.table_revisiones.itemSelectionChanged.connect(self.cargar_revision_en_formulario)
        
        self.table_revisiones.setColumnWidth(0, 50)
        self.table_revisiones.setColumnWidth(1, 250)
        self.table_revisiones.setColumnWidth(2, 180)

        layout.addWidget(self.table_revisiones)
        self.tab_revision.setLayout(layout)

        self.combo_ano_revision.currentIndexChanged.connect(self.cargar_estudiantes_revision)
        self.combo_materia_revision.currentIndexChanged.connect(self.cargar_momentos_y_notas_revision)
        self.combo_momento_revision.currentIndexChanged.connect(self.cargar_nota_anterior_revision)
        self.spin_nota_nueva.valueChanged.connect(self.actualizar_resultado_revision_automatico)
        
        QTimer.singleShot(100, self.cargar_datos_revision)
        self.cargar_combos_revision()
        self.cargar_tabla_revisiones()

    def cargar_combos_revision(self):
        """Carga los combos iniciales para la pestaña de revisión académica."""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC")
            anos = cur.fetchall()
            self.combo_ano_revision.clear()
            self.combo_ano_revision.addItem("Seleccionar año...", None)
            for ano in anos:
                self.combo_ano_revision.addItem(ano[1], ano[0])
            
            self.combo_estudiante_revision.clear()
            self.combo_materia_revision.clear()
            self.combo_materia_revision.addItem("Seleccionar materia...", None)
            self.combo_momento_revision.setCurrentIndex(0)
            self.spin_nota_anterior.setValue(0)
            self.spin_nota_nueva.setValue(0)
            self.combo_resultado_revision.setCurrentIndex(0)
            self.combo_docente_revisor.clear()
            self.combo_docente_revisor.addItem("Seleccionar docente...", None)
            self.text_justificacion.clear()
            
            cur.execute("""
                SELECT e.cedula, e.nombres, e.apellidos, g.nombre, s.letra, a.descripcion
                FROM ESTUDIANTE e
                JOIN MATRICULA m ON e.cedula = m.cedula_estudiante
                JOIN SECCION s ON m.codigo_seccion = s.codigo
                JOIN GRADO g ON s.codigo_grado = g.codigo
                JOIN ANO_ESCOLAR a ON m.codigo_ano_escolar = a.codigo
                WHERE e.estado_estudiante = 'A'
                ORDER BY e.apellidos, e.nombres
            """)
            self.estudiantes_data_revision = cur.fetchall()
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando combos de revisión:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def filtrar_estudiantes_revision(self, texto):
        """Filtra estudiantes para el completer de la pestaña de revisión."""
        if len(texto) < 1:
            self.estudiante_completer_revision.setModel(QStringListModel([]))
            return
        
        texto = texto.lower().strip()
        opciones = []
        
        for estudiante in self.estudiantes_data_revision:
            cedula, nombres, apellidos, grado, seccion, ano = estudiante
            nombres_lower = nombres.lower()
            apellidos_lower = apellidos.lower()
            cedula_str = str(cedula)
            nombre_completo = f"{nombres_lower} {apellidos_lower}"
            
            if (texto in cedula_str or 
                texto in nombres_lower or 
                texto in apellidos_lower or 
                texto in nombre_completo):
                display_text = f"{nombres} {apellidos} - {grado} {seccion} ({ano}) (CI: {cedula})"
                opciones.append(display_text)
        
        model = QStringListModel(opciones)
        self.estudiante_completer_revision.setModel(model)
        self.estudiante_completer_revision.complete()

    def on_estudiante_selected_revision(self, texto):
        """Maneja la selección de un estudiante en la pestaña de revisión."""
        try:
            if "(CI: " in texto:
                cedula = texto.split("(CI: ")[1].split(")")[0]
            else:
                return
            
            self.estudiante_seleccionado_revision = None
            for estudiante in self.estudiantes_data_revision:
                if str(estudiante[0]) == cedula:
                    self.estudiante_seleccionado_revision = estudiante
                    break
            
            if self.estudiante_seleccionado_revision:
                print(f"Estudiante seleccionado para revisión: {self.estudiante_seleccionado_revision}")
                ano_desc_estudiante = self.estudiante_seleccionado_revision[5]
                
                index_ano = self.combo_ano_revision.findText(ano_desc_estudiante)
                if index_ano != -1:
                    self.combo_ano_revision.setCurrentIndex(index_ano)
                else:
                    QMessageBox.warning(self, "Advertencia", f"No se encontró el año escolar '{ano_desc_estudiante}' para el estudiante seleccionado.")

                self.cargar_materias_revision()
            else:
                print(f"No se encontró estudiante para revisión con cédula: {cedula}")
                
        except Exception as e:
            print(f"Error al seleccionar estudiante para revisión: {str(e)}")

    def validar_estudiante_manual_revision(self):
        """Valida cuando el usuario escribe manualmente el estudiante en la pestaña de revisión."""
        texto = self.combo_estudiante_revision.text().strip()
        if not texto:
            self.estudiante_seleccionado_revision = None
            self.combo_materia_revision.clear()
            self.combo_materia_revision.addItem("Seleccionar materia...", None)
            self.combo_momento_revision.setCurrentIndex(0)
            self.spin_nota_anterior.setValue(0)
            self.spin_nota_nueva.setValue(0)
            self.combo_resultado_revision.setCurrentIndex(0)
            self.combo_docente_revisor.clear()
            self.combo_docente_revisor.addItem("Seleccionar docente...", None)
            self.text_justificacion.clear()
            return
        
        found = False
        for estudiante in self.estudiantes_data_revision:
            cedula, nombres, apellidos, grado, seccion, ano = estudiante
            display_text = f"{nombres} {apellidos} - {grado} {seccion} ({ano}) (CI: {cedula})"
            
            if texto == display_text:
                self.estudiante_seleccionado_revision = estudiante
                ano_desc_estudiante = self.estudiante_seleccionado_revision[5]
                index_ano = self.combo_ano_revision.findText(ano_desc_estudiante)
                if index_ano != -1:
                    self.combo_ano_revision.setCurrentIndex(index_ano)
                self.cargar_materias_revision()
                found = True
                break
        
        if not found:
            self.estudiante_seleccionado_revision = None
            self.combo_materia_revision.clear()
            self.combo_materia_revision.addItem("Seleccionar materia...", None)
            self.combo_momento_revision.setCurrentIndex(0)
            self.spin_nota_anterior.setValue(0)
            self.spin_nota_nueva.setValue(0)
            self.combo_resultado_revision.setCurrentIndex(0)
            self.combo_docente_revisor.clear()
            self.combo_docente_revisor.addItem("Seleccionar docente...", None)
            self.text_justificacion.clear()
            QMessageBox.warning(self, "Advertencia", "Estudiante no encontrado. Seleccione uno de la lista o verifique los datos.")

    def cargar_estudiantes_revision(self):
        """Carga los estudiantes en el combobox de revisión basado en el año escolar seleccionado."""
        codigo_ano = self.combo_ano_revision.currentData()
        
        self.combo_estudiante_revision.clear()
        self.estudiante_seleccionado_revision = None
        self.combo_materia_revision.clear()
        self.combo_materia_revision.addItem("Seleccionar materia...", None)
        self.combo_docente_revisor.clear()
        self.combo_docente_revisor.addItem("Seleccionar docente...", None)
        self.spin_nota_anterior.setValue(0)
        self.spin_nota_nueva.setValue(0)
        self.combo_resultado_revision.setCurrentIndex(0)
        self.text_justificacion.clear()

        if not hasattr(self, '_last_ano_revision_loaded') or self._last_ano_revision_loaded != codigo_ano:
            self._last_ano_revision_loaded = codigo_ano
            conn = self.conectar_db()
            if not conn:
                return

            try:
                cur = conn.cursor()
                if codigo_ano:
                    cur.execute("""
                        SELECT e.cedula, e.nombres, e.apellidos, g.nombre, s.letra, a.descripcion
                        FROM ESTUDIANTE e
                        JOIN MATRICULA m ON e.cedula = m.cedula_estudiante
                        JOIN SECCION s ON m.codigo_seccion = s.codigo
                        JOIN GRADO g ON s.codigo_grado = g.codigo
                        JOIN ANO_ESCOLAR a ON m.codigo_ano_escolar = a.codigo
                        WHERE m.codigo_ano_escolar = %s AND e.estado_estudiante = 'A'
                        ORDER BY e.apellidos, e.nombres
                    """, (codigo_ano,))
                else:
                     cur.execute("""
                        SELECT e.cedula, e.nombres, e.apellidos, g.nombre, s.letra, a.descripcion
                        FROM ESTUDIANTE e
                        JOIN MATRICULA m ON e.cedula = m.cedula_estudiante
                        JOIN SECCION s ON m.codigo_seccion = s.codigo
                        JOIN GRADO g ON s.codigo_grado = g.codigo
                        JOIN ANO_ESCOLAR a ON m.codigo_ano_escolar = a.codigo
                        WHERE e.estado_estudiante = 'A'
                        ORDER BY e.apellidos, e.nombres
                    """)
                self.estudiantes_data_revision = cur.fetchall()
                
            except psycopg2.Error as e:
                QMessageBox.critical(self, "Error", f"Error cargando estudiantes para revisión por año:\n{str(e)}")
            finally:
                if conn:
                    conn.close()

    def cargar_materias_revision(self):
        """Carga las materias para el estudiante seleccionado en la pestaña de revisión."""
        self.combo_materia_revision.clear()
        self.combo_materia_revision.addItem("Seleccionar materia...", None)
        self.combo_docente_revisor.clear()
        self.combo_docente_revisor.addItem("Seleccionar docente...", None)
        self.spin_nota_anterior.setValue(0)
        self.spin_nota_nueva.setValue(0)
        self.combo_resultado_revision.setCurrentIndex(0)
        self.text_justificacion.clear()

        if not self.estudiante_seleccionado_revision:
            return
        
        cedula_estudiante = self.estudiante_seleccionado_revision[0]
        codigo_ano = self.combo_ano_revision.currentData()
        
        if not codigo_ano:
            QMessageBox.warning(self, "Advertencia", "Seleccione un año escolar para cargar las materias.")
            return

        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT m.codigo, m.nombre
                FROM EVALUACION ev
                JOIN MATERIA m ON ev.codigo_materia = m.codigo
                WHERE ev.cedula_estudiante = %s AND ev.codigo_ano_escolar = %s
                AND ev.es_revision = False
                ORDER BY m.nombre
            """, (cedula_estudiante, codigo_ano))
            materias = cur.fetchall()
            
            for mat in materias:
                self.combo_materia_revision.addItem(mat[1], mat[0])
                
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando materias para revisión:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_momentos_y_notas_revision(self):
        """Carga los momentos y la nota anterior para la materia seleccionada."""
        self.combo_momento_revision.clear()
        self.combo_momento_revision.addItems(["1", "2", "3"])
        self.spin_nota_anterior.setValue(0)
        self.spin_nota_nueva.setValue(0)
        self.combo_resultado_revision.setCurrentIndex(0)
        self.text_justificacion.clear()
        self.combo_docente_revisor.clear()
        self.combo_docente_revisor.addItem("Seleccionar docente...", None)

        codigo_materia = self.combo_materia_revision.currentData()
        
        if not self.estudiante_seleccionado_revision or not codigo_materia:
            return

        cedula_estudiante = self.estudiante_seleccionado_revision[0]
        codigo_ano = self.combo_ano_revision.currentData()

        if not codigo_ano:
            return

        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT numero_momento, nota, resultado, cedula_docente_evaluador
                FROM EVALUACION
                WHERE cedula_estudiante = %s AND codigo_materia = %s
                AND codigo_ano_escolar = %s AND es_revision = False
                ORDER BY numero_momento
            """, (cedula_estudiante, codigo_materia, codigo_ano))
            evaluaciones_existentes = cur.fetchall()
            
            cur.execute("""
                SELECT cedula, nombres, apellidos FROM PERSONAL 
                WHERE tipo_personal = 'Docente' AND estado = 'A'
                ORDER BY apellidos, nombres
            """)
            docentes_disponibles = cur.fetchall()
            for doc in docentes_disponibles:
                self.combo_docente_revisor.addItem(f"{doc[1]} {doc[2]} (CI: {doc[0]})", doc[0])

            if evaluaciones_existentes:
                ultimo_momento, ultima_nota, ultimo_resultado, ultimo_docente = evaluaciones_existentes[-1]
                
                index_momento = self.combo_momento_revision.findText(str(ultimo_momento))
                if index_momento != -1:
                    self.combo_momento_revision.setCurrentIndex(index_momento)
                
                self.spin_nota_anterior.setValue(ultima_nota)
                self.spin_nota_nueva.setValue(ultima_nota)
                self.combo_resultado_revision.setCurrentText(ultimo_resultado)

                if ultimo_docente:
                    index_docente = self.combo_docente_revisor.findData(ultimo_docente)
                    if index_docente != -1:
                        self.combo_docente_revisor.setCurrentIndex(index_docente)
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando momentos y notas para revisión:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_nota_anterior_revision(self):
        """Carga la nota anterior en el spinbox cuando se selecciona un momento."""
        self.spin_nota_anterior.setValue(0)
        self.spin_nota_nueva.setValue(0)
        self.combo_resultado_revision.setCurrentIndex(0)
        self.text_justificacion.clear()

        momento_text = self.combo_momento_revision.currentText()
        if not momento_text:
            return 
        try:
            numero_momento = int(momento_text)
        except ValueError:
            QMessageBox.warning(self, "Error de Selección", "El momento seleccionado no es un número válido.")
            return

        cedula_estudiante = self.estudiante_seleccionado_revision[0] if self.estudiante_seleccionado_revision else None
        codigo_materia = self.combo_materia_revision.currentData()
        codigo_ano = self.combo_ano_revision.currentData()
        

        if not all([cedula_estudiante, codigo_materia, codigo_ano, numero_momento]):
            return

        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT nota, resultado, cedula_docente_evaluador
                FROM EVALUACION
                WHERE cedula_estudiante = %s AND codigo_materia = %s
                AND codigo_ano_escolar = %s AND numero_momento = %s
                AND es_revision = False
                ORDER BY fecha_evaluacion DESC
                LIMIT 1
            """, (cedula_estudiante, codigo_materia, codigo_ano, numero_momento))
            
            resultado = cur.fetchone()
            if resultado:
                nota_anterior, res_anterior, docente_anterior = resultado
                self.spin_nota_anterior.setValue(nota_anterior)
                self.spin_nota_nueva.setValue(nota_anterior)
                self.combo_resultado_revision.setCurrentText(res_anterior)

                if docente_anterior:
                    index_docente = self.combo_docente_revisor.findData(docente_anterior)
                    if index_docente != -1:
                        self.combo_docente_revisor.setCurrentIndex(index_docente)
            else:
                QMessageBox.information(self, "Información", "No se encontró una evaluación anterior para este momento.")
                
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando nota anterior: {str(e)}")
        finally:
            if conn:
                conn.close()

    def actualizar_resultado_revision_automatico(self):
        """Actualiza el resultado (A/R) basado en la NOTA NUEVA ingresada."""
        nota = self.spin_nota_nueva.value()
        if nota >= 10:
            self.combo_resultado_revision.setCurrentText("A")
        else:
            self.combo_resultado_revision.setCurrentText("R")

    def procesar_revision(self):
        """Procesa una revisión académica"""
        if not all([
            self.estudiante_seleccionado_revision,
            self.combo_materia_revision.currentData(),
            self.combo_ano_revision.currentData(),
            self.combo_momento_revision.currentData(),
            self.spin_nota_nueva.value() >= 0,
            self.combo_docente_revisor.currentData(),
            self.text_justificacion.toPlainText().strip()
        ]):
            QMessageBox.warning(self, "Advertencia", "Complete todos los campos obligatorios para la revisión.")
            return

        if self.spin_nota_anterior.value() == 0 and self.spin_nota_nueva.value() != 0:
             reply = QMessageBox.question(self, 'Confirmar Nueva Evaluación',
                                     "No se encontró una nota anterior para este momento. ¿Desea registrar esta como una nueva evaluación de revisión?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return
        elif self.spin_nota_anterior.value() == 0 and self.spin_nota_nueva.value() == 0:
            QMessageBox.warning(self, "Advertencia", "No se puede procesar una revisión con nota 0 si no hay nota anterior. Asegúrese de que la nota anterior esté cargada o ingrese una nota nueva válida.")
            return


        conn = self.conectar_db()
        if not conn:
            return

        try:
            cur = conn.cursor()
            
            cedula_estudiante = self.estudiante_seleccionado_revision[0]
            codigo_materia = self.combo_materia_revision.currentData()
            codigo_ano_escolar = self.combo_ano_revision.currentData()
            momento_revision = int(self.combo_momento_revision.currentText())
            nota_nueva = self.spin_nota_nueva.value()
            resultado_revision = self.combo_resultado_revision.currentText()
            cedula_docente_revisor = self.combo_docente_revisor.currentData()
            justificacion = self.text_justificacion.toPlainText().strip()

            nota_anterior = self.spin_nota_anterior.value()

            cur.execute("""
                DELETE FROM EVALUACION
                WHERE cedula_estudiante = %s AND codigo_materia = %s 
                AND codigo_ano_escolar = %s AND numero_momento = %s;
            """, (cedula_estudiante, codigo_materia, codigo_ano_escolar, momento_revision))

            cur.execute("""
                INSERT INTO EVALUACION (
                    cedula_estudiante, codigo_materia, codigo_ano_escolar,
                    numero_momento, nota, resultado, fecha_evaluacion,
                    cedula_docente_evaluador, observaciones, es_revision
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (cedula_estudiante, codigo_materia, codigo_ano_escolar,
                  momento_revision, nota_nueva, resultado_revision, date.today(),
                  cedula_docente_revisor, justificacion, True))

            nueva_evaluacion_id = cur.fetchone()[0]

            cur.execute("""
                SELECT id FROM REVISION_ACADEMICA
                WHERE cedula_estudiante = %s AND codigo_materia = %s
                AND codigo_ano_escolar = %s AND momento_revision = %s
            """, (cedula_estudiante, codigo_materia, codigo_ano_escolar, momento_revision))
            
            revision_existente = cur.fetchone()

            if revision_existente:
                cur.execute("""
                    UPDATE REVISION_ACADEMICA
                    SET fecha_revision = %s, nota_anterior = %s, nota_nueva = %s,
                        resultado_revision = %s, cedula_docente_revisor = %s,
                        justificacion = %s, estado_revision = 'A'
                    WHERE id = %s;
                """, (date.today(), nota_anterior, nota_nueva, resultado_revision,
                      cedula_docente_revisor, justificacion, revision_existente[0]))
            else:
                cur.execute("""
                    INSERT INTO REVISION_ACADEMICA (
                        cedula_estudiante, codigo_materia, codigo_ano_escolar,
                        momento_revision, tipo_revision, fecha_revision,
                        nota_anterior, nota_nueva, resultado_revision,
                        cedula_docente_revisor, justificacion, estado_revision
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (cedula_estudiante, codigo_materia, codigo_ano_escolar,
                      momento_revision, 'R', date.today(),
                      nota_anterior, nota_nueva, resultado_revision,
                      cedula_docente_revisor, justificacion, 'A'))

            conn.commit()
            QMessageBox.information(self, "Éxito", "Revisión académica procesada correctamente.")
            self.limpiar_formulario_revision()
            self.cargar_tabla_revisiones()
            self.buscar_materias_pendientes()
            
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de BD", f"Error al procesar revisión:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")
        finally:
            conn.close()

    def cargar_tabla_revisiones(self):
        """Carga los datos de revisión académica en la tabla."""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    ra.id,
                    e.nombres || ' ' || e.apellidos as estudiante,
                    m.nombre as materia,
                    ra.momento_revision,
                    ra.nota_anterior,
                    ra.nota_nueva,
                    ra.resultado_revision,
                    ra.fecha_revision
                FROM REVISION_ACADEMICA ra
                JOIN ESTUDIANTE e ON ra.cedula_estudiante = e.cedula
                JOIN MATERIA m ON ra.codigo_materia = m.codigo
                ORDER BY ra.fecha_revision DESC
                LIMIT 100
            """)
            revisiones = cur.fetchall()
            
            self.table_revisiones.setRowCount(len(revisiones))
            for row, rev in enumerate(revisiones):
                for col, data in enumerate(rev):
                    item = QTableWidgetItem(str(data) if data else "")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table_revisiones.setItem(row, col, item)
            self.table_revisiones.resizeColumnsToContents()
            
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando tabla de revisiones:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def limpiar_formulario_revision(self):
        """Limpia los campos del formulario de revisión."""
        self.combo_estudiante_revision.clear()
        self.estudiante_seleccionado_revision = None
        self.combo_materia_revision.clear()
        self.combo_materia_revision.addItem("Seleccionar materia...", None)
        self.combo_ano_revision.setCurrentIndex(0)
        self.combo_momento_revision.setCurrentIndex(0)
        self.spin_nota_anterior.setValue(0)
        self.spin_nota_nueva.setValue(0)
        self.combo_resultado_revision.setCurrentIndex(0)
        self.combo_docente_revisor.clear()
        self.combo_docente_revisor.addItem("Seleccionar docente...", None)
        self.text_justificacion.clear()
        self.combo_estudiante_revision.setFocus()

    def cargar_revision_en_formulario(self):
        """Carga los datos de una revisión seleccionada en el formulario."""
        selected_row = self.table_revisiones.currentRow()
        if selected_row != -1:
            rev_id = self.table_revisiones.item(selected_row, 0).text()
            estudiante_display = self.table_revisiones.item(selected_row, 1).text()
            materia_nombre = self.table_revisiones.item(selected_row, 2).text()
            momento = self.table_revisiones.item(selected_row, 3).text()
            nota_anterior = float(self.table_revisiones.item(selected_row, 4).text())
            nota_nueva = float(self.table_revisiones.item(selected_row, 5).text())
            resultado = self.table_revisiones.item(selected_row, 6).text()
            fecha_rev = self.table_revisiones.item(selected_row, 7).text()

            conn = self.conectar_db()
            if not conn:
                return
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.cedula, e.nombres, e.apellidos, g.nombre, s.letra, a.descripcion
                    FROM REVISION_ACADEMICA ra
                    JOIN ESTUDIANTE e ON ra.cedula_estudiante = e.cedula
                    JOIN MATRICULA m ON e.cedula = m.cedula_estudiante AND m.codigo_ano_escolar = ra.codigo_ano_escolar
                    JOIN SECCION s ON m.codigo_seccion = s.codigo
                    JOIN GRADO g ON s.codigo_grado = g.codigo
                    JOIN ANO_ESCOLAR a ON m.codigo_ano_escolar = a.codigo
                    WHERE ra.id = %s
                """, (rev_id,))
                estudiante_info_db = cur.fetchone()
                if estudiante_info_db:
                    self.estudiante_seleccionado_revision = estudiante_info_db
                    full_est_display = f"{estudiante_info_db[1]} {estudiante_info_db[2]} - {estudiante_info_db[3]} {estudiante_info_db[4]} ({estudiante_info_db[5]}) (CI: {estudiante_info_db[0]})"
                    self.combo_estudiante_revision.setText(full_est_display)
                    
                    index_ano = self.combo_ano_revision.findText(estudiante_info_db[5])
                    if index_ano != -1:
                        self.combo_ano_revision.setCurrentIndex(index_ano)
                    
                    self.cargar_materias_revision()
                    index_materia = self.combo_materia_revision.findText(materia_nombre)
                    if index_materia != -1:
                        self.combo_materia_revision.setCurrentIndex(index_materia)

                self.combo_momento_revision.setCurrentText(momento)
                self.spin_nota_anterior.setValue(nota_anterior)
                self.spin_nota_nueva.setValue(nota_nueva)
                self.combo_resultado_revision.setCurrentText(resultado)
                cur.execute("""
                    SELECT justificacion, cedula_docente_revisor
                    FROM REVISION_ACADEMICA
                    WHERE id = %s
                """, (rev_id,))
                just_doc = cur.fetchone()
                if just_doc:
                    self.text_justificacion.setText(just_doc[0] if just_doc[0] else "")
                    if just_doc[1]:
                        if self.combo_docente_revisor.count() <=1:
                            cur.execute("""
                                SELECT cedula, nombres, apellidos FROM PERSONAL 
                                WHERE tipo_personal = 'Docente' AND estado = 'A'
                                ORDER BY apellidos, nombres
                            """)
                            docentes_disponibles = cur.fetchall()
                            for doc in docentes_disponibles:
                                self.combo_docente_revisor.addItem(f"{doc[1]} {doc[2]} (CI: {doc[0]})", doc[0])

                        index_docente = self.combo_docente_revisor.findData(just_doc[1])
                        if index_docente != -1:
                            self.combo_docente_revisor.setCurrentIndex(index_docente)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al cargar revisión en formulario: {str(e)}")
            finally:
                if conn:
                    conn.close()

    def actualizar_datos_revision(self):
        """Actualiza los datos mostrados en la tabla de revisiones."""
        self.cargar_tabla_revisiones()
        QMessageBox.information(self, "Actualización", "Lista de revisiones actualizada.")

    def cargar_datos_pendientes_en_revision(self):
        """Método auxiliar para recargar la tabla de pendientes en la pestaña de revisión si es necesario."""
        pass

    def setup_tab_estadisticas(self):
        """Configuración mejorada de la pestaña de estadísticas - ACTUALIZADA"""
        layout = QVBoxLayout()
        
        title = QLabel("Estadísticas Académicas Detalladas")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #1B3659;")
        layout.addWidget(title)
        
        controls_layout = QHBoxLayout()
        self.combo_ano_stats = QComboBox()
        self.combo_seccion_stats = QComboBox()
        
        controls_layout.addWidget(QLabel("Año Escolar:"))
        controls_layout.addWidget(self.combo_ano_stats)
        controls_layout.addWidget(QLabel("Sección:"))
        controls_layout.addWidget(self.combo_seccion_stats)
        
        btn_generar_stats = QPushButton("Generar Estadísticas")
        btn_generar_stats.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_BLUE}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_generar_stats.clicked.connect(self.generar_estadisticas_detalladas)
        controls_layout.addWidget(btn_generar_stats)
        
        btn_exportar_stats = QPushButton("Exportar a CSV")
        btn_exportar_stats.setStyleSheet(f"QPushButton {{ background-color: {COLOR_ACCENT_GREEN}; color: {COLOR_WHITE}; padding: 8px; font-weight: bold; border-radius: 8px; }}")
        btn_exportar_stats.clicked.connect(self.exportar_estadisticas)
        controls_layout.addWidget(btn_exportar_stats)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        self.table_estadisticas = QTableWidget()
        self.table_estadisticas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_estadisticas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_estadisticas.setAlternatingRowColors(True)
        self.table_estadisticas.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_estadisticas)
        
        self.tab_estadisticas.setLayout(layout)
        
        self.cargar_combos_estadisticas()
        
        self.combo_ano_stats.currentIndexChanged.connect(self.cargar_secciones_stats)
        self.combo_seccion_stats.currentIndexChanged.connect(self.generar_estadisticas_detalladas)

    def cargar_combos_estadisticas(self):
        """Carga los combos iniciales para la pestaña de estadísticas."""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            cur.execute("SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC")
            anos = cur.fetchall()
            self.combo_ano_stats.clear()
            self.combo_ano_stats.addItem("Todos los años...", None)
            for ano in anos:
                self.combo_ano_stats.addItem(ano[1], ano[0])
            
            self.combo_seccion_stats.clear()
            self.combo_seccion_stats.addItem("Todas las secciones...", None)
            cur.execute("""
                SELECT s.codigo, g.nombre || ' - ' || s.letra
                FROM SECCION s
                JOIN GRADO g ON s.codigo_grado = g.codigo
                ORDER BY g.nombre, s.letra
            """)
            secciones = cur.fetchall()
            for seccion in secciones:
                self.combo_seccion_stats.addItem(seccion[1], seccion[0])
                
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando combos de estadísticas:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def cargar_secciones_stats(self):
        """Carga las secciones para el combo de estadísticas basado en el año escolar."""
        codigo_ano = self.combo_ano_stats.currentData()
        self.combo_seccion_stats.clear()
        self.combo_seccion_stats.addItem("Todas las secciones...", None)
        
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            if codigo_ano:
                cur.execute("""
                    SELECT DISTINCT s.codigo, g.nombre || ' - ' || s.letra
                    FROM SECCION s
                    JOIN GRADO g ON s.codigo_grado = g.codigo
                    JOIN MATRICULA m ON s.codigo = m.codigo_seccion
                    WHERE m.codigo_ano_escolar = %s
                    ORDER BY g.nombre, s.letra
                """, (codigo_ano,))
            else:
                cur.execute("""
                    SELECT s.codigo, g.nombre || ' - ' || s.letra
                    FROM SECCION s
                    JOIN GRADO g ON s.codigo_grado = g.codigo
                    ORDER BY g.nombre, s.letra
                """)
            secciones = cur.fetchall()
            for sec in secciones:
                self.combo_seccion_stats.addItem(sec[1], sec[0])
            
            self.generar_estadisticas_detalladas()
                
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error", f"Error cargando secciones para estadísticas:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def generar_estadisticas_detalladas(self):
        """Genera estadísticas detalladas por materia."""
        ano = self.combo_ano_stats.currentData()
        seccion = self.combo_seccion_stats.currentData()
        
        conn = self.conectar_db()
        if not conn:
            return []
        
        try:
            cur = conn.cursor()
            
            query = """
                SELECT 
                    m.nombre as materia,
                    COUNT(DISTINCT e.cedula) as total_estudiantes,
                    COUNT(ev.id) as total_evaluaciones,
                    COUNT(CASE WHEN ev.resultado = 'A' THEN 1 END) as aprobados,
                    COUNT(CASE WHEN ev.resultado = 'R' THEN 1 END) as reprobados,
                    COUNT(CASE WHEN ev.resultado = 'A' AND e.genero = 'M' THEN 1 END) as aprobados_v,
                    COUNT(CASE WHEN ev.resultado = 'A' AND e.genero = 'F' THEN 1 END) as aprobados_h,
                    COUNT(CASE WHEN ev.resultado = 'R' AND e.genero = 'M' THEN 1 END) as reprobados_v,
                    COUNT(CASE WHEN ev.resultado = 'R' AND e.genero = 'F' THEN 1 END) as reprobados_h,
                    AVG(ev.nota) as promedio_materia
                FROM MATERIA m
                LEFT JOIN EVALUACION ev ON m.codigo = ev.codigo_materia
                LEFT JOIN ESTUDIANTE e ON ev.cedula_estudiante = e.cedula
                LEFT JOIN MATRICULA mat ON e.cedula = mat.cedula_estudiante
                WHERE m.estado = 'A'
            """
            
            params = []
            if ano:
                query += " AND ev.codigo_ano_escolar = %s"
                params.append(ano)
            if seccion:
                query += " AND mat.codigo_seccion = %s"
                params.append(seccion)
            
            query += " GROUP BY m.codigo, m.nombre ORDER BY m.nombre"
            
            cur.execute(query, params)
            resultados = cur.fetchall()
            
            headers = [
                "Materia", "Total Estudiantes", "Total Evaluaciones", 
                "Aprobados", "Reprobados", "Aprobados (V)", "Aprobados (H)", 
                "Reprobados (V)", "Reprobados (H)", "Promedio Materia"
            ]
            self.table_estadisticas.setColumnCount(len(headers))
            self.table_estadisticas.setHorizontalHeaderLabels(headers)
            self.table_estadisticas.setRowCount(len(resultados))
            
            for row, data in enumerate(resultados):
                for col, item_data in enumerate(data):
                    if isinstance(item_data, (float)):
                        item = QTableWidgetItem(f"{item_data:.2f}")
                    else:
                        item = QTableWidgetItem(str(item_data) if item_data is not None else "")
                    self.table_estadisticas.setItem(row, col, item)
            
            self.table_estadisticas.resizeColumnsToContents()
            
            return resultados
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error obteniendo estadísticas detalladas: {str(e)}")
            return []
        finally:
            conn.close()

    def exportar_estadisticas(self):
        """Exporta estadísticas a archivo CSV"""
        data_to_export = self.generar_estadisticas_detalladas()

        if not data_to_export:
            QMessageBox.warning(self, "Advertencia", "No hay datos para exportar.")
            return
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Exportar Estadísticas", 
                f"estadisticas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                "Archivos CSV (*.csv)"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    headers = [self.table_estadisticas.horizontalHeaderItem(i).text() 
                               for i in range(self.table_estadisticas.columnCount())]
                    writer.writerow(headers)
                    
                    for row_data_tuple in data_to_export:
                        row_data_str = [str(item) if item is not None else "" for item in row_data_tuple]
                        writer.writerow(row_data_str)
                
                QMessageBox.information(self, "Exportación Exitosa", f"Estadísticas exportadas a: {filename}")
                os.startfile(filename)
                
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"Error al exportar estadísticas: {str(e)}")

    def verificar_estudiante_puede_ser_promovido(self, cedula_estudiante, ano_escolar):
        """Verifica si un estudiante puede ser promovido basado en materias pendientes"""
        conn = self.conectar_db()
        if not conn:
            return False, "Error de conexión"
        
        try:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT COUNT(*) as total_pendientes
                FROM (
                    SELECT DISTINCT mp.codigo_materia
                    FROM MATERIA_PENDIENTE mp
                    WHERE mp.cedula_estudiante = %s 
                        AND mp.codigo_ano_escolar = %s
                        AND mp.aprobada = False
                    
                    UNION
                    
                    SELECT DISTINCT ev.codigo_materia
                    FROM EVALUACION ev
                    WHERE ev.cedula_estudiante = %s 
                        AND ev.codigo_ano_escolar = %s
                        AND ev.nota < 10.0
                        AND ev.es_revision = False
                        AND NOT EXISTS (
                            SELECT 1 FROM MATERIA_PENDIENTE mp2
                            WHERE mp2.cedula_estudiante = ev.cedula_estudiante
                            AND mp2.codigo_materia = ev.codigo_materia
                            AND mp2.codigo_ano_escolar = ev.codigo_ano_escolar
                            AND mp2.momento_pendiente = ev.numero_momento
                            AND mp2.aprobada = True
                        )
                ) as pendientes
            """, (cedula_estudiante, ano_escolar, cedula_estudiante, ano_escolar))
            
            resultado = cur.fetchone()
            total_pendientes = resultado[0] if resultado else 0
            
            if total_pendientes == 0:
                return True, "Estudiante puede ser promovido"
            elif total_pendientes <= 2:
                return True, f"Estudiante puede ser promovido con {total_pendientes} materia(s) pendiente(s)"
            else:
                return False, f"Estudiante NO puede ser promovido. Tiene {total_pendientes} materias pendientes"
            
        except Exception as e:
            return False, f"Error verificando promoción: {str(e)}"
        finally:
            conn.close()

    def cargar_datos_revision(self):
        """Carga los datos necesarios para la pestaña de revisión"""
        self.cargar_anos_escolares_revision()
        self.cargar_docentes_revision()
        self.cargar_estudiantes_data_revision()

    def cargar_anos_escolares_revision(self):
        """Carga años escolares para revisión"""
        if not hasattr(self, 'combo_ano_revision'):
            return
            
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("SELECT codigo, descripcion FROM ANO_ESCOLAR ORDER BY descripcion DESC")
            anos = cur.fetchall()
            
            self.combo_ano_revision.clear()
            self.combo_ano_revision.addItem("Seleccionar año...", None)
            
            for codigo, descripcion in anos:
                self.combo_ano_revision.addItem(descripcion, codigo)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando años escolares: {str(e)}")
        finally:
            conn.close()

    def cargar_docentes_revision(self):
        """Carga docentes para revisión - Busca 'docente' sin importar mayúsculas/minúsculas"""
        if not hasattr(self, 'combo_docente_revisor'):
            return
            
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT cedula, nombres || ' ' || apellidos as nombre_completo
                FROM PERSONAL 
                WHERE UPPER(cargo) LIKE '%DOCENTE%' AND estado = 'A'
                ORDER BY apellidos, nombres
            """)
            
            docentes = cur.fetchall()
            
            self.combo_docente_revisor.clear()
            self.combo_docente_revisor.addItem("Seleccionar docente...", None)
            
            print(f"=== DOCENTES CARGADOS PARA REVISIÓN ===")
            for cedula, nombre in docentes:
                self.combo_docente_revisor.addItem(nombre, cedula)
                print(f"Cédula: {cedula}, Nombre: {nombre}")
            
            print(f"Total docentes cargados: {len(docentes)}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando docentes: {str(e)}")
            print(f"Error detallado: {str(e)}")
        finally:
            conn.close()

    def cargar_estudiantes_data_revision(self):
        """Carga todos los datos de estudiantes para búsqueda"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.cedula, e.nombres, e.apellidos, g.nombre, s.letra, ae.descripcion
                FROM ESTUDIANTE e
                JOIN MATRICULA m ON e.cedula = m.cedula_estudiante
                JOIN SECCION s ON m.codigo_seccion = s.codigo
                JOIN GRADO g ON s.codigo_grado = g.codigo
                JOIN ANO_ESCOLAR ae ON m.codigo_ano_escolar = ae.codigo
                WHERE e.estado_estudiante = 'A'
                ORDER BY e.apellidos, e.nombres
            """)
            
            self.estudiantes_data_revision = cur.fetchall()
            print(f"Cargados {len(self.estudiantes_data_revision)} estudiantes para búsqueda")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando datos de estudiantes: {str(e)}")
            print(f"Error detallado: {str(e)}")
        finally:
            conn.close()      

    def buscar_docente_asignado(self, estudiante_cedula, materia_codigo, ano_codigo):
        """Método auxiliar para buscar el docente asignado a una materia específica"""
        conn = self.conectar_db()
        if not conn:
            return None
        
        try:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT DISTINCT e.cedula_docente_evaluador, p.nombres || ' ' || p.apellidos as nombre_completo
                FROM EVALUACION e
                JOIN PERSONAL p ON e.cedula_docente_evaluador = p.cedula
                WHERE e.cedula_estudiante = %s 
                AND e.codigo_materia = %s 
                AND e.codigo_ano_escolar = %s
                AND e.cedula_docente_evaluador IS NOT NULL
                LIMIT 1
            """, (estudiante_cedula, materia_codigo, ano_codigo))
            
            docente = cur.fetchone()
            if docente:
                print(f"Docente encontrado en EVALUACION: {docente[1]} (Cédula: {docente[0]})")
                return docente[0]
            
            cur.execute("""
                SELECT DISTINCT r.cedula_docente_revisor, p.nombres || ' ' || p.apellidos as nombre_completo
                FROM REVISION_ACADEMICA r
                JOIN PERSONAL p ON r.cedula_docente_revisor = p.cedula
                WHERE r.cedula_estudiante = %s 
                AND r.codigo_materia = %s 
                AND r.codigo_ano_escolar = %s
                AND r.cedula_docente_revisor IS NOT NULL
                LIMIT 1
            """, (estudiante_cedula, materia_codigo, ano_codigo))
            
            docente = cur.fetchone()
            if docente:
                print(f"Docente encontrado en REVISION_ACADEMICA: {docente[1]} (Cédula: {docente[0]})")
                return docente[0]
            
            cur.execute("""
                SELECT DISTINCT ad.cedula_docente, p.nombres || ' ' || p.apellidos as nombre_completo
                FROM ASIGNACION_DOCENTE ad
                JOIN PERSONAL p ON ad.cedula_docente = p.cedula
                JOIN MATRICULA m ON ad.codigo_seccion = m.codigo_seccion
                WHERE m.cedula_estudiante = %s 
                AND ad.codigo_materia = %s 
                AND ad.codigo_ano_escolar = %s
                AND m.codigo_ano_escolar = %s
                LIMIT 1
            """, (estudiante_cedula, materia_codigo, ano_codigo, ano_codigo))
            
            docente = cur.fetchone()
            if docente:
                print(f"Docente encontrado en ASIGNACION_DOCENTE: {docente[1]} (Cédula: {docente[0]})")
                return docente[0]
            
            cur.execute("""
                SELECT DISTINCT s.cedula_docente_guia, p.nombres || ' ' || p.apellidos as nombre_completo
                FROM SECCION s
                JOIN PERSONAL p ON s.cedula_docente_guia = p.cedula
                JOIN MATRICULA m ON s.codigo = m.codigo_seccion
                WHERE m.cedula_estudiante = %s 
                AND m.codigo_ano_escolar = %s
                AND s.cedula_docente_guia IS NOT NULL
                LIMIT 1
            """, (estudiante_cedula, ano_codigo))
            
            docente = cur.fetchone()
            if docente:
                print(f"Docente guía encontrado: {docente[1]} (Cédula: {docente[0]})")
                return docente[0]
            
            print("No se encontró docente asignado en ninguna tabla")
            return None
            
        except Exception as e:
            print(f"Error buscando docente asignado: {str(e)}")
            return None
        finally:
            conn.close()

    def cargar_tabla_revisiones(self):
        """Carga la tabla de revisiones existentes"""
        conn = self.conectar_db()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT r.id, e.nombres || ' ' || e.apellidos, m.nombre, r.momento_revision,
                    r.nota_anterior, r.nota_nueva, r.resultado_revision, r.fecha_revision
                FROM REVISION_ACADEMICA r
                JOIN ESTUDIANTE e ON r.cedula_estudiante = e.cedula
                JOIN MATERIA m ON r.codigo_materia = m.codigo
                ORDER BY r.fecha_revision DESC
                LIMIT 50
            """)
            
            revisiones = cur.fetchall()
            self.table_revisiones.setRowCount(len(revisiones))
            
            for row, revision in enumerate(revisiones):
                for col, data in enumerate(revision):
                    self.table_revisiones.setItem(row, col, QTableWidgetItem(str(data)))
                    
        except Exception as e:
            print(f"Error cargando tabla de revisiones: {str(e)}")
        finally:
            conn.close()

