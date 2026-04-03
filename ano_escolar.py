import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel,
                             QPushButton, QMessageBox, QTableWidget,
                             QTableWidgetItem, QHBoxLayout, QHeaderView,
                             QLineEdit, QDateEdit, QComboBox, QGridLayout, QCheckBox, QApplication) # Importar QApplication
from PyQt6.QtCore import Qt, QDate, pyqtSignal # Importar pyqtSignal

# --- Definición de la Paleta de Colores (Puedes importarla de un archivo común si lo tienes) ---
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


class AnoEscolarApp(QMainWindow):
    """
    Ventana para la gestión de Años Escolares.
    Permite visualizar, agregar, modificar y eliminar registros de años escolares.
    """
    closed = pyqtSignal() # <--- ¡Añadida la señal 'closed'!

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data # Almacenar los datos del usuario si son necesarios
        self.init_ui()
        self.load_anos_escolares() # Cargar datos al iniciar
        self.showFullScreen() # <--- Mostrar en pantalla completa

    def get_connection(self):
        """
        Intenta establecer y devolver una conexión a la base de datos PostgreSQL.
        Maneja errores de conexión.
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Conexión",
                                 f"No se pudo conectar a la base de datos: {e}")
            return None

    def init_ui(self):
        """
        Inicializa la interfaz de usuario de la ventana de Año Escolar.
        """
        self.setWindowTitle(f'Gestión de Año Escolar - {self.user_data["codigo_usuario"]}')
        # self.setGeometry(150, 150, 1100, 750) # Ya no es necesario si se usa showFullScreen()
        self.setStyleSheet(self.get_styles())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Título de la ventana
        title_label = QLabel('Gestión de Años Escolares')
        title_label.setObjectName('titleLabel')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Formulario de entrada
        form_layout = QGridLayout()
        form_layout.setSpacing(10)

        # Campo Código de Año (mapeado a 'codigo' en la DB)
        form_layout.addWidget(QLabel('Código de Año:'), 0, 0)
        self.ano_input = QLineEdit()
        self.ano_input.setPlaceholderText('Ej: 2023-2024')
        self.ano_input.setObjectName('inputField')
        form_layout.addWidget(self.ano_input, 0, 1)

        # Campo Descripción
        form_layout.addWidget(QLabel('Descripción:'), 1, 0)
        self.descripcion_input = QLineEdit()
        self.descripcion_input.setPlaceholderText('Ej: Año Escolar 2023-2024')
        self.descripcion_input.setObjectName('inputField')
        form_layout.addWidget(self.descripcion_input, 1, 1)

        # Campo Año Inicio (entero)
        form_layout.addWidget(QLabel('Año Inicio (Numérico):'), 2, 0)
        self.ano_inicio_input = QLineEdit()
        self.ano_inicio_input.setPlaceholderText('Ej: 2023')
        self.ano_inicio_input.setObjectName('inputField')
        form_layout.addWidget(self.ano_inicio_input, 2, 1)

        # Campo Año Fin (entero)
        form_layout.addWidget(QLabel('Año Fin (Numérico):'), 3, 0)
        self.ano_fin_input = QLineEdit()
        self.ano_fin_input.setPlaceholderText('Ej: 2024')
        self.ano_fin_input.setObjectName('inputField')
        form_layout.addWidget(self.ano_fin_input, 3, 1)

        # Campo Fecha Inicio (Date)
        form_layout.addWidget(QLabel('Fecha Inicio:'), 4, 0)
        self.fecha_inicio_input = QDateEdit(calendarPopup=True)
        self.fecha_inicio_input.setDate(QDate.currentDate())
        self.fecha_inicio_input.setObjectName('dateField')
        form_layout.addWidget(self.fecha_inicio_input, 4, 1)

        # Campo Fecha Fin (Date)
        form_layout.addWidget(QLabel('Fecha Fin:'), 5, 0)
        self.fecha_fin_input = QDateEdit(calendarPopup=True)
        self.fecha_fin_input.setDate(QDate.currentDate().addYears(1)) # Por defecto un año después
        self.fecha_fin_input.setObjectName('dateField')
        form_layout.addWidget(self.fecha_fin_input, 5, 1)

        # Campo Estado (ComboBox)
        form_layout.addWidget(QLabel('Estado (Activo/Inactivo):'), 6, 0)
        self.estado_combo = QComboBox()
        self.estado_combo.addItems(['Activo', 'Inactivo'])
        self.estado_combo.setObjectName('inputField')
        form_layout.addWidget(self.estado_combo, 6, 1)

        # Campo Activo (Boolean)
        form_layout.addWidget(QLabel('Activo:'), 7, 0)
        self.activo_check = QCheckBox()
        self.activo_check.setObjectName('checkBoxField')
        form_layout.addWidget(self.activo_check, 7, 1)

        main_layout.addLayout(form_layout)

        # Botones de acción
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.add_button = QPushButton('Agregar Año Escolar')
        self.add_button.setObjectName('actionButton')
        self.add_button.clicked.connect(self.add_ano_escolar)
        button_layout.addWidget(self.add_button)

        self.update_button = QPushButton('Modificar Año Escolar')
        self.update_button.setObjectName('actionButton')
        self.update_button.clicked.connect(self.update_ano_escolar)
        button_layout.addWidget(self.update_button)

        self.delete_button = QPushButton('Eliminar Año Escolar')
        self.delete_button.setObjectName('deleteButton')
        self.delete_button.clicked.connect(self.delete_ano_escolar)
        button_layout.addWidget(self.delete_button)

        self.clear_button = QPushButton('Limpiar Campos')
        self.clear_button.setObjectName('clearButton')
        self.clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

        # Tabla de años escolares
        self.table = QTableWidget()
        self.table.setObjectName('dataTable')
        # Ajustado a 8 columnas: codigo, descripcion, ano_inicio, ano_fin, fecha_inicio, fecha_fin, estado, activo
        self.table.setColumnCount(8) 
        self.table.setHorizontalHeaderLabels(['Código', 'Descripción', 'Año Inicio', 'Año Fin', 'Fecha Inicio', 'Fecha Fin', 'Estado', 'Activo']) # Ajustado
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.display_selected_ano_escolar)
        main_layout.addWidget(self.table)

        # Botón para cerrar la ventana y volver al menú
        self.back_to_menu_button = QPushButton('Volver al Menú') # <--- Nuevo botón para volver al menú
        self.back_to_menu_button.setObjectName('closeButton') # Reutilizar estilo 'closeButton'
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        main_layout.addWidget(self.back_to_menu_button, alignment=Qt.AlignmentFlag.AlignRight)

    def get_styles(self):
        """
        Define y retorna los estilos QSS para la ventana de Año Escolar.
        """
        return f"""
            QMainWindow {{
                background-color: {COLOR_MAIN_BACKGROUND};
            }}
            #titleLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 24px;
                font-weight: bold;
                color: {COLOR_PRIMARY_DARK_BLUE};
                padding: 10px;
                background-color: {COLOR_OFF_WHITE};
                border-radius: 8px;
                margin-bottom: 15px;
            }}
            QLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            #inputField, #dateField, QComboBox {{
                padding: 10px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 5px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                background-color: {COLOR_WHITE};
                color: {COLOR_DARK_TEXT};
            }}
            #inputField:focus, #dateField:focus, QComboBox:focus {{
                border-color: {COLOR_ACCENT_BLUE};
                outline: none;
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTAuNDY0MSA2LjVMMTMuOTI4MiAzTDIuMDcxOCAzTDQuNTM1OSAxMC41TDcgMTBaIiBmaWxsPSIjMUMzNTVCIi8+Cjwvc3ZnPg==); /* Calendario SVG */
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
                width: 20px;
                padding-right: 5px;
            }}
            QComboBox::down-arrow {{
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgNS41TDcgOS41TDEwIDU.1IiBzdHJva2U9IiM0OTUwNTciIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
                width: 14px;
                height: 14px;
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 5px;
                background-color: {COLOR_WHITE};
                selection-background-color: {COLOR_ACCENT_BLUE};
                selection-color: {COLOR_WHITE};
            }}
            #actionButton {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
            }}
            #actionButton:hover {{
                background-color: {COLOR_ACCENT_BLUE};
            }}
            #actionButton:pressed {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
            }}
            #deleteButton {{
                background-color: {COLOR_ERROR_RED};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
            }}
            #deleteButton:hover {{
                background-color: #E04C3C;
            }}
            #deleteButton:pressed {{
                background-color: #C0392B;
            }}
            #clearButton {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
            }}
            #clearButton:hover {{
                background-color: #89A0BD;
            }}
            #clearButton:pressed {{
                background-color: #7089A7;
            }}
            #dataTable {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                selection-background-color: {COLOR_ACCENT_BLUE};
                selection-color: {COLOR_WHITE};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {COLOR_DARK_TEXT};
            }}
            #dataTable::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                color: {COLOR_WHITE};
                padding: 8px;
                border: 1px solid {COLOR_DEEP_DARK_BLUE};
                font-weight: bold;
            }}
            #closeButton {{
                background-color: {COLOR_DEEP_DARK_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 20px;
            }}
            #closeButton:hover {{
                background-color: #162a4d;
            }}
            #closeButton:pressed {{
                background-color: #10203a;
            }}
            #checkBoxField::indicator {{
                width: 18px;
                height: 18px;
                margin-right: 8px;
                border-radius: 4px;
            }}

            #checkBoxField::indicator:unchecked {{
                background: {COLOR_OFF_WHITE};
                border: 2px solid {COLOR_DEEP_DARK_BLUE};
            }}

            #checkBoxField::indicator:checked {{
                background: {COLOR_DEEP_DARK_BLUE};
                border: 2px solid {COLOR_DEEP_DARK_BLUE};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTggM0w0IDdMMiA1IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }}
        """

    def load_anos_escolares(self):
        """
        Carga los años escolares desde la base de datos y los muestra en la tabla.
        """
        conn = self.get_connection()
        if not conn:
            return

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Seleccionar todas las columnas relevantes
                cursor.execute("SELECT codigo, descripcion, ano_inicio, ano_fin, fecha_inicio, fecha_fin, estado, activo FROM ano_escolar ORDER BY codigo DESC")
                anos_escolares = cursor.fetchall()
                self.table.setRowCount(len(anos_escolares))
                for row_idx, ano_escolar in enumerate(anos_escolares):
                    self.table.setItem(row_idx, 0, QTableWidgetItem(ano_escolar['codigo']))
                    self.table.setItem(row_idx, 1, QTableWidgetItem(ano_escolar['descripcion'] if ano_escolar['descripcion'] is not None else ''))
                    self.table.setItem(row_idx, 2, QTableWidgetItem(str(ano_escolar['ano_inicio']) if ano_escolar['ano_inicio'] is not None else ''))
                    self.table.setItem(row_idx, 3, QTableWidgetItem(str(ano_escolar['ano_fin']) if ano_escolar['ano_fin'] is not None else ''))
                    self.table.setItem(row_idx, 4, QTableWidgetItem(ano_escolar['fecha_inicio'].strftime('%Y-%m-%d')))
                    self.table.setItem(row_idx, 5, QTableWidgetItem(ano_escolar['fecha_fin'].strftime('%Y-%m-%d')))
                    # Convertir 'estado' de char(1) a string completo
                    estado_display = 'Activo' if ano_escolar['estado'] == 'A' else 'Inactivo'
                    self.table.setItem(row_idx, 6, QTableWidgetItem(estado_display))
                    # Convertir 'activo' de boolean a string
                    activo_display = 'Sí' if ano_escolar['activo'] else 'No'
                    self.table.setItem(row_idx, 7, QTableWidgetItem(activo_display))
        except psycopg2.Error as e:
            QMessageBox.critical(self, "Error de Base de Datos", f"Error al cargar años escolares: {e}")
        finally:
            if conn:
                conn.close()

    def add_ano_escolar(self):
        """
        Agrega un nuevo año escolar a la base de datos.
        """
        ano_codigo = self.ano_input.text().strip()
        descripcion = self.descripcion_input.text().strip()
        ano_inicio_str = self.ano_inicio_input.text().strip()
        ano_fin_str = self.ano_fin_input.text().strip()
        fecha_inicio = self.fecha_inicio_input.date().toPyDate()
        fecha_fin = self.fecha_fin_input.date().toPyDate()
        estado_ui = self.estado_combo.currentText()
        estado_db = 'A' if estado_ui == 'Activo' else 'I'
        activo = self.activo_check.isChecked()

        if not ano_codigo or not fecha_inicio or not fecha_fin:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor, complete los campos obligatorios (Código de Año, Fechas).")
            return

        if fecha_inicio >= fecha_fin:
            QMessageBox.warning(self, "Fechas Inválidas", "La fecha de inicio debe ser anterior a la fecha de fin.")
            return
        
        # Validar y convertir ano_inicio y ano_fin a enteros
        try:
            ano_inicio = int(ano_inicio_str) if ano_inicio_str else None
            ano_fin = int(ano_fin_str) if ano_fin_str else None
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "Los campos 'Año Inicio' y 'Año Fin' deben ser números enteros.")
            return

        conn = self.get_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ano_escolar (codigo, descripcion, ano_inicio, ano_fin, fecha_inicio, fecha_fin, estado, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (ano_codigo, descripcion, ano_inicio, ano_fin, fecha_inicio, fecha_fin, estado_db, activo))
                conn.commit()
                QMessageBox.information(self, "Éxito", "Año escolar agregado correctamente.")
                self.clear_fields()
                self.load_anos_escolares()
        except psycopg2.IntegrityError as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de Integridad", f"Ya existe un año escolar con ese código: {e}")
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"Error al agregar año escolar: {e}")
        finally:
            if conn:
                conn.close()

    def update_ano_escolar(self):
        """
        Modifica el año escolar seleccionado en la base de datos.
        """
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un año escolar de la tabla para modificar.")
            return

        ano_escolar_codigo = self.table.item(selected_rows[0].row(), 0).text()
        
        ano_nuevo_codigo = self.ano_input.text().strip()
        descripcion = self.descripcion_input.text().strip()
        ano_inicio_str = self.ano_inicio_input.text().strip()
        ano_fin_str = self.ano_fin_input.text().strip()
        fecha_inicio = self.fecha_inicio_input.date().toPyDate()
        fecha_fin = self.fecha_fin_input.date().toPyDate()
        estado_ui = self.estado_combo.currentText()
        estado_db = 'A' if estado_ui == 'Activo' else 'I'
        activo = self.activo_check.isChecked()

        if not ano_nuevo_codigo or not fecha_inicio or not fecha_fin:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor, complete los campos obligatorios (Código de Año, Fechas).")
            return

        if fecha_inicio >= fecha_fin:
            QMessageBox.warning(self, "Fechas Inválidas", "La fecha de inicio debe ser anterior a la fecha de fin.")
            return
        
        # Validar y convertir ano_inicio y ano_fin a enteros
        try:
            ano_inicio = int(ano_inicio_str) if ano_inicio_str else None
            ano_fin = int(ano_fin_str) if ano_fin_str else None
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "Los campos 'Año Inicio' y 'Año Fin' deben ser números enteros.")
            return

        conn = self.get_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE ano_escolar SET codigo = %s, descripcion = %s, ano_inicio = %s, ano_fin = %s,
                                         fecha_inicio = %s, fecha_fin = %s, estado = %s, activo = %s
                    WHERE codigo = %s
                """, (ano_nuevo_codigo, descripcion, ano_inicio, ano_fin,
                      fecha_inicio, fecha_fin, estado_db, activo, ano_escolar_codigo))
                conn.commit()
                QMessageBox.information(self, "Éxito", "Año escolar modificado correctamente.")
                self.clear_fields()
                self.load_anos_escolares()
        except psycopg2.IntegrityError as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de Integridad", f"Ya existe un año escolar con ese código: {e}")
        except psycopg2.Error as e:
            conn.rollback()
            QMessageBox.critical(self, "Error de Base de Datos", f"Error al modificar año escolar: {e}")
        finally:
            if conn:
                conn.close()

    def delete_ano_escolar(self):
        """
        Elimina el año escolar seleccionado de la base de datos.
        """
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, seleccione un año escolar de la tabla para eliminar.")
            return

        ano_escolar_codigo = self.table.item(selected_rows[0].row(), 0).text()

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     "¿Está seguro de que desea eliminar este año escolar?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            conn = self.get_connection()
            if not conn:
                return

            try:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM ano_escolar WHERE codigo = %s", (ano_escolar_codigo,))
                    conn.commit()
                    QMessageBox.information(self, "Éxito", "Año escolar eliminado correctamente.")
                    self.clear_fields()
                    self.load_anos_escolares()
            except psycopg2.Error as e:
                conn.rollback()
                QMessageBox.critical(self, "Error de Base de Datos", f"Error al eliminar año escolar: {e}")
            finally:
                if conn:
                    conn.close()

    def display_selected_ano_escolar(self):
        """
        Muestra los datos del año escolar seleccionado en los campos de entrada.
        """
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            self.ano_input.setText(self.table.item(row, 0).text())
            self.descripcion_input.setText(self.table.item(row, 1).text())
            self.ano_inicio_input.setText(self.table.item(row, 2).text())
            self.ano_fin_input.setText(self.table.item(row, 3).text())
            self.fecha_inicio_input.setDate(QDate.fromString(self.table.item(row, 4).text(), 'yyyy-MM-dd'))
            self.fecha_fin_input.setDate(QDate.fromString(self.table.item(row, 5).text(), 'yyyy-MM-dd'))
            
            estado_display = self.table.item(row, 6).text()
            self.estado_combo.setCurrentText(estado_display)

            activo_display = self.table.item(row, 7).text()
            self.activo_check.setChecked(activo_display == 'Sí')
        else:
            self.clear_fields()

    def clear_fields(self):
        """
        Limpieza los campos del formulario.
        """
        self.ano_input.clear()
        self.descripcion_input.clear()
        self.ano_inicio_input.clear()
        self.ano_fin_input.clear()
        self.fecha_inicio_input.setDate(QDate.currentDate())
        self.fecha_fin_input.setDate(QDate.currentDate().addYears(1))
        self.estado_combo.setCurrentIndex(0) # Selecciona el primer elemento ('Activo')
        self.activo_check.setChecked(False) # Desmarcar el checkbox

    def go_back_to_menu(self):
        """
        Cierra esta ventana y emite una señal para que el menú principal se muestre.
        """
        self.close() # Cierra el QMainWindow actual
        # La señal 'closed' ya se emite en closeEvent, que es llamado por self.close()

    def closeEvent(self, event):
        """
        Sobrescribe el evento de cierre para emitir la señal 'closed'.
        """
        self.closed.emit() # Emitir la señal al cerrar la ventana
        super().closeEvent(event)

# Bloque para ejecutar la aplicación (solo para pruebas directas del módulo)
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
    
#     # Configurar estilo global para la aplicación
#     app.setStyle('Fusion')
    
#     # Aplicar estilos a los message boxes (si tienes una función para ello)
#     # setup_message_box_styles() 

#     # Simular una configuración de DB y datos de usuario para probar este módulo
#     test_db_config = {
#         'host': 'localhost',
#         'database': 'Sigme', # Usar la DB real de tu sistema
#         'user': 'Diego',
#         'password': 'Diego-78',
#         'port': '5432'
#     }
#     test_user_data = {
#         'id': '1',
#         'codigo_usuario': 'testuser',
#         'cedula_personal': 'V-12345678',
#         'rol': 'control de estudio',
#         'estado': 'activo',
#         'debe_cambiar_clave': False
#     }

#     # Instanciar AnoEscolarApp con la configuración de la DB
#     ano_escolar_app = AnoEscolarApp(db_config=test_db_config, user_data=test_user_data)
    
#     # No necesitas una QMainWindow externa para mostrarla si AnoEscolarApp ya es QMainWindow
#     # ano_escolar_app.show() # showFullScreen() ya se llama en __init__

#     sys.exit(app.exec())
