import network
from umqtt.simple import MQTTClient
import time
import random
from machine import Pin
from dht import DHT22  

ssid = "Wokwi-GUEST"
password = ""

mqtt_server = "broker.hivemq.com"
topic_light = "home/light"
topic_fan = "home/fan"
topic_temp_request = "home/temperature/request"
topic_temp_response = "home/temperature/response"
topic_ac = "home/ac"

def generate_client_id():
    characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return "ESP32_Client_Wokwi_" + ''.join(random.choice(characters) for _ in range(8))

client_id = generate_client_id()
client = MQTTClient(client_id, mqtt_server)

led_light = Pin(18, Pin.OUT)
led_fan = Pin(19, Pin.OUT)
led_ac = Pin(22, Pin.OUT)  

temp_sensor = DHT22(Pin(21))  

def connect_wifi():
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)
    
    
    timeout = 20 
    start_time = time.time()
    
    while not station.isconnected():
        print("Attempting to connect to Wi-Fi...")
        time.sleep(1)
        
        
        if time.time() - start_time > timeout:
            print("Wi-Fi connection timeout. Retrying...")
            station.disconnect()
            time.sleep(2)
            station.connect(ssid, password)
            start_time = time.time()
    
    
    if station.isconnected():
        print("Connected to Wi-Fi. IP Address: ", station.ifconfig()[0])
        return True
    else:
        print("Failed to connect to Wi-Fi")
        return False

def connect_mqtt():
    print("Connecting to MQTT...")
    try:
        client.connect()
        print(f"Connected to MQTT broker with client ID: {client_id}")
    except Exception as e:
        print("MQTT Connection Failed: ", e)
        time.sleep(5)
        connect_mqtt()

def read_temperature():
    try:
        temp_sensor.measure()
        temperature = temp_sensor.temperature()
        return temperature
    except Exception as e:
        print(f"Failed to read temperature: {e}")
        return None

def mqtt_callback(topic, msg):
    decoded_msg = msg.decode()
    topic_decoded = topic.decode()
    print(f"Message received on topic '{topic_decoded}': {decoded_msg}")
    
    if topic_decoded == topic_light:
        if decoded_msg == "ON":
            print("Turning light ON")
            led_light.on()
        elif decoded_msg == "OFF":
            print("Turning light OFF")
            led_light.off()
    
    elif topic_decoded == topic_fan:
        if decoded_msg == "ON":
            print("Turning fan ON")
            led_fan.on()
        elif decoded_msg == "OFF":
            print("Turning fan OFF")
            led_fan.off()

    elif topic_decoded == topic_temp_request:
        
        temperature = read_temperature()
        if temperature is not None:
            response_message = f"Temperature: {temperature}°C"
            print(f"Publishing temperature: {response_message}")
            client.publish(topic_temp_response, response_message)

    elif topic_decoded == topic_ac:
        if decoded_msg in ["ON", "AUTO"]:
            
            temperature = read_temperature()
            if temperature is not None:
                if temperature > 25:
                    if decoded_msg == "ON":
                        print("Turning AC ON (user requested and temperature < 25°C)")
                    elif decoded_msg == "AUTO":
                        print("Auto mode: Temperature below threshold, turning AC ON")
                    led_ac.on()
                else:
                    print(f"Temperature is {temperature}°C, denying AC ON request")
                    led_ac.off()  
        elif decoded_msg == "OFF":
            print("Turning AC OFF")
            led_ac.off()
        else:
            print(f"Unrecognized AC command: {decoded_msg}")

    else:
        print(f"Unrecognized topic: {topic_decoded}")

def main():
    
    wifi_connected = False
    while not wifi_connected:
        wifi_connected = connect_wifi()
        if not wifi_connected:
            print("Retrying Wi-Fi connection in 5 seconds...")
            time.sleep(5)
    
    connect_mqtt()

    print("Subscribing to topics...")
    client.set_callback(mqtt_callback)
    client.subscribe(topic_light)
    client.subscribe(topic_fan)
    client.subscribe(topic_temp_request)
    client.subscribe(topic_ac)
    print("Subscribed to topics.")

    while True:
        try:
            client.check_msg()
            time.sleep(1)
        except OSError as e:
            print(f"OSError: {e}, attempting to reconnect...")
            time.sleep(5)
            connect_mqtt()
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

main()