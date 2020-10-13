import sqlite3
from . import networking
from mac_vendor_lookup import MacLookup

#To be passed as cursor's 'row factory'.
def dictFactory(cursor, row):
    dictionary = {}
    for idx, col in enumerate(cursor.description):
        dictionary[col[0]] = row[idx]
    return dictionary

#Create database if it doesn't exist and create relevant tables if they don't exist.
def dbSetup(conn, cursor):
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS networks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ssid TEXT,
                routerMac TEXT UNIQUE
              );'''
          )
        cursor.execute('''CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                macAddr TEXT,
                ipAddr TEXT,
                manufacturer TEXT,
                networkId INTEGER REFERENCES networks(id), 
                notificationEnabled INTEGER DEFAULT 0, 
                tone INTEGER DEFAULT 0,
                UNIQUE(macAddr, networkId)
            );'''
        )
        
        conn.commit()
        
    except sqlite3.Error:
        return 1
    
    return 0

#Takes a scan of network, returns id of network in db.
def getNetworkId(hosts, conn, cursor):
    routerMac = networking.getRouterMac(hosts).upper()
    ssid = networking.getNetworkName(routerMac)

    try:
        cursor.execute('SELECT id FROM networks WHERE routerMac = ?',
            [routerMac])
        return cursor.fetchone()['id']
    
    except:
        cursor.execute('INSERT OR ABORT INTO networks (ssid, routerMac) VALUES (?, ?)',
            [ssid, routerMac])
        conn.commit()
        
        return cursor.lastrowid
    
#Populate the hosts table in the database based on scan results (hosts).
def catalogNetwork(conn, cursor, surveyResults):
    networkId = getNetworkId(surveyResults, conn, cursor)
    
    cursor.execute('SELECT * FROM hosts WHERE networkId = ?',
        [networkId])
    hosts = { host['macAddr'] : host 
        for host in cursor.fetchall() }
    
    for host in surveyResults:
        notRecorded = (host['mac'] not in hosts.keys())
        
        #Does db ip match survey ip? (can differ in dynamic-addressed networks)
        wrongIp = (0 if notRecorded 
            else (hosts[host['mac']]['ipAddr'] != host['ip']))
        
        if notRecorded or wrongIp:
            try:
                manufacturer = MacLookup().lookup(host['mac'])
            except:
                manufacturer = 'unknown'
            
            #Upsert.
            cursor.execute('''INSERT OR ABORT INTO hosts (macAddr, ipAddr, manufacturer, networkId) VALUES (?, ?, ?, ?)
                ON CONFLICT(macAddr, networkId) DO UPDATE SET ipAddr = ?;''',
                [host['mac'], host['ip'], manufacturer, networkId, host['ip']])
            
            hosts[host['mac']] = {
                'id': cursor.lastrowid,
                'macAddr': host['mac'],
                'ipAddr': host['ip'],
                'manufacturer': manufacturer,
                'networkId': networkId,
                'notificationEnabled': 0,
                'tone': 0
            }
            
    conn.commit()
    #Make dict w/ hostId as key rather than mac.
    retHosts = { host['id'] : host for _, host in hosts.items() }
    
    return retHosts