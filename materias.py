import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QMessageBox, 
                             QDialog, QFormLayout, QTextEdit, QSpinBox,
                             QHeaderView, QFrame, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal # Importar pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

# --- Definición de la Paleta de Colores (Duplicada para autocontención, idealmente centralizar) ---
COLOR_LIGHT_GRAYISH_BLUE = "#b3cbdc"
COLOR_DEEP_DARK_BLUE = "#1c355b"
COLOR_OFF_WHITE = "#e4eaf4"
COLOR_MEDIUM_GRAYISH_BLUE = "#7089a7"
COLOR_ERROR_RED = "#e74c3c"
COLOR_SUCCESS_GREEN = "#2ecc71"
COLOR_MAIN_BACKGROUND = "#CBDCE1"
COLOR_ACCENT_BLUE = "#5B9BD5"
COLOR_WHITE = "#FFFFFF"
COLOR_DARK_TEXT = "#333333"
COLOR_PRIMARY_DARK_BLUE = "#1B375C"


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
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor) # Usar RealDictCursor por defecto
            return True
        except psycopg2.Error as e:
            print(f"Error conectando a la base de datos: {e}")
            self.connection = None # Asegurarse de que la conexión sea None si falla
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

class MateriaDialog(QDialog):
    """Diálogo para agregar/editar materias"""
    
    def __init__(self, parent=None, materia_data=None):
        super().__init__(parent)
        self.materia_data = materia_data
        self.setup_ui()
        self.apply_styles()
        
        if materia_data:
            self.load_data()
    
    def setup_ui(self):
        self.setWindowTitle("Agregar Materia" if not self.materia_data else "Editar Materia")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # Formulario
        form_layout = QFormLayout()
        
        self.nombre_edit = QLineEdit()
        self.nombre_edit.setPlaceholderText("Ej: Matemática")
        form_layout.addRow("Nombre:", self.nombre_edit)
        
        self.codigo_edit = QLineEdit()
        self.codigo_edit.setPlaceholderText("Ej: MAT")
        form_layout.addRow("Código:", self.codigo_edit)
        
        self.descripcion_edit = QTextEdit()
        self.descripcion_edit.setPlaceholderText("Descripción de la materia...")
        self.descripcion_edit.setMaximumHeight(100)
        form_layout.addRow("Descripción:", self.descripcion_edit)
        
        self.horas_semanales_spin = QSpinBox()
        self.horas_semanales_spin.setRange(1, 10)
        self.horas_semanales_spin.setValue(4)
        form_layout.addRow("Horas Semanales:", self.horas_semanales_spin)
        
        layout.addLayout(form_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.guardar_btn = QPushButton("Guardar")
        self.guardar_btn.clicked.connect(self.accept)
        
        self.cancelar_btn = QPushButton("Cancelar")
        self.cancelar_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.guardar_btn)
        button_layout.addWidget(self.cancelar_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def apply_styles(self):
        """Aplica estilos azul y blanco al diálogo"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_OFF_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            QLabel {{
                color: {COLOR_DEEP_DARK_BLUE};
                font-weight: bold;
            }}
            QLineEdit, QTextEdit, QSpinBox {{
                background-color: {COLOR_WHITE};
                border: 2px solid {COLOR_ACCENT_BLUE};
                border-radius: 5px;
                padding: 5px;
                color: {COLOR_DARK_TEXT};
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
                border-color: {COLOR_PRIMARY_DARK_BLUE};
                background-color: {COLOR_OFF_WHITE};
            }}
            QPushButton {{
                background-color: {COLOR_ACCENT_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_DEEP_DARK_BLUE};
            }}
        """)
    
    def load_data(self):
        """Carga los datos de la materia para edición"""
        if self.materia_data:
            # Asumiendo que materia_data es un diccionario de RealDictCursor
            self.nombre_edit.setText(self.materia_data['nombre'])
            self.codigo_edit.setText(self.materia_data['codigo'])
            self.descripcion_edit.setText(self.materia_data['descripcion'] or "")
            self.horas_semanales_spin.setValue(self.materia_data['horas_semanales'])
    
    def get_data(self):
        """Retorna los datos del formulario"""
        return {
            'nombre': self.nombre_edit.text().strip(),
            'codigo': self.codigo_edit.text().strip().upper(),
            'descripcion': self.descripcion_edit.toPlainText().strip(),
            'horas_semanales': self.horas_semanales_spin.value()
        }
    
    def validate_data(self):
        """Valida los datos del formulario"""
        data = self.get_data()
        
        if not data['nombre']:
            QMessageBox.warning(self, "Error", "El nombre de la materia es obligatorio")
            return False
        
        if not data['codigo']:
            QMessageBox.warning(self, "Error", "El código de la materia es obligatorio")
            return False
        
        if len(data['codigo']) > 10:
            QMessageBox.warning(self, "Error", "El código no puede tener más de 10 caracteres")
            return False
        
        return True
    
    def accept(self):
        if self.validate_data():
            super().accept()

class MateriasWidget(QMainWindow): # Cambiado de QWidget a QMainWindow
    """Widget principal para gestionar materias"""

    # Señal personalizada que se emite cuando el widget se cierra
    closed = pyqtSignal() 
    
    def __init__(self, db_config, user_data): # Recibir db_config y user_data
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db = DatabaseConnection(self.db_config) # Pasar db_config a DatabaseConnection
        self.init_db_connection_and_table() # Nueva función para manejar la conexión y creación de tabla
        self.setup_ui()
        self.apply_styles()
        
        # Cargar materias solo si la conexión fue exitosa
        if self.db.connection and not self.db.connection.closed:
            self.load_materias()
        else:
            self.mostrar_mensaje_sin_bd() # Mostrar mensaje si no hay conexión
        
        # Mostrar en pantalla completa
        self.showFullScreen()

    def init_db_connection_and_table(self):
        """
        Intenta conectar a la base de datos y crear la tabla 'materias' si no existe.
        """
        print("Iniciando conexión y configuración de tabla 'materias'...")
        if not self.db.connect():
            print("Fallo la conexión inicial a la base de datos.")
            return False

        print("Conexión exitosa, verificando/creando tabla 'materias'...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS materias (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL UNIQUE,
            codigo VARCHAR(10) NOT NULL UNIQUE,
            descripcion TEXT,
            horas_semanales INTEGER NOT NULL DEFAULT 4,
            activo BOOLEAN DEFAULT TRUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        if self.db.execute_query(create_table_query):
            print("Tabla 'materias' verificada/creada correctamente.")
            return True
        else:
            print("Error al crear la tabla 'materias'.")
            self.db.disconnect() # Desconectar si falla la creación de tabla
            return False
    
    def mostrar_mensaje_sin_bd(self):
        """Muestra un mensaje cuando no hay conexión a la base de datos"""
        self.info_label.setText("Sin conexión a base de datos - No se pueden cargar/gestionar materias.")
        self.agregar_btn.setEnabled(False)
        self.editar_btn.setEnabled(False)
        self.eliminar_btn.setEnabled(False)
        self.cargar_predefinidas_btn.setEnabled(False)
        # Ocultar el botón de configurar BD si la conexión ya viene de la ventana principal
        # self.config_btn.hide() # Si no quieres que el usuario final pueda reconfigurar la BD desde aquí
    
    def setup_ui(self):
        self.setWindowTitle("Gestión de Materias") # Establecer título de la ventana
        # self.setGeometry(150, 150, 1000, 700) # Ya no es necesario si se usa showFullScreen()

        central_widget = QWidget() # Crear un QWidget para ser el central widget
        self.setCentralWidget(central_widget) # Establecerlo como central widget
        layout = QVBoxLayout(central_widget) # Aplicar el layout al central widget
        
        # Título
        title_label = QLabel("Gestión de Materias")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)
        
        # Barra de herramientas
        toolbar_layout = QHBoxLayout()
        
        self.buscar_edit = QLineEdit()
        self.buscar_edit.setPlaceholderText("Buscar materia...")
        self.buscar_edit.textChanged.connect(self.buscar_materias)
        toolbar_layout.addWidget(self.buscar_edit)
        
        self.agregar_btn = QPushButton("Agregar Materia")
        self.agregar_btn.clicked.connect(self.agregar_materia)
        toolbar_layout.addWidget(self.agregar_btn)
        
        self.editar_btn = QPushButton("Editar")
        self.editar_btn.clicked.connect(self.editar_materia)
        self.editar_btn.setEnabled(False)
        toolbar_layout.addWidget(self.editar_btn)
        
        self.eliminar_btn = QPushButton("Eliminar")
        self.eliminar_btn.clicked.connect(self.eliminar_materia)
        self.eliminar_btn.setEnabled(False)
        toolbar_layout.addWidget(self.eliminar_btn)
        
        self.cargar_predefinidas_btn = QPushButton("Cargar Materias Predefinidas")
        self.cargar_predefinidas_btn.clicked.connect(self.cargar_materias_predefinidas)
        toolbar_layout.addWidget(self.cargar_predefinidas_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Tabla de materias
        self.tabla_materias = QTableWidget()
        self.tabla_materias.setColumnCount(5)
        self.tabla_materias.setHorizontalHeaderLabels(["ID", "Nombre", "Código", "Descripción", "Horas Semanales"])
        
        # Configurar tabla
        header = self.tabla_materias.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.tabla_materias.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_materias.itemSelectionChanged.connect(self.on_selection_changed)
        self.tabla_materias.itemDoubleClicked.connect(self.editar_materia)
        
        layout.addWidget(self.tabla_materias)
        
        # Información
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_frame.setObjectName("infoFrame")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel("Total de materias: 0")
        self.info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.info_label)
        
        info_frame.setLayout(info_layout)
        layout.addWidget(info_frame)

        # Botón para volver al menú
        self.back_button = QPushButton("Volver al Menú")
        self.back_button.setObjectName('backButton')
        self.back_button.clicked.connect(self.go_back_to_menu)
        layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignRight)
        
    def apply_styles(self):
        """Aplica estilos azul y blanco al widget"""
        self.setStyleSheet(f"""
            QMainWindow {{ 
                background-color: {COLOR_MAIN_BACKGROUND};
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            
            #titleLabel {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                color: {COLOR_WHITE};
                padding: 15px;
                border-radius: 10px;
                margin: 10px;
            }}
            
            QLineEdit {{
                background-color: {COLOR_WHITE};
                border: 2px solid {COLOR_ACCENT_BLUE};
                border-radius: 5px;
                padding: 8px;
                color: {COLOR_DARK_TEXT};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY_DARK_BLUE};
                background-color: {COLOR_OFF_WHITE};
            }}
            
            QPushButton {{
                background-color: {COLOR_ACCENT_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_DEEP_DARK_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
            }}
            
            QTableWidget {{
                background-color: {COLOR_WHITE};
                alternate-background-color: {COLOR_OFF_WHITE};
                selection-background-color: {COLOR_ACCENT_BLUE};
                selection-color: {COLOR_WHITE};
                gridline-color: {COLOR_LIGHT_GRAYISH_BLUE};
                border: 2px solid {COLOR_ACCENT_BLUE};
                border-radius: 5px;
            }}
            
            QTableWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
            }}
            
            QTableWidget::item:selected {{
                background-color: {COLOR_ACCENT_BLUE};
                color: {COLOR_WHITE};
            }}
            
            QHeaderView::section {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                color: {COLOR_WHITE};
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
            
            #infoFrame {{
                background-color: {COLOR_OFF_WHITE};
                border: 2px solid {COLOR_ACCENT_BLUE};
                border-radius: 5px;
                margin: 5px;
            }}
            
            #infoLabel {{
                color: {COLOR_DEEP_DARK_BLUE};
                font-weight: bold;
                padding: 10px;
            }}
            #backButton {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 20px;
            }}
            #backButton:hover {{
                background-color: #162a4d;
            }}
            #backButton:pressed {{
                background-color: #10203a;
            }}
        """)
    
    def load_materias(self):
        """Carga las materias desde la base de datos y las muestra en la tabla."""
        materias = self.db.fetch_all("SELECT id, nombre, codigo, descripcion, horas_semanales FROM materias WHERE activo = TRUE ORDER BY nombre ASC")
        self.tabla_materias.setRowCount(len(materias))
        for row_idx, materia in enumerate(materias):
            self.tabla_materias.setItem(row_idx, 0, QTableWidgetItem(str(materia['id'])))
            self.tabla_materias.setItem(row_idx, 1, QTableWidgetItem(materia['nombre']))
            self.tabla_materias.setItem(row_idx, 2, QTableWidgetItem(materia['codigo']))
            self.tabla_materias.setItem(row_idx, 3, QTableWidgetItem(materia['descripcion'] or ""))
            self.tabla_materias.setItem(row_idx, 4, QTableWidgetItem(str(materia['horas_semanales'])))
        self.info_label.setText(f"Total de materias: {len(materias)}")
        self.on_selection_changed() # Actualizar estado de botones

    def agregar_materia(self):
        """Abre el diálogo para agregar una nueva materia."""
        dialog = MateriaDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            query = """
            INSERT INTO materias (nombre, codigo, descripcion, horas_semanales)
            VALUES (%s, %s, %s, %s);
            """
            if self.db.execute_query(query, (data['nombre'], data['codigo'], data['descripcion'], data['horas_semanales'])):
                QMessageBox.information(self, "Éxito", "Materia agregada correctamente.")
                self.load_materias()
            else:
                QMessageBox.critical(self, "Error", "No se pudo agregar la materia. El código o nombre pueden ya existir.")
    
    def editar_materia(self):
        """Abre el diálogo para editar la materia seleccionada."""
        selected_rows = self.tabla_materias.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Seleccione una materia para editar.")
            return
        
        row = selected_rows[0].row()
        materia_id = int(self.tabla_materias.item(row, 0).text())
        
        # Obtener todos los datos de la materia para pasarlos al diálogo de edición
        materias = self.db.fetch_all("SELECT id, nombre, codigo, descripcion, horas_semanales FROM materias WHERE id = %s", (materia_id,))
        if not materias:
            QMessageBox.critical(self, "Error", "No se encontró la materia seleccionada.")
            return
        
        materia_data = materias[0] # RealDictCursor devuelve un diccionario
        
        dialog = MateriaDialog(self, materia_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            query = """
            UPDATE materias
            SET nombre = %s, codigo = %s, descripcion = %s, horas_semanales = %s
            WHERE id = %s;
            """
            if self.db.execute_query(query, (data['nombre'], data['codigo'], data['descripcion'], data['horas_semanales'], materia_id)):
                QMessageBox.information(self, "Éxito", "Materia actualizada correctamente.")
                self.load_materias()
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar la materia. El código o nombre pueden ya existir.")
                
    def eliminar_materia(self):
        """Elimina la materia seleccionada (eliminación lógica)"""
        selected_rows = self.tabla_materias.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Seleccione una materia para eliminar.")
            return
        
        row = selected_rows[0].row()
        materia_id = int(self.tabla_materias.item(row, 0).text())
        materia_nombre = self.tabla_materias.item(row, 1).text()
        
        reply = QMessageBox.question(self, "Confirmar Eliminación", 
                                     f"¿Está seguro de que desea eliminar la materia '{materia_nombre}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            query = "UPDATE materias SET activo = FALSE WHERE id = %s"
            
            if self.db.execute_query(query, (materia_id,)):
                QMessageBox.information(self, "Éxito", "Materia eliminada correctamente.")
                self.load_materias()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar la materia.")

    def buscar_materias(self):
        """Filtra las materias en la tabla según el texto de búsqueda."""
        search_text = self.buscar_edit.text().strip().lower()
        for row in range(self.tabla_materias.rowCount()):
            nombre_item = self.tabla_materias.item(row, 1) # Columna de Nombre
            codigo_item = self.tabla_materias.item(row, 2) # Columna de Código
            
            if nombre_item and codigo_item:
                nombre = nombre_item.text().lower()
                codigo = codigo_item.text().lower()
                
                if search_text in nombre or search_text in codigo:
                    self.tabla_materias.setRowHidden(row, False)
                else:
                    self.tabla_materias.setRowHidden(row, True)

    def cargar_materias_predefinidas(self):
        """Carga un conjunto de materias predefinidas si la tabla está vacía."""
        # Verificar si la tabla ya tiene materias
        count_query = "SELECT COUNT(*) FROM materias WHERE activo = TRUE;"
        count_result = self.db.fetch_all(count_query)
        
        if count_result and count_result[0]['count'] > 0:
            QMessageBox.information(self, "Información", "La tabla de materias ya contiene datos activos. No se cargarán materias predefinidas.")
            return

        reply = QMessageBox.question(self, "Cargar Materias Predefinidas",
                                     "¿Desea cargar un conjunto de materias predefinidas en la base de datos?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            materias_predefinidas = [
                ("Castellano", "CAST", "Lengua y Literatura Castellana", 5),
                ("Inglés", "ING", "Idioma Inglés", 3),
                ("Matemática", "MAT", "Matemática", 5),
                ("Educación Física", "EF", "Educación Física", 2),
                ("Física", "FIS", "Física", 4),
                ("Química", "QUIM", "Química", 4),
                ("Biología", "BIO", "Biología", 4),
                ("Ciencias de la Tierra", "CT", "Ciencias de la Tierra", 3),
                ("Geografía Historia y Ciudadanía", "GHC", "Geografía Historia y Ciudadanía", 4),
                ("Formación para la Soberanía", "FS", "Formación para la Soberanía Nacional", 2),
                ("Ciencias Naturales", "CN", "Ciencias Naturales", 4),
                ("Arte y Patrimonio", "AP", "Arte y Patrimonio", 2),
                ("Orientación y Convivencia", "OC", "Orientación y Convivencia", 2),
                ("CRP", "CRP", "Creando, Recreando y Produciendo", 3)
            ]
            
            insert_query = """
            INSERT INTO materias (nombre, codigo, descripcion, horas_semanales, activo)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (nombre) DO UPDATE SET activo = TRUE; -- Activar si ya existe
            """
            
            success_count = 0
            for materia in materias_predefinidas:
                if self.db.execute_query(insert_query, materia):
                    success_count += 1
            
            if success_count > 0:
                QMessageBox.information(self, "Éxito", f"Se cargaron {success_count} materias predefinidas correctamente.")
                self.load_materias()
            else:
                QMessageBox.warning(self, "Advertencia", "No se pudo cargar ninguna materia predefinida o ya existían todas y estaban activas.")

    def on_selection_changed(self):
        """Habilita/deshabilita los botones de editar y eliminar según la selección en la tabla."""
        has_selection = len(self.tabla_materias.selectionModel().selectedRows()) > 0
        self.editar_btn.setEnabled(has_selection)
        self.eliminar_btn.setEnabled(has_selection)

    def go_back_to_menu(self):
        """
        Cierra esta ventana y emite una señal para que el menú principal se muestre.
        """
        self.close() # Cierra el QMainWindow actual
        # La señal 'closed' ya se emite en closeEvent, que es llamado por self.close()

    def closeEvent(self, event):
        """
        Sobrescribe el evento de cierre para desconectar la base de datos y emitir la señal.
        """
        self.db.disconnect()
        self.closed.emit() # Emitir la señal también al cerrar con la 'X'
        super().closeEvent(event)

# Función para configurar estilos globales de QMessageBox
def setup_message_box_styles():
    """Configura estilos globales para los QMessageBox"""
    QApplication.instance().setStyleSheet(f"""
        QMessageBox {{
            background-color: {COLOR_OFF_WHITE};
            color: {COLOR_DEEP_DARK_BLUE};
        }}
        QMessageBox QLabel {{
            color: {COLOR_DEEP_DARK_BLUE};
        }}
        QMessageBox QPushButton {{
            background-color: {COLOR_ACCENT_BLUE};
            color: {COLOR_WHITE};
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
            min-width: 80px;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {COLOR_PRIMARY_DARK_BLUE};
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {COLOR_DEEP_DARK_BLUE};
        }}
        QMessageBox QPushButton:default {{
            background-color: {COLOR_PRIMARY_DARK_BLUE};
        }}
        QMessageBox QPushButton:default:hover {{
            background-color: {COLOR_DEEP_DARK_BLUE};
        }}
    """)