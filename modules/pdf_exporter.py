# modules/pdf_exporter.py (v2.3 - Διόρθωση FPDF Dest='B')
import pandas as pd
from fpdf import FPDF
import sys
import os
import unicodedata

class PDF(FPDF):
    """
    Κλάση που κληρονομεί από το FPDF για να φτιάξει Header και Footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = "Financial Report"
        
        # === v2.1 FIX ===
        try:
            self.font_name = "Arial"
            try:
                # Το fpdf2 (που εγκαθίσταται ως "fpdf") υποστηρίζει uni=True
                self.add_font("Arial", "", "Arial.ttf", uni=True)
            except RuntimeError:
                # Fallback αν δεν βρει το Arial.ttf
                print("Warning: Arial.ttf not found. Falling back to built-in font (Ελληνικά μπορεί να μην εμφανίζονται).")
                self.font_name = "helvetica"

            self.set_font(self.font_name, 'B', 12)
        except Exception as e:
            print(f"Warning: Could not set Arial font. {e}. Falling back to helvetica.")
            self.font_name = "helvetica"

    def _clean_text(self, text):
        """
        v2.1: "Καθαρίζει" το κείμενο για να μπει στο PDF.
        """
        if not isinstance(text, str):
            text = str(text)
        
        try:
            # Προσπαθεί να μετατρέψει Ελληνικούς τόνους σε απλά γράμματα
            normalized_text = unicodedata.normalize('NFKD', text)
            ascii_bytes = normalized_text.encode('ascii', 'ignore')
            ascii_text = ascii_bytes.decode('ascii')
            
            if not ascii_text: 
                return text.encode('latin-1', 'replace').decode('latin-1')
                
            return ascii_text
        except Exception:
             return text.encode('latin-1', 'replace').decode('latin-1')


    def set_company_name(self, name):
        """ Ορίζει το όνομα της εταιρείας για το header """
        self.company_name = self._clean_text(name)

    def header(self):
        self.set_font(self.font_name, 'B', 12)
        self.cell(0, 10, self.company_name, 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        """ Δημιουργεί έναν τίτλο κεφαλαίου """
        self.set_font(self.font_name, 'B', 14)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, self._clean_text(title), 0, 1, 'L', fill=True)
        self.ln(4)

    def write_dataframe(self, df: pd.DataFrame, title: str):
        """
        v2.1 - "Έξυπνη" συνάρτηση για να γράφει ένα DataFrame στο PDF
        """
        self.chapter_title(title)
        
        if df is None or df.empty:
            self.set_font(self.font_name, '', 11)
            self.cell(0, 10, "No data available for this section.", 0, 1)
            self.ln(5)
            return

        col_widths = {}
        df_reset = pd.DataFrame() 
        
        try:
            df_reset = df.reset_index()
            if df_reset.columns[0].lower() == 'year':
                 col_widths[df_reset.columns[0]] = 30
                 header_names = df_reset.columns[1:]
                 if len(header_names) == 0: 
                     width_per_col = self.w - 20 - 30
                 else:
                     width_per_col = (self.w - 20 - 30) / len(header_names)
            else:
                header_names = df_reset.columns
                width_per_col = (self.w - 20) / len(df_reset.columns)
            
            for col in header_names:
                col_widths[col] = width_per_col
        
        except Exception as e:
            print(f"Error setting col widths: {e}")
            df_reset = df.reset_index() 
            width_per_col = (self.w - 20) / len(df_reset.columns)
            for col in df_reset.columns:
                col_widths[col] = width_per_col

        self.set_font(self.font_name, 'B', 9)
        self.set_fill_color(240, 240, 240)
        for col in df_reset.columns:
            self.cell(col_widths[col], 7, self._clean_text(str(col)), 1, 0, 'C', fill=True)
        self.ln()

        self.set_font(self.font_name, '', 9)
        self.set_fill_color(255, 255, 255)
        fill = False
        
        for i, row in df_reset.iterrows():
            for col in df_reset.columns:
                val = row[col]
                if isinstance(val, (int, float)):
                    val_str = f"{val:,.2f}"
                else:
                    val_str = self._clean_text(str(val))
                
                self.cell(col_widths[col], 6, val_str, 'LR', 0, 'R', fill=fill)
            self.ln()
            fill = not fill 
        
        self.cell(sum(col_widths.values()), 0, '', 'T') 
        self.ln(10)


def create_pdf_report(
    info_df: pd.DataFrame, 
    categories: dict, 
    company_df: pd.DataFrame  
) -> bytes:
    """
    Δημιουργεί μια πλήρη αναφορά PDF.
    v2.3: Διορθώνει το σφάλμα FPDF dest='B'.
    """
    pdf = PDF()
    
    try:
        company_name = info_df['Όνομα'].iloc[0]
        pdf.set_company_name(company_name)
    except Exception:
        pdf.set_company_name("Financial Analysis Report")

    pdf.add_page()

    if 'Όνομα' in info_df.columns:
        pdf.write_dataframe(info_df.set_index('Όνομα').T, "Company Overview")
    else:
         pdf.write_dataframe(info_df.T, "Company Overview")

    if company_df is not None and 'Year' in company_df.columns:
        pdf.write_dataframe(company_df.set_index('Year'), "Consolidated Financial Data")
    elif company_df is not None:
        pdf.write_dataframe(company_df, "Consolidated Financial Data")
    else:
        pdf.chapter_title("Consolidated Financial Data")
        pdf.set_font(pdf.font_name, '', 11)
        pdf.cell(0, 10, "No consolidated data was found or merged.", 0, 1)
        pdf.ln(5)

    if categories:
        for category_name, category_df in categories.items():
            if not category_df.empty and 'Year' in category_df.columns:
                pdf.write_dataframe(category_df.set_index('Year'), f"Ratios: {category_name}")
            else:
                pdf.write_dataframe(category_df, f"Ratios: {category_name} (Raw)")
    else:
        pdf.chapter_title("Ratio Analysis")
        pdf.set_font(pdf.font_name, '', 11)
        pdf.cell(0, 10, "No ratio categories were calculated.", 0, 1)
        pdf.ln(5)
            
    print("✅ PDF Report Generated.")
    
    # === v2.3 FIX: Χρήση του Fallback που είχαμε ήδη ===
    # Η παλιά έκδοση FPDF (1.7.2) που εγκατέστησε η pip ΔΕΝ υποστηρίζει dest='B'.
    # Πρέπει να χρησιμοποιήσουμε το 'S' (String) και να το κωδικοποιήσουμε σε bytes.
    try:
        # Επιστροφή String, κωδικοποιημένο σε 'latin-1' (που καταλαβαίνει η FPDF)
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        print(f"CRITICAL PDF ERROR: {e}")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "PDF Generation Error", 0, 1, 'C')
        pdf.set_font("helvetica", "", 12)
        pdf.multi_cell(0, 10, f"An error occurred during PDF generation: {e}")
        # Επιστροφή "καθαρών" bytes σε περίπτωση σφάλματος
        return pdf.output(dest='S').encode('latin-1')