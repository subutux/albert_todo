# -*- coding: utf-8 -*-

"""
Get a list of TODOs / Tasks from an caldav server.

Tested with the radicale server.

Triggers:
    `t <query>`: lists the current todo's and filter with query
        * mark done
        * postpone for one hour
        * postpone 'till tomorrow
        * postpone 'till next week
        * reload the cache
    `ta <query>`: Add a todo
        * No due date
        * Due 'till one hour
        * Due 'till tomorrow
        * Due 'till next week

"""
from typing import Dict, AnyStr, List

from albert import (
    Item,
    ItemBase,

    iconLookup,

    info,

    configLocation,

    ProcAction, ClipAction, FuncAction
)
import os
import configparser
import subprocess

import caldav
import vobject

import datetime

unresolved_todo = iconLookup("appointment-new")
resolved_todo = iconLookup("answer-correct")

__title__ = "TODOs"
__version__ = "0.4.0"
__triggers__ = ["t ", "ta "]
__authors__ = "Stijn Van Campenhout <subutux@gmail.com>"
__py_deps = ["vobject", "caldav"]
__exec_deps__ = ["xdg-open"]

helpText = """
# Please edit this file with your calendars you want to manage the todos for.
# With each calendar in a section.
#
# For example:
# [Work]
# url = http://my.calendar/work
# username = username
# password = pa$$word # No quotes around the values!
"""

config = configparser.ConfigParser()
configurationFileName = "calendars.ini"
configuration_directory = os.path.join(configLocation(), __title__)
calendar_configuration_file = os.path.join(configuration_directory,
                                           configurationFileName)


class CaldavClients(object):
    """docstring for CaldavClients"""
    Connections: Dict[AnyStr, caldav.Principal]

    def __init__(self):
        super(CaldavClients, self).__init__()
        self.config = configparser.ConfigParser()
        self.Connections = {}
        self.todos = []
        self.refreshed_on = datetime.datetime.now()

    def set_connections(self, conf: configparser.ConfigParser):
        self.config = conf
        self.Connections = {}
        for section in conf.sections():
            info(f"loading {section}")
            self.Connections[section] = caldav.DAVClient(
                url=conf[section]['url'],
                username=conf[section]['username'],
                password=conf[section]['password']).principal()

    def load_todos(self):
        self.todos = []
        for con in self.Connections.keys():
            calendars = self.Connections[con].calendars()
            for calendar in range(len(calendars)):
                cal = calendars[calendar]
                if cal.canonical_url == self.config[con]['url']:
                    for todo in cal.todos():
                        self.todos.append({
                            "source": [con, calendar],
                            "todo": todo.vobject_instance
                        })

    def refresh(self):
        now = datetime.datetime.now()
        if (now - self.refreshed_on) > datetime.timedelta(minutes=5):
            self.load_todos()
            self.refreshed_on = now

    def query(self, query):
        todos = []
        for todo in self.todos:
            if query.lower() in todo["todo"].vtodo.summary.valueRepr().lower():
                todos.append(todo)

        def sortByDue(todo):
            obj = todo["todo"]
            if "due" in obj.vtodo.contents.keys():
                dueDate: datetime = obj.vtodo.due.valueRepr()
                if not isinstance(dueDate, datetime.datetime):
                    dueDate = datetime.datetime.combine(
                        dueDate, datetime.datetime.min.time())
                if dueDate.tzinfo is None:
                    dueDate = dueDate.astimezone()
            else:
                dueDate = None
            info(dueDate)
            return dueDate
        # todos.sort(key=lambda todo: sortByDue(todo))
        # info([x["todo"].vtodo.due.valueRepr() for x in todos])
        return todos

    def createTodo(self, name, summary, due=None):
        todo = vobject.iCalendar()
        todo.add('vtodo')
        todo.vtodo.add('summary').value = summary
        if due:
            todo.vtodo.add('due').value = due
        for cal in self.Connections[name].calendars():
            if cal.canonical_url == self.config[name]["url"]:
                cal.add_todo(todo.serialize())
                info("added todo")
                self.todos.append(todo)
                # self.load_todos()

    def findTodo(self, name, uid):
        calendars: List[caldav.Calendar] = self.Connections[name].calendars()
        for cal in calendars:
            if cal.canonical_url == self.config[name]["url"]:
                todos = [t for t in cal.todos()
                         if t.vobject_instance.vtodo.uid.valueRepr() == uid]
                if len(todos) == 0:
                    # Cannot find todo
                    return None

                return todos[0]

    def markDone(self, name, uid):
        todo = self.findTodo(name, uid)
        if todo:
            todo.complete()
            self.load_todos()

    def postpone(self, name, uid, due):
        todo = self.findTodo(name, uid)
        if todo:
            info(todo.vobject_instance.vtodo.summary.valueRepr())
            info(todo.vobject_instance.vtodo.uid.valueRepr())
            info(todo.vobject_instance.vtodo.contents.keys())
            if "due" in todo.vobject_instance.vtodo.contents.keys():
                todo.vobject_instance.vtodo.due.value = due
            else:
                todo.vobject_instance.vtodo.add('due').value = due
            todo.save()
            self.load_todos()


connections = CaldavClients()


def initialize():
    if os.path.exists(calendar_configuration_file):
        config.read(calendar_configuration_file)
        connections.set_connections(config)
        connections.load_todos()
    else:
        try:
            os.makedirs(configuration_directory, exist_ok=True)
            try:
                with open(calendar_configuration_file, "w") as output_file:
                    output_file.write(helpText)
                subprocess.call(['xdg-open', calendar_configuration_file])
            except OSError:
                print("There was an error opening the file: %s" %
                      calendar_configuration_file)
        except OSError:
            print("There was an error making the directory: %s" %
                  configuration_directory)


# Can be omitted
def finalize():
    pass


def buildItem(todo):
    obj = todo["todo"]
    uid = obj.vtodo.uid.valueRepr()
    text = "{}: {}".format(todo["source"][0], obj.vtodo.summary.valueRepr())
    iconPath = unresolved_todo
    subtext = "no due date"
    urgency = ItemBase.Urgency.Alert
    onehour = datetime.datetime.now() + datetime.timedelta(hours=1)

    tonight = datetime.datetime.now()
    tonight = tonight.replace(hour=16, minute=0, second=0)

    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    tomorrow.replace(hour=9, minute=0, second=0)  # always 9 AM

    nextweek = datetime.datetime.now() + datetime.timedelta(days=7)
    nextweek.replace(hour=9, minute=0, second=0)  # always 9 AM

    if "due" in obj.vtodo.contents.keys():
        dueDate: datetime = obj.vtodo.due.valueRepr()
        if not isinstance(dueDate, datetime.datetime):
            dueDate = datetime.datetime.combine(
                dueDate, datetime.datetime.min.time())
            # dueDate = dueDate.replace(
            #     hour=9, minute=0, second=0)  # always 9 am
        if dueDate.tzinfo is None:
            dueDate = dueDate.astimezone()
        info(dueDate)
        now = datetime.datetime.now().astimezone()
        info(now)
        if dueDate < now:
            subtext = "❌ due: {:%Y-%m-%d %H:%M}".format(dueDate)
            urgency = ItemBase.Urgency.Normal
        elif (dueDate - now) < datetime.timedelta(hours=12):
            subtext = "⚠️ due: {:%Y-%m-%d %H:%M}".format(dueDate)
            urgency = ItemBase.Urgency.Notification
        else:
            subtext = "🕑 due: {:%Y-%m-%d %H:%M}".format(dueDate)

    return Item(
        id=f'{dueDate.timestamp()}',
        text=text,
        subtext=subtext,
        icon=iconPath,
        completion=f't {obj.vtodo.summary.valueRepr()}',
        urgency=urgency,
        actions=[FuncAction(text="Mark done",
                            callable=lambda: connections.markDone(
                                todo["source"][0], uid)),

                 FuncAction(text="Postpone for one hour",
                            callable=lambda: connections.postpone(
                                todo["source"][0], uid, onehour)),

                 FuncAction(text="Postpone ' till 4 P.M.'",
                            callable=lambda: connections.postpone(
                                todo["source"][0], uid, tonight)),

                 FuncAction(text="Postpone 'till tomorrow",
                            callable=lambda: connections.postpone(
                                todo["source"][0], uid, tomorrow)),
                 FuncAction(text="Postpone 'till next week",
                            callable=lambda: connections.postpone(
                                todo["source"][0], uid, nextweek)),
                 FuncAction(text="Reload todo's",
                            callable=lambda: connections.load_todos()),
                 ]
    )


def handleQuery(query):
    if not query.isTriggered:
        return
    query.disableSort()
    if query.trigger == "t ":
        return handleList(query)
    if query.trigger == "ta ":
        return handleAdd(query)


def handleAdd(query):
    actions = []
    onehour = datetime.datetime.now() + datetime.timedelta(hours=1)
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    tomorrow.replace(hour=9, minute=0, second=0)  # always 9 AM
    nextweek = datetime.datetime.now() + datetime.timedelta(days=7)
    nextweek.replace(hour=9, minute=0, second=0)  # always 9 AM
    for name in connections.config.sections():
        actions.append(
            FuncAction(text=f"Create todo in {name}",
                       callable=lambda: connections.createTodo(
                           name, query.string))
        )
        actions.append(
            FuncAction(text=f"Create todo in {name} for in one hour",
                       callable=lambda: connections.createTodo(
                           name, query.string, onehour))
        )
        actions.append(
            FuncAction(text=f"Create todo in {name} for tomorrow",
                       callable=lambda: connections.createTodo(
                           name, query.string, tomorrow))
        )
        actions.append(
            FuncAction(text=f"Create todo in {name} for next week",
                       callable=lambda: connections.createTodo(
                           name, query.string, nextweek))
        )

    return Item(
        id=f"newtodo-{query.string}",
        text=query.string,
        subtext="Create a new todo",
        icon=iconLookup("add"),
        actions=actions
    )


def handleList(query):
    if len(config.sections()) == 0:
        # Try to reload the config.
        config.read(calendar_configuration_file)
        if len(config.sections()) == 0:
            info("No sections defined in config.")
            return Item(id="config",
                        icon=unresolved_todo,
                        text="Configuration not complete",
                        subtext="No sections in the Configuration file",
                        actions=[
                            ProcAction(
                                text="Edit configuration in default editor",
                                commandline=['xdg-open',
                                             calendar_configuration_file],
                                cwd="~"),
                            ClipAction(
                                text="Copy the path of the configuration file",
                                clipboardText=calendar_configuration_file)
                        ])
        else:
            connections.set_connections(config)
            connections.load_todos()
    items = []
    connections.refresh()
    for todo in connections.query(query.string):
        info(todo["todo"].vtodo.summary.valueRepr())
        info(todo["todo"].vtodo.due.valueRepr())
        items.append(buildItem(todo))

    return items
