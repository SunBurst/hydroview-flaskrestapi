import json
import pytz
import uuid

from collections import defaultdict, OrderedDict
from datetime import datetime
from dateutil.relativedelta import relativedelta

from flask import abort, make_response, redirect, request, url_for

from app import app, session
from utils import CustomEncoder, datetime_to_timestamp_ms, make_timestamp_range

@app.route('/')
def index():
    return make_response(open('app/templates/index.html').read())

########## Stations API ############

@app.route('/api/stations', methods=['GET'])
def get_stations():
    bucket = request.args.get('bucket', default=0, type=int)
    query = "SELECT * FROM stations WHERE bucket=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (bucket,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/station', methods=['GET'])
def get_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    query = "SELECT * FROM station_info_by_station WHERE id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    try:
        data = rows[0]
    except IndexError:    
        abort(404)
    
    return json.dumps(data, cls=CustomEncoder)    

@app.route('/api/profile_vertical_positions_by_station_parameter', methods=['GET'])
def get_profile_vertical_positions_by_station_parameter():
    station_id = request.args.get('station_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    query = "SELECT * FROM vertical_positions_by_station_parameter WHERE station_id=? AND parameter_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, parameter_id,)).result()
    data =  [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/webcam_live_urls_by_station', methods=['GET'])
def get_webcam_live_urls_by_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    query = "SELECT * FROM webcam_live_urls_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data =  [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/video_urls_by_station', methods=['GET'])
def get_video_urls_by_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    from_timestamp = request.args.get('from_timestamp', type=int)
    to_timestamp = request.args.get('to_timestamp', type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    limit = request.args.get('limit', default=0, type=int)
    
    query = """
        SELECT * FROM video_urls_by_station WHERE station_id=? AND added_date>=? AND 
            added_date<=? ORDER BY added_date {order}""".format(order=order_by)
    
    if limit:
        query += " LIMIT {limit}".format(limit=limit)

    prepared = session.prepare(query)
    from_dt = datetime.fromtimestamp(from_timestamp/1000)
    to_dt = datetime.fromtimestamp(to_timestamp/1000)
    
    rows = session.execute_async(prepared, (station_id, from_dt, to_dt,)).result()   
    
    data = [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/hourly_webcam_photos_by_station', methods=['GET'])
def get_hourly_webcam_photos_by_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    from_timestamp = request.args.get('from_timestamp', type=int)
    on_timestamp = request.args.get('on_timestamp', type=int)
    to_timestamp = request.args.get('to_timestamp', type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    limit = request.args.get('limit', default=0, type=int)
    
    query = "SELECT * FROM hourly_webcam_photos_by_station WHERE station_id=? AND date=? "
        
    if from_timestamp and to_timestamp: 
        query += "AND timestamp >=? AND timestamp <=? "
    
    query += "ORDER BY timestamp {order} ".format(order=order_by)

    if limit:
        query += "LIMIT {limit}".format(limit=limit)
    
    prepared = session.prepare(query)
    
    data = []
    
    if on_timestamp:
        on_dt = datetime.fromtimestamp(on_timestamp/1000)
        rows = session.execute_async(prepared, (station_id, on_dt,)).result()
        data = [row for row in rows]
    elif from_timestamp and to_timestamp:
        from_dt = datetime.fromtimestamp(from_timestamp/1000)
        to_dt = datetime.fromtimestamp(to_timestamp/1000)
        
        futures = []

        current_date = datetime(from_dt.year, from_dt.month, from_dt.day)

        while (current_date <= to_dt):
            futures.append(session.execute_async(prepared, (station_id, current_date, from_timestamp, to_timestamp,)))
            current_date += relativedelta(days=1)

        for future in futures:
            rows = future.result()
            for row in rows:
                data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/sensors_by_station/<uuid:station_id>', methods=['GET'])
def get_sensors_by_station(station_id):
    query = "SELECT * FROM sensors_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data = [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/parameters_by_station', methods=['GET'])
def get_parameters_by_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    
    query = "SELECT * FROM parameters_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data =  [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/groups_by_station/<uuid:station_id>', methods=['GET'])
def get_groups_by_station(station_id):
    query = "SELECT * FROM parameter_groups_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data =  [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/parameter_sensors_by_station', methods=['GET'])
def get_parameter_sensors_by_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    
    query = "SELECT * FROM parameter_sensors_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/groups_by_sensor/<uuid:sensor_id>', methods=['GET'])
def get_groups_by_sensor(sensor_id):
    query = "SELECT * FROM parameter_groups_by_sensor WHERE sensor_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (sensor_id,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/parameters_by_sensor/<uuid:sensor_id>', methods=['GET'])
def get_parameters_by_sensor(sensor_id):
    query = "SELECT * FROM parameters_by_sensor WHERE sensor_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (sensor_id,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/measurement_frequencies_by_sensor_parameter', methods=['GET'])
def get_measurement_frequencies_by_sensor_parameter():
	sensor_id = request.args.get('sensor_id', type=uuid.UUID)
	parameter_id = request.args.get('parameter_id', type=uuid.UUID)
	parameter_type = request.args.get('parameter_type', type=str)
	
	query = "SELECT * FROM measurement_frequencies_by_sensor_parameter WHERE sensor_id=? AND parameter_id=? AND parameter_type=?"
	prepared = session.prepare(query)
	rows = session.execute_async(prepared, (sensor_id, parameter_id, parameter_type, )).result()
	data = [row for row in rows]
	
	return json.dumps(data, cls=CustomEncoder)

@app.route('/api/dynamic_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_dynamic_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    
    frequencies_query = "SELECT * FROM group_measurement_frequencies_by_station WHERE station_id=? AND group_id=?"
    prepared_frequencies_query = session.prepare(frequencies_query)
    frequencies_rows = session.execute_async(prepared_frequencies_query, (station_id, group_id,)).result()
    frequencies = []
    
    try:
        frequencies_row = frequencies_rows[0]
    except IndexError as e:
        print(e)
    else:
        frequencies = frequencies_row.get('measurement_frequencies', [])
        
    if not frequencies:
        return json.dumps([], cls=CustomEncoder)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    delta = to_dt - from_dt

    if delta.days < 12: # delta < 12 days
        if delta.days < 6: # delta < 6 days
            if delta.days < 4: # delta < 4 days
                if delta.days < 3: # delta < 3 days
                    if delta.days < 2:  # delta < 2 days
                        if delta.days < 1:  # delta < 1 days
                            if delta.seconds < (60 * 60 * 5): # delta < 5 hours                             
                                if delta.seconds < (60 * 5):    # delta < 5 minutes
                                    if '1 Sec' in frequencies:
                                        return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '1 Min' in frequencies:
                                        return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '5 Min' in frequencies:
                                        return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '10 Min' in frequencies:
                                        return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '15 Min' in frequencies:
                                        return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '20 Min' in frequencies:
                                        return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '30 Min' in frequencies:
                                        return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif 'Hourly' in frequencies:
                                        return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif 'Daily' in frequencies:
                                        return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                else:   # 5 hours > delta >= 5 minutes
                                    if '1 Min' in frequencies:
                                        return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '1 Sec' in frequencies:
                                        return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '5 Min' in frequencies:
                                        return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '10 Min' in frequencies:
                                        return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '15 Min' in frequencies:
                                        return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '20 Min' in frequencies:
                                        return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif '30 Min' in frequencies:
                                        return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif 'Hourly' in frequencies:
                                        return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                    elif 'Daily' in frequencies:
                                        return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            else:   # 1 days > delta >= 5 hours 
                                if '5 Min' in frequencies:
                                    return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif '1 Min' in frequencies:
                                    return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)                                
                                elif '1 Sec' in frequencies:
                                    return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif '10 Min' in frequencies:
                                    return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif '15 Min' in frequencies:
                                    return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif '20 Min' in frequencies:
                                    return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif '30 Min' in frequencies:
                                    return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif 'Hourly' in frequencies:
                                    return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                                elif 'Daily' in frequencies:
                                    return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        else:   # 2 days < delta >= 1 days
                            if '10 Min' in frequencies:
                                return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif '5 Min' in frequencies:
                                return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif '1 Min' in frequencies:
                                return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)                                
                            elif '1 Sec' in frequencies:
                                return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif '15 Min' in frequencies:
                                return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif '20 Min' in frequencies:
                                return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif '30 Min' in frequencies:
                                return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif 'Hourly' in frequencies:
                                return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                            elif 'Daily' in frequencies:
                                return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    else:   # 3 days > delta >= 2 days
                        if '15 Min' in frequencies:
                            return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif '10 Min' in frequencies:
                            return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif '5 Min' in frequencies:
                            return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif '1 Min' in frequencies:
                            return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)                                
                        elif '1 Sec' in frequencies:
                            return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif '20 Min' in frequencies:
                            return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif '30 Min' in frequencies:
                            return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif 'Hourly' in frequencies:
                            return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                        elif 'Daily' in frequencies:
                            return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                else:   # 4 days > delta >= 3 days
                    if '20 Min' in frequencies:
                        return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif '15 Min' in frequencies:
                        return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif '10 Min' in frequencies:
                        return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif '5 Min' in frequencies:
                        return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif '1 Min' in frequencies:
                        return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)                                
                    elif '1 Sec' in frequencies:
                        return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif '30 Min' in frequencies:
                        return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif 'Hourly' in frequencies:
                        return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                    elif 'Daily' in frequencies:
                        return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            else:   # 6 days < delta >= 4 days
                if '30 Min' in frequencies:
                    return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif '20 Min' in frequencies:
                    return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif '15 Min' in frequencies:
                    return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif '10 Min' in frequencies:
                    return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif '5 Min' in frequencies:
                    return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif '1 Min' in frequencies:
                    return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)                                
                elif '1 Sec' in frequencies:
                    return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif 'Hourly' in frequencies:
                    return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
                elif 'Daily' in frequencies:
                    return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        else:   # 12 days > delta >= 6 days
            if 'Hourly' in frequencies:
                return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '30 Min' in frequencies:
                return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '20 Min' in frequencies:
                return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '15 Min' in frequencies:
                return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '10 Min' in frequencies:
                return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '5 Min' in frequencies:
                return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '1 Min' in frequencies:
                return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif '1 Sec' in frequencies:
                return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
            elif 'Daily' in frequencies:
                return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
    else:   # unbound > delta >= 12 days
        if 'Daily' in frequencies:
            return get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif 'Hourly' in frequencies:
            return get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '30 Min' in frequencies:
            return get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '20 Min' in frequencies:
            return get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '15 Min' in frequencies:
            return get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '10 Min' in frequencies:
            return get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '5 Min' in frequencies:
            return get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '1 Min' in frequencies:
            return get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
        elif '1 Sec' in frequencies:
            return get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp)
    
    
    return json.dumps({}, cls=CustomEncoder)
 
@app.route('/api/daily_single_parameter_measurements_by_sensor', methods=['GET'])
def get_daily_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, year, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM daily_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND year=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
                
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/hourly_single_parameter_measurements_by_sensor', methods=['GET'])
def get_hourly_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, year, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM hourly_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND year=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
                
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)


@app.route('/api/thirty_min_single_parameter_measurements_by_sensor', methods=['GET'])
def get_thirty_min_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, year, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM thirty_min_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND year=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
                
    prepared = session.prepare(query)
        
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)


@app.route('/api/twenty_min_single_parameter_measurements_by_sensor', methods=['GET'])
def get_twenty_min_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, year, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM twenty_min_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND year=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
                
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)


@app.route('/api/fifteen_min_single_parameter_measurements_by_sensor', methods=['GET'])
def get_fifteen_min_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM fifteen_min_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
                
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)    
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/ten_min_single_parameter_measurements_by_sensor', methods=['GET'])
def get_ten_min_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM ten_min_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)
        
@app.route('/api/five_min_single_parameter_measurements_by_sensor', methods=['GET'])
def get_five_min_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
        
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM five_min_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)

    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/one_min_single_parameter_measurements_by_sensor', methods=['GET'])
def get_one_min_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, week_first_day, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM one_min_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND week_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)

    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    year, week_number, weekday = from_dt.isocalendar()
    current_first_day_of_week = datetime.strptime('{year} {week_number} 1'.format(year=year, week_number=week_number), '%Y %W %w')
    while (current_first_day_of_week <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_week, from_timestamp, to_timestamp, )))
        current_first_day_of_week += relativedelta(weeks=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)


@app.route('/api/one_sec_single_parameter_measurements_by_sensor', methods=['GET'])
def get_one_sec_single_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, date, timestamp, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM one_sec_single_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND date=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    current_day = datetime(from_dt.year, from_dt.month, from_dt.day)
    while (current_day <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_day, from_timestamp, to_timestamp, )))
        current_day += relativedelta(days=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/daily_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_daily_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, year, timestamp, vertical_position, unit"
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM daily_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND year=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, year, from_timestamp, to_timestamp,)))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/hourly_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_hourly_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, year, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM hourly_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND year=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/thirty_min_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_thirty_min_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM thirty_min_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)

    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/twenty_min_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_twenty_min_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM twenty_min_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/fifteen_min_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_fifteen_min_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM fifteen_min_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/ten_min_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_ten_min_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM ten_min_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? 
                AND timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/five_min_profile_parameter_measurements_by_sensor')
def get_five_min_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, month_first_day, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM five_min_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/one_min_profile_parameter_measurements_by_sensor', methods=['GET'])
def get_one_min_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, week_first_day, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM one_min_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND week_first_day=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    year, week_number, weekday = from_dt.isocalendar()
    current_first_day_of_week = datetime.strptime('{year} {week_number} 1'.format(year=year, week_number=week_number), '%Y %W %w')
    while (current_first_day_of_week <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_first_day_of_week, from_timestamp, to_timestamp, )))
        current_first_day_of_week += relativedelta(weeks=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/one_sec_profile_parameter_measurements_by_sensor')
def get_one_sec_profile_parameter_measurements_by_sensor():
    sensor_id = request.args.get('sensor_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    qc_level = request.args.get('qc_level', type=int)
    from_timestamp = request.args.get('from_timestamp', default=None, type=int)
    to_timestamp = request.args.get('to_timestamp', default=None, type=int)
    order_by = request.args.get('order_by', default='DESC', type=str)
    data_sets = request.args.getlist('data_sets')
    
    columns = "sensor_id, parameter_id, qc_level, date, timestamp, vertical_position, unit"
    
    try:
        data_sets = data_sets[0].split(',')
    except IndexError as e:
        data_sets = []
    
    if not data_sets:
        columns += ",min, avg, max"
    
    if "min" in data_sets:
        columns += ",min_value"
    if "avg" in data_sets:
        columns += ",avg_value"
    if "max" in data_sets:
        columns += ",max_value"
    
    query = """
        SELECT {columns} FROM one_sec_profile_measurements_by_sensor WHERE sensor_id=? AND 
            parameter_id=? AND qc_level=? AND date=? AND timestamp>=? AND 
                timestamp<=? ORDER BY timestamp {order}""".format(columns=columns, order=order_by)
    
    prepared = session.prepare(query)
    
    from_timestamp, to_timestamp = make_timestamp_range(from_timestamp, to_timestamp)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_day = datetime(from_dt.year, from_dt.month, from_dt.day)
    while (current_day <= to_dt):
        futures.append(session.execute_async(prepared, (sensor_id, parameter_id, qc_level, current_day, from_timestamp, to_timestamp, )))
        current_day += relativedelta(days=1)
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/group_measurement_frequencies_by_station/<uuid:station_id>', methods=['GET'])
def get_group_measurement_frequencies_by_station(station_id):
    query = "SELECT * FROM group_measurement_frequencies_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, )).result()
    data = [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/measurement_frequencies_by_station', methods=['GET'])
def get_measurement_frequencies_by_station():
    station_id = request.args.get('station_id', type=uuid.UUID)
    
    query = "SELECT * FROM measurement_frequencies_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, )).result()
    data = [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/group_parameters_by_station/<uuid:station_id>', methods=['GET'])
def get_group_parameters_by_station(station_id):
    query = "SELECT * FROM group_parameters_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, )).result()
    data =  [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/group_parameters_by_station_group/<uuid:station_id>/<uuid:group_id>', methods=['GET'])
def get_group_parameters_by_station_group(station_id, group_id):
    query = "SELECT * FROM parameters_by_station_group WHERE station_id=? AND group_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, group_id, )).result()
    data =  [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/daily_group_measurements_by_station/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_date>/<int:to_date>', methods=['GET'])
def get_daily_group_measurements_by_station(station_id, group_id, qc_level, from_date, to_date):
    query = "SELECT * FROM daily_parameter_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND date>=? AND date<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_date/1000.0)
    to_dt = datetime.fromtimestamp(to_date/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_date, to_date, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/daily_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_date>/<int:to_date>', methods=['GET'])
def get_daily_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_date, to_date):
    query = "SELECT * FROM daily_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND date>=? AND date<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_date/1000.0)
    to_dt = datetime.fromtimestamp(to_date/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_date, to_date, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/daily_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_date>/<int:to_date>', methods=['GET'])
def get_daily_group_measurements_by_station_chart(station_id, group_id, qc_level, from_date, to_date):
    query = "SELECT * FROM daily_parameter_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND date>=? AND date<=? ORDER BY date ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_date/1000.0)
    to_dt = datetime.fromtimestamp(to_date/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_date, to_date, )))
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('date'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('date'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)

@app.route('/api/hourly_group_measurements_by_station/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_date_hour>/<int:to_date_hour>/')
def get_hourly_group_measurements_by_station(station_id, group_id, qc_level, from_date_hour, to_date_hour):
    query = "SELECT * FROM hourly_parameter_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND date_hour>=? AND date_hour<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_date_hour/1000.0)
    to_dt = datetime.fromtimestamp(to_date_hour/1000.0)

    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_date_hour, to_date_hour, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)

    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/thirty_min_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_thirty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM thirty_min_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/twenty_min_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_twenty_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM twenty_min_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/fifteen_min_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_fifteen_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM fifteen_min_group_meas_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/ten_min_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_ten_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM ten_min_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/hourly_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_date_hour>/<int:to_date_hour>', methods=['GET'])
def get_hourly_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_date_hour, to_date_hour):
    query = "SELECT * FROM hourly_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND date_hour>=? AND date_hour<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_date_hour/1000.0)
    to_dt = datetime.fromtimestamp(to_date_hour/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_date_hour, to_date_hour, )))
    
    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/thirty_min_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>/')
def get_thirty_min_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM thirty_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)
    
@app.route('/api/twenty_min_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>/')
def get_twenty_min_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM twenty_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)
    
@app.route('/api/fifteen_min_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>/')
def get_fifteen_min_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM fifteen_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_timestamp, to_timestamp, )))
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'name': parameter_name, 
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)
    
@app.route('/api/ten_min_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>/')
def get_ten_min_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM ten_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []

    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'name': parameter_name, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)
    
@app.route('/api/one_min_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>')
def get_one_min_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM one_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND week_first_day=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    year, week_number, weekday = from_dt.isocalendar()
    current_first_day_of_week = datetime.strptime('{} {} 1'.format(year, week_number), '%Y %W %w')
    while (current_first_day_of_week <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_first_day_of_week, from_timestamp, to_timestamp, )))
        current_first_day_of_week += relativedelta(weeks=1)
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'name': parameter_name, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)
    
@app.route('/api/one_sec_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>/')
def get_one_sec_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM one_sec_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND date=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_day = datetime(from_dt.year, from_dt.month, from_dt.day)
    while (current_day <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_day, from_timestamp, to_timestamp, )))
        current_day += relativedelta(days=1)
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            parameter_id_str = str(parameter_id)
            if parameter_id_str not in parameters:
                parameters[parameter_id_str] = {
                    'id': parameter_id, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id_str]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id_str]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)

@app.route('/api/hourly_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_date_hour>/<int:to_date_hour>/')
def get_hourly_group_measurements_by_station_chart(station_id, group_id, qc_level, from_date_hour, to_date_hour):
    query = "SELECT * FROM hourly_parameter_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND year=? AND date_hour>=? AND date_hour<=? ORDER BY date_hour ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_date_hour/1000.0)
    to_dt = datetime.fromtimestamp(to_date_hour/1000.0)
    
    futures = []
    for year in range(from_dt.year, to_dt.year + 1):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, year, from_date_hour, to_date_hour, )))
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            if parameter_id not in parameters:
                parameters[parameter_id] = {
                    'id': parameter_id, 
                    'qc_level': qc_level,
                    'unit': parameter_unit,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id]['averages'].append([row.get('date_hour'), row.get('avg_value')])
            parameters[parameter_id]['ranges'].append([row.get('date_hour'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)

    
@app.route('/api/five_min_group_measurements_by_station/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_five_min_group_measurements_by_station(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM five_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []

    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)

    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/five_min_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_five_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM five_min_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    
    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)

    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/one_min_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_one_min_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    
    query = "SELECT * FROM one_min_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND week_first_day=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    year, week_number, weekday = from_dt.isocalendar()
    current_first_day_of_week = datetime.strptime('{} {} 1'.format(year, week_number), '%Y %W %w')
    while (current_first_day_of_week <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_first_day_of_week, from_timestamp, to_timestamp, )))
        current_first_day_of_week += relativedelta(weeks=1)

    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/one_sec_group_measurements_by_station_time_grouped/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>', methods=['GET'])
def get_one_sec_group_measurements_by_station_time_grouped(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    
    query = "SELECT * FROM one_sec_group_measurements_by_station_grouped WHERE station_id=? AND group_id=? AND qc_level=? AND date=? AND timestamp>=? AND timestamp<=?"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []
    current_date = datetime(from_dt.year, from_dt.month, from_dt.day)
    while (current_date <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_date, from_timestamp, to_timestamp, )))
        current_date += relativedelta(days=1)

    data = []
    for future in futures:
        rows = future.result()
        for row in rows:
            data.append(row)
    
    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/five_min_group_measurements_by_station_chart/<uuid:station_id>/<uuid:group_id>/<int:qc_level>/<int:from_timestamp>/<int:to_timestamp>/')
def get_five_min_group_measurements_by_station_chart(station_id, group_id, qc_level, from_timestamp, to_timestamp):
    query = "SELECT * FROM five_min_group_measurements_by_station WHERE station_id=? AND group_id=? AND qc_level=? AND month_first_day=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp ASC"
    prepared = session.prepare(query)
    
    from_dt = datetime.fromtimestamp(from_timestamp/1000.0)
    to_dt = datetime.fromtimestamp(to_timestamp/1000.0)
    
    futures = []

    current_first_day_of_month = datetime(from_dt.year, from_dt.month, 1)
    while (current_first_day_of_month <= to_dt):
        futures.append(session.execute_async(prepared, (station_id, group_id, qc_level, current_first_day_of_month, from_timestamp, to_timestamp, )))
        current_first_day_of_month += relativedelta(months=1)
    
    parameters = OrderedDict()

    for future in futures:
        rows = future.result()
        for row in rows:
            parameter_id = row.get('parameter_id')
            parameter_unit = row.get('unit')
            if parameter_id not in parameters:
                parameters[parameter_id] = {
                    'id': parameter_id, 
                    'unit': parameter_unit,
                    'qc_level': qc_level,
                    'averages': [],
                    'ranges': []
                }

            parameters[parameter_id]['averages'].append([row.get('timestamp'), row.get('avg_value')])
            parameters[parameter_id]['ranges'].append([row.get('timestamp'), row.get('min_value'), row.get('max_value')])

    return json.dumps(parameters, cls=CustomEncoder)
    
@app.route('/api/group_qc_levels_by_station/<uuid:station_id>', methods=['GET'])
def get_group_qc_levels_by_station(station_id):
    query = "SELECT * FROM group_qc_levels_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/measurement_frequencies_by_station_parameter', methods=['GET'])
def get_measurement_frequencies_by_station_parameter():
    station_id = request.args.get('station_id', type=uuid.UUID)
    parameter_id = request.args.get('parameter_id', type=uuid.UUID)
    parameter_type = request.args.get('parameter_type', type=uuid.UUID)
    
    query = """SELECT * FROM measurement_frequencies_by_station_parameter WHERE station_id=? AND 
        parameter_id=? AND parameter_type=?"""

    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, parameter_id, parameter_type,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)

@app.route('/api/parameter_measurement_frequencies_by_station/<uuid:station_id>', methods=['GET'])
def get_parameter_measurement_frequencies_by_station(station_id):
    query = "SELECT * FROM parameter_measurement_frequencies_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id, )).result()
    data = [row for row in rows]
    
    return json.dumps(data, cls=CustomEncoder)
    
@app.route('/api/parameter_qc_levels_by_station/<uuid:station_id>', methods=['GET'])
def get_parameter_qc_levels_by_station(station_id):
    query = "SELECT * FROM parameter_qc_levels_by_station WHERE station_id=?"
    prepared = session.prepare(query)
    rows = session.execute_async(prepared, (station_id,)).result()
    data = [row for row in rows]

    return json.dumps(data, cls=CustomEncoder)

