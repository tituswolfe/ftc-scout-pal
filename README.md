# ScoutPal

ScoutPal calculates advanced statistics (EPA & SOS) and uses Discord webhook integration to supercharge your FIRST Tech Challenge scouting on the fly!



## Requirements

- **Python 3.10** or higher
- **Pip** (Python package manager)
- **Git**
- **Discord Webhook URL** (with "Manage Webhooks" permissions). 
## Installation

### 1. Clone repository

```bash
git clone https://github.com/tituswolfe/ftc-scout-pal
cd ftc-scout-pal
```

### Recomended: Setup virtual environment (keep dependencies isolated)
```bash
# Create the environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

```
    
### 2. Install all required packages using pip

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure the project

1. Locate the config.example.yaml file in the root directory.

2. Create a copy named config.yaml:
```bash
cp config.example.yaml config.yaml
```
3. Open config.yaml and fill in your specific settings and credentials

NOTE: You will need an active Discord Webhook URL. 

Go to the channel you want to use.

Channel > Edit Channel > Integrations > Webhooks

Click "New Webhook" and copy webhook url.

```yaml
webhook_url: "YOUR_WEBHOOK_URL"
season: "2025"
event_code: "FTCCMP1EDIS"
include_penalties: True
update_interval_seconds: 300 # 5 minutes
```
## Usage/Examples

### Generate CSV File for Event

1. Go to [FTC Scout](https://ftcscout.org/) and find the event you want to scout.

Example: https://ftcscout.org/events/2025/FTCCMP1EDIS/matches
```
Season: 2025
Event Code: FTCCMP1EDIS
```

Note: ScoutPal only calculates data from qualifier matches, playoffs are not included (due to easily skewing EPA and OPR ratings).

2. Run generate_event_statistics.py

```bash
python3 generate_event_statistics.py --season [SEASON] --event [EVENT_CODE] --penalties ["yes", "no"]
```

Example
```bash
python3 generate_event_statistics.py --season 2025 --event FTCCMP1EDIS --penalties yes
```

3. Open geneated CSV File

You can open the generated CSV in your spreedsheet editor of choice. 

Example of generated CSV file structure:
```file
[SEASON]_[EVENT_CODE]_statistics.csv
```


### Send CSV File to Discord on Intervals

1. Go to [FTC Scout](https://ftcscout.org/) and find the event you want to scout.

Example: https://ftcscout.org/events/2025/FTCCMP1EDIS/matches
```
Season: 2025
Event Code: FTCCMP1EDIS
```

2. Update config.yaml
```yaml
webhook_url: "YOUR_WEBHOOK_URL"
season: "2025" # <- Your event season
event_code: "FTCCMP1EDIS" # <- Your event code
include_penalties: True
update_interval_seconds: 300 # 5 minutes
```

3. Run discord_reporter.py

```bash
python3 discord_reporter.py
```

Leave script running to get statistics to Discord on interval.



## Authors

Built for 9808 Team Chargers.

Special thanks to the MO/KS FTC community for the encouragement and help!

- [@Titus](https://github.com/tituswolfe)
- [@Ryan (Alum)](https://github.com/RyanMichalak9808) 

