import requests
import csv
from datetime import datetime, timedelta

# OpenWeather API Key (Replace with your own key)
API_KEY = "c22c55ffc74929630e37956fe7f6857e"

# API Endpoint
BASE_URL = "https://pro.openweathermap.org/data/2.5/forecast/hourly"

LAT = 32.90
LON = -97.03

def fetch_weather_data():
    # Get tomorrow's date in YYYYMMDD format
    tomorrow_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    filename = f'weather_data_{tomorrow_date}.csv'
    
    # Construct the full API URL
    url = f"{BASE_URL}?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
    print(url)

    # Make the API call
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        weather_data = response.json()  # Parse the JSON response
        
        # Prepare CSV file to write data
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write the header row
            writer.writerow([ 'year', 'month', 'day', 'closest_hour_crs_dep', 'temp', 'pressure', 'humidity', 'wind_speed', 'wind_deg', 'weather_id'])
            
            # Extract relevant details from each forecast
            for forecast in weather_data["list"]:
                timestamp = forecast["dt"]
                temp = forecast["main"]["temp"]
                pressure = forecast["main"]["pressure"]
                humidity = forecast["main"]["humidity"]
                wind_speed = forecast["wind"]["speed"]
                wind_deg = forecast["wind"]["deg"]
                weather_id = forecast["weather"][0]["id"]
                
                # Convert timestamp to year, month, and day
                dt = datetime.utcfromtimestamp(timestamp)
                year = dt.year
                month = dt.month
                day = dt.day
                hour = dt.hour

                # Write the data to the CSV
                writer.writerow([year, month, day, hour, temp, pressure, humidity, wind_speed, wind_deg, weather_id])

        print(f"Data has been written to {filename}.")
    else:
        print(f"Error: Unable to fetch data. Status Code: {response.status_code}")
