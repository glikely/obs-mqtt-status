OBS support for Tasmota Tally Ligths over MQTT
==============================================

This script uses MQTT to set Tally light colours for sources.

The script configuration dialog allows you to add a list of sources that
should send Tally light updates.
Any source that has the same name as one in the list will generate topic
updates to set the light colour when the source becomes visible in either the
`Program` or `Preview` outputs, or goes invisible.
Topic updates are sent to the `cmnd/<source-name>/color` topic.

- A source visible in `Program` will be set to `FF0000` (red)
- A source visible in `Preview` will be set to `00FF00` (green)
- A source not visible will be set to `000000` (off)

Tally Light Setup
-----------------

Update topics are compatible with the default Tasmota MQTT topics.
Any RGB Tasmota device can easily be used as a tally light.
Configure the Tasmota device to connect to the MQTT broker, and in the MQTT
configuration page set the `Topic = ` field to the name of the source.
If the Tasmota topic and the script configuration match then you should
immediately see the Tasmota colour match the source visibility.

Note: MQTT topics should only contain ASCII alphanumeric characters.
Do not use spaces and avoid special characters.
Your source name must exactly match the topic used by the Tasmota device.

Installation
------------

This script depends on a recent OBS (Tested with v26.0.2), Python,
and `paho.mqtt.client` Python library.
To install, clone this repo and then add the script to OBS using the Tools->Scripts menu.

You will need an MQTT broker. Any broker will do, but the simplest is to install a
broker on the same machine that is running OBS.
This script has been tested with [Eclipse Mosquitto](https://mosquitto.org/download).

### Windows

Windows users will need to follow the OBS instructions for installing Python.
At the time of writing, OBS only works with Python 3.6.
paho.mqtt.client can be installed from an Administrator CMD prompt using `pip3`

```
pip3 install mqtt-wrapper
```

To install the Mosquitto MQTT broker, use the installer package on the
Mosquitto web site.
You will also need to add a firewall rule to allow inbound and outbound
connections on TCP port 1883.

### Linux & MacOS

Linux and MacOS users will already have python installed. `paho.mqtt.client` can be installed using `pip3`

```
pip3 install mqtt-wrapper
```
