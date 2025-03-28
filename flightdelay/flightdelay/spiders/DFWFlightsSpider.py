import scrapy
from scrapy_playwright.page import PageMethod
from datetime import datetime, timedelta
import time
import pytz
import csv
from fake_useragent import UserAgent


class DFWFlightsSpider(scrapy.Spider):
    name = "DFWFlightsSpider"

    def __init__(self):
        # Open the CSV file for overwriting
        self.file = open('flights_for_display.csv', mode='w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow(["year", "month", "day", "day_of_week", "flight_number", "dest", "departure_time", "closest_hour_crs_dep", "op_unique_carrier"])

    def start_requests(self):
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9",
        }
        current_epoch = int(time.time())
        yield scrapy.Request(
            f'https://api.flightradar24.com/common/v1/airport.json?code=dfw&plugin[]=&plugin-setting[schedule][mode]=departures&plugin-setting[schedule][timestamp]={current_epoch}&page=-2&limit=100&fleet=&token=',
            headers=headers,
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                errback=self.close_page
            ),
            callback=self.parse
        )

    async def close_page(self, error):
        page = error.request.meta['playwright_page']
        await page.close()

    def convert_epoch_to_dallas_time(self, epoch_time):
        if epoch_time:
            dallas_tz = pytz.timezone("America/Chicago")
            dt_utc = datetime.utcfromtimestamp(epoch_time).replace(tzinfo=pytz.utc)
            dt_dallas = dt_utc.astimezone(dallas_tz)
            return dt_dallas.strftime('%Y-%m-%d %H:%M:%S %Z')
        return "N/A"

    async def parse(self, response):
        flights_info = response.json()
        departures = (
            flights_info.get("result", {})
            .get("response", {})
            .get("airport", {})
            .get("pluginData", {})
            .get("schedule", {})
            .get("departures", {})
            .get("data", [])
        )

        for flight in departures:
            flight_details = flight.get('flight', {})
            if not flight_details:
                continue

            flight_number = (
                flight_details.get('identification', {}).get('number', {}).get('default', '')
            )
            if not flight_number:
                continue

            destination = flight_details.get('airport', {}).get('destination', {}).get('code', {}).get('iata', '')
            departure_time_epoch = flight_details.get('time', {}).get('scheduled', {}).get('departure', '')
            departure_time = self.convert_epoch_to_dallas_time(departure_time_epoch)
            departure_date = departure_time.split(" ")[0]

            def closest_hour(dep_time_epoch: str):
                dep_time = datetime.strptime(dep_time_epoch.replace(" UTC", ""), "%Y-%m-%d %H:%M:%S %Z")
                hours = dep_time.hour
                minutes = dep_time.minute
                closest_hour = hours + (1 if minutes >= 30 else 0)
                if closest_hour == 24:
                    closest_hour = 0
                    dep_time += timedelta(days=1)
                return closest_hour, dep_time.year, dep_time.month, dep_time.day, (dep_time.weekday() + 1) % 7 + 1

            closest_dep_hour, year, month, day, day_of_week_spark = closest_hour(departure_time)

            row = [year, month, day, day_of_week_spark, flight_number, destination, departure_time, closest_dep_hour, flight_details.get('airline', {}).get('code', {}).get('iata', '')]
            self.writer.writerow(row)

        # Iterate through pages 2 to 25 and fetch the data
        for i in range(-1, 25):  # Page 2 to 25
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

    def closed(self, reason):
        # Close the file when the spider finishes
        self.file.close()
