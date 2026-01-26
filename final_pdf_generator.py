"""
Ablink SGCarmart Scraper - Final PDF-Match Generator
By Oneiros Indonesia

Generates report with EXACT colors and layout from uploaded PDF
No process visible - direct result
"""

import pandas as pd
from datetime import datetime
import os


class FinalPDFGenerator:
    """Generate report exactly matching PDF colors and layout"""
    
    def generate_report(self, df, output_file=None):
        """Generate report silently with exact PDF styling"""
        
        current_date = datetime.now().strftime("%d %b").upper()
        timestamp = datetime.now().strftime("%d %B %Y")
        
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
            body {{ margin: 0; padding: 5px; }}
            .no-print {{ display: none !important; }}
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Calibri', Arial, sans-serif;
            font-size: 8pt;
            padding: 10px;
            background: #f5f5f5;
        }}
        
        .container {{
            background: white;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header {{
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 10px;
            color: #000;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
            background: white;
        }}
        
        /* Header styling - light gray like PDF */
        th {{
            background: #d9d9d9;
            border: 1px solid #a6a6a6;
            padding: 3px 4px;
            text-align: center;
            font-weight: bold;
            font-size: 7.5pt;
            color: #000;
        }}
        
        td {{
            border: 1px solid #d0d0d0;
            padding: 2px 5px;
            font-size: 8pt;
        }}
        
        /* Vehicle name column */
        td.vehicle {{
            text-align: left;
            padding-left: 8px;
            background: #fff;
            font-weight: normal;
        }}
        
        /* Category headers - light gray with bold */
        td.category {{
            background: #e7e6e6;
            font-weight: bold;
            text-align: left;
            padding: 4px 8px;
            font-size: 9pt;
            color: #000;
            border: 1px solid #b8b8b8;
        }}
        
        /* Price cells - white background */
        td.price {{
            text-align: right;
            padding-right: 8px;
            background: #fff;
            color: #000;
        }}
        
        /* Units cells - white background, centered */
        td.units {{
            text-align: center;
            background: #fff;
            color: #000;
        }}
        
        /* Empty cells - dash */
        td.empty {{
            text-align: center;
            background: #fff;
            color: #666;
        }}
        
        /* Total columns - white with bold */
        td.total {{
            text-align: center;
            font-weight: bold;
            background: #fff;
            color: #000;
        }}
        
        /* DIFF positive - green text */
        td.diff-pos {{
            text-align: center;
            font-weight: bold;
            background: #fff;
            color: #00b050;
        }}
        
        /* DIFF negative - red text */
        td.diff-neg {{
            text-align: center;
            font-weight: bold;
            background: #fff;
            color: #ff0000;
        }}
        
        /* DIFF zero */
        td.diff-zero {{
            text-align: center;
            background: #fff;
            color: #000;
        }}
        
        .footer {{
            margin-top: 15px;
            text-align: center;
            font-size: 7pt;
            color: #666;
        }}
        
        .controls {{
            margin-bottom: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        
        .btn {{
            padding: 8px 16px;
            margin: 0 5px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 9pt;
            font-weight: bold;
        }}
        
        .btn-print {{
            background: #0066cc;
            color: white;
        }}
        
        .btn-print:hover {{
            background: #0052a3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="controls no-print">
            <button class="btn btn-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
        </div>
        
        <div class="header">
            DATE: {current_date} &nbsp;&nbsp;&nbsp;&nbsp; D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S
        </div>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 140px;"></th>
"""
        
        # Year headers
        for year in years:
            html += f'                    <th colspan="2" style="min-width: 60px;">{year}</th>\n'
        html += '                    <th colspan="2">2014 & Older</th>\n'
        html += '                    <th style="min-width: 45px;">TOTAL<br>UNITS</th>\n'
        html += '                    <th style="min-width: 45px;">Previous<br>(Date)</th>\n'
        html += '                    <th style="min-width: 35px;">DIFF</th>\n'
        html += '                </tr>\n'
        html += '            </thead>\n'
        html += '            <tbody>\n'
        
        # Group by category
        categories = df['Category'].unique()
        
        for category in categories:
            # Category header row
            total_cols = len(years) * 2 + 2 + 4
            html += f'                <tr>\n'
            html += f'                    <td colspan="{total_cols}" class="category">{category}</td>\n'
            html += f'                </tr>\n'
            
            # Vehicles
            cat_df = df[df['Category'] == category]
            
            for _, row in cat_df.iterrows():
                html += '                <tr>\n'
                html += f'                    <td class="vehicle">{row["Vehicle"]}</td>\n'
                
                # Each year: price and units
                for year in years:
                    price_col = f'{year}_price'
                    units_col = f'{year}_units'
                    
                    # Price
                    if price_col in df.columns:
                        price = row[price_col]
                        if pd.isna(price) or price == 0:
                            html += '                    <td class="empty">-</td>\n'
                        else:
                            html += f'                    <td class="price">${int(price):,}</td>\n'
                    else:
                        html += '                    <td class="empty">-</td>\n'
                    
                    # Units
                    if units_col in df.columns:
                        units = row[units_col]
                        if pd.isna(units) or units == 0:
                            html += '                    <td class="units">0</td>\n'
                        else:
                            html += f'                    <td class="units">{int(units)}</td>\n'
                    else:
                        html += '                    <td class="units">0</td>\n'
                
                # 2014 & Older
                price_2014 = row.get('2014_price', 0)
                units_2014 = row.get('2014_units', 0)
                
                if pd.isna(price_2014) or price_2014 == 0:
                    html += '                    <td class="empty">-</td>\n'
                else:
                    html += f'                    <td class="price">${int(price_2014):,}</td>\n'
                
                if pd.isna(units_2014) or units_2014 == 0:
                    html += '                    <td class="units">0</td>\n'
                else:
                    html += f'                    <td class="units">{int(units_2014)}</td>\n'
                
                # TOTAL UNITS
                total = row.get('TOTAL UNITS', 0)
                html += f'                    <td class="total">{int(total)}</td>\n'
                
                # Previous
                prev = row.get('Previous', 0)
                html += f'                    <td class="total">{int(prev)}</td>\n'
                
                # DIFF - color coded
                diff = row.get('DIFF', 0)
                if diff > 0:
                    html += f'                    <td class="diff-pos">{int(diff)}</td>\n'
                elif diff < 0:
                    html += f'                    <td class="diff-neg">{int(diff)}</td>\n'
                else:
                    html += f'                    <td class="diff-zero">{int(diff)}</td>\n'
                
                html += '                </tr>\n'
        
        html += """            </tbody>
        </table>
        
        <div class="footer">
            <p><strong>Ablink SGCarmart Scraper</strong> | Developed by Oneiros Indonesia</p>
            <p>Generated: """ + timestamp + """ | Data Source: www.sgcarmart.com</p>
        </div>
    </div>
    
    <script>
        // Auto-focus for immediate visibility
        window.onload = function() {
            document.body.style.opacity = '1';
        };
    </script>
</body>
</html>"""
        
        # Save silently
        if not output_file:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = "daily_reports"
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            output_file = f"{output_folder}/depreciation_report_{ts}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file
