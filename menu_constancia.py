import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal # Importar pyqtSignal

# Importa tus aplicaciones de Constancias
# Asegúrate de que los constructores de estas clases acepten 'db_config' y 'user_data'
from constancia_asistencia_app import ConstanciaAsistenciaApp
from constancias_retiro import MainWindow # MainWindow de Constancia de Retiro
from constancia_prosecucion import ConstanciaApp
from constancia_titulo_app import ConstanciaApp as ConstanciaTituloApp
from constancia_estudio import ConstanciaApp as ConstanciaEstudioApp
from constancia_labor_social import ConstanciaApp as ConstanciaLaborSocialApp

# Si tienes un DBManager centralizado en otro archivo, puedes importarlo aquí.
# Por ahora, asumimos que cada módulo de constancia gestionará su propia instancia de DBManager.
# from db_manager import DBManager # Descomentar si usas un DBManager global

class MainMenuApp(QWidget):
    closed = pyqtSignal() # Definir la señal 'closed'

    def __init__(self, db_config, user_data): # Aceptar db_config y user_data
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data # Almacenar user_data para pasarlo a los módulos

        # Las instancias de DBManager y CertificateGenerator ahora serán manejadas
        # por cada módulo de constancia individualmente, usando el db_config pasado.
        # Por lo tanto, se eliminan las inicializaciones aquí.

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        """Inicializa la interfaz de usuario del menú principal."""
        self.setWindowTitle('Menú Principal de Constancias')
        self.setGeometry(200, 200, 400, 350) # Tamaño de la ventana del menú

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Centrar los elementos verticalmente

        title_label = QLabel('Seleccione el tipo de Constancia a Generar:')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20) # Espacio después del título

        # Lista de botones con sus textos y si están habilitados
        buttons_info = [
            ("Constancia de Asistencia", True),
            ("Constancia de Retiro", True),
            ("Constancia de Labor Social", True),
            ("Constancia de Título", True),
            ("Constancia de Estudio", True),
            ("Constancia de Prosecución", True),
        ]

        # Crear y añadir los botones
        self.buttons = {}
        for text, enabled in buttons_info:
            button = QPushButton(text)
            button.setEnabled(enabled)
            # Pasar db_config y user_data a la función que abre la pantalla
            button.clicked.connect(lambda _, t=text: self.open_constancia_screen(t))
            main_layout.addWidget(button)
            self.buttons[text] = button
            main_layout.addSpacing(10) # Espacio entre botones

        self.setLayout(main_layout)

    def apply_styles(self):
        """Aplica estilos QSS al menú principal."""
        self.setStyleSheet("""
            QWidget {
                background-color: #e4eaf4;
                color: #1c355b;
                font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 15px;
            }

            QLabel {
                color: #1c355b;
                font-weight: bold;
                font-size: 18px;
                padding: 10px;
            }

            QPushButton {
                background-color: #1c355b;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 16px;
                min-height: 40px;
                margin: 5px 50px;
            }

            QPushButton:hover {
                background-color: #7089a7;
            }

            QPushButton:pressed {
                background-color: #1c355b;
            }

            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

    def open_constancia_screen(self, constancia_type):
        """Abre la pantalla de la constancia seleccionada."""
        # Se asume que todas las clases de Constancia ahora aceptan db_config y user_data
        if constancia_type == "Constancia de Asistencia":
            self.constancia_asistencia_app = ConstanciaAsistenciaApp(db_config=self.db_config, user_data=self.user_data)
            self.constancia_asistencia_app.show()
            # self.hide() # Puedes ocultar el menú principal si lo deseas
        elif constancia_type == "Constancia de Retiro":
            # MainWindow de Constancia de Retiro ahora debe aceptar db_config y user_data
            self.constancia_retiro_app = MainWindow(db_config=self.db_config, user_data=self.user_data)
            self.constancia_retiro_app.show()
            # self.hide()
        elif constancia_type == "Constancia de Prosecución":
            self.constancia_prosecucion_app = ConstanciaApp(db_config=self.db_config, user_data=self.user_data)
            self.constancia_prosecucion_app.show()
            # self.hide()
        elif constancia_type == "Constancia de Título":
            self.constancia_titulo_app = ConstanciaTituloApp(db_config=self.db_config, user_data=self.user_data)
            self.constancia_titulo_app.show()
            # self.hide()
        elif constancia_type == "Constancia de Estudio":
            self.constancia_estudio_app = ConstanciaEstudioApp(db_config=self.db_config, user_data=self.user_data)
            self.constancia_estudio_app.show()
            # self.hide()
        elif constancia_type == "Constancia de Labor Social":
            self.constancia_labor_social_app = ConstanciaLaborSocialApp(db_config=self.db_config, user_data=self.user_data)
            self.constancia_labor_social_app.show()
            # self.hide()
        else:
            QMessageBox.information(self, 'Función No Disponible',
                                    f'La pantalla de "{constancia_type}" aún no ha sido implementada.')

    def closeEvent(self, event):
        """
        Maneja el evento de cierre de la ventana principal y emite la señal 'closed'.
        Cada aplicación de constancia es responsable de cerrar su propia conexión a la DB
        en su respectivo closeEvent. Por lo tanto, no es necesario cerrar conexiones aquí.
        """
        self.closed.emit() # Emitir la señal al cerrar la ventana
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Configuración centralizada de la base de datos
    # ¡Asegúrate de que esta configuración coincida con la de tu base de datos real!
    db_config = {
        "database": "bd",
        "user": "postgres",
        "password": "12345678",
        "host": "localhost",
        "port": "5432"
    }

    # Datos de usuario simulados (ajusta según tu estructura de usuario)
    user_data = {
        'id': 1,
        'username': 'admin_menu',
        'role': 'administrador'
    }

    main_menu = MainMenuApp(db_config=db_config, user_data=user_data)
    main_menu.show()
    sys.exit(app.exec())
