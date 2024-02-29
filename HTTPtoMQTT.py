from paho.mqtt import client as mqtt_Client
from http.server import BaseHTTPRequestHandler, HTTPServer
import time, logging, json
import configparser

def read_config(filename='config.conf'):
    config = configparser.ConfigParser()
    config.read(filename)

    # Get credentials from the 'credentials' section
    username = config.get('credentials', 'username')
    password = config.get('credentials', 'password')
    # Get connection info from the 'connection' section
    broker = config.get('connection', 'broker')
    port = config.get('connection', 'port')
    client_id = config.get('connection', 'client_id')
    
    return username, password, broker, port, client_id

username, password, broker, port, client_id = read_credentials()
    

print("Sleeping for 60s")
time.sleep(60)
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected with result code "+str(rc))
        global Connected
        Connected = True
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("$SYS/#")
    else:
        print("Connection failed")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    pass

client = mqtt_Client.Client(client_id)
client.username_pw_set(username, password=password)
client.on_connect = on_connect
client.on_message = on_message

Connected = False
client.connect(broker, port=port)
client.loop_start()
while Connected != True: # wait for connection
    time.sleep(0.1)

ident = "brewpi"
name = "BrewPi"
model = "3B+"
manufact = "DIY"

t = "BrewPi/"
base_t = t + "fermentrack/"
av_t = "BrewPi/status"

channels = [
    {"name": "Beer Temperature",
    "device_class": "temperature",
    "unit": "°C",
    "ic": "glass-mug-variant",
    "expire": 120},
    {"name": "Setpoint Beer",
    "device_class": "temperature",
    "unit": "°C",
    "ic": "glass-mug-variant",
    "expire": 0},
    {"name": "Fridge Temperature",
    "device_class": "temperature",
    "unit": "°C",
    "ic": "fridge-industrial-outline",
    "expire": 120},
    {"name": "Setpoint Fridge",
    "device_class": "temperature",
    "unit": "°C",
    "ic": "fridge-industrial-outline",
    "expire": 0},
    {"name": "Room Temperature",
    "device_class": "temperature",
    "unit": "°C",
    "ic": "home-thermometer-outline",
    "expire": 120},
    {"name": "Specific Gravity",
    "device_class": "temperature",
    "unit": "-",
    "ic": "water-percent",
    "expire": 0},
    {"name": "Control Mode",
    "device_class": False,
    "unit": False,
    "ic": "state-machine",
    "expire": 0}
]

for elem in channels:
    id = elem['name'].lower().replace(' ', '_')
    payload_unit = ""
    payload_devclass = ""
    payload_base = "{\"name\": \"" + elem['name'] + "\", \"uniq_id\": \"" + id + "\", \"stat_t\": \"" + base_t + id + "\", \"avty_t\": \"" + av_t + "\","
    if elem['device_class']:
        payload_devclass= "\"dev_cla\": \"" + elem['device_class'] + "\","
    if elem['unit']:
        payload_unit = "\"unit_of_meas\": \"" + elem['unit'] + "\","
    payload_suffix = "\"ic\": \"" + "mdi:" + elem['ic'] + "\", \"expire_after\": " + str(elem['expire']) + ", \"dev\":  { \"identifiers\": [\"" + ident + "\"], \"name\": \"" + name + "\",  \"model\": \"" + model + "\", \"manufacturer\": \"" + manufact + "\"}}"
    payload = payload_base + payload_devclass + payload_unit + payload_suffix
    topic = "homeassistant/sensor/"+ident+"/"+id+"/config"
    print("Topic: " + topic)
    print("Payload: " + payload)
    try:
        client.publish(topic, payload, retain=True)
    except:
        #print(topic)
        #print(payload)
        pass
client.publish(av_t, "online")

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_response()
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        data=(post_data.decode('utf-8'))
        print("received data:" + data)
        dataDict=json.loads(data)
        brewpi = dataDict['brewpi_devices'][0]
        tilt = dataDict['gravity_sensors'][0]
        brewpi_items=['beer_temp', 'beer_setting', 'fridge_temp', 'fridge_setting', 'room_temp']
        tilt_items=['gravity']

        control_mode_raw=str(brewpi['control_mode']);
        if(control_mode_raw=='p'):
            control_mode='Beer Profile';
        elif(control_mode_raw=='f'):
            control_mode='Fridge Constant';
        elif(control_mode_raw=='b'):
            control_mode='Beer Constant';
        elif(control_mode_raw=='o'):
            control_mode='Off';
        else:
            control_mode='Unknown';
        client.publish(av_t, "online")
        try:
            client.publish(base_t + "beer_temperature", str(brewpi['beer_temp']));
        except:
            print("Failed to publish beer temperature")
        try:
            client.publish(base_t + "setpoint_beer", str(brewpi['beer_setting']));
        except:
            print("Failed to publish beer setpoint")
        try:
            client.publish(base_t + "fridge_temperature", str(brewpi['fridge_temp']));
        except:
            print("Failed to publish fridge temperature")
        try:
            client.publish(base_t + "setpoint_fridge", str(brewpi['fridge_setting']));
        except:
            print("Failed to publish frdige setpoint")
        try:
            client.publish(base_t + "room_temperature", str(brewpi['room_temp']));
        except:
            print("Failed to publish room temperature")
        try:
            client.publish(base_t + "control_mode", control_mode);
            print("Published Control Mode: " + control_mode);
        except:
            print("Failed to publish control mode")
        try:
            client.publish(base_t + "specific_gravity", str(tilt['gravity']));
        except:
            print("Failed to publish specific gravity")

        self._set_response()
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()