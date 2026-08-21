"""Fetch KunstLab Varde PLAY bookings from SpeedAdmin and publish them as an ICS feed."""
import datetime
import os
import sys
import tempfile
import zoneinfo

import requests
from icalendar import Calendar, Event, vText

API_BASE = "https://api.speedadmin.dk/v1"
SCHOOL_ID = 6655
EXTRA_ROOM_IDS = [10225, 10233]
SCHOOL_NAME = "KunstLab Varde"
TIMEZONE = zoneinfo.ZoneInfo("Europe/Copenhagen")
DAYS_PAST = 7
DAYS_FUTURE = 360
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "kunstlab-varde.ics")


def fetch_bookings(api_key: str, **filters) -> list[dict]:
    now = datetime.datetime.now(TIMEZONE)
    body = {
        "DateFrom": (now - datetime.timedelta(days=DAYS_PAST)).isoformat(),
        "DateTo": (now + datetime.timedelta(days=DAYS_FUTURE)).isoformat(),
        **filters,
    }
    response = requests.post(
        f"{API_BASE}/playbooking",
        json=body,
        headers={"Authorization": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_all_bookings(api_key: str) -> list[dict]:
    # separate calls per filter since CourseSchoolIds/RoomIds combine with AND, not OR
    school_bookings = fetch_bookings(api_key, CourseSchoolIds=[SCHOOL_ID])
    room_bookings = fetch_bookings(api_key, RoomIds=EXTRA_ROOM_IDS)
    print(f"CourseSchoolIds=[{SCHOOL_ID}] -> {len(school_bookings)} bookings", file=sys.stderr)
    print(f"RoomIds={EXTRA_ROOM_IDS} -> {len(room_bookings)} bookings", file=sys.stderr)
    merged = {b["BookingId"]: b for b in school_bookings + room_bookings}
    return list(merged.values())


def build_calendar(bookings: list[dict]) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//SpeedAdmin Booking Sync//kunstlab-varde//")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", SCHOOL_NAME)
    cal.add("x-wr-timezone", str(TIMEZONE))
    # hints only; clients like Google Calendar decide their own poll cadence regardless
    cal.add("x-published-ttl", datetime.timedelta(hours=1))
    cal.add("refresh-interval", datetime.timedelta(hours=1))

    for booking in bookings:
        booking_id = booking.get("BookingId")
        title = booking.get("Title") or booking.get("CourseName") or "Booking"
        for slot in booking.get("TimeSlots", []):
            booking_date = datetime.date.fromisoformat(slot["BookingDate"][:10])
            start_time = datetime.time.fromisoformat(slot["StartTime"][:8])
            end_time = datetime.time.fromisoformat(slot["EndTime"][:8])
            dtstart = datetime.datetime.combine(booking_date, start_time, tzinfo=TIMEZONE)
            dtend = datetime.datetime.combine(booking_date, end_time, tzinfo=TIMEZONE)

            event = Event()
            # UID must stay stable across regenerations so clients don't churn duplicate events
            event.add("uid", f"speedadmin-{booking_id}-{dtstart.isoformat()}@kunstlab-varde")
            event.add("summary", vText(title))
            event.add("dtstart", dtstart)
            event.add("dtend", dtend)
            event.add("dtstamp", datetime.datetime.now(datetime.timezone.utc))
            cal.add_component(event)

    return cal


def main() -> None:
    api_key = os.environ.get("SPEEDADMIN_API_KEY")
    if not api_key:
        print("SPEEDADMIN_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    bookings = fetch_all_bookings(api_key)
    calendar = build_calendar(bookings)

    output_path = os.path.abspath(OUTPUT_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # write to a temp file first so a failed run never leaves a truncated feed behind
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(output_path))
    with os.fdopen(fd, "wb") as f:
        f.write(calendar.to_ical())
    os.replace(tmp_path, output_path)
    print(f"Wrote {len(bookings)} bookings to {output_path}")


if __name__ == "__main__":
    main()
