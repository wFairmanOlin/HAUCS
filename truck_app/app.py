from flask import Flask, render_template, jsonify, request
# from flask_apscheduler import APScheduler
from datetime import datetime, timedelta, timezone
import os, smtplib, json
import numpy as np
import pytz
import random
import time
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

###BLE SETUP
ble = BLERadio()
uart_connection = None

sensor_file = "data/sensor.json"

app = Flask(__name__)

@app.route('/')
def home():
#    with open('static/json/farm_features.json', 'r') as file:
#        data = file.read()
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

'''
Data Source: call this from javascript to get fresh data
'''
@app.route('/sdata', methods=['GET'])
def get_ble():
    with open(sensor_file) as file:
        sdata = json.load(file)
        
    return jsonify(sdata)

@app.route('/data/' + '<ref>', methods=['GET'])
def data(ref):
    db_path = ref.split(' ')
    db_path = "/".join(db_path)
    data = db.reference(db_path).get()
    return jsonify(data)

'''
Data Source: call this from javascript to get fresh data in given time range
'''
@app.route('/dataTime/' + '<ref>', methods=['GET'])
def dataTime(ref):
    variables = ref.split(' ')
    db_path = "/".join(variables[0:2])
    start = variables[2]
    end = variables[3]
    data = db.reference(db_path).order_by_key().start_at(start).end_at(end).get()
    if len(variables) > 4:
        n = int(variables[4])
        data = db.reference(db_path).order_by_key().start_at(start).end_at(end).limit_to_last(n).get()
    else:
        data = db.reference(db_path).order_by_key().start_at(start).end_at(end).get()

    return jsonify(data)

@app.route('/drone')
def drone_list():
    data = db.reference('/LH_Farm/drone').get()
    keys = list(data.keys())
    keys.sort(key=str.lower)
    return render_template('drone_list.html', keys=keys)

@app.route('/drone/'+'<drone_id>')
def drone(drone_id):
    return render_template('drone.html', id=drone_id)

@app.route('/history')
def history():
    with open('static/json/farm_features.json', 'r') as file:
        data = file.read()
    
    return render_template('history.html', data=data)




if __name__ == "__main__":
    # scheduler = APScheduler()
    # scheduler.add_job(func=update_overview, trigger='interval', id='job', seconds=60)
    # scheduler.start()
    app.run(debug=True)

