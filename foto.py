import sys
import psycopg2
from psycopg2 import Error
from psycopg2.extras import RealDictCursor
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QLineEdit,
                             QMessageBox, QFileDialog, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QBuffer, QIODevice
from PyQt6.QtGui import QFont, QPixmap, QImageReader
import os
import mimetypes # Para determinar el tipo MIME del archivo

# --- Definición de la Paleta de Colores (Centralizada) ---
PRIMARY_COLOR = '#1c355b' # Azul oscuro fuerte
ACCENT_COLOR = '#7089a7'  # Azul grisáceo medio
LIGHT_BACKGROUND = '#e4eaf4' # Azul muy claro para fondos
TEXT_COLOR = '#333333' # Gris oscuro para texto
WHITE_COLOR = '#FFFFFF'
SUCCESS_COLOR = '#16a34a' # Verde
ERROR_COLOR = '#dc2626'   # Rojo
FONT_FAMILY = 'Arial'

# --- Clase para Manejo de la Base de Datos (Reutilizada) ---
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


# --- Clase Principal del Módulo de Carga de Imágenes ---
class ImageUploaderApp(QMainWindow):
    closed = pyqtSignal() # Señal para indicar que la ventana se ha cerrado

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db = DatabaseConnection(self.db_config)
        self.selected_file_path = None

        self.init_db_connection_and_table()
        self.init_ui()
        self.apply_styles()
        self.showFullScreen()

    def init_db_connection_and_table(self):
        """
        Intenta conectar a la base de datos y crear la tabla 'imagenes' si no existe.
        """
        print("Iniciando conexión y configuración de tabla 'imagenes'...")
        if not self.db.connect():
            print("Fallo la conexión inicial a la base de datos.")
            return False

        print("Conexión exitosa, verificando/creando tabla 'imagenes'...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS imagenes (
            id SERIAL PRIMARY KEY,
            nombre_archivo VARCHAR(255) NOT NULL,
            mime_type VARCHAR(50) NOT NULL,
            datos_imagen BYTEA NOT NULL, -- Para almacenar los datos binarios de la imagen
            fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        if self.db.execute_query(create_table_query):
            print("Tabla 'imagenes' verificada/creada correctamente.")
            return True
        else:
            print("Error al crear la tabla 'imagenes'.")
            self.db.disconnect()
            return False

    def init_ui(self):
        self.setWindowTitle("SIGME - Subir Imágenes a DB")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- Título Principal y Botón Volver al Menú ---
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {PRIMARY_COLOR}; border-radius: 5px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel("MÓDULO DE SUBIDA DE IMÁGENES")
        title_label.setFont(QFont(FONT_FAMILY, 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {WHITE_COLOR}; background-color: {PRIMARY_COLOR};")
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.back_to_menu_button = QPushButton('Volver al Menú')
        self.back_to_menu_button.setObjectName('backButton')
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        header_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(header_frame)

        # --- Contenido Principal ---
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Sección de selección de archivo
        file_selection_layout = QHBoxLayout()
        self.select_file_button = QPushButton("Seleccionar Imagen")
        self.select_file_button.setObjectName("actionButton")
        self.select_file_button.clicked.connect(self.select_image_file)
        file_selection_layout.addWidget(self.select_file_button)

        self.file_path_label = QLineEdit("Ningún archivo seleccionado")
        self.file_path_label.setReadOnly(True)
        self.file_path_label.setObjectName("readOnlyField")
        file_selection_layout.addWidget(self.file_path_label)
        content_layout.addLayout(file_selection_layout)

        # Botón de subir imagen
        self.upload_button = QPushButton("⬆️ Subir Imagen a la Base de Datos")
        self.upload_button.setObjectName("uploadButton")
        self.upload_button.clicked.connect(self.upload_image)
        self.upload_button.setEnabled(False) # Deshabilitado hasta que se seleccione un archivo
        content_layout.addWidget(self.upload_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Área para mostrar la imagen subida (opcional, para verificación)
        self.image_display_label = QLabel("La imagen subida aparecerá aquí (si se recupera de la DB)")
        self.image_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display_label.setFixedSize(300, 200) # Tamaño fijo para el display
        self.image_display_label.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {ACCENT_COLOR};
                border-radius: 8px;
                background-color: {WHITE_COLOR};
                color: {TEXT_COLOR};
            }}
        """)
        content_layout.addWidget(self.image_display_label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(content_frame)
        main_layout.addStretch()

        # Barra de estado
        self.status_bar = QLabel("Listo para seleccionar una imagen.")
        self.status_bar.setStyleSheet(f"background-color: {LIGHT_BACKGROUND}; color: {TEXT_COLOR}; border-top: 1px solid {ACCENT_COLOR}; padding: 5px;")
        self.status_bar.setFont(QFont(FONT_FAMILY, 9))
        main_layout.addWidget(self.status_bar)

    def apply_styles(self):
        """Aplica los estilos CSS a los widgets de la aplicación."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {LIGHT_BACKGROUND};
            }}
            QFrame#contentFrame {{
                background-color: {WHITE_COLOR};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 8px;
                padding: 10px;
            }}
            QLabel {{
                color: {PRIMARY_COLOR};
                font-weight: normal;
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QLineEdit#readOnlyField {{
                background-color: {LIGHT_BACKGROUND};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
                color: {TEXT_COLOR};
                font-family: '{FONT_FAMILY}', sans-serif;
            }}
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: {WHITE_COLOR};
                border: none;
                border-radius: 8px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 120px;
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
            QPushButton#uploadButton {{
                background-color: {SUCCESS_COLOR};
                color: {WHITE_COLOR};
                border: none;
                border-radius: 10px;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 16px;
                min-width: 200px;
            }}
            QPushButton#uploadButton:hover {{
                background-color: #1a8a40;
            }}
            QPushButton#uploadButton:pressed {{
                background-color: #106020;
            }}
            QPushButton#uploadButton:disabled {{
                background-color: #a3d9b8;
                color: #ffffff;
            }}
        """)

    def select_image_file(self):
        """Abre un diálogo de archivo para seleccionar una imagen."""
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Imágenes (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setViewMode(QFileDialog.ViewMode.List)
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.selected_file_path = selected_files[0]
                self.file_path_label.setText(os.path.basename(self.selected_file_path))
                self.upload_button.setEnabled(True)
                self.status_bar.setText(f"Archivo seleccionado: {os.path.basename(self.selected_file_path)}")
                self.image_display_label.clear() # Limpiar display anterior
                self.image_display_label.setText("La imagen subida aparecerá aquí (si se recupera de la DB)")
            else:
                self.selected_file_path = None
                self.file_path_label.setText("Ningún archivo seleccionado")
                self.upload_button.setEnabled(False)
                self.status_bar.setText("Selección de archivo cancelada.")

    def upload_image(self):
        """Sube la imagen seleccionada a la base de datos."""
        if not self.selected_file_path:
            QMessageBox.warning(self, "Error", "Por favor, seleccione un archivo de imagen primero.")
            return

        try:
            with open(self.selected_file_path, 'rb') as f:
                image_data = f.read()
            
            file_name = os.path.basename(self.selected_file_path)
            mime_type, _ = mimetypes.guess_type(self.selected_file_path)
            if not mime_type or not mime_type.startswith('image/'):
                QMessageBox.warning(self, "Tipo de Archivo Inválido", "El archivo seleccionado no es una imagen válida.")
                return

            # Modificado para usar self.db.execute_query
            query = """
            INSERT INTO imagenes (nombre_archivo, mime_type, datos_imagen)
            VALUES (%s, %s, %s) RETURNING id;
            """
            # execute_query ya maneja la conexión y el commit/rollback
            # Necesitamos obtener el ID de retorno, por lo que usaremos fetch_one después de execute_query
            # o una transacción manual si execute_query no soporta RETURNING directamente
            # Para simplificar, vamos a modificar execute_query para que devuelva el cursor si es necesario,
            # o hacer la inserción directamente aquí con un nuevo cursor.
            # La forma más limpia es que execute_query pueda devolver resultados si la consulta es RETURNING.
            # Por ahora, para el ID de retorno, vamos a hacer la operación manualmente para esta función.
            
            # --- Inicio de la corrección del error ---
            conn = self.db.connection # Acceder a la conexión existente
            if not conn or conn.closed: # Si la conexión no está activa, intentar reconectar
                if not self.db.connect():
                    QMessageBox.critical(self, "Error de Conexión", "No hay conexión activa a la base de datos.")
                    return

            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (file_name, mime_type, psycopg2.Binary(image_data)))
                    uploaded_id = cursor.fetchone()[0] # Obtener el ID de la imagen recién insertada
                    conn.commit() # Confirmar la transacción
                    QMessageBox.information(self, "Éxito", f"Imagen '{file_name}' subida correctamente con ID: {uploaded_id}")
                    self.status_bar.setText(f"Imagen '{file_name}' subida. ID: {uploaded_id}")
                    self.display_image_from_db(uploaded_id) # Mostrar la imagen recién subida
                    self.selected_file_path = None # Limpiar la selección después de subir
                    self.file_path_label.setText("Ningún archivo seleccionado")
                    self.upload_button.setEnabled(False)
            except psycopg2.Error as e:
                conn.rollback() # Revertir la transacción en caso de error
                QMessageBox.critical(self, "Error de Base de Datos", f"Error al subir la imagen: {e}")
            # --- Fin de la corrección del error ---

        except FileNotFoundError:
            QMessageBox.critical(self, "Error de Archivo", "El archivo seleccionado no fue encontrado.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error inesperado: {e}")

    def display_image_from_db(self, image_id):
        """
        Recupera una imagen de la base de datos por su ID y la muestra en un QLabel.
        """
        query = "SELECT datos_imagen, mime_type FROM imagenes WHERE id = %s;"
        image_record = self.db.fetch_one(query, (image_id,))

        if image_record:
            image_data = bytes(image_record['datos_imagen']) # Convertir de psycopg2.Binary a bytes
            mime_type = image_record['mime_type']

            pixmap = QPixmap()
            # Usar QImageReader para cargar la imagen desde los bytes
            buffer = QBuffer()
            buffer.setData(image_data)
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            
            reader = QImageReader(buffer, mime_type.encode('utf-8'))
            image = reader.read()
            
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                # Escalar la imagen para que quepa en el QLabel
                scaled_pixmap = pixmap.scaled(self.image_display_label.size(), 
                                              Qt.AspectRatioMode.KeepAspectRatio, 
                                              Qt.TransformationMode.SmoothTransformation)
                self.image_display_label.setPixmap(scaled_pixmap)
                self.image_display_label.setText("") # Borrar texto si la imagen se muestra
            else:
                self.image_display_label.setText("No se pudo cargar la imagen desde la DB.")
                print(f"Error: No se pudo cargar QImage desde los datos binarios para ID {image_id}.")
        else:
            self.image_display_label.setText("Imagen no encontrada en la DB.")
            print(f"Error: Imagen con ID {image_id} no encontrada en la base de datos.")


    def go_back_to_menu(self):
        """Cierra esta ventana y emite una señal para que el menú principal se muestre."""
        self.close()

    def closeEvent(self, event):
        """Sobrescribe el evento de cierre para desconectar la base de datos y emitir la señal."""
        self.db.disconnect()
        self.closed.emit()
        super().closeEvent(event)

