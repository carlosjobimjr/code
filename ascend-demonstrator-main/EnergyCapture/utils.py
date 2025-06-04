import os
import requests
import json
import secrets
from asgiref.sync import async_to_sync, sync_to_async
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from channels.layers import get_channel_layer


channel_layer = get_channel_layer()

def request_to_shelly_cloud():
	AUTH_KEY = os.environ.get('AUTH_KEY')
	s = requests.post('https://shelly-43-eu.shelly.cloud/device/all_status', data={'auth_key':AUTH_KEY}, verify=False)

	try:
		receivedData = s.json() #converting received response into json structure
	except JSONDecodeError:
		print("Failed request! (JSON DECODE ERROR)")
		receivedData= {}

	return receivedData


def create_periodic_task_against_session(session_key, device_id):
	data = request_to_shelly_cloud()
	if data == {}:
		return None

	try:
		session_obj = Session.objects.get(session_key=session_key)
	except ObjectDoesNotExist:
		return None

	# create periodic task
	# 		1. Kilowats per hour in 2 mins interval
	# 		2. Kilogram CO2 emitted per hour in 2 mins interval

	now = timezone.now()
	schedule, created = IntervalSchedule.objects.get_or_create(
		every=10,
		period=IntervalSchedule.SECONDS
	)

	previous_task_qs = PeriodicTask.objects.filter(
		name__istartswith=f"send-khw-data-to-socket-{session_key}-",
	)
	previous_task_qs.update(enabled=False)

	task = PeriodicTask.objects.create(
		interval=schedule,
		name=f"send-khw-data-to-socket-{session_key}-{secrets.token_hex(4)}",
		task="EnergyCapture.tasks.send_power_data_to_websocket",
		kwargs=json.dumps({
			"session_key": session_key,
			"device_id": device_id,
		})
	)

	return True


def send_websocket_data_to_particular_session(session_obj, data):
	room_name = f"room_{session_obj.session_key}"
	async_to_sync(get_channel_layer().group_send)(room_name, {"type": "send.message", "text": data,})
	print("Message sent")
	return True


def send_co2_and_khw_data_to_socket(session_key, device_id):
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

	room_name = f"room_{session_key}"
	print("ROOM NAME ", room_name)


	async_to_sync(get_channel_layer().group_send)(room_name, {"type": "send.message", "text": device_data,})

	print("Message sent to consumer")


def disable_all_periodic_task_for_a_session(session_obj: Session):
	if isinstance(session_obj, str):
		session_key = session_obj

	elif isinstance(session_obj, Session):
		session_key = session_obj.session_key

	else:
		return False

	print("Disabling all periodic task for a session")
	periodic_task_qs = PeriodicTask.objects.filter(name__icontains=f"{session_obj.session_key}")
	periodic_task_qs.update(enabled=False)
	return periodic_task_qs


def disable_a_periodic_task_for_session(session_obj, name__startswith):
	if isinstance(session_obj, str):
		session_key = session_obj

	elif isinstance(session_obj, Session):
		session_key = session_obj.session_key

	else:
		return False


	qs = PeriodicTask.objects.filter(name__istartswith=f"{name__startswith}-{session_key}")
	qs.update(enabled=False)
	return qs


@sync_to_async
def get_device_data(device_id):
	data = request_to_shelly_cloud()
	if data == {}:
		return None

	device_data = data["data"]["devices_status"][device_id]
	return device_data


def convert_from_power_to_co2_with_co2_choices(power, company):
	CO2PerKWH = company.co2_choice
	CO2 = (float(power/1000) * float(CO2PerKWH))
	return CO2


def get_co2_emission_in_per_hour_time(user):
	company = user.profile.user_company
	station = company.station_set.first()
	now = timezone.now()

	station_time_qs = station.stationtime_set.filter(time__date=now.date()).order_by("time")
	station_time_data = list(station_time_qs.values())

	today_hour = now.time().hour
	
	x_axis_data = []
	y_axis_data = []
	for hour in range(1, today_hour+1):
		for data in station_time_data:
			time = data["time"]
			if time.time().hour == hour:
				y_axis_data.append(convert_from_power_to_co2_with_co2_choices(data.get("power", 0), company))
				x_axis_data.append(hour)

	return x_axis_data, y_axis_data


def get_kwh_in_per_hour_time(user):
	company = user.profile.user_company
	station = company.station_set.first()
	now = timezone.now()

	station_time_qs = station.stationtime_set.filter(time__date=now.date()).order_by("time")
	station_time_data = list(station_time_qs.values())

	today_hour = now.time().hour
	
	x_axis_data = []
	y_axis_data = []
	for hour in range(1, today_hour+1):
		for data in station_time_data:
			time = data["time"]
			if time.time().hour == hour:
				y_axis_data.append(float(data.get("power", 0)))
				x_axis_data.append(hour)

	return x_axis_data, y_axis_data
