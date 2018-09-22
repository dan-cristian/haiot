from music import mpd
from main.logger_helper import L
from rule import rule_common
from rule.rules_run import water_all_3_minute, water_front_off, water_back_off, water_front_3_minute, \
    water_back_3_minute


# special format needed: alexawemo_<wemo device name, substitute space with _>_<operation: on or off>
def alexawemo_front_lights_on():
    L.l.info('front_lights_relay on')
    rule_common.update_custom_relay('front_lights_relay', True)
    return True


def alexawemo_front_lights_off():
    L.l.info('front_lights_relay off')
    rule_common.update_custom_relay('front_lights_relay', False)
    return True


def alexawemo_watering_on():
    """is_async=1"""
    water_all_3_minute()
    return True


def alexawemo_watering_off():
    """is_async=1"""
    water_front_off()
    water_back_off()
    return True


def alexawemo_waterfront_on():
    """is_async=1"""
    water_front_3_minute()
    return True


def alexawemo_waterback_on():
    """is_async=1"""
    water_back_3_minute()
    return True


def alexawemo_music_livingroom_on():
    return mpd.play('livingroom', default_dir='/_New/')


def alexawemo_music_livingroom_off():
    return mpd.pause('livingroom')


def alexawemo_music_bedroom_on():
    return mpd.play('bedroom', default_dir='/_New/')


def alexawemo_music_bedroom_off():
    return mpd.pause('bedroom')


def alexawemo_music_bathroom_on():
    return mpd.play('bedroom', default_dir='/_New/')


def alexawemo_music_bathroom_off():
    return mpd.pause('bedroom')