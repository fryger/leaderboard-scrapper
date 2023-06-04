from webdriver_manager.chrome import ChromeDriverManager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

import os
from dotenv import load_dotenv

import re
from datetime import datetime, timedelta
import string

load_dotenv()

options = Options()
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)

driver.implicitly_wait(20)


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

    page = "https://www.strava.com/clubs/919103/members"
    driver.get(page)

    try:
        pagination_nav = driver.find_element(By.CLASS_NAME, "pagination")
    except NoSuchElementException:
        pagination_nav = None

    page_nums = re.findall(r"\d+", pagination_nav.text) if pagination_nav else ["1"]

    for page_num in page_nums:
        driver.get(page + f"?page={page_num}")
        members.update(get_members())

    return members


def list_athletes_activities(athletes):
    def get_activities(athlete):
        athlete_activities = []

        driver.get(athlete[2])

        activities = driver.find_elements(
            By.CLASS_NAME,
            "------packages-feed-ui-src-components-media-Card-Card__card--dkL_L",
        )

        for activity in activities:
            try:
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

            activity_type = activity_header_element.find_element(
                By.CLASS_NAME,
                "------packages-feed-ui-src-features-Activity-Activity__activity-icon--lq3sA",
            ).text

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

            athlete_activities.append(
                (
                    activity_id,
                    activity_timedate,
                    activity_type,
                    activity_name,
                    activity_url,
                    stats,
                )
            )

        return athlete_activities

    for athlete in athletes:
        activities = get_activities(athlete)

        for activity in activities:
            build_record(athlete, activity)


def build_record(athlete, activity):
    def normalize_str(text):
        return text.lower().translate(str.maketrans("", "", string.punctuation)).strip()

    def datetime_value(text):
        if "Yesterday" in text:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today - timedelta(days=1)
            text = text.replace("Yesterday", yesterday.strftime("%d %B %Y"))
        elif "Today" in text:
            text = text.replace("Today", datetime.now().strftime("%d %B %Y"))

        datetime_obj = datetime.strptime(text, "%d %B %Y at %H:%M")
        timestamp = datetime_obj.timestamp()

        return int(timestamp)

    def distance_value(text):
        return int(float(re.search(r"\d+\.\d+", text).group()) * 1000)

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

    record_base = {
        "id": int(activity[0]),
        "timestamp": datetime_value(activity[1]),
        "type": normalize_str(activity[2]),
        "url": activity[4],
        "title": activity[3],
        "athlete_id": athlete[1],
        "athlete_name": athlete[0],
        "athlete_url": athlete[1],
    }

    # add unsupperored strings like title: Cal, value: 275 Cal
    type_value_to_regex = {
        "distance": distance_value,
        "time": time_value,
        "pace": pace_value,
        "elev gain": elev_value,
        "steps": steps_value,
    }

    normalized_stats = [
        (normalize_str(stat[0]), type_value_to_regex[normalize_str(stat[0])](stat[1]))
        for stat in activity[5]
    ]

    record_base.update(dict(normalized_stats))

    ...


login()
athletes = list_club_members()
list_athletes_activities(athletes)
