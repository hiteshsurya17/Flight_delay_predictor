import pandas as pd
from datetime import datetime, timedelta

def combine_flight_weather_data_for_date(date: str):
    """
    Combines flight data and weather data for a given date and saves the result as a new CSV file.
    
    Parameters:
    - date (str): The date for which to combine the flight and weather data in 'YYYY-MM-DD' format.
    
    Returns:
    None
    """
    # Define file paths for the flight data and weather data
    flights_file_path = f'flightdelay/flights_{date}.csv'
    weather_file_path = f'weather_data_{date}.csv'

    # Load the CSV files into pandas DataFrames
    try:
        flights_df = pd.read_csv(flights_file_path, on_bad_lines='skip')
        weather_df = pd.read_csv(weather_file_path)
    except FileNotFoundError:
        print(f"File not found: {flights_file_path} or {weather_file_path}")
        return

    # Merge the DataFrames on the specified columns
    combined_df = pd.merge(flights_df, weather_df, 
                           on=["year", "month", "day", "closest_hour_crs_dep"], 
                           how="left")

    # Change all values in the 'year' column to 2024
    combined_df['year'] = 2024

    # Define the path for the combined CSV file
    combined_file_path = f'combined_flight_weather_data_{date}.csv'

    # Save the combined DataFrame to a new CSV file
    combined_df.to_csv(combined_file_path, index=False)

    print(f"Combined CSV file saved as '{combined_file_path}'.")


def combine_flight_weather_data():
    # Define file paths for the flight data and weather data
    flights_file_path = f'flightdelay/flights_for_display.csv'
    todays_date = datetime.utcnow().strftime("%Y-%m-%d")
    weather_file_path = f'weather_data_{todays_date}.csv'

    # Load the CSV files into pandas DataFrames, skipping bad lines
    try:
        flights_df = pd.read_csv(flights_file_path, on_bad_lines='skip')  # Skip rows with issues
        weather_df = pd.read_csv(weather_file_path, on_bad_lines='skip')  # Skip rows with issues
    except FileNotFoundError:
        print(f"File not found: {flights_file_path} or {weather_file_path}")
        return
    
    # invalid_rows = flights_df[~flights_df['year'].astype(str).str.match(r'^\d+$', na=False)]
    # print(invalid_rows)
    # flights_df = flights_df[flights_df['year'].astype(str).str.match(r'^\d+$', na=False)]

    flights_df.dropna(subset=["year", "month", "day", "closest_hour_crs_dep"], inplace=True)
    # flights_df['year'] = flights_df['year'].astype(int)
    flights_df = flights_df.astype({"year": int, "month": int, "day": int, "closest_hour_crs_dep": int})

    # print(flights_df.head)
    # print(weather_df.head)
    # print('DTYPES:')
    # print(flights_df.dtypes)
    # print(weather_df.dtypes)
    # flights_df['year'] = flights_df['year'].astype(int)
    # weather_df['year'] = weather_df['year'].astype(int)
    


    # Merge the DataFrames on the specified columns
    combined_df = pd.merge(flights_df, weather_df, 
                           on=["year", "month", "day", "closest_hour_crs_dep"], 
                           how="left")

    # Change all values in the 'year' column to 2024
    combined_df['year'] = 2024

    # Define the path for the combined CSV file
    combined_file_path = f'combined_flight_weather_data.csv'

    # Save the combined DataFrame to a new CSV file
    combined_df.to_csv(combined_file_path, index=False)

    print(f"Combined CSV file saved as '{combined_file_path}'.")

