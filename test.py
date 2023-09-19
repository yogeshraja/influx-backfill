#!/usr/bin/env python3

import json
from pprint import pprint
import requests
from tqdm import tqdm
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
open_pr_map={}
def create_map(points:list):
    for point in points:
        open_pr_map[point["tags"]["pull_Request_id"]]={
            "state":point["fields"]["state"],
            "point":point
        }

# client = InfluxDBClient(url="https://influxdb.silabs.net/", token="o0c8EZcu7U8GOPqVkDgZuw", org="devops")
client = InfluxDBClient(url="http://localhost:8086/", token="2mbOXskjFn_F12LgqxJ0K3wur1e2VN1-xW4952rxeXb3jcPa5WEJnxC5YRmj4wDgCNogUFnDyIfUFRLRMwgikg==", org="devops")
write_api = client.write_api(write_options=SYNCHRONOUS)

r = requests.get(
    "https://mimir-query-frontend.silabs.net/prometheus/api/v1/label/__name__/values"
)
print("Got labels")
# pprint(r.json())
data = ["stash_gsdk_all_pull_requests"]

for label in data:
    for x in range(40,1,-1):
        end = datetime.now() - timedelta(days=x)
        start = end - timedelta(days=1)
        r = requests.get(
                "https://mimir-query-frontend.silabs.net/prometheus/api/v1/query_range?query=%s&start=%sZ&end=%sZ&step=60"
                % (label, start.isoformat(), end.isoformat())
        )
        # pprint(r.json())
        result = r.json()["data"]["result"]
        for serie in tqdm(result, desc=label):
                all_points = []
                open_points_der=[]
                open_points = []
                for value in serie["values"]:
                    ts = value[0]
                    v = value[1]
                    tags={
                        "pull_Request_id":serie["metric"]["pull_request_id"],
                        "project":"GSDK"
                    }
                    rem_fields=["__name__","env","ha_cluster","instance","job","task_id"]
                    for f in rem_fields:
                        serie['metric'].pop(f,'nada')
                    serie['metric']['pull_request_id']=int(serie['metric']['pull_request_id'])
                    all_points.append(
							{
                                "measurement": "gsdk",
                                "tags": tags,
                                "time": datetime.utcfromtimestamp(ts).isoformat() + "Z",
                                "fields": serie['metric'],
							}
					)
                    open_points.append(
                            {
                                "measurement": "gsdk_open",
                                "tags": tags,
                                "time": datetime.utcfromtimestamp(ts).isoformat() + "Z",
                                "fields": serie['metric'],
                            }
                    )
                create_map(open_points)
                open_points_der=[point["point"] for point in open_pr_map.values() if point["state"]=="OPEN"]
                write_api.write(bucket="stash-pr",org="devops",record=all_points)
                write_api.write(bucket="stash-pr",org="devops",record=open_points_der)
    pprint(open_pr_map.keys())
    pprint(len(open_pr_map.keys()))