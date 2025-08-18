import requests
from google.transit import gtfs_realtime_pb2


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

    trains = [train_to_dict(train) for train in trains_json["trains"]]

    trains_ic = [
        train
        for train in trains
        if train["carrier"] == "IC" #and train["route"] == "ICeip"
    ]

    print(trains_ic[7])
    print("Total trains:", len(trains_ic))

    feed = gtfs_realtime_pb2.FeedMessage()

    feed.header.gtfs_realtime_version = "2.0"

    for train in trains_ic:
        ent = gtfs_realtime_pb2.FeedEntity()

        ent.id = train["gtfsId"]
        ent.trip_update.trip.trip_id = train["gtfsId"]
        ent.trip_update.trip.start_date = "20250818"
        ent.trip_update.trip.schedule_relationship = (
            gtfs_realtime_pb2.TripDescriptor.SCHEDULED
        )
        # ent.trip_update.delay = 600

        for i, station in enumerate(train["stations"]):
            stu = gtfs_realtime_pb2.TripUpdate.StopTimeUpdate(
                stop_sequence=i,
                departure=gtfs_realtime_pb2.TripUpdate.StopTimeEvent(
                    delay = int(station["departureDelay"]/1000)
                ),
                arrival = gtfs_realtime_pb2.TripUpdate.StopTimeEvent(
                    delay = int(station["arrivalDelay"]/1000),
                ),
            )
            ent.trip_update.stop_time_update.append(stu)
        
        if "5310" in train["gtfsId"]:
            print("Found train with ID 5310:", ent)
        feed.entity.append(ent)
    # print(feed)

    with open("output.pb", "wb") as f:
        f.write(feed.SerializeToString())
