import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.const import CONF_ID, ENTITY_CATEGORY_CONFIG
from . import ComfortzoneComponent, comfortzone_ns
from .const import CONF_COMFORTZONE_ID
DEPENDENCIES = ["comfortzone"]
CurveNumber = comfortzone_ns.class_("ComfortzoneCurveNumber", number.Number)
CONFIG_SCHEMA = number.number_schema(CurveNumber, icon="mdi:chart-bell-curve", entity_category=ENTITY_CATEGORY_CONFIG).extend({
    cv.GenerateID(CONF_COMFORTZONE_ID): cv.use_id(ComfortzoneComponent),
})
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await number.register_number(var, config, min_value=1, max_value=10, step=1)
    hub = await cg.get_variable(config[CONF_COMFORTZONE_ID])
    cg.add(hub.set_curve_number(var))
