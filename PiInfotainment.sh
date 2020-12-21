#/bin/bash
BASE_DIR=/home/pi/infotainment
EXIT_CODE=10

while [ "$EXIT_CODE" == "10" ]
do
  echo "Startig PiInfotainment system"
  /usr/bin/python3 $BASE_DIR/infotainment.py
  EXIT_CODE="$?"
done  

echo "PiInfotainment system termiated: Exit code $EXIT_CODE"