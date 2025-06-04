from django.utils.timezone import timedelta
from decimal import Decimal
from django.db.models import Sum
from .models import SubProcess, Process
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

def calculate_subprocess_totals(process_id, process_name):
    """Calculate total values for subprocesses based on process type."""
    try:
        # Get subprocess based on process name
        subprocess = SubProcess.objects.filter(
            process_id=process_id,
            name=process_name
        ).first()
        
        if not subprocess:
            logger.error(f"No subprocess found for process_id={process_id}, name={process_name}")
            return None
            
        # For single subprocess processes like Cut Ply, return its own values
        totals = {
            "total_interface_time": format_timedelta(subprocess.interfaceTime),
            "total_process_time": format_timedelta(subprocess.processTime),
            "total_material_wastage": f"£{subprocess.materialWastage:.3f}" if subprocess.materialWastage else "£0.000",
            "total_labour_cost": f"£{subprocess.labourSumCost:.3f}" if subprocess.labourSumCost else "£0.000",
            "total_power_cost": f"£{subprocess.powerCost:.3f}" if subprocess.powerCost else "£0.000",
            "total_cost": f"£{subprocess.totalCost:.3f}" if subprocess.totalCost else "£0.000"
        }
        
        return totals
        
    except Exception as e:
        logger.error(f"Error calculating subprocess totals: {str(e)}")
        return None

def get_subprocess_data(instance):
    """Get all required data for a subprocess instance."""
    try:
        data = {}
        
        # Only include time values if they exist and are non-zero
        if instance.processTime and instance.processTime.total_seconds() > 0:
            data['processTime'] = format_timedelta(instance.processTime)
        if instance.interfaceTime and instance.interfaceTime.total_seconds() > 0:
            data['interfaceTime'] = format_timedelta(instance.interfaceTime)
            
        # Only include cost values if they exist and are non-zero
        if instance.materialWastage:
            data['materialWastage'] = f"£{instance.materialWastage:.3f}"
        if instance.labourSumCost:
            data['labourSumCost'] = f"£{instance.labourSumCost:.3f}"
        if instance.powerCost:
            data['powerCost'] = f"£{instance.powerCost:.3f}"
        if instance.totalCost:
            data['totalCost'] = f"£{instance.totalCost:.3f}"
            
        return data
    except Exception as e:
        logger.error(f"Error getting subprocess data: {str(e)}")
        return None

def update_subprocess_message(instance):
    """Create message dictionary with all required fields including totals."""
    try:
        message = {
            "Name": instance.name,
            "fields": {}
        }
        
        # Get subprocess-specific data
        subprocess_data = get_subprocess_data(instance)
        if subprocess_data:
            message['fields'].update(subprocess_data)
        
        # Add status and basic fields
        if instance.status is not None:
            message['fields']['Status'] = instance.status
            
        # Format dates
        dt_format = '%b. %d, %Y, %I:%M%p'
        if instance.jobStart:
            message['fields']['Job Start'] = instance.jobStart.strftime(dt_format)
        if instance.jobEnd:
            message['fields']['Job End'] = instance.jobEnd.strftime(dt_format)
        if hasattr(instance, 'plyInstance'):
            message['fields']['Ply Instance'] = instance.plyInstance
        if hasattr(instance, 'labourInput'):
            message['fields']['Labour Input'] = f"{instance.labourInput}%"

        # Add other fields
        if instance.power:
            message['fields']['Power Consumption'] = f"{instance.power:.6f} kWh"
        if instance.CO2:
            message['fields']['CO2 emissions from power'] = f"{instance.CO2:.5f} Kg"
        if instance.operator:
            message['fields']['Operator'] = instance.operator

        if hasattr(instance, 'materialWastageCost'):
            message['fields']['Cost of Material Waste'] = f"£{instance.materialWastageCost:.3f}" if instance.materialWastageCost is not None else "£0.000"
        if hasattr(instance, 'materialScrapCost'):
            message['fields']['Cost of Scrap'] = f"£{instance.materialScrapCost:.3f}"
        if hasattr(instance, 'materialPartCost'):
            message['fields']['Cost of Part'] = f"£{instance.materialPartCost:.3f}"
        if hasattr(instance, 'technicianLabourCost'):
            message['fields']['Technician Labour Cost'] = f"£{instance.technicianLabourCost:.3f}"
        if hasattr(instance, 'totalCost'):
            message['fields']['Total Cost'] = f"£{instance.totalCost:.3f}"
        
        if hasattr(instance, 'processTime'):
            message['fields']['Process Time'] = format_timedelta(instance.processTime)
        if hasattr(instance, 'interfaceTime'):
            message['fields']['Interface Time'] = format_timedelta(instance.interfaceTime)

        # Update lastCard based on process type
        monitored_processes = ['Pickup Initial Ply', 'Pickup Ply & Weld', 'Ply Placed', 'Ply Waiting']
        if instance.name in monitored_processes:
            # For first subprocess in sequence (Pickup Initial Ply) - set initial values in lastCard
            if instance.name == 'Pickup Initial Ply':
                message['fields'].update({
                    'total_interface_time': format_timedelta(instance.interfaceTime) if instance.interfaceTime else "0:00:00",
                    # 'total_process_time': "0:00:00",  
                    'total_material_wastage': f"£{instance.materialWastage:.3f}" if instance.materialWastage else "£0.000",
                    'total_labour_cost': f"£{instance.labourSumCost:.3f}" if instance.labourSumCost else "£0.000",
                    'total_power_cost': f"£{instance.powerCost:.3f}" if instance.powerCost else "£0.000",
                    'total_cost': f"£{instance.totalCost:.3f}" if instance.totalCost else "£0.000",
                    'isLastCard': True
                })
                logger.info(f"Updated lastCard with initial values from Pickup Initial Ply")

            # For second subprocess (Pickup Ply & Weld) - add to Pickup Initial Ply values
            elif instance.name == 'Pickup Ply & Weld':
                pickup_initial = SubProcess.objects.filter(
                    process_id=instance.process_id,
                    name='Pickup Initial Ply'
                ).first()
                
                if pickup_initial:
                    message['fields'].update({
                        # 'total_interface_time': format_timedelta(pickup_initial.interfaceTime) if pickup_initial.interfaceTime else "0:00:00",
                        'total_process_time': format_timedelta(instance.processTime) if instance.processTime else "0:00:00",
                        'total_material_wastage': f"£{(pickup_initial.materialWastage + instance.materialWastage):.3f}",
                        'total_labour_cost': f"£{(pickup_initial.labourSumCost + instance.labourSumCost):.3f}",
                        'total_power_cost': f"£{(pickup_initial.powerCost + instance.powerCost):.3f}",
                        'total_cost': f"£{(pickup_initial.totalCost + instance.totalCost):.3f}",
                        'isLastCard': True
                    })
                    logger.info(f"Updated lastCard by adding Pickup Ply & Weld values to existing values")

            # For first subprocess in second sequence (Ply Placed) - set initial values
            elif instance.name == 'Ply Placed':
                message['fields'].update({
                    'total_interface_time': format_timedelta(instance.interfaceTime) if instance.interfaceTime else "0:00:00",  # Changed
                    # 'total_process_time': format_timedelta(instance.processTime) if instance.processTime else "0:00:00",
                    'total_material_wastage': f"£{instance.materialWastage:.3f}" if instance.materialWastage else "£0.000",
                    'total_labour_cost': f"£{instance.labourSumCost:.3f}" if instance.labourSumCost else "£0.000",
                    'total_power_cost': f"£{instance.powerCost:.3f}" if instance.powerCost else "£0.000",
                    'total_cost': f"£{instance.totalCost:.3f}" if instance.totalCost else "£0.000",
                    'isLastCard': True
                })
                logger.info(f"Updated lastCard with initial values from Ply Placed")

            # For second subprocess (Ply Waiting) - add to Ply Placed values
            elif instance.name == 'Ply Waiting':
                ply_placed = SubProcess.objects.filter(
                    process_id=instance.process_id,
                    name='Ply Placed'
                ).first()

                if ply_placed:
                    message['fields'].update({
                        # Add interface times from both subprocesses
                        'total_interface_time': format_timedelta(ply_placed.interfaceTime + instance.interfaceTime) if (ply_placed.interfaceTime and instance.interfaceTime) else "0:00:00",
                        # 'total_process_time': format_timedelta(ply_placed.processTime + instance.processTime) if (ply_placed.processTime and instance.processTime) else "0:00:00",
                        'total_material_wastage': f"£{(ply_placed.materialWastage + instance.materialWastage):.3f}",
                        'total_labour_cost': f"£{(ply_placed.labourSumCost + instance.labourSumCost):.3f}",
                        'total_power_cost': f"£{(ply_placed.powerCost + instance.powerCost):.3f}",
                        'total_cost': f"£{(ply_placed.totalCost + instance.totalCost):.3f}",
                        'isLastCard': True
                    })
                    logger.info(f"Updated lastCard by adding Ply Waiting values to Ply Placed values")

        elif instance.name == 'Load and Cut Ply':
            # Cut Ply handling remains the same
            message['fields'].update({
                'Process Time': format_timedelta(instance.processTime) if instance.processTime else "0:00:00",  # Consistent field name
                'processTime': format_timedelta(instance.processTime) if instance.processTime else "0:00:00",   # For VSM update
                # 'total_interface_time': format_timedelta(instance.interfaceTime) if instance.interfaceTime else "0:00:00",
                'total_process_time': format_timedelta(instance.processTime) if instance.processTime else "0:00:00",
                'total_material_wastage': f"£{instance.materialWastage:.3f}" if instance.materialWastage else "£0.000",
                'total_labour_cost': f"£{instance.labourSumCost:.3f}" if instance.labourSumCost else "£0.000",
                'total_power_cost': f"£{instance.powerCost:.3f}" if instance.powerCost else "£0.000",
                'total_cost': f"£{instance.totalCost:.3f}" if instance.totalCost else "£0.000",
                'isLastCard': True
            })
        return message
    except Exception as e:
        logger.error(f"Error updating subprocess message: {str(e)}")
        return None
