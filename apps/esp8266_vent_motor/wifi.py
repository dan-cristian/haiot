def connect(ssid, password):
    import network

    station = network.WLAN(network.STA_IF)

    if station.isconnected():
        print("Already connected with IP {}".format(station.ifconfig()))
        return

    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        pass

    print("Wifi connection successful with IP {}".format(station.ifconfig()))

