import time

station = None

def connect(ssid, password):
    import network
    global station
    print("Wifi connect")
    station = network.WLAN(network.STA_IF)

    if station.isconnected():
        print("Already connected with IP {}".format(station.ifconfig()))
        return True

    station.active(True)
    station.connect(ssid, password)
    count = 0
    while not station.isconnected():
        count += 1
        time.sleep(1)
        if count > 30:
            print("unable to connect to wifi after {} tries".format(count))
            return False

    print("Wifi connection successful with IP {}".format(station.ifconfig()))
    return True

