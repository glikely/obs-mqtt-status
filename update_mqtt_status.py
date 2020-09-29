# Script to generate MQTT updates on OBS status
# SPDX-License-Identifier: AGPL-3.0

import json
import socket # Just so we can properly handle hostname exceptions
import obspython as obs
import paho.mqtt.client as mqtt
#import ssl # Results in PyExc_OSError so I guess we're stuck without it for now


# Meta
__version__ = '1.0.1'
__version_info__ = (1, 0, 1)
__license__ = "AGPLv3" # ...or proprietary if you want to negotiate
__license_info__ = {
    "AGPLv3": {
        "product": "update_mqtt_status",
        "users": 0, # 0 being unlimited
        "customer": "Unsupported",
        "version": __version__,
        "license_format": "1.0",
    }
}
__author__ = 'Riskable <riskable@youknowwhat.com>'

__doc__ = """\
Publishes real-time OBS status info to the given MQTT server/port/channel \
at the configured interval.
"""

# Default values for the configurable options:
INTERVAL = 5 # Update interval (in seconds)
MQTT_HOST = "localhost" # Hostname of your MQTT server
MQTT_PORT = 1883 # Default MQTT port is 1883
MQTT_CHANNEL = "obs/status"

# This is how we keep track of the current status:
STATUS = {
    "recording": False,
    "streaming": False,
    "paused": False,
    "replay_buffer": False, # If it's active or not
    "fps": 0,
    "frame_time_ns": 0,
    "frames": 0,
    "lagged_frames": 0,
}
PREV_STATUS = STATUS.copy()

# Using a global MQTT client variable to keep things simple:
CLIENT = mqtt.Client()


def on_mqtt_connect(client, userdata, flags, rc):
    """
    Called when the MQTT client is connected from the server.  Just prints a
    message indicating we connected successfully.
    """
    print("MQTT connection successful")

CLIENT.on_connect = on_mqtt_connect

def on_mqtt_disconnect(client, userdata, rc):
    """
    Called when the MQTT client gets disconnected.  Just logs a message about it
    (we'll auto-reconnect inside of update_status()).
    """
    print("MQTT disconnected.  Reason: {}".format(str(rc)))

CLIENT.on_disconnect = on_mqtt_disconnect

def update_status():
    """
    Updates the STATUS global with the current status (recording/streaming) and
    publishes it (JSON-encoded) to the configured
    MQTT_HOST/MQTT_PORT/MQTT_CHANNEL.  Meant to be called at the configured
    INTERVAL.
    """
    CLIENT.loop() # This is so is_connected() will accurately reflect the status
    global PREV_STATUS
    global STATUS
    STATUS["recording"] = obs.obs_frontend_recording_active()
    STATUS["streaming"] = obs.obs_frontend_streaming_active()
    STATUS["paused"] = obs.obs_frontend_recording_paused()
    STATUS["replay_buffer"] = obs.obs_frontend_replay_buffer_active()
    STATUS["fps"] = obs.obs_get_active_fps()
    STATUS["frame_time_ns"] = obs.obs_get_average_frame_time_ns()
    # Commented this out because it doesn't seem useful (real-time):
    #STATUS["frame_interval_ns"] = obs.obs_get_frame_interval_ns()
    STATUS["frames"] = obs.obs_get_total_frames()
    STATUS["lagged_frames"] = obs.obs_get_lagged_frames()
    #print("update_status() STATUS: %s" % STATUS) # Uncomment for debug
    if not CLIENT.is_connected():
        CLIENT.connect(MQTT_HOST, MQTT_PORT, 60)
    if PREV_STATUS["streaming"] and not STATUS["streaming"]:
        # Publish a one-time final message indicating streaming is stopped
        CLIENT.publish(MQTT_CHANNEL, json.dumps(STATUS))
    elif PREV_STATUS["recording"] and not STATUS["recording"]:
        # Publish a one-time final message indicating recording is stopped
        CLIENT.publish(MQTT_CHANNEL, json.dumps(STATUS))
    # Only start publishing regular messages if we're streaming or recording
    if STATUS["recording"] or STATUS["streaming"]:
        CLIENT.publish(MQTT_CHANNEL, json.dumps(STATUS))
    PREV_STATUS = STATUS.copy()

def script_description():
    return __doc__ # We wrote a nice docstring...  Might as well use it!

def script_load(settings):
    """
    Just prints a message indicating that the script was loaded successfully.
    """
    print("MQTT script loaded.")

def script_unload():
    """
    Publishes a final status message indicating we're no longer recording or
    streaming (so your MQTT-enabled whatever doesn't get stuck thinking you're
    recording/streaming forever) and calls `CLIENT.disconnect()` (even though
    that's probably not necessary).
    """
    final_status = {
        "recording": False,
        "streaming": False,
        "paused": False,
        "replay_buffer": False, # If it's active or not
        "fps": 0,
        "frame_time_ns": 0,
        "frames": 0,
        "lagged_frames": 0,
    }
    CLIENT.publish(MQTT_CHANNEL, json.dumps(final_status))
    CLIENT.disconnect()

def script_defaults(settings):
    """
    Sets up our default settings in the OBS Scripts interface.
    """
    obs.obs_data_set_default_string(settings, "mqtt_host", MQTT_HOST)
    obs.obs_data_set_default_string(settings, "mqtt_channel", MQTT_CHANNEL)
    obs.obs_data_set_default_int(settings, "mqtt_port", MQTT_PORT)
    obs.obs_data_set_default_int(settings, "interval", INTERVAL)

def script_properties():
    """
    Makes this script's settings configurable via OBS's Scripts GUI.
    """
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(
        props, "mqtt_host", "MQTT server hostname", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(
        props, "mqtt_channel", "MQTT channel",
        obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(
        props, "mqtt_port", "MQTT TCP/IP port", MQTT_PORT, 65535, 1)
    obs.obs_properties_add_int(
        props, "interval", "Update Interval (seconds)", 1, 3600, 1)
    return props

def script_update(settings):
    """
    Applies any changes made to the MQTT settings in the OBS Scripts GUI then
    reconnects the MQTT client.
    """
    # Apply the new settings
    global MQTT_HOST
    global MQTT_PORT
    global MQTT_CHANNEL
    global INTERVAL
    mqtt_host = obs.obs_data_get_string(settings, "mqtt_host")
    if mqtt_host != MQTT_HOST:
        MQTT_HOST = mqtt_host
    mqtt_channel = obs.obs_data_get_string(settings, "mqtt_channel")
    if mqtt_channel != MQTT_CHANNEL:
        MQTT_CHANNEL = mqtt_channel
    mqtt_port = obs.obs_data_get_int(settings, "mqtt_port")
    if mqtt_port != MQTT_PORT:
        MQTT_PORT = mqtt_port
    INTERVAL = obs.obs_data_get_int(settings, "interval")

    # Disconnect (if connected) and reconnect the MQTT client
    CLIENT.disconnect()
    try:
        CLIENT.connect(MQTT_HOST, MQTT_PORT, 60)
        # Publish our initial state
        CLIENT.publish(MQTT_CHANNEL, json.dumps(STATUS))
    except (socket.gaierror, ConnectionRefusedError) as e:
        print("NOTE: Got a socket issue: %s" % e)
        pass # Ignore it for now

    # Remove and replace the timer that publishes our status information
    obs.timer_remove(update_status)
    obs.timer_add(update_status, INTERVAL * 1000)
    CLIENT.loop() # So we can know if we connected successfully
