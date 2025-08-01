import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any

def export_to_csv(data: List[Any], filepath: str):
    """
    Export data to CSV file
    
    Args:
        data: List of data objects
        filepath: Path to output file
    """
    if not data:
        # Create empty file
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['No data'])
        return
    
    # Get fields from first item
    if hasattr(data[0], '__dict__'):
        # Handle Telegram User objects or other objects with __dict__
        fields = data[0].__dict__.keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            
            for item in data:
                writer.writerow([getattr(item, field, '') for field in fields])
    
    else:
        # Handle dictionaries
        fields = data[0].keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)

def export_to_json(data: List[Dict[str, Any]], filepath: str):
    """
    Export data to JSON file
    
    Args:
        data: List of data objects
        filepath: Path to output file
    """
    # Convert any objects to dictionaries
    if hasattr(data[0], '__dict__'):
        serializable_data = [item.__dict__ for item in data]
    else:
        serializable_data = data
    
    # Handle datetime objects
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, default=json_serializer, ensure_ascii=False, indent=2)

def export_to_txt(data: List[Any], filepath: str, field: str = 'username'):
    """
    Export data to text file, one item per line
    
    Args:
        data: List of data objects
        filepath: Path to output file
        field: Field to export (default: username)
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            if hasattr(item, field):
                value = getattr(item, field)
                if value:
                    f.write(f"{value}\n")
            elif isinstance(item, dict) and field in item:
                value = item[field]
                if value:
                    f.write(f"{value}\n")