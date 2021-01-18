#!/usr/bin/python
''' Formatting displayed messages 
'''
import logging
import time
import datetime
import os
import GPSlookup
import config

def item2str(item, prefix='', postfix=''):
  if item == None:
    return ''
  if isinstance(item, tuple):
    val = int(item[0]) / int(item[1])
    if val > 1:
      if val == int(val):
        val = str(int(val)) # display as integer 
      else:
        val = str(val)  # display as decimal number
    else:
      val = '1/' + str(int(item[1] / item[0])) # display as fracture    
  else:
    val = str(item)
  val = prefix + val + postfix    
  return val      

def _clean_string(fmt_str):
  fmt_str = ''.join([c for c in fmt_str if c in config.CODEPOINTS]) # clean string 
  fmt_str = fmt_str[:99]  # limit length to 99 characters
  return fmt_str

def format_text(iFiles, pic_num):
  try:
    filename = os.path.basename(iFiles[pic_num][0])
    pathname = os.path.dirname(os.path.relpath(iFiles[pic_num][0], config.PIC_DIR))
    dt_str = '-'
    if iFiles[pic_num][3]:
      dt_str = datetime.datetime.fromtimestamp(iFiles[pic_num][3]).strftime("%d.%m.%Y")
    gps_str = '' 
    if config.RESOLVE_GPS: # GPS reverse lookup is quite expensive - so we check if it is required, before executing
      exif_info = iFiles[pic_num][4] 
      if exif_info: 
        gps_info = exif_info.get('GPSInfo')
        if gps_info: 
          gps_str = GPSlookup.lookup( gps_info )

    rep = { 
      '<file>':   filename[:40],    # filename of image
      '<path>':   pathname[:40],    # pathname of image
      '<date>':   dt_str,           # image creation date (dd.mm.yyyy)
      '<num>':    str(pic_num+1),        # number of current picuture in current file list
      '<total>':  str(len(iFiles)),      # total number of picutures in current file list  
      '<rating>': '*' * int(exif_info.get('Rating', 0)),
      '<make>':   exif_info.get('Make', ''),
      '<model>':  exif_info.get('Model', ''),
      '<artist>': exif_info.get('Artist', ''),
      '<copy>':   exif_info.get('Copyright', ''),
      '<desc>':   exif_info.get('ImageDescription', ''),
      '<exp>':    item2str(exif_info.get('ExposureTime'), postfix='s'),
      '<fnum>':   item2str(exif_info.get('FNumber'), prefix='f/'),
      '<iso>':    item2str(exif_info.get('ISOSpeedRatings'), prefix='ISO '),
      '<flen>':   item2str(exif_info.get('FocalLength'), postfix='mm'),
      '<flen35>': item2str(exif_info.get('FocalLengthIn35mmFilm'), postfix='mm'),
      '<res>':    item2str(exif_info.get('ExifImageWidth'), postfix='x') + item2str(exif_info.get('ExifImageHeight')),
      '<gps>':    gps_str 
    }

    txt1 = config.TEXT1_FORMAT
    txt2 = config.TEXT2_FORMAT
    txt3 = config.TEXT3_FORMAT
    txt4 = config.TEXT4_FORMAT

    for i, j in rep.items():
      txt1 = txt1.replace(i, j)
      txt2 = txt2.replace(i, j)
      txt3 = txt3.replace(i, j)
      txt4 = txt4.replace(i, j)

    txt1 = _clean_string(txt1)
    txt2 = _clean_string(txt2)
    txt3 = _clean_string(txt3)
    txt4 = _clean_string(txt4)
  except Exception as e: # something went wrong when formatting
    txt1 = txt2 = txt3 = txt4 = ' '
    logging.warning('Exception in format_text: {}'.format(str(e)) )
  return (txt1, txt2, txt3, txt4)

#---------------------------
if __name__ == "__main__":
  format_text( {}, 0 )
