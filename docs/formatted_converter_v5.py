import os
from docx import Document
from docx.shared import Inches, Pt

def apply_professional_styles(doc):
    """Applies clean, corporate typography to the document."""
    # Base normal style setup
    style_normal = doc.styles['Normal']
    font_normal = style_normal.font
    font_normal.name = 'Arial'
    font_normal.size = Pt(11)
    style_normal.paragraph_format.line_spacing = 1.25
    style_normal.paragraph_format.space_after = Pt(8)

    # Heading 1 setup
    style_h1 = doc.styles['Heading 1']
    font_h1 = style_h1.font
    font_h1.name = 'Arial'
    font_h1.size = Pt(18)
    font_h1.bold = True
    font_h1.color.rgb = None  # Black text
    style_h1.paragraph_format.space_before = Pt(12)
    style_h1.paragraph_format.space_after = Pt(6)

    # Heading 2 setup
    style_h2 = doc.styles['Heading 2']
    font_h2 = style_h2.font
    font_h2.name = 'Arial'
    font_h2.size = Pt(14)
    font_h2.bold = True
    font_h2.color.rgb = None
    style_h2.paragraph_format.space_before = Pt(12)
    style_h2.paragraph_format.space_after = Pt(4)

def build_nda(output_path):
    doc = Document()
    apply_professional_styles(doc)
    
    doc.add_heading("MUTUAL NON-DISCLOSURE AGREEMENT", level=1)
    doc.add_paragraph("This Mutual Non-Disclosure Agreement (the \"Agreement\") is entered into as of [INSERT DATE] (the \"Effective Date\"), by and between:")
    doc.add_paragraph("1. [COMPANY A NAME], a corporation organized under the laws of [STATE/COUNTRY], with offices at [ADDRESS] (\"Party A\"); and")
    doc.add_paragraph("2. [COMPANY B NAME], a corporation organized under the laws of [STATE/COUNTRY], with offices at [ADDRESS] (\"Party B\").")
    
    doc.add_heading("1. Definition of Confidential Information", level=2)
    doc.add_paragraph("For purposes of this Agreement, \"Confidential Information\" shall include all information or material that has or could have commercial value or other utility in the business in which Disclosing Party is engaged. If Information is in written form, the Disclosing Party shall label or stamp the materials with the word \"Confidential\" or some similar warning.")
    
    doc.add_heading("2. Obligations of Receiving Party", level=2)
    doc.add_paragraph("The Receiving Party shall hold and maintain the Confidential Information in strictest confidence for the sole and exclusive benefit of the Disclosing Party. Receiving Party shall carefully restrict access to Confidential Information to employees, contractors, and third parties as is reasonably required.")
    
    doc.add_heading("3. Exclusions from Confidentiality", level=2)
    doc.add_paragraph("Receiving Party's obligations under this Agreement do not extend to information that is:")
    doc.add_paragraph("Publicly known at the time of disclosure or subsequently becomes publicly known through no fault of the Receiving Party.", style='List Bullet')
    doc.add_paragraph("Discovered or created by the Receiving Party before disclosure by Disclosing Party.", style='List Bullet')
    doc.add_paragraph("Learned by the Receiving Party through legitimate means other than from the Disclosing Party.", style='List Bullet')
    
    doc.add_heading("IN WITNESS WHEREOF, the parties have executed this Agreement.", level=2)
    doc.add_paragraph("PARTY A: ___________________________    Date: _______________")
    doc.add_paragraph("PARTY B: ___________________________    Date: _______________")
    
    doc.save(output_path)

def build_msa(output_path):
    doc = Document()
    apply_professional_styles(doc)
    
    doc.add_heading("MASTER SERVICES AGREEMENT", level=1)
    doc.add_paragraph("This Master Services Agreement (the \"MSA\") is executed as of [INSERT DATE], by and between [PROVIDER NAME] (\"Provider\") and [CLIENT NAME] (\"Client\").")
    
    doc.add_heading("1. Structure and Statements of Work", level=2)
    doc.add_paragraph("This MSA sets forth the general legal terms and conditions under which Provider will supply professional services to Client. The specific scope, timeline, milestones, and fees for individual initiatives will be exclusively defined inside independent Statements of Work (\"SOW\") executed by both parties.")
    
    doc.add_heading("2. Intellectual Property Rights", level=2)
    doc.add_paragraph("Unless specified otherwise inside an applicable SOW, all deliverables specifically created for Client under this framework shall be considered \"Work Made for Hire\" and shall become the sole property of Client upon complete payment of all corresponding fees.")
    
    doc.add_heading("3. Limitation of Liability", level=2)
    doc.add_paragraph("NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES. IN NO EVENT SHALL EITHER PARTY'S TOTAL AGGREGATE LIABILITY EXCEED THE FEES ACTUALLY PAID BY CLIENT UNDER THE APPLICABLE SOW IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.")
    
    doc.save(output_path)

def build_sow(output_path):
    doc = Document()
    apply_professional_styles(doc)
    
    doc.add_heading("STATEMENT OF WORK (SOW)", level=1)
    doc.add_paragraph("This Statement of Work is issued pursuant to the Master Services Agreement dated [INSERT MSA DATE] by and between Provider and Client.")
    
    doc.add_heading("1. Project Scope & Objectives", level=2)
    doc.add_paragraph("[Insert a detailed narrative detailing the operational engineering or business milestones this specific project aims to resolve.]")
    
    doc.add_heading("2. Core Deliverables & Milestones", level=2)
    doc.add_paragraph("Milestone 1: Completion of initial technical architecture scoping documents due by [DATE].", style='List Bullet')
    doc.add_paragraph("Milestone 2: Beta version release and user-acceptance test loops due by [DATE].", style='List Bullet')
    doc.add_paragraph("Milestone 3: Deployment of final code asset environments and knowledge transition due by [DATE].", style='List Bullet')
    
    doc.add_heading("3. Compensation structure", level=2)
    doc.add_paragraph("Client agrees to pay Provider a fixed fee of $[INSERT AMOUNT] according to the following schedule:")
    doc.add_paragraph("30% upfront initialization payment upon execution.", style='List Bullet')
    doc.add_paragraph("40% upon satisfactory sign-off of Milestone 2.", style='List Bullet')
    doc.add_paragraph("30% final balance within 30 days of project closure.", style='List Bullet')
    
    doc.save(output_path)

def build_order_form(output_path):
    doc = Document()
    apply_professional_styles(doc)
    
    doc.add_heading("COMMERCIAL ORDER FORM", level=1)
    doc.add_paragraph("This order form is governed by the terms of the Master SaaS Agreement between the parties.")
    
    doc.add_heading("Customer Information", level=2)
    doc.add_paragraph("Company Name: [INSERT] \nBilling Address: [INSERT] \nPrimary Contact: [INSERT]")
    
    doc.add_heading("Subscription Details & Tiers", level=2)
    doc.add_paragraph("Product Tier: Enterprise SaaS Platform Access", style='List Bullet')
    doc.add_paragraph("Provisioned Seat Allocation: [INSERT SEAT COUNT] Authorized Users", style='List Bullet')
    doc.add_paragraph("Subscription Initial Term: Twelve (12) Months", style='List Bullet')
    
    doc.add_heading("Pricing Breakdown Table Layout Placeholder", level=2)
    doc.add_paragraph("[Item Description]                 [Unit Pricing]         [Total Fee]")
    doc.add_paragraph("SaaS Platform Access License       $__________            $__________")
    doc.add_paragraph("API Data Integration Add-on        $__________            $__________")
    
    doc.save(output_path)

def generate_all():
    target_dir = "Beautiful_Templates"
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"[*] Compiling pristine layouts inside: {target_dir}/")
    build_nda(os.path.join(target_dir, "1_Mutual_NDA_Template.docx"))
    build_msa(os.path.join(target_dir, "2_Master_Services_Agreement.docx"))
    build_sow(os.path.join(target_dir, "3_Statement_of_Work.docx"))
    build_order_form(os.path.join(target_dir, "4_SaaS_Order_Form.docx"))
    print("[✔] Generation complete! Files are natively structured Word documents.")

if __name__ == "__main__":
    generate_all()

