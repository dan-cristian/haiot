def connect(ssid, password):
    import network

    station = network.WLAN(network.STA_IF)

    if station.isconnected():
        print("Already connected")
        return

    station.active(True)
    station.connect(ssid, password)

    while not station.isconnected():
        pass

    print("Wifi connection successful")
    print(station.ifconfig())
