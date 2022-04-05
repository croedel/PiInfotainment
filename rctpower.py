#!/usr/bin/env python3

import socket, select, sys
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
    rctdata= {}
    for( field, title ) in data_array:
        rctdata[field] = query_object( sock, field ) 
    return rctdata

#---------------------------------------------
def connect_to_server( server, port ):
    # open the socket and connect to the remote device:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server, port))
    except OSError as msg:
        print("Couldn't connect to server {}:{} -> {}".format(server, port, msg))
        return "ERROR"
    return sock    

#---------------------------------------------

server = '192.168.178.32'
port = 8899

data_array = [
    # (Name, Field)
    ( "battery.soc",                        "Battery: {} %" ),
    ( "dc_conv.dc_conv_struct[0].p_dc_lp",  "Generator A power: {} W" ),
    ( "dc_conv.dc_conv_struct[1].p_dc_lp",  "Generator B power: {} W" ),
    ( "g_sync.p_acc_lp",                    "Battery charge: {} W" ),
    ( "g_sync.p_ac_load_sum_lp",            "House consumption: {} W" ),
    ( "g_sync.p_ac_grid_sum_lp",            "Grid power drain: {} W" ),

    ( "energy.e_ext_day",                   "" ),
    ( "energy.e_ac_day",                    "" ),
    ( "energy.e_grid_load_day",             "" ),
    ( "energy.e_grid_feed_day",             "" ),
    ( "energy.e_dc_day[0]",                 "" ),
    ( "energy.e_dc_day[1]",                 "" ),
    ( "energy.e_load_day",                  "" ),

    ( "energy.e_ext_month",                 "" ),
    ( "energy.e_ac_month",                  "" ),
    ( "energy.e_grid_load_month",           "" ),
    ( "energy.e_grid_feed_month",           "" ),
    ( "energy.e_dc_month[0]",               "" ),
    ( "energy.e_dc_month[1]",               "" ),
    ( "energy.e_load_month",                "" ),

    ( "energy.e_ext_year",                  "" ),
    ( "energy.e_ac_year",                   "" ),
    ( "energy.e_grid_load_year",            "" ),
    ( "energy.e_grid_feed_year",            "" ),
    ( "energy.e_dc_year[0]",                "" ),
    ( "energy.e_dc_year[1]",                "" ),
    ( "energy.e_load_year",                 "" ),

    ( "energy.e_ext_total",                 "" ),
    ( "energy.e_ac_total",                  "" ),
    ( "energy.e_grid_load_total",           "" ),
    ( "energy.e_grid_feed_total",           "" ),
    ( "energy.e_dc_total[0]",               "" ),
    ( "energy.e_dc_total[1]",               "" ),
    ( "energy.e_load_total",                "" )
]

sock = connect_to_server( server, port )
if sock != "ERROR":
    rctdata = retrieve_data( sock, data_array )    

    for( param, value ) in rctdata.items():    
        print( param + ": " + str(value) )



