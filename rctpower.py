#!/usr/bin/env python3
"""
Reads parameters from a RCT Power GmbH device. 
This module uses heavily the great project https://github.com/svalouch/python-rctclient 
"""

from locale import format_string
from config import cfg
import logging

import socket, select, sys
import json
from telnetlib import RCTE
from rctclient.frame import ReceiveFrame, make_frame
from rctclient.registry import REGISTRY as R
from rctclient.types import Command
from rctclient.utils import decode_value

#---------------------------------------------
def query_object( sock, parameter ):
    # query information about an object ID:
    object_info = R.get_by_name(parameter)

    # construct a byte stream that will send a read command for the object ID we want, and send it
    send_frame = make_frame(command=Command.READ, id=object_info.object_id)
    sock.send(send_frame)

    # loop until we got the entire response frame
    frame = ReceiveFrame()
    while True:
        ready_read, _, _ = select.select([sock], [], [], 2.0)
        if sock in ready_read:
            # receive content of the input buffer
            buf = sock.recv(256)
            # if there is content, let the frame consume it
            if len(buf) > 0:
                frame.consume(buf)
                # if the frame is complete, we're done
                if frame.complete():
                    break
            else:
                # the socket was closed by the device, exit
                sys.exit(1)

    # decode the frames payload
    value = decode_value(object_info.response_data_type, frame.data)
    return value

#---------------------------------------------
def retrieve_data( sock, field_array ):
    rawdata = {} 
    for field, devicedata, title, scale, sformat in field_array:
        if devicedata == True:    
            value = query_object( sock, field )        
            if value != None:
                rawdata[field] = value
    return rawdata

#---------------------------------------------
def format_data( rawdata, field_array ):
    rctdata = {}
    for field, devicedata, title, scale, sformat in field_array:
        value = rawdata[field]
        if value != None:       
            node = {}
            node["title"] = title
            node["format"] = sformat
            if scale != None and isinstance(scale, int):    
                node["value"] = value/scale
            else:
                node["value"] = value
            rctdata[field] = node
    return rctdata

#---------------------------------------------
def connect_to_server( server, port ):
    # open the socket and connect to the remote device:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server, port))
    except OSError as msg:
        logging.error("Couldn't connect to server {}:{} -> {}".format(server, port, msg))
        return "ERROR"
    return sock    

#---------------------------------------------
def get_RCT_device_data():
    # Defines which data to retrieve from the device    
    field_array = [
        # (Field, Device-data, Title, Scale, Format)
        ( "android_description",                True ,  "Name",     	        None,   "{}" ),
        ( "dc_conv.dc_conv_struct[0].p_dc_lp",  True ,  "PV Leistung Strang A", 1,      "{:.2f}W" ),
        ( "dc_conv.dc_conv_struct[1].p_dc_lp",  True ,  "PV Leistung Strang B", 1,      "{:.2f}W" ),
        ( "g_sync.p_acc_lp",                    True ,  "Speicher Ladestrom",   1,      "{:.2f}W" ),
        ( "battery.soc",                        True ,  "Speicher Ladestatus",  1,      "{:.0f}%" ),
        ( "g_sync.p_ac_load_sum_lp",            True ,  "Haus Verbrauch",       1,      "{:.2f}W" ),
        ( "g_sync.p_ac_grid_sum_lp",            True ,  "Netz Bezug",           1,      "{:.2f}W" ),
        ( "prim_sm.island_flag",                True ,  "Inselmodus",           None,   "{}" ),
   
        ( "energy.e_dc_day[0]",                 True ,  "PV Leistung Strang A", 1000,   "{:.1f}kWh" ),
        ( "energy.e_dc_day[1]",                 True ,  "PV Leistung Strang B", 1000,   "{:.1f}kWh" ),
        ( "energy.e_ext_day",                   True ,  "Externer Bezug",       1000,   "{:.1f}kWh" ),
        ( "energy.e_ac_day",                    True ,  "Gesamtverbrauch",      1000,   "{:.1f}kWh" ),
        ( "energy.e_grid_load_day",             True ,  "Netz Bezug",           1000,   "{:.1f}kWh" ),
        ( "energy.e_grid_feed_day",             True ,  "Netz Einspeisung",     1000,   "{:.1f}kWh" ),
        ( "energy.e_load_day",                  True ,  "Haus Verbrauch",       1000,   "{:.1f}kWh" ),
  
        # calculated data (device-data = False)
        ( "energy.e_dc_day",                    False , "PV Leistung",          1000,   "{:.1f}kWh" ),
        ( "energy.e_autarky_day",               False,  "Autarkie",             1,      "{:.0%}" ),
        ( "energy.e_balance_day",               False,  "Energiebilanz",        1,      "{:.0%}" )
    ]

    rawdata = None
    rctdata = None
    # Connect to server
    sock = connect_to_server( cfg['RCT_SERVER'], cfg['RCT_PORT'] )
    if sock != "ERROR":
        # read data from RCT data device
        rawdata = retrieve_data( sock, field_array )

        # calculate some custom data 
        rawdata["energy.e_dc_day"] = rawdata["energy.e_dc_day[0]"] + rawdata["energy.e_dc_day[1]"]
        rawdata["energy.e_autarky_day"] = 1 - (rawdata["energy.e_ext_day"] / rawdata["energy.e_ac_day"]) if rawdata["energy.e_ac_day"] else 1
        rawdata["energy.e_balance_day"] = (rawdata["energy.e_grid_feed_day"] - rawdata["energy.e_grid_load_day"]) / rawdata["energy.e_ac_day"] if rawdata["energy.e_ac_day"] else 0

        # Format result
        rctdata = format_data( rawdata, field_array )
    return rctdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    rctdata = get_RCT_device_data()
    if rctdata:
        for field, data in rctdata.items():
            logging.info( field + " (" + data["title"] + "): " + data["format"].format(data["value"]) )

