"""
Ablink SGCarmart Scraper - HTML Report Generator
By Oneiros Indonesia

Generates professional Excel-style HTML reports with color-coded values
CSS styling mimics Excel/Google Sheets appearance
Optimized for print-to-PDF output
"""

import pandas as pd
from datetime import datetime
import os


class DepreciationHTMLGenerator:
    """Generate Excel-like HTML reports for depreciation data"""
    
    def __init__(self):
        self.html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Depreciation Report - {date}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Calibri', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        
        .header .subtitle {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .stats-bar {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1px;
            background: #e0e0e0;
            border-bottom: 2px solid #1e3c72;
        }}
        
        .stat-item {{
            background: white;
            padding: 15px 20px;
            text-align: center;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1e3c72;
        }}
        
        .content {{
            padding: 0;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        
        thead {{
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        th {{
            background: #217346;
            color: white;
            padding: 12px 8px;
            text-align: center;
            font-weight: 600;
            border: 1px solid #1a5c37;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        th.vehicle-col {{
            text-align: left;
            min-width: 180px;
            background: #2c8e5f;
        }}
        
        th.category-col {{
            text-align: left;
            min-width: 150px;
            background: #2c8e5f;
        }}
        
        th.year-col {{
            min-width: 70px;
            background: #1e5d3f;
        }}
        
        th.total-col {{
            background: #d35400;
            min-width: 90px;
        }}
        
        th.diff-col {{
            background: #c0392b;
            min-width: 60px;
        }}
        
        td {{
            padding: 10px 8px;
            border: 1px solid #ddd;
            text-align: center;
        }}
        
        td.vehicle-cell {{
            text-align: left;
            font-weight: 500;
            color: #2c3e50;
            background: #f8f9fa;
        }}
        
        td.category-cell {{
            text-align: left;
            font-size: 10px;
            color: #7f8c8d;
            font-weight: 600;
            background: #ecf0f1;
        }}
        
        td.value-cell {{
            font-family: 'Consolas', 'Monaco', monospace;
            font-weight: 500;
        }}
        
        td.zero {{
            color: #bdc3c7;
            background: #fafafa;
        }}
        
        td.positive {{
            background: #d5f4e6;
            color: #27ae60;
            font-weight: 600;
        }}
        
        td.negative {{
            background: #fadbd8;
            color: #e74c3c;
            font-weight: 600;
        }}
        
        td.total-cell {{
            background: #fff3cd;
            font-weight: 700;
            color: #856404;
        }}
        
        tbody tr:hover {{
            background: #e8f4fd;
        }}
        
        tbody tr:nth-child(even) td:not(.vehicle-cell):not(.category-cell) {{
            background: #f9f9f9;
        }}
        
        .category-header {{
            background: #34495e !important;
            color: white !important;
            font-weight: bold;
            font-size: 13px;
            padding: 12px 8px;
            text-align: left;
            border: none;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 12px;
        }}
        
        .footer p {{
            margin: 5px 0;
        }}
        
        .controls {{
            padding: 20px;
            background: #ecf0f1;
            text-align: center;
            border-top: 1px solid #ddd;
        }}
        
        .btn {{
            display: inline-block;
            padding: 12px 24px;
            margin: 5px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.3s;
        }}
        
        .btn:hover {{
            background: #2980b9;
        }}
        
        .btn-success {{
            background: #27ae60;
        }}
        
        .btn-success:hover {{
            background: #229954;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .controls {{
                display: none;
            }}
            
            table {{
                font-size: 10px;
            }}
            
            th, td {{
                padding: 6px 4px;
            }}
        }}
        
        @media (max-width: 768px) {{
            .stats-bar {{
                grid-template-columns: 1fr 1fr;
            }}
            
            table {{
                font-size: 10px;
            }}
            
            th, td {{
                padding: 6px 4px;
            }}
        }}
        
        .legend {{
            padding: 15px 20px;
            background: #f8f9fa;
            border-top: 1px solid #ddd;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 12px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 30px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🚗 Vehicle Depreciation Report</h1>
            <p class="subtitle">SGCarmart - Depreciation by Year & Category</p>
        </div>
        
        <!-- Statistics Bar -->
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-label">Report Date</div>
                <div class="stat-value">{report_date}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Total Vehicles</div>
                <div class="stat-value">{total_vehicles}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Total Units</div>
                <div class="stat-value">{total_units}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Categories</div>
                <div class="stat-value">{total_categories}</div>
            </div>
        </div>
        
        <!-- Table -->
        <div class="content">
            <div class="table-wrapper">
                {table_html}
            </div>
        </div>
        
        <!-- Legend -->
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #d5f4e6;"></div>
                <span>Positive Diff</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #fadbd8;"></div>
                <span>Negative Diff</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #fff3cd;"></div>
                <span>Total Units</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #fafafa;"></div>
                <span>No Data (0)</span>
            </div>
        </div>
        
        <!-- Controls -->
        <div class="controls">
            <button onclick="window.print()" class="btn btn-success">🖨️ Print / Save as PDF</button>
            <button onclick="exportToExcel()" class="btn">📊 Download Excel</button>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p><strong>Ablink SGCarmart Scraper</strong> | Developed by Oneiros Indonesia</p>
            <p>Generated: {timestamp}</p>
            <p>Data Source: www.sgcarmart.com</p>
        </div>
    </div>
    
    <script>
        function exportToExcel() {{
            alert('Excel file is already available in the daily_reports folder!');
        }}
        
        // Format numbers with commas
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Depreciation report loaded successfully');
        }});
    </script>
</body>
</html>
"""
    
    def generate_report(self, df, output_file=None):
        """
        Generate beautiful HTML report from DataFrame
        
        Args:
            df: pandas DataFrame with depreciation data
            output_file: Output HTML file path
        """
        
        # Prepare statistics
        report_date = datetime.now().strftime("%d %B %Y")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_vehicles = len(df)
        
        # Calculate statistics
        if 'TOTAL UNITS' in df.columns:
            total_units = df['TOTAL UNITS'].sum()
        else:
            total_units = 0
        
        if 'Category' in df.columns:
            total_categories = df['Category'].nunique()
        else:
            total_categories = 0
        
        # Generate table HTML
        table_html = self._generate_table_html(df)
        
        # Fill template
        html_content = self.html_template.format(
            date=report_date,
            report_date=datetime.now().strftime("%d/%m/%Y"),
            total_vehicles=total_vehicles,
            total_units=f"{total_units:,}",
            total_categories=total_categories,
            table_html=table_html,
            timestamp=timestamp
        )
        
        # Save file
        if output_file is None:
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"daily_reports/depreciation_styled_{timestamp_file}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[OK] Styled HTML report saved: {output_file}")
        return output_file
    
    def _generate_table_html(self, df):
        """Generate Excel-like table HTML"""
        
        html = '<table>\n'
        
        # Header
        html += '<thead>\n<tr>\n'
        
        for col in df.columns:
            if col in ['Vehicle']:
                css_class = 'vehicle-col'
            elif col in ['Category']:
                css_class = 'category-col'
            elif col in ['TOTAL UNITS', 'Previous']:
                css_class = 'total-col'
            elif col in ['DIFF']:
                css_class = 'diff-col'
            elif col.isdigit() or 'Older' in col:
                css_class = 'year-col'
            else:
                css_class = ''
            
            html += f'<th class="{css_class}">{col}</th>\n'
        
        html += '</tr>\n</thead>\n'
        
        # Body
        html += '<tbody>\n'
        
        current_category = None
        
        for idx, row in df.iterrows():
            # Check if category changed (add category header row)
            if 'Category' in df.columns:
                if row['Category'] != current_category:
                    current_category = row['Category']
                    html += f'<tr><td colspan="{len(df.columns)}" class="category-header">{current_category}</td></tr>\n'
            
            html += '<tr>\n'
            
            for col in df.columns:
                value = row[col]
                
                # Determine cell class
                if col == 'Vehicle':
                    cell_class = 'vehicle-cell'
                    display_value = value
                elif col == 'Category':
                    cell_class = 'category-cell'
                    display_value = value
                elif col == 'DIFF':
                    if isinstance(value, (int, float)):
                        if value > 0:
                            cell_class = 'value-cell positive'
                            display_value = f'+{int(value)}'
                        elif value < 0:
                            cell_class = 'value-cell negative'
                            display_value = str(int(value))
                        else:
                            cell_class = 'value-cell zero'
                            display_value = '0'
                    else:
                        cell_class = 'value-cell'
                        display_value = value
                elif col in ['TOTAL UNITS', 'Previous']:
                    cell_class = 'value-cell total-cell'
                    if isinstance(value, (int, float)):
                        display_value = f"{int(value):,}"
                    else:
                        display_value = value
                else:
                    # Year columns
                    if isinstance(value, (int, float)):
                        if value == 0:
                            cell_class = 'value-cell zero'
                            display_value = '-'
                        else:
                            cell_class = 'value-cell'
                            display_value = f"${int(value):,}"
                    else:
                        cell_class = 'value-cell'
                        display_value = value
                
                html += f'<td class="{cell_class}">{display_value}</td>\n'
            
            html += '</tr>\n'
        
        html += '</tbody>\n'
        html += '</table>\n'
        
        return html


def main():
    """Generate styled HTML report from latest Excel file"""
    
    print("="*70)
    print("Depreciation Styled HTML Generator")
    print("="*70)
    
    # Find latest Excel file
    report_folder = "daily_reports"
    excel_files = [f for f in os.listdir(report_folder) if f.startswith('depreciation') and f.endswith('.xlsx')]
    
    if not excel_files:
        print("\n[ERROR] No depreciation Excel files found!")
        return
    
    latest_file = max(excel_files, key=lambda x: os.path.getmtime(os.path.join(report_folder, x)))
    excel_path = os.path.join(report_folder, latest_file)
    
    print(f"\n[INFO] Using file: {latest_file}")
    
    # Read Excel
    df = pd.read_excel(excel_path)
    
    print(f"[INFO] Loaded {len(df)} rows")
    
    # Generate HTML
    generator = DepreciationHTMLGenerator()
    html_file = generator.generate_report(df)
    
    # Open in browser
    try:
        import webbrowser
        abs_path = os.path.abspath(html_file)
        print(f"\n[INFO] Opening report in browser...")
        webbrowser.open('file://' + abs_path)
        print(f"[OK] Report opened!")
    except Exception as e:
        print(f"[WARNING] Could not auto-open: {e}")
    
    print("\n" + "="*70)
    print("✓ Styled HTML Report Generated!")
    print("="*70)
    print(f"\nFile: {html_file}")
    print("\nFeatures:")
    print("  ✓ Excel-like spreadsheet styling")
    print("  ✓ Color-coded diff values")
    print("  ✓ Sticky header")
    print("  ✓ Print-optimized")
    print("  ✓ Mobile responsive")
    print("\nTo save as PDF:")
    print("  1. Click 'Print / Save as PDF' button")
    print("  2. Or press Ctrl+P")
    print("="*70)


if __name__ == "__main__":
    main()
