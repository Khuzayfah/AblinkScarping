"""Export service for generating reports in various formats"""
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
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
