# modules/report_generator.py (v5.0 - CFA Compatible)
from fpdf import FPDF
import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'ValuePy - Forensic Analysis Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def clean_text(text):
    if text is None: return ""
    text = str(text).replace("🟢", "").replace("🔴", "").replace("⚠️", "").replace("✅", "").replace("€", "EUR ")
    return text.strip()

def create_pdf_bytes(company_name, res):
    pdf = PDFReport()
    pdf.add_page()
    
    # 1. Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, txt=f"Report: {clean_text(company_name)}", ln=True, align='L')
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, txt=f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.line(10, 35, 200, 35)
    pdf.ln(10)

    # UNPACK DATA (New Structure)
    an = res.get('Analysis', {})
    forensics = res.get('Forensics', {})
    
    def add_section(title, data_dict):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, title, ln=True, fill=True)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        
        # Grid layout simulation (2 cols)
        keys = list(data_dict.keys())
        for i in range(0, len(keys), 2):
            k1 = keys[i]
            v1 = data_dict[k1]
            pdf.cell(50, 6, k1 + ":", border=0)
            pdf.cell(40, 6, str(v1), border=0)
            
            if i + 1 < len(keys):
                k2 = keys[i+1]
                v2 = data_dict[k2]
                pdf.cell(50, 6, k2 + ":", border=0)
                pdf.cell(40, 6, str(v2), border=0, ln=True)
            else:
                pdf.ln()
        pdf.ln(4)

    # 2. Forensics Summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "I. Forensic Health Check", ln=True)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(60, 8, f"Health Score: {forensics.get('Health_Score',0)}/100", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(60, 6, f"Z-Score (Bankruptcy): {forensics.get('Z_Score',0)}", ln=True)
    pdf.cell(60, 6, f"M-Score (Manipulation): {forensics.get('M_Score',0)}", ln=True)
    pdf.ln(5)

    # 3. The 7 Pillars
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "II. Fundamental Analysis (7 Pillars)", ln=True)
    
    add_section("1. Liquidity", an.get('1_Liquidity', {}))
    add_section("2. Activity & Efficiency", an.get('2_Activity', {}))
    add_section("3. Solvency", an.get('3_Solvency', {}))
    add_section("4. Profitability", an.get('4_Profitability', {}))
    add_section("5. Management Returns", an.get('5_Management', {}))
    add_section("6. Per Share Data", an.get('6_Per_Share', {}))
    add_section("7. Cash Flow", an.get('7_Cash_Flow', {}))

    # Footer Disclaimer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, "Disclaimer: Automated analysis for educational purposes only.")

    return bytes(pdf.output())