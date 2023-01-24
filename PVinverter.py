#!/usr/bin/env python3
"""
Reads parameters from a PV device. 
"""

from locale import format_string
from config import cfg
import logging

if cfg['PV_TYPE'] == "RCTpower":
    import RCTpower

#---------------------------------------------
def format_rawdata( rawdata ):
    pvdata = {}
    parameter_map = []
    if cfg['PV_TYPE'] == "RCTpower":
        parameter_map = RCTpower.parameter_map

    for parameter, normalized, scale, sformat in parameter_map:
        value = rawdata.get(normalized)
        if value != None:       
            node = {}
            if scale != None and isinstance(scale, int):    
                node["value"] = value/scale
            else:
                node["value"] = value
            node["format"] = sformat
            pvdata[normalized] = node
    return pvdata
 
#---------------------------------------------
def get_PV_device_data():
    rawdata = {}
    pvdata = {}

    # retrieve data from PV device
    if cfg['PV_TYPE'] == "RCTpower":
        rawdata = RCTpower.retrieve_PV_data()

    try:
        # add some calculated data
        rawdata["day_production"] = rawdata["day_string_a"] + rawdata["day_string_b"]
        rawdata["day_autarky_rate"] = 1 - (rawdata["day_ext"] / rawdata["day_energy"]) if rawdata["day_energy"] else 1
        rawdata["day_balance_rate"] = (rawdata["day_grid_feed"] - rawdata["day_grid_load"]) / rawdata["day_energy"] if rawdata["day_energy"] else 0
        rawdata["day_balance"] = rawdata["day_grid_feed"] - rawdata["day_grid_load"]
    except:
        logging.error("Couldn't add calculated data")

    # scale and add format
    pvdata = format_rawdata( rawdata )

    return pvdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    pvdata = get_PV_device_data()
    if pvdata:
        for parameter, data in pvdata.items():
            logging.info( parameter + ": " + data["format"].format(data["value"]) )

