#!/usr/bin/env python3
"""
Reads parameters from a PV device. 
"""

from locale import format_string
from config import cfg
import logging
import time
from MTEC_API import MTECapi

#---------------------------------------------
def format_data( data ):
    value = float(data.get("value", 0))
    unit = data.get("unit", "")
    direction = data.get("direction")

    # do some formatting for nicer output
    if unit == "kW" and value < 1: # Convert to W  
        value = int(value*1000)
        unit = "W"    
    elif unit == "W": # Don't show decimal places for W
        value = int(value)   

    if direction:
        return { "value": value, "unit": unit, "direction": direction }
    else:
        return { "value": value, "unit": unit }
    
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
    #        'current_PV': {'value': 630.4, 'unit': 'kWh', 'direction': 1},    
    #        ...
    #    }
    #     
    # value and unit should be self explaining. direction indicated the flow direction:
    #  1: "obtain"
    #  2: "feed in" 
    #  3: "idle"       

    station_id = cfg["PV_STATION_ID"]
    if len(station_id)<15:
        station_id = cfg["PV_DEMO_STATION_ID"]

    now = time.localtime() # "now" = time of data refresh
    pvdata["dt"] = { "value": time.strftime("%d.%m.%Y %H:%M:%S", now), "unit": "" }

    api = MTECapi.MTECapi()
    data = api.query_station_data(station_id)
    pvdata["day_production"] = data["todayEnergy"]              # Energy produced by the PV today
    pvdata["month_production"] = data["monthEnergy"]            # Energy produced by the PV this month
    pvdata["year_production"] = data["yearEnergy"]              # Energy produced by the PV this year
    pvdata["total_production"] = data["totalEnergy"]            # Energy produced by the PV in total
    pvdata["current_PV"] = format_data(data["PV"])              # Current flow from PV
    pvdata["current_grid"] = format_data( data["grid"] )        # Current flow from/to grid
    pvdata["current_battery"] = format_data( data["battery"] )  # Current flow from/to battery
    pvdata["current_battery_SOC"] = { "value": data["battery"]["SOC"], "unit": "%" }   # Current battery SOC
    pvdata["current_load"] = format_data( data["load"])          # Current consumed energy
    pvdata["grid_interrupt"] = { "value": data["lackMaster"], "unit": "" }  # Grid interrup flag

    data = api.query_usage_data(station_id, "today")
    pvdata["day_grid_load"] = data["day_grid_load"]     # Today's energy loaded from grid
    pvdata["day_grid_feed"] = data["day_grid_feed"]     # Today's energy fed into grid
    pvdata["day_usage"] = data["day_usage"]             # Today's total energy consumption
    pvdata["day_usage_self"] = data["day_usage_self"]   # Today's energy consumption originating from own PV or battery (i.e. not grid)
    pvdata["day_total"] = data["day_total"]             # Today's total energy production (PV + battery discharge)

    # calculate autarky rate
    autarky_rate = 100 * pvdata["day_usage_self"]["value"] / pvdata["day_usage"]["value"] if pvdata["day_usage"]["value"]>0 else 0
    pvdata["day_autarky_rate"] = { "value": "{:.1f}".format(autarky_rate), "unit": "%" }    # Today's independance rate from grid power
    self_usage_rate = 100 * pvdata["day_usage_self"]["value"] / pvdata["day_total"]["value"] if pvdata["day_total"]["value"]>0 else 0
    pvdata["day_self_usage_rate"] = { "value": "{:.1f}".format(self_usage_rate), "unit": "%" }    # Ratio of self used energy (vs. fed into grid)

    return pvdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    pvdata = get_PV_device_data()
    if pvdata:
        for param, data in pvdata.items():
            logging.info( "{}: {}{}".format(param, data["value"], data["unit"]) )

