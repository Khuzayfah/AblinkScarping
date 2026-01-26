"""
Ablink SGCarmart Scraper - History Manager
By Oneiros Indonesia

Manage daily scraping history
"""

import json
import os
from datetime import datetime
import pandas as pd


class HistoryManager:
    """Manage scraping history"""
    
    def __init__(self, history_dir="daily_reports/history"):
        self.history_dir = history_dir
        self.index_file = os.path.join(history_dir, "index.json")
        os.makedirs(history_dir, exist_ok=True)
    
    def save_report(self, df, scrape_date=None):
        """Save report to history"""
        if scrape_date is None:
            scrape_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create date folder
        date_folder = os.path.join(self.history_dir, scrape_date)
        os.makedirs(date_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%H%M%S")
        
        # Save CSV
        csv_file = os.path.join(date_folder, f"data_{timestamp}.csv")
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # Save Excel
        excel_file = os.path.join(date_folder, f"data_{timestamp}.xlsx")
        df.to_excel(excel_file, index=False)
        
        # Update index
        self._update_index(scrape_date, timestamp, df)
        
        return {
            'date': scrape_date,
            'time': timestamp,
            'csv': csv_file,
            'excel': excel_file
        }
    
    def _update_index(self, date, time, df):
        """Update history index"""
        # Load existing index
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {}
        
        # Add summary
        summary = {
            'time': time,
            'datetime': f"{date} {time[:2]}:{time[2:4]}:{time[4:6]}",
            'total_vehicles': len(df),
            'total_units': int(df['TOTAL UNITS'].sum()),
            'categories': df['Category'].nunique()
        }
        
        if date not in index:
            index[date] = []
        
        index[date].append(summary)
        
        # Save index
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
    
    def get_history_dates(self):
        """Get list of dates with history"""
        if not os.path.exists(self.index_file):
            return []
        
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        return sorted(index.keys(), reverse=True)
    
    def get_date_data(self, date):
        """Get data for a specific date"""
        if not os.path.exists(self.index_file):
            return None
        
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if date in index:
            # Get latest entry for the date
            latest = index[date][-1]
            
            # Load CSV data
            csv_file = os.path.join(self.history_dir, date, f"data_{latest['time']}.csv")
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                return {
                    'date': date,
                    'time': latest['time'],
                    'datetime': latest['datetime'],
                    'data': df,
                    'summary': latest
                }
        
        return None
    
    def get_latest(self):
        """Get latest scraping data"""
        dates = self.get_history_dates()
        if dates:
            return self.get_date_data(dates[0])
        return None
