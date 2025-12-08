# modules/languages.py
# Το Λεξικό του ValuePy (GR/EN)

TEXTS = {
    'GR': {
        'sidebar_title': "📜 Ιστορικό",
        'clear_history': "Καθαρισμός",
        'search_tab': "🔍 Αναζήτηση",
        'upload_tab': "📂 Ανέβασμα Αρχείου",
        'ticker_placeholder': "π.χ. MSFT, AEGN...",
        'comp_label': "⚔️ Προσθήκη Ανταγωνιστών",
        'comp_placeholder': "π.χ. GOOG, AMZN (με κόμμα)",
        'btn_run': "Έναρξη Ανάλυσης",
        'btn_upload': "Ανάλυση Αρχείου",
        'select_view': "Επιλογή Προβολής:",
        'download_pdf': "📥 Λήψη PDF",
        'tabs': ["📊 Γραφήματα", "⚖️ Αποτίμηση", "📄 Δεδομένα"],
        'processing': "Γίνεται επεξεργασία...",
        'val_lab_title': "🧪 Εργαστήριο Αποτίμησης",
        'val_lab_desc': "Ρύθμισε το WACC για να δεις αν η εταιρεία δημιουργεί αξία.",
        'metrics': {
            'quality': "ΠΟΙΟΤΗΤΑ ΚΕΡΔΩΝ",
            'roe': "ΑΠΟΔΟΣΗ (ROE)",
            'dso': "ΕΙΣΠΡΑΞΗ (DSO)",
            'valuation': "ΑΠΟΤΙΜΗΣΗ",
            'gap': "Διαφορά",
            'lev': "Μόχλευση",
            'solvent': "ΒΙΩΣΙΜΗ",
            'zombie': "ΖΟΜΠΙ",
            'creating': "ΔΗΜΙΟΥΡΓΕΙ",
            'destroying': "ΚΑΤΑΣΤΡΕΦΕΙ",
            'ok': "OK",
            'red_flag': "ΚΙΝΔΥΝΟΣ"
        },
        'waterfall_title': "Κέρδη vs Πραγματικά Μετρητά"
    },
    'EN': {
        'sidebar_title': "📜 History",
        'clear_history': "Clear History",
        'search_tab': "🔍 Search Ticker",
        'upload_tab': "📂 Upload File",
        'ticker_placeholder': "e.g. MSFT, AAPL...",
        'comp_label': "⚔️ Add Competitors",
        'comp_placeholder': "e.g. GOOG, AMZN (comma separated)",
        'btn_run': "Run Analysis",
        'btn_upload': "Analyze File",
        'select_view': "Select Company View:",
        'download_pdf': "📥 Download PDF",
        'tabs': ["📊 Charts", "⚖️ Valuation", "📄 Data"],
        'processing': "Processing...",
        'val_lab_title': "🧪 Valuation Lab",
        'val_lab_desc': "Adjust WACC to check for Economic Value Creation.",
        'metrics': {
            'quality': "EARNINGS QUALITY",
            'roe': "ROE (RETURN)",
            'dso': "DSO (COLLECTION)",
            'valuation': "VALUATION",
            'gap': "Gap",
            'lev': "Lev",
            'solvent': "SOLVENT",
            'zombie': "ZOMBIE",
            'creating': "CREATING",
            'destroying': "DESTROYING",
            'ok': "OK",
            'red_flag': "RED FLAG"
        },
        'waterfall_title': "Earnings vs Cash Flow Reality"
    }
}

def get_text(lang_code):
    return TEXTS.get(lang_code, TEXTS['EN'])