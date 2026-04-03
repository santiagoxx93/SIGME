import sys
from PyQt6.QtWidgets import QApplication

# Importa la ventana de login desde el archivo windows.py
from login import LoginWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion') # Configurar tema de la aplicación

    window = LoginWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()