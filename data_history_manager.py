"""
Ablink SGCarmart Scraper - Data History Manager
By Oneiros Indonesia

Manages historical scraping data with unlimited history
"""

import json
import os
from datetime import datetime, timedelta
import pandas as pd


class DataHistoryManager:
    """Manages historical scraping data"""
    
    def __init__(self, history_dir="data/history"):
        self.history_dir = history_dir
        self.index_file = os.path.join(history_dir, "index.json")
        
        # Create directories
        os.makedirs(history_dir, exist_ok=True)
        
        # Load or create index
        self._load_index()
    
    def _load_index(self):
        """Load history index"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {
                'dates': [],
                'latest': None,
                'total_records': 0
            }
            self._save_index()
    
    def _save_index(self):
        """Save history index"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def save_data(self, data, date=None):
        """
        Save scraped data to history
        
        Args:
            data: Scraped data dictionary
            date: Date string (YYYY-MM-DD), defaults to today
        
        Returns:
            str: Saved date
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Create date folder
        date_dir = os.path.join(self.history_dir, date)
        os.makedirs(date_dir, exist_ok=True)
        
        # Generate timestamp for this scrape
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Save JSON data
        json_file = os.path.join(date_dir, f"data_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Also save as latest for this date
        latest_file = os.path.join(date_dir, "latest.json")
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Save CSV for easy viewing
        if 'vehicles' in data:
            rows = []
            for v in data['vehicles']:
                row = {
                    'Category': v['category'],
                    'Vehicle': v['vehicle'],
                    'Total Units': v.get('total_units', 0),
                    'Previous': v.get('previous', 0),
                    'Diff': v.get('diff', 0)
                }
                for year, year_data in v.get('years', {}).items():
                    row[f'{year}_Lowest'] = year_data.get('lowest', 0)
                    row[f'{year}_Average'] = year_data.get('average', 0)
                    row[f'{year}_Units'] = year_data.get('units', 0)
                rows.append(row)
            
            df = pd.DataFrame(rows)
            csv_file = os.path.join(date_dir, f"data_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            # Excel file
            excel_file = os.path.join(date_dir, f"data_{timestamp}.xlsx")
            df.to_excel(excel_file, index=False)
        
        # Update index
        if date not in self.index['dates']:
            self.index['dates'].append(date)
            self.index['dates'].sort(reverse=True)
        
        self.index['latest'] = date
        self.index['total_records'] += 1
        self._save_index()
        
        print(f"[OK] Data saved for {date}")
        return date
    
    def get_dates(self):
        """Get all available dates (sorted newest first)"""
        return sorted(self.index['dates'], reverse=True)
    
    def get_data(self, date):
        """
        Get data for a specific date
        
        Args:
            date: Date string (YYYY-MM-DD)
        
        Returns:
            dict: Data for that date, or None if not found
        """
        date_dir = os.path.join(self.history_dir, date)
        latest_file = os.path.join(date_dir, "latest.json")
        
        if os.path.exists(latest_file):
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def get_latest(self):
        """Get the most recent data"""
        if self.index['latest']:
            return self.get_data(self.index['latest'])
        return None
    
    def get_previous_date(self, current_date):
        """Get the date before the given date"""
        dates = self.get_dates()
        
        try:
            idx = dates.index(current_date)
            if idx < len(dates) - 1:
                return dates[idx + 1]
        except ValueError:
            pass
        
        return None
    
    def get_next_date(self, current_date):
        """Get the date after the given date"""
        dates = self.get_dates()
        
        try:
            idx = dates.index(current_date)
            if idx > 0:
                return dates[idx - 1]
        except ValueError:
            pass
        
        return None
    
    def calculate_diff(self, current_data, previous_data):
        """
        Calculate differences between current and previous data
        
        Args:
            current_data: Current day's data
            previous_data: Previous day's data
        
        Returns:
            dict: Updated current data with diff values
        """
        if not previous_data or 'vehicles' not in previous_data:
            return current_data
        
        # Create lookup for previous data
        prev_lookup = {}
        for v in previous_data['vehicles']:
            key = (v['category'], v['vehicle'])
            prev_lookup[key] = v.get('total_units', 0)
        
        # Update current data with diff
        for v in current_data.get('vehicles', []):
            key = (v['category'], v['vehicle'])
            prev_units = prev_lookup.get(key, v.get('total_units', 0))
            v['previous'] = prev_units
            v['diff'] = v.get('total_units', 0) - prev_units
        
        return current_data
    
    def get_history_summary(self, limit=30):
        """
        Get summary of historical data
        
        Args:
            limit: Maximum number of dates to include
        
        Returns:
            list: Summary data for each date
        """
        dates = self.get_dates()[:limit]
        summary = []
        
        for date in dates:
            data = self.get_data(date)
            if data:
                total_vehicles = len(data.get('vehicles', []))
                total_units = sum(v.get('total_units', 0) for v in data.get('vehicles', []))
                
                summary.append({
                    'date': date,
                    'time': data.get('time', ''),
                    'total_vehicles': total_vehicles,
                    'total_units': total_units
                })
        
        return summary
    
    def cleanup_old_data(self, keep_days=365):
        """
        Remove data older than specified days
        
        Args:
            keep_days: Number of days to keep
        """
        cutoff = (datetime.now() - timedelta(days=keep_days)).strftime('%Y-%m-%d')
        
        removed = 0
        for date in self.index['dates'][:]:
            if date < cutoff:
                date_dir = os.path.join(self.history_dir, date)
                if os.path.exists(date_dir):
                    import shutil
                    shutil.rmtree(date_dir)
                    removed += 1
                self.index['dates'].remove(date)
        
        if removed > 0:
            self._save_index()
            print(f"[OK] Removed {removed} old records")
        
        return removed
