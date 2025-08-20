import os
import sys
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from services.document_processor import extract_text_from_document
from services.ai_analyzer import analyze_document_coverage, answer_question_with_rag, generate_policy_draft, identify_risks_for_control, get_iso_controls_from_db
from services.vector_store_manager import create_vector_store
# --- Importar Vertex AI para inicialización ---
import vertexai
import google.auth

# Cargar variables de entorno desde .env
load_dotenv()

# --- Verificación y Configuración de Google Cloud ---
google_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
location = os.getenv('GOOGLE_CLOUD_LOCATION') # La ubicación debe estar definida explícitamente en .env

# Verificación de credenciales
if not google_creds_path or not os.path.exists(google_creds_path):
    print("="*80)
    print("ERROR FATAL: No se encuentra el fichero de credenciales de Google Cloud.")
    print(f"La variable de entorno GOOGLE_APPLICATION_CREDENTIALS apunta a: {google_creds_path}")
    print("Por favor, asegúrate de que la ruta en tu fichero .env es correcta y absoluta.")
    print("Ejemplo para Windows: GOOGLE_APPLICATION_CREDENTIALS=C:\\ruta\\completa\\a\\tu\\fichero.json")
    print("="*80)
    sys.exit(1) # Detener la aplicación si la configuración es incorrecta

# Verificación del ID de proyecto e inicialización de Vertex AI
if not project_id:
    print("="*80)
    print("ERROR FATAL: La variable de entorno 'GOOGLE_CLOUD_PROJECT' no está configurada.")
    print("Por favor, añade tu ID de proyecto de Google Cloud a tu fichero .env.")
    print("="*80)
    sys.exit(1) # Detener la aplicación
else:
    try:
        # Inicializar Vertex AI con el proyecto y las credenciales encontradas.
        # Esto configura la librería para todas las llamadas posteriores.
        vertexai.init(project=project_id, location=location)
        print(f"--- Vertex AI inicializado para el proyecto: {project_id} ---")
    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"ERROR FATAL: Error de credenciales de Google. Causa: {e}")
        sys.exit(1)
    except Exception as e:
        print("="*80)
        print(f"ERROR FATAL: No se pudo inicializar Vertex AI. Causa: {e}")
        print("Verifica que el proyecto exista, que la facturación esté habilitada y que la cuenta de servicio tenga el rol 'Usuario de Vertex AI'.")
        print("="*80)
        sys.exit(1) # Detener la aplicación

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
            # Redirigir a la página de selección de controles (simulación de SoA)
            return redirect(url_for('select_controls', filename=filename))
        else:
            flash('Tipo de fichero no permitido. Sube solo PDF o DOCX.', 'error')
            return redirect(request.url)
    return render_template('index.html', title='Inicio')

@app.route('/select_controls/<filename>', methods=['GET', 'POST'])
def select_controls(filename):
    """Página para que el usuario seleccione los controles aplicables (simula la SoA)."""
    if request.method == 'POST':
        # Guardar los controles seleccionados en la sesión del usuario
        session['applicable_controls'] = request.form.getlist('applicable_controls')
        if not session['applicable_controls']:
            flash('No has seleccionado ningún control como aplicable. El análisis se realizará sobre todos.', 'warning')
        return redirect(url_for('analysis_page', filename=filename))

    # Para el método GET, mostrar la lista de controles
    all_controls = get_iso_controls_from_db()
    # La función get_iso_controls_from_db devuelve una lista vacía si hay un error
    # o no hay datos, por lo que esta es la única comprobación necesaria y segura.
    if not all_controls:
        flash('No se pudieron cargar los controles de la base de datos. Asegúrate de haber ejecutado el script de inicialización.', 'error')
        return redirect(url_for('index'))
    
    return render_template('select_controls.html', title='Declaración de Aplicabilidad', filename=filename, all_controls=all_controls)

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

    # Obtener los controles aplicables de la sesión, o todos si no se seleccionó ninguno.
    applicable_controls_ids = session.get('applicable_controls', [])

    # Realizar el análisis de cobertura con la IA
    analysis_results = []
    if extracted_text:
        # Renombramos la variable para mayor claridad
        raw_analysis_results = analyze_document_coverage(extracted_text, applicable_controls_ids)
        
        # Verificamos de forma más robusta si el análisis devolvió un error
        if raw_analysis_results and isinstance(raw_analysis_results[0], dict) and "error" in raw_analysis_results[0]:
             flash(f'Error en el análisis de IA: {raw_analysis_results[0]["error"]}', 'error')
             # No pasamos los resultados con error a la plantilla, se queda como lista vacía.
        else:
            analysis_results = raw_analysis_results

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

@app.route('/identify_risks', methods=['POST'])
def identify_risks():
    """Endpoint para identificar riesgos de un control no cubierto."""
    data = request.get_json()
    control_id = data.get('control_id')
    control_description = data.get('control_description')

    if not control_id or not control_description:
        return jsonify({'error': 'Faltan datos del control.'}), 400

    risks = identify_risks_for_control(control_id, control_description)
    return jsonify({'risks': risks})

# Esto permite ejecutar la aplicación directamente con `python app.py`
# lo cual es útil para depurar. `debug=True` activa el recargado automático
# y muestra páginas de error más detalladas.
if __name__ == '__main__':
    app.run(debug=True)