import esphome.const as c
import esphome.components.climate as cl
import esphome.components.uart as u
import inspect

icons = [name for name in dir(c) if name.startswith('ICON_')]
print('ICON count:', len(icons))
print('Sample ICONs:', icons[:20])
print('Has ICON_FAN:', hasattr(c,'ICON_FAN'))
print('Has ICON_HEATING_COIL:', hasattr(c,'ICON_HEATING_COIL'))
print('Climate attrs (selected):', [a for a in dir(cl) if 'schema' in a.lower() or 'Climate' in a])
try:
    sig = inspect.signature(u.final_validate_device_schema)
    print('uart.final_validate_device_schema signature:', sig)
except Exception as e:
    print('uart.final_validate_device_schema error:', e)

# show esphome version
try:
    import pkg_resources
    ver = pkg_resources.get_distribution('esphome').version
    print('esphome package version:', ver)
except Exception:
    try:
        import esphome
        print('esphome module:', getattr(esphome, '__version__', 'unknown'))
    except Exception:
        print('Could not determine esphome version')
