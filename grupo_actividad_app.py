import sys
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor # Importar RealDictCursor para obtener resultados como diccionarios
from datetime import date
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QCheckBox,
    QMessageBox, QDateEdit, QTabWidget, QGroupBox, QFormLayout, QHeaderView
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal # Importar pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QIntValidator # Importar QIntValidator

# --- Clase DBManager (Reutilizada de momento_evaluativo_app.py) ---
class DBManager:
    """Clase para manejar la conexión y operaciones con la base de datos PostgreSQL."""
    def __init__(self, db_config): # Aceptar un diccionario db_config
        self.db_config = db_config
        self.conn = None
        self.connect() # Intentar conectar al inicio

    def connect(self):
        """Establece una conexión a la base de datos PostgreSQL."""
        db_to_connect = self.db_config.get('database')
        try:
            self.conn = psycopg2.connect(**self.db_config) # Usar la configuración principal
            self.conn.autocommit = True # Auto-commit para DDL y DML simples
            print(f"Conexión a la base de datos '{db_to_connect}' exitosa.")
            return True
        except Error as e:
            print(f"Error al conectar a la base de datos '{db_to_connect}': {e}")
            self.conn = None
            return False

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Ejecuta una consulta SQL y maneja la conexión/errores."""
        if not self.conn or self.conn.closed:
            print("No hay conexión activa a la base de datos. Intentando reconectar...")
            if not self.connect():
                QMessageBox.critical(None, "Error de Conexión",
                                     "No se pudo conectar a la base de datos. Verifique la configuración o que el servidor esté activo.")
                return None

        try:
            # Usar RealDictCursor para SELECTs para obtener resultados como diccionarios
            if query.strip().upper().startswith("SELECT"):
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    if fetch_one:
                        return cur.fetchone()
                    return cur.fetchall()
            else: # Para INSERT, UPDATE, DELETE, DDL
                with self.conn.cursor() as cur:
                    cur.execute(query, params)
                    # Para INSERT con RETURNING ID
                    if "RETURNING id" in query.lower():
                        return cur.fetchone()[0] # Asume que el ID es el primer (y único) valor retornado
                    return True
        except Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            QMessageBox.critical(None, "Error en la Base de Datos",
                                 f"Ocurrió un error al ejecutar la operación en la base de datos:\n{e}\nPor favor, contacte a soporte.")
            if self.conn: # Intentar rollback si hay un error en DML
                self.conn.rollback()
            return None

# --- Clase GrupoActividadModel ---
class GrupoActividadModel:
    def __init__(self, db_manager):
        self.db = db_manager

    # --- Operaciones para GRUPO_ACTIVIDAD ---

    def create_grupo_actividad(self, nombre_grupo, tipo_actividad, descripcion,
                                 cedula_coordinador, codigo_ano_escolar, cupos_disponibles, activo=True):
        query = """
        INSERT INTO grupo_actividad (nombre_grupo, tipo_actividad, descripcion,
                                     cedula_coordinador, codigo_ano_escolar, cupos_disponibles, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        params = (nombre_grupo, tipo_actividad, descripcion,
                  cedula_coordinador, codigo_ano_escolar, cupos_disponibles, activo)
        result = self.db.execute_query(query, params, fetch_one=True) # fetch_one=True para RETURNING id
        if result:
            print(f"Grupo de Actividad '{nombre_grupo}' creado con ID: {result['id']}")
            return result['id'] # Acceder por clave de diccionario
        return None

    def get_all_grupos_actividad(self):
        query = "SELECT * FROM grupo_actividad ORDER BY nombre_grupo;"
        return self.db.execute_query(query, fetch_all=True) # Retorna lista de diccionarios

    def get_grupo_actividad_by_id(self, grupo_id):
        query = "SELECT * FROM grupo_actividad WHERE id = %s;"
        return self.db.execute_query(query, (grupo_id,), fetch_one=True) # Retorna diccionario

    def update_grupo_actividad(self, grupo_id, nombre_grupo, tipo_actividad, descripcion,
                                 cedula_coordinador, codigo_ano_escolar, cupos_disponibles, activo):
        query = """
        UPDATE grupo_actividad
        SET nombre_grupo = %s, tipo_actividad = %s, descripcion = %s,
            cedula_coordinador = %s, codigo_ano_escolar = %s,
            cupos_disponibles = %s, activo = %s
        WHERE id = %s;
        """
        params = (nombre_grupo, tipo_actividad, descripcion,
                  cedula_coordinador, codigo_ano_escolar,
                  cupos_disponibles, activo, grupo_id)
        return self.db.execute_query(query, params)

    def delete_grupo_actividad(self, grupo_id):
        # Primero eliminar participaciones relacionadas para evitar errores de FK
        # Asegúrate de que delete_participacion_by_grupo maneja correctamente los errores
        success_delete_participations = self.delete_participacion_by_grupo(grupo_id) # Esta llamada debe manejar su propio éxito/fracaso
        if success_delete_participations is False: # Si hubo un error al eliminar participaciones, no continuar
            print(f"Error al eliminar participaciones para el grupo {grupo_id}. No se eliminará el grupo.")
            return False

        query = "DELETE FROM grupo_actividad WHERE id = %s;"
        return self.db.execute_query(query, (grupo_id,))

    # --- Operaciones para PARTICIPACION_GRUPO ---

    def create_participacion_grupo(self, cedula_estudiante, id_grupo, fecha_inscripcion,
                                     nivel_participacion, observaciones, activo=True):
        query = """
        INSERT INTO participacion_grupo (cedula_estudiante, id_grupo, fecha_inscripcion,
                                         nivel_participacion, observaciones, activo)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """
        params = (cedula_estudiante, id_grupo, fecha_inscripcion,
                  nivel_participacion, observaciones, activo)
        result = self.db.execute_query(query, params, fetch_one=True) # fetch_one=True para RETURNING id
        if result:
            print(f"Participación registrada con ID: {result['id']}")
            return result['id'] # Acceder por clave de diccionario
        return None

    def get_participaciones_by_grupo(self, grupo_id):
        query = """
        SELECT pg.*, e.nombres AS nombre_estudiante, e.apellidos AS apellido_estudiante
        FROM participacion_grupo pg
        JOIN estudiante e ON pg.cedula_estudiante = e.cedula
        WHERE pg.id_grupo = %s ORDER BY e.nombres;
        """
        return self.db.execute_query(query, (grupo_id,), fetch_all=True) # Retorna lista de diccionarios

    def get_participacion_by_id(self, participacion_id):
        query = "SELECT * FROM participacion_grupo WHERE id = %s;"
        return self.db.execute_query(query, (participacion_id,), fetch_one=True) # Retorna diccionario

    def update_participacion_grupo(self, participacion_id, cedula_estudiante, id_grupo,
                                     fecha_inscripcion, nivel_participacion, observaciones, activo):
        query = """
        UPDATE participacion_grupo
        SET cedula_estudiante = %s, id_grupo = %s, fecha_inscripcion = %s,
            nivel_participacion = %s, observaciones = %s, activo = %s
        WHERE id = %s;
        """
        params = (cedula_estudiante, id_grupo, fecha_inscripcion,
                  nivel_participacion, observaciones, activo, participacion_id)
        return self.db.execute_query(query, params)

    def delete_participacion_grupo(self, participacion_id):
        query = "DELETE FROM participacion_grupo WHERE id = %s;"
        return self.db.execute_query(query, (participacion_id,))

    def delete_participacion_by_grupo(self, grupo_id):
        query = "DELETE FROM participacion_grupo WHERE id_grupo = %s;"
        return self.db.execute_query(query, (grupo_id,))

    # Funciones para obtener datos de FK para los ComboBox
    def get_personal_list(self):
        query = "SELECT cedula, nombres, apellidos FROM personal ORDER BY nombres;"
        return self.db.execute_query(query, fetch_all=True) # Retorna lista de diccionarios

    def get_ano_escolar_list(self):
        query = "SELECT codigo FROM ano_escolar ORDER BY codigo DESC;"
        return self.db.execute_query(query, fetch_all=True) # Retorna lista de diccionarios

    def get_estudiante_list(self):
        query = "SELECT cedula, nombres, apellidos FROM estudiante ORDER BY nombres;"
        return self.db.execute_query(query, fetch_all=True) # Retorna lista de diccionarios

# --- Clase GrupoActividadUI ---
class GrupoActividadUI(QWidget):
    closed = pyqtSignal() # Señal para indicar que el módulo se cerró

    def __init__(self, db_config, user_data): # Aceptar db_config y user_data
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db_manager = DBManager(self.db_config) # Instanciar DBManager
        if not self.db_manager.conn:
            QMessageBox.critical(self, "Error de Conexión", "No se pudo conectar a la base de datos. Verifique los parámetros.")
            sys.exit(1) # Salir si no hay conexión

        self.model = GrupoActividadModel(self.db_manager) # Pasar la instancia de DBManager al modelo

        self.setWindowTitle("SIGME - Módulo de Grupo de Actividad")
        self.setGeometry(100, 100, 1000, 700) # Ajustar tamaño inicial

        self.apply_palette()
        self.init_ui()

        # --- Bloquear señales durante la carga inicial de datos ---
        self.filter_grupo_combo.blockSignals(True)
        self.id_grupo_participacion_combo.blockSignals(True)

        # Cargar los combos
        self.load_personal_to_combo()
        self.load_ano_escolar_to_combo()
        self.load_estudiante_to_combo()
        self.populate_grupo_combos() # Llenar el combo de grupos en la pestaña de participación y filtro

        # --- Re-habilitar señales después de la carga inicial ---
        self.filter_grupo_combo.blockSignals(False)
        self.id_grupo_participacion_combo.blockSignals(False)

        # Cargar la tabla de grupos y limpiar formularios
        self.load_grupos_actividad()
        self.clear_grupo_fields()
        self.clear_participacion_fields()

        # Cargar las participaciones para el grupo inicialmente seleccionado (o el placeholder)
        # Se pasa show_message=False para evitar el QMessageBox en la carga inicial
        self.load_participaciones_by_grupo(show_message=False)


    def apply_palette(self):
        palette = QPalette()
        # Colores principales de la paleta #b3cbdc #1c355b #e4eaf4 #7089a7
        # Fondo general: #e4eaf4 (claro)
        # Elementos principales (botones, headers): #7089a7 (azul medio)
        # Texto: #1c355b (azul oscuro)
        # Controles, input fields: #b3cbdc (azul claro grisáceo)

        palette.setColor(QPalette.ColorRole.Window, QColor("#e4eaf4"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1c355b"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#b3cbdc")) # Color de fondo de los inputs
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#d0dbe9")) # Para filas alternas en tablas
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#e4eaf4"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1c355b"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1c355b"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#7089a7"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("red"))
        palette.setColor(QPalette.ColorRole.Link, QColor("#1c355b"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#7089a7")) # Selección
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))

        self.setPalette(palette)
        # Aplicar estilos a elementos específicos para asegurar la consistencia
        self.setStyleSheet("""
            QWidget {
                font-family: Arial;
                font-size: 14px;
            }
            QLabel {
                color: #1c355b;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                background-color: #b3cbdc;
                border: 1px solid #7089a7;
                padding: 5px;
                border-radius: 3px;
                color: #1c355b;
            }
            QPushButton {
                background-color: #7089a7;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a7491; /* Un poco más oscuro al pasar el ratón */
            }
            QTableWidget {
                background-color: #e4eaf4;
                alternate-background-color: #d0dbe9;
                selection-background-color: #7089a7;
                selection-color: white;
                border: 1px solid #7089a7;
            }
            QHeaderView::section {
                background-color: #7089a7;
                color: white;
                padding: 5px;
                border: 1px solid #5a7491;
            }
            QTableWidget QHeaderView::section:horizontal {
                border-bottom: 2px solid #5a7491;
            }
            QTabWidget::pane { /* The tab widget frame */
                border: 1px solid #7089a7;
                background-color: #e4eaf4;
            }
            QTabWidget::tab-bar {
                left: 5px; /* move to the right by 5px */
            }
            QTabBar::tab {
                background: #b3cbdc;
                border: 1px solid #7089a7;
                border-bottom-color: #7089a7; /* same as pane color */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 120px;
                padding: 8px;
                color: #1c355b;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #7089a7;
                color: white;
            }
            QTabBar::tab:selected {
                border-color: #7089a7;
                border-bottom-color: #e4eaf4; /* make the selected tab look like it's part of the pane */
            }
            QGroupBox {
                border: 1px solid #7089a7;
                border-radius: 5px;
                margin-top: 2ex; /* leave space for title */
                font-weight: bold;
                color: #1c355b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; /* position at the top left */
                padding: 0 3px;
                background-color: #e4eaf4;
            }
            /* Estilo específico para el botón de volver */
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

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Botón para volver al menú principal
        self.back_to_menu_button = QPushButton("Volver al Menú Principal")
        self.back_to_menu_button.setObjectName("backButton") # Para aplicar estilos específicos
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        main_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.tab_widget = QTabWidget()
        self.tab_grupo = QWidget()
        self.tab_participacion = QWidget()

        self.tab_widget.addTab(self.tab_grupo, "Gestión de Grupos de Actividad")
        self.tab_widget.addTab(self.tab_participacion, "Gestión de Participaciones")

        self.setup_grupo_tab()
        self.setup_participacion_tab()

        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)


    def setup_grupo_tab(self):
        layout = QVBoxLayout(self.tab_grupo)

        # Formulario de entrada para Grupo_Actividad
        input_group = QGroupBox("Datos del Grupo de Actividad")
        form_layout = QFormLayout()

        self.grupo_id_label = QLabel("ID:")
        self.grupo_id_display = QLineEdit()
        self.grupo_id_display.setReadOnly(True)
        self.grupo_id_display.setText("Automático")
        form_layout.addRow(self.grupo_id_label, self.grupo_id_display)

        self.nombre_grupo_input = QLineEdit()
        self.nombre_grupo_input.setPlaceholderText("Ej: Dibujo")
        form_layout.addRow("Nombre Grupo:", self.nombre_grupo_input)

        self.tipo_actividad_input = QLineEdit()
        self.tipo_actividad_input.setPlaceholderText("Ej: Artística")
        form_layout.addRow("Tipo Actividad:", self.tipo_actividad_input)

        self.descripcion_input = QLineEdit() # Podría ser QTextEdit para descripciones largas
        self.descripcion_input.setPlaceholderText("A qué se dedica el grupo")
        form_layout.addRow("Descripción:", self.descripcion_input)

        self.cedula_coordinador_combo = QComboBox()
        form_layout.addRow("Cédula Coordinador:", self.cedula_coordinador_combo)

        self.codigo_ano_escolar_combo = QComboBox()
        form_layout.addRow("Código Año Escolar:", self.codigo_ano_escolar_combo)

        self.cupos_disponibles_input = QLineEdit()
        self.cupos_disponibles_input.setPlaceholderText("Límite de participantes")
        self.cupos_disponibles_input.setValidator(QIntValidator(0, 999999)) # Solo números, ajuste el rango según necesidad
        form_layout.addRow("Cupos Disponibles:", self.cupos_disponibles_input)

        self.activo_checkbox = QCheckBox("Activo")
        self.activo_checkbox.setChecked(True)
        form_layout.addRow("Estado:", self.activo_checkbox)

        input_group.setLayout(form_layout)
        layout.addWidget(input_group)

        # Botones de acción para Grupo_Actividad
        button_layout = QHBoxLayout()
        self.add_grupo_btn = QPushButton("Agregar Grupo")
        self.add_grupo_btn.clicked.connect(self.add_grupo)
        self.update_grupo_btn = QPushButton("Actualizar Grupo")
        self.update_grupo_btn.clicked.connect(self.update_grupo)
        self.update_grupo_btn.setEnabled(False) # Deshabilitado hasta seleccionar
        self.delete_grupo_btn = QPushButton("Eliminar Grupo")
        self.delete_grupo_btn.clicked.connect(self.delete_grupo)
        self.delete_grupo_btn.setEnabled(False) # Deshabilitado hasta seleccionar
        self.clear_grupo_btn = QPushButton("Limpiar Campos")
        self.clear_grupo_btn.clicked.connect(self.clear_grupo_fields)

        button_layout.addWidget(self.add_grupo_btn)
        button_layout.addWidget(self.update_grupo_btn)
        button_layout.addWidget(self.delete_grupo_btn)
        button_layout.addWidget(self.clear_grupo_btn)
        layout.addLayout(button_layout)

        # Tabla de Grupos de Actividad
        self.grupo_table = QTableWidget()
        self.grupo_table.setColumnCount(8)
        self.grupo_table.setHorizontalHeaderLabels([
            "ID", "Nombre Grupo", "Tipo Actividad", "Descripción",
            "Cédula Coordinador", "Código Año Escolar", "Cupos", "Activo"
        ])
        self.grupo_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.grupo_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.grupo_table.itemSelectionChanged.connect(self.load_grupo_to_form)
        layout.addWidget(self.grupo_table)

    def setup_participacion_tab(self):
        layout = QVBoxLayout(self.tab_participacion)

        # Selector de grupo para filtrar participaciones
        filter_group_box = QGroupBox("Filtrar Participaciones por Grupo")
        filter_layout = QHBoxLayout()
        self.filter_grupo_combo = QComboBox()
        self.filter_grupo_combo.addItem("Seleccione un Grupo para ver Participaciones", -1) # Default
        # Conectar la señal usando un lambda para pasar el argumento show_message=True
        self.filter_grupo_combo.currentIndexChanged.connect(lambda index: self.load_participaciones_by_grupo(show_message=True))
        filter_layout.addWidget(QLabel("Seleccionar Grupo:"))
        filter_layout.addWidget(self.filter_grupo_combo)
        filter_group_box.setLayout(filter_layout)
        layout.addWidget(filter_group_box)

        # Formulario de entrada para Participacion_Grupo
        input_group = QGroupBox("Datos de la Participación")
        form_layout = QFormLayout()

        self.participacion_id_label = QLabel("ID:")
        self.participacion_id_display = QLineEdit()
        self.participacion_id_display.setReadOnly(True)
        self.participacion_id_display.setText("Automático")
        form_layout.addRow(self.participacion_id_label, self.participacion_id_display)

        self.cedula_estudiante_combo = QComboBox()
        form_layout.addRow("Cédula Estudiante:", self.cedula_estudiante_combo)

        self.id_grupo_participacion_combo = QComboBox()
        form_layout.addRow("Grupo de Actividad:", self.id_grupo_participacion_combo)

        self.fecha_inscripcion_input = QDateEdit(QDate.currentDate())
        self.fecha_inscripcion_input.setCalendarPopup(True)
        form_layout.addRow("Fecha de Inscripción:", self.fecha_inscripcion_input)

        self.nivel_participacion_input = QLineEdit()
        self.nivel_participacion_input.setPlaceholderText("Ej: Delantero, Vocalista")
        form_layout.addRow("Nivel Participación:", self.nivel_participacion_input)

        self.observaciones_participacion_input = QLineEdit()
        self.observaciones_participacion_input.setPlaceholderText("Observaciones adicionales")
        form_layout.addRow("Observaciones:", self.observaciones_participacion_input)

        self.activo_participacion_checkbox = QCheckBox("Activo")
        self.activo_participacion_checkbox.setChecked(True)
        form_layout.addRow("Estado:", self.activo_participacion_checkbox)

        input_group.setLayout(form_layout)
        layout.addWidget(input_group)


        # Botones de acción para Participacion_Grupo
        button_layout = QHBoxLayout()
        self.add_participacion_btn = QPushButton("Agregar Participación")
        self.add_participacion_btn.clicked.connect(self.add_participacion)
        self.update_participacion_btn = QPushButton("Actualizar Participación")
        self.update_participacion_btn.clicked.connect(self.update_participacion)
        self.update_participacion_btn.setEnabled(False)
        self.delete_participacion_btn = QPushButton("Eliminar Participación")
        self.delete_participacion_btn.clicked.connect(self.delete_participacion)
        self.delete_participacion_btn.setEnabled(False)
        self.clear_participacion_btn = QPushButton("Limpiar Campos")
        self.clear_participacion_btn.clicked.connect(self.clear_participacion_fields)

        button_layout.addWidget(self.add_participacion_btn)
        button_layout.addWidget(self.update_participacion_btn)
        button_layout.addWidget(self.delete_participacion_btn)
        button_layout.addWidget(self.clear_participacion_btn)
        layout.addLayout(button_layout)

        # Tabla de Participaciones
        self.participacion_table = QTableWidget()
        self.participacion_table.setColumnCount(8) # Actualizado a 8 columnas para incluir Nombre Estudiante
        self.participacion_table.setHorizontalHeaderLabels([
            "ID", "Cédula Estudiante", "Nombre Estudiante", "Grupo ID", "Fecha Insc.", "Nivel Part.", "Observaciones", "Activo"
        ])
        self.participacion_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.participacion_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.participacion_table.itemSelectionChanged.connect(self.load_participacion_to_form)
        layout.addWidget(self.participacion_table)

    def load_personal_to_combo(self):
        self.cedula_coordinador_combo.clear()
        self.cedula_coordinador_combo.addItem("Seleccione un Coordinador", None)
        personal_list = self.model.get_personal_list()
        if personal_list:
            for p in personal_list: # p es un diccionario
                self.cedula_coordinador_combo.addItem(f"{p['cedula']} - {p['nombres']} {p['apellidos']}", p['cedula'])

    def load_ano_escolar_to_combo(self):
        self.codigo_ano_escolar_combo.clear()
        self.codigo_ano_escolar_combo.addItem("Seleccione un Año Escolar", None)
        ano_escolar_list = self.model.get_ano_escolar_list()
        if ano_escolar_list:
            for a in ano_escolar_list: # a es un diccionario
                self.codigo_ano_escolar_combo.addItem(a['codigo'], a['codigo'])

    def load_estudiante_to_combo(self):
        self.cedula_estudiante_combo.clear()
        self.cedula_estudiante_combo.addItem("Seleccione un Estudiante", None)
        estudiante_list = self.model.get_estudiante_list()
        if estudiante_list:
            for e in estudiante_list: # e es un diccionario
                self.cedula_estudiante_combo.addItem(f"{e['cedula']} - {e['nombres']} {e['apellidos']}", e['cedula'])

    def populate_grupo_combos(self):
        # Para el filtro de grupos en la pestaña de participación y para el combo de selección de grupo en participación
        # Las señales ya están bloqueadas en __init__ para esta llamada inicial.
        self.filter_grupo_combo.clear()
        self.filter_grupo_combo.addItem("Seleccione un Grupo para ver Participaciones", -1)
        self.id_grupo_participacion_combo.clear()
        self.id_grupo_participacion_combo.addItem("Seleccione un Grupo", None)

        grupos = self.model.get_all_grupos_actividad()
        if grupos:
            for grupo in grupos: # grupo es un diccionario
                self.filter_grupo_combo.addItem(f"{grupo['nombre_grupo']} (ID: {grupo['id']})", grupo['id'])
                self.id_grupo_participacion_combo.addItem(f"{grupo['nombre_grupo']} (ID: {grupo['id']})", grupo['id'])


    # --- Métodos para GRUPO_ACTIVIDAD ---

    def load_grupos_actividad(self):
        self.grupo_table.setRowCount(0)
        grupos = self.model.get_all_grupos_actividad()

        if grupos:
            self.grupo_table.setRowCount(len(grupos))
            for row_idx, grupo in enumerate(grupos): # grupo es un diccionario
                # ID, Nombre Grupo, Tipo Actividad, Descripción, Cédula Coordinador, Código Año Escolar, Cupos, Activo
                self.grupo_table.setItem(row_idx, 0, QTableWidgetItem(str(grupo.get('id', ''))))
                self.grupo_table.setItem(row_idx, 1, QTableWidgetItem(grupo.get('nombre_grupo', '')))
                self.grupo_table.setItem(row_idx, 2, QTableWidgetItem(grupo.get('tipo_actividad', '')))
                self.grupo_table.setItem(row_idx, 3, QTableWidgetItem(grupo.get('descripcion', '') or "")) # Descripción puede ser NULL
                self.grupo_table.setItem(row_idx, 4, QTableWidgetItem(str(grupo.get('cedula_coordinador', '') or "")))
                self.grupo_table.setItem(row_idx, 5, QTableWidgetItem(grupo.get('codigo_ano_escolar', '') or ""))
                self.grupo_table.setItem(row_idx, 6, QTableWidgetItem(str(grupo.get('cupos_disponibles', ''))))
                self.grupo_table.setItem(row_idx, 7, QTableWidgetItem("Sí" if grupo.get('activo', False) else "No"))
        self.grupo_table.resizeColumnsToContents()
        self.grupo_table.horizontalHeader().setStretchLastSection(True)
        # populate_grupo_combos() se llama en __init__ después de bloquear/desbloquear señales
        # y también en add_grupo/update_grupo/delete_grupo.
        # No es necesario llamarlo aquí de nuevo si ya se maneja en __init__ y en las operaciones CRUD.
        # Si se llama aquí, se debe asegurar que las señales estén bloqueadas.
        # Para mayor seguridad, se puede llamar con blockSignals(True) si se necesita aquí.
        # self.populate_grupo_combos() # Se comenta para evitar redundancia y posibles triggers.

    def add_grupo(self):
        nombre = self.nombre_grupo_input.text().strip()
        tipo = self.tipo_actividad_input.text().strip()
        descripcion = self.descripcion_input.text().strip()
        coordinador_idx = self.cedula_coordinador_combo.currentIndex()
        coordinador = self.cedula_coordinador_combo.itemData(coordinador_idx) if coordinador_idx > 0 else None
        ano_escolar_idx = self.codigo_ano_escolar_combo.currentIndex()
        ano_escolar = self.codigo_ano_escolar_combo.itemData(ano_escolar_idx) if ano_escolar_idx > 0 else None
        cupos_str = self.cupos_disponibles_input.text().strip()
        activo = self.activo_checkbox.isChecked()

        if not nombre or not tipo or not cupos_str:
            QMessageBox.warning(self, "Campos Vacíos", "Los campos 'Nombre Grupo', 'Tipo Actividad' y 'Cupos Disponibles' son obligatorios.")
            return
        try:
            cupos = int(cupos_str)
            if cupos < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "'Cupos Disponibles' debe ser un número entero no negativo.")
            return

        if self.model.create_grupo_actividad(nombre, tipo, descripcion if descripcion else None,
                                             coordinador, ano_escolar, cupos, activo):
            QMessageBox.information(self, "Éxito", f"Grupo '{nombre}' agregado exitosamente.")
            self.clear_grupo_fields()
            self.load_grupos_actividad() # Recargar la tabla y los combos de grupo
        else:
            QMessageBox.critical(self, "Error", "No se pudo agregar el grupo. Verifique los datos.")

    def load_grupo_to_form(self):
        selected_rows = self.grupo_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            grupo_id = int(self.grupo_table.item(row, 0).text())
            nombre = self.grupo_table.item(row, 1).text()
            tipo = self.grupo_table.item(row, 2).text()
            descripcion = self.grupo_table.item(row, 3).text()
            coordinador_cedula = self.grupo_table.item(row, 4).text()
            ano_escolar_codigo = self.grupo_table.item(row, 5).text()
            cupos = self.grupo_table.item(row, 6).text()
            activo = self.grupo_table.item(row, 7).text() == "Sí"

            self.grupo_id_display.setText(str(grupo_id))
            self.nombre_grupo_input.setText(nombre)
            self.tipo_actividad_input.setText(tipo)
            self.descripcion_input.setText(descripcion)

            # Seleccionar coordinador en el ComboBox
            # Asegúrate de que el tipo de dato de `findData` coincida con el tipo de dato almacenado en el itemData
            # La cédula de personal es VARCHAR en la BD, por lo que el itemData debe ser string.
            idx = self.cedula_coordinador_combo.findData(coordinador_cedula)
            if idx != -1:
                self.cedula_coordinador_combo.setCurrentIndex(idx)
            else:
                self.cedula_coordinador_combo.setCurrentIndex(0) # Seleccionar "Seleccione..."

            # Seleccionar año escolar en el ComboBox
            idx = self.codigo_ano_escolar_combo.findData(ano_escolar_codigo)
            if idx != -1:
                self.codigo_ano_escolar_combo.setCurrentIndex(idx)
            else:
                self.codigo_ano_escolar_combo.setCurrentIndex(0) # Seleccionar "Seleccione..."

            self.cupos_disponibles_input.setText(cupos)
            self.activo_checkbox.setChecked(activo)

            self.add_grupo_btn.setEnabled(False)
            self.update_grupo_btn.setEnabled(True)
            self.delete_grupo_btn.setEnabled(True)
        else:
            self.clear_grupo_fields()

    def update_grupo(self):
        grupo_id_str = self.grupo_id_display.text()
        if grupo_id_str == "Automático" or not grupo_id_str:
            QMessageBox.warning(self, "Error", "Seleccione un grupo para actualizar.")
            return

        grupo_id = int(grupo_id_str)
        nombre = self.nombre_grupo_input.text().strip()
        tipo = self.tipo_actividad_input.text().strip()
        descripcion = self.descripcion_input.text().strip()
        coordinador_idx = self.cedula_coordinador_combo.currentIndex()
        coordinador = self.cedula_coordinador_combo.itemData(coordinador_idx) if coordinador_idx > 0 else None
        ano_escolar_idx = self.codigo_ano_escolar_combo.currentIndex()
        ano_escolar = self.codigo_ano_escolar_combo.itemData(ano_escolar_idx) if ano_escolar_idx > 0 else None
        cupos_str = self.cupos_disponibles_input.text().strip()
        activo = self.activo_checkbox.isChecked()

        if not nombre or not tipo or not cupos_str:
            QMessageBox.warning(self, "Campos Vacíos", "Los campos 'Nombre Grupo', 'Tipo Actividad' y 'Cupos Disponibles' son obligatorios.")
            return
        try:
            cupos = int(cupos_str)
            if cupos < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "'Cupos Disponibles' debe ser un número entero no negativo.")
            return

        if self.model.update_grupo_actividad(grupo_id, nombre, tipo, descripcion if descripcion else None,
                                             coordinador, ano_escolar, cupos, activo):
            QMessageBox.information(self, "Éxito", f"Grupo '{nombre}' actualizado exitosamente.")
            self.clear_grupo_fields()
            self.load_grupos_actividad() # Recargar la tabla y los combos de grupo
        else:
            QMessageBox.critical(self, "Error", "No se pudo actualizar el grupo. Verifique los datos.")

    def delete_grupo(self):
        grupo_id_str = self.grupo_id_display.text()
        if grupo_id_str == "Automático" or not grupo_id_str:
            QMessageBox.warning(self, "Error", "Seleccione un grupo para eliminar.")
            return

        grupo_id = int(grupo_id_str)
        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Está seguro de que desea eliminar el grupo con ID {grupo_id}? "
                                     "Se eliminarán también todas las participaciones asociadas.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.model.delete_grupo_actividad(grupo_id):
                QMessageBox.information(self, "Éxito", f"Grupo con ID {grupo_id} eliminado exitosamente.")
                self.clear_grupo_fields()
                self.load_grupos_actividad() # Recargar la tabla y los combos de grupo
                self.load_participaciones_by_grupo(show_message=False) # Recargar tabla de participaciones sin mensaje
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el grupo.")

    def clear_grupo_fields(self):
        self.grupo_id_display.setText("Automático")
        self.nombre_grupo_input.clear()
        self.tipo_actividad_input.clear()
        self.descripcion_input.clear()
        self.cedula_coordinador_combo.setCurrentIndex(0)
        self.codigo_ano_escolar_combo.setCurrentIndex(0)
        self.cupos_disponibles_input.clear()
        self.activo_checkbox.setChecked(True)
        self.add_grupo_btn.setEnabled(True)
        self.update_grupo_btn.setEnabled(False)
        self.delete_grupo_btn.setEnabled(False)
        self.grupo_table.clearSelection()

    # --- Métodos para PARTICIPACION_GRUPO ---

    def load_participaciones_by_grupo(self, show_message=True): # Añadir argumento show_message
        self.participacion_table.setRowCount(0)
        self.clear_participacion_fields() # Limpiar formulario al cambiar de grupo

        selected_grupo_id = self.filter_grupo_combo.currentData()
        if selected_grupo_id is None or selected_grupo_id == -1: # Manejar None o el valor -1 de "Seleccione un Grupo"
            if show_message: # Solo mostrar mensaje si show_message es True
                QMessageBox.information(self, "Información", "Por favor, seleccione un grupo válido para ver sus participaciones.")
            return

        participaciones = self.model.get_participaciones_by_grupo(selected_grupo_id)
        if participaciones:
            self.participacion_table.setRowCount(len(participaciones))
            for row_idx, p in enumerate(participaciones): # p es un diccionario
                # ID (0), cedula_estudiante (1), nombre_estudiante (2), grupo_id (3), fecha_inscripcion (4),
                # nivel_participacion (5), observaciones (6), activo (7)
                self.participacion_table.setItem(row_idx, 0, QTableWidgetItem(str(p.get('id', '')))) # ID Participación
                self.participacion_table.setItem(row_idx, 1, QTableWidgetItem(str(p.get('cedula_estudiante', '')))) # Cédula Estudiante
                self.participacion_table.setItem(row_idx, 2, QTableWidgetItem(f"{p.get('nombre_estudiante', '') or ''} {p.get('apellido_estudiante', '') or ''}")) # Nombre y Apellido Estudiante
                self.participacion_table.setItem(row_idx, 3, QTableWidgetItem(str(p.get('id_grupo', '')))) # ID Grupo

                fecha_inscripcion_dt = p.get('fecha_inscripcion')
                self.participacion_table.setItem(row_idx, 4, QTableWidgetItem(fecha_inscripcion_dt.strftime("%Y-%m-%d") if fecha_inscripcion_dt else '')) # Fecha Inscripcion

                self.participacion_table.setItem(row_idx, 5, QTableWidgetItem(p.get('nivel_participacion', '') or "")) # Nivel Participacion
                self.participacion_table.setItem(row_idx, 6, QTableWidgetItem(p.get('observaciones', '') or "")) # Observaciones
                self.participacion_table.setItem(row_idx, 7, QTableWidgetItem("Sí" if p.get('activo', False) else "No")) # Activo
        self.participacion_table.resizeColumnsToContents()
        self.participacion_table.horizontalHeader().setStretchLastSection(True)


    def add_participacion(self):
        cedula_estudiante_idx = self.cedula_estudiante_combo.currentIndex()
        cedula_estudiante = self.cedula_estudiante_combo.itemData(cedula_estudiante_idx) if cedula_estudiante_idx > 0 else None
        id_grupo_idx = self.id_grupo_participacion_combo.currentIndex()
        id_grupo = self.id_grupo_participacion_combo.itemData(id_grupo_idx) if id_grupo_idx > 0 else None
        fecha_inscripcion = self.fecha_inscripcion_input.date().toString(Qt.DateFormat.ISODate)
        nivel_participacion = self.nivel_participacion_input.text().strip()
        observaciones = self.observaciones_participacion_input.text().strip()
        activo = self.activo_participacion_checkbox.isChecked()

        if not cedula_estudiante or not id_grupo:
            QMessageBox.warning(self, "Campos Obligatorios", "Debe seleccionar un estudiante y un grupo.")
            return

        if self.model.create_participacion_grupo(cedula_estudiante, id_grupo, fecha_inscripcion,
                                                 nivel_participacion if nivel_participacion else None,
                                                 observaciones if observaciones else None, activo):
            QMessageBox.information(self, "Éxito", "Participación agregada exitosamente.")
            self.clear_participacion_fields()
            self.load_participaciones_by_grupo(show_message=False) # Recargar la tabla sin mensaje
        else:
            QMessageBox.critical(self, "Error", "No se pudo agregar la participación. Verifique los datos.")

    def load_participacion_to_form(self):
        selected_rows = self.participacion_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            participacion_id = int(self.participacion_table.item(row, 0).text())
            cedula_estudiante = self.participacion_table.item(row, 1).text() # Obtener como string para findData
            grupo_id = int(self.participacion_table.item(row, 3).text()) # Columna 3 es ID Grupo
            fecha_inscripcion_str = self.participacion_table.item(row, 4).text()
            nivel_participacion = self.participacion_table.item(row, 5).text()
            observaciones = self.participacion_table.item(row, 6).text()
            activo = self.participacion_table.item(row, 7).text() == "Sí"

            self.participacion_id_display.setText(str(participacion_id))

            idx = self.cedula_estudiante_combo.findData(cedula_estudiante)
            if idx != -1:
                self.cedula_estudiante_combo.setCurrentIndex(idx)
            else:
                self.cedula_estudiante_combo.setCurrentIndex(0) # Fallback

            idx = self.id_grupo_participacion_combo.findData(grupo_id)
            if idx != -1:
                self.id_grupo_participacion_combo.setCurrentIndex(idx)
            else:
                self.id_grupo_participacion_combo.setCurrentIndex(0) # Fallback

            self.fecha_inscripcion_input.setDate(QDate.fromString(fecha_inscripcion_str, Qt.DateFormat.ISODate))
            self.nivel_participacion_input.setText(nivel_participacion)
            self.observaciones_participacion_input.setText(observaciones)
            self.activo_participacion_checkbox.setChecked(activo)

            self.add_participacion_btn.setEnabled(False)
            self.update_participacion_btn.setEnabled(True)
            self.delete_participacion_btn.setEnabled(True)
        else:
            self.clear_participacion_fields()

    def update_participacion(self):
        participacion_id_str = self.participacion_id_display.text()
        if participacion_id_str == "Automático" or not participacion_id_str:
            QMessageBox.warning(self, "Error", "Seleccione una participación para actualizar.")
            return

        participacion_id = int(participacion_id_str)
        cedula_estudiante_idx = self.cedula_estudiante_combo.currentIndex()
        cedula_estudiante = self.cedula_estudiante_combo.itemData(cedula_estudiante_idx) if cedula_estudiante_idx > 0 else None
        id_grupo_idx = self.id_grupo_participacion_combo.currentIndex()
        id_grupo = self.id_grupo_participacion_combo.itemData(id_grupo_idx) if id_grupo_idx > 0 else None
        fecha_inscripcion = self.fecha_inscripcion_input.date().toString(Qt.DateFormat.ISODate)
        nivel_participacion = self.nivel_participacion_input.text().strip()
        observaciones = self.observaciones_participacion_input.text().strip()
        activo = self.activo_participacion_checkbox.isChecked()

        if not cedula_estudiante or not id_grupo:
            QMessageBox.warning(self, "Campos Obligatorios", "Debe seleccionar un estudiante y un grupo.")
            return

        if self.model.update_participacion_grupo(participacion_id, cedula_estudiante, id_grupo,
                                                 fecha_inscripcion, nivel_participacion if nivel_participacion else None,
                                                 observaciones if observaciones else None, activo):
            QMessageBox.information(self, "Éxito", f"Participación con ID {participacion_id} actualizada exitosamente.")
            self.clear_participacion_fields()
            self.load_participaciones_by_grupo(show_message=False) # Recargar la tabla sin mensaje
        else:
            QMessageBox.critical(self, "Error", "No se pudo actualizar la participación.")

    def delete_participacion(self):
        participacion_id_str = self.participacion_id_display.text()
        if participacion_id_str == "Automático" or not participacion_id_str:
            QMessageBox.warning(self, "Error", "Seleccione una participación para eliminar.")
            return

        participacion_id = int(participacion_id_str)
        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     f"¿Está seguro de que desea eliminar la participación con ID {participacion_id}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.model.delete_participacion_grupo(participacion_id):
                QMessageBox.information(self, "Éxito", f"Participación con ID {participacion_id} eliminada exitosamente.")
                self.clear_participacion_fields()
                self.load_participaciones_by_grupo(show_message=False) # Recargar la tabla sin mensaje
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar la participación.")

    def clear_participacion_fields(self):
        self.participacion_id_display.setText("Automático")
        self.cedula_estudiante_combo.setCurrentIndex(0)
        # Mantener el grupo seleccionado en el combo de Participación si es el caso, o resetear
        # Si el filtro de grupo está activo, se podría intentar mantener ese grupo seleccionado en este combo.
        # Por ahora, se resetea al índice 0.
        self.id_grupo_participacion_combo.setCurrentIndex(0)
        self.fecha_inscripcion_input.setDate(QDate.currentDate())
        self.nivel_participacion_input.clear()
        self.observaciones_participacion_input.clear()
        self.activo_participacion_checkbox.setChecked(True)
        self.add_participacion_btn.setEnabled(True)
        self.add_participacion_btn.setStyleSheet("") # Resetear estilo si se deshabilitó antes
        self.update_participacion_btn.setEnabled(False)
        self.delete_participacion_btn.setEnabled(False)
        self.participacion_table.clearSelection()

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
        self.db_manager.close()
        self.closed.emit()
        super().closeEvent(event)


# --- Funciones de Configuración de Base de Datos (Fuera de las clases) ---
def setup_database_grupo_actividad(db_config_for_setup):
    """
    Crea las tablas 'grupo_actividad' y 'participacion_grupo' si no existen.
    También asegura la existencia de 'personal', 'ano_escolar' y 'estudiante'
    para las claves foráneas.
    """
    app_db_manager = DBManager(db_config_for_setup)
    
    if app_db_manager.conn:
        print(f"DEBUG: Conexión exitosa para setup con db_config: {db_config_for_setup.get('database')}. Procediendo a crear tablas.")
        try:
            # Crear tabla 'personal' si no existe (asumida para FK en grupo_actividad)
            create_personal_table_query = """
            CREATE TABLE IF NOT EXISTS personal (
                cedula VARCHAR(20) PRIMARY KEY,
                nombres VARCHAR(100) NOT NULL,
                apellidos VARCHAR(100) NOT NULL,
                -- Otros campos de personal si los hay
                rol VARCHAR(50) DEFAULT 'docente'
            );
            """
            app_db_manager.execute_query(create_personal_table_query)
            print("Table 'personal' checked/created successfully.")

            # Crear tabla 'ano_escolar' si no existe (asumida para FK en grupo_actividad)
            create_ano_escolar_table_query = """
            CREATE TABLE IF NOT EXISTS ano_escolar (
                codigo VARCHAR(10) PRIMARY KEY,
                descripcion VARCHAR(100) NOT NULL,
                numero_anho INTEGER NOT NULL,
                nivel_educativo VARCHAR(50) DEFAULT 'Media General',
                activo BOOLEAN DEFAULT TRUE
            );
            """
            app_db_manager.execute_query(create_ano_escolar_table_query)
            print("Table 'ano_escolar' checked/created successfully.")

            # Crear tabla 'estudiante' si no existe (asumida para FK en participacion_grupo)
            create_estudiante_table_query = """
            CREATE TABLE IF NOT EXISTS estudiante (
                id SERIAL,
                cedula VARCHAR(20) PRIMARY KEY, -- Asegurarse de que sea VARCHAR
                nombres VARCHAR(100) NOT NULL,
                apellidos VARCHAR(100) NOT NULL,
                genero VARCHAR(10),
                fecha_nacimiento DATE,
                telefono VARCHAR(20),
                correo VARCHAR(100),
                direccion TEXT,
                foto_data BYTEA
            );
            """
            app_db_manager.execute_query(create_estudiante_table_query)
            print("Table 'estudiante' checked/created successfully.")

            # Crear tabla 'grupo_actividad'
            create_grupo_actividad_table_query = """
            CREATE TABLE IF NOT EXISTS grupo_actividad (
                id SERIAL PRIMARY KEY,
                nombre_grupo VARCHAR(100) NOT NULL,
                tipo_actividad VARCHAR(100) NOT NULL,
                descripcion TEXT,
                cedula_coordinador VARCHAR(20),
                codigo_ano_escolar VARCHAR(10),
                cupos_disponibles INTEGER NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (cedula_coordinador) REFERENCES personal(cedula) ON DELETE SET NULL,
                FOREIGN KEY (codigo_ano_escolar) REFERENCES ano_escolar(codigo) ON DELETE RESTRICT,
                UNIQUE (nombre_grupo, codigo_ano_escolar) -- Un grupo con el mismo nombre en el mismo año escolar
            );
            """
            app_db_manager.execute_query(create_grupo_actividad_table_query)
            print("Table 'grupo_actividad' checked/created successfully.")

            # Crear tabla 'participacion_grupo'
            create_participacion_grupo_table_query = """
            CREATE TABLE IF NOT EXISTS participacion_grupo (
                id SERIAL PRIMARY KEY,
                cedula_estudiante VARCHAR(20) NOT NULL,
                id_grupo INTEGER NOT NULL,
                fecha_inscripcion DATE NOT NULL,
                nivel_participacion VARCHAR(100),
                observaciones TEXT,
                activo BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (cedula_estudiante) REFERENCES estudiante(cedula) ON DELETE CASCADE,
                FOREIGN KEY (id_grupo) REFERENCES grupo_actividad(id) ON DELETE CASCADE,
                UNIQUE (cedula_estudiante, id_grupo) -- Un estudiante solo puede participar una vez en un grupo
            );
            """
            app_db_manager.execute_query(create_participacion_grupo_table_query)
            print("Table 'participacion_grupo' checked/created successfully.")

        except Exception as e:
            print(f"DEBUG: Error al configurar tablas de grupo de actividad: {e}")
        finally:
            app_db_manager.close() # Cerrar la conexión de la aplicación
            print("DEBUG: Conexión de setup cerrada.")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Configuración de la base de datos
    db_config = {
        'host': 'localhost',
        'database': 'bd', # Asegúrate de que esta DB exista y el usuario tenga permisos
        'user': 'postgres',
        'password': '12345678', # ¡IMPORTANTE! Reemplaza con tu contraseña real
        'port': '5432'
    }

    # Datos de usuario simulados
    test_user_data = {
        'id': 1,
        'username': 'testuser',
        'role': 'admin'
    }

    # --- IMPORTANTE: Ejecuta setup_database_grupo_actividad() una vez para preparar tus tablas ---
    # Descomenta la línea de abajo, ejecuta el script UNA VEZ, y luego vuelve a comentarla.
    # Necesitarás un usuario con permisos para crear bases de datos/tablas.
    setup_database_grupo_actividad(db_config)

    window = GrupoActividadUI(db_config, test_user_data)
    window.show()
    sys.exit(app.exec())
