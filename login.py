import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import time

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QMessageBox,
                             QFrame, QCheckBox, QHeaderView, QComboBox,
                             QGridLayout, QSpacerItem, QSizePolicy, QDialog,
                             QApplication)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap

# Importa GeneralMainWindow desde el nuevo archivo menu_general.py
# Asegúrate de que este archivo exista y contenga la clase GeneralMainWindow
from menu_general import GeneralMainWindow

# --- Definición de la Paleta de Colores ---
COLOR_LIGHT_GRAYISH_BLUE = "#b3cbdc"
COLOR_DEEP_DARK_BLUE = "#1c355b"
COLOR_OFF_WHITE = "#e4eaf4"
COLOR_MEDIUM_GRAYISH_BLUE = "#7089a7"
COLOR_ERROR_RED = "#e74c3c" # Para mensajes de error
COLOR_SUCCESS_GREEN = "#2ecc71" # Para mensajes de éxito

COLOR_MAIN_BACKGROUND = "#CBDCE1" # Fondo principal, actualizado a #CBDCE1
COLOR_ACCENT_BLUE = "#5B9BD5"
COLOR_WHITE = "#FFFFFF"
COLOR_DARK_TEXT = "#333333"

COLOR_BUTTON_HOVER = "#4A8BCD"
COLOR_BUTTON_PRESSED = "#3C7DBA"

COLOR_DISABLED_BG = "#A0C0E0"
COLOR_DISABLED_TEXT = "#6080A0"

COLOR_PRIMARY_DARK_BLUE = "#1B375C"


class LoginWindow(QMainWindow):
    """
    Ventana de login principal de la aplicación.
    Permite a los usuarios ingresar sus credenciales y seleccionar el tipo de acceso.
    También incluye un botón oculto para el registro de nuevos usuarios.
    Toda la lógica de la base de datos para el login está integrada aquí.
    """
    DB_CONFIG_FILE = 'db_connection.conf' # Nombre del archivo de configuración

    def __init__(self):
        super().__init__()
        self.db_config = self._load_db_config()
        self.init_database() # Inicializar la DB con la configuración cargada
        self.current_user = None
        self.last_key_pressed = None # Para la combinación de teclas
        self.init_ui()

    @staticmethod
    def _load_db_config():
        """
        Carga la configuración de la base de datos desde un archivo.
        Si el archivo no existe o está vacío, usa valores por defecto.
        """
        config = {
            'host': 'localhost',
            'database': 'Sigme',
            'user': 'Diego',
            'password': 'Diego-78',
            'port': '5432'
        }
        if os.path.exists(LoginWindow.DB_CONFIG_FILE):
            try:
                with open(LoginWindow.DB_CONFIG_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            except Exception as e:
                print(f"Error al leer el archivo de configuración DB: {e}")
        return config

    @staticmethod
    def _save_db_config(config_data):
        """
        Guarda la configuración actual de la base de datos en un archivo.
        """
        try:
            with open(LoginWindow.DB_CONFIG_FILE, 'w') as f:
                for key, value in config_data.items():
                    f.write(f"{key}={value}\n")
            return True
        except Exception as e:
            print(f"Error al guardar el archivo de configuración DB: {e}")
            return False

    def get_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL.
        Maneja errores de conexión.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            print(f"Error de conexión a la base de datos con la configuración actual: {e}")
            return None

    def init_database(self):
        """
        Inicializa la base de datos: crea las tablas 'usuario' y 'login' si no existen,
        e inserta un usuario administrador por defecto si no hay ninguno.
        """
        conn = self.get_connection()
        if not conn:
            print("No se pudo conectar a la base de datos para la inicialización.")
            return
        
        try:
            with conn.cursor() as cursor:
                # Crear tabla usuario (ajustada para usar VARCHAR en 'estado' y sin FK a personal)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usuario (
                        id SERIAL PRIMARY KEY,
                        codigo_usuario VARCHAR(50) UNIQUE NOT NULL,
                        cedula_personal VARCHAR(20) UNIQUE NOT NULL,
                        rol VARCHAR(50) NOT NULL,
                        clave_hash VARCHAR(64) NOT NULL,
                        estado VARCHAR(20) DEFAULT 'activo',
                        fecha_creacion DATE DEFAULT CURRENT_DATE,
                        ultimo_acceso DATE,
                        intentos_fallidos INTEGER DEFAULT 0,
                        debe_cambiar_clave BOOLEAN DEFAULT TRUE
                    )
                ''')

                # Crear tabla login (historial de accesos) (ajustada para usar VARCHAR en 'tipo_acceso')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS login (
                        id SERIAL PRIMARY KEY,
                        id_usuario INTEGER,
                        fecha DATE,
                        hora TIME,
                        ip_acceso VARCHAR(45),
                        tipo_acceso VARCHAR(100),
                        navegador VARCHAR(100),
                        exitoso BOOLEAN,
                        FOREIGN KEY (id_usuario) REFERENCES usuario (id)
                    )
                ''')

                # Verificar si el usuario administrador por defecto ya existe
                cursor.execute('SELECT COUNT(*) FROM usuario WHERE codigo_usuario = %s', ('admin',))
                admin_exists = cursor.fetchone()[0] > 0

                # Insertar usuario administrador por defecto solo si no existe
                if not admin_exists:
                    # Contraseña por defecto para el admin (¡ALMACENADA EN TEXTO PLANO!)
                    # ADVERTENCIA: Esto es inseguro para producción.
                    default_admin_password = 'admin123' 
                    cursor.execute('''
                        INSERT INTO usuario
                        (codigo_usuario, cedula_personal, rol, clave_hash, estado, debe_cambiar_clave)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', ('admin', '12345678', 'administrador', default_admin_password, 'activo', False))
                    print("Usuario administrador por defecto 'admin' creado.")

            conn.commit()
            print("Base de datos inicializada/verificada correctamente.")
        except psycopg2.errors.DuplicateTable:
            print("Las tablas ya existen, continuando...")
            conn.commit()
        except psycopg2.Error as e:
            print(f"Error al inicializar la base de datos: {e}")
        finally:
            if conn:
                conn.close()

    def authenticate_user(self, codigo_usuario, clave, is_admin_attempt=False):
        """
        Autentica un usuario contra la base de datos.
        Registra intentos fallidos y exitosos.
        """
        conn = self.get_connection()
        if not conn:
            return None

        user_data = None
        log_success = False
        log_type = 'intento fallido'
        user_id_for_log = None
        
        time.sleep(0.1) # Pequeño retardo para mitigar ataques de fuerza bruta

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT id, codigo_usuario, cedula_personal, rol, intentos_fallidos, estado, clave_hash, debe_cambiar_clave
                    FROM usuario
                    WHERE codigo_usuario = %s
                ''', (codigo_usuario,))
                user_record = cursor.fetchone()

                if user_record:
                    user_id_for_log = user_record['id']
                    
                    if user_record['estado'] != 'activo':
                        log_type = 'acceso denegado (cuenta inactiva)'
                        return None

                    # ADVERTENCIA: Comparación de contraseña en texto plano.
                    # ¡Debe usarse hashing de contraseñas en producción!
                    if clave == user_record['clave_hash']:
                        if is_admin_attempt and user_record['rol'] != 'administrador':
                            log_type = 'intento admin con rol incorrecto'
                            self._increment_failed_attempts(cursor, user_id_for_log)
                            conn.commit()
                            return None
                        
                        log_success = True
                        log_type = f'acceso exitoso ({user_record["rol"]})'
                        self._reset_failed_attempts(cursor, user_id_for_log)
                        conn.commit()
                        
                        user_data = {
                            'id': str(user_record['id']),  # Convertir a string
                            'codigo_usuario': user_record['codigo_usuario'],
                            'cedula_personal': str(user_record['cedula_personal']), # Convertir a string
                            'rol': user_record['rol'],
                            'estado': user_record['estado'],
                            'debe_cambiar_clave': user_record['debe_cambiar_clave']
                        }
                    else:
                        log_type = 'credenciales incorrectas'
                        self._increment_failed_attempts(cursor, user_id_for_log)
                        conn.commit()
                        return None
                else:
                    log_type = 'usuario no existe'
                    return None
        except psycopg2.Error as e:
            print(f"Error al autenticar usuario: {e}")
            conn.rollback()
            return None
        finally:
            self._log_access_attempt(user_id_for_log, log_success, log_type)
            if conn:
                conn.close()
        
        return user_data

    def _increment_failed_attempts(self, cursor, user_id):
        """
        Incrementa el contador de intentos fallidos para un usuario.
        """
        cursor.execute('''
            UPDATE usuario
            SET intentos_fallidos = intentos_fallidos + 1
            WHERE id = %s
        ''', (user_id,))

    def _reset_failed_attempts(self, cursor, user_id):
        """
        Reinicia el contador de intentos fallidos y actualiza el último acceso.
        """
        cursor.execute('''
            UPDATE usuario
            SET intentos_fallidos = 0, ultimo_acceso = CURRENT_DATE
            WHERE id = %s
        ''', (user_id,))

    def _log_access_attempt(self, user_id, exitoso, tipo_acceso):
        """
        Registra un intento de acceso en la tabla de historial de login.
        """
        conn = self.get_connection()
        if not conn:
            return
            
        try:
            with conn.cursor() as cursor:
                now = datetime.now()
                ip_address = '127.0.0.1' # Placeholder, obtener la IP real en una app web/de escritorio
                browser_info = 'PyQt6 App' # Placeholder, obtener info real del navegador/cliente

                cursor.execute('''
                    INSERT INTO login
                    (id_usuario, fecha, hora, ip_acceso, tipo_acceso, navegador, exitoso)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (user_id, now.date(), now.time(), ip_address,
                      tipo_acceso, browser_info, exitoso))
                conn.commit()
        except psycopg2.Error as e:
            print(f"Error al registrar acceso: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def init_ui(self):
        """
        Inicializa la interfaz de usuario de la ventana de login.
        """
        self.setWindowTitle('Sistema de Login')
        self.setGeometry(100, 100, 450, 400)
        self.setStyleSheet(self.get_login_styles()) # Aplica estilos QSS

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(25)
        layout.setContentsMargins(50, 40, 50, 40)

        title = QLabel('SISTEMA DE ACCESO')
        title.setObjectName('title')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # --- Botón oculto para registrar nuevo usuario ---
        self.register_user_btn = QPushButton('Registrar Nuevo Usuario (Admin)')
        self.register_user_btn.setObjectName('hiddenRegisterButton')
        self.register_user_btn.clicked.connect(self.show_registration_window)
        layout.addWidget(self.register_user_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.register_user_btn.hide() # Inicialmente oculto

        # Instalar el filtro de eventos en la ventana principal para capturar las pulsaciones de teclas
        self.installEventFilter(self) 

        login_frame = QFrame()
        login_frame.setObjectName('loginFrame')
        login_frame.setContentsMargins(35, 30, 35, 30)

        login_layout = QVBoxLayout(login_frame)
        login_layout.setSpacing(15)

        user_label = QLabel('Usuario:')
        user_label.setObjectName('fieldLabel')
        login_layout.addWidget(user_label)

        self.user_input = QLineEdit()
        self.user_input.setObjectName('inputField')
        self.user_input.setPlaceholderText('Ingrese su usuario')
        login_layout.addWidget(self.user_input)

        pass_label = QLabel('Contraseña:')
        pass_label.setObjectName('fieldLabel')
        login_layout.addWidget(pass_label)

        self.pass_input = QLineEdit()
        self.pass_input.setObjectName('inputField')
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText('Ingrese su contraseña')
        login_layout.addWidget(self.pass_input)

        self.admin_check = QCheckBox('Acceso como Administrador')
        self.admin_check.setObjectName('adminCheck')
        login_layout.addWidget(self.admin_check)

        layout.addWidget(login_frame)

        login_btn = QPushButton('INICIAR SESIÓN')
        login_btn.setObjectName('loginButton')
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)

        self.pass_input.returnPressed.connect(self.login) # Permite iniciar sesión con Enter

        layout.addStretch() # Empuja los elementos hacia arriba

    def eventFilter(self, obj, event):
        """
        Filtra los eventos para detectar la combinación de teclas 'b' + 'r'.
        """
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_B:
                self.last_key_pressed = 'b'
            elif key == Qt.Key.Key_R and self.last_key_pressed == 'b':
                self.register_user_btn.show()
                self.last_key_pressed = None # Resetear la secuencia
            else:
                self.last_key_pressed = None # Resetear si se presiona otra tecla

        return super().eventFilter(obj, event) # Importante llamar al método base

    def get_login_styles(self):
        """
        Define y retorna los estilos QSS para la ventana de login.
        Utiliza la paleta de colores definida.
        """
        return f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 #162a4d); /* Degradado de azul oscuro */
            }}

            #title {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 28px;
                font-weight: bold;
                color: {COLOR_OFF_WHITE}; /* Blanco azulado */
                margin-bottom: 25px;
                text-shadow: 1px 1px 3px rgba(0,0,0,0.4);
            }}

            #hiddenRegisterButton {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 600;
                max-width: 200px;
                margin-bottom: 10px;
            }}
            #hiddenRegisterButton:hover {{
                background-color: {COLOR_DEEP_DARK_BLUE};
            }}
            #hiddenRegisterButton:pressed {{
                background-color: #10203a;
            }}

            #loginFrame {{
                background: rgba(255, 255, 255, 0.98);
                border-radius: 12px;
                border: none;
                box-shadow: 0 8px 20px rgba(0,0,0,0.25);
            }}

            #fieldLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {COLOR_DEEP_DARK_BLUE};
                margin-bottom: 5px;
            }}

            #inputField {{
                padding: 12px 15px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                background: {COLOR_OFF_WHITE};
                color: #333333;
                selection-background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                min-height: 20px;
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
            }}

            #inputField:focus {{
                border-color: {COLOR_DEEP_DARK_BLUE};
                outline: none;
                background: {COLOR_OFF_WHITE};
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1), 0 0 0 3px rgba(28, 53, 91, 0.3);
            }}

            #adminCheck {{
                font-family: 'Segoe UI', sans-serif;
                color: {COLOR_DEEP_DARK_BLUE};
                font-size: 13px;
                font-weight: 600;
                margin-top: 15px;
                padding: 2px;
            }}

            #adminCheck::indicator {{
                width: 18px;
                height: 18px;
                margin-right: 8px;
                border-radius: 4px;
            }}

            #adminCheck::indicator:unchecked {{
                background: {COLOR_OFF_WHITE};
                border: 2px solid {COLOR_DEEP_DARK_BLUE};
            }}

            #adminCheck::indicator:checked {{
                background: {COLOR_DEEP_DARK_BLUE};
                border: 2px solid {COLOR_DEEP_DARK_BLUE};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTggM0w0IDdMMiA1IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }}

            #loginButton {{
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 #162a4d);
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 14px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                min-height: 40px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                letter-spacing: 0.5px;
            }}

            #loginButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #162a4d, stop:1 {COLOR_DEEP_DARK_BLUE});
            }}

            #loginButton:pressed {{
                background: #162a4d;
                padding-top: 15px;
                padding-bottom: 13px;
            }}
        """

    def login(self):
        """
        Maneja el intento de inicio de sesión.
        Valida las credenciales y redirige a la ventana principal adecuada.
        """
        usuario = self.user_input.text().strip()
        clave = self.pass_input.text().strip()
        is_admin_attempt = self.admin_check.isChecked()

        if not usuario or not clave:
            QMessageBox.warning(self, 'Error', 'Por favor complete todos los campos.')
            return

        # Intenta autenticar al usuario
        user_data = self.authenticate_user(usuario, clave, is_admin_attempt)

        if user_data:
            self.current_user = user_data
            # Redirige según el tipo de intento y el rol del usuario
            # Solo si es un intento de admin Y el rol es administrador, va al panel de admin
            if is_admin_attempt and self.current_user['rol'] == 'administrador':
                self.show_admin_main_window()
            else:
                # En cualquier otro caso (no es intento de admin, o es admin pero no marcó el checkbox,
                # o es otro rol), va al panel general.
                self.show_general_main_window()
        else:
            # Mensajes de error específicos basados en el escenario de fallo
            QMessageBox.warning(self, 'Error de Login', 'Usuario o contraseña incorrectos, o cuenta inactiva.')
            self.pass_input.clear() # Limpiar siempre la contraseña en caso de error

    def show_general_main_window(self):
        """
        Muestra la ventana principal general y cierra la ventana de login.
        """
        # Pasa la configuración de la base de datos directamente
        self.general_main_window = GeneralMainWindow(self.db_config, self.current_user)
        self.general_main_window.show()
        self.close()

    def show_admin_main_window(self):
        """
        Muestra la ventana principal de administración y cierra la ventana de login.
        """
        # Pasa la configuración de la base de datos directamente
        self.admin_main_window = AdminMainWindow(self.db_config, self.current_user)
        self.admin_main_window.show()
        self.close()

    def show_registration_window(self):
        """
        Muestra la ventana de registro de nuevo usuario.
        """
        # Pasa la configuración de la base de datos directamente
        self.registration_window = RegistrationWindow(self.db_config)
        self.registration_window.show()
        # Puedes decidir si quieres cerrar la ventana de login o mantenerla abierta
        # self.close()

class AdminMainWindow(QMainWindow):
    """
    Ventana principal exclusiva para usuarios con rol de administrador
    que inician sesión con privilegios.
    """
    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user = user_data
        self.init_ui()

    def get_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL.
        Maneja errores de conexión.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            print(f"Error de conexión a la base de datos con la configuración actual: {e}")
            return None

    def get_users(self):
        """
        Carga los datos de los usuarios desde la base de datos.
        """
        conn = self.get_connection()
        if not conn:
            return []
            
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT id, codigo_usuario, cedula_personal, rol, estado,
                                fecha_creacion, ultimo_acceso, intentos_fallidos, debe_cambiar_clave
                    FROM usuario
                    ORDER BY id
                ''')
                result = cursor.fetchall()
                return result
        except psycopg2.Error as e:
            print(f"Error al obtener usuarios: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_login_history(self):
        """
        Carga el historial de accesos desde la base de datos.
        """
        conn = self.get_connection()
        if not conn:
            return []
            
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT l.fecha, l.hora, u.codigo_usuario, l.tipo_acceso,
                                l.ip_acceso, l.exitoso
                    FROM login l
                    LEFT JOIN usuario u ON l.id_usuario = u.id
                    ORDER BY l.fecha DESC, l.hora DESC
                ''')
                result = cursor.fetchall()
                return result
        except psycopg2.Error as e:
            print(f"Error al obtener historial de accesos: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def init_ui(self):
        """
        Inicializa la interfaz de usuario de la ventana principal de administración.
        """
        self.setWindowTitle(f'Panel de Administración - {self.user["codigo_usuario"]}')
        self.setGeometry(100, 100, 800, 650) # Un poco más grande para admin
        self.setStyleSheet(self.get_admin_main_styles())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 10)

        header = QLabel(f'Bienvenido, Administrador {self.user["codigo_usuario"]}')
        header.setObjectName('header')
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setObjectName('mainTabs')

        self.registro_tab = self.create_registro_tab()
        self.tabs.addTab(self.registro_tab, 'Gestión de Usuarios')

        self.historial_tab = self.create_historial_tab()
        self.tabs.addTab(self.historial_tab, 'Historial de Accesos')

        layout.addWidget(self.tabs)

        logout_btn = QPushButton('Cerrar Sesión')
        logout_btn.setObjectName('logoutButton')
        logout_btn.clicked.connect(self.logout)
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 5, 20, 15)
        button_layout.addStretch()
        button_layout.addWidget(logout_btn)
        button_layout.addStretch()
        layout.addWidget(button_container)

    def create_registro_tab(self):
        """
        Crea la pestaña para la gestión de usuarios registrados.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel('Gestión de Usuarios Registrados')
        title.setObjectName('tabTitle')
        layout.addWidget(title)

        self.users_table = QTableWidget()
        self.users_table.setObjectName('dataTable')
        headers = ['ID', 'Usuario', 'Cédula', 'Rol', 'Estado',
                                     'Fecha Creación', 'Último Acceso', 'Intentos Fallidos', 'Cambiar Clave']
        self.users_table.setColumnCount(len(headers))
        self.users_table.setHorizontalHeaderLabels(headers)

        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.load_users_data()
        layout.addWidget(self.users_table)

        # Contenedor para los botones de acción
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Empuja los botones a la derecha

        # Botón para registrar nuevo usuario
        register_new_btn = QPushButton('Registrar Nuevo Usuario')
        register_new_btn.setObjectName('actionButton')
        register_new_btn.clicked.connect(self.show_registration_window_from_admin)
        button_layout.addWidget(register_new_btn)

        # Botón para modificar usuario seleccionado
        modify_user_btn = QPushButton('Modificar Usuario Seleccionado')
        modify_user_btn.setObjectName('actionButton')
        modify_user_btn.clicked.connect(self.show_edit_user_dialog)
        button_layout.addWidget(modify_user_btn)
        
        layout.addLayout(button_layout) # Añade el layout de botones al layout principal de la pestaña

        return widget

    def show_registration_window_from_admin(self):
        """
        Muestra la ventana de registro de nuevo usuario desde el panel de administración.
        """
        self.registration_window = RegistrationWindow(self.db_config)
        self.registration_window.registration_success.connect(self.load_users_data) # Conectar señal para recargar tabla
        self.registration_window.show()

    def show_edit_user_dialog(self):
        """
        Muestra el diálogo para modificar el usuario seleccionado en la tabla.
        """
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, 'Selección Requerida', 'Por favor, seleccione un usuario de la tabla para modificar.')
            return

        # Obtener los datos del usuario seleccionado
        row = selected_rows[0].row()
        user_id = int(self.users_table.item(row, 0).text()) # ID del usuario
        
        # Recuperar todos los datos del usuario de la DB para asegurar que estén completos
        user_data_to_edit = None
        all_users = self.get_users() # Usar el método get_users de esta clase
        for user in all_users:
            if user['id'] == user_id:
                user_data_to_edit = user
                break

        if user_data_to_edit:
            self.edit_user_dialog = EditUserDialog(self.db_config, user_data_to_edit)
            self.edit_user_dialog.user_updated.connect(self.load_users_data) # Conectar señal para recargar tabla
            self.edit_user_dialog.exec() # Mostrar como diálogo modal
        else:
            QMessageBox.critical(self, 'Error', 'No se pudieron cargar los datos del usuario seleccionado.')


    def create_historial_tab(self):
        """
        Crea la pestaña para el historial de accesos.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel('Historial de Accesos al Sistema')
        title.setObjectName('tabTitle')
        layout.addWidget(title)

        self.history_table = QTableWidget()
        self.history_table.setObjectName('dataTable')
        headers = ['Fecha', 'Hora', 'Usuario', 'Tipo Acceso', 'IP', 'Exitoso']
        self.history_table.setColumnCount(len(headers))
        self.history_table.setHorizontalHeaderLabels(headers)

        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.load_history_data()
        layout.addWidget(self.history_table)

        refresh_btn = QPushButton('Refrescar Datos')
        refresh_btn.setObjectName('actionButton')
        refresh_btn.clicked.connect(self.load_history_data)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

        return widget

    def load_users_data(self):
        """
        Carga los datos de los usuarios desde la base de datos y los muestra en la tabla.
        """
        users = self.get_users() # Usar el método get_users de esta clase
        self.users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            # Acceder a los datos por nombre de columna (diccionario)
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
            self.users_table.setItem(row, 1, QTableWidgetItem(user['codigo_usuario']))
            self.users_table.setItem(row, 2, QTableWidgetItem(user['cedula_personal']))
            self.users_table.setItem(row, 3, QTableWidgetItem(user['rol']))
            self.users_table.setItem(row, 4, QTableWidgetItem(user['estado']))
            self.users_table.setItem(row, 5, QTableWidgetItem(str(user['fecha_creacion'].strftime('%Y-%m-%d')) if user['fecha_creacion'] else 'N/A'))
            self.users_table.setItem(row, 6, QTableWidgetItem(str(user['ultimo_acceso'].strftime('%Y-%m-%d')) if user['ultimo_acceso'] else 'N/A'))
            self.users_table.setItem(row, 7, QTableWidgetItem(str(user['intentos_fallidos'])))
            self.users_table.setItem(row, 8, QTableWidgetItem('Sí' if user['debe_cambiar_clave'] else 'No'))


    def load_history_data(self):
        """
        Carga el historial de accesos desde la base de datos y lo muestra en la tabla.
        """
        history = self.get_login_history() # Usar el método get_login_history de esta clase
        self.history_table.setRowCount(len(history))

        for row, record in enumerate(history):
            # Acceder a los datos por nombre de columna (diccionario)
            self.history_table.setItem(row, 0, QTableWidgetItem(str(record['fecha'].strftime('%Y-%m-%d'))))
            self.history_table.setItem(row, 1, QTableWidgetItem(str(record['hora'].strftime('%H:%M:%S'))))
            self.history_table.setItem(row, 2, QTableWidgetItem(record['codigo_usuario'] if record['codigo_usuario'] else 'N/A'))
            self.history_table.setItem(row, 3, QTableWidgetItem(record['tipo_acceso']))
            self.history_table.setItem(row, 4, QTableWidgetItem(record['ip_acceso']))
            self.history_table.setItem(row, 5, QTableWidgetItem('Sí' if record['exitoso'] else 'No'))

    def get_admin_main_styles(self):
        """
        Define y retorna los estilos QSS para la ventana principal de administración.
        Utiliza la paleta de colores definida.
        """
        return f"""
            QMainWindow {{
                background: {COLOR_OFF_WHITE};
            }}

            #header {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 19px;
                font-weight: bold;
                color: {COLOR_OFF_WHITE};
                padding: 18px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                             stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 {COLOR_MEDIUM_GRAYISH_BLUE});
                border: none;
                margin-bottom: 0px;
            }}

            #mainTabs {{
                background: {COLOR_OFF_WHITE};
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 10px;
                margin: 20px;
                padding: 5px;
            }}

            #mainTabs::pane {{
                border: none;
                background: {COLOR_OFF_WHITE};
                border-radius: 8px;
                padding: 15px;
            }}

            #mainTabs::tab-bar {{
                alignment: center;
            }}
            QTabBar::tab {{
                font-family: 'Segoe UI', sans-serif;
                background: {COLOR_LIGHT_GRAYISH_BLUE};
                color: {COLOR_DEEP_DARK_BLUE};
                padding: 12px 25px;
                margin: 3px;
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                min-width: 130px;
                transition: all 0.3s ease;
            }}

            QTabBar::tab:selected {{
                background: {COLOR_OFF_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
                border-color: {COLOR_DEEP_DARK_BLUE};
                border-bottom: 2px solid {COLOR_OFF_WHITE};
                margin-bottom: -2px;
                font-weight: bold;
            }}

            QTabBar::tab:hover:!selected {{
                background: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
                border-color: {COLOR_DEEP_DARK_BLUE};
            }}

            #tabTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
                padding-bottom: 15px;
                margin-bottom: 15px;
                border-bottom: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
            }}

            #formFrame {{
                background: {COLOR_OFF_WHITE};
                border-radius: 15px;
                border: 2px solid {COLOR_LIGHT_GRAYISH_BLUE};
                max-width: 650px;
                margin: 0px auto 20px auto;
                padding: 35px;
            }}

            #fieldLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {COLOR_DEEP_DARK_BLUE};
                margin-bottom: 2px;
            }}

            #inputField, QComboBox {{
                padding: 12px 15px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                background: {COLOR_OFF_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
                selection-background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                min-height: 20px;
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
            }}

            #inputField:focus, QComboBox:focus {{
                border-color: {COLOR_DEEP_DARK_BLUE};
                outline: none;
                background: {COLOR_OFF_WHITE};
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1), 0 0 0 3px rgba(28, 53, 91, 0.3);
            }}

            QComboBox::drop-down {{
                border: none;
                background: transparent;
                width: 30px;
                padding-right: 5px;
            }}

            QComboBox::down-arrow {{
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNS41TDcgOS.1TDioIDUuNSIgc3Ryb2tlPSIjNDk1MDU3IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
                width: 14px;
                height: 14px;
                margin-right: 8px;
            }}

            QComboBox QAbstractItemView {{
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                background: {COLOR_OFF_WHITE};
                selection-background-color: {COLOR_DEEP_DARK_BLUE};
                selection-color: {COLOR_OFF_WHITE};
                outline: none;
                padding: 5px 0px;
                min-width: 150px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}

            QComboBox QAbstractItemView::item {{
                padding: 8px 15px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}

            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_OFF_WHITE};
            }}
            
            #dataTable {{
                background: {COLOR_OFF_WHITE};
                alternate-background-color: #F8F9FA;
                selection-background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                selection-color: {COLOR_OFF_WHITE};
                gridline-color: {COLOR_LIGHT_GRAYISH_BLUE};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                color: {COLOR_DEEP_DARK_BLUE};
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
            }}

            #dataTable::item {{
                padding: 10px;
                border-bottom: 1px solid #F1F3F4;
            }}

            #dataTable::item:selected {{
                background: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
            }}

            #dataTable::item:hover {{
                background: rgba(112, 137, 167, 0.1);
            }}

            QHeaderView::section {{
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 #162a4d);
                color: {COLOR_OFF_WHITE};
                padding: 10px 8px;
                font-weight: bold;
                border: none;
                border-right: 1px solid rgba(255,255,255,0.2);
                font-size: 13px;
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            #actionButton {{
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_MEDIUM_GRAYISH_BLUE}, stop:1 {COLOR_DEEP_DARK_BLUE});
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                margin-top: 15px;
                max-width: 200px;
                font-size: 13px;
                text-align: center;
            }}

            #actionButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 {COLOR_MEDIUM_GRAYISH_BLUE});
            }}

            #actionButton:pressed {{
                background: {COLOR_DEEP_DARK_BLUE};
                padding-top: 11px;
                padding-bottom: 9px;
            }}

            #logoutButton {{
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_ERROR_RED}, stop:1 #c0392b);
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 12px 25px;
                border-radius: 8px;
                font-weight: bold;
                margin: 10px auto;
                max-width: 160px;
                font-size: 14px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            }}

            #logoutButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 #c0392b, stop:1 #a52a22);
            }}

            #logoutButton:pressed {{
                background: #a52a22;
                padding-top: 13px;
                padding-bottom: 11px;
            }}

            QScrollBar:vertical {{
                background: {COLOR_LIGHT_GRAYISH_BLUE};
                width: 12px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background: {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 6px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {COLOR_DEEP_DARK_BLUE};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    def logout(self):
        """
        Cierra la ventana actual y abre una nueva ventana de login.
        """
        self.close()
        # Importar LoginWindow aquí para evitar importación circular al inicio
        from __main__ import LoginWindow 
        self.login_window = LoginWindow() # LoginWindow ya carga su propia db_config
        self.login_window.show()

class RegistrationWindow(QMainWindow):
    """
    Ventana para el registro de nuevos usuarios y configuración de la base de datos.
    Toda la lógica de la base de datos para el registro está integrada aquí.
    """
    registration_success = pyqtSignal()

    def __init__(self, db_config):
        super().__init__()
        self.db_config = db_config
        self.init_ui()
        self.load_db_config_fields() # Cargar la configuración actual al iniciar

    def get_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL.
        Maneja errores de conexión.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            print(f"Error de conexión a la base de datos con la configuración actual: {e}")
            return None

    def register_new_user(self, codigo_usuario, cedula_personal, rol, clave):
        """
        Registra un nuevo usuario en la base de datos.
        """
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO usuario
                    (codigo_usuario, cedula_personal, rol, clave_hash, estado, debe_cambiar_clave)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (codigo_usuario, cedula_personal, rol, clave, 'activo', True))
                
                conn.commit()
                return True
        except psycopg2.IntegrityError as e:
            print(f"Error de integridad al registrar usuario: {e}")
            conn.rollback()
            return False
        except psycopg2.Error as e:
            print(f"Ocurrió un error al registrar usuario: {e}")
            conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def init_ui(self):
        """
        Inicializa la interfaz de usuario de la ventana de registro.
        """
        self.setWindowTitle('Registro de Nuevo Usuario y Configuración DB')
        self.setGeometry(150, 150, 1000, 600) # Tamaño ajustado para diseño lado a lado
        self.setStyleSheet(self.get_registration_styles())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget) # *** CAMBIO CLAVE: QHBoxLayout ***
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(30) # Espacio entre las dos secciones

        # --- Sección de Registro de Usuarios ---
        user_registration_container = QVBoxLayout() # Contenedor vertical para la sección de registro
        user_registration_container.setSpacing(15)

        user_registration_frame = QFrame()
        user_registration_frame.setObjectName('formFrame')
        
        user_registration_layout = QGridLayout(user_registration_frame)
        user_registration_layout.setContentsMargins(30, 25, 30, 25) # Padding interno
        user_registration_layout.setHorizontalSpacing(15)
        user_registration_layout.setVerticalSpacing(20)
        
        title_user = QLabel('Registro de Nuevos Usuarios')
        title_user.setObjectName('tabTitle')
        title_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_registration_layout.addWidget(title_user, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        
        row = 1 # Empezar desde la fila 1 después del título

        # Campo Código de Usuario
        codigo_label = QLabel('Código de Usuario:')
        codigo_label.setObjectName('fieldLabel')
        user_registration_layout.addWidget(codigo_label, row, 0)

        self.new_user_codigo_input = QLineEdit()
        self.new_user_codigo_input.setObjectName('inputField')
        self.new_user_codigo_input.setPlaceholderText('Código de Usuario (Ej: jdoe123)')
        user_registration_layout.addWidget(self.new_user_codigo_input, row, 1)
        row += 1

        # Campo Cédula Personal
        cedula_label = QLabel('Cédula Personal:')
        cedula_label.setObjectName('fieldLabel')
        user_registration_layout.addWidget(cedula_label, row, 0)

        self.new_user_cedula_input = QLineEdit()
        self.new_user_cedula_input.setObjectName('inputField')
        self.new_user_cedula_input.setPlaceholderText('Cédula Personal (Ej: V-12345678)')
        user_registration_layout.addWidget(self.new_user_cedula_input, row, 1)
        row += 1

        # Selector de Rol
        rol_label = QLabel('Rol del Usuario:')
        rol_label.setObjectName('fieldLabel')
        user_registration_layout.addWidget(rol_label, row, 0)

        self.new_user_rol_combo = QComboBox()
        self.new_user_rol_combo.setObjectName('inputField')
        self.new_user_rol_combo.addItems(['administrador', 'control de estudio', 'docente'])
        user_registration_layout.addWidget(self.new_user_rol_combo, row, 1)
        row += 1

        # Campo Contraseña
        clave_label = QLabel('Contraseña:')
        clave_label.setObjectName('fieldLabel')
        user_registration_layout.addWidget(clave_label, row, 0)

        self.new_user_clave_input = QLineEdit()
        self.new_user_clave_input.setObjectName('inputField')
        self.new_user_clave_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_user_clave_input.setPlaceholderText('Contraseña (Ej: PasswordSeguro123)')
        user_registration_layout.addWidget(self.new_user_clave_input, row, 1)
        row += 1

        # Espacio antes del botón
        user_registration_layout.addItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), row, 0, 1, 2)
        row += 1

        # Botón de registro
        register_btn = QPushButton('Registrar Usuario')
        register_btn.setObjectName('actionButton')
        register_btn.clicked.connect(self.register_user)
        user_registration_layout.addWidget(register_btn, row, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter) 

        user_registration_container.addWidget(user_registration_frame)
        user_registration_container.addStretch() # Empuja el frame hacia arriba en su contenedor vertical

        main_layout.addLayout(user_registration_container) # Añadir el contenedor vertical al layout principal

        # --- Sección de Configuración de Base de Datos ---
        db_config_container = QVBoxLayout() # Contenedor vertical para la sección de DB
        db_config_container.setSpacing(15)

        db_config_frame = QFrame()
        db_config_frame.setObjectName('formFrame')

        db_config_layout = QGridLayout(db_config_frame)
        db_config_layout.setContentsMargins(30, 25, 30, 25) # Padding interno
        db_config_layout.setHorizontalSpacing(15)
        db_config_layout.setVerticalSpacing(20)

        title_db = QLabel('Configuración de Conexión a la Base de Datos')
        title_db.setObjectName('tabTitle')
        title_db.setAlignment(Qt.AlignmentFlag.AlignCenter)
        db_config_layout.addWidget(title_db, 0, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)

        db_row = 1
        # Host
        db_config_layout.addWidget(QLabel('Host:'), db_row, 0)
        self.db_host_input = QLineEdit()
        self.db_host_input.setObjectName('inputField')
        db_config_layout.addWidget(self.db_host_input, db_row, 1)
        db_row += 1

        # Database Name
        db_config_layout.addWidget(QLabel('Base de Datos:'), db_row, 0)
        self.db_name_input = QLineEdit()
        self.db_name_input.setObjectName('inputField')
        db_config_layout.addWidget(self.db_name_input, db_row, 1)
        db_row += 1

        # User
        db_config_layout.addWidget(QLabel('Usuario DB:'), db_row, 0)
        self.db_user_input = QLineEdit()
        self.db_user_input.setObjectName('inputField')
        db_config_layout.addWidget(self.db_user_input, db_row, 1)
        db_row += 1

        # Password
        db_config_layout.addWidget(QLabel('Contraseña DB:'), db_row, 0)
        self.db_password_input = QLineEdit()
        self.db_password_input.setObjectName('inputField')
        self.db_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        db_config_layout.addWidget(self.db_password_input, db_row, 1)
        db_row += 1

        # Port
        db_config_layout.addWidget(QLabel('Puerto DB:'), db_row, 0)
        self.db_port_input = QLineEdit()
        self.db_port_input.setObjectName('inputField')
        db_config_layout.addWidget(self.db_port_input, db_row, 1)
        db_row += 1

        # Espacio antes del botón
        db_config_layout.addItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), db_row, 0, 1, 2)
        db_row += 1

        # Botón para guardar configuración DB
        save_db_config_btn = QPushButton('Guardar Configuración DB')
        save_db_config_btn.setObjectName('actionButton')
        save_db_config_btn.clicked.connect(self.save_db_config)
        db_config_layout.addWidget(save_db_config_btn, db_row, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)

        db_config_container.addWidget(db_config_frame)
        db_config_container.addStretch() # Empuja el frame hacia arriba en su contenedor vertical

        main_layout.addLayout(db_config_container) # Añadir el contenedor vertical al layout principal

        # Botón de cerrar (fuera de los layouts de las secciones para que esté centrado abajo)
        close_button_container = QHBoxLayout()
        close_button_container.addStretch()
        close_btn = QPushButton('Cerrar')
        close_btn.setObjectName('logoutButton')
        close_btn.clicked.connect(self.close)
        close_button_container.addWidget(close_btn)
        close_button_container.addStretch()

        final_window_layout = QVBoxLayout(central_widget)
        final_window_layout.setContentsMargins(0,0,0,0) # Resetear márgenes
        final_window_layout.addLayout(main_layout) # Añadir el QHBoxLayout de las secciones
        final_window_layout.addLayout(close_button_container) # Añadir el QHBoxLayout del botón de cerrar


    def load_db_config_fields(self):
        """
        Carga la configuración actual de la base de datos en los campos de entrada.
        """
        current_config = self.db_config # Acceder directamente a la configuración
        self.db_host_input.setText(current_config.get('host', ''))
        self.db_name_input.setText(current_config.get('database', ''))
        self.db_user_input.setText(current_config.get('user', ''))
        self.db_password_input.setText(current_config.get('password', '')) # Mostrar la contraseña si está disponible (¡Advertencia de seguridad!)
        self.db_port_input.setText(current_config.get('port', ''))

    def save_db_config(self):
        """
        Guarda la nueva configuración de la base de datos.
        """
        new_config = {
            'host': self.db_host_input.text().strip(),
            'database': self.db_name_input.text().strip(),
            'user': self.db_user_input.text().strip(),
            'password': self.db_password_input.text().strip(),
            'port': self.db_port_input.text().strip()
        }

        if not all(new_config.values()):
            QMessageBox.warning(self, 'Campos Incompletos', 'Por favor, complete todos los campos de configuración de la base de datos.')
            return

        if LoginWindow._save_db_config(new_config): # Usar el método estático de LoginWindow
            # Actualizar la configuración en la instancia actual de RegistrationWindow
            self.db_config.update(new_config) 
            QMessageBox.information(self, 'Configuración Guardada', 'La configuración de la base de datos ha sido actualizada y la conexión se ha intentado reestablecer. Por favor, reinicie la aplicación para asegurar que los cambios surtan efecto completamente.')
        else:
            QMessageBox.critical(self, 'Error al Guardar', 'No se pudo guardar la configuración de la base de datos. Verifique los permisos o el formato.')


    def get_registration_styles(self):
        """
        Define y retorna los estilos QSS para la ventana de registro.
        Reutiliza muchos estilos de las otras ventanas para consistencia.
        """
        return f"""
            QMainWindow {{
                background: {COLOR_OFF_WHITE};
            }}

            #tabTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
                padding-bottom: 15px;
                margin-bottom: 15px;
                border-bottom: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
            }}

            #formFrame {{
                background: {COLOR_OFF_WHITE};
                border-radius: 15px;
                border: 2px solid {COLOR_LIGHT_GRAYISH_BLUE};
                padding: 35px;
            }}

            #fieldLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {COLOR_DEEP_DARK_BLUE};
                margin-bottom: 2px;
            }}

            #inputField {{
                padding: 12px 15px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                background: {COLOR_OFF_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
                selection-background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                min-height: 20px;
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
            }}

            #inputField:focus {{
                border-color: {COLOR_DEEP_DARK_BLUE};
                outline: none;
                background: {COLOR_OFF_WHITE};
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1), 0 0 0 3px rgba(28, 53, 91, 0.3);
            }}

            QComboBox::drop-down {{
                border: none;
                background: transparent;
                width: 30px;
                padding-right: 5px;
            }}

            QComboBox::down-arrow {{
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNS41TDcgOS41TDEwIDU.1IiBzdHJva2U9IiM0OTUwNTciIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
                width: 14px;
                height: 14px;
                margin-right: 8px;
            }}

            QComboBox QAbstractItemView {{
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                background: {COLOR_OFF_WHITE};
                selection-background-color: {COLOR_DEEP_DARK_BLUE};
                selection-color: {COLOR_OFF_WHITE};
                outline: none;
                padding: 5px 0px;
                min-width: 150px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}

            QComboBox QAbstractItemView::item {{
                padding: 8px 15px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}

            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_OFF_WHITE};
            }}

            #actionButton {{
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_SUCCESS_GREEN}, stop:1 #27ae60);
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                margin-top: 15px;
                max-width: 200px;
                font-size: 13px;
                text-align: center;
            }}

            #actionButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 #27ae60, stop:1 #229a54);
            }}

            #actionButton:pressed {{
                background: #229a54;
                padding-top: 11px;
                padding-bottom: 9px;
            }}

            #logoutButton {{ /* Reutilizado para el botón de cerrar en el registro */
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_MEDIUM_GRAYISH_BLUE}, stop:1 {COLOR_DEEP_DARK_BLUE});
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 12px 25px;
                border-radius: 8px;
                font-weight: bold;
                margin: 10px auto;
                max-width: 160px;
                font-size: 14px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            }}
            #logoutButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 {COLOR_MEDIUM_GRAYISH_BLUE});
            }}

            #logoutButton:pressed {{
                background: {COLOR_DEEP_DARK_BLUE};
                padding-top: 13px;
                padding-bottom: 11px;
            }}
        """

    def register_user(self):
        """
        Maneja el registro de un nuevo usuario desde la ventana de registro.
        """
        codigo = self.new_user_codigo_input.text().strip()
        cedula = self.new_user_cedula_input.text().strip()
        rol = self.new_user_rol_combo.currentText()
        clave = self.new_user_clave_input.text().strip()

        if not codigo or not cedula or not clave:
            QMessageBox.warning(self, 'Campos Incompletos', 'Por favor, complete todos los campos para registrar al usuario.')
            return

        # Validación básica de contraseña (puedes añadir más reglas como regex)
        if len(clave) < 8 or not any(char.isupper() for char in clave) or \
           not any(char.islower() for char in clave) or not any(char.isdigit() for char in clave):
            QMessageBox.warning(self, 'Contraseña Débil', 'La contraseña debe tener al menos 8 caracteres, incluyendo mayúsculas, minúsculas y números.')
            return

        # Intenta registrar el usuario
        if self.register_new_user(codigo, cedula, rol, clave): # Usar el método de esta clase
            QMessageBox.information(self, 'Registro Exitoso', f'Usuario "{codigo}" registrado con éxito. Se le solicitará cambiar la contraseña en el primer inicio de sesión.')
            # Limpiar campos después del registro exitoso
            self.new_user_codigo_input.clear()
            self.new_user_cedula_input.clear()
            self.new_user_clave_input.clear()
            self.registration_success.emit() # Emitir la señal de éxito
        else:
            QMessageBox.critical(self, 'Error de Registro', 'Ocurrió un error al intentar registrar el usuario. Es posible que el código de usuario o la cédula ya existan.')

class EditUserDialog(QDialog):
    """
    Diálogo para modificar los datos de un usuario existente.
    Toda la lógica de la base de datos para la edición de usuarios está integrada aquí.
    """
    user_updated = pyqtSignal()

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.init_ui()

    def get_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL.
        Maneja errores de conexión.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            print(f"Error de conexión a la base de datos con la configuración actual: {e}")
            return None

    def update_user(self, user_id, data):
        """
        Actualiza los datos de un usuario existente en la base de datos.
        `data` es un diccionario con los campos a actualizar.
        Retorna True si la actualización es exitosa, False en caso contrario.
        """
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                # Construir la parte SET de la consulta dinámicamente
                set_clauses = []
                values = []
                for key, value in data.items():
                    # Evitar actualizar la clave_hash con este método
                    if key != 'clave_hash':
                        set_clauses.append(f"{key} = %s")
                        values.append(value)
                
                if not set_clauses: # No hay nada que actualizar
                    return True

                values.append(user_id) # Añadir el ID para la cláusula WHERE

                query = f"UPDATE usuario SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(query, values)
                conn.commit()
                return True
        except psycopg2.IntegrityError as e:
            print(f"Error de integridad al actualizar usuario: {e}")
            conn.rollback()
            return False
        except psycopg2.Error as e:
            print(f"Error al actualizar usuario: {e}")
            conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def update_password(self, user_id, new_password):
        """
        Actualiza la contraseña de un usuario específico.
        Retorna True si la actualización es exitosa, False en caso contrario.
        """
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                # ADVERTENCIA: Aquí se está almacenando la contraseña en texto plano.
                # Para producción, deberías usar un hash de contraseña (ej. bcrypt).
                cursor.execute('''
                    UPDATE usuario
                    SET clave_hash = %s, debe_cambiar_clave = FALSE
                    WHERE id = %s
                ''', (new_password, user_id))
                conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Error al actualizar contraseña: {e}")
            conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def init_ui(self):
        """
        Inicializa la interfaz de usuario del diálogo de edición de usuario.
        """
        self.setWindowTitle(f'Modificar Usuario: {self.user_data["codigo_usuario"]}')
        self.setGeometry(250, 250, 500, 550)
        self.setStyleSheet(self.get_edit_user_styles())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        title = QLabel('Modificar Datos de Usuario')
        title.setObjectName('dialogTitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setObjectName('formFrame')
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(25, 25, 25, 25)
        form_layout.setHorizontalSpacing(15)
        form_layout.setVerticalSpacing(15)

        row = 0
        # ID del usuario (solo lectura)
        form_layout.addWidget(QLabel('ID de Usuario:'), row, 0)
        id_label = QLabel(str(self.user_data['id']))
        id_label.setObjectName('infoLabel')
        form_layout.addWidget(id_label, row, 1)
        row += 1

        # Código de Usuario
        form_layout.addWidget(QLabel('Código de Usuario:'), row, 0)
        self.codigo_input = QLineEdit(self.user_data['codigo_usuario'])
        self.codigo_input.setObjectName('inputField')
        form_layout.addWidget(self.codigo_input, row, 1)
        row += 1

        # Cédula Personal
        form_layout.addWidget(QLabel('Cédula Personal:'), row, 0)
        # Convertir a string explícitamente para QLineEdit
        self.cedula_input = QLineEdit(str(self.user_data['cedula_personal']))
        self.cedula_input.setObjectName('inputField')
        form_layout.addWidget(self.cedula_input, row, 1)
        row += 1

        # Rol
        form_layout.addWidget(QLabel('Rol:'), row, 0)
        self.rol_combo = QComboBox()
        self.rol_combo.setObjectName('inputField')
        self.rol_combo.addItems(['administrador', 'control de estudio', 'docente'])
        self.rol_combo.setCurrentText(self.user_data['rol'])
        form_layout.addWidget(self.rol_combo, row, 1)
        row += 1

        # Estado
        form_layout.addWidget(QLabel('Estado:'), row, 0)
        self.estado_combo = QComboBox()
        self.estado_combo.setObjectName('inputField')
        self.estado_combo.addItems(['activo', 'inactivo'])
        self.estado_combo.setCurrentText(self.user_data['estado'])
        form_layout.addWidget(self.estado_combo, row, 1)
        row += 1

        # Debe cambiar clave
        self.debe_cambiar_clave_check = QCheckBox('Debe cambiar clave en el próximo login')
        self.debe_cambiar_clave_check.setChecked(self.user_data['debe_cambiar_clave'])
        self.debe_cambiar_clave_check.setObjectName('adminCheck') # Reutiliza estilo
        form_layout.addWidget(self.debe_cambiar_clave_check, row, 0, 1, 2)
        row += 1

        layout.addWidget(form_frame)

        # Sección para cambiar contraseña
        password_frame = QFrame()
        password_frame.setObjectName('passwordFrame')
        password_layout = QVBoxLayout(password_frame)
        password_layout.setContentsMargins(25, 15, 25, 25)
        password_layout.setSpacing(10)

        password_title = QLabel('Cambiar Contraseña (Opcional)')
        password_title.setObjectName('sectionTitle')
        password_layout.addWidget(password_title)

        password_label = QLabel('Nueva Contraseña:')
        password_label.setObjectName('fieldLabel')
        password_layout.addWidget(password_label)
        self.new_password_input = QLineEdit()
        self.new_password_input.setObjectName('inputField')
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText('Dejar vacío para no cambiar')
        password_layout.addWidget(self.new_password_input)

        confirm_password_label = QLabel('Confirmar Contraseña:')
        confirm_password_label.setObjectName('fieldLabel')
        password_layout.addWidget(confirm_password_label)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setObjectName('inputField')
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText('Confirmar nueva contraseña')
        password_layout.addWidget(self.confirm_password_input)

        layout.addWidget(password_frame)

        # Botones de acción
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton('Guardar Cambios')
        save_btn.setObjectName('actionButton')
        save_btn.clicked.connect(self.save_changes)
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton('Cancelar')
        cancel_btn.setObjectName('logoutButton') # Reutiliza estilo de logoutButton
        cancel_btn.clicked.connect(self.reject) # Cierra el diálogo con resultado QDialog.Rejected
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def save_changes(self):
        """
        Guarda los cambios del usuario en la base de datos.
        """
        user_id = self.user_data['id']
        new_codigo = self.codigo_input.text().strip()
        new_cedula = self.cedula_input.text().strip()
        new_rol = self.rol_combo.currentText()
        new_estado = self.estado_combo.currentText()
        new_debe_cambiar_clave = self.debe_cambiar_clave_check.isChecked()

        new_password = self.new_password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()

        # Validaciones
        if not new_codigo or not new_cedula:
            QMessageBox.warning(self, 'Campos Incompletos', 'El código de usuario y la cédula personal no pueden estar vacíos.')
            return

        if new_password: # Si se intenta cambiar la contraseña
            if new_password != confirm_password:
                QMessageBox.warning(self, 'Contraseñas No Coinciden', 'Las nuevas contraseñas no coinciden.')
                return
            if len(new_password) < 8 or not any(char.isupper() for char in new_password) or \
               not any(char.islower() for char in new_password) or not any(char.isdigit() for char in new_password):
                QMessageBox.warning(self, 'Contraseña Débil', 'La nueva contraseña debe tener al menos 8 caracteres, incluyendo mayúsculas, minúsculas y números.')
                return

        # Preparar datos para actualización
        updated_data = {
            'codigo_usuario': new_codigo,
            'cedula_personal': new_cedula,
            'rol': new_rol,
            'estado': new_estado,
            'debe_cambiar_clave': new_debe_cambiar_clave
        }

        # Intentar actualizar el usuario
        success = self.update_user(user_id, updated_data) # Usar el método de esta clase
        if success:
            # Si hay una nueva contraseña, actualizarla
            if new_password:
                password_success = self.update_password(user_id, new_password) # Usar el método de esta clase
                if not password_success:
                    QMessageBox.warning(self, 'Advertencia', 'Los datos del usuario se actualizaron, pero hubo un error al cambiar la contraseña.')
            
            QMessageBox.information(self, 'Éxito', 'Usuario actualizado correctamente.')
            self.user_updated.emit() # Emitir señal de que el usuario fue actualizado
            self.accept() # Cierra el diálogo con resultado QDialog.Accepted
        else:
            QMessageBox.critical(self, 'Error', 'No se pudo actualizar el usuario. Verifique si el código de usuario o la cédula ya existen.')

    def get_edit_user_styles(self):
        """
        Define y retorna los estilos QSS para el diálogo de edición de usuario.
        """
        return f"""
            QDialog {{
                background: {COLOR_OFF_WHITE};
                border-radius: 15px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
            }}

            #dialogTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 20px;
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
                padding-bottom: 10px;
                margin-bottom: 15px;
                border-bottom: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
            }}

            #formFrame, #passwordFrame {{
                background: {COLOR_OFF_WHITE};
                border-radius: 10px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                padding: 15px;
                margin-bottom: 15px;
            }}

            QLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            
            #infoLabel {{ /* Para campos de solo lectura como el ID */
                font-weight: normal;
                color: #555555;
            }}

            #sectionTitle {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                font-weight: bold;
                color: {COLOR_DEEP_DARK_BLUE};
                margin-bottom: 10px;
                border-bottom: 1px dashed {COLOR_LIGHT_GRAYISH_BLUE};
                padding-bottom: 5px;
            }}

            #inputField, QComboBox {{
                padding: 10px 12px;
                border: 1px solid {COLOR_MEDIUM_GRAYISH_BLUE};
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                background: {COLOR_OFF_WHITE};
                color: {COLOR_DEEP_DARK_BLUE};
                selection-background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
            }}

            #inputField:focus, QComboBox:focus {{
                border-color: {COLOR_DEEP_DARK_BLUE};
                outline: none;
                box-shadow: 0 0 0 2px rgba(28, 53, 91, 0.2);
            }}

            QComboBox::drop-down {{
                border: none;
                background: transparent;
                width: 25px;
                padding-right: 3px;
            }}

            QComboBox::down-arrow {{
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNS41TDcgOS41TDEwIDU.1IiBzdHJva2U9IiM0OTUwNTciIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
                width: 14px;
                height: 14px;
                margin-right: 5px;
            }}

            QComboBox QAbstractItemView {{
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 6px;
                background: {COLOR_OFF_WHITE};
                selection-background-color: {COLOR_DEEP_DARK_BLUE};
                selection-color: {COLOR_OFF_WHITE};
                outline: none;
                padding: 3px 0px;
                min-width: 120px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}

            QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
                color: {COLOR_DEEP_DARK_BLUE};
            }}

            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_OFF_WHITE};
            }}

            #actionButton {{
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_SUCCESS_GREEN}, stop:1 #27ae60);
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
            }}

            #actionButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 #27ae60, stop:1 #229a54);
            }}

            #actionButton:pressed {{
                background: #229a54;
            }}

            #logoutButton {{ /* Reutilizado para el botón de cancelar */
                font-family: 'Segoe UI', sans-serif;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_MEDIUM_GRAYISH_BLUE}, stop:1 {COLOR_DEEP_DARK_BLUE});
                color: {COLOR_OFF_WHITE};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            }}

            #logoutButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                             stop:0 {COLOR_DEEP_DARK_BLUE}, stop:1 {COLOR_MEDIUM_GRAYISH_BLUE});
            }}

            #logoutButton:pressed {{
                background: {COLOR_DEEP_DARK_BLUE};
            }}
        """

# Bloque para ejecutar la aplicación
if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec())
