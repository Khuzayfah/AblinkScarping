"""
Ablink SGCarmart Scraper - Market Analysis Dashboard
By Oneiros Indonesia

Features:
- REAL scraping from SGCarmart (valid data)
- Auto scraping daily at 9:00 AM
- Manual scraping with button
- History with left/right navigation (unlimited)
- Upload pricelist & comparison
- Export to Excel, PDF, CSV
- All in English
"""

from flask import Flask, render_template, jsonify, send_file, request
from datetime import datetime
import pandas as pd
import os
import json
import threading
import time
import schedule
from werkzeug.utils import secure_filename

# Import custom modules
from sgcarmart_scraper import SGCarmartScraper
from data_history_manager import DataHistoryManager

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload

# Initialize history manager
history_manager = DataHistoryManager()

# Ensure folders exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('daily_reports', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('data/history', exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Global state
scraping_status = {
    'is_scraping': False,
    'last_scrape': None,
    'last_status': 'Ready',
    'next_scheduled': '09:00'
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_pricelist():
    """Load uploaded pricelist data"""
    pricelist_file = 'data/pricelist.json'
    if os.path.exists(pricelist_file):
        with open(pricelist_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_pricelist(data):
    """Save pricelist data"""
    pricelist_file = 'data/pricelist.json'
    with open(pricelist_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def perform_scraping():
    """Execute scraping from SGCarmart"""
    global scraping_status
    
    if scraping_status['is_scraping']:
        return {'success': False, 'error': 'Scraping already in progress'}
    
    scraping_status['is_scraping'] = True
    scraping_status['last_status'] = 'Scraping in progress...'
    
    try:
        print(f"\n[{datetime.now()}] Starting SGCarmart scraping...")
        
        # Create scraper and run
        scraper = SGCarmartScraper(headless=True)
        data = scraper.scrape_all_categories()
        
        if data:
            # Get previous data for diff calculation
            prev_data = history_manager.get_latest()
            if prev_data:
                data = history_manager.calculate_diff(data, prev_data)
            
            # Save to history
            saved_date = history_manager.save_data(data)
            
            scraping_status['last_scrape'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            scraping_status['last_status'] = f'Success - {len(data.get("vehicles", []))} vehicles scraped'
            
            print(f"[OK] Scraping completed: {len(data.get('vehicles', []))} vehicles")
            
            return {
                'success': True,
                'date': saved_date,
                'vehicles_count': len(data.get('vehicles', [])),
                'message': 'Scraping completed successfully'
            }
        else:
            scraping_status['last_status'] = 'Failed - No data retrieved'
            return {'success': False, 'error': 'No data retrieved'}
    
    except Exception as e:
        scraping_status['last_status'] = f'Error: {str(e)}'
        print(f"[ERROR] Scraping failed: {e}")
        return {'success': False, 'error': str(e)}
    
    finally:
        scraping_status['is_scraping'] = False


def scheduled_scrape():
    """Scheduled scraping task"""
    print(f"\n[SCHEDULER] Running scheduled scrape at {datetime.now()}")
    perform_scraping()


def run_scheduler():
    """Run the scheduler in background"""
    # Schedule daily at 9:00 AM
    schedule.every().day.at("09:00").do(scheduled_scrape)
    
    print("[SCHEDULER] Started - Daily scraping scheduled at 09:00 AM")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def compare_prices(pricelist, sgcarmart_data):
    """Compare our prices with SGCarmart - detailed analysis"""
    comparison = []
    
    if not pricelist or not sgcarmart_data:
        return comparison
    
    for item in pricelist.get('vehicles', []):
        vehicle_name = item.get('vehicle', '').upper()
        our_depreciation = item.get('depreciation', 0)
        registered_year = str(item.get('registered_year', ''))
        category = item.get('category', '')
        
        if our_depreciation <= 0:
            continue
        
        # Find matching vehicle in SGCarmart data
        best_match = None
        best_match_score = 0
        
        for sg_vehicle in sgcarmart_data.get('vehicles', []):
            sg_name = sg_vehicle['vehicle'].upper()
            
            # Calculate match score
            score = 0
            
            # Check for common keywords
            keywords = ['HINO', 'TOYOTA', 'DYNA', 'HIACE', 'NISSAN', 'NV200', 'NV350', 
                       'MITSUBISHI', 'FEA', 'FEB', 'ISUZU', 'NPR', 'NMR', 'NNR', 'NHR', 'NJR',
                       'HONDA', 'N-VAN', 'CABSTAR', 'KIA', 'DUTRO', 'XZU']
            
            for kw in keywords:
                if kw in vehicle_name and kw in sg_name:
                    score += 10
            
            if score > best_match_score:
                best_match_score = score
                best_match = sg_vehicle
        
        if best_match and best_match_score >= 10:
            # Try to find matching year
            year_data = best_match.get('years', {}).get(registered_year, {})
            
            # If exact year not found, try nearby years
            if not year_data:
                for yr in [str(int(registered_year) + 1), str(int(registered_year) - 1)]:
                    year_data = best_match.get('years', {}).get(yr, {})
                    if year_data:
                        break
            
            if year_data:
                sg_lowest = year_data.get('lowest', 0)
                sg_average = year_data.get('average', 0)
                sg_units = year_data.get('units', 0)
                
                # Calculate how many cheaper/expensive
                if sg_average > 0 and sg_lowest > 0:
                    if our_depreciation > sg_average:
                        # Most are cheaper than us
                        cheaper_count = int(sg_units * 0.8)
                        expensive_count = sg_units - cheaper_count
                    elif our_depreciation > sg_lowest:
                        # Some are cheaper, some expensive
                        # Estimate based on where our price falls
                        ratio = (our_depreciation - sg_lowest) / (sg_average - sg_lowest + 1)
                        cheaper_count = int(sg_units * ratio * 0.5)
                        expensive_count = sg_units - cheaper_count
                    else:
                        # We are cheapest
                        cheaper_count = 0
                        expensive_count = sg_units
                else:
                    cheaper_count = 0
                    expensive_count = 0
                
                comparison.append({
                    'vehicle': item.get('vehicle', ''),
                    'registered_year': registered_year,
                    'our_depreciation': our_depreciation,
                    'sg_lowest': sg_lowest,
                    'sg_average': sg_average,
                    'sg_units': sg_units,
                    'cheaper_count': cheaper_count,
                    'expensive_count': expensive_count,
                    'category': best_match.get('category', ''),
                    'sg_vehicle_name': best_match.get('vehicle', '')
                })
    
    return comparison


# ============== ROUTES ==============

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('market_analysis.html')


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """Manual scraping endpoint"""
    result = perform_scraping()
    return jsonify(result)


@app.route('/api/status')
def api_status():
    """Get scraping status"""
    return jsonify({
        'is_scraping': scraping_status['is_scraping'],
        'last_scrape': scraping_status['last_scrape'],
        'last_status': scraping_status['last_status'],
        'next_scheduled': scraping_status['next_scheduled']
    })


@app.route('/api/history')
def api_history():
    """Get all available history dates"""
    dates = history_manager.get_dates()
    return jsonify({
        'success': True,
        'dates': dates,
        'total': len(dates)
    })


@app.route('/api/data/<date>')
def api_data_by_date(date):
    """Get data for specific date"""
    data = history_manager.get_data(date)
    
    if data:
        return jsonify({
            'success': True,
            'data': data,
            'date': date,
            'previous_date': history_manager.get_previous_date(date),
            'next_date': history_manager.get_next_date(date)
        })
    
    return jsonify({'success': False, 'error': 'No data for this date'})


@app.route('/api/data/latest')
def api_data_latest():
    """Get latest data"""
    data = history_manager.get_latest()
    
    if data:
        dates = history_manager.get_dates()
        current_date = dates[0] if dates else None
        
        return jsonify({
            'success': True,
            'data': data,
            'date': current_date,
            'previous_date': history_manager.get_previous_date(current_date) if current_date else None,
            'next_date': None
        })
    
    # No history, return sample data
    from sgcarmart_scraper import SGCarmartScraper
    scraper = SGCarmartScraper()
    sample_data = scraper._get_sample_data()
    
    return jsonify({
        'success': True,
        'data': sample_data,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'previous_date': None,
        'next_date': None,
        'is_sample': True
    })


@app.route('/api/upload-pricelist', methods=['POST'])
def upload_pricelist():
    """Upload pricelist file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Read file
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Process data
            vehicles = []
            for _, row in df.iterrows():
                try:
                    # Try different column names
                    desc = row.get('Description', row.get('Model', row.get('Vehicle', '')))
                    reg_date = str(row.get('Registered Date', row.get('Reg Date', '')))
                    asking = row.get('Asking $', row.get('Price', row.get('Asking', 0)))
                    coe = str(row.get('COE Expiry', row.get('COE', '')))
                    category = str(row.get('Category', ''))
                    
                    # Clean price
                    if isinstance(asking, str):
                        asking = float(asking.replace('$', '').replace(',', '') or 0)
                    
                    vehicle = {
                        'vehicle': str(desc),
                        'category': category,
                        'registered_date': reg_date,
                        'asking_price': float(asking),
                        'coe_expiry': coe,
                    }
                    
                    # Calculate depreciation
                    if vehicle['asking_price'] > 0 and vehicle['coe_expiry']:
                        try:
                            coe_year = int(vehicle['coe_expiry'].split('/')[-1])
                            years_left = coe_year - datetime.now().year
                            if years_left > 0:
                                vehicle['depreciation'] = int(vehicle['asking_price'] / years_left)
                            else:
                                vehicle['depreciation'] = 0
                            
                            # Extract registered year
                            vehicle['registered_year'] = int(reg_date.split('/')[-1])
                        except:
                            vehicle['depreciation'] = 0
                            vehicle['registered_year'] = 0
                    else:
                        vehicle['depreciation'] = 0
                        vehicle['registered_year'] = 0
                    
                    if vehicle['vehicle']:
                        vehicles.append(vehicle)
                except Exception as e:
                    continue
            
            pricelist_data = {
                'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'filename': filename,
                'vehicles': vehicles
            }
            
            save_pricelist(pricelist_data)
            
            return jsonify({
                'success': True,
                'message': f'Uploaded {len(vehicles)} vehicles',
                'count': len(vehicles)
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Invalid file type'})


@app.route('/api/clear-pricelist', methods=['POST'])
def clear_pricelist():
    """Clear pricelist data"""
    pricelist_file = 'data/pricelist.json'
    if os.path.exists(pricelist_file):
        os.remove(pricelist_file)
    return jsonify({'success': True, 'message': 'Pricelist cleared'})


@app.route('/api/pricelist')
def get_pricelist():
    """Get current pricelist"""
    pricelist = load_pricelist()
    if pricelist:
        return jsonify({'success': True, 'data': pricelist})
    return jsonify({'success': False, 'message': 'No pricelist uploaded'})


@app.route('/api/comparison')
def get_comparison():
    """Get price comparison"""
    pricelist = load_pricelist()
    sgcarmart = history_manager.get_latest()
    
    if not sgcarmart:
        from sgcarmart_scraper import SGCarmartScraper
        scraper = SGCarmartScraper()
        sgcarmart = scraper._get_sample_data()
    
    comparison = compare_prices(pricelist, sgcarmart)
    
    return jsonify({
        'success': True,
        'data': comparison,
        'pricelist_count': len(pricelist.get('vehicles', [])) if pricelist else 0,
        'sgcarmart_count': len(sgcarmart.get('vehicles', [])) if sgcarmart else 0
    })


@app.route('/api/export/<date>/<format>')
def export_data(date, format):
    """Export data for specific date"""
    data = history_manager.get_data(date)
    
    if not data:
        # Use latest or sample
        data = history_manager.get_latest()
        if not data:
            from sgcarmart_scraper import SGCarmartScraper
            scraper = SGCarmartScraper()
            data = scraper._get_sample_data()
    
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Convert to DataFrame
    rows = []
    for v in data.get('vehicles', []):
        row = {'Category': v['category'], 'Vehicle': v['vehicle']}
        for year, year_data in sorted(v.get('years', {}).items(), reverse=True):
            row[f'{year}_Lowest'] = year_data.get('lowest', 0)
            row[f'{year}_Average'] = year_data.get('average', 0)
            row[f'{year}_Units'] = year_data.get('units', 0)
        row['Total Units'] = v.get('total_units', 0)
        row['Previous'] = v.get('previous', 0)
        row['Diff'] = v.get('diff', 0)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if format == 'csv':
        filename = f'market_analysis_{date}_{timestamp}.csv'
        filepath = f'daily_reports/{filename}'
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    elif format == 'excel':
        filename = f'market_analysis_{date}_{timestamp}.xlsx'
        filepath = f'daily_reports/{filename}'
        df.to_excel(filepath, index=False)
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    elif format == 'pdf':
        # Generate HTML for PDF
        from market_analysis_generator import MarketAnalysisGenerator
        generator = MarketAnalysisGenerator()
        html_file = generator.generate_report(data)
        return send_file(html_file, as_attachment=False)
    
    return jsonify({'error': 'Invalid format'}), 400


if __name__ == '__main__':
    print("="*70)
    print("Ablink SGCarmart Scraper - Market Analysis Dashboard")
    print("By Oneiros Indonesia")
    print("="*70)
    print("\nFeatures:")
    print("  - REAL scraping from SGCarmart")
    print("  - Auto scraping daily at 9:00 AM")
    print("  - Manual scraping with button")
    print("  - History with left/right navigation")
    print("  - Upload pricelist & comparison")
    print("  - Export to Excel, PDF, CSV")
    print("\nStarting scheduler...")
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("[OK] Scheduler started - Auto scraping at 09:00 daily")
    print("\nStarting server...")
    
    port = int(os.environ.get('PORT', 5555))
    print(f"Open: http://localhost:{port}")
    print("="*70)
    
    app.run(debug=True, port=port, host='0.0.0.0', use_reloader=False)
