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
    # retrieve data from PV device and store it in normalized format
    # you hopefully can change that quite easily to map your PV inverter's data
    # result should be "pvdata" being a dict of dicts which looks like that:   
    #    {
    #        'dt': {'value': '05.02.2023 14:55:02', 'unit': ''}, 
    #        'day_production': {'value': 20.1, 'unit': 'kWh'}, 
    #        'total_production': {'value': 630.4, 'unit': 'kWh'}, 
    #        ...
    #    }    
    station_id = cfg["PV_STATION_ID"]
    if len(station_id)<15:
        station_id = cfg["PV_DEMO_STATION_ID"]

    now = time.localtime() # "now" = time of data refresh
    pvdata["dt"] = { "value": time.strftime("%d.%m.%Y %H:%M:%S", now), "unit": "" }

    api = MTECapi.MTECapi()
    data = api.query_station_data(station_id)
    pvdata["day_production"] = data["todayEnergy"]
    pvdata["month_production"] = data["monthEnergy"]    
    pvdata["year_production"] = data["yearEnergy"]    
    pvdata["total_production"] = data["totalEnergy"]    
    pvdata["current_PV"] = data["PV"] 
    pvdata["current_grid"] = data["grid"] 
    pvdata["current_battery"] = data["battery"] 
    pvdata["current_battery_SOC"] = { "value": data["battery"]["SOC"], "unit": "%" }  
    pvdata["current_load"] = data["load"] 
    pvdata["grid_interrupt"] = { "value": data["lackMaster"], "unit": "" }

    data = api.query_grid_connected_data(station_id)
    pvdata["day_grid_load"] = data["eMeterTotalBuy"]
    pvdata["day_grid_feed"] = data["eMeterTotalSell"] 
    pvdata["day_usage"] = data["eUse"]
    pvdata["day_usage_self"] = data["eUseSelf"]
    pvdata["day_system_production"] = data["eDayTotal"]

    # calculate useful rates
    autarky_rate = 100 * pvdata["day_usage_self"]["value"] / pvdata["day_usage"]["value"] if pvdata["day_usage"]["value"]>0 else 0
    pvdata["day_autarky_rate"] = { "value": "{:.1f}".format(autarky_rate), "unit": "%" }

    return pvdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    pvdata = get_PV_device_data()
    if pvdata:
        for param, data in pvdata.items():
            logging.info( "{}: {} {}".format(param, data["value"], data["unit"]) )

