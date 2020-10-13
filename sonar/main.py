#!/usr/bin/env python3

import os
import sys

#Fix kivy bug by specifying relevant info.
if sys.platform.startswith('linux'):
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['DISPLAY'] = ':0'
    os.environ['KIVY_AUDIO'] = 'sdl2'

from screeninfo import get_monitors
from kivy.config import Config

#Size window to fullscreen. Must be done at start of script. 
#Built-in kivy fullscreen method is buggy, causes debian systems to crash.
screenDimensions = get_monitors()[0]
Config.set('graphics', 'width', screenDimensions.width)
Config.set('graphics', 'height', screenDimensions.height)
Config.set('kivy','window_icon','sonar.webp')


from kivymd.app import MDApp
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.list import MDList, OneLineListItem, OneLineIconListItem, IconLeftWidget, OneLineAvatarIconListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.behaviors.toggle_behavior import MDToggleButton
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.icon_definitions import md_icons
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.selectioncontrol import MDSwitch, MDCheckbox
from kivymd.uix.snackbar import Snackbar

from kivy.lang import Builder
from kivy.metrics import dp, sp, MetricsBase
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window
from kivy.properties import BooleanProperty, StringProperty, NumericProperty

from math import floor

from . import networking
from . import database

import sqlite3
import multiprocessing
import pygame

class ToggleButtonClass(MDRectangleFlatButton, MDToggleButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_down = self.theme_cls.primary_light

class itemConfirm(OneLineAvatarIconListItem):
    divider = None
    active = BooleanProperty()
    index = NumericProperty()

#Not possible to inherit from item confirm without screwing up the on_press 
#function for this class in the '.kv' file.
#On_press statement must be in '.kv' file, because main file requires sudo priveleges.
#Executing the callback with sudo priveleges interferes.
class itemConfirmMusic(OneLineAvatarIconListItem):
    divider = None
    active = BooleanProperty()
    index = NumericProperty()
    pass

class notificationSettings(MDBoxLayout):
    enabled = BooleanProperty(None)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        pass    

#If a host enters/leaves the network, put its id onto notifsQ.
#If we lock this thread, the main process halts, so we can't write to initHosts.
#Instead, we write to hostsQ while main processs periodically sets its host values
#equal to the values of hostsQ.
def notifsProducer(initSurveyRes, initHosts, notifsQ, hostsQ):
    conn = sqlite3.connect('database.db')
    conn.row_factory = database.dictFactory 
    cursor = conn.cursor()
    
    currentHostSet = networking.getHostsOnNetwork(
            initSurveyRes, initHosts)
    
    while 1:
        surveyRes = networking.surveyNetwork('255.255.255.0', 3)
        
        #Both this and main proc write to db, but only this one reads periodically.
        #Since sql is atomic, we can prevent conflicts.
        hosts = database.catalogNetwork(conn, cursor, surveyRes)
        oldHostSet = currentHostSet
        currentHostSet = networking.getHostsOnNetwork(
            surveyRes, hosts)
        
        notifs = []
        
        for hostId, host in hosts.items():
            #Host just entered network and is notif-enabled.
            needsNotif = (hostId in (currentHostSet - oldHostSet)
                and host['notificationEnabled'])

            if needsNotif:
                notifs.append(hostId)

            host['onNetwork'] = (hostId in currentHostSet)

        print(hosts)
        notifsQ.put(notifs)
        hostsQ.put(hosts)
    
#Because of the way kivy is built, all UI goes in this class.
class sonarApp(MDApp):
    #Since we named class 'sonarApp', kivy auto-builds 'sonar.kv'.
    def build(self):
        self.theme_cls.primary_palette = 'DeepPurple'
    
    #Runs when user starts app.
    def on_start(self):
        self.conn = sqlite3.connect('database.db')
        #Ensure that results from sqlite queries are returned as dictionaries.
        self.conn.row_factory = database.dictFactory 
        self.cursor = self.conn.cursor()

        #Make all relevant tables if they do not yet exist.
        database.dbSetup(self.conn, self.cursor)
        
        #Get hosts on network from a single ARP broadcast.
        hostsOnNetwork = networking.surveyNetwork('255.255.255.0', 1)
        
        currentNetworkId = database.getNetworkId(hostsOnNetwork, self.conn, self.cursor)
        
        self.cursor.execute('SELECT * FROM networks WHERE id = ?', [currentNetworkId])
        currentNetwork = { currentNetworkId : self.cursor.fetchone() }
        
        self.cursor.execute('SELECT * FROM networks WHERE id != ?', [currentNetworkId])
        restOfNetworks = { network['id'] : network
            for network in self.cursor.fetchall() }
        
        #Ensure that currentNetwork is first in 'networks', and thus on GUI.
        networks = { **currentNetwork, **restOfNetworks }

        #Create list of networks, which give a table of hosts when clicked.
        for network in networks.values():
            columnWidth = (self.root.width * 0.69) / 5 / 5

            networkListItem = OneLineListItem(
                text = network['ssid'],
                on_press = (
                    lambda _, network = network, columnWidth = columnWidth:
                    self.networkTable(network, columnWidth) 
                )
            )

            self.root.ids['networksList'].add_widget(networkListItem)

        self.hosts = database.catalogNetwork(
            self.conn, self.cursor, hostsOnNetwork) 
        hostIdsOnNetwork = networking.getHostsOnNetwork(
            hostsOnNetwork, self.hosts)
        
        for hostId in self.hosts:
            onNetwork = (hostId in hostIdsOnNetwork)
            self.hosts[hostId]['onNetwork'] = onNetwork
        
        notifsQ = multiprocessing.Queue()
        hostsQ = multiprocessing.Queue()

        self.notifsProducerP = multiprocessing.Process(
            target = notifsProducer,
            args = (hostsOnNetwork, self.hosts, notifsQ, hostsQ,)
        )
        self.notifsProducerP.start()

        #Play ringtone for each notif-enabled host that entered network.
        #Update self.hosts data.
        def notifsConsumer(_):
            if not notifsQ.empty():
                for hostId in notifsQ.get_nowait():
                    MDDialog(
                        title = '%s has entered the network' % self.hosts[hostId]['macAddr']
                    ).open()
                    self.playRingtone(self.hosts[hostId]['tone'])
            
            #update host values.
            if not hostsQ.empty():
                currentHosts = hostsQ.get_nowait()
                
                for hostId, host in currentHosts.items():
                    self.hosts[hostId] = host


        #Check / react to contents of notifsQ every 5 seconds.
        self.notifChecker = Clock.schedule_interval(notifsConsumer, 5)

    #Plays ringtone no. given from file in 'ringtones'.
    #Needs to be method of app class so it can be called from '.kv' file.
    def playRingtone(self, ringtoneNo):
        if ringtoneNo not in range(1,10):
            return

        else:
            #kivy's audio module has issues on debian systems (inc. mine), so we use pygame.
            pygame.mixer.init()
            filepath = os.path.abspath(__file__)
            filedir = os.path.dirname(filepath)
            musicpath = os.path.join(filedir, "ringtones/%d.wav" % ringtoneNo)
            pygame.mixer.music.load(os.path.abspath(musicpath))
            pygame.mixer.music.play()
    
    #When user clicks a network row, display table showing its hosts.
    def networkTable(self, network, columnWidth):
        keysToShow = ['macAddr', 'ipAddr', 'manufacturer', 'notificationEnabled', 'onNetwork']

        hostsRowData = [
            list({
                    key:value 
                    for (key, value) in host.items()
                    if key in keysToShow
                }.values())
            for host in self.hosts.values()
        ]

        self.hostsTable = MDDataTable(
            column_data =  [
                ('MAC Address', columnWidth),
                ('IP Address', columnWidth),
                ('Manufacturer', columnWidth),
                ('Notifications Enabled', columnWidth),
                ('On Network', columnWidth)
            ],
            row_data = hostsRowData,
            size_hint = (0.7, 0.7)
        )

        self.hostsTable.bind(on_row_press = self.onHostPress)
        self.hostsTable.open()
    
    #If user clicks row corresponding for host in self.hostsTable, display dialog.
    #Dialog allows user to enable notifications / set notif tone for relevant host.
    def onHostPress(self, instanceTable, instanceRow):
        rowIndex = floor(instanceRow.index / 5)
        hostData = instanceTable.row_data[rowIndex]
        content = notificationSettings(enabled = hostData[3])
        hostId = list(self.hosts.values())[rowIndex]['id']

        self.hostDialog = MDDialog(
            title = 'Notifications for %s' % hostData[0],
            content_cls = content,
            type = 'custom',
            buttons = [
                ToggleButtonClass(
                    text = 'Cancel',
                    group = 'submit',
                    on_release = (lambda _: self.hostDialog.dismiss(force = 1))
                ),
                ToggleButtonClass(
                    text = 'OK',
                    group = 'submit',
                    on_release = (lambda _: self.hostDialogSubmit(hostId, rowIndex))
                )
            ]
        )
        
        #Nth value of checkbox bools indicate if checkbox n is selected.
        checkboxBools = [0] * 9
        
        if hostData[3]:
            checkboxBools[int(self.hosts[hostId]['tone']) - 1] = 1
        
        musicItems = [
            itemConfirmMusic(
                text = ('Ringtone %d' % num),
                active = (checkboxBools[num - 1]),
                index = num
            )
            for num in range(1,10)
        ]
        
        for item in musicItems:
            self.hostDialog.content_cls.ids['notifList'].add_widget(item)

        self.hostDialog.open()

    #When user submits host dialog, input info into db and update self.hosts.
    def hostDialogSubmit(self, hostId, hostIndex):
        #Get binary value of switch.
        notificationsEnabled = int(
            self.hostDialog.content_cls.ids['notificationsEnabled'].active)

        self.hosts[hostId]['notificationEnabled']  = notificationsEnabled

        if notificationsEnabled:
            selectedItem = None
            widgetList = list(enumerate(
                self.hostDialog.content_cls.ids['notifList'].children
            ))

            for index, widget in reversed(widgetList):
                if widget.ids['check'].active:
                    selectedIndex = widget.index

                    #update db;
                    self.cursor.execute(
                        'UPDATE hosts SET notificationEnabled = 1, tone = ? WHERE id = ?', 
                        [selectedIndex, hostId])
                    self.conn.commit()

                    self.hosts[hostId]['tone'] = selectedIndex
                    
                    #Close host's table and host dialog.
                    #MDDataTable can't be updated, so we need to close.
                    self.hostDialog.dismiss(force = 1)
                    self.hostsTable.dismiss(force = 1)
                    
                    return

            #Tell user to select a tone value, since none were selected.
            Snackbar(
                text = "Please select an option",
                padding = "20dp"
            ).open()

        else:
            self.hostsTable.table_data.row_data[hostIndex][3] = '1'
            self.cursor.execute('UPDATE hosts SET notificationEnabled = 0 WHERE id = ?',
                [hostId])
            self.conn.commit()
            self.hostDialog.dismiss(force = 1)
            
    def selectNotifType(self):
        self.hostDialog.content_cls.ids['options'].opacity = 1
        self.hostDialog.update_height()   
        
def main():
    if os.getuid() != 0:
        print('Must run with sudo')
        exit(1)
        
    app = sonarApp()
    app.run()
    app.notifsProducerP.terminate()
    app.notifChecker.cancel()
    exit(0)
    
main()
