import requests
from google.transit import gtfs_realtime_pb2
import os


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


def main():
    print("This is the main function of the CLI module.")
    trains_json = requests.get("https://cdn.zbiorkom.live/active.json").json()
    finished_trains_json = requests.get("https://cdn.zbiorkom.live/completed.json").json()

    trains = [train_to_dict(train) for train in trains_json["trains"]]
    alerts = [alert for alert in trains_json["alerts"]]

    # TODO: add station ids and detours/canceled stations
    # TODO: add finished trains

    trains_ic = [train for train in trains if train["carrier"] == "IC"]

    print("Total trains:", len(trains_ic))

    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.gtfs_realtime_version = "2.0"

    for train in trains_ic:
        ent = gtfs_realtime_pb2.FeedEntity()

        ent.id = train["gtfsId"]
        ent.trip_update.trip.trip_id = train["gtfsId"]
        ent.trip_update.trip.start_date = train["gtfsId"][0:10].replace(
            "-", ""
        )  # YYYYMMDD
        ent.trip_update.trip.schedule_relationship = (
            gtfs_realtime_pb2.TripDescriptor.SCHEDULED
        )

        for i, station in enumerate(train["stations"]):
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
                # alert_ent.alert.informed_entity.trip.trip_id = ent.id
                feed.entity.append(alert_ent)

        feed.entity.append(ent)

    if os.environ.get("DEBUG"):
        with open("output.json", "w") as f:
            f.write(str(feed))

    with open("output.pb", "wb") as f:
        f.write(feed.SerializeToString())
