import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QMessageBox, 
                             QDialog, QFormLayout, QTextEdit, QSpinBox,
                             QHeaderView, QFrame, QCheckBox, QComboBox, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QPalette, QColor

# --- Definición de la Paleta de Colores ---
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
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
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


class InstitucionApp(QMainWindow):
    """
    Ventana para la gestión de Instituciones.
    Permite visualizar, agregar, modificar y eliminar registros de instituciones.
    """
    closed = pyqtSignal() # Señal para indicar que la ventana se ha cerrado

    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        self.db = DatabaseConnection(self.db_config)
        
        # Inicializar info_label y otros widgets antes de setup_ui
        self.info_label = QLabel("Estado de la conexión...")
        self.info_label.setObjectName("infoLabel")
        self.btn_guardar = QPushButton() # Placeholder
        self.btn_guardar_cambios = QPushButton() # Placeholder
        self.btn_eliminar = QPushButton() # Placeholder

        self.init_db_connection_and_table()
        self.setup_ui()
        self.apply_styles() # Aplicar los estilos
        
        if self.db.connection and not self.db.connection.closed:
            self.load_registros() # Cargar registros al iniciar
        else:
            self.mostrar_mensaje_sin_bd()
        
        self.showFullScreen() # Mostrar en pantalla completa

    def init_db_connection_and_table(self):
        """
        Intenta conectar a la base de datos y crear la tabla 'institucion' si no existe.
        """
        print("Iniciando conexión y configuración de tabla 'institucion'...")
        if not self.db.connect():
            print("Fallo la conexión inicial a la base de datos.")
            return False

        print("Conexión exitosa, verificando/creando tabla 'institucion'...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS institucion (
            codigo_dea VARCHAR(50) PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL UNIQUE,
            direccion TEXT,
            telefono VARCHAR(20),
            municipio VARCHAR(100),
            estado VARCHAR(100),
            zona_educativa VARCHAR(50),
            director_actual VARCHAR(255),
            coordinador_academico VARCHAR(255),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        if self.db.execute_query(create_table_query):
            print("Tabla 'institucion' verificada/creada correctamente.")
            return True
        else:
            print("Error al crear la tabla 'institucion'.")
            self.db.disconnect()
            return False

    def mostrar_mensaje_sin_bd(self):
        """Muestra un mensaje cuando no hay conexión a la base de datos"""
        self.info_label.setText("Sin conexión a base de datos - No se pueden cargar/gestionar instituciones.")
        self.btn_guardar.setEnabled(False)
        self.btn_guardar_cambios.setEnabled(False)
        self.btn_eliminar.setEnabled(False)

    def setup_ui(self):
        self.setWindowTitle("SIGME2 | Gestión de Instituciones")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) # Layout principal horizontal

        # Menú lateral con botones para cambiar vistas
        menu_lateral = QVBoxLayout()
        self.btn_registrar = QPushButton("  ➕ Registrar")
        self.btn_registrar.clicked.connect(self.mostrar_formulario)
        self.btn_tabla = QPushButton("  📋 Ver Registros")
        self.btn_tabla.clicked.connect(self.mostrar_tabla)

        menu_lateral.addWidget(self.btn_registrar)
        menu_lateral.addWidget(self.btn_tabla)
        menu_lateral.addStretch()

        # Control de vistas: formulario y tabla
        self.stack = QStackedWidget()
        self.stack.addWidget(self._formulario_registro_widget()) # Usar un método privado para crear el widget
        self.stack.addWidget(self._tabla_registros_widget()) # Usar un método privado para crear el widget

        main_layout.addLayout(menu_lateral, 1)
        main_layout.addWidget(self.stack, 4)

        # Información (Movido aquí para ser parte del main_layout)
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_frame.setObjectName("infoFrame")
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.info_label) # self.info_label ya está inicializado en __init__
        info_frame.setLayout(info_layout)
        main_layout.addWidget(info_frame) # Añadir al layout principal

        # Botón para volver al menú principal
        self.back_to_menu_button = QPushButton('Volver al Menú')
        self.back_to_menu_button.setObjectName('backButton') # Usar un ObjectName para aplicar estilo
        self.back_to_menu_button.clicked.connect(self.go_back_to_menu)
        menu_lateral.addWidget(self.back_to_menu_button) # Añadir al menú lateral

    def _formulario_registro_widget(self):
        """
        Crea y retorna el widget con el formulario para registrar o editar instituciones.
        Incluye buscador, campos de entrada y botones de acción.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Área de búsqueda
        filtro_layout = QHBoxLayout()
        self.buscar_input = QLineEdit()
        self.buscar_input.setClearButtonEnabled(True)
        self.buscar_input.setPlaceholderText("Buscar por nombre o código DEA")
        self.buscar_input.returnPressed.connect(self.filtrar_tabla)

        self.btn_limpiar_busqueda = QPushButton("Limpiar")
        self.btn_limpiar_busqueda.clicked.connect(self.limpiar_busqueda)
        filtro_layout.addWidget(self.buscar_input)
        filtro_layout.addWidget(self.btn_limpiar_busqueda)
        layout.addLayout(filtro_layout)

        # Diccionario para almacenar los campos de entrada
        self.campos = {}
        # Definición de los campos y sus etiquetas
        campos_data = [
            ("codigo_dea", "Código DEA"),
            ("nombre", "Nombre"),
            ("direccion", "Dirección"),
            ("telefono", "Teléfono"),
            ("municipio", "Municipio"),
            ("estado", "Estado"), # Estado geográfico
            ("zona_educativa", "Zona Educativa"),
            ("director_actual", "Director Actual"),
            ("coordinador_academico", "Coordinador Académico")
        ]

        # Creación de etiquetas y campos de entrada
        for clave, texto in campos_data:
            label = QLabel(texto)
            entrada = QLineEdit()
            layout.addWidget(label)
            layout.addWidget(entrada)
            # Configuración específica para algunos campos
            if clave == "telefono":
                entrada.setInputMask("(9999)-999-99-99")
            elif clave == "zona_educativa":
                entrada.setInputMask("ZZ-999")
            self.campos[clave] = entrada
        
        # Eliminado: Checkbox para el estado activo
        # self.activo_check = QCheckBox("Activo")
        # self.activo_check.setChecked(True) # Por defecto activo
        # layout.addWidget(self.activo_check)

        # Botón para guardar una nueva institución
        self.btn_guardar = QPushButton("💾 Guardar Institución")
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self.guardar_institucion)

        # Botón para guardar cambios en edición
        self.btn_guardar_cambios = QPushButton("💾 Guardar Cambios")
        self.btn_guardar_cambios.setDefault(True)
        self.btn_guardar_cambios.setVisible(False)
        self.btn_guardar_cambios.clicked.connect(self.guardar_cambios)

        layout.addWidget(self.btn_guardar)
        layout.addWidget(self.btn_guardar_cambios)
        layout.addStretch()

        return widget

    def _tabla_registros_widget(self):
        """
        Crea y retorna el widget con la tabla que muestra todos los registros.
        Incluye botones para eliminar registros seleccionados.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Configuración de la tabla
        self.tabla = QTableWidget()
        self.tabla.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)
        # Ajustado a 9 columnas (eliminado 'activo')
        self.tabla.setColumnCount(9) 
        self.tabla.setHorizontalHeaderLabels([
            "Código DEA", "Nombre", "Dirección", "Teléfono",
            "Municipio", "Estado", "Zona Educativa", "Director", "Coordinador"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.itemDoubleClicked.connect(self.editar_registro_desde_tabla) # Para editar al doble click
        
        # Botón para eliminar registros seleccionados
        self.btn_eliminar = QPushButton("🗑️ Eliminar Seleccionado")
        self.btn_eliminar.clicked.connect(self.eliminar_registro)

        layout.addWidget(self.tabla)
        layout.addWidget(self.btn_eliminar)
        return widget

    def apply_styles(self):
        """
        Define y aplica los estilos QSS a la ventana de Institución y sus widgets.
        """
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLOR_MAIN_BACKGROUND};
            }}
            QLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: {COLOR_DEEP_DARK_BLUE};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                padding: 10px;
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 5px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                background-color: {COLOR_WHITE};
                color: {COLOR_DARK_TEXT};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border-color: {COLOR_ACCENT_BLUE};
                outline: none;
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                color: {COLOR_WHITE};
                border: none;
                border-radius: 12px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_DEEP_DARK_BLUE};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_MEDIUM_GRAYISH_BLUE};
                color: {COLOR_OFF_WHITE};
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
            QTableWidget {{
                background-color: {COLOR_WHITE};
                border: 1px solid {COLOR_LIGHT_GRAYISH_BLUE};
                border-radius: 8px;
                selection-background-color: {COLOR_ACCENT_BLUE};
                selection-color: {COLOR_WHITE};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: {COLOR_DARK_TEXT};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_PRIMARY_DARK_BLUE};
                color: {COLOR_WHITE};
                padding: 8px;
                border: 1px solid {COLOR_DEEP_DARK_BLUE};
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
            /* Eliminado: Estilos para #checkBoxField */
        """)

    def mostrar_formulario(self):
        """
        Muestra la vista del formulario para ingresar o editar datos.
        """
        self.stack.setCurrentIndex(0)
        self.preparar_formulario_nuevo() # Limpiar campos al mostrar el formulario

    def mostrar_tabla(self):
        """
        Muestra la vista de la tabla con los registros y recarga los datos.
        """
        self.stack.setCurrentIndex(1)
        self.load_registros()

    def preparar_formulario_nuevo(self):
        """
        Limpia y prepara el formulario para ingresar un nuevo registro.
        """
        for campo in self.campos.values():
            campo.clear()
        # Eliminado: self.activo_check.setChecked(True)
        self.campos["codigo_dea"].setReadOnly(False)
        self.btn_guardar_cambios.setVisible(False)
        self.btn_guardar.setVisible(True)
        self.edicion_codigo_dea = None
        self.buscar_input.setText("")
        # Restablecer estilos del buscador
        self.buscar_input.setStyleSheet("") 
        self.buscar_input.setToolTip("")

    def limpiar_busqueda(self):
        """
        Restablece el formulario y elimina filtros de búsqueda.
        """
        self.preparar_formulario_nuevo()
        self.load_registros() # Recargar la tabla sin filtros

    def guardar_institucion(self):
        """
        Guarda un nuevo registro en la base de datos.
        Valida que todos los campos estén completos.
        """
        datos = {k: v.text().strip() for k, v in self.campos.items()}
        # Eliminado: datos['activo'] = self.activo_check.isChecked()

        if any(not datos[k] for k in ["codigo_dea", "nombre", "direccion", "telefono", "municipio", "estado", "zona_educativa", "director_actual", "coordinador_academico"]):
            QMessageBox.warning(self, "Validación", "Por favor, completa todos los campos.")
            return
        
        query = """
        INSERT INTO institucion (codigo_dea, nombre, direccion, telefono, municipio, estado,
        zona_educativa, director_actual, coordinador_academico)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (datos['codigo_dea'], datos['nombre'], datos['direccion'], datos['telefono'],
                  datos['municipio'], datos['estado'], datos['zona_educativa'],
                  datos['director_actual'], datos['coordinador_academico']) # Eliminado: datos['activo']

        if self.db.execute_query(query, params):
            QMessageBox.information(self, "Éxito", "Institución registrada exitosamente.")
            self.preparar_formulario_nuevo()
            self.load_registros() # Recargar la tabla
        else:
            # El error ya es manejado por DatabaseConnection
            pass

    def filtrar_tabla(self):
        """
        Filtra los registros de la tabla según el texto de búsqueda.
        Si no se encuentra coincidencia, muestra mensaje informativo.
        """
        texto = self.buscar_input.text().strip().lower()
        self.btn_guardar_cambios.setVisible(False)
        self.btn_guardar.setVisible(True)

        if not texto:
            self.load_registros() # Recargar sin filtro
            return

        encontrado = False
        self.tabla.clearSelection() # Limpiar selección actual
        
        for i in range(self.tabla.rowCount()):
            codigo = self.tabla.item(i, 0).text().lower()
            nombre = self.tabla.item(i, 1).text().lower()
            match = texto in codigo or texto in nombre
            self.tabla.setRowHidden(i, not match)
            
            if match and not encontrado:
                # Si se encuentra una coincidencia, cargarla en el formulario
                self.mostrar_formulario()
                # Obtener los datos de la fila encontrada (ahora 9 columnas)
                valores = [self.tabla.item(i, j).text() for j in range(self.tabla.columnCount())]
                
                # Mapear los valores de la tabla a los campos del formulario
                self.campos["codigo_dea"].setText(valores[0])
                self.campos["nombre"].setText(valores[1])
                self.campos["direccion"].setText(valores[2])
                self.campos["telefono"].setText(valores[3])
                self.campos["municipio"].setText(valores[4])
                self.campos["estado"].setText(valores[5])
                self.campos["zona_educativa"].setText(valores[6])
                self.campos["director_actual"].setText(valores[7])
                self.campos["coordinador_academico"].setText(valores[8])
                # Eliminado: self.activo_check.setChecked(valores[9] == 'Sí')

                self.campos["codigo_dea"].setReadOnly(True) # No permitir cambiar el código DEA en edición
                self.buscar_input.setStyleSheet("background-color: #fff4cc; border: 2px solid #ffc107;")
                self.buscar_input.setToolTip("🛠️ Editando institución encontrada")
                self.campos["nombre"].setFocus()
                self.btn_guardar_cambios.setVisible(True)
                self.btn_guardar.setVisible(False)
                self.edicion_codigo_dea = valores[0] # Almacenar el código DEA original para la actualización
                encontrado = True

        if not encontrado:
            QMessageBox.information(self, "Resultado", "No se encontró ninguna coincidencia.")
            self.preparar_formulario_nuevo() # Limpiar el formulario si no se encuentra nada

    def load_registros(self):
        """
        Carga todos los registros desde la base de datos y los muestra en la tabla.
        """
        registros = self.db.fetch_all(
            "SELECT codigo_dea, nombre, direccion, telefono, municipio, estado, zona_educativa, director_actual, coordinador_academico FROM institucion ORDER BY nombre ASC"
        )
        self.tabla.setRowCount(len(registros))
        for i, registro in enumerate(registros):
            self.tabla.setItem(i, 0, QTableWidgetItem(registro['codigo_dea']))
            self.tabla.setItem(i, 1, QTableWidgetItem(registro['nombre']))
            self.tabla.setItem(i, 2, QTableWidgetItem(registro['direccion'] or ""))
            self.tabla.setItem(i, 3, QTableWidgetItem(registro['telefono'] or ""))
            self.tabla.setItem(i, 4, QTableWidgetItem(registro['municipio'] or ""))
            self.tabla.setItem(i, 5, QTableWidgetItem(registro['estado'] or ""))
            self.tabla.setItem(i, 6, QTableWidgetItem(registro['zona_educativa'] or ""))
            self.tabla.setItem(i, 7, QTableWidgetItem(registro['director_actual'] or ""))
            self.tabla.setItem(i, 8, QTableWidgetItem(registro['coordinador_academico'] or ""))
            # Eliminado: activo_display = 'Sí' if registro['activo'] else 'No'
            # Eliminado: self.tabla.setItem(i, 9, QTableWidgetItem(activo_display))
        self.info_label.setText(f"Total de instituciones: {len(registros)}")
        # Asegurarse de que los botones de edición/eliminación se actualicen
        self.on_selection_changed_table() 


    def actualizar_registro(self, item):
        """
        Actualiza un registro en la base de datos cuando se edita directamente en la tabla.
        (Este método no se usa con el flujo actual de edición por formulario, pero se mantiene si se desea edición directa en tabla)
        """
        # Desconectar temporalmente la señal para evitar bucles infinitos
        self.tabla.itemChanged.disconnect(self.actualizar_registro)

        fila = item.row()
        columna = item.column()
        codigo_dea = self.tabla.item(fila, 0).text()
        
        # Mapeo de índices de columna a nombres de campo de la base de datos (ahora 9 campos)
        campos_db = [
            "codigo_dea", "nombre", "direccion", "telefono",
            "municipio", "estado", "zona_educativa",
            "director_actual", "coordinador_academico"
        ]
        campo = campos_db[columna]
        nuevo_valor = item.text()

        # Eliminado: Manejar el campo 'activo' específicamente
        # if campo == "activo":
        #     nuevo_valor = True if nuevo_valor.lower() == 'sí' else False

        try:
            query = sql.SQL("UPDATE institucion SET {} = %s WHERE codigo_dea = %s").format(sql.Identifier(campo))
            if self.db.execute_query(query, (nuevo_valor, codigo_dea)):
                QMessageBox.information(self, "Éxito", f"Campo '{campo}' actualizado correctamente.")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo actualizar el campo '{campo}'.")
        except Exception as e:
            QMessageBox.critical(self, "Error al actualizar", str(e))
        finally:
            # Reconectar la señal
            self.tabla.itemChanged.connect(self.actualizar_registro)


    def guardar_cambios(self):
        """
        Guarda los cambios realizados en el formulario de edición en la base de datos.
        """
        if self.edicion_codigo_dea is None:
            QMessageBox.warning(self, "Error", "No hay institución seleccionada para editar.")
            return

        datos = {k: v.text().strip() for k, v in self.campos.items()}
        # Eliminado: datos['activo'] = self.activo_check.isChecked()

        if any(not datos[k] for k in ["codigo_dea", "nombre", "direccion", "telefono", "municipio", "estado", "zona_educativa", "director_actual", "coordinador_academico"]):
            QMessageBox.warning(self, "Validación", "Por favor, completa todos los campos.")
            return

        query = """
        UPDATE institucion SET
            nombre = %s,
            direccion = %s,
            telefono = %s,
            municipio = %s,
            estado = %s,
            zona_educativa = %s,
            director_actual = %s,
            coordinador_academico = %s
        WHERE codigo_dea = %s;
        """
        params = (datos['nombre'], datos['direccion'], datos['telefono'],
                  datos['municipio'], datos['estado'], datos['zona_educativa'],
                  datos['director_actual'], datos['coordinador_academico'],
                  self.edicion_codigo_dea) # Eliminado: datos['activo']

        if self.db.execute_query(query, params):
            QMessageBox.information(self, "Éxito", "Institución actualizada correctamente.")
            self.preparar_formulario_nuevo()
            self.load_registros()
        else:
            # El error ya es manejado por DatabaseConnection
            pass

    def eliminar_registro(self):
        """
        Elimina el registro seleccionado en la tabla después de confirmación.
        """
        fila_seleccionada = self.tabla.currentRow()
        if fila_seleccionada == -1:
            QMessageBox.warning(self, "Selecciona una fila", "Debes seleccionar una fila para eliminar.")
            return
        
        codigo_dea = self.tabla.item(fila_seleccionada, 0).text()
        nombre_institucion = self.tabla.item(fila_seleccionada, 1).text()

        confirmacion = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro que deseas eliminar la institución '{nombre_institucion}' (Código DEA: {codigo_dea})?\n"
            "Esta acción eliminará la información de manera permanente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmacion == QMessageBox.StandardButton.Yes:
            query = "DELETE FROM institucion WHERE codigo_dea = %s;"
            if self.db.execute_query(query, (codigo_dea,)):
                QMessageBox.information(self, "Eliminado", "Institución eliminada correctamente.")
                self.load_registros() # Recargar la tabla para reflejar el cambio
                self.preparar_formulario_nuevo() # Limpiar formulario si se elimina el que estaba en edición
            else:
                # El error ya es manejado por DatabaseConnection
                pass

    def editar_registro_desde_tabla(self, item):
        """
        Carga los datos de la fila doble-clicada en el formulario para edición.
        """
        fila = item.row()
        self.mostrar_formulario() # Cambiar a la vista del formulario

        # Obtener los datos de la fila seleccionada (ahora 9 columnas)
        valores = [self.tabla.item(fila, j).text() for j in range(self.tabla.columnCount())]
        
        # Llenar los campos del formulario
        self.campos["codigo_dea"].setText(valores[0])
        self.campos["nombre"].setText(valores[1])
        self.campos["direccion"].setText(valores[2])
        self.campos["telefono"].setText(valores[3])
        self.campos["municipio"].setText(valores[4])
        self.campos["estado"].setText(valores[5])
        self.campos["zona_educativa"].setText(valores[6])
        self.campos["director_actual"].setText(valores[7])
        self.campos["coordinador_academico"].setText(valores[8])
        # Eliminado: self.activo_check.setChecked(valores[9] == 'Sí')

        self.campos["codigo_dea"].setReadOnly(True) # No permitir cambiar el código DEA en edición
        self.btn_guardar.setVisible(False)
        self.btn_guardar_cambios.setVisible(True)
        self.edicion_codigo_dea = valores[0] # Almacenar el código DEA original

    def clear_fields(self):
        """
        Limpia los campos del formulario.
        """
        self.preparar_formulario_nuevo() # Reutilizar la función para limpiar y resetear

    def on_selection_changed_table(self):
        """
        Método para actualizar el estado de los botones de edición/eliminación
        basado en la selección de la tabla. (No se usa directamente con el flujo actual
        de edición por doble click, pero es buena práctica para botones de la tabla)
        """
        # Aquí puedes añadir lógica si tuvieras botones de "Editar" o "Eliminar"
        # que solo se habilitan al seleccionar una fila en la tabla.
        # Por ahora, la edición se maneja con doble click y el eliminar con un botón general.
        pass

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


# Bloque para ejecutar la aplicación (solo para pruebas directas del módulo)
# if __name__ == '__main__':
#     app = QApplication(sys.argv)

#     # Simular una configuración de DB y datos de usuario para probar este módulo
#     test_db_config = {
#         'host': 'localhost',
#         'database': 'SIGME2', 
#         'user': 'postgres',
#         'password': '1234',
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

#     institucion_app = InstitucionApp(db_config=test_db_config, user_data=test_user_data)
#     institucion_app.show()

#     sys.exit(app.exec())
