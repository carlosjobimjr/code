# Django
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.db.models.fields import NOT_PROVIDED
from django.contrib import messages
from django import template
# Importing local .py files
from .forms import *
from .models import *
from monorepo.models import CommonTask
from MainData.models import *
from EdgeDetection.forms import *
from EdgeDetection.views import *
# from . helper import *
import asyncio
import django.utils
from zoneinfo import ZoneInfo
# Importing DateTime
from datetime import datetime, date, time, timedelta
import io, os, random, requests, math, environ, json, environ
from asgiref.sync import async_to_sync
from django.utils import timezone
from .opc_client import *
import requests
from opcua import Client, ua
import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.contrib import messages
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

from django.views.decorators.http import require_http_methods

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

django.utils.timezone.activate(ZoneInfo("Europe/London"))

logger = logging.getLogger('__name__')

def index(response):
    """View to return home page"""
    if response.user.is_authenticated:
        admin = False
        if response.user.groups.filter(name='Admin').exists():
            admin = True
        # return response and page
        return render(response, 'Main/index.html', {'admin': admin})
    else:
        return redirect('/mylogout/')



def check_weight_tolerance(nominal_weight, actual_weight, tolerance):
    """Check if actual weight is within tolerance range"""
    lower_bound = nominal_weight - tolerance
    upper_bound = nominal_weight + tolerance
    return lower_bound <= actual_weight <= upper_bound

def get_user_roles(user):
    management = user.groups.filter(name='Management').exists()
    supervisor = user.groups.filter(name='Supervisor').exists()
    technician = user.groups.filter(name='Technician').exists()
    admin = user.groups.filter(name='Admin').exists()
    return management, technician, supervisor, admin

def showProcess(response, id):
    if not response.user.is_authenticated:
        return redirect('/mylogout/')

    print("\n=== Starting showProcess ===")
    print(f"Request method: {response.method}")
    
    try:
        # Get latest weight reading
        latest_weight = SensorDataStorage.objects.filter(
            weight__isnull=False
        ).order_by('-id').first()
        current_weight = latest_weight.weight if latest_weight else None
        print(f"Current weight from sensor: {current_weight}")

        # Get process and verify access
        pro = Process.objects.get(id=id)
        if pro.project not in response.user.profile.user_company.project_set.all():
            return redirect('/')
            
        # Get subprocesses
        subprocesses = SubProcess.objects.filter(process=pro)
        initial_weight_subprocess = subprocesses.filter(name='Part Assessment (Initial Weight)').first()
        final_weight_subprocess = subprocesses.filter(name='Part Assessment (Final Weight)').first()
        trim_subprocess = subprocesses.filter(name='Trim').first()

        weight_sensor = Sensor.objects.filter(
            sub_process__process=pro,
            sub_process__name='Part Assessment (Initial Weight)'
        ).first()
        
        final_weight_sensor = Sensor.objects.filter(
            sub_process__process=pro,
            sub_process__name='Part Assessment (Final Weight)'
        ).first()

        if weight_sensor:
            print(f"Initial weight sensor before update: {weight_sensor.actualWeight}")

        if response.method == 'POST':
            print("\n=== Processing POST Request ===")
            print("POST data:", response.POST)
            try:
                if 'set_actual_weight' in response.POST and initial_weight_subprocess:
                    print("Found set_actual_weight in POST data")
                    print(f"Initial weight subprocess: {initial_weight_subprocess}")
                    print(f"Current weight to save: {current_weight}")
                    
                    if not weight_sensor:
                        print("Creating new weight sensor")
                        weight_sensor = Sensor(sub_process=initial_weight_subprocess)
                    else:
                        print("Using existing weight sensor")
                    
                    if current_weight is not None:
                        print(f"Previous actualWeight: {weight_sensor.actualWeight}")
                        weight_sensor.actualWeight = Decimal(str(current_weight))
                        weight_sensor.save()
                        print(f"New actualWeight saved: {weight_sensor.actualWeight}")
                        weight_sensor.refresh_from_db()
                        print(f"Refreshed actualWeight: {weight_sensor.actualWeight}")
                        
                if 'set_final_tolerance' in response.POST and final_weight_subprocess:
                    tolerance = Decimal(response.POST.get('tolerance', '0'))
                    if not final_weight_sensor:
                        final_weight_sensor = Sensor(
                            tolerance=tolerance,
                            sub_process=final_weight_subprocess
                        )
                    final_weight_sensor.tolerance = tolerance
                    if current_weight is not None:
                        final_weight_sensor.finalWeight = Decimal(str(current_weight))
                    final_weight_sensor.save()
                        
            except Exception as e:
                print(f"Error in POST handling: {e}")
                logger.error(f"Error in POST handling: {e}")

        # Calculate totals
        totals = {
            'interface_time': sum(
                sub.interfaceTime.total_seconds() 
                for sub in subprocesses 
                if sub.interfaceTime is not None
            ),
            'process_time': sum(
                (sub.processTime.total_seconds() if sub.name in ['Blank Pressed', 'Trim','Cut Ply Shapes','Load and Cut Ply', 'Pickup Ply & Weld', 'Press Part', 'Trim To Shape', 'Heat Tool', 'Check Final Geometry with Checking Template'] else 0)
                for sub in subprocesses 
                if sub.processTime is not None
            ),
            'material_wastage': sum(sub.materialWastage for sub in subprocesses),
            'labour_cost': sum(sub.labourSumCost for sub in subprocesses),
            'power_cost': sum(sub.powerCost for sub in subprocesses),
            'total_cost': sum(sub.totalCost for sub in subprocesses)
        }

        # Calculate material wastage cost
        material_wastage_cost = None
        if trim_subprocess and weight_sensor and final_weight_sensor:
            if weight_sensor.actualWeight is not None and final_weight_sensor.finalWeight is not None:
                weight_loss = abs(weight_sensor.actualWeight - final_weight_sensor.finalWeight)
                material_wastage_cost = weight_loss * Decimal('50.865') 

        print("\n=== Final Context Check ===")
        if weight_sensor:
            print(f"Weight sensor actual weight being sent to template: {weight_sensor.actualWeight}")

        # Get user roles
        management, technician, supervisor, admin = get_user_roles(response.user)

        if management or supervisor:
            pro.update_subprocess_positions()
            orderedSubProList = pro.order_subprocess_custom()
            firstCardID = orderedSubProList.first()
            lastCardID = orderedSubProList.last()
            machine_name = _get_machine_name(orderedSubProList)

            context = {
                'process': pro,
                'current_weight': current_weight,
                'weight_sensor': weight_sensor,
                'final_weight_sensor': final_weight_sensor,
                'orderedSubProList': orderedSubProList,
                'firstCardID': firstCardID,
                'lastCardID': lastCardID,
                'machine_name': machine_name,
                'total_interface_time': timedelta(seconds=totals['interface_time']),
                'total_process_time': timedelta(seconds=totals['process_time']),
                'total_material_wastage': totals['material_wastage'],
                'total_labour_cost': totals['labour_cost'],
                'total_power_cost': totals['power_cost'],
                'total_cost': totals['total_cost'],
                'material_wastage_cost': material_wastage_cost,
                'management': management,
                'supervisor': supervisor,
                'technician': technician,
                'admin': admin,
                'ply_instances': ["Load and Cut Ply", "Ply Placed", "Ply Waiting", "Ply Removed", 
                              "Pickup Initial Ply", "Pickup Ply & Weld"],
                'blank_instances': ["Blank Placed", "Blank Waiting", "Blank Removed", 
                                "Initialisation", "Heat Mould and Platten Up", 
                                "Blank Loaded in Machine", "Temperature Reached and Platten Down",
                                "Platten Down", "Blank Inside Press", "Blank Pressed"],
                'part_instances': ["Mould Cooling", "Part Released from Mould", 
                               "Machine Returns To Home Location", "Part Leaves Machine",
                               "Part Assessment (Initial Weight)", "Trim",
                               "Part Assessment (Final Weight)", "Part Assessment (Final Geometry)"],
                'process_time_instances': ["Load and Cut Ply", "Pickup Ply & Weld", 
                                       "Heat Mould and Platten Up", "Blank Pressed",
                                       "Mould Cooling", "Trim"]
            }
            return render(response, 'Main/showProcess.html', context)

        elif technician:
            orderedSubProList = pro.order_subprocess()
            firstCard = orderedSubProList.first()
            lastCard = orderedSubProList.last()

            context = {
                'orderedSubProList': orderedSubProList,
                'firstCardID': firstCard.id,
                'lastCardID': lastCard.id,
                'process': pro,
                'management': management,
                'technician': technician,
                'supervisor': supervisor,
                'current_weight': current_weight,
                'weight_sensor': weight_sensor,
                'final_weight_sensor': final_weight_sensor
            }
            return render(response, 'Main/showProcess.html', context)

    except Exception as e:
        print(f"\n=== Error in showProcess ===\n{e}")
        logger.error(f"Error in showProcess: {e}")
        return redirect('/')

def _get_machine_name(subprocesses):
    """Helper function to determine machine name based on subprocess."""
    for sub_process in subprocesses:
        if sub_process.name in ['Load and Cut Ply', 'Take Ply Roll From Storage To Zund']:
            return 'Zund Ply Cutter'
        elif sub_process.name in ['Ply Placed', 'Ply Waiting', 'Pickup Initial Ply', 
                                'Pickup Ply & Weld', 'Blank Placed', 'Blank Waiting', 'Blank Removed']:
            return 'KUKA Robot'
        elif sub_process.name in ["Trim"]:
            return 'UR-10'
        elif sub_process.name in ["Initialisation", "Heat Mould and Platten Up", 
                                "Blank Loaded in Machine", "Temperature Reached and Platten Down",
                                "Platten Down", "Blank Inside Press", "Blank Pressed", 
                                "Mould Cooling", "Part Released from Mould",
                                "Machine Returns To Home Location", "Part Leaves Machine"]:
            return 'Press'
    return None


def initialize_subprocess_parts(pro, processName):
    subProcessPartSet = []
    if pro.partinstance_set.first():
        subProcessPartSet = get_subprocess_parts(pro.partinstance_set.first().part_set.all(), processName,
                                                 subProcessPartSet)
    # if pro.blankinstance_set.first():
    #     subProcessPartSet = get_subprocess_parts(pro.blankinstance_set.first().blank_set.all(), processName,
    #                                              subProcessPartSet)
    # if pro.plyinstance_set.first():
    #     subProcessPartSet = get_subprocess_parts(pro.plyinstance_set.first().ply_set.all(), processName,
    #                                              subProcessPartSet)
    return subProcessPartSet


def get_subprocess_parts(parts, processName, subProcessPartSet):
    for part in parts:
        if ProcessPart.objects.filter(part=part, processName=processName).exists():
            processPart = ProcessPart.objects.get(part=part, processName=processName)
            subProcessPartSet.extend(processPart.subprocesspart_set.all())
    return subProcessPartSet


def get_active_product_subprocesses(user, pro, subProcessPartSet):
    product = ProcessPart.objects.get(id=user.profile.sequence_choice)
    active, piece = get_active_piece(product)
    if active:
        subProcessPartSet.extend(product.subprocesspart_set.all())
    else:
        user.profile.sequence_choice = None
        user.profile.save()
    return subProcessPartSet, product


def get_active_piece(product):
    piece = None
    active = False
    if product.ply and product.ply.plyInst:
        piece = product.ply
        active = True
    elif product.blank and product.blank.blankInstance:
        piece = product.blank
        active = True
    elif product.part and product.part.partInstance:
        piece = product.part
        active = True
    return active, piece



def handle_post_requests(response, pro, form, sensor_form, part_instance_form, select_sensor_form, deletion, addDevice,
                         subProcessPartSet, time_form):
    if response.POST.get('addSubProcess') or response.POST.get('deleteSubProcess'):
        form = addManualSubProcess(pro, response.POST) if pro.project.manual else addSubProcess(pro, response.POST)
        if form.is_valid():
            handle_subprocess_operations(response, pro, form)
    if response.POST.get('addSensor') or response.POST.get('deleteSensor'):
        sensor_form = SensorForm(pro, response.POST)
        if sensor_form.is_valid():
            handle_sensor_operations(response, pro, sensor_form, deletion, select_sensor_form)
    if response.POST.get('addDeviceID'):
        handle_device_addition(response, pro)
    if response.POST.get('deleteSelection'):
        handle_device_deletion(response)
    if response.POST.get('requestHardware'):
        handle_hardware_request(response, pro)
    if response.POST.get('changePartInstance'):
        handle_part_instance_change(response, pro, part_instance_form, subProcessPartSet)
    if response.POST.get('play'):
        handle_subprocess_play(response)
    handle_sensor_time_update(response, pro, time_form)


def handle_subprocess_operations(response, pro, form):
    reqSubProcess = form.cleaned_data['manualName'] if pro.project.manual else form.cleaned_data['name']
    if response.POST.get('addSubProcess'):
        add_subprocess(response, pro, reqSubProcess)
    elif response.POST.get('deleteSubProcess'):
        delete_subprocess(response, pro, reqSubProcess)


def add_subprocess(response, pro, reqSubProcess):
    if pro.subprocess_set.filter(name=reqSubProcess) or pro.subprocess_set.filter(manualName=reqSubProcess):
        messages.error(response, "This Sub Process already exists!")
    else:
        if pro.project.manual:
            processCheck = reqSubProcess in ['material_pressed', 'final_inspection']
            pro.subprocess_set.create(manualName=reqSubProcess, processCheck=processCheck)
        else:
            processCheck = reqSubProcess in ['material_pressed', 'final_inspection']
            pro.subprocess_set.create(name=reqSubProcess, processCheck=processCheck)
        messages.success(response, "Sub Process successfully added!")
        pro.update_subprocess_positions()


def delete_subprocess(response, pro, reqSubProcess):
    try:
        p = pro.subprocess_set.get(manualName=reqSubProcess) if pro.project.manual else pro.subprocess_set.get(
            name=reqSubProcess)
        if pro.name == "Form Preform" and p.manualName in ["Initialisation", "Material Pressed", "Final Inspection"]:
            messages.error(response, "You cannot delete this Sub-Process because it is vital to Form Preform")
        else:
            p.delete()
            messages.success(response, "Sub Process successfully deleted!")
    except:
        messages.error(response, 'Sub Process does not exist!')


def handle_sensor_operations(response, pro, sensor_form, deletion, select_sensor_form):
    reqSensor = sensor_form.cleaned_data['choice']
    if response.POST.get('addSensor'):
        add_sensor(response, pro, reqSensor)
    elif response.POST.get('deleteSensor'):
        delete_sensor(response, pro, reqSensor, deletion, select_sensor_form)


def add_sensor(response, pro, reqSensor):
    if not Sensor.objects.all().filter(name=reqSensor.name).exists():
        sensor = pro.sensor_set.create(name=reqSensor.name, process=pro, modelID="SKXCV" + str(random.randint(0, 999)))
        messages.success(response, "Sensor successfully added!")
    else:
        sensor = Sensor.objects.get(name=reqSensor.name, modelID=reqSensor.modelID)
        if sensor not in pro.sensor_set.all():
            sensor.process = pro
            sensor.save()
            messages.success(response, "Sensor successfully added!")
        else:
            messages.error(response, 'Sensor already exists!')


def delete_sensor(response, pro, reqSensor, deletion, select_sensor_form):
    sensor = pro.sensor_set.filter(name=reqSensor.name).first()
    if pro.sensor_set.filter(name=reqSensor.name).count() > 1:
        messages.error(response, "Select a Sensor to delete!")
        sensorSet = pro.sensor_set.filter(name=reqSensor.name)
        deletion = True
        select_sensor_form = SelectSensorForm(sensorSet, response.POST)
    else:
        sensor.delete()
        messages.success(response, 'Sensor successfully deleted!')


def handle_device_addition(response, pro):
    cleaned_data = Sensor.pro_sensor_choices_dict[response.POST['proName']]
    sensor = pro.sensor_set.create(name=cleaned_data, process=pro, modelID=response.POST['name'])
    messages.success(response, sensor.name + " Successfully Added!")


def handle_device_deletion(response):
    sensor = Sensor.objects.get(modelID=response.POST['choice'])
    sensor.delete()
    messages.success(response, "Sensor successfully deleted!")


def handle_hardware_request(response, pro):
    data = {
        'isok': True,
        'machines': {
            'Ply Cutter': {
                'isok': True,
                'devices': {
                    'Humidity Sensor': {'id': 1, 'isok': True, 'modelID': 'TC-611'},
                    'Pressure Sensor': {'id': 2, 'isok': False, 'modelID': 'PS-219'},
                    'VOC': {'id': 3, 'isok': True, 'modelID': 'US-519'},
                },
                'tiaBlocks': {'block1': {'id': 1}, 'block2': {'id': 2}, 'block3': {'id': 3}},
            },
            'Preforming Cell': {
                'isok': False,
                'devices': {
                    'Thermocouple': {'id': 4, 'isok': True, 'modelID': 'TC-421'},
                    'Pressure Sensor': {'id': 5, 'isok': True, 'modelID': 'PS-311'},
                    'Ultrasonic Sensor': {'id': 6, 'isok': True, 'modelID': 'US-109'},
                    'Power Clamp (Big Cabinet)': {'id': 7, 'isok': True, 'modelID': '3494546ecb06'},
                    'Power Clamp (Kuka Robot)': {'id': 8, 'isok': True, 'modelID': '3494546ed0bd'},
                    'Power Clamp (CNC Router)': {'id': 9, 'isok': True, 'modelID': 'c8c9a37057ca'},
                },
                'tiaBlocks': {'block4': {'id': 4}, 'block5': {'id': 5}, 'block6': {'id': 6}},
            },
        },
    }

    for machineKey in data['machines']:
        machine = get_or_create_machine(response.user.profile.user_company, machineKey)
        for device in data['machines'][machineKey]['devices']:
            device_data = data['machines'][machineKey]['devices'][device]
            sensor = get_or_create_sensor(device_data)
            sensor.machine = machine
            sensor.save()
            if machine in pro.machine.all() and not pro.possiblesensors_set.filter(name=sensor.name,
                                                                                   machine=machine).exists():
                pro.possiblesensors_set.create(name=sensor.name, machine=machine, modelID=sensor.modelID)


def get_or_create_machine(company, machine_name):
    if not company.machine_set.filter(name=machine_name).exists():
        return Machine.objects.create(name=machine_name, company=company)
    return Machine.objects.get(name=machine_name)


def get_or_create_sensor(device_data):
    if not Sensor.objects.filter(id=device_data['id']).exists():
        return Sensor.objects.create(name=device_data['name'], id=device_data['id'], modelID=device_data['modelID'])
    return Sensor.objects.get(id=device_data['id'], modelID=device_data['modelID'])


def handle_part_instance_change(response, pro, part_instance_form, subProcessPartSet):
    part_instance_form = PartInstanceForm(pro, response.POST)
    if part_instance_form.is_valid():
        reqInputClean = part_instance_form.cleaned_data['choice']
        product = get_product_instance(pro, reqInputClean)
        profile = response.user.profile
        profile.sequence_choice = product.id
        profile.save()
        subProcessPartSet.extend(product.subprocesspart_set.all())
        return redirect('/' + str(pro.id))


def get_product_instance(pro, reqInputClean):
    if "Ply" in reqInputClean:
        plyInstance = pro.plyinstance_set.get(instance_id=int(reqInputClean[-1]))
        return plyInstance.ply_set.first().processpart_set.first()
    if "Blank" in reqInputClean:
        blankInstance = pro.blankinstance_set.get(instance_id=int(reqInputClean[-1]))
        return blankInstance.blank_set.first().processpart_set.first()
    if "Part" in reqInputClean:
        partInstance = pro.partinstance_set.get(instance_id=int(reqInputClean[-1]))
        return partInstance.part_set.first().processpart_set.first()


def handle_subprocess_play(response):
    subProcessID = response.POST['play']
    subProcess = SubProcess.objects.get(id=subProcessID)
    if subProcess.operator:
        subProcess.status = 1
        subProcess.jobStart = datetime.now().replace(microsecond=0)
        subProcess.save()
    else:
        messages.error(response, 'Sub process needs an operator!')


def handle_sensor_time_update(response, process, time_form):
    sensor_update_mappings = {
        'changeVOCGraph': 'VOC Sensor',
        'changeTempGraph': 'Thermocouple',
        'changeHumidityGraph': 'Humidity Sensor',
        'changeDustGraph': 'Dust Sensor',
        'changeEnergyGraph': [
            'Power Clamp (Big Oven)',
            'Power Clamp (Big Cabinet)',
            'Power Clamp (Kuka Robot)',
            'Power Clamp (CNC Router)'
        ],
        'changeStrainGraph': 'Strain Gauge',
        'changeNoiseGraph': 'Microphone',
        'changeAccelerationGraph': 'Accelerometer',
    }

    for post_key, sensor_names in sensor_update_mappings.items():
        if response.POST.get(post_key):
            time_form = ChangeGraphTime(response.POST)
            if time_form.is_valid():
                if isinstance(sensor_names, list):
                    for sensor_name in sensor_names:
                        if process.sensor_set.all().filter(name=sensor_name).exists():
                            sensor = process.sensor_set.all().get(name=sensor_name)
                            sensor.averageTime = response.POST['time']
                            sensor.save()
                else:
                    if process.sensor_set.all().filter(name=sensor_names).exists():
                        sensor = process.sensor_set.all().get(name=sensor_names)
                        sensor.averageTime = response.POST['time']
                        sensor.save()


def showProjects(response):
    """View function to display and manage projects."""
    if not response.user.is_authenticated:
        return redirect('/mylogout/')

    management = response.user.groups.filter(name='Management').exists()
    supervisor = response.user.groups.filter(name='Supervisor').exists()
    company = response.user.profile.user_company
    form = CreateNewProject()
    delform = deleteProject(company)

    if not company.project_set.filter(project_name="Manual Project").exists():
        # Create base project
        project = Project.objects.create(
            project_name="Manual Project",
            company=company,
            techRate=Decimal('25.000'),
            superRate=Decimal('35.000'),
            powerRate=Decimal('0.15000'),
            manual=True,
            setUpCost=Decimal('100.00'),
            CO2PerPower=Decimal('0.50'),
            workOrderNumber="MAN-001"
        )

        now = datetime.now()
        current_time = now

        # Create Cut Plies process
        cut_plies = Process.objects.create(
            project=project,
            manualName="Cut Plies",
            position=0
        )

        # Define Cut Plies subprocess data
        cut_plies_subprocesses = [
            {
                'name': "Take Ply Roll From Storage To Zund",
                'operator': "Technician",
                'status': 2,
                'position': 1,
                'jobStart': current_time,
                'jobEnd': current_time + timedelta(minutes=1, seconds=8),
                'interfaceTime': timedelta(minutes=1, seconds=8),
                'processTime': timedelta(minutes=0),
                'labourInput': 200,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=1, seconds=8),
                'technicianLabourCost': Decimal('2.180'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('2.180'),
                'totalCost': Decimal('2.180')
            },
            {
                'name': "Position Material On Cutter Bed",
                'operator': "Technician",
                'status': 2,
                'position': 2,
                'jobStart': current_time + timedelta(minutes=1, seconds=8),
                'jobEnd': current_time + timedelta(minutes=2, seconds=8),
                'interfaceTime': timedelta(minutes=1),
                'processTime': timedelta(minutes=0),
                'labourInput': 200,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=1),
                'technicianLabourCost': Decimal('1.930'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('1.930'),
                'totalCost': Decimal('1.930')
            },
            {
                'name': "Cut Ply Shapes",
                'operator': "Technician",
                'status': 2,
                'position': 3,
                'jobStart': current_time + timedelta(minutes=2, seconds=8),
                'jobEnd': current_time + timedelta(minutes=3, seconds=23),
                'interfaceTime': timedelta(minutes=0),
                'processTime': timedelta(minutes=1, seconds=15),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.250000'),
                'CO2': Decimal('0.06000'),
                'technicianLabour': timedelta(minutes=1, seconds=15),
                'technicianLabourCost': Decimal('1.210'),
                'materialPartCost': Decimal('22.580'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('11.080'),
                'materialWastage': Decimal('33.660'),
                'powerCost': Decimal('0.080'),
                'labourSumCost': Decimal('1.210'),
                'totalCost': Decimal('34.950')
            },
            {
                'name': "Inspect Cut Ply Shapes",
                'operator': "Technician",
                'status': 2,
                'position': 4,
                'jobStart': current_time + timedelta(minutes=3, seconds=23),
                'jobEnd': current_time + timedelta(minutes=3, seconds=38),
                'interfaceTime': timedelta(seconds=15),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('3.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(seconds=15),
                'technicianLabourCost': Decimal('0.240'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.680'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('0.240'),
                'totalCost': Decimal('0.920')
            },
            {
                'name': "De-bed Material",
                'operator': "Technician",
                'status': 2,
                'position': 5,
                'jobStart': current_time + timedelta(minutes=3, seconds=38),
                'jobEnd': current_time + timedelta(minutes=4, seconds=8),
                'interfaceTime': timedelta(seconds=30),
                'processTime': timedelta(minutes=0),
                'labourInput': 200,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(seconds=30),
                'technicianLabourCost': Decimal('0.970'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('0.970'),
                'totalCost': Decimal('0.970')
            },
            {
                'name': "Return Ply Roll To Storage",
                'operator': "Technician",
                'status': 2,
                'position': 6,
                'jobStart': current_time + timedelta(minutes=4, seconds=8),
                'jobEnd': current_time + timedelta(minutes=5, seconds=16),
                'interfaceTime': timedelta(minutes=1, seconds=8),
                'processTime': timedelta(minutes=0),
                'labourInput': 200,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=1, seconds=8),
                'technicianLabourCost': Decimal('2.180'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('2.180'),
                'totalCost': Decimal('2.180')
            }
        ]

        # Create Cut Plies subprocesses
        for subprocess_data in cut_plies_subprocesses:
            subprocess_data['process'] = cut_plies
            SubProcess.objects.create(**subprocess_data)

        # Update current_time after Cut Plies process
        current_time = current_time + timedelta(minutes=5, seconds=16)

        # Create Create Blanks process
        create_blanks = Process.objects.create(
            project=project,
            manualName="Create Blanks",
            position=1
        )

        # Define Create Blanks subprocess data
        blanks_subprocesses = [
            {
                'name': "Form Plies Into Stack",
                'operator': "Technician",
                'status': 2,
                'position': 1,
                'jobStart': current_time,
                'jobEnd': current_time + timedelta(minutes=2),
                'interfaceTime': timedelta(minutes=2),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=2),
                'technicianLabourCost': Decimal('1.930'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('1.930'),
                'totalCost': Decimal('1.930')  
            },
            {
                'name': "Add Release Film",
                'operator': "Technician",
                'status': 2,
                'position': 2,
                'jobStart': current_time + timedelta(minutes=2),
                'jobEnd': current_time + timedelta(minutes=5),
                'interfaceTime': timedelta(minutes=3),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=3),
                'technicianLabourCost': Decimal('2.900'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('2.900'),
                'totalCost': Decimal('2.900') 
            },
            {
                'name': "Clip Stack Into Cassette",
                'operator': "Technician",
                'status': 2,
                'position': 3,
                'jobStart': current_time + timedelta(minutes=5),
                'jobEnd': current_time + timedelta(minutes=8),
                'interfaceTime': timedelta(minutes=3),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=3),
                'technicianLabourCost': Decimal('2.900'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('2.900'),
                'totalCost': Decimal('2.900') 
            }
        ]

        # Create Create Blanks subprocesses
        for subprocess_data in blanks_subprocesses:
            subprocess_data['process'] = create_blanks
            SubProcess.objects.create(**subprocess_data)

                # 3. Form Preform process
        form_preform = Process.objects.create(
            project=project,
            manualName="Form Preform",
            position=2
        )

        # Create Form Preform subprocesses
        form_preform_subprocesses = [
            {
                'name': "Heat Tool",
                'operator': "Technician",
                'status': 2,
                'position': 1,
                'jobStart': current_time,
                'jobEnd': current_time + timedelta(minutes=20, seconds=30),
                'interfaceTime': timedelta(seconds=30),
                'processTime': timedelta(minutes=20),
                'labourInput': 2.44,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('12.000000'),
                'CO2': Decimal('2.90000'),
                'technicianLabour': timedelta(minutes=20, seconds=30),
                'technicianLabourCost': Decimal('0.480'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),  
                'powerCost': Decimal('3.700'),
                'labourSumCost': Decimal('0.480'),
                'totalCost': Decimal('4.180')
            }, 
            {
                'name': "Move Cassette To Press",
                'operator': "Technician",
                'status': 2,
                'position': 2,
                'jobStart': current_time + timedelta(minutes=20, seconds=30),
                'jobEnd': current_time + timedelta(minutes=22, seconds=30),
                'interfaceTime': timedelta(minutes=2),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=2),
                'technicianLabourCost': Decimal('1.930'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('1.930'),
                'totalCost': Decimal('1.930')
            },
            {
                'name': "Position Cassette in Press Between Tools",
                'operator': "Technician",
                'status': 2,
                'position': 3,
                'jobStart': current_time + timedelta(minutes=22, seconds=30),
                'jobEnd': current_time + timedelta(minutes=23, seconds=30),
                'interfaceTime': timedelta(minutes=1),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=1),
                'technicianLabourCost': Decimal('0.970'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('0.970'),
                'totalCost': Decimal('0.970')
            },
            {
                'name': "Press Part",
                'operator': "Technician",
                'status': 2,
                'position': 4,
                'jobStart': current_time + timedelta(minutes=23, seconds=30),
                'jobEnd': current_time + timedelta(minutes=25, seconds=30),
                'interfaceTime': timedelta(minutes=0),
                'processTime': timedelta(minutes=2),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.700000'),
                'CO2': Decimal('0.17000'),
                'technicianLabour': timedelta(minutes=2),
                'technicianLabourCost': Decimal('1.930'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.220'),
                'labourSumCost': Decimal('1.930'),
                'totalCost': Decimal('2.150')
            },
            {
                'name': "Cool Tool",
                'operator': "Technician",
                'status': 2,
                'position': 5,
                'jobStart': current_time + timedelta(minutes=25, seconds=30),
                'jobEnd': current_time + timedelta(minutes=66),
                'interfaceTime': timedelta(minutes=40),
                'processTime': timedelta(seconds=0),
                'labourInput': 1.23,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('2.000000'),
                'CO2': Decimal('0.48000'),
                'technicianLabour': timedelta(minutes=40, seconds=30),
                'technicianLabourCost': Decimal('0.480'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.620'),
                'labourSumCost': Decimal('0.480'),
                'totalCost': Decimal('1.100')
            },
            {
                'name': "Extract From Hydraulic Press",
                'operator': "Technician",
                'status': 2,
                'position': 6,
                'jobStart': current_time + timedelta(minutes=66),
                'jobEnd': current_time + timedelta(minutes=68),
                'interfaceTime': timedelta(minutes=2),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=2),
                'technicianLabourCost': Decimal('1.930'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('1.930'),
                'totalCost': Decimal('1.930')
            }
        ]

        # Create Form Preform subprocesses
        for subprocess_data in form_preform_subprocesses:
            subprocess_data['process'] = form_preform
            SubProcess.objects.create(**subprocess_data)

        # Create Final Inspection process
        final_inspection = Process.objects.create(
            project=project,
            manualName="Final Inspection",
            position=3
        )

        # Define subprocesses for Final Inspection
        final_inspection_subprocesses = [
            {
                'name': "Inspect Product For Defects",
                'operator': "Technician",
                'status': 2,
                'position': 1,
                'jobStart': current_time,
                'jobEnd': current_time + timedelta(minutes=3),
                'interfaceTime': timedelta(minutes=3),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('5.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=3),
                'technicianLabourCost': Decimal('2.900'),
                'supervisorLabourCost': Decimal('2.900'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('2.990'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('2.990'),  
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('5.800'), 
                'totalCost': Decimal('8.890')  
            },
            {
                'name': "Weigh Initial Product",
                'operator': "Technician",
                'status': 2,
                'position': 2,
                'jobStart': current_time + timedelta(minutes=3),
                'jobEnd': current_time + timedelta(minutes=5),
                'interfaceTime': timedelta(minutes=2),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('1.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=2),
                'technicianLabourCost': Decimal('1.930'),
                'supervisorLabourCost': Decimal('0.000'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('1.930'),
                'totalCost': Decimal('1.930') 
            },
            {
                'name': "Trim To Shape",
                'operator': "Technician",
                'status': 2,
                'position': 3,
                'jobStart': current_time + timedelta(minutes=5),
                'jobEnd': current_time + timedelta(minutes=35),
                'interfaceTime': timedelta(minutes=0),
                'processTime': timedelta(minutes=30),
                'labourInput': 100,
                'scrapRate': Decimal('0.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=30),
                'technicianLabourCost': Decimal('14.500'),
                'supervisorLabourCost': Decimal('0.000'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.000'),
                'materialWastageCost': Decimal('21.970'),
                'materialWastage': Decimal('21.970'), 
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('14.500'),
                'totalCost': Decimal('36.470')  
            },
            {
                'name': "Weigh Final Product",
                'operator': "Technician",
                'status': 2,
                'position': 4,
                'jobStart': current_time + timedelta(minutes=35),
                'jobEnd': current_time + timedelta(minutes=37),
                'interfaceTime': timedelta(minutes=2),
                'processTime': timedelta(minutes=0),
                'labourInput': 100,
                'scrapRate': Decimal('1.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=2),
                'technicianLabourCost': Decimal('0.970'),
                'supervisorLabourCost': Decimal('0.000'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.160'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'), 
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('0.970'),
                'totalCost': Decimal('1.130')  
            },
            {
                'name': "Check Final Geometry with Checking Template",
                'operator': "Technician",
                'status': 2,
                'position': 5,
                'jobStart': current_time + timedelta(minutes=37),
                'jobEnd': current_time + timedelta(minutes=47),
                'interfaceTime': timedelta(minutes=0),
                'processTime': timedelta(minutes=10),
                'labourInput': 100,
                'scrapRate': Decimal('5.000'),
                'batchSize': Decimal('2.000'),
                'power': Decimal('0.000000'),
                'CO2': Decimal('0.00000'),
                'technicianLabour': timedelta(minutes=10),
                'technicianLabourCost': Decimal('4.830'),
                'supervisorLabourCost': Decimal('4.830'),
                'materialPartCost': Decimal('0.000'),
                'materialScrapCost': Decimal('0.790'),
                'materialWastageCost': Decimal('0.000'),
                'materialWastage': Decimal('0.000'),  
                'powerCost': Decimal('0.000'),
                'labourSumCost': Decimal('9.660'), 
                'totalCost': Decimal('10.450')  
            }
        ]

        # Create Final Inspection subprocesses
        for subprocess_data in final_inspection_subprocesses:
            subprocess_data['process'] = final_inspection
            SubProcess.objects.create(**subprocess_data)

    projects = company.project_set.all()

    if management or supervisor:
        if response.method == 'POST':
            if response.user.has_perm('Main.edit_project'):
                if response.POST.get('addProject'):
                    form = CreateNewProject(response.POST)
                    if form.is_valid():
                        name = form.cleaned_data['name']
                        manual = form.cleaned_data['manual']
                        
                        if company.project_set.filter(project_name=name).exists():
                            messages.error(response, 'Project already in list!')
                        else:
                            Project.objects.create(
                                project_name=name,
                                company=company,
                                techRate=Decimal('25.000'),
                                superRate=Decimal('35.000'),
                                powerRate=Decimal('0.15000'),
                                manual=manual,
                                setUpCost=Decimal('100.00'),
                                CO2PerPower=Decimal('0.50'),
                                workOrderNumber="MAN-001"
                            )

                elif response.POST.get('deleteProject'):
                    delform = deleteProject(company, response.POST)
                    if delform.is_valid():
                        name = delform.cleaned_data['choice']
                        try:
                            project = company.project_set.get(project_name=name)
                            project.delete()
                            messages.success(response, 'Project successfully deleted!')
                        except:
                            messages.error(response, 'Project not in list!')
            else:
                messages.error(response, 'You do not have permission for this action!')

        return render(response, 'Main/showProjects.html', {
            'delform': delform,
            'form': form,
            'management': management,
            'supervisor': supervisor,
            'company': company,
            'projects': projects
        })
    
    elif response.user.groups.filter(name='Technician').exists():
        return render(response, 'Main/showProjects.html', {
            'management': management,
            'supervisor': supervisor,
            'company': company,
            'projects': projects
        })
    
    return redirect

from decimal import Decimal
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def format_timedelta(td):
    """Format timedelta into HH:MM:SS string."""
    if not td:
        return "0:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}"

def safe_value(value, value_type='decimal'):
    """Convert value to Decimal or timedelta safely"""
    if value_type == 'decimal':
        try:
            return Decimal(str(value or '0'))
        except (ValueError, TypeError):
            return Decimal('0')
    else:  # timedelta
        if isinstance(value, timedelta):
            return value
        try:
            hours, minutes, seconds = map(int, value.split(':'))
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except:
            return timedelta()
def aggregate_process_data(process):
    """Calculate totals for a process"""
    totals = {
        'interface_time': timedelta(),
        'process_time': timedelta(),
        'material_wastage': Decimal('0'),
        'labour_cost': Decimal('0'),
        'power_cost': Decimal('0'),
        'total_cost': Decimal('0')
    }

    process_time_instances = [
        "Load and Cut Ply", "Pickup Ply & Weld", 
        "Heat Tool", "Press Part", "Blank Pressed",
        "Trim", "Mould Cooling"
    ]

    for subprocess in process.subprocess_set.all():
        try:
            # Handle time calculations based on subprocess type
            if subprocess.interfaceTime:
                totals['interface_time'] += subprocess.interfaceTime

            if subprocess.processTime and subprocess.name in process_time_instances:
                totals['process_time'] += subprocess.processTime

            # Handle special case for Form Preform process
            if process.name == 'Form Preform' and subprocess.name == 'Heat Tool':
                totals['process_time'] = subprocess.processTime
                if subprocess.jobStart and subprocess.jobEnd:
                    total_time = subprocess.jobEnd - subprocess.jobStart
                    totals['interface_time'] = total_time - subprocess.processTime

            # Handle costs - using safe decimal conversion
            totals['material_wastage'] += safe_decimal(subprocess.materialWastage)
            totals['labour_cost'] += safe_decimal(subprocess.labourSumCost)
            totals['power_cost'] += safe_decimal(subprocess.powerCost)
            totals['total_cost'] += safe_decimal(subprocess.totalCost)

        except Exception as e:
            logger.error(f"Error processing {subprocess.name}: {str(e)}")
            continue

    return totals

def safe_decimal(value):
    """Convert value to Decimal safely"""
    try:
        if value is None:
            return Decimal('0')
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0')

def prepare_process_data(processes):
    """Update processes with calculated totals"""
    try:
        for process in processes:
            totals = aggregate_process_data(process)
            # Set formatted values
            process_values = {
                'interfaceTime': format_timedelta(totals['interface_time']),
                'processTime': format_timedelta(totals['process_time']),
                'materialWastage': f"{totals['material_wastage']:.3f}",
                'labourSumCost': f"{totals['labour_cost']:.3f}",
                'powerCost': f"{totals['power_cost']:.3f}",
                'totalCost': f"{totals['total_cost']:.3f}"
            }
            for key, value in process_values.items():
                setattr(process, key, value)
    except Exception as e:
        logger.error(f"Error preparing process data: {str(e)}")
    return processes

def calculate_total_values(processes):
    """Calculate grand totals for all processes"""
    totals = {
        'interface_time': timedelta(),
        'process_time': timedelta(),
        'material_wastage': Decimal('0'),
        'labour_cost': Decimal('0'),
        'power_cost': Decimal('0'),
        'total_cost': Decimal('0')
    }

    for process in processes:
        # Add time values
        totals['interface_time'] += safe_value(process.interfaceTime, 'time')
        totals['process_time'] += safe_value(process.processTime, 'time')
        # Add cost values
        for field, key in [
            ('materialWastage', 'material_wastage'),
            ('labourSumCost', 'labour_cost'),
            ('powerCost', 'power_cost'),
            ('totalCost', 'total_cost')
        ]:
            totals[key] += safe_value(getattr(process, field))

    return {
        'total_interface_time': format_timedelta(totals['interface_time']),
        'total_process_time': format_timedelta(totals['process_time']),
        'total_material_wastage': f"{totals['material_wastage']:.3f}",
        'total_labour_cost': f"{totals['labour_cost']:.3f}",
        'total_power_cost': f"{totals['power_cost']:.3f}",
        'total_cost': f"{totals['total_cost']:.3f}"
    }

from django.shortcuts import redirect, render, HttpResponse
from decimal import Decimal
from .forms import (
    ConstForm, addManualProcess, addProcess, AddMaterialForm,
    ProjectPartInstanceForm, ProcessWindowForm, ProjectConstants
)

from django.shortcuts import redirect, render, HttpResponse
from decimal import Decimal

def showAllProcess(request, id):
    if not request.user.is_authenticated:
        return redirect('/mylogout/')
    
    try:
        project = Project.objects.get(id=id)
        if project not in request.user.profile.user_company.project_set.all():
            return redirect('/')
        
        # Set user role
        group = next((g for g in ['Management', 'Supervisor', 'Technician']
                   if request.user.groups.filter(name=g).exists()), 'Technician')
        
        # Prepare context
        context = {
            'selected_project': project,
            'management': False,  # Set both to False by default
            'supervisor': True,
            'partInstance': '',
            'const_form': ConstForm(group=group),
            'form': addManualProcess() if project.manual else addProcess(project),
            'material_form': AddMaterialForm(),
            'project_part_instance_form': ProjectPartInstanceForm(project),
            'process_window_form': ProcessWindowForm(),
        }

        # Set the appropriate flag based on group - PUT HERE
        if group == 'Management':
            context['management'] = True
        elif group == 'Supervisor':
            context['supervisor'] = True
        
        # Handle form submission
        if request.method == 'POST' and 'changeConst' in request.POST:
            if group in ['Management', 'Supervisor']:
                handle_const_change(request, project, context)
            else:
                context['error1'] = "Permission denied. Only Management and Supervisor can modify values."
        
        # Update process data
        ordered_processes = project.order_process_custom()
        context['orderedProList'] = prepare_process_data(ordered_processes)
        context['lastProcess'] = ordered_processes.last()
        context.update(calculate_total_values(ordered_processes))
        
        return render(request, 'Main/showAllProcess.html', context)
    
    except Project.DoesNotExist:
        return redirect('/')
    except Exception as e:
        print(f"Error: {str(e)}")
        return HttpResponse(status=500)

def handle_post_request(request, project, context):
    """Handle various POST requests for process management"""
    group = next((g for g in ['Management', 'Supervisor'] 
                 if request.user.groups.filter(name=g).exists()), None)
    
    post_type = get_post_type(request.POST)
    
    # Check permissions based on group
    if post_type == 'changeConst':
        if group in ['Management', 'Supervisor']:
            handle_const_change(request, project, context)
        else:
            context['error1'] = "Permission denied. Only Management and Supervisor can modify values."
    elif post_type == 'process_action':
        handle_process_action(request, project, context)
    elif post_type == 'material':
        handle_material_update(request, project)
    elif post_type == 'processWindow':
        handle_process_window(request, project)
    elif post_type == 'selectPartInstance':
        handle_part_instance(request, project, context)
    elif post_type == 'AutoFill':
        handle_auto_fill(request, project)
    else:
        context['error1'] = "Invalid request type"

def handle_const_change(request, project, context):
    """Handle form submission for changing project constants"""
    user_group = next(
        (group for group in ['Management', 'Supervisor']
         if request.user.groups.filter(name=group).exists()),
        None
    )

    if not user_group:
        context['error1'] = "Permission denied. Only Management and Supervisor can modify values."
        return

    const_form = ConstForm(group=user_group, data=request.POST)
    if not const_form.is_valid():
        context['error1'] = "Please enter a valid value"
        return

    try:
        choice = const_form.cleaned_data['choice']
        value = const_form.cleaned_data['value']
        
        field_name = ProjectConstants.get_field_name(user_group, choice)
        if not field_name or not hasattr(project, field_name):
            context['error1'] = "Invalid selection"
            return

        # Validate value based on user group
        if user_group == 'Management':
            # Management can change any value
            pass
        elif user_group == 'Supervisor':
            # Add any specific validation for Supervisor if needed
            pass

        setattr(project, field_name, value)
        project.save()
        
        context['const_form'] = ConstForm(group=user_group)
        context['success_message'] = f"Value updated successfully"
        
    except Exception as e:
        context['error1'] = "Error updating value"
        print(f"Error updating constant: {str(e)}")



def get_post_type(post_data):
    """Determine type of POST request"""
    process_action_keys = {'addProcess', 'deleteProcess', 'status', 'stopStatus', 'play'}
    other_action_keys = {'changeConst', 'material', 'processWindow', 'selectPartInstance', 'AutoFill'}
    
    if any(key in post_data for key in process_action_keys):
        return 'process_action'
    
    for key in other_action_keys:
        if key in post_data:
            return key
    
    return None


def handle_process_action(response, project, context):
    """Handle process-related actions (add/delete/status changes)"""
    if response.POST.get('addProcess') or response.POST.get('deleteProcess'):
        form = (addManualProcess(response.POST) if project.manual 
               else addProcess(project, response.POST))
        
        if form.is_valid():
            process_name = (Process.manual_process_dict[form.cleaned_data['manualName']] 
                          if project.manual else form.cleaned_data['choice'])
            
            if response.POST.get('addProcess'):
                handle_process_add(project, process_name)
            else:
                handle_process_delete(project, process_name)

    # Handle status changes
    status_actions = {
        'status': 2,
        'stopStatus': 3,
        'play': 1
    }
    
    for action, status in status_actions.items():
        if process_id := response.POST.get(action):
            process = Process.objects.get(id=process_id)
            process.status = status
            process.save()


def handle_material_update(response, project):
    """Handle material updates"""
    form = AddMaterialForm(response.POST)
    if form.is_valid():
        update_project_material(project, form)

def handle_process_window(response, project):
    """Handle process window updates"""
    form = ProcessWindowForm(response.POST)
    if form.is_valid():
        project.processWindow = form.cleaned_data['value']
        project.save()

def handle_part_instance(response, project, context):
    """Handle part instance selection"""
    form = ProjectPartInstanceForm(project, response.POST)
    if form.is_valid():
        context['partInstance'] = form.cleaned_data['choice']
    else:
        messages.error(response, 'Invalid part instance selection')

def handle_auto_fill(response, project):
    """Handle auto-fill functionality"""
    messages.success(response, "Data successfully auto-filled!")
    set_default_project_values(project)
    project.save()


def showSubProcess(response, id):
    """View to show and allow the addition or deletion of components"""
    # setup
    # check sub pro belongs to user company
    if response.user.is_authenticated:
        sub_pro = SubProcess.objects.get(id=id)
        deletion, final = False, False
        name = response.user.profile.user_company.company_name
        if sub_pro.name == "Final Inspection" or sub_pro.manualName == "Final Inspection":
            final = True
        sName = ""
        if sub_pro.process.project.manual:
            sName = sub_pro.manualName
        else:
            sName = sub_pro.name
        # setup
        weightForm = EnterPartWeight()
        input_form = addManualInfo()
        input_time_form = addManualTimeInfo()
        sensor_form = SensorForm(sub_pro.process)
        machine_form = MachineForm()
        prev_material_form = PreviousMaterialForm()
        imageForm = ImageUploadForm()
        fileForm = FileUploadForm()
        if sub_pro.process.project.manual:
            sub_master_form = SubMasterForm(sub_pro.manualName)
        else:
            sub_master_form = SubMasterForm(sub_pro.name)
        operator_form = operatorForm(name)
        management, supervisor = False, False

        if deletion == False:
            sensorSet = Sensor.objects.none()
            select_sensor_form = SelectSensorForm(sensorSet)

        if response.user.groups.filter(name='Management').exists():
            management = True
        if response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        if sub_pro.process.project.company == response.user.profile.user_company:
            if management or supervisor:
                if response.method == 'POST':
                    # permission check
                    if response.user.has_perm('Main.edit_sub_process'):
                        # check response type
                        if sub_pro.partInstance != None or sub_pro.startPoint:
                            if response.POST.get('addPreCost'):
                                prev_material_form = PreviousMaterialForm(response.POST)
                                if prev_material_form.is_valid():
                                    sub_pro.materialWastageCost = prev_material_form.cleaned_data['value']
                                    sub_pro.save()
                            if response.POST.get('addManual'):
                                if User.objects.filter(username=sub_pro.operator).exists():
                                    input_form = addManualInfo(response.POST)
                                    if input_form.is_valid():
                                        # read and clean input
                                        reqInputDirty = input_form.cleaned_data['task']
                                        reqInput = SubProcess.manual_input_dict[reqInputDirty]
                                        inputValue = input_form.cleaned_data['value']

                                        # save to model
                                        setattr(sub_pro, reqInput, inputValue)
                                        sub_pro.save()
                                        messages.success(response, "Value Successfully changed!")

                                        # update parent process values
                                        if reqInputDirty == 'BAT':
                                            sub_pro.process.updateBatchSize()

                                        elif reqInputDirty == 'SCR':
                                            sub_pro.process.updateScrapRate()

                                        elif reqInputDirty == 'LAB':
                                            sub_pro.process.updateLabourInput()

                                        elif reqInputDirty == 'POR':
                                            sub_pro.updateSubCO2()
                                            sub_pro.process.updatePowerCon()

                                        # sets start and end times for process (min and max of sub process's)
                                        sub_pro.process.updateProcessStartEnd()

                                        # update costs
                                        sub_pro.updateSubCosts()
                                        sub_pro.process.updateProcessCosts()
                                    else:
                                        messages.error(response, "Invalid input!")
                                else:
                                    messages.error(response, 'Sub Process needs operator')
                            # check response type
                            if response.POST.get('addManualTime'):
                                if User.objects.filter(username=sub_pro.operator).exists():
                                    input_time_form = addManualTimeInfo(response.POST)
                                    if input_time_form.is_valid():
                                        # read and clean task and value
                                        reqInputDirty = input_time_form.cleaned_data['task']
                                        reqInput = sub_pro.manual_input_time_dict[reqInputDirty]
                                        inputValue = datetime.now().replace(microsecond=0)
                                        valid = False

                                        # set to model and save
                                        if sub_pro.jobStart == None or sub_pro.jobEnd == None:
                                            valid = True
                                        else:
                                            if inputValue.timestamp() - sub_pro.jobStart.timestamp() < 0:
                                                messages.error(response, "You cannot end the job before Job Start!")
                                                sub_pro.jobStart = None
                                                sub_pro.jobEnd = None
                                                sub_pro.save()
                                                valid = False

                                            if sub_pro.jobEnd != None:
                                                valid = True

                                        if valid == True:
                                            setattr(sub_pro, reqInput, inputValue)
                                            # save changes
                                            sub_pro.save()

                                            # sets start and end times for process (min and max of sub process's)
                                            sub_pro.process.updateProcessStartEnd()

                                            # update costs
                                            sub_pro.updateSubCosts()
                                            sub_pro.process.updateProcessCosts()

                                            if final == True:
                                                return redirect('/finalInspection' + str(sub_pro.id))
                                            else:
                                                return redirect('/c' + str(sub_pro.id))
                                else:
                                    messages.error(response, 'Sub Process needs operator')
                        else:
                            messages.error(response, "Warning: This Sub-Process is not active!")
                        # check to stop sensorform.is_valid displaying error on other form
                        if (response.POST.get('addSensor') or response.POST.get('deleteSensor')):
                            sensor_form = SensorForm(sub_pro.process, response.POST)
                            if sensor_form.is_valid():
                                # read in and clean sensor name
                                reqSensor = sensor_form.cleaned_data['choice']

                                # check response type
                                if response.POST.get('addSensor'):
                                    # check if sensor exists and show error

                                    s = Sensor.objects.get(name=reqSensor.name, modelID=reqSensor.modelID)

                                    if not s in sub_pro.sensor_set.all():
                                        sub_pro.sensor_set.add(s)
                                        messages.success(response, 'Sensor successfully added!')
                                    else:
                                        messages.error(response, 'Sensor already exists!')
                                # check response type
                                elif response.POST.get('deleteSensor'):
                                    # if sensor exists delete
                                    try:
                                        sensor = sub_pro.sensor_set.filter(name=reqSensor.name).first()

                                        if len(sub_pro.sensor_set.filter(name=reqSensor.name)) > 1:
                                            messages.error(response, "Select a Sensor to delete!")
                                            sensorSet = sub_pro.sensor_set.filter(name=reqSensor.name)
                                            deletion = True
                                            select_sensor_form = SelectSensorForm(sensorSet, response.POST)
                                        else:
                                            sensor.delete()

                                            messages.success(response, 'Sensor successfully deleted!')
                                    except:
                                        messages.error(response, "Sensor does not exist!")
                        # if sensor doesnt exist show error

                        # messages.error(response, 'Sensor does not exist!')

                        # check to stop machineform.is_valid displaying error on other form
                        if (response.POST.get('addMachine') or response.POST.get('delMachine')):
                            machine_form = MachineForm(response.POST)
                            if machine_form.is_valid():
                                # read in machine name
                                reqMachineDirty = machine_form.cleaned_data['name']
                                reqMachine = Machine.machine_choices_dict[reqMachineDirty]
                                process = sub_pro.process
                                # check response type
                                if response.POST.get('addMachine'):
                                    if Machine.objects.filter(name=reqMachine).exists():
                                        # if machine exists show error
                                        if sub_pro.plyCutter != None and sub_pro.plyCutter.name == reqMachine:
                                            # error2 = "Ply cutter already exists! \n"
                                            messages.error(response, 'Ply Cutter has already been assigned!')
                                        elif sub_pro.sortPickAndPlace != None and sub_pro.sortPickAndPlace.name == reqMachine:
                                            messages.error(response, "Pick and Place (sorts) already exists!")
                                        elif sub_pro.blanksPickAndPlace != None and sub_pro.blanksPickAndPlace.name == reqMachine:
                                            messages.error(response, "Pick and Place (blanks) already exists!")
                                        elif sub_pro.preformCell != None and sub_pro.preformCell.name == reqMachine:
                                            messages.error(response, "Preforming Cell already exists!")
                                        else:
                                            if (reqMachine == "Ply Cutter"):
                                                setattr(sub_pro, 'plyCutter', Machine.objects.get(name=reqMachine))
                                            elif (reqMachine == "Pick and Place (sort)"):
                                                setattr(sub_pro, 'sortPickAndPlace',
                                                        Machine.objects.get(name=reqMachine))
                                            elif (reqMachine == "Pick and Place (blanks)"):
                                                setattr(sub_pro, 'blanksPickAndPlace',
                                                        Machine.objects.get(name=reqMachine))
                                            elif (reqMachine == "Preforming Cell"):
                                                setattr(sub_pro, 'preformCell', Machine.objects.get(name=reqMachine))
                                            sub_pro.save()
                                            messages.success(response, 'Machine successfully added!')

                                    else:

                                        # if machine doesnt exist create and show success

                                        Machine.objects.create(name=reqMachine)

                                        if (reqMachine == "Ply Cutter"):
                                            setattr(sub_pro, 'plyCutter', Machine.objects.get(name=reqMachine))
                                        elif (reqMachine == "Pick and Place (sort)"):
                                            setattr(sub_pro, 'sortPickAndPlace', Machine.objects.get(name=reqMachine))
                                        elif (reqMachine == "Pick and Place (blanks)"):
                                            setattr(sub_pro, 'blanksPickAndPlace', Machine.objects.get(name=reqMachine))
                                        elif (reqMachine == "Preforming Cell"):
                                            setattr(sub_pro, 'preformCell', Machine.objects.get(name=reqMachine))
                                        sub_pro.save()

                                        messages.success(response, 'Machine successfully added!')
                                # check response type
                                elif response.POST.get('delMachine'):

                                    # if machine exists delete
                                    try:
                                        Machine.objects.get(name=reqMachine).delete()
                                        messages.success(response, 'Machine successfully deleted!')
                                        return redirect('/' + str(process.id))
                                    except:
                                        messages.error(response, "Machine does not exist!")
                        if response.POST.get('ChangeOP'):

                            operator_form = operatorForm(name, response.POST)
                            choiceDirty = ""
                            if operator_form.is_valid():
                                choice = operator_form.cleaned_data['choice']

                            setattr(sub_pro, 'operator', choice.user.username)
                            sub_pro.save()

                            # sets start and end times for process (min and max of sub process's)
                            sub_pro.process.updateProcessStartEnd()

                            # update costs
                            sub_pro.updateSubCosts()
                            sub_pro.process.updateProcessCosts()

                            if final == True:
                                return redirect('/finalInspection' + str(sub_pro.id))
                            else:
                                return redirect('/c' + str(sub_pro.id))

                        if response.POST.get('deleteSelection'):
                            sensor = Sensor.objects.get(modelID=response.POST['choice'])

                            sensor.delete()
                            messages.success(response, "Sensor successfully deleted!")

                        if response.POST.get(
                                'ChangeSubMaster'):  # used to change specific subprocess fields within components page
                            if sub_pro.process.project.manual:
                                name = sub_pro.manualName
                            else:
                                name = sub_pro.name
                            sub_master_form = SubMasterForm(name, response.POST)
                            if sub_master_form.is_valid():
                                choiceDirty = sub_master_form.cleaned_data['choice']
                                if sub_pro.manualName == "Material Pressed Inside Press":
                                    choiceClean = SubProcess.material_in_press_dict[choiceDirty]
                                elif sub_pro.manualName == "Material Pressed":
                                    choiceClean = SubProcess.material_pressed_dict[choiceDirty]
                                elif sub_pro.manualName == "Removal End effector actuated":
                                    choiceClean = SubProcess.removal_effector_dict[choiceDirty]
                                elif sub_pro.manualName == "Final Inspection" or sub_pro.name == "Final Inspection":
                                    choiceClean = SubProcess.trimming_dict[choiceDirty]

                                value = sub_master_form.cleaned_data['value']

                                setattr(sub_pro, choiceClean, value)
                                sub_pro.save()
                                sub_pro.updateSubCosts()
                                sub_pro.process.updateProcessCosts()

                                if final == True:
                                    return redirect('/finalInspection' + str(sub_pro.id))
                                else:
                                    return redirect('/c' + str(sub_pro.id))

                        # check to stop machineform.is_valid displaying error on other form
                        if response.POST.get('addWeight'):
                            weightForm = EnterPartWeight(response.POST)
                            if weightForm.is_valid():
                                weight = weightForm.cleaned_data['value']
                                sub_pro.preTrimWeight = weight
                                sub_pro.save()
                                scale = sub_pro.sensor_set.get(name='Scale')
                                scale.preTrimWeight = weight
                                scale.save()

                        if response.POST.get('addFile'):
                            file_upload_view(response, sub_pro)

                        if response.POST.get('addImage'):
                            image_upload_view(response, sub_pro)



                    else:
                        # show permission error
                        messages.error(response, 'You do not have permission for this action!')
                if final == True:

                    return render(response, 'Main/finalInspection.html',
                                  {'deletion': deletion, 'imageForm': imageForm, 'fileForm': fileForm,
                                   'select_sensor_form': select_sensor_form, 'sensorSet': sensorSet, 'sub_pro': sub_pro,
                                   'input_form': input_form, 'input_time_form': input_time_form,
                                   'sensor_form': sensor_form, 'machine_form': machine_form, 'weightForm': weightForm,
                                   'management': management, 'supervisor': supervisor,
                                   'sub_master_form': sub_master_form, 'operator_form': operator_form})
                else:
                    return render(response, 'Main/components.html',
                                  {'deletion': deletion, 'select_sensor_form': select_sensor_form,
                                   'sensorSet': sensorSet, 'sub_pro': sub_pro, 'input_form': input_form,
                                   'input_time_form': input_time_form, 'sensor_form': sensor_form,
                                   'machine_form': machine_form, 'weightForm': weightForm, 'management': management,
                                   'supervisor': supervisor, 'sub_master_form': sub_master_form,
                                   'operator_form': operator_form})
            elif response.user.groups.filter(name='Technician').exists():
                return render(response, 'Main/components.html', {'sub_pro': sub_pro})
            else:
                # redirect to home page
                redirect('/')
        # if sub process isnt in user company group redirect to home
        return HttpResponseRedirect('/')
    else:
        return redirect('/mylogout/')


def showEnvironSensors(response, id):
    if response.user.is_authenticated:
        management, supervisor = False, False,
        process = Process.objects.get(id=id)
        time_form = ChangeGraphTime()
        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        if process.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:
                if response.POST.get('changeVOCGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="VOC Sensor").exists():
                            sensor = process.sensor_set.all().get(name="VOC Sensor")
                            sensor.averageTime = response.POST['time']
                            sensor.save()

                if response.POST.get('changeTempGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Thermocouple").exists():
                            sensor = process.sensor_set.all().get(name="Thermocouple")
                            sensor.averageTime = response.POST['time']
                            sensor.save()

                if response.POST.get('changeHumidityGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Humidity Sensor").exists():
                            sensor = process.sensor_set.all().get(name="Humidity Sensor")
                            sensor.averageTime = response.POST['time']
                            sensor.save()

                if response.POST.get('changeDustGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Dust Sensor").exists():
                            sensor = process.sensor_set.all().get(name="Dust Sensor")
                            sensor.averageTime = response.POST['time']
                            sensor.save()

                return render(response, 'Main/showEnvironSensors.html',
                              {'time_form': time_form, 'management': management, 'supervisor': supervisor,
                               'process': process})
            else:
                # redirect to the home page
                return redirect('/')
        else:
            # redirect to the home page
            return redirect('/')
    else:
        return redirect('/mylogout/')


def environGraph(response, id):
    if response.user.is_authenticated:
        Proc, management, supervisor = Process.objects.get(id=id), False, False
        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True

        if Proc.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:

                # default variables
                requiredField, labels, tempData, tempLabels, vocData, vocLabels, dustData, dustLabels, humidityData, humidityLabels, = '', [], [], [], [], [], [], [], [], []
                data = {'Temp': 0, 'VOC': 0, 'Dust': 0, 'Humidity': 0}
                minV = {'Temp': -5, 'VOC': -10, 'Dust': 2, 'Humidity': 2}  # min lines for each graph
                maxV = {'Temp': 50, 'VOC': 15, 'Dust': 25, 'Humidity': 20}  # max lines for each graph

                for sensor in Proc.sensor_set.all():
                    avgList = []
                    average = 0
                    if sensor.name == "Thermocouple":
                        tempLabels.append(
                            sensor.name + "-" + sensor.modelID)  # add sensor name and corresponding model ID
                        tempLabels.append("Average Temperature Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(temp=random.randint(0, 40), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()
                        if len(sensor.sensortime_set.all()) != 0:  # if sensor is receiving data (sensortime data)
                            tempData.append(
                                sensor.sensortime_set.all().last().temp)  # append temperature attribute from sensortime attribute
                            for each in sensor.sensortime_set.all():
                                avgList.append(each.temp)

                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            tempData.append(average)
                        # -Un-comment this to see cool graph lines-#
                        # tempData.append(random.randint(0,40))
                        else:
                            tempData.append(0)

                    if sensor.name == "VOC Sensor":
                        vocLabels.append(
                            sensor.name + "-" + sensor.modelID)  # add sensor name and corresponding model ID
                        vocLabels.append("Average VOC Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(VOC=random.randint(0, 10), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()
                        if len(sensor.sensortime_set.all()) != 0:  # if sensor is receiving data (sensortime data)
                            vocData.append(
                                sensor.sensortime_set.all().last().VOC)  # append VOC attribute from sensortime attribute
                            for each in sensor.sensortime_set.all():
                                avgList.append(each.VOC)

                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            vocData.append(average)
                        # vocData.append(random.randint(0, 10))
                        else:
                            vocData.append(0)

                    if sensor.name == "Humidity Sensor":
                        humidityLabels.append(
                            sensor.name + "-" + sensor.modelID)  # add sensor name and corresponding model ID
                        humidityLabels.append("Average Humidity Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(humidity=random.randint(5, 15), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()
                        if len(sensor.sensortime_set.all()) != 0:  # if sensor is receiving data (sensortime data)
                            humidityData.append(
                                sensor.sensortime_set.all().last().humidity)  # append humidity attribute from sensortime attribute
                            for each in sensor.sensortime_set.all():
                                avgList.append(each.humidity)

                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            humidityData.append(average)
                        # humidityData.append(random.randint(5,15))
                        else:
                            humidityData.append(0)

                    if sensor.name == "Dust Sensor":
                        dustLabels.append(
                            sensor.name + "-" + sensor.modelID)  # add sensor name and corresponding model ID
                        dustLabels.append("Average Dust Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(dust=random.randint(5, 20), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()
                        if len(sensor.sensortime_set.all()) != 0:  # if sensor is receiving data (sensortime data)
                            dustData.append(
                                sensor.sensortime_set.all().last().dust)  # append dust attribute from sensortime attribute
                            for each in sensor.sensortime_set.all():
                                avgList.append(each.dust)

                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            dustData.append(average)
                        # dustData.append(random.randint(5,20))
                        else:
                            dustData.append(0)

                return JsonResponse(
                    data={'data': data, 'tempData': tempData, 'tempLabels': tempLabels, 'vocData': vocData,
                          'vocLabels': vocLabels, 'dustData': dustData, 'dustLabels': dustLabels,
                          'humidityData': humidityData, 'humidityLabels': humidityLabels, 'labels': labels,
                          'maxV': maxV, 'minV': minV})
    else:
        return redirect('/mylogout/')


def popUp(response, id):
    # setup
    if response.user.is_authenticated:
        subpro = SubProcess.objects.get(id=id)
        initialTempTime, initialTempData, initialPressureData, initialPressureTime, cleanPressureData, cleanTempData = [], [], [], [], [], []
        temperatureData, pressureData = {}, {}
        tempReached, pressureReached, jobEnd = False, False, False
        thermo, pressSensor, temp = None, None, None
        tempReachedTime, pressureReachedTime, firstPressure = "00:00:00", "00:00:00", "00:00:00"
        total, tMaxTemp, tMinTemp, pMaxPressure, pMinPressure, refreshRate, seconds, cleanedTempReachedTime, cleanedPressureReachedTime = 0, 0, 10, 10, 0, 1500, 0, 0, 0
        ellipseSupport, ellipseSupportPressure, = "", ""
        time = ""
        currentTime = datetime.now()
        time = currentTime.strftime("%H:%M:%S")

        if subpro.sensor_set.filter(name="Thermocouple").exists():  # initialise thermocouple
            thermo = subpro.sensor_set.get(name="Thermocouple")
            tempReached = thermo.temperatureReached
            tempReachedTime = thermo.tempReachedTime
            tMaxTemp = thermo.maxTemp
            tMinTemp = thermo.minTemp
        if subpro.sensor_set.filter(name="Pressure Sensor").exists():  # initialise pressure sensor
            pressSensor = subpro.sensor_set.get(name="Pressure Sensor")
            pressureReached = pressSensor.pressureReached
            pMaxPressure = pressSensor.maxPressure
            pMinPressure = pressSensor.minPressure
            pressureReachedTime = pressSensor.pressureReachedTime

        if subpro.jobEnd != None and subpro.jobStart != None:
            jobEnd = True
        if subpro.jobEnd == None and subpro.jobStart != None:  # if task is ongoing

            if thermo != None:  # if thermocouple exists
                thermo.sensortime_set.create(time=datetime.now(), temp=random.randint(3, 5))  # create sensortime data

            if pressSensor != None:  # if pressure sensor exists
                pressSensor.sensortime_set.create(time=datetime.now(), pressure=random.randint(6, 8))

            if tempReached == True:  # if temperature reached set value
                thermo.tempReachedTime = time
                temp = currentTime + timedelta(seconds=3)
                ellipseSupport = temp.strftime("%H:%M:%S")
                thermo.temperatureReached = False
                tempReached = True
                thermo.save()
                tempReachedTime = thermo.tempReachedTime

            if pressureReached == True:  # if pressure reached set value
                pressSensor.pressureReachedTime = time
                pressSensor.pressureReached = False
                temp = currentTime + timedelta(seconds=3)
                ellipseSupportPressure = temp.strftime("%H:%M:%S")
                pressureReached = True
                pressureReachedTime = pressSensor.pressureReachedTime
                pressSensor.save()

            if thermo != None:
                for each in thermo.sensortime_set.all():
                    currentTime = each.time
                    time = currentTime.strftime("%H:%M:%S")
                    initialTempData.append({'x': time, 'y': each.temp})

                if thermo.tempReachedTime != None:
                    r = datetime.strptime(thermo.tempReachedTime, '%H:%M:%S')
                    temp = r + timedelta(seconds=3)
                    ellipseSupport = temp.strftime("%H:%M:%S")

            if pressSensor != None:
                for each in pressSensor.sensortime_set.all():
                    currentTime = each.time
                    time = currentTime.strftime("%H:%M:%S")
                    initialPressureData.append({'x': time, 'y': each.pressure})

                if pressSensor.pressureReachedTime != None:
                    r = datetime.strptime(pressSensor.pressureReachedTime, '%H:%M:%S')
                    temp = r + timedelta(seconds=3)
                    ellipseSupportPressure = temp.strftime("%H:%M:%S")

            currentTime = datetime.now()
            time = currentTime.strftime("%H:%M:%S")

        if subpro.jobStart != None and subpro.jobEnd != None:  # if task is finished
            if thermo != None:
                for each in thermo.sensortime_set.all():
                    currentTime = each.time

                    time = currentTime.strftime("%H:%M:%S")
                    initialTempData.append({'x': time, 'y': each.temp})

                if len(initialTempData) > 0:
                    firstTemp = initialTempData[0]['x']
                    lastTemp = initialTempData[-1]['x']

                    k = datetime.strptime(firstTemp, '%H:%M:%S')
                    z = datetime.strptime(lastTemp, '%H:%M:%S')

                    dif = z - k

                    reachedDif = z - datetime.strptime(thermo.tempReachedTime, '%H:%M:%S')

                    cleanedTempReachedTime = 0

                    total = int(dif.total_seconds())
                    cleanedTempReachedTime = total - int(reachedDif.total_seconds())
                    newList = list(range(0, int(total)))

                    initialTempData = []
                    count = 0
                    for each in thermo.sensortime_set.all():
                        if count >= len(newList):
                            break
                        else:
                            initialTempData.append({'x': str(newList[count]), 'y': each.temp})
                            count += 1

            if pressSensor != None:
                for each in pressSensor.sensortime_set.all():
                    currentTime = each.time
                    time = currentTime.strftime("%H:%M:%S")
                    initialPressureData.append({'x': time, 'y': each.pressure})

                if len(initialPressureData) > 0:
                    firstPressure = initialPressureData[0]['x']
                    lastPressure = initialPressureData[-1]['x']

                    k = datetime.strptime(firstPressure, '%H:%M:%S')
                    z = datetime.strptime(lastPressure, '%H:%M:%S')

                    dif = z - k

                    reachedDif = z - datetime.strptime(pressSensor.pressureReachedTime, '%H:%M:%S')

                    cleanedPressureReachedTime = 0

                    total = int(dif.total_seconds())
                    cleanedPressureReachedTime = total - int(reachedDif.total_seconds())
                    newList = list(range(0, int(total)))

                    initialPressureData = []
                    count = 0
                    for each in pressSensor.sensortime_set.all():
                        if count >= len(newList):
                            break
                        else:
                            initialPressureData.append({'x': str(newList[count]), 'y': each.pressure})

                            count += 1

        if subpro.jobStart != None and subpro.jobEnd == None:

            management = False
            supervisor = False
            if response.user.groups.filter(name='Management').exists():
                management = True
            elif response.user.groups.filter(name='Supervisor').exists():
                supervisor = True

            if subpro.process.project in response.user.profile.user_company.project_set.all():
                if management or supervisor:
                    if thermo != None:
                        if len(thermo.sensortime_set.all()) == 0:
                            temperatureData.update({str(id): 0, 'maxTemp': thermo.maxTemp, 'minTemp': thermo.minTemp})
                        else:
                            temperatureData.update({str(id): thermo.sensortime_set.all().last().temp, 'time': time,
                                                    'maxTemp': thermo.maxTemp,
                                                    'minTemp': thermo.minTemp})  # if thermocouple exists within sub process, display popup real-time temperature graph
                    if pressSensor != None:

                        if len(pressSensor.sensortime_set.all()) == 0:
                            pressureData.update({str(id): 0, 'maxPressure': pressSensor.maxPressure,
                                                 'minPressure': pressSensor.minPressure})
                        else:
                            pressureData.update(
                                {str(id): pressSensor.sensortime_set.all().last().pressure, 'time': time,
                                 'maxPressure': pressSensor.maxPressure,
                                 'minPressure': pressSensor.minPressure})  # if pressure sensor exists within sub process, display popup real-time pressure graph

                    return JsonResponse(
                        data={'refreshRate': refreshRate, 'ellipseSupportPressure': ellipseSupportPressure,
                              'ellipseSupport': ellipseSupport, 'jobEnd': jobEnd,
                              'pressureReachedTime': pressureReachedTime, 'pressureReached': pressureReached,
                              'tempReachedTime': tempReachedTime, 'tempReached': tempReached,
                              'pressureReached': pressureReached, 'initialTempData': initialTempData,
                              'initialPressureData': initialPressureData, 'temperatureData': temperatureData,
                              'pressureData': pressureData, })
        elif subpro.jobStart != None and subpro.jobEnd != None:
            refreshRate = 100000000

            # pressureReachedTime = middle['x']
            # tempReachedTime = middle['x']

            temperatureData.update({str(id): 0, 'maxTemp': tMaxTemp, 'minTemp': tMinTemp})
            pressureData.update({str(id): 0, 'maxPressure': pMaxPressure, 'minPressure': pMinPressure})
            return JsonResponse(
                data={'ellipseSupportPressure': ellipseSupportPressure, 'ellipseSupport': ellipseSupport,
                      'cleanedPressureReachedTime': cleanedPressureReachedTime,
                      'cleanedTempReachedTime': cleanedTempReachedTime, 'jobEnd': jobEnd, 'refreshRate': refreshRate,
                      'firstPressure': firstPressure, 'total': total, 'pressureReachedTime': pressureReachedTime,
                      'tempReachedTime': tempReachedTime, 'pressureReached': pressureReached,
                      'tempReached': tempReached, 'pressureReached': pressureReached,
                      'initialTempData': initialTempData, 'initialPressureData': initialPressureData,
                      'temperatureData': temperatureData, 'pressureData': pressureData})
        elif subpro.jobStart == None and subpro.jobEnd == None:
            refreshRate = 10000
            temperatureData.update({str(id): 0, 'maxTemp': tMaxTemp, 'minTemp': tMinTemp})
            pressureData.update({str(id): 0, 'maxPressure': pMaxPressure, 'minPressure': pMinPressure})
            return JsonResponse(
                data={'ellipseSupportPressure': ellipseSupportPressure, 'ellipseSupport': ellipseSupport,
                      'jobEnd': jobEnd, 'refreshRate': refreshRate, 'firstPressure': firstPressure, 'total': total,
                      'pressureReachedTime': pressureReachedTime, 'tempReachedTime': tempReachedTime,
                      'pressureReached': pressureReached, 'tempReached': tempReached,
                      'pressureReached': pressureReached, 'initialTempData': initialTempData,
                      'initialPressureData': initialPressureData, 'temperatureData': temperatureData,
                      'pressureData': pressureData})
    else:
        return redirect('/mylogout/')


def machineHealthShow(response, id):
    process = Process.objects.get(id=id)
    if response.user.is_authenticated:
        management = False
        supervisor = False
        time_form = ChangeGraphTime()
        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        if process.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:
                if response.POST.get('changeEnergyGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Power Clamp (Big Oven)").exists():
                            ovenSensor = process.sensor_set.all().get(name="Power Clamp (Big Oven)")

                        if process.sensor_set.all().filter(name="Power Clamp (Big Cabinet)").exists():
                            cabinetSensor = process.sensor_set.all().get(name="Power Clamp (Big Cabinet)")

                        if process.sensor_set.all().filter(name="Power Clamp (Kuka Robot)").exists():
                            kukaSensor = process.sensor_set.all().get(name="Power Clamp (Kuka Robot)")

                        if process.sensor_set.all().filter(name="Power Clamp (CNC Router)").exists():
                            cncSensor = process.sensor_set.all().get(name="Power Clamp (CNC Router)")

                        ovenSensor.averageEnergyTime = response.POST['time']
                        cabinetSensor.averageEnergyTime = response.POST['time']
                        kukaSensor.averageEnergyTime = response.POST['time']
                        cncSensor.averageEnergyTime = response.POST['time']

                        ovenSensor.save()
                        cabinetSensor.save()
                        kukaSensor.save()
                        cncSensor.save()
                if response.POST.get('changeStrainGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Strain Gauge").exists():
                            sensor = process.sensor_set.all().get(name="Strain Gauge")
                            sensor.averageTime = response.POST['time']
                            sensor.save()
                if response.POST.get('changeNoiseGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Microphone").exists():
                            sensor = process.sensor_set.all().get(name="Microphone")
                            sensor.averageTime = response.POST['time']
                            sensor.save()
                if response.POST.get('changeAccelerationGraph'):
                    time_form = ChangeGraphTime(response.POST)
                    if time_form.is_valid():
                        if process.sensor_set.all().filter(name="Accelerometer").exists():
                            sensor = process.sensor_set.all().get(name="Accelerometer")
                            sensor.averageTime = response.POST['time']
                            sensor.save()

                # open Machine Health Page
                return render(response, 'Main/showMachineHealth.html',
                              {'time_form': time_form, 'management': management, 'supervisor': supervisor,
                               'process': process})
        else:
            # redirect to the home page
            return redirect('/')
    else:
        return redirect('/mylogout/')


from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import Process, Sensor
from .forms import ChangeGraphTime

def newSensor(response, id):
    if not response.user.is_authenticated:
        return redirect('/mylogout/')
    
    management, supervisor = False, False
    process = Process.objects.get(id=id)
    time_form = ChangeGraphTime()
    
    # Check user permissions
    if response.user.groups.filter(name='Management').exists():
        management = True
    elif response.user.groups.filter(name='Supervisor').exists():
        supervisor = True
        
    if process.project not in response.user.profile.user_company.project_set.all():
        return redirect('/')
    if not (management or supervisor):
        return redirect('/')
        
    # Mapping for sensor types and their form handlers
    sensor_update_mappings = {
        'changeVOCGraph': 'VOC Sensor',
        'changeTempGraph': 'Thermocouple',
        'changeHumidityGraph': 'Humidity Sensor',
        'changeDustGraph': 'Dust Sensor',
        'changeEnergyGraph': [
            'Power Clamp (Big Oven)',
            'Power Clamp (Big Cabinet)',
            'Power Clamp (Kuka Robot)',
            'Power Clamp (CNC Router)'
        ],
        'changeStrainGraph': 'Strain Gauge',
        'changeNoiseGraph': 'Noise Sensor 1',
        'changeAccelerationGraph': 'Accelerometer',
    }
    
    # Handle form submissions
    if response.method == 'POST':
        time_form = ChangeGraphTime(response.POST)
        if time_form.is_valid():
            new_time = time_form.cleaned_data['time']
            
            # Check which form was submitted
            for post_key, sensor_names in sensor_update_mappings.items():
                if response.POST.get(post_key):
                    # Handle energy sensors differently
                    if isinstance(sensor_names, list):
                        sensors_updated = []
                        for sensor_name in sensor_names:
                            sensor = process.sensor_set.filter(name=sensor_name).first()
                            if sensor:
                                sensor.averageTime = new_time
                                sensor.save()
                                sensors_updated.append(sensor_name)
                        
                        if sensors_updated and response.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'status': 'success',
                                'message': f'Updated average time for sensors: {", ".join(sensors_updated)}',
                                'new_time': new_time
                            })
                    else:
                        # Handle single sensor update
                        sensor = process.sensor_set.filter(name=sensor_names).first()
                        if sensor:
                            sensor.averageTime = new_time
                            sensor.save()
                            
                            if response.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                return JsonResponse({
                                    'status': 'success',
                                    'message': f'Updated average time for {sensor_names}',
                                    'new_time': new_time
                                })
    
    # Get current average times for all sensors
    energy_sensors = {}
    for sensor_name in sensor_update_mappings['changeEnergyGraph']:
        sensor = process.sensor_set.filter(name=sensor_name).first()
        if sensor:
            energy_sensors[sensor_name] = sensor.averageTime
    
    # Get noise sensor if it exists
    noise_sensor = process.sensor_set.filter(name='Noise Sensor 1').first()
    noise_sensor_id = noise_sensor.id if noise_sensor else None
    
    context = {
        'time_form': time_form,
        'management': management,
        'supervisor': supervisor,
        'process': process,
        'sensor_id': id,
        'noise_sensor_id': noise_sensor_id,
        'energy_sensors': energy_sensors,
    }
    
    return render(response, 'Main/newSensor.html', context)

def machineHealth(response, id):
    if response.user.is_authenticated:

        management = False
        supervisor = False
        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True

        Proc = Process.objects.get(id=id)
        if Proc.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:

                # setup
                energyData, energyLabels, microphoneData, microphoneLabels, torqueData, torqueLabels, accelerationData, accelerationLabels, labels = [], [], [], [], [], [], [], [], []
                maxV, minV = [15, 15, 15], [-5, -5, -5]  # default min and max lines
                bigCabinetPower, bigOvenPower, kukaRobotPower, cncPower = 0, 0, 0, 0
                kWh = False
                bigOven, bigCabinet, kuka, CNC = {}, {}, {}, {}

                # request call to shelly API for all power clamp data
                s = requests.post('https://shelly-43-eu.shelly.cloud/device/all_status',
                                  data={'auth_key': os.environ.get('AUTH_KEY')})
                receivedData = s.json()  # converting received response into json structure
                
                if Proc.sensor_set.all().filter(name="Power Clamp (Big Oven)").exists():
                    try:
                        bigOven = receivedData['data']['devices_status'][Proc.sensor_set.all().get(
                            name="Power Clamp (Big Oven)").modelID]  # getting big oven device data

                    except KeyError:
                        bigOven['total_power'] = 0
                else:
                    bigOven['total_power'] = 0

                if Proc.sensor_set.all().filter(name="Power Clamp (Big Cabinet)").exists():
                    try:
                        bigCabinet = receivedData['data']['devices_status'][Proc.sensor_set.all().get(
                            name="Power Clamp (Big Cabinet)").modelID]  # getting big cabinet device data
                    except KeyError:
                        bigCabinet['total_power'] = 0
                else:
                    bigCabinet['total_power'] = 0

                if Proc.sensor_set.all().filter(name="Power Clamp (Kuka Robot)").exists():
                    try:
                        kuka = receivedData['data']['devices_status'][Proc.sensor_set.all().get(
                            name="Power Clamp (Kuka Robot)").modelID]  # getting kuka robot device data
                    except KeyError:
                        kuka['total_power'] = 0
                else:
                    kuka['total_power'] = 0

                if Proc.sensor_set.all().filter(name="Power Clamp (CNC Router)").exists():
                    try:
                        CNC = receivedData['data']['devices_status'][
                            Proc.sensor_set.all().get(name="Power Clamp (CNC Router)").modelID]
                    except KeyError:
                        CNC['total_power'] = 0
                else:
                    CNC['total_power'] = 0

                if bigOven['total_power'] > 1000:  # if watts per hour exceeds 1000, set measurement to kWh instead
                    kWh = True
                else:
                    kWh = True

                # assigning power values
                bigOvenPower = bigOven['total_power']
                bigCabinetPower = bigCabinet['total_power']
                kukaRobotPower = kuka['total_power']
                cncPower = CNC['total_power']

                # print(bigOvenPower)

                energySensors = []
                # breakpoint()
                if Proc.sensor_set.all().filter(name="Power Clamp (Big Oven)").exists():
                    ovenSensor = Proc.sensor_set.all().get(name="Power Clamp (Big Oven)")
                    ovenSensor.sensortime_set.create(energy=bigOvenPower, time=datetime.now())
                    if len(ovenSensor.sensortime_set.all()) >= ovenSensor.averageEnergyTime:
                        ovenSensor.sensortime_set.first().delete()

                    energySensors.append(ovenSensor)

                if Proc.sensor_set.all().filter(name="Power Clamp (Big Cabinet)").exists():
                    cabinetSensor = Proc.sensor_set.all().get(name="Power Clamp (Big Cabinet)")
                    cabinetSensor.sensortime_set.create(energy=bigCabinetPower, time=datetime.now())
                    if len(cabinetSensor.sensortime_set.all()) >= cabinetSensor.averageEnergyTime:
                        cabinetSensor.sensortime_set.first().delete()

                    energySensors.append(cabinetSensor)

                if Proc.sensor_set.all().filter(name="Power Clamp (Kuka Robot)").exists():
                    kukaSensor = Proc.sensor_set.all().get(name="Power Clamp (Kuka Robot)")
                    kukaSensor.sensortime_set.create(energy=kukaRobotPower, time=datetime.now())
                    if len(kukaSensor.sensortime_set.all()) >= kukaSensor.averageEnergyTime:
                        kukaSensor.sensortime_set.first().delete()

                    energySensors.append(kukaSensor)

                if Proc.sensor_set.all().filter(name="Power Clamp (CNC Router)").exists():
                    cncSensor = Proc.sensor_set.all().get(name="Power Clamp (CNC Router)")
                    cncSensor.sensortime_set.create(energy=cncPower, time=datetime.now())
                    if len(cncSensor.sensortime_set.all()) >= cncSensor.averageEnergyTime:
                        cncSensor.sensortime_set.first().delete()
                    energySensors.append(cncSensor)

                # print(energySensors)
                # x,p,k = None,None,None
                # #if power is returning a negative value, invert it into a positive
                # if bigOven['total_power'] < 0:
                #   bigOvenPower = x['total_power'] * -1        #Huh?

                # if bigCabinet['total_power'] < 0:
                #   bigCabinetPower = p['total_power'] * -1

                # if kuka['total_power'] < 0:
                #   kukaRobotPower = k['total_power'] * -1

                if kWh == False:  # assign in watts per hour
                    energyLabels.append("Big Oven (Watts)")
                    energyLabels.append("Big Cabinet (Watts)")
                    energyLabels.append("Kuka Robot (Watts)")
                    energyLabels.append("CNC Router (Watts)")
                    energyLabels.append("Total Power Consumption (Watts)")
                    energyData.append(bigOvenPower)
                    energyData.append(bigCabinetPower)
                    energyData.append(kukaRobotPower)
                    energyData.append(cncPower)
                    energyData.append(bigOvenPower + bigCabinetPower + kukaRobotPower + cncPower)

                else:  # assign in kWh
                    energyLabels.append("Big Oven (kWh) ")
                    energyLabels.append("Big Cabinet (kWh) ")
                    energyLabels.append("Kuka Robot (kWh)")
                    energyLabels.append("CNC Router (kWh)")
                    energyLabels.append("Total Power Consumption (kWh)")
                    energyData.append(bigOvenPower / 1000)
                    energyData.append(bigCabinetPower / 1000)
                    energyData.append(kukaRobotPower / 1000)
                    energyData.append(cncPower / 1000)
                    energyData.append((bigOvenPower + bigCabinetPower + kukaRobotPower + cncPower) / 1000)

                CO2perKWH = (((bigOvenPower / 1000) + (bigCabinetPower / 1000) + (kukaRobotPower / 1000) + (
                        cncPower / 1000))) * float(Proc.project.CO2PerPower)  # CO2 per KWH calculation

                avgList = []
                for instance in energySensors:
                    for power in instance.sensortime_set.all():
                        avgList.append(power.energy)
                try:
                    average = (sum(avgList) / len(avgList)) / 1000
                except:
                    average = 0
                try:
                    # Ensure energySensors is not empty
                    if not energySensors:
                        raise IndexError("energySensors list is empty")

                    # Iterate through instances and collect power energy values
                    for instance in energySensors:
                        for power in instance.sensortime_set.all():
                            avgList.append(power.energy)

                    # Calculate the average energy
                    if avgList:
                        average = (sum(avgList) / len(avgList)) / 1000
                    else:
                        average = 0  # If avgList is empty, set average to 0

                    # Append the average energy time to the labels and data
                    energyLabels.append("Average Power Consumption in the last " + str(energySensors[0].averageEnergyTime) + " seconds")
                    energyData.append(average)

                except IndexError as e:
                    print(f"IndexError: {e}")
                    # Handle the case where energySensors is empty
                    energyLabels.append("Average Power Consumption in the last 0 seconds")
                    energyData.append(0)

                except Exception as e:
                    print(f"An error occurred: {e}")
                    # Handle any other unexpected exceptions
                    energyLabels.append("Average Power Consumption in the last N/A seconds")
                    energyData.append(0)
                # energyLabels.append(
                #     "Average Power Consumption in the last " + str(energySensors[0].averageEnergyTime) + " seconds")
                # energyData.append(average)

                # assigning real-time microphone, torque and acceleration data to graphs
                for sensor in Proc.sensor_set.all():
                    average = 0
                    avgList = []
                    if sensor.name == "Microphone":
                        microphoneLabels.append(sensor.name + "-" + sensor.modelID)
                        microphoneLabels.append("Average Noise Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(noise=random.randint(1, 10), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()
                        if len(sensor.sensortime_set.all()) != 0:
                            microphoneData.append(sensor.sensortime_set.all().last().noise)
                            # microphoneData.append(random.randint(5,10))
                            for each in sensor.sensortime_set.all():
                                avgList.append(each.noise)

                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            microphoneData.append(average)
                        else:
                            microphoneData.append(random.randint(5, 10))

                    if sensor.name == "Strain Gauge":
                        torqueLabels.append(sensor.name + "-" + sensor.modelID)
                        torqueLabels.append("Average Strain Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(torque=random.randint(1, 10), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()

                        if len(sensor.sensortime_set.all()) != 0:
                            torqueData.append(sensor.sensortime_set.all().last().torque)
                            for each in sensor.sensortime_set.all():
                                avgList.append(each.torque)
                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            torqueData.append(average)
                            torqueData.append(random.randint(0,10))

                        else:
                            torqueData.append(random.randint(0, 10))

                    if sensor.name == "Accelerometer":
                        accelerationLabels.append(sensor.name + "-" + sensor.modelID)
                        accelerationLabels.append(
                            "Average Acceleration Over The last " + str(sensor.averageTime) + " Seconds")
                        sensor.sensortime_set.create(acceleration=random.randint(1, 10), time=datetime.now())
                        if len(sensor.sensortime_set.all()) >= sensor.averageTime:
                            sensor.sensortime_set.first().delete()

                        if len(sensor.sensortime_set.all()) != 0:
                            accelerationData.append(sensor.sensortime_set.all().last().acceleration)

                            for each in sensor.sensortime_set.all():
                                avgList.append(each.acceleration)
                            average = sum(avgList) / len(sensor.sensortime_set.all())
                            accelerationData.append(average)
                        # accelerationData.append(random.randint(5,10))
                        else:
                            accelerationData.append(random.randint(5, 10))

                return JsonResponse(data={'CO2perKWH': CO2perKWH, 'accelerationLabels': accelerationLabels,
                                          'accelerationData': accelerationData, 'torqueLabels': torqueLabels,
                                          'torqueData': torqueData, 'microphoneData': microphoneData,
                                          'microphoneLabels': microphoneLabels, 'labels': labels,
                                          'energyData': energyData, 'energyLabels': energyLabels, 'minV': minV,
                                          'maxV': maxV})
        else:
            return redirect('/')
    else:
        return redirect('/mylogout/')


def final(response, id):
    if response.user.is_authenticated:
        sub_pro = SubProcess.objects.get(id=id)
        management = False
        supervisor = False
        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        if sub_pro.process.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:
                # assigning nominal and actual values
                nominalThickness = sub_pro.process.project.nominalPartThickness
                actualThickness = sub_pro.actualThickness
                nominalWeight = sub_pro.process.project.nominalPartWeight
                actualWeight = sub_pro.postTrimWeight

                data = {}
                dataThickness = {}
                data.update({'Nominal Weight': nominalWeight})
                data.update({'Actual Weight': actualWeight})
                dataThickness.update({'Nominal Thickness': nominalThickness})
                dataThickness.update({'Actual Thickness': actualThickness})

                # data returned as json response for graph data on final inspection page

                return JsonResponse(data={'data': data, 'dataThickness': dataThickness})
    else:
        return redirect('/mylogout/')


def systemArchitecture(response, id):
    if response.user.is_authenticated:
        project = Project.objects.get(id=id)
        management = False
        supervisor = False
        technician = False
        
        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        elif response.user.groups.filter(name='Technician').exists():
            technician = True
            
        if project in response.user.profile.user_company.project_set.all():
            if management or supervisor or technician:
                # Initialize default process steps with machines and sensors
                processes = [
                    {
                        'name': 'Cut Plies',
                        'machine': {'name': 'Ply Cutter', 'status': 1},  # status 1 for green/active
                        'sensors': [{'name': 'Load and Cut Ply', 'status': 2}]  # status 2 for green/active
                    },
                    {
                        'name': 'Buffer (Ply Storage)',
                        'machine': {'name': 'Ply Cutter', 'status': 1},
                        'sensors': [
                            {'name': 'Ply Placed', 'status': 2},
                            {'name': 'Ply Waiting', 'status': 2}
                        ]
                    },
                    {
                        'name': 'Create Blanks',
                        'machine': {'name': 'Preforming Cell', 'status': 1},
                        'sensors': [
                            {'name': 'Pickup Initial Ply', 'status': 2},
                            {'name': 'Pickup Ply & Weld', 'status': 2}
                        ]
                    },
                    {
                        'name': 'Buffer (Blank Storage)',
                        'machine': {'name': 'Preforming Cell', 'status': 1},
                        'sensors': [
                            {'name': 'Blank Placed', 'status': 2},
                            {'name': 'Blank Waiting', 'status': 2},
                            {'name': 'Blank Removed', 'status': 2}
                        ]
                    },
                    {
                        'name': 'Form Preform',
                        'machine': {'name': 'Preforming Cell', 'status': 1},
                        'sensors': [
                            {'name': 'Initialisation', 'status': 2},
                            {'name': 'Heat Mould and Platten Up', 'status': 2},
                            {'name': 'Blank Loaded in Machine', 'status': 2},
                            {'name': 'Temperature Reached and Platten Down', 'status': 2},
                            {'name': 'Blank Inside Press', 'status': 2},
                            {'name': 'Blank Pressed', 'status': 2},
                            {'name': 'Mould Cooling', 'status': 2},
                            {'name': 'Part Released from Mould', 'status': 2},
                            {'name': 'Machine Returns To Home Location', 'status': 2},
                            {'name': 'Part Leaves Machine', 'status': 2}
                        ]
                    },
                    {
                        'name': 'Final Inspection',
                        'machine': {'name': 'Preforming Cell', 'status': 1},
                        'sensors': [
                            {'name': 'Part Assessment (Initial Weight)', 'status': 2},
                            {'name': 'Trim', 'status': 2},
                            {'name': 'Part Assessment (Final Weight)', 'status': 2},
                            {'name': 'Part Assessment (Final Geometry)', 'status': 2}
                        ]
                    }
                ]
                
                # Update the project's processes with the default data
                project.order_process_custom = processes
                
                return render(response, 'Main/showSystemArchitecture.html',
                            {'technician': technician,
                             'management': management,
                             'supervisor': supervisor,
                             'selected_project': project})
            else:
                return redirect('/')
        else:
            return redirect('/')
    else:
        return redirect('/mylogout/')



import logging
from django.utils import timezone
from django.http import JsonResponse
from functools import wraps
import inspect

logger = logging.getLogger(__name__)

class OPCUAMethodCall:
    def __init__(self, method_name, namespace="ns=3"):
        self.method_name = method_name
        self.namespace = namespace
        
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = Client("opc.tcp://10.10.42.11:4840")
            try:
                client.connect()
                logger.info(f"Connected to OPC UA server for {self.method_name}")
                
                # Set up nodes for method call
                parent_node = client.get_node(f'{self.namespace};s="{self.method_name}"')
                method_node = client.get_node(f'{self.namespace};s="{self.method_name}".Method')
                
                # Call the original function
                result = func(*args, **kwargs)
                
                if isinstance(result, tuple) and len(result) == 2:
                    params, _ = result
                    input_value = ua.Variant(params, ua.VariantType.UInt16)
                    method_result = parent_node.call_method(method_node, input_value)
                else:
                    method_result = parent_node.call_method(method_node)
                
                logger.info(f"{self.method_name} method result: {method_result}")
                return True
                
            except Exception as e:
                logger.error(f"Error in {self.method_name}: {str(e)}")
                return False
            finally:
                try:
                    client.disconnect()
                    logger.info(f"Disconnected from OPC UA server for {self.method_name}")
                except Exception as e:
                    logger.error(f"Error during disconnect: {str(e)}")
                    
        return wrapper

class SubProcessHandler:
    def __init__(self):
        self.handlers = {}
        self.tool_heat_params = {'temp1': 230, 'temp2': 70}
        self._register_handlers()
    
    def _register_handlers(self):
        @OPCUAMethodCall("00_INIT_CALL_DB")
        def handle_init():
            return None
        
        @OPCUAMethodCall("01_TOOL_HEAT_CALL_DB")
        def handle_tool_heat(**kwargs):
            return [kwargs['temp1'], kwargs['temp2']], True
        
        @OPCUAMethodCall("03_TOOL_READY_CALL_DB")
        def handle_tool_ready():
            return None
            
        @OPCUAMethodCall("04_BLANK_IN_CALL_DB")
        def handle_blank_in(param1=0, param2=0):
            return [param1, param2], True

        @OPCUAMethodCall("06_TOOL_COOL_CALL_DB")
        def handle_tool_cool(**kwargs):
            # Get cooling temperatures from parameters
            temp_centre = kwargs.get('temp_centre', 0)
            temp_side = kwargs.get('temp_side', 0)
            return [temp_centre, temp_side], True

        @OPCUAMethodCall("07_PART_RELEASE_CALL_DB")
        def handle_part_release():
            return None

        @OPCUAMethodCall("08_PART_OUT_CALL_DB")
        def handle_part_out():
            return None

        self.handlers = {
            'Initialisation': (handle_init, {}),
            'Heat Mould and Platten Up': (handle_tool_heat, self.tool_heat_params),
            'Blank Loaded in Machine': None,  
            'Temperature Reached and Platten Down': (handle_tool_ready, {}),
            'Blank Inside Press': (handle_blank_in, {'param1': 0, 'param2': 0}),
            'Mould Cooling': (handle_tool_cool, {'temp_centre': 0, 'temp_side': 0}),
            'Part Released from Mould': (handle_part_release, {}),
            'Machine Returns To Home Location': (handle_part_out, {})
        }

    def get_temperature(self):
        """Get current temperature settings"""
        return self.tool_heat_params.copy()

    def set_temperature(self, temp1=None, temp2=None):
        """Update temperature values"""
        if temp1 is not None:
            self.tool_heat_params['temp1'] = temp1
        if temp2 is not None:
            self.tool_heat_params['temp2'] = temp2
        
        handler = self.handlers['Heat Mould and Platten Up'][0]
        self.handlers['Heat Mould and Platten Up'] = (handler, self.tool_heat_params)
        return self.tool_heat_params 
    
    def handle_subprocess(self, subprocess):
        """Handle a subprocess based on its name"""
        handler_info = self.handlers.get(subprocess.name)
        
        if handler_info is None:
            return True
            
        handler, params = handler_info
        return handler(**params)


logger = logging.getLogger(__name__)

def trigger_blank_pressed():
    """Handle blank pressed process without timer value parameter"""
    client = Client("opc.tcp://10.10.42.11:4840")
    try:
        client.connect()
        logger.info("Connected to OPC UA server for Blank Pressed")
        
        # Call the blank pressed method
        parent_node = client.get_node('ns=3;s="05_BLANK_PRESSED_CALL_DB"')
        method_node = client.get_node('ns=3;s="05_BLANK_PRESSED_CALL_DB".Method')
        result = parent_node.call_method(method_node)
        
        logger.info(f"Blank Pressed method call result: {result}")
        return True
        
    except Exception as e:
        logger.error(f"Error in Blank Pressed: {str(e)}")
        return False
    finally:
        try:
            client.disconnect()
            logger.info("Disconnected from OPC UA server for Blank Pressed")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")


from django.utils.timezone import now 
def format_datetime(dt):
    """Format datetime to remove microseconds"""
    if not dt:
        return None
    return dt.replace(microsecond=0)

def format_duration(duration):
    """Format timedelta to HH:MM:SS format"""
    if not duration:
        return timedelta()
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def part_start(request, id):
    try:
        if request.method != 'POST':
            messages.error(request, 'Only POST method is allowed')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        subprocess = SubProcess.objects.get(id=id)
        current_time = format_datetime(now())
        
        # Initialize default values for all subprocesses
        subprocess.power = Decimal('0.000000')
        subprocess.CO2 = Decimal('0.00000')
        subprocess.materialWastageCost = Decimal('0.000')
        subprocess.materialScrapCost = Decimal('0.000')
        subprocess.materialPartCost = Decimal('0.000')
        subprocess.technicianLabourCost = Decimal('0.000')
        subprocess.supervisorLabourCost = Decimal('0.000')
        subprocess.labourSumCost = Decimal('0.000')
        subprocess.totalCost = Decimal('0.000')
        subprocess.operator = 'Technician' 
        subprocess.labourInput = 100  

        # Get all subprocesses for the process
        process = subprocess.process
        all_subprocesses = SubProcess.objects.filter(process=process)
        
        # Define subprocess groups
        initialization_to_blank_pressed = [
            'Initialisation', 'Heat Mould and Platten Up', 'Blank Loaded in Machine',
            'Temperature Reached and Platten Down', 'Blank Inside Press', 'Blank Pressed'
        ]
        mould_cooling_to_part_leaves = [
            'Mould Cooling', 'Part Released from Mould',
            'Machine Returns To Home Location', 'Part Leaves Machine'
        ]
        
        # Set instances based on subprocess type
        if subprocess.name in initialization_to_blank_pressed:
            subprocess.blankInstance = 1
        if subprocess.name in mould_cooling_to_part_leaves:
            subprocess.partInstance = 1
            
        # Special handling for specific subprocesses
        if subprocess.name == 'Initialisation':
            subprocess.interfaceTime = timedelta()
            
        elif subprocess.name == 'Blank Pressed':
            subprocess.scrapRate = 5  
            material_scrap_cost = Decimal('5.000') 
            subprocess.materialWastage = material_scrap_cost
            subprocess.materialScrapCost = material_scrap_cost
            subprocess.processTime = timedelta()
        
        # Calculate costs
        supervisor_rate = 58
        subprocess.supervisorLabourCost = (
            Decimal(str(supervisor_rate * subprocess.labourInput * 0.25 / 100))
        ).quantize(Decimal('0.001'))
        subprocess.labourSumCost = subprocess.supervisorLabourCost
        
        if subprocess.name == 'Blank Pressed':
            subprocess.totalCost = subprocess.supervisorLabourCost + subprocess.materialWastage
        else:
            subprocess.totalCost = subprocess.supervisorLabourCost
        
        # Save initial values before OPCUA call
        subprocess.save()
        
        # Handle OPCUA calls
        success = False
        if subprocess.name == 'Blank Pressed':
            success = trigger_blank_pressed()
        else:
            handler = SubProcessHandler()
            success = handler.handle_subprocess(subprocess)
        
        if success:
            subprocess.status = 1
            subprocess.date = datetime.now()
            subprocess.jobStart = current_time
            
            # Initialize processTime for specific processes
            if subprocess.name in ['Blank Pressed', 'Trim']:
                subprocess.processTime = timedelta()
            
            subprocess.save()
            messages.success(request, f'{subprocess.name} started successfully')
        else:
            messages.error(request, f'{subprocess.name} failed to start')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
        # Special handling for Blank Removed affecting Blank Waiting
        if subprocess.name == "Blank Removed":
            blank_waiting = all_subprocesses.filter(name='Blank Waiting').first()
            blank_removed = all_subprocesses.filter(name='Blank Removed').first()
            if blank_waiting and blank_waiting.status == 1:
                logger.info('Completing Blank Waiting subprocess due to Blank Removed start')
                
                blank_waiting.status = 2
                blank_waiting.jobEnd = current_time
                blank_removed.blankInstance = 1
                
                if blank_waiting.jobStart:
                    interface_duration = current_time - blank_waiting.jobStart
                    formatted_duration = format_duration(interface_duration)
                    
                    if blank_waiting.interfaceTime is None:
                        blank_waiting.interfaceTime = formatted_duration
                    else:
                        existing_time = format_duration(blank_waiting.interfaceTime)
                        blank_waiting.interfaceTime = existing_time + formatted_duration
                
                blank_waiting.save()
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            
    except Exception as e:
        logger.error(f'Error in part_start: {str(e)}')
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def part_approve(request, id):
    try:
        subprocess = SubProcess.objects.get(id=id)
        current_time = format_datetime(timezone.now())
        
        if not subprocess.jobStart:
            messages.error(request, 'Job has not started')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        subprocess.status = 2
        subprocess.jobEnd = current_time

        # Power and CO2 calculations for specific subprocesses
        power_data = {
            'Initialisation': Decimal('0.003451'),
            'Blank Inside Press': Decimal('0.002592'),
            'Machine Returns To Home Location': Decimal('0.003933')
        }

        if subprocess.name in power_data:
            # Set power consumption in kWh
            subprocess.power = power_data[subprocess.name]
            
            # Calculate CO2 emissions (power * 0.241 kg/kWh)
            subprocess.CO2 = (subprocess.power * Decimal('0.241')).quantize(Decimal('0.00001'))
            
            # Calculate power cost (power * 0.308 £/kWh)
            subprocess.powerCost = (subprocess.power * Decimal('0.308')).quantize(Decimal('0.001'))
            
            # Update total cost to include power cost
            if subprocess.totalCost is None:
                subprocess.totalCost = Decimal('0')
            subprocess.totalCost += subprocess.powerCost

        # Calculate time based on subprocess type
        if subprocess.name in ['Blank Pressed', 'Trim']:
            # Calculate process time
            process_duration = current_time - subprocess.jobStart
            formatted_duration = format_duration(process_duration)
            
            if subprocess.processTime is None:
                subprocess.processTime = formatted_duration
            else:
                existing_time = format_duration(subprocess.processTime)
                subprocess.processTime = existing_time + formatted_duration
            print(f"Calculated processTime for {subprocess.name}: {subprocess.processTime}")
        else:
            # Calculate interface time for other subprocesses
            if subprocess.jobStart:
                interface_duration = current_time - subprocess.jobStart
                formatted_duration = format_duration(interface_duration)
                
                if subprocess.interfaceTime is None:
                    subprocess.interfaceTime = formatted_duration
                else:
                    existing_time = format_duration(subprocess.interfaceTime)
                    subprocess.interfaceTime = existing_time + formatted_duration

        # Calculate material wastage cost when Final Weight is approved
        if subprocess.name == 'Part Assessment (Final Weight)':
            print("Processing Final Weight approval - calculating material wastage")
            
            initial_weight_sensor = Sensor.objects.filter(
                sub_process__process=subprocess.process,
                sub_process__name='Part Assessment (Initial Weight)'
            ).first()

            final_weight_sensor = Sensor.objects.filter(
                sub_process__process=subprocess.process,
                sub_process__name='Part Assessment (Final Weight)'
            ).first()

            if initial_weight_sensor and final_weight_sensor:
                if initial_weight_sensor.actualWeight is not None and final_weight_sensor.finalWeight is not None:
                    print(f"Initial Weight: {initial_weight_sensor.actualWeight}")
                    print(f"Final Weight: {final_weight_sensor.finalWeight}")
                    
                    weight_loss = initial_weight_sensor.actualWeight - final_weight_sensor.finalWeight
                    material_wastage_cost = abs(weight_loss) * 10
                    
                    trim_subprocess = subprocess.process.subprocess_set.filter(name='Trim').first()
                    if trim_subprocess:
                        trim_subprocess.materialWastageCost = material_wastage_cost
                        trim_subprocess.totalCost = material_wastage_cost
                        trim_subprocess.save()
                        print(f"Saved material wastage cost to Trim: £{material_wastage_cost}")

        # Handle Blank Placed approval initiating Blank Waiting
        if subprocess.name == "Blank Placed":
            blank_waiting = subprocess.process.subprocess_set.filter(name="Blank Waiting").first()
            if blank_waiting:
                blank_waiting.status = 1
                subprocess.date = datetime.now() 
                blank_waiting.jobStart = current_time
                blank_waiting.interfaceTime = timedelta()
                blank_waiting.blankInstance = 1
                blank_waiting.save()

        # Save the subprocess with updated information
        subprocess.save()
        messages.success(request, f'{subprocess.name} approved successfully')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        
    except Exception as e:
        logger.error(f'Error in part_approve: {str(e)}')
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))




# def trigger_init_call():
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         # Connect to server - removed session timeout setting since it's not needed
#         client.connect()
#         logger.info("Connected to OPC UA server.")
        
#         # Get the nodes
#         parent_node = client.get_node('ns=3;s="00_INIT_CALL_DB"')
#         method_node = client.get_node('ns=3;s="00_INIT_CALL_DB".Method')
        
#         # Call the method directly
#         result = parent_node.call_method(method_node)
#         logger.info(f"INIT_CALL method result: {result}")
#         return result
        
#     except Exception as e:
#         logger.error(f"Error in init_call: {str(e)}")
#         return False
        
#     finally:
#         try:
#             client.disconnect()
#             logger.info("Disconnected from OPC UA server.")
#         except Exception as e:
#             logger.error(f"Error during disconnect: {str(e)}")


# def trigger_tool_heat_call(temp1=50, temp2=70):
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         logger.info("Connected to OPC UA server.")
#         method_node = client.get_node('ns=3;s="01_TOOL_HEAT_CALL_DB".Method')
#         parent_node = method_node.get_parent()
#         input_value = ua.Variant([temp1, temp2], ua.VariantType.UInt16)
#         result = parent_node.call_method(method_node, input_value)
#         logger.info(f"TOOL_HEAT_CALL method result: {result}")
#         return result
#     except Exception as e:
#         logger.error(f"Error in tool_heat_call: {str(e)}")
#         return False
#     finally:
#         client.disconnect()
#         logger.info("Disconnected from OPC UA server.")

# def trigger_tool_ready_call():
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         parent_node = client.get_node('ns=3;s="03_TOOL_READY_CALL_DB"')
#         method_node = client.get_node('ns=3;s="03_TOOL_READY_CALL_DB".Method')
#         result = parent_node.call_method(method_node)
#         return result
#     except Exception as e:
#         print(f"Error in tool_ready_call: {e}")
#         return False
#     finally:
#         client.disconnect()

# def trigger_blank_in_call(param1=0, param2=0):
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         method_node = client.get_node('ns=3;s="04_BLANK_IN_CALL_DB".Method')
#         parent_node = method_node.get_parent()
#         input_value = ua.Variant([param1, param2], ua.VariantType.UInt16)
#         result = parent_node.call_method(method_node, input_value)
#         return result
#     except Exception as e:
#         print(f"Error in blank_in_call: {e}")
#         return False
#     finally:
#         client.disconnect()

# def trigger_blank_pressed_call():
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         parent_node = client.get_node('ns=3;s="05_BLANK_PRESSED_CALL_DB"')
#         method_node = client.get_node('ns=3;s="05_BLANK_PRESSED_CALL_DB".Method')
#         result = parent_node.call_method(method_node)
#         return result
#     except Exception as e:
#         print(f"Error in blank_pressed_call: {e}")
#         return False
#     finally:
#         client.disconnect()

# def trigger_tool_cool_call():
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         parent_node = client.get_node('ns=3;s="06_TOOL_COOL_CALL_DB"')
#         method_node = client.get_node('ns=3;s="06_TOOL_COOL_CALL_DB".Method')
#         result = parent_node.call_method(method_node)
#         return result
#     except Exception as e:
#         print(f"Error in tool_cool_call: {e}")
#         return False
#     finally:
#         client.disconnect()

# def trigger_part_release_call():
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         parent_node = client.get_node('ns=3;s="07_PART_RELLESE_CALL_DB"')
#         method_node = client.get_node('ns=3;s="07_PART_RELLESE_CALL_DB".Method')
#         result = parent_node.call_method(method_node)
#         return result
#     except Exception as e:
#         print(f"Error in part_release_call: {e}")
#         return False
#     finally:
#         client.disconnect()

# def trigger_part_out_call():
#     client = Client("opc.tcp://10.10.42.11:4840")
#     try:
#         client.connect()
#         parent_node = client.get_node('ns=3;s="08_PART_OUT_CALL_DB"')
#         method_node = client.get_node('ns=3;s="08_PART_OUT_CALL_DB".Method')
#         result = parent_node.call_method(method_node)
#         return result
#     except Exception as e:
#         print(f"Error in part_out_call: {e}")
#         return False
#     finally:
#         client.disconnect()



def part_bad(response, id):
    if response.user.is_authenticated:  # and (supervisor or admin):
        # DEFINING
        management, supervisor, admin = False, False, False
        sub_pro = SubProcess.objects.get(id=id)
        process = sub_pro.process
        processPartName = process.name
        orderedSubProList = process.order_subprocess_custom()
        indexList = list(orderedSubProList)
        index = indexList.index(sub_pro)
        project = sub_pro.process.project
        processPartList = []
        productList = []

        # ASSIGNING USER GROUP
        if response.user.groups.filter(name="Management").exists():
            management = True
        elif response.user.groups.filter(name="Supervisor").exists():
            supervisor = True
        elif response.user.groups.filter(name="Admin").exists():
            admin = True
        # DEFINING THE NEXT SUB-PROCESS/PROCESS IN THE PROCESS/PROJECT
        try:
            nextSub = orderedSubProList[index + 1]  # the next sub process in sequence
        except IndexError:
            if not process.endPoint:
                nextProcess = project.process_set.get(position=process.position + 1)
                nextSub = nextProcess.order_subprocess_custom().first()
        sub_pro.jobEnd = datetime.now().replace(microsecond=0)
        sub_pro.save()
        # DEFINING THE CURRENT INSTANCE ATTR AS A PART, PLY OR BLANK
        if sub_pro.partTask:
            attr = 'partInstance'

        elif sub_pro.blankTask:
            attr = 'blankInstance'

        elif sub_pro.plyTask:
            attr = 'plyInstance'

        currentInstance = getattr(sub_pro, attr)

        if currentInstance == None:
            messages.error(response, 'No parts to be made bad')  # ERROR HANDLING
        else:  # FINDING THE TASK SO WE CAN CREATE LISTS FOR SAVING DATA
            if sub_pro.partTask:
                partInst = PartInstance.objects.get(instance_id=currentInstance)
                for part in partInst.part_set.all():
                    productList.append(part)
                    processPartList.append(part.processpart_set.get(processName=processPartName))
            elif sub_pro.blankTask:
                blankInst = BlankInstance.objects.get(instance_id=sub_pro.blankInstance)
                for blank in blankInst.blank_set.all():
                    productList.append(blank)
                    processPartList.append(blank.processpart_set.get(processName=processPartName))
            elif sub_pro.plyTask:
                plyInst = PlyInstance.objects.get(instance_id=currentInstance)
                for ply in plyInst.ply_set.all():
                    productList.append(ply)
                    processPartList.append(ply.processpart_set.get(processName=processPartName))
            # LOOPING THROUGH PROCESS PARTS SAVING SENSOR DATA
            for processPart in processPartList:
                # save sensor data related to process
                sensorName = ""
                for sensor in process.sensor_set.all():  # loop through sensor fields and mirror to sensor data
                    sensorData = processPart.sensordata_set.create(sensorName=sensor.name, status=sensor.status)
                    sensorData.mirrorSensorAttributes(sensor)

                try:
                    previousSub = processPart.subprocesspart_set.last()  # get previous sub from previous sub process
                    sub_pro.wastedTime = sub_pro.jobStart - previousSub.jobEnd  # get wasted time
                except:
                    sub_pro.wastedTime = timedelta()

                sub_pro.save()
                # create sub process part and assign values to fields
                subProcessPart = SubProcessPart.objects.create(subProcessName=sub_pro.name, processPart=processPart,
                                                               date=date.today(), processTime=sub_pro.processTime,
                                                               interfaceTime=sub_pro.interfaceTime)

                subProcessPart.mirrorAttributes(sub_pro)

                subProcessPart.updateIntervals()

                processPart.updateProcessPartMachines(sub_pro.process)
                processPart.updateWholeProcessPart()
                processPart.save()

                # iterate through sensors associated with sub process's
                for sensor in sub_pro.sensor_set.all():
                    # create sensor data object and assign values to fields
                    sensorData = SensorData.objects.create(sensorName=sensor.name, subProcessPart=subProcessPart,
                                                           status=sensor.status)
                    sensorData.mirrorSensorAttributes(sensor)
            # LOOPING THROUGH THE PRODUCTS SAVING THE MATERIAL THATS BEEN USED
            for product in productList:

                for attr in project._meta.fields:  # loop through project attributes and assign to part
                    if "Cost" in attr.name or attr.name == "part" or attr.name == "date" or attr.name == "plyCutter" or attr.name == "sortPickAndPlace" or attr.name == "blanksPickAndPlace" or attr.name == "preformCell" or attr.name == "id":
                        pass
                    else:
                        value = getattr(project, attr.name)
                        setattr(product, attr.name, value)

                product.updateWholePart()
                product.submitted = True
                product.badPart = True
                product.save()

            sub_pro.resetAttributes()

            # for each in process.repeatblock_set.all():
            #   each.iteration = 0
            #   each.finished = False
            #   each.save()

            messages.success(response, "Part Data successfully submitted!")
            sub_pro.status = 3
            sub_pro.save()
            process_set = project.order_process_custom()
            # RESET CURRENT INSTANCE
            if sub_pro.partTask:
                partInstance = PartInstance.objects.get(instance_id=currentInstance)
                partInstance.delete()
            elif sub_pro.plyTask:
                plyInstance = PlyInstance.objects.get(instance_id=currentInstance)
                plyInstance.delete()
            elif sub_pro.blankTask:
                blankInstance = BlankInstance.objects.get(instance_id=currentInstance)
                blankInstance.delete()

        return redirect('/' + str(process.id))
    return redirect('/')


def viewImages(response, id):
    if response.user.is_authenticated:
        management = False
        supervisor = False
        technician = False

        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        elif response.user.groups.filter(name='Technician').exists():
            technician = True

        if management or supervisor or technician:
            project = Project.objects.get(id=id)
            return render(response, 'Main/viewImages.html', {'selected_project': project})
        else:
            return redirect('/')
    else:
        return redirect('/')


def viewImagesDetail(response, id):
    if response.user.is_authenticated:
        management = False
        supervisor = False

        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True

        if management or supervisor:
            project = Project.objects.get(id=id)
            return render(response, 'Main/viewImagesDetail.html', {'selected_project': project})
        else:
            return redirect('/')
    else:
        return redirect('/')


def viewImageSpecific(response, id, part):
    if response.user.is_authenticated:
        management = False
        supervisor = False

        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True

        if management or supervisor:
            if part == 0:
                subpro = SubProcess.objects.get(id=id)
                project = subpro.process.project
            else:
                subpro = SubProcessPart.objects.get(id=id)
                project = subpro.processPart.part.project

            return render(response, 'Main/viewImageSpecific.html', {'sub_pro': subpro, 'project': project})
        else:
            return redirect('/')
    else:
        return redirect('/')


def viewFiles(response, id):
    if response.user.is_authenticated:
        project = Project.objects.get(id=id)
        management = False
        supervisor = False

        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True

        if management or supervisor:
            return render(response, 'Main/viewFiles.html', {'project': project})
        else:
            return redirect('/')
    else:
        return redirect('/')


def downloadFile(response, id, part):
    if response.user.is_authenticated:
        if part == 0:
            sub_pro = SubProcess.objects.get(id=id)
        else:
            sub_pro = SubProcessPart.objects.get(id=id)

        if response.user.groups.filter(name='Management').exists():
            management = True
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True

        if management or supervisor:

            filename = sub_pro.file.name.split('/')[-1]
            response = HttpResponse(sub_pro.file, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename=%s' % filename

            return response
        else:
            return redirect('/')
    else:
        return redirect('/')

def connect_to_plc(request):
    try:
        client = Client("opc.tcp://10.10.42.11:4840")
        client.connect()
        client.disconnect()
        return JsonResponse({"status": "Connected to Press PLC via UA Expert"})
    except Exception as e:
        return JsonResponse({"status": f"Connection failed: {str(e)}"})

def noise_chart(request):
    return render(request, 'Main/noise_chart.html')

def go_to_edge_detection(request, id):
    return redirect('edge_detection:edge_detection', id=id)

def get_sensor_data(request, sensor_id):
    # Get the sensor object
    sensor = get_object_or_404(Sensor, id=sensor_id)
    
    # Return maxTemp and minTemp as JSON
    data = {
        'maxTemp': sensor.maxTemp,
        'minTemp': sensor.minTemp
    }
    
    return JsonResponse(data)

def get_current_process_id(request, process_id):
    try:
        process = Process.objects.get(id=process_id)
        return JsonResponse({'current_process_id': process.id})
    except Process.DoesNotExist:
        # Instead of returning an error, return a more user-friendly message
        return JsonResponse({'message': 'There is no further process'}, status=200)

def trigger_shuttle(request):
    message = trigger_shuttle_system()
    return JsonResponse({'message': message})

def export_project_pdf(request, id):
    try:
        project = Project.objects.get(id=id)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(letter),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Project Header
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph("{}'s Project Data - ID: {}".format(project.project_name, project.id), title_style))
        
        # Process Analysis
        processes = prepare_process_data(project.process_set.all().order_by('id'))
        lastProcess = processes.last()
        
        for process in processes:
            # Process Header
            elements.append(Paragraph("Process: {}".format(process.name), styles['Heading2']))
            
            # Process VSM Table
            vsm_data = [
                ['VSM Values'],
                ['Interface Time', str(process.interfaceTime)],
                ['Process Time', str(process.processTime)],
                ['Material Wastage', '£{}'.format(process.materialWastage)],
                ['Labour Cost', '£{}'.format(process.labourSumCost)],
                ['Power Cost', '£{}'.format(process.powerCost)],
                ['Total Cost', '£{}'.format(process.totalCost)]
            ]
            
            vsm_table = Table(vsm_data, colWidths=[3*inch, 4*inch])  
            vsm_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white)
            ]))
            elements.append(vsm_table)
            elements.append(Spacer(1, 15))
            
            # Subprocess Analysis
            subprocesses = process.subprocess_set.all()
            for subprocess in subprocesses:
                # Subprocess Header
                elements.append(Paragraph("Subprocess: {}".format(subprocess.name), styles['Heading3']))
                
                # Subprocess Details Table
                subprocess_data = [
                    ['Metric', 'Value'],
                    ['Operator', subprocess.operator],
                    ['Labour Input', '{:.2f}%'.format(subprocess.labourInput)],
                    ['Process/Interface Time', str(subprocess.processTime if subprocess.name in ['Load and Cut Ply', 'Pickup Ply & Weld', 'Trim'] else subprocess.interfaceTime)],
                    ['Job Start', str(subprocess.jobStart)],
                    ['Job End', str(subprocess.jobEnd)],
                    ['Scrap Rate', '{:.2f}%'.format(subprocess.scrapRate)],
                    ['Power Consumption', '{:.2f} Kwh'.format(subprocess.power)],
                    ['CO2 emissions', '{:.2f} Kg'.format(subprocess.CO2)],
                    ['Material Waste Cost', '£{:.3f}'.format(subprocess.materialWastageCost)],
                    ['Material Scrap Cost', '£{:.3f}'.format(subprocess.materialScrapCost)],
                    ['Material Part Cost', '£{:.3f}'.format(subprocess.materialPartCost)],
                    ['Technician Labour Cost', '£{:.3f}'.format(subprocess.technicianLabourCost)],
                    ['Supervisor Labour Cost', '£{:.3f}'.format(subprocess.supervisorLabourCost)],
                    ['Total Cost', '£{:.3f}'.format(subprocess.totalCost)]
                ]
                
                subprocess_table = Table(subprocess_data, colWidths=[3*inch, 4*inch])
                subprocess_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white)
                ]))
                elements.append(subprocess_table)
                elements.append(Spacer(1, 10))
                
                # Subprocess VSM
                sub_vsm_data = [
                    ['VSM Values'],
                    ['Interface Time', str(subprocess.interfaceTime)],
                    ['Process Time', str(subprocess.processTime)],
                    ['Material Wastage', '£{:.3f}'.format(subprocess.materialWastage)],
                    ['Labour Cost', '£{:.3f}'.format(subprocess.labourSumCost)],
                    ['Power Cost', '£{:.3f}'.format(subprocess.powerCost)],
                    ['Total Cost', '£{:.3f}'.format(subprocess.totalCost)]
                ]
                
                sub_vsm_table = Table(sub_vsm_data, colWidths=[3*inch, 4*inch])  # Adjusted column widths
                sub_vsm_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white)
                ]))
                elements.append(sub_vsm_table)
                elements.append(Spacer(1, 15))
            
            # Add page break between processes
            if process != lastProcess:
                elements.append(PageBreak())
        
        # Total Values for all processes
        totals = calculate_total_values(processes)
        elements.append(Paragraph("Total Process Values", styles['Heading2']))
        totals_data = [
            ['Total Values'],
            ['Total Interface Time', str(totals["total_interface_time"])],
            ['Total Process Time', str(totals["total_process_time"])],
            ['Total Material Wastage', '£{}'.format(totals["total_material_wastage"])],
            ['Total Labour Cost', '£{}'.format(totals["total_labour_cost"])],
            ['Total Power Cost', '£{}'.format(totals["total_power_cost"])],
            ['Total Cost', '£{}'.format(totals["total_cost"])]
        ]
        
        totals_table = Table(totals_data, colWidths=[3*inch, 4*inch]) 
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey)
        ]))
        elements.append(totals_table)
        
        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="project_{}_analysis.pdf"'.format(id)
        response.write(pdf)
        return response
        
    except Exception as e:
        messages.error(request, 'Error generating PDF: {}'.format(str(e)))
        return redirect('/p{}'.format(id))
  

import os
import io
from PIL import Image as PILImage

from django.http import HttpResponse
from django.shortcuts import redirect
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def crop_image(input_path, output_path):
    """
    Remove borders from an image
    - Open the image
    - Automatically crop out white or near-white borders
    """
    try:
        with PILImage.open(input_path) as img:
            # Convert image to RGB if it's not already
            img = img.convert('RGB')
            
            # Get image data
            data = list(img.getdata())
            
            # Find image boundaries
            width, height = img.size
            left, top = width, height
            right, bottom = 0, 0
            
            for y in range(height):
                for x in range(width):
                    pixel = data[y * width + x]
                    # Check if pixel is not white (allowing some variance)
                    if not all(v > 240 for v in pixel):
                        left = min(left, x)
                        top = min(top, y)
                        right = max(right, x)
                        bottom = max(bottom, y)
            
            # Crop the image
            cropped_img = img.crop((left, top, right+1, bottom+1))
            
            # Save the cropped image
            cropped_img.save(output_path)
    except Exception as e:
        print(f"Error processing image {input_path}: {e}")

def preprocess_images(input_dir, output_dir):
    """
    Preprocess all images in a directory
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each image
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            crop_image(input_path, output_path)

# Preprocess images before PDF generation
preprocess_images('/home/airborne_amot/screenshots', '/home/airborne_amot/processed_screenshots')
preprocess_images('/home/airborne_amot/results', '/home/airborne_amot/processed_results')

def scale_image_for_pdf(img_path, max_width=7*inch, max_height=5*inch):
    """
    Scale image to fit within specified max dimensions while maintaining aspect ratio
    """
    with PILImage.open(img_path) as pil_img:
        # Get original image dimensions
        orig_width, orig_height = pil_img.size
        
        # Calculate scaling factor
        width_ratio = max_width / orig_width
        height_ratio = max_height / orig_height
        scale_ratio = min(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = int(orig_width * scale_ratio)
        new_height = int(orig_height * scale_ratio)
        
        # Resize image
        resized_img = pil_img.resize((new_width, new_height), PILImage.LANCZOS)
        
        # Temporary path for resized image
        temp_path = img_path.replace('.', '_scaled.')
        resized_img.save(temp_path)
        
        return temp_path

from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import navy
from reportlab.lib.units import inch
import os
import io

def export_pdf_supervisor(request, id):
    try:
        processes = Process.objects.filter(name__in=["Form Preform", "Final Inspection"])
        
        # Define page size and margins
        PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)
        MARGIN = 40  # Increased side margins
        BOTTOM_MARGIN = 60  # Increased bottom margin for logo
        TOP_MARGIN = 40  # Explicit top margin
        
        # Calculate maximum content area
        MAX_CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)
        MAX_CONTENT_HEIGHT = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=MARGIN,
            leftMargin=MARGIN,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN
        )

        elements = []
        styles = getSampleStyleSheet()

        # Define all styles at the beginning
        approval_style = ParagraphStyle(
            'Approval',
            parent=styles['Normal'],
            fontSize=14,
            alignment=1,  # Center alignment
            spaceAfter=10,
            spaceBefore=20,
            fontName='Helvetica-Bold'  # Make text bold
        )

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=15,
            alignment=1
        )

        report_info_style = ParagraphStyle(
            'ReportInfo',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            spaceAfter=5
        )

        process_style = ParagraphStyle(
            'Process',
            parent=styles['Heading2'],
            fontSize=20,
            spaceAfter=10,
            alignment=1,
            textColor=navy
        )

        subprocess_style = ParagraphStyle(
            'Subprocess',
            parent=styles['Heading3'],
            fontSize=16,
            spaceAfter=15,
            alignment=1
        )

        page_number_style = ParagraphStyle(
            'PageNumber',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,  # Center alignment
            textColor=navy
        )

        # Add report header
        elements.append(Paragraph("The Form Preform and Final Inspection System Decision Report", title_style))
        elements.append(Paragraph("Report to: Lucy Sun", report_info_style))
        elements.append(Paragraph("Reported by: Emin Alper Sensoy", report_info_style))
        elements.append(Paragraph("Date: 9th of January, 2025", report_info_style))
        elements.append(Spacer(1, 15))

        # Set directories
        screenshots_dir = '/home/airborne_amot/processed_screenshots'
        results_dir = '/home/airborne_amot/processed_results'

        # Configure logo for footer
        logo_path = os.path.join(results_dir, 'airbornelogo.png')
        im = Image(logo_path)
        im.drawHeight = 0.3*inch  # Reduced height
        im.drawWidth = 0.6*inch   # Reduced width proportionally

        def add_logo_and_page_number(canvas, doc):
            canvas.saveState()
            
            # Position logo in bottom right corner
            logo_x = doc.pagesize[0] - im.drawWidth - 40  # 40 points from right edge
            logo_y = 35  # 35 points from bottom
            
            # Add logo
            im.drawOn(canvas, logo_x, logo_y)
            
            # Add page number for all pages after the cover page
            page_num = canvas.getPageNumber()
            if page_num > 1:  # Skip the first/cover page
                adjusted_page_num = page_num - 1  # Start counting from 1 after cover
                page_number = Paragraph(str(adjusted_page_num), page_number_style)  # Just the number
                
                # Center the page number at the bottom
                page_width = doc.pagesize[0]
                page_number.wrapOn(canvas, 50, 30)  # Reduced width since text is shorter
                page_number.drawOn(canvas, (page_width - 50) / 2, 35)
            
            canvas.restoreState()

        # Function to safely add image with consistent sizing
        def add_image(img_path):
            try:
                with PILImage.open(img_path) as pil_img:
                    img_width, img_height = pil_img.size
                
                img = Image(img_path)
                
                # Adjust scaling based on the image name and subprocess
                filename = os.path.basename(img_path)
                
                if filename == 'BlankPressed1.png':
                    scaling_factor = 0.85  # Larger for first Blank Pressed image
                    safe_max_height = MAX_CONTENT_HEIGHT * 0.85
                elif filename == 'BlankPressed2.png':
                    scaling_factor = 0.85  # Larger for second Blank Pressed image
                    safe_max_height = MAX_CONTENT_HEIGHT * 0.85
                elif filename == 'temperaturereachedplattendown.png':
                    scaling_factor = 0.65  # Keep the smaller scale for this one
                    safe_max_height = MAX_CONTENT_HEIGHT * 0.85
                else:
                    scaling_factor = 0.85  # Standard scale for other images
                    safe_max_height = MAX_CONTENT_HEIGHT * 0.85
                
                safe_max_width = MAX_CONTENT_WIDTH * scaling_factor
                draw_width = min(MAX_CONTENT_WIDTH * scaling_factor, safe_max_width)
                
                aspect_ratio = float(img_height) / float(img_width)
                draw_height = draw_width * aspect_ratio
                
                if draw_height > safe_max_height:
                    draw_height = safe_max_height
                    draw_width = draw_height / aspect_ratio
                
                img.drawWidth = draw_width
                img.drawHeight = draw_height
                
                return img
                
            except Exception as e:
                print(f"Error processing image {img_path}: {str(e)}")
                img = Image(img_path)
                img.drawWidth = MAX_CONTENT_WIDTH * 0.6
                img.drawHeight = MAX_CONTENT_HEIGHT * 0.6
                return img

        # Image mapping dictionary
        subprocess_image_map = {
            'Initialisation': 'initialisation.png',
            'Heat Mould and Platten Up': 'heatmould.png',
            'Blank Loaded in Machine': 'blankloaded.png',
            'Temperature Reached and Platten Down': 'temperaturereachedplattendown.png',
            'Blank Inside Press': 'blankinsidepress.png',
            'Blank Pressed': ['BlankPressed1.png', 'BlankPressed2.png'],
            'Mould Cooling': 'mouldcooling.png',
            'Part Released from Mould': 'partleavesmould.png',
            'Machine Returns To Home Location': 'machinereturnstohomelocation.png',
            'Part Assessment (Initial Weight)': 'partassessmentinitialweight.png',
            'Trim': 'trim.png',
            'Part Assessment (Final Weight)': 'partassessmentfinalweight.png'
        }

        # Process the documents
        for process in processes:
            elements.append(PageBreak())
            elements.append(Paragraph(f"Process: {process.name}", process_style))
            
            subprocesses = SubProcess.objects.filter(process=process)
            
            for subprocess in subprocesses:
                elements.append(Paragraph(f"Subprocess: {subprocess.name}", subprocess_style))

                if subprocess.name == "Part Assessment (Final Geometry)":
                    elements.append(Paragraph("Original DXF Shape", subprocess_style))
                    dxf_path = os.path.join(results_dir, 'new_dxf.png')
                    if os.path.exists(dxf_path):
                        img = add_image(dxf_path)
                        if img:
                            elements.append(img)
                    
                    elements.append(PageBreak())
                    elements.append(Paragraph("Original Image", subprocess_style))
                    original_path = os.path.join(results_dir, 'original_image.jpg')
                    if os.path.exists(original_path):
                        img = add_image(original_path)
                        if img:
                            elements.append(img)
                    
                    elements.append(PageBreak())
                    elements.append(Paragraph("Edge Detection Result", subprocess_style))
                    output_path = os.path.join(results_dir, 'new_edresult.png')
                    if os.path.exists(output_path):
                        img = add_image(output_path)
                        if img:
                            elements.append(img)
                elif subprocess.name == "Part Leaves Machine":
                    elements.append(Spacer(1, 20))  # Add some space
                    elements.append(Paragraph("Approve this subprocess when the manual operation is completed", approval_style))
                    elements.append(Spacer(1, 20))  # Add some space after
                else:
                    if subprocess.name in subprocess_image_map:
                        image_names = subprocess_image_map[subprocess.name]
                        if not isinstance(image_names, list):
                            image_names = [image_names]
                        
                        for image_name in image_names:
                            img_path = os.path.join(screenshots_dir, image_name)
                            if os.path.exists(img_path):
                                img = add_image(img_path)
                                if img:
                                    elements.append(img)
                
                # Add page break if not the last subprocess
                if subprocess != list(subprocesses)[-1]:
                    elements.append(PageBreak())

        # Build PDF
        doc.build(elements, onFirstPage=add_logo_and_page_number, onLaterPages=add_logo_and_page_number)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="system_decision_report_{id}.pdf"'
        response.write(pdf)
        return response

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return redirect(f'/p{id}')
def export_all_plies_pdf(request, id):
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to export PDF')
        return redirect('login')
    
    try:
        project = Project.objects.get(id=2)  # Fixed: Now using the passed id parameter
        if not (request.user.groups.filter(name='Management').exists() or 
                request.user.groups.filter(name='Supervisor').exists()):
            messages.error(request, 'Permission denied')
            return redirect('home')
            
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30
        )
        elements.append(Paragraph(f"Project {project.id} - Plies Report", title_style))
        
        plies = Ply.objects.filter(project=project)
        num_plies = len(plies)
        cut_plies_process = Process.objects.get(project=project, name='Cut Plies')
        load_cut_subprocess = cut_plies_process.subprocess_set.get(name='Load and Cut Ply')
        ply_area_ratio = 0.25

        total_process_time = load_cut_subprocess.processTime if load_cut_subprocess.processTime else timedelta(seconds=0)
        individual_process_time = total_process_time / num_plies if num_plies > 0 else timedelta(seconds=0)
        
        individual_tech_cost = float(load_cut_subprocess.technicianLabourCost) * 4 / num_plies if load_cut_subprocess.technicianLabourCost else 0
        individual_power = float(load_cut_subprocess.power) / num_plies if load_cut_subprocess.power else 0
        individual_co2 = float(load_cut_subprocess.CO2) / num_plies if load_cut_subprocess.CO2 else 0
        
        for index, ply in enumerate(plies):
            elements.append(Paragraph(f"Ply {ply.ply_id} - {ply.name}", styles['Heading2']))
            elements.append(Spacer(1, 12))
            
            individual_waste_cost = float(load_cut_subprocess.materialWastageCost) * ply_area_ratio if load_cut_subprocess.materialWastageCost else 0
            individual_scrap_cost = float(load_cut_subprocess.materialScrapCost) if load_cut_subprocess.materialScrapCost else 0
            material_part_cost = float(load_cut_subprocess.materialPartCost) if load_cut_subprocess.materialPartCost else 0
            supervisor_cost = float(load_cut_subprocess.supervisorLabourCost) if load_cut_subprocess.supervisorLabourCost else 0
            
            total_cost = (
                individual_waste_cost +
                individual_scrap_cost +
                material_part_cost +
                individual_tech_cost +
                supervisor_cost
            )

            # Set job end time based on ply
            if ply.ply_id == 1707 and ply.name == 'PLYTYPE_121_2':
                job_end = '2024-12-10 14:01:21'
            else:
                job_end = 'N/A'
            
            subprocess_data = [
                ['Process Information', ''],
                ['Operator', load_cut_subprocess.operator or 'N/A'],
                ['Labour Input', f"{load_cut_subprocess.labourInput}%" if load_cut_subprocess.labourInput else '0%'],
                ['Process Time', str(individual_process_time)],
                ['Interface Time', str(load_cut_subprocess.interfaceTime) if load_cut_subprocess.interfaceTime else 'N/A'],
                ['Job Start', load_cut_subprocess.jobStart.strftime('%Y-%m-%d %H:%M:%S') if index == 0 and load_cut_subprocess.jobStart else 'N/A'],
                ['Job End', job_end],
                ['Scrap Rate', f"{load_cut_subprocess.scrapRate}%" if load_cut_subprocess.scrapRate else '0%'],
                ['Batch Size', str(load_cut_subprocess.batchSize) if load_cut_subprocess.batchSize else 'N/A'],
                ['Power Consumption', f"{individual_power:.6f} Kwh"],
                ['CO2 Emissions', f"{individual_co2:.6f} Kg"],
                ['Material Waste Cost', f"£{individual_waste_cost:.3f}"],
                ['Material Scrap Cost', f"£{individual_scrap_cost:.3f}"],
                ['Material Part Cost', f"£{material_part_cost:.3f}"],
                ['Technician Labour Cost', f"£{individual_tech_cost:.3f}"],
                ['Supervisor Labour Cost', f"£{supervisor_cost:.3f}"],
                ['Total Cost', f"£{total_cost:.3f}"]
            ]
            
            subprocess_table = Table(subprocess_data, colWidths=[2.5*inch, 3.5*inch])
            subprocess_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(subprocess_table)
            
            if ply != plies.last():
                elements.append(PageBreak())
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="project_{id}_plies.pdf"'
        response.write(pdf)
        return response
        
    except Project.DoesNotExist:
        messages.error(request, 'Project not found')
        return redirect('/')
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('/')


from django.http import JsonResponse
from django.utils import timezone
import requests
import jwt



import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from django.utils import timezone

from .models import SensorDataStorage

def export_sensor_data_pdf(request):
    """
    Generate a comprehensive PDF export of all sensor data and print values
    
    Returns:
        HttpResponse: PDF file with full-page sensor data table
    """
    print("\n=== Starting PDF Export ===")
    
    # Retrieve all sensor data
    sensor_data = SensorDataStorage.objects.all().order_by('-timestamp')
    print(f"Retrieved {sensor_data.count()} records from database")
    
    # Create a buffer
    buffer = io.BytesIO()
    page_size = landscape(letter)
    
    # Adjust margins to maximize available space
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=page_size,
        leftMargin=1,
        rightMargin=1,
        topMargin=1,
        bottomMargin=1
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        alignment=TA_CENTER,
        fontSize=7,  # Tiny title
        spaceAfter=1  # Minimal space after title
    )
    
    # Content elements
    story = []
    story.append(Paragraph("Sensor Data Report", title_style))
    
    # Prepare table header
    table_data = [
        [
            'Timestamp', 'Big\nCabinet', 'KUKA\nCabinet', 'CNC\nRouter', 'Big\nOven', 'Total', 'Average', 'PM1.0', 'PM2.5', 'PM10', 'Noise', 'Acc\nX', 'Acc\nY', 'Acc\nZ', 'Ang Vel\nX', 'Ang Vel\nY', 'Ang Vel\nZ', 'Roll', 'Pitch', 'Yaw', 'Temp', 'Humidity', 'VOC', 'Weight', 'Load\nMean', 'Torque\n1', 'Torque\n2'
        ]
    ]

    # Add sensor data rows
    for record in sensor_data:
        table_data.append([
            record.timestamp.strftime('%Y-%m-%d\n%H:%M:%S'),
            f"{record.big_cabinet_power:.2f}" if record.big_cabinet_power is not None else 'N/A',
            f"{record.kuka_cabinet_power:.2f}" if record.kuka_cabinet_power is not None else 'N/A',
            f"{record.cnc_router_power:.2f}" if record.cnc_router_power is not None else 'N/A',
            f"{record.big_oven_power:.2f}" if record.big_oven_power is not None else 'N/A',
            f"{record.total_power:.2f}" if record.total_power is not None else 'N/A',
            f"{record.average_power:.2f}" if record.average_power is not None else 'N/A',
            f"{record.pm1_concentration:.1f}" if record.pm1_concentration is not None else 'N/A',
            f"{record.pm25_concentration:.1f}" if record.pm25_concentration is not None else 'N/A',
            f"{record.pm10_concentration:.1f}" if record.pm10_concentration is not None else 'N/A',
            f"{record.noise_level:.1f}" if record.noise_level is not None else 'N/A',
            f"{record.acceleration_x:.2f}" if record.acceleration_x is not None else 'N/A',
            f"{record.acceleration_y:.2f}" if record.acceleration_y is not None else 'N/A',
            f"{record.acceleration_z:.2f}" if record.acceleration_z is not None else 'N/A',
            f"{record.angular_velocity_x:.1f}" if record.angular_velocity_x is not None else 'N/A',
            f"{record.angular_velocity_y:.1f}" if record.angular_velocity_y is not None else 'N/A',
            f"{record.angular_velocity_z:.1f}" if record.angular_velocity_z is not None else 'N/A',
            f"{record.roll_angle:.1f}" if record.roll_angle is not None else 'N/A',
            f"{record.pitch_angle:.1f}" if record.pitch_angle is not None else 'N/A',
            f"{record.yaw_angle:.1f}" if record.yaw_angle is not None else 'N/A',
            f"{record.temperature:.1f}" if record.temperature is not None else 'N/A',
            f"{record.humidity:.1f}" if record.humidity is not None else 'N/A',
            f"{record.voc_index}" if record.voc_index is not None else 'N/A',
            f"{record.weight:.2f}" if record.weight is not None else 'N/A',
            f"{record.motor_load_mean:.2f}" if record.motor_load_mean is not None else 'N/A',
            f"{record.actual_torque_percentage:.1f}" if record.actual_torque_percentage is not None else 'N/A',
            f"{record.actual_torque_percentage2:.1f}" if record.actual_torque_percentage2 is not None else 'N/A'
        ])

    # Create and style table
    table = Table(
        table_data,
        repeatRows=1,
        spaceAfter=0,
        spaceBefore=0,
        # Distribute columns evenly across the page width
        colWidths=[f"{100/len(table_data[0])}%" for _ in range(len(table_data[0]))]
    )
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 5),  # Tiny header font
        ('FONTSIZE', (0,1), (-1,-1), 4),  # Extremely small data font
        ('BOTTOMPADDING', (0,0), (-1,0), 1),  # Minimal padding
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 0.2, colors.black),  # Thinnest grid lines
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.lightgrey])
    ]))
    
    # Add table to story
    story.append(table)
    
    # Build PDF with default page template
    doc.build(story)
    
    # Create response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sensor_data_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    response.write(pdf)
    
    print("\n=== PDF Export Complete ===")
    return response

import csv
from django.http import HttpResponse
from django.utils import timezone

from .models import SensorDataStorage

def export_sensor_data_csv(request):
    """
    Generate a comprehensive CSV export of all sensor data
    
    Returns:
        HttpResponse: CSV file with sensor data
    """
    # Retrieve all sensor data
    sensor_data = SensorDataStorage.objects.all().order_by('-timestamp')
    
    # Create HTTP response with CSV mime type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sensor_data_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    # Write header row
    header = [
        'Timestamp'.center(20), 
        'Big Cabinet Power (kWh)'.center(20), 
        'KUKA Cabinet Power (kWh)'.center(20),
        'CNC Router Power (kWh)'.center(20),
        'Big Oven Power (kWh)'.center(20),
        'Total Power (kWh)'.center(20),
        'Average Power (kWh)'.center(20),
        'PM1.0 (μg/m³)'.center(20),
        'PM2.5 (μg/m³)'.center(20),
        'PM10 (μg/m³)'.center(20),
        'Noise (dB)'.center(20),
        'Acceleration X (m/s²)'.center(20),
        'Acceleration Y (m/s²)'.center(20), 
        'Acceleration Z (m/s²)'.center(20),
        'Angular Velocity X (°/s)'.center(20),
        'Angular Velocity Y (°/s)'.center(20),
        'Angular Velocity Z (°/s)'.center(20),
        'Roll Angle (°)'.center(20),
        'Pitch Angle (°)'.center(20),
        'Yaw Angle (°)'.center(20),
        'Temperature (°C)'.center(20),
        'Humidity (%)'.center(20),
        'VOC Index'.center(20),
        'Weight (kg)'.center(20),
        'Motor Load Mean'.center(20),
        'Torque 1 (%)'.center(20),
        'Torque 2 (%)'.center(20)
    ]
    writer.writerow(header)
    
    # Write data rows
    prev_timestamp = None
    for record in sensor_data:
        if prev_timestamp == record.timestamp.strftime('%Y-%m-%d %H:%M:%S'):
            continue
        prev_timestamp = record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        row = [
            prev_timestamp.center(20),
            f"{record.big_cabinet_power:.4f}".center(20) if record.big_cabinet_power is not None else 'N/A'.center(20),
            f"{record.kuka_cabinet_power:.4f}".center(20) if record.kuka_cabinet_power is not None else 'N/A'.center(20),
            f"{record.cnc_router_power:.4f}".center(20) if record.cnc_router_power is not None else 'N/A'.center(20),
            f"{record.big_oven_power:.4f}".center(20) if record.big_oven_power is not None else 'N/A'.center(20),
            f"{record.total_power:.4f}".center(20) if record.total_power is not None else 'N/A'.center(20),
            f"{record.average_power:.4f}".center(20) if record.average_power is not None else 'N/A'.center(20),
            f"{record.pm1_concentration:.2f}".center(20) if record.pm1_concentration is not None else 'N/A'.center(20),
            f"{record.pm25_concentration:.2f}".center(20) if record.pm25_concentration is not None else 'N/A'.center(20),
            f"{record.pm10_concentration:.2f}".center(20) if record.pm10_concentration is not None else 'N/A'.center(20),
            f"{record.noise_level:.1f}".center(20) if record.noise_level is not None else 'N/A'.center(20),
            f"{record.acceleration_x:.3f}".center(20) if record.acceleration_x is not None else 'N/A'.center(20),
            f"{record.acceleration_y:.3f}".center(20) if record.acceleration_y is not None else 'N/A'.center(20),
            f"{record.acceleration_z:.3f}".center(20) if record.acceleration_z is not None else 'N/A'.center(20),
            f"{record.angular_velocity_x:.2f}".center(20) if record.angular_velocity_x is not None else 'N/A'.center(20),
            f"{record.angular_velocity_y:.2f}".center(20) if record.angular_velocity_y is not None else 'N/A'.center(20),
            f"{record.angular_velocity_z:.2f}".center(20) if record.angular_velocity_z is not None else 'N/A'.center(20),
            f"{record.roll_angle:.2f}".center(20) if record.roll_angle is not None else 'N/A'.center(20),
            f"{record.pitch_angle:.2f}".center(20) if record.pitch_angle is not None else 'N/A'.center(20),
            f"{record.yaw_angle:.2f}".center(20) if record.yaw_angle is not None else 'N/A'.center(20),
            f"{record.temperature:.1f}".center(20) if record.temperature is not None else 'N/A'.center(20),
            f"{record.humidity:.1f}".center(20) if record.humidity is not None else 'N/A'.center(20),
            f"{record.voc_index}".center(20) if record.voc_index is not None else 'N/A'.center(20),
            f"{record.weight:.2f}".center(20) if record.weight is not None else 'N/A'.center(20),
            f"{record.motor_load_mean:.2f}".center(20) if record.motor_load_mean is not None else 'N/A'.center(20),
            f"{record.actual_torque_percentage:.1f}".center(20) if record.actual_torque_percentage is not None else 'N/A'.center(20),
            f"{record.actual_torque_percentage2:.1f}".center(20) if record.actual_torque_percentage2 is not None else 'N/A'.center(20)
        ]
        writer.writerow(row)
    
    return response