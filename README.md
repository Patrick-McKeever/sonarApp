# Sonar

Sonar is an app designed to provide alerts once specific devices enter your wifi network. Using the Sonar GUI, users can view a list of hosts on the current network and enable notifications for certain hosts. When an ARP scan detects that the relevant host has entered the network, Sonar will play the selected "ringtone" for that host within 15-20 seconds and provide an in-app popup to indicate as much.

## Installation

To install Sonar, clone the repository and use pip for installation:

```
git clone https://github.com/Patrick-McKeever/sonarApp.git
sudo pip install -r sonarApp/requirements.txt
sudo pip install -e sonarApp
```

## Dependencies

Running Sonar on Linux also requires "route", with which certain Linux distros may not ship. In this case, run:

```
sudo apt install net-tools
```

## Usage

To open Sonar, simply run the following from command line:

```
sudo sonarApp
```


## Potential Issues

Due to certain inconsistencies between KivyMD and later versions of Kivy, it is pertinent that Sonar be run with Kivy version 2.0.0rc3 or lower.
