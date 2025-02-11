import os
import json
import google.generativeai as genai
import PyPDF2
from fastapi import FastAPI, UploadFile
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
Extract the following KPIs from the document:
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
Return the KPIs in a structured JSON format.
"""

app = FastAPI(
    title="KPI Extraction API",
    description="Upload a PDF to extract KPIs",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for frontend integration
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



def process_with_gemini(file_path):
    """Processes extracted text using Gemini AI with a fixed prompt."""
    uploaded_file = genai.upload_file(file_path)
    try:
        response = genai_model.generate_content([FIXED_PROMPT, uploaded_file])
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
async def extract_kpi(file: UploadFile):
    """Handles PDF file upload and extracts KPIs."""
    try:
        file_path = f"temp_{file.filename}"

        # Save file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract text from PDF
        # extracted_text = extract_text_from_pdf(file_path)
        # os.remove(file_path)  # Cleanup temp file

        # if "Error" in extracted_text:
        #     return {"error": extracted_text}

        # Process extracted text with Gemini
        return process_with_gemini(file_path)
    except Exception as e:
        return {"error": f"File processing error: {str(e)}"}

# # Run the API
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)
