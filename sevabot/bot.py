# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import imp
import sys
import logging

import Skype4Py

from sevabot import modules

logger = logging.getLogger("sevabot")


class Sevabot:
    """
    Skype bot interface handler.
    """

    def __init__(self):
        self.cmds = {}
        self.cron = []
        self.chats = {}

    def start(self):

        if sys.platform == "Linux":
            self.skype = Skype4Py.Skype(Transport='x11')
        else:
            # OSX
            self.skype = Skype4Py.Skype()

        self.skype.Attach()
        self.skype.OnMessageStatus = self.handleMessages
        self.getChats()

    def getChats(self):
        """
        Scan all chats on initial connect.
        """
        chats = {}
        for chat in self.skype.Chats:
            chats[chat.FriendlyName] = chat
        self.chats = chats

    def handleMessages(self, msg, status):
        """
        Handle incoming messages
        """
        if status == "RECEIVED" or status == "SENT":
            logger.debug("%s - %s - %s: %s" % (status, msg.Chat.FriendlyName, msg.FromHandle, msg.Body))

        if status == "RECEIVED" and msg.Body:

            words = msg.Body.split()

            if len(words) < 0:
                return

            keyword = words[0]

            logger.debug("Trying to identify keyword: %s" % keyword)

            if modules.is_module(keyword):
                # Execute module asynchronously

                def callback(output):
                    msg.Chat.SendMessage(func(
                            *args[1:],
                            msg=output,
                            skype=self.skype,
                            bot=self
                        ))

                modules.run_module(keyword, words[1:], callback)
                return

            if msg.Body == "!loadModules":
                msg.Chat.SendMessage("Loading modules...")
                try:
                    self.loadModules()
                except Exception as e:
                    msg.Chat.SendMessage(str(e))
                    return
                return

            elif msg.Body == "!loadChats":
                self.getChats()
                return

            if msg.Body[0] == "!":
                args = msg.Body.split(" ")
                try:
                    func = self.cmds[args[0]]
                    msg.Chat.SendMessage(func(
                            *args[1:],
                            msg=msg,
                            skype=self.skype,
                            bot=self
                        ))
                except Exception as e:
                    msg.Chat.SendMessage(str(e))

    def runCmd(self, cmd):
        args = cmd.split(" ")
        return self.cmds["!" + args[0]](*args[1:], bot=self, skype=self.skype)

    def sendMsg(self, chat, msg):
        self.chats[chat].SendMessage(msg)

    def runCron(self, interval):
        """
        Run cron jobs defined by modules.
        This function is called from the main script.
        Interval is the same as the main loops time.sleep's interval.
        """

        for job in self.cron:
            if 'timer' not in job:
                job['timer'] = job['interval']

            # get the chat objects for the cron job
            chats = []
            if type(job['chats'][0]) == str:
                for chat in job['chats']:
                    try:
                        chat = self.chats[chat]
                        chats.append(chat)
                    except KeyError:
                        pass
                job['chats'] = chats

            job['timer'] -= interval

            if job['timer'] <= 0:
                try:
                    job['cmd'](chats=job['chats'])
                except Exception as e:
                    print("Error " + str(e))
                job['timer'] = job['interval']