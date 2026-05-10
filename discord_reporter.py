import generate_event_statistics
import requests
import yaml
import time
import pandas as pd
import io
from datetime import datetime

def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)
    
def get_csv_data(data_dict):
    data_frame = pd.DataFrame(data_dict)
    csv_buffer = io.StringIO() 
    data_frame.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def send_webhook_message(message, files, webhook_url):
    payload = {
        "content": message,
        "username": "ScoutPal"
    }

    try:
        response = requests.post(webhook_url, data=payload, files=files)
        response.raise_for_status()
        print(f"Successfully sent message at {datetime.now()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

def main():
    print("Starting Discord Webhook loop!")

    while True:
        config = load_config()
        webhook_url = config['webhook_url']
        season = config['season']
        event_code = config['event_code']
        include_penalties = config['include_penalties']
        update_interval_seconds = config['update_interval_seconds']
        
        statistics = generate_event_statistics.get_statistics(season, event_code, include_penalties)

        formatted_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
        discord_message = f"## `{season} {event_code} Statisitics | {formatted_datetime}`"

        filename = f"{season}_{event_code}_{formatted_datetime}_stats.csv"
        files = {
            "file": (filename, get_csv_data(statistics))
        }

        send_webhook_message(discord_message, files, webhook_url)

        time.sleep(update_interval_seconds)

if __name__ == "__main__":
    main()