# modules/pdf_exporter.py (v2.1 - Font Fix)
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
        # Η DejaVu δημιουργεί FileNotFoundError σε πολλά συστήματα.
        # Χρησιμοποιούμε την ενσωματωμένη "Arial" που (συνήθως) 
        # υποστηρίζει βασικά Ελληνικά μέσω του 'latin-1' encoding.
        try:
            # Προσθήκη της γραμματοσειράς Arial (απαιτείται το ttf αρχείο)
            # Χρειαζόμαστε το uni=True για υποστήριξη Unicode (UTF-8)
            # ΣΗΜΕΙΩΣΗ: Το fpdf2 (η νεότερη έκδοση) το χειρίζεται αυτό αυτόματα. 
            # Η παλιά FPDF μπορεί να θέλει χειροκίνητη προσθήκη.
            # Ας δοκιμάσουμε να βασιστούμε στις default γραμματοσειρές της FPDF.
            self.font_name = "Arial"
            # Δοκιμάζουμε να προσθέσουμε μια default γραμματοσειρά που μπορεί να υπάρχει
            # Το 'cp1253' είναι το Greek encoding.
            self.set_font(self.font_name, 'B', 12)
        except Exception as e:
            print(f"Warning: Could not set Arial font. {e}. Falling back to helvetica.")
            # Fallback αν η Arial αποτύχει
            self.font_name = "helvetica" # (Δεν θα υποστηρίζει Ελληνικά)

    def _clean_text(self, text):
        """
        v2.1: "Καθαρίζει" το κείμενο για να μπει στο PDF, αφαιρώντας
        χαρακτήρες που δεν υποστηρίζει το 'latin-1' (που χρησιμοποιεί η FPDF).
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Προσπαθεί να μετατρέψει Ελληνικούς τόνους σε απλά γράμματα
        # π.χ. 'Επισκόπηση' -> 'Επισκοπηση'
        try:
            # Normalize (NFD) σπάει τους τόνους, (NFKD) σπάει και άλλα.
            normalized_text = unicodedata.normalize('NFKD', text)
            # Κρατάμε μόνο ASCII χαρακτήρες
            ascii_bytes = normalized_text.encode('ascii', 'ignore')
            ascii_text = ascii_bytes.decode('ascii')
            
            if not ascii_text: # Αν το αποτέλεσμα είναι κενό (π.χ. ήταν μόνο ελληνικά)
                return text.encode('latin-1', 'replace').decode('latin-1')
                
            return ascii_text
        except Exception:
             # Αν αποτύχει τελείως, το στέλνουμε ως έχει
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

        # --- Ρύθμιση Πλάτους Στηλών ---
        col_widths = {}
        df_reset = pd.DataFrame() # Αρχικοποίηση
        
        try:
            df_reset = df.reset_index()
            # Αν η πρώτη στήλη είναι το 'Year', κάνε την πιο μικρή
            if df_reset.columns[0].lower() == 'year':
                 col_widths[df_reset.columns[0]] = 30
                 header_names = df_reset.columns[1:]
                 if len(header_names) == 0: # Αν έχει ΜΟΝΟ το Year
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
            # Fallback
            df_reset = df.reset_index() # (Βεβαιώσου ότι υπάρχει)
            width_per_col = (self.w - 20) / len(df_reset.columns)
            for col in df_reset.columns:
                col_widths[col] = width_per_col

        # --- Εκτύπωση Header ---
        self.set_font(self.font_name, 'B', 9)
        self.set_fill_color(240, 240, 240)
        for col in df_reset.columns:
            self.cell(col_widths[col], 7, self._clean_text(str(col)), 1, 0, 'C', fill=True)
        self.ln()

        # --- Εκτύπωση Γραμμών ---
        self.set_font(self.font_name, '', 9)
        self.set_fill_color(255, 255, 255)
        fill = False
        
        for i, row in df_reset.iterrows():
            for col in df_reset.columns:
                val = row[col]
                # Formatarisma arithmon
                if isinstance(val, (int, float)):
                    val_str = f"{val:,.2f}"
                else:
                    val_str = self._clean_text(str(val))
                
                self.cell(col_widths[col], 6, val_str, 'LR', 0, 'R', fill=fill)
            self.ln()
            fill = not fill # Εναλλαγή χρώματος
        
        self.cell(sum(col_widths.values()), 0, '', 'T') # Κλείσιμο πίνακα
        self.ln(10)


def create_pdf_report(
    info_df: pd.DataFrame, 
    categories: dict, 
    company_df: pd.DataFrame  # <-- v2.0: Η ΝΕΑ ΠΡΟΣΘΗΚΗ
) -> bytes:
    """
    Δημιουργεί μια πλήρη αναφορά PDF.
    v2.1: Χρησιμοποιεί την απλοποιημένη λογική γραμματοσειράς.
    """
    pdf = PDF()
    
    # Ορίζουμε το όνομα της εταιρείας για το header
    try:
        company_name = info_df['Όνομα'].iloc[0]
        pdf.set_company_name(company_name)
    except Exception:
        pdf.set_company_name("Financial Analysis Report")

    pdf.add_page()

    # 1. Πίνακας Επισκόπησης
    # v2.1: Έλεγχος αν το index είναι το 'Όνομα'
    if 'Όνομα' in info_df.columns:
        pdf.write_dataframe(info_df.set_index('Όνομα').T, "Company Overview")
    else:
         pdf.write_dataframe(info_df.T, "Company Overview")


    # 2. Ο "Χρυσός Πίνακας" (v2.0 ΝΕΑ ΠΡΟΣΘΗΚΗ)
    if company_df is not None and 'Year' in company_df.columns:
        pdf.write_dataframe(company_df.set_index('Year'), "Consolidated Financial Data")
    elif company_df is not None:
        pdf.write_dataframe(company_df, "Consolidated Financial Data")
    else:
        pdf.chapter_title("Consolidated Financial Data")
        pdf.set_font(pdf.font_name, '', 11)
        pdf.cell(0, 10, "No consolidated data was found or merged.", 0, 1)
        pdf.ln(5)


    # 3. Πίνακες Δεικτών (ανά κατηγορία)
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
    
    # Επιστροφή των bytes του PDF
    try:
        return pdf.output(dest='S')
    except Exception as e:
        print(f"CRITICAL PDF ERROR: {e}")
        # v2.1: Αν η κωδικοποίηση αποτύχει, στέλνουμε ένα κενό PDF 
        # για να μην κρασάρει τελείως το Streamlit.
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "PDF Generation Error", 0, 1, 'C')
        pdf.set_font("helvetica", "", 12)
        pdf.multi_cell(0, 10, f"An error occurred during PDF generation: {e}\nThis is often due to unsupported characters (like complex Greek symbols) that FPDF's default fonts cannot handle.")
        return pdf.output(dest='S')