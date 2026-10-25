import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button, time
from esphome.const import CONF_ID
from . import ComfortzoneComponent, comfortzone_ns
from .const import CONF_COMFORTZONE_ID
DEPENDENCIES = ["comfortzone"]
HotWaterButton = comfortzone_ns.class_("ComfortzoneHotWaterButton", button.Button)
ACTIONS = {"extra_hot_water": 0, "fireplace": 1, "sync_clock": 2}


def validate_action(config):
    sync = config["action"] == "sync_clock"
    if sync and ("enable" in config or "time_id" not in config):
        raise cv.Invalid("sync_clock requires time_id and does not accept enable")
    if not sync and ("enable" not in config or "time_id" in config):
        raise cv.Invalid("extra_hot_water/fireplace require enable and do not accept time_id")
    config.setdefault("icon", {"extra_hot_water": "mdi:water-boiler", "fireplace": "mdi:fireplace",
                               "sync_clock": "mdi:clock-check-outline"}[config["action"]])
    return config


CONFIG_SCHEMA = cv.All(button.button_schema(HotWaterButton).extend({
    cv.GenerateID(CONF_COMFORTZONE_ID): cv.use_id(ComfortzoneComponent),
    cv.Optional("action", default="extra_hot_water"): cv.one_of(*ACTIONS),
    cv.Optional("enable"): cv.boolean,
    cv.Optional("time_id"): cv.use_id(time.RealTimeClock),
}), validate_action)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await button.register_button(var, config)
    hub = await cg.get_variable(config[CONF_COMFORTZONE_ID])
    cg.add(var.set_parent(hub))
    cg.add(var.set_action(ACTIONS[config["action"]]))
    if "enable" in config:
        cg.add(var.set_enable(config["enable"]))
    if "time_id" in config:
        rtc = await cg.get_variable(config["time_id"])
        cg.add(hub.set_time_source(rtc))
