import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import button
from esphome.const import CONF_ID
from . import ComfortzoneComponent, comfortzone_ns
from .const import CONF_COMFORTZONE_ID
DEPENDENCIES = ["comfortzone"]
HotWaterButton = comfortzone_ns.class_("ComfortzoneHotWaterButton", button.Button)
CONFIG_SCHEMA = button.button_schema(HotWaterButton, icon="mdi:water-boiler").extend({
    cv.GenerateID(CONF_COMFORTZONE_ID): cv.use_id(ComfortzoneComponent),
    cv.Required("enable"): cv.boolean,
})
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await button.register_button(var, config)
    hub = await cg.get_variable(config[CONF_COMFORTZONE_ID])
    cg.add(var.set_parent(hub))
    cg.add(var.set_enable(config["enable"]))
