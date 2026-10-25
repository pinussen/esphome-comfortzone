import json
from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.pins as pins
from esphome.components import uart
from esphome.components.globals import GlobalsComponent
from esphome.const import (CONF_RESTORE_VALUE, CONF_INITIAL_VALUE, CONF_UART_ID, CONF_ID, CONF_RX_PIN, CONF_TX_PIN, CONF_NUMBER)
from esphome.core import (CORE)
from .const import (
    CONF_COMFORTZONE_ID,
    CONF_RE_DE_PIN, CONF_TE3_OFFSET_GLOBAL_ID,
)

CODEOWNERS = ["@vinnyspb"]
DEPENDENCIES = ["uart"]

comfortzone_ns = cg.esphome_ns.namespace("comfortzone")
ComfortzoneComponent = comfortzone_ns.class_("ComfortzoneComponent", cg.Component, uart.UARTDevice)


def validate_global_float_with_restore_and_initial_value(value):
    defined_globals = CORE.raw_config.get('globals', {})
    global_var_conf = next((g for g in defined_globals if g.get('id') == value), None)
    if global_var_conf is None:
        raise cv.Invalid(f"Global ID '{value.id}' not found")

    if global_var_conf.get('type') != 'float':
        raise cv.Invalid(f"Global variable '{value.id}' must have type 'float'")

    if not global_var_conf.get(CONF_RESTORE_VALUE, False):
        raise cv.Invalid(f"Global variable '{value.id}' must have 'restore_value' set to true")

    if str(global_var_conf.get(CONF_INITIAL_VALUE, '')) != '0.0':
        raise cv.Invalid(f"Global variable '{value.id}' must have 'initial_value' set to '0.0'")

    return value


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_COMFORTZONE_ID): cv.declare_id(ComfortzoneComponent),
        cv.Required(CONF_RE_DE_PIN): pins.gpio_output_pin_schema,
        cv.Optional("detect_idle_break", default=False): cv.boolean,
        cv.Optional("controller_address", default=0x45726963): cv.hex_uint32_t,
        cv.Required(CONF_TE3_OFFSET_GLOBAL_ID): cv.All(
            # Ensure the ID refers to a global variable
            cv.use_id(GlobalsComponent),
            # Custom validator to enforce specific attributes about the global
            validate_global_float_with_restore_and_initial_value,
        ),
    }
).extend(uart.UART_DEVICE_SCHEMA)
FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "comfortzone", baud_rate=19200, require_tx=True, require_rx=True, data_bits=8, parity="NONE", stop_bits=1
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_COMFORTZONE_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    cg.add(var.set_controller_address(config["controller_address"]))

    if config["detect_idle_break"]:
        bus = next(b for b in CORE.config["uart"] if b[CONF_ID] == config[CONF_UART_ID])
        if not CORE.is_esp32 or CONF_RX_PIN not in bus:
            raise cv.Invalid("detect_idle_break requires an ESP32 hardware UART with an RX pin")
        cg.add(var.set_rx_idle_pin(bus[CONF_RX_PIN][CONF_NUMBER]))
        cg.add(var.set_tx_monitor_pin(bus[CONF_TX_PIN][CONF_NUMBER]))

    if CONF_RE_DE_PIN in config and config[CONF_RE_DE_PIN]:
        re_de_pin = await cg.gpio_pin_expression(config[CONF_RE_DE_PIN])
        cg.add(var.set_re_de_pin(re_de_pin))

    if CONF_TE3_OFFSET_GLOBAL_ID in config:
        var_global_offset = await cg.get_variable(config[CONF_TE3_OFFSET_GLOBAL_ID])
        cg.add(var.set_te3_offset_global(var_global_offset))

    snapshot = json.loads((Path(__file__).resolve().parent / "third_party" /
                           "comfortzone_heatpump.lock.json").read_text())
    cg.add_define("CZ_LIBRARY_REVISION", snapshot["commit"][:12])
    cg.add_library("FastCRC", version=None, repository="https://github.com/vinnyspb/FastCRC.git#c25258960e313a68237bf62db08770707955b82b")
    # Link the exact bundled sources; file:// leaves a stale copy after edits.
    library_path = "symlink://" + str(Path(__file__).resolve().parent / "third_party" / "comfortzone_heatpump")
    cg.add_library("comfortzone_heatpump", version=None, repository=library_path)
