# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

import os
from dotenv import load_dotenv

import re
from datetime import datetime, timedelta
import string
import boto3
import json
import time

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("leaderboard_activities")


load_dotenv()

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-tools")
options.add_argument("--no-zygote")
options.add_argument("--single-process")
options.add_argument("--user-data-dir=/tmp/chromium")
options.binary_location = "/opt/chromium/chrome"
# options.add_experimental_option("detach", True)

driver = webdriver.Chrome(
    executable_path="/opt/chromedriver/chromedriver",
    options=options,
    service_log_path="/tmp/chromedriver.log",
)
# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))


driver.implicitly_wait(2)


def login():
    LOGIN = os.getenv("STRAVA_USR")
    PWD = os.getenv("STRAVA_PWD")

    page = "https://www.strava.com/login"
    driver.get(page)

    driver.find_element(By.ID, "email").send_keys(LOGIN)
    driver.find_element(By.ID, "password").send_keys(PWD)

    driver.find_element(By.ID, "login-button").click()


def list_club_members():
    def get_members():
        page_members = []

        atheletes = driver.find_elements(By.CLASS_NAME, "text-headline")

        for athlete in atheletes:
            member = athlete.find_element(By.TAG_NAME, "a")

            profile_name = member.text
            profile_url = member.get_attribute("href")
            profile_id = profile_url.split("/")[-1]

            page_members.append((profile_name, profile_id, profile_url))

        return page_members

    members = set()

    clubs = [
        "https://www.strava.com/clubs/919103/members",
        "https://www.strava.com/clubs/1144460/members",
        "https://www.strava.com/clubs/1144477/members",
    ]

    for club in clubs:
        driver.get(club)

        try:
            pagination_nav = driver.find_element(By.CLASS_NAME, "pagination")
        except NoSuchElementException:
            pagination_nav = None

        page_nums = re.findall(r"\d+", pagination_nav.text) if pagination_nav else ["1"]

        for page_num in page_nums:
            driver.get(club + f"?page={page_num}")
            members.update(get_members())

    return members


def list_athletes_activities(athletes):
    def get_activities(url):
        def find_activities(wait):
            page_activities = []

            time.sleep(wait)

            activities = driver.find_elements(
                By.CLASS_NAME,
                "------packages-feed-ui-src-components-media-Card-Card__card--dkL_L",
            )

            for activity in activities:
                try:
                    # Check if feed entry is activity
                    activity.find_element(
                        By.CLASS_NAME,
                        "------packages-feed-ui-src-components-media-EntryFooter-EntryFooter__entry-footer--LFJNf",
                    )
                except NoSuchElementException:
                    continue

                activity_meta_element = activity.find_element(
                    By.CLASS_NAME,
                    "------packages-feed-ui-src-components-media-EntryHeader-EntryHeader__entry-header--y6vu8",
                )

                activity_header_element = activity.find_element(
                    By.CLASS_NAME,
                    "------packages-feed-ui-src-components-media-EntryBody-EntryBody__entry-body--vOGbj",
                )
                activity_title_element = activity_header_element.find_element(
                    By.CSS_SELECTOR,
                    "a.------packages-feed-ui-src-components-ActivityEntryBody-ActivityEntryBody__activity-name--pT7HD",
                )
                activity_stats_element = activity_header_element.find_element(
                    By.CLASS_NAME,
                    "------packages-feed-ui-src-components-ActivityEntryBody-ActivityEntryBody__stats--nkm0Y",
                )

                try:
                    activity_type = activity_header_element.find_element(
                        By.CLASS_NAME,
                        "------packages-feed-ui-src-features-Activity-Activity__activity-icon--lq3sA",
                    ).text
                except NoSuchElementException:
                    activity_type_group = (
                        activity_meta_element.find_element(
                            By.CLASS_NAME,
                            "------packages-feed-ui-src-features-GroupActivity-GroupActivity__activity-icon--eMkcT",
                        )
                        .find_element(By.TAG_NAME, "path")
                        .get_attribute("d")
                    )

                    ride_str = "M5.5 19.675a5.166 5.166 0 005.105-4.485h1.105l3.28-6.52.76 1.46a5.044 5.044 0 101.22-.57l-2.03-3.89H17a.333.333 0 01.33.33v.57h1.34V6A1.674 1.674 0 0017 4.32h-4.29l1.57 3.01H8.542L7.66 5.67h1.45l-.72-1.35H4.17l.72 1.35h1.241l1.26 2.37v.01l-.76 1.41a5.2 5.2 0 00-1.13-.135 5.175 5.175 0 100 10.35zm12.79-4.695h1.52l-2.2-4.2c.291-.073.59-.11.89-.11a3.83 3.83 0 11-3.83 3.83 3.877 3.877 0 011.7-3.19l1.92 3.67zm-4.82-6.31l-2.046 4.082-2.17-4.082h4.216zm-5.32.8l2.323 4.371H5.8l2.35-4.37zM5.5 10.675c.151.005.302.019.451.041l-1.58 2.944.79 1.53h4.1a3.822 3.822 0 11-3.76-4.515z"
                    run_str = "M21.3 18.12L14.98 6.28a2.6 2.6 0 00-4.63.07l-.46.93a.585.585 0 01-.21-.45V3.17A2.452 2.452 0 007.24.72a2.172 2.172 0 00-2.01 1.4L2.91 6.84 1.39 7.96a2.768 2.768 0 00-1.06 2.06 2.96 2.96 0 00.9 2.32l7.76 7.9a11.62 11.62 0 008.22 3.43h3.65a2.757 2.757 0 002.41-1.4l.05-.09a2.7 2.7 0 00-.01-2.73 2.665 2.665 0 00-2.01-1.33zm.85 3.39l-.05.09a1.425 1.425 0 01-1.24.73h-3.65a10.257 10.257 0 01-7.26-3.04l-7.78-7.92a1.566 1.566 0 01-.49-1.27 1.426 1.426 0 01.5-1.05l.71-.53 8.6 8.48h1.64v-.28L3.98 7.7l2.48-5.02a.848.848 0 01.78-.61 1.1 1.1 0 011.09 1.1v3.66a1.92 1.92 0 001.92 1.92h.43l.88-1.8a1.24 1.24 0 011.12-.7 1.257 1.257 0 011.11.67l1.04 1.94L12.69 10v1.52l2.77-1.47.77 1.42v.01l-2.63 1.39v1.53l3.26-1.73.74 1.37-3.02 1.6v1.53l3.65-1.94 2.06 3.85.25.36h.4a1.376 1.376 0 011.2.69 1.34 1.34 0 01.01 1.38z"
                    swim_str = "M19.99 13.33a3.7 3.7 0 01-3.32-2l-.17-.32h-1.01l-.17.32a3.763 3.763 0 01-6.65 0l-.17-.32H7.49l-.17.32a3.72 3.72 0 01-3.32 2 3.7 3.7 0 01-3.01-1.51v1.88a5.02 5.02 0 003.01.98 5.054 5.054 0 004-1.92 5.116 5.116 0 007.99 0 5.122 5.122 0 007.01.94v-1.88a3.71 3.71 0 01-3.01 1.51zm-7.99 8a3.725 3.725 0 01-3.33-2L8.49 19H7.5l-.18.33a3.7 3.7 0 01-3.32 2 3.7 3.7 0 01-3.01-1.51v1.89c.873.64 1.929.98 3.01.97a5.054 5.054 0 004-1.92 5.054 5.054 0 004 1.92 4.947 4.947 0 003-.98v-1.87a3.654 3.654 0 01-3 1.5zm8-16.02a3.735 3.735 0 01-3.33-2L16.51 3h-1.02l-.16.31a3.724 3.724 0 01-3.33 2 3.681 3.681 0 01-3-1.5V5.7a5.04 5.04 0 003 .96 5.024 5.024 0 004-1.92 5.023 5.023 0 004 1.92 5.124 5.124 0 003-.95v-1.9a3.654 3.654 0 01-3 1.5z"
                    walk_str = "M8.33 17.33H5.67v1.34h2.66zm4 0H9.67v1.34h2.66zm4 0h-2.66v1.34h2.66z"
                    inline_skate_str = "M2.98 23.67a2.664 2.664 0 10-.01-5.328 2.664 2.664 0 00.01 5.328zm0-3.98a1.32 1.32 0 110 2.64 1.32 1.32 0 010-2.64zm15.36 1.32a2.665 2.665 0 105.33-.01 2.665 2.665 0 00-5.33.01zm3.99 0a1.32 1.32 0 11-1.32-1.32 1.333 1.333 0 011.32 1.32zm-10 0a2.67 2.67 0 105.34 0 2.67 2.67 0 00-5.34 0zm3.99 0A1.32 1.32 0 1115 19.69a1.333 1.333 0 011.32 1.32zm-10 0a2.67 2.67 0 105.34 0 2.67 2.67 0 00-5.34 0zm3.99 0a1.32 1.32 0 11-2.641 0 1.32 1.32 0 012.64 0zm-9.11-4.9a3.754 3.754 0 002.89 1.35h15.42a3.188 3.188 0 003.18-3.18 2.5 2.5 0 00-1.32-2.2L10.7 6.37l.67-3.56A2.09 2.09 0 009.3.33H7.23l-1.34 2H2.22L.36 13.02a3.764 3.764 0 00.84 3.09zm19.53-2.84a1.14 1.14 0 01.61 1.01 1.83 1.83 0 01-1.83 1.83h-2.023l1.857-3.578 1.386.738zM3.35 3.67h3.26l1.34-2H9.3a.739.739 0 01.58.28.755.755 0 01.16.61l-.661 3.5h-2.43v1.35h2.829l3.8 2.036L12.1 12.33h1.52l1.15-2.24 3.384 1.8-2.189 4.22H8.326a4.463 4.463 0 00-4.451-4.31H1.939L3.35 3.67zm-1.66 9.58l.019-.1h2.166a3.113 3.113 0 013.1 2.957H4.09a2.446 2.446 0 01-2.4-2.86v.003z"
                    mtb_str = "M5.07 10.17h-.96l-.675-1.35h3.5l.675 1.35H6.54l1.432 3.342 6.196-1.966-.588-1.266 3.43-.933v1.393l-1.543.414 1.55 3.098a4.68 4.68 0 016.663 4.228 4.78 4.78 0 01-.34 1.75A4.65 4.65 0 0119 23.15a4.67 4.67 0 01-4.432-6.14h1.46a3.32 3.32 0 106.052 2.72 3.17 3.17 0 00.25-1.25A3.33 3.33 0 0019 15.16a3.32 3.32 0 00-1.377.301l1.51 3.019h-1.509l-2.17-4.334-5.184 6.604-1.024-.28A4.65 4.65 0 015 23.15a4.67 4.67 0 010-9.34v1.35a3.32 3.32 0 102.917 4.949l-2.897-.79V17.48h-.003l2.624-1.314-2.57-5.996zm5.554 3.917l4.143-1.314.021.041-4.605 5.858-.799-1.864L11.4 15.8zM6.4 18.3l1.775-.887.663 1.547zm3.23-3.13l-.304-.671-.82.26.344.802.78-.39z"

                    if activity_type_group == ride_str:
                        activity_type = "Ride"

                    elif activity_type_group == run_str:
                        activity_type = "Run"

                    elif activity_type_group == swim_str:
                        activity_type = "Swim"

                    elif activity_type_group == walk_str:
                        activity_type = "Walk"

                    elif activity_type_group == inline_skate_str:
                        activity_type = "Inline Skate"

                    elif activity_type_group == mtb_str:
                        activity_type = "Mountain Bike Ride"

                    else:
                        continue

                activity_timedate = activity_meta_element.find_element(
                    By.CSS_SELECTOR, 'time[data-testid="date_at_time"]'
                ).text

                activity_name = activity_title_element.text
                activity_url = activity_title_element.get_attribute("href")
                activity_id = activity_url.split("/")[-1]

                stats_labels = [
                    stat_label.text
                    for stat_label in activity_stats_element.find_elements(
                        By.CLASS_NAME,
                        "------packages-feed-ui-src-components-ActivityEntryBody-ActivityEntryBody__stat-label--DjJOy",
                    )
                ]
                stats_values = [
                    stat_value.text
                    for stat_value in activity_stats_element.find_elements(
                        By.CLASS_NAME,
                        "------packages-ui-Stat-styles-module__statValue--O3TZD",
                    )
                ]

                stats = set(zip(stats_labels, stats_values))

                page_activities.append(
                    (
                        activity_id,
                        activity_timedate,
                        activity_type,
                        activity_name,
                        activity_url,
                        stats,
                    )
                )

            return page_activities

        driver.get(url)

        try:
            athlete_activities = find_activities(2)

        except StaleElementReferenceException:
            athlete_activities = find_activities(3)

        return athlete_activities

    def generate_activities_urls(athlete):
        activities_urls = []

        END_WEEK = datetime.today().isocalendar().week
        START_WEEK = END_WEEK - 1

        for i in range(START_WEEK, END_WEEK + 1):
            activities_urls.append(
                f"{athlete[2]}#interval?interval=2023{i}&interval_type=week&chart_type=miles&year_offset=0"
            )

        return activities_urls

    for athlete_num, athlete in enumerate(athletes):
        driver.get(athlete[2])
        activities = []

        activities_urls = generate_activities_urls(athlete)

        for url in activities_urls:
            partial_activity = get_activities(url)

            activities.extend(partial_activity) if partial_activity else None

        for activity_num, activity in enumerate(activities):
            print(athlete_num, activity_num, len(athletes), len(activities))

            record = build_record(athlete, activity)
            upload_activity(record)


def upload_activity(record):
    try:
        table.put_item(Item=record)
    except Exception as e:
        print(e)


def build_record(athlete, activity):
    def normalize_str(text):
        return text.lower().translate(str.maketrans("", "", string.punctuation)).strip()

    def datetime_value(text):
        if "Yesterday" in text:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today - timedelta(days=1)
            text = text.replace("Yesterday", yesterday.strftime("%B %d, %Y"))
        elif "Today" in text:
            text = text.replace("Today", datetime.now().strftime("%B %d, %Y"))

        for fmt in ("%B %d, %Y at %I:%M %p", "%d %B %Y at %H:%M", "%B %d, %Y at %H:%M"):
            try:
                datetime_obj = datetime.strptime(text, fmt)
            except ValueError:
                pass

        timestamp = datetime_obj.timestamp()

        return int(timestamp)

    def distance_value(text):
        pattern = r"\d+\.?\d*"
        match = re.search(pattern, text)

        if match:
            number = float(match.group())

            if "km" in text:
                meters = int(number * 1000)
                return meters
            elif "m" in text:
                return int(number)

        return None

    def speed_value(text):
        return float(re.search(r"\d+\.\d+", text).group())

    def time_value(text):
        hours = int(v.group(1)) * 3600 if (v := re.search(r"(\d+)h", text)) else 0
        minutes = int(v.group(1)) * 60 if (v := re.search(r"(\d+)m", text)) else 0
        seconds = int(v.group(1)) if (v := re.search(r"(\d+)s", text)) else 0

        return hours + minutes + seconds

    def pace_value(text):
        number_matched = re.search(r"(\d+):(\d+)", text)
        minutes = int(number_matched.group(1)) * 60
        seconds = int(number_matched.group(2))

        return minutes + seconds

    def elev_value(text):
        return int(re.sub(r"[^\d]", "", text))

    def steps_value(text):
        return int(re.sub(r"[^\d]", "", text))

    def cal_value(text):
        return int(re.sub(r"[^\d]", "", text))

    def avg_temp_value(text):
        return re.search(r"-?\d+", text).group()

    def hr_value(text):
        return int(re.sub(r"[^\d]", "", text))

    record_base = {
        "id": str(activity[0]),
        "timestamp": str(datetime_value(activity[1])),
        "type": str(normalize_str(activity[2])),
        "url": str(activity[4]),
        "title": str(activity[3]),
        "athlete_id": str(athlete[1]),
        "athlete_name": str(athlete[0]),
        "athlete_url": str(athlete[2]),
    }

    type_value_to_regex = {
        "distance": distance_value,
        "time": time_value,
        "pace": pace_value,
        "elev gain": elev_value,
        "steps": steps_value,
        "cal": cal_value,
        "speed": speed_value,
        "avg temp": avg_temp_value,
        "avg hr": hr_value,
        "max hr": hr_value,
    }

    try:
        normalized_stats = [
            (
                normalize_str(stat[0]),
                str(type_value_to_regex[normalize_str(stat[0])](stat[1])),
            )
            for stat in activity[5]
        ]
    except KeyError:
        return None

    record_base.update(dict(normalized_stats))

    return record_base


def lambda_handler(event, context):
    login()
    athletes = list_club_members()
    list_athletes_activities(athletes)


if __name__ == "__main__":
    login()
    athletes = list_club_members()
    list_athletes_activities(athletes)
