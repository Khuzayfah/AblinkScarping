"""
Ablink SGCarmart Scraper - Web Dashboard with History Slider
By Oneiros Indonesia

Features:
- Manual scraping
- Auto daily scraping at 9 AM
- History slider (left/right)
- Export CSV, Excel, PDF
- Soft natural colors
"""

from flask import Flask, render_template, jsonify, send_file, request
from datetime import datetime
import pandas as pd
import os
from soft_generator import SoftGenerator
from history_manager import HistoryManager
import threading
import schedule
import time

app = Flask(__name__)
history_mgr = HistoryManager()


def create_sample_data():
    """Create sample data for demonstration"""
    data = {
        'Vehicle': [
            'HINO DUTRO 2.8', 'TOYOTA DYNA 2.8', 'TOYOTA DYNA 3.0', 'NISSAN CABSTAR',
            'MITSUBISHI FEA01', 'ISUZU NHR / NJR', 'KIA 2500',
            'HINO XZU710', 'ISUZU NPR85', 'ISUZU NMR85', 'ISUZU NNR85', 'MITSUBISHI FEB21',
            'TOYOTA HIACE 3.0M', 'TOYOTA HIACE 3.0A', 'TOYOTA HIACE 2.8A',
            'NISSAN NV350 2.5M', 'NISSAN NV200 1.5M',
            'HONDA N-VAN', 'TOYOTA HIACE 2.0', 'NISSAN NV350 2.0', 'NISSAN NV200 1.6A'
        ],
        'Category': [
            '10FT DIESEL', '10FT DIESEL', '10FT DIESEL', '10FT DIESEL', '10FT DIESEL',
            '10FT DIESEL', '10FT DIESEL',
            '14FT DIESEL', '14FT DIESEL', '14FT DIESEL', '14FT DIESEL', '14FT DIESEL',
            'VAN DIESEL (GOODS VAN)', 'VAN DIESEL (GOODS VAN)', 'VAN DIESEL (GOODS VAN)',
            'VAN DIESEL (GOODS VAN)', 'VAN DIESEL (GOODS VAN)',
            'VAN PETROL (GOODS VAN)', 'VAN PETROL (GOODS VAN)', 'VAN PETROL (GOODS VAN)',
            'VAN PETROL (GOODS VAN)'
        ],
        '2025_price': [11510, 0, 0, 0, 0, 13470, 0, 12220, 13180, 12520, 12250, 12370, 0, 0, 13230, 0, 0, 9540, 12260, 0, 9340],
        '2025_units': [49, 0, 0, 0, 0, 2, 0, 27, 2, 2, 1, 12, 0, 0, 14, 0, 0, 27, 1, 0, 9],
        '2024_price': [11450, 0, 0, 0, 0, 0, 10550, 12220, 0, 0, 0, 0, 0, 0, 13050, 0, 0, 9350, 0, 0, 9860],
        '2024_units': [8, 0, 0, 0, 0, 0, 1, 6, 0, 0, 0, 0, 0, 0, 1, 0, 0, 3, 0, 0, 3],
        '2023_price': [0, 14720, 0, 0, 0, 0, 11170, 13120, 0, 0, 0, 12470, 0, 0, 15180, 0, 0, 9950, 10760, 8870, 9690],
        '2023_units': [0, 2, 0, 0, 0, 0, 2, 2, 0, 0, 0, 2, 0, 0, 1, 0, 0, 1, 3, 1, 3],
        '2022_price': [0, 12740, 13470, 10110, 0, 0, 10020, 13880, 14060, 13530, 13740, 0, 13610, 0, 14230, 0, 0, 10040, 11240, 9550, 0],
        '2022_units': [0, 14, 1, 1, 0, 0, 3, 2, 5, 1, 2, 0, 1, 0, 1, 0, 0, 13, 9, 4, 0],
        '2021_price': [0, 13310, 15580, 8530, 11550, 11400, 11180, 15790, 13760, 0, 0, 0, 13590, 13780, 14030, 0, 0, 0, 11360, 9860, 9980],
        '2021_units': [0, 4, 4, 1, 5, 1, 3, 1, 3, 0, 0, 0, 7, 10, 22, 0, 0, 0, 11, 1, 18],
        '2020_price': [0, 0, 15330, 9770, 11670, 12990, 10350, 16130, 0, 0, 0, 13060, 13310, 13990, 14660, 10350, 11570, 0, 0, 0, 9860],
        '2020_units': [0, 0, 11, 2, 3, 2, 2, 2, 0, 0, 0, 4, 12, 3, 22, 3, 1, 0, 0, 0, 8],
        '2019_price': [0, 0, 16160, 0, 12060, 0, 0, 16280, 0, 13460, 0, 14770, 14130, 14110, 14830, 11530, 9530, 0, 0, 0, 11530],
        '2019_units': [0, 0, 10, 0, 4, 0, 0, 1, 0, 1, 0, 5, 10, 3, 6, 2, 6, 0, 0, 0, 8],
        '2018_price': [0, 0, 16220, 0, 0, 11680, 0, 16270, 19710, 17190, 14560, 15740, 13780, 16600, 21270, 10370, 9720, 0, 0, 0, 11300],
        '2018_units': [0, 0, 7, 0, 0, 3, 0, 3, 1, 1, 2, 7, 13, 5, 1, 6, 6, 0, 0, 0, 1],
        '2017_price': [0, 0, 16700, 11090, 11550, 11740, 0, 18440, 13610, 0, 16420, 16320, 13630, 15130, 0, 10320, 9320, 0, 0, 0, 11590],
        '2017_units': [0, 0, 5, 9, 2, 3, 0, 1, 3, 0, 1, 7, 9, 3, 0, 4, 8, 0, 0, 0, 7],
        '2016_price': [0, 0, 9950, 8360, 18840, 9150, 0, 29970, 0, 0, 10150, 9950, 9750, 29200, 0, 0, 8160, 0, 0, 0, 9150],
        '2016_units': [0, 0, 19, 3, 2, 6, 0, 3, 0, 0, 1, 8, 6, 1, 0, 0, 6, 0, 0, 0, 2],
        '2015_price': [0, 0, 9840, 9620, 8560, 8080, 0, 10370, 9170, 0, 0, 8360, 8010, 11410, 0, 8070, 8360, 0, 0, 0, 8560],
        '2015_units': [0, 0, 23, 1, 3, 6, 0, 3, 2, 0, 0, 19, 19, 1, 0, 7, 6, 0, 0, 0, 11],
        '2014_price': [0, 0, 8960, 8700, 10940, 8920, 0, 18020, 13640, 0, 10230, 10030, 8980, 11170, 0, 9050, 7760, 0, 0, 0, 9760],
        '2014_units': [0, 0, 19, 7, 3, 2, 0, 1, 1, 0, 1, 5, 9, 4, 0, 3, 2, 0, 0, 0, 1],
        'TOTAL UNITS': [57, 20, 99, 24, 22, 25, 11, 52, 17, 5, 8, 69, 86, 30, 68, 26, 35, 44, 24, 6, 71],
        'Previous': [55, 17, 105, 29, 25, 24, 9, 54, 21, 3, 11, 72, 78, 25, 61, 28, 37, 41, 15, 8, 50],
        'DIFF': [2, 3, -6, -5, -3, 1, 2, -2, -4, 2, -3, -3, 8, 5, 7, -2, -2, 3, 9, -2, 21]
    }
    return pd.DataFrame(data)


def scrape_data():
    """Scrape data (sample for now)"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scraping data...")
    
    # Create sample data
    df = create_sample_data()
    
    # Save to history
    result = history_mgr.save_report(df)
    
    # Generate HTML report
    generator = SoftGenerator()
    html_file = generator.generate_report(df)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scraping complete!")
    print(f"  Saved to: {result['date']}")
    print(f"  HTML: {html_file}")
    
    return result


def daily_scrape():
    """Daily scraping job"""
    scrape_data()


def run_scheduler():
    """Run scheduler in background"""
    schedule.every().day.at("09:00").do(daily_scrape)
    
    while True:
        schedule.run_pending()
        time.sleep(60)


# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard_slider.html')


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Manual scrape endpoint"""
    try:
        result = scrape_data()
        return jsonify({
            'success': True,
            'date': result['date'],
            'time': result['time']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history')
def api_history():
    """Get history dates"""
    dates = history_mgr.get_history_dates()
    return jsonify({
        'dates': dates
    })


@app.route('/api/data/<date>')
def api_data(date):
    """Get data for specific date"""
    data = history_mgr.get_date_data(date)
    
    if data:
        # Convert DataFrame to dict
        df_dict = data['data'].to_dict('records')
        
        return jsonify({
            'success': True,
            'date': data['date'],
            'time': data['time'],
            'datetime': data['datetime'],
            'summary': data['summary'],
            'data': df_dict
        })
    
    return jsonify({
        'success': False,
        'error': 'Date not found'
    }), 404


@app.route('/api/export/<date>/<format>')
def api_export(date, format):
    """Export data"""
    data = history_mgr.get_date_data(date)
    
    if not data:
        return jsonify({'error': 'Date not found'}), 404
    
    df = data['data']
    
    if format == 'csv':
        filename = f"export_{date}.csv"
        filepath = f"daily_reports/{filename}"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    elif format == 'excel':
        filename = f"export_{date}.xlsx"
        filepath = f"daily_reports/{filename}"
        df.to_excel(filepath, index=False)
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    elif format == 'pdf':
        # Generate HTML and return for printing
        generator = SoftGenerator()
        html_file = generator.generate_report(df)
        return send_file(html_file, as_attachment=False)
    
    return jsonify({'error': 'Invalid format'}), 400


if __name__ == '__main__':
    print("="*70)
    print("Ablink SGCarmart Scraper - Web Dashboard")
    print("By Oneiros Indonesia")
    print("="*70)
    print("\nFeatures:")
    print("  - Manual scraping")
    print("  - Auto daily scraping at 9:00 AM")
    print("  - History slider")
    print("  - Export CSV, Excel, PDF")
    print("  - Soft natural colors")
    print("\nStarting server...")
    port = int(os.environ.get('PORT', 5555))
    print(f"Open: http://localhost:{port}")
    print("="*70)
    
    app.run(debug=False, port=port, host='0.0.0.0')
