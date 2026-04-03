import sys
import psycopg2
from psycopg2 import Error
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QMessageBox, QTableWidget, QTableWidgetItem, QHBoxLayout, QSplitter,
    QHeaderView, QDateEdit, QComboBox, QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime
import os
import platform

# --- Importaciones adicionales para ReportLab Platypus ---
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import black
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
# --- Fin de importaciones adicionales ---

# --- NUEVO: Función para cargar la configuración de la DB ---
def load_db_config(config_file='db_connection.conf'):
    """
    Carga la configuración de la base de datos desde un archivo.
    Si el archivo no existe o está incompleto, lo crea con valores de ejemplo
    y muestra un mensaje al usuario.
    """
    config = {}
    required_keys = ['host', 'database', 'user', 'password', 'port']
    file_exists = os.path.exists(config_file)

    if file_exists:
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'): # Ignorar comentarios
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except Exception as e:
            QMessageBox.critical(None, "Error de Lectura de Configuración",
                                 f"Error al leer el archivo de configuración '{config_file}': {e}")
            return None
    else:
        QMessageBox.warning(None, "Archivo de Configuración No Encontrado",
                            f"El archivo de configuración de la base de datos '{config_file}' no se encontró.\n"
                            "Se creará un archivo con valores por defecto. Por favor, edítelo con sus credenciales reales.")
        # Crear el archivo con placeholders
        try:
            with open(config_file, 'w') as f:
                f.write("# Configuración de la Base de Datos\n")
                f.write("# Edite estas líneas con sus credenciales de PostgreSQL\n")
                f.write("host=localhost\n")
                f.write("database=your_database_name\n")
                f.write("user=your_username\n")
                f.write("password=your_password\n")
                f.write("port=5432\n") # Puerto por defecto de PostgreSQL
            QMessageBox.information(None, "Archivo Creado",
                                    f"Se ha creado el archivo '{config_file}' con valores de ejemplo. "
                                    "Por favor, cierre la aplicación, edite este archivo con sus credenciales reales y reinicie.")
            return None # No podemos continuar sin credenciales válidas
        except Exception as e:
            QMessageBox.critical(None, "Error al Crear Archivo",
                                 f"No se pudo crear el archivo de configuración: {e}")
            return None

    # Verificar que todas las claves requeridas estén presentes y no vacías
    missing_keys = [key for key in required_keys if key not in config or not config[key]]
    if missing_keys:
        QMessageBox.critical(None, "Configuración Incompleta",
                             f"El archivo '{config_file}' está incompleto o con valores vacíos. "
                             f"Faltan las siguientes claves o están vacías: {', '.join(missing_keys)}. "
                             "Por favor, edítelo con sus credenciales correctas y reinicie la aplicación.")
        return None
    
    # Convertir el puerto a entero, si existe y es un número
    try:
        config['port'] = int(config['port'])
    except ValueError:
        QMessageBox.critical(None, "Error de Configuración", "El puerto de la base de datos no es un número válido.")
        return None

    return config

# --- Parte 1: Clase para la Base de Datos ---
class DatabaseManager:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.connect()

    def connect(self):
        if not self.db_config: # Si la configuración es nula, no intentar conectar
            print("No se puede conectar: Configuración de DB no proporcionada o inválida.")
            return False

        if self.conn and not self.conn.closed:
            return True # Ya conectado

        try:
            self.conn = psycopg2.connect(
                dbname=self.db_config.get('database'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password'),
                host=self.db_config.get('host'),
                port=self.db_config.get('port')
            )
            print(f"Conexión a la base de datos '{self.db_config.get('database')}' exitosa para Constancia de Estudio.")
            return True
        except Error as e:
            QMessageBox.critical(None, "Error de Conexión", f"No se pudo conectar a la base de datos: {e}")
            self.conn = None
            return False

    def disconnect(self):
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")
            self.conn = None

    def execute_query(self, query, params=None):
        if not self.conn or self.conn.closed:
            # Intentar reconectar si la conexión se perdió
            if not self.connect():
                return None # Falló la reconexión

        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                result = cur.fetchall()
                return result
            else:
                self.conn.commit()
                return True
        except Error as e:
            QMessageBox.critical(None, "Error de Consulta", f"Error al ejecutar la consulta: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_student_data(self, cedula):
        query = """
            SELECT
                e.nombres,
                e.apellidos,
                e.cedula,
                e.fecha_nacimiento,
                g.nombre AS nombre_grado,
                m.ano_que_cursa,
                m.codigo_ano_escolar
            FROM
                estudiante e
            JOIN
                matricula m ON e.cedula = m.cedula_estudiante
            JOIN
                grado g ON m.ano_que_cursa = g.numero_ano
            WHERE
                e.cedula = %s
            ORDER BY m.codigo_ano_escolar DESC
            LIMIT 1;
        """
        result = self.execute_query(query, (cedula,))
        if result:
            return result[0]
        return None

    def get_all_students_for_list(self, search_text=""):
        query = """
            SELECT
                e.cedula,
                e.nombres,
                e.apellidos,
                m.ano_que_cursa
            FROM
                estudiante e
            JOIN
                matricula m ON e.cedula = m.cedula_estudiante
            WHERE
                e.estado_estudiante = 'ACTIVO'
                AND (e.cedula ILIKE %s OR e.nombres ILIKE %s OR e.apellidos ILIKE %s)
            ORDER BY e.apellidos, e.nombres;
        """
        search_param = f"%{search_text}%"
        result = self.execute_query(query, (search_param, search_param, search_param))
        return result


# --- Parte 2: Clase para Generar PDF ---
class PDFGenerator:
    def __init__(self, filename="constancia_de_estudio.pdf"):
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()
        self.meses_espanol = {
            1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
            5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
            9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
        }
        self.logo_izquierda_path = None
        self.escudo_derecha_path = None

    def set_image_paths(self, logo_path, escudo_path):
        self.logo_izquierda_path = logo_path
        self.escudo_derecha_path = escudo_path

    def create_custom_styles(self):
        self.styles.add(ParagraphStyle(name='Justificado',
                                             parent=self.styles['Normal'],
                                             alignment=TA_JUSTIFY,
                                             fontName='Helvetica',
                                             fontSize=12,
                                             leading=14))

        self.styles.add(ParagraphStyle(name='TituloInstitucional',
                                             parent=self.styles['Normal'],
                                             alignment=TA_CENTER,
                                             fontName='Helvetica-Bold',
                                             fontSize=10,
                                             spaceAfter=0))

        self.styles.add(ParagraphStyle(name='TituloConstancia',
                                             parent=self.styles['Normal'],
                                             alignment=TA_CENTER,
                                             fontName='Helvetica-Bold',
                                             fontSize=14,
                                             spaceAfter=20))

        self.styles.add(ParagraphStyle(name='AtentamenteCentrado',
                                             parent=self.styles['Normal'],
                                             alignment=TA_CENTER,
                                             fontName='Helvetica',
                                             fontSize=12,
                                             spaceBefore=0,
                                             spaceAfter=0))

        self.styles.add(ParagraphStyle(name='LineaCortaCentrada',
                                             parent=self.styles['Normal'],
                                             alignment=TA_CENTER,
                                             fontName='Helvetica-Bold',
                                             fontSize=14,
                                             leading=1,
                                             spaceBefore=5,
                                             spaceAfter=0))

        self.styles.add(ParagraphStyle(name='CargoFirma',
                                             parent=self.styles['Normal'],
                                             alignment=TA_CENTER,
                                             fontName='Helvetica',
                                             fontSize=12,
                                             spaceBefore=0,
                                             spaceAfter=0))

        self.styles.add(ParagraphStyle(name='LineaFirma',
                                             parent=self.styles['Normal'],
                                             alignment=TA_CENTER,
                                             fontName='Helvetica-Bold',
                                             fontSize=14,
                                             spaceBefore=5,
                                             spaceAfter=0))


    def generate_constancia_estudio(self, student_data, fecha_expedicion):
        doc = SimpleDocTemplate(self.filename, pagesize=letter,
                                 leftMargin=inch, rightMargin=inch,
                                 topMargin=inch, bottomMargin=inch)
        Story = []

        # --- SECCIÓN DE CABECERA CON IMÁGENES Y TEXTO ---
        header_text_style = self.styles['TituloInstitucional']
        header_text_elements = [
            Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", header_text_style),
            Paragraph("ESTADO BOLIVARIANO DE MIRANDA", header_text_style),
            Paragraph("UNIDAD EDUCATIVA ESTADAL “CARMEN RUIZ”", header_text_style),
            Paragraph("CÓDIGO PLANTEL: OD00221508", header_text_style),
            Paragraph("CHARALLAVE – CRISTÓBAL ROJAS", header_text_style),
            Paragraph("TELÉFONO: 0239.2487847", header_text_style),
        ]

        logo_izq = None
        if self.logo_izquierda_path and os.path.exists(self.logo_izquierda_path):
            try:
                logo_izq = Image(self.logo_izquierda_path, width=1.0 * inch, height=1.0 * inch)
                logo_izq.hAlign = 'LEFT'
            except Exception as e:
                QMessageBox.warning(None, "Error de Imagen", f"No se pudo cargar el logo izquierdo: {e}")
                logo_izq = None

        escudo_der = None
        if self.escudo_derecha_path and os.path.exists(self.escudo_derecha_path):
            try:
                escudo_der = Image(self.escudo_derecha_path, width=1.0 * inch, height=1.0 * inch)
                escudo_der.hAlign = 'RIGHT'
            except Exception as e:
                QMessageBox.warning(None, "Error de Imagen", f"No se pudo cargar el escudo derecho: {e}")
                escudo_der = None

        header_table_data = [
            [logo_izq if logo_izq else '', header_text_elements, escudo_der if escudo_der else '']
        ]

        header_table_style = TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (2, 0), (2, 0), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ])

        col_widths = [1.2 * inch, None, 1.2 * inch]

        header_table = Table(header_table_data, colWidths=col_widths)
        header_table.setStyle(header_table_style)
        Story.append(header_table)
        Story.append(Spacer(1, 0.4 * inch))
        # --- FIN SECCIÓN DE CABECERA CON IMÁGENES Y TEXTO ---

        # Título de la constancia (TituloConstancia con fontSize=14)
        Story.append(Paragraph("CONSTANCIA DE ESTUDIO", self.styles['TituloConstancia']))
        Story.append(Spacer(1, 0.8 * inch))

        # Contenido de la constancia
        nombres = student_data[0]
        apellidos = student_data[1]
        cedula = student_data[2]
        fecha_nacimiento = student_data[3]
        nombre_grado = student_data[4]
        ano_que_cursa = student_data[5]
        ano_escolar = student_data[6]

        today = datetime.today()
        age = today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

        nombre_completo_html = f"<b>{nombres.upper()} {apellidos.upper()}</b>"
        cedula_html = f"<b>{cedula}</b>"
        age_html = f"<b>{age}</b>"
        grado_a_mostrar_html = f"<b>{ano_que_cursa}º</b>"

        main_text = (
            "Quien Suscribe, Directivo de la Unidad Educativa Estadal “Carmen Ruiz”, "
            "hace constar por medio de la presente que el (la) estudiante: "
            f"{nombre_completo_html}, portador (a) de la Cédula de Identidad N° {cedula_html}, "
            f"de {age_html} Años, y cursa el: {grado_a_mostrar_html}, en esta Institución Educativa."
        )
        Story.append(Paragraph(main_text, self.styles['Justificado']))
        Story.append(Spacer(1, 0.15 * inch))

        ano_escolar_html = f"Año escolar <b>{ano_escolar}</b>."
        Story.append(Paragraph(ano_escolar_html, self.styles['Justificado']))
        Story.append(Spacer(1, 0.3 * inch))

        dia = fecha_expedicion.day
        mes_str = self.meses_espanol.get(fecha_expedicion.month, "MES DESCONOCIDO")
        año_str = fecha_expedicion.year

        fecha_expedicion_html = (
            f"Constancia que se expide en la ciudad de CHARALLAVE a los "
            f"<b>{dia}</b> días del mes de <b>{mes_str}</b> del año <b>{año_str}</b>."
        )
        Story.append(Paragraph(fecha_expedicion_html, self.styles['Justificado']))
        Story.append(Spacer(1, 1.0 * inch))

        # --- SECCIÓN DE FIRMA ---
        Story.append(Paragraph("Atentamente", self.styles['AtentamenteCentrado']))
        Story.append(Paragraph('_________________________', self.styles['LineaCortaCentrada']))
        Story.append(Spacer(1, 1.0 * inch))
        Story.append(Paragraph("Directivo", self.styles['CargoFirma']))
        Story.append(Paragraph("__________________________________________", self.styles['LineaFirma']))
        # --- FIN SECCIÓN DE FIRMA ---

        Story.append(Spacer(1, 0.5 * inch))

        try:
            doc.build(Story)
            QMessageBox.information(None, "Éxito", f"Constancia de estudio generada como '{self.filename}'")
            pdf_path = os.path.abspath(self.filename)
            try:
                if platform.system() == "Windows":
                    os.startfile(pdf_path)
                elif platform.system() == "Darwin": # macOS
                    os.system(f"open \"{pdf_path}\"")
                else: # Linux
                    os.system(f"xdg-open \"{pdf_path}\"")
            except Exception as e:
                QMessageBox.warning(None, "Error al Abrir PDF", f"No se pudo abrir el PDF automáticamente. Error: {e}")

        except Exception as e:
            QMessageBox.critical(None, "Error al Generar PDF", f"Ocurrió un error al construir el PDF: {e}")


# --- Parte 3: Interfaz de Usuario (PyQt6) ---
class ConstanciaApp(QWidget):
    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config
        self.user_data = user_data
        
        # Iniciar DatabaseManager solo si la configuración es válida
        self.db = None
        if self.db_config:
            self.db = DatabaseManager(db_config=self.db_config)
        else:
            QMessageBox.critical(self, "Error de Inicio",
                                 "No se pudo cargar la configuración de la base de datos. "
                                 "La aplicación no puede funcionar sin ella. Por favor, revise el archivo de configuración.")
            # Si no hay DB config, la aplicación debe cerrarse o deshabilitar funcionalidades
            self.is_db_ready = False
            return

        self.is_db_ready = True # Marcador para saber si la DB está lista
        self.pdf_gen = PDFGenerator()

        # Variables para almacenar las rutas de imagen seleccionadas por el usuario
        self.logo_left_path = "logo_escuela.jpg" # Ruta predeterminada
        self.escudo_right_path = "escudo_venezuela.jpg" # Ruta predeterminada
        self.output_directory = os.path.expanduser("~/Documentos/ConstanciasEstudio") # Directorio de salida predeterminado

        self.init_ui()
        if self.is_db_ready:
            self.load_students()
        else:
            self.setDisabled(True) # Deshabilita la ventana si la DB no está lista

    def init_ui(self):
        self.setWindowTitle("Generador de Constancias de Estudio")
        self.setGeometry(100, 100, 900, 700)

        # --- Definición de la paleta de colores ---
        COLOR_BACKGROUND_LIGHT = "#e4eaf4"
        COLOR_ACCENT_LIGHT = "#b3cbdc"
        COLOR_ACCENT_MEDIUM = "#7089a7"
        COLOR_PRIMARY_DARK = "#1c355b"

        # --- Estilos Globales (aplicados a la ventana principal) ---
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                color: {COLOR_PRIMARY_DARK};
                font-family: Arial;
                font-size: 10pt;
            }}
            QLabel {{
                color: {COLOR_PRIMARY_DARK};
                font-weight: bold;
            }}
            QLineEdit {{
                background-color: white;
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                padding: 5px;
                border-radius: 4px;
                color: {COLOR_PRIMARY_DARK};
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY_DARK};
                color: {COLOR_BACKGROUND_LIGHT};
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_MEDIUM};
            }}
            QTableWidget {{
                background-color: white;
                alternate-background-color: {COLOR_BACKGROUND_LIGHT};
                border: 1px solid {COLOR_ACCENT_LIGHT};
                gridline-color: {COLOR_ACCENT_LIGHT};
                selection-background-color: {COLOR_ACCENT_MEDIUM};
                selection-color: white;
            }}
            QTableWidget QHeaderView::section {{
                background-color: {COLOR_PRIMARY_DARK};
                color: white;
                padding: 5px;
                border: 1px solid {COLOR_ACCENT_LIGHT};
            }}
            QDateEdit, QComboBox {{
                background-color: white;
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                padding: 5px;
                border-radius: 4px;
                color: {COLOR_PRIMARY_DARK};
            }}
            QSplitter::handle {{
                background-color: {COLOR_ACCENT_LIGHT};
                width: 5px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLOR_ACCENT_MEDIUM};
            }}
            QGroupBox {{
                font-weight: bold;
                color: {COLOR_PRIMARY_DARK};
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                border-radius: 5px;
                margin-top: 1ex; /* Espacio para el título */
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center; /* Centrar el título */
                padding: 0 3px;
                background-color: {COLOR_BACKGROUND_LIGHT}; /* Fondo del título para que no se vea el borde */
            }}
        """)

        main_layout = QVBoxLayout(self)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel (Student List)
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por Cédula o Nombres...")
        self.search_input.textChanged.connect(self.load_students)
        left_panel_layout.addWidget(self.search_input)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(["Cédula", "Nombres", "Apellidos", "Grado Actual"])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.student_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.student_table.itemSelectionChanged.connect(self.select_student_from_table)
        left_panel_layout.addWidget(self.student_table)
        top_splitter.addWidget(left_panel_widget)


        # Right Panel (Student Details and Generation)
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)

        self.title_details = QLabel("Detalles del Estudiante")
        self.title_details.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLOR_PRIMARY_DARK};")
        right_panel_layout.addWidget(self.title_details)

        self.fields = {}

        def add_detail_field(layout_obj, label_text, key):
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setReadOnly(True)
            layout_obj.addWidget(label)
            layout_obj.addWidget(line_edit)
            self.fields[key] = line_edit

        add_detail_field(right_panel_layout, "Nombre Completo:", "nombre_completo")
        add_detail_field(right_panel_layout, "Cédula:", "cedula")
        add_detail_field(right_panel_layout, "Edad:", "edad")
        add_detail_field(right_panel_layout, "Grado y Sección Cursado:", "grado_seccion")
        add_detail_field(right_panel_layout, "Año Escolar:", "ano_escolar")

        self.label_fecha_exp = QLabel("Fecha de Expedición:")
        self.date_expedicion = QDateEdit(calendarPopup=True)
        self.date_expedicion.setDate(QDate.currentDate())
        right_panel_layout.addWidget(self.label_fecha_exp)
        right_panel_layout.addWidget(self.date_expedicion)

        top_splitter.addWidget(right_panel_widget)

        top_splitter.setSizes([300, 600])

        main_layout.addWidget(top_splitter)

        # --- Sección de Configuración de Archivos (parte inferior) ---
        config_group_box = QGroupBox("Configuración de Archivos")
        config_layout = QVBoxLayout(config_group_box)

        # Directorio de Salida
        output_dir_h_layout = QHBoxLayout()
        self.output_dir_label = QLabel("Directorio de Salida de PDFs:")
        output_dir_h_layout.addWidget(self.output_dir_label)
        self.output_dir_input = QLineEdit(self.output_directory)
        output_dir_h_layout.addWidget(self.output_dir_input)
        self.btn_select_output_dir = QPushButton("Seleccionar Directorio...")
        self.btn_select_output_dir.clicked.connect(self.select_output_directory)
        output_dir_h_layout.addWidget(self.btn_select_output_dir)
        config_layout.addLayout(output_dir_h_layout)

        # Logo Izquierdo
        logo_left_h_layout = QHBoxLayout()
        self.logo_left_label = QLabel("Ruta del Logo Izquierdo:")
        logo_left_h_layout.addWidget(self.logo_left_label)
        self.logo_left_input = QLineEdit(self.logo_left_path)
        logo_left_h_layout.addWidget(self.logo_left_input)
        self.btn_select_logo_left = QPushButton("Seleccionar Logo...")
        self.btn_select_logo_left.clicked.connect(self.select_logo_left)
        logo_left_h_layout.addWidget(self.btn_select_logo_left)
        config_layout.addLayout(logo_left_h_layout)

        # Escudo Derecho
        escudo_right_h_layout = QHBoxLayout()
        self.escudo_right_label = QLabel("Ruta del Escudo Derecho:")
        escudo_right_h_layout.addWidget(self.escudo_right_label)
        self.escudo_right_input = QLineEdit(self.escudo_right_path)
        escudo_right_h_layout.addWidget(self.escudo_right_input)
        self.btn_select_escudo_right = QPushButton("Seleccionar Escudo...")
        self.btn_select_escudo_right.clicked.connect(self.select_escudo_right)
        escudo_right_h_layout.addWidget(self.btn_select_escudo_right)
        config_layout.addLayout(escudo_right_h_layout)

        main_layout.addWidget(config_group_box)

        # Botón Generar
        self.btn_generar = QPushButton("Generar Constancia de Estudio")
        self.btn_generar.clicked.connect(self.generar_constancia)
        self.btn_generar.setEnabled(False) # Deshabilitado hasta que se seleccione un estudiante
        main_layout.addWidget(self.btn_generar)

        # Variables para almacenar la cédula y los datos completos del estudiante
        self.current_selected_cedula = None
        self.student_full_data = None

    def select_output_directory(self):
        dir_dialog = QFileDialog(self)
        dir_dialog.setFileMode(QFileDialog.FileMode.Directory)
        dir_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dir_dialog.setWindowTitle("Seleccionar Directorio de Salida")
        if dir_dialog.exec():
            selected_dir = dir_dialog.selectedFiles()
            if selected_dir:
                self.output_directory = selected_dir[0]
                self.output_dir_input.setText(self.output_directory)

    def select_logo_left(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Archivo de Logo Izquierdo")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_left_path = selected_files[0]
                self.logo_left_input.setText(self.logo_left_path)

    def select_escudo_right(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Archivo de Escudo Derecho")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.escudo_right_path = selected_files[0]
                self.escudo_right_input.setText(self.escudo_right_path)

    def load_students(self):
        if not self.is_db_ready: # No intentar cargar estudiantes si la DB no está lista
            return

        search_text = self.search_input.text()
        students = self.db.get_all_students_for_list(search_text)
        self.student_table.setRowCount(0)

        if students:
            self.student_table.setRowCount(len(students))
            for row_idx, student in enumerate(students):
                cedula, nombres, apellidos, ano_que_cursa = student
                self.student_table.setItem(row_idx, 0, QTableWidgetItem(cedula))
                self.student_table.setItem(row_idx, 1, QTableWidgetItem(nombres))
                self.student_table.setItem(row_idx, 2, QTableWidgetItem(apellidos))
                self.student_table.setItem(row_idx, 3, QTableWidgetItem(f"{ano_que_cursa}º"))
        elif search_text:
            QMessageBox.information(self, "Información", "No se encontraron estudiantes con ese criterio de búsqueda.")
        else:
            pass # No mostrar mensaje si no hay búsqueda y la tabla está vacía (ej. al inicio)


    def select_student_from_table(self):
        if not self.is_db_ready:
            return

        selected_items = self.student_table.selectedItems()
        if not selected_items:
            for key in self.fields:
                self.fields[key].clear()
            self.btn_generar.setEnabled(False)
            self.current_selected_cedula = None
            self.student_full_data = None
            return

        row = selected_items[0].row()
        cedula = self.student_table.item(row, 0).text()
        self.current_selected_cedula = cedula

        self.student_full_data = self.db.get_student_data(cedula)

        if self.student_full_data:
            nombres, apellidos, cedula_found, fecha_nacimiento, nombre_grado, ano_que_cursa, ano_escolar = self.student_full_data

            today = datetime.today()
            age = today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

            self.fields["nombre_completo"].setText(f"{nombres} {apellidos}")
            self.fields["cedula"].setText(cedula_found)
            self.fields["edad"].setText(str(age))
            self.fields["grado_seccion"].setText(f"{ano_que_cursa}º ({nombre_grado if nombre_grado else 'N/A'})")
            self.fields["ano_escolar"].setText(ano_escolar)
            self.btn_generar.setEnabled(True)
        else:
            QMessageBox.warning(self, "Error", "No se pudieron cargar los detalles del estudiante.")
            self.btn_generar.setEnabled(False)
            self.current_selected_cedula = None
            self.student_full_data = None

    def generar_constancia(self):
        if not self.is_db_ready:
            QMessageBox.critical(self, "Error de Base de Datos", "La aplicación no está conectada a la base de datos.")
            return

        if not self.student_full_data:
            QMessageBox.warning(self, "Advertencia", "No hay un estudiante seleccionado para generar la constancia.")
            return

        if not (self.logo_left_path and os.path.exists(self.logo_left_path)):
            QMessageBox.warning(self, "Advertencia", "La ruta del logo izquierdo no es válida o el archivo no existe. El PDF se generará sin este logo.")
        if not (self.escudo_right_path and os.path.exists(self.escudo_right_path)):
            QMessageBox.warning(self, "Advertencia", "La ruta del escudo derecho no es válida o el archivo no existe. El PDF se generará sin este escudo.")

        os.makedirs(self.output_directory, exist_ok=True)

        cedula_estudiante = self.student_full_data[2]
        current_datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = os.path.join(self.output_directory, f"Constancia_Estudio_{cedula_estudiante}_{current_datetime_str}.pdf")

        self.pdf_gen.filename = pdf_filename
        self.pdf_gen.set_image_paths(self.logo_left_path, self.escudo_right_path)

        fecha_expedicion_qdate = self.date_expedicion.date()
        fecha_expedicion_dt = datetime(
            fecha_expedicion_qdate.year(),
            fecha_expedicion_qdate.month(),
            fecha_expedicion_qdate.day()
        )
        try:
            self.pdf_gen.generate_constancia_estudio(self.student_full_data, fecha_expedicion_dt)

        except Exception as e:
            QMessageBox.critical(self, "Error al Generar PDF", f"Ocurrió un error: {e}")
        finally:
            self.student_table.clearSelection()


    def closeEvent(self, event):
        if self.db: # Asegurarse de que el objeto db existe antes de intentar desconectar
            self.db.disconnect()
        event.accept()


# --- Ejecución de la Aplicación ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Cargar la configuración de la base de datos desde el archivo
    db_params = load_db_config()

    # Si la configuración de la DB no se pudo cargar, no iniciar la ventana principal
    if db_params is None:
        sys.exit(1) # Salir con un código de error

    # Datos de usuario simulados para pruebas
    # Estos datos no deberían venir de un archivo público si contienen información sensible.
    # Podrían venir de un sistema de autenticación, variables de entorno, etc.
    user_data = {
        'id': 1,
        'username': 'admin',
        'role': 'secretaria'
    }

    window = ConstanciaApp(db_config=db_params, user_data=user_data)
    # Mostrar la ventana solo si la configuración de la DB fue exitosa y la app se inicializó bien
    if window.is_db_ready:
        window.show()
    else:
        sys.exit(1) # Salir si la inicialización de la app falló (ej. por DB no lista)

    sys.exit(app.exec())