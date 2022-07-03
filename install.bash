#!/bin/bash

if ! pwd | grep -q Autopilot
then
    echo "Seems like you are not in the Autopilot directory. CD into it and then run the installer script."
    exit 1
fi

if [ -e ~/Library/com.UmActually.Autopilot ]
then
  echo "Seems like Autopilot is already installed."
  exit 1
else
  mkdir ~/Library/com.UmActually.Autopilot ~/Library/com.UmActually.Autopilot/Resources
fi

echo -e "\nInstalling PyAutoGUI (Python module for automation)\n"
python3 -m pip install pyautogui
echo

echo -e "\nCopying source files to ~/Library/com.UmActually.Autopilot"
cp -R *.py *.bash *.md ~/Library/com.UmActually.Autopilot
cp -R Resources/*.cpp Resources/*.json Resources/*.txt Resources/*.png ~/Library/com.UmActually.Autopilot/Resources

echo -e "\nCreating autopilot & ap executables"
c++ Resources/autopilot.cpp -o Resources/autopilot
chmod u+x Resources/autopilot
cp Resources/autopilot Resources/ap

echo -e "\nMoving executables to /usr/local/bin/\n"
sudo mv Resources/autopilot Resources/ap /usr/local/bin/

echo -e "\nAutopilot successfully installed. Reopen your terminal to start using it.\n"
