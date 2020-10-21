# RaspiPicFrame

Welcome to my Digital Picture Frame project for the Raspberry Pi! 
It uses the pi3d (http://pi3d.github.io/) project and is heavily based on PictureFrame2020.py from https://github.com/pi3d/pi3d_demos.
If you're new to the topic, I can definitively recommend to read https://www.thedigitalpictureframe.com/. You'll find a lot of useful info there!

## Major extensions to PictureFrame2020.py
- Largely enhaced ability to overlay texts: directory, pathname, image date, ...
- Read image EXIF info and enable to show them as text overlay
- Read GPS Info from image and reverse lookup to return location info
- Retrieve weather forecast and show info as every Nth slide between the images
- Optimized for direct mounting of image directory via WIFI
- Fast startup time due to improved improved directory scanning
- Enable to show images created within the last N days
- Optionally add randomly older pictures 
- Enable to specify blacklist for image directories which shall be ignored (e.g. backup, system directories, thumbnails, ...)

## Installation
You might want to follow the instructions on https://www.thedigitalpictureframe.com/how-to-add-crossfading-slide-transitions-to-your-digital-picture-frame-using-pi3d/
Instead of starting PictureFrame2020.py as listed within this article, just download the files of this repository to your raspberry pi.

## Configuration
In order to enable the enhanced features, this project added quite some new config options. SInce this definitively would break the reasonable limits of a command line, I decided to create a classical config file instead of an overloaded module of command line options.
You'll easily recognize the inherited options from PictureFrame2020config. They should still work as documented within this project.

### Weather forecast
For the weather forecast feature you need to create a free account on https://openweathermap.org/
Then please create an API key for https://openweathermap.org/api/one-call-api

Now you might want to have a look on following config entries:
W_LATITUDE      # latitude of your location
W_LONGITUDE     # longitude of your location
W_APPID         # put your API key here       
