#!/usr/bin/env python3
"""
Reads parameters from a RCT Power GmbH device. 
This module uses heavily the great project https://github.com/svalouch/python-rctclient 
"""
from config import cfg
import logging

import socket, select

from telnetlib import RCTE
from rctclient.frame import ReceiveFrame, make_frame
from rctclient.registry import REGISTRY as R
from rctclient.types import Command
from rctclient.utils import decode_value

parameter_map = [     
    # Defines mapping and normalization of device parameters       
    # (parameter, normalized, scale, format)
    ( "android_description",                "name",     	             None,   "{}" ),
    ( "dc_conv.dc_conv_struct[0].p_dc_lp",  "current_string_a",          1,      "{:.2f}W" ),
    ( "dc_conv.dc_conv_struct[1].p_dc_lp",  "current_string_b",          1,      "{:.2f}W" ),
    ( "g_sync.p_acc_lp",                    "current_battery_power",     1,      "{:.2f}W" ),
    ( "battery.soc",                        "current_battery_soc",       1,      "{:.0f}%" ),
    ( "g_sync.p_ac_load_sum_lp",            "current_house_ext_power",   1,      "{:.2f}W" ),
    ( "g_sync.p_ac_grid_sum_lp",            "current_grid_power",        1,      "{:.2f}W" ),
    ( "prim_sm.island_flag",                "current_island_mode",       None,   "{}" ),

    ( "energy.e_dc_day[0]",                 "day_string_a",              1000,   "{:.1f}kWh" ),
    ( "energy.e_dc_day[1]",                 "day_string_b",              1000,   "{:.1f}kWh" ),
    ( "energy.e_ext_day",                   "day_ext",                   1000,   "{:.1f}kWh" ),
    ( "energy.e_ac_day",                    "day_energy",                1000,   "{:.1f}kWh" ),
    ( "energy.e_grid_load_day",             "day_grid_load",             1000,   "{:.1f}kWh" ),
    ( "energy.e_grid_feed_day",             "day_grid_feed",             1000,   "{:.1f}kWh" ),
    ( "energy.e_load_day",                  "day_house_usage",           1000,   "{:.1f}kWh" ),
    ( "energy.e_ac_total",                  "total_energy",              1000,   "{:.1f}kWh" ),

    # calculated data 
    ( "",                                   "day_production",            1000,   "{:.1f}kWh" ),
    ( "",                                   "day_autarky_rate",             1,      "{:.0%}" ),
    ( "",                                   "day_balance_rate",             1,      "{:.0%}" ),
    ( "",                                   "day_balance",               1000,   "{:.1f}kWh" )
]

#---------------------------------------------
def query_object( sock, parameter ):
    value = None
    # query information about an object ID:
    try:
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
    except:
        logging.warning("Couldn't retrieve parameter '{}'".format(parameter))

    return value

#---------------------------------------------
def retrieve_PV_data():
    server = cfg['PV_SERVER']
    port = cfg['PV_PORT']
    rawdata = {} 

    try:
        # open the socket and connect to the remote device:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server,port))

        # read data from RCT data device
        for parameter, normalized, scale, sformat in parameter_map:
            if len(parameter) > 0: # exclude calculated data
                value = query_object( sock, parameter )        
                if value != None:
                    rawdata[normalized] = value
    except OSError as msg:
        logging.error("Couldn't connect to RCT server {}:{} -> {}".format(server, port, msg))
    
    return rawdata
