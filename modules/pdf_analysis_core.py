import pdfplumber
import pandas as pd
import tabula
import os

def extract_tables_from_pdf(pdf_path):
    all_tables = []

    # Προσπάθεια με pdfplumber
    print("🔍 Δοκιμή εξαγωγής με pdfplumber...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table in tables:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    all_tables.append(df)
        if all_tables:
            print(f"✅ Εξαγωγή επιτυχής με pdfplumber ({len(all_tables)} πίνακες)")
            return all_tables
        else:
            print("⚠️ Δεν βρέθηκαν πίνακες με pdfplumber.")
    except Exception as e:
        print("❌ Σφάλμα pdfplumber:", e)

    # Εναλλακτικά με tabula
    print("🔁 Δοκιμή εξαγωγής με tabula...")
    try:
        tabula_tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True)
        if tabula_tables:
            print(f"✅ Εξαγωγή επιτυχής με tabula ({len(tabula_tables)} πίνακες)")
            all_tables.extend(tabula_tables)
        else:
            print("⚠️ Δεν βρέθηκαν πίνακες με tabula.")
    except Exception as e:
        print("❌ Σφάλμα tabula:", e)

    return all_tables


def show_extracted_data(tables):
    if not tables:
        print("❌ Δεν βρέθηκαν πίνακες στο PDF.")
        return
    print(f"\n📊 Σύνολο πινάκων: {len(tables)}\n")
    for i, df in enumerate(tables, start=1):
        print(f"Πίνακας {i}:")
        print(df.head())
        print("-" * 40)


if __name__ == "__main__":
    pdf_path = input("Δώσε το path του PDF αρχείου: ").strip()

    if not os.path.exists(pdf_path):
        print("❌ Το αρχείο δεν βρέθηκε.")
    else:
        tables = extract_tables_from_pdf(pdf_path)
        show_extracted_data(tables)
