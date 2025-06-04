from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, date, timedelta
from .choices import *
from django.core.validators import MaxValueValidator, MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Case, When, Value
from django.db.models.functions import Lower
from django.db.models.fields import NOT_PROVIDED
import django.utils
from zoneinfo import ZoneInfo
django.utils.timezone.activate(ZoneInfo("Europe/London"))
from jsonfield import JSONField
from django.utils import timezone

class Company(models.Model):
    '''Model for storing company information'''
     #--Choices--#
    COMPANY_CHOICES = [
    ('airborne','Airborne'),
    ('test_comp','Test Company'),
    ]
    company_choices_dict = {
    'airborne' : 'Airborne',
    'test_comp' : 'Test Company'
    }
    company_name = models.CharField(max_length=50, choices=COMPANY_CHOICES, null=True)
    total_power = models.FloatField(default=0, null = True)
    co2_choice = models.DecimalField(max_digits=10, decimal_places=5, null=True)
    json = JSONField(null=True)

    def __str__(self):
        return self.company_name

class CompanyTime(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null = True)
    power = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    time=models.DateTimeField(default=django.utils.timezone.now)
    id = models.BigAutoField(primary_key=True)

    # PROFILE START
class Profile(models.Model):
    '''Model to extend the standard django user model '''
    user = models.OneToOneField(User, on_delete=models.CASCADE, default='default')
    username = models.CharField(primary_key=True, default="anonymous", max_length=50)
    user_company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    sequence_choice = models.IntegerField(default = None, null = True)
    duration_energy = models.DecimalField(max_digits=30, decimal_places=3, default=0.06, null=True)
    energy_start_date = models.DateTimeField(null=True, default=django.utils.timezone.now)
    energy_end_date = models.DateTimeField(null=True, default=django.utils.timezone.now)


    def __str__(self):
        return self.user.username


    # SIGNALS REDUNDANT
    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(username=instance.username, user=instance)


    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()


    # PROFILE END
class Material(models.Model):
    MATERIAL_CHOICES = [
        ('test', 'Test One'),
        ('test2', 'Test Two'),
       
    ]
    
    material_choices_dict = {
        'test' : 'Test One',
        'test2' : 'Test Two',

    }
    name = models.CharField(max_length=30, choices=MATERIAL_CHOICES, null = True)
    optimumTime = models.DurationField(null=True, default=timedelta(0))
    optimumTemp = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    optimumPressure = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    priceKG = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    priceM2 = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    materialDensity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    materialCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    

class Project(models.Model):
    '''Model to hold projects and their information'''
    project_name = models.CharField(max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    techRate = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    superRate = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    powerRate = models.DecimalField(max_digits=10, decimal_places=5, default=0)
    manual = models.BooleanField(default=False)
    setUpCost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    CO2PerPower = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    workOrderNumber = models.CharField(max_length=20, null=True)
    
    baselinePartNo = models.IntegerField(default=0)
    badPartCounter = models.IntegerField(default=0)
    goodPartCounter = models.IntegerField(default=0)
    
    startDate = models.DateField(null=True)
    OEEstartDate = models.DateField(null=True)
    endDate = models.DateField(null=True)
    OEEendDate = models.DateField(null=True)

    priceKG = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    priceM2 = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    materialDensity = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    weightTolerance = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    lengthTolerance = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    widthTolerance = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    depthTolerance = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    preformWrinklingTolerance = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    thicknessTolerance = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    nominalVolumeWrinkling = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    nominalPartWeight = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    nominalPartArea = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    nominalPartLength = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    nominalPartWidth = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    nominalPartThickness = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    totalShiftTime = models.DecimalField(max_digits = 10, decimal_places=3, default = 0)
    plannedDownTime = models.DecimalField(max_digits = 10, decimal_places=3, default = 0)
    allDownTime = models.DecimalField(max_digits = 10, decimal_places=3, default = 0)
    allStopTime = models.DecimalField(max_digits = 10, decimal_places=3, default = 0)
    theoreticalCycleTime = models.DecimalField(max_digits = 10, decimal_places=3, default = 0)
    defectAmount = models.DecimalField(max_digits = 10, decimal_places=3, default = 0)

    material = models.CharField(max_length=50, null=True)

    learningRate = models.FloatField(default=0.88)

    machineConfirmed = models.BooleanField(default=False)
    processConfirmed = models.BooleanField(default=False)
    editStatus = models.IntegerField(default=0)
    noSuggested = models.BooleanField(default=False)

    processWindow = models.BooleanField(default=False)
    #Cost Breakdown

    #--Labour--#    
    technicianLabour = models.DurationField(null=True)
    supervisorLabour = models.DurationField(null=True)
    technicianLabourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    supervisorLabourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    
    #--Total Cost--#
    assumedCost = models.FloatField(default=1, null=True)

    #Cost Breakdown
    materialCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    powerCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    labourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    totalCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    
    #Choices
    CONST_CHOICES_SUPER = [
        ('NPW','    Nominal Part Weight'),
        ('NPL','    Nominal Length'),
        ('NWI','    Nominal Width'),
        ('NPT','    Nominal Thickness'),
        ('TT',      'Thickness Tolerance'),
        ('WT',      'Width tolerance'),
        ('LT',      'Length tolerance'),
        ('DT',      'Depth tolerance'),
        ('TW',      'Weight Tolerance'),
        ('NVW',     'Nominal volume of wrinkling'),
        ('PWT',     'Preform wrinkling tolerance'),


    ]

    const_dict_super = {
        'NPW':'nominalPartWeight',
        'NPL':'nominalPartLength',
        'NWI':'nominalPartWidth',
        'NPT':'nominalPartThickness',
        'TT': 'thicknessTolerance',
        'WT':'widthTolerance',
        'LT':'lengthTolerance',
        'DT':'depthTolerance',
        'NPW':'nominalPartWeight',
        'TW':'weightTolerance',
        'NVW':'nominalVolumeWrinkling',
        'PWT':'preformWrinklingTolerance',
    }

    CONST_CHOICES_MANG = [
        ('THR','Technician Rate'),
        ('SUR','Supervisor Rate'),
        ('PWR','Electricity Rate'),
        ('SUC','Set Up Cost'),
        ("BPN", 'Baseline Part Number'),
        ("PKW", 'CO2 per KWH'),
        ("WON", 'Work Order Number'),
        
    ]
    
    const_dict_mang = {
        'THR':'techRate',
        'SUR':'superRate',
        'PWR':'powerRate',
        'BPN':'baseLinePartNo',
        "PKW":'CO2PerPower',
        'SUC':'setUpCost',
        "WON": 'Work Order Number',
        
    }

    PLY_CUTTER_LIST = [
        'Cut Plies',
        'Inspect Plies',
        'Buffer (Ply Storage)',
    ]

    PRE_CELL_LIST = [
        'Create Blanks',
        'Prep Material For Press',
        'Buffer (Blank Storage)',
        'Pre Heat',
        'Form Preform',
        'Final Inspection'
    ]


    #--Methods--#
    
    def updateProjectCosts(self):
        #Initialisation
        totalTechLabour = timedelta()
        totalSuperLabour = timedelta()
        totalTechLabourCost = 0
        totalSuperLabourCost = 0
        totalLabourCost = 0
        totalPowerCost = 0
        totalMaterialCost = 0
        
        #for every process in project process set
        for process in self.process_set.all():
            totalTechLabour += process.technicianLabour
            totalSuperLabour += process.supervisorLabour
            totalTechLabourCost += process.technicianLabourCost
            totalSuperLabourCost += process.supervisorLabourCost
            totalLabourCost += process.labourSumCost
            totalPowerCost += process.powerCost
            totalMaterialCost += process.materialSumCost #cumulatively add all costs
            
        #project costs are equal to total costs from adding all process costs
        self.technicianLabour = totalTechLabour 
        self.supervisorLabour = totalSuperLabour
        self.technicianLabourCost = totalTechLabourCost
        self.supervisorLabourCost = totalSuperLabourCost
        self.materialCost = totalMaterialCost

        totalLabourCost = self.technicianLabourCost + self.supervisorLabourCost

        self.labourCost = totalLabourCost
        self.materialCost = totalMaterialCost
        self.powerCost = totalPowerCost
        
        self.totalCost = self.materialCost + self.powerCost + self.labourCost  
        self.save()     
    
    def __str__(self):
        return self.project_name

    def order_process(self): #order all processes sequentially
        processSet = self.process_set.all()
        return processSet.order_by( Case( 
                                When ( name ="Incoming Goods", then=Value(0) ),
                                When ( name ="Store Material", then=Value(1)  ),
                                When ( name ="Move Material to Ply Cutting", then=Value(2) ),
                                When ( name ="Cut Plies", then=Value(3) ),
                                When ( name ="Inspect Plies", then=Value(4) ),
                                When ( name ="Sort Plies", then=Value(5) ),
                                When ( name ='Buffer (Ply Storage)', then=Value(6) ),
                                When ( name ="Create Blanks", then=Value(7) ),
                                When ( name ='Buffer (Blank Storage)', then=Value(8) ),
                                When ( name ="Prep Material For Press", then=Value(9) ),
                                When ( name ="Pre Heat", then=Value(10) ),
                                When ( name ="Form Preform", then=Value(11) ),
                                When ( name ='Final Inspection', then=Value(12)),
                                When ( name ="Destination", then=Value(13) ),
                                When ( manualName ="Incoming Goods", then=Value(0) ),
                                When ( manualName ="Store Material", then=Value(1)  ),
                                When ( manualName ="Move Material to Ply Cutting", then=Value(2) ),
                                When ( manualName ="Cut Plies", then=Value(3) ),
                                When ( manualName ="Inspect Plies", then=Value(4) ),
                                When ( manualName ="Sort Plies", then=Value(5) ),
                                When ( manualName ='Buffer (Ply Storage)', then=Value(6) ),
                                When ( manualName ='Create Blanks', then=Value(7) ),
                                When ( manualName ='Buffer (Blank Storage)', then=Value(8) ),
                                When ( manualName ="Create Stabilised Blanks", then=Value(9) ),
                                When ( manualName ="Form Preform", then=Value(10) ),
                                When ( manualName ='Final Inspection', then=Value(11) ),
                                default = Value(0)
                                    )
                                )

    def order_process_custom(self):
        processSet = self.process_set.all() 
        return processSet.order_by( Case( 
                                When ( position = 0, then=Value(0) ),
                                When ( position = 1, then=Value(1)  ),
                                When ( position = 2, then=Value(2)  ),
                                When ( position = 3, then=Value(3) ),
                                When ( position = 4, then=Value(4) ),
                                When ( position = 5, then=Value(5) ),
                                When ( position = 6, then=Value(6) ),
                                When ( position = 7, then=Value(7) ),
                                When ( position = 8, then=Value(8) ),
                                When ( position = 9, then=Value(9) ),
                                When ( position = 10, then=Value(10) ),
                                When ( position = 11, then=Value(11) ),
                                When ( position = 12, then=Value(12) ),
                                When ( position = 13, then=Value(13) ),
                                )
        )

    def update_process_positions(self):
        count = 0
        for each in self.order_process():
            if each.position is None and self.editStatus != 0:
                each.position = count
                each.save()
            elif self.editStatus == 0:
                each.position = count 
                each.save()
            count+=1
        for every in self.order_process_custom():
            if every.position == 0 and every.position != len(self.order_process_custom()) -1:
                every.startPoint = True
                every.endPoint = False
            elif every.position == len(self.order_process_custom())-1 and every.position != 0:
                every.endPoint = True
                every.startPoint = False
            elif every.position == 0 and every.position == len(self.order_process_custom()) -1:
                every.startPoint = True
                every.endPoint = True
            else:
                every.startPoint = False
                every.endPoint = False
            every.save()


    class Meta:
        permissions = [
            ('edit_project', 'create or delete project')
        ]

class Machine(models.Model):
    
    #--Choices--#
    MACHINE_CHOICES = [
        ('ply_cutter','Ply Cutter'),
        ('pick_place_sort','Pick and Place (sort)'),
        ('pick_place_blanks','Pick and Place (blanks)'),
        ('preform_cell', 'Preforming Cell'),
    ]
    machine_choices_dict = {
        'ply_cutter':'Ply Cutter',
        'pick_place_sort':'Pick and Place (sort)',
        'pick_place_blanks':'Pick and Place (blanks)',
        'preform_cell':'Preforming Cell',
    }
    
    """Model to contain all the machine"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=50, choices=MACHINE_CHOICES)
    status = models.IntegerField(default=0)
    projects = models.ManyToManyField(Project)

    def __str__(self):
        return self.name

class PossibleProjectProcess(models.Model):

    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name


class PossibleProjectTia(models.Model):

    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

class PossibleProjectMachines(models.Model):

    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class PossibleProjectSensors(models.Model):

    name = models.CharField(max_length=50)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    modelID = models.CharField(max_length=50, null = True)

    def __str__(self):
        return self.name

        


class Process(models.Model):
    """Model to represent a manufacturing process"""
    
    #--Choices--#
    PROCESS_CHOICES = [
    ('','Choose a Process'),
    ('incoming_goods', 'Incoming Goods'),
    ('store_material', 'Store Material'),
    ('move_material', 'Move Material to Ply Cutting'),
    ('cut_plies', 'Cut Plies'),
    ('inspect_plies', 'Inspect Plies'),
    ('sort_plies', 'Sort Plies'),
    ('create_blanks', 'Create Stabilised Blanks'),
    ('form_preform', 'Form Preform'),
    ('pre_heat', 'Pre Heat'),
    ]
    process_dict = {
    'incoming_goods': 'Incoming Goods',
    'store_material': 'Store Material',
    'move_material': 'Move Material to Ply Cutting',
    'cut_plies': 'Cut Plies',
    'inspect_plies': 'Inspect Plies',
    'sort_plies': 'Sort Plies',
    'create_blanks': 'Create Stabilised Blanks',
    'form_preform': 'Form Preform',
    'pre_heat': 'Pre Heat',
    }

    MANUAL_PROCESS_CHOICES = [
    ('','Choose a Process'),
    ('incoming_goods', 'Incoming Goods'),
    ('store_material', 'Store Material'),
    ('move_material', 'Move Material to Ply Cutting'),
    ('cut_plies', 'Cut Plies'),
    ('inspect_plies', 'Inspect Plies'),
    ('sort_plies', 'Sort Plies'),
    ('create_blanks', 'Create Stabilised Blanks'),
    ('form_preform', 'Form Preform'),
    ]
    manual_process_dict = {
    'incoming_goods': 'Incoming Goods',
    'store_material': 'Store Material',
    'move_material': 'Move Material to Ply Cutting',
    'cut_plies': 'Cut Plies',
    'inspect_plies': 'Inspect Plies',
    'sort_plies': 'Sort Plies',
    'create_blanks': 'Create Stabilised Blanks',
    'form_preform': 'Form Preform',
    }

    CUT_PLIES_SUB_LIST = [
        'Cut Initialisation',
        'Backer Removal',
        'Vail Addition',
        'Cut Ply',
        'Unload Ply',
    ]

    BUFFER_PLY_STORAGE_LIST = [
        'Ply Placed',
        'Ply Waiting',
    ]

    CREATE_BLANKS_SUB_LIST = [
        'Pickup Initial Ply',
        'Pickup Ply & Weld',
    ]

    BUFFER_BLANK_STORAGE_LIST = [
        'Blank Placed',
        'Blank Waiting',
        'Blank Removed',
    ]

    PREP_FOR_PRESS_SUB_LIST = [
        'Lay Bottom Casette',
        'Lay Blank',
        'Lay Top Casette',
        # 'Unload Casette', Duplicate sub-process
    ]

    FORM_PREFORM_SUB_LIST = [
        'Initialisation',
        'Heat Mould and Platten Up',
        'Blank Loaded in Machine',
        'Temperature Reached and Platten Down',
        'Blank Inside Press',
        'Blank Pressed',
        'Mould Cooling',
        'Part Released from Mould',
        'Machine Returns to Home Location',
        'Preform leaves Tool',
        'Part Leaves Machine',
    ]

    PRE_HEAT_SUB_LIST = [

        'Load',
        'Heating',
        'Unload'
    ]

    DESTINATION_SUB_LIST = [

        'Mould moves to loading',
        'Inserts Heated',
        'Mould loaded',
        'Mould moves into press'
    ]

    FINAL_INSPECTION_SUB_LIST = [
        'Part Assessment (Initial Weight)',
        'Trim',
        'Part Assessment (Final Weight)',
        'Part Assessment (Final Geometry)',
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    machine = models.ManyToManyField(Machine)
    name = models.CharField(max_length=50, null=True)
    manualName = models.CharField(max_length=50,null=True)
    viable = models.BooleanField(default=False)
    operator = models.CharField(max_length=50, null=True)
    labourInput = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cycleTime = models.DurationField(null=True, default=timedelta())
    processTime = models.DurationField(null=True, default=timedelta())
    jobStart = models.DateTimeField(null=True, default=None)
    jobEnd = models.DateTimeField(null=True, default=None)
    processStart = models.DateTimeField(null=True, default=None)
    processEnd = models.DateTimeField(null=True, default=None)
    interfaceTime = models.DurationField(null=True, default=timedelta())
    badPart = models.BooleanField(default=False)
    scrapRate = models.DecimalField(max_digits=3, decimal_places=0, default=0)
    minBatchSize = models.DecimalField(max_digits=50, decimal_places=0, default=50)
    maxBatchSize = models.DecimalField(max_digits=50, decimal_places=0, default=350)
    power = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    status = models.IntegerField(default=0)
    qualityCheck = models.BooleanField(default=False, null=True)    
    CO2 = models.DecimalField(max_digits=50, decimal_places=5, default=0)
    cycleCostRatio = models.DecimalField(max_digits=50, decimal_places=3, default=0)
    wastedTime = models.DurationField(null=True)
    editProcess = models.BooleanField(default=False)
    cached_CO2 = models.DecimalField(max_digits=50, decimal_places=3, default=0)
    
    #Cost Breakdown

    #--Material--#
    materialWastage = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialScrap = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialPart = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialWastageCost = models.DecimalField(max_digits=15, decimal_places=3, default=0)   
    materialScrapCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialPartCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialSumCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    
    #--Labour--#
    technicianLabour = models.DurationField(null=True, default=timedelta())
    supervisorLabour = models.DurationField(null=True, default=timedelta())
    technicianLabourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    supervisorLabourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    labourSumCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    
    #--Utility--#
    powerCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    
    #--TotalCost--#
    totalCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    processCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    partCreated = models.BooleanField(default=False)

    position = models.IntegerField(default=None, null = True)
    startPoint = models.BooleanField(default = False)
    endPoint = models.BooleanField(default = False)

    initialised = models.BooleanField(default=False)

    #Data Remapping#
    blankPlaced = models.BooleanField(default=False)
    blankWaiting = models.BooleanField(default=False)
    blankRemoved = models.BooleanField(default=False)

    blankInCassette = models.BooleanField(default=False)
    destinationClear = models.BooleanField(default=False)
    unloadExecuted = models.BooleanField(default=False)

    blankCassetteInPosition = models.BooleanField(default=False)
    temperatureOkay = models.BooleanField(default=False)
    heatingDoneAtCorrectTime = models.BooleanField(default=False)
    pressIsClear = models.BooleanField(default=False)
    cassetteLeftPreHeater = models.BooleanField(default=False)

    robotConnected = models.BooleanField(default=False)

    mouldInLoadingArea = models.BooleanField(default=False)
    insertsAtTempAndTime = models.BooleanField(default=False)
    mouldInPress = models.BooleanField(default=False)



    
    #--methods--#
    def updateIntervals(self):
        """Function to update a process's cycle,interface and process times"""
        #setup
        totalInterface = timedelta()
        totalProcess = timedelta()
        totalCycle = timedelta()
        #cycle sub process's to find total interface and process times
        for subPro in self.subprocess_set.all():
            totalInterface += subPro.interfaceTime
            totalProcess += subPro.processTime
        
        #calc total cycle
        totalCycle = totalInterface + totalProcess  
        
        #assign to model and save
        self.interfaceTime = totalInterface
        self.processTime = totalProcess
        self.save()

    def updateBatchSize(self):
        """Function to update a process batch range"""
        #setup  
        batchList = []
        process = self
        
        #get list of all batch sizes
        for subPro in process.subprocess_set.all():
            batchList.append(subPro.batchSize)
        
        #assign to model and save
        process.minBatchSize = min(batchList)
        process.maxBatchSize = max(batchList)
        process.save()

    def updateProcessStartEnd(self):
        """Function to update a process's start and end times"""
        #setup  
        endList = []
        startList = []
        process = self

        for subPro in process.subprocess_set.all():
            if subPro.jobStart is not None:
                startList.append(subPro.jobStart)
                if subPro.jobEnd is not None:
                    endList.append(subPro.jobEnd)
        
        #find min time in start list and assign 
        if len(startList) != 0:     
            process.jobStart = min(startList)
        #find max time in end list and assign
        if len(endList) != 0:   
            process.jobEnd = max(endList)
        #save
        process.save()

    def updateScrapRate(self):
        """Function to update a process scrap value"""
        process = self
        #setup  
        scrapList = []
        #create list of all scrap rates
        for subPro in process.subprocess_set.all():
            scrapList.append(subPro.scrapRate)
        
        #find average scrap assign and save
        process.scrapRate = sum(scrapList)/len(scrapList)
        process.save()

    def updateLabourInput(self):
        """Function to update a process labour input"""
        #setups
        process = self
        labourList = []
        #create list of all labour inputs
        for subPro in process.subprocess_set.all():
            if subPro.labourInput is not None:
                labourList.append(subPro.labourInput)
        
        #calc average labour assign and save
        process.labourInput = sum(labourList)/len(labourList)
        process.save()

    def updatePowerCon(self):
        """Function To update the power value of a given process by summing all related sub-process power values"""
        #setup
        powerList = []
        CO2List = []
        #get all power values
        for subPro in self.subprocess_set.all():
            if subPro.power is not None:
                powerList.append(subPro.power)
            if subPro.CO2 is not None:
                CO2List.append(subPro.CO2)
        
        #calc average and assign
        self.power = sum(powerList)
        self.CO2 = sum(CO2List)
        self.save()
        
        
    def updateProcessCosts(self):
        """Function to update costs associated with process's"""
        #Initialisation
        totalTechLabour = timedelta()
        totalSuperLabour = timedelta()
        totalTechLabourCost = 0
        totalSuperLabourCost = 0
        totalLabourCost = 0
        totalPowerCost = 0
        totalProcessCost = 0
        totalMaterialCost = 0
        totalScrapCost = 0
        totalPartCost = 0
        
        #for each subprocess in process subprocess set
        for subProcess in self.subprocess_set.all():
            #cumulatively adding all subprocess cost data
            totalTechLabour += subProcess.technicianLabour
            totalSuperLabour += subProcess.supervisorLabour
            totalTechLabourCost += subProcess.technicianLabourCost
            totalSuperLabourCost += subProcess.supervisorLabourCost
            totalLabourCost += subProcess.labourSumCost
            totalPowerCost += subProcess.powerCost

            if subProcess.processCheck:
                totalProcessCost += subProcess.totalCost
        
        #if final inspection exists run this
            if subProcess.weighPoint:
                SubProcessWeights.objects.create(subProPart=subProcess, weight= float(subProcess.preTrimWeight))

            if subProcess.finalWeighPoint:
                if subProcess.process.project.manual:
                    finalInspection = self.subprocess_set.get(name=subProcess.manualName)
                else:
                    finalInspection = self.subprocess_set.get(name=subProcess.name)
                subProQuery = self.order_subprocess_custom()
                subProQuery = subProQuery.order_by('-position') 
                for value in subProQuery:
                    if value.weighPoint:
                        finalInspection.preTrimWeight = value.preTrimWeight
                        break

                #if post trim weight and pre trim weight have been defined
                if (finalInspection.postTrimWeight is not None) and (finalInspection.preTrimWeight is not None):
                    #calculations for finding material costs
                    self.materialWastageCost = float(finalInspection.preTrimWeight - finalInspection.postTrimWeight) * float(self.project.priceKG) 
                    self.materialPartCost = float(finalInspection.postTrimWeight) * float(self.project.priceKG)
                    self.materialWastage = float(finalInspection.preTrimWeight - finalInspection.postTrimWeight)
                    self.materialPart = float(finalInspection.postTrimWeight)
                    if len(self.project.part_set.all()) != 0:
                        self.materialScrap = self.project.badPartCounter/len(self.project.part_set.all())* 100
                        if self.materialWastage != 0 and self.materialScrap != 0:
                            self.materialScrapCost = float(self.materialWastageCost) / float(self.materialWastage) * (1+float(self.materialWastage)*(1+float(self.materialScrap)))
                        else:
                            self.materialScrapCost = 0
                    else:
                        self.materialScrapCost = 0
                    self.materialSumCost = float(self.materialPartCost) + float(self.materialWastageCost) + float(self.materialScrapCost) 
                    self.save()
                    #assigning final inspection costs 
                    finalInspection.materialWastage = self.materialWastage
                    finalInspection.materialPart = self.materialPart
                    finalInspection.materialScrap = self.materialScrap
                    finalInspection.materialWastageCost = self.materialWastageCost 
                    finalInspection.materialPartCost = self.materialPartCost
                    finalInspection.materialScrapCost = self.materialScrapCost
                    finalInspection.materialSumCost = self.materialSumCost
                    finalInspection.save()
                    finalInspection.updateSubCosts()

        #process costs defined here from subprocess costs
        self.technicianLabour = totalTechLabour
        self.supervisorLabour = totalSuperLabour
        self.technicianLabourCost = totalTechLabourCost
        self.supervisorLabourCost = totalSuperLabourCost
        self.labourSumCost = totalLabourCost
        self.powerCost = totalPowerCost
        self.processCost = totalProcessCost
        self.totalCost = float(self.powerCost) + float(self.labourSumCost) + float(self.materialSumCost)


        if self.totalCost == 0 or self.cycleTime.total_seconds() == 0:
            self.cycleCostRatio = 0
        else:
            self.cycleCostRatio = float(self.totalCost)/float(self.cycleTime.total_seconds()/24*60*60)

        self.save()

    def order_subprocess(self): #ordering all subprocess in this sequential order
        subprocessSet = self.subprocess_set.all()    
        
        return subprocessSet.order_by( Case( 
                                When ( name ="Initialisation", then=Value(0) ),
                                When ( name ="Heat Mould and Platten Up", then=Value(1)  ),
                                When ( name ="Blank Loaded in Machine", then=Value(2) ),
                                When ( name ="Temperature Reached and Platten Down", then=Value(3) ),
                                When ( name ="Blank Inside Press", then=Value(4) ),
                                When ( name ="Blank Pressed", then=Value(5) ),
                                When ( name ="Mould Cooling", then=Value(6) ),
                                When ( name ="Part Released from Mould", then=Value(7) ),
                                When ( name ="Machine Returns to Home Location", then=Value(8) ),
                                When ( name ="Preform leaves Tool", then=Value(9) ),
                                When ( name ="Part Leaves Machine", then=Value(10) ),
                                When ( manualName ="Initialisation", then=Value(5) ),
                                When ( manualName ="Material loaded in female tool", then=Value(1)  ),
                                When ( manualName ="Male Tool Lifted In Position", then=Value(2) ),
                                When ( manualName ="Lower Male Tool to create Preform", then=Value(3) ),
                                When ( manualName ="Remove Male Tool", then=Value(4) ),
                                When ( manualName ="Release Preform from Female Tool", then=Value(5) ),
                                default = Value(0)
                                    )
                                )

    def order_subprocess_custom(self):
        subprocessSet = self.subprocess_set.all() 
        return subprocessSet.order_by( Case( 
                                When ( position = 0, then=Value(0) ),
                                When ( position = 1, then=Value(1)  ),
                                When ( position = 2,then=Value(2)  ),
                                When ( position = 3, then=Value(3) ),
                                When ( position = 4, then=Value(4) ),
                                When ( position = 5, then=Value(5) ),
                                When ( position = 6, then=Value(6) ),
                                When ( position = 7, then=Value(7) ),
                                When ( position = 8, then=Value(8) ),
                                When ( position = 9, then=Value(9) ),
                                When ( position = 10, then=Value(10) ),
                                )
        )

    def update_subprocess_positions(self):
        count = 0
        for each in self.order_subprocess():
            if each.position == None and self.project.editStatus != 0:
                each.position = count
                each.save()
            elif self.project.editStatus == 0:
                each.position = count
                each.save()
            count+=1
        for every in self.order_subprocess_custom():
            if every.position == 0 and every.process.initialised is False:
                every.startPoint = True
                every.endPoint = False
            elif every.position == len(self.order_subprocess_custom())-1:
                every.endPoint = True
                every.startPoint = False
            elif every.position == 1 and every.process.initialised is True:
                every.startPoint = True 
                every.endPoint = False
            else:
                every.startPoint = False
                every.endPoint = False
            every.save()
                                

    def __str__(self):
        if self.project.manual:
            return self.manualName
        else:
            return self.name

    class Meta:
        permissions = [
            ('edit_process', 'create or delete process')
        ]

class PossibleSubProcesses(models.Model):
    name = models.CharField(max_length=50)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class SubProcess(models.Model):
    """Model to represent a manufacturing sub process"""

    #--Choices--#
    SUB_PROCESS_CHOICES = [
        ('init', 'Initialisation'),
        ('heat_mould_and_platten_up', 'Heat Mould and Platten Up'),
        ('blank_loaded_in_machine', 'Blank Loaded in Machine'),
        ('temperature_reached_and_platten_down' , 'Temperature Reached and Platten Down'),
        ('blank_inside_press', 'Blank Inside Press'),
        ('blank_pressed', 'Blank Pressed'),
        ('mould_cooling', 'Mould Cooling'),
        ('part_released_from_mould', 'Part Released from Mould'),
        ('machine_init', 'Machine Returns To Home Location'),
        ('remover_on', 'Removal End effector actuated'),
        ('pre_form_gone', 'Preform Leaves Tool'),
    ]
    
    sub_process_dict = {
        'init' : 'Initialisation',
        'heat_mould_and_platten_up': 'Heat Mould and Platten Up',
        'blank_loaded_in_machine': 'Blank Loaded in Machine',
        'temperature_reached_and_platten_down' : 'Temperature Reached and Platten Down',
        'platten_init' : 'Platten at initial location',
        'material_tool_in_press' : 'Material and Tool Inside Press',
        'material_pressed' : 'Material Pressed',
        'material_released' : 'Material Released from Tool',
        'machine_init' : 'Machine Returns To Initial Locations',
        'remover_on' : 'Removal End effector actuated',
        'pre_form_gone' : 'Preform leaves Tool',
    }

    MANUAL_SUB_PROCESS_CHOICES = [
        ('init', 'Initialisation'),
        ('material_loaded', 'Material loaded in female tool'),
        ('material_tool', 'Male Tool Lifted In Position'),
        ('material_pressed', 'Lower Male Tool to create Preform'),
        ('remover_on', 'Remove Male Tool'),
        ('material_released', 'Release Preform from Female Tool'),
    ]
    manual_sub_process_dict = {
        'init' : 'Initialisation',
        'material_loaded' : 'Material loaded in female tool',
        'material_tool' : 'Male Tool Lifted In Position',
        'material_pressed' : 'Lower Male Tool to create Preform',
        'remover_on': 'Remove Male Tool',
        'material_released' : 'Release Preform from Female Tool',
    }
    
    
    MANUAL_INPUT_CHOICES = [
        ('LAB','    Labour Input'),
        ('SCR','    Scrap Rate'),
        ('BAT','    Batch Size'),
        ('POR','    Power Consumption'),
    ]
    manual_input_dict = {
        'LAB' : 'labourInput',
        'SCR' : 'scrapRate',
        'BAT' : 'batchSize',
        'POR' : 'power',
    }

    MANUAL_INPUT_TIME_CHOICES = [
        ('JBS','    Job Start Time'),
        ('JBE','    Job End Time'),
    ]

    manual_input_time_dict = {
        'JBS' : 'jobStart',
        'JBE' : 'jobEnd',
    }

    MATERIAL_IN_PRESS_CHOICES = [
        ('CPT', 'Centre Position at tension frame'),
        ('CPMT', 'Centre position at male tool'),
        ('T', 'Tolerance'),
    ]

    material_in_press_dict = {
        'CPT':'centrePosT',
        'CPMT': 'centrePosMT',
        'T': 'tolerance',
    }

    MATERIAL_PRESSED_CHOICES = [
        ('TEMP', 'Temperature'),
        ('PR', 'Pressure'),
        ('TI', 'Time'),
    ]

    material_pressed_dict = {
        'TEMP': 'temperature',
        'PR': 'pressure',
        'TI': 'time',
    }

    REMOVAL_EFFECTOR_CHOICES = [
        ('VP', 'Vertical position of end effector'),
        ('x2', 'Tolerance'),
    ]

    removal_effector_dict = {
        'VP': 'verticalEffector',
        'PR': 'tolerancex2',
    }

    TRIMMING_CHOICES = [
    
        ('AT', 'Actual Thickness'),
        ('PRW', 'Actual Pre Trim Weight'),
        ('POW', 'Actual Post Trim Weight'),
        ('ACW', 'Actual Width'),
        ('AL', 'Actual Length'),
    ]

    trimming_dict = {
    
        'AT':'actualThickness',
        'PRW':'preTrimWeight',
        'POW':'postTrimWeight',
        'ACW':'actualWidth',
        'AL':'actualLength',

    }
    
    PLY_LIST = [
        'Cut Ply',
        'Blank Placed',
        'Blank Waiting',
        'Blank Removed',
        'Pickup Initial Ply',
        'Pickup Ply & Weld',
    ]

    CONSOLIDATION_LIST = [
        'Weld',
        'Blank Pressed',
    ]

    BLANKS_LIST = [
        'Unload Blank',
        'Lay Bottom Casette',
        'Lay Blank',
        'Lay Top Casette',
        'Initialisation',
        'Heat Mould and Platten up',
        'Blank Loaden in Machine',
        'Temperature Reached and Platten Down',
        'Blank Inside Press',
        'Blank Pressed',
        'Load',
        'Heating',
        'Unload',
    ]

    PART_LIST = [
        'Mould Cooling',
        'Part Released from Mould',
        'Machine Returns To Home Location',
        'Removal End effector actuated',
        'Part Leaves Machine',
        'Preform leaves Tool',
        'Mould moves to loading',
        'Inserts Heated',
        'Mould loaded',
        'Mould moves into press',
    ]

    PROCESS_TASK_LIST = [
        'Cut Ply',
        'Pickup Ply & Weld',
        'Heating',
        'Material Pressed',
        'Mould loaded',
        'Trim',
    ]

    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    plyCutter = models.ForeignKey(Machine,  related_name='sub_plyCutter', on_delete=models.CASCADE, null=True)
    sortPickAndPlace = models.ForeignKey(Machine, related_name='sub_sortPickAndPlace',on_delete=models.CASCADE, null=True)
    blanksPickAndPlace = models.ForeignKey(Machine,related_name='sub_blanksPickAndPlace', on_delete=models.CASCADE, null=True)
    preformCell = models.ForeignKey(Machine,related_name='sub_preformCell', on_delete=models.CASCADE, null=True)

    name = models.CharField(max_length=50, null=True)
    manualName = models.CharField(max_length=50,  null=True)

    repeat = models.BooleanField(default = False)
    operator = models.CharField(max_length=50, null=True)
    labourInput = models.IntegerField(default=0, validators=[MaxValueValidator(100), MinValueValidator(0)])
    processTime = models.DurationField(null=True, default=timedelta())
    jobStart = models.DateTimeField(null=True, default=None)
    jobEnd = models.DateTimeField(null=True, default=None)
    date = models.DateTimeField(null=True, default=None)
    position = models.IntegerField(null = True)
    startPoint = models.BooleanField(default=False)
    endPoint = models.BooleanField(default=False)
    interfaceTime = models.DurationField(null=True, default=timedelta())
    badPart = models.BooleanField(default=False)
    scrapRate = models.DecimalField(max_digits=3, decimal_places=0, default=0)
    batchSize = models.DecimalField(max_digits=50, decimal_places=0, default=4)
    power = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    status = models.IntegerField(default=0)
    processCheck = models.BooleanField(default=False, null=True)
    qualityCheck = models.BooleanField(default=False, null=True)
    CO2 = models.DecimalField(max_digits=50, decimal_places=5, default=0)
    cycleCostRatio = models.DecimalField(max_digits=50, decimal_places=3, default=0)
    preSubCost = models.DecimalField(max_digits=50, decimal_places=3, default=0)

    wastedTime = models.DurationField(default=timedelta())  
    criterion = models.CharField(max_length=800, null=True)

    #Edge detection fields
    image = models.ImageField(upload_to='images', null=True)
    file = models.FileField(upload_to='files', null=True)

    
    #Sub-Process specific fields

    #--Final Inspection--#

    weighPoint = models.BooleanField(default=False)
    finalWeighPoint = models.BooleanField(default=False)
    postTrimWeight = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    preTrimWeight = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    actualThickness = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    actualWidth = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    actualLength = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    #--Material and tool inside press--#
    centrePosT =models.DecimalField(max_digits=10, decimal_places=3, default=0)
    centrePosMT=models.DecimalField(max_digits=10, decimal_places=3, default=0)
    tolerance=models.DecimalField(max_digits=10, decimal_places=3, default=0)
    
    #--Material Pressed--#
    temperature = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    time = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    pressure = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    #--Removal End Effector is actuated--#
    verticalEffector = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    tolerancex2 = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    #Cost Breakdown

    #--Material--#
    materialWastage = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialScrap = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialPart = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialWastageCost = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    materialScrapCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialPartCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialSumCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    #--Labour--#
    technicianLabour = models.DurationField(null=True, default=timedelta())
    supervisorLabour = models.DurationField(null=True, default=timedelta())
    technicianLabourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    supervisorLabourCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    labourSumCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    #--Utility--#
    powerCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    #--TotalCost--#
    totalCost = models.DecimalField(max_digits=10, decimal_places=3, default = 0)

    partInstance = models.IntegerField(default=None, null = True)
    blankInstance = models.IntegerField(default=None, null= True)
    plyInstance = models.IntegerField(default=None, null= True)

    partTask = models.BooleanField(default=False)
    blankTask = models.BooleanField(default=False)
    plyTask = models.BooleanField(default=False)
    consolidationCheck = models.BooleanField(default=False)

    materialDensity = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    plySurfaceArea = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    totalSurfaceArea = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    plyPerimeter = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    totalSumOfPerimeter = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    totalSurfaceArea = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    totalOffcutArea = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    powerUsage = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialRateArea = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialRateWeight = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    materialDensity = models.DecimalField(max_digits=10, decimal_places=3, default = 0)
    blankArea = models.DecimalField(max_digits=10, decimal_places=3, default = 0)


    
    def updateSubCO2(self):
        #sub process CO2 calculation
        self.CO2 = float(self.power)*float(self.process.project.CO2PerPower)
        self.save()
    
    def updateSubCosts(self):
        """Function to update costs associated with sub process's"""
        self.updateSubIntervals()
        #error handling for float divison by zero
        #finding labour costs
        if self.technicianLabour.total_seconds() == 0 or self.process.project.techRate == 0:
            self.technicianLabourCost = 0
        else:
            self.technicianLabourCost = self.technicianLabour.total_seconds()/(60*60) * float(self.process.project.techRate)
            
        if self.supervisorLabour.total_seconds() == 0 or self.process.project.superRate == 0:
            self.supervisorLabourCost = 0
        else:
            self.supervisorLabourCost = self.supervisorLabour.total_seconds()/(60*60) * float(self.process.project.superRate)

        #total cost calculations
        self.materialSumCost = float(self.materialWastageCost) + float(self.materialScrapCost) + float(self.materialPartCost)
        self.labourSumCost = self.technicianLabourCost + self.supervisorLabourCost
        self.powerCost = float(self.power) * float(self.process.project.powerRate)
        self.totalCost = float(self.powerCost) + float(self.labourSumCost) + float(self.materialSumCost)
        
        if self.processCheck:
            interval = self.processTime.total_seconds()/24*60*60
        else:
            interval = self.interfaceTime.total_seconds()/24*60*60
        

        if float(self.totalCost) == 0 or float(interval) == 0:
            self.cycleCostRatio = 0
        else:
            self.cycleCostRatio = float(self.totalCost)/float(interval)
      
        self.save()
        
    def updateSubIntervals(self):
        """Function to update the sub process's interface or process times"""
        user = User.objects.get(username=self.operator)
              
        if (self.jobStart is not None) and (self.jobEnd is not None):
            #the tz replace was originally executed when input read in but did not work
            interval = self.jobEnd - self.jobStart
            if self.processCheck:
                self.processTime = interval
            else:
                self.interfaceTime = interval
            if user.groups.filter(name='Supervisor').exists():
                interval = timedelta(seconds=int((int(self.labourInput)/100) * float(interval.total_seconds())))        
                self.supervisorLabour = interval
                self.technicianLabour = timedelta() 
            else:
                interval = timedelta(seconds=int((int(self.labourInput)/100) * float(interval.total_seconds())))
                self.technicianLabour = interval
                self.supervisorLabour = timedelta()
            

            self.save()
            self.process.updateIntervals()

    def calcWastedTime(self, indexList, processPart):
        """Function to calculate the wasted time between sub processes"""
        if self.startPoint != True:
            if self.process.endPoint == True and self.endPoint==True:
                self.wastedTime = 0
            else:
                index = indexList.index(self)
                previousSub = processPart.subprocesspart_set.last()
                self.wastedTime = self.jobStart - previousSub.jobEnd    
            self.save()


    def resetAttributes(self):
        for attr in self._meta.fields:
            if attr.name == 'process' or attr.name == 'name' or attr.name == 'manualName' or attr.name == 'id' or attr.name == 'processCheck' or attr.name == "startPoint" or attr.name == "repeat" or attr.name == "criterion" or attr.name == "partTask" or attr.name == "blankTask" or attr.name == "plyTask" or attr.name == "consolidationCheck":
                pass
            elif attr.default != NOT_PROVIDED:
                setattr(self, attr.name, attr.default)
        self.save()

        for sensor in self.sensor_set.all():
            for attr in sensor._meta.fields:
                if attr.name == 'process' or attr.name == 'name' or attr.name == 'proName' or attr.name == 'id' or attr.name == 'subProcess' or attr.name == 'status':
                    pass
                elif attr.default != NOT_PROVIDED:
                    setattr(sensor, attr.name, attr.default)
            sensor.save()

            for sensortime in sensor.sensortime_set.all():
                for attr in sensortime._meta.fields:
                    if attr.name == 'sensor':
                        pass
                    elif attr.default != NOT_PROVIDED:
                        setattr(sensortime, attr.name, attr.default)
                sensortime.save()
            sensor.sensortime_set.all().delete()


    def __str__(self):
        if self.process.project.manual:
            return self.manualName
        else:
            return self.name

    def ReturnList(self):
        return self.SubProcessList

    class Meta:
        permissions = [
            ('edit_sub_process', 'create or delete sub process')
        ]


class SubProcessWeights(models.Model):
    """Model to store weights associated with SubProcessParts"""
    subProPart = models.ForeignKey(SubProcess, on_delete=models.CASCADE)
    weight = models.DecimalField(default=0, null=True, decimal_places=4, max_digits=10)


class Sensor(models.Model):
    """Model to contain all the sensors"""
    
    #--Choices--#
    PRO_SENSOR_CHOICES = [  
        ('qr_code','QR Code'),
        ('rth','RTH'),
        ('L515','L515'),
        ('D455','D455'),
        ('VOC','VOC Sensor'),
        ('DUS','Dust Sensor'),
        ('HUS','Humidity Sensor'),
        ('accelerometer', 'Accelerometer'),
        ('strain_gauge', 'Strain Gauge'),
        ('microphone', 'Microphone'),
        ('thermocouple', 'Thermocouple'),
        ('power_clamp-big_oven', 'Power Clamp (Big Oven)'),
        ('power_clamp-big_cabinet', 'Power Clamp (Big Cabinet)'),
        ('power_clamp-kuka_robot', 'Power Clamp (Kuka Robot)'),
        ('power_clamp-cnc_router', 'Power Clamp (CNC Router)'),


    ]
    pro_sensor_choices_dict = {
        'qr_code':'QR Code',
        'rth':'RTH',
        'L515':'L515',
        'D455':'D455',
        'VOC':'VOC Sensor',
        'DUS':'Dust Sensor',
        'HUS':'Humidity Sensor',
        'accelerometer': 'Accelerometer',
        'strain_gauge': 'Strain Gauge',
        'microphone':'Microphone',
        'thermocouple':'Thermocouple',
        'power_clamp-big_oven':'Power Clamp (Big Oven)',
        'power_clamp-big_cabinet':'Power Clamp (Big Cabinet)',
        'power_clamp-kuka_robot':'Power Clamp (Kuka Robot)',
        'power_clamp-cnc_router':'Power Clamp (CNC Router)',

    }

    SENSOR_CHOICES = [
        ('L515','L515'),
        ('D455','D455'),
        ('thermocouple', 'Thermocouple'),
        ('timer', 'Timer'),
        ('loc_sw', 'Location Switch'),
        ('accelerometer', 'Accelerometer'),
        ('motor', 'Motor Driver'),
        ('microphone', 'Microphone'),
        ('encoder','Encoder'),
        ('pistons_loc','Pistons Location Switch'),
        ('ultrasonic','Ultrasonic Sensor'),
        ('strain_gauge', 'Strain Gauge'),
        ('scale','Scale'),
        ('pressure','Pressure Sensor'),
        ('robot_signal', 'Robot Signal'),
        ('code_trigger', 'Code Trigger'),

    ]
    sensor_choices_dict = {
        'L515':'L515',
        'D455':'D455',
        'thermocouple':'Thermocouple',
        'timer':'Timer',
        'loc_sw':'Location Switch',
        'accelerometer':'Accelerometer',
        'motor':'Motor Driver',
        'microphone':'Microphone',
        'encoder':'Encoder',
        'pistons':'Pistons',
        'pistons_loc':'Pistons Location Switch',
        'ultrasonic':'Ultrasonic Sensor',
        'strain_gauge':'Strain Gauge',
        'scale':'Scale',
        'pressure' : 'Pressure Sensor',
        'robot_signal': 'Robot Signal',
        'code_trigger': 'Code Trigger',
    }

    # standard values
    name = models.CharField(max_length=50, null=True)
    proName = models.CharField(max_length=50, null=True)
    status = models.IntegerField(default=0)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null=True)
    sub_process = models.ForeignKey(SubProcess, on_delete=models.CASCADE, null=True)

    averageEnergyTime = models.IntegerField(default=5)
    averageTime = models.IntegerField(default=5)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, null=True)
    

    temperatureReached = models.BooleanField(default = False)
    tempReachedTime = models.CharField(null = True, max_length=50)
    pressureReached = models.BooleanField(default = False)
    pressureReachedTime = models.CharField(null = True, max_length=50)
    # bounds
    maxTemp = models.IntegerField(default=10, null=True)
    minTemp = models.IntegerField(default=0, null=True)
    maxPressure = models.IntegerField(default=0, null=True)
    minPressure = models.IntegerField(default=10, null=True)
    maxVOC = models.IntegerField(default=10, null=True)
    minVOC = models.IntegerField(default=0, null=True)
    maxHumid = models.IntegerField(default= 10, null=True)
    minHumid = models.IntegerField(default = 0, null = True)
    maxDust = models.IntegerField(default= 10, null=True)
    minDust = models.IntegerField(default = 0, null = True)
    maxNoise = models.IntegerField(default = 0, null = True)
    minNoise = models.IntegerField(default = 0, null = True)
    maxTorque = models.IntegerField(default = 0, null = True)
    minTorque = models.IntegerField(default = 0, null = True)
    minAccel = models.IntegerField(default = 0, null = True)
    maxAccel = models.IntegerField(default = 0, null = True)
    tolerance = models.IntegerField(default=10, null=True)
    # non-time dependant
    distance = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    posCheck = models.BooleanField(default=False, null=True)
    actualWeight = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    finalWeight = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    thickness = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    partPresent = models.BooleanField(default=False, null=True)
    partDimX = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    partDimY = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    encoderPos = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    timerCheck = models.BooleanField(default=False, null=True)
    # Service info NO RESET!
    serviceDate = models.DateTimeField(null=True)
    contactNum = PhoneNumberField(null=True, unique=True)
    dateInstalled = models.DateTimeField(null=True)
    modelID = models.CharField(max_length=50, null=True)
    warrentExp = models.DateTimeField(null=True)
    
    def __str__(self):
        return self.name


class SensorTime(models.Model):
    """Model to store time data for a given sensor"""
    # standard values
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    # timedependant
    temp = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    distance = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    pressure = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    noise = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    energy = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    VOC = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    dust = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    humidity = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    torque = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    acceleration = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    time = models.DateTimeField(default=None)


class PartInstance(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null = True)
    instance_id = models.IntegerField(primary_key=True, default=1)

    def __str__(self):
        return str(self.instance_id)

class BlankInstance(models.Model):
    """Model to contain an instance of a Ply"""
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null = True)
    instance_id = models.IntegerField(primary_key=True, default=1)

    def __str__(self):
        return str(self.instance_id)

class PlyInstance(models.Model):
    """Model to contain an instance of a Ply"""
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null = True)
    instance_id = models.IntegerField(primary_key=True, default=1)

    def __str__(self):
        return str(self.instance_id)
        
class TiaBlocks(models.Model):

    name = models.CharField(max_length=50)
    project = models.ManyToManyField(Project)
    subProcess = models.ManyToManyField(SubProcess)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name

class PossibleSensors(models.Model):
    name = models.CharField(max_length=50)
    process = models.ForeignKey(Process,on_delete=models.CASCADE, null = True)
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, null=True)
    modelID = models.CharField(max_length=50, null = True)

    def __str__(self):
        return self.name

class RepeatBlock(models.Model):
    iteration = models.IntegerField(null=True)
    number_of_iterations = models.IntegerField(null=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null = True)
    finished = models.BooleanField(default = False)

class RepeatBlockSubProcesses(models.Model):
    sub_process = models.ForeignKey(SubProcess, on_delete = models.CASCADE, null = True)
    repeat_block = models.ForeignKey(RepeatBlock, on_delete = models.CASCADE, null = True) 
    start = models.BooleanField(default = False)
    end = models.BooleanField(default = False)
        

#CUSTOM ERRORS

class Error(Exception):
    """Base error class"""
    pass
    
class TimeAttributeIsNone(Error):
    """Error for if submitted part is missing attributes"""
    pass

class InstanceQueue(models.Model):
    instance_id = models.IntegerField(null=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null = True)

class ERP_Schedule(models.Model):
    task_name = models.CharField(null=True, max_length=20)
    date_of_execution = models.DateField(null=True)
    time_of_execution = models.CharField(null=True, max_length=20)
    changed = models.BooleanField(null=True)
    run_task = models.CharField(null=True, max_length=50)


from django.db import models
from django.utils import timezone

class SensorDataStorage(models.Model):
    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Power Consumption
    big_cabinet_power = models.FloatField(
        verbose_name="Big Cabinet Power Consumption",
        help_text="Power consumption in kWh",
        null=True, blank=True
    )
    kuka_cabinet_power = models.FloatField(
        verbose_name="KUKA Cabinet Power Consumption",
        help_text="Power consumption in kWh",
        null=True, blank=True
    )
    cnc_router_power = models.FloatField(
        verbose_name="CNC Router Power Consumption",
        help_text="Power consumption in kWh",
        null=True, blank=True
    )
    big_oven_power = models.FloatField(
        verbose_name="Big Oven Power Consumption",
        help_text="Power consumption in kWh",
        null=True, blank=True
    )
    total_power = models.FloatField(
        verbose_name="Total Power Consumption",
        help_text="Total power consumption across all devices in kWh",
        null=True, blank=True
    )
    average_power = models.FloatField(
        verbose_name="Average Power Consumption",
        help_text="Average power consumption across active devices in kWh",
        null=True, blank=True
    )

    # Air Quality Sensors
    pm1_concentration = models.FloatField(
        verbose_name="PM1.0 Concentration",
        help_text="Mass concentration of particles < 1.0 μm (μg/m³)",
        null=True, blank=True
    )
    pm25_concentration = models.FloatField(
        verbose_name="PM2.5 Concentration",
        help_text="Mass concentration of particles < 2.5 μm (μg/m³)",
        null=True, blank=True
    )
    pm10_concentration = models.FloatField(
        verbose_name="PM10 Concentration",
        help_text="Mass concentration of particles < 10 μm (μg/m³)",
        null=True, blank=True
    )

    # Noise Sensor
    noise_level = models.FloatField(
        verbose_name="Noise Level",
        help_text="Noise measurement value in dB",
        null=True, blank=True
    )

    # Vibration Sensors
    acceleration_x = models.FloatField(
        verbose_name="X-Axis Acceleration",
        help_text="Acceleration in X axis (m/sec²)",
        null=True, blank=True
    )
    acceleration_y = models.FloatField(
        verbose_name="Y-Axis Acceleration",
        help_text="Acceleration in Y axis (m/sec²)",
        null=True, blank=True
    )
    acceleration_z = models.FloatField(
        verbose_name="Z-Axis Acceleration",
        help_text="Acceleration in Z axis (m/sec²)",
        null=True, blank=True
    )
    angular_velocity_x = models.FloatField(
        verbose_name="X-Axis Angular Velocity",
        help_text="Angular velocity in X axis (deg/sec)",
        null=True, blank=True
    )
    angular_velocity_y = models.FloatField(
        verbose_name="Y-Axis Angular Velocity",
        help_text="Angular velocity in Y axis (deg/sec)",
        null=True, blank=True
    )
    angular_velocity_z = models.FloatField(
        verbose_name="Z-Axis Angular Velocity",
        help_text="Angular velocity in Z axis (deg/sec)",
        null=True, blank=True
    )
    roll_angle = models.FloatField(
        verbose_name="Roll Angle",
        help_text="Roll angle in degrees",
        null=True, blank=True
    )
    pitch_angle = models.FloatField(
        verbose_name="Pitch Angle",
        help_text="Pitch angle in degrees",
        null=True, blank=True
    )
    yaw_angle = models.FloatField(
        verbose_name="Yaw Angle",
        help_text="Yaw angle in degrees",
        null=True, blank=True
    )

    # VOC Sensors
    temperature = models.FloatField(
        verbose_name="Temperature",
        help_text="Temperature in °C",
        null=True, blank=True
    )
    humidity = models.FloatField(
        verbose_name="Humidity",
        help_text="Humidity in rH",
        null=True, blank=True
    )
    voc_index = models.IntegerField(
        verbose_name="VOC Index",
        help_text="VOC Value in Air Quality Index",
        null=True, blank=True
    )

    # Weighing Scale
    weight = models.FloatField(
        verbose_name="Weight",
        help_text="Weight in kg",
        null=True, blank=True
    )

    # Motor Data
    motor_load_mean = models.FloatField(
        verbose_name="Motor Load Mean",
        help_text="Mean motor load value",
        null=True, blank=True
    )
    actual_torque_percentage = models.FloatField(
        verbose_name="Actual Torque Percentage",
        help_text="Actual torque percentage",
        null=True, blank=True
    )
    actual_torque_percentage2 = models.FloatField(
        verbose_name="Actual Torque Percentage 2",
        help_text="Second actual torque percentage",
        null=True, blank=True
    )

    # Temperature Monitor
    high_temp_current = models.IntegerField(
        verbose_name="High Temperature Current",
        help_text="Current high temperature value",
        null=True, blank=True
    )
    high_temp_target = models.IntegerField(
        verbose_name="High Temperature Target",
        help_text="Target high temperature value",
        null=True, blank=True
    )
    temp_match = models.BooleanField(
        verbose_name="Temperature Match",
        help_text="Whether current temperature matches target",
        default=False
    )

    # Switch Status
    platten_down = models.BooleanField(default=False)
    shuttle_home = models.BooleanField(default=False)
    platten_up = models.BooleanField(default=False)
    shuttle_press = models.BooleanField(default=False)
    timer_started = models.BooleanField(default=False)
    timer_active = models.BooleanField(default=False)
    timer_completed = models.BooleanField(default=False)
    timer_et = models.IntegerField(
        verbose_name="Timer ET",
        help_text="Timer elapsed time",
        default=0
    )
    timer_total = models.IntegerField(
        verbose_name="Timer Total",
        help_text="Timer total time",
        default=0
    )

    class Meta:
        verbose_name = "Sensor Data Storage"
        verbose_name_plural = "Sensor Data Storages"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Sensor Data at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    @classmethod
    def create_from_data(cls, sensor_data, motor_data, status_data):
        """
        Create a new SensorDataStorage instance from the provided data.
        
        Args:
            sensor_data (dict): Sensor data from ROS bridge
            motor_data (dict): Motor data from OPC UA
            status_data (dict): Status data including temperatures and switches
        """
        instance = cls(timestamp=timezone.now())

        # Process Air Quality Data
        if 'Air Quality Sensor 2' in sensor_data:
            aq_data = sensor_data['Air Quality Sensor 2']['Air Quality Sensor Values']
            instance.pm1_concentration = aq_data.get('Mass concentration in μg / m3 of particles size < 1 μm')
            instance.pm25_concentration = aq_data.get('Mass concentration in μg / m3 of particles size < 2.5 μm')
            instance.pm10_concentration = aq_data.get('Mass concentration in μg / m3 of particles size < 10 μm')

        # Process Noise Data
        if 'Noise Sensor 1' in sensor_data:
            instance.noise_level = sensor_data['Noise Sensor 1']['Noise Sensor Values'].get('Noise measurement value in dB')

        # Process Vibration Data
        if 'Vibration Sensor 1' in sensor_data:
            vib_data = sensor_data['Vibration Sensor 1']['Vibration Sensor Values']
            instance.acceleration_x = vib_data.get('Acceleration X in m/sec2')
            instance.acceleration_y = vib_data.get('Acceleration Y in m/sec2')
            instance.acceleration_z = vib_data.get('Acceleration Z in m/sec2')
            instance.angular_velocity_x = vib_data.get('Angular Velocity X in deg/sec')
            instance.angular_velocity_y = vib_data.get('Angular Velocity Y in deg/sec')
            instance.angular_velocity_z = vib_data.get('Angular Velocity Z in deg/sec')
            instance.roll_angle = vib_data.get('Roll Angle X in deg')
            instance.pitch_angle = vib_data.get('Pitch Angle Y in deg')
            instance.yaw_angle = vib_data.get('Yaw Angle Z in deg')

        # Process VOC Data
        if 'VOC Sensor 1' in sensor_data:
            voc_data = sensor_data['VOC Sensor 1']['VOC Sensor Values']
            instance.temperature = voc_data.get('Temperature Value in °C')
            instance.humidity = voc_data.get('Humidity Value in rH')
            instance.voc_index = voc_data.get('VOC Value in Air Quality Index')

        # Process Weight Data
        if 'Weighing Scale 1' in sensor_data:
            instance.weight = sensor_data['Weighing Scale 1']['Weighing Scale Values'].get('Weight in kg')

        # Process Motor Data
        if motor_data:
            instance.motor_load_mean = motor_data.get('motorLoadMean_M3')
            instance.actual_torque_percentage = motor_data.get('ActuaTorquePercentage')
            instance.actual_torque_percentage2 = motor_data.get('ActualTorquePercentage2')

        # Process Status Data
        if status_data:
            switch_status = status_data.get('Switch Status', {})
            instance.platten_down = switch_status.get('platten_down', False)
            instance.shuttle_home = switch_status.get('shuttle_home', False)
            instance.platten_up = switch_status.get('platten_up', False)
            instance.shuttle_press = switch_status.get('shuttle_press', False)
            instance.timer_started = switch_status.get('timer_started', False)
            instance.timer_active = switch_status.get('timer_active', False)
            instance.timer_completed = switch_status.get('timer_completed', False)
            instance.timer_et = switch_status.get('timer_et', 0)
            instance.timer_total = switch_status.get('timer_total', 0)

        instance.save()
        return instance