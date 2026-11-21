import os
from bs4 import BeautifulSoup

def clean_and_package_html(html_content):
    """
    Cleans out tracking code and embeds the legal text into a structurally
    sound HTML template that Microsoft Word reads natively as a styled document.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Destructive strip of script blocks and tracking codes
    for element in soup(["script", "noscript"]):
        element.decompose()
        
    # Extract the core body text elements
    body_content = soup.find('body')
    if body_content:
        inner_html = str(body_content)
    else:
        inner_html = str(soup)
        
    # Build a perfectly compliant HTML document with Word XML namespaces
    word_compliant_html = f"""<html xmlns:o="urn:schemas-microsoft-com:office:office" 
xmlns:w="urn:schemas-microsoft-com:office:word" 
xmlns="http://w3.org">
<head>
    <meta charset="utf-8">
    <title>Contract Template</title>
    <!--[if gte mso 9]>
    <xml>
        <w:WordDocument>
            <w:View>Print</w:View>
            <w:Zoom>100</w:Zoom>
            <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
    </xml>
    <![endif]-->
    <style>
        body {{
            font-family: "Calibri", "Arial", sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            margin: 1in;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        }}
        td, th {{
            padding: 6px;
            vertical-align: top;
        }}
    </style>
</head>
<body>
    {inner_html}
</body>
</html>"""
    return word_compliant_html

def convert_to_native_word():
    input_base_folder = "Downloaded_Contracts"
    output_base_folder = "Converted_Docs_Final"
    
    if not os.path.exists(input_base_folder):
        print(f"[!] Source folder '{input_base_folder}' not found. Run the downloader first.")
        return

    print(f"[*] Packaging HTML files into Microsoft Word native formats...")

    for root, dirs, files in os.walk(input_base_folder):
        for file in files:
            if file.endswith('.html'):
                html_path = os.path.join(root, file)
                
                # Recreate category folders
                relative_path = os.path.relpath(root, input_base_folder)
                output_dir = os.path.join(output_base_folder, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                
                docx_filename = file.replace('.html', '.docx')
                docx_path = os.path.join(output_dir, docx_filename)
                
                print(f"[~] Packaging: {file} -> {docx_filename}")
                
                try:
                    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_html = f.read()
                    
                    # Transform into Microsoft-ready rich text markup
                    final_markup = clean_and_package_html(raw_html)
                    
                    # Write file out with .docx extension
                    with open(docx_path, 'w', encoding='utf-8') as f_out:
                        f_out.write(final_markup)
                        
                    print(f" [+] Saved: {docx_path}")
                    
                except Exception as e:
                    print(f" [!] Error processing {file}: {e}")

if __name__ == "__main__":
    convert_to_native_word()
    print("\n[✔] Success! Open the files in 'Converted_Docs_Final' using Word or Pages.")

