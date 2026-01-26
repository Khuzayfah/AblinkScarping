"""
Ablink SGCarmart Scraper - n8n API Integration
By Oneiros Indonesia

RESTful API endpoints for workflow automation
Compatible with n8n, Zapier, and custom integrations
"""

from flask import Flask, request, jsonify
from depreciation_scraper import DepreciationScraper
from depreciation_html_generator import DepreciationHTMLGenerator
import pandas as pd
from datetime import datetime
import os
import json

app = Flask(__name__)

# API Key for security (change this!)
API_KEY = "your-secret-api-key-change-this"

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """
    API endpoint for n8n to trigger scraping
    
    POST /api/scrape
    Headers:
        X-API-Key: your-secret-api-key
    Body (optional):
        {
            "headless": true,
            "timeout": 30,
            "format": ["excel", "csv", "html"]
        }
    
    Returns:
        {
            "status": "success",
            "message": "Scraping completed",
            "files": {
                "excel": "path/to/file.xlsx",
                "csv": "path/to/file.csv",
                "html": "path/to/file.html"
            },
            "data_summary": {
                "total_vehicles": 21,
                "categories": 4,
                "total_units": 1006
            },
            "timestamp": "2026-01-25T10:30:00"
        }
    """
    
    # Check API key
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({
            'status': 'error',
            'message': 'Invalid API key'
        }), 401
    
    # Get config from request body
    config_data = request.json if request.json else {}
    
    # Scraper config
    config = {
        'headless': config_data.get('headless', True),
        'timeout': config_data.get('timeout', 30),
        'delay': config_data.get('delay', 3),
        'output_folder': 'daily_reports',
        'save_excel': 'excel' in config_data.get('format', ['excel', 'csv', 'html']),
        'save_csv': 'csv' in config_data.get('format', ['excel', 'csv', 'html']),
        'save_html': False  # We'll generate styled HTML separately
    }
    
    try:
        # Run scraper
        scraper = DepreciationScraper(config)
        result = scraper.run()
        
        if not result or not result.get('excel'):
            return jsonify({
                'status': 'error',
                'message': 'Scraping failed - No data found',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Read scraped data
        df = pd.read_excel(result['excel'])
        
        # Generate styled HTML
        html_file = None
        if 'html' in config_data.get('format', ['excel', 'csv', 'html']):
            generator = DepreciationHTMLGenerator()
            html_file = generator.generate_report(df)
        
        # Calculate summary
        data_summary = {
            'total_vehicles': len(df),
            'categories': df['Category'].nunique() if 'Category' in df.columns else 0,
            'total_units': int(df['TOTAL UNITS'].sum()) if 'TOTAL UNITS' in df.columns else 0
        }
        
        # Prepare file paths
        files = {
            'excel': os.path.abspath(result['excel']) if result.get('excel') else None,
            'csv': os.path.abspath(result['csv']) if result.get('csv') else None,
            'html': os.path.abspath(html_file) if html_file else None
        }
        
        # Remove None values
        files = {k: v for k, v in files.items() if v}
        
        return jsonify({
            'status': 'success',
            'message': 'Scraping completed successfully',
            'files': files,
            'data_summary': data_summary,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """
    Check API status
    GET /api/status
    """
    return jsonify({
        'status': 'online',
        'service': 'SGCarmart Scraper API',
        'version': '1.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/latest', methods=['GET'])
def api_latest():
    """
    Get latest scraped data
    GET /api/latest?format=json
    
    Returns latest data file info
    """
    api_key = request.headers.get('X-API-Key')
    if api_key != API_KEY:
        return jsonify({
            'status': 'error',
            'message': 'Invalid API key'
        }), 401
    
    report_folder = 'daily_reports'
    
    if not os.path.exists(report_folder):
        return jsonify({
            'status': 'error',
            'message': 'No reports found'
        }), 404
    
    # Find latest Excel file
    excel_files = [f for f in os.listdir(report_folder) 
                   if f.startswith('depreciation') and f.endswith('.xlsx')]
    
    if not excel_files:
        return jsonify({
            'status': 'error',
            'message': 'No data files found'
        }), 404
    
    latest_file = max(excel_files, 
                     key=lambda x: os.path.getmtime(os.path.join(report_folder, x)))
    
    excel_path = os.path.join(report_folder, latest_file)
    
    # Read data
    df = pd.read_excel(excel_path)
    
    # Return format
    format_type = request.args.get('format', 'info')
    
    if format_type == 'json':
        # Return full data as JSON
        return jsonify({
            'status': 'success',
            'data': df.to_dict(orient='records'),
            'file': latest_file,
            'timestamp': datetime.fromtimestamp(os.path.getmtime(excel_path)).isoformat()
        })
    else:
        # Return file info only
        return jsonify({
            'status': 'success',
            'file': latest_file,
            'path': os.path.abspath(excel_path),
            'size': os.path.getsize(excel_path),
            'modified': datetime.fromtimestamp(os.path.getmtime(excel_path)).isoformat(),
            'rows': len(df),
            'columns': len(df.columns)
        })

if __name__ == '__main__':
    print("="*70)
    print("Ablink SGCarmart Scraper - API Server")
    print("By Oneiros Indonesia")
    print("="*70)
    print("\nAPI Endpoints:")
    print("  POST /api/scrape    - Trigger scraping")
    print("  GET  /api/status    - Check API status")
    print("  GET  /api/latest    - Get latest data")
    print("\nAuthentication:")
    print(f"  X-API-Key: {API_KEY}")
    print("\nExample n8n HTTP Request Node:")
    print("""
  Method: POST
  URL: http://YOUR_SERVER:5001/api/scrape
  Headers:
    X-API-Key: your-secret-api-key-change-this
  Body (JSON):
    {
      "headless": true,
      "timeout": 30,
      "format": ["excel", "csv", "html"]
    }
    """)
    print("\n" + "="*70)
    print("Starting API server on port 5001...")
    print("Press Ctrl+C to stop")
    print("="*70 + "\n")
    
    # Run on different port from web app
    app.run(debug=False, host='0.0.0.0', port=5001)
