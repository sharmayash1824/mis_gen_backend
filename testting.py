import os
import json
import google.generativeai as genai
import PyPDF2
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import csv

# Load Gemini API key
API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
if not API_KEY:
    raise ValueError(
        "Gemini API key is missing. Please set it in Replit Secrets.")

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
- Gr. Weight(MT)
- Net Weight
- LC No.
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
    description=
    "Upload multiple PDFs to extract combined KPIs and save them as CSV.",
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
        response = genai_model.generate_content([FIXED_PROMPT] +
                                                uploaded_files)
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


def update_csv_file(kpi_data, append=True):
    """Updates the CSV file with KPI entries, preventing duplicates based on PO No."""
    csv_file = 'KPI_Entries.csv'
    existing_ponos = set()

    # Read existing PO numbers
    if os.path.exists(csv_file):
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            existing_ponos = {row['PO No.'] for row in reader}

    # Check if PO No. already exists
    if kpi_data.get('PO No.') in existing_ponos:
        return {"message": "Duplicate entry. KPI data already exists for this PO No."}

    with open(csv_file, mode='a' if append else 'w', newline='') as file:
        writer = csv.writer(file)

        if file.tell() == 0:
            writer.writerow([
                'PO No.', 'Supplier', 'Material', 'Material Description',
                'PO Rate (USD)', 'Gr. Weight(MT)', 'Net Weight', 'LC No.',
                'Bank Name', 'Total No. of Containers', 'Load Port',
                'Acceptance Amount', 'BL No', 'BL Date', 'Invoice No',
                'Invoice Date'
            ])  # Header row

        writer.writerow([
            kpi_data.get('PO No.'),
            kpi_data.get('Supplier'),
            kpi_data.get('Material'),
            kpi_data.get('Material Description'),
            kpi_data.get('PO Rate (USD)'),
            kpi_data.get('Gr. Weight(MT)'),
            kpi_data.get('Net Weight'),
            kpi_data.get('LC No.'),
            kpi_data.get('Bank Name'),
            kpi_data.get('Total No. of Containers'),
            kpi_data.get('Load Port'),
            kpi_data.get('Acceptance Amount'),
            kpi_data.get('BL No'),
            kpi_data.get('BL Date'),
            kpi_data.get('Invoice No'),
            kpi_data.get('Invoice Date')
        ])


@app.post("/extract_kpi/")
async def extract_kpi(files: list[UploadFile] = File(...)):
    """Handles multiple PDF file uploads and extracts combined KPIs."""
    temp_files = []

    try:
        for file in files:
            file_path = f"temp_{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append(file_path)

        result = process_with_gemini(temp_files)

        for file_path in temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)

        return result
    except Exception as e:
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        return {"error": f"File processing error: {str(e)}"}


@app.post("/save_kpis/")
async def save_kpis(kpi_data: dict):
    """Endpoint to save KPIs to CSV when 'Update Backend CSV' button is pressed."""
    try:
        response = update_csv_file(kpi_data, append=True)
        if isinstance(response, dict) and 'message' in response:
            return response  # Return duplicate message if exists
        return {"message": "KPI data saved successfully."}
    except Exception as e:
        return {"error": f"Error saving KPI data: {str(e)}"}


@app.get("/get_kpis/")
async def get_kpis():
    """Retrieves the existing KPIs for editing."""
    csv_file = 'KPI_Entries.csv'
    try:
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    except FileNotFoundError:
        return {"error": "CSV file not found."}