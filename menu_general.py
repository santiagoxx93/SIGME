import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFrame, QGridLayout,
                             QMessageBox, QScrollArea, QSizePolicy, QApplication)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap

from estudiante import EstudianteApp
from institucion import InstitucionApp
from foto import ImageUploaderApp
from ano_escolar import AnoEscolarApp
from menu_constancia import MainMenuApp
from asignacion_docente import AsignacionDocenteWindow 
from grupo_actividad_app import GrupoActividadUI, GrupoActividadModel
from representante import RepresentanteApp 
from grado import GradoApp
from momento_evaluativo_app import MomentoEvaluativoApp
from materias import MateriasWidget 
from personal import PersonalModule
from Secciones import ModuloInstitucion 
from matricula import MatriculaApp
from evaluaciones import GestionNotasWindow


# --- Definición de la Paleta de Colores (Duplicada para autocontención) ---
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


class GeneralMainWindow(QMainWindow):
    """
    Ventana principal general para usuarios con rol 'control de estudio' o 'docente'.
    Ahora gestiona su propia conexión a la base de datos usando db_config.
    """
    def __init__(self, db_config, user_data): # Recibe db_config directamente
        super().__init__()
        self.db_config = db_config # Almacena la configuración de la base de datos
        self.user = user_data
        self.module_buttons = {}
        self.init_ui()
        self.configure_module_access()

        # Diccionario para mantener referencias a las ventanas de módulos abiertas
        self.open_module_windows = {}

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

    def init_ui(self):
        """
        Inicializa la interfaz de usuario de la ventana principal general con el diseño del "Menú Moderno".
        """
        self.setWindowTitle(f'Sistema de Gestión Escolar - {self.user["rol"].capitalize()} {self.user["codigo_usuario"]}')
        self.setGeometry(100, 100, 800, 600)

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_MAIN_BACKGROUND};
                border-radius: 15px;
            }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- Header Section ---
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet(f"""
            #headerFrame {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }}
            QLabel.headerIcon {{
                background-color: {COLOR_WHITE};
                border-radius: 20px;
                border: 2px solid {COLOR_PRIMARY_DARK_BLUE};
            }}
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        header_layout.setSpacing(20)

        icon_size = QSize(40, 40)
        icons_placeholder = QHBoxLayout()
        for _ in range(3):
            icon_label = QLabel()
            icon_label.setFixedSize(icon_size)
            icon_label.setObjectName("headerIcon")
            icons_placeholder.addWidget(icon_label)
        header_layout.addLayout(icons_placeholder)
        header_layout.addStretch()

        header_title = QLabel(f'Bienvenido, {self.user["rol"].capitalize()} {self.user["codigo_usuario"]}')
        header_title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_title.setStyleSheet(f"color: {COLOR_WHITE};")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        main_layout.addWidget(header_frame)

        # --- Main Content Area ---
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_frame.setStyleSheet(f"""
            #contentFrame {{
                background-color: {COLOR_MAIN_BACKGROUND};
                border-radius: 10px;
                padding: 15px;
            }}
            QLabel#modulesTitle {{
                background-color: {COLOR_WHITE};
                color: {COLOR_DARK_TEXT};
                border: 2px solid {COLOR_PRIMARY_DARK_BLUE};
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 15px;
                font-family: "Arial", sans-serif;
                font-size: 20px;
                font-weight: bold;
            }}
        """)
        main_layout.addWidget(content_frame)

        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        modules_title = QLabel('Módulos del Sistema')
        modules_title.setObjectName('modulesTitle')
        modules_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(modules_title)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(16)

        left_column_layout = QVBoxLayout()
        left_column_layout.setSpacing(15)
        right_column_layout = QVBoxLayout()
        right_column_layout.setSpacing(15)

        buttons_data = [
            ("Año Escolar", "año_escolar"),
            ("Asignación Docente", "asignacion_docente"),
            ("Institución", "institucion"),
            ("Materias", "materias"),
            ("Estudiante", "estudiante"),
            ("Constancias", "constancias"),
            ("Evaluaciones", "evaluaciones"),
            ("Matrícula", "matricula"),
            ("Grupo Actividad", "grupo_actividad"),
            ("Momento Evaluativo", "momento_evaluativo"),
            ("Representante", "representante"), 
            ("Personal", "personal"),
            ("Grado", "grado"),
            ("Subir Imágenes", "subir_imagenes"), # <--- COMA AÑADIDA AQUÍ
            ("Secciones", "secciones"), # NUEVO BOTÓN
        ]

        half_point = (len(buttons_data) + 1) // 2 
        
        for i, (text, obj_name) in enumerate(buttons_data):
            btn = QPushButton(text)
            btn.setObjectName('moduleButton')
            btn.setProperty('moduleName', obj_name)
            btn.setFixedSize(200, 50)
            btn.setFont(QFont("Arial", 12))
            btn.clicked.connect(lambda checked, name=obj_name: self.open_module(name))
            self.module_buttons[obj_name] = btn

            if i < half_point:
                left_column_layout.addWidget(btn)
            else:
                right_column_layout.addWidget(btn)
        
        buttons_layout.addLayout(left_column_layout)
        buttons_layout.addLayout(right_column_layout)
        
        content_layout.addLayout(buttons_layout)
        content_layout.addStretch()

        # --- Footer Section (Logout Button) ---
        logout_btn = QPushButton('Cerrar Sesión')
        logout_btn.setObjectName('logoutButton')
        logout_btn.clicked.connect(self.logout)
        
        logout_btn.setStyleSheet(f"""
            QPushButton#logoutButton {{
                background-color: {COLOR_ERROR_RED};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: bold;
                transition: background-color 0.3s ease;
            }}
            QPushButton#logoutButton:hover {{
                background-color: #C82333; /* Un poco más oscuro al pasar el ratón */
            }}
            QPushButton#logoutButton:pressed {{
                background-color: #A52A2A;
            }}
        """)
        
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        footer_layout.addWidget(logout_btn)
        footer_layout.addStretch()
        main_layout.addLayout(footer_layout)

    def configure_module_access(self):
        """
        Configura la habilitación/deshabilitación de los botones de módulo
        según el rol del usuario.
        """
        user_role = self.user['rol']

        allowed_modules = {
            'control de estudio': [
                "materias", "estudiante", "evaluaciones", "constancias",
                "grupo_actividad", "momento_evaluativo","secciones" # Añadido para control de estudio
            ],
            'docente': [
                "materias", "estudiante", "evaluaciones", "constancias",
                "grupo_actividad", "momento_evaluativo"
            ],
            'administrador': [
                "año_escolar", "asignacion_docente", "institucion", "materias",
                "estudiante", "constancias", "evaluaciones", "matricula",
                "grupo_actividad", "momento_evaluativo", "representante",
                "personal", "grado", "subir_imagenes","secciones" # Añadido para administrador
            ]
        }

        for module_name, button in self.module_buttons.items():
            if user_role in allowed_modules and module_name in allowed_modules[user_role]:
                button.setEnabled(True)
                button.setStyleSheet(f"""
                    QPushButton#moduleButton {{
                        background-color: {COLOR_PRIMARY_DARK_BLUE};
                        color: {COLOR_WHITE};
                        border: none;
                        border-radius: 10px;
                        padding: 10px 20px;
                        font-weight: bold;
                        transition: background-color 0.3s ease;
                    }}
                    QPushButton#moduleButton:hover {{
                        background-color: {COLOR_ACCENT_BLUE};
                        border: 2px solid {COLOR_WHITE};
                    }}
                    QPushButton#moduleButton:pressed {{
                        background-color: {COLOR_PRIMARY_DARK_BLUE};
                    }}
                """)
            else:
                button.setEnabled(False)
                button.setStyleSheet(f"""
                    QPushButton#moduleButton {{
                        background-color: {COLOR_DISABLED_BG};
                        color: {COLOR_DISABLED_TEXT};
                        border: none;
                        border-radius: 10px;
                        padding: 10px 20px;
                        font-weight: bold;
                    }}
                """)

    def open_module(self, module_name):
        """
        Función para manejar la apertura de módulos.
        """
        if not self.module_buttons[module_name].isEnabled():
            QMessageBox.warning(self, "Acceso Denegado", "No tienes permisos para acceder a este módulo.")
            return

        # Si el módulo ya está abierto, lo traemos al frente
        if module_name in self.open_module_windows and self.open_module_windows[module_name].isVisible():
            self.open_module_windows[module_name].activateWindow()
            self.open_module_windows[module_name].raise_()
            return

        # Lógica para abrir ventanas específicas
        if module_name == "año_escolar":
            # Instancia AnoEscolarApp y le pasa el db_config y user_data
            self.ano_escolar_window = AnoEscolarApp(db_config=self.db_config, user_data=self.user)
            self.ano_escolar_window.closed.connect(self.show) # Conectar señal de cierre para mostrar el menú de nuevo
            self.ano_escolar_window.show()
            self.open_module_windows[module_name] = self.ano_escolar_window
            self.hide() # Ocultar la ventana principal al abrir el módulo
        elif module_name == "asignacion_docente":
            # Instancia AsignacionDocenteWindow y le pasa el db_config y user_data
            self.asignacion_docente_window = AsignacionDocenteWindow(db_config=self.db_config, user_data=self.user)
            self.asignacion_docente_window.closed.connect(self.show) # Conectar señal de cierre para mostrar el menú de nuevo
            self.asignacion_docente_window.show()
            self.open_module_windows[module_name] = self.asignacion_docente_window
            self.hide() # Ocultar la ventana principal al abrir el módulo
        elif module_name == "representante": 
            self.representante_window = RepresentanteApp(db_config=self.db_config, user_data=self.user)
            self.representante_window.closed.connect(self.show) # Conectar señal de cierre para mostrar el menú de nuevo
            self.representante_window.show()
            self.open_module_windows[module_name] = self.representante_window
            self.hide() # Ocultar la ventana principal al abrir el módulo
        elif module_name == "materias": 
            self.materias_window = MateriasWidget(db_config=self.db_config, user_data=self.user)
            self.materias_window.closed.connect(self.show) # Conectar señal de cierre para mostrar el menú de nuevo
            self.materias_window.show()
            self.open_module_windows[module_name] = self.materias_window
            self.hide() # Ocultar la ventana principal al abrir el módulo
        elif module_name == "subir_imagenes": 
            self.image_uploader_window = ImageUploaderApp(db_config=self.db_config, user_data=self.user)
            self.image_uploader_window.closed.connect(self.show) # Conectar señal de cierre para mostrar el menú de nuevo
            self.image_uploader_window.show()
            self.open_module_windows[module_name] = self.image_uploader_window
            self.hide() # Ocultar la ventana principal al abrir el módulo
        # El bloque para "materias" estaba duplicado, se mantiene el primero y se elimina el segundo.
        elif module_name == "institucion": 
            self.institucion_window = InstitucionApp(db_config=self.db_config, user_data=self.user)
            self.institucion_window.closed.connect(self.show) # Conectar señal de cierre para mostrar el menú de nuevo
            self.institucion_window.show()
            self.open_module_windows[module_name] = self.institucion_window
            self.hide() # Ocultar la ventana principal al abrir el módulo
        elif module_name == "estudiante":
            self.estudiante_window = EstudianteApp(db_config=self.db_config, user_data=self.user)
            self.estudiante_window.closed.connect(self.show)
            self.estudiante_window.show()
            self.open_module_windows[module_name] = self.estudiante_window
            self.hide()
        elif module_name == "personal":
            self.personal_window = PersonalModule(db_config=self.db_config, user_data=self.user)
            self.personal_window.closed.connect(self.show)
            self.personal_window.show()
            self.open_module_windows[module_name] = self.personal_window
            self.hide()
        elif module_name == "grado":
            self.grado_window = GradoApp(db_config=self.db_config, user_data=self.user)
            self.grado_window.closed.connect(self.show)
            self.grado_window.show()
            self.open_module_windows[module_name] = self.grado_window
            self.hide()
        elif module_name == "momento_evaluativo":
            self.momento_window = MomentoEvaluativoApp(db_config=self.db_config, user_data=self.user)
            self.momento_window.closed.connect(self.show)
            self.momento_window.show()
            self.open_module_windows[module_name] = self.momento_window
            self.hide()
        elif module_name == "grupo_actividad":
            self.grupo_window = GrupoActividadUI(db_config=self.db_config, user_data=self.user)
            self.grupo_window.closed.connect(self.show)
            self.grupo_window.show()
            self.open_module_windows[module_name] = self.grupo_window
            self.hide()
        elif module_name == "constancias":
            self.constancia = MainMenuApp(db_config=self.db_config, user_data=self.user)
            self.constancia.closed.connect(self.show)
            self.constancia.show()
            self.open_module_windows[module_name] = self.constancia
            self.hide()
        elif module_name == "secciones":
            self.secciones = ModuloInstitucion(db_config=self.db_config, user_data=self.user)
            self.secciones.closed.connect(self.show)
            self.secciones.show()
            self.open_module_windows[module_name] = self.secciones
            self.hide()
        elif module_name == "matricula":
            self.matricula_window = MatriculaApp(db_config=self.db_config, user_data=self.user)
            self.matricula_window.closed.connect(self.show)
            self.matricula_window.show()
            self.open_module_windows[module_name] = self.matricula_window
            self.hide()
        elif module_name == "evaluaciones":
            self.evaluaciones_window = GestionNotasWindow(db_config=self.db_config, user_data=self.user)
            self.evaluaciones_window.closed.connect(self.show)
            self.evaluaciones_window.show()
            self.open_module_windows[module_name] = self.evaluaciones_window
            self.hide()
        else:
            QMessageBox.information(self, "Módulo Seleccionado", f"Has seleccionado el módulo: {module_name.replace('_', ' ').title()} (Funcionalidad no implementada aún).")

    def logout(self):
        """
        Cierra la ventana actual y abre una nueva ventana de login.
        """
        # Cierra todas las ventanas de módulos abiertas antes de cerrar la principal
        for window in list(self.open_module_windows.values()): # Usar list() para evitar RuntimeError: dictionary changed size during iteration
            if window and window.isVisible(): # Verificar si la ventana existe y es visible
                try:
                    window.close()
                except Exception as e:
                    print(f"Error al cerrar ventana de módulo: {e}")
        self.close()
        # Importación local para evitar circular dependencies
        # Asumiendo que LoginWindow está en el archivo principal (e.g., login.py)
        from __main__ import LoginWindow 
        self.login_window = LoginWindow() # LoginWindow ya carga su propia db_config
        self.login_window.show()

# Bloque para ejecutar la aplicación (eliminado para no usar simulación)
# if __name__ == '__main__':
#     app = QApplication(sys.argv)

#     # Simular una configuración de DB y datos de usuario para probar
#     test_db_config = {
#         'host': 'localhost',
#         'database': 'Sigme',
#         'user': 'Diego',
#         'password': 'Diego-78',
#         'port': '5432'
#     }
#     test_user_data = {
#         'id': 1,
#         'codigo_usuario': 'testuser',
#         'cedula_personal': 'V-12345678',
#         'rol': 'control de estudio', # Cambia esto para probar diferentes roles
#         'estado': 'activo',
#         'debe_cambiar_clave': False
#     }

#     main_window = GeneralMainWindow(db_config=test_db_config, user_data=test_user_data)
#     main_window.show()
#     sys.exit(app.exec())
