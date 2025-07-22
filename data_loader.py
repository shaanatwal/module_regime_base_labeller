# Save this file as data_loader.py
import pandas as pd

def load_parquet_data(file_path: str) -> pd.DataFrame:
    """
    Loads OHLCV data from a Parquet file and removes all non-trading
    periods by dropping rows with NaN values. This creates a truly 
    continuous display for all market sessions.
    """
    print(f"Loading data from: {file_path}")
    try:
        df = pd.read_parquet(file_path)
        
        # --- Ensure required columns exist ---
        required_cols = ['t', 'o', 'h', 'l', 'c']
        if not all(col in df.columns for col in required_cols):
            print(f"Error: Data must contain columns {required_cols}")
            return pd.DataFrame()

        initial_rows = len(df)
        print(f"Original data points: {initial_rows}")

        # --- Drop any rows where the essential OHLC data is missing ---
        # This is the most robust way to remove all non-trading periods
        # (weekends, holidays, etc.), assuming they are represented by NaNs.
        df.dropna(subset=['o', 'h', 'l', 'c'], inplace=True)
        
        filtered_rows = len(df)
        print(f"Data points after removing NaN rows: {filtered_rows}")
        
        # --- Prepare the timestamp column for display ---
        # We still do this so the date/time display on the chart is correct.
        df['t'] = pd.to_datetime(df['t'])
        if df['t'].dt.tz is None:
            df['t'] = df['t'].dt.tz_localize('UTC')

        # CRITICAL STEP: Reset the index to be continuous (0, 1, 2, ...).
        # This makes the filtered data plot sequentially without gaps.
        df.reset_index(drop=True, inplace=True)
        
        print("Data index reset for continuous display.")
        print("Data index type:", type(df.index))
        
        return df

    except Exception as e:
        print(f"Error loading or processing data: {e}")
        return pd.DataFrame()