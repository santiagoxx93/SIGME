# Sistema Integrado de Gestión Modular Educativo (SIGME)

🌐 **Sitio Web Oficial:** [sigme.site](https://sigme.site/)

SIGME es una aplicación de escritorio diseñada para gestionar de manera eficiente los procesos administrativos y académicos de una institución educativa. 

## 🚀 Características Principales

*   **Gestión de Estudiantes y Personal:** Registro, actualización y control de alumnos, docentes y personal administrativo.
*   **Gestión Académica:** Asignación de docentes, materias, secciones y control de notas (evaluaciones).
*   **Matrícula:** Sistema completo para inscripción y matriculación.
*   **Generador de Constancias:** Creación automática de documentos en PDF (Constancias de Estudio, Retiro, Asistencia, etc.).
*   **Interfaz Gráfica:** Diseñada para ser intuitiva y fácil de usar, permitiendo un trabajo fluido.

## 🛠️ Tecnologías Usadas

*   **Lenguaje:** Python 3.x
*   **Interfaz de Usuario (GUI):** PyQt6
*   **Base de Datos:** PostgreSQL (mediante `psycopg2`)
*   **Generación de PDFs:** ReportLab
*   **Manejo de Imágenes:** Pillow (PIL)

## 📋 Requisitos e Instalación

1. Clona este repositorio en tu computadora:
   ```bash
   git clone https://github.com/santiagoxx93/SIGME.git
   cd SIGME
   ```

2. (Opcional pero recomendado) Crea un entorno virtual:
   ```bash
   python -m venv venv
   # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias del proyecto:
   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta la aplicación:
   ```bash
   python main.py
   ```

*Nota: La aplicación requiere una conexión funcional a una base de datos PostgreSQL, parametrizada a través del archivo de configuración pertinente.*
