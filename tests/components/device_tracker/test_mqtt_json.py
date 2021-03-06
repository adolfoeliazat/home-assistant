"""The tests for the JSON MQTT device tracker platform."""
import asyncio
import json
import unittest
from unittest.mock import patch
import logging
import os

from homeassistant.setup import setup_component
from homeassistant.components import device_tracker
from homeassistant.const import CONF_PLATFORM

from tests.common import (
    get_test_home_assistant, mock_mqtt_component, fire_mqtt_message)

_LOGGER = logging.getLogger(__name__)

LOCATION_MESSAGE = {
    'longitude': 1.0,
    'gps_accuracy': 60,
    'latitude': 2.0,
    'battery_level': 99.9}

LOCATION_MESSAGE_INCOMPLETE = {
    'longitude': 2.0}


class TestComponentsDeviceTrackerJSONMQTT(unittest.TestCase):
    """Test JSON MQTT device tracker platform."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        mock_mqtt_component(self.hass)

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.hass.stop()
        try:
            os.remove(self.hass.config.path(device_tracker.YAML_DEVICES))
        except FileNotFoundError:
            pass

    def test_ensure_device_tracker_platform_validation(self): \
            # pylint: disable=invalid-name
        """Test if platform validation was done."""
        @asyncio.coroutine
        def mock_setup_scanner(hass, config, see, discovery_info=None):
            """Check that Qos was added by validation."""
            self.assertTrue('qos' in config)

        with patch('homeassistant.components.device_tracker.mqtt_json.'
                   'async_setup_scanner', autospec=True,
                   side_effect=mock_setup_scanner) as mock_sp:

            dev_id = 'paulus'
            topic = 'location/paulus'
            assert setup_component(self.hass, device_tracker.DOMAIN, {
                device_tracker.DOMAIN: {
                    CONF_PLATFORM: 'mqtt_json',
                    'devices': {dev_id: topic}
                }
            })
            assert mock_sp.call_count == 1

    def test_json_message(self):
        """Test json location message."""
        dev_id = 'zanzito'
        topic = 'location/zanzito'
        location = json.dumps(LOCATION_MESSAGE)

        assert setup_component(self.hass, device_tracker.DOMAIN, {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: 'mqtt_json',
                'devices': {dev_id: topic}
            }
        })
        fire_mqtt_message(self.hass, topic, location)
        self.hass.block_till_done()
        state = self.hass.states.get('device_tracker.zanzito')
        self.assertEqual(state.attributes.get('latitude'), 2.0)
        self.assertEqual(state.attributes.get('longitude'), 1.0)

    def test_non_json_message(self):
        """Test receiving a non JSON message."""
        dev_id = 'zanzito'
        topic = 'location/zanzito'
        location = 'home'

        assert setup_component(self.hass, device_tracker.DOMAIN, {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: 'mqtt_json',
                'devices': {dev_id: topic}
            }
        })

        with self.assertLogs(level='ERROR') as test_handle:
            fire_mqtt_message(self.hass, topic, location)
            self.hass.block_till_done()
            self.assertIn(
                "ERROR:homeassistant.components.device_tracker.mqtt_json:"
                "Error parsing JSON payload: home",
                test_handle.output[0])

    def test_incomplete_message(self):
        """Test receiving an incomplete message."""
        dev_id = 'zanzito'
        topic = 'location/zanzito'
        location = json.dumps(LOCATION_MESSAGE_INCOMPLETE)

        assert setup_component(self.hass, device_tracker.DOMAIN, {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: 'mqtt_json',
                'devices': {dev_id: topic}
            }
        })

        with self.assertLogs(level='ERROR') as test_handle:
            fire_mqtt_message(self.hass, topic, location)
            self.hass.block_till_done()
            self.assertIn(
                "ERROR:homeassistant.components.device_tracker.mqtt_json:"
                "Skipping update for following data because of missing "
                "or malformatted data: {\"longitude\": 2.0}",
                test_handle.output[0])
