import os
from bs4 import BeautifulSoup
from html2docx import html2docx

def clean_and_format_html(html_content):
    """
    Cleans up tracking noise, inline scripts, and page breaks from SEC filings
    while keeping core structural HTML tags like tables, bold, and lists intact.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Destructive strip of script blocks and tracking codes
    for element in soup(["script", "style", "head", "title", "meta", "noscript"]):
        element.decompose()
        
    # Remove empty tags that mess up Word line spacing
    for empty_tag in soup.find_all(['p', 'div', 'span']):
        if not empty_tag.get_text(strip=True) and not empty_tag.find_all():
            empty_tag.decompose()
            
    return str(soup)

def convert_with_proper_formatting():
    input_base_folder = "Downloaded_Contracts"
    output_base_folder = "Converted_Docs_Formatted"
    
    if not os.path.exists(input_base_folder):
        print(f"[!] Source folder '{input_base_folder}' not found. Run the downloader first.")
        return

    print(f"[*] Beginning structural HTML conversion to styled Word documents...")

    for root, dirs, files in os.walk(input_base_folder):
        for file in files:
            if file.endswith('.html'):
                html_path = os.path.join(root, file)
                
                # Recreate category directories
                relative_path = os.path.relpath(root, input_base_folder)
                output_dir = os.path.join(output_base_folder, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                
                docx_filename = file.replace('.html', '.docx')
                docx_path = os.path.join(output_dir, docx_filename)
                
                print(f"[~] Formatting: {file} -> {docx_filename}")
                
                try:
                    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_html = f.read()
                    
                    # Clean tracking artifacts but keep structural formatting
                    structured_html = clean_and_format_html(raw_html)
                    
                    # FIX: Explicitly pass the title argument required by the function signature
                    clean_title = docx_filename.replace('.docx', '')
                    docx_buffer = html2docx(structured_html, title=clean_title)
                    
                    # Save document
                    with open(docx_path, 'wb') as f_out:
                        f_out.write(docx_buffer.read())
                        
                    print(f" [+] Saved with formatting: {docx_path}")
                    
                except Exception as e:
                    print(f" [!] Error formatting {file}: {e}")

if __name__ == "__main__":
    convert_with_proper_formatting()
    print("\n[✔] Done! Check the 'Converted_Docs_Formatted' folder for visually styled files.")

