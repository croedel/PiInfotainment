#!/usr/bin/env python3
"""
Reads parameters from a JSON REST API. 
"""
from config import cfg
import logging
import requests

#---------------------------------------------
def do_API_call( url ):
    data = {}
    try:
        response = requests.get( url, timeout=5 )
    except requests.exceptions.RequestException as err:
        logging.error( "Couldn't request PV REST API: {:s} ({:s}) Exception {:s}".format(url, str(payload), str(err)) )
    else:
        if response.status_code == 200:
            data = response.json()
        else:
            logging.error( "Couldn't request PV REST API: {:s} ({:s}) Response {}".format(url, str(payload), response) )
    return data    

#---------------------------------------------
def retrieve_PV_data():
    data = {}

    url = 'https://jsonplaceholder.typicode.com/users/'
    rawdata = do_API_call( url )    
    if rawdata:
        logging.info( str(rawdata) )

#    data["name"] =
#    data["current_string_a"] =
#    data["current_string_b"] = 
#    data["current_battery_power"] =
#    data["current_battery_soc"] = 
#    data["current_house_ext_power"] =
#    data["current_grid_power"] =  
#    data["current_island_mode"] = 
#    data["day_string_a"] =        
#    data["day_string_b"] =        
#    data["day_ext"] =             
#    data["day_energy"] =          
#    data["day_grid_load"] =       
#    data["day_grid_feed"] =       
#    data["day_house_usage"] = 
#    data["total_energy"] =    

    return data

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    data = retrieve_PV_data()
    if data:
        for param, value in data.items():
            logging.info( "{}: {}".format(param, value))

