import sys
import psycopg2
from psycopg2 import Error
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QComboBox, QFileDialog, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle # Añadido TableStyle aquí
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
import os # Asegúrate de que os esté importado

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
            print(f"Conexión a la base de datos '{self.db_config.get('database')}' exitosa para Constancia de Asistencia.")
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
    def __init__(self, filename="constancia_de_asistencia.pdf", logo_carmen_ruiz_path=None, logo_miranda_path=None):
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()
        self.meses_espanol = {
            1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
            5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
            9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
        }
        # Rutas de las imágenes, ahora se toman de los parámetros
        self.logo_carmen_ruiz_path = logo_carmen_ruiz_path
        self.logo_miranda_path = logo_miranda_path


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


    def generate_constancia_asistencia(self, selected_citation_data, motivo_para_constancia, fecha_constancia):
        doc = SimpleDocTemplate(self.filename, pagesize=letter,
                                 leftMargin=inch, rightMargin=inch,
                                 topMargin=inch, bottomMargin=inch)
        Story = []

        # Desempaquetar los datos de la citación
        citation_id, fecha_citacion_db, motivo_db, asistio, \
        rep_nombres, rep_apellidos, rep_cedula, \
        est_nombres, est_apellidos, est_cedula, \
        grado_nombre, seccion_letra = selected_citation_data

        dia = fecha_constancia.day
        año = fecha_constancia.year
        mes_espanol = self.meses_espanol.get(fecha_constancia.month, fecha_constancia.strftime('%B').lower())

        # --- SECCIÓN DE CABECERA CON IMÁGENES Y TEXTO ---
        header_text_style = self.styles['TituloInstitucional']
        header_text_elements = [
            Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", header_text_style),
            Paragraph("GOBERNACIÓN DEL ESTADO BOLIVARIANO DE MIRANDA", header_text_style),
            Paragraph("UNIDAD EDUCATIVA ESTADAL", header_text_style),
            Paragraph("<br/>", header_text_style), # Espacio adicional
            Paragraph("<font size='20'><b>\" CARMEN RUIZ \"</b></font>", header_text_style),
            Paragraph("<br/>", header_text_style), # Espacio adicional
            Paragraph("CÓDIGO PLANTEL: OD00221508", header_text_style),
            Paragraph("CHARALLAVE – CRISTÓBAL ROJAS", header_text_style),
            Paragraph("TELÉFONO: 0239.2487847", header_text_style),
        ]

        img_carmen_ruiz = Spacer(1,1) # Placeholder si la imagen no existe
        if self.logo_carmen_ruiz_path and os.path.exists(self.logo_carmen_ruiz_path):
            img_carmen_ruiz = Image(self.logo_carmen_ruiz_path, width=2.17 * cm, height=2.28 * cm)
            img_carmen_ruiz.hAlign = 'LEFT'
        else:
            QMessageBox.warning(None, "Advertencia", f"No se encontró la imagen del logo Carmen Ruiz en: {self.logo_carmen_ruiz_path}. Se usará un espacio en blanco.")


        img_miranda = Spacer(1,1) # Placeholder si la imagen no existe
        if self.logo_miranda_path and os.path.exists(self.logo_miranda_path):
            img_miranda = Image(self.logo_miranda_path, width=2.17 * cm, height=2.28 * cm)
            img_miranda.hAlign = 'RIGHT'
        else:
            QMessageBox.warning(None, "Advertencia", f"No se encontró la imagen del logo Miranda en: {self.logo_miranda_path}. Se usará un espacio en blanco.")

        header_table_data = [
            [img_carmen_ruiz, header_text_elements, img_miranda]
        ]

        col_widths = [1.8 * inch, 3.9 * inch, 1.8 * inch]
        header_table = Table(header_table_data, colWidths=col_widths)

        header_table.setStyle(TableStyle([ # Ahora se instancia TableStyle explícitamente
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        Story.append(header_table)
        Story.append(Spacer(1, 0.3 * inch))

        # Usar la fecha de la constancia para la fecha de emisión del documento
        Story.append(Paragraph(f"Charallave, {dia} de {mes_espanol} de {año}", self.styles['Right']))
        Story.append(Spacer(1, 0.4 * inch))

        Story.append(Paragraph("<b><u>CONSTANCIA DE ASISTENCIA</u></b>", self.styles['Center']))
        Story.append(Spacer(1, 0.4 * inch))

        content_paragraph = f"""
        Quien suscribe, Directivo de la Unidad Educativa Estadal "Carmen Ruiz",
        hace constar por medio de la presente que el(la) ciudadano(a) :
        <b>{rep_nombres} {rep_apellidos}</b>, portador (a) de la cédula de identidad N°:
        <b>{rep_cedula}</b>, Representante legal del estudiante:
        <b>{est_nombres} {est_apellidos}</b>, cédula identidad N°: <b>{est_cedula}</b>
        cursante del <b>{grado_nombre} "{seccion_letra}"</b>, asistió el día de hoy:
        <b>{fecha_constancia.strftime('%d/%m/%Y')}</b> para tratar asunto: <b>{motivo_para_constancia}</b>.
        """
        Story.append(Paragraph(content_paragraph, self.styles['Justificado'])) # Usar estilo Justificado
        Story.append(Spacer(1, 0.2 * inch))

        Story.append(Paragraph("Sin más a que hacer referencia, queda de Usted.", self.styles['Justificado'])) # Usar estilo Justificado
        Story.append(Paragraph("Atentamente,", self.styles['AtentamenteCentrado']))
        Story.append(Spacer(1, 0.2 * inch))

        Story.append(Paragraph("___________________________", self.styles['LineaCortaCentrada']))
        Story.append(Paragraph("Directora (e)", self.styles['CargoFirma']))

        Story.append(Spacer(1, 0.5 * inch))

        try:
            doc.build(Story)
            QMessageBox.information(None, "Éxito", f"Constancia de asistencia generada como '{self.filename}'")
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
class ConstanciaAsistenciaApp(QWidget):
    # El constructor ahora acepta db_config y user_data
    def __init__(self, db_config, user_data):
        super().__init__()
        self.db_config = db_config # Almacenar la configuración de la base de datos
        self.user_data = user_data # Almacenar los datos del usuario (si se necesitan más adelante)
        self.db_conn = None
        # Inicializar PDFGenerator con rutas iniciales vacías o predeterminadas
        self.pdf_gen = PDFGenerator(logo_carmen_ruiz_path="", logo_miranda_path="") 
        self.init_ui()
        self.apply_styles() # Aplicar estilos
        self.connect_db() # Conectar a la base de datos

    def init_ui(self):
        """Inicializa la interfaz de usuario de la aplicación."""
        self.setWindowTitle('Generador de Constancias de Asistencia')
        self.setGeometry(100, 100, 800, 700)

        main_layout = QVBoxLayout()

        # Sección de búsqueda
        search_layout = QHBoxLayout()
        self.search_label = QLabel('Buscar por Cédula de Estudiante o Representante:')
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Ingrese cédula (ej. 12345678 o V-12345678)...')
        self.search_button = QPushButton('Buscar Citación')
        self.search_button.clicked.connect(self.search_citation)

        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # Sección de selección de citación (para cuando hay múltiples resultados)
        self.citation_selection_label = QLabel('Seleccione la citación:')
        self.citation_combo_box = QComboBox()
        self.citation_combo_box.currentIndexChanged.connect(self.display_selected_citation_details)
        main_layout.addWidget(self.citation_selection_label)
        main_layout.addWidget(self.citation_combo_box)
        self.citation_selection_label.hide()
        self.citation_combo_box.hide()

        # Sección de detalles de la citación seleccionada
        details_layout = QVBoxLayout()
        self.details_label = QLabel('Detalles de la Citación Seleccionada:')
        self.details_text_edit = QTextEdit()
        self.details_text_edit.setReadOnly(True)
        details_layout.addWidget(self.details_label)
        details_layout.addWidget(self.details_text_edit)
        main_layout.addLayout(details_layout)

        # Campo: Motivo/Asunto para la Constancia (Editable y ahora siempre vacío por defecto)
        motivo_layout = QHBoxLayout()
        self.motivo_label = QLabel('Motivo/Asunto de la Constancia:')
        self.motivo_input = QLineEdit()
        self.motivo_input.setPlaceholderText('Ingrese el motivo o asunto para la constancia...')
        motivo_layout.addWidget(self.motivo_label)
        motivo_layout.addWidget(self.motivo_input)
        main_layout.addLayout(motivo_layout)
        self.motivo_label.hide()
        self.motivo_input.hide()

        # Selector de fecha para la constancia (Esta fecha se usará para toda la constancia)
        date_selection_layout = QHBoxLayout()
        self.date_label = QLabel('Fecha de la Constancia:')
        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDate(QDate.currentDate()) # Establece la fecha actual por defecto
        date_selection_layout.addWidget(self.date_label)
        date_selection_layout.addWidget(self.date_edit)
        main_layout.addLayout(date_selection_layout)
        self.date_label.hide()
        self.date_edit.hide()

        # --- Nuevos elementos para selección de imágenes ---
        image_selection_group_layout = QVBoxLayout()
        image_selection_group_layout.addWidget(QLabel("<b>Configuración de Imágenes del PDF:</b>"))

        # Selección de Logo Carmen Ruiz
        carmen_ruiz_logo_layout = QHBoxLayout()
        carmen_ruiz_logo_layout.addWidget(QLabel("Ruta Logo Carmen Ruiz:"))
        self.logo_carmen_ruiz_path_input = QLineEdit(r"C:\Users\Windows 10 Pro\Desktop\modulo constancia defini\logo_carmen_ruiz.jpg") # Ruta predeterminada
        carmen_ruiz_logo_layout.addWidget(self.logo_carmen_ruiz_path_input)
        btn_select_carmen_ruiz_logo = QPushButton("Seleccionar Logo...")
        btn_select_carmen_ruiz_logo.clicked.connect(self.select_carmen_ruiz_logo_path)
        carmen_ruiz_logo_layout.addWidget(btn_select_carmen_ruiz_logo)
        image_selection_group_layout.addLayout(carmen_ruiz_logo_layout)

        # Selección de Logo Miranda
        miranda_logo_layout = QHBoxLayout()
        miranda_logo_layout.addWidget(QLabel("Ruta Logo Miranda:"))
        self.logo_miranda_path_input = QLineEdit(r"C:\Users\Windows 10 Pro\Desktop\modulo constancia defini\logo_miranda.jpg") # Ruta predeterminada
        miranda_logo_layout.addWidget(self.logo_miranda_path_input)
        btn_select_miranda_logo = QPushButton("Seleccionar Logo...")
        btn_select_miranda_logo.clicked.connect(self.select_miranda_logo_path)
        miranda_logo_layout.addWidget(btn_select_miranda_logo)
        image_selection_group_layout.addLayout(miranda_logo_layout)

        main_layout.addLayout(image_selection_group_layout)
        # --- Fin de nuevos elementos para selección de imágenes ---

        # Botón para generar la constancia (y PDF)
        self.generate_button = QPushButton('Generar Constancia (y PDF)')
        self.generate_button.clicked.connect(self.generate_constancia)
        self.generate_button.setEnabled(False)
        main_layout.addWidget(self.generate_button)

        # Área de visualización de la constancia generada
        self.constancia_label = QLabel('Constancia Generada (Vista Previa):')
        self.constancia_text_edit = QTextEdit()
        self.constancia_text_edit.setReadOnly(True)
        main_layout.addWidget(self.constancia_label)
        main_layout.addWidget(self.constancia_text_edit)

        self.setLayout(main_layout)

    def apply_styles(self):
        """Aplica los estilos a la aplicación utilizando QSS."""
        self.setStyleSheet("""
            QWidget {
                background-color: #e4eaf4; /* Azul muy claro */
                color: #1c355b; /* Azul oscuro para el texto principal */
                font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 14px;
            }

            QLabel {
                color: #1c355b; /* Azul oscuro para etiquetas */
                font-weight: bold;
                padding: 5px 0;
            }

            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                background-color: #FFFFFF; /* Fondo blanco para campos de entrada */
                border: 1px solid #b3cbdc; /* Azul claro medio para el borde */
                border-radius: 4px;
                padding: 8px;
                color: #1c355b;
                selection-background-color: #b3cbdc; /* Azul claro medio para selección */
            }

            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #1c355b; /* Azul oscuro para el foco */
                background-color: #F9FCFF; /* Fondo ligeramente azulado al enfocar */
            }

            QPushButton {
                background-color: #1c355b; /* Azul oscuro vibrante para botones */
                color: #FFFFFF; /* Texto blanco en botones */
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 15px;
                min-height: 30px; /* Altura mínima para botones */
            }

            QPushButton:hover {
                background-color: #7089a7; /* Gris azulado al pasar el ratón */
            }

            QPushButton:pressed {
                background-color: #1c355b; /* Azul oscuro aún más oscuro al presionar */
            }

            QPushButton:disabled {
                background-color: #b3cbdc; /* Azul claro medio para botones deshabilitados */
                color: #FFFFFF; /* Texto blanco */
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #b3cbdc;
                border-left-style: solid; /* just a single line */
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }

            QComboBox::down-arrow {
                /* Eliminada la ruta absoluta. Usará la flecha predeterminada de Qt */
                /* image: url(C:/Users/Windows 10 Pro/Desktop/modulo constancia defini/arrow_down.png); */
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #b3cbdc;
                selection-background-color: #b3cbdc;
                selection-color: #1c355b;
                background-color: #FFFFFF;
            }
            
            QDateEdit::up-arrow, QDateEdit::down-arrow {
                width: 12px;
                height: 12px;
            }
            QDateEdit::up-button, QDateEdit::down-button {
                background-color: #b3cbdc;
                border-left: 1px solid #7089a7;
                width: 20px;
            }
            QDateEdit::up-button:hover, QDateEdit::down-button:hover {
                background-color: #7089a7;
            }
        """)

    def connect_db(self):
        """Establece la conexión a la base de datos PostgreSQL utilizando self.db_config."""
        try:
            self.db_conn = psycopg2.connect(
                host=self.db_config.get('host'),
                database=self.db_config.get('database'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password'),
                port=self.db_config.get('port')
            )
            print(f"Conexión a la base de datos '{self.db_config.get('database')}' establecida con éxito para ConstanciaAsistenciaApp.")
        except psycopg2.Error as e:
            QMessageBox.critical(self, 'Error de Conexión', f'No se pudo conectar a la base de datos para Constancia de Asistencia: {e}')
            self.db_conn = None

    def select_carmen_ruiz_logo_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Logo Carmen Ruiz")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_carmen_ruiz_path_input.setText(selected_files[0])

    def select_miranda_logo_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen (*.png *.jpg *.jpeg *.gif *.bmp)")
        file_dialog.setWindowTitle("Seleccionar Logo Miranda")
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.logo_miranda_path_input.setText(selected_files[0])

    def search_citation(self):
        """Busca citaciones en la base de datos según la cédula ingresada."""
        if not self.db_conn:
            QMessageBox.warning(self, 'Error', 'No hay conexión a la base de datos.')
            return

        search_cedula_raw = self.search_input.text().strip()
        if not search_cedula_raw:
            QMessageBox.warning(self, 'Advertencia', 'Por favor, ingrese una cédula para buscar.')
            return

        # Normalizar la entrada: eliminar "V-" si está presente, y crear una versión con "V-"
        search_cedula_plain = search_cedula_raw.lstrip('Vv-')
        search_cedula_with_prefix = f"V-{search_cedula_plain}"

        try:
            cursor = self.db_conn.cursor()
            query = """
            SELECT
                c.id,
                c.fecha_citacion,
                c.motivo,
                c.asistio,
                r.nombres AS rep_nombres,
                r.apellidos AS rep_apellidos,
                r.cedula AS rep_cedula,
                e.nombres AS est_nombres,
                e.apellidos AS est_apellidos,
                e.cedula AS est_cedula,
                g.nombre AS grado_nombre,
                s.letra AS seccion_letra
            FROM
                citacion c
            JOIN
                representante r ON c.cedula_representante = r.cedula
            JOIN
                estudiante e ON c.cedula = e.cedula
            JOIN
                matricula m ON e.cedula = m.cedula_estudiante AND r.cedula = m.cedula_representante
            JOIN
                seccion s ON m.codigo_seccion = s.codigo
            JOIN
                grado g ON s.codigo_grado = g.codigo
            WHERE
                r.cedula = %s OR r.cedula = %s OR e.cedula = %s OR e.cedula = %s
            ORDER BY
                c.fecha_citacion DESC;
            """
            cursor.execute(query, (search_cedula_plain, search_cedula_with_prefix,
                                   search_cedula_plain, search_cedula_with_prefix))
            self.citations = cursor.fetchall()

            self.citation_combo_box.clear()
            if self.citations:
                self.citation_selection_label.show()
                self.citation_combo_box.show()
                self.motivo_label.show()
                self.motivo_input.show()
                self.date_label.show()
                self.date_edit.show()
                for i, citation in enumerate(self.citations):
                    display_text = (
                        f"{citation[1].strftime('%Y-%m-%d')} - "
                        f"Est: {citation[7]} {citation[8]} (CI: {citation[9]}) - "
                        f"Rep: {citation[4]} {citation[5]} (CI: {citation[6]}) - "
                        f"Motivo: {citation[2]}"
                    )
                    self.citation_combo_box.addItem(display_text, citation)
                self.generate_button.setEnabled(True)
                self.display_selected_citation_details()
            else:
                self.citation_selection_label.hide()
                self.citation_combo_box.hide()
                self.motivo_label.hide()
                self.motivo_input.hide()
                self.date_label.hide()
                self.date_edit.hide()
                self.details_text_edit.clear()
                self.constancia_text_edit.clear()
                self.generate_button.setEnabled(False)
                QMessageBox.information(self, 'Búsqueda', 'No se encontraron citaciones para la cédula ingresada.')

        except psycopg2.Error as e:
            QMessageBox.critical(self, 'Error de Consulta', f'Error al buscar citaciones: {e}')
        finally:
            if cursor:
                cursor.close()

    def display_selected_citation_details(self):
        """Muestra los detalles de la citación seleccionada en el QTextEdit y deja el campo de motivo vacío para escribir."""
        selected_citation_data = self.citation_combo_box.currentData()
        if selected_citation_data:
            citation_id, fecha_citacion_db, motivo_db, asistio, \
            rep_nombres, rep_apellidos, rep_cedula, \
            est_nombres, est_apellidos, est_cedula, \
            grado_nombre, seccion_letra = selected_citation_data

            details_text = (
                f"ID Citación: {citation_id}\n"
                f"Fecha de Citación (BD): {fecha_citacion_db.strftime('%d/%m/%Y')}\n" # Aclara que es de la BD
                f"Motivo (BD): {motivo_db if motivo_db is not None else 'N/A'}\n"
                f"Asistió: {'Sí' if asistio else 'No'}\n\n"
                f"--- Datos del Representante ---\n"
                f"Nombre: {rep_nombres} {rep_apellidos}\n"
                f"Cédula: {rep_cedula}\n\n"
                f"--- Datos del Estudiante ---\n"
                f"Nombre: {est_nombres} {est_apellidos}\n"
                f"Cédula: {est_cedula}\n"
                f"Grado y Sección: {grado_nombre} \"{seccion_letra}\"\n"
            )
            self.details_text_edit.setText(details_text)
            self.motivo_input.clear()
        else:
            self.details_text_edit.clear()
            self.motivo_input.clear()
            self.date_edit.setDate(QDate.currentDate()) # Siempre que no haya selección, se pone la actual

    def generate_constancia(self):
        """
        Genera el texto de la constancia de asistencia en la interfaz
        y también crea un archivo PDF de la constancia.
        La fecha de asistencia se tomará del QDateEdit.
        """
        selected_citation_data = self.citation_combo_box.currentData()
        if not selected_citation_data:
            QMessageBox.warning(self, 'Advertencia', 'Por favor, seleccione una citación primero.')
            return

        motivo_para_constancia = self.motivo_input.text().strip()
        if not motivo_para_constancia:
            QMessageBox.warning(self, 'Advertencia', 'Por favor, ingrese el motivo o asunto para la constancia.')
            return

        # Obtener la fecha seleccionada del QDateEdit para la constancia
        selected_date_qdate = self.date_edit.date()
        fecha_constancia = selected_date_qdate.toPyDate() # Objeto datetime.date

        # Actualizar las rutas de las imágenes en la instancia de PDFGenerator
        self.pdf_gen.logo_carmen_ruiz_path = self.logo_carmen_ruiz_path_input.text()
        self.pdf_gen.logo_miranda_path = self.logo_miranda_path_input.text()

        # Generación del PDF con ReportLab
        file_name, _ = QFileDialog.getSaveFileName(self, "Guardar Constancia PDF",
                                                     f"Constancia_Asistencia_{selected_citation_data[6]}_{fecha_constancia.strftime('%Y%m%d')}.pdf",
                                                     "Archivos PDF (*.pdf)")
        if file_name:
            try:
                self.pdf_gen.generate_constancia_asistencia(selected_citation_data, motivo_para_constancia, fecha_constancia)
                QMessageBox.information(self, 'PDF Generado', f'Constancia PDF guardada en: {file_name}')
            except Exception as e:
                QMessageBox.critical(self, 'Error al Generar PDF', f'Ocurrió un error al crear el PDF: {e}')
        else:
            QMessageBox.information(self, 'Guardar PDF', 'La generación del PDF fue cancelada.')

        # --- Generación del texto para la interfaz (se mantiene para vista previa) ---
        # Los datos de la citación de la BD, pero la fecha_citacion_db NO se usará para "asistió el día de hoy"
        citation_id, fecha_citacion_db, motivo_db, asistio, \
        rep_nombres, rep_apellidos, rep_cedula, \
        est_nombres, est_apellidos, est_cedula, \
        grado_nombre, seccion_letra = selected_citation_data

        dia = fecha_constancia.day
        año = fecha_constancia.year

        # Mapeo de meses de inglés a español
        meses_espanol = {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
        mes_ingles = fecha_constancia.strftime('%B')
        mes_espanol = meses_espanol.get(mes_ingles, mes_ingles)

        constancia_text = f"""
REPÚBLICA BOLIVARIANA DE VENEZUELA
GOBERNACIÓN DEL ESTADO BOLIVARIANO DE MIRANDA
UNIDAD EDUCATIVA ESTADAL
" CARMEN RUIZ "
CÓDIGO PLANTEL: OD00221508
Charallave, {dia} de {mes_espanol} de {año}

CONSTANCIA DE ASISTENCIA

    Quien suscribe, Directivo de la Unidad Educativa Estadal "Carmen Ruiz", hace constar por medio de la presente que el(la) ciudadano(a) : {rep_nombres} {rep_apellidos}, portador (a) de la cédula de identidad N°: {rep_cedula}, Representante legal del estudiante: {est_nombres} {est_apellidos}, cédula identidad N°: {est_cedula} cursante del {grado_nombre} "{seccion_letra}", asistió el día de hoy: {fecha_constancia.strftime('%d/%m/%Y')} para tratar asunto: {motivo_para_constancia}

    Sin más a que hacer referencia, queda de Usted.
Atentamente,

___________________________
Directora (e)
"""
        self.constancia_text_edit.setText(constancia_text)


    def closeEvent(self, event):
        """Cierra la conexión a la base de datos cuando la aplicación se cierra."""
        if self.db_conn:
            self.db_conn.close()
            print("Conexión a la base de datos cerrada.")
        event.accept()

if __name__ == '__main__':
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
        'username': 'testuser_asistencia',
        'role': 'secretaria'
    }

    ex = ConstanciaAsistenciaApp(db_config=test_db_config, user_data=test_user_data)
    ex.show()
    sys.exit(app.exec())
