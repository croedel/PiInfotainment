# Raspi Infotainment system

**This project is still work-in-progress!**

Welcome to the Raspi Infotainment system project!  
This ia a hobby project meant for Raspberry Pi which combines following core functionalities:
- Advanced digital picture frame: Enables to displays you digital images in a slideshow with smooth transitions 
- Weather forecast: Show your local weather forecast
- Surveillance camera viewer: Show live picture of a surveillance camera when it detects motion  
- Simple webserver: Enables you to remotely control the Infotainment System

The Picture Frame functionality of RaspiInfotainment uses the pi3d (https://pi3d.github.io/) project and is heavily based on PictureFrame2020.py from https://github.com/pi3d/pi3d_demos.

By the way: If you're new to the topic, I can definitively recommend to read https://www.thedigitalpictureframe.com/. You'll find a lot of useful info there!

## Functionalities
Following sections explain the 3 core functionalities.

### Picture Frame
The major enhancements of RaspiInfotainment vs PictureFrame2020.py are:

- Optimized for direct mounting of image directory via WIFI (e.g. from a NAS) - no copying required!
- Fast startup time - even if image directory contains a huge number of sub-directories and pictures 
- Largely enhanced ability to overlay info texts: directory, pathname, image date, ...
- Read image EXIF info and enable to show them as text overlay
- Read GPS Info from image and reverse lookup to return human readable location info
- Enable to show images created within the last N days
- Optionally add randomly older pictures 
- Enable to specify blacklist for image directories which shall be ignored (e.g. backup, system directories, thumbnails, ...)
- Enable to ignore directories which contain a "magic filename" `.INFOTAINMENT_IGNORE.txt`
- Monitor can be scheduled to be switched ON/OFF automatically at certain times 

### Webserver
RaspiInfotainment provides a simple HTTP server which can be used to remote control the Infotainment server.
Per default it will start on your Raspberry PI on standard port 80. So you can easily access it within any browser within your lokal network by entering `http://<IP address of yor Raspberry Pi>`

It enables following commands:

| Command       | Parameter   | Description
|---------------|-------------|-----------------------
| Back          | -           | Back to previous image
| Subdirectory  | -           | Scan and display images withi this subdirectory
| Start date    | YYYY/MM/DD  |  Show only images which were taken after this date
| End date      | YYYY/MM/DD  |  Show only images which were taken before this date 
| Recent days   | N           |  Show only images which were taken within the last N days
| Time delay    | N           |  How long each photo shall be shown (in seconds)
| Pause         | -           |  Pause photos
| Camera        | -           |  Switch to surveillance camera viewer
| Monitor       | ON, OFF, AUTO | Switch monitor ON or OFF manually or re-set to AUTO mode

Feel free to make it look nicer by e.g. customizing `stylesheet.css` ;-)

The webserver writes a message into the mosquitto MQTT broker on your Pi which is then again read by the infotainment system.

### Weather forecast
RaspiInfotainment enables to show a weather forecast page. It uses https://openweathermap.org/ to retrieve the forecast data for your location.
This forecast page then gets shown as every Nth slide between the images of the picture viewer.

### Surveillance camera viewer
This fuctionality is meant to display e.g. a frontdoor surveillance camera. It gets automatically displayed when the camera detects a motion.

This functionality automatically switches the monitor ON evan if it was scheduled to be OFF at this pount in time.

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

Some prerequisites:

```
apt-get install vlc
apt-get install mosquitto mosquitto-clients
pip3 install exifread
pip3 install --upgrade pil
pip3 install --upgrade Pillow
pip3 install python-vlc 
pip3 install paho-mqtt
pip3 install pyheif
```

Now let's install the PIInfotainment system:

```
cd /home/pi/infotainment && wget https://github.com/croedel/PiInfotainment/archive/main.zip && unzip main.zip && rm main.zip
```

In a next step, you need to copy the config-template.py to config.py. Within this, you need to config e.g. your picture directory, your geo-location, API key etc. (See below for more details on configuration)

```
cd /home/pi/infotainment && cp config-template.py config.py
```

### Auto start using systemd
In order to start the PiInfotainment system automatically, you can use the systemd script templates within systemd directory:

| Script                | Description
|-----------------------|----------------------------------------------
| infotainment.service  | Start script for the main PiInfotainment system
| infoserver.service    | Start the Webserver to remote control the PiInfotainment system
| mnt-photo.mnt         | You can optionally use this to auto-mount a NFS share e.g. from your NAS 

You just might need to replace some minor things like IP addresses etc.

_Hint:_ In order to install them, you need to be root (or use sudo):

- Copy them to the systemd directory `/etc/systemd/system`
- Make them readable for everybody: `chmod 644 /etc/systemd/system/infotainment.service` etc 
- Reload systemctl units by `systemctl daemon-reload`
- To start a service manually, use `systemctl start infotainment.service` etc. 
- To start a service at boot time automatically, use `systemctl enable infotainment.service` etc.

_Tipp:_ The logs will get written to `/var/log/syslog`

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

Depending of the directory structure you're using for your pictures, you might have some naming convention for directories which shouldn't be used for the Infotainment system. (e.g. Backup, Archive, ...)

```
IGNORE_DIRS   # Ignore images if they are in one of those directories
```

I personally like that the Infotainment system should display the most recent photos:

```
RECENT_DAYS   # If set to > 0, only images which were created within the last N days are shown```
```

It's nice to randomly add some older pictures. You can set the propabitily the Infotainemt systems selects an outdated file by using the following options:

```
OUTDATED_FILE_PROP  # Include outdated images with a propability of 1/x (0=disable)
```

Some config options which define the timing

```
TIME_DELAY      # Defines how long a single slide is shown 
FADE_TIME       # change time during which slides overlap 
INFO_TXT_TIME   # duration for showing text overlay over image 
```

__Tipp:__ If you have certain sub-directories within your `PIC_DIR` which you don't want to be displayed, just create or touch) a "magic file" named `.INFOTAINMENT_IGNORE.txt` within them. RaspiInfotainment will ignore all images within these directories. 

For convenience and energy saving purposes you can schedule to switch you PI's monitor ON and OFF at certain times. You can schedule this very fine grain an a weekday basis. If you switch the monitor manually (e.g. by using the Webserver), the manually set status has precedence and "wins" over the automated scheduling.

```
# Monitor schedule
# One line per day: 0=Monday ... 6=Sunday
# For each day you can define an array of start-stop time pairs, each of them consists of hour and minute 
MONITOR_SCHEDULE = {
  0: [ [(7,0), (10,0)], [(16,0), (22,0)] ], 
  1: [ [(7,15), (10,30)], [(16,0), (22,0)] ], 
  2: [ [(7,0), (18,0)] ], 
  3: [ [(7,0), (10,0)], [(16,0), (18,0), [(10,0), (22,30)]] ], 
  4: [ [(7,0), (10,0)], [(16,0), (22,0)] ], 
  5: [ [(8,0), (23,30)] ], 
  6: [ [(8,0), (23,30)] ] 
}
```

### Weather forecast
For the weather forecast feature you need to create a free account on https://openweathermap.org/
Then please create an API key for https://openweathermap.org/api/one-call-api

Now you might want to have a look on following config entries:

```
W_SKIP_CNT      # show weather info after each N pictures (=0 disables weather info)
W_LATITUDE      # latitude of your location
W_LONGITUDE     # longitude of your location
W_API_KEY       # put your API key here       
```

### Surveillance camera viewer
The project assumes you have a surveillance camera which can be accessed via e.g rtsp protocol.
This then gets displayed by VLC.

Add this to config.py e.g. as

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

## Home-Automation integration
It's very easy to integrate the Infotainment system into any existing Home-Automation environment which supports web hooks (e.g. Alexa, Google Home, ...).

You can easily use any command which is provided by the Webserver:

```
http://<IP Address of you RasperryPi>/index.html?topic=<command>&data=<data>
```  

The webserver writes a message into the mosquitto MQTT broker on ypur Pi which is then again read by the infotainment system.
