""" Config file of RaspiInfotainment project. 
"""

# Picture handling 
#PIC_DIR = "/home/pi/Pictures" # directory where to find the pictures
PIC_DIR = "/mnt/photo/2020" # directory where to find the pictures
#PIC_DIR = "//SYNOLOGYDS216/photo/2020"
SUBDIRECTORY = ""    # (optional) subdir of pic_dir - can be changed by MQTT
IGNORE_DIRS = ['.AppleDouble','@eaDir','#snapshot','Backup','Archive'] # Ignore images if they are in one of those directories
#CHECK_DIR_TM = 60.0  # time in seconds between checking if the image directory has changed
CHECK_DIR_TM = 300.0  # time in seconds between checking if the image directory has changed
RECENT_DAYS = 30      # If set to > 0, only images which were created within the last N days are shown.
OUTDATED_DIR_PROP = 10    # Include outdated directories with a propability of 1/x  
OUTDATED_FILE_PROP = 50  # Include outdated images with a propability of 1/x  
NO_FILES_IMG = "/home/pi/infotainment/no-pictures.jpg"  # image to show if none selected

# Shader 
FIT = True          # shrink to fit screen i.e. don't crop
BLUR_AMOUNT = 12.0   # larger values than 12 will increase processing load quite a bit
BLUR_EDGES = False   # use blurred version of image to fill edges - will override FIT = False
BLUR_ZOOM = 1.0      # must be >= 1.0 which expands the backgorund to just fill the space around the image
EDGE_ALPHA = 0.3     # background colour at edge. 1.0 would show reflection of image")
FPS = 20.0           # granularity of blending
BACKGROUND = (0.2, 0.2, 0.3, 1.0) # RGBA to fill edges when fitting
SHADER = "/home/pi/infotainment/shaders/blend_new"
KENBURNS = False     # Use Kenburns effect; it set to True: will set FIT->False and BLUR_EDGES->False
AUTO_RESIZE = True   # set this to False if you want to use 4K resolution on Raspberry Pi 4. You should ensure your images are the correct size for the display
BLEND_TYPE = 0.0     # choose between ["blend":0.0, "burn":1.0, "bump:2.0"]; type of blend the shader can do
BLEND_OPTIONS = {"blend":0.0, "burn":1.0, "bump":2.0} # that work with the blend_new fragment shader (better don't change!)

# Shuffle
SHUFFLE = True        # shuffle on reloading image files - can be changed by MQTT
RESHUFFLE_NUM = 1     # no of loops before reshuffling
RECENT_N = 5          # when shuffling the keep n most recent ones to play before the rest
#TIME_DELAY = 30.0    # time between consecutive slide starts - can be changed by MQTT
TIME_DELAY = 12.0     # time between consecutive slide starts - can be changed by MQTT
#FADE_TIME = 4.0      # change time during which slides overlap 
FADE_TIME = 2         # change time during which slides overlap 
SHOW_NAMES_TM = 6.0   # duration for shhowing text overlay over image 

# Text overlay
TEXT1_FORMAT = "<date> (<num>/<total>) <gps>"           
TEXT2_FORMAT = "<path>/<file> <desc>"                 
TEXT3_FORMAT = "<flen> (<flen35>) <exp> <fnum> <iso>"   
TEXT4_FORMAT = "<rating> <artist>"          
TEXT_POINT_SIZE = 45 
RESOLVE_GPS = True      # Resolve GPS coordinates in EXIF 

# Options
VERBOSE = True      # show debug messages
KEYBOARD = False     # set to False when running headless to avoid curses error. True for debugging
FONT_FILE = "/home/pi/infotainment/fonts/NotoSans-Regular.ttf"
DELAY_EXIF = True    # set this to false if there are problems with date filtering - it will take a long time for initial loading if there are many images!
CODEPOINTS = '1234567890AÄBCDEFGHIJKLMNOÖPQRSTUÜVWXYZ.,!* _-/:;@()°%abcdefghijklmnñopqrstuvwxyzäöüß' # valid text characters 

# MQTT
USE_MQTT = True
MQTT_SERVER = "localhost"   # Just change if you want to use a different MQTT server
MQTT_PORT = 1883            # Just change if you want to use a different MQTT server
MQTT_LOGIN  = " "           # Just change if you want to use a different MQTT server
MQTT_PASSWORD = ""          # Just change if you want to use a different MQTT server  

# Weather
W_SKIP_CNT = 2             # show weather info after each N pictures (=0 disables weather info)
W_REFRESH_DELAY = 300      # refresh weather info every N seconds
W_LATITUDE = 48.1355979    # latitude of your location (decimal degrees, e.g. 48.12345)
W_LONGITUDE = 11.3627159   # longitude of your location (decimal degrees, e.g. 11.98765)
W_UNIT = "metric"          # metric 
W_LANGUAGE = "de"          # language
W_API_KEY = "6ebd6acb5966433fad4c667062d4c18e" # openweathermap API key for "One Call API" 
W_BACK_IMG = "/home/pi/infotainment/weather_icons/weather_back_16_9.jpg"   # background image for weather info

W_NOW_TITLE     = "<date>: <pressure>, Luftf. <humidity>, Wolken <clouds>, Sonne <sunrise> / <sunset>"
W_NOW_TXT       = "<temp> (<ftemp>) <desc> <prec>, Wind <wind> (<winddeg>), UV <uvtxt> (<uvi>)"
W_ALERT_TITLE   = "Wetter Warnung!"
W_ALERT_TXT     = "<start> - <end>: <event>"
W_FORECAST_TITE = "<date> <daytime>"
W_FORECAST_TXT  = "<temp> (<ftemp>), Wind <wind> (<winddeg>), Niederschlag <pop>, Luftf. <humidity>, Wolken <clouds>" 
W_POINT_SIZE = 42

# CAMERA
CAMERA_ZOOM = 0.56          # zoom level for vlc player (e.g. shrink or enlarge video)
CAMERA_URL = "rtsp://user:webcamuser@192.168.178.51:554/h264Preview_01_main"  # URL of webcam stream, e.g. "rtsp://<user>:<pw>@<ip-address>:<port>/<path>"
CAMERA_THRESHOLD = 30       # threshold for the camera viewer. Defines how long viewer will be displayed after a MQTT event

#############################################################################
######### Usually you don't ned to change anything below this line ##########

EXIF_DICT = {}

from PIL import ExifTags
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

EXIF_DICT = create_EXIF_dict() 

