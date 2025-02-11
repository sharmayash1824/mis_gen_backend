
import os
import json
import google.generativeai as genai
import PyPDF2
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil

# Load Gemini API key
API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
if not API_KEY:
    raise ValueError("Gemini API key is missing. Please set it in Replit Secrets.")

genai.configure(api_key=API_KEY)
genai_model = genai.GenerativeModel("gemini-1.5-flash")

# Define prompt for KPI extraction
FIXED_PROMPT = """
Extract the following KPIs from these multiple documents and combine the information:
- PO No.
- Supplier
- Material (e.g., SS 304)
- Material Description
- PO Rate (USD)
- Net Weight
- Gross weight
- FLC No
- Bank Name
- Total No. of Containers
- Load Port
- Acceptance Amount
- BL No
- BL Date
- Invoice No
- Invoice Date
Analyze all documents together and return a single comprehensive JSON output combining information from all documents.
"""

app = FastAPI(
    title="KPI Extraction API",
    description="Upload multiple PDFs to extract combined KPIs",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "KPI Extraction API is running!"}

def process_with_gemini(file_paths):
    """Processes multiple files using Gemini AI with a fixed prompt."""
    try:
        uploaded_files = [genai.upload_file(path) for path in file_paths]
        response = genai_model.generate_content([FIXED_PROMPT] + uploaded_files)
        clean_text = response.text.strip("```json").strip("``` ").strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse JSON response",
                "raw_response": clean_text
            }
    except Exception as e:
        return {"error": f"Error processing with Gemini: {str(e)}"}

@app.post("/extract_kpi/")
async def extract_kpi(files: list[UploadFile] = File(...)):
    """Handles multiple PDF file uploads and extracts combined KPIs."""
    try:
        temp_files = []
        
        # Save all files temporarily
        for file in files:
            file_path = f"temp_{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append(file_path)

        # Process all files together
        result = process_with_gemini(temp_files)

        # Clean up temporary files
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)

        return result
    except Exception as e:
        # Clean up in case of error
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        return {"error": f"File processing error: {str(e)}"}
