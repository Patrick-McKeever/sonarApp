from scapy.all import *
from ipaddress import ip_network
from plyer import wifi
from subprocess import check_output, call
from time import sleep
import socket
import sys
import netifaces
import plyer
import sqlite3
import os

#Map out all MAC addrs currently in IP range based on "times" (int) ARP scans.
def surveyNetwork(subnetMask, times):
    #Get user's subnet.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(('8.8.8.8', 1))
    cidrNetwork = sock.getsockname()[0] + '/' + subnetMask
    subnet = str(ip_network(cidrNetwork, strict = False))
    
    #Broadcast ARP discovery requests across network.
    hosts = []
    
    for i in range(times):
        arpBroadcast = Ether(dst = "ff:ff:ff:ff:ff:ff") / ARP(pdst = subnet)

        for request, response in srp(arpBroadcast, timeout = 5, verbose = False)[0]:
            currentMacs = [host['mac'] for host in hosts]
            
            if response.hwsrc not in currentMacs:
                hosts.append({'ip': response.psrc, 'mac': response.hwsrc})

    return hosts

#Given a surveyResult, returns router's mac addr.
def getRouterMac(hostList):
    routerIp = netifaces.gateways()['default'][netifaces.AF_INET][0]
    return list(filter(lambda x: x['ip'] == routerIp, hostList))[0]['mac']

#Given router's macAddr, returns network's SSID.
def getNetworkName(routerMac):
    if sys.platform.startswith('linux'):
        interface = netifaces.interfaces()[1]
        fields = ['SSID', 'BSSID', 'FREQ']
        networksRaw = check_output([
                'nmcli', '--terse',
                '--fields', ','.join(fields),
                'device', 'wifi', 'list', 'ifname', interface
            ]).decode('utf-8')

        for line in networksRaw.splitlines():
            #Regex just splits the string without splitting escape characters;
            row = { field: value 
                       for field, value in zip(fields, re.split(r'(?<!\\):', line)) 
                  }
            
            row['BSSID'] = row['BSSID'].replace('\\:', ':')
            
            if(row['BSSID'] == routerMac):
                return row['SSID']
    
    elif sys.platform.startswith('win32'):
        currentNetwork = check_output([
                'netsh', interface,
                'show', 'interfaces'
            ]).decode('utf-8').split('\n')
        
        ssidLine = [ line for line in currentNetwork if 'SSID' in line and 'BSSID' not in line ]
        
        if ssidLine:
            ssidList = ssidLine[0].split(':')
            connectedSsid = ssidList[1].strip()
            return connectedSsid
        
    elif sys.platform.startswith('darwin'):
        return check_output('/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport -I | awk -F: "/ SSID/{print $2}"').decode('utf-8')
    
    return

#Returns list of hostIds on network;
def getHostsOnNetwork(surveyResults, hosts):
    macsOnNetwork = [host['mac'] for host in surveyResults]

    return { host['id']
        for host in hosts.values()
        if host['macAddr'] in macsOnNetwork }


