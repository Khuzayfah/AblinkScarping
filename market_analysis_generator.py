"""
Ablink SGCarmart Scraper - Market Analysis Report Generator
By Oneiros Indonesia

Generates HTML reports with:
- Depreciation chart (Lowest + Average)
- Units sold chart (60 days)
- Price comparison
"""

import pandas as pd
from datetime import datetime
import os


class MarketAnalysisGenerator:
    """Generate market analysis HTML reports"""
    
    # Category colors - soft natural
    CATEGORY_COLORS = {
        '10FT DIESEL': '#E8F4E8',
        '14FT DIESEL': '#E8F0F8',
        'VAN DIESEL (GOODS VAN)': '#FFF8E8',
        'VAN PETROL (GOODS VAN)': '#F8E8F0',
    }
    
    def generate_report(self, data, output_file=None):
        """Generate complete market analysis report"""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"daily_reports/market_analysis_{timestamp}.html"
        
        current_date = datetime.now().strftime("%d %b").upper()
        
        # Get all years
        all_years = set()
        for vehicle in data.get('vehicles', []):
            all_years.update(vehicle.get('years', {}).keys())
        years = sorted(all_years, reverse=True)[:12]  # Max 12 years
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Market Analysis Report - {current_date}</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 5mm;
        }}
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 15px;
            background: #fafafa;
            font-size: 10px;
        }}
        
        .header {{
            text-align: center;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 3px;
            margin-bottom: 15px;
            padding: 15px;
            background: linear-gradient(135deg, #4a7c59 0%, #6b9b7a 100%);
            color: white;
            border-radius: 8px;
        }}
        
        .section-title {{
            text-align: center;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 2px;
            margin: 20px 0 10px 0;
            padding: 10px;
            background: #4a7c59;
            color: white;
            border-radius: 5px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9px;
            margin-bottom: 20px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        th {{
            background: #4a7c59;
            color: white;
            border: 1px solid #3d6b4a;
            padding: 6px 3px;
            text-align: center;
            font-weight: 700;
            font-size: 8px;
        }}
        
        th.year-header {{
            background: #5a8c69;
        }}
        
        th.sub-header {{
            background: #6b9b7a;
            font-size: 7px;
        }}
        
        td {{
            border: 1px solid #ddd;
            padding: 4px 3px;
            text-align: center;
            font-size: 9px;
        }}
        
        td:first-child {{
            text-align: left;
            padding-left: 6px;
            font-weight: 600;
            color: #333;
        }}
        
        .category-row {{
            font-weight: 700;
            font-size: 9px;
            text-align: left !important;
            padding: 6px !important;
            color: #333;
            border-top: 2px solid #4a7c59;
        }}
        
        .lowest {{
            color: #2e7d32;
            font-weight: 700;
        }}
        
        .average {{
            color: #1565c0;
            font-weight: 600;
        }}
        
        .units {{
            color: #666;
        }}
        
        .total-col {{
            background: #fff8e1;
            font-weight: 700;
            color: #e65100;
        }}
        
        .diff-pos {{
            background: #e8f5e9;
            color: #2e7d32;
            font-weight: 700;
        }}
        
        .diff-neg {{
            background: #ffebee;
            color: #c62828;
            font-weight: 700;
        }}
        
        .empty {{
            color: #bbb;
        }}
        
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 10px;
            color: #666;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
        }}
        
        .print-btn {{
            background: #4a7c59;
            color: white;
            border: none;
            padding: 12px 30px;
            font-size: 14px;
            cursor: pointer;
            border-radius: 25px;
            margin: 15px auto;
            display: block;
        }}
        
        .print-btn:hover {{
            background: #3d6b4a;
        }}
        
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; background: white; }}
            .section-title, th, .category-row, .total-col, .diff-pos, .diff-neg {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
    
    <div class="header">
        DATE: {current_date} &nbsp;&nbsp;&nbsp; D E P R E C I A T I O N &nbsp; / &nbsp; U N I T S
    </div>
    
    <!-- DEPRECIATION TABLE -->
    <table>
        <thead>
            <tr>
                <th rowspan="2" style="width: 120px;">Vehicle</th>
"""
        
        # Year headers with Lowest + Average
        for year in years:
            html += f'                <th colspan="2" class="year-header">{year}</th>\n'
        
        html += """                <th rowspan="2">TOTAL<br>UNITS</th>
                <th rowspan="2">Previous<br>(Date)</th>
                <th rowspan="2">DIFF</th>
            </tr>
            <tr>
"""
        
        # Sub-headers (Lowest | Average)
        for year in years:
            html += '                <th class="sub-header">Lowest</th>\n'
            html += '                <th class="sub-header">Average</th>\n'
        
        html += """            </tr>
        </thead>
        <tbody>
"""
        
        # Data rows
        current_category = None
        for vehicle in data.get('vehicles', []):
            category = vehicle.get('category', '')
            
            # Category header
            if category != current_category:
                current_category = category
                bg_color = self.CATEGORY_COLORS.get(category, '#f5f5f5')
                colspan = 3 + (len(years) * 2)
                html += f'            <tr><td colspan="{colspan}" class="category-row" style="background: {bg_color};">{category}</td></tr>\n'
            
            # Vehicle row
            html += f'            <tr>\n'
            html += f'                <td>{vehicle["vehicle"]}</td>\n'
            
            # Year data
            for year in years:
                year_data = vehicle.get('years', {}).get(year, {})
                lowest = year_data.get('lowest', 0)
                average = year_data.get('average', 0)
                
                if lowest > 0:
                    html += f'                <td class="lowest">${lowest:,}</td>\n'
                else:
                    html += '                <td class="empty">-</td>\n'
                
                if average > 0:
                    html += f'                <td class="average">${average:,}</td>\n'
                else:
                    html += '                <td class="empty">-</td>\n'
            
            # Totals
            total_units = vehicle.get('total_units', 0)
            previous = vehicle.get('previous', 0)
            diff = vehicle.get('diff', 0)
            
            html += f'                <td class="total-col">{total_units}</td>\n'
            html += f'                <td>{previous}</td>\n'
            
            if diff > 0:
                html += f'                <td class="diff-pos">+{diff}</td>\n'
            elif diff < 0:
                html += f'                <td class="diff-neg">{diff}</td>\n'
            else:
                html += f'                <td>{diff}</td>\n'
            
            html += '            </tr>\n'
        
        html += """        </tbody>
    </table>
    
    <!-- UNITS SOLD TABLE -->
    <div class="section-title">
        NUMBER OF UNITS SOLD LAST 60 DAYS
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 120px;">Vehicle</th>
"""
        
        # Year headers for units
        for year in years:
            html += f'                <th>{year}</th>\n'
        
        html += """                <th>TOTAL<br>UNITS</th>
                <th>Last 120<br>Days</th>
            </tr>
        </thead>
        <tbody>
"""
        
        # Units data rows
        current_category = None
        for vehicle in data.get('vehicles', []):
            category = vehicle.get('category', '')
            
            # Category header
            if category != current_category:
                current_category = category
                bg_color = self.CATEGORY_COLORS.get(category, '#f5f5f5')
                colspan = 3 + len(years)
                html += f'            <tr><td colspan="{colspan}" class="category-row" style="background: {bg_color};">{category}</td></tr>\n'
            
            # Vehicle row
            html += f'            <tr>\n'
            html += f'                <td>{vehicle["vehicle"]}</td>\n'
            
            # Year units
            for year in years:
                year_data = vehicle.get('years', {}).get(year, {})
                units = year_data.get('units', 0)
                
                if units > 0:
                    html += f'                <td class="units">{units}</td>\n'
                else:
                    html += '                <td class="empty">0</td>\n'
            
            # Totals
            total_units = vehicle.get('total_units', 0)
            previous = vehicle.get('previous', 0)
            
            html += f'                <td class="total-col">{total_units}</td>\n'
            html += f'                <td>{previous}</td>\n'
            html += '            </tr>\n'
        
        html += """        </tbody>
    </table>
    
    <div class="footer">
        <strong>Ablink SGCarmart Scraper</strong> | Developed by <strong>Oneiros Indonesia</strong><br>
        Market Analysis Report - Generated on """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
    </div>
    
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
</body>
</html>"""
        
        # Save file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file
