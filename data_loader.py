# Save this file as data_loader.py
import pandas as pd

def load_parquet_data(file_path: str) -> pd.DataFrame:
    """
    Loads OHLCV data from a Parquet file and sets the timestamp
    column 't' as the index.
    """
    print(f"Loading data from: {file_path}")
    try:
        df = pd.read_parquet(file_path)
        
        # Ensure the timestamp column exists before setting it as the index
        if 't' in df.columns:
            df['t'] = pd.to_datetime(df['t'])
            # --- THIS IS THE FIX ---
            # Set the 't' column as the DataFrame's index.
            df = df.set_index('t')
            print("Data loaded successfully and 't' column set as index.")
        else:
             print("Warning: 't' column not found in data.")

        print("Data index type:", type(df.index))
        print("First 5 rows:\n", df.head())
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()