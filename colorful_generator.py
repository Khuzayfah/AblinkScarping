"""
Ablink SGCarmart Scraper - Colorful Report Generator
By Oneiros Indonesia

Colorful HTML report with:
- Each category has different background color
- Easy to distinguish data
- Print-friendly
"""

import pandas as pd
from datetime import datetime
import os


class ColorfulGenerator:
    """Generate colorful HTML reports with color-coded categories"""
    
    # Category colors - bright and distinct
    CATEGORY_COLORS = {
        '10FT DIESEL': '#FFE6E6',      # Light red
        '14FT DIESEL': '#E6F3FF',      # Light blue
        'VAN DIESEL (GOODS VAN)': '#E6FFE6',   # Light green
        'VAN PETROL (GOODS VAN)': '#FFF4E6',   # Light orange
    }
    
    def generate_report(self, df, output_file=None):
        """Generate colorful HTML report"""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"daily_reports/colorful_report_{timestamp}.html"
        
        # Extract years from column names
        year_cols = [col for col in df.columns if '_price' in col or '_units' in col]
        years = sorted(list(set([col.split('_')[0] for col in year_cols if col.split('_')[0].isdigit()])), reverse=True)
        
        current_date = datetime.now().strftime("%d %b").upper()
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Depreciation Report - Colorful</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 10mm;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: white;
        }}
        
        .header {{
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 3px;
            margin-bottom: 15px;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: 1px solid #5568d3;
            padding: 8px 4px;
            text-align: center;
            font-weight: bold;
            font-size: 8px;
        }}
        
        td {{
            border: 1px solid #ddd;
            padding: 6px 4px;
            text-align: center;
        }}
        
        td:first-child {{
            text-align: left;
            padding-left: 8px;
            font-weight: 500;
        }}
        
        /* Category row colors */
        td.category {{
            font-weight: bold;
            font-size: 9px;
            text-align: left;
            padding: 8px;
            color: #333;
            border-top: 2px solid #888;
            border-bottom: 2px solid #888;
        }}
        
        /* Price cells - light background */
        td.price {{
            background: #f8f9ff;
            font-weight: 600;
            color: #2c5aa0;
        }}
        
        /* Units cells - white background */
        td.units {{
            background: white;
            color: #666;
        }}
        
        /* TOTAL UNITS column */
        td.total {{
            background: #fff4e6;
            font-weight: bold;
            color: #e67e22;
            font-size: 10px;
        }}
        
        /* Previous column */
        td.previous {{
            background: #f0f0f0;
            color: #666;
        }}
        
        /* DIFF columns */
        td.diff-pos {{
            background: #d4edda;
            color: #155724;
            font-weight: bold;
            font-size: 10px;
        }}
        
        td.diff-neg {{
            background: #f8d7da;
            color: #721c24;
            font-weight: bold;
            font-size: 10px;
        }}
        
        td.diff-zero {{
            background: #f8f9fa;
            color: #6c757d;
        }}
        
        /* Empty cells */
        td.empty {{
            background: #fafafa;
            color: #ccc;
        }}
        
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 11px;
            color: #666;
            padding: 15px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 8px;
        }}
        
        .print-button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 14px;
            cursor: pointer;
            border-radius: 25px;
            margin: 20px auto;
            display: block;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }}
        
        .print-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.3);
        }}
        
        @media print {{
            .print-button {{ display: none; }}
            body {{ padding: 0; }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            th {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            td.category, td.price, td.units, td.total, td.previous, 
            td.diff-pos, td.diff-neg, .footer {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}
        
        /* Legend */
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 15px;
            border-radius: 20px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .legend-color {{
            width: 30px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <button class="print-button" onclick="window.print()">🖨️ Print / Save as PDF</button>
    
    <div class="header">
        DATE: {current_date} &nbsp;&nbsp;&nbsp; D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S
    </div>
    
    <div class="legend">
"""
        
        # Add legend for categories
        for category, color in self.CATEGORY_COLORS.items():
            html += f"""
        <div class="legend-item">
            <div class="legend-color" style="background: {color};"></div>
            <span style="font-size: 10px; font-weight: 500;">{category}</span>
        </div>
"""
        
        html += """
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 120px;">VEHICLE</th>
"""
        
        # Year headers (colspan 2 for price + units)
        for year in years:
            html += f'                <th colspan="2" style="width: 65px;">{year}</th>\n'
        
        html += """                <th colspan="2">2014 & Older</th>
                <th>TOTAL<br>UNITS</th>
                <th>Previous<br>(Date)</th>
                <th>DIFF</th>
            </tr>
        </thead>
        <tbody>
"""
        
        # Group by category
        current_category = None
        
        for idx, row in df.iterrows():
            category = row['Category']
            
            # Category header row
            if category != current_category:
                current_category = category
                bg_color = self.CATEGORY_COLORS.get(category, '#f0f0f0')
                colspan = 2 + (len(years) * 2) + 2 + 3  # vehicle + years + 2014 + totals
                html += f'            <tr><td colspan="{colspan}" class="category" style="background: {bg_color};">{category}</td></tr>\n'
            
            # Vehicle name
            vehicle = row['Vehicle']
            html += f'            <tr>\n                <td style="font-weight: 500;">{vehicle}</td>\n'
            
            # Price and units for each year
            for year in years:
                price_col = f'{year}_price'
                units_col = f'{year}_units'
                
                if price_col in df.columns and units_col in df.columns:
                    price = row[price_col]
                    units = row[units_col]
                    
                    # Price cell
                    if pd.isna(price) or price == 0:
                        html += '                <td class="price empty">-</td>\n'
                    else:
                        html += f'                <td class="price">${int(price):,}</td>\n'
                    
                    # Units cell
                    if pd.isna(units) or units == 0:
                        html += '                <td class="units empty">0</td>\n'
                    else:
                        html += f'                <td class="units">{int(units)}</td>\n'
            
            # 2014 & Older (price + units)
            old_price_col = '2014_price'
            old_units_col = '2014_units'
            
            if old_price_col in df.columns:
                old_price = row[old_price_col]
                if pd.isna(old_price) or old_price == 0:
                    html += '                <td class="price empty">-</td>\n'
                else:
                    html += f'                <td class="price">${int(old_price):,}</td>\n'
            
            if old_units_col in df.columns:
                old_units = row[old_units_col]
                if pd.isna(old_units) or old_units == 0:
                    html += '                <td class="units empty">0</td>\n'
                else:
                    html += f'                <td class="units">{int(old_units)}</td>\n'
            
            # TOTAL UNITS
            total = row['TOTAL UNITS']
            html += f'                <td class="total">{int(total)}</td>\n'
            
            # Previous
            previous = row['Previous']
            html += f'                <td class="previous">{int(previous)}</td>\n'
            
            # DIFF
            diff = row['DIFF']
            if diff > 0:
                html += f'                <td class="diff-pos">+{int(diff)}</td>\n'
            elif diff < 0:
                html += f'                <td class="diff-neg">{int(diff)}</td>\n'
            else:
                html += f'                <td class="diff-zero">{int(diff)}</td>\n'
            
            html += '            </tr>\n'
        
        html += """        </tbody>
    </table>
    
    <div class="footer">
        <strong>Ablink SGCarmart Scraper</strong> | Developed by <strong>Oneiros Indonesia</strong><br>
        Colorful Report - Easy to Read and Distinguish
    </div>
    
    <button class="print-button" onclick="window.print()">🖨️ Print / Save as PDF</button>
</body>
</html>"""
        
        # Save HTML file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file
