import scrapy
from scrapy_playwright.page import PageMethod
from datetime import datetime, timedelta
import pytz
import time
import csv

class DFWFlightsDelaysYesterday(scrapy.Spider):
    name = "DFWFlightsDelaysYesterday"
    
    def start_requests(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        # Get yesterday's date in epoch timestamp
        dallas_tz = pytz.timezone("America/Chicago")
        yesterday = datetime.now(dallas_tz) - timedelta(days=1)
        self.yesterday_str = yesterday.strftime("%Y-%m-%d")  # Store string format for filename
        current_epoch = int(time.time())

        # Open CSV file and write headers
        self.filename = f'flight_delays_{self.yesterday_str}.csv'
        with open(self.filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["date", "flight_number", "destination", "scheduled_departure", "actual_departure", "delayed"])

        # Start requests
        print(f'https://api.flightradar24.com/common/v1/airport.json?code=dfw&plugin[]=&plugin-setting[schedule][mode]=departures&plugin-setting[schedule][timestamp]={current_epoch}&page=-1&limit=100&fleet=&token=')
        yield scrapy.Request(
            f'https://api.flightradar24.com/common/v1/airport.json?code=dfw&plugin[]=&plugin-setting[schedule][mode]=departures&plugin-setting[schedule][timestamp]={current_epoch}&page=-1&limit=100&fleet=&token=',
            headers=headers,
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                errback=self.close_page
            )
        )

    async def close_page(self, error):
        page = error.request.meta['playwright_page']
        await page.close()

    def convert_epoch_to_dallas_time(self, epoch_time):
        """Convert epoch timestamp to Dallas local time."""
        if epoch_time:
            dallas_tz = pytz.timezone("America/Chicago")
            dt_utc = datetime.utcfromtimestamp(epoch_time).replace(tzinfo=pytz.utc)
            dt_dallas = dt_utc.astimezone(dallas_tz)
            return dt_dallas.strftime('%Y-%m-%d %H:%M:%S %Z')
        return "N/A"

    def calculate_delay(self, scheduled_epoch, actual_epoch):
        """Calculate if a flight is delayed by more than 15 minutes."""
        if scheduled_epoch and actual_epoch:
            return (actual_epoch - scheduled_epoch) > 900  # 15 minutes in seconds
        return False

    async def parse(self, response):
        print('Processing response...')
        flights_info = response.json()
        departures = (
            flights_info.get("result", {}).get("response", {}).get("airport", {})
            .get("pluginData", {}).get("schedule", {}).get("departures", {}).get("data", [])
        )

        data_list = []
        
        for flight in departures:
            flight_details = flight.get('flight', {})
            if not flight_details:
                continue

            flight_number = flight_details.get('identification', {}).get('number', {}).get('default', '')
            if not flight_number:
                continue
            
            destination = flight_details.get('airport', {}).get('destination', {}).get('code', {}).get('iata', '')
            scheduled_dep_epoch = flight_details.get('time', {}).get('scheduled', {}).get('departure', None)
            actual_dep_epoch = flight_details.get('time', {}).get('real', {}).get('departure', None)
            
            # Skip flights without actual departure time
            if actual_dep_epoch is None:
                continue

            scheduled_dep = self.convert_epoch_to_dallas_time(scheduled_dep_epoch)
            actual_dep = self.convert_epoch_to_dallas_time(actual_dep_epoch)
            delayed = self.calculate_delay(scheduled_dep_epoch, actual_dep_epoch)

            data_list.append([
                self.yesterday_str, flight_number, destination, scheduled_dep, actual_dep, delayed
            ])

        # Append to CSV file
        with open(self.filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(data_list)

        print(f"Saved data to {self.filename}")

        # Iterate through additional pages
        for i in range(-2, -25, -1):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            current_epoch = int(time.time())

            yield scrapy.Request(
                f'https://api.flightradar24.com/common/v1/airport.json?code=dfw&plugin[]=&plugin-setting[schedule][mode]=departures&plugin-setting[schedule][timestamp]={current_epoch}&page={i}&limit=100&fleet=&token=',
                headers=headers,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    errback=self.close_page
                ),
                callback=self.parse
            )
