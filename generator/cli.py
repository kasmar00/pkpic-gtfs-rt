import requests
from google.transit import gtfs_realtime_pb2
import os
from datetime import datetime


def train_to_dict(train):
    return {
        "id": train[0],
        "gtfsId": train[1],
        "carrier": train[2],
        "route": train[3],
        "shortName": train[4],
        "stations": [station_to_dict(station) for station in train[5]],
    }


def station_to_dict(station):
    return {
        "id": station[0],
        "scheduledArrival": station[1],
        "arrivalDelay": station[2],
        "scheduledDeparture": station[3],
        "departureDelay": station[4],
        "platform": station[5],  # platform/track
        "isCancelled": station[6],
        "alertIds": station[7],  # index of alert in alerts array
    }

import argparse

carriers = {
    "IC": None,
    "RJ": None,
}

def main():
    parser = argparse.ArgumentParser("python3 -m generator")
    parser.add_argument("--carrier", help="Short name of carrier", type=str, required=True)
    args = parser.parse_args()

    if args.carrier not in carriers:
        raise ValueError(f"Unknown carrier {args.carrier}, available: {', '.join(carriers.keys())}")
    print(f"Generating GTFS-RT for {args.carrier}")

    trains_json = requests.get("https://cdn.zbiorkom.live/active.json").json()
    finished_trains_json = requests.get("https://cdn.zbiorkom.live/completed.json").json()

    # TODO: add station ids and detours/canceled stations

    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.gtfs_realtime_version = "2.0"

    trains, alerts = json_to_trains_and_alerts(trains_json, args.carrier)
    process_trains(trains, alerts, feed)

    finished_trains, finished_alerts = json_to_trains_and_alerts(finished_trains_json, args.carrier)
    process_trains(finished_trains, finished_alerts, feed)

    if os.environ.get("DEBUG"):
        with open("output.json", "w") as f:
            f.write(str(feed))

    with open("output.pb", "wb") as f:
        f.write(feed.SerializeToString())


def json_to_trains_and_alerts(trains_json, carrier):
    trains = [train_to_dict(train) for train in trains_json["trains"]]
    alerts = [alert for alert in trains_json["alerts"]]
    filtered_trains = [train for train in trains if train["carrier"] == carrier]

    return filtered_trains, alerts

def trip_id_to_date(trip_id: str) -> str: # YYYYMMDD
    if "-" not in trip_id[0:8]: #RJ
        return trip_id[0:8]
    return trip_id[0:10].replace("-", "") #IC


def process_trains(trains_ic, alerts, feed):
    for train in trains_ic:
        ent = gtfs_realtime_pb2.FeedEntity()

        ent.id = train["gtfsId"]
        ent.trip_update.trip.trip_id = train["gtfsId"]
        ent.trip_update.trip.start_date = trip_id_to_date(train["gtfsId"]) # YYYYMMDD
        ent.trip_update.trip.schedule_relationship = (
            gtfs_realtime_pb2.TripDescriptor.SCHEDULED
        )

        stations = train["stations"]
        if stations[0]["departureDelay"] < - 23*3600*1000 or stations[0]["departureDelay"] > 23*3600*1000:
            print(f"{train['gtfsId']}: {datetime.fromtimestamp(stations[0]['scheduledArrival']/1000)}")
            continue
        for i, station in enumerate(stations):
            stu = gtfs_realtime_pb2.TripUpdate.StopTimeUpdate(
                stop_sequence=i,
                departure=gtfs_realtime_pb2.TripUpdate.StopTimeEvent(
                    delay=int(station["departureDelay"] / 1000)
                ),
                arrival=gtfs_realtime_pb2.TripUpdate.StopTimeEvent(
                    delay=int(station["arrivalDelay"] / 1000),
                ),
            )

            if station["isCancelled"]:
                stu.schedule_relationship = (
                    gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship.SKIPPED
                )

            ent.trip_update.stop_time_update.append(stu)

            # TODO: add one global alert for all trains with the same alert text
            for alertId in station["alertIds"]:
                alert: str = alerts[alertId]
                alert_ent = gtfs_realtime_pb2.FeedEntity()
                alert_ent.id = ent.id + f"_{i}_{alertId}"

                alert_ent.alert.cause = gtfs_realtime_pb2.Alert.UNKNOWN_CAUSE
                alert_ent.alert.effect = gtfs_realtime_pb2.Alert.UNKNOWN_EFFECT

                alert_ent.alert.header_text.translation.append(
                    gtfs_realtime_pb2.TranslatedString.Translation(
                        text=alert,
                        language="pl",
                    )
                )

                trip_selector = gtfs_realtime_pb2.EntitySelector()
                # TODO: add affected stop
                trip_selector.trip.trip_id = ent.trip_update.trip.trip_id
                trip_selector.trip.start_date = ent.trip_update.trip.start_date

                alert_ent.alert.informed_entity.append(trip_selector)
                feed.entity.append(alert_ent)

        feed.entity.append(ent)
