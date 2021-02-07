""" Config file of RaspiInfotainment project. 
"""
import yaml
import os
import logging
import types 
from PIL import ExifTags

logging.basicConfig( level=logging.INFO, format="[%(levelname)s] %(filename)s: %(message)s" )

def create_EXIF_dict():
  exif_dict = {
    'Orientation': None,
    'DateTimeOriginal': None,
    'ImageDescription': None,
    'Rating': None,
    'Make': None,
    'Model': None,
    'Artist': None,
    'Copyright': None,
    'ExposureTime': None,
    'FNumber': None,
    'ISOSpeedRatings': None,
    'FocalLength': None,
    'ExifImageWidth': None,
    'ExifImageHeight': None,
    'FocalLengthIn35mmFilm': None,
    'GPSInfo': None
  }

  # create reverse lookup dictionary
  for k, v in ExifTags.TAGS.items():
    if v in exif_dict:
      exif_dict[v] = k
  if (exif_dict['Orientation'] == None) or (exif_dict['DateTimeOriginal'] == None):
    logging.critical( "Couldn't look-up essential EXIF Id's - exiting")
    exit(1)
  return exif_dict

######################################
BASE_DIR = os.path.dirname(__file__) # Base installation directory

try:
  fname = os.path.join(BASE_DIR, "config.yaml")
  with open(fname, 'r', encoding='utf-8') as myfile:
    cfg = yaml.safe_load(myfile)
except yaml.YAMLError as err:
  logging.error("Couldn't read config file {}: {}".format(fname, str(err)) )

cfg['EXIF_DICT'] = create_EXIF_dict() 

# create absolute file paths
cfg['NO_FILES_IMG'] =   os.path.join(BASE_DIR, "images", cfg['NO_FILES_IMG'])  
cfg['DIR_CACHE_FILE'] = os.path.join(BASE_DIR, cfg['DIR_CACHE_FILE'])  
cfg['SHADER'] =         os.path.join(BASE_DIR, "shaders", cfg['SHADER'])
cfg['FONT_FILE'] =      os.path.join(BASE_DIR, "fonts", cfg['FONT_FILE'])
cfg['W_ICON_DIR'] =     os.path.join(BASE_DIR, "images", cfg['W_ICON_DIR']) 
cfg['W_BACK_IMG'] =     os.path.join(BASE_DIR, "images", cfg['W_BACK_IMG'])   
cfg['SRV_ROOT'] =       os.path.join(BASE_DIR, cfg['SRV_ROOT'])
