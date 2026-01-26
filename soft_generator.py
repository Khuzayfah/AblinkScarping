"""
Ablink SGCarmart Scraper - Soft Natural Colors Generator
By Oneiros Indonesia

Soft, natural colors that are easy on the eyes
"""

import pandas as pd
from datetime import datetime
import os


class SoftGenerator:
    """Generate HTML reports with soft, natural colors"""
    
    # Soft natural colors - easy on the eyes
    CATEGORY_COLORS = {
        '10FT DIESEL': '#F5E6D3',      # Warm beige
        '14FT DIESEL': '#D3E4F5',      # Soft sky blue
        'VAN DIESEL (GOODS VAN)': '#D8F3DC',   # Mint green
        'VAN PETROL (GOODS VAN)': '#FFE5D9',   # Peach
    }
    
    def generate_report(self, df, output_file=None):
        """Generate soft-colored HTML report"""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"daily_reports/report_{timestamp}.html"
        
        # Extract years from column names
        year_cols = [col for col in df.columns if '_price' in col or '_units' in col]
        years = sorted(list(set([col.split('_')[0] for col in year_cols if col.split('_')[0].isdigit()])), reverse=True)
        
        current_date = datetime.now().strftime("%d %b %Y").upper()
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Depreciation Report - {current_date}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 10mm;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #fafaf8;
        }}
        
        .header {{
            text-align: center;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 2px;
            margin-bottom: 20px;
            padding: 20px;
            background: linear-gradient(135deg, #8B9DC3 0%, #6B7FA8 100%);
            color: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th {{
            background: linear-gradient(135deg, #8B9DC3 0%, #6B7FA8 100%);
            color: white;
            border: 1px solid #7A8DAF;
            padding: 12px 6px;
            text-align: center;
            font-weight: 700;
            font-size: 10px;
            letter-spacing: 0.5px;
        }}
        
        td {{
            border: 1px solid #E8E8E6;
            padding: 8px 6px;
            text-align: center;
            font-size: 11px;
        }}
        
        td:first-child {{
            text-align: left;
            padding-left: 12px;
            font-weight: 600;
            color: #2C3E50;
        }}
        
        /* Category row colors */
        td.category {{
            font-weight: 700;
            font-size: 11px;
            text-align: left;
            padding: 10px 12px;
            color: #34495E;
            border-top: 2px solid #95A5A6;
            border-bottom: 2px solid #95A5A6;
            letter-spacing: 0.5px;
        }}
        
        /* Price cells */
        td.price {{
            background: #F8F9FB;
            font-weight: 700;
            color: #2C5F8D;
            font-size: 11px;
        }}
        
        /* Units cells */
        td.units {{
            background: white;
            color: #5A6C7D;
            font-weight: 600;
        }}
        
        /* TOTAL UNITS column */
        td.total {{
            background: #FFF5E6;
            font-weight: 700;
            color: #D68910;
            font-size: 12px;
        }}
        
        /* Previous column */
        td.previous {{
            background: #F5F5F3;
            color: #6C757D;
            font-weight: 600;
        }}
        
        /* DIFF columns */
        td.diff-pos {{
            background: #DFF0D8;
            color: #2D7A3E;
            font-weight: 700;
            font-size: 12px;
        }}
        
        td.diff-neg {{
            background: #F8DEDC;
            color: #B94A48;
            font-weight: 700;
            font-size: 12px;
        }}
        
        td.diff-zero {{
            background: #F8F9FA;
            color: #95A5A6;
            font-weight: 600;
        }}
        
        /* Empty cells */
        td.empty {{
            background: #FAFAF9;
            color: #BDC3C7;
            font-style: italic;
        }}
        
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #5A6C7D;
            padding: 15px;
            background: linear-gradient(135deg, #F5F7FA 0%, #E8ECF1 100%);
            border-radius: 8px;
        }}
        
        .print-button {{
            background: linear-gradient(135deg, #8B9DC3 0%, #6B7FA8 100%);
            color: white;
            border: none;
            padding: 14px 35px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            border-radius: 30px;
            margin: 20px auto;
            display: block;
            box-shadow: 0 4px 8px rgba(0,0,0,0.12);
            transition: all 0.3s;
            letter-spacing: 0.5px;
        }}
        
        .print-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.18);
        }}
        
        @media print {{
            .print-button {{ display: none; }}
            body {{ padding: 0; background: white; }}
            .header, th, td.category, td.price, td.units, td.total, 
            td.previous, td.diff-pos, td.diff-neg, .footer {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}
        
        /* Legend */
        .legend {{
            display: flex;
            justify-content: center;
            gap: 25px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 20px;
            border-radius: 25px;
            background: white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }}
        
        .legend-color {{
            width: 35px;
            height: 22px;
            border-radius: 6px;
            border: 1px solid #DDD;
        }}
        
        .legend-text {{
            font-size: 11px;
            font-weight: 600;
            color: #34495E;
        }}
    </style>
</head>
<body>
    <button class="print-button" onclick="window.print()">🖨️ Print / Save as PDF</button>
    
    <div class="header">
        DATE: {current_date} &nbsp;&nbsp;•&nbsp;&nbsp; DEPRECIATION / UNITS
    </div>
    
    <div class="legend">
"""
        
        # Add legend for categories
        for category, color in self.CATEGORY_COLORS.items():
            html += f"""
        <div class="legend-item">
            <div class="legend-color" style="background: {color};"></div>
            <span class="legend-text">{category}</span>
        </div>
"""
        
        html += """
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 130px;">VEHICLE</th>
"""
        
        # Year headers (colspan 2 for price + units)
        for year in years:
            html += f'                <th colspan="2" style="width: 70px;">{year}</th>\n'
        
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
                bg_color = self.CATEGORY_COLORS.get(category, '#F5F5F3')
                colspan = 2 + (len(years) * 2) + 2 + 3
                html += f'            <tr><td colspan="{colspan}" class="category" style="background: {bg_color};">{category}</td></tr>\n'
            
            # Vehicle name
            vehicle = row['Vehicle']
            html += f'            <tr>\n                <td>{vehicle}</td>\n'
            
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
                        html += '                <td class="units empty">-</td>\n'
                    else:
                        html += f'                <td class="units">{int(units)}</td>\n'
            
            # 2014 & Older
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
                    html += '                <td class="units empty">-</td>\n'
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
        Soft Natural Colors - Easy on the Eyes
    </div>
    
    <button class="print-button" onclick="window.print()">🖨️ Print / Save as PDF</button>
</body>
</html>"""
        
        # Save HTML file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file
