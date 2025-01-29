# INVOICE EXTRACTOR

# PDF Invoice Extractor

The **PDF Invoice Extractor** is a Streamlit-based application that extracts structured data from invoices in PDF format and consolidates the extracted information into a single, unified table. The extracted data can then be downloaded as a CSV file for further processing and analysis.

## Features

- Download PDFs from a Google Drive folder link.
- Convert PDF pages to images for processing.
- Extract text from images using OCR (Tesseract).
- Use a Hugging Face LLM to process text and extract structured invoice data.
- Consolidate all extracted data into a single table.
- Export consolidated data as a CSV file.
- Automatic cleanup of downloaded and processed files.

## Prerequisites

Ensure the following dependencies are installed:
- Python 3.8 or later
- Required Python packages:
  - `streamlit`
  - `pypdfium2`
  - `Pillow`
  - `gdown`
  - `pytesseract`
  - `langchain_huggingface`
  - `pandas`
  - `shutil`
  - `markdown-analysis` 

## Installation

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Tesseract OCR:

   - **Windows**: Download and install from [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
   - **Linux/macOS**: Install via your package manager:
     ```bash
     sudo apt-get install tesseract-ocr   # For Linux
     brew install tesseract              # For macOS
     ```

4. Obtain a Hugging Face API Key:
   - Sign up or log in to [Hugging Face](https://huggingface.co/).
   - Generate an API key from your account settings.
   - Provide the API key in the app when prompted.

## Usage

1. Run the Streamlit application:

   ```bash
   streamlit run invoice_extractor.py
   ```

2. In the web interface:
   - Enter your Hugging Face API Key in the sidebar.
   - Provide the Google Drive folder link containing the PDFs.
   - Click the **Start Processing** button.

3. The app will:
   - Download PDF files from the specified Google Drive folder.
   - Extract structured invoice data and consolidate it into a single table.
   - Display the consolidated table in the app.
   - Allow you to download the data as a CSV file.

