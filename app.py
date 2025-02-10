# import os
# import json
# import google.generativeai as genai
# import PyPDF2
# from fastapi import FastAPI, UploadFile
# from fastapi.middleware.cors import CORSMiddleware
# import shutil

# # Load Gemini API key
# API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
# if not API_KEY:
#     raise ValueError("Gemini API key is missing. Please set it in Replit Secrets.")

# genai.configure(api_key=API_KEY)
# genai_model = genai.GenerativeModel("gemini-1.5-flash")

# # Define prompt for KPI extraction
# FIXED_PROMPT = """
# Extract the following KPIs from the document:
# - PO No.
# - Supplier
# - Material (e.g., SS 304)
# - Material Description
# - PO Rate (USD)
# - Qty Shipped (MT)
# - FLC No
# - Bank Name
# - Total No. of Containers
# - Load Port
# - Acceptance Amount
# - BL No
# - BL Date
# - Invoice No
# - Invoice Date
# Return the KPIs in a structured JSON format.
# """

# app = FastAPI(
#     title="KPI Extraction API",
#     description="Upload a PDF to extract KPIs",
#     version="1.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
#     openapi_url="/openapi.json",
# )

# # Enable CORS for frontend integration
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.get("/")
# def read_root():
#     return {"message": "KPI Extraction API is running!"}



# def process_with_gemini(file_path):
#     """Processes extracted text using Gemini AI with a fixed prompt."""
#     uploaded_file = genai.upload_file(file_path)
#     try:
#         response = genai_model.generate_content([FIXED_PROMPT, uploaded_file])
#         clean_text = response.text.strip("```json").strip("``` ").strip()

#         try:
#             return json.loads(clean_text)
#         except json.JSONDecodeError:
#             return {
#                 "error": "Failed to parse JSON response",
#                 "raw_response": clean_text
#             }
#     except Exception as e:
#         return {"error": f"Error processing with Gemini: {str(e)}"}


# @app.post("/extract_kpi/")
# async def extract_kpi(file: UploadFile):
#     """Handles PDF file upload and extracts KPIs."""
#     try:
#         file_path = f"temp_{file.filename}"

#         # Save file temporarily
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         # Extract text from PDF
#         # extracted_text = extract_text_from_pdf(file_path)
#         # os.remove(file_path)  # Cleanup temp file

#         # if "Error" in extracted_text:
#         #     return {"error": extracted_text}

#         # Process extracted text with Gemini
#         return process_with_gemini(file_path)
#     except Exception as e:
#         return {"error": f"File processing error: {str(e)}"}

# # # Run the API
# # if __name__ == "__main__":
# #     import uvicorn
# #     uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)


import os
import json
import google.generativeai as genai
import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
from fastapi.responses import FileResponse

# Load Gemini API key
API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
if not API_KEY:
    raise ValueError("Gemini API key is missing. Please set it in Replit Secrets.")

genai.configure(api_key=API_KEY)
genai_model = genai.GenerativeModel("gemini-1.5-flash")

# Define prompt for KPI extraction
FIXED_PROMPT = """
Extract the following KPIs from the document and return a clean JSON:
- PO No.
- Supplier
- Material (e.g., SS 304)
- Material Description
- PO Rate (USD) (Ensure this is a number)
- Qty Shipped (MT) (Ensure this is a number)
- FLC No
- Bank Name
- Total No. of Containers (Ensure this is a number)
- Load Port
- Acceptance Amount (Ensure this is a number)
- BL No
- BL Date (Format as YYYY-MM-DD)
- Invoice No
- Invoice Date (Format as YYYY-MM-DD)
Ensure the JSON is formatted cleanly with proper data types.
"""

app = FastAPI(
    title="KPI Extraction API",
    description="Upload multiple PDFs to extract KPIs and download as an Excel file.",
    version="2.0",
    docs_url="/docs",
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
            extracted_data = json.loads(clean_text)

            # Ensure AI response is valid JSON
            if isinstance(extracted_data, dict):
                return extracted_data
            else:
                return {"error": "Unexpected AI response format", "raw_response": clean_text}
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_response": clean_text}
    except Exception as e:
        return {"error": f"Error processing with Gemini: {str(e)}"}


@app.post("/extract_kpi_multiple/")
async def extract_kpi_multiple(files: list[UploadFile]):
    """Handles multiple PDF uploads, extracts KPIs, and saves them in an Excel file."""
    extracted_data = []
    expected_fields = [
        "PO No.", "Supplier", "Material", "Material Description", "PO Rate (USD)", "Qty Shipped (MT)",
        "FLC No", "Bank Name", "Total No. of Containers", "Load Port", "Acceptance Amount",
        "BL No", "BL Date", "Invoice No", "Invoice Date"
    ]

    for file in files:
        file_path = f"temp_{file.filename}"

        # Save file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process file with Gemini AI
        extracted_info = process_with_gemini(file_path)
        extracted_info["File Name"] = file.filename  # Add filename to data

        # Ensure all expected fields exist (fill missing with "N/A")
        for field in expected_fields:
            extracted_info.setdefault(field, "N/A")

        extracted_data.append(extracted_info)
        os.remove(file_path)  # Cleanup file after processing

    # Convert extracted data into a Pandas DataFrame
    if extracted_data:
        df = pd.DataFrame(extracted_data)
    else:
        df = pd.DataFrame(columns=["File Name"] + expected_fields)  # Create an empty file if no data

    # Convert numeric fields properly
    numeric_columns = ["PO Rate (USD)", "Qty Shipped (MT)", "Total No. of Containers", "Acceptance Amount"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")  # Convert, but keep NaN if invalid

    # Format dates properly
    date_columns = ["BL Date", "Invoice Date"]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")  # Convert & format

    # Save to an Excel file with proper formatting
    excel_path = "extracted_kpis.xlsx"
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='KPIs')
        worksheet = writer.sheets['KPIs']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column = list(column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

    return {
        "message": "Extraction successful!",
        "excel_url": "/download_excel/"
    }


@app.get("/download_excel/")
async def download_excel():
    """Provides a downloadable link for the extracted KPI data in an Excel file."""
    excel_path = "extracted_kpis.xlsx"
    if os.path.exists(excel_path):
        return FileResponse(
            excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="extracted_kpis.xlsx"
        )
    return {"error": "Excel file not found"}
