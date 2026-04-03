import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QDateEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
import psycopg2
from psycopg2 import Error
import os
from datetime import date

# Importaciones de ReportLab (mantener aquí para que CertificateGenerator las tenga disponibles)
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus.flowables import Image
from reportlab.lib.utils import ImageReader


# --- 1. Configuración de la Base de Datos y Funciones de Consulta ---
class DatabaseManager:
    # MODIFICACIÓN: Ahora recibe db_config como un diccionario
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_config.get('database'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password'),
                host=self.db_config.get('host'),
                port=self.db_config.get('port')
            )
            print("Conexión a la base de datos exitosa.")
        except Error as e:
            print(f"Error al conectar a la base de datos: {e}")
            QMessageBox.critical(None, "Error de Conexión",
                                 f"No se pudo conectar a la base de datos: {e}\n"
                                 "Por favor, verifica los parámetros de conexión.")
            self.conn = None

    def close(self):
        if self.conn:
            self.conn.close()
            print("Conexión a la base de datos cerrada.")

    def get_student_data_for_withdrawal(self, cedula_estudiante):
        if not self.conn:
            QMessageBox.warning(None, "Error de Conexión", "No hay conexión activa a la base de datos.")
            return None

        try:
            with self.conn.cursor() as cur:
                query = """
                SELECT
                    e.nombres,
                    e.apellidos,
                    e.cedula,
                    e.fecha_nacimiento,
                    e.lugar_nacimiento,
                    e.motivo_retiro,
                    e.fecha_retiro,
                    m.ano_que_cursa,
                    s.letra AS nombre_seccion,
                    ae.ano_inicio,
                    ae.ano_fin,
                    r.nombres AS representante_nombres,
                    r.apellidos AS representante_apellidos
                FROM
                    estudiante e
                JOIN
                    matricula m ON e.cedula = m.cedula_estudiante
                LEFT JOIN
                    seccion s ON m.codigo_seccion = s.codigo
                LEFT JOIN
                    ano_escolar ae ON m.codigo_ano_escolar = ae.codigo
                LEFT JOIN
                    representante r ON m.cedula_representante = r.cedula
                WHERE
                    e.cedula = %s
                ORDER BY
                    m.fecha_matricula DESC
                LIMIT 1;
                """
                cur.execute(query, (cedula_estudiante,))
                result = cur.fetchone()
                return result
        except Error as e:
            print(f"Error al obtener datos del estudiante: {e}")
            QMessageBox.critical(None, "Error de Consulta", f"Error al obtener datos del estudiante: {e}")
            return None

    def get_all_students_summary(self):
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                query = """
                WITH LatestMatricula AS (
                    SELECT
                        m.cedula_estudiante,
                        MAX(m.fecha_matricula) AS max_fecha_matricula
                    FROM
                        matricula m
                    GROUP BY
                        m.cedula_estudiante
                )
                SELECT
                    e.cedula,
                    e.nombres,
                    e.apellidos,
                    e.estado_estudiante,
                    m.ano_que_cursa,
                    s.letra AS seccion
                FROM
                    estudiante e
                LEFT JOIN
                    LatestMatricula lm ON e.cedula = lm.cedula_estudiante
                LEFT JOIN
                    matricula m ON lm.cedula_estudiante = m.cedula_estudiante AND lm.max_fecha_matricula = m.fecha_matricula
                LEFT JOIN
                    seccion s ON m.codigo_seccion = s.codigo
                ORDER BY
                    e.apellidos, e.nombres;
                """
                cur.execute(query)
                return cur.fetchall()
        except Error as e:
            print(f"Error al obtener lista de estudiantes: {e}")
            QMessageBox.critical(None, "Error de Consulta", f"Error al obtener lista de estudiantes: {e}")
            return []

# --- 2. Lógica de Generación de la Constancia Mejorada ---
class CertificateGenerator:
    def __init__(self, logo_arriba_path=None, logo_escudo_path=None):
        self.styles = getSampleStyleSheet()

        # Estilo para el encabezado centrado
        self.styles.add(ParagraphStyle(
            name='HeaderStyle',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12,
            spaceAfter=4,
            fontName='Helvetica'
        ))

        # Estilo para el título de la constancia
        self.styles.add(ParagraphStyle(
            name='TitleStyle',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=14,
            fontName='Helvetica-Bold',
            spaceAfter=20,
            spaceBefore=20
        ))

        # Estilo para el cuerpo del documento con interlineado 1.5
        self.styles.add(ParagraphStyle(
            name='BodyStyle',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            fontSize=12,
            fontName='Helvetica',
            leading=18,  # Mantener 18 para 1.5 de interlineado (12 * 1.5 = 18)
            spaceAfter=12, # Espacio después del párrafo
            firstLineIndent=36   # Sangría de primera línea
        ))

        # Estilo para la firma
        self.styles.add(ParagraphStyle(
            name='SignatureStyle',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=12,
            fontName='Helvetica',
            spaceAfter=8
        ))

        # Rutas a las imágenes, ahora se inicializan con los parámetros
        self.logo_arriba_path = logo_arriba_path
        self.logo_escudo_path = logo_escudo_path

    def generate_withdrawal_certificate(self, data, output_path="Constancia_Retiro.pdf"):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=72,
            rightMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        story = []

        # --- ENCABEZADO CON IMÁGENES ---
        left_image_obj = None
        right_image_obj = None

        # Verificar si las imágenes existen y cargarlas
        if self.logo_arriba_path and os.path.exists(self.logo_arriba_path):
            left_image_obj = Image(self.logo_arriba_path, width=1.130 * inch, height=1.024 * inch) # Ajustado
            left_image_obj.hAlign = 'LEFT'
        else:
            left_image_obj = Paragraph("", self.styles['HeaderStyle'])
            QMessageBox.warning(None, "Advertencia", f"No se encontró la imagen en la ruta: {self.logo_arriba_path}. Se usará un espacio en blanco.")

        if self.logo_escudo_path and os.path.exists(self.logo_escudo_path):
            right_image_obj = Image(self.logo_escudo_path, width=0.831 * inch, height=0.803 * inch) # Ajustado
            right_image_obj.hAlign = 'RIGHT'
        else:
            right_image_obj = Paragraph("", self.styles['HeaderStyle'])
            QMessageBox.warning(None, "Advertencia", f"No se encontró la imagen en la ruta: {self.logo_escudo_path}. Se usará un espacio en blanco.")

        # Texto del encabezado
        header_text = """
        <para align="center">
        República Bolivariana de Venezuela<br/>
        Gobernación del Estado Miranda<br/>
        Dirección General de Educación<br/>
        <b>U.E.E. Carmen Ruiz</b><br/>
        <b>COD. DEA:OD00221508</b><br/>
        Charallave- Edo. Miranda
        </para>
        """

        # Tabla para el encabezado con imágenes y texto
        header_table_data = [
            [left_image_obj, Paragraph(header_text, self.styles['HeaderStyle']), right_image_obj]
        ]

        header_table = Table(header_table_data, colWidths=[1.5*inch, 3.5*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('LEFTPADDING', (1,0), (1,0), 0),
            ('RIGHTPADDING', (1,0), (1,0), 0),
        ]))

        story.append(header_table)
        story.append(Spacer(0, 0.3 * inch))

        # --- TÍTULO DE LA CONSTANCIA (AHORA EN CURSIVA) ---
        title_text = '<i><u><b>CONSTANCIA DE RETIRO</b></u></i>'
        story.append(Paragraph(title_text, self.styles['TitleStyle']))

        # --- PREPARAR DATOS ---
        nombre_completo = f"{data['nombres_estudiante']} {data['apellidos_estudiante']}"
        cedula_formatted = f"V-{data['cedula_estudiante']}" if data['cedula_estudiante'] else "V-_______________"
        fecha_nacimiento_str = data['fecha_nacimiento'].strftime("%d/%m/%Y") if data['fecha_nacimiento'] else "___/___/____"
        lugar_nacimiento = data['lugar_nacimiento'] if data['lugar_nacimiento'] else "_________________"
        edad_estudiante = self._calculate_age(data['fecha_nacimiento']) if data['fecha_nacimiento'] else "_____"

        # Convertir año a texto
        ano_texto = self._convert_year_to_text(data['ano_que_cursa'])
        seccion_letra = data['nombre_seccion'] if data['nombre_seccion'] else "_______________"
        ano_escolar = f"{data['ano_inicio_escolar']}-{data['ano_fin_escolar']}" if data['ano_inicio_escolar'] and data['ano_fin_escolar'] else "20___-20___"

        motivo_retiro = data['motivo_retiro'] if data['motivo_retiro'] else "____________________"
        nombre_representante = f"{data['nombres_representante']} {data['apellidos_representante']}".strip()
        if not nombre_representante.strip():
            nombre_representante = "____________________"

        # --- PÁRRAFO PRINCIPAL (DATOS EN NEGRITA) ---
        main_paragraph = f"""
        Quien suscribe, Directora (E) de la <b>Unidad Educativa Estadal "Carmen Ruíz"</b>. Profa.
        FRANCIA MARCANO, titular de la cédula de identidad <b>V- 3.882.635</b>, por medio de la presente hace constar que el alumno (a):
        <b>{nombre_completo}</b>, titular de la cédula de identidad <b>{cedula_formatted}</b>.
        Fecha de Nacimiento <b>{fecha_nacimiento_str}</b>, Lugar: <b>{lugar_nacimiento}</b>, de <b>{edad_estudiante}</b> años de edad
        cursó en esta Institución el <b>{ano_texto}</b> de <b>{seccion_letra}</b>, durante el año escolar <b>{ano_escolar}</b>.
        """

        story.append(Paragraph(main_paragraph, self.styles['BodyStyle']))

        # --- MOTIVO DE RETIRO (EN NEGRITA) ---
        motivo_paragraph = f"Retirado por: <b>{motivo_retiro}</b>"
        story.append(Paragraph(motivo_paragraph, self.styles['BodyStyle']))

        # --- REPRESENTANTE (EN NEGRITA) ---
        representante_paragraph = f"Persona que hace la solicitud, REPRESENTANTE: <b>{nombre_representante}</b>"
        story.append(Paragraph(representante_paragraph, self.styles['BodyStyle']))

        # --- FECHA DE EXPEDICIÓN (EN NEGRITA) ---
        meses = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        nombre_mes = meses.get(data['mes_expedicion'], "___________")

        fecha_expedicion = f"""
        Constancia que se expide a petición de la parte interesada a los <b>{data['dia_expedicion']}</b> días
        del mes de <b>{nombre_mes}</b> de <b>{data['ano_expedicion']}</b>
        """

        story.append(Paragraph(fecha_expedicion, self.styles['BodyStyle']))
        story.append(Spacer(0, 0.5 * inch))

        # --- FIRMA ---
        story.append(Paragraph("Atentamente,", self.styles['SignatureStyle']))
        story.append(Spacer(0, 0.8 * inch))  # Espacio para la firma física

        story.append(Paragraph("_________________________", self.styles['SignatureStyle']))
        story.append(Paragraph("Profa. FRANCIA MARCANO", self.styles['SignatureStyle']))
        story.append(Paragraph("DIRECTORA (E)", self.styles['SignatureStyle']))

        try:
            doc.build(story)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error al Generar Constancia", f"Ocurrió un error al generar la constancia: {e}")
            print(f"Error al generar la constancia: {e}")
            return False

    def _calculate_age(self, birth_date):
        if isinstance(birth_date, QDate):
            birth_date = birth_date.toPyDate()

        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age

    def _convert_year_to_text(self, year_number):
        year_mapping = {
            1: "Primer Año",
            2: "Segundo Año",
            3: "Tercer Año",
            4: "Cuarto Año",
            5: "Quinto Año"
        }
        return year_mapping.get(year_number, f"{year_number} Año" if year_number else "______")

# --- 3. Interfaz Gráfica (PyQt6) ---
class MainWindow(QWidget):
    # MODIFICACIÓN: Ahora recibe db_config y user_data
    def __init__(self, db_config, user_data):
        super().__init__()
        # Almacenar db_config y user_data
        self.db_config = db_config
        self.user_data = user_data
        
        # MODIFICACIÓN: Instanciar DatabaseManager con el diccionario db_config
        self.db_manager = DatabaseManager(self.db_config)
        
        # Inicializar CertificateGenerator aquí, pero sus rutas de imagen se establecerán dinámicamente
        self.cert_generator = CertificateGenerator()
        self.current_student_cedula = None
        self.init_ui()
        self.load_students_into_table()

    def init_ui(self):
        self.setWindowTitle("Generador de Constancia de Retiro")
        self.setGeometry(100, 100, 1000, 600)

        # --- Estilos CSS (QSS) para la paleta de colores ---
        # Definición de colores
        COLOR_BACKGROUND_LIGHT = "#e4eaf4"  # Gris muy claro/blanquecino
        COLOR_ACCENT_LIGHT = "#b3cbdc"       # Azul claro/grisáceo
        COLOR_ACCENT_MEDIUM = "#7089a7"      # Azul medio/grisáceo
        COLOR_PRIMARY_DARK = "#1c355b"       # Azul oscuro profundo

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_LIGHT};
                font-family: Arial;
                font-size: 10pt;
                color: {COLOR_PRIMARY_DARK}; /* Color de texto por defecto */
            }}
            QLabel {{
                color: {COLOR_PRIMARY_DARK};
                font-weight: bold;
                padding-top: 5px;
                padding-bottom: 2px;
            }}
            QLabel[textFormat="RichText"] {{ /* Para los <h2> */
                font-size: 14pt;
                color: {COLOR_PRIMARY_DARK};
                margin-bottom: 10px;
                padding: 10px;
                border-bottom: 2px solid {COLOR_ACCENT_MEDIUM};
            }}
            QLineEdit, QDateEdit {{
                background-color: white;
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                border-radius: 4px;
                padding: 5px;
                color: {COLOR_PRIMARY_DARK};
            }}
            QPushButton {{
                background-color: {COLOR_ACCENT_LIGHT};
                color: {COLOR_PRIMARY_DARK};
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_MEDIUM};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {COLOR_PRIMARY_DARK};
                color: white;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
                border: 1px solid #999999;
            }}
            QTableWidget {{
                background-color: white;
                border: 1px solid {COLOR_ACCENT_MEDIUM};
                border-radius: 5px;
                selection-background-color: {COLOR_ACCENT_LIGHT};
                selection-color: {COLOR_PRIMARY_DARK};
                gridline-color: #cccccc;
            }}
            QHeaderView::section {{
                background-color: {COLOR_PRIMARY_DARK};
                color: white;
                padding: 5px;
                border: 1px solid {COLOR_ACCENT_MEDIUM};
            }}
            QTableWidget::item {{
                padding: 3px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLOR_ACCENT_LIGHT}; /* Resalta la selección */
                color: {COLOR_PRIMARY_DARK};
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: {COLOR_ACCENT_MEDIUM};
                border-left-style: solid; /* just a single line */
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }}
            QDateEdit::down-arrow {{
                image: url(arrow_down.png); /* Asegúrate de tener una imagen de flecha si la usas */
            }}
        """)


        main_layout = QHBoxLayout()

        # --- Panel Izquierdo: Lista de Estudiantes ---
        left_panel_layout = QVBoxLayout()
        # Se añade un objectName para poder aplicar estilo específico a este QLabel si es necesario
        left_panel_layout.addWidget(QLabel("<h2>Lista de Estudiantes</h2>", objectName="titleLabel"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por Cédula o Nombre...")
        self.search_input.textChanged.connect(self.filter_students_table)
        left_panel_layout.addWidget(self.search_input)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(["Cédula", "Nombres", "Apellidos", "Estado Actual"])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.student_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.student_table.itemSelectionChanged.connect(self.display_selected_student_details)
        left_panel_layout.addWidget(self.student_table)

        main_layout.addLayout(left_panel_layout, 2)

        # --- Panel Derecho: Detalles del Estudiante y Generación ---
        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(QLabel("<h2>Detalles del Estudiante y Retiro</h2>", objectName="titleLabel"))

        # Formulario de detalles
        form_layout = QVBoxLayout()

        self.lbl_full_name = QLabel("Nombre Completo:")
        self.txt_full_name = QLineEdit()
        self.txt_full_name.setReadOnly(True)
        form_layout.addWidget(self.lbl_full_name)
        form_layout.addWidget(self.txt_full_name)

        self.lbl_cedula = QLabel("Cédula:")
        self.txt_cedula = QLineEdit()
        self.txt_cedula.setReadOnly(True)
        form_layout.addWidget(self.lbl_cedula)
        form_layout.addWidget(self.txt_cedula)

        self.lbl_birth_info = QLabel("Fecha y Lugar de Nacimiento:")
        self.txt_birth_info = QLineEdit()
        self.txt_birth_info.setReadOnly(True)
        form_layout.addWidget(self.lbl_birth_info)
        form_layout.addWidget(self.txt_birth_info)

        self.lbl_grade_section = QLabel("Grado y Sección Cursado:")
        self.txt_grade_section = QLineEdit()
        self.txt_grade_section.setReadOnly(True)
        form_layout.addWidget(self.lbl_grade_section)
        form_layout.addWidget(self.txt_grade_section)

        self.lbl_school_year = QLabel("Año Escolar de Retiro:")
        self.txt_school_year = QLineEdit()
        self.txt_school_year.setReadOnly(True)
        form_layout.addWidget(self.lbl_school_year)
        form_layout.addWidget(self.txt_school_year)

        self.lbl_withdrawal_reason = QLabel("Motivo de Retiro:")
        self.txt_withdrawal_reason = QLineEdit()
        self.txt_withdrawal_reason.setReadOnly(False)
        form_layout.addWidget(self.lbl_withdrawal_reason)
        form_layout.addWidget(self.txt_withdrawal_reason)

        self.lbl_representative = QLabel("Representante Solicitante:")
        self.txt_representative = QLineEdit()
        self.txt_representative.setReadOnly(True)
        form_layout.addWidget(self.lbl_representative)
        form_layout.addWidget(self.txt_representative)

        right_panel_layout.addLayout(form_layout)

        # Fecha de expedición de la constancia
        date_expedition_layout = QHBoxLayout()
        date_expedition_layout.addWidget(QLabel("Fecha de Expedición:"))
        self.date_expedition_edit = QDateEdit(QDate.currentDate())
        self.date_expedition_edit.setCalendarPopup(True)
        self.date_expedition_edit.setDisplayFormat("dd/MM/yyyy")
        date_expedition_layout.addWidget(self.date_expedition_edit)
        right_panel_layout.addLayout(date_expedition_layout)

        # --- Nuevos elementos para selección de imágenes ---
        image_selection_group_layout = QVBoxLayout()
        image_selection_group_layout.addWidget(QLabel("<b>Configuración de Imágenes del PDF:</b>"))

        # Selección de Logo Superior
        logo_arriba_layout = QHBoxLayout()
        logo_arriba_layout.addWidget(QLabel("Ruta Logo Superior:"))
        self.logo_arriba_path_input = QLineEdit("logo_arriba.jpg") # Ruta predeterminada
        logo_arriba_layout.addWidget(self.logo_arriba_path_input)
        btn_select_logo_arriba = QPushButton("Seleccionar Logo Superior...")
        btn_select_logo_arriba.clicked.connect(self.select_logo_arriba_path)
        logo_arriba_layout.addWidget(btn_select_logo_arriba)
        image_selection_group_layout.addLayout(logo_arriba_layout)

        # Selección de Logo Escudo
        logo_escudo_layout = QHBoxLayout()
        logo_escudo_layout.addWidget(QLabel("Ruta Logo Escudo:"))
        self.logo_escudo_path_input = QLineEdit("logo_escudo.png") # Ruta predeterminada
        logo_escudo_layout.addWidget(self.logo_escudo_path_input)
        btn_select_logo_escudo = QPushButton("Seleccionar Logo Escudo...")
        btn_select_logo_escudo.clicked.connect(self.select_logo_escudo_path)
        logo_escudo_layout.addWidget(btn_select_logo_escudo)
        image_selection_group_layout.addLayout(logo_escudo_layout)

        right_panel_layout.addLayout(image_selection_group_layout)
        # --- Fin de nuevos elementos para selección de imágenes ---

        # Botón de generar
        self.generate_button = QPushButton("Generar Constancia de Retiro")
        self.generate_button.clicked.connect(self.generate_certificate)
        self.generate_button.setEnabled(False)
        right_panel_layout.addWidget(self.generate_button)

        right_panel_layout.addStretch(1)
        main_layout.addLayout(right_panel_layout, 3)

        self.setLayout(main_layout)

    def select_logo_arriba_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Logo Superior")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_arriba_path_input.setText(selected_files[0])

    def select_logo_escudo_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Logo Escudo")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_escudo_path_input.setText(selected_files[0])

    def load_students_into_table(self):
        students_data = self.db_manager.get_all_students_summary()
        self.student_table.setRowCount(len(students_data))
        for row_idx, student in enumerate(students_data):
            cedula, nombres, apellidos, estado, ano_que_cursa, seccion = student
            self.student_table.setItem(row_idx, 0, QTableWidgetItem(str(cedula)))
            self.student_table.setItem(row_idx, 1, QTableWidgetItem(nombres))
            self.student_table.setItem(row_idx, 2, QTableWidgetItem(apellidos))
            estado_display = f"{estado} ({ano_que_cursa} {seccion})" if ano_que_cursa and seccion else estado
            self.student_table.setItem(row_idx, 3, QTableWidgetItem(estado_display if estado else "Desconocido"))
        self.original_students_data = students_data

    def filter_students_table(self):
        filter_text = self.search_input.text().lower()
        for row_idx in range(self.student_table.rowCount()):
            cedula_item = self.student_table.item(row_idx, 0)
            nombres_item = self.student_table.item(row_idx, 1)
            apellidos_item = self.student_table.item(row_idx, 2)

            match_cedula = filter_text in cedula_item.text().lower() if cedula_item else False
            match_nombres = filter_text in nombres_item.text().lower() if nombres_item else False
            match_apellidos = filter_text in apellidos_item.text().lower() if apellidos_item else False

            self.student_table.setRowHidden(row_idx, not (match_cedula or match_nombres or match_apellidos))

    def clear_student_details(self):
        """Limpia todos los campos de detalles del estudiante en la interfaz."""
        self.txt_full_name.clear()
        self.txt_cedula.clear()
        self.txt_birth_info.clear()
        self.txt_grade_section.clear()
        self.txt_school_year.clear()
        self.txt_withdrawal_reason.clear()
        self.txt_representative.clear()

    def display_selected_student_details(self):
        selected_items = self.student_table.selectedItems()
        if not selected_items:
            self.clear_student_details()
            self.generate_button.setEnabled(False)
            self.current_student_cedula = None
            return

        row = selected_items[0].row()
        cedula_item = self.student_table.item(row, 0)
        if cedula_item:
            cedula = cedula_item.text()
            self.current_student_cedula = cedula
            student_data = self.db_manager.get_student_data_for_withdrawal(cedula)
            if student_data:
                self.populate_student_details(student_data)
                self.generate_button.setEnabled(True)
            else:
                self.clear_student_details()
                self.generate_button.setEnabled(False)
        else:
            self.clear_student_details()
            self.generate_button.setEnabled(False)
            self.current_student_cedula = None

    def populate_student_details(self, data):
        self.txt_full_name.setText(f"{data[0]} {data[1]}")
        self.txt_cedula.setText(str(data[2]))

        fecha_nac = data[3].strftime("%d/%m/%Y") if data[3] else "Desconocida"
        edad = self.cert_generator._calculate_age(data[3]) if data[3] else "Desconocida"
        self.txt_birth_info.setText(f"Fecha: {fecha_nac}, Lugar: {data[4] if data[4] else 'Desconocido'}, Edad: {edad}")

        grado_seccion = f"{data[7] if data[7] else 'Grado Desconocido'} de {data[8] if data[8] else 'Sección Desconocida'}"
        self.txt_grade_section.setText(grado_seccion)

        ano_escolar = f"{data[9] if data[9] else 'XXXX'}-{data[10] if data[10] else 'YYYY'}"
        self.txt_school_year.setText(ano_escolar)

        self.txt_withdrawal_reason.setText(data[5] if data[5] else "")

        representante = f"{data[11] if data[11] else 'N/A'} {data[12] if data[12] else ''}"
        self.txt_representative.setText(representante.strip())

    def generate_certificate(self):
        if not self.current_student_cedula:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un estudiante de la lista.")
            return

        student_raw_data = self.db_manager.get_student_data_for_withdrawal(self.current_student_cedula)

        if not student_raw_data:
            QMessageBox.critical(self, "Error de Datos", "No se pudieron cargar los datos completos del estudiante.")
            return

        user_entered_withdrawal_reason = self.txt_withdrawal_reason.text()
        if not user_entered_withdrawal_reason.strip():
            QMessageBox.warning(self, "Motivo de Retiro Requerido", "Por favor, ingresa el motivo de retiro.")
            return

        data_to_pass = {
            'nombres_estudiante': student_raw_data[0],
            'apellidos_estudiante': student_raw_data[1],
            'cedula_estudiante': student_raw_data[2],
            'fecha_nacimiento': student_raw_data[3],
            'lugar_nacimiento': student_raw_data[4],
            'motivo_retiro': user_entered_withdrawal_reason,
            'fecha_retiro': student_raw_data[6],
            'ano_que_cursa': student_raw_data[7],
            'nombre_seccion': student_raw_data[8],
            'ano_inicio_escolar': student_raw_data[9],
            'ano_fin_escolar': student_raw_data[10],
            'nombres_representante': student_raw_data[11],
            'apellidos_representante': student_raw_data[12],
            'dia_expedicion': self.date_expedition_edit.date().day(),
            'mes_expedicion': self.date_expedition_edit.date().month(),
            'ano_expedicion': self.date_expedition_edit.date().year()
        }

        output_filename = f"Constancia_Retiro_{data_to_pass['cedula_estudiante']}_{QDate.currentDate().toString('yyyyMMdd_hhmmss')}.pdf"

        # Actualizar las rutas de las imágenes en la instancia de CertificateGenerator
        self.cert_generator.logo_arriba_path = self.logo_arriba_path_input.text()
        self.cert_generator.logo_escudo_path = self.logo_escudo_path_input.text()

        if self.cert_generator.generate_withdrawal_certificate(data_to_pass, output_filename):
            QMessageBox.information(self, "Éxito", f"Constancia generada exitosamente en:\n{os.path.abspath(output_filename)}")
            try:
                os.startfile(os.path.abspath(output_filename))
            except AttributeError:
                try:
                    import subprocess
                    subprocess.call(['xdg-open', os.path.abspath(output_filename)])
                except Exception as e:
                    print(f"No se pudo abrir automáticamente el archivo {output_filename}. Error: {e}")
            except Exception as e:
                print(f"Error al intentar abrir el archivo: {e}")
        else:
            QMessageBox.critical(self, "Error", "No se pudo generar la constancia.")

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos cuando la aplicación se cierra."""
        self.db_manager.close()
        event.accept()

# --- Bloque principal para ejecutar la aplicación ---
if __name__ == '__main__':
    # Define la configuración de la base de datos una única vez
    db_config_global = {
        "database": "bd",
        "user": "postgres",
        "password": "12345678",
        "host": "localhost",
        "port": "5432"
    }

    # Define los datos del usuario. Para esta aplicación, puede ser un diccionario vacío
    # o contener información del usuario logueado si tu aplicación principal lo maneja.
    user_data_global = {
        'id': 123,
        'username': 'admin_retiros',
        'role': 'administrador'
    }

    app = QApplication(sys.argv)
    
    # Pasa db_config y user_data a la ventana principal
    main_window = MainWindow(db_config=db_config_global, user_data=user_data_global)
    main_window.show()
    sys.exit(app.exec())