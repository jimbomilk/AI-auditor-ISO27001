import os
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from services.document_processor import extract_text_from_document
from services.ai_analyzer import analyze_document_coverage, answer_question_with_rag, generate_policy_draft
from services.vector_store_manager import create_vector_store
# --- Diagnóstico de Versión ---
# El método anterior (`__version__`) falló. Usamos una forma más robusta para obtener la versión del paquete.
try:
    from importlib.metadata import version
    pkg_version = version('langchain-google-genai')
    print(f"--- Usando langchain-google-genai versión: {pkg_version} ---")
except Exception as e:
    print(f"--- No se pudo determinar la versión de langchain-google-genai: {e} ---")
# -----------------------------

# Cargar variables de entorno desde .env
load_dotenv()

# --- Configuración ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Inicializar la aplicación Flask
app = Flask(__name__)
# Es una buena práctica tener una clave secreta por defecto para desarrollo
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_default_secret_key_for_testing')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear el directorio de subidas si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Verificación de la clave de API (aunque no la usemos todavía)
# Esto nos ayudará a depurar problemas de configuración más adelante.
if not os.getenv('API_KEY_GEMINI') or os.getenv('API_KEY_GEMINI') == "YOUR_GEMINI_API_KEY":
    print("ADVERTENCIA: La variable de entorno API_KEY_GEMINI no está configurada en el fichero .env")
    print("Por favor, obtén una clave y añádela para poder usar las funciones de IA.")

def allowed_file(filename):
    """Verifica si el fichero tiene una extensión permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    """Ruta principal para mostrar y procesar la carga de archivos."""
    if request.method == 'POST':
        # Verificar si la petición POST tiene la parte del fichero
        if 'file' not in request.files:
            flash('No se encontró la parte del fichero en la petición', 'error')
            return redirect(request.url)
        file = request.files['file']
        # Si el usuario no selecciona un fichero, el navegador
        # envía una parte vacía sin nombre de fichero.
        if file.filename == '':
            flash('Ningún fichero seleccionado', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Redirigir a la página de análisis para este fichero
            return redirect(url_for('analysis_page', filename=filename))
        else:
            flash('Tipo de fichero no permitido. Sube solo PDF o DOCX.', 'error')
            return redirect(request.url)
    return render_template('index.html', title='Inicio')

@app.route('/analysis/<filename>')
def analysis_page(filename):
    """Muestra el texto extraído del documento y prepara para el análisis."""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash(f'Error: El fichero {filename} no fue encontrado.', 'error')
        return redirect(url_for('index'))

    # Extraer el texto del documento usando nuestro nuevo servicio
    extracted_text = extract_text_from_document(file_path)

    if not extracted_text:
        flash(f'No se pudo extraer texto del fichero {filename}. Puede que esté vacío, protegido o corrupto.', 'warning')
    
    # Usamos el nombre del fichero (sin extensión) como nombre de la colección
    collection_name, _ = os.path.splitext(filename)

    # Crear o actualizar la base de datos vectorial para este documento
    if extracted_text:
        try:
            create_vector_store(extracted_text, collection_name)
            flash(f'Documento "{filename}" procesado y listo para chatear.', 'success')
        except Exception as e:
            flash(f'Error al crear la base de datos vectorial: {e}', 'error')

    # Realizar el análisis de cobertura con la IA
    analysis_results = []
    if extracted_text:
        analysis_results = analyze_document_coverage(extracted_text)
        if analysis_results and "error" in analysis_results[0]:
             flash(f'Error en el análisis de IA: {analysis_results[0]["error"]}', 'error')
             analysis_results = [] # Limpiar resultados para no mostrar error en la tabla

    return render_template('analysis.html', title=f'Análisis de {filename}', filename=filename, extracted_text=extracted_text, analysis_results=analysis_results, collection_name=collection_name)

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint para el chat interactivo."""
    data = request.get_json()
    question = data.get('question')
    collection_name = data.get('collection_name')

    if not question or not collection_name:
        return jsonify({'error': 'Falta la pregunta o el nombre de la colección.'}), 400

    answer = answer_question_with_rag(question, collection_name)
    return jsonify({'answer': answer})

@app.route('/generate_draft', methods=['POST'])
def generate_draft():
    """Endpoint para generar un borrador de política."""
    data = request.get_json()
    control_id = data.get('control_id')
    control_description = data.get('control_description')

    if not control_id or not control_description:
        return jsonify({'error': 'Faltan datos del control.'}), 400

    draft = generate_policy_draft(control_id, control_description)
    return jsonify({'draft': draft})

# Esto permite ejecutar la aplicación directamente con `python app.py`
# lo cual es útil para depurar. `debug=True` activa el recargado automático
# y muestra páginas de error más detalladas.
if __name__ == '__main__':
    app.run(debug=True)