import streamlit as st
import pypdfium2 as pdfium
from PIL import Image
from io import BytesIO
import gdown
from pytesseract import image_to_string
import os
import tempfile
from langchain_huggingface import HuggingFaceEndpoint
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
import pandas as pd
import shutil
from mrkdwn_analysis import MarkdownAnalyzer
import time

# Streamlit UI
st.title("PDF Invoice Extractor")
st.write("Provide the Google Drive folder link containing PDFs with invoices to extract structured data.")

# Sidebar for Hugging Face API Key
st.sidebar.title("Hugging Face API Key")
huggingface_api_key = st.sidebar.text_input("Enter your Hugging Face API Key:", type="password")

# Verifying Hugging Face API key
if huggingface_api_key:
    try:
        # Set up Hugging Face API with the provided key
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = huggingface_api_key
        repo_id = "Qwen/QwQ-32B-Preview"
        llm = HuggingFaceEndpoint(repo_id=repo_id, temperature=0.5)
        st.sidebar.success("Hugging Face API Key is valid!")
    except Exception as e:
        st.sidebar.error(f"Error with Hugging Face API Key: {e}")
else:
    st.sidebar.warning("Please provide a Hugging Face API Key.")

# User input for Google Drive Folder URL
folder_url = st.text_input("Enter Google Drive Folder URL:")

if "final_df" not in st.session_state:
    st.session_state.final_df = None
# Submit button to start the process
submit_button = st.button("Start Processing")

# Function to download DataFrame as CSV
def convert_df_to_csv(df):
    # Convert the DataFrame to CSV
    csv = df.to_csv(index=False)
    return csv
if submit_button:
    # Check if Hugging Face API Key is provided
    if not huggingface_api_key:
        st.error("Please provide a valid Hugging Face API Key before proceeding.")
    else:
        # Create an output folder for downloaded files
            output_folder = "downloaded_files"
            os.makedirs(output_folder, exist_ok=True)
            with st.spinner("Downloading files from folder..."):
                gdown.download_folder(folder_url, output=output_folder, quiet=False)

            # List all PDF files in the downloaded folder
            pdf_files = [f for f in os.listdir(output_folder) if f.endswith(".pdf")]

            if not pdf_files:
                st.error("No PDF files found in the provided Google Drive folder.")
            else:
                st.success(f"PDF file(s) downloaded successfully!")

                def convert_pdf_to_images(file_path, scale=300/72):
                    # Open the PDF document
                    pdf_file = pdfium.PdfDocument(file_path)
                    try:
                        # Process all pages
                        page_indices = [i for i in range(len(pdf_file))]
                        renderer = pdf_file.render(
                            pdfium.PdfBitmap.to_pil,
                            page_indices=page_indices,
                            scale=scale,
                        )
                        list_final_images = []
                        for i, image in zip(page_indices, renderer):
                            image_byte_array = BytesIO()
                            image.save(image_byte_array, format='jpeg', optimize=True)
                            image_byte_array = image_byte_array.getvalue()
                            list_final_images.append({i: image_byte_array})
                        return list_final_images
                    finally:
                        # Ensure the PDF document is closed
                        pdf_file.close()
                

                def extract_text_with_pytesseract(list_dict_final_images):
                    image_list = [list(data.values())[0] for data in list_dict_final_images]
                    image_content = []
                    for image_bytes in image_list:
                        image = Image.open(BytesIO(image_bytes))
                        raw_text = str(image_to_string(image))
                        image_content.append(raw_text)
                    return "\n".join(image_content)

                invoice_prompt_template = (
                    """As an expert in extracting and organizing invoice data, carefully analyze the provided input {user_input}, which may contain multiple invoices in an unstructured format. Follow these steps to extract and organize the data into a structured markdown table:
                
                    1. **Identification**: Identify all relevant invoice details in the text, such as Invoice Number, Invoice Date, Vendor Name, GSTIN, Buyer Name, GST of Buyer, Invoice Description, HSN/SAC Code, Quantity, Rate by Quantity, Taxable Amount, CGST, SGST, IGST, and Total Invoice Value.
                    
                    2. **Validation**: Ensure that the extracted data is valid and follows the expected format for each field (e.g., dates in YYYY-MM-DD format, numeric fields with proper decimals). If any field is missing or unclear, leave it blank or use a placeholder such as "-".
                    
                    3. **Deduplication**: Remove duplicate entries to ensure data integrity and clarity. Retain only unique rows.
                    
                    4. **Formatting**: Organize the extracted information into a well-structured markdown table. The table should have the following columns:
                       - Invoice Number
                       - Invoice Date
                       - Vendor Name
                       - GSTIN
                       - Buyer Name
                       - GST of Buyer
                       - Invoice Description
                       - HSN/SAC Code
                       - Quantity
                       - Rate by Quantity
                       - Taxable Amount
                       - CGST
                       - SGST
                       - IGST
                       - Total Invoice Value
                    
                    5. **Output**: Return only the completed markdown table without any additional text, explanation, or context.
                
                    **Example Table**:
                    | Invoice Number | Invoice Date | Vendor Name | GSTIN | Buyer Name | GST of Buyer  | Invoice Description  | HSN/SAC Code | Quantity | Rate by Quantity | Taxable Amount | CGST | SGST | IGST | Total Invoice Value |
                    |----------------|--------------|-------------|-------|------------|---------------|----------------------|--------------|----------|------------------|----------------|------|------|------|---------------------|
                    | 12345          | 2023-01-01   | Vendor A    | 1234  | Buyer A    | 5678          | Description A        | 12345        | 10       | 100              | 1000           | 90   | 90   | 180  | 1360                |
                
                    Ensure that the table you generate is accurate, complete, and free of errors or empty rows. Don'y generate duplicate values as same like don't generate subtotal and Total as a seperate"""
                )


                invoice_prompt = ChatPromptTemplate.from_template(invoice_prompt_template)
                invoice_chain = LLMChain(llm=llm, prompt=invoice_prompt)

                # Function to convert data to a DataFrame
                def convert_to_dataframe(data):
                    if "Table" not in data:
                        print("No table found in the extracted data. Skipping...")
                        return None
                    all_rows = []
                    for table in data["Table"]:
                        header = table["header"]
                        for row in table["rows"]:
                            all_rows.append(row)

                    # Create a DataFrame
                    df = pd.DataFrame(all_rows, columns=header)
                    # Remove duplicate columns if any
                    df = df.loc[:, ~df.columns.duplicated()]
                    # Replace any NaN or empty values with "-"
                    df = df.fillna("-")

                    # Remove rows that are completely empty
                    df = df.dropna(how="all")

                    return df

                # # Function to download DataFrame as CSV
                # def convert_df_to_csv(df):
                #     # Convert the DataFrame to CSV
                #     csv = df.to_csv(index=False)
                #     return csv
                
                def delete_downloaded_files(folder):
                    if os.path.exists(folder):
                        for root, dirs, files in os.walk(folder):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    os.unlink(file_path)  # Attempt to delete each file
                                except PermissionError:
                                    st.warning(f"File {file} is still in use. Skipping deletion.")
                        shutil.rmtree(folder, ignore_errors=True)  # Remove the folder
                        print(f"Deleted folder: {folder}")


                # Combine all tables into a single DataFrame
                consolidated_data = []

                for pdf_file in pdf_files:
                    file_path = os.path.join(output_folder, pdf_file)

                    with st.spinner(f"Processing {pdf_file}..."):
                        # Convert PDF to images
                        images = convert_pdf_to_images(file_path)

                        # Extract text from images
                        extracted_text = extract_text_with_pytesseract(images)

                        # Process extracted text with LLM
                        invoice_result = invoice_chain.invoke({"user_input": extracted_text})
                        invoice_text = invoice_result.get('text', "")

                        if invoice_text:
                            cleaned_invoice_text = invoice_text.replace("Assistant:", "").strip()

                            # Save cleaned_invoice_text to invoice.md
                            with open("invoice.md", "w") as file:
                                file.write(cleaned_invoice_text)

                            # Parse markdown table from invoice.md
                            analyzer = MarkdownAnalyzer("invoice.md")

                            data = analyzer.identify_tables()

                            # Convert data to DataFrame
                            df = convert_to_dataframe(data)

                            # Append the rows to the consolidated_data list
                            consolidated_data.append(df)

                 # Combine all DataFrames into one
                if consolidated_data:
                    final_df = pd.concat(consolidated_data, ignore_index=True)

                    # Store the final DataFrame in the session state
                    st.session_state.final_df = final_df

                    # Provide the download button for the combined CSV
                    # csv = convert_df_to_csv(final_df)

                                        # Display the consolidated data after download button
                    # st.write("Invoice Data:")
                    # st.dataframe(final_df)

                    # st.download_button(
                    #     label="Download All Invoices as CSV",
                    #     data=csv,
                    #     file_name="all_invoices.csv",
                    #     mime="text/csv"
                    # )

                delete_downloaded_files(output_folder)

            # else:
            #     st.error("No PDF files found in the provided Google Drive folder.")
# Display the consolidated table and download button if DataFrame exists
if st.session_state.final_df is not None:
    st.write("Invoice Data:")
    st.dataframe(st.session_state.final_df)

    csv = convert_df_to_csv(st.session_state.final_df)

    st.download_button(
        label="Download All Invoices as CSV",
        data=csv,
        file_name="all_invoices.csv",
        mime="text/csv"
    )