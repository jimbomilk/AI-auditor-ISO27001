import os
from docx import Document
from pypdf import PdfReader

def _extract_text_from_pdf(file_path: str) -> str:
    """Extrae texto de un fichero PDF."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error al leer el PDF {file_path}: {e}")
        return ""

def _extract_text_from_docx(file_path: str) -> str:
    """Extrae texto de un fichero DOCX."""
    try:
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        print(f"Error al leer el DOCX {file_path}: {e}")
        return ""

def extract_text_from_document(file_path: str) -> str:
    """Extrae texto de un documento (PDF o DOCX) basado en su extensión."""
    _, extension = os.path.splitext(file_path)
    if extension.lower() == '.pdf':
        return _extract_text_from_pdf(file_path)
    elif extension.lower() == '.docx':
        return _extract_text_from_docx(file_path)
    
    print(f"Tipo de fichero no soportado para extracción: {extension}")
    return ""

