import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select
from esphome.const import CONF_ID
from . import ComfortzoneComponent, comfortzone_ns
from .const import CONF_COMFORTZONE_ID
DEPENDENCIES = ["comfortzone"]
FanSelect = comfortzone_ns.class_("ComfortzoneFanSelect", select.Select)
CONFIG_SCHEMA = select.select_schema(FanSelect, icon="mdi:fan").extend({
    cv.GenerateID(CONF_COMFORTZONE_ID): cv.use_id(ComfortzoneComponent),
})
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await select.register_select(var, config, options=["Low", "Normal", "High"])
    hub = await cg.get_variable(config[CONF_COMFORTZONE_ID])
    cg.add(hub.set_fan_select(var))
