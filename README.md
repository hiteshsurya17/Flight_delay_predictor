# Flight_delay_predictor
![FlightDelay drawio](https://github.com/user-attachments/assets/6fd43a86-c8c4-407c-b48e-d6ee3b8c3938)

✈️ DFW Flight Delay Prediction System
This project explores the impact of weather on flight delays using machine learning. Historical flight performance data from the U.S. Bureau of Transportation Statistics (BTS) and historical weather data from the OpenWeather API (specific to DFW Airport) were collected and hosted on AWS S3. An EMR Spark job was used to preprocess the data by filtering DFW departures, integrating weather features, and preparing the dataset for modeling.

The processed data was used to train multiple classification models to predict flight delays, with a specific focus on identifying delays caused by weather conditions. While overall prediction accuracy is limited due to the complexity of flight delay factors, the research emphasizes the role of weather in such delays.

A Flask-based web application was developed to serve real-time predictions. It scrapes upcoming DFW flight data and fetches weather forecasts from OpenWeather, processes them through the trained model, and returns predictions. Users can search for a specific flight using a search bar or scroll through a list of upcoming flights. A separate model statistics page visualizes the accuracy of yesterday's predictions using bar charts.
