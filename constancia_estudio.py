import sys
import psycopg2
from psycopg2 import Error
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit,
    QMessageBox, QTableWidget, QTableWidgetItem, QHBoxLayout, QSplitter,
    QHeaderView, QDateEdit, QComboBox, QFileDialog # Importar QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, cm
from datetime import datetime
import os

# --- Importaciones adicionales para ReportLab Platypus ---
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import black
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
# --- Fin de importaciones adicionales ---


# --- Parte 1: Clase para la Base de Datos ---
class DatabaseManager:
    # El constructor ahora acepta un diccionario db_config
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.connect() # Conectar al instanciar

    def connect(self):
        try:
            # Usar el diccionario db_config para la conexión
            self.conn = psycopg2.connect(
                dbname=self.db_config.get('database'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password'),
                host=self.db_config.get('host'),
                port=self.db_config.get('port')
            )
            print(f"Conexión a la base de datos '{self.db_config.get('database')}' exitosa para Constancia de Estudio.")
        except Error as e:
            QMessageBox.critical(None, "Error de Conexión", f"No se pudo conectar a la base de datos: {e}")
            self.conn = None

    def disconnect(self):
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")

    def execute_query(self, query, params=None):
        if not self.conn or self.conn.closed: # Verificar si la conexión está cerrada o no existe
            self.connect() # Intentar reconectar
            if not self.conn: # Si la reconexión falla, no se puede ejecutar la consulta
                return None

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
            # Realizar rollback en caso de error en operaciones de escritura
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
            return result[0] # Retorna la primera fila (tupla)
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
    # El constructor ahora acepta rutas de imagen como parámetros
    def __init__(self, filename="constancia_de_estudio.pdf", logo_izquierda_path=None, escudo_derecha_path=None):
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()
        self.meses_espanol = {
            1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
            5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
            9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
        }
        # Rutas de las imágenes, ahora se toman de los parámetros o se usan valores por defecto
        self.logo_izquierda_path = logo_izquierda_path
        self.escudo_derecha_path = escudo_derecha_path


    def create_custom_styles(self):
        # Estilo para el texto justificado
        self.styles.add(ParagraphStyle(name='Justificado',
                                         parent=self.styles['Normal'],
                                         alignment=TA_JUSTIFY,
                                         fontName='Helvetica',
                                         fontSize=12,
                                         leading=14))

        # Estilo para los títulos institucionales (centrado, negrita y tamaño más pequeño)
        self.styles.add(ParagraphStyle(name='TituloInstitucional',
                                         parent=self.styles['Normal'],
                                         alignment=TA_CENTER,
                                         fontName='Helvetica-Bold',
                                         fontSize=10,
                                         spaceAfter=0))

        # Estilo para el título principal de la constancia (más grande, tamaño 14)
        self.styles.add(ParagraphStyle(name='TituloConstancia',
                                         parent=self.styles['Normal'],
                                         alignment=TA_CENTER,
                                         fontName='Helvetica-Bold',
                                         fontSize=14,
                                         spaceAfter=20))

        # Estilo para el texto "Atentamente" centrado
        self.styles.add(ParagraphStyle(name='AtentamenteCentrado',
                                         parent=self.styles['Normal'],
                                         alignment=TA_CENTER,
                                         fontName='Helvetica',
                                         fontSize=12,
                                         spaceBefore=0,
                                         spaceAfter=0))

        # Estilo para la línea corta debajo de "Atentamente"
        self.styles.add(ParagraphStyle(name='LineaCortaCentrada',
                                         parent=self.styles['Normal'],
                                         alignment=TA_CENTER,
                                         fontName='Helvetica-Bold',
                                         fontSize=14,
                                         leading=1,
                                         spaceBefore=5,
                                         spaceAfter=0))

        # Estilo para el texto "Directivo" (centrado, encima de la línea)
        self.styles.add(ParagraphStyle(name='CargoFirma',
                                         parent=self.styles['Normal'],
                                         alignment=TA_CENTER,
                                         fontName='Helvetica',
                                         fontSize=12,
                                         spaceBefore=0,
                                         spaceAfter=0))

        # Estilo para la línea de firma (centrada)
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
        # Usar self.logo_izquierda_path que ahora es dinámico
        if self.logo_izquierda_path and os.path.exists(self.logo_izquierda_path):
            logo_izq = Image(self.logo_izquierda_path, width=1.0 * inch, height=1.0 * inch)
            logo_izq.hAlign = 'LEFT'

        escudo_der = None
        # Usar self.escudo_derecha_path que ahora es dinámico
        if self.escudo_derecha_path and os.path.exists(self.escudo_derecha_path):
            escudo_der = Image(self.escudo_derecha_path, width=1.0 * inch, height=1.0 * inch)
            escudo_der.hAlign = 'RIGHT'

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
                if sys.platform == "win32":
                    os.startfile(pdf_path)
                elif sys.platform == "darwin":
                    os.system(f"open {pdf_path.replace(' ', '\\ ')}")
                else:
                    os.system(f"xdg-open {pdf_path.replace(' ', '\\ ')}")
            except Exception as e:
                QMessageBox.warning(None, "Error al Abrir PDF", f"No se pudo abrir el PDF automáticamente. Error: {e}")

        except Exception as e:
            QMessageBox.critical(None, "Error al Generar PDF", f"Ocurrió un error al construir el PDF: {e}")


# --- Parte 3: Interfaz de Usuario (PyQt6) ---
class ConstanciaApp(QWidget):
    # El constructor ahora acepta db_config y user_data
    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config # Almacenar la configuración de la base de datos
        self.user_data = user_data # Almacenar los datos del usuario (si se necesitan más adelante)
        # Inicializar PDFGenerator con rutas iniciales vacías o predeterminadas
        self.pdf_gen = PDFGenerator(logo_izquierda_path="", escudo_derecha_path="") 
        self.db = DatabaseManager(db_config=self.db_config) # Pasar el diccionario db_config
        self.init_ui()
        self.load_students()

    def init_ui(self):
        self.setWindowTitle("Generador de Constancias de Estudio")
        self.setGeometry(100, 100, 900, 600)

        # --- Definición de la paleta de colores ---
        COLOR_BACKGROUND_LIGHT = "#e4eaf4"   # Blanco muy claro/grisáceo
        COLOR_ACCENT_LIGHT = "#b3cbdc"       # Azul claro/grisáceo
        COLOR_ACCENT_MEDIUM = "#7089a7"      # Azul grisáceo medio
        COLOR_PRIMARY_DARK = "#1c355b"       # Azul oscuro profundo

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
            QPushButton:pressed {{
                background-color: {COLOR_PRIMARY_DARK};
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
            QDateEdit {{
                background-color: white;
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                padding: 5px;
                border-radius: 4px;
                color: {COLOR_PRIMARY_DARK};
            }}
            QComboBox {{
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
        """)

        main_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        left_panel_widget = QWidget()
        left_panel_widget.setLayout(left_panel)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por Cédula o Nombres...")
        self.search_input.textChanged.connect(self.load_students)
        left_panel.addWidget(self.search_input)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(["Cédula", "Nombres", "Apellidos", "Grado Actual"])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.student_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.student_table.itemSelectionChanged.connect(self.select_student_from_table)
        left_panel.addWidget(self.student_table)

        right_panel = QVBoxLayout()
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel)

        self.title_details = QLabel("Detalles del Estudiante")
        self.title_details.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLOR_PRIMARY_DARK};")
        right_panel.addWidget(self.title_details)

        self.fields = {}

        def add_detail_field(layout_obj, label_text, key):
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setReadOnly(True)
            layout_obj.addWidget(label)
            layout_obj.addWidget(line_edit)
            self.fields[key] = line_edit

        add_detail_field(right_panel, "Nombre Completo:", "nombre_completo")
        add_detail_field(right_panel, "Cédula:", "cedula")
        add_detail_field(right_panel, "Edad:", "edad")
        add_detail_field(right_panel, "Grado y Sección Cursado:", "grado_seccion")
        add_detail_field(right_panel, "Año Escolar:", "ano_escolar")

        self.label_fecha_exp = QLabel("Fecha de Expedición:")
        self.date_expedicion = QDateEdit(calendarPopup=True)
        self.date_expedicion.setDate(QDate.currentDate())
        right_panel.addWidget(self.label_fecha_exp)
        right_panel.addWidget(self.date_expedicion)

        # --- Nuevos elementos para selección de imágenes ---
        image_selection_group_layout = QVBoxLayout()
        image_selection_group_layout.addWidget(QLabel("<b>Configuración de Imágenes del PDF:</b>"))

        # Selección de Logo Izquierdo
        logo_izq_layout = QHBoxLayout()
        logo_izq_layout.addWidget(QLabel("Ruta Logo Izquierdo:"))
        self.logo_izquierda_path_input = QLineEdit("logo_escuela.jpg") # Ruta predeterminada
        self.logo_izquierda_path_input.setReadOnly(True) # Opcional: hacerla solo lectura si siempre se selecciona
        logo_izq_layout.addWidget(self.logo_izquierda_path_input)
        btn_select_logo_izq = QPushButton("Seleccionar Logo...")
        btn_select_logo_izq.clicked.connect(self.select_logo_izquierda_path)
        logo_izq_layout.addWidget(btn_select_logo_izq)
        image_selection_group_layout.addLayout(logo_izq_layout)

        # Selección de Escudo Derecho
        escudo_der_layout = QHBoxLayout()
        escudo_der_layout.addWidget(QLabel("Ruta Escudo Derecho:"))
        self.escudo_derecha_path_input = QLineEdit("escudo_venezuela.jpg") # Ruta predeterminada
        self.escudo_derecha_path_input.setReadOnly(True) # Opcional: hacerla solo lectura si siempre se selecciona
        escudo_der_layout.addWidget(self.escudo_derecha_path_input)
        btn_select_escudo_der = QPushButton("Seleccionar Escudo...")
        btn_select_escudo_der.clicked.connect(self.select_escudo_derecha_path)
        escudo_der_layout.addWidget(btn_select_escudo_der)
        image_selection_group_layout.addLayout(escudo_der_layout)

        right_panel.addLayout(image_selection_group_layout)
        # --- Fin de nuevos elementos para selección de imágenes ---


        self.btn_generar = QPushButton("Generar Constancia de Estudio")
        self.btn_generar.clicked.connect(self.generar_constancia)
        self.btn_generar.setEnabled(False)
        right_panel.addWidget(self.btn_generar)

        right_panel.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel_widget)
        splitter.addWidget(right_panel_widget)
        splitter.setSizes([300, 600])

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.current_selected_cedula = None
        self.student_full_data = None

    def select_logo_izquierda_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Logo Izquierdo")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_izquierda_path_input.setText(selected_files[0])

    def select_escudo_derecha_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Escudo Derecho")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.escudo_derecha_path_input.setText(selected_files[0])

    def load_students(self):
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

    def select_student_from_table(self):
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
        if self.student_full_data:
            fecha_expedicion_qdate = self.date_expedicion.date()
            fecha_expedicion_dt = datetime(
                fecha_expedicion_qdate.year(),
                fecha_expedicion_qdate.month(),
                fecha_expedicion_qdate.day()
            )
            try:
                # Actualizar las rutas de las imágenes en la instancia de PDFGenerator
                self.pdf_gen.logo_izquierda_path = self.logo_izquierda_path_input.text()
                self.pdf_gen.escudo_derecha_path = self.escudo_derecha_path_input.text()

                self.pdf_gen.generate_constancia_estudio(self.student_full_data, fecha_expedicion_dt)

            except Exception as e:
                QMessageBox.critical(self, "Error al Generar PDF", f"Ocurrió un error: {e}")
        else:
            QMessageBox.warning(self, "Advertencia", "No hay datos de estudiante para generar la constancia.")

    def closeEvent(self, event):
        self.db.disconnect()
        event.accept()


# --- Ejecución de la Aplicación ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Configuración de la base de datos para pruebas independientes
    test_db_config = {
        "database": "bd",
        "user": "postgres",
        "password": "12345678",
        "host": "localhost",
        "port": "5432"
    }

    # Datos de usuario simulados para pruebas independientes
    test_user_data = {
        'id': 1,
        'username': 'testuser_estudio',
        'role': 'secretaria'
    }

    window = ConstanciaApp(db_config=test_db_config, user_data=test_user_data)
    window.show()
    sys.exit(app.exec())
