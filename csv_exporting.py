#!/usr/bin/env python3

import os

def df2csv(df, filename=None, data_dir='data'):
   
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}/")
    
    # Generate filename
    if filename is None:
        filename = 'export'
    
    # Remove .csv extension if user included it
    if filename.endswith('.csv'):
        filename = filename[:-4]
    
    # Create full path
    filepath = os.path.join(data_dir, f"{filename}.csv")
    
    # Export to CSV
    df.to_csv(filepath, index=False)
    
    # Print confirmation with file info
    file_size = os.path.getsize(filepath) / 1024  # KB
    print(f"  Exported {len(df)} rows x {len(df.columns)} columns to:")
    print(f"  {filepath}")
    print(f"  Size: {file_size:.1f} KB\n")
    
    return filepath