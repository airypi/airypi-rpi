import requests, pickle, os, getpass, json, sys
from requests.adapters import HTTPAdapter
from cookielib import domain_match, user_domain_match
import client
from socketio_client import SocketIO
import time
from urlparse import urlparse



domain_name = 'www.airypi.com'
#domain_name = '192.168.2.105'

server_url = 'https://' + domain_name

    
def get_cookie(session):
    for cookie in session.cookies:
        return cookie

def require_input(message):
    while True:
        input = raw_input(message)
        if len(input) == 0:
            print "This field cannot be left blank"
        elif len(input) > 40:
            print "Input is too long!"
        else:
            return input
        
def require_password(message):
    while True:
        input = getpass.getpass(message)
        if len(input) == 0:
            print "Please enter a password"
        elif len(input) > 40:
            print "Password is too long!"
        else:
            return input

def require_yn(message):
    while True:
        input = raw_input(message)
        if input[0] == 'y':
            return True
        elif input[0] == 'n':
            return False
        else:
            print "Please enter (y/n)"
        
class Authenticator:
    def touchopen(self, filename, *args, **kwargs):
        fd = os.open(filename, os.O_RDWR | os.O_CREAT)
        return os.fdopen(fd, *args, **kwargs)
    
    def login(self):        
        home = os.path.expanduser("~")
        file_name = os.path.join(home, '.airypi_session')

        try:
            with open(file_name) as cookie_file:
                data = pickle.load(cookie_file)
                self.s = data['session']
                self.device = data['device']
                self.server_auth_token = csrf_token = data['auth_token']
        except Exception:
            should_register = require_yn("Would you like to register for an account? (y/n): ")
            auth_token = None
            self.s = requests.Session()

            if should_register:
                print "Register"
                print "Your email will only be used for account related purposes"

                while True:
                    email = require_input('Email: ')

                    result = requests.post(server_url + '/register_check/email', 
                        headers = {'Content-type': 'application/json'},
                        data=json.dumps({'email': email})).json()
                    if 'avaliable' not in result['objects']:
                        print "Email has been taken"
                        continue

                    password = require_password('Password (input is hidden):')
                    response = self.s.post(server_url + '/register', 
                        headers = {'Content-type': 'application/json'},
                        data=json.dumps({'email': email, 'password': password}))
                    auth_token = response.json()['objects']['auth_token']
                    print "A verification email has been sent. You do not need to confirm this email to connect to apps."
                    break
            else:
                print "Login"

                while True:
                    email = require_input('Email: ')
                    password = require_password('Password (input is hidden): ')
                
                    login_response = self.s.post(server_url + '/login', 
                                                data = json.dumps({'email': email, 
                                                                   'password': password}), 
                                                headers = {'Content-type': 
                                                           'application/json'}).json()
                    if "error" not in login_response['objects']:
                        auth_token = login_response['objects']['auth_token']
                        break                    
                    print "Error while logging in: " + login_response['objects']['error']
            self.server_auth_token = auth_token

            devices = self.s.get(server_url + '/devices').json()
            device_names = [device['name'] for device in devices['objects']]
            device_name = None
            
            while True:
                device_name = require_input('Give this Raspberry Pi a name: ')
                if device_name not in device_names:
                    break

                print "Device already exists with name " + device_name
            device_type = 'RASPBERRY_PI'
            device_response = self.server_post(server_url + '/devices/', 
                                          headers = {'Content-type': 'application/json'},
                                          data=json.dumps({
                                            'device_name': device_name, 
                                            'device_type': device_type
                                          }))
            self.device = device_response.json()['objects']
            
            with open(file_name, 'w') as cookie_file:
                pickle.dump({'session':self.s, 
                             'device': self.device,
                             'auth_token': self.server_auth_token}, cookie_file)
        session_cookie = get_cookie(self.s)
        self.server_session_id = session_cookie.value
        self.server_domain = session_cookie.domain
    
    def connect_to_app(self, app_name, url = None):
        self.login()

        if url is None:
            self.app_name = app_name
            
            url_response = self.s.get(server_url + '/app-url?app-name=' + app_name)
            url = url_response.json()['objects']['url']
            self.app_url = url
        else:
            self.app_url = url
        
        auth_info = self.s.get(url + '/login').json()

        response = self.server_post(server_url + '/oauth/authorize', data=auth_info['objects'])
        response = response.json()

        self.app_auth_token = response['objects']['auth_token']
        
        self.app_post(url + '/register-device-id', 
                    data = {'device_id': self.device['id']})
        
        #hack since i actually dont know how to just get a cookie
        cookie = None
        for session_cookie in self.s.cookies:
            if session_cookie.domain != self.server_domain:
                cookie = session_cookie

        o = urlparse(self.app_url)
        socketIO = SocketIO(o.hostname, o.port, 
                            params={'t': long(time.time() * 1000)}, 
                            cookies={"session": str(cookie.value)})
        app_namespace = socketIO.define(client.AppNamespace, '/client')
        app_namespace.login = self
        return socketIO, app_namespace
    
    def connect_to_server(self):
        socketIO = SocketIO(server_url, 
                            params={'t': long(time.time() * 1000)}, 
                            cookies={"session": str(self.server_session_id)})
        server_namespace = socketIO.define(client.ServerNamespace, '/client')
        #really wish i could do this in the constructor
        server_namespace.login = self
            
        return socketIO, server_namespace

    def server_post(self, *args, **kwargs):
        headers = kwargs.get('headers', {})
        headers['Authorization'] = self.server_auth_token
        kwargs['headers'] = headers
        return self.s.post(*args, **kwargs)

    def app_post(self, *args, **kwargs):
        headers = kwargs.get('headers', {})
        headers['Authorization'] = self.app_auth_token
        kwargs['headers'] = headers
        return self.s.post(*args, **kwargs)