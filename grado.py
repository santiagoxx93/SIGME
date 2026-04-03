import sys
import psycopg2
from psycopg2.extras import RealDictCursor # Importar RealDictCursor
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QTextEdit,
    QSpacerItem, QSizePolicy, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGroupBox # QGroupBox para simular LabelFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate # Importar pyqtSignal y QDate
from PyQt6.QtGui import QFont, QPalette, QColor

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


class GradoApp(QWidget):
    # Señal que se emite cuando la ventana del módulo se cierra
    closed = pyqtSignal()

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data # No usado directamente en este módulo, pero pasado para consistencia
        self.setWindowTitle("SIGME - Módulo de Año Escolar")
        self.setGeometry(100, 100, 950, 750) # Ajustado el tamaño de la ventana
        self.init_ui()
        self.apply_styles()
        self.load_anhos_data() # Carga inicial de datos

    def get_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL
        utilizando la configuración pasada al constructor.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Conexión", f"No se pudo conectar a la base de datos: {e}")
            return None

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

        self.title_label = QLabel("GESTIÓN DE AÑOS ACADÉMICOS")
        self.title_label.setObjectName("mainTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_bar_layout.addWidget(self.title_label)

        top_bar_layout.addSpacerItem(QSpacerItem(100, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        self.back_to_menu_button = QPushButton("Volver al Menú")
        self.back_to_menu_button.setObjectName("backToMenuButton")
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        top_bar_layout.addWidget(self.back_to_menu_button)

        main_layout.addWidget(top_bar_container)

        # --- Tabla de Años ---
        frame_tabla = QGroupBox("📚 Años Académicos Registrados en la Base de Datos")
        frame_tabla.setObjectName("groupBoxFrame")
        frame_tabla_layout = QVBoxLayout(frame_tabla)
        frame_tabla_layout.setContentsMargins(15, 25, 15, 15) # Ajustar márgenes

        self.tabla_anhos = QTableWidget()
        self.tabla_anhos.setColumnCount(5)
        self.tabla_anhos.setHorizontalHeaderLabels(['Código', 'Nombre', 'Nivel Educativo', 'Nº Año', 'Activo'])
        self.tabla_anhos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_anhos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_anhos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_anhos.clicked.connect(self.load_anho_to_form) # Cargar datos al formulario al hacer clic

        frame_tabla_layout.addWidget(self.tabla_anhos)

        self.boton_borrar = QPushButton("🗑️ Borrar Selección")
        self.boton_borrar.setObjectName("actionButton")
        self.boton_borrar.clicked.connect(self.borrar_anho_seleccionado)
        frame_tabla_layout.addWidget(self.boton_borrar, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(frame_tabla)

        # --- Formulario de Registro ---
        frame_registro = QGroupBox("📝 Registrar Nuevo Año")
        frame_registro.setObjectName("groupBoxFrame")
        frame_registro_layout = QGridLayout(frame_registro)
        frame_registro_layout.setContentsMargins(15, 25, 15, 15) # Ajustar márgenes
        frame_registro_layout.setHorizontalSpacing(15)
        frame_registro_layout.setVerticalSpacing(10)

        # Widgets del formulario
        label_codigo = QLabel("Código:")
        label_codigo.setObjectName("fieldLabel")
        frame_registro_layout.addWidget(label_codigo, 0, 0)
        self.entry_codigo = QLineEdit()
        self.entry_codigo.setPlaceholderText("Ej. 1ER-AÑO")
        self.entry_codigo.setObjectName("inputField")
        frame_registro_layout.addWidget(self.entry_codigo, 0, 1)

        label_nombre = QLabel("Nombre:")
        label_nombre.setObjectName("fieldLabel")
        frame_registro_layout.addWidget(label_nombre, 0, 2)
        self.entry_nombre = QLineEdit()
        self.entry_nombre.setPlaceholderText("Ej. Primer Año de Media General")
        self.entry_nombre.setObjectName("inputField")
        frame_registro_layout.addWidget(self.entry_nombre, 0, 3)

        label_numero = QLabel("Número Año:")
        label_numero.setObjectName("fieldLabel")
        frame_registro_layout.addWidget(label_numero, 1, 0)
        self.entry_numero = QLineEdit()
        self.entry_numero.setPlaceholderText("Ej. 1")
        self.entry_numero.setObjectName("inputField")
        frame_registro_layout.addWidget(self.entry_numero, 1, 1)

        label_descripcion = QLabel("Descripción:")
        label_descripcion.setObjectName("fieldLabel")
        frame_registro_layout.addWidget(label_descripcion, 1, 2)
        self.entry_descripcion = QTextEdit() # Usar QTextEdit para descripción
        self.entry_descripcion.setPlaceholderText("Notas adicionales sobre el año académico...")
        self.entry_descripcion.setObjectName("inputField")
        self.entry_descripcion.setFixedHeight(60) # Altura fija para el QTextEdit
        frame_registro_layout.addWidget(self.entry_descripcion, 1, 3)

        # Ocupar el espacio restante en las columnas
        frame_registro_layout.setColumnStretch(1, 1)
        frame_registro_layout.setColumnStretch(3, 1)

        button_layout_registro = QHBoxLayout()
        button_layout_registro.addStretch()
        self.boton_registrar = QPushButton("Registrar Año")
        self.boton_registrar.setObjectName("actionButton")
        self.boton_registrar.clicked.connect(self.registrar_nuevo_anho)
        button_layout_registro.addWidget(self.boton_registrar)

        self.boton_actualizar = QPushButton("Actualizar Año")
        self.boton_actualizar.setObjectName("actionButton")
        self.boton_actualizar.clicked.connect(self.actualizar_anho_seleccionado)
        self.boton_actualizar.setEnabled(False) # Deshabilitado inicialmente
        button_layout_registro.addWidget(self.boton_actualizar)

        self.boton_limpiar = QPushButton("Limpiar Campos")
        self.boton_limpiar.setObjectName("actionButton")
        self.boton_limpiar.clicked.connect(self.clear_fields)
        button_layout_registro.addWidget(self.boton_limpiar)
        button_layout_registro.addStretch()

        frame_registro_layout.addLayout(button_layout_registro, 2, 0, 1, 4) # Añadir botones en la fila 2, ocupando 4 columnas

        main_layout.addWidget(frame_registro)

        # --- Indicadores ---
        frame_indicadores = QGroupBox("📊 Indicadores")
        frame_indicadores.setObjectName("groupBoxFrame")
        frame_indicadores_layout = QVBoxLayout(frame_indicadores)
        frame_indicadores_layout.setContentsMargins(15, 25, 15, 15)

        self.label_indicador_total = QLabel("Total de años registrados: 0")
        self.label_indicador_total.setObjectName("indicatorLabel")
        self.label_indicador_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_indicadores_layout.addWidget(self.label_indicador_total)

        main_layout.addWidget(frame_indicadores)
        main_layout.addStretch(1) # Empuja el contenido hacia arriba

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
                background-color: {COLOR_DEEP_DARK_BLUE};
            }}
            QLabel {{
                font-size: 15px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            #fieldLabel {{
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
                margin-bottom: 2px;
            }}
            #indicatorLabel {{
                font-size: 18px;
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            QLineEdit, QComboBox, QTextEdit {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 15px;
                color: {COLOR_DEEP_DARK_BLUE};
                selection-background-color: {COLOR_LIGHT_GRAYISH_BLUE};
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
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
            
            /* Styles for QTableWidget */
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
            QGroupBox {{
                background-color: {COLOR_OFF_WHITE};
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 10px;
                margin-top: 20px; /* Espacio para el título */
                font-size: 16px;
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center; /* Centra el título */
                padding: 0 10px;
                background-color: {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 5px;
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
            #actionButton {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_OFF_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
            }}
            #actionButton:hover {{
                background-color: {COLOR_ACCENT_BLUE};
            }}
            #actionButton:pressed {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_DISABLED_BG};
                color: {COLOR_DISABLED_TEXT};
            }}
        """)

    def clear_fields(self):
        self.entry_codigo.clear()
        self.entry_nombre.clear()
        self.entry_numero.clear()
        self.entry_descripcion.clear()
        self.entry_codigo.setEnabled(True) # Habilitar código para nuevo registro
        self.boton_registrar.setEnabled(True)
        self.boton_actualizar.setEnabled(False)
        self.boton_borrar.setEnabled(False)

    def load_anhos_data(self):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            if conn is None:
                return
            
            cursor = conn.cursor(cursor_factory=RealDictCursor) # Usar RealDictCursor
            cursor.execute("SELECT codigo, nombre, nivel_educativo, numero_anho, activo FROM anhos ORDER BY numero_anho;")
            records = cursor.fetchall()

            self.tabla_anhos.setRowCount(0) # Limpiar filas existentes
            self.tabla_anhos.setRowCount(len(records))

            for row_idx, record in enumerate(records):
                self.tabla_anhos.setItem(row_idx, 0, QTableWidgetItem(record.get('codigo', '')))
                self.tabla_anhos.setItem(row_idx, 1, QTableWidgetItem(record.get('nombre', '')))
                self.tabla_anhos.setItem(row_idx, 2, QTableWidgetItem(record.get('nivel_educativo', '')))
                self.tabla_anhos.setItem(row_idx, 3, QTableWidgetItem(str(record.get('numero_anho', ''))))
                self.tabla_anhos.setItem(row_idx, 4, QTableWidgetItem('Sí' if record.get('activo', False) else 'No'))
            
            self.actualizar_indicadores()

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Ocurrió un error al cargar los datos: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado al cargar los datos: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def load_anho_to_form(self):
        selected_row = self.tabla_anhos.currentRow()
        if selected_row >= 0:
            self.clear_fields() # Limpiar campos antes de cargar
            
            codigo = self.tabla_anhos.item(selected_row, 0).text()
            nombre = self.tabla_anhos.item(selected_row, 1).text()
            # nivel_educativo = self.tabla_anhos.item(selected_row, 2).text() # Si tuvieras un campo para esto
            numero_anho = self.tabla_anhos.item(selected_row, 3).text()
            # activo = self.tabla_anhos.item(selected_row, 4).text() # Si tuvieras un campo para esto

            # Para la descripción, necesitamos obtenerla de la DB ya que la tabla no la muestra
            conn = self.get_connection()
            if conn:
                try:
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute("SELECT descripcion FROM anhos WHERE codigo = %s", (codigo,))
                        result = cursor.fetchone()
                        descripcion = result['descripcion'] if result else ""
                        self.entry_descripcion.setPlainText(descripcion)
                except psycopg2.Error as e:
                    QMessageBox.warning(self, "Error", f"No se pudo cargar la descripción: {e}")
                finally:
                    conn.close()

            self.entry_codigo.setText(codigo)
            self.entry_nombre.setText(nombre)
            self.entry_numero.setText(numero_anho)
            
            self.entry_codigo.setEnabled(False) # Deshabilitar edición del código al actualizar
            self.boton_registrar.setEnabled(False)
            self.boton_actualizar.setEnabled(True)
            self.boton_borrar.setEnabled(True)

    def registrar_nuevo_anho(self):
        codigo = self.entry_codigo.text().strip().upper()
        nombre = self.entry_nombre.text().strip()
        numero_str = self.entry_numero.text().strip()
        descripcion = self.entry_descripcion.toPlainText().strip() # Usar toPlainText() para QTextEdit

        if not all([codigo, nombre, numero_str, descripcion]):
            QMessageBox.warning(self, "Campos Vacíos", "Todos los campos son obligatorios.")
            return

        try:
            numero_anho = int(numero_str)
        except ValueError:
            QMessageBox.warning(self, "Formato Inválido", "El 'Número Año' debe ser un número entero.")
            return

        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            if conn is None:
                return

            cursor = conn.cursor()
            cursor.execute("SELECT codigo FROM anhos WHERE codigo = %s", (codigo,))
            if cursor.fetchone():
                QMessageBox.warning(self, "Código Existente", f"El código '{codigo}' ya existe.")
                return

            insert_query = """
            INSERT INTO anhos (codigo, nombre, numero_anho, descripcion)
            VALUES (%s, %s, %s, %s);
            """
            cursor.execute(insert_query, (codigo, nombre, numero_anho, descripcion))
            conn.commit()
            QMessageBox.information(self, "Registro Exitoso", f"El año '{nombre}' ha sido registrado.")
            self.clear_fields()
            self.load_anhos_data()
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo registrar el año:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def borrar_anho_seleccionado(self):
        selected_items = self.tabla_anhos.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Sin Selección", "Por favor, selecciona un año para borrar.")
            return
        
        # El código está en la primera columna (índice 0)
        codigo_anho = selected_items[0].text() 
        nombre_anho = self.tabla_anhos.item(selected_items[0].row(), 1).text() # Nombre en la segunda columna

        reply = QMessageBox.question(self, "Confirmar Borrado",
                                     f"¿Seguro que quieres borrar el año '{nombre_anho}' (Código: {codigo_anho})?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = None
            cursor = None
            try:
                conn = self.get_connection()
                if conn is None:
                    return

                cursor = conn.cursor()
                delete_query = "DELETE FROM anhos WHERE codigo = %s;"
                cursor.execute(delete_query, (codigo_anho,))
                conn.commit()
                if cursor.rowcount > 0:
                    self.clear_fields()
                    self.load_anhos_data()
                else:
                    QMessageBox.warning(self, "No Encontrado", f"No se encontró el año con código '{codigo_anho}'.")
            except psycopg2.Error as e:
                if conn:
                    conn.rollback()
                QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo eliminar el registro:\n{e}")
            except Exception as e:
                QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

    def actualizar_anho_seleccionado(self):
        codigo = self.entry_codigo.text().strip().upper() # El código está deshabilitado, se usa el cargado
        nombre = self.entry_nombre.text().strip()
        numero_str = self.entry_numero.text().strip()
        descripcion = self.entry_descripcion.toPlainText().strip()

        if not all([codigo, nombre, numero_str, descripcion]):
            QMessageBox.warning(self, "Campos Vacíos", "Todos los campos son obligatorios para actualizar.")
            return

        try:
            numero_anho = int(numero_str)
        except ValueError:
            QMessageBox.warning(self, "Formato Inválido", "El 'Número Año' debe ser un número entero.")
            return

        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            if conn is None:
                return

            cursor = conn.cursor()
            update_query = """
            UPDATE anhos SET
                nombre = %s, numero_anho = %s, descripcion = %s
            WHERE codigo = %s;
            """
            cursor.execute(update_query, (nombre, numero_anho, descripcion, codigo))
            conn.commit()
            if cursor.rowcount > 0:
                QMessageBox.information(self, "Actualización Exitosa", f"El año '{nombre}' ha sido actualizado.")
                self.clear_fields()
                self.load_anhos_data()
            else:
                QMessageBox.warning(self, "No Encontrado", f"No se encontró el año con código '{codigo}' para actualizar.")
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"No se pudo actualizar el año:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ha ocurrido un error inesperado: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def actualizar_indicadores(self):
        """Actualiza las etiquetas de indicadores contando las filas de la tabla."""
        total_filas = self.tabla_anhos.rowCount()
        self.label_indicador_total.setText(f"Total de años registrados: {total_filas}")

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


# --- Funciones de Configuración de Base de Datos (Fuera de la clase AnoEscolarApp) ---
# Estas funciones son para la configuración inicial de tu base de datos PostgreSQL.
# Se recomienda ejecutarlas una única vez para preparar el entorno.
# NO DEBEN SER PARTE DEL FLUJO NORMAL DE LA APLICACIÓN.

def setup_database_anhos(db_config_for_setup):
    """
    Crea la tabla 'anhos' en la base de datos si no existe.
    Utiliza la configuración de la base de datos proporcionada.
    """
    conn_postgres = None
    cursor_postgres = None
    try:
        # 1. Conectar a la base de datos 'postgres' (o una con permisos de superusuario)
        # para crear la base de datos de la aplicación si no existe.
        db_name = db_config_for_setup.get('database', 'sigme_db') # Usar 'sigme_db' como default
        user_for_setup = db_config_for_setup.get('user', 'postgres')
        password_for_setup = db_config_for_setup.get('password', '123456') # ¡IMPORTANTE! Reemplaza con tu contraseña real

        conn_postgres = psycopg2.connect(
            host=db_config_for_setup.get('host', 'localhost'),
            database='postgres', # Conectar a la DB por defecto 'postgres'
            user=user_for_setup,
            password=password_for_setup,
            port=db_config_for_setup.get('port', '5432')
        )
        conn_postgres.autocommit = True # Necesario para CREATE DATABASE
        cursor_postgres = conn_postgres.cursor()

        try:
            cursor_postgres.execute(f"CREATE DATABASE {db_name};")
            print(f"Database '{db_name}' created successfully.")
        except psycopg2.errors.DuplicateDatabase:
            print(f"Database '{db_name}' already exists.")
        except psycopg2.Error as e:
            print(f"Error creating database '{db_name}': {e}")
            # No re-raise, intentar continuar si el error es solo por duplicidad
        
    except psycopg2.Error as e:
        print(f"Error de conexión inicial a 'postgres' para setup: {e}")
        return # Salir si no se puede conectar a 'postgres'
    finally:
        if cursor_postgres:
            cursor_postgres.close()
        if conn_postgres:
            conn_postgres.close()

    # 2. Conectar a la base de datos de la aplicación para crear la tabla 'anhos'.
    # Usar la misma configuración de db_config_for_setup para la conexión final
    conn_app_db = None
    cursor_app_db = None
    try:
        conn_app_db = psycopg2.connect(**db_config_for_setup)
        cursor_app_db = conn_app_db.cursor() # Cursor normal para DDL/DML

        sql = """
        CREATE TABLE IF NOT EXISTS anhos (
            codigo VARCHAR(10) PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            numero_anho INTEGER NOT NULL,
            descripcion TEXT,
            nivel_educativo VARCHAR(50) DEFAULT 'Media General',
            activo BOOLEAN DEFAULT TRUE
        );
        """
        cursor_app_db.execute(sql)
        conn_app_db.commit()
        print("Table 'anhos' checked/created successfully.")
    except psycopg2.Error as e:
        print(f"Error setting up 'anhos' table in '{db_name}': {e}")
        if conn_app_db:
            conn_app_db.rollback()
    finally:
        if cursor_app_db:
            cursor_app_db.close()
        if conn_app_db:
            conn_app_db.close()
