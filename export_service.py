"""Export service for generating reports in various formats"""
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A3, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

DAILY_TABLE_COLUMNS = [
    'date', 'name_model', 'year_registered', 'depreciation', 'dealer_name', 'price'
]


class ExportService:
    """Service for exporting data to CSV, Excel, and PDF"""
    
    @staticmethod
    def to_dataframe(data):
        """Convert data to pandas DataFrame"""
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        # Reorder columns for better presentation
        columns_order = ['date', 'make_model', 'registered_year', 'depreciation', 
                        'dealer_name', 'price']
        existing_columns = [col for col in columns_order if col in df.columns]
        return df[existing_columns]
    
    @staticmethod
    def _flatten_grouped_data(daily_data):
        """Flatten grouped daily data into flat rows for CSV/Excel/PDF export."""
        if not daily_data or 'groups' not in daily_data:
            return []
        rows = []
        report_date = daily_data.get('date', '')
        for group in daily_data['groups']:
            category = group['category']
            for model_data in group['models']:
                model = model_data['name_model']
                entries = model_data.get('entries', [])
                if not entries:
                    rows.append({
                        'date': report_date,
                        'category': category,
                        'name_model': model,
                        'no': '',
                        'year_registered': '–',
                        'depreciation': '–',
                        'dealer_name': '–',
                        'price': '–'
                    })
                else:
                    for i, entry in enumerate(entries, 1):
                        price = entry.get('price')
                        price_str = f"${price:,.0f}" if price else '–'
                        rows.append({
                            'date': report_date,
                            'category': category,
                            'name_model': model,
                            'no': i,
                            'year_registered': entry['year_registered'],
                            'depreciation': entry['depreciation'],
                            'dealer_name': entry['dealer_name'],
                            'price': price_str
                        })
        return rows

    @staticmethod
    def to_daily_dataframe(daily_data):
        """Convert grouped daily data to DataFrame for export."""
        rows = ExportService._flatten_grouped_data(daily_data)
        if not rows:
            return pd.DataFrame(columns=['date', 'category', 'name_model', 'no', 'year_registered', 'depreciation', 'dealer_name', 'price'])
        return pd.DataFrame(rows)

    @staticmethod
    def export_daily_table_csv(daily_data):
        """Export daily table to CSV"""
        df = ExportService.to_daily_dataframe(daily_data)
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return output

    @staticmethod
    def export_daily_table_excel(daily_data):
        """Export daily table to Excel"""
        df = ExportService.to_daily_dataframe(daily_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Daily Report', index=False)
            worksheet = writer.sheets['Daily Report']
            for idx, col in enumerate(df.columns):
                max_len = len(str(col))
                if len(df) > 0:
                    max_len = max(max_len, df[col].astype(str).str.len().max())
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len + 2, 50)
        output.seek(0)
        return output

    @staticmethod
    def export_daily_table_pdf(daily_data, title="SGCarMart Daily Report"):
        """Export daily table to PDF"""
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        df = ExportService.to_daily_dataframe(daily_data)
        if len(df) > 0:
            table_data = [df.columns.tolist()] + df.values.tolist()
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No data available", styles['Normal']))
        doc.build(elements)
        output.seek(0)
        return output
    
    @staticmethod
    def export_to_csv(data):
        """Export data to CSV format"""
        df = ExportService.to_dataframe(data)
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return output
    
    @staticmethod
    def export_to_excel(data):
        """Export data to Excel format"""
        df = ExportService.to_dataframe(data)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Daily Report', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Daily Report']
            
            # Auto-adjust column widths
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
        
        output.seek(0)
        return output
    
    @staticmethod
    def export_to_pdf(data, title="SGCarMart Daily Report"):
        """Export data to PDF format"""
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        
        # Add title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))
        
        # Add date
        date_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        elements.append(Paragraph(date_text, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Prepare data for table
        if data:
            df = ExportService.to_dataframe(data)
            
            # Create table data
            table_data = [df.columns.tolist()] + df.values.tolist()
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No data available", styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        output.seek(0)
        return output
    
    @staticmethod
    def generate_summary(data):
        """Generate summary statistics from data"""
        if not data:
            return {
                'total_listings': 0,
                'highest_price': 0,
                'lowest_price': 0,
                'average_price': 0,
                'unique_models': 0
            }
        
        df = pd.DataFrame(data)
        prices = df['price'].dropna()

        return {
            'total_listings': len(df),
            'highest_price': float(prices.max()) if len(prices) > 0 else 0,
            'lowest_price': float(prices.min()) if len(prices) > 0 else 0,
            'average_price': float(prices.mean()) if len(prices) > 0 else 0,
            'unique_models': df['make_model'].nunique() if 'make_model' in df.columns else 0
        }

    # ─── Depreciation / Units Table Export ─────────────────────────

    @staticmethod
    def _flatten_depreciation_data(dep_data, categories, date_str=""):
        """Flatten depreciation pivot data into rows for CSV/Excel/PDF.
        Each row: Category, Vehicle, Year, LOW, AVG, COUNT
        Plus a wide-format version for spreadsheet-like export.
        """
        current_year = datetime.now().year
        years = list(range(current_year, 2014, -1))  # 2026..2015
        year_labels = [str(y) for y in years] + ["2014 & Older"]
        year_keys = [str(y) for y in years] + ["2014"]

        rows = []
        for category, models in categories.items():
            for vehicle in models:
                vehicle_data = dep_data.get(vehicle, {})
                row = {"Category": category, "Vehicle": vehicle}
                total_units = 0
                for label, key in zip(year_labels, year_keys):
                    yd = vehicle_data.get(int(key) if key != "2014" else key) or vehicle_data.get(key, {})
                    low = yd.get("lowest", 0) if yd else 0
                    avg = yd.get("average", 0) if yd else 0
                    cnt = yd.get("unit", 0) if yd else 0
                    total_units += cnt
                    row[f"{label} LOW"] = f"${low:,}" if low else "-"
                    row[f"{label} AVG"] = f"${avg:,}" if avg else "-"
                    row[f"{label} COUNT"] = cnt if cnt else "-"
                row["TOTAL UNITS"] = total_units
                rows.append(row)
        return rows

    @staticmethod
    def export_depreciation_csv(dep_data, categories, date_str=""):
        rows = ExportService._flatten_depreciation_data(dep_data, categories, date_str)
        if not rows:
            df = pd.DataFrame(columns=["Category", "Vehicle", "TOTAL UNITS"])
        else:
            df = pd.DataFrame(rows)
        output = BytesIO()
        df.to_csv(output, index=False, encoding="utf-8")
        output.seek(0)
        return output

    @staticmethod
    def export_depreciation_excel(dep_data, categories, date_str=""):
        rows = ExportService._flatten_depreciation_data(dep_data, categories, date_str)
        if not rows:
            df = pd.DataFrame(columns=["Category", "Vehicle", "TOTAL UNITS"])
        else:
            df = pd.DataFrame(rows)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Depreciation", index=False)
            ws = writer.sheets["Depreciation"]

            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            hdr_fill = PatternFill("solid", fgColor="4472C4")
            hdr_font = Font(bold=True, color="FFFFFF", size=10)
            cat_fill = PatternFill("solid", fgColor="548235")
            cat_font = Font(bold=True, color="FFFFFF", size=10)
            num_font = Font(bold=True, size=9)
            thin_border = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin"),
            )

            # Style header row
            for cell in ws[1]:
                cell.fill = hdr_fill
                cell.font = hdr_font
                cell.alignment = Alignment(horizontal="center", wrap_text=True)
                cell.border = thin_border

            # Style data rows
            prev_cat = None
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
                cat_val = row[0].value
                for cell in row:
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal="center")
                    if cell.column > 2:
                        cell.font = num_font
                # Bold vehicle name
                row[1].font = Font(bold=True, size=9)
                row[1].alignment = Alignment(horizontal="left")

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        max_len = max(max_len, len(str(cell.value or "")))
                    except:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 3, 18)
            # Wider for Vehicle column
            ws.column_dimensions["B"].width = 22

        output.seek(0)
        return output

    @staticmethod
    def export_depreciation_pdf(dep_data, categories, date_str="", title="Depreciation / Units"):
        rows = ExportService._flatten_depreciation_data(dep_data, categories, date_str)
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A3), leftMargin=20, rightMargin=20, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"{title} — {date_str}", styles["Title"]))
        elements.append(Spacer(1, 8))

        if not rows:
            elements.append(Paragraph("No data available", styles["Normal"]))
        else:
            df = pd.DataFrame(rows)
            # Simplify: only show Category, Vehicle, per-year COUNT + TOTAL UNITS
            # Full table is too wide — show summary
            simple_cols = ["Category", "Vehicle"]
            current_year = datetime.now().year
            for y in range(current_year, 2014, -1):
                col = f"{y} COUNT"
                if col in df.columns:
                    simple_cols.append(col)
            if "2014 & Older COUNT" in df.columns:
                simple_cols.append("2014 & Older COUNT")
            simple_cols.append("TOTAL UNITS")

            sdf = df[[c for c in simple_cols if c in df.columns]]
            # Rename columns shorter for PDF
            rename_map = {}
            for c in sdf.columns:
                if c.endswith(" COUNT"):
                    rename_map[c] = c.replace(" COUNT", "")
            sdf = sdf.rename(columns=rename_map)

            table_data = [sdf.columns.tolist()] + sdf.values.tolist()
            col_widths = [80, 110] + [28] * (len(sdf.columns) - 2)
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("FONTSIZE", (0, 1), (-1, -1), 6),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B4C6E7")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F7FC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)

        doc.build(elements)
        output.seek(0)
        return output
