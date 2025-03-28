import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import OrdinalEncoder, LabelEncoder
from datetime import datetime

# Load the trained model and encoders
xgb_classifier = joblib.load('XGBoostClassifier3/xgboost_classifier_optimized.pkl')
label_encoders = joblib.load('XGBoostClassifier3/label_encoders_opt.pkl')
feature_encoder = joblib.load('XGBoostClassifier3/feature_encoder_opt.pkl')
carrier_weather_le = joblib.load('XGBoostClassifier3/carrier_weather_encoder.pkl')


# Function to handle unseen labels
def handle_unseen_labels(df, col, encoder):
    unseen_mask = ~df[col].isin(encoder.classes_)
    unseen_labels = df[unseen_mask].copy()
    
    # Debugging: Print which values are unknown
    unknown_values = df.loc[unseen_mask, col].unique()
    print(f"Unseen values in column '{col}': {unknown_values}")

    unseen_labels["AI Delay Prediction"] = "---"
    df_known = df[~unseen_mask].copy()

    if not df_known.empty:
        df_known[col] = encoder.transform(df_known[col])
    
    return df_known, unseen_labels

# Function to handle unseen categories, applied to all categorical features at once
def handle_unseen_categories(df, categorical_features, encoder):
    df_categorical = df[categorical_features].astype(str)  # Ensure all values are strings
    
    df_known = df.copy()
    unseen_labels_list = []

    unseen_mask = np.zeros(len(df), dtype=bool)

    for col in categorical_features:
        feature_unseen_mask = ~df[col].isin(encoder.categories_[encoder.feature_names_in_.tolist().index(col)])
        unseen_mask |= feature_unseen_mask
        
        # Debugging: Print which values are unknown
        unknown_values = df.loc[feature_unseen_mask, col].unique()
        print(f"Unseen values in categorical column '{col}': {unknown_values}")

    unseen_labels = df[unseen_mask].copy()
    unseen_labels["AI Delay Prediction"] = "---"
    df_known = df[~unseen_mask].copy()
    
    if not df_known.empty:
        df_known[categorical_features] = encoder.transform(df_known[categorical_features])

    unseen_labels_list.append(unseen_labels)
    unseen_labels = pd.concat(unseen_labels_list, ignore_index=True)
    df_known[categorical_features] = df_known[categorical_features].astype('category')

    return df_known, unseen_labels


def predict_flight_delays_for_date(date):
    df = pd.read_csv(f'combined_flight_weather_data_{date}.csv')
    print(f'Length before dropping duplicates: {len(df)}')
    df = df.drop_duplicates()
    print(f'Total flights after dropping duplicates: {len(df)}')
    
    df.dropna(subset=["op_unique_carrier", "dest", "flight_number", "weather_id", "temp"], inplace=True)
    print(f"Rows after dropna: {df.shape[0]}")

    df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['hour_sin'] = np.sin(2 * np.pi * df['closest_hour_crs_dep'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['closest_hour_crs_dep'] / 24)
    df.drop(['day_of_week', 'month', 'closest_hour_crs_dep'], axis=1, inplace=True)

    df_known = df.copy()
    unseen_labels_list = []

    # Handle unseen labels for categorical features
    for col in ['op_unique_carrier', 'dest', 'flight_number']:
        le = label_encoders[col]
        df_known, unseen_labels = handle_unseen_labels(df_known, col, le)
        unseen_labels_list.append(unseen_labels)
        print(f"Total unseen records for '{col}': {len(unseen_labels)}")
        if df_known.shape[0] == 0:
            print(f"No known data for {col}, skipping encoding.")
        else:
            df_known[col] = df_known[col].astype('category')

    # Handle unseen labels for the 'carrier_weather' feature
    df_known['carrier_weather'] = df_known['op_unique_carrier'].astype(str) + "_" + df_known['weather_id'].astype(str)
    df_known, unseen_labels = handle_unseen_labels(df_known, 'carrier_weather', carrier_weather_le)
    unseen_labels_list.append(unseen_labels)
    print(f"Total unseen records for 'carrier_weather': {len(unseen_labels)}")

    if df_known.shape[0] == 0:
        print(f"No known data for carrier_weather, skipping encoding.")
    df_known['carrier_weather'] = df_known['carrier_weather'].astype('category')

    # Handle unseen categories for categorical features
    categorical_features = ['weather_id', 'wind_deg', 'year', 'day']
    if df_known[categorical_features].shape[0] > 0:
        df_known, unseen_labels = handle_unseen_categories(df_known, categorical_features, feature_encoder)
        unseen_labels_list.append(unseen_labels)
        print(f"Total unseen records for categorical features: {len(unseen_labels)}")
    else:
        print(f"Data for categorical features {categorical_features} is empty, skipping transformation.")

    # Prepare data for prediction
    features = ['year', 'day', 'op_unique_carrier', 'flight_number', 'dest', 'temp', 'pressure',
                'humidity', 'wind_speed', 'wind_deg', 'weather_id', 
                'day_of_week_sin', 'day_of_week_cos', 'month_sin', 'month_cos', 'hour_sin', 'hour_cos', 'carrier_weather']
    X_new = df_known[features]

    for col in ['op_unique_carrier']:
        X_new[col] = X_new[col].astype('category')

    y_probs = xgb_classifier.predict_proba(X_new)[:, 1]
    best_threshold = 0.40
    y_pred_tuned = (y_probs >= best_threshold).astype(int)

    # Preserve original index before transformations
    df_known['original_index'] = df_known.index

    # Prepare final dataset
    df_known['AI Delay Prediction'] = ['Yes' if pred == 1 else 'No' for pred in y_pred_tuned]

    unseen_labels_combined = pd.concat(unseen_labels_list, ignore_index=True) if unseen_labels_list else pd.DataFrame()
    df_final = pd.concat([df_known, unseen_labels_combined], ignore_index=False)    


    # Ensure original_index is unique before merging
    df_final = df_final.drop_duplicates(subset=['original_index'])

    # Merge predictions back to original dataframe using index alignment
    df['AI Delay Prediction'] = df_final.set_index('original_index').reindex(df.index)['AI Delay Prediction']


    # Count predictions
    prediction_counts = df['AI Delay Prediction'].value_counts()
    print(f"Number of 'Yes': {prediction_counts.get('Yes', 0)}")
    print(f"Number of 'No': {prediction_counts.get('No', 0)}")
    print(f"Number of '---': {prediction_counts.get('---', 0)}")

    # Save results
    df.to_json(f'flight_delay_predictions_{date}.json', orient='records')
    print(f"Predictions added to flight_delay_predictions_{date}.json")

def predict_flight_delays():
    df = pd.read_csv(f'combined_flight_weather_data.csv')
    print(f'Length before dropping duplicates: {len(df)}')
    df = df.drop_duplicates()
    print(f'Total flights after dropping duplicates: {len(df)}')
    
    df.dropna(subset=["op_unique_carrier", "dest", "flight_number", "weather_id", "temp"], inplace=True)
    print(f"Rows after dropna: {df.shape[0]}")

    df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['hour_sin'] = np.sin(2 * np.pi * df['closest_hour_crs_dep'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['closest_hour_crs_dep'] / 24)
    df.drop(['day_of_week', 'month', 'closest_hour_crs_dep'], axis=1, inplace=True)

    df_known = df.copy()
    unseen_labels_list = []

    # Handle unseen labels for categorical features
    for col in ['op_unique_carrier', 'dest', 'flight_number']:
        le = label_encoders[col]
        df_known, unseen_labels = handle_unseen_labels(df_known, col, le)
        unseen_labels_list.append(unseen_labels)
        print(f"Total unseen records for '{col}': {len(unseen_labels)}")
        if df_known.shape[0] == 0:
            print(f"No known data for {col}, skipping encoding.")
        else:
            df_known[col] = df_known[col].astype('category')

    # Handle unseen labels for the 'carrier_weather' feature
    df_known['carrier_weather'] = df_known['op_unique_carrier'].astype(str) + "_" + df_known['weather_id'].astype(str)
    df_known, unseen_labels = handle_unseen_labels(df_known, 'carrier_weather', carrier_weather_le)
    unseen_labels_list.append(unseen_labels)
    print(f"Total unseen records for 'carrier_weather': {len(unseen_labels)}")

    if df_known.shape[0] == 0:
        print(f"No known data for carrier_weather, skipping encoding.")
    df_known['carrier_weather'] = df_known['carrier_weather'].astype('category')

    # Handle unseen categories for categorical features
    categorical_features = ['weather_id', 'wind_deg', 'year', 'day']
    if df_known[categorical_features].shape[0] > 0:
        df_known, unseen_labels = handle_unseen_categories(df_known, categorical_features, feature_encoder)
        unseen_labels_list.append(unseen_labels)
        print(f"Total unseen records for categorical features: {len(unseen_labels)}")
    else:
        print(f"Data for categorical features {categorical_features} is empty, skipping transformation.")

    # Prepare data for prediction
    features = ['year', 'day', 'op_unique_carrier', 'flight_number', 'dest', 'temp', 'pressure',
                'humidity', 'wind_speed', 'wind_deg', 'weather_id', 
                'day_of_week_sin', 'day_of_week_cos', 'month_sin', 'month_cos', 'hour_sin', 'hour_cos', 'carrier_weather']
    X_new = df_known[features]

    for col in ['op_unique_carrier']:
        X_new[col] = X_new[col].astype('category')

    y_probs = xgb_classifier.predict_proba(X_new)[:, 1]
    best_threshold = 0.40
    y_pred_tuned = (y_probs >= best_threshold).astype(int)

    # Preserve original index before transformations
    df_known['original_index'] = df_known.index

    # Prepare final dataset
    df_known['AI Delay Prediction'] = ['Yes' if pred == 1 else 'No' for pred in y_pred_tuned]

    unseen_labels_combined = pd.concat(unseen_labels_list, ignore_index=True) if unseen_labels_list else pd.DataFrame()
    df_final = pd.concat([df_known, unseen_labels_combined], ignore_index=False)    


    # Ensure original_index is unique before merging
    df_final = df_final.drop_duplicates(subset=['original_index'])

    # Merge predictions back to original dataframe using index alignment
    df['AI Delay Prediction'] = df_final.set_index('original_index').reindex(df.index)['AI Delay Prediction']


    # Count predictions
    prediction_counts = df['AI Delay Prediction'].value_counts()
    print(f"Number of 'Yes': {prediction_counts.get('Yes', 0)}")
    print(f"Number of 'No': {prediction_counts.get('No', 0)}")
    print(f"Number of '---': {prediction_counts.get('---', 0)}")

    # Save results
    df.to_json(f'flight_delay_predictions.json', orient='records')
    print(f"Predictions added to flight_delay_predictions.json")


