"""
Ablink SGCarmart Scraper - PDF Enhanced HTML Generator
By Oneiros Indonesia

Generates HTML report EXACTLY matching PDF format:
- Each year: 2 columns (Price + Units)
- Compact layout
- Category headers
- Color-coded DIFF
"""

import pandas as pd
from datetime import datetime
import os


class PDFEnhancedGenerator:
    """Generate HTML exactly matching PDF layout"""
    
    def generate_report(self, df, output_file=None):
        """Generate PDF-exact HTML report"""
        
        current_date = datetime.now().strftime("%d %b").upper()
        timestamp = datetime.now().strftime("%d %B %Y")
        
        # Year columns
        years = ['2025', '2024', '2023', '2022', '2021', '2020', 
                '2019', '2018', '2017', '2016', '2015', '2014']
        
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
                margin: 8mm;
            }}
            body {{ margin: 0; padding: 8px; }}
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Calibri', Arial, sans-serif;
            font-size: 8pt;
            padding: 15px;
            background: white;
        }}
        
        .header {{
            text-align: left;
            margin-bottom: 10px;
            font-weight: bold;
            font-size: 10pt;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7.5pt;
        }}
        
        th {{
            background: #d9d9d9;
            border: 0.5pt solid #000;
            padding: 2px 3px;
            text-align: center;
            font-weight: bold;
            font-size: 7pt;
            white-space: nowrap;
        }}
        
        td {{
            border: 0.5pt solid #000;
            padding: 2px 4px;
            text-align: right;
            white-space: nowrap;
        }}
        
        td.vehicle {{
            text-align: left;
            padding-left: 6px;
            font-size: 8pt;
        }}
        
        td.category {{
            background: #e8e8e8;
            font-weight: bold;
            text-align: left;
            padding-left: 6px;
            font-size: 8.5pt;
        }}
        
        td.price {{
            text-align: right;
            padding-right: 6px;
        }}
        
        td.units {{
            text-align: center;
            padding: 2px 2px;
        }}
        
        td.total {{
            text-align: center;
            font-weight: bold;
        }}
        
        td.diff-pos {{
            text-align: center;
            color: #008000;
            font-weight: bold;
        }}
        
        td.diff-neg {{
            text-align: center;
            color: #c00000;
            font-weight: bold;
        }}
        
        td.diff-zero {{
            text-align: center;
        }}
        
        td.empty {{
            text-align: center;
        }}
        
        .footer {{
            margin-top: 15px;
            text-align: center;
            font-size: 7pt;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        DATE: {current_date} &nbsp;&nbsp;&nbsp; D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S
    </div>
    
    <table>
        <thead>
            <tr>
"""
        
        # Year headers
        html += '                <th style="width: 120px;"></th>\n'  # Empty for vehicle column
        for year in years:
            html += f'                <th colspan="2" style="width: 65px;">{year}</th>\n'
        html += '                <th colspan="2">2014 & Older</th>\n'
        html += '                <th>TOTAL<br>UNITS</th>\n'
        html += '                <th>Previous<br>(Date)</th>\n'
        html += '                <th>DIFF</th>\n'
        html += '            </tr>\n'
        html += '        </thead>\n'
        html += '        <tbody>\n'
        
        # Group by category
        categories = df['Category'].unique()
        
        for category in categories:
            # Category row
            total_cols = len(years) * 2 + 2 + 4  # years*2 + 2014*2 + vehicle + totals
            html += f'            <tr>\n'
            html += f'                <td colspan="{total_cols}" class="category">{category}</td>\n'
            html += f'            </tr>\n'
            
            # Vehicles in category
            cat_df = df[df['Category'] == category]
            
            for _, row in cat_df.iterrows():
                html += '            <tr>\n'
                html += f'                <td class="vehicle">{row["Vehicle"]}</td>\n'
                
                # Each year: price and units
                for year in years:
                    price_col = f'{year}_price'
                    units_col = f'{year}_units'
                    
                    # Price
                    if price_col in df.columns:
                        price = row[price_col]
                        if pd.isna(price) or price == 0:
                            html += '                <td class="empty">-</td>\n'
                        else:
                            html += f'                <td class="price">${int(price):,}</td>\n'
                    else:
                        html += '                <td class="empty">-</td>\n'
                    
                    # Units
                    if units_col in df.columns:
                        units = row[units_col]
                        if pd.isna(units) or units == 0:
                            html += '                <td class="units">0</td>\n'
                        else:
                            html += f'                <td class="units">{int(units)}</td>\n'
                    else:
                        html += '                <td class="units">0</td>\n'
                
                # 2014 & Older
                if '2014_price' in df.columns:
                    price = row['2014_price']
                    if pd.isna(price) or price == 0:
                        html += '                <td class="empty">-</td>\n'
                    else:
                        html += f'                <td class="price">${int(price):,}</td>\n'
                else:
                    html += '                <td class="empty">-</td>\n'
                
                if '2014_units' in df.columns:
                    units = row['2014_units']
                    if pd.isna(units) or units == 0:
                        html += '                <td class="units">0</td>\n'
                    else:
                        html += f'                <td class="units">{int(units)}</td>\n'
                else:
                    html += '                <td class="units">0</td>\n'
                
                # TOTAL UNITS
                total = row.get('TOTAL UNITS', 0)
                html += f'                <td class="total">{int(total)}</td>\n'
                
                # Previous
                prev = row.get('Previous', 0)
                html += f'                <td class="total">{int(prev)}</td>\n'
                
                # DIFF
                diff = row.get('DIFF', 0)
                if diff > 0:
                    html += f'                <td class="diff-pos">{int(diff)}</td>\n'
                elif diff < 0:
                    html += f'                <td class="diff-neg">{int(diff)}</td>\n'
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
        
        # Save
        if not output_file:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = "daily_reports"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            output_file = f"{output_folder}/pdf_exact_{ts}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"[OK] PDF-exact HTML: {output_file}")
        
        return output_file
