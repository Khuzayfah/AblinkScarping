"""
Ablink SGCarmart Scraper - PDF-Style HTML Generator
By Oneiros Indonesia

Generates HTML report matching the exact PDF format:
- Each year has 2 columns: Price ($) and Units
- Category section headers
- Color-coded DIFF values
"""

import pandas as pd
from datetime import datetime
import os


class PDFStyleHTMLGenerator:
    """Generate HTML reports matching PDF format exactly"""
    
    def generate_report(self, df, output_file=None):
        """
        Generate PDF-style HTML report
        
        Args:
            df: DataFrame with columns: Vehicle, Category, year columns, TOTAL UNITS, Previous, DIFF
            output_file: Output filename (optional)
        
        Returns:
            str: Path to generated HTML file
        """
        
        # Get current date
        current_date = datetime.now().strftime("%d %b").upper()
        timestamp = datetime.now().strftime("%d %B %Y")
        
        # Identify year columns
        year_columns = ['2025', '2024', '2023', '2022', '2021', '2020', 
                       '2019', '2018', '2017', '2016', '2015', '2014 & Older']
        
        # Start HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Depreciation Report - {current_date}</title>
    <style>
        @media print {{
            @page {{
                size: A4 landscape;
                margin: 10mm;
            }}
            body {{
                margin: 0;
                padding: 10px;
            }}
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            font-size: 9pt;
            padding: 20px;
            background: white;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 15px;
            font-weight: bold;
            font-size: 11pt;
        }}
        
        .date {{
            display: inline-block;
            margin-right: 50px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
        }}
        
        th {{
            background: #d9d9d9;
            border: 1px solid #000;
            padding: 4px 2px;
            text-align: center;
            font-weight: bold;
            font-size: 7pt;
        }}
        
        td {{
            border: 1px solid #000;
            padding: 3px 4px;
            text-align: right;
        }}
        
        td.vehicle-name {{
            text-align: left;
            font-weight: normal;
            padding-left: 8px;
        }}
        
        td.category {{
            background: #e0e0e0;
            font-weight: bold;
            text-align: left;
            padding-left: 8px;
            font-size: 9pt;
        }}
        
        td.price {{
            text-align: right;
        }}
        
        td.units {{
            text-align: center;
        }}
        
        td.total {{
            text-align: center;
            font-weight: bold;
        }}
        
        td.diff-positive {{
            text-align: center;
            color: #006600;
            font-weight: bold;
        }}
        
        td.diff-negative {{
            text-align: center;
            color: #cc0000;
            font-weight: bold;
        }}
        
        td.diff-zero {{
            text-align: center;
        }}
        
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 8pt;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <span class="date">DATE: {current_date}</span>
        <span>D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S</span>
    </div>
    
    <table>
        <thead>
            <tr>
                <th rowspan="2" style="width: 150px;">VEHICLE</th>
"""
        
        # Year headers (each year has 2 columns: price and units)
        for year in year_columns:
            html += f'                <th colspan="2">{year}</th>\n'
        
        html += """                <th rowspan="2">TOTAL<br>UNITS</th>
                <th rowspan="2">Previous<br>(Date)</th>
                <th rowspan="2">DIFF</th>
            </tr>
        </thead>
        <tbody>
"""
        
        # Group by category
        categories = df['Category'].unique()
        
        for category in categories:
            # Category header row
            total_cols = len(year_columns) * 2 + 4  # years*2 + vehicle + total + previous + diff
            html += f'            <tr>\n'
            html += f'                <td colspan="{total_cols}" class="category">{category}</td>\n'
            html += f'            </tr>\n'
            
            # Get vehicles in this category
            category_df = df[df['Category'] == category]
            
            for _, row in category_df.iterrows():
                html += '            <tr>\n'
                
                # Vehicle name
                html += f'                <td class="vehicle-name">{row["Vehicle"]}</td>\n'
                
                # For each year: price and units columns
                for year in year_columns:
                    if year in df.columns:
                        price = row[year]
                        # Price column
                        if pd.isna(price) or price == 0:
                            html += '                <td class="price">-</td>\n'
                        else:
                            html += f'                <td class="price">${price:,.0f}</td>\n'
                        
                        # Units column (we'll use 0 for now as units are embedded with prices in current data)
                        html += '                <td class="units">0</td>\n'
                    else:
                        html += '                <td class="price">-</td>\n'
                        html += '                <td class="units">0</td>\n'
                
                # TOTAL UNITS
                total_units = row.get('TOTAL UNITS', 0)
                html += f'                <td class="total">{int(total_units)}</td>\n'
                
                # Previous
                previous = row.get('Previous', 0)
                html += f'                <td class="total">{int(previous)}</td>\n'
                
                # DIFF (color-coded)
                diff = row.get('DIFF', 0)
                if diff > 0:
                    html += f'                <td class="diff-positive">{int(diff)}</td>\n'
                elif diff < 0:
                    html += f'                <td class="diff-negative">{int(diff)}</td>\n'
                else:
                    html += f'                <td class="diff-zero">{int(diff)}</td>\n'
                
                html += '            </tr>\n'
        
        html += """        </tbody>
    </table>
    
    <div class="footer">
        <p><strong>Ablink SGCarmart Scraper</strong> | Developed by Oneiros Indonesia</p>
        <p>Generated: """ + timestamp + """ | Data Source: www.sgcarmart.com</p>
    </div>
</body>
</html>"""
        
        # Save file
        if not output_file:
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = "daily_reports"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            output_file = f"{output_folder}/depreciation_pdf_style_{timestamp_file}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"[OK] PDF-style HTML report saved: {output_file}")
        
        return output_file
