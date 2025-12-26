from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2docx import Converter
import os
import uuid

# =========================
# CONFIGURATION DES DOSSIERS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# APP FASTAPI
# =========================

app = FastAPI(title="BantuDoc API")

# =========================
# CORS (PRODUCTION SAFE)
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production (Render)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {"status": "Backend OK"}

# =========================
# UTILS
# =========================

def cleanup_files(*paths: str):
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

# =========================
# ENDPOINT : PDF → DOCX
# =========================

@app.post("/convert/pdf-to-docx")
async def convert_pdf_to_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # Vérification type
    if file.content_type != "application/pdf":
        return JSONResponse(
            status_code=400,
            content={"error": "Le fichier doit être un PDF"}
        )

    # Lecture du fichier
    contents = await file.read()

    # Vérification taille (10 Mo max)
    if len(contents) > 10 * 1024 * 1024:
        return JSONResponse(
            status_code=400,
            content={"error": "Le fichier est trop volumineux (max 10 Mo)"}
        )

    # Noms temporaires
    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.pdf")
    output_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.docx")

    # Sauvegarde PDF
    with open(input_path, "wb") as f:
        f.write(contents)

    # Conversion
    try:
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
    except Exception as e:
        cleanup_files(input_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur de conversion : {str(e)}"}
        )

    # Nettoyage automatique après envoi
    background_tasks.add_task(cleanup_files, input_path, output_path)

    # Envoi du DOCX
    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=file.filename.replace(".pdf", ".docx"),
    )
