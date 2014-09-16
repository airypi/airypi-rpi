import gevent.monkey
gevent.monkey.patch_all()
import gevent

import os

import execute

import json, sys
#import smbus, spidev, RPi.GPIO, serial
import time, Queue

import auth
from socketio_client import SocketIO, BaseNamespace
import RPi.GPIO as GPIO
import traceback

def perform_action_queue(ws):
    queue = Queue.Queue()
    
    #first queue up actions
    while True:
        m = json.loads(ws.recieve(), 'utf-8')
        ws.send(json.dumps({'result': None}))
        
        if m.func != 'execute':
            queue.put(m)
        else:
            break
    
    #then empty queue
    while not queue.empty():
        m = queue.get()
        
        if m.cls:
            call_class_related_method(m)
        elif m.type == "queue":
            if m.func == 'sleep':
                gevent.sleep(m.params)

class AppNamespace(BaseNamespace):
    def on_connect(self):
        self.emit('run', {})
        self.server_namespace.emit('to_user', {'type': 'app_connect', 'data': {}})
    
        if hasattr(self.login, 'app_name'):
            print "Connected to: " + self.login.app_name
        else:
            print "Connected to: " + self.login.app_url

    def on_io(self, *args):
        try:
            func = args[0]
            if func['module'] not in execute.permitted_modules():
                return
            
            executor = execute.permitted_modules()[func['module']]
            retval = executor(self.login, func)
            self.login.app_post(self.login.app_url + '/run/retval', data=json.dumps({'result': retval}))
        except Exception, e:
            error = traceback.format_exc()
            self.login.app_post(self.login.app_url + '/run/retval', data=json.dumps({'error': error}))

    def on_multi(self, *args):
        pass
        
    def on_execute(self, *args):
        perform_action_queue(self)
            
    def on_ui(self, *args):
        self.server_namespace.emit('to_user', {'type': 'ui', 'data': args[0]})
        self.login.app_post(self.login.app_url + '/run/retval', data=json.dumps({'result': "None"}))
    
    def on_ui_load(self, *args): 
        self.server_namespace.emit('to_user', 
                                   {'type': 'ui_load', 
                                    'data': args[0],
                                    'app_name': self.login.app_name})

    def on_disconnect(self):
        execute.cleanup()

    def emit(self, *args, **kwargs):
        if self._transport.connected:
            BaseNamespace.emit(self, *args, **kwargs)

class ServerNamespace(BaseNamespace):
    def on_user_message(self, *args):
        message = args[0]
        
        if message['type'] != 'switch':
            if self.login.app_url is not None:
                self.login.app_post(self.login.app_url + '/run/event', data = json.dumps(message))
            else:
                self.emit('to_user', json.dumps({'type': 'ui_load'}))
        elif message['type'] == 'switch' and self.app_namespace is not None:
            self.app_namespace.disconnect()
            self.app_greenlet.kill(block=True)

            execute.cleanup()
            #self.app_greenlet.join()
            
            app_client, self.app_namespace = self.login.connect_to_app(message['app_name'])
            self.app_namespace.server_namespace = self
            self.app_greenlet = gevent.spawn(wait_forever_app, app_client)

def wait_forever_server(client):
    while True:
        try:
            client.wait()
            gevent.sleep(0)
        except Exception, e:
            print traceback.format_exc()

            print e
            continue
        break

def wait_forever_app(client):
    while True:
        try:
            client.wait()
            gevent.sleep(0)
        except Exception, e:
            print traceback.format_exc()
            print e

            execute.cleanup()
            continue
        break

def get_app_name(login, cmd_app_name = None, url = None):
    if url is not None:
        return None

    if cmd_app_name is not None:
        app_info_response = login.s.get(auth.server_url + '/app/' + cmd_app_name).json()
        if 'app_name' in app_info_response['objects']:
            return cmd_app_name

    while True:
        app_name = auth.require_input('App name: ')    
        app_info_response = login.s.get(auth.server_url + '/app/' + app_name).json()
        
        if 'app_name' in app_info_response['objects']:
            return app_name
        print "Please enter a valid app name"

def run(cmd_app_name = None, url = None):
    _ROOT = os.path.abspath(os.path.dirname(__file__))
    cert_path = os.path.join(_ROOT, 'websocket', 'cacert.pem')
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path

    app_greenlet = None
    server_greenlet = None
    try:
        login = auth.Authenticator()
        login.login()

        app_name = get_app_name(login, cmd_app_name = cmd_app_name, url = url)

        while True:
            try:
                server_client, server_namespace = login.connect_to_server()    
                app_client, app_namespace = login.connect_to_app(app_name, url=url) 
            except Exception, e:
                print traceback.format_exc()
                print e
                continue
            break

        server_namespace.app_namespace = app_namespace
        app_namespace.server_namespace = server_namespace
        
        app_greenlet = gevent.spawn(wait_forever_app, app_client)
        
        server_namespace.app_greenlet = app_greenlet

        server_greenlet = gevent.spawn(wait_forever_server, server_client)
   
        while True:
            gevent.sleep(0.1)
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        print traceback.format_exc()
        print e
        if app_greenlet is not None:
            app_greenlet.kill(block = True)
        if server_greenlet is not None:
            server_greenlet.kill(block = True)

        print "cleaning up"
        GPIO.cleanup()
    