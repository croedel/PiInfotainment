#!/usr/bin/env python3
"""
Reads parameters from a PV device. 
"""

from locale import format_string
from config import cfg
import logging
import time
from MTEC_energybutler_API import MTECapi
 
#---------------------------------------------
def get_PV_device_data():
    pvdata = {}
    now = time.localtime() # "now" = time of data refresh
    pvdata["dt"] = { "value": time.strftime("%d.%m.%Y %H:%M:%S", now), "unit": "" }

    # retrieve data from PV device and store it in normalized format
    # you hopefully can change that quite easily to map your PV inverter's data
    api = MTECapi.MTECapi()
    data = api.query_station_data(cfg["PV_STATION_ID"])
    pvdata["day_production"] = data["todayEnergy"]
    pvdata["total_production"] = data["totalEnergy"]    
    pvdata["current_PV"] = data["PV"] 
    pvdata["current_grid"] = data["grid"] 
    pvdata["current_battery"] = data["battery"] 
    pvdata["current_battery_SOC"] = { "value": data["battery"]["SOC"], "unit": "%" }  
    pvdata["current_load"] = data["load"] 

    data = api.query_grid_connected_data(cfg["PV_STATION_ID"])
    pvdata["day_grid_load"] = data["eMeterTotalBuy"]
    pvdata["day_grid_feed"] = data["eMeterTotalSell"] 
    pvdata["day_usage"] = data["eUse"]
    pvdata["day_usage_self"] = data["eUseSelf"]
    pvdata["day_system_production"] = data["eDayTotal"]

    # calculate useful rates
    autarky_rate = 100 * pvdata["day_usage_self"]["value"] / pvdata["day_usage"]["value"] if pvdata["day_usage"]["value"]>0 else 0
    own_usage_rate = 100 * pvdata["day_usage_self"]["value"] / pvdata["day_system_production"]["value"] if pvdata["day_system_production"]["value"]>0 else 0
    pvdata["day_autarky_rate"] = { "value": "{:.1f}".format(autarky_rate), "unit": "%" }
    pvdata["day_own_usage_rate"] = { "value": "{:.1f}".format(own_usage_rate), "unit": "%" }

    return pvdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    pvdata = get_PV_device_data()
    if pvdata:
        for param, data in pvdata.items():
            logging.info( "{}: {} {}".format(param, data["value"], data["unit"]) )

