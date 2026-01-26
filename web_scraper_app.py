"""
Ablink SGCarmart Scraper - Web Interface
By Oneiros Indonesia

Flask-based web application with one-click refresh button
Real-time progress tracking and automatic file generation
"""

from flask import Flask, render_template, jsonify, send_file
from depreciation_scraper import DepreciationScraper
from depreciation_html_generator import DepreciationHTMLGenerator
import pandas as pd
from datetime import datetime
import os
import threading

app = Flask(__name__)

# Global variables
scraping_status = {
    'is_scraping': False,
    'status': 'Ready',
    'last_update': None,
    'latest_file': None
}

@app.route('/')
def index():
    """Main page with refresh button"""
    
    # Get latest report
    report_folder = 'daily_reports'
    excel_files = []
    
    if os.path.exists(report_folder):
        excel_files = [f for f in os.listdir(report_folder) 
                      if f.startswith('depreciation') and f.endswith('.xlsx')]
    
    latest_data = None
    if excel_files:
        latest_file = max(excel_files, 
                         key=lambda x: os.path.getmtime(os.path.join(report_folder, x)))
        excel_path = os.path.join(report_folder, latest_file)
        
        try:
            latest_data = pd.read_excel(excel_path)
            scraping_status['latest_file'] = latest_file
            scraping_status['last_update'] = datetime.fromtimestamp(
                os.path.getmtime(excel_path)
            ).strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
    
    return render_template('index.html', 
                         data=latest_data, 
                         status=scraping_status)

@app.route('/scrape', methods=['POST'])
def scrape_data():
    """API endpoint to trigger scraping"""
    
    if scraping_status['is_scraping']:
        return jsonify({
            'status': 'error',
            'message': 'Scraping already in progress'
        })
    
    # Run scraping in background thread
    thread = threading.Thread(target=run_scraping)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Scraping started...'
    })

@app.route('/status')
def get_status():
    """Get current scraping status"""
    return jsonify(scraping_status)

@app.route('/download/<filename>')
def download_file(filename):
    """Download Excel or CSV file"""
    file_path = os.path.join('daily_reports', filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

def run_scraping():
    """Run scraping in background"""
    global scraping_status
    
    scraping_status['is_scraping'] = True
    scraping_status['status'] = 'Scraping in progress...'
    
    try:
        # Configure scraper
        config = {
            'headless': True,
            'timeout': 30,
            'delay': 3,
            'output_folder': 'daily_reports',
            'save_excel': True,
            'save_csv': True,
            'save_html': False  # We'll generate styled HTML separately
        }
        
        # Run scraper
        scraper = DepreciationScraper(config)
        result = scraper.run()
        
        if result and result.get('excel'):
            # Generate beautiful HTML
            excel_file = result['excel']
            df = pd.read_excel(excel_file)
            
            generator = DepreciationHTMLGenerator()
            html_file = generator.generate_report(df)
            
            scraping_status['status'] = 'Success!'
            scraping_status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            scraping_status['latest_file'] = os.path.basename(excel_file)
        else:
            scraping_status['status'] = 'Failed - No data found'
    
    except Exception as e:
        scraping_status['status'] = f'Error: {str(e)}'
    
    finally:
        scraping_status['is_scraping'] = False

# Create templates folder
def create_template():
    """Create HTML template"""
    
    template_dir = 'templates'
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ablink SGCarmart Scraper by Oneiros Indonesia</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 28px;
        }
        
        .header .subtitle {
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }
        
        .controls {
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 2px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .status-box {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #28a745;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.scraping {
            background: #ffc107;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-text {
            font-size: 14px;
            color: #666;
        }
        
        .status-text strong {
            color: #333;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: #28a745;
            color: white;
        }
        
        .btn-primary:hover {
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
        }
        
        .btn-primary:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-secondary {
            background: #007bff;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #0056b3;
        }
        
        .btn-download {
            background: #17a2b8;
            color: white;
        }
        
        .btn-download:hover {
            background: #138496;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #28a745;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .content {
            padding: 30px;
        }
        
        .info-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .info-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .info-card .label {
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        
        .info-card .value {
            font-size: 28px;
            font-weight: bold;
        }
        
        .table-wrapper {
            overflow-x: auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        
        th {
            background: #217346;
            color: white;
            padding: 12px 10px;
            text-align: center;
            font-weight: 600;
            border: 1px solid #1a5c37;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: center;
        }
        
        tbody tr:hover {
            background: #f1f3f5;
        }
        
        .no-data {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .footer {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 13px;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        
        .alert.show {
            display: block;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <h1>🚗 Ablink SGCarmart Scraper</h1>
                <p class="subtitle">By Oneiros Indonesia | Real-time Depreciation Data</p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 12px; opacity: 0.9;">Last Update</div>
                <div style="font-size: 16px; font-weight: bold;" id="lastUpdate">
                    {{ status.last_update or 'Never' }}
                </div>
            </div>
        </div>
        
        <!-- Controls -->
        <div class="controls">
            <div class="status-box">
                <div class="status-indicator" id="statusIndicator"></div>
                <div class="status-text">
                    Status: <strong id="statusText">{{ status.status }}</strong>
                </div>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-primary" id="refreshBtn" onclick="startScraping()">
                    🔄 Refresh Data
                </button>
                {% if status.latest_file %}
                <button class="btn btn-download" onclick="downloadExcel()">
                    📊 Download Excel
                </button>
                <button class="btn btn-secondary" onclick="window.print()">
                    🖨️ Print / Save PDF
                </button>
                {% endif %}
            </div>
        </div>
        
        <!-- Alert -->
        <div id="alert" class="alert"></div>
        
        <!-- Content -->
        <div class="content">
            {% if data is not none %}
            <!-- Info Cards -->
            <div class="info-cards">
                <div class="info-card">
                    <div class="label">Total Vehicles</div>
                    <div class="value">{{ data|length }}</div>
                </div>
                <div class="info-card">
                    <div class="label">Categories</div>
                    <div class="value">{{ data['Category'].nunique() if 'Category' in data.columns else 0 }}</div>
                </div>
                <div class="info-card">
                    <div class="label">Total Units</div>
                    <div class="value">{{ data['TOTAL UNITS'].sum() if 'TOTAL UNITS' in data.columns else 0 }}</div>
                </div>
                <div class="info-card">
                    <div class="label">Data Freshness</div>
                    <div class="value" style="font-size: 18px;">✓ Latest</div>
                </div>
            </div>
            
            <!-- Table -->
            <div class="table-wrapper">
                {{ data.to_html(index=False, classes='data-table', border=0)|safe }}
            </div>
            {% else %}
            <div class="no-data">
                <h3>No data available</h3>
                <p>Click "Refresh Data" to scrape latest data from SGCarmart</p>
            </div>
            {% endif %}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p><strong>Ablink SGCarmart Scraper</strong> | Developed by Oneiros Indonesia</p>
            <p>© 2026 Oneiros Indonesia | Powered by Python & Flask</p>
        </div>
    </div>
    
    <script>
        let checkInterval;
        
        function startScraping() {
            const btn = document.getElementById('refreshBtn');
            const statusText = document.getElementById('statusText');
            const statusIndicator = document.getElementById('statusIndicator');
            
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Scraping...';
            statusIndicator.classList.add('scraping');
            
            fetch('/scrape', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    showAlert(data.message, 'info');
                    
                    // Start checking status
                    checkInterval = setInterval(checkStatus, 2000);
                })
                .catch(error => {
                    showAlert('Error starting scraper: ' + error, 'error');
                    btn.disabled = false;
                    btn.innerHTML = '🔄 Refresh Data';
                    statusIndicator.classList.remove('scraping');
                });
        }
        
        function checkStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('statusText').textContent = data.status;
                    
                    if (!data.is_scraping) {
                        clearInterval(checkInterval);
                        
                        const btn = document.getElementById('refreshBtn');
                        btn.disabled = false;
                        btn.innerHTML = '🔄 Refresh Data';
                        
                        const statusIndicator = document.getElementById('statusIndicator');
                        statusIndicator.classList.remove('scraping');
                        
                        if (data.status.includes('Success')) {
                            showAlert('Data refreshed successfully! Reloading page...', 'success');
                            
                            // Reload page after 2 seconds
                            setTimeout(() => {
                                window.location.reload();
                            }, 2000);
                        } else if (data.status.includes('Error') || data.status.includes('Failed')) {
                            showAlert('Scraping failed. Please try again.', 'error');
                        }
                        
                        if (data.last_update) {
                            document.getElementById('lastUpdate').textContent = data.last_update;
                        }
                    }
                });
        }
        
        function downloadExcel() {
            const filename = '{{ status.latest_file }}';
            window.location.href = '/download/' + filename;
        }
        
        function showAlert(message, type) {
            const alert = document.getElementById('alert');
            alert.className = 'alert alert-' + type + ' show';
            alert.textContent = message;
            
            setTimeout(() => {
                alert.classList.remove('show');
            }, 5000);
        }
        
        // Auto-check status on page load
        window.addEventListener('load', function() {
            checkStatus();
        });
    </script>
</body>
</html>"""
    
    template_path = os.path.join(template_dir, 'index.html')
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[OK] Template created: {template_path}")

if __name__ == '__main__':
    print("="*70)
    print("Ablink SGCarmart Scraper - Web Interface")
    print("By Oneiros Indonesia")
    print("="*70)
    
    # Create template
    create_template()
    
    print("\n[INFO] Web server starting...")
    print("[INFO] Open browser and go to: http://localhost:5000")
    print("[INFO] Click 'Refresh Data' button to scrape latest data")
    print("\nPress Ctrl+C to stop server\n")
    print("="*70)
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
