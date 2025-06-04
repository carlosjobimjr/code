from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.db.models.fields import NOT_PROVIDED
from Main.models import Project, Sensor
from MainData.models import *
from datetime import timedelta, datetime
from django.contrib.auth.models import User, Group
from django.utils import timezone

from django.contrib import messages

from .forms import *

import io

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import F 
from monorepo.models import CommonPly, CommonTask
from MainData.models import Ply
from Main.models import PlyInstance, Process, SubProcess, Project
from monorepo.polygon import calculate_polygon_metrics, polygon_wkts
from Main.views import calculate_total_values
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from decimal import Decimal, ROUND_HALF_UP

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

from django.http import HttpResponse
def format_timedelta(td):
    """Convert timedelta to formatted string"""
    if not td:
        return "0:00:00"
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"

def generate_ply_pdf(ply, processPart):
    """Generate PDF with ply details and all associated process information"""
    buffer = io.BytesIO()  # Fixed typo from BytsIO to BytesIO
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=15
    )
    elements.append(Paragraph(f"Ply Details Report - {ply.name}", title_style))
    
    # Basic Ply Information
    ply_data = [
        ['Ply Information', ''],
        ['Ply ID', str(ply.ply_id)],
        ['Name', ply.name],
        ['Date', ply.date.strftime('%Y-%m-%d')],
        ['Price per KG', f"£{ply.priceKG}/Kg"],
        ['Price per M²', f"£{ply.priceM2}/m²"],
        ['Material Density', f"{ply.materialDensity}Kg/m²"],
        ['Power Rate', f"£{ply.project.powerRate}/Kwh"],
        ['CO2 Emissions', f"{ply.CO2EmissionsPerPly}Kg"],
    ]
    
    if hasattr(ply, 'materialCostPerPly'):
        management_data = [
            ['Material Cost', f"£{ply.materialCostPerPly}"],
            ['Material Wastage Cost', f"£{ply.materialWastageCostPerPly}"],
            ['Technician Labour Cost', f"£{ply.technicianLabourCostPerPly}"],
            ['Supervisor Labour Cost', f"£{ply.supervisorLabourCostPerPly}"],
            ['Total Cost', f"£{ply.totalCost}"],
            ['Area Ratio', f"{ply.plyAreaRatio:.3f}"],
            ['Perimeter Ratio', f"{ply.plyPerimeterRatio:.3f}"],
            ['Scrap Rate', f"{ply.plyScrapRate}%"]
        ]
        ply_data.extend(management_data)
    
    ply_table = Table(ply_data, colWidths=[2.5*inch, 3.5*inch])
    ply_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(ply_table)
    elements.append(Spacer(1, 10))  
    
    process_order = [
        'Cut Plies',
        'Buffer (Ply Storage)',
        'Create Blanks',
        'Buffer (Blank Storage)'
    ]
    
    # Get all processes for this ply
    all_processes = ProcessPart.objects.filter(ply=ply)
    
    # Add section for each process in correct order
    for i, process_name in enumerate(process_order):
        process = all_processes.filter(processName=process_name).first()
        if process:
            elements.append(Paragraph(f"Process: {process.processName}", styles['Heading3']))
            
            process_data = [
                ['Process Information', ''],
                ['Date', process.date.strftime('%Y-%m-%d')],
                ['Labour Input', f"{process.labourInput}%"],
                ['Job Start', process.jobStart.strftime('%H:%M:%S') if process.jobStart else 'N/A'],
                ['Job End', process.jobEnd.strftime('%H:%M:%S') if process.jobEnd else 'N/A'],
                ['Process Time', format_timedelta(process.processTime)],
                ['Interface Time', format_timedelta(process.interfaceTime)],
                ['Cycle Time', format_timedelta(process.cycleTime)],
                ['Technician Labour', format_timedelta(process.technicianLabour)],
                ['Supervisor Labour', format_timedelta(process.supervisorLabour) if process.supervisorLabour else 'N/A'],
            ]
            
            process_table = Table(process_data, colWidths=[2.5*inch, 3.5*inch])
            process_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(process_table)
            
            # Add subprocess information if available
            subprocesses = SubProcessPart.objects.filter(processPart=process)
            if subprocesses.exists():
                elements.append(Spacer(1, 5))
                elements.append(Paragraph("Subprocess Details", styles['Heading4']))
                for subprocess in subprocesses:
                    subprocess_data = [
                        ['Subprocess Information', ''],
                        ['Name', subprocess.subProcessName],
                        ['Status', subprocess.get_status_display()],
                        ['Start Time', subprocess.startTime.strftime('%H:%M:%S') if subprocess.startTime else 'N/A'],
                        ['End Time', subprocess.endTime.strftime('%H:%M:%S') if subprocess.endTime else 'N/A'],
                    ]
                    
                    subprocess_table = Table(subprocess_data, colWidths=[2.5*inch, 3.5*inch])
                    subprocess_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    elements.append(subprocess_table)
            
            # Add page break if not the last process
            if i < len(process_order) - 1:
                elements.append(PageBreak())
    
    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

def export_ply_pdf(response, id):
    """View function to handle PDF export"""
    if not response.user.is_authenticated:
        return redirect('/')
        
    try:
        ply = Ply.objects.get(ply_id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()
        
        if not (ply.project in response.user.profile.user_company.project_set.all() and 
                (management or supervisor)):
            return redirect('/')
            
        processPart = ProcessPart.objects.filter(ply=ply).first()
        
        # Generate PDF
        pdf = generate_ply_pdf(ply, processPart)
        
        # Create response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ply_{ply.ply_id}_report.pdf"'
        response.write(pdf)
        return response
        
    except Exception as e:
        messages.error(response, f'Error generating PDF: {str(e)}')
        return redirect(f'/plyDetail{id}')

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import csv
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect


def export_blank_pdf(response, id):
    if not response.user.is_authenticated:
        return redirect('/')
        
    try:
        blank = Blank.objects.get(blank_id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()
        
        if not (blank.project in response.user.profile.user_company.project_set.all() and 
                (management or supervisor)):
            return redirect('/')
            
        # Get the selected process part
        processPart = blank.processpart_set.first()
        
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
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph(f"Blank {blank.blank_id} Report", title_style))
        
        # Blank Details
        elements.append(Paragraph("Blank Details", styles['Heading2']))
        blank_data = [
            ['Metric', 'Value'],
            ['Price per KG', f'£{blank.priceKG}'],
            ['Price per M²', f'£{blank.priceM2}'],
            ['Material Density', f'{blank.materialDensity} Kg/m²'],
            ['Power Rate', f'£{blank.project.powerRate}/Kwh'],
            ['CO2 Emissions', f'{blank.CO2EmissionsPerBlank} Kg']
        ]
        
        if management:
            blank_data.extend([
                ['Material Cost', f'£{blank.materialCostPerBlank}'],
                ['Material Wastage Cost', f'£{blank.materialWastageCostPerBlank}'],
                ['Technician Labour Cost', f'£{blank.technicianLabourCostPerBlank}'],
                ['Supervisor Labour Cost', f'£{blank.supervisorLabourCostPerBlank}'],
                ['Total Cost', f'£{blank.totalCost}'],
                ['Process Time', str(blank.processTimePerBlank)],
                ['Interface Time', str(blank.interfaceTimePerBlank)],
                ['Cycle Time', str(blank.cycleTimePerBlank)],
                ['Area Ratio', str(blank.blankAreaRatio)],
                ['Perimeter Ratio', str(blank.blankPerimeterRatio)],
                ['Scrap Rate', f'{blank.blankScrapRate}%']
            ])
        
        table = Table(blank_data, colWidths=[3*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # Process Details
        if processPart:
            elements.append(Paragraph(f"Process: {processPart.processName}", styles['Heading2']))
            process_data = [
                ['Metric', 'Value'],
                ['Date', str(processPart.date)],
                ['Labour Input', f'{processPart.labourInput}%'],
                ['Job Start', str(processPart.jobStart)],
                ['Job End', str(processPart.jobEnd)],
                ['Interface Time', str(processPart.interfaceTime)],
                ['Process Time', str(processPart.processTime)],
                ['Cycle Time', str(processPart.cycleTime)],
                ['Technician Labour Time', str(processPart.technicianLabour)],
                ['Supervisor Labour Time', str(processPart.supervisorLabour)],
                ['Power Consumption', f'{processPart.power} Kwh'],
                ['CO2 Emissions', f'{processPart.CO2} Kg']
            ]
            
            if management:
                process_data.extend([
                    ['Technician Labour Cost', f'£{processPart.technicianLabourCost}'],
                    ['Total Cost', f'£{processPart.totalCost}']
                ])
            
            table = Table(process_data, colWidths=[3*inch, 4*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

        # Part Relations
        if blank.part:
            elements.append(Paragraph(f"Part Relations - Part {blank.part.part_id}", styles['Heading2']))
            part_data = [
                ['Metric', 'Value'],
                ['Price per KG', f'£{blank.part.priceKG}'],
                ['Price per M²', f'£{blank.part.priceM2}'],
                ['Material Density', f'{blank.part.materialDensity} Kg/m²'],
                ['Power Rate', f'£{blank.part.project.powerRate}/Kwh'],
                ['CO2 Emissions', f'{blank.part.CO2EmissionsPerPart} Kg']
            ]
            
            if management:
                part_data.extend([
                    ['Material Cost', f'£{blank.part.materialCostPerPart}'],
                    ['Material Wastage Cost', f'£{blank.part.materialWastageCostPerPart}'],
                    ['Technician Labour Cost', f'£{blank.part.technicianLabourCostPerPart}'],
                    ['Supervisor Labour Cost', f'£{blank.part.supervisorLabourCostPerPart}'],
                    ['Total Cost', f'£{blank.part.totalCost}'],
                    ['Process Time', str(blank.part.processTimePerPart)],
                    ['Interface Time', str(blank.part.interfaceTimePerPart)],
                    ['Cycle Time', str(blank.part.cycleTimePerPart)],
                    ['Area Ratio', str(blank.part.partAreaRatio)],
                    ['Perimeter Ratio', str(blank.part.partPerimeterRatio)],
                    ['Scrap Rate', f'{blank.part.partScrapRate}%']
                ])
            
            table = Table(part_data, colWidths=[3*inch, 4*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

        # Ply Relations
        if blank.ply_set.exists():
            elements.append(Paragraph("Ply Relations", styles['Heading2']))
            for ply in blank.ply_set.all():
                elements.append(Paragraph(f"Ply {ply.ply_id}", styles['Heading3']))
                ply_data = [
                    ['Metric', 'Value'],
                    ['Price per KG', f'£{ply.priceKG}'],
                    ['Price per M²', f'£{ply.priceM2}'],
                    ['Material Density', f'{ply.materialDensity} Kg/m²'],
                    ['Power Rate', f'£{ply.powerRate}/Kwh'],
                    ['CO2 Emissions', f'{ply.CO2EmissionsPerPly} Kg']
                ]
                
                if management:
                    ply_data.extend([
                        ['Material Cost', f'£{ply.materialCostPerPly}'],
                        ['Material Wastage Cost', f'£{ply.materialWastageCostPerPly}'],
                        ['Technician Labour Cost', f'£{ply.technicianLabourCostPerPly}'],
                        ['Supervisor Labour Cost', f'£{ply.supervisorLabourCostPerPly}'],
                        ['Total Cost', f'£{ply.totalCost}'],
                        ['Process Time', str(ply.processTimePerPly)],
                        ['Interface Time', str(ply.interfaceTimePerPly)],
                        ['Cycle Time', str(ply.cycleTimePerPly)],
                        ['Area Ratio', str(ply.plyAreaRatio)],
                        ['Perimeter Ratio', str(ply.plyPerimeterRatio)],
                        ['Scrap Rate', f'{ply.plyScrapRate}%']
                    ])
                
                table = Table(ply_data, colWidths=[3*inch, 4*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="blank_{blank.blank_id}_report.pdf"'
        response.write(pdf)
        return response
        
    except Exception as e:
        messages.error(response, f'Error generating PDF: {str(e)}')
        return redirect(f'/blankDetail{id}')

def export_blank_csv(response, id):
    """View function to handle CSV export for blank details"""
    if not response.user.is_authenticated:
        return redirect('/')
        
    try:
        blank = Blank.objects.get(blank_id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()
        
        if not (blank.project in response.user.profile.user_company.project_set.all() and 
                (management or supervisor)):
            return redirect('/')
        
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="blank_{blank.blank_id}_data.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Price per KG', f'£{blank.priceKG}'])
        writer.writerow(['Price per M²', f'£{blank.priceM2}'])
        writer.writerow(['Material Density', f'{blank.materialDensity} Kg/m²'])
        writer.writerow(['Power Rate', f'£{blank.project.powerRate}/Kwh'])
        writer.writerow(['CO2 Emissions', f'{blank.CO2EmissionsPerBlank} Kg'])
        
        if management:
            writer.writerow(['Material Cost', f'£{blank.materialCostPerBlank}'])
            writer.writerow(['Material Wastage Cost', f'£{blank.materialWastageCostPerBlank}'])
            writer.writerow(['Technician Labour Cost', f'£{blank.technicianLabourCostPerBlank}'])
            writer.writerow(['Supervisor Labour Cost', f'£{blank.supervisorLabourCostPerBlank}'])
            writer.writerow(['Total Cost', f'£{blank.totalCost}'])
            writer.writerow(['Process Time', str(blank.processTimePerBlank)])
            writer.writerow(['Interface Time', str(blank.interfaceTimePerBlank)])
            writer.writerow(['Cycle Time', str(blank.cycleTimePerBlank)])
            writer.writerow(['Area Ratio', str(blank.blankAreaRatio)])
            writer.writerow(['Perimeter Ratio', str(blank.blankPerimeterRatio)])
            writer.writerow(['Scrap Rate', f'{blank.blankScrapRate}%'])
        
        return response
        
    except Exception as e:
        messages.error(response, f'Error generating CSV: {str(e)}')
        return redirect(f'/blankDetail{id}')

def get_ply_instance_number(ply):
    """Get the instance number (1-4) for this ply"""
    common_plies = CommonPly.objects.using('LION').filter(
        date_cut__isnull=False
    ).order_by('-id')[:4]
    
    for index, common_ply in enumerate(reversed(common_plies), 1):
        if common_ply.id == ply.ply_id:
            return index
    return None

def calculate_total_cost(material_cost, wastage_cost, technician_cost, supervisor_cost):
    """Calculate total cost from all components with proper decimal handling"""
    total = (
        Decimal(str(material_cost or 0)) +
        Decimal(str(wastage_cost or 0)) +
        Decimal(str(technician_cost or 0)) +
        Decimal(str(supervisor_cost or 0))
    )
    return total.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

def viewPlyDetail(response, id):
    """View function to handle ply details and process selections"""
    if not response.user.is_authenticated:
        return redirect('/')

    try:
        # Basic setup and permissions
        ply = Ply.objects.get(ply_id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()

        if not (ply.project in response.user.profile.user_company.project_set.all() and 
                (management or supervisor)):
            return redirect('/')

        # Get ply instance number (1-4)
        ply_number = get_ply_instance_number(ply)

        # Get ply shape data
        common_ply = CommonPly.objects.using('LION').filter(id=ply.ply_id).first()
        if common_ply and common_ply.shape:
            coords = list(common_ply.shape.coords[0])
            if coords:
                x_coords = [x for x, y in coords]
                y_coords = [y for x, y in coords]
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                width = max_x - min_x
                height = max_y - min_y
                padding = 0.1
                padded_width = width * (1 + padding * 2)
                padded_height = height * (1 + padding * 2)
                
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                
                path = f"M {coords[0][0]} {coords[0][1]}"
                for x, y in coords[1:]:
                    path += f" L {x} {y}"
                path += " Z"
                
                ply.shape_path = path
                ply.view_box = f"{center_x - padded_width/2} {center_y - padded_height/2} {padded_width} {padded_height}"
                ply.transform = "translate(0, 0) scale(1)"

        # Process selection setup
        processes = Process.objects.all()
        process_choices = [(process.id, process.name) for process in processes]
        process_select_form = selectProcessPartForm(process_choices)

        if response.POST.get('processPartSelect'):
            process_select_form = selectProcessPartForm(process_choices, response.POST)
            if process_select_form.is_valid():
                process_id = process_select_form.cleaned_data['choice']
                selected_process = Process.objects.get(id=process_id)

                # Get or create ProcessPart
                processPart, _ = ProcessPart.objects.get_or_create(
                    processName=selected_process.name,
                    ply=ply
                )

                # Set common values
                processPart.date = timezone.now().date()
                processPart.labourInput = 50

                try:
                    metrics = calculate_polygon_metrics(polygon_wkts)
                    ply_type = ply.name if ply.name else 'PLYTYPE_120_1'
                    perimeter_ratio = Decimal(str(metrics['ply_perimeter_ratios'].get(ply_type, 0.25)))

                    if selected_process.name == 'Cut Plies':
                        subprocess = SubProcess.objects.filter(
                            process__name='Cut Plies',
                            name='Load and Cut Ply'
                        ).first()
                        
                        if not subprocess:
                            raise SubProcess.DoesNotExist('Load and Cut Ply subprocess not found')

                        # Get power rate from project
                        power_rate = Decimal('0.308')  # Default to £0.308 if not set

                        # Set timing based on ply number
                        if ply_number == 1:
                            processPart.jobStart = subprocess.jobStart
                            processPart.jobEnd = None
                        elif ply_number == 4:
                            processPart.jobStart = None
                            processPart.jobEnd = subprocess.jobEnd
                        else:
                            processPart.jobStart = None
                            processPart.jobEnd = None

                        # Calculate process times without milliseconds
                        base_process_time = subprocess.processTime or timedelta()
                        total_seconds = int(base_process_time.total_seconds())
                        individual_seconds = total_seconds // 4
                        processPart.processTime = timedelta(seconds=individual_seconds)
                        processPart.interfaceTime = subprocess.interfaceTime or timedelta()
                        processPart.cycleTime = processPart.processTime + processPart.interfaceTime
                        processPart.technicianLabour = timedelta(seconds=int(processPart.cycleTime.total_seconds() * 0.5))

                        # Fixed ratios
                        ply.plyAreaRatio = Decimal('0.25')
                        ply.plyPerimeterRatio = Decimal('0.25')

                        # Calculate individual costs
                        material_cost = Decimal(str(subprocess.materialPartCost or 0))
                        wastage_cost = Decimal(str(subprocess.materialWastageCost or 0)) / 4
                        technician_cost = Decimal(str(subprocess.technicianLabourCost or 0))
                        supervisor_cost = Decimal(str(subprocess.supervisorLabourCost or 0)) / 4

                        # Calculate power and CO2 for individual ply
                        if subprocess.power is not None:
                            individual_power = float(subprocess.power) / 4
                            power_cost = Decimal(str(individual_power)) * power_rate
                            
                            ply.power = individual_power
                            processPart.power = individual_power
                            processPart.powerCost = power_cost.quantize(Decimal('0.001'))
                        else:
                            ply.power = 0
                            processPart.power = 0
                            processPart.powerCost = Decimal('0')

                        if subprocess.CO2 is not None:
                            individual_co2 = float(subprocess.CO2) / 4
                            ply.CO2EmissionsPerPly = individual_co2
                            processPart.CO2 = individual_co2
                        else:
                            ply.CO2EmissionsPerPly = 0
                            processPart.CO2 = 0

                        # Update ply costs
                        ply.materialCostPerPly = material_cost.quantize(Decimal('0.001'))
                        ply.materialWastageCostPerPly = wastage_cost.quantize(Decimal('0.001'))
                        ply.technicianLabourCostPerPly = technician_cost.quantize(Decimal('0.001'))
                        ply.supervisorLabourCostPerPly = supervisor_cost.quantize(Decimal('0.001'))
                        ply.powerRate = power_rate.quantize(Decimal('0.328'))

                        # Calculate total cost including power cost
                        ply.totalCost = (
                            ply.materialCostPerPly +
                            ply.materialWastageCostPerPly +
                            ply.technicianLabourCostPerPly +
                            ply.supervisorLabourCostPerPly +
                            processPart.powerCost
                        ).quantize(Decimal('0.001'))

                        # Update process times
                        ply.processTimePerPly = processPart.processTime
                        ply.interfaceTimePerPly = processPart.interfaceTime
                        ply.cycleTimePerPly = processPart.cycleTime

                    elif selected_process.name == 'Buffer (Ply Storage)':
                        ply_placed = SubProcess.objects.filter(
                            process__name='Buffer (Ply Storage)',
                            name='Ply Placed'
                        ).first()
                        ply_waiting = SubProcess.objects.filter(
                            process__name='Buffer (Ply Storage)',
                            name='Ply Waiting'
                        ).first()
                        
                        if not (ply_placed and ply_waiting):
                            raise SubProcess.DoesNotExist('Required Buffer subprocesses not found')

                        # Set power rate
                        power_rate = Decimal('0.308')
                        ply.powerRate = power_rate

                        # Set fixed ratios
                        ply.plyAreaRatio = Decimal('0.25')
                        ply.plyPerimeterRatio = Decimal('0.25')

                        # Set timing based on ply number
                        if ply_number == 1:
                            processPart.jobStart = ply_placed.jobStart
                            processPart.jobEnd = ply_waiting.jobEnd
                            processPart.interfaceTime = ply_placed.interfaceTime
                            processPart.processTime = ply_placed.processTime + ply_waiting.processTime
                        else:
                            processPart.jobStart = None
                            processPart.jobEnd = None
                            processPart.interfaceTime = timedelta()
                            processPart.processTime = ply_placed.processTime + ply_waiting.processTime

                        # Calculate cycle and technician labor time
                        processPart.cycleTime = processPart.processTime + processPart.interfaceTime
                        processPart.technicianLabour = timedelta(seconds=int(processPart.cycleTime.total_seconds() * 0.5))

                        # Calculate costs
                        technician_cost = (Decimal(str((ply_placed.technicianLabourCost or 0) + 
                                                   (ply_waiting.technicianLabourCost or 0))) / 4)
                        supervisor_cost = (Decimal(str((ply_placed.supervisorLabourCost or 0) + 
                                                   (ply_waiting.supervisorLabourCost or 0))) / 4)

                        # Calculate power and CO2
                        if ply_placed.power is not None and ply_waiting.power is not None:
                            individual_power = (float(ply_placed.power) + float(ply_waiting.power)) / 4
                            power_cost = Decimal(str(individual_power)) * power_rate
                        else:
                            individual_power = 0
                            power_cost = Decimal('0')

                        if ply_placed.CO2 is not None and ply_waiting.CO2 is not None:
                            individual_co2 = (float(ply_placed.CO2) + float(ply_waiting.CO2)) / 4
                        else:
                            individual_co2 = 0

                        # Update process part values
                        processPart.power = individual_power
                        processPart.powerCost = power_cost.quantize(Decimal('0.001'))
                        processPart.CO2 = individual_co2
                        processPart.materialCostPerPly = Decimal('0')
                        processPart.materialWastageCostPerPly = Decimal('0')
                        processPart.technicianLabourCostPerPly = technician_cost.quantize(Decimal('0.001'))
                        processPart.supervisorLabourCostPerPly = supervisor_cost.quantize(Decimal('0.001'))

                        # Update ply values
                        ply.power = individual_power
                        ply.CO2EmissionsPerPly = individual_co2
                        ply.materialCostPerPly = Decimal('0')
                        ply.materialWastageCostPerPly = Decimal('0')
                        ply.technicianLabourCostPerPly = technician_cost.quantize(Decimal('0.001'))
                        ply.supervisorLabourCostPerPly = supervisor_cost.quantize(Decimal('0.001'))

                        # Calculate total cost
                        ply.totalCost = (
                            ply.technicianLabourCostPerPly +
                            ply.supervisorLabourCostPerPly +
                            power_cost
                        ).quantize(Decimal('0.001'))

                        # Update process times
                        ply.processTimePerPly = processPart.processTime
                        ply.interfaceTimePerPly = processPart.interfaceTime
                        ply.cycleTimePerPly = processPart.cycleTime

                    elif selected_process.name == 'Create Blanks':
                        pickup_initial = SubProcess.objects.filter(
                            process__name='Create Blanks',
                            name='Pickup Initial Ply'
                        ).first()
                        pickup_weld = SubProcess.objects.filter(
                            process__name='Create Blanks',
                            name='Pickup Ply & Weld'
                        ).first()
                        
                        if not (pickup_initial and pickup_weld):
                            raise SubProcess.DoesNotExist('Required Create Blanks subprocesses not found')

                        # Set power rate
                        power_rate = Decimal('0.308')
                        ply.powerRate = power_rate

                        # Set fixed ratios
                        ply.plyAreaRatio = Decimal('0.25')
                        ply.plyPerimeterRatio = Decimal('0.25')

                        # Calculate base process time for three stages
                        base_process_time = pickup_weld.processTime or timedelta()
                        individual_process_time = timedelta(seconds=int(base_process_time.total_seconds()) // 3)  # Divide by 3 for three stages

                        # Set timing based on ply number
                        if ply_number == 1 or ply_number == 4:
                            # First and fourth plies share timing (stage 1)
                            processPart.jobStart = pickup_weld.jobStart
                            processPart.jobEnd = pickup_weld.jobEnd
                            processPart.processTime = individual_process_time
                            
                            if ply_number == 1:
                                processPart.interfaceTime = pickup_initial.interfaceTime
                            else:
                                processPart.interfaceTime = timedelta()
                        elif ply_number == 2:
                            # Second ply (stage 2)
                            processPart.jobStart = pickup_weld.jobStart
                            processPart.jobEnd = pickup_weld.jobEnd
                            processPart.interfaceTime = timedelta()
                            processPart.processTime = individual_process_time
                        else:  # ply_number == 3
                            # Third ply (stage 3)
                            processPart.jobStart = pickup_weld.jobStart
                            processPart.jobEnd = pickup_weld.jobEnd
                            processPart.interfaceTime = timedelta()
                            processPart.processTime = individual_process_time

                        # Calculate cycle time and technician labor
                        processPart.cycleTime = processPart.processTime + processPart.interfaceTime
                        processPart.technicianLabour = timedelta(seconds=int(processPart.cycleTime.total_seconds() * 0.5))

                        # Calculate cycle time and technician labor
                        processPart.cycleTime = processPart.processTime + processPart.interfaceTime
                        processPart.technicianLabour = timedelta(seconds=int(processPart.cycleTime.total_seconds() * 0.5))

                        # Calculate costs
                        technician_cost = (Decimal(str((pickup_initial.technicianLabourCost or 0) + 
                                               (pickup_weld.technicianLabourCost or 0))) / 4)
                        supervisor_cost = (Decimal(str((pickup_initial.supervisorLabourCost or 0) + 
                                               (pickup_weld.supervisorLabourCost or 0))) / 4)

                        # Calculate power and CO2
                        if pickup_initial.power is not None and pickup_weld.power is not None:
                            individual_power = (float(pickup_initial.power) + float(pickup_weld.power)) / 4
                            power_cost = Decimal(str(individual_power)) * power_rate
                        else:
                            individual_power = 0
                            power_cost = Decimal('0')

                        if pickup_initial.CO2 is not None and pickup_weld.CO2 is not None:
                            individual_co2 = (float(pickup_initial.CO2) + float(pickup_weld.CO2)) / 4
                        else:
                            individual_co2 = 0

                        # Update process part values
                        processPart.power = individual_power
                        processPart.powerCost = power_cost.quantize(Decimal('0.001'))
                        processPart.CO2 = individual_co2
                        processPart.materialCostPerPly = Decimal('0')
                        processPart.materialWastageCostPerPly = Decimal('0')
                        processPart.technicianLabourCostPerPly = technician_cost.quantize(Decimal('0.001'))
                        processPart.supervisorLabourCostPerPly = supervisor_cost.quantize(Decimal('0.001'))

                        # Update ply values
                        ply.power = individual_power
                        ply.CO2EmissionsPerPly = individual_co2
                        ply.materialCostPerPly = Decimal('0')
                        ply.materialWastageCostPerPly = Decimal('0')
                        ply.technicianLabourCostPerPly = technician_cost.quantize(Decimal('0.001'))
                        ply.supervisorLabourCostPerPly = supervisor_cost.quantize(Decimal('0.001'))

                        # Calculate total cost
                        ply.totalCost = (
                            technician_cost +
                            supervisor_cost +
                            power_cost
                        ).quantize(Decimal('0.001'))

                        # Update ply times
                        ply.processTimePerPly = processPart.processTime
                        ply.interfaceTimePerPly = processPart.interfaceTime
                        ply.cycleTimePerPly = processPart.cycleTime

                    processPart.save()
                    ply.save()
                    messages.success(response, 'Process Successfully Changed!')

                except SubProcess.DoesNotExist as e:
                    messages.error(response, str(e))
                    return redirect(f'/plyDetail{id}')

        else:
            processPart = ProcessPart.objects.filter(ply=ply).first()

        return render(response, 'MainData/viewPlyDetail.html', {
            'ply': ply,
            'management': management,
            'supervisor': supervisor,
            'processPart': processPart,
            'process_select_form': process_select_form
        })

    except Exception as e:
        messages.error(response, f'Error: {str(e)}')
        return redirect('/')

def viewBlankDetail(response, id):
    """View function to display blank details and process information."""
    if not response.user.is_authenticated:
        return redirect('/')

    try:
        # Fetch blank and check permissions
        blank = Blank.objects.get(blank_id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()

        if not (blank.project in response.user.profile.user_company.project_set.all() and 
                (management or supervisor)):
            return redirect('/')

        # Set specific material properties
        blank.priceKG = Decimal('61.870')
        blank.priceM2 = Decimal('48.260')
        blank.materialDensity = Decimal('1857.00')
        blank.CO2PerPower = Decimal('0.241')  # Adding CO2 per power rate
        blank.save()

        # Process selection setup
        available_processes = ['Buffer (Ply Storage)', 'Create Blanks']
        processSet = [(process, process) for process in available_processes]
        processPart = blank.processpart_set.first()
        process_select_form = selectProcessPartForm(processSet)

        # Ensure 4 plies exist
        plies = Ply.objects.filter(blank=blank).order_by('ply_id')
        if not plies.exists():
            for i in range(1, 5):
                Ply.objects.create(
                    blank=blank,
                    ply_id=i,
                    project=blank.project
                )
            plies = Ply.objects.filter(blank=blank).order_by('ply_id')

        # Process selection handling
        if response.POST.get('processPartSelect'):
            process_select_form = selectProcessPartForm(processSet, response.POST)
            if process_select_form.is_valid():
                selected_process = process_select_form.cleaned_data['choice']

                if selected_process == 'Buffer (Ply Storage)':
                    # Interface times calculation
                    ply_placed_interface = timedelta(minutes=0, seconds=47)
                    ply_waiting_interface = timedelta(minutes=4, seconds=42)
                    total_interface_time = ply_placed_interface + ply_waiting_interface

                    # Calculate technician labour time (half of interface time)
                    technician_labour_time = timedelta(minutes=2, seconds=45)

                    # Job timing
                    job_start = datetime(2025, 1, 9, 9, 58, 0, tzinfo=timezone.utc)
                    job_end = datetime(2025, 1, 9, 10, 3, 0, tzinfo=timezone.utc)

                    # Create or update ProcessPart
                    processPart = ProcessPart.objects.update_or_create(
                        processName=selected_process,
                        blank=blank,
                        defaults={
                            'date': timezone.now().date(),
                            'labourInput': 50,
                            'jobStart': job_start,
                            'jobEnd': job_end,
                            'processTime': timedelta(),
                            'interfaceTime': total_interface_time,
                            'cycleTime': total_interface_time,
                            'technicianLabour': technician_labour_time,
                            'supervisorLabour': timedelta(),
                            'technicianLabourCost': Decimal('14.500'),
                            'totalCost': Decimal('14.502'),
                            'power': Decimal('0.066780'),
                            'CO2': Decimal('0.01615')
                        }
                    )[0]

                    # Update Blank model
                    blank.processTimePerBlank = timedelta()
                    blank.interfaceTimePerBlank = total_interface_time
                    blank.cycleTimePerBlank = total_interface_time
                    blank.technicianLabourCostPerBlank = Decimal('14.500')
                    blank.totalCost = Decimal('14.502')
                    blank.blankAreaRatio = Decimal('1')
                    blank.blankPerimeterRatio = Decimal('1')
                    blank.save()

                    # Update each ply
                    power_rate = Decimal('0.308')
                    for ply in plies:
                        ply.materialCostPerPly = Decimal('0')
                        ply.materialWastageCostPerPly = Decimal('0')
                        ply.technicianLabourCostPerPly = Decimal('3.625')  # 14.500 / 4
                        ply.supervisorLabourCostPerPly = Decimal('0')
                        
                        ply.processTimePerPly = timedelta()
                        ply.interfaceTimePerPly = total_interface_time / 4
                        ply.cycleTimePerPly = total_interface_time / 4
                        
                        ply.power = Decimal('0.016695')  # 0.066780 / 4
                        ply.powerRate = power_rate
                        ply.CO2EmissionsPerPly = Decimal('0.004038')  # 0.01615 / 4
                        
                        ply.plyAreaRatio = Decimal('1')
                        ply.plyPerimeterRatio = Decimal('1')
                        
                        power_cost = (ply.power * power_rate).quantize(Decimal('0.001'))
                        ply.totalCost = (
                            ply.materialCostPerPly +
                            ply.materialWastageCostPerPly +
                            ply.technicianLabourCostPerPly +
                            power_cost
                        ).quantize(Decimal('0.001'))
                        
                        ply.save()

                messages.success(response, 'Process Successfully Changed!')

        return render(response, 'MainData/viewBlankDetail.html', {
            'blank': blank,
            'management': management,
            'supervisor': supervisor,
            'processPart': processPart,
            'process_select_form': process_select_form,
            'priceKG': blank.priceKG,
            'priceM2': blank.priceM2,
            'materialDensity': blank.materialDensity,
            'powerRate': blank.CO2PerPower,  # pass power rate (CO2PerPower)
            'CO2EmissionsPerBlank': blank.CO2EmissionsPerBlank,  # pass CO2 emissions per blank
        })

    except Exception as e:
        messages.error(response, f'Error: {str(e)}')
        print(f"Error in viewBlankDetail: {str(e)}")
        return redirect('/')


        
def viewPartDetail(response, id):
    """View function to display part details and process information."""
    if not response.user.is_authenticated:
        return redirect('/')
        
    try:
        part = Part.objects.get(part_id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()

        if not (part.project in response.user.profile.user_company.project_set.all() and 
                (management or supervisor)):
            return redirect('/')

        # Get processes for dropdown
        available_processes = ['Form Preform', 'Final Inspection']
        processSet = [(process, process) for process in available_processes]
        processPart = part.processpart_set.first()
        process_select_form = selectProcessPartForm(processSet)

        # Handle process selection
        if response.POST.get('processPartSelect'):
            process_select_form = selectProcessPartForm(processSet, response.POST)
            if process_select_form.is_valid():
                selected_process = process_select_form.cleaned_data['choice']

                # Initialize total values
                total_values = {
                    'interface_time': timedelta(),
                    'process_time': timedelta(),
                    'job_start': None,
                    'job_end': None,
                    'material_waste_cost': Decimal('0'),
                    'material_scrap_cost': Decimal('0'),
                    'material_part_cost': Decimal('0'),
                    'technician_labour_cost': Decimal('0'),
                    'supervisor_labour_cost': Decimal('0')
                }

                if selected_process == 'Form Preform':
                    # Initialize totals for the process
                    process_totals = {
                        'interface_time': timedelta(),
                        'process_time': timedelta(),
                        'job_start': None,  # Fixed - removed the + operator and fixed formatting
                        'job_end': None,
                        'scrap_rate': Decimal('0'),
                        'power_consumption': Decimal('0'),
                        'co2_emissions': Decimal('0'),
                        'material_waste_cost': Decimal('0'),
                        'material_scrap_cost': Decimal('0'),
                        'material_part_cost': Decimal('0'),
                        'technician_labour_cost': Decimal('0'),
                        'supervisor_labour_cost': Decimal('0'),
                        'total_cost': Decimal('0')
                    }

                    # Get subprocesses in sequence
                    form_preform_subprocesses = SubProcess.objects.filter(
                        name__in=[
                            'Mould Cooling',
                            'Part Released from Mould',
                            'Machine Returns To Home Location',
                            'Part Leaves Machine'
                        ]
                    ).order_by('id')

                    # Get first and last timings
                    first_subprocess = form_preform_subprocesses.first()
                    last_subprocess = form_preform_subprocesses.last()
                    
                    if first_subprocess and first_subprocess.jobStart:
                        process_totals['job_start'] = first_subprocess.jobStart
                    
                    if last_subprocess and last_subprocess.jobEnd:
                        process_totals['job_end'] = last_subprocess.jobEnd

                    # Sum up values from all subprocesses
                    for subprocess in form_preform_subprocesses:
                        if subprocess.interfaceTime:
                            process_totals['interface_time'] += subprocess.interfaceTime
                        if subprocess.processTime:
                            process_totals['process_time'] += subprocess.processTime
                        
                        # Sum up numerical values
                        process_totals['power_consumption'] += Decimal(str(subprocess.power or 0))
                        process_totals['co2_emissions'] += Decimal(str(subprocess.CO2 or 0))
                        process_totals['material_waste_cost'] += Decimal(str(subprocess.materialWastageCost or 0))
                        process_totals['material_scrap_cost'] += Decimal(str(subprocess.materialScrapCost or 0))
                        process_totals['material_part_cost'] += Decimal(str(subprocess.materialPartCost or 0))
                        process_totals['technician_labour_cost'] += Decimal(str(subprocess.technicianLabourCost or 0))
                        process_totals['supervisor_labour_cost'] += Decimal(str(subprocess.supervisorLabourCost or 0))
                        
                        # Calculate total cost for this subprocess
                        subprocess_total = (
                            Decimal(str(subprocess.materialWastageCost or 0)) +
                            Decimal(str(subprocess.materialScrapCost or 0)) +
                            Decimal(str(subprocess.materialPartCost or 0)) +
                            Decimal(str(subprocess.technicianLabourCost or 0)) +
                            Decimal(str(subprocess.supervisorLabourCost or 0))
                        )
                        process_totals['total_cost'] += subprocess_total

                    # Create or update ProcessPart with summed values
                    ProcessPart.objects.update_or_create(
                        processName=selected_process,
                        part=part,
                        defaults={
                            'date': timezone.now().date(),
                            'labourInput': 100,  # Set to 100% as shown in data
                            'jobStart': process_totals['job_start'],
                            'jobEnd': process_totals['job_end'],
                            'interfaceTime': process_totals['interface_time'],
                            'processTime': process_totals['process_time'],
                            'cycleTime': process_totals['interface_time'] + process_totals['process_time'],
                            'power': process_totals['power_consumption'],
                            'CO2': process_totals['co2_emissions'],
                            'materialWastageCost': process_totals['material_waste_cost'],
                            'materialScrapCost': process_totals['material_scrap_cost'],
                            'materialPartCost': process_totals['material_part_cost'],
                            'technicianLabourCost': process_totals['technician_labour_cost'],
                            'supervisorLabourCost': process_totals['supervisor_labour_cost'],
                            'totalCost': process_totals['total_cost']
                        }
                    )
                if selected_process == 'Final Inspection':
                    # Get timing data from Initial Weight and Final Assessment subprocesses
                    init_weight_subprocess = SubProcess.objects.filter(
                        name='Part Assessment (Initial Weight)'
                    ).first()
                    final_assessment_subprocess = SubProcess.objects.filter(
                        name='Part Assessment (Final Weight)'
                    ).first()

                    if init_weight_subprocess and final_assessment_subprocess:
                        # Calculate total values
                        process_totals = {
                            'interface_time': timedelta(hours=0, minutes=0, seconds=54), 
                            'process_time': timedelta(hours=0, minutes=6, seconds=24),    # From Trim subprocess
                            'job_start': datetime(2025, 1, 9, 15, 16, 20, tzinfo=timezone.utc),  # Initial Weight Start
                            'job_end': datetime(2025, 1, 9, 15, 23, 56, tzinfo=timezone.utc),    # Final Weight End
                        }

                        # Update Part model
                        part.processTimePerPart = process_totals['process_time']
                        part.interfaceTimePerPart = process_totals['interface_time']
                        part.cycleTimePerPart = process_totals['process_time'] + process_totals['interface_time']
                        part.materialCostPerPart = Decimal('0.000')
                        part.materialWastageCostPerPart = Decimal('12.000')  # From Trim subprocess
                        part.technicianLabourCostPerPart = Decimal('0.000')
                        part.supervisorLabourCostPerPart = Decimal('43.500')  # 14.500 * 3 (Initial, Trim, Final)
                        part.totalCost = Decimal('55.500')  # 12.000 + 43.500
                        part.CO2EmissionsPerPart = Decimal('0')
                        part.partScrapRate = 0
                        part.save()

                        # Update ProcessPart
                        ProcessPart.objects.update_or_create(
                            processName=selected_process,
                            part=part,
                            defaults={
                                'date': timezone.now().date(),
                                'labourInput': 100,
                                'jobStart': process_totals['job_start'],
                                'jobEnd': process_totals['job_end'],
                                'interfaceTime': process_totals['interface_time'],
                                'processTime': process_totals['process_time'],
                                'cycleTime': process_totals['interface_time'] + process_totals['process_time'],
                                'technicianLabour': timedelta(0),
                                'supervisorLabour': process_totals['interface_time'] + process_totals['process_time'],
                                'materialWastageCost': Decimal('12.000'),
                                'technicianLabourCost': Decimal('0.000'),
                                'supervisorLabourCost': Decimal('43.500'),
                                'totalCost': Decimal('55.500')
                            }
                        )

                        messages.success(response, 'Process Successfully Changed!')
                # Update the processPart for display
                processPart = ProcessPart.objects.filter(
                    part=part,
                    processName=selected_process
                ).first()

                messages.success(response, 'Process Successfully Changed!')

        return render(response, 'MainData/viewPartDetail.html', {
            'part': part,
            'management': management,
            'supervisor': supervisor,
            'processPart': processPart,
            'process_select_form': process_select_form
        })

    except Exception as e:
        messages.error(response, f'Error: {str(e)}')
        print(f"Error in viewPartDetail: {str(e)}")
        return redirect('/')


from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db.models import Max

# Models from Main app
from Main.models import Project, Process, SubProcess

# Models from MainData app
from MainData.models import Part, PartInstance, Blank, BlankInstance, Ply, PlyInstance

# Model from monorepo app
from monorepo.models import CommonPly

def viewProjectParts(response, id):
    """View to handle project parts, including ply creation with names"""
    if not response.user.is_authenticated:
        return redirect('/mylogout/')
        
    try:
        project = Project.objects.get(id=id)
        management = response.user.groups.filter(name='Management').exists()
        supervisor = response.user.groups.filter(name='Supervisor').exists()
        
        if not (response.user.profile.user_company and 
                project in response.user.profile.user_company.project_set.all() and
               (management or supervisor)):
            return redirect('/')
        
        process = Process.objects.filter(project=project).first()
        if process:
            cut_ply = SubProcess.objects.filter(name='Load and Cut Ply').first()
            if cut_ply:
                # Get latest CommonPly entries
                common_plies = CommonPly.objects.using('LION').filter(
                    date_cut__isnull=False
                ).order_by('-id')[:4]
                
                if common_plies:
                    # Create/update plies
                    for index, common_ply in enumerate(reversed(common_plies), 1):
                        # Create new PlyInstance with unique instance_id
                        max_ply_instance_id = PlyInstance.objects.all().aggregate(Max('instance_id'))['instance_id__max']
                        new_ply_instance_id = 1 if max_ply_instance_id is None else max_ply_instance_id + 1
                        
                        ply_instance = PlyInstance.objects.create(
                            instance_id=new_ply_instance_id,
                            process=process
                        )
                        
                        # Get name from CommonPly or use default pattern
                        ply_name = common_ply.name if hasattr(common_ply, 'name') and common_ply.name else f'PLYTYPE_120_{index}'
                        
                        # Update or create Ply
                        ply, created = Ply.objects.update_or_create(
                            ply_id=common_ply.id,
                            project=project,
                            defaults={
                                'date': common_ply.date_cut.date(),
                                'plyInst': ply_instance,
                                'name': ply_name
                            }
                        )
                    
                    # Check for unassigned plies
                    latest_plies = list(Ply.objects.filter(
                        project=project,
                        blank__isnull=True
                    ).order_by('-ply_id')[:4])
                    
                    if len(latest_plies) == 4:
                        latest_plies.reverse()  # Order from oldest to newest
                        
                        # Create new blank instance with unique instance_id
                        max_blank_instance_id = BlankInstance.objects.all().aggregate(Max('instance_id'))['instance_id__max']
                        new_blank_instance_id = 1 if max_blank_instance_id is None else max_blank_instance_id + 1
                        
                        blank_instance = BlankInstance.objects.create(
                            instance_id=new_blank_instance_id,
                            process=process
                        )
                        
                        # Create new blank
                        blank = Blank.objects.create(
                            project=project,
                            date=timezone.now().date(),
                            blankInstance=blank_instance
                        )
                        
                        # Link plies to blank
                        for ply in latest_plies:
                            ply.blank = blank
                            ply.save()
            
            # Create Part for Blank ID 4 if it doesn't exist
            blank_4 = Blank.objects.filter(blank_id=4, part__isnull=True).first()
            if blank_4:
                # Get the maximum instance_id and increment by 1 for PartInstance
                max_instance_id = PartInstance.objects.all().aggregate(Max('instance_id'))['instance_id__max']
                new_instance_id = 1 if max_instance_id is None else max_instance_id + 1
                
                # Create new part instance with unique instance_id
                part_instance = PartInstance.objects.create(
                    instance_id=new_instance_id,
                    process=process
                )
                
                # Get the maximum part_id and increment by 1
                max_part_id = Part.objects.all().aggregate(Max('part_id'))['part_id__max']
                new_part_id = 1 if max_part_id is None else max_part_id + 1
                
                # Create the part
                part = Part.objects.create(
                    part_id=new_part_id,
                    project=project,
                    date=timezone.now().date(),
                    partInstance=part_instance,
                    submitted=True  # Mark as submitted
                )
                
                # Link blank to part
                blank_4.part = part
                blank_4.save()

        return render(response, 'MainData/viewProjectPart.html', {
            'project': project,
            'management': management,
            'supervisor': supervisor
        })
    
    except Exception as e:
        messages.error(response, f'Error: {str(e)}')
        return redirect('/')



def viewPartSubDetail(response, id):
    '''View to allow the user to access the detail of the sub process related to the part'''
    #setup
    if response.user.is_authenticated:
        proPart, management, supervisor = ProcessPart.objects.get(id=id), False, False
        part, ply, blank = False,False,False
        if response.user.groups.filter(name='Management').exists(): 
            management = True   
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True   
        if proPart.part is not None:
            checkVar = proPart.part
            part = True
        elif proPart.blank is not None:
            checkVar = proPart.blank
            blank = True
        elif proPart.ply is not None:
            checkVar = proPart.ply
            ply = True
            
        #check project in user company set
        if checkVar.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:
                orderedSubProcessPartList = proPart.subprocesspart_set.all()
                lastCardID = orderedSubProcessPartList.last()
                return render(response, 'MainData/viewPartSubDetail.html', {'part':part, 'ply':ply, 'blank':blank,  'proPart':proPart,  'management':management, 'supervisor':supervisor, 'lastCardID': lastCardID})
        else:
            #redirect to home page
            return redirect('/')
            
        #redirect to home page
        return redirect('/')    
    else:
        return redirect('/mylogout/')
        
def viewPartSubSensorDetail(response, id):
    '''view to allow user to access sensor detail related to the part'''
    #setup      
    if response.user.is_authenticated:
        subProPart, management, supervisor = SubProcessPart.objects.get(id=id), False, False
        if response.user.groups.filter(name='Management').exists(): 
            management = True   
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True   
        #check project in user company set
        if subProPart.processPart.part.project in response.user.profile.user_company.project_set.all():
            if management or supervisor:
                return render(response, 'MainData/viewPartSubSensorDetail.html', {'subProPart' : subProPart,  'management':management, 'supervisor':supervisor})
        else:
            #redirect to the home page      
            return redirect('/')    
        
        #redirect to home page
        return redirect('/')    
    else:
        return redirect('/mylogout/')
        

def processPartSensor(response, id):
    #setup      
    if response.user.is_authenticated:
        sensorData, management, supervisor, processPart, subProcessPart, error, project = SensorData.objects.get(id=id), False, False, False, False, '',''
        if sensorData.processPart is not None:
            project = sensorData.processPart.part.project
            processPart = True
        elif sensorData.subProcessPart is not None:
            project = sensorData.subProcessPart.processPart.part.project
            subProcessPart = True

        if response.user.groups.filter(name='Management').exists(): 
            management = True   
        elif response.user.groups.filter(name='Supervisor').exists():
            supervisor = True
        
            
        if project in response.user.profile.user_company.project_set.all():
            if management or supervisor:
                return render(response, 'MainData/processPartSensor.html', {'sensorData' : sensorData,  'management':management, 'supervisor':supervisor, 'processPart':processPart, 'subProcessPart':subProcessPart })
        else:
            #redirect to the home page      
            return redirect('/')    
            
        #redirect to home page
        return redirect('/')    
    else:
        return redirect('/mylogout/')
    

def updateProcessGraph(response, id):
    #part data sensor graphs
    if response.user.is_authenticated:
        sensor, data, labels, date = SensorData.objects.get(id=id), [], [], []
        #get all sensortime data for sensors and append it to data and labels for graph plotting
        for instance in sensor.sensortimedata_set.all():
            if sensor.sensorName == "Thermocouple":
                data.append(instance.temp) 
                format_data = "%H:%M:%S"
                labels.append(datetime.strftime(instance.time, format_data))

            elif sensor.sensorName == "Accelerometer":
                data.append(instance.acceleration)
                format_data = "%H:%M:%S"
                labels.append(datetime.strftime(instance.time, format_data))

            elif sensor.sensorName == "Pressure Sensor":
                data.append(instance.pressure)
                format_data = "%H:%M:%S"
                labels.append(datetime.strftime(instance.time, format_data))

            elif sensor.sensorName == "Motor Driver":
                data.append(instance.torque)
                format_data = "%H:%M:%S"
                labels.append(datetime.strftime(instance.time, format_data))

            elif sensor.sensorName == "Microphone":
                data.append(instance.noise)
                format_data = "%H:%M:%S"
                labels.append(datetime.strftime(instance.time, format_data))

            format_data = "%m/%d/%Y"
            date = datetime.strftime(instance.time, format_data)



        return JsonResponse(data={'data':data, 'labels':labels, 'date': date,})
    else:
        return redirect('/')

        