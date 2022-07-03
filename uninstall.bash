#!/bin/bash

if ! [ -e ~/Library/com.UmActually.Autopilot ]
then
  echo "Seems like Autopilot is not installed."
  exit 1
else
  rm -rIv ~/Library/com.UmActually.Autopilot
fi

sudo rm -Iv /usr/local/bin/ap /usr/local/bin/autopilot

echo -e "\nAutopilot successfully uninstalled.\n"
