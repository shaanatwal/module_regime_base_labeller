import pandas as pd

def load_parquet_data(file_path: str) -> pd.DataFrame:
    """
    Loads OHLCV data from a specified Parquet file.

    This function performs several crucial preprocessing steps:
    1. Ensures all required columns ('t', 'o', 'h', 'l', 'c', 'v') are present.
    2. Removes any rows with missing data in essential columns to prevent errors.
    3. Standardizes the timestamp column to be timezone-aware (UTC).
    4. Resets the DataFrame index to be a continuous integer sequence (0, 1, 2,...),
       which is critical for the charting logic that maps bar index to x-coordinates.

    Args:
        file_path: The full path to the .parquet file.

    Returns:
        A cleaned and prepared pandas DataFrame, or an empty DataFrame on error.
    """
    print(f"Loading data from: {file_path}")
    try:
        df = pd.read_parquet(file_path)
        
        # --- 1. Validate Columns ---
        required_cols = ['t', 'o', 'h', 'l', 'c', 'v']
        if not all(col in df.columns for col in required_cols):
            # If data is missing essential columns, it cannot be plotted.
            print(f"Error: Input data must contain the following columns: {required_cols}")
            return pd.DataFrame()

        initial_rows = len(df)
        print(f"Original data points: {initial_rows}")

        # --- 2. Clean Data ---
        # Drop any rows where price or volume data is missing.
        df.dropna(subset=['o', 'h', 'l', 'c', 'v'], inplace=True)
        
        filtered_rows = len(df)
        print(f"Data points after removing NaN rows: {filtered_rows}")
        
        # --- 3. Standardize Timestamps ---
        # Convert the timestamp column to pandas datetime objects.
        df['t'] = pd.to_datetime(df['t'])
        # If timestamps are naive, localize them to UTC for consistency.
        if df['t'].dt.tz is None:
            df['t'] = df['t'].dt.tz_localize('UTC')

        # --- 4. Reset Index ---
        # This is a CRITICAL step. The rest of the application assumes that the
        # DataFrame index directly corresponds to the candle's position on the
        # x-axis (e.g., bar #0, bar #1, etc.). Resetting the index ensures this
        # is true, regardless of any filtering or original indexing.
        df.reset_index(drop=True, inplace=True)
        print("Data index has been reset for continuous display.")
        
        return df

    except Exception as e:
        print(f"An unexpected error occurred during data loading or processing: {e}")
        return pd.DataFrame()