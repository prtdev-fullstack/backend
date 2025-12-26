from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2docx import Converter
import os
import uuid

# =========================
# CONFIG DOSSIERS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# APP
# =========================

app = FastAPI(title="BantuDoc API")

# =========================
# CORS (VERCEL + LOCAL)
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bantu-doc.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Backend OK"}

# =========================
# CLEANUP
# =========================

def cleanup_files(*paths):
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

# =========================
# PDF → DOCX (DOUBLE ROUTE)
# =========================

@app.post("/convert/pdf-to-docx")
@app.post("/convert/pdf-to-docx/")
async def convert_pdf_to_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if file.content_type != "application/pdf":
        return JSONResponse(
            status_code=400,
            content={"error": "Le fichier doit être un PDF"}
        )

    contents = await file.read()

    if len(contents) > 10 * 1024 * 1024:
        return JSONResponse(
            status_code=400,
            content={"error": "Fichier trop volumineux (10 Mo max)"}
        )

    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.pdf")
    output_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.docx")

    with open(input_path, "wb") as f:
        f.write(contents)

    try:
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
    except Exception as e:
        cleanup_files(input_path)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=file.filename.replace(".pdf", ".docx"),
    )
