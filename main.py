from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2docx import Converter
import os
import uuid

# =========================
# CONFIGURATION
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
# CORS (CORRECT & PROD SAFE)
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bantu-doc.vercel.app",   # ❌ PAS DE /
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # 🔥 CRUCIAL
)

# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {"status": "Backend OK"}

# =========================
# PDF → DOCX
# =========================

@app.post("/convert/pdf-to-docx")
async def convert_pdf_to_docx(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return JSONResponse(
            status_code=400,
            content={"error": "Le fichier doit être un PDF"}
        )

    input_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.pdf")
    output_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.docx")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    def file_iterator():
        with open(output_path, "rb") as f:
            yield from f

    return StreamingResponse(
        file_iterator(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename.replace(".pdf", ".docx")}"'
        }
    )
