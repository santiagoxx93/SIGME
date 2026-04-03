import sys
import psycopg2
from psycopg2.extras import RealDictCursor # Importar RealDictCursor
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QDateEdit, QComboBox, QTextEdit,
    QSpacerItem, QSizePolicy, QFrame, QCalendarWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QTabWidget
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal # Importar pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QImage, QFontDatabase

# Importar la librería Pillow (si es necesaria para futuras funcionalidades de imagen)
from PIL import Image as PILImage
from PIL.ImageQt import ImageQt

# --- Definición de la Paleta de Colores (Reinsertada) ---
COLOR_LIGHT_GRAYISH_BLUE = "#b3cbdc"
COLOR_DEEP_DARK_BLUE = "#1c355b"
COLOR_OFF_WHITE = "#e4eaf4"
COLOR_MEDIUM_GRAYISH_BLUE = "#7089a7"
COLOR_ERROR_RED = "#e74c3c" # Para mensajes de error
COLOR_SUCCESS_GREEN = "#2ecc71" # Para mensajes de éxito

COLOR_MAIN_BACKGROUND = "#CBDCE1" # Fondo principal
COLOR_ACCENT_BLUE = "#5B9BD5"
COLOR_WHITE = "#FFFFFF"
COLOR_DARK_TEXT = "#333333"

COLOR_BUTTON_HOVER = "#4A8BCD"
COLOR_BUTTON_PRESSED = "#3C7DBA"

COLOR_DISABLED_BG = "#A0C0E0"
COLOR_DISABLED_TEXT = "#6080A0"

COLOR_PRIMARY_DARK_BLUE = "#1B375C"


class PersonalModule(QWidget):
    # Señal que se emite cuando la ventana del módulo se cierra
    closed = pyqtSignal()

    def __init__(self, db_config, user_data): # Ahora acepta db_config y user_data
        super().__init__()
        self.db_config = db_config # Almacena la configuración de la base de datos
        self.user_data = user_data # Almacena los datos del usuario logueado
        self.setWindowTitle("SIGME - Módulo de Personal")
        self.setGeometry(100, 100, 1200, 850)
        self.init_ui()
        self.apply_styles()
        self.load_personal_data() # Carga inicial de datos

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # Top Bar for Logo and Title
        top_bar_container = QFrame()
        top_bar_container.setObjectName("topBarFrame")
        top_bar_layout = QHBoxLayout(top_bar_container)
        top_bar_layout.setContentsMargins(20, 20, 20, 20)

        # Title - Make it expand and center
        self.title_label = QLabel("REGISTRO Y GESTIÓN DE PERSONAL")
        self.title_label.setObjectName("mainTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_bar_layout.addWidget(self.title_label)

        # Spacer to balance the title with the logo on the left
        top_bar_layout.addSpacerItem(QSpacerItem(100, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        # Botón para volver al menú principal
        self.back_to_menu_button = QPushButton("Volver al Menú")
        self.back_to_menu_button.setObjectName("backToMenuButton")
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        top_bar_layout.addWidget(self.back_to_menu_button)

        main_layout.addWidget(top_bar_container)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        main_layout.addWidget(self.tab_widget)

        # --- Registration Tab ---
        registration_tab = QWidget()
        registration_layout = QVBoxLayout(registration_tab)
        registration_layout.setContentsMargins(40, 30, 40, 30)
        registration_layout.setSpacing(20) # Add some spacing between form and buttons

        # Central Form Layout (using QGridLayout for 3 columns)
        form_grid_layout = QGridLayout()
        form_grid_layout.setSpacing(15)
        form_grid_layout.setHorizontalSpacing(30)

        self.fields = {}
        self.field_definitions = [ # Definir como atributo de instancia para reutilizar
            ("cedula", "Cédula:", "string", "Ej. V-12345678"),
            ("nombres", "Nombres:", "string", "Nombres del personal"),
            ("apellidos", "Apellidos:", "string", "Apellidos del personal"),
            ("cargo", "Cargo:", "string", "Ej. Profesor, Coordinador, Administrador"),
            ("especialidad", "Especialidad:", "string", "Ej. Matemáticas, Lengua, Gestión"),
            ("telefono", "Teléfono:", "string", "Ej. 0412-1234567"),
            ("correo", "Correo:", "string", "Ej. usuario@ejemplo.com"),
            ("fecha_nacimiento", "Fecha de Nacimiento:", "date", None),
            ("genero", "Género:", "combo", ["M", "F", "Otro"]),
            ("fecha_ingreso", "Fecha de Ingreso:", "date", None),
            ("turno", "Turno:", "combo", ["Mañana", "Tarde", "Integral"]),
            ("carga_horaria", "Carga Horaria (int):", "string", "Ej. 40 (horas semanales)"),
            ("estado", "Estado:", "combo", ["Activo", "Inactivo", "Vacaciones", "Permiso"]),
            ("observaciones", "Observaciones (text):", "text_area", "Notas adicionales sobre el personal...")
        ]

        row = 0
        col = 0
        for i, (name, label_text, field_type, placeholder_or_items) in enumerate(self.field_definitions):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; color: #1c355b; margin-bottom: 2px;")

            input_widget = None

            if field_type == "string":
                input_widget = QLineEdit()
                input_widget.setPlaceholderText(placeholder_or_items)
            elif field_type == "date":
                input_widget = QDateEdit()
                input_widget.setCalendarPopup(True)
                input_widget.setDate(QDate(2000, 1, 1) if name == 'fecha_nacimiento' else QDate.currentDate())
            elif field_type == "combo":
                input_widget = QComboBox()
                input_widget.addItems(placeholder_or_items)
            elif field_type == "text_area":
                input_widget = QTextEdit()
                input_widget.setPlaceholderText(placeholder_or_items)
                input_widget.setFixedHeight(80)
            
            if input_widget:
                self.fields[name] = input_widget # Asegura que el campo se añade a self.fields

            if field_type == "text_area":
                # Special layout for text_area to span 3 columns
                form_grid_layout.addWidget(label, row, col, 1, 3)
                form_grid_layout.addWidget(input_widget, row + 1, col, 1, 3)
                # After the text area, subsequent fields should start on a new row and column 0
                row += 2
                col = 0 # Reset col to 0 for next potential row
            else:
                form_grid_layout.addWidget(label, row, col)
                form_grid_layout.addWidget(input_widget, row + 1, col)
                col += 1
                if col > 2:
                    col = 0
                    row += 2
        
        registration_layout.addLayout(form_grid_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 0) # Adjust margins for buttons within tab
        button_layout.setSpacing(30)
        
        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.save_button = QPushButton("Registrar Personal")
        self.save_button.clicked.connect(self.register_personal)
        button_layout.addWidget(self.save_button)

        self.update_button = QPushButton("Actualizar Personal")
        self.update_button.clicked.connect(self.update_personal)
        self.update_button.setEnabled(False) # Deshabilitado inicialmente
        button_layout.addWidget(self.update_button)

        self.delete_button = QPushButton("Eliminar Personal")
        self.delete_button.clicked.connect(self.delete_personal)
        self.delete_button.setEnabled(False) # Deshabilitado inicialmente
        button_layout.addWidget(self.delete_button)

        self.clear_button = QPushButton("Limpiar Campos")
        self.clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_button)

        button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        registration_layout.addLayout(button_layout)
        registration_layout.addStretch(1) # Push content to top

        self.tab_widget.addTab(registration_tab, "Registrar Personal")

        # --- List Tab ---
        list_tab = QWidget()
        list_layout = QVBoxLayout(list_tab)
        list_layout.setContentsMargins(20, 20, 20, 20) # Add margins for the table

        self.personal_table = QTableWidget()
        # Usar los nombres de las etiquetas como encabezados
        self.personal_table.setHorizontalHeaderLabels([fd[1].replace(":", "") for fd in self.field_definitions])
        self.personal_table.setColumnCount(len(self.field_definitions)) # Establecer el número de columnas
        self.personal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.personal_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.personal_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Make table read-only
        self.personal_table.clicked.connect(self.load_personal_to_form) # Load data to form on row click
        
        list_layout.addWidget(self.personal_table)
        self.tab_widget.addTab(list_tab, "Lista de Personal")

        # Connect tab change signal to load data
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """Called when the tab is changed."""
        if self.tab_widget.tabText(index) == "Lista de Personal":
            self.load_personal_data()

    def apply_styles(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLOR_OFF_WHITE))
        palette.setColor(QPalette.ColorRole.Button, QColor(COLOR_DEEP_DARK_BLUE))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLOR_OFF_WHITE))
        palette.setColor(QPalette.ColorRole.Base, QColor(COLOR_WHITE))
        palette.setColor(QPalette.ColorRole.Text, QColor(COLOR_DEEP_DARK_BLUE))

        self.setPalette(palette)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_OFF_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
                font-family: 'Roboto', sans-serif;
            }}
            #topBarFrame {{
                background-color: {COLOR_DEEP_DARK_BLUE};
            }}
            #mainTitleLabel {{
                font-size: 32px;
                font-weight: bold;
                color: {COLOR_OFF_WHITE};
                background-color: {COLOR_DEEP_DARK_BLUE}; /* Asegura que el QLabel tenga el mismo fondo */
            }}
            QLabel {{
                font-size: 15px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            QLineEdit, QDateEdit, QComboBox, QTextEdit {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 15px;
                color: {COLOR_DEEP_DARK_BLUE};
                selection-background-color: {COLOR_LIGHT_GRAYISH_BLUE};
            }}
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QTextEdit:focus {{
                border-color: {COLOR_DEEP_DARK_BLUE};
                outline: none;
                box-shadow: 0 0 0 2px rgba(28, 53, 91, 0.2);
            }}
            QComboBox::drop-down {{
                border: 0px;
            }}
            QPushButton {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_OFF_WHITE};
                border: none;
                border-radius: 10px;
                padding: 14px 30px;
                font-size: 17px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
                border: 1px solid {COLOR_OFF_WHITE};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_LIGHT_GRAYISH_BLUE};
                color: {COLOR_DEEP_DARK_BLUE};
                border: 1px solid {COLOR_DEEP_DARK_BLUE};
            }}
            
            /* Styles for QCalendarWidget (the date picker popup) */
            QCalendarWidget {{
                background-color: #f0f4f7;
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 8px;
            }}
            QCalendarWidget QAbstractItemView {{
                selection-background-color: {COLOR_LIGHT_GRAYISH_BLUE};
                selection-color: {COLOR_DEEP_DARK_BLUE};
                background-color: {COLOR_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
                border: none;
            }}
            QCalendarWidget QToolButton {{
                background-color: {COLOR_LIGHT_GRAYISH_BLUE};
                color: {COLOR_DEEP_DARK_BLUE};
                border-radius: 5px;
                margin: 5px;
                font-size: 14px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
            }}
            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
            }}
            QCalendarWidget QMenu {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 5px;
            }}
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {{
                width: 16px;
                height: 16px;
                background-color: {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 3px;
                margin: 2px;
            }}
            QCalendarWidget QSpinBox::up-button:hover, QCalendarWidget QSpinBox::down-button:hover {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
            }}
            QCalendarWidget QSpinBox::up-arrow, QCalendarWidget QSpinBox::down-arrow {{
                image: none;
            }}
            QCalendarWidget #qt_calendar_prevmonth, QCalendarWidget #qt_calendar_nextmonth {{
                qproperty-icon: url(no_icon.png); /* Asegúrate de tener un icono o que no afecte si no existe */
            }}
            QCalendarWidget QTableView {{
                alternate-background-color: #f8fbfc;
            }}
            /* Estilos para QTableWidget */
            QTableWidget {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 8px;
                font-size: 14px;
                color: {COLOR_DEEP_DARK_BLUE};
                gridline-color: {COLOR_OFF_WHITE};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_LIGHT_GRAYISH_BLUE};
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            QHeaderView::section {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_OFF_WHITE};
                padding: 8px;
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                font-weight: bold;
            }}
            QHeaderView::section:horizontal {{
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            
            /* Styles for QTabWidget */
            QTabWidget::pane {{ /* The tab widget frame */
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                background-color: {COLOR_OFF_WHITE};
                border-radius: 8px;
            }}

            QTabWidget::tab-bar {{
                left: 5px; /* move to the right */
            }}

            QTabBar::tab {{
                background: {COLOR_LIGHT_GRAYISH_BLUE}; /* Light blue/gray */
                color: {COLOR_DEEP_DARK_BLUE}; /* Dark blue text */
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE}; /* Medium blue/gray border */
                border-bottom-color: {COLOR_OFF_WHITE}; /* Same as pane color */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 10px 20px;
                min-width: 100px;
                font-size: 16px;
                font-weight: bold;
                margin-right: 2px;
            }}

            QTabBar::tab:selected {{
                background: {COLOR_DEEP_DARK_BLUE}; /* Dark blue for selected tab */
                color: {COLOR_OFF_WHITE}; /* Light text for selected tab */
                border-color: {COLOR_DEEP_DARK_BLUE};
                border-bottom-color: {COLOR_DEEP_DARK_BLUE}; /* match the pane border */
            }}

            QTabBar::tab:hover:!selected {{
                background: {COLOR_MEDIUM_GRAYISH_BLUE}; /* Medium blue/gray on hover for unselected */
                color: {COLOR_OFF_WHITE};
            }}

            QTabBar::tab:!selected {{
                margin-top: 2px; /* make non-selected tabs look sunken */
            }}

            #backToMenuButton {{
                background-color: {COLOR_ACCENT_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
            }}
            #backToMenuButton:hover {{
                background-color: #4A8BCD; /* Un poco más oscuro */
            }}
            #backToMenuButton:pressed {{
                background-color: #3C7DBA; /* Aún más oscuro */
            }}
        """)

    def get_db_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL
        utilizando la configuración pasada al constructor.
        """
        try:
            conn = psycopg2.connect(**self.db_config) # Usa self.db_config
            return conn
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la base de datos: {e}")
            return None

    def register_personal(self):
        conn = None  # Inicializar conn a None
        cursor = None # Inicializar cursor a None
        try:
            conn = self.get_db_connection()
            if conn is None:
                QMessageBox.warning(self, "Error de Conexión", "No se pudo establecer conexión a la base de datos. Por favor, verifique su configuración (usuario, contraseña, base de datos).")
                return 
            
            cursor = conn.cursor() 

            cedula = self.fields['cedula'].text().strip()
            nombres = self.fields['nombres'].text().strip()
            apellidos = self.fields['apellidos'].text().strip()
            cargo = self.fields['cargo'].text().strip()
            especialidad = self.fields['especialidad'].text().strip()
            telefono = self.fields['telefono'].text().strip()
            correo = self.fields['correo'].text().strip()
            fecha_nacimiento = self.fields['fecha_nacimiento'].date().toString("yyyy-MM-dd")
            genero = self.fields['genero'].currentText().strip()
            fecha_ingreso = self.fields['fecha_ingreso'].date().toString("yyyy-MM-dd")
            turno = self.fields['turno'].currentText().strip()
            
            carga_horaria_str = self.fields['carga_horaria'].text().strip()
            if not carga_horaria_str.isdigit():
                QMessageBox.warning(self, "Entrada Inválida", "La carga horaria debe ser un número entero.")
                return
            carga_horaria = int(carga_horaria_str)

            estado = self.fields['estado'].currentText().strip()
            observaciones = self.fields['observaciones'].toPlainText().strip() # Corrected: Accessing QTextEdit content

            if not all([cedula, nombres, apellidos, cargo, telefono, correo, fecha_nacimiento, genero, fecha_ingreso, turno, carga_horaria_str, estado]):
                QMessageBox.warning(self, "Campos Vacíos", "Por favor, complete todos los campos obligatorios.")
                return

            cursor.execute("SELECT cedula FROM personal WHERE cedula = %s", (cedula,))
            if cursor.fetchone():
                QMessageBox.warning(self, "Cédula Existente", "La cédula ingresada ya está registrada. Por favor, verifique.")
                return

            insert_query = """
            INSERT INTO personal (
                cedula, nombres, apellidos, cargo, especialidad, telefono, correo, 
                fecha_nacimiento, genero, fecha_ingreso, turno, carga_horaria, estado, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(insert_query, (
                cedula, nombres, apellidos, cargo, especialidad, telefono, correo,
                fecha_nacimiento, genero, fecha_ingreso, turno, carga_horaria, estado, observaciones
            ))
            conn.commit()
            QMessageBox.information(self, "Registro Exitoso", f"Personal '{nombres} {apellidos}' registrado con éxito.")
            self.clear_fields()
            self.load_personal_data() # Recargar datos en la tabla
            self.save_button.setEnabled(True) # Habilitar guardar
            self.update_button.setEnabled(False) # Deshabilitar actualizar
            self.delete_button.setEnabled(False) # Deshabilitar eliminar
        except psycopg2.Error as e:
            if conn: # Solo intentar rollback si la conexión existe y es válida
                conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"Ocurrió un error al registrar el personal: {e}")
        except Exception as e: # Captura cualquier otra excepción inesperada
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado: {e}")
        finally:
            if cursor: # Solo cerrar si el cursor fue creado y no es None
                cursor.close()
            if conn: # Solo cerrar si la conexión fue establecida y no es None
                conn.close()

    def update_personal(self):
        conn = None
        cursor = None
        try:
            conn = self.get_db_connection()
            if conn is None:
                return
            cursor = conn.cursor()

            cedula = self.fields['cedula'].text().strip()
            nombres = self.fields['nombres'].text().strip()
            apellidos = self.fields['apellidos'].text().strip()
            cargo = self.fields['cargo'].text().strip()
            especialidad = self.fields['especialidad'].text().strip()
            telefono = self.fields['telefono'].text().strip()
            correo = self.fields['correo'].text().strip()
            fecha_nacimiento = self.fields['fecha_nacimiento'].date().toString("yyyy-MM-dd")
            genero = self.fields['genero'].currentText().strip()
            fecha_ingreso = self.fields['fecha_ingreso'].date().toString("yyyy-MM-dd")
            turno = self.fields['turno'].currentText().strip()
            
            carga_horaria_str = self.fields['carga_horaria'].text().strip()
            if not carga_horaria_str.isdigit():
                QMessageBox.warning(self, "Entrada Inválida", "La carga horaria debe ser un número entero.")
                return
            carga_horaria = int(carga_horaria_str)

            estado = self.fields['estado'].currentText().strip()
            observaciones = self.fields['observaciones'].toPlainText().strip()

            if not all([cedula, nombres, apellidos, cargo, telefono, correo, fecha_nacimiento, genero, fecha_ingreso, turno, carga_horaria_str, estado]):
                QMessageBox.warning(self, "Campos Vacíos", "Por favor, complete todos los campos obligatorios.")
                return

            update_query = """
            UPDATE personal SET
                nombres = %s, apellidos = %s, cargo = %s, especialidad = %s,
                telefono = %s, correo = %s, fecha_nacimiento = %s, genero = %s,
                fecha_ingreso = %s, turno = %s, carga_horaria = %s, estado = %s, observaciones = %s
            WHERE cedula = %s;
            """
            cursor.execute(update_query, (
                nombres, apellidos, cargo, especialidad, telefono, correo,
                fecha_nacimiento, genero, fecha_ingreso, turno, carga_horaria, estado, observaciones,
                cedula
            ))
            conn.commit()
            if cursor.rowcount > 0:
                QMessageBox.information(self, "Actualización Exitosa", f"Personal con cédula '{cedula}' actualizado con éxito.")
                self.clear_fields()
                self.load_personal_data()
                self.save_button.setEnabled(True) # Habilitar guardar
                self.update_button.setEnabled(False) # Deshabilitar actualizar
                self.delete_button.setEnabled(False) # Deshabilitar eliminar
            else:
                QMessageBox.warning(self, "No Encontrado", f"No se encontró personal con cédula '{cedula}'.")
        except psycopg2.Error as e:
            if conn: # Solo intentar rollback si la conexión existe y es válida
                conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"Ocurrió un error al actualizar el personal: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def delete_personal(self):
        conn = None
        cursor = None
        try:
            conn = self.get_db_connection()
            if conn is None:
                return
            cursor = conn.cursor()
            cedula = self.fields['cedula'].text().strip()
            if not cedula:
                QMessageBox.warning(self, "Cédula Vacía", "Seleccione un registro de la tabla para eliminar.")
                return

            reply = QMessageBox.question(self, "Confirmar Eliminación",
                                         f"¿Está seguro de que desea eliminar el registro de personal con cédula '{cedula}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                delete_query = "DELETE FROM personal WHERE cedula = %s;"
                cursor.execute(delete_query, (cedula,))
                conn.commit()
                if cursor.rowcount > 0:
                    QMessageBox.information(self, "Eliminación Exitosa", f"Personal con cédula '{cedula}' eliminado con éxito.")
                    self.clear_fields()
                    self.load_personal_data()
                    self.save_button.setEnabled(True) # Habilitar guardar
                    self.update_button.setEnabled(False) # Deshabilitar actualizar
                    self.delete_button.setEnabled(False) # Deshabilitar eliminar
                else:
                    QMessageBox.warning(self, "No Encontrado", f"No se encontró personal con cédula '{cedula}'.")
        except psycopg2.Error as e:
            if conn: # Solo intentar rollback si la conexión existe y es válida
                conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"Ocurrió un error al eliminar el personal: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def load_personal_data(self):
        conn = None
        cursor = None
        try:
            conn = self.get_db_connection()
            if conn is None:
                return
            
            # Usar RealDictCursor para acceder a los resultados por nombre de columna
            cursor = conn.cursor(cursor_factory=RealDictCursor) 
            cursor.execute("SELECT * FROM personal ORDER BY cedula;")
            records = cursor.fetchall()

            self.personal_table.setRowCount(0) # Clear existing rows
            self.personal_table.setRowCount(len(records))

            # Obtener los nombres de los campos en el orden definido en field_definitions
            field_names_order = [fd[0] for fd in self.field_definitions]
            
            for row_idx, record in enumerate(records):
                for field_idx, field_name in enumerate(field_names_order):
                    # Acceder al valor por el nombre de la columna del diccionario
                    value = record.get(field_name) # Usar .get() para evitar KeyError si la columna no existe

                    if isinstance(value, datetime.date): # psycopg2 devuelve date como datetime.date
                        value = value.strftime("%Y-%m-%d")
                    elif value is None:
                        value = ""
                    else:
                        value = str(value)
                    
                    item = QTableWidgetItem(value)
                    self.personal_table.setItem(row_idx, field_idx, item)

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Ocurrió un error al cargar los datos: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado al cargar los datos: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def load_personal_to_form(self):
        selected_row = self.personal_table.currentRow()
        if selected_row >= 0:
            self.clear_fields() # Clear current form data

            # Usar self.field_definitions directamente
            field_definitions_form_map = {fd[0]: (fd[2], fd[3]) for fd in self.field_definitions}

            # Iterate through the table columns and populate the form fields
            for col_idx, (field_name, _, field_type, _) in enumerate(self.field_definitions): # Iterar sobre field_definitions
                item = self.personal_table.item(selected_row, col_idx)
                if item:
                    value = item.text()
                    field_widget = self.fields.get(field_name) # Use .get() for safety

                    if field_widget:
                        if field_type == "string":
                            field_widget.setText(value)
                        elif field_type == "date":
                            date_value = QDate.fromString(value, "yyyy-MM-dd")
                            if date_value.isValid():
                                field_widget.setDate(date_value)
                            else:
                                field_widget.setDate(QDate.currentDate()) # Fallback
                        elif field_type == "combo":
                            index = field_widget.findText(value)
                            if index >= 0:
                                field_widget.setCurrentIndex(index)
                        elif field_type == "text_area":
                            field_widget.setPlainText(value)
            
            self.fields['cedula'].setEnabled(False) # Disable Cédula for update/delete
            self.save_button.setEnabled(False) # Disable save
            self.update_button.setEnabled(True) # Enable update
            self.delete_button.setEnabled(True) # Enable delete

            self.tab_widget.setCurrentIndex(0) # Switch to registration tab

    def clear_fields(self):
        for field_name, field_widget in self.fields.items():
            if isinstance(field_widget, QLineEdit):
                field_widget.clear()
            elif isinstance(field_widget, QDateEdit):
                # Restablecer fecha de nacimiento a una fecha por defecto (ej. 2000-01-01)
                # y fecha de ingreso a la fecha actual
                if field_name == 'fecha_nacimiento':
                    field_widget.setDate(QDate(2000, 1, 1))
                else: # fecha_ingreso
                    field_widget.setDate(QDate.currentDate())
            elif isinstance(field_widget, QComboBox):
                field_widget.setCurrentIndex(0) # Reset to first item
            elif isinstance(field_widget, QTextEdit):
                field_widget.clear()
        
        self.fields['cedula'].setEnabled(True) # Re-enable Cédula for new entry
        self.save_button.setEnabled(True) # Re-enable save
        self.update_button.setEnabled(False) # Disable update
        self.delete_button.setEnabled(False) # Disable delete

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


# --- Funciones de Configuración de Base de Datos (Fuera de la clase PersonalModule) ---
# Estas funciones son para la configuración inicial de tu base de datos PostgreSQL.
# Se recomienda ejecutarlas una única vez para preparar el entorno.
# NO DEBEN SER PARTE DEL FLUJO NORMAL DE LA APLICACIÓN.

def setup_database():
    """
    Configura la base de datos PostgreSQL:
    - Crea la base de datos 'sigme_db' si no existe.
    - Crea el usuario 'sigme_user' si no existe.
    - Otorga todos los privilegios a 'sigme_user' sobre 'sigme_db'.
    - Crea la tabla 'personal' si no existe.
    
    ¡ADVERTENCIA DE SEGURIDAD!
    Esta función usa la contraseña de superusuario de PostgreSQL directamente.
    Úsala SOLO para la configuración inicial y luego elimínala o asegúrala.
    """
    conn = None
    cursor = None 
    try:
        # Conectar a la base de datos predeterminada 'postgres' para crear la nueva DB
        conn = psycopg2.connect(
            host="localhost",
            database="postgres", # Conectarse a la base de datos 'postgres' por defecto
            user="postgres",
            password="123456" # <--- ¡IMPORTANTE! Reemplaza esto con tu contraseña de superusuario de PostgreSQL
        )
        conn.autocommit = True # Permitir comandos DDL sin commit explícito
        cursor = conn.cursor()

        # Crear base de datos 'sigme_db' si no existe
        try:
            cursor.execute("CREATE DATABASE sigme_db;")
            print("Database 'sigme_db' created successfully.")
        except psycopg2.errors.DuplicateDatabase:
            print("Database 'sigme_db' already exists.")
        
        # Crear usuario 'sigme_user' si no existe
        try:
            cursor.execute("CREATE USER sigme_user WITH PASSWORD 'sigme_password';")
            print("User 'sigme_user' created successfully.")
        except psycopg2.errors.DuplicateObject:
            print("User 'sigme_user' already exists.")

        # Otorgar privilegios a 'sigme_user' en 'sigme_db'
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE sigme_db TO sigme_user;")
        print("Privileges granted on database 'sigme_db' to 'sigme_user'.")

    except psycopg2.Error as e:
        print(f"Error setting up database (initial connection/user/db creation): {e}")
    finally:
        if cursor: 
            cursor.close()
        if conn: 
            conn.close()

    # Ahora conectar a 'sigme_db' para crear la tabla 'personal'
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="sigme_db",
            user="sigme_user", # Usar el nuevo usuario con permisos
            password="sigme_password" 
        )
        cursor = conn.cursor()

        # Crear tabla 'personal' si no existe
        create_table_query = """
        CREATE TABLE IF NOT EXISTS personal (
            id SERIAL PRIMARY KEY, -- Añadido un ID SERIAL para clave primaria
            cedula VARCHAR(100) UNIQUE NOT NULL, -- UNIQUE para asegurar que la cédula es única
            nombres VARCHAR(100) NOT NULL,
            apellidos VARCHAR(100) NOT NULL,
            cargo VARCHAR(100),
            especialidad VARCHAR(100),
            telefono VARCHAR(20),
            correo VARCHAR(100),
            fecha_nacimiento DATE,
            genero VARCHAR(10),
            fecha_ingreso DATE,
            turno VARCHAR(20),
            carga_horaria INT,
            estado VARCHAR(20),
            observaciones TEXT
        );
        """
        cursor.execute(create_table_query)
        print("Table 'personal' checked/created successfully.")
        conn.commit()
    except psycopg2.Error as e:
        print(f"Error setting up database (table creation): {e}")
    finally:
        if cursor: 
            cursor.close()
        if conn: 
            conn.close()
