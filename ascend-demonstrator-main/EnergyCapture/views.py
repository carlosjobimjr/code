from .models import *
from .forms import *
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
import random
import requests
from django.contrib import messages
import os, environ
import calendar
import time
import datetime
import math
import json
from django.shortcuts import render,redirect
from django_celery_beat.models import PeriodicTasks, PeriodicTask, IntervalSchedule
import math
import pytz
from decimal import Decimal
from dateutil.parser import isoparse
from django.utils import timezone
from .tasks import create_periodic_task_against_session_task
from .utils import get_co2_emission_in_per_hour_time, get_kwh_in_per_hour_time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import jwt
from django.views.decorators.http import require_GET
import logging

from django.contrib.auth.decorators import login_required
from zoneinfo import ZoneInfo

#Proportion used for conversion of profile attribute (duration_energy) into step size for graphs (Defines the gaps between x-axis metrics)
proportion = {'0.060': 6, '0.300':60, '3.600':600, '86.400':3600, '604.800':7200, '31556.952':31536000, '259.200':86400, '999999.999':86400, '1337.012':3600}



import logging
import requests
import jwt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

@csrf_exempt
@require_GET
def oauth_callback(request):
    # Get the authorization code from the request
    code = request.GET.get('code')
    
    if not code:
        logger.error("No authorization code received")
        return JsonResponse({'error': 'No authorization code provided'}, status=400)

    # Define your client ID and redirect URI
    client_id = "shelly-diy"
    redirect_uri = "http://10.10.42.125:8000/oauth/callback/"
    
    # Decode the JWT to extract user API URL
    try:
        decoded = jwt.decode(code, options={"verify_signature": False})
        user_api_url = decoded.get('user_api_url', 'https://shelly-43-eu.shelly.cloud')
    except Exception as e:
        logger.error(f"Error decoding JWT: {e}")
        user_api_url = 'https://shelly-43-eu.shelly.cloud'
    
    # Prepare the token exchange request
    token_exchange_url = f"{user_api_url}/auth/exchange_code"
    
    try:
        # Exchange code for access token
        response = requests.post(token_exchange_url, json={
            'code': code,
            'client_id': client_id,
        })
        
        logger.info(f"Token exchange response status: {response.status_code}")
        logger.info(f"Token exchange response content: {response.text}")
        
        # Parse the response
        response_data = response.json()
        
        # Check if token exchange was successful
        if response_data.get('isok', False):
            access_token = response_data.get('data', {}).get('token')
            
            if access_token:
                logger.info("Successfully retrieved access token")
                return JsonResponse({
                    'access_token': access_token,
                    'user_api_url': user_api_url
                })
            else:
                logger.error("No token found in response")
                return JsonResponse({'error': 'No access token in response'}, status=400)
        else:
            logger.error(f"Token exchange failed: {response_data}")
            return JsonResponse({
                'error': 'Token exchange unsuccessful',
                'details': response_data
            }, status=400)
    
    except requests.RequestException as e:
        logger.exception("Network error during token exchange")
        return JsonResponse({'error': 'Network error occurred', 'details': str(e)}, status=500)
    except Exception as e:
        logger.exception("Unexpected error during OAuth callback")
        return JsonResponse({'error': 'Unexpected error', 'details': str(e)}, status=500)



																		#----SETUP VIEWS-----#
#########################################################################################################################################################################
#########################################################################################################################################################################

def get_added_clamps(request):
    clamps = list(PowerClamp.objects.values('name', 'deviceID'))
    
    for clamp in clamps:
        clamp['deviceID'] = clamp['deviceID'].lower()  # Ensure lowercase for comparison
    
    return JsonResponse({'clamps': clamps})

def addPowerClamps(response, id):
	if response.user.is_authenticated: #If user is logged in
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #if user has the "Energy" Group
			equipment = Equipment.objects.get(id=id)
			powerClamps = equipment.powerclamp_set.all()
			
			devices=PossibleDeviceID.objects.all() #Possible device IDs are created from JSON from cloud
			
			#Add and deletion form for power clamps
			addForm = AddPowerClampForm(devices)
			delForm = DeletePowerClampForm(powerClamps)

			if response.method == 'POST': #If user submits a form
				user = response.user.profile #getting profile 
				#If user submits add form
				if 'add' in response.POST:
					addForm = AddPowerClampForm(devices, response.POST)
					if addForm.is_valid():
						name = addForm.cleaned_data['name']
						deviceID = addForm.cleaned_data['deviceID']

						if PowerClamp.objects.filter(deviceID=deviceID).exists(): #if Device ID already assigned to power clamp
							print('Power clamp already exists! It may be assigned to another piece of equipment.')
						elif PowerClamp.objects.filter(name=name).exists(): #If Power Clamp Name exists already
							print('Choose a different name!')
						else: #Otherwise, create power clamp
							powerClamp = equipment.powerclamp_set.create(name=name, deviceID=deviceID)
							powerClamp.save()

						create_periodic_task_against_session_task.delay(response.session.session_key, deviceID)
						print("CREATED PERIODIC TASKS")
							
				#If user submits delete form
				elif 'delete' in response.POST:
					delForm = DeletePowerClampForm(powerClamps, response.POST)
					if delForm.is_valid():
						powerClamp = delForm.cleaned_data['name'] #Get powerclamp from drop down list (Avoids condition checking because of model choice field)
						powerClamp.delete()
			powerClamps = PowerClamp.objects.all()
			return render(response, 'EnergyCapture/addPowerClamps.html', {'addForm':addForm, 'delForm':delForm, 'powerClamps':powerClamps, 'equipment':equipment})
		else:
			return redirect('/')
	else:
		return redirect('/')

def addStation(response):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group

			#Add,Delete,CO2 forms initialised
			addForm = AddStationForm()
			delForm = DeleteStationForm(response.user.profile.user_company.station_set.all())
			co2Form = ChooseCO2Form()
			if response.method == "POST":
				#if user submits add form
				if 'add' in response.POST:
					addForm = AddStationForm(response.POST)
					if addForm.is_valid():
						stationName = addForm.cleaned_data['name']
						if not response.user.profile.user_company.station_set.filter(name=stationName).exists():
							response.user.profile.user_company.station_set.create(name=stationName)
							messages.success(response, "Station created!")
						else:
							messages.error(response, "Station already exists!")
				#if user submits delete form
				if 'delete' in response.POST:
					delForm = DeleteStationForm(Station.objects.all(), response.POST)
					if delForm.is_valid():
						station = delForm.cleaned_data['station']
						if response.user.profile.user_company.station_set.filter(name=station.name).exists():
							station.delete()
							messages.success(response, "Station deleted!")
						else:
							messages.error("response", "Station does not exist!")

				#if user submits co2 form
				if 'co2'in response.POST:
					co2Form = ChooseCO2Form(response.POST)
					if co2Form.is_valid():
						name = co2Form.cleaned_data['name']
						if CO2.objects.all().filter(name=name, company=response.user.profile.user_company).exists():
							co2_object = CO2.objects.all().get(name=name, company=response.user.profile.user_company)
						else:
							#setting CO2 metrics to multiply by kWh for kg CO2e
							if name == 'Scope 2':
								value = 0.19121
							elif name == 'Scope 3 (Generation)':
								value = 0.04625
							elif name == 'Scope 3 (Transmission and Distribution':
								value = 0.00423
							elif name == 'Total':
								value = 0.24169
							co2_object = CO2.objects.create(name=name, value=value, company=response.user.profile.user_company) #Create CO2 objects
						company = response.user.profile.user_company 
						company.co2_choice = co2_object.value #CO2 choice assigned to company
						company.save()
						messages.success(response, "CO2 factor changed")

			return render(response, 'EnergyCapture/addStation.html', {'stations':Station.objects.all(), 'addForm':addForm, 'delForm':delForm, 'co2Form':co2Form})
		else:
			return redirect('/')
	else:
		return redirect('/')

def addEquipment(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			station = Station.objects.get(id=id)
			company= response.user.profile.user_company
			addForm = AddEquipmentForm()
			delForm = DeleteEquipmentForm(station.equipment_set.all())
			if response.method == "POST":
				if 'add' in response.POST:
					addForm = AddEquipmentForm(response.POST)
					if addForm.is_valid():
						equipmentName = addForm.cleaned_data['name']
						if not station.equipment_set.filter(name=equipmentName).exists():
							schedule, created = IntervalSchedule.objects.get_or_create(every=1000000, period=IntervalSchedule.MICROSECONDS)
							equipment = station.equipment_set.create(name=equipmentName)
							pt = PeriodicTask.objects.create(interval=schedule, name="EnergyCapture_addPowerClamps"+str(equipment.id), task ="EnergyCapture.tasks.PostData", 
								args=json.dumps([equipment.id]))
							pt.enabled = False 
							pt.save()

							if not PeriodicTask.objects.filter(name="EnergyCapture_addEquipment"+str(station.id)).exists():
								ePT = PeriodicTask.objects.create(interval=schedule, name="EnergyCapture_addEquipment"+str(station.id), task="EnergyCapture.tasks.PostData_Equipment", args=json.dumps([station.id]))
								ePT.enabled = False 
								ePT.save()

							if not PeriodicTask.objects.filter(name="EnergyCapture_addStation").exists():
								sPT = PeriodicTask.objects.create(interval=schedule, name="EnergyCapture_addStation", task="EnergyCapture.tasks.PostData_Station", args=json.dumps([company.id]))
								sPT.enabled = False 
								sPT.save()

							if not PeriodicTask.objects.filter(name="EnergyCapture_energyCaptureDashboard").exists():
								zPT = PeriodicTask.objects.create(interval=schedule, name="EnergyCapture_energyCaptureDashboard", task="EnergyCapture.tasks.PostData_Dashboard", args=json.dumps([company.id]))
								zPT.enabled = False 
								zPT.save()

							if not PeriodicTask.objects.filter(name="EnergyCapture_stationDashboard"+str(station.id)).exists():
								xPT = PeriodicTask.objects.create(interval=schedule, name="EnergyCapture_stationDashboard"+str(station.id), task="EnergyCapture.tasks.PostData_Dashboard_Station_Level", args=json.dumps([station.id]))
								xPT.enabled = False 
								xPT.save()

								schedule, created = IntervalSchedule.objects.get_or_create(every=3000000, period=IntervalSchedule.MICROSECONDS)
								Master_XPT = PeriodicTask.objects.create(interval=schedule, name = "Master_Schedule_Station"+str(station.id), task="EnergyCapture.tasks.Master_Scheduler_Station", args=json.dumps([station.id]))




							if not PeriodicTask.objects.filter(name="EnergyCapture_equipmentDashboard"+str(equipment.id)).exists():
								lPT = PeriodicTask.objects.create(interval=schedule, name="EnergyCapture_equipmentDashboard"+str(equipment.id), task="EnergyCapture.tasks.PostData_Dashboard_Equipment_Level", args=json.dumps([equipment.id]))
								lPT.enabled = False 
								lPT.save()

							schedule, created = IntervalSchedule.objects.get_or_create(every=2000000, period=IntervalSchedule.MICROSECONDS)

							if not PeriodicTask.objects.filter(name="Scheduler_Requests").exists():
								masterPT = PeriodicTask.objects.create(interval=schedule, name="Scheduler_Requests", task="EnergyCapture.tasks.Schedule")
								messages.success(response, "Equipment created!")
								schedule, created = IntervalSchedule.objects.get_or_create(every=3000000, period=IntervalSchedule.MICROSECONDS)
								masterCompany = PeriodicTask.objects.create(interval=schedule, name="Master_Company_Scheduler", task="EnergyCapture.tasks.Master_Company_Scheduler")
						else:
							messages.error(response, "Equipment already exists!")
				if 'delete' in response.POST:
					delForm = DeleteEquipmentForm(station.equipment_set.all(), response.POST)

					if delForm.is_valid():
						equipment = delForm.cleaned_data['equipment']
						if station.equipment_set.all().filter(name=equipment.name).exists():
							equipment.delete()
							messages.success(response, "Equipment deleted!")
						else:
							messages.error("response", "Equipment does not exist!")

			return render(response, 'EnergyCapture/addEquipment.html', {'station':station, 'addForm':addForm, 'delForm':delForm})
		else:
			return redirect('/')
	else:
		return redirect('/')

#########################################################################################################################################################################
#########################################################################################################################################################################
																		#----SETUP VIEWS END-----#







																		#----SETUP GRAPHS START-----#
#########################################################################################################################################################################
#########################################################################################################################################################################

def grabEnergy_PowerClamp(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group
			data, initialData, masterData, labels, times =[],[],[],[],[]
			duration = response.user.profile.duration_energy #Duration is user specified metric for time frame
			count = 0
			equipment = Equipment.objects.get(id=id)
			endDate = datetime.datetime.now()
			startDate = endDate - datetime.timedelta(seconds=float(duration)*1000+10) #Set startDate to (endDate - user specified time frame)

			if equipment.powerclamp_set.all():
				for powerClamp in equipment.powerclamp_set.all():
					initialData = []
					labels.append(powerClamp.name+str(" (kWh)"))
					if powerClamp.powerclamptime_set.last():
						time_inner = powerClamp.powerclamptime_set.last().time
					else:
						time_inner = timezone.now()
					times.append(math.trunc(datetime.datetime.timestamp(time_inner)*1000)) #Set time as a timestamp because it is more compatible with Chart JS V3.9.1
				
					for each in powerClamp.powerclamptime_set.all().filter(time__gte=startDate, time__lte=endDate):
						initialData.append({'x':math.trunc(datetime.datetime.timestamp(each.time)*1000),'y':each.power/1000}) #Set to {'x': ..., 'y': ...} for compatibilty with Chart JS V3.9.1 format
					masterData.insert(count, initialData) #insert into correct index
					count+=1

			return JsonResponse(data={'data':data, 'labels':labels, 'times':times, 'masterData':masterData, 'duration':duration})
		else:
			return redirect('/')
	else:
		return redirect('/')

def grabEnergy_Equipment(response,id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group
			data, initialData, masterData, labels, times =[],[],[],[],[]
			duration = response.user.profile.duration_energy
			count = 0
			station = Station.objects.get(id=id)
			endDate = datetime.datetime.now()
			startDate = endDate - datetime.timedelta(seconds=float(duration)*1000+10) #Set startDate to (endDate - user specified time frame)

			if station.equipment_set.all():
				for equipment in station.equipment_set.all():
					initialData = []
					labels.append(equipment.name+str(" (kWh)"))
					times.append(math.trunc(datetime.datetime.timestamp(equipment.equipmenttime_set.last().time)*1000)) #Set time as a timestamp because it is more compatible with Chart JS V3.9.1

					qs = equipment.equipmenttime_set.all().filter(time__gte=startDate, time__lte=endDate)
					for each in qs:
						initialData.append({'x':math.trunc(datetime.datetime.timestamp(each.time)*1000),'y':each.power/1000}) #Set to {'x': ..., 'y': ...} for compatibilty with Chart JS V3.9.1 format
					
					masterData.insert(count, initialData) #insert into correct index
					count+=1

			return JsonResponse(data={'data':data, 'labels':labels, 'times':times, 'masterData':masterData, 'duration':duration})
		else:
			return redirect('/')
	else:
		return redirect('/')

def grabEnergy_Station(response):
	if response.user.is_authenticated:
		energy = True
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group
			
			data, initialData, masterData, labels, times =[],[],[],[],[]
			duration = response.user.profile.duration_energy
			endDate = timezone.now()
			startDate = endDate - datetime.timedelta(minutes=30)#Set startDate to (endDate - user specified time frame)
			count = 0
			print("Start date", startDate)
			print("End Date", endDate)
			if response.user.profile.user_company.station_set.all():
				for station in response.user.profile.user_company.station_set.all():
					initialData = []
					if station.stationtime_set.all():
						labels.append(station.name+str(" (kWh)"))
						station_time_qs = station.stationtime_set.all().filter(time__gte=startDate, time__lte=endDate)
						if station_time_qs.exists():
							for each in station_time_qs:
								initialData.append({'x':math.trunc(datetime.datetime.timestamp(each.time)*1000),'y':each.power/1000}) #Set to {'x': ..., 'y': ...} for compatibilty with Chart JS V3.9.1 format
							masterData.insert(count, initialData) #insert into correct index
							count+=1
		

			data = {'data':data, 'labels':labels, 'times':times, 'masterData':masterData, 'duration':duration}
			print(data)
			return JsonResponse(data=data)
		else:
			return redirect('/')
	else:
		return redirect('/')

def grabCO2_Station(response):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			data, initialData, masterData, labels, times =[],[],[],[],[]
			duration = response.user.profile.duration_energy
			count = 0
			CO2perKWH = float(response.user.profile.user_company.co2_choice) #Company co2 factor
			endDate = datetime.datetime.now()
			startDate = endDate - datetime.timedelta(seconds=float(duration)*1000+10)

			if response.user.profile.user_company.station_set.all():
				for station in response.user.profile.user_company.station_set.all():
					initialData = []

					labels.append(station.name+str(" (kg CO2e Per Hour)"))
					times.append(math.trunc(datetime.datetime.timestamp(station.stationtime_set.last().time)*1000))#Set time as a timestamp because it is more compatible with Chart JS V3.9.1

					for each in station.stationtime_set.all().filter(time__gte=startDate, time__lte=endDate):
						initialData.append({'x':math.trunc(datetime.datetime.timestamp(each.time)*1000),'y':(float(each.power)/1000)*CO2perKWH}) #Set to {'x': ..., 'y': ...} for compatibilty with Chart JS V3.9.1 format
					masterData.insert(count, initialData)
					count+=1
				

			return JsonResponse(data={'data':data, 'labels':labels, 'times':times, 'masterData':masterData, 'duration':duration})
		else:
			return redirect('/')
	else:
		return redirect('/')

#########################################################################################################################################################################
#########################################################################################################################################################################
																		#----SETUP GRAPHS END-----#







																		#----DASHBOARD OVEWRVIEW GRAPHS START-----#
#########################################################################################################################################################################
#########################################################################################################################################################################

def grab_pie_kWh_station(response):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group
			pie = []
			pie_labels = []
			total = 0 
			duration = response.user.profile.duration_energy #User specified time frame as a decimal

			if str(duration) != str(1337.012): #If user has not chosen a "custom" time frame from drop down list
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else: #If user chose a custom time frame
				endDate = response.user.profile.energy_end_date #Get end date and start date from user profile attributes
				startDate = response.user.profile.energy_start_date

			if response.user.profile.user_company.station_set.all():
				for station in response.user.profile.user_company.station_set.all():
					
					pie_labels.append(station.name) # append station names to labels
					kwh_set = station.stationtime_set.filter(time__gte=startDate, time__lte=endDate).iterator() #.iterator() method used for optimisation with larger datasets
					for k in kwh_set: #iterate through iterator object
						total+=(float(k.power)/1000) * 2/3600 #2/3600 metric used because we query data every 2 seconds from the cloud. Cloud returns a 
															  #"projected" watts per hour, so multiplying it by the 2/3600 interval gives us the best approximation for that 2 second moment
					pie.append(total)

					total=0

			return JsonResponse(data={'pie':pie, 'pie_labels':pie_labels})
		else:
			return redirect('/')
	else:
		return redirect('/')

def grab_pie_CO2_station(response):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
			pie = []
			pie_labels = []
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012): #If user has not chosen a "custom" time frame from drop down list
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else: #If user chose a custom time frame
				endDate = response.user.profile.energy_end_date #Get end date and start date from user profile attributes
				startDate = response.user.profile.energy_start_date

			total = 0

			if response.user.profile.user_company.station_set.all():
					for station in response.user.profile.user_company.station_set.all():
						pie_labels.append(station.name) # append station names to labels
						co2_set = station.stationtime_set.filter(time__gte=startDate, time__lte=endDate).iterator() #.iterator() method used for optimisation with larger datasets
						for k in co2_set:
							total+=((float(k.power)/1000) * 2/3600) * float(response.user.profile.user_company.co2_choice) #2/3600 metric used because we query data every 2 seconds from the cloud. Cloud returns a 
																														   #"projected" watts per hour, so multiplying it by the 2/3600 interval gives us the best approximation for that 2 second moment
						pie.append(total)

						total=0

						


			return JsonResponse(data={'pie':pie, 'pie_labels':pie_labels})
		else:
			return redirect('/')
	else:
		return redirect('/')
#TODO: UPDATE THESE WHEN BRANCHES ARE MERGED PROPERLY

def grab_line_kWh_all(response):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			data, hoursData, time_catch=[],[],[]
			duration = response.user.profile.duration_energy

			tz_info = ZoneInfo('Europe/London')

			steps = proportion[str(duration)]
			
			if str(duration) != str(1337.012):
				# endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				endDate = timezone.now()
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000) - datetime.timedelta(seconds=float(steps/2))
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			graphStart = math.trunc(datetime.datetime.timestamp(startDate)*1000)

			interval = 3/ float(duration*100)

			

			if response.user.profile.user_company.companytime_set.all():
				kWh_set = response.user.profile.user_company.companytime_set.all().filter(time__gte=startDate, time__lte=endDate).iterator()
				tempDate = startDate + datetime.timedelta(seconds=float(steps/2))
				for time in kWh_set:

					if time.time >= tempDate:
						
						hoursData.append({'x': math.trunc(datetime.datetime.timestamp(tempDate)*1000), 'y':sum(data)})
						startDate = tempDate
						tempDate = tempDate+ datetime.timedelta(seconds=float(steps/2))
						data=[]
					else:
						data.append(float(time.power)*interval / 1000)
				
					
				hoursData.append({'x': math.trunc(datetime.datetime.timestamp(response.user.profile.user_company.companytime_set.last().time)*1000), 'y':sum(data)})

			data = {'data':hoursData, 'start':graphStart }
			print(data)
			return JsonResponse(data=data)
		else:
			return redirect('/')
	else:
		return redirect('/')
#UPDATE WHEN BRANCHES MERGED PROPERLY
def grab_line_CO2_all(response):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
			data, hoursData, time_catch =[],[],[]
			duration = response.user.profile.duration_energy

			steps = proportion[str(duration)]

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)- datetime.timedelta(seconds=float(steps/2))
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			graphStart = math.trunc(datetime.datetime.timestamp(startDate)*1000)

			interval = 3/ float(duration*100)

			if response.user.profile.user_company.companytime_set.all():
				CO2_set = response.user.profile.user_company.companytime_set.all().filter(time__gte=startDate, time__lte=endDate).iterator()
				tempDate = startDate + datetime.timedelta(seconds=float(steps/2))
				for time in CO2_set:

					if time.time >= tempDate:
						hoursData.append({'x': math.trunc(datetime.datetime.timestamp(tempDate)*1000), 'y':sum(data)})
						startDate = tempDate
						tempDate += datetime.timedelta(seconds=float(steps/2))
						data=[]
					else:
						data.append((float(time.power)*interval / 1000)* float(response.user.profile.user_company.co2_choice))
					
				hoursData.append({'x': math.trunc(datetime.datetime.timestamp(response.user.profile.user_company.companytime_set.last().time)*1000), 'y':sum(data)})



			return JsonResponse(data={'data':hoursData, 'start':graphStart })
		else:
			return redirect('/')

	else:
		return redirect('/')

def populate_bar_chart(response):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
				
			kWhData = []
			CO2Data = []
			labels = []
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012): #If user has not chosen a custom time frame
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else: #if user has chosen a custom time frame
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date
			totalK = 0
			totalC=0

			for station in response.user.profile.user_company.station_set.all():
				labels.append(station.name)
				iterator_set = station.stationtime_set.filter(time__gte=startDate, time__lte=endDate).iterator() #.iterator() is useful for larger datasets - optimisation
				for k in iterator_set:
					totalK+=((float(k.power)/1000) * 2/3600) #Total kWh
					totalC+=((float(k.power)/1000) * 2/3600) * float(response.user.profile.user_company.co2_choice) #totalCO2
				
				kWhData.append(totalK)
				CO2Data.append(totalC)
				totalK = 0
				totalC=0



			return JsonResponse(data={"kWhData":kWhData, "CO2Data": CO2Data, "labels":labels})
		else:
			return redirect('/')
	else:
		return redirect('/')

#########################################################################################################################################################################
#########################################################################################################################################################################
																		#----DASHBOARD OVERVIEW GRAPHS END-----#






																		#----DASHBOARD STATION GRAPHS START-----#
#########################################################################################################################################################################
#########################################################################################################################################################################

def grab_indiviudal_station_kWh(response, id):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy: #If user has energy group
			station = Station.objects.get(id=id)
			

			pie = []
			pie_labels = []
			total = 0
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012): #If user has not picked a custom time frame
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else: #If user picks a custom time frame
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			if station.equipment_set.all():
					for equip in station.equipment_set.all():
						
						pie_labels.append(equip.name)
						kwh_set = equip.equipmenttime_set.filter(time__gte=startDate, time__lte=endDate).iterator() #.iterator() method is useful for optimisation
						for k in kwh_set:
							total+=(float(k.power)/1000) * 2/3600
						pie.append(total)

						total=0


			return JsonResponse(data={'pie':pie, 'pie_labels':pie_labels})
		else:
			return redirect('/')
	else:
		return redirect('/')

#Comments for this are redundant as it is an iteration of previous functions
def grab_individual_station_CO2(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
				
			station = Station.objects.get(id=id)
			pie = []
			pie_labels = []
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			total = 0

			if station.equipment_set.all():
					for equip in station.equipment_set.all():
						pie_labels.append(equip.name)
						co2_set = equip.equipmenttime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
						for k in co2_set:
							total+=((float(k.power)/1000) * 2/3600) * float(response.user.profile.user_company.co2_choice)
						pie.append(total)

						total=0


			return JsonResponse(data={'pie':pie, 'pie_labels':pie_labels})
		else:
			return redirect('/')
	else:
		return redirect('/')
#Comments redundant 
def grab_equipment_kWh_CO2(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			station = Station.objects.get(id=id)


			kWhData = []
			CO2Data = []
			labels = []
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date
			totalK = 0
			totalC=0

			for equip in station.equipment_set.all():
				labels.append(equip.name)
				iterator_set = equip.equipmenttime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
				for k in iterator_set:
					totalK+=((float(k.power)/1000) * 2/3600)
					totalC+=((float(k.power)/1000) * 2/3600) * float(response.user.profile.user_company.co2_choice)
				
				kWhData.append(totalK)
				CO2Data.append(totalC)
				totalK = 0
				totalC=0


			return JsonResponse(data={"kWhData":kWhData, "CO2Data": CO2Data, "labels":labels})
		else:
			return redirect('/')
	else:
		return redirect('/')
#UPDATE WHEN BRANCHES MERGEDD
def grab_equipment_line_kWh(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:		
			station = Station.objects.get(id=id)
			data, hoursData, time_catch=[],[],[]
			duration = response.user.profile.duration_energy

			tz_info = ZoneInfo('Europe/London')

			steps = proportion[str(duration)]
			
			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			graphStart = math.trunc(datetime.datetime.timestamp(startDate)*1000)

			count = 1
			interval = 2/ (float(steps))

			kWh_set = station.stationtime_set.all().filter(time__gte=startDate)
			continuous_count = 0

			if station.stationtime_set.all():
				for time in kWh_set.iterator():

					if count == steps/2:

						data.append(float(time.power)*interval / 1000)
						hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time_catch[0])*1000), 'y':sum(data)})
						data=[]
						time_catch=[]
						count = 1
					else:
						data.append(float(time.power)*interval / 1000)
						time_catch.append(time.time)
						count +=1

				
				hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time.time)*1000), 'y':sum(data)})



			return JsonResponse(data={'data':hoursData, 'start':graphStart })
		else:
			return redirect('/')
	else:
		return redirect('/')
#TODO: UPDATE WHEN BRANCES MERGED
def grab_equipment_line_CO2(response, id):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			station = Station.objects.get(id=id)
			data, hoursData, time_catch =[],[],[]
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			graphStart = math.trunc(datetime.datetime.timestamp(startDate)*1000)
			count = 1

			steps = proportion[str(duration)]
			interval = 2/ (float(steps))
			CO2_set = station.stationtime_set.all().filter(time__gte=startDate, time__lte=endDate)
			continuous_count = 0
			if station.stationtime_set.all():
				for time in CO2_set.iterator():
					if count == steps/2:
						data.append((float(time.power)*interval / 1000) * float(response.user.profile.user_company.co2_choice))
						hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time_catch[0])*1000), 'y':sum(data)})
						data=[]
						time_catch=[]
						count = 1

					else:
						data.append((float(time.power) *interval/ 1000)*float(response.user.profile.user_company.co2_choice))
						count +=1
						time_catch.append(time.time)

				hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time.time)*1000), 'y':sum(data)})



			return JsonResponse(data={'data':hoursData, 'start':graphStart })
		else:
			return redirect('/')
	else:
		return redirect('/')

#########################################################################################################################################################################
#########################################################################################################################################################################
																		#----DASHBOARD STATION GRAPHS END-----#






																		#----DASHBOARD EQUIPMENT GRAPHS START-----#
#########################################################################################################################################################################
#########################################################################################################################################################################

def grab_individual_equipment_kWh(response, id):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
			equipment = Equipment.objects.get(id=id)
			pie = []
			pie_labels = []
			total = 0
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			if equipment.powerclamp_set.all():
					for clamp in equipment.powerclamp_set.all():
						
						pie_labels.append(clamp.name)
						kwh_set = clamp.powerclamptime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
						for k in kwh_set:
							total+=(float(k.power)/1000) * 2/3600
						pie.append(total)

						total=0


			return JsonResponse(data={'pie':pie, 'pie_labels':pie_labels})
		else:
			return redirect('/')
	else:
		return redirect('/')

def grab_individual_equipment_CO2(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
			equipment = Equipment.objects.get(id=id)
			pie = []
			pie_labels = []
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			total = 0

			if equipment.powerclamp_set.all():
					for clamp in equipment.powerclamp_set.all():
						pie_labels.append(clamp.name)
						co2_set = clamp.powerclamptime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
						for k in co2_set:
							total+=((float(k.power)/1000) * 2/3600) * float(response.user.profile.user_company.co2_choice)
						pie.append(total)

						total=0

			return JsonResponse(data={'pie':pie, 'pie_labels':pie_labels})
		else:
			return redirect('/')
	else:
		return redirect('/')

def grab_clamp_kWh_CO2(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			equipment = Equipment.objects.get(id=id)

			kWhData = []
			CO2Data = []
			labels = []
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date
			totalK = 0
			totalC=0

			for clamp in equipment.powerclamp_set.all():
				labels.append(clamp.name)
				iterator_set = clamp.powerclamptime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
				for k in iterator_set:
					totalK+=((float(k.power)/1000) * 2/3600)
					totalC+=((float(k.power)/1000) * 2/3600) * float(response.user.profile.user_company.co2_choice)
				
				kWhData.append(totalK)
				CO2Data.append(totalC)
				totalK = 0
				totalC=0

			return JsonResponse(data={"kWhData":kWhData, "CO2Data": CO2Data, "labels":labels})
		else:
			return redirect('/')
	else:
		return redirect('/')


def grab_clamps_line_kWh(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
			
			equipment = Equipment.objects.get(id=id)
			data, hoursData, time_catch=[],[],[]
			duration = response.user.profile.duration_energy

			tz_info = ZoneInfo('Europe/London')

			steps = proportion[str(duration)]
			
			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			graphStart = math.trunc(datetime.datetime.timestamp(startDate)*1000)

			count = 1
			interval = 2/ (float(steps))

			kWh_set = equipment.equipmenttime_set.all().filter(time__gte=startDate).iterator()
			continuous_count = 0

			if equipment.equipmenttime_set.all():
				for time in kWh_set:

					if count == steps/2:

						data.append(float(time.power)*interval / 1000)
						hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time_catch[0])*1000), 'y':sum(data)})
						data=[]
						time_catch=[]
						count = 1
					else:
						data.append(float(time.power)*interval / 1000)
						time_catch.append(time.time)
						count +=1

				
				hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time.time)*1000), 'y':sum(data)})

			return JsonResponse(data={'data':hoursData, 'start':graphStart })
		else:
			return redirect('/')
	else:
		return redirect('/')

def grab_clamps_line_CO2(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
				
			equipment = Equipment.objects.get(id=id)
			data, hoursData, time_catch =[],[],[]
			duration = response.user.profile.duration_energy

			if str(duration) != str(1337.012):
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate - datetime.timedelta(seconds=(float(duration))*1000)
			else:
				endDate = response.user.profile.energy_end_date
				startDate = response.user.profile.energy_start_date

			graphStart = math.trunc(datetime.datetime.timestamp(startDate)*1000)
			count = 1

			steps = proportion[str(duration)]
			interval = 2/ (float(steps))
			CO2_set = equipment.equipmenttime_set.all().filter(time__gte=startDate, time__lte=endDate).iterator()
			continuous_count = 0
			if equipment.equipmenttime_set.all():
				for time in CO2_set:
					if count == steps/2:
						data.append((float(time.power)*interval / 1000) * float(response.user.profile.user_company.co2_choice))
						hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time_catch[0])*1000), 'y':sum(data)})
						data=[]
						time_catch=[]
						count = 1

					else:
						data.append((float(time.power) *interval/ 1000)*float(response.user.profile.user_company.co2_choice))
						count +=1
						time_catch.append(time.time)

				hoursData.append({'x': math.trunc(datetime.datetime.timestamp(time.time)*1000), 'y':sum(data)})


			return JsonResponse(data={'data':hoursData, 'start':graphStart })
		else:
			return redirect('/')
	else:
		return redirect('/')

#########################################################################################################################################################################
#########################################################################################################################################################################
																		#----DASHBOARD EQUIPMENT GRAPHS END-----#





																		#----DASHBOARD VIEWS START-----#
#########################################################################################################################################################################
#########################################################################################################################################################################




def energyCaptureDashboard(response):
    if not response.user.is_authenticated:
        return redirect('/')

    try:
        energy = True

        if energy:
            # Get user duration with safety check
            duration = response.user.profile.duration_energy or Decimal('86.400')
            
            stepSize = proportion.get(str(duration), '1.000')  # Default step if not found
            hours_kWh = 0
            temparr = []
            
            form = ChooseDateRange()
            time_form = ChooseTime()
            custom, nextStep = False, False
            company = response.user.profile.user_company
            user = response.user.profile
            string = ""

            # Safe date formatting with checks
            try:
                s = user.energy_start_date.strftime("%Y-%m-%d") if user.energy_start_date else ""
                e = user.energy_end_date.strftime("%Y-%m-%d") if user.energy_end_date else ""
            except AttributeError:
                s, e = "", ""

            strings = {
                '0.060': "",
                '0.300': "",
                '3.600': " for last hour",
                '86.400': " for last 24 hours",
                '604.800': " for last week",
                '31556.952': " for last year",
                '259.200': " for last month",
                '999999.999': " for entire lifespan",
                '1337.012': f" from {s} to {e}"
            }

            # Safe conversion for co2_choice
            try:
                co2_factor = float(company.co2_choice if company.co2_choice is not None else 1.0)
            except (ValueError, TypeError):
                co2_factor = 1.0

            kWh = getattr(company, 'total_power', 0) or 0
            CO2 = kWh * co2_factor

            stations = company.station_set.all()
            equipments = Equipment.objects.filter(station__in=stations)
            total_power_of_stations = sum(x or 0 for x in equipments.values_list("total_power", flat=True))
            total_co2_of_stations = total_power_of_stations * co2_factor

            if response.method == 'POST':
                if 'Date' in response.POST:
                    form = ChooseDateRange(response.POST)
                    if form.is_valid():
                        start = response.POST['start_date_field'] + " 00:00:00"
                        end = response.POST['end_date_field'] + " 23:59:59"
                        custom = True
                        nextStep = True
                        user.duration_energy = Decimal('1337.012')

                        start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                        end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                        user.energy_start_date = start
                        user.energy_end_date = end

                if 'Time_Frame' in response.POST:
                    time_form = ChooseTime(response.POST)
                    if time_form.is_valid():
                        choice = time_form.cleaned_data['time_field']
                        if choice == "Custom":
                            custom = True
                            nextStep = False
                        elif choice == "AT":
                            kWh = getattr(company, 'total_power', 0) or 0
                            CO2 = kWh * co2_factor
                            user.duration_energy = Decimal('604.800')
                        elif choice == "YR":
                            user.duration_energy = Decimal('31556.952')
                            string = " for last year"
                        elif choice == "WK":
                            user.duration_energy = Decimal('604.800')
                            string = " for last week"
                        elif choice == "DAY":
                            user.duration_energy = Decimal('86.400')
                            string = " for last day"
                        elif choice == "HR":
                            user.duration_energy = Decimal('3.600')
                            string = " for last hour"
                        elif choice == "MTH":
                            user.duration_energy = Decimal('259.200')
                            string = " for last month"

                user.save()
                try:
                    temp = round(user.duration_energy, 3)
                    stepSize = proportion.get(str(temp), '1.000')
                except (TypeError, AttributeError):
                    stepSize = '1.000'

            # Calculate today's usage
            startDate = datetime.datetime.today().replace(microsecond=0, hour=0, minute=0, second=0)
            company_iterator = company.companytime_set.filter(time__gte=startDate).iterator()

            for energy in company_iterator:
                try:
                    power_value = float(energy.power if energy.power is not None else 0)
                    temparr.append(power_value * 2/3600)
                except (ValueError, TypeError):
                    continue
                    
            hours_kWh = sum(temparr) / 1000

            # Calculate weekly rate
            rate_iterator = company.companytime_set.filter(
                time__lte=startDate,
                time__gte=startDate - datetime.timedelta(days=7)
            ).iterator()
            
            temparr = []
            ncount = 1
            time = None
            
            for energy in rate_iterator:
                if ncount >= 8:
                    break
                    
                try:
                    power_value = float(energy.power if energy.power is not None else 0)
                    temparr.append(power_value * 2/3600)
                except (ValueError, TypeError):
                    continue
                    
                current_time = energy.time.replace(microsecond=0, hour=0, minute=0, second=0)
                if current_time != time:
                    ncount += 1
                    time = current_time
                else:
                    time = current_time

            sum_rate = sum(temparr) / 1000
            average_kWh = sum_rate / max(ncount, 1)  # Avoid division by zero
            average_CO2 = average_kWh * co2_factor

            CO2 = 0
            kWh = 0

            if not custom or not nextStep:
                endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
                try:
                    duration_seconds = float(user.duration_energy or 86.400) * 1000
                    startDate = endDate - datetime.timedelta(seconds=duration_seconds)
                except (ValueError, TypeError):
                    startDate = endDate - datetime.timedelta(days=1)
                kwh_set = company.companytime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
            elif custom and nextStep:
                endDate = end
                startDate = start
                kwh_set = company.companytime_set.filter(time__gte=start, time__lte=end).iterator()

            for k in kwh_set:
                try:
                    power_value = float(k.power if k.power is not None else 0)
                    kWh += (power_value * 2/3600) / 1000
                    CO2 += ((power_value * 2/3600) / 1000) * co2_factor
                except (ValueError, TypeError):
                    continue

            kWh = round(kWh, 2)
            CO2 = round(CO2, 2)

            CO2_Analogies = {
                'CO2_car': (CO2 * 0.221),
                'CO2_fire': (CO2 * 2),
                'CO2_phone': (CO2 * 121.643)
            }
            
            endDate = datetime.date.today()
            
            try:
                duration_key = str(round(user.duration_energy, 3))
                string = strings.get(duration_key, "")
            except (TypeError, AttributeError):
                string = ""

            kwh_x_data, kwh_y_data = get_kwh_in_per_hour_time(response.user)
            co2_x_data, co2_y_data = get_co2_emission_in_per_hour_time(response.user)

            context = {
                'average_kWh': average_kWh,
                'average_CO2': average_CO2,
                'CO2_Analogies': CO2_Analogies,
                'endDate': endDate,
                'kWh': kWh,
                'CO2': CO2,
                'stepSize': stepSize,
                'hours_kWh': hours_kWh,
                'company': company,
                'form': form,
                'ChooseTime': ChooseTime,
                'custom': custom,
                'string': string,
                'kwh_x_data': kwh_x_data,
                'kwh_y_data': kwh_y_data,
                'co2_x_data': co2_x_data,
                'co2_y_data': co2_y_data,
                'total_power_of_stations': total_power_of_stations,
                'total_co2_of_stations': total_co2_of_stations,
            }

            return render(response, 'EnergyCapture/dashboard.html', context)

    except Exception as e:
        print(f"Error in energyCaptureDashboard: {str(e)}")
        return redirect('/')

    return redirect('/')

from Main.models import Process, SubProcess

def overviewHierarchy(response):
    if not response.user.is_authenticated:
        return redirect('/')
       
    if not response.user.groups.filter(name='Energy').exists():
        return redirect('/')
 
    user = response.user.profile
    company = user.user_company
    stations = company.station_set.all()
    stationCount = stations.count()
   
    container = {}
    power_container = {}
    indirect_power = {}  # Container for indirect energy data
   
    custom = False
    nextStep = False
    form = ChooseDateRange()
    time_form = ChooseTime()
   
    s = user.energy_start_date.strftime("%Y-%m-%d")
    e = user.energy_end_date.strftime("%Y-%m-%d")
    strings = {
        '0.060': "",
        '0.300': "",
        '3.600': " for last hour",
        '86.400': " in the last 24 hours",
        '604.800': " for last week",
        '31556.952': " for last year",
        '259.200': " for last month",
        '999999.999': " for entire lifespan",
        '1337.012': f" from {s} to {e}"
    }
    string = strings[str(user.duration_energy)]
   
    if response.method == 'POST':
        if 'Date' in response.POST:
            form = ChooseDateRange(response.POST)
            if form.is_valid():
                start = datetime.datetime.strptime(
                    response.POST['start_date_field'] + " 00:00:00",
                    "%Y-%m-%d %H:%M:%S"
                )
                end = datetime.datetime.strptime(
                    response.POST['end_date_field'] + " 23:59:59",
                    "%Y-%m-%d %H:%M:%S"
                )
                custom = True
                nextStep = True
                user.duration_energy = Decimal('1337.012')
                user.energy_start_date = start
                user.energy_end_date = end
               
        if 'Time_Frame' in response.POST:
            time_form = ChooseTime(response.POST)
            if time_form.is_valid():
                choice = time_form.cleaned_data['time_field']
                duration_mapping = {
                    "Custom": ('1337.012', True, False),
                    "AT": ('999999.999', False, False),
                    "YR": ('31556.952', False, False),
                    "WK": ('604.800', False, False),
                    "DAY": ('86.400', False, False),
                    "HR": ('3.600', False, False),
                    "MTH": ('259.200', False, False),
                }
               
                if choice in duration_mapping:
                    duration, custom, nextStep = duration_mapping[choice]
                    user.duration_energy = Decimal(duration)
       
        user.save()
 
    if not custom or not nextStep:
        endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
        startDate = endDate - datetime.timedelta(seconds=float(user.duration_energy)*1000)
        b_endDate = startDate
        b_startDate = startDate - datetime.timedelta(seconds=float(user.duration_energy) * 1000)
    else:
        endDate = user.energy_end_date
        startDate = user.energy_start_date
        b_endDate = startDate
        diff = startDate - endDate
        b_startDate = startDate + diff

    # Initialize indirect power values with exact 0.000
    indirect_power = {
        'kuka_robot': Decimal('0.000'),
        'welding_table': Decimal('0.000'),
        'pistons': Decimal('0.000'),
        'compressor': Decimal('0.000')
    }

    # Calculate indirect energy if processes exist
    all_processes = Process.objects.filter(project__company=company)
    
    for process in all_processes:
        # Get relevant subprocesses
        ply_subprocesses = SubProcess.objects.filter(
            process=process,
            name__in=['Ply Placed', 'Ply Waiting', 'Pickup Initial Ply', 'Pickup Ply & Weld']
        )
        
        # Check Pickup Initial Ply status for KUKA and Welding
        pickup_initial = SubProcess.objects.filter(
            process=process,
            name='Pickup Initial Ply',
            status=2
        ).exists()
        
        # Check Blank Pressed status for Pistons
        blank_pressed = SubProcess.objects.filter(
            process=process,
            name='Blank Pressed',
            status=2
        ).exists()
        
        if pickup_initial:
            # Sum power for KUKA robot
            kuka_sum = sum(sub.power for sub in ply_subprocesses if sub.power)
            if kuka_sum:
                indirect_power['kuka_robot'] = Decimal(str(kuka_sum)).quantize(Decimal('0.000'))
                # Calculate welding table power (KUKA sum + 0.100)
                indirect_power['welding_table'] = (Decimal(str(kuka_sum)) + Decimal('0.100')).quantize(Decimal('0.000'))
        
        if blank_pressed:
            # Add pistons power
            indirect_power['pistons'] = Decimal('0.125').quantize(Decimal('0.000'))
        
        # Calculate compressor power (sum of all indirect power)
        indirect_power['compressor'] = (
            indirect_power['kuka_robot'] + 
            indirect_power['welding_table'] + 
            indirect_power['pistons']
        ).quantize(Decimal('0.000'))

    def calculate_power(qs, time_range):
        return sum([float(entry.power) * 2/3600 for entry in qs.filter(
            time__gte=time_range[0],
            time__lte=time_range[1]
        ).iterator()]) / 1000
 
    def calculate_percentage_change(current, previous):
        if previous == 0:
            return 0
        return (100 - current/previous*100) * -1
 
    company_current_power = 0
    company_previous_power = 0
 
    for station in stations:
        station_current_power = 0
        station_previous_power = 0
       
        for equipment in station.equipment_set.all():
            equipment_current_power = 0
            equipment_previous_power = 0
           
            for clamp in equipment.powerclamp_set.all():
                clamp_current_power = calculate_power(
                    clamp.powerclamptime_set,
                    (startDate, endDate)
                )
                clamp_previous_power = calculate_power(
                    clamp.powerclamptime_set,
                    (b_startDate, b_endDate)
                )
               
                power_container[clamp] = clamp_current_power
                container[clamp] = calculate_percentage_change(
                    clamp_current_power,
                    clamp_previous_power
                )
               
                equipment_current_power += clamp_current_power
                equipment_previous_power += clamp_previous_power
           
            power_container[equipment] = equipment_current_power
            container[equipment] = calculate_percentage_change(
                equipment_current_power,
                equipment_previous_power
            )
           
            station_current_power += equipment_current_power
            station_previous_power += equipment_previous_power
       
        power_container[station] = station_current_power
        container[station] = calculate_percentage_change(
            station_current_power,
            station_previous_power
        )
       
        company_current_power += station_current_power
        company_previous_power += station_previous_power
   
    power_container['company'] = company_current_power
    container['company'] = calculate_percentage_change(
        company_current_power,
        company_previous_power
    )
 
    return render(response, 'EnergyCapture/overviewHierarchy.html', {
        'string': string,
        'custom': custom,
        'stations': stations,
        'stationCount': stationCount,
        'company': company,
        'container': container,
        'form': form,
        'ChooseTime': time_form,
        'power_container': power_container,
        'indirect_power': indirect_power
    })



#This is essentially the same as overiew dashboard but with a station object instead. 
def viewStationDashboard(response, id):
	if response.user.is_authenticated:

		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
		
			duration = response.user.profile.duration_energy

			stepSize = proportion[str(duration)] 
			hours_kWh = 0
			temparr = []
			form = ChooseDateRange()
			time_form = ChooseTime()
			custom, nextStep = False, False
			station = Station.objects.get(id=id)
			user = response.user.profile
			string=""
			s = user.energy_start_date.strftime("%Y-%m-%d")
			e = user.energy_end_date.strftime("%Y-%m-%d")
			strings = {'0.060': "", '0.300':"", '3.600': " for last hour", '86.400': " for last 24 hours", '604.800': " for last week", '31556.952': " for last year", '259.200': " for last month", '999999.999':" for entire lifespan", '1337.012': f" from {s} to {e}"}
			
			kWh = station.total_power
			CO2 = station.total_power * float(response.user.profile.user_company.co2_choice)
		

			if response.method == 'POST':
				
				if 'Date' in response.POST:
					form = ChooseDateRange(response.POST)
					if form.is_valid():
						start = response.POST['start_date_field']+  " 00:00:00"
						end = response.POST['end_date_field']+ " 23:59:59"
						custom=True
						nextStep = True
						user.duration_energy = Decimal(1337.012)
						

						start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
						end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

						user.energy_start_date = start
						user.energy_end_date = end


				if 'Time_Frame' in response.POST:
					time_form = ChooseTime(response.POST)
					if time_form.is_valid():
						choice = time_form.cleaned_data['time_field']

						if choice == "Custom":
							custom = True
							nextStep = False

						elif choice == "AT":
							user.duration_energy = Decimal(999999.999)
						elif choice == "YR":
							user.duration_energy = Decimal(31556.952)
							string=" for last year"
						elif choice == "WK":
							user.duration_energy =  Decimal(604.800)
							string=" for last week"
						elif choice == "DAY":
							user.duration_energy =  Decimal(86.400)
							string=" for last day"
						elif choice == "HR":
							user.duration_energy = Decimal(3.600)
							string=" for last hour"
						elif choice == "MTH":
							user.duration_energy = Decimal(259.200)
							string=" for last month"
							

				user.save()
				temp = round(user.duration_energy, 3)
				stepSize = proportion[str(temp)] 


			startDate = datetime.datetime.today().replace(microsecond=0, hour=0, minute=0, second=0)
			station_iterator = station.stationtime_set.all().filter(time__gte=startDate).iterator()


			for energy in station_iterator:
				temparr.append(float(energy.power)*2/3600)
			hours_kWh = sum(temparr) /1000

			rate_iterator = station.stationtime_set.all().filter(time__lte=startDate, time__gte=startDate-datetime.timedelta(days=7)).iterator()
			temparr = []
			ncount = 1
			time = None
			for energy in rate_iterator:
				if ncount != 8:
					temparr.append(float(energy.power)*2/3600)
					if energy.time.replace(microsecond=0, hour=0, minute=0, second=0) != time:
						ncount+=1
						time=energy.time.replace(microsecond=0, hour=0, minute=0, second=0)
					else:
						time = energy.time.replace(microsecond=0, hour=0, minute=0, second=0)
				else:
					break

			sum_rate = sum(temparr) / 1000
			average_kWh = sum_rate / ncount 
			average_CO2 = average_kWh * float(response.user.profile.user_company.co2_choice)

			CO2=0
			kWh = 0

			if not custom or not nextStep:
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate-datetime.timedelta(seconds=float(user.duration_energy)*1000)
				kwh_set = station.stationtime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
			elif custom and nextStep:
				endDate = end
				startDate = start
				kwh_set = station.stationtime_set.filter(time__gte=start, time__lte=end).iterator()

			for k in kwh_set:
				kWh += (float(k.power) * 2/3600) / 1000
				CO2 += ((float(k.power)*2/3600)/1000) * float(response.user.profile.user_company.co2_choice)
			kWh = round(kWh,2)
			CO2 = round(CO2,2)

			endDate = datetime.date.today()
			string = strings[str(round(response.user.profile.duration_energy,3))]
			CO2_Analogies = {'CO2_car':(CO2 * 0.221), 'CO2_fire':(CO2 * 2), 'CO2_phone':(CO2 * 121.643)}

			return render(response, 'EnergyCapture/stationDashboard.html', {'average_kWh':average_kWh, 'average_CO2':average_CO2, 'CO2_Analogies':CO2_Analogies,
			  'endDate':endDate, 'kWh': kWh, 'CO2':CO2, 'stepSize':stepSize, 'hours_kWh':hours_kWh, 'station':station, 'form':form, 'ChooseTime':ChooseTime, 'custom':custom, 'string':string})

		else:
			return redirect('/')
	else:
		return redirect('/')

#This is the same as the dashboard overview page but with an equipment object instead
def viewEquipmentDashboard(response, id):
	if response.user.is_authenticated:
		energy = False
		if response.user.groups.filter(name='Energy').exists():
			energy = True
		if energy:
			
			duration = response.user.profile.duration_energy

			stepSize = proportion[str(duration)] 
			hours_kWh = 0
			temparr = []
			form = ChooseDateRange()
			time_form = ChooseTime()
			custom, nextStep = False, False
			equipment = Equipment.objects.get(id=id)
			user = response.user.profile
			string=""
			s = user.energy_start_date.strftime("%Y-%m-%d")
			e = user.energy_end_date.strftime("%Y-%m-%d")
			strings = {'0.060': "", '0.300':"", '3.600': " for last hour", '86.400': " for last 24 hours", '604.800': " for last week", '31556.952': " for last year", '259.200': " for last month", '999999.999':" for entire lifespan", '1337.012': f" from {s} to {e}"}
			
			kWh = equipment.total_power
			CO2 = equipment.total_power * float(response.user.profile.user_company.co2_choice)
		

			if response.method == 'POST':
				
				if 'Date' in response.POST:
					form = ChooseDateRange(response.POST)
					if form.is_valid():
						start = response.POST['start_date_field']+  " 00:00:00"
						end = response.POST['end_date_field']+ " 23:59:59"
						custom=True
						nextStep = True
						user.duration_energy = Decimal(1337.012)
						

						start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
						end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

						user.energy_start_date = start
						user.energy_end_date = end


				if 'Time_Frame' in response.POST:
					time_form = ChooseTime(response.POST)
					if time_form.is_valid():
						choice = time_form.cleaned_data['time_field']

						if choice == "Custom":
							custom = True
							nextStep = False
						elif choice == "AT":
							user.duration_energy = Decimal(999999.999)
						elif choice == "YR":
							user.duration_energy = Decimal(31556.952)
							string=" for last year"
						elif choice == "WK":
							user.duration_energy =  Decimal(604.800)
							string=" for last week"
						elif choice == "DAY":
							user.duration_energy =  Decimal(86.400)
							string=" for last day"
						elif choice == "HR":
							user.duration_energy = Decimal(3.600)
							string=" for last hour"
						elif choice == "MTH":
							user.duration_energy = Decimal(259.200)
							string=" for last month"
							

				user.save()
				temp = round(user.duration_energy, 3)
				stepSize = proportion[str(temp)] 


			startDate = datetime.datetime.today().replace(microsecond=0, hour=0, minute=0, second=0)
			equip_iterator = equipment.equipmenttime_set.all().filter(time__gte=startDate).iterator()

			for energy in equip_iterator:
				temparr.append(float(energy.power)*2/3600)
			hours_kWh = sum(temparr) /1000

			rate_iterator = equipment.equipmenttime_set.all().filter(time__lte=startDate, time__gte=startDate-datetime.timedelta(days=7)).iterator()
			temparr = []
			ncount = 1
			time = None
			for energy in rate_iterator:
				if ncount != 8:
					temparr.append(float(energy.power)*2/3600)
					if energy.time.replace(microsecond=0, hour=0, minute=0, second=0) != time:
						ncount+=1
						time=energy.time.replace(microsecond=0, hour=0, minute=0, second=0)
					else:
						time = energy.time.replace(microsecond=0, hour=0, minute=0, second=0)
				else:
					break

			sum_rate = sum(temparr) / 1000
			average_kWh = sum_rate / ncount 
			average_CO2 = average_kWh * float(response.user.profile.user_company.co2_choice)

			CO2=0
			kWh = 0

			if not custom or not nextStep:
				endDate = datetime.datetime.now(ZoneInfo('Europe/London'))
				startDate = endDate-datetime.timedelta(seconds=float(user.duration_energy)*1000)
				kwh_set = equipment.equipmenttime_set.filter(time__gte=startDate, time__lte=endDate).iterator()
			elif custom and nextStep:
				endDate = end
				startDate = start
				kwh_set = equipment.equipmenttime_set.filter(time__gte=start, time__lte=end).iterator()

			for k in kwh_set:
				kWh += (float(k.power) * 2/3600) / 1000
				CO2 += ((float(k.power)*2/3600)/1000) * float(response.user.profile.user_company.co2_choice)
			kWh = round(kWh,2)
			CO2 = round(CO2,2)

			endDate = datetime.date.today()
			string = strings[str(round(response.user.profile.duration_energy,3))]
			CO2_Analogies = {'CO2_car':(CO2 * 0.221), 'CO2_fire':(CO2 * 2), 'CO2_phone':(CO2 * 121.643)}
			return render(response, 'EnergyCapture/equipmentDashboard.html', {'average_kWh':average_kWh, 'average_CO2':average_CO2 ,'CO2_Analogies':CO2_Analogies,
			  'endDate':endDate, 'kWh': kWh, 'CO2':CO2, 'stepSize':stepSize, 'hours_kWh':hours_kWh, 'equipment':equipment, 'form':form, 'ChooseTime':ChooseTime, 'custom':custom, 'string':string})
	else:
		return redirect('/')



#########################################################################################################################################################################
#########################################################################################################################################################################
																		#----DASHBOARD VIEWS END-----#		