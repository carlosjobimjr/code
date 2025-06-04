from celery import shared_task
from Main.models import SubProcess
from celery.utils.log import get_task_logger
from .models import CommonTask, IntegrationManager, CommonPly, PlyIntegrationManager
from django.utils.timezone import now
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import datetime, date, timedelta
import time  # Move this here
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .polygon import calculate_polygon_metrics, polygon_wkts
from Main.signals import subprocess_handler
from decimal import Decimal, ROUND_HALF_UP
import requests
import logging
from Main.utils import format_timedelta
from MainData.models import ProcessPart

logger = logging.getLogger(__name__)


def format_timedelta(td):
    if not td:
        return timedelta()
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    
def format_datetime(dt):
    if not dt:
        return None
    return dt.replace(microsecond=0)

def calculate_process_duration(current_date_cut, previous_date_cut, job_start):
  
    if previous_date_cut is None:
        # First ply: calculate from job_start to first cut
        return current_date_cut - job_start
    else:
        # Subsequent plies: calculate between cuts
        return current_date_cut - previous_date_cut

from celery import shared_task
from decimal import Decimal
import logging
import requests
from django.utils.timezone import now
from datetime import timedelta

logger = logging.getLogger(__name__)

def get_power_consumption():
    DEVICE_ID = "3494546ed0bd"
    AUTH_KEY = "MTE5ODgwdWlk6BA0E5CB7819B5C5451CAC0087A8053AC7CB686CBA6ECC3550121F24EA6B1ADB67D80B45BE65AC23"
    BASE_URL = "https://shelly-43-eu.shelly.cloud/device/status"
    
    try:
        params = {'id': DEVICE_ID, 'auth_key': AUTH_KEY}
        response = requests.get(BASE_URL, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return Decimal(str(data['data']['device_status'].get('total_power', 0)))
        return Decimal('0')
    except Exception as e:
        logger.error(f"Error getting power: {str(e)}")
        return Decimal('0')

def calculate_power_consumption(power_w, duration):
    if not power_w or not duration:
        return Decimal('0')
    
    try:
        # Convert watts to kilowatts
        power_kw = power_w / Decimal('1000')
        # Convert duration to hours and multiply
        duration_hours = Decimal(str(duration.total_seconds())) / Decimal('3600')
        return power_kw * duration_hours
    except Exception as e:
        logger.error(f"Error calculating power consumption: {str(e)}")
        return Decimal('0')

def update_subprocess_costs(subprocess, power_ratio=Decimal('0.25'), increment=True):
    try:
        # Get initial power reading
        power_w = get_power_consumption()
        duration = None
        
        # Get the appropriate duration based on subprocess type
        if subprocess.name == 'Load and Cut Ply' and subprocess.processTime:
            duration = subprocess.processTime
            # Load and Cut Ply always increments
            increment = True
        elif subprocess.name == 'Pickup Initial Ply' and subprocess.interfaceTime:
            duration = subprocess.interfaceTime
        elif subprocess.name == 'Pickup Ply & Weld' and subprocess.processTime:
            duration = subprocess.processTime
        elif subprocess.name == 'Ply Placed' and subprocess.interfaceTime:
            duration = subprocess.interfaceTime
        elif subprocess.name == 'Ply Waiting' and subprocess.interfaceTime:
            duration = subprocess.interfaceTime
            
        if not duration:
            logger.warning(f"No valid duration found for {subprocess.name}")
            return
            
        # Calculate total power consumption
        total_kwh = calculate_power_consumption(power_w, duration)
        
        # Calculate costs
        power_cost = total_kwh * Decimal('0.308') * power_ratio
        co2_emissions = total_kwh * Decimal('0.24169')
        technician_rate = Decimal('58')
        labour_total = Decimal('0.5')
        technician_labour_cost = technician_rate * labour_total * power_ratio
        
        # Update subprocess values
        if increment:
            subprocess.power = (subprocess.power or Decimal('0')) + total_kwh
            subprocess.powerCost = (subprocess.powerCost or Decimal('0')) + power_cost
            subprocess.CO2 = (subprocess.CO2 or Decimal('0')) + co2_emissions
            subprocess.technicianLabourCost = (subprocess.technicianLabourCost or Decimal('0')) + technician_labour_cost
            subprocess.labourSumCost = (subprocess.labourSumCost or Decimal('0')) + technician_labour_cost
        else:
            subprocess.power = total_kwh
            subprocess.powerCost = power_cost
            subprocess.CO2 = co2_emissions
            subprocess.technicianLabourCost = technician_labour_cost
            subprocess.labourSumCost = technician_labour_cost
        
        # Special handling for Load and Cut Ply material costs and total cost calculation
        if subprocess.name == 'Load and Cut Ply':
            # Calculate material costs
            metrics = calculate_polygon_metrics(polygon_wkts)
            total_surface_area = Decimal(str(sum(metrics['ply_surface_areas'].values())))
            total_wastage = Decimal(str(metrics['total_wastage']))
            
            # Calculate material part cost (constant)
            if not subprocess.materialPartCost:
                subprocess.materialPartCost = total_surface_area * Decimal('10') / 1000000
            
            # Calculate material wastage cost (accumulates)
            material_wastage_cost = ((total_wastage / 4) * Decimal('10') * Decimal('0.25')) / 100000
            if increment:
                subprocess.materialWastageCost = (subprocess.materialWastageCost or Decimal('0')) + material_wastage_cost
            else:
                subprocess.materialWastageCost = material_wastage_cost
            
            # Calculate material scrap cost
            scrap_cost = (total_surface_area / 4) * Decimal('10') * Decimal('0') / 100000
            if increment:
                subprocess.materialScrapCost = (subprocess.materialScrapCost or Decimal('0')) + scrap_cost
            else:
                subprocess.materialScrapCost = scrap_cost
            
            # Calculate total material wastage
            subprocess.materialWastage = (
                subprocess.materialWastageCost + 
                subprocess.materialScrapCost + 
                subprocess.materialPartCost
            ).quantize(Decimal('0.001'))
            
            # Calculate total cost
            subprocess.totalCost = (
                subprocess.materialWastage +  # This includes all material costs
                subprocess.technicianLabourCost +  # Labour cost
                subprocess.powerCost  # Power cost
            ).quantize(Decimal('0.001'))
            
        else:
            if increment:
                subprocess.totalCost = (subprocess.totalCost or Decimal('0')) + technician_labour_cost + power_cost
            else:
                subprocess.totalCost = technician_labour_cost + power_cost
        
        # Ensure all decimal values are properly rounded
        subprocess.power = subprocess.power.quantize(Decimal('0.000001'))
        subprocess.powerCost = subprocess.powerCost.quantize(Decimal('0.000001'))
        subprocess.CO2 = subprocess.CO2.quantize(Decimal('0.000001'))
        subprocess.technicianLabourCost = subprocess.technicianLabourCost.quantize(Decimal('0.000001'))
        subprocess.labourSumCost = subprocess.labourSumCost.quantize(Decimal('0.000001'))
        if not subprocess.name == 'Load and Cut Ply':
            subprocess.totalCost = subprocess.totalCost.quantize(Decimal('0.000001'))
        
        subprocess.save()
        logger.info(f"{subprocess.name} - Power: {power_w}W, Total: {total_kwh:.6f}kWh, Duration: {duration}")
        if subprocess.name == 'Load and Cut Ply':
            logger.info(f"Material Wastage: £{subprocess.materialWastage}")
            logger.info(f"Labour Cost: £{subprocess.technicianLabourCost}")
            logger.info(f"Power Cost: £{subprocess.powerCost}")
            logger.info(f"Total Cost: £{subprocess.totalCost}")
            
    except Exception as e:
        logger.error(f"Error updating costs for {subprocess.name}: {str(e)}")
        raise


@shared_task
def poll_postgre_data():
    logger.info('Starting CommonTask and CommonPly pull')

    # Get or create IntegrationManager for CommonTask
    task_integration_manager, created = IntegrationManager.objects.get_or_create(
        integration_name="CommonTask pull",
        defaults={
            'integration_watermark': 0,
            'integration_last_run_at': None
        }
    )

    if not created:
        task_integration_manager.integration_last_run_at = None
        task_integration_manager.save()

    # Get or create IntegrationManager for CommonPly
    ply_integration_manager, created = PlyIntegrationManager.objects.get_or_create(
        integration_name="CommonPly pull",
        defaults={
            'integration_watermark': 0,
            'integration_last_run_at': None
        }
    )

    if not created:
        ply_integration_manager.integration_last_run_at = None
        ply_integration_manager.save()

    # Set up thresholds and limits
    task_threshold = task_integration_manager.integration_watermark + 1
    task_limit = task_integration_manager.integration_watermark + 2000
    ply_threshold = ply_integration_manager.integration_watermark + 1
    ply_limit = ply_integration_manager.integration_watermark + 2000

    logger.info('CommonTask pull watermark = %d, threshold = %d', 
                task_integration_manager.integration_watermark, task_threshold)
    logger.info('CommonPly pull watermark = %d threshold = %d', 
                ply_integration_manager.integration_watermark, ply_threshold)

    common_tasks = (CommonTask.objects.using('LION')
                   .filter(id__gte=task_threshold, id__lt=task_limit)
                   .order_by('id'))

    common_plys = (CommonPly.objects.using('LION')
                  .filter(id__gte=ply_threshold, id__lt=ply_limit)
                  .exclude(date_cut=None)  
                  .order_by('id'))

    # Get subprocess instances
    cut_ply_subprocess = SubProcess.objects.filter(name='Load and Cut Ply').first()
    pickup_ply_and_weld_subprocess = SubProcess.objects.filter(name='Pickup Ply & Weld').first()
    pickup_initial_ply_subprocess = SubProcess.objects.filter(name='Pickup Initial Ply').first()
    ply_placed_subprocess = SubProcess.objects.filter(name='Ply Placed').first()
    ply_waiting_subprocess = SubProcess.objects.filter(name='Ply Waiting').first()
    blank_placed_subprocess = SubProcess.objects.filter(name='Blank Placed').first()
    blank_waiting_subprocess = SubProcess.objects.filter(name='Blank Waiting').first()

    if not cut_ply_subprocess:
        logger.error('Subprocess Cut Ply not found in database.')
        return

    first_common_ply = CommonPly.objects.using('LION').all().first()
    last_common_ply = CommonPly.objects.using('LION').all().last()

    logger.info(f'CommonPlys {common_plys.count()} objects fetched')
    if first_common_ply:
        logger.info(f'CommonPlys first id in external db = {first_common_ply.id}')
    if last_common_ply:
        logger.info(f'CommonPlys last id in external db = {last_common_ply.id}')

    new_task_watermark = None
    new_ply_watermark = None

    for common_task in common_tasks:
        if common_task.command == 10 and common_task.date_done:
            new_task_watermark = common_task.id 
            
            if cut_ply_subprocess.jobStart is None: 
                logger.info(f'Initializing Cut Ply subprocess with date_done: {common_task.date_done}')
                cut_ply_subprocess.jobStart = common_task.date_done
                cut_ply_subprocess.status = 1
                cut_ply_subprocess.operator = 'Technician'
                cut_ply_subprocess.plyInstance = 0
                cut_ply_subprocess.processTime = timedelta()
                cut_ply_subprocess.labourInput = 50
                cut_ply_subprocess.date = datetime.now()
                cut_ply_subprocess.save()
                
    if not cut_ply_subprocess.jobStart:
        logger.info('No Command 10 date_done found. Skipping Cut Ply processing.')
        return

    metrics = calculate_polygon_metrics(polygon_wkts)
    total_surface_area = Decimal(str(sum(metrics['ply_surface_areas'].values())))
    cut_ply_subprocess.materialPartCost = total_surface_area * Decimal('10') / 1000000

    for common_ply in common_plys:
        if common_ply.date_cut:
            logger.info(f'Processing ply with date_cut: {common_ply.date_cut}')
            cut_ply_subprocess.jobEnd = common_ply.date_cut
            
            process_duration = common_ply.date_cut - cut_ply_subprocess.jobStart
            cut_ply_subprocess.processTime = format_timedelta(process_duration)
            
            # Calculate all costs (power, material, and total)
            update_subprocess_costs(subprocess=cut_ply_subprocess)
            
            if cut_ply_subprocess.plyInstance is not None:
                cut_ply_subprocess.plyInstance += 1
                if cut_ply_subprocess.plyInstance == 4:
                    cut_ply_subprocess.status = 2
                    logger.info("Cut Ply process complete - power monitoring will stop")

            cut_ply_subprocess.save()
            new_ply_watermark = common_ply.id
            
            logger.info(f'Final values:')
            logger.info(f'Power: {cut_ply_subprocess.power} kWh')
            logger.info(f'Power Cost: £{cut_ply_subprocess.powerCost}')
            logger.info(f'Total Cost: £{cut_ply_subprocess.totalCost}')
            logger.info(f'Ply Instance: {cut_ply_subprocess.plyInstance}')
            logger.info(f'Status: {cut_ply_subprocess.status}')

    for common_task in common_tasks:
        if common_task.command == 2:
            if pickup_initial_ply_subprocess.jobEnd is None:
                if common_task.date_started:
                    logger.info(f'Updating Pickup Initial Ply subprocess jobStart. New Job Start = {common_task.date_started}')
                    pickup_initial_ply_subprocess.jobStart = common_task.date_started
                    pickup_initial_ply_subprocess.status = 1
                    pickup_initial_ply_subprocess.labourInput = 50
                    pickup_initial_ply_subprocess.date = datetime.now()
                    if pickup_initial_ply_subprocess.plyInstance is None:
                        pickup_initial_ply_subprocess.plyInstance = 1
                    if pickup_initial_ply_subprocess.interfaceTime is None:
                        pickup_initial_ply_subprocess.interfaceTime = timedelta()
                    pickup_initial_ply_subprocess.save()
                    logger.info(f'Saved Pickup Initial Ply subprocess jobStart. ID = {pickup_initial_ply_subprocess.id}')

                if common_task.date_done:
                    logger.info(f'Updating Pickup Initial Ply subprocess jobEnd. New Job End = {common_task.date_done}')
                    pickup_initial_ply_subprocess.jobEnd = common_task.date_done
                    pickup_initial_ply_subprocess.status = 2
                    if pickup_initial_ply_subprocess.interfaceTime is not None and pickup_initial_ply_subprocess.jobStart:
                        interface_duration = common_task.date_done - pickup_initial_ply_subprocess.jobStart
                        pickup_initial_ply_subprocess.interfaceTime = format_timedelta(interface_duration)
                        # Calculate power and costs after duration is known
                        update_subprocess_costs(
                            subprocess=pickup_initial_ply_subprocess,
                        )
                    pickup_initial_ply_subprocess.save()
                    logger.info(f'Saved Pickup Initial Ply subprocess jobEnd. ID = {pickup_initial_ply_subprocess.id}')
                    new_task_watermark = common_task.id
                    logger.info('Complete update for first command 2. Moving to next ID.')
                else:
                    logger.info('Incomplete update for first command 2. Waiting for complete data.')
                
                continue

            else:
                if common_task.date_started:
                    logger.info(f'Updating Pickup Ply & Weld subprocess jobStart. New Job Start = {common_task.date_started}')
                    pickup_ply_and_weld_subprocess.jobStart = common_task.date_started
                    pickup_ply_and_weld_subprocess.status = 1
                    pickup_ply_and_weld_subprocess.labourInput = 50
                    pickup_ply_and_weld_subprocess.date = datetime.now()
                    if pickup_ply_and_weld_subprocess.plyInstance is None:
                        pickup_ply_and_weld_subprocess.plyInstance = 1
                    if pickup_ply_and_weld_subprocess.processTime is None:
                        pickup_ply_and_weld_subprocess.processTime = timedelta()
                    pickup_ply_and_weld_subprocess.save()
                    logger.info(f'Saved Pickup Ply & Weld subprocess jobStart. ID = {pickup_ply_and_weld_subprocess.id}')

                if common_task.date_done and pickup_ply_and_weld_subprocess.jobStart:
                    logger.info(f'Updating Pickup Ply & Weld subprocess jobEnd. New Job End = {common_task.date_done}')
                    pickup_ply_and_weld_subprocess.jobEnd = common_task.date_done
                    pickup_ply_and_weld_subprocess.status = 2
                    if pickup_ply_and_weld_subprocess.processTime is not None:
                        # Calculate process time
                        process_duration = common_task.date_done - pickup_ply_and_weld_subprocess.jobStart
                        pickup_ply_and_weld_subprocess.processTime += format_timedelta(process_duration)
                    if pickup_ply_and_weld_subprocess.plyInstance is not None:
                        pickup_ply_and_weld_subprocess.plyInstance += 1
                        # Calculate power and costs after duration is known
                        update_subprocess_costs(
                            subprocess=pickup_ply_and_weld_subprocess,
                            increment=True 
                        )
                    pickup_ply_and_weld_subprocess.save()
                    logger.info(f'Saved Pickup Ply & Weld subprocess jobEnd. ID = {pickup_ply_and_weld_subprocess.id}')
                    new_task_watermark = common_task.id
                    logger.info('Complete update for subsequent command 2. Moving to next ID.')
                else:
                    logger.info('Incomplete update for subsequent command 2. Waiting for complete data.')




    for common_task in common_tasks:
        if common_task.command == 1:
            if common_task.date_started:
                logger.info(f'Updating Ply Placed subprocess jobStart. New Job Start = {common_task.date_started}')
                if not ply_placed_subprocess.jobStart or common_task.date_started > ply_placed_subprocess.jobStart:
                    ply_placed_subprocess.jobStart = common_task.date_started
                    if ply_placed_subprocess.status == 0:
                        ply_placed_subprocess.status = 1
                        ply_placed_subprocess.date = datetime.now()
                    if ply_placed_subprocess.plyInstance is None:
                        ply_placed_subprocess.plyInstance = 1
                    if ply_placed_subprocess.interfaceTime is None:
                        ply_placed_subprocess.interfaceTime = timedelta()
                    ply_placed_subprocess.save()
                    logger.info(f'Saved Ply Placed subprocess jobStart. ID = {ply_placed_subprocess.id}')
            if common_task.date_done:
                logger.info(f'Updating Ply Placed subprocess jobEnd. New Job End = {common_task.date_done}')
                if not ply_placed_subprocess.jobEnd or common_task.date_done > ply_placed_subprocess.jobEnd:
                    ply_placed_subprocess.jobEnd = common_task.date_done
                    ply_placed_subprocess.labourInput = 50
                    if ply_placed_subprocess.status == 1:
                        ply_placed_subprocess.status = 2
                    if ply_placed_subprocess.interfaceTime is not None and ply_placed_subprocess.jobStart:
                        interface_duration = common_task.date_done - ply_placed_subprocess.jobStart
                        ply_placed_subprocess.interfaceTime += format_timedelta(interface_duration)
                    update_subprocess_costs(
                            subprocess=ply_placed_subprocess,
                        )
                    ply_placed_subprocess.save()
                    logger.info(f'Saved Ply Placed subprocess jobEnd. ID = {ply_placed_subprocess.id}')
                logger.info(f'Updating Ply Waiting subprocess jobStart. New Job Start = {common_task.date_done}')
                if not ply_waiting_subprocess.jobStart or common_task.date_done > ply_waiting_subprocess.jobStart:
                    ply_waiting_subprocess.jobStart = common_task.date_done
                    if ply_waiting_subprocess.status == 0:
                        ply_waiting_subprocess.status = 1
                        ply_waiting_subprocess.date = datetime.now()
                    if ply_waiting_subprocess.plyInstance is None:
                        ply_waiting_subprocess.plyInstance = ply_placed_subprocess.plyInstance
                    if ply_waiting_subprocess.interfaceTime is None:
                        ply_waiting_subprocess.interfaceTime = timedelta()
                    ply_waiting_subprocess.save()
                    logger.info(f'Saved Ply Waiting subprocess jobStart. ID = {ply_waiting_subprocess.id}')
                new_task_watermark = common_task.id
                logger.info('Complete update for command 1. Moving to next ID.')
            else:
                logger.info('Incomplete update for command 1. Waiting for complete data.')

    for common_task in common_tasks:
        if common_task.command == 3:
            if common_task.date_started:
                formatted_date_started = format_datetime(common_task.date_started)
                logger.info(f'Found command 3 with date_started = {formatted_date_started}')
                logger.info(f'Current Ply Waiting status = {ply_waiting_subprocess.status}')
                logger.info(f'Current Ply Waiting jobEnd = {ply_waiting_subprocess.jobEnd}')

                if (ply_waiting_subprocess.status == 1 and 
                    ply_waiting_subprocess.jobStart is not None and
                    (ply_waiting_subprocess.jobEnd is None or 
                     formatted_date_started > ply_waiting_subprocess.jobEnd)):
                    
                    logger.info(f'Updating Ply Waiting subprocess jobEnd. New Job End = {formatted_date_started}')
                    ply_waiting_subprocess.jobEnd = formatted_date_started
                    ply_waiting_subprocess.status = 2  # Set to completed
                    
                    try:
                        interface_duration = formatted_date_started - ply_waiting_subprocess.jobStart
                        formatted_duration = format_timedelta(interface_duration)
                        if ply_waiting_subprocess.interfaceTime is None:
                            ply_waiting_subprocess.interfaceTime = formatted_duration
                        else:
                            existing_time = format_timedelta(ply_waiting_subprocess.interfaceTime)
                            ply_waiting_subprocess.interfaceTime = existing_time + formatted_duration
                    except TypeError as e:
                        logger.error(f"Error calculating interface duration: {str(e)}")
                        ply_waiting_subprocess.interfaceTime = timedelta()
                    
                    if ply_waiting_subprocess.plyInstance is not None:
                        ply_waiting_subprocess.plyInstance += 1
                    
                    update_subprocess_costs(
                        subprocess=ply_waiting_subprocess,
                    )
                    ply_waiting_subprocess.save()
                    logger.info(f'Successfully updated Ply Waiting subprocess. Status = {ply_waiting_subprocess.status}')

                logger.info(f'Current Pickup Ply & Weld status = {pickup_ply_and_weld_subprocess.status}')
                logger.info(f'Updating Pickup Ply & Weld subprocess jobStart. New Job Start = {formatted_date_started}')
                
                pickup_ply_and_weld_subprocess.jobStart = formatted_date_started
                pickup_ply_and_weld_subprocess.status = 1  # Set to In Progress
                if pickup_ply_and_weld_subprocess.plyInstance is None:
                    pickup_ply_and_weld_subprocess.plyInstance = (ply_waiting_subprocess.plyInstance 
                                                                if ply_waiting_subprocess.plyInstance is not None 
                                                                else 1)
                if pickup_ply_and_weld_subprocess.processTime is None:
                    pickup_ply_and_weld_subprocess.processTime = timedelta()
                pickup_ply_and_weld_subprocess.save()
                logger.info(f'Saved Pickup Ply & Weld subprocess jobStart. ID = {pickup_ply_and_weld_subprocess.id}')
                    
            if common_task.date_done:
                # Format date_done without milliseconds
                formatted_date_done = format_datetime(common_task.date_done)
                logger.info(f'Found command 3 with date_done = {formatted_date_done}')
                
                if (pickup_ply_and_weld_subprocess.status == 1 and 
                    pickup_ply_and_weld_subprocess.jobStart is not None):
                    
                    logger.info(f'Updating Pickup Ply & Weld subprocess jobEnd. New Job End = {formatted_date_done}')
                    pickup_ply_and_weld_subprocess.jobEnd = formatted_date_done
                    pickup_ply_and_weld_subprocess.status = 2
                    
                    if pickup_ply_and_weld_subprocess.processTime is not None:
                        process_duration = formatted_date_done - pickup_ply_and_weld_subprocess.jobStart
                        formatted_process_time = format_timedelta(process_duration)
                        existing_time = format_timedelta(pickup_ply_and_weld_subprocess.processTime)
                        pickup_ply_and_weld_subprocess.processTime = existing_time + formatted_process_time
                    
                    if pickup_ply_and_weld_subprocess.plyInstance is not None:
                        pickup_ply_and_weld_subprocess.plyInstance += 1
                    
                    update_subprocess_costs(
                        subprocess=pickup_ply_and_weld_subprocess,
                        increment=True
                    )
                    pickup_ply_and_weld_subprocess.save()
                    logger.info(f'Successfully completed Pickup Ply & Weld subprocess. Status = {pickup_ply_and_weld_subprocess.status}')

                    logger.info(f'Updating Blank Placed subprocess with jobStart = {formatted_date_done}')
                    blank_placed_subprocess.jobStart = formatted_date_done
                    blank_placed_subprocess.status = 1
                    blank_placed_subprocess.blankInstance = 1
                    blank_placed_subprocess.date = datetime.now()
                    blank_placed_subprocess.interfaceTime = timedelta()
                    blank_placed_subprocess.save()
                    logger.info(f'Successfully updated Blank Placed subprocess. Status = {blank_placed_subprocess.status}')
            
                new_task_watermark = common_task.id
                logger.info('Complete update for command 3. Moving to next ID.')
        else:
            logger.info('Not command 3, checking next task')



    if new_task_watermark:
        task_integration_manager.integration_watermark = new_task_watermark
        task_integration_manager.integration_last_run_at = now()
        task_integration_manager.save()
        logger.info('Updated CommonTask watermark to %d', new_task_watermark)
    else:
        logger.info('No CommonTask watermark update: waiting for complete data')

    if new_ply_watermark:
        ply_integration_manager.integration_watermark = new_ply_watermark
        ply_integration_manager.integration_last_run_at = now()
        ply_integration_manager.save()
        logger.info('Updated CommonPly watermark to %d', new_ply_watermark)
    else:
        logger.info('No CommonPly watermark update: waiting for complete data')

    logger.info('Finished CommonTask and CommonPly pull')