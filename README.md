# Sonar

Sonar is an app designed to provide alerts once specific devices enter your wifi network. Using the Sonar GUI, users can view a list of hosts on the current network and enable notifications for certain hosts. When an ARP scan detects that the relevant host has entered the network, Sonar will play the selected "ringtone" for that host within 15-20 seconds and provide an in-app popup to indicate as much.

## Installation

To install Sonar, clone and install the setup.py file.

```
git clone [url] .
sudo pip install -e sonarApp
```

## Dependencies

Since Sonar must run as sudo (due to Scapy), it may be necessary to install dependencies as sudo:

```
sudo pip install -r sonarApp/requirements.txt
```

## Usage

To open Sonar, simply run the following from command line:

```
sudo sonarApp
```