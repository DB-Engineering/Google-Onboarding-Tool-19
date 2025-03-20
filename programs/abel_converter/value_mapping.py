def map_units(fieldname):
    if any([
        "alarm" in fieldname,
        "run_command" in fieldname,
        "run_status" in fieldname,
        "damper_command" in fieldname,
        "damper_status" in fieldname,
        "mode" in fieldname,
        "valve_command" in fieldname,
        "valve_status" in fieldname,
        "count" in fieldname,
        "powerfactor" in fieldname
    ]):
        return "no-units"
    elif "percentage" in fieldname:
        return "percent"
    elif "temperature" in fieldname:
        return "degrees-fahrenheit"
    elif "frequency" in fieldname:
        return "hertz"
    elif "current" in fieldname:
        return "amperes"
    elif "torque" in fieldname:
        return "newton-meters"
    elif "power" in fieldname:
        return "kilowatts"
    elif "illuminance" in fieldname:
        return "lux"
    elif "energy_accumulator" in fieldname:
        return "kilowatt-hours"
    elif "time_accumulator" in fieldname:
        return "hours"
    elif "load_power" in fieldname:
        return "tons-of-refrigeration"
    elif "cooling_thermal_power" in fieldname:
        return "tons-of-refrigeration"
    elif "reactive_power" in fieldname:
        return "kilovolt-amperes-reactive"
    elif "reactive_energy_accumulator" in fieldname:
        return "kilovolt-ampere-hours"
    elif "thermal_energy_accumulator" in fieldname:
        return "tons-of-refrigeration"
    elif "thermalefficiency" in fieldname:
        return "kilowatts-per-ton"
    elif "water_volume_accumulator" in fieldname:
        return "us-gallons"
    elif "heating_thermal_power" in fieldname:
        return "btus-per-hour"
    elif "enthalpy" in fieldname:
        return "btus-per-pound-dry-air"
    elif "humidity" in fieldname:
        return "percent-relative-humidity"
    elif "voltage" in fieldname:
        return "volts"
    elif "air" in fieldname and "pressure" in fieldname:
        return "inches-of-water"
    elif any(["refrigerant" in fieldname, "water" in fieldname, "differential" in fieldname])  and "pressure" in fieldname:
        return "pounds-force-per-square-inch"
    elif "air" in fieldname and "flowrate" in fieldname:
        return "cubic-feet-per-minute"
    elif "water" in fieldname and "flowrate" in fieldname:
        return "us-gallons-per-minute"
    else:
        pass
    
def map_states(field_name, raw_state):
    if raw_state==None or type(raw_state)==float: 
        return_value = None
    else:
        if raw_state[0]=="active":
            if "alarm" in field_name: return_value = "ACTIVE"
            if "occupancy_status" in field_name: return_value = "OCCUPIED"
            if any(["run_command" in field_name, "run_status" in field_name]): return_value = "ON"
            if any(["damper_command" in field_name, "damper_status" in field_name]): return_value = "OPEN"
            if any(["valve_command" in field_name, "valve_status" in field_name]):  return_value = "OPEN"
        if raw_state[0]=="inactive":
            if "alarm" in field_name: return_value = "INACTIVE"
            if "occupancy_status" in field_name: return_value = "UNOCCUPIED"
            if any(["run_command" in field_name, "run_status" in field_name]): return_value = "OFF"
            if any(["damper_command" in field_name, "damper_status" in field_name]): return_value = "CLOSED"
            if any(["valve_command" in field_name, "valve_status" in field_name]): return_value = "CLOSED"
    return(return_value)