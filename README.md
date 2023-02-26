# Raspi Infotainment system

**This project is still work-in-progress!**

Welcome to the Raspi Infotainment system project!  
This is a hobby project for Raspberry Pi which combines following core functionalities:
- Advanced digital picture frame: Enables to displays you digital images in a slideshow with smooth transitions 
- Weather forecast: Show your local weather forecast
- Surveillance camera viewer: Show live picture of a surveillance camera when it detects motion  
- Simple webserver: Enables you to remotely control the Infotainment System
- Enable to integrate into almost any home automation system which supports HTTP hooks 
- Reads and displays data from a photovoltaic inverter (M-TEC)  

The Picture Frame functionality of RaspiInfotainment uses the pi3d (https://pi3d.github.io/) project and is heavily based on PictureFrame2020.py from https://github.com/pi3d/pi3d_demos. Kudos to these awsome projects!

By the way: If you're new to the topic, I can definitively recommend to read https://www.thedigitalpictureframe.com/. You'll find a lot of useful info there!

## Functionalities
Following sections explain the 3 core functionalities.

### Picture Frame
The major enhancements of RaspiInfotainment vs. PictureFrame2020.py are:

- Optimized for direct mounting of image directory via WIFI (e.g. from a NAS) - no copying required!
- Fast startup time - even if image directory contains a huge number of sub-directories and pictures by implementing a directory cache
- Largely enhanced ability to overlay info texts: directory, pathname, image date, ...
- Read image EXIF info and enable to show them as text overlay
- Read GPS Info from image and reverse lookup to return human readable location info
- Enable to show images created within the last N days
- Optionally add randomly older pictures 
- Enable to specify blacklist for image directories which shall be ignored (e.g. backup, system directories, thumbnails, ...)
- Finegrain control which pictures shall be shown via YUML files with file name pattern matching  
- Energy saving: Raspi monitor can be scheduled to be switched ON/OFF automatically at certain times 

### Webserver
Raspi Infotainment provides a HTTP server which can be used to remote control the Infotainment server.
Per default it will start on your Raspberry PI on standard port 80. So you can easily access it within any browser within your lokal network by entering `http://<IP address of your Raspberry Pi>`

The webserver communicates with the infotainment server via the mosquitto MQTT broker on your Pi.

It offers:

- Server configuration: Change most useful server config settings at runtime, e.g. start date, end date, ...
- Server control: Remote control the infotainment server, e.g. pause,  monitor on/off, restart, shutdown, ...
- Server status: Shows some status info from yor Raspi, e.g. which photo is currently displayed, monitor status, CPU temperature, etc.
- Picture history: Recent photos which were displayed


### Weather forecast
RaspiInfotainment enables to show a weather forecast page. It uses https://openweathermap.org/ to retrieve the forecast data for your location.
This forecast page then gets shown as every Nth slide between the images of the picture viewer.

### Surveillance camera viewer
This fuctionality is meant to display e.g. a frontdoor surveillance camera. It gets automatically displayed when the camera detects a motion.

This functionality automatically switches the monitor ON even if it was scheduled to be OFF at this point in time.

### PV device data from RCT Power
This module enables to read interesting parameters from a RCT Power GmbH device. 
This module is based on the great project https://github.com/svalouch/python-rctclient 

--------------------------------------

## Installation
You might want to follow the instructions on https://www.thedigitalpictureframe.com/how-to-add-crossfading-slide-transitions-to-your-digital-picture-frame-using-pi3d/. This is a really good decription how to setup the Rasperry Pi.

Instead of starting `PictureFrame2020.py` as listed within this article, just download the files of *this* repository to your Raspberry Pi. The main script you need to start is `PiInfotainment.sh`.

The whole package consists of:
```
Raspberry Pi
  - PiInfotainment.sh
     - infotainment.py    # the main program
       - vlc              # surveillance camera viewer
  - infoserver.py         # Webserver
  - mosquitto             # MQTT broker
```

To install, you might want to follow this instruction:

_Hint:_ You need to be root (or use sudo).

Some prerequisites we need to install:

```
apt-get install vlc
apt-get install mosquitto mosquitto-clients
apt-get install influxdb-client
pip3 install exifread
pip3 install --upgrade pil
pip3 install --upgrade Pillow
pip3 install python-vlc 
pip3 install paho-mqtt
pip3 install pyyaml
pip3 install pyheif
pip3 install requests
pip3 install rctclient
```

if pyheif is not working correctly, you might want to try this:
```
apt-get remove libde265-0 -y && sudo apt-get remove libheif1 -y && sudo apt-get remove libheif-dev -y && sudo apt-get remove libde265-dev -y && sudo apt install autotools-dev automake libtool texinfo x265 -y && git clone https://github.com/strukturag/libde265.git && cd libde265 && ./autogen.sh && ./configure --disable-dec265 --disable-sherlock265 --prefix /usr && make && sudo make install && cd .. && git clone https://github.com/strukturag/libheif.git && cd libheif && ./autogen.sh && ./configure --prefix /usr && make && sudo make install && cd .. && git clone https://github.com/libffi/libffi.git && cd libffi && ./autogen.sh && ./configure --prefix /usr && make && sudo make install && cd .. && pip3 install git+https://github.com/carsales/pyheif.git && sudo pip3 install pyheif
```

Now let's install the PIInfotainment system:

```
cd /home/pi/infotainment && wget https://github.com/croedel/PiInfotainment/archive/main.zip && unzip main.zip && rm main.zip
```

In a next step, you need to copy `templates/config-template.yaml` to `config.yaml`. Within this, you need to config e.g. your picture directory, your geo-location, API key etc. (See below for more details on configuration)

```
cd /home/pi/infotainment && cp templates/config-template.yaml config.yaml
```

### Auto start using systemd
In order to start the PiInfotainment system automatically, you can use the systemd script templates within `templates` directory:

| Script                | Description
|-----------------------|----------------------------------------------
| infotainment.service  | Start script for the main PiInfotainment system
| infoserver.service    | Start the Webserver to remote control the PiInfotainment system
| mnt-photo.mnt         | You can optionally use this to auto-mount a NFS share e.g. from your NAS 

You just might need to replace some minor things like hostname/IP addresses etc.

_Hint:_ In order to install them, you need to be root (or use sudo):

- Copy them to the systemd directory `/etc/systemd/system`
- Make them readable for everybody: `chmod 644 /etc/systemd/system/infotainment.service` etc 
- Reload systemctl units by `systemctl daemon-reload`
- To start a service manually, use `systemctl start infotainment.service` etc. 
- To start a service at boot time automatically, use `systemctl enable infotainment.service` etc.

_Tipps:_ 
- The logs will get written to `/var/log/syslog`. So you can watch what the system is doing by e.g. `tail -f /var/log/syslog`
- If you have a realy huge photo directory, the first start will take a few minutes since the infotaiment system needs to walk through the whole directory tree. Subsequent starts will be significantly faster due to the implemeted disk cache.

--------------------------------------

## Configuration
In order to enable the enhanced features, this project added quite some new config options. Since this definitively would break the reasonable limits of a command line, I decided to create a classical config file instead of an overloaded module of command line options.

You'll easily recognize the inherited options from PictureFrame2020config. They should still work as documented within this project. A really good description of those can be found on https://www.thedigitalpictureframe.com/pi3d-parameters-directory-config/.

Some config options you might want to have a special look on:

### Digital picture frame
Quite obviously, you need to configure where to find your photos. This can be a local drive or a mounted drive e.g. from your NAS. 

```
PIC_DIR     # directory where to find the pictures
```

Depending of the directory structure you're using for your pictures, you might have some naming convention for directories which shouldn't be used for the Infotainment system. (e.g. Backup, Archive, ...) This option is working recursively, i.e. it prunes the directory. Neither files in the directory itself nor in its children get included.

```
IGNORE_DIRS   # Ignore images if they are in one of those directories
```

If you have a huge pohoto archive, you might want to limit the timerange for the fotos you want to show.

```
DATE_FROM    # Sets start date [y,m,d] of the timerange for the fotos you want to show (None=unlimited)
DATE_TO      # Sets end date [y,m,d] of the timerange for the fotos you want to show (None=unlimited)
```

Static dates can be good, but I personally like that the Infotainment system should display the most recent photos:

```
RECENT_DAYS   # If set to > 0, show images which were created within the last N days (supercedes DATE_FROM)
```

Selecting by timerange is the foundation. But wouldn't it be nice to randomly add some older pictures? You can set the propabitily the Infotainemt systems selects an outdated file by using the following options:

```
OUTDATED_FILE_PROP  # Include outdated images with this propability (0.0=disable) 
```

To avoid a "hard cut" between the files which are included because they are within `DATE_FROM` and `DATE_TO`, and those outside this time interval, you can set `PROP_SLOPE`. This defines a time span in days, which smoothly decreases the propability depending on the "distance" from the configured time span (`DATE_FROM`and `DATE_TO`). 

Example: If you defined `RECENT_DAYS=60` you would miss fotos take 61 days ago. If you define `PROP_SLOPE=10` fotos taken 61 days ago would get included with 90% propability, those taken 62 days ago with 80% propability, etc. 

```
PROP_SLOPE   # Timespan for smoothly decreasing propability to select files outside timerange 
```

__Hint:__ Per default, all pictures within the `PIC_DIR` directory tree get included. For a more fine grain control of which files shall get included in a certain directory, you can create a "magic file" named `.INFOTAINMENT.yaml` within a directory. 
Please see section below for more details. 

Some config options which define the timing

```
TIME_DELAY      # Defines how long a single slide is shown 
FADE_TIME       # change time during which slides overlap 
INFO_TXT_TIME   # duration for showing text overlay over image 
```

### Scheduled switching of the monitor
For convenience and energy saving purposes you can schedule to switch you PI's monitor ON and OFF at certain times. You can schedule this very fine grain an a weekday basis. 

`MONITOR_SCHEDULE` allows to define multiple pairs of start-stop time for each weekday.
- Weekdays are numbered from 0 to 6: 0=Monday ... 6=Sunday
- Each weekday may contain as many start-stop time pairs as you need
- Times are defined as `[HH,MM]`

```
MONITOR_SCHEDULE : 
  0: 
    - [[07,00], [11,00]] 
    - [[16,00], [22,00]] 
  1: 
    - [[07,00], [11,00]] 
    - [[16,00], [22,00]] 
  2: 
    - [[07,00], [11,00]] 
    - [[16,00], [22,00]] 
  3: 
    - [[08,00], [22,30]] 
  4: 
    - [[08,00], [22,30]] 
  5: 
    - [[08,00], [22,30]] 
  6:
    - [[08,00], [22,30]]  
```
If you switch the monitor manually (e.g. by using the Webserver), the manually set status has precedence and "wins" over the automated scheduling.

### Magic YAML file
Per default, all pictures within the `PIC_DIR` directory tree get included. For a more fine grain control of which files shall get included in a certain directory, you can create a "magic file" named `.INFOTAINMENT.yaml` within a directory. 

This YAML formatted file contains an `exclude` and and `include` section. Both can contain list of filenames or wildcard patterns. It supports UNIX shell-style wildcards (e.g. `*` and `?`) (see https://docs.python.org/3/library/fnmatch.html). 

Using this, you can e.g. 
- exclude all images in a certain directory
- exclude all images except the listed ones
- exclude images with a certain name pattern
- ...

Some examples:
```
# exlude all files within this directory
---
exclude:
  - "*"
include:
```

```
# exlude all files, except those named "IMG_*.jpg"
---
exclude:
  - "*"
include:
  - "IMG_*.jpg"
```

```
# exlude all named "DCP_*.jpg" except those named "DCP_000*.jpg" or "DCP_001*.jpg" 
---
exclude:
  - "DCP_*.jpg"
include:
  - "DCP_000*.jpg"
  - "DCP_001*.jpg"
```

### General info screen options
The infotainment system supports showing 2 types of info screens:
- Weather forecast screen
- Photo Voltaic (PV) info screen

Both screens are shown alternating.

WIth the following options you can adjust how often the info screens appear and how often the informatio shall get refreshed.

```
INFO_SKIP_CNT : 15          # show infotainment screen after each N pictures (=0 disables infotainment sceen)
INFO_REFRESH_DELAY : 300    # refresh infotainment info every N seconds
```

### Weather forecast
For the weather forecast feature you need to create a free account on https://openweathermap.org/
Then please create an API key for https://openweathermap.org/api/one-call-api

Now you might want to have a look on following config entries:

```
W_LATITUDE      # latitude of your location
W_LONGITUDE     # longitude of your location
W_API_KEY       # put your API key here       
```

Though the weather screen is created dynamically according to the display resolution, it is optimized for a display size of FullHD (1920 x 1080). If you use a different screen size or ratio, you might need to adjust it.
You might want to start with following config entries:

```
W_POINT_SIZE     # weather text size
W_STATIC_SIZE    # size of static images (temp, humidity, wind, ...)
W_ICON_SIZE      # size of weather forecast icons (sunny, cloudy, ...) 
W_MARGIN_LEFT    # left margin 
W_MARGIN_TOP     # top margin
W_SPACING        # spacing between the weather columns
```

If this shouldn't give you the desired results, you can think about changing the sizing calculation within `weatherscreen.py`

### RKI COVID Incidence
Nowadays the COVID 7-day incidence is a very important figure. Therefore I added a functionality which retrieves this info from RKI and displays it on to the weather screen.
To define the location for which you want to display the figure, you should go to https://npgeo-corona-npgeo-de.hub.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0/data. Search for your "Landkreis" and look for the "AGS" id.

The second important figure is the 7-day hospitalization index. It is retrieved from the RKI GitHub Repository (https://github.com/robert-koch-institut)
[Robert Koch-Institut (2021): COVID-19-Hospitalisierungen in Deutschland, Berlin: Zenodo. DOI:10.5281/zenodo.5519056.]

This location id as well as the region name then sould be added to config.yaml: 

```
RKI_ID : 09179          # RKI region ID
RKI_REGION : "Bayern"   # Bundesland
```

### PV Information
The Infotainment System supports showing some information about a potentially installed Photo Voltaic (PV) system.
If you don't own a PV or want to disable the functionality, set `PV_INFO_ENABLE` to `False`.

Unfortunately, there is no standard for PV systems. Each one supports their own proprietary API's. Therefore you probably will have to adjust the implementation according to your system. If you want to adapt the PV info to your PV system, you might want to have a look to `PVinverter.py`. Here the data from the PV inverter is fetched and mapped to a normalized data structure. You hopefully can change that quite easily to map your PV inverter's data. 

I personally own an M-TEC Energybutler system. For that one I created an API which retrieves the necessary data. You can find it with the project `MTEC_energybutler_API`. In order to use it, please install it in a sub-folder of this project.
In order to connect to your PV device, you need to set e-mail adress, password and your individual stationId.

```
PV_INFO_ENABLE : True       # Enable / disable PV Info
PV_EMAIL : ""               # e-mail address you used to register at M-TEC portal
PV_PASSWORD : ""            # password you used to register at M-TEC portal
PV_STATION_ID : ""          # Your individual MCT power stationId
```

Additionally supported parameters are:
```
PV_ICON_DIR : "icons"       # PV icon directory
PV_BACK_IMG : "PV_background_16_9.png"   # background image for PV info 
PV_POINT_SIZE : 80          # PV text size
PV_MARGIN_LEFT : 30         # left margin 
PV_MARGIN_TOP : 75          # top margin
```

### Metadata display
Pi Infotainment offers 4 text lines to show customizable metadata of the shown image: 2 footer lines and 2 header lines.
The content can be configures within the config file:

``` 
TEXT_FORMAT : 
  - "<flen> (<flen35>) <exp> <fnum> <iso> <artist>"  # Header line 1 
  - "<rating> <desc>"                                # Header line 2
  - "<date> <gps>"                                   # Footer line 1
  - "<path>/<file>"                                  # Footer line 2
```

The format supports following variables which will be dynamically replaced with image data:

| Variable      | Description 
|------------   |------------------------- 
| `<file>`      | filename of image 
| `<path>`      | pathname of image
| `<date>`      | image creation date (dd.mm.yyyy)
| `<num>`       | number of current picuture in current file list
| `<total>`     | # total number of picutures in current file list 

Additionally following EXIF metadata tags are supported

| Variable      | EXIF Tag                    | Description
|------------   |-----------------------------|---------------------
| `<rating>`    | Rating                      | 0-5 "stars"
| `<make>`      | Make                        | Camera 
| `<model>`     | Model                       | Camera model
| `<artist>`    | Artist                      | Photographer
| `<copy>`      | Copyright                   | Copyright
| `<desc>`      | ImageDescription            | Description of the image
| `<exp>`       | ExposureTime                | Exposure time
| `<fnum>`      | FNumber                     | Camera aperture
| `<iso>`       | ISOSpeedRatings             | ISO rating
| `<flen>`      | FocalLength                 | focal length 
| `<flen35>`    | FocalLengthIn35mmFilm       | focal length compared to a 35mm camera  
| `<res>`       | ExifImageWidth, ExifImageHeight | image width and height
| `<gps>`       | GPSInfo                     | reverse lookuped geo location 


### Surveillance camera viewer
The project assumes you have a surveillance camera which can be accessed via e.g rtsp protocol.
This then gets displayed by VLC.

Add this to config.yaml e.g. as

```
CAMERA_URL    # URL of webcam stream
CAMERA_ZOOM   # zoom level for VLC to e.g. shrink or enlarge video being displayed
```

Now you need to add a Web Hook to you surveillance camera. If you're using Surveillance Station, you e.g. can do this via `Action rules`.

Create a rule which gets triggered when the camera detects a motion. Let it be repeated in a slightly shorter interval then you've set the `CAMERA_THRESHOLD`. This ensures that the surveillance camera keeps being displayed as long as the motion is still active. 

And add following URL as Web Hook:

```
http://<IP Address of you RasperryPi>/index.html?topic=camera
```

-------------------------

## Home-Automation integration
It's very easy to integrate the Infotainment system into any existing Home-Automation environment which supports web hooks (e.g. Alexa, Google Home, ...).

You can easily use any command which is provided by the Webserver:

```
http://<IP Address of you RasperryPi>/index.html?topic=<command>&data=<data>
```  

The webserver writes a message into the mosquitto MQTT broker on ypur Pi which is then again read by the infotainment system.

## Utilities
### Dircache Manager

`dircachemgr.py` is a small command-line tool which you can use to manage the picture dir cache. You can e.g. list the content, refresh it etc. See help (`dircachemgr.py -h`) for more details
