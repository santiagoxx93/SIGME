import sys
import psycopg2
from psycopg2 import Error
from datetime import date
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDateEdit, QComboBox, QTextEdit, QHeaderView
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QIntValidator, QDoubleValidator

class DatabaseManager:
    """Clase para manejar la conexión y operaciones con la base de datos PostgreSQL."""
    def __init__(self, db_config): # Aceptar un diccionario db_config
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Establece la conexión a la base de datos PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_config.get('database'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password'),
                host=self.db_config.get('host'),
                port=self.db_config.get('port')
            )
            self.cursor = self.conn.cursor()
            print(f"Conexión a la base de datos '{self.db_config.get('database')}' establecida con éxito.")
        except Error as e:
            print(f"Error al conectar a la base de datos '{self.db_config.get('database')}': {e}")
            self.conn = None
            self.cursor = None

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")

    def create_momento_evaluativo_table(self):
        """Crea la tabla Momento_Evaluativo si no existe."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS Momento_Evaluativo (
            Numero INT PRIMARY KEY,
            Codigo_ano_escolar VARCHAR(20) NOT NULL,
            Nombre VARCHAR(100) NOT NULL,
            Fecha_inicio DATE NOT NULL,
            Fecha_fin DATE NOT NULL,
            Porcentaje FLOAT NOT NULL,
            Estado CHAR(1) NOT NULL DEFAULT 'A',
            Observaciones TEXT,
            -- Asumiendo una tabla AÑO_ESCOLAR para la FK.
            -- Si tienes una tabla ANO_ESCOLAR, descomenta la siguiente línea:
            -- FOREIGN KEY (Codigo_ano_escolar) REFERENCES ANO_ESCOLAR(codigo),
            CHECK (Estado IN ('A', 'C'))
        );
        """
        try:
            self.cursor.execute(create_table_query)
            self.conn.commit()
            print("Tabla 'Momento_Evaluativo' verificada/creada con éxito.")
        except Error as e:
            print(f"Error al crear la tabla 'Momento_Evaluativo': {e}")
            if self.conn:
                self.conn.rollback()

    def insert_momento_evaluativo(self, numero, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado='A', observaciones=None):
        """Inserta un nuevo momento evaluativo."""
        insert_query = """
        INSERT INTO Momento_Evaluativo (Numero, Codigo_ano_escolar, Nombre, Fecha_inicio, Fecha_fin, Porcentaje, Estado, Observaciones)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        try:
            self.cursor.execute(insert_query, (numero, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones))
            self.conn.commit()
            print(f"Momento evaluativo {nombre} insertado con éxito.")
            return True
        except Error as e:
            print(f"Error al insertar momento evaluativo: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def update_momento_evaluativo(self, numero, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones):
        """Actualiza un momento evaluativo existente."""
        update_query = """
        UPDATE Momento_Evaluativo
        SET Codigo_ano_escolar = %s, Nombre = %s, Fecha_inicio = %s, Fecha_fin = %s, Porcentaje = %s, Estado = %s, Observaciones = %s
        WHERE Numero = %s;
        """
        try:
            self.cursor.execute(update_query, (codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones, numero))
            self.conn.commit()
            print(f"Momento evaluativo {numero} actualizado con éxito.")
            return True
        except Error as e:
            print(f"Error al actualizar momento evaluativo: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def delete_momento_evaluativo(self, numero):
        """Elimina un momento evaluativo."""
        delete_query = """
        DELETE FROM Momento_Evaluativo WHERE Numero = %s;
        """
        try:
            self.cursor.execute(delete_query, (numero,))
            self.conn.commit()
            print(f"Momento evaluativo {numero} eliminado con éxito.")
            return True
        except Error as e:
            print(f"Error al eliminar momento evaluativo: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def fetch_all_momentos_evaluativos(self):
        """Recupera todos los momentos evaluativos."""
        select_query = "SELECT Numero, Codigo_ano_escolar, Nombre, Fecha_inicio, Fecha_fin, Porcentaje, Estado, Observaciones FROM Momento_Evaluativo ORDER BY Numero;"
        try:
            self.cursor.execute(select_query)
            return self.cursor.fetchall()
        except Error as e:
            print(f"Error al recuperar momentos evaluativos: {e}")
            return []

    def check_total_percentage_for_year(self, codigo_ano_escolar, current_momento_numero=None):
        """Verifica que la suma de porcentajes para un año escolar sea 100."""
        query = """
        SELECT COALESCE(SUM(Porcentaje), 0.0) FROM Momento_Evaluativo
        WHERE Codigo_ano_escolar = %s
        """
        params = [codigo_ano_escolar]
        if current_momento_numero is not None:
            query += " AND Numero != %s"
            params.append(current_momento_numero)

        try:
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            return result[0] if result else 0.0
        except Error as e:
            print(f"Error al verificar el total de porcentajes: {e}")
            return 0.0

class MomentoEvaluativoApp(QWidget):
    """Clase principal de la aplicación con la interfaz de usuario."""
    closed = pyqtSignal() # Señal para indicar que el módulo se cerró

    def __init__(self, db_config, user_data): # Aceptar db_config y user_data aquí
        super().__init__()
        self.db_config = db_config # Almacenar db_config si es necesario para futuras referencias
        self.user_data = user_data # Almacenar user_data
        self.db = DatabaseManager(self.db_config) # Pasar el diccionario db_config
        if not self.db.conn:
            QMessageBox.critical(self, "Error de Conexión", "No se pudo conectar a la base de datos. Verifique los parámetros.")
            sys.exit(1) # Salir si no hay conexión
        self.db.create_momento_evaluativo_table() # Asegura que la tabla exista

        self.setWindowTitle("Gestión de Momentos Evaluativos")
        self.setGeometry(100, 100, 1000, 600)
        self.setObjectName("MomentoEvaluativoAppWindow") # Asignar un objectName a la ventana principal
        self.init_ui()
        self.apply_styles() # Aplicar estilos después de inicializar la UI
        self.load_momentos()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # --- Botón para volver al menú principal ---
        self.back_button = QPushButton("Volver al Menú Principal")
        self.back_button.setObjectName("backButton") # Para aplicar estilos específicos
        self.back_button.clicked.connect(self.return_to_main_menu)
        
        # Añadir el botón al inicio del layout principal
        main_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # --- Formulario de entrada ---
        form_layout = QVBoxLayout()
        form_grid = QHBoxLayout() # Usaremos un layout horizontal para organizar mejor los campos en dos columnas

        # Columna 1
        col1_layout = QVBoxLayout()
        col1_layout.addWidget(QLabel("Número (PK):"))
        self.numero_input = QLineEdit()
        self.numero_input.setPlaceholderText("Ej: 1, 2, 3")
        self.numero_input.setValidator(QIntValidator()) # Solo números enteros
        col1_layout.addWidget(self.numero_input)

        col1_layout.addWidget(QLabel("Código Año Escolar (FK):"))
        self.codigo_ano_escolar_input = QLineEdit()
        self.codigo_ano_escolar_input.setPlaceholderText("Ej: 2024-2025")
        col1_layout.addWidget(self.codigo_ano_escolar_input)

        col1_layout.addWidget(QLabel("Nombre:"))
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: Primer Momento")
        col1_layout.addWidget(self.nombre_input)

        col1_layout.addWidget(QLabel("Fecha Inicio:"))
        self.fecha_inicio_input = QDateEdit(calendarPopup=True)
        self.fecha_inicio_input.setDate(QDate.currentDate())
        col1_layout.addWidget(self.fecha_inicio_input)

        # Columna 2
        col2_layout = QVBoxLayout()
        col2_layout.addWidget(QLabel("Fecha Fin:"))
        self.fecha_fin_input = QDateEdit(calendarPopup=True)
        self.fecha_fin_input.setDate(QDate.currentDate())
        col2_layout.addWidget(self.fecha_fin_input)

        col2_layout.addWidget(QLabel("Porcentaje (%):"))
        self.porcentaje_input = QLineEdit()
        self.porcentaje_input.setPlaceholderText("Ej: 30.5")
        # Validator para números flotantes (0-100) con hasta 2 decimales
        self.porcentaje_input.setValidator(QDoubleValidator(0.0, 100.0, 2, self))
        col2_layout.addWidget(self.porcentaje_input)

        col2_layout.addWidget(QLabel("Estado:"))
        self.estado_combo = QComboBox()
        self.estado_combo.addItems(["A (Activo)", "C (Cerrado)"])
        col2_layout.addWidget(self.estado_combo)

        col2_layout.addWidget(QLabel("Observaciones:"))
        self.observaciones_input = QTextEdit()
        self.observaciones_input.setPlaceholderText("Notas adicionales sobre el momento...")
        col2_layout.addWidget(self.observaciones_input)

        form_grid.addLayout(col1_layout)
        form_grid.addLayout(col2_layout)
        form_layout.addLayout(form_grid)

        # --- Botones de acción ---
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Guardar")
        self.save_button.clicked.connect(self.save_momento)
        button_layout.addWidget(self.save_button)

        self.update_button = QPushButton("Actualizar")
        self.update_button.clicked.connect(self.update_momento)
        self.update_button.setEnabled(False) # Deshabilitado por defecto
        button_layout.addWidget(self.update_button)

        self.delete_button = QPushButton("Eliminar")
        self.delete_button.clicked.connect(self.delete_momento)
        self.delete_button.setEnabled(False) # Deshabilitado por defecto
        button_layout.addWidget(self.delete_button)

        self.clear_button = QPushButton("Limpiar Formulario")
        self.clear_button.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_button)

        form_layout.addLayout(button_layout)
        main_layout.addLayout(form_layout)

        # --- Tabla de momentos evaluativos ---
        self.table = QTableWidget()
        self.table.setColumnCount(8) # Numero, Codigo_ano_escolar, Nombre, Fecha_inicio, Fecha_fin, Porcentaje, Estado, Observaciones
        self.table.setHorizontalHeaderLabels([
            "Número", "Año Escolar", "Nombre", "Fecha Inicio",
            "Fecha Fin", "Porcentaje", "Estado", "Observaciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Ajusta las columnas al tamaño
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.populate_form_from_table)
        main_layout.addWidget(self.table)

        self.setLayout(main_layout)

    def apply_styles(self):
        """Aplica los estilos visuales a la ventana y sus widgets."""
        style_sheet = """
        #MomentoEvaluativoAppWindow { /* Estilo específico para la ventana principal */
            background-color: #e4eaf4; /* Fondo claro */
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #1c355b; /* Texto principal oscuro */
        }

        QLabel {
            color: #1c355b; /* Etiquetas de texto oscuro */
            font-weight: bold;
            margin-top: 5px;
            margin-bottom: 2px;
        }

        QLineEdit, QDateEdit, QComboBox, QTextEdit {
            background-color: #f8fbfd; /* Fondo de campos de entrada más claro */
            border: 1px solid #b3cbdc; /* Borde suave */
            border-radius: 5px;
            padding: 8px;
            selection-background-color: #7089a7; /* Color de selección */
            color: #1c355b;
        }

        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #7089a7; /* Borde más pronunciado al enfocar */
        }

        QPushButton {
            background-color: #7089a7; /* Color principal para botones */
            color: white; /* Texto blanco en botones */
            border: none;
            border-radius: 8px;
            padding: 10px 15px;
            font-weight: bold;
            min-width: 100px;
            margin: 5px;
        }

        QPushButton:hover {
            background-color: #1c355b; /* Color oscuro al pasar el ratón */
            border: 1px solid #b3cbdc;
        }

        QPushButton:pressed {
            background-color: #b3cbdc; /* Color más claro al presionar */
        }

        QPushButton:disabled {
            background-color: #cccccc; /* Color para botones deshabilitados */
            color: #666666;
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


        QTableWidget {
            background-color: #f8fbfd; /* Fondo de tabla claro */
            border: 1px solid #b3cbdc;
            border-radius: 8px;
            gridline-color: #b3cbdc; /* Líneas de la cuadrícula */
            selection-background-color: #b3cbdc; /* Color de selección de fila */
            selection-color: #1c355b; /* Color de texto de selección */
        }

        QTableWidget::item {
            padding: 5px;
        }

        QTableWidget QHeaderView::section {
            background-color: #1c355b; /* Fondo del encabezado de la tabla oscuro */
            color: white; /* Texto del encabezado blanco */
            padding: 8px;
            border: 1px solid #b3cbdc;
            font-weight: bold;
        }

        QTableWidget QHeaderView::section:horizontal {
            border-bottom: 2px solid #7089a7; /* Borde inferior para encabezados horizontales */
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: #b3cbdc;
            border-left-style: solid;
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
        }

        QComboBox::down-arrow {
            image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAAVUlEQVQ4jWNgoBAw4gYgD4gFo+D/BwMDw/9/BwMDAwMDAwMDw8/AwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDABgAmkX6Vn6oAAAAASUVORK5CYII=); /* Flecha para ComboBox */
        }
        """
        self.setStyleSheet(style_sheet) # Aplicar la hoja de estilos a esta ventana

    def load_momentos(self):
        """Carga los momentos evaluativos desde la BD y los muestra en la tabla."""
        momentos = self.db.fetch_all_momentos_evaluativos()
        self.table.setRowCount(len(momentos))
        for row_idx, momento in enumerate(momentos):
            for col_idx, data in enumerate(momento):
                item = QTableWidgetItem(str(data))
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable) # Hacer que las celdas no sean editables directamente
                self.table.setItem(row_idx, col_idx, item)

    def clear_form(self):
        """Limpia todos los campos del formulario."""
        self.numero_input.clear()
        self.codigo_ano_escolar_input.clear()
        self.nombre_input.clear()
        self.fecha_inicio_input.setDate(QDate.currentDate())
        self.fecha_fin_input.setDate(QDate.currentDate())
        self.porcentaje_input.clear()
        self.estado_combo.setCurrentIndex(0) # 'A (Activo)'
        self.observaciones_input.clear()
        self.save_button.setEnabled(True)
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.numero_input.setReadOnly(False) # Habilitar edición del número para nuevas entradas
        self.table.clearSelection() # Deseleccionar cualquier fila

    def populate_form_from_table(self):
        """Rellena el formulario con los datos de la fila seleccionada."""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.clear_form() # Si no hay selección, limpiar el formulario
            return

        row = selected_rows[0].row() # Obtener la fila seleccionada
        self.numero_input.setText(self.table.item(row, 0).text())
        self.codigo_ano_escolar_input.setText(self.table.item(row, 1).text())
        self.nombre_input.setText(self.table.item(row, 2).text())

        fecha_inicio_str = self.table.item(row, 3).text()
        self.fecha_inicio_input.setDate(QDate.fromString(fecha_inicio_str, "yyyy-MM-dd"))

        fecha_fin_str = self.table.item(row, 4).text()
        self.fecha_fin_input.setDate(QDate.fromString(fecha_fin_str, "yyyy-MM-dd"))

        self.porcentaje_input.setText(self.table.item(row, 5).text())

        estado_text = self.table.item(row, 6).text()
        # Ajustar para mostrar "A (Activo)" o "C (Cerrado)"
        self.estado_combo.setCurrentText(f"{estado_text} ({'Activo' if estado_text == 'A' else 'Cerrado'})")

        observaciones_text = self.table.item(row, 7).text()
        self.observaciones_input.setText(observaciones_text)

        self.save_button.setEnabled(False)
        self.update_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.numero_input.setReadOnly(True) # No permitir editar el número si se está actualizando

    def validate_inputs(self, is_update=False):
        """Valida que los campos requeridos no estén vacíos y que las fechas sean válidas."""
        numero_text = self.numero_input.text().strip()
        codigo_ano_escolar = self.codigo_ano_escolar_input.text().strip()
        nombre = self.nombre_input.text().strip()
        porcentaje_text = self.porcentaje_input.text().strip()
        fecha_inicio = self.fecha_inicio_input.date()
        fecha_fin = self.fecha_fin_input.date()

        if not numero_text and not is_update: # Número es PK y es requerido para guardar
            QMessageBox.warning(self, "Error de Validación", "El campo 'Número' es obligatorio.")
            return False
        if not codigo_ano_escolar:
            QMessageBox.warning(self, "Error de Validación", "El campo 'Código Año Escolar' es obligatorio.")
            return False
        if not nombre:
            QMessageBox.warning(self, "Error de Validación", "El campo 'Nombre' es obligatorio.")
            return False
        if not porcentaje_text:
            QMessageBox.warning(self, "Error de Validación", "El campo 'Porcentaje' es obligatorio.")
            return False

        try:
            porcentaje = float(porcentaje_text)
            if not (0 <= porcentaje <= 100):
                QMessageBox.warning(self, "Error de Validación", "El 'Porcentaje' debe estar entre 0 y 100.")
                return False
        except ValueError:
            QMessageBox.warning(self, "Error de Validación", "El 'Porcentaje' debe ser un número válido.")
            return False

        if fecha_inicio > fecha_fin:
            QMessageBox.warning(self, "Error de Validación", "La 'Fecha Inicio' no puede ser posterior a la 'Fecha Fin'.")
            return False

        return True

    def get_form_data(self):
        """Recupera los datos del formulario."""
        numero = int(self.numero_input.text()) if self.numero_input.text().strip() else None
        codigo_ano_escolar = self.codigo_ano_escolar_input.text().strip()
        nombre = self.nombre_input.text().strip()
        fecha_inicio = self.fecha_inicio_input.date().toString("yyyy-MM-dd")
        fecha_fin = self.fecha_fin_input.date().toString("yyyy-MM-dd")
        porcentaje = float(self.porcentaje_input.text())
        estado = self.estado_combo.currentText()[0] # 'A' o 'C'
        observaciones = self.observaciones_input.toPlainText().strip()
        return numero, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones

    def save_momento(self):
        """Guarda un nuevo momento evaluativo."""
        if not self.validate_inputs():
            return

        numero, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones = self.get_form_data()

        # Validar la suma de porcentajes
        current_sum = self.db.check_total_percentage_for_year(codigo_ano_escolar)
        if (current_sum + porcentaje) > 100.001: # Pequeña tolerancia para errores de flotante
            QMessageBox.warning(self, "Error de Porcentaje", f"La suma de porcentajes para el año escolar '{codigo_ano_escolar}' (incluyendo este momento) excedería 100%. Suma actual: {current_sum:.2f}%")
            return

        if self.db.insert_momento_evaluativo(numero, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones):
            QMessageBox.information(self, "Éxito", "Momento evaluativo guardado correctamente.")
            self.clear_form()
            self.load_momentos()
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar el momento evaluativo. Posiblemente el Número ya existe para ese año escolar o hay un problema de conexión.")

    def update_momento(self):
        """Actualiza un momento evaluativo existente."""
        if not self.validate_inputs(is_update=True):
            return

        numero_original = int(self.numero_input.text()) # El número no cambia en update
        _, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones = self.get_form_data()

        # Validar la suma de porcentajes para el año escolar, excluyendo el momento actual
        current_sum = self.db.check_total_percentage_for_year(codigo_ano_escolar, numero_original)
        if (current_sum + porcentaje) > 100.001:
            QMessageBox.warning(self, "Error de Porcentaje", f"La suma de porcentajes para el año escolar '{codigo_ano_escolar}' (incluyendo este momento) excedería 100%. Suma actual (sin este momento): {current_sum:.2f}%")
            return

        if self.db.update_momento_evaluativo(numero_original, codigo_ano_escolar, nombre, fecha_inicio, fecha_fin, porcentaje, estado, observaciones):
            QMessageBox.information(self, "Éxito", "Momento evaluativo actualizado correctamente.")
            self.clear_form()
            self.load_momentos()
        else:
            QMessageBox.critical(self, "Error", "No se pudo actualizar el momento evaluativo.")

    def delete_momento(self):
        """Elimina el momento evaluativo seleccionado."""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Por favor, seleccione un momento para eliminar.")
            return

        reply = QMessageBox.question(self, 'Confirmar Eliminación',
                                     "¿Está seguro de que desea eliminar este momento evaluativo?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            row = selected_rows[0].row()
            numero_to_delete = int(self.table.item(row, 0).text())
            if self.db.delete_momento_evaluativo(numero_to_delete):
                QMessageBox.information(self, "Éxito", "Momento evaluativo eliminado correctamente.")
                self.clear_form()
                self.load_momentos()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el momento evaluativo.")

    def return_to_main_menu(self):
        """Emite la señal de cierre y cierra la ventana para volver al menú principal."""
        self.closed.emit() # Emitir la señal de que la ventana se está cerrando
        self.close() # Cerrar la ventana actual

    def closeEvent(self, event):
        """Maneja el cierre de la aplicación para cerrar la conexión a la BD y emitir la señal."""
        self.db.close()
        self.closed.emit() # Asegurarse de que la señal se emita también al cerrar con la 'X'
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Configuración de la base de datos (simulando la lectura de db_connection.conf)
    db_config = {
        'host': 'localhost',
        'database': 'bd', # Asegúrate de que esta DB exista y el usuario tenga permisos
        'user': 'postgres',
        'password': '12345678', # ¡IMPORTANTE! Reemplaza con tu contraseña real
        'port': '5432'
    }

    # Datos de usuario simulados (reemplaza con datos reales si es necesario)
    test_user_data = {
        'id': 1,
        'username': 'testuser',
        'role': 'admin'
    }

    window = MomentoEvaluativoApp(db_config, test_user_data) # Pasar el diccionario db_config y user_data
    window.show()
    sys.exit(app.exec())
