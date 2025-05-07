# app.py

import streamlit as st
import pandas as pd
from datetime import datetime
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
import webbrowser

# Title
st.title("Invoice Generator")

st.subheader("Invoice Details")

client = st.text_input("Client Name")
client_address = st.text_area("Client Address (Optional)")
quote_date = st.date_input("Date", value=datetime.today())
initials = st.text_input("Employee Initials (e.g. MJ)")
quote_number = st.text_input("Quote Number")
ship_via = st.selectbox("Ship Via", ["Customer PU", "Rite-Way Semi"])
invoice_type = st.selectbox("Invoice Type", ["Invoice", "Deposit", "Credit"])

st.markdown("### Line Items")
num_items = st.number_input("How many line items?",
                            min_value=1, max_value=10, value=1)

line_items = []
for i in range(int(num_items)):
    description = st.text_input(
        f"Description #{i+1} (leave blank to use 'As per quote {quote_number}')", key=f"desc_{i}")
    amount = st.number_input(
        f"Amount #{i+1}", min_value=0.0, step=0.01, key=f"amt_{i}")
    if not description:
        description = f"As per quote {quote_number}"
    line_items.append((description, amount))

subtotal = sum(amount for _, amount in line_items)
pst_exempt = st.checkbox("PST Exempt")
gst_exempt = st.checkbox("GST Exempt")

pst = 0 if pst_exempt else subtotal * 0.07
gst = 0 if gst_exempt else subtotal * 0.05
total = subtotal + pst + gst

st.write(f"Subtotal: ${subtotal:.2f}")
st.write(f"PST (7%): {'Exempt' if pst_exempt else f'${pst:.2f}'})")
st.write(f"GST (5%): {'Exempt' if gst_exempt else f'${gst:.2f}'})")
st.write(f"Total: ${total:.2f}")


def get_next_invoice_number():
    filename = "invoice_log.xlsx"
    if not os.path.exists(filename):
        return "KAM001"
    try:
        df = pd.read_excel(filename)
        last_invoice = df["Invoice Number"].dropna().iloc[-1]
        last_num = int(last_invoice.replace("KAM", ""))
        return f"KAM{last_num+1:03d}"
    except:
        return "KAM001"


invoice_number = get_next_invoice_number()


def generate_invoice_pdf(data, line_items, filename):
    c = canvas.Canvas(filename, pagesize=LETTER)
    width, height = LETTER

    copies = [
        ("Client Copy", None),
        ("Accounting Copy", colors.yellow),
        ("Office Copy", colors.green),
        ("Records Copy", colors.cornflower)
    ]

    for copy_label, color in copies:
        c.setFillColor(colors.white)
        c.rect(0, 0, width, height, fill=True, stroke=0)

        invoice_text = "INVOICE"
        c.setFont("Helvetica-Bold", 18)
        invoice_text_width = c.stringWidth(invoice_text, "Helvetica-Bold", 18)
        invoice_box_x = width - 50 - invoice_text_width
        invoice_box_y = height - 50

        if color:
            c.setFillColor(color)
            c.rect(invoice_box_x - 5, invoice_box_y - 5,
                   invoice_text_width + 10, 25, fill=True, stroke=0)

        c.setFillColor(colors.black)
        c.drawRightString(width - 50, invoice_box_y + 10, invoice_text)

        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawRightString(width - 50, invoice_box_y - 5, copy_label)

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.red)
        c.drawRightString(width - 50, invoice_box_y - 20,
                          f"{data['Invoice Number']}")

        logo_y_top = height - 80
        if os.path.exists("RitewayLogoWeb.png"):
            c.setFillColor(colors.white)
            c.rect(40, logo_y_top, 120, 45, fill=True, stroke=0)
            c.drawImage("RitewayLogoWeb.png", 40, logo_y_top +
                        5, width=100, height=35, mask='auto')

        info_y = logo_y_top - 25
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(40, info_y, "Rite-Way Fencing (Kamloops) Inc.")
        c.drawString(40, info_y - 15, "405 Chilcotin Rd.")
        c.drawString(40, info_y - 30, "Kamloops, BC V2H 1G3")

        y = info_y - 50
        c.setFont("Helvetica", 10)
        details = [
            ("Client", data["Client"]),
            ("Client Address", data["Client Address"]),
            ("Date", str(data["Date"])),
            ("Initials", data["Initials"]),
            ("Quote Number", data["Quote Number"]),
            ("Ship Via", data["Ship Via"]),
            ("Invoice Type", data["Type"])
        ]
        for label_text, value in details:
            if value:
                c.drawString(40, y, f"{label_text}: {value}")
                y -= 15

        y -= 10

        # Build two-column layout: descriptions left, totals right (force all rows to show)
        left_col = [desc for desc, amt in line_items]
        total_col = [
            f"Subtotal: ${data['Amount']:.2f}",
            f"PST: {'Exempt' if data['PST'] == 0 else f'${data['PST']:.2f}'}",
            f"GST: {'Exempt' if data['GST'] == 0 else f'${data['GST']:.2f}'}",
            f"Total: ${data['Total']:.2f}"
        ]

        pad_left = max(0, len(total_col) - len(left_col))
        pad_right = max(0, len(left_col) - len(total_col))
        left_col += [""] * pad_left
        total_col += [""] * pad_right

        table_data = [["Description", ""]] + list(zip(left_col, total_col))

        table = Table(table_data, colWidths=[400, 130])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold')
        ]))
        table.wrapOn(c, width, height)
        table_height = table._height
        table.drawOn(c, 40, y - table_height)

        y = y - table_height - 30

        terms = [
            "* Due upon receipt unless previous arrangements made",
            "* Approved credit customers net 30 days",
            "* 1 1/2 per month (18% per annum) service charge on all overdue",
            "* Minimum charge $20.00",
            "* Shortages must be reported on delivery",
            "* Goods returned without our permission are subject to 20% restocking charge",
            "* We do not accept returns after 30 days.",
            "Make all checks payable to Rite-Way Fencing (Kamloops) Inc."
        ]
        c.setFont("Helvetica", 7)
        for line in terms:
            c.drawString(40, y, line)
            y -= 10

        c.showPage()
    c.save()


if st.button("Finalize Invoice"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    invoice_data = {
        "Timestamp": now,
        "Invoice Number": invoice_number,
        "Client": client,
        "Client Address": client_address,
        "Date": quote_date,
        "Initials": initials,
        "Quote Number": quote_number,
        "Ship Via": ship_via,
        "Type": invoice_type,
        "Amount": subtotal,
        "PST": pst,
        "GST": gst,
        "Total": total
    }

    try:
        df = pd.read_excel("invoice_log.xlsx")
    except FileNotFoundError:
        df = pd.DataFrame()
    df = df._append(invoice_data, ignore_index=True)
    df.to_excel("invoice_log.xlsx", index=False)

    folder = "Client Invoices"
    os.makedirs(folder, exist_ok=True)
    sanitized_name = client.replace(" ", "_").replace("/", "_")
    pdf_filename = os.path.join(
        folder, f"{invoice_number}_{sanitized_name}.pdf")

    generate_invoice_pdf(invoice_data, line_items, pdf_filename)
    webbrowser.open_new_tab(pdf_filename)

    st.success(f"Invoice {invoice_number} saved and opened!")
