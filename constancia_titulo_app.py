import os
import sys
import re
import subprocess
import platform
from datetime import datetime

import psycopg2
from psycopg2 import Error

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Asegúrate de que las fuentes TTF estén en el mismo directorio que tu script
# o en una ubicación accesible por el sistema.
# Si no las tienes, puedes descargarlas o comentar estas líneas para usar las predeterminadas.
try:
    pdfmetrics.registerFont(TTFont('BaskervilleOldFace', 'BaskervilleOldFace.ttf'))
    pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))
    pdfmetrics.registerFont(TTFont('Calibri-Bold', 'Calibri-Bold.ttf'))
except Exception as e:
    print(f"Advertencia: No se pudieron cargar las fuentes personalizadas. Usando fuentes predeterminadas. Error: {e}")

# --- Clase: DatabaseManager para manejar la conexión y consultas ---
class DatabaseManager:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.conn = None
        self.connect() # Intentar conectar al inicializar

    def connect(self):
        if self.conn and not self.conn.closed:
            return True # Ya conectado

        try:
            self.conn = psycopg2.connect(**self.db_config)
            print(f"Conexión a la base de datos '{self.db_config.get('database')}' exitosa para Constancia de Título.")
            return True
        except Error as e:
            QMessageBox.critical(None, "Error de Conexión a la Base de Datos",
                                 f"No se pudo establecer conexión con la base de datos:\n{e}\n"
                                 "Por favor, verifique la configuración (host, base de datos, usuario, contraseña, puerto).")
            self.conn = None
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")
            self.conn = None

    def execute_query(self, query: str, params=None, fetch_one=False):
        if not self.connect(): # Asegurarse de que la conexión esté activa
            return None

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    if fetch_one:
                        return cur.fetchone()
                    else:
                        return cur.fetchall()
                else:
                    self.conn.commit()
                    return True
        except Error as e:
            QMessageBox.critical(None, "Error de Consulta de BD", f"Ocurrió un error al ejecutar la consulta:\n{e}")
            if self.conn:
                self.conn.rollback() # Revertir cambios en caso de error
            return None

    def obtener_datos_institucion(self):
        query = "SELECT * FROM INSTITUCION LIMIT 1;"
        row = self.execute_query(query, fetch_one=True)
        if row:
            columns = ["codigo_dea", "nombre", "direccion", "telefono", "municipio", "estado", "zona_educativa", "director_actual", "coordinador_academico"]
            return dict(zip(columns, row))
        return None

    def obtener_datos_estudiante(self, cedula: str):
        query = """
        SELECT
            cedula, nacionalidad, nombres, apellidos, genero, fecha_nacimiento,
            lugar_nacimiento, estado_nacimiento, municipio_nacimiento, direccion,
            telefono, correo, estatura, peso, talla_camisa, talla_pantalon,
            talla_zapatos, condiciones_medicas, medicamentos, plantel_procedencia,
            fecha_ingreso, estado_estudiante, fecha_retiro, motivo_retiro
        FROM ESTUDIANTE WHERE cedula = %s;
        """
        return self.execute_query(query, (cedula,), fetch_one=True)

    def insertar_constancia(self, constancia_data: dict):
        insert_query = """
        INSERT INTO CONSTANCIA (
            numero, tipo_constancia, cedula_estudiante, cedula_representante,
            codigo_ano_escolar, codigo_seccion, fecha_emision, motivo_solicitud,
            funcionario_emisor, codigo_constancia, observaciones, estado
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
        """
        params = (
            constancia_data['numero'], constancia_data['tipo_constancia'],
            constancia_data['cedula_estudiante'], constancia_data['cedula_representante'],
            constancia_data['codigo_ano_escolar'], constancia_data['codigo_seccion'],
            constancia_data['fecha_emision'], constancia_data['motivo_solicitud'],
            constancia_data['funcionario_emisor'], constancia_data['codigo_constancia'],
            constancia_data['observaciones'], constancia_data['estado']
        )
        return self.execute_query(insert_query, params)

    def obtener_datos_profesor(self, cedula_profesor: str):
        cedula_limpia = cedula_profesor.strip().upper()
        queries = [
            "SELECT nombres, apellidos, cedula FROM PERSONAL WHERE cedula = %s",
            "SELECT nombres, apellidos, cedula FROM PERSONAL WHERE UPPER(cedula) = %s",
            "SELECT nombres, apellidos, cedula FROM PERSONAL WHERE cedula ILIKE %s"
        ]

        # Considerar si la cédula es con 'V-' o 'E-' o sin prefijo
        cedula_variations = [cedula_limpia]
        if cedula_limpia.startswith(('V-', 'E-')):
            cedula_variations.append(cedula_limpia[2:]) # Cédula sin el prefijo V- o E-
        else:
            cedula_variations.extend([f"V-{cedula_limpia}", f"E-{cedula_limpia}"]) # Probar con prefijos

        for variation in cedula_variations:
            row = self.execute_query(queries[0], (variation,), fetch_one=True) # Intenta coincidencia exacta
            if row:
                return {'nombres': row[0], 'apellidos': row[1], 'cedula': row[2]}

        # Si no se encuentra con coincidencia exacta, probar ILIKE
        for variation in cedula_variations:
            row = self.execute_query(queries[2], (variation,), fetch_one=True)
            if row:
                return {'nombres': row[0], 'apellidos': row[1], 'cedula': row[2]}

        return None

# --- Fin de la Clase DatabaseManager ---

class ConstanciaApp(QWidget):

    # El constructor ahora recibe el diccionario de configuración de la BD Y los datos del usuario
    def __init__(self, db_config: dict, user_data: dict = None):
        super().__init__()

        self.db = DatabaseManager(db_config) # Instancia el gestor de base de datos
        self.user_data = user_data if user_data is not None else {} # Almacena los datos del usuario
        self.output_directory = os.path.expanduser("~/Documentos/ConstanciasPDF") # Directorio por defecto
        self.logo_path = "carmen ruiz.jpg" # Ruta del logo por defecto (debería existir o ser modificada por el usuario)

        # Definir paleta de colores
        self.colors = {
            "primary_light": "#e0f7fa",  # Azul claro muy suave
            "primary_dark": "#006064",   # Azul verdoso oscuro
            "accent": "#00bcd4",         # Cian brillante
            "secondary_light": "#f5f5f5",# Gris muy claro
            "text_dark": "#212121",      # Gris casi negro
            "text_light": "#ffffff"      # Blanco
        }

        self.setWindowTitle("Sistema de Gestión de Constancias de Título")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()

        # Si hay datos de usuario y un funcionario emisor predeterminado, úsalo
        if self.user_data.get('cedula'):
            self.funcionario_entry.setText(self.user_data['cedula'])
            self.funcionario_entry.setReadOnly(True) # Opcional: para que no lo cambie el usuario

    def setup_ui(self):
        # Apply styles using QSS (Qt Style Sheets) for a more direct translation of ttk.Style
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colors["primary_light"]}; /* Equivalent to master.configure(bg=...)*/
            }}
            QFrame, QGroupBox {{
                background-color: {self.colors["primary_light"]}; /* Equivalent to TFrame, TLabelframe background*/
            }}
            QGroupBox::title {{
                color: {self.colors["primary_dark"]};
                font: bold 12pt "Helvetica"; /* Equivalent to TLabelframe font*/
            }}
            QLabel {{
                color: {self.colors["primary_dark"]};
                font: 11pt "Helvetica"; /* Equivalent to TLabel font*/
            }}
            QLabel#titleLabel {{ /* Specific ID for the title label */
                font: bold 20pt "Helvetica"; /* Equivalent to Title.TLabel font*/
                color: {self.colors["primary_dark"]};
            }}
            QLabel#statusLabel {{ /* Specific ID for the status label */
                font: italic 10pt "Helvetica"; /* Equivalent to Status.TLabel font*/
                color: {self.colors["accent"]};
            }}
            QLineEdit {{
                background-color: {self.colors["secondary_light"]}; /* Equivalent to TEntry fieldbackground*/
                color: {self.colors["primary_dark"]}; /* Equivalent to TEntry foreground*/
                border: 1px solid {self.colors["accent"]}; /* Equivalent to TEntry bordercolor, relief="flat"*/
                font: 11pt "Helvetica"; /* Equivalent to TEntry font*/
                padding: 5px; /* Adjust padding as needed */
            }}
            QLineEdit:focus {{
                background-color: white; /* Equivalent to TEntry map focus*/
            }}
            QPushButton {{
                background-color: {self.colors["accent"]}; /* Equivalent to TButton background*/
                color: white; /* Equivalent to TButton foreground*/
                font: bold 12pt "Helvetica"; /* Equivalent to TButton font*/
                border: none; /* Equivalent to TButton relief="flat"*/
                padding: 12px; /* Adjust padding as needed */
            }}
            QPushButton:hover {{ /* Simulating active state */
                background-color: {self.colors["primary_dark"]}; /* Equivalent to TButton map active*/
            }}
        """)

        main_layout = QVBoxLayout(self) # Replaces main_frame = ttk.Frame(self.master, padding="30")
        main_layout.setContentsMargins(30, 30, 30, 30) # Equivalent to padding
        main_layout.setSpacing(0) # Reduce default spacing

        title_label = QLabel("Sistema de Gestión de Constancias de Título") #
        title_label.setObjectName("titleLabel") # Set object name for specific styling
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Equivalent to sticky="nsew" for a single widget in a row
        main_layout.addWidget(title_label)
        main_layout.addSpacing(30) # Equivalent to pady=(0, 30)

        input_group_box = QGroupBox("Datos del Estudiante para Constancia") # Replaces ttk.LabelFrame
        input_layout = QGridLayout(input_group_box) # Replaces input_frame.grid
        input_layout.setContentsMargins(25, 25, 25, 25) # Equivalent to padding
        input_layout.setHorizontalSpacing(10) # Equivalent to padx=(0, 10) for labels
        input_layout.setVerticalSpacing(15) # Equivalent to pady=(0, 15) for rows

        cedula_label = QLabel("Cédula de Identidad del Estudiante (Ej. V-31223146):")
        input_layout.addWidget(cedula_label, 0, 0, Qt.AlignmentFlag.AlignLeft) # sticky="w"
        self.cedula_entry = QLineEdit() #
        self.cedula_entry.setPlaceholderText("") # Equivalent to insert(0, "")
        input_layout.addWidget(self.cedula_entry, 0, 1) # sticky="ew"

        funcionario_label = QLabel("Cédula del Funcionario Emisor (Ej. V-6305171):")
        input_layout.addWidget(funcionario_label, 1, 0, Qt.AlignmentFlag.AlignLeft) # sticky="w"
        self.funcionario_entry = QLineEdit()
        input_layout.addWidget(self.funcionario_entry, 1, 1) # sticky="ew"

        main_layout.addWidget(input_group_box)
        main_layout.addSpacing(15) # Equivalent to pady=15 for input_frame

        # --- Sección de Configuración de Rutas ---
        paths_group_box = QGroupBox("Configuración de Rutas")
        paths_layout = QGridLayout(paths_group_box)
        paths_layout.setContentsMargins(25, 25, 25, 25)
        paths_layout.setHorizontalSpacing(10)
        paths_layout.setVerticalSpacing(15)

        # Ruta del Logo
        logo_label = QLabel("Ruta del Logo (ej. carmen ruiz.jpg):")
        paths_layout.addWidget(logo_label, 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.logo_path_input = QLineEdit(self.logo_path) # Usar self.logo_path inicial
        paths_layout.addWidget(self.logo_path_input, 0, 1)
        btn_select_logo = QPushButton("Seleccionar Logo...")
        btn_select_logo.clicked.connect(self.select_logo_path)
        paths_layout.addWidget(btn_select_logo, 0, 2)

        # Directorio de Salida
        output_dir_label = QLabel("Directorio de Salida de PDFs:")
        paths_layout.addWidget(output_dir_label, 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.output_directory_input = QLineEdit(self.output_directory)
        paths_layout.addWidget(self.output_directory_input, 1, 1)
        btn_select_output_dir = QPushButton("Seleccionar Directorio...")
        btn_select_output_dir.clicked.connect(self.select_output_directory)
        paths_layout.addWidget(btn_select_output_dir, 1, 2)

        main_layout.addWidget(paths_group_box)
        main_layout.addSpacing(15)

        main_layout.addStretch(1) # Equivalent to grid_rowconfigure(1, weight=1) for main_frame

        generate_button = QPushButton("Generar Constancia y Registrar en Sistema")
        generate_button.clicked.connect(self.generar_y_guardar_constancia) # Equivalent to command=
        main_layout.addWidget(generate_button, alignment=Qt.AlignmentFlag.AlignCenter) # Equivalent to ipady, ipadx, and grid positioning
        main_layout.addSpacing(10) # Equivalent to pady=(20, 10)

        self.status_label = QLabel("Aplicación lista. Ingrese la cédula para iniciar.")
        self.status_label.setObjectName("statusLabel") # Set object name for specific styling
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter) # sticky="n"
        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(0) # Equivalent to pady=(10, 0)

    def select_logo_path(self):
        """Abre un diálogo para seleccionar el archivo del logo."""
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Archivo de Logo")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_path_input.setText(selected_files[0])
                self.logo_path = selected_files[0] # Actualizar la variable de instancia

    def select_output_directory(self):
        """Abre un diálogo para seleccionar el directorio de salida de los PDFs."""
        dir_dialog = QFileDialog(self)
        dir_dialog.setFileMode(QFileDialog.FileMode.Directory)
        dir_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dir_dialog.setWindowTitle("Seleccionar Directorio de Salida")
        if dir_dialog.exec():
            selected_dir = dir_dialog.selectedFiles()
            if selected_dir:
                self.output_directory_input.setText(selected_dir[0])
                self.output_directory = selected_dir[0] # Actualizar la variable de instancia

    def generar_y_guardar_constancia(self):
        cedula_estudiante = self.cedula_entry.text().strip().upper()
        cedula_funcionario = self.funcionario_entry.text().strip().upper()

        if not re.match(r"^[VE]-\d{7,9}$", cedula_estudiante):
            QMessageBox.warning(self, "Entrada Inválida", "La cédula del estudiante debe tener el formato V-12345678 o E-12345678.")
            return
        if not re.match(r"^[VE]-\d{7,9}$", cedula_funcionario):
            QMessageBox.warning(self, "Entrada Inválida", "La cédula del funcionario debe tener el formato V-12345678 o E-12345678.")
            return

        # Obtener datos de la institución y el estudiante usando DatabaseManager
        institucion_info = self.db.obtener_datos_institucion()
        if not institucion_info:
            QMessageBox.critical(self, "Error de Datos", "No se pudieron obtener los datos de la institución. Verifique la base de datos.")
            return

        estudiante_info_tuple = self.db.obtener_datos_estudiante(cedula_estudiante)
        if not estudiante_info_tuple:
            QMessageBox.warning(self, "Estudiante No Encontrado", f"No se encontró un estudiante con la cédula '{cedula_estudiante}'.")
            return

        # Mapear los datos del estudiante de tupla a diccionario para mayor claridad
        estudiante_columns = [
            "cedula", "nacionalidad", "nombres", "apellidos", "genero", "fecha_nacimiento",
            "lugar_nacimiento", "estado_nacimiento", "municipio_nacimiento", "direccion",
            "telefono", "correo", "estatura", "peso", "talla_camisa", "talla_pantalon",
            "talla_zapatos", "condiciones_medicas", "medicamentos", "plantel_procedencia",
            "fecha_ingreso", "estado_estudiante", "fecha_retiro", "motivo_retiro"
        ]
        estudiante_info = dict(zip(estudiante_columns, estudiante_info_tuple))


        profesor_info = self.db.obtener_datos_profesor(cedula_funcionario)
        if not profesor_info:
            QMessageBox.warning(self, "Funcionario No Encontrado", f"No se encontró un funcionario con la cédula '{cedula_funcionario}'.")
            return

        # Generar un número de constancia (ej. basado en fecha y hora, o desde DB si tienes secuencia)
        # Para este ejemplo, lo generaremos simple. En un sistema real, esto debería ser gestionado por la DB.
        numero_constancia = datetime.now().strftime("%Y%m%d%H%M%S") # Ejemplo de número único

        constancia_data = {
            'numero': numero_constancia,
            'tipo_constancia': 'TITULO', # Asumiendo que es una constancia de título
            'cedula_estudiante': cedula_estudiante,
            'cedula_representante': None, # O recoger si aplica
            'codigo_ano_escolar': None, # O recoger si aplica
            'codigo_seccion': None, # O recoger si aplica
            'fecha_emision': datetime.now(),
            'motivo_solicitud': 'CONSTANCIA DE TÍTULO',
            'funcionario_emisor': cedula_funcionario,
            'codigo_constancia': f"CT-{numero_constancia}", # Código interno
            'observaciones': 'Generada automáticamente por el sistema.',
            'estado': 'EMITIDA'
        }

        # Intentar registrar la constancia en la DB
        if self.db.insertar_constancia(constancia_data):
            # Si el registro es exitoso, generar el PDF
            pdf_filename = os.path.join(self.output_directory, f"Constancia_Titulo_{cedula_estudiante}_{numero_constancia}.pdf")
            os.makedirs(self.output_directory, exist_ok=True) # Asegura que el directorio exista

            self.generar_pdf_constancia(
                estudiante_info,
                constancia_data,
                pdf_filename,
                institucion_info,
                profesor_info
            )
            self.status_label.setText(f"Constancia N° {numero_constancia} generada y registrada con éxito.")
            self.status_label.setStyleSheet("color: green;")
            self.abrir_pdf(pdf_filename)
        else:
            self.status_label.setText("Error al registrar la constancia en el sistema.")
            self.status_label.setStyleSheet("color: red;")

    def abrir_pdf(self, filename):
        try:
            if platform.system() == 'Windows':
                os.startfile(filename)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', filename])
            else:  # Linux
                subprocess.run(['xdg-open', filename])
        except Exception as e:
            print(f"No se pudo abrir el PDF automáticamente: {e}")
            QMessageBox.warning(self, "Error al Abrir PDF", f"No se pudo abrir el PDF automáticamente. Por favor, ábralo manualmente desde: {filename}\nError: {e}")


    def generar_pdf_constancia(self, estudiante_info: dict, constancia_info: dict, filename: str, institucion_info: dict, profesor_info: dict):

        meses_espanol = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }

        def obtener_nombre_completo(nombres, apellidos):
            return f"{nombres} {apellidos}".strip().upper()

        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        # Configurar márgenes según especificaciones
        margin_top = 2.5 * cm
        margin_left = 2 * cm
        margin_bottom = 2.5 * cm
        margin_right = 2 * cm

        # Fuentes con fallback
        baskerville_font = 'BaskervilleOldFace' if 'BaskervilleOldFace' in pdfmetrics.getRegisteredFontNames() else 'Times-Roman'
        calibri_font = 'Calibri' if 'Calibri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        calibri_bold_font = 'Calibri-Bold' if 'Calibri-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'

        # Agregar logo
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                c.drawImage(self.logo_path, margin_left, height - margin_top - 60, width=60, height=60, preserveAspectRatio=True)
            except Exception as e:
                QMessageBox.warning(self, "Error de Imagen", f"No se pudo cargar el logo: {e}. Asegúrese de que el archivo es una imagen válida.")
        else:
            QMessageBox.warning(self, "Advertencia", "No se ha seleccionado un logo o el archivo no existe. El PDF se generará sin logo.")

        # Dibujar rectángulo del encabezado
        rect_x = margin_left + 70  # Después del logo
        rect_y = height - margin_top - 80
        rect_width = width - margin_left - margin_right - 70 - 40  # Reducir 40 puntos más
        rect_height = 80

        c.setStrokeColor(HexColor("#dce6f2"))
        c.setLineWidth(2.25)
        c.rect(rect_x, rect_y, rect_width, rect_height, fill=0)

        # Encabezado dentro del rectángulo
        current_y = rect_y + rect_height - 15

        # REPUBLICA BOLIVARIANA DE VENEZUELA
        c.setFont(baskerville_font, 12)
        c.setFillColor(HexColor("#4f81bd"))
        text = "REPÚBLICA BOLIVARIANA DE VENEZUELA"
        text_width = c.stringWidth(text, baskerville_font, 12)
        c.drawString(rect_x + (rect_width - text_width) / 2, current_y, text)

        # Datos de la institución
        current_y -= 12  # Interlineado 1.0
        c.setFont(calibri_font, 12)
        c.setFillColor(HexColor("#000000"))

        if institucion_info:
            institucion_lines = [
                f"{institucion_info['estado'].upper()}",
                f"{institucion_info['nombre'].upper()}",
                f"CÓDIGO DEA: {institucion_info['codigo_dea']}",
                f"{institucion_info['direccion'].upper()}, {institucion_info['municipio'].upper()}",
                f"TELÉFONO: {institucion_info['telefono']}"
            ]
            for line in institucion_lines:
                text_width = c.stringWidth(line, calibri_font, 12)
                c.drawString(rect_x + (rect_width - text_width) / 2, current_y, line)
                current_y -= 12

        # Título de la Constancia
        c.setFont(baskerville_font, 18)
        c.setFillColor(HexColor("#000000"))
        c.drawCentredString(width / 2, height - margin_top - 120, "CONSTANCIA DE TÍTULO")
        c.line(width / 2 - 100, height - margin_top - 125, width / 2 + 100, height - margin_top - 125) # Línea debajo del título

        c.setFont(calibri_font, 10)
        c.setFillColor(HexColor("#4f81bd"))
        c.drawCentredString(width / 2, height - margin_top - 145, f"N° {constancia_info['numero']}")


        # Cuerpo del documento
        current_y = height - margin_top - 180
        text_margin_left = margin_left + 1.5 * cm # Pequeña sangría para el cuerpo

        c.setFont(calibri_font, 12)
        c.setFillColor(HexColor("#000000"))

        texto_inicial = "Quien suscribe, Director(a) de la Unidad Educativa Estadal “Carmen Ruiz”, hace constar por medio de la presente que el (la) ciudadano(a):"
        c.drawString(text_margin_left, current_y, texto_inicial)
        current_y -= 20

        # Datos del estudiante
        nombre_completo_estudiante = obtener_nombre_completo(estudiante_info['nombres'], estudiante_info['apellidos'])
        cedula_estudiante_formato = estudiante_info['cedula'].upper()

        datos_estudiante_str = f"{nombre_completo_estudiante}, titular de la Cédula de Identidad {cedula_estudiante_formato},"
        datos_estudiante_str += f" nacido(a) en {estudiante_info['lugar_nacimiento'].upper()}, Estado {estudiante_info['estado_nacimiento'].upper()} "
        datos_estudiante_str += f"en fecha {estudiante_info['fecha_nacimiento'].strftime('%d de %B de %Y')},"

        # Usar TextObject para control preciso de posición y ajustar si es necesario
        # Ojo: ReportLab Canvas no interpreta tags HTML como <b>, necesitas manejar el bold manualmente cambiando la fuente.
        # Para mantener la simplicidad y el estilo previo, se imprime la cadena sin formato HTML.
        c.drawString(text_margin_left, current_y, datos_estudiante_str)
        current_y -= 20 # Ajustar si la línea es larga

        # Más del cuerpo
        texto_central = f"egresó de esta Institución en el Año Escolar {constancia_info['codigo_ano_escolar'] if constancia_info['codigo_ano_escolar'] else '____________'},"
        texto_central += " habiendo cursado y aprobado el ciclo diversificado en la Mención o Especialidad de CIENCIAS."
        c.drawString(text_margin_left, current_y, texto_central)
        current_y -= 40 # Espacio para el siguiente párrafo

        texto_final = "Constancia que se expide a solicitud de parte interesada, en Charallave, a los "
        fecha_emision = constancia_info['fecha_emision']
        dia = fecha_emision.day
        mes = meses_espanol[fecha_emision.month]
        año = fecha_emision.year
        texto_final += f"{dia} días del mes de {mes} del año {año}."
        c.drawString(text_margin_left, current_y, texto_final)
        current_y -= 80 # Espacio para la firma

        # Sección de Firma
        c.setFont(calibri_font, 12)
        c.drawCentredString(width / 2, current_y, "Atentamente,")
        current_y -= 20

        # Línea de firma para Director/a
        c.line(width / 2 - 70, current_y, width / 2 + 70, current_y)
        current_y -= 15
        c.setFont(calibri_bold_font, 12)
        c.drawCentredString(width / 2, current_y, institucion_info['director_actual'].upper() if institucion_info and institucion_info['director_actual'] else '_________________________')
        current_y -= 15
        c.setFont(calibri_font, 10)
        c.drawCentredString(width / 2, current_y, "DIRECTOR(A)")

        # Cédula del funcionario emisor (quien está firmando)
        current_y -= 30
        c.setFont(calibri_font, 9)
        c.setFillColor(HexColor("#808080")) # Gris para texto más pequeño
        profesor_nombre_completo = obtener_nombre_completo(profesor_info['nombres'], profesor_info['apellidos'])
        c.drawRightString(width - margin_right, margin_bottom + 10, f"Emitido por: {profesor_nombre_completo} ({profesor_info['cedula'].upper()})")
        c.drawString(margin_left, margin_bottom + 10, f"Código de Constancia: {constancia_info['codigo_constancia']}")

        c.showPage()
        c.save()
        QMessageBox.information(self, "Generación Exitosa", f"La constancia de título ha sido generada en:\n{filename}")


    def closeEvent(self, event):
        # Asegurarse de cerrar la conexión a la base de datos al cerrar la aplicación
        if self.db:
            self.db.disconnect()
        event.accept()

# --- Ejecución de la Aplicación ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Aquí es donde se define la configuración de la base de datos
    # Esta es la parte que "viene desde atrás" como un parámetro.
    my_db_config = {
        'host': 'localhost',
        'database': 'bd',
        'user': 'postgres',
        'password': '12345678',
        'port': '5432'
    }

    # Aquí es donde se definen los datos del usuario logeado
    # Esta es la parte que "viene desde atrás" como un parámetro.
    # Por ejemplo, si este módulo fuera llamado desde un módulo de autenticación.
    my_user_data = {
        'id': 1,
        'username': 'secretaria.ejemplo',
        'role': 'secretaria',
        'cedula': 'V-12345678' # Asume que la cédula del funcionario emisor se sabe al logearse
    }

    # Pasamos tanto db_config como user_data al constructor de ConstanciaApp
    window = ConstanciaApp(db_config=my_db_config, user_data=my_user_data)
    window.show()
    sys.exit(app.exec())