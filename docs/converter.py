import os
from bs4 import BeautifulSoup
from docx import Document

def clean_html_to_text(html_content):
    """
    Parses legacy SEC HTML files, handles nested tables, and extracts
    structured text paragraphs while preserving basic spacing.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Strip unnecessary web scripts, styling blocks, and headers
    for element in soup(["script", "style", "head", "title", "meta"]):
        element.decompose()
        
    paragraphs = []
    # SEC filings extensively use paragraphs (<p>) and table rows for alignments
    for element in soup.find_all(['p', 'div', 'tr']):
        text = element.get_text(strip=True)
        if text:
            # Simple deduplication for text extracted from nested elements
            if not paragraphs or paragraphs[-1] != text:
                paragraphs.append(text)
                
    return paragraphs

def convert_html_folder_to_docx():
    input_base_folder = "Downloaded_Contracts"
    output_base_folder = "Converted_Docs"
    
    if not os.path.exists(input_base_folder):
        print(f"[!] Source folder '{input_base_folder}' not found. Please run the download script first.")
        return

    print(f"[*] Beginning text extraction and conversion into: '{output_base_folder}/'")

    # Walk through the MSA, SOW, NDA folders created by the downloader
    for root, dirs, files in os.walk(input_base_folder):
        for file in files:
            if file.endswith('.html'):
                html_path = os.path.join(root, file)
                
                # Determine output paths mirroring the category directory layout
                relative_path = os.path.relpath(root, input_base_folder)
                output_dir = os.path.join(output_base_folder, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                
                docx_filename = file.replace('.html', '.docx')
                docx_path = os.path.join(output_dir, docx_filename)
                
                print(f"[~] Converting: {file} -> {docx_filename}")
                
                try:
                    # Read raw HTML
                    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    
                    # Clean and parse text elements
                    clean_paragraphs = clean_html_to_text(html_content)
                    
                    # Create a new Word document file
                    doc = Document()
                    doc.add_heading(docx_filename.replace('_', ' ').replace('.docx', ''), level=1)
                    
                    # Append each clean paragraph structure to the document template
                    for para_text in clean_paragraphs:
                        doc.add_paragraph(para_text)
                        
                    # Save the Word file
                    doc.save(docx_path)
                    print(f" [+] Successfully saved: {docx_path}")
                    
                except Exception as e:
                    print(f" [!] Failed to convert {file}. Error: {e}")

if __name__ == "__main__":
    convert_html_folder_to_docx()
    print("\n[✔] Processing complete! Your editable Word files are waiting in 'Converted_Docs'.")

