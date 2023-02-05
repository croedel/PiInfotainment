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
    pvdata["day_production"] = data["todayEnergy"]      # Energy produced by the PV today
    pvdata["month_production"] = data["monthEnergy"]    # Energy produced by the PV this month
    pvdata["year_production"] = data["yearEnergy"]      # Energy produced by the PV this year
    pvdata["total_production"] = data["totalEnergy"]    # Energy produced by the PV in total
    pvdata["current_PV"] = data["PV"]                   # Current PV production
    pvdata["current_grid"] = data["grid"]               # Current flow from/to grid
    pvdata["current_battery"] = data["battery"]         # Current flow from/to battery    
    pvdata["current_battery_SOC"] = { "value": data["battery"]["SOC"], "unit": "%" }  # Current battery SOC
    pvdata["current_load"] = data["load"]               # Current consumed energy
    pvdata["grid_interrupt"] = { "value": data["lackMaster"], "unit": "" }  # Grid interrup flag

    data = api.query_grid_connected_data(station_id)
    pvdata["day_grid_load"] = data["eMeterTotalBuy"]    # Today's energy loaded from grid
    pvdata["day_grid_feed"] = data["eMeterTotalSell"]   # Today's energy fed into grid
    pvdata["day_usage"] = data["eUse"]                  # Today's total energy consumption
    pvdata["day_usage_self"] = data["eUseSelf"]         # Today's energy consumption originating from own PV or battery (i.e. not grid)

    # calculate autarky rate
    autarky_rate = 100 * pvdata["day_usage_self"]["value"] / pvdata["day_usage"]["value"] if pvdata["day_usage"]["value"]>0 else 0
    pvdata["day_autarky_rate"] = { "value": "{:.1f}".format(autarky_rate), "unit": "%" }    # Today's independance rate from grid power

    return pvdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    pvdata = get_PV_device_data()
    if pvdata:
        for param, data in pvdata.items():
            logging.info( "{}: {}{}".format(param, data["value"], data["unit"]) )

