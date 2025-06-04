from __future__ import absolute_import, unicode_literals


from celery import shared_task, Task
import time
import random
from celery import Celery
from celery.schedules import crontab
from asgiref.sync import async_to_sync, sync_to_async
import channels.layers
import requests
import os
from opcua import *
from django.apps import apps
from datetime import datetime, timedelta
import random
import string
import math
import pytz
from zoneinfo import ZoneInfo
from django.utils import timezone
from .utils import request_to_shelly_cloud, create_periodic_task_against_session, send_co2_and_khw_data_to_socket, \
		send_websocket_data_to_particular_session, disable_a_periodic_task_for_session, disable_all_periodic_task_for_a_session
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from .models import *
import certifi
import urllib3

User = get_user_model()


channel_layer = get_channel_layer()

timezone.activate(ZoneInfo("Europe/London"))


@shared_task
def request_to_shelly_cloud_task():
	AUTH_KEY = os.environ.get('AUTH_KEY')
	s = requests.post('https://shelly-43-eu.shelly.cloud/device/all_status', data={'auth_key':AUTH_KEY})

	try:
		receivedData = s.json() #converting received response into json structure
	except JSONDecodeError:
		print("Failed request! (JSON DECODE ERROR)")
		receivedData= {}

	return receivedData


@shared_task
def Master_Scheduler_Station(id):
	Station = apps.get_model(app_label='EnergyCapture', model_name='Station')
	PowerClamp = apps.get_model(app_label='EnergyCapture', model_name='PowerClamp')
	Company = apps.get_model(app_label='Main', model_name='Company')
	company = Company.objects.first()
	station = Station.objects.get(id=id)
	drilldown = company.json

	total = 0
	grandTotal = 0
	if drilldown:
		for equipment in station.equipment_set.all():
			for clamp in equipment.powerclamp_set.all():
				if clamp.deviceID in drilldown.keys():
					clamp.powerclamptime_set.create(power=drilldown[clamp.deviceID]['total_power'], time=timezone.localtime(timezone.now()))
					total+=drilldown[clamp.deviceID]['total_power']
				else:
					rand = random.randint(54,743)
					clamp.powerclamptime_set.create(power=rand, time=timezone.localtime(timezone.now()))
					total+=rand

			equipment.equipmenttime_set.create(power=total, time=timezone.localtime(timezone.now()))
			grandTotal += total
			total = 0
		station.stationtime_set.create(power=grandTotal, time=timezone.localtime(timezone.now()))
		print("success")
			

	else:
		print("fail")
		station.stationtime_set.create(power=0,time=timezone.localtime(timezone.now()))
		for equipment in station.equipment_set.all():
			equipment.equipmenttime_set.create(power=0, time=timezone.localtime(timezone.now()))
			for clamp in equipment.powerclamp_set.all():
				clamp.powerclamptime_set.create(power=0, time=timezone.localtime(timezone.now()))

@shared_task
def Master_Company_Scheduler():
	Company = apps.get_model(app_label='Main', model_name='Company')
	company = Company.objects.first()

	total = 0
	for station in company.station_set.all():
		total += station.stationtime_set.last().power

	company.companytime_set.create(power=total, time=timezone.localtime(timezone.now()))



@shared_task(task_ignore_result = True)
def Schedule():

	s = requests.post('https://shelly-43-eu.shelly.cloud/device/all_status', data={'auth_key':os.environ.get('AUTH_KEY')})
	try:
		receivedData = s.json() #converting received response into json structure
	except JSONDecodeError:
		print("Failed request! (JSON DECODE ERROR)")
		receivedData= {}
		drilldown = {}
	PossibleDeviceID = apps.get_model(app_label='EnergyCapture', model_name='PossibleDeviceID')

	try:
		drilldown=receivedData['data']['devices_status']
	except KeyError:
		print("Failed request (JSON KEY ERROR)!")
		drilldown = {}
		
	Company = apps.get_model(app_label='Main', model_name='Company')
	company = Company.objects.first()
	company.json = drilldown
	company.save()

	if drilldown:
		for temp in drilldown.keys():
	 		PossibleDeviceID.objects.get_or_create(deviceID=temp)

@shared_task(task_ignore_result = True)
def PostData(equipment): #Post data to powerClamp page
	channel_layer = channels.layers.get_channel_layer() #get channel layer form redis so we can get rooms
	data, labels, times =[],[],[]
	total_power=0
	postData = {}
	Equipment = apps.get_model(app_label='EnergyCapture', model_name='Equipment') #Equipment model
	equipment = Equipment.objects.get(id=equipment) #equipment ID specified on creation of this periodic task, so this task will always be related to the channel room 
	for powerClamp in equipment.powerclamp_set.all():
		data.append(float(powerClamp.powerclamptime_set.last().power))
		labels.append(powerClamp.name)
		times.append(float(math.trunc(datetime.timestamp(powerClamp.powerclamptime_set.last().time)*1000))) #grab latest power data and timestamp

	postData = {'data':data, 'labels':labels, 'times':times}

	async_to_sync(channel_layer.group_send)('EnergyCapture_addPowerClamps'+str(equipment.id), {'type':"graph_message", "message":postData}) #throw data to django channel room directly related to this task

@shared_task(task_ignore_result = True)
def PostData_Equipment(station): #Post data to equipment page
	channel_layer = channels.layers.get_channel_layer() #getting channel layer from redis so we can get rooms
	data, labels, times =[],[],[]
	total_power=0
	postData = {}
	Station = apps.get_model(app_label='EnergyCapture', model_name='Station') #Get station model
	station = Station.objects.get(id=station) #got our station now as this task can only be created with station ID specified
	for equipment in station.equipment_set.all():
		data.append(float(equipment.equipmenttime_set.last().power)) #get latest power and time stamp, then throw to django channel room
		labels.append(equipment.name)
		times.append(float(math.trunc(datetime.timestamp(equipment.equipmenttime_set.last().time)*1000)))

	postData = {'data':data, 'labels':labels, 'times':times}

	async_to_sync(channel_layer.group_send)('EnergyCapture_addEquipment'+str(station.id), {'type':"graph_message", "message":postData}) #beautiful code that sends our data straight to channel room



@shared_task(task_ignore_result = True)
def PostData_Station(company): #Post data to setup overview page
	channel_layer = channels.layers.get_channel_layer()  #getting channel layer from redis so we can get rooms
	data, labels, times =[],[],[]
	total_power=0
	
	CO2 = []
	postData = {}
	Company = apps.get_model(app_label='Main', model_name='Company') #get company model
	company = Company.objects.get(id=company)
	CO2PerKWH= company.co2_choice #we got company so we can get CO2 choice for kg co2e
	for station in company.station_set.all():
		data.append(float(station.stationtime_set.last().power))
		CO2.append((float(station.stationtime_set.last().power)/1000) * float(CO2PerKWH)) #getting kg CO2e and timestamp (latest)
		labels.append(station.name+str(" (Wh)"))
		times.append(float(math.trunc(datetime.timestamp(station.stationtime_set.last().time)*1000)))


	postData = {'data':data, 'labels':labels, 'times':times, 'CO2':CO2}

	async_to_sync(channel_layer.group_send)('EnergyCapture_addStation', {'type':"graph_message", "message":postData}) #throwing data to our channel room and into graph

@shared_task(task_ignore_result = True)
def PostData_Dashboard(company): #Post data to dashboard overview page
	channel_layer = channels.layers.get_channel_layer() #redis channel layer for rooms
	data, labels, times =[],[],[]
	total_power=0
	CO2 = []
	postData = {}
	Company = apps.get_model(app_label='Main', model_name='Company')
	company = Company.objects.get(id=company) #company specified on this periodic task creation (See equipment setup page view for details)
	CO2PerKWH = company.co2_choice
	total_power = company.total_power
	total_CO2 = company.total_power * float(CO2PerKWH)  #getting latest total kwh/co2 #TODO: Kind of redundant now but could be implemented in future, review nathan
	for station in company.station_set.all():
		data.append(float(station.stationtime_set.last().power)/1000) #CO2, timestamps etc to be thrown into channel room
		CO2.append((float(station.stationtime_set.last().power)/1000) *float(CO2PerKWH))
		labels.append(station.name+str(" (kWh)"))
		times.append(float(math.trunc(datetime.timestamp(station.stationtime_set.last().time)*1000)))


	postData = {'data':data, 'labels':labels, 'times':times, 'CO2':CO2, 'total_power':total_power, 'total_CO2':total_CO2}
	return postData
	async_to_sync(channel_layer.group_send)('EnergyCapture_energyCaptureDashboard', {'type':"graph_message", "message":postData}) #data launched into room and into graph (magic)

@shared_task(task_ignore_result = True)
def PostData_Dashboard_Station_Level(station): #Post data to Dashboard station page
	channel_layer = channels.layers.get_channel_layer() #Redis channel layer with rooms - basically a database exists within redis that stores the rooms we create with the daphne on-connect django channels function
	data, labels, times =[],[],[]
	total_power=0
	CO2 = []
	
	postData = {}
	Station = apps.get_model(app_label='EnergyCapture', model_name='Station') #station with "station" ID that we specify when creating this periodic task
	station = Station.objects.get(id=station)
	CO2PerKWH= station.company.co2_choice
	total_power = station.total_power #REDUNDANT PROBABLY REVIEW NUTHON
	total_CO2 = station.total_power * float(CO2PerKWH)
	for equipment in station.equipment_set.all():
		data.append(float(equipment.equipmenttime_set.last().power)/1000)
		CO2.append((float(equipment.equipmenttime_set.last().power)/1000) *float(CO2PerKWH))
		labels.append(equipment.name+str(" (kWh)"))
		times.append(float(math.trunc(datetime.timestamp(equipment.equipmenttime_set.last().time)*1000))) #Data with timestamp to be launched


	postData = {'data':data, 'labels':labels, 'times':times, 'CO2':CO2, 'total_power':total_power, 'total_CO2':total_CO2}

	async_to_sync(channel_layer.group_send)('EnergyCapture_stationDashboard'+str(station.id), {'type':"graph_message", "message":postData}) #Low orbit ion cannoned into station dashboard page with specified ID 

@shared_task(task_ignore_result = True)
def PostData_Dashboard_Equipment_Level(equipment): #Post data to Equipmetn dashboard page
	channel_layer = channels.layers.get_channel_layer() #Redis channel layer with rooms
	data, labels, times =[],[],[]
	total_power=0
	CO2 = []
	postData = {}
	Equipment = apps.get_model(app_label='EnergyCapture', model_name='Equipment')
	equipment = Equipment.objects.get(id=equipment)
	CO2PerKWH = equipment.station.company.co2_choice #CO2 per KWH from company object
	total_power = equipment.total_power #redundantly reminding myself that this is redundant
	total_CO2 = equipment.total_power * float(CO2PerKWH)
	for clamp in equipment.powerclamp_set.all():
		data.append(float(clamp.powerclamptime_set.last().power)/1000) #Data to be launched
		CO2.append((float(clamp.powerclamptime_set.last().power)/1000) *float(CO2PerKWH))
		labels.append(clamp.name+str(" (kWh)"))
		times.append(float(math.trunc(datetime.timestamp(clamp.powerclamptime_set.last().time)*1000)))


	postData = {'data':data, 'labels':labels, 'times':times, 'CO2':CO2, 'total_power':total_power, 'total_CO2':total_CO2}

	async_to_sync(channel_layer.group_send)('EnergyCapture_equipmentDashboard'+str(equipment.id), {'type':"graph_message", "message":postData}) #Data given to equipment dashboard page to populate real time graph (epic)

@shared_task()
def object_listener():
	Process = apps.get_model(app_label='Main', model_name='Process')
	p = Process.objects.first()

	if not p.CO2 == p.cached_CO2:
		p.cached_CO2=p.CO2 
		p.save()
		print("updated!")


@shared_task
def send_co2_and_khw_data_to_socket_task(session_key, device_id):
	return send_co2_and_khw_data_to_socket(session_key, device_id)

@shared_task
def create_periodic_task_against_session_task(session_key, device_id):
	return create_periodic_task_against_session(session_key=session_key, device_id=device_id)


@shared_task
def grab_energy_station_task(session_key):
	try:
		session_obj = Session.objects.get(session_key=session_key)
	except ObjectDoesNotExist:
		return disable_a_periodic_task_for_session(session_key)

	now = timezone.now()
	if now > session_obj.expire_date:
		return disable_a_periodic_task_for_session(session_obj)

	session_data = session_obj.get_decoded()
	user_id = session_data.get("_auth_user_id")

	try:
		user = User.objects.get(id=user_id)
	except ObjectDoesNotExist:
		return disable_a_periodic_task_for_session(session_obj)

	if user.is_authenticated:
		energy = True
		if user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group
			
			data, initialData, masterData, labels, times =[],[],[],[],[]
			duration = user.profile.duration_energy
			endDate = timezone.now()
			startDate = endDate - datetime.timedelta(minutes=30)#Set startDate to (endDate - user specified time frame)
			count = 0
			print(startDate)
			print(endDate)
			if user.profile.user_company.station_set.all():
				for station in user.profile.user_company.station_set.all():
					initialData = []
					if station.stationtime_set.all():
						labels.append(station.name+str(" (kWh)"))
						qs = station.stationtime_set.all().filter(time__gte=startDate, time__lte=endDate)
						print(qs)
						if qs.exists():
							for each in qs:
								initialData.append(
								{'x':math.trunc(datetime.datetime.timestamp(each.time)*1000),'y': float(each.power/1000)}
							) #Set to {'x': ..., 'y': ...} for compatibilty with Chart JS V3.9.1 format

							masterData.insert(count, initialData) #insert into correct index
							count+=1
		
			print(len(masterData))
			print("Returning Json Response")
			data = {'data':data, 'labels':labels, 'times':times, 'masterData':masterData, 'duration':float(duration)}
			print("data", data)
			return send_websocket_data_to_particular_session(session_obj=session_obj, data=data)
		else:
			return None
	else:
		return None



@shared_task
def send_power_data_to_websocket(session_key, device_id):
	try:
		session_obj = Session.objects.get(session_key=session_key)
	except ObjectDoesNotExist:
		disable_all_periodic_task_for_a_session(session_obj)
		return None

	now = timezone.now()
	# use expire date of session to configure for sending
	if now > session_obj.expire_date:
		disable_all_periodic_task_for_a_session(session_obj)
		return None

	data = request_to_shelly_cloud()
	if data == {}:
		return None

	device_data = data["data"]["devices_status"].get(device_id, None)
	if device_data is None:
		return None

	total_power = device_data.get("total_power", None)
	if total_power is None:
		return None

	ws_data = {
		"command": "kwh graph",
		"power": float(total_power),
	}

	return send_websocket_data_to_particular_session(session_obj, ws_data)


@shared_task
def add_data_to_station_task():
	data = request_to_shelly_cloud()
	total_power = 0
	devices_data = data["data"]["devices_status"]
	for device_id in devices_data.keys():
		device = devices_data[device_id]
		power = device["total_power"]
		total_power += power

	users = User.objects.all()
	for user in users:
		print(user)
		try:
			company = user.profile.user_company
		except ObjectDoesNotExist:
			continue

		if company is None:
			print("Company is None for ", user)
			continue

		station = company.station_set.last()
		if station is None:
			continue
		station_time_obj = station.stationtime_set.create(power=total_power)
		print("Created station time")

	return True


@shared_task
def add_power_clamp_time_task():
	power_clamp_qs = PowerClamp.objects.all()
	data = request_to_shelly_cloud()
	devices_data = data["data"]["devices_status"]
	for device_id in devices_data:
		dev_data = devices_data.get(device_id)
		total_power = dev_data["total_power"]
		try:
			power_clamp_obj = PowerClamp.objects.get(deviceID=device_id)
		except ObjectDoesNotExist:
			continue
		
		power_clamp_obj.powerclamptime_set.create(power=total_power)

# @shared_task
# def opc_test():
# 	try:
# 		client = Client("opc.tcp://192.168.0.2:4840")

# 		client.connect()
# 		print("sucess")

# 		# node = client.get_node('ns=3;s="tensionHomeSW"')

# 		# value = node.get_value()

# 		# Sensor = apps.get_model(app_label='Main', model_name='Sensor')
# 		# sensor = Sensor.objects.get(id=3)
# 		# sensor.posCheck = value

# 		# if value:
# 		# 	sensor.status = 2
# 		# else:
# 		# 	sensor.status = 3

# 		# print(sensor.status)
# 		# sensor.save()
		
# 	finally:
# 		client.disconnect()