#!/usr/bin/env python3

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
def retrieve_data( sock, data_array ):
    rctdata = [] 
    last_category = ""
    node = None

    for( field, category, scale, title, sformat ) in data_array:
        value = query_object( sock, field )
        if value != None:
            if category != last_category:
                if node != None:
                    rctdata.append(node)        
                node = {}
                node["category"] = category
                node["data"] = {}
            if scale:
                node["data"][title] = sformat.format( value/scale )
            else:
                node["data"][title] = sformat.format( value )
            last_category = category
    if node != None:
        rctdata.append(node)        
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
    data_array = [
        # (Field, Category, Scale, Title, Format)
        ( "android_description",                "now", None,    "Name",     	        "{}" ),
        ( "dc_conv.dc_conv_struct[0].p_dc_lp",  "now", 1,       "PV Leistung Strang A", "{:.2f} W" ),
        ( "dc_conv.dc_conv_struct[1].p_dc_lp",  "now", 1,       "PV Leistung Strang B", "{:.2f} W" ),
        ( "g_sync.p_acc_lp",                    "now", 1,       "Speicher Ladestrom",   "{:.2f} W" ),
        ( "battery.soc",                        "now", 1,       "Speicher Ladestatus",  "{:.2f} %" ),
        ( "g_sync.p_ac_load_sum_lp",            "now", 1,       "Haus Verbrauch",       "{:.2f} W" ),
        ( "g_sync.p_ac_grid_sum_lp",            "now", 1,       "Netz Bezug",           "{:.2f} W" ),
        ( "rb485.u_l_grid[0]",                  "now", 1,       "Netz Spannung (1)",    "{:.2f} V" ),
        ( "rb485.u_l_grid[1]",                  "now", 1,       "Netz Spannung (2)",    "{:.2f} V" ),
        ( "rb485.u_l_grid[2]",                  "now", 1,       "Netz Spannung (3)",    "{:.2f} V" ),
        ( "prim_sm.island_flag",                "now", None,    "Inselmodus",           "{}" ),
        
        ( "energy.e_dc_day[0]",                 "day", 1000,    "PV Leistung Strang A", "{:.1f} kWh" ),
        ( "energy.e_dc_day[1]",                 "day", 1000,    "PV Leistung Strang B", "{:.1f} kWh" ),
        ( "energy.e_ext_day",                   "day", 1000,    "Externer Bezug",       "{:.1f} kWh" ),
        ( "energy.e_ac_day",                    "day", 1000,    "Gesamtverbrauch",      "{:.1f} kWh" ),
        ( "energy.e_grid_load_day",             "day", 1000,    "Netz Bezug",           "{:.1f} kWh" ),
        ( "energy.e_grid_feed_day",             "day", 1000,    "Netz Einspeisung",     "{:.1f} kWh" ),
        ( "energy.e_load_day",                  "day", 1000,    "Haus Verbrauch",       "{:.1f} kWh" ),

        ( "energy.e_dc_month[0]",               "month", 1000,  "PV Leistung Strang A", "{:.0f} kWh" ),
        ( "energy.e_dc_month[1]",               "month", 1000,  "PV Leistung Strang B", "{:.0f} kWh" ),
        ( "energy.e_ext_month",                 "month", 1000,  "Externer Bezug",       "{:.0f} kWh" ),
        ( "energy.e_ac_month",                  "month", 1000,  "Gesamtverbrauch",      "{:.0f} kWh" ),
        ( "energy.e_grid_load_month",           "month", 1000,  "Netz Bezug",           "{:.0f} kWh" ),
        ( "energy.e_grid_feed_month",           "month", 1000,  "Netz Einspeisung",     "{:.0f} kWh" ),
        ( "energy.e_load_month",                "month", 1000,  "Haus Verbrauch",       "{:.0f} kWh" ),

        ( "energy.e_dc_year[0]",                "year", 1000,   "PV Leistung Strang A", "{:.0f} kWh" ),
        ( "energy.e_dc_year[1]",                "year", 1000,   "PV Leistung Strang B", "{:.0f} kWh" ),
        ( "energy.e_ext_year",                  "year", 1000,   "Externer Bezug",       "{:.0f} kWh" ),
        ( "energy.e_ac_year",                   "year", 1000,   "Gesamtverbrauch",      "{:.0f} kWh" ),
        ( "energy.e_grid_load_year",            "year", 1000,   "Netz Bezug",           "{:.0f} kWh" ),
        ( "energy.e_grid_feed_year",            "year", 1000,   "Netz Einspeisung",     "{:.0f} kWh" ),
        ( "energy.e_load_year",                 "year", 1000,   "Haus Verbrauch",       "{:.0f} kWh" ),

        ( "energy.e_dc_total[0]",               "total", 1000,  "PV Leistung Strang A", "{:.0f} kWh" ),
        ( "energy.e_dc_total[1]",               "total", 1000,  "PV Leistung Strang B", "{:.0f} kWh" ),
        ( "energy.e_ext_total",                 "total", 1000,  "Externer Bezug",       "{:.0f} kWh" ),
        ( "energy.e_ac_total",                  "total", 1000,  "Gesamtverbrauch",      "{:.0f} kWh" ),
        ( "energy.e_grid_load_total",           "total", 1000,  "Netz Bezug",           "{:.0f} kWh" ),
        ( "energy.e_grid_feed_total",           "total", 1000,  "Grid feed",            "{:.0f} kWh" ),
        ( "energy.e_load_total",                "total", 1000,  "Haus Verbrauch",       "{:.0f} kWh" )
    ]

    rctdata = None
    sock = connect_to_server( cfg['RCT_SERVER'], cfg['RCT_PORT'] )
    if sock != "ERROR":
        rctdata = retrieve_data( sock, data_array )    
    return rctdata

#-------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

    rctdata = get_RCT_device_data()
    if rctdata != None:
        logging.info(json.dumps(rctdata, indent=4))

