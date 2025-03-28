import matplotlib
matplotlib.use('Agg')  # Use the Agg backend to avoid GUI-related issues
import matplotlib.pyplot as plt
import io
from apscheduler.schedulers.background import BackgroundScheduler
import time
import subprocess
import base64
import os
from flask import Flask, render_template, jsonify
import json
import pandas as pd
from datetime import datetime, timedelta
import openweather_data 
import preparing_forecast_data
import delay_forecasting

app = Flask(__name__)

def fetch_display_data():
    print(f"Scrapy spiders started at {datetime.now()}")
    original_dir = os.getcwd()
    # Change directory to where the Scrapy project is located
    os.chdir('flightdelay')  # Make sure this path is correct

    # Run the first Scrapy spider (DFWFlightsSpider)
    try:
        subprocess.run(['scrapy', 'crawl', 'DFWFlightsSpider'], check=True)
        print("DFWFlightsSpider finished successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running DFWFlightsSpider: {e}")

    os.chdir(original_dir)
    print(f'Preparing forecast data for the flights to be displayed at {datetime.now()}')
    preparing_forecast_data.combine_flight_weather_data()

    print(f'preparing delay delay predictions for the flights to be displayed at {datetime.now()}')
    delay_forecasting.predict_flight_delays()


def fetch_flights_stats_data():
    original_dir = os.getcwd()
    os.chdir('flightdelay')  

    try:
        subprocess.run(['scrapy', 'crawl', 'DFWFlightsDelaysYesterday'], check=True)
        print("DFWFlightsDelaysYesterday finished successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running DFWFlightsDelaysYesterday: {e}")
    
    print("Waiting for 10 seconds before running the next spider...")
    time.sleep(10)
    # Run the second Scrapy spider (DFWFlightsYesterday)
    try:
        subprocess.run(['scrapy', 'crawl', 'DFWFlightsyesterday'], check=True)
        print("DFWFlightsyesterday finished successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error running DFWFlightsyesterday: {e}")

    os.chdir(original_dir)
    print(f'Preparing forecast data for yesterdays flights at {datetime.now()}')
    yesterdays_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    preparing_forecast_data.combine_flight_weather_data_for_date(yesterdays_date)

    print(f'preparing flight delay predictions for yesterdays flights at {datetime.now()}')
    delay_forecasting.predict_flight_delays_for_date(yesterdays_date)
    

def weather_data_fetch_job():
    print(f"Running weather data fetch job at {datetime.now()}")
    openweather_data.fetch_weather_data()  # Call the function from openweather_data.py

def delete_old_files():
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    day_before_yesterday = today - timedelta(days=2)
    day_before_yesterday_date_str = day_before_yesterday.strftime('%Y-%m-%d')
    yesterday = today - timedelta(days=1)
    yesterday_date_str = yesterday.strftime('%Y-%m-%d')

    # Define files that should NOT be deleted
    keep_csv_files = {
        "flights_for_display.csv",
        f"flights_{yesterday_date_str}.csv",
        f"flight_delays_{yesterday_date_str}.csv",
        f"flight_delays_{day_before_yesterday_date_str}.csv",
        "combined_flight_weather_data.csv",
        f"combined_flight_weather_data_{yesterday_date_str}.csv",
        f"combined_flight_weather_{yesterday_date_str}.csv",
        f"weather_data_{today_str}.csv",
        f"weather_data_{yesterday_date_str}.csv",
    }

    keep_json_files = {
        "flight_delay_predictions.json",
        f"flight_delay_predictions_{yesterday_date_str}.json",
        f"flight_delay_predictions_{day_before_yesterday_date_str}.json",
    }

    # Delete unnecessary CSV files in 'flightdelay' directory
    flightdelay_dir = "flightdelay"
    if os.path.exists(flightdelay_dir):
        for file in os.listdir(flightdelay_dir):
            if file.endswith(".csv") and file not in keep_csv_files:
                os.remove(os.path.join(flightdelay_dir, file))
                print(f"Deleted old CSV file: {file}")

    # Delete unnecessary CSV and JSON files in the main directory
    main_dir = os.getcwd()
    for file in os.listdir(main_dir):
        file_path = os.path.join(main_dir, file)

        # Delete old CSV files
        if file.endswith(".csv") and file not in keep_csv_files:
            os.remove(file_path)
            print(f"Deleted old CSV file: {file}")

        # Delete old JSON files
        elif file.endswith(".json") and file not in keep_json_files:
            os.remove(file_path)
            print(f"Deleted old JSON file: {file}")

    print("Old files cleanup completed.")

scheduler = BackgroundScheduler(daemon=True)

scheduler.add_job(delete_old_files, 'cron', hour=1, minute=0)  

scheduler.add_job(fetch_display_data, 'cron', hour=0, minute=30)  

scheduler.add_job(fetch_flights_stats_data, 'cron', hour=0, minute=5)  

# Schedule the weather data fetch job to run every day at 6 PM
scheduler.add_job(weather_data_fetch_job, 'cron', hour=18, minute=0)  # Run weather data job at 6 PM

scheduler.start()

def load_flight_data(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.route('/flights', methods=['GET'])
def get_flights():
    flights = load_flight_data(f'flight_delay_predictions.json')
    return jsonify(flights)

def load_flight_delays(filename):
    try:
        return pd.read_csv(filename)
    except FileNotFoundError:
        return pd.DataFrame()

@app.route("/flight-statistics")
def flight_statistics():
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_date_str = yesterday.strftime('%Y-%m-%d')  # Format the date as 'YYYY-MM-DD'

    day_before_yesterday = datetime.now() - timedelta(days=2)
    day_before_yesterday_date_str = day_before_yesterday.strftime('%Y-%m-%d')
    
    print(f"Yesterday's date (formatted): {yesterday_date_str}")

    predictions_file = f"flight_delay_predictions_{yesterday_date_str}.json"
    delays_file = f"flightdelay/flight_delays_{yesterday_date_str}.csv"

    # Check if yesterday's data exists, else fallback to day before yesterday
    if not (os.path.exists(predictions_file) and os.path.exists(delays_file)):
        print(f"Yesterday's data not found. Using data from {day_before_yesterday_date_str}.")
        predictions_file = f"flight_delay_predictions_{day_before_yesterday_date_str}.json"
        delays_file = f"flightdelay/flight_delays_{day_before_yesterday_date_str}.csv"

    predictions = load_flight_data(predictions_file)
    delays = load_flight_delays(delays_file)

    
    print(f"Predictions data loaded: {len(predictions)} records")
    print(f"Delays data loaded: {len(delays)} records")

    # Merge data
    predictions_df = pd.DataFrame(predictions)
    delays_df = delays[['flight_number', 'delayed']]  # Keep only relevant columns for merge
    merged_df = pd.merge(predictions_df, delays_df, how="inner", on="flight_number")
    
    # Filter for flights predicted as delayed
    predicted_delayed_df = merged_df[merged_df['AI Delay Prediction'] == "Yes"]

    # Calculate statistics
    predicted_delayed_flights = len(predicted_delayed_df)
    actually_delayed_flights = predicted_delayed_df['delayed'].sum()
    not_delayed_flights = predicted_delayed_flights - actually_delayed_flights

    # Calculate accuracy percentage and round to 2 decimal places
    accuracy_percentage = round((actually_delayed_flights / predicted_delayed_flights * 100), 2) if predicted_delayed_flights > 0 else 0

    total_flights_scheduled = len(delays_df)  # Total flights scheduled on yesterday's date

    # Create bar chart for prediction accuracy
    fig, ax = plt.subplots()
    ax.bar(['Actually Delayed', 'Not Actually Delayed'], 
           [actually_delayed_flights, not_delayed_flights], 
           color=['#FF6347', '#87CEFA'])
    
    ax.set_ylabel('Number of Flights')
    ax.set_title('Predicted Delayed Flights vs Actually Delayed Flights')
    ax.set_ylim(0, predicted_delayed_flights)

    # Save the bar chart to a BytesIO object
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')

    statistics = {
        'total_predicted_delayed': predicted_delayed_flights,
        'actually_delayed': actually_delayed_flights,
        'accuracy': accuracy_percentage,
        'total_flights_scheduled': total_flights_scheduled
    }
    # Calculate Delay Prediction Accuracy by Carrier
    accuracy_by_carrier = merged_df.groupby("op_unique_carrier").apply(
        lambda x: pd.Series({
            'predicted_delayed': len(x[x['AI Delay Prediction'] == "Yes"]),
            'actually_delayed': x['delayed'].sum(),
            'accuracy': round((len(x[x['AI Delay Prediction'] == "Yes"]) / x['delayed'].sum()) * 100, 2) if len(x[x['AI Delay Prediction'] == "Yes"]) > 0 else 0
        })
    ).reset_index()

    # Pass the accuracy_by_carrier dataframe to the template
    return render_template("flight_statistics.html", 
                        statistics=statistics, 
                        data=predicted_delayed_df.head(10), 
                        bar_chart=img_base64,
                        yesterday_date=yesterday_date_str,
                        accuracy_by_carrier=accuracy_by_carrier,
                        )



@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
