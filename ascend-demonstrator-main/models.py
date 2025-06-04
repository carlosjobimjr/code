# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class EnergycaptureCo2(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    value = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    company = models.ForeignKey('MainCompany', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EnergyCapture_co2'


class EnergycaptureEquipment(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    station = models.ForeignKey('EnergycaptureStation', models.DO_NOTHING, blank=True, null=True)
    total_power = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EnergyCapture_equipment'


class EnergycaptureEquipmenttime(models.Model):
    power = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    time = models.DateTimeField()
    id = models.BigAutoField(primary_key=True)
    equipment = models.ForeignKey(EnergycaptureEquipment, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EnergyCapture_equipmenttime'


class EnergycapturePossibledeviceid(models.Model):
    id = models.BigAutoField(primary_key=True)
    deviceid = models.CharField(db_column='deviceID', max_length=50, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'EnergyCapture_possibledeviceid'


class EnergycapturePowerclamp(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    deviceid = models.CharField(db_column='deviceID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    equipment = models.ForeignKey(EnergycaptureEquipment, models.DO_NOTHING, blank=True, null=True)
    total_power = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EnergyCapture_powerclamp'


class EnergycapturePowerclamptime(models.Model):
    power = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    time = models.DateTimeField()
    id = models.BigAutoField(primary_key=True)
    powerclamp = models.ForeignKey(EnergycapturePowerclamp, models.DO_NOTHING, db_column='powerClamp_id', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'EnergyCapture_powerclamptime'


class EnergycaptureStation(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    company = models.ForeignKey('MainCompany', models.DO_NOTHING, blank=True, null=True)
    total_power = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EnergyCapture_station'


class EnergycaptureStationtime(models.Model):
    power = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    time = models.DateTimeField()
    id = models.BigAutoField(primary_key=True)
    station = models.ForeignKey(EnergycaptureStation, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'EnergyCapture_stationtime'


class MaindataBlank(models.Model):
    blank_id = models.BigAutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    submitted = models.IntegerField()
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.DecimalField(db_column='labourInput', max_digits=5, decimal_places=2)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    processtimeperblank = models.BigIntegerField(db_column='processTimePerBlank', blank=True, null=True)  # Field name made lowercase.
    interfacetimeperblank = models.BigIntegerField(db_column='interfaceTimePerBlank', blank=True, null=True)  # Field name made lowercase.
    cycletimeperblank = models.BigIntegerField(db_column='cycleTimePerBlank', blank=True, null=True)  # Field name made lowercase.
    powerconsumptioncostperblank = models.DecimalField(db_column='powerConsumptionCostPerBlank', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    pricekg = models.IntegerField(db_column='priceKG')  # Field name made lowercase.
    pricem2 = models.IntegerField(db_column='priceM2')  # Field name made lowercase.
    co2perpower = models.DecimalField(db_column='CO2PerPower', max_digits=10, decimal_places=2)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    techrate = models.IntegerField(db_column='techRate')  # Field name made lowercase.
    superrate = models.IntegerField(db_column='superRate')  # Field name made lowercase.
    superlabourhours = models.BigIntegerField(db_column='superLabourHours', blank=True, null=True)  # Field name made lowercase.
    techlabourhours = models.BigIntegerField(db_column='techLabourHours', blank=True, null=True)  # Field name made lowercase.
    powerrate = models.IntegerField(db_column='powerRate')  # Field name made lowercase.
    setupcost = models.DecimalField(db_column='setUpCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    co2emissionsperblank = models.DecimalField(db_column='CO2EmissionsPerBlank', max_digits=50, decimal_places=3)  # Field name made lowercase.
    badpart = models.IntegerField(db_column='badPart')  # Field name made lowercase.
    materialwastageperblank = models.DecimalField(db_column='materialWastagePerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankarearatio = models.DecimalField(db_column='blankAreaRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankperimeterratio = models.DecimalField(db_column='blankPerimeterRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankscraprate = models.DecimalField(db_column='blankScrapRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapperblank = models.DecimalField(db_column='materialScrapPerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecostperblank = models.DecimalField(db_column='materialWastageCostPerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialratearea = models.DecimalField(db_column='materialRateArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialrateweight = models.DecimalField(db_column='materialRateWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourtotal = models.DecimalField(db_column='labourTotal', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialcostperblank = models.DecimalField(db_column='materialCostPerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapcostperblank = models.DecimalField(db_column='materialScrapCostPerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabourcostperblank = models.DecimalField(db_column='technicianLabourCostPerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcostperblank = models.DecimalField(db_column='supervisorLabourCostPerBlank', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourcost = models.DecimalField(db_column='labourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerusage = models.DecimalField(db_column='powerUsage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankinstance = models.ForeignKey('MainBlankinstance', models.DO_NOTHING, db_column='blankInstance_id', blank=True, null=True)  # Field name made lowercase.
    part = models.ForeignKey('MaindataPart', models.DO_NOTHING, blank=True, null=True)
    project = models.ForeignKey('MainProject', models.DO_NOTHING)
    blankperimeter = models.DecimalField(db_column='blankPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blanksurfacearea = models.DecimalField(db_column='blankSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totaloffcutarea = models.DecimalField(db_column='totalOffcutArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsumofperimeters = models.DecimalField(db_column='totalSumOfPerimeters', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsurfacearea = models.DecimalField(db_column='totalSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_blank'


class MaindataPart(models.Model):
    part_id = models.AutoField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    submitted = models.IntegerField()
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.DecimalField(db_column='labourInput', max_digits=5, decimal_places=2)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    processtimeperpart = models.BigIntegerField(db_column='processTimePerPart', blank=True, null=True)  # Field name made lowercase.
    interfacetimeperpart = models.BigIntegerField(db_column='interfaceTimePerPart', blank=True, null=True)  # Field name made lowercase.
    cycletimeperpart = models.BigIntegerField(db_column='cycleTimePerPart', blank=True, null=True)  # Field name made lowercase.
    powerconsumptioncostperpart = models.DecimalField(db_column='powerConsumptionCostPerPart', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    pricekg = models.IntegerField(db_column='priceKG')  # Field name made lowercase.
    pricem2 = models.IntegerField(db_column='priceM2')  # Field name made lowercase.
    co2perpower = models.DecimalField(db_column='CO2PerPower', max_digits=10, decimal_places=2)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    techrate = models.IntegerField(db_column='techRate')  # Field name made lowercase.
    superrate = models.IntegerField(db_column='superRate')  # Field name made lowercase.
    superlabourhours = models.BigIntegerField(db_column='superLabourHours', blank=True, null=True)  # Field name made lowercase.
    techlabourhours = models.BigIntegerField(db_column='techLabourHours', blank=True, null=True)  # Field name made lowercase.
    powerrate = models.IntegerField(db_column='powerRate')  # Field name made lowercase.
    materialcostperpart = models.DecimalField(db_column='materialCostPerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourtotal = models.DecimalField(db_column='labourTotal', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialrateweight = models.DecimalField(db_column='materialRateWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialratearea = models.DecimalField(db_column='materialRateArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastageperpart = models.DecimalField(db_column='materialWastagePerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partarearatio = models.DecimalField(db_column='partAreaRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    setupcost = models.DecimalField(db_column='setUpCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    co2emissionsperpart = models.DecimalField(db_column='CO2EmissionsPerPart', max_digits=50, decimal_places=3)  # Field name made lowercase.
    badpart = models.IntegerField(db_column='badPart')  # Field name made lowercase.
    materialscrapcostperpart = models.DecimalField(db_column='materialScrapCostPerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapperpart = models.DecimalField(db_column='materialScrapPerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecostperpart = models.DecimalField(db_column='materialWastageCostPerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerusage = models.DecimalField(db_column='powerUsage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcostperpart = models.DecimalField(db_column='supervisorLabourCostPerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partperimeterratio = models.DecimalField(db_column='partPerimeterRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partscraprate = models.DecimalField(db_column='partScrapRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabourcostperpart = models.DecimalField(db_column='technicianLabourCostPerPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourcost = models.DecimalField(db_column='labourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partinstance = models.ForeignKey('MainPartinstance', models.DO_NOTHING, db_column='partInstance_id', blank=True, null=True)  # Field name made lowercase.
    project = models.ForeignKey('MainProject', models.DO_NOTHING)
    partperimeter = models.DecimalField(db_column='partPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partsurfacearea = models.DecimalField(db_column='partSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totaloffcutarea = models.DecimalField(db_column='totalOffcutArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsumofperimeters = models.DecimalField(db_column='totalSumOfPerimeters', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsurfacearea = models.DecimalField(db_column='totalSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_part'


class MaindataPly(models.Model):
    ply_id = models.IntegerField(primary_key=True)
    date = models.DateField(blank=True, null=True)
    submitted = models.IntegerField()
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.DecimalField(db_column='labourInput', max_digits=5, decimal_places=2)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    processtimeperply = models.BigIntegerField(db_column='processTimePerPly', blank=True, null=True)  # Field name made lowercase.
    interfacetimeperply = models.BigIntegerField(db_column='interfaceTimePerPly', blank=True, null=True)  # Field name made lowercase.
    cycletimeperply = models.BigIntegerField(db_column='cycleTimePerPly', blank=True, null=True)  # Field name made lowercase.
    powerconsumptioncostperply = models.DecimalField(db_column='powerConsumptionCostPerPly', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    pricekg = models.IntegerField(db_column='priceKG')  # Field name made lowercase.
    pricem2 = models.IntegerField(db_column='priceM2')  # Field name made lowercase.
    co2perpower = models.DecimalField(db_column='CO2PerPower', max_digits=10, decimal_places=2)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    techrate = models.IntegerField(db_column='techRate')  # Field name made lowercase.
    superrate = models.IntegerField(db_column='superRate')  # Field name made lowercase.
    superlabourhours = models.BigIntegerField(db_column='superLabourHours', blank=True, null=True)  # Field name made lowercase.
    techlabourhours = models.BigIntegerField(db_column='techLabourHours', blank=True, null=True)  # Field name made lowercase.
    powerrate = models.IntegerField(db_column='powerRate')  # Field name made lowercase.
    setupcost = models.DecimalField(db_column='setUpCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    co2emissionsperply = models.DecimalField(db_column='CO2EmissionsPerPly', max_digits=50, decimal_places=3)  # Field name made lowercase.
    badpart = models.IntegerField(db_column='badPart')  # Field name made lowercase.
    plyscraprate = models.DecimalField(db_column='plyScrapRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourtotal = models.DecimalField(db_column='labourTotal', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialcostperply = models.DecimalField(db_column='materialCostPerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialratearea = models.DecimalField(db_column='materialRateArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    plyarearatio = models.DecimalField(db_column='plyAreaRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    plyperimeterratio = models.DecimalField(db_column='plyPerimeterRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapperply = models.DecimalField(db_column='materialScrapPerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecostperply = models.DecimalField(db_column='materialWastageCostPerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialrateweight = models.DecimalField(db_column='materialRateWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapcostperply = models.DecimalField(db_column='materialScrapCostPerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastageperply = models.DecimalField(db_column='materialWastagePerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabourcostperply = models.DecimalField(db_column='technicianLabourCostPerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcostperply = models.DecimalField(db_column='supervisorLabourCostPerPly', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourcost = models.DecimalField(db_column='labourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerusage = models.DecimalField(db_column='powerUsage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blank = models.ForeignKey(MaindataBlank, models.DO_NOTHING, blank=True, null=True)
    plyinst = models.ForeignKey('MainPlyinstance', models.DO_NOTHING, db_column='plyInst_id', blank=True, null=True)  # Field name made lowercase.
    project = models.ForeignKey('MainProject', models.DO_NOTHING)
    plyperimeter = models.DecimalField(db_column='plyPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    plysurfacearea = models.DecimalField(db_column='plySurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totaloffcutarea = models.DecimalField(db_column='totalOffcutArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsumofperimeters = models.DecimalField(db_column='totalSumOfPerimeters', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsurfacearea = models.DecimalField(db_column='totalSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_ply'


class MaindataProcesspart(models.Model):
    id = models.BigAutoField(primary_key=True)
    processname = models.CharField(db_column='processName', max_length=30, blank=True, null=True)  # Field name made lowercase.
    date = models.DateField(blank=True, null=True)
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.DecimalField(db_column='labourInput', max_digits=5, decimal_places=2)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    processstart = models.DateTimeField(db_column='processStart', blank=True, null=True)  # Field name made lowercase.
    processend = models.DateTimeField(db_column='processEnd', blank=True, null=True)  # Field name made lowercase.
    processtime = models.BigIntegerField(db_column='processTime', blank=True, null=True)  # Field name made lowercase.
    cycletime = models.BigIntegerField(db_column='cycleTime', blank=True, null=True)  # Field name made lowercase.
    interfacetime = models.BigIntegerField(db_column='interfaceTime', blank=True, null=True)  # Field name made lowercase.
    popupstart = models.DateTimeField(db_column='popUpStart', blank=True, null=True)  # Field name made lowercase.
    popupend = models.DateTimeField(db_column='popUpEnd', blank=True, null=True)  # Field name made lowercase.
    scraprate = models.DecimalField(db_column='scrapRate', max_digits=3, decimal_places=0)  # Field name made lowercase.
    minbatchsize = models.DecimalField(db_column='minBatchSize', max_digits=50, decimal_places=0)  # Field name made lowercase.
    maxbatchsize = models.DecimalField(db_column='maxBatchSize', max_digits=50, decimal_places=0)  # Field name made lowercase.
    power = models.DecimalField(max_digits=10, decimal_places=3)
    status = models.IntegerField()
    processcheck = models.IntegerField(db_column='processCheck', blank=True, null=True)  # Field name made lowercase.
    qualitycheck = models.IntegerField(db_column='qualityCheck', blank=True, null=True)  # Field name made lowercase.
    cyclecostratio = models.DecimalField(db_column='cycleCostRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    posttrimweight = models.DecimalField(db_column='postTrimWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    pretrimweight = models.DecimalField(db_column='preTrimWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    wastedtime = models.BigIntegerField(db_column='wastedTime', blank=True, null=True)  # Field name made lowercase.
    co2 = models.DecimalField(db_column='CO2', max_digits=50, decimal_places=3)  # Field name made lowercase.
    materialwastage = models.DecimalField(db_column='materialWastage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrap = models.DecimalField(db_column='materialScrap', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpart = models.DecimalField(db_column='materialPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecost = models.DecimalField(db_column='materialWastageCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapcost = models.DecimalField(db_column='materialScrapCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpartcost = models.DecimalField(db_column='materialPartCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialsumcost = models.DecimalField(db_column='materialSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabour = models.BigIntegerField(db_column='technicianLabour')  # Field name made lowercase.
    supervisorlabour = models.BigIntegerField(db_column='supervisorLabour')  # Field name made lowercase.
    technicianlabourcost = models.DecimalField(db_column='technicianLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcost = models.DecimalField(db_column='supervisorLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    laboursumcost = models.DecimalField(db_column='labourSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powercost = models.DecimalField(db_column='powerCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerrate = models.DecimalField(db_column='powerRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blank = models.ForeignKey(MaindataBlank, models.DO_NOTHING, blank=True, null=True)
    blankspickandplace = models.ForeignKey('MainMachine', models.DO_NOTHING, db_column='blanksPickAndPlace_id', blank=True, null=True)  # Field name made lowercase.
    part = models.ForeignKey(MaindataPart, models.DO_NOTHING, blank=True, null=True)
    ply = models.ForeignKey(MaindataPly, models.DO_NOTHING, blank=True, null=True)
    plycutter = models.ForeignKey('MainMachine', models.DO_NOTHING, db_column='plyCutter_id', related_name='maindataprocesspart_plycutter_set', blank=True, null=True)  # Field name made lowercase.
    preformcell = models.ForeignKey('MainMachine', models.DO_NOTHING, db_column='preformCell_id', related_name='maindataprocesspart_preformcell_set', blank=True, null=True)  # Field name made lowercase.
    sortpickandplace = models.ForeignKey('MainMachine', models.DO_NOTHING, db_column='sortPickAndPlace_id', related_name='maindataprocesspart_sortpickandplace_set', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_processpart'


class MaindataSensordata(models.Model):
    id = models.BigAutoField(primary_key=True)
    sensorname = models.CharField(db_column='sensorName', max_length=30, blank=True, null=True)  # Field name made lowercase.
    status = models.IntegerField()
    maxtemp = models.IntegerField(db_column='maxTemp', blank=True, null=True)  # Field name made lowercase.
    mintemp = models.IntegerField(db_column='minTemp', blank=True, null=True)  # Field name made lowercase.
    maxpressure = models.IntegerField(db_column='maxPressure', blank=True, null=True)  # Field name made lowercase.
    minpressure = models.IntegerField(db_column='minPressure', blank=True, null=True)  # Field name made lowercase.
    distance = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    poscheck = models.IntegerField(db_column='posCheck', blank=True, null=True)  # Field name made lowercase.
    actualweight = models.DecimalField(db_column='actualWeight', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    thickness = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    partpresent = models.IntegerField(db_column='partPresent', blank=True, null=True)  # Field name made lowercase.
    partdimx = models.DecimalField(db_column='partDimX', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    partdimy = models.DecimalField(db_column='partDimY', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    encoderpos = models.DecimalField(db_column='encoderPos', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    timercheck = models.IntegerField(db_column='timerCheck', blank=True, null=True)  # Field name made lowercase.
    servicedate = models.DateTimeField(db_column='serviceDate', blank=True, null=True)  # Field name made lowercase.
    contactnum = models.CharField(db_column='contactNum', unique=True, max_length=128, blank=True, null=True)  # Field name made lowercase.
    dateinstalled = models.DateTimeField(db_column='dateInstalled', blank=True, null=True)  # Field name made lowercase.
    modelid = models.CharField(db_column='modelID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    warrentexp = models.DateTimeField(db_column='warrentExp', blank=True, null=True)  # Field name made lowercase.
    processpart = models.ForeignKey(MaindataProcesspart, models.DO_NOTHING, db_column='processPart_id', blank=True, null=True)  # Field name made lowercase.
    subprocesspart = models.ForeignKey('MaindataSubprocesspart', models.DO_NOTHING, db_column='subProcessPart_id', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_sensordata'


class MaindataSensortimedata(models.Model):
    id = models.BigAutoField(primary_key=True)
    time = models.DateTimeField(blank=True, null=True)
    temp = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    pressure = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    noise = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    energy = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    voc = models.DecimalField(db_column='VOC', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    dust = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    torque = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    acceleration = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    sensordata = models.ForeignKey(MaindataSensordata, models.DO_NOTHING, db_column='sensorData_id', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_sensortimedata'


class MaindataSubprocesspart(models.Model):
    id = models.BigAutoField(primary_key=True)
    subprocessname = models.CharField(db_column='subProcessName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    date = models.DateField(blank=True, null=True)
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.DecimalField(db_column='labourInput', max_digits=5, decimal_places=2)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    prointtime = models.BigIntegerField(db_column='proIntTime', blank=True, null=True)  # Field name made lowercase.
    processtime = models.BigIntegerField(db_column='processTime', blank=True, null=True)  # Field name made lowercase.
    interfacetime = models.BigIntegerField(db_column='interfaceTime', blank=True, null=True)  # Field name made lowercase.
    cycletime = models.BigIntegerField(db_column='cycleTime', blank=True, null=True)  # Field name made lowercase.
    popupstart = models.DateTimeField(db_column='popUpStart', blank=True, null=True)  # Field name made lowercase.
    popupend = models.DateTimeField(db_column='popUpEnd', blank=True, null=True)  # Field name made lowercase.
    scraprate = models.DecimalField(db_column='scrapRate', max_digits=3, decimal_places=0)  # Field name made lowercase.
    batchsize = models.DecimalField(db_column='batchSize', max_digits=50, decimal_places=0)  # Field name made lowercase.
    power = models.DecimalField(max_digits=10, decimal_places=3)
    status = models.IntegerField()
    processcheck = models.IntegerField(db_column='processCheck', blank=True, null=True)  # Field name made lowercase.
    qualitycheck = models.IntegerField(db_column='qualityCheck', blank=True, null=True)  # Field name made lowercase.
    pretrimweight = models.DecimalField(db_column='preTrimWeight', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    posttrimweight = models.DecimalField(db_column='postTrimWeight', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    wastedtime = models.BigIntegerField(db_column='wastedTime', blank=True, null=True)  # Field name made lowercase.
    co2 = models.DecimalField(db_column='CO2', max_digits=50, decimal_places=3)  # Field name made lowercase.
    weighpoint = models.IntegerField(db_column='weighPoint')  # Field name made lowercase.
    finalweighpoint = models.IntegerField(db_column='finalWeighPoint')  # Field name made lowercase.
    image = models.CharField(max_length=100, blank=True, null=True)
    file = models.CharField(max_length=100, blank=True, null=True)
    position = models.IntegerField(blank=True, null=True)
    materialwastage = models.DecimalField(db_column='materialWastage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrap = models.DecimalField(db_column='materialScrap', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpart = models.DecimalField(db_column='materialPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecost = models.DecimalField(db_column='materialWastageCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapcost = models.DecimalField(db_column='materialScrapCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpartcost = models.DecimalField(db_column='materialPartCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialsumcost = models.DecimalField(db_column='materialSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabour = models.BigIntegerField(db_column='technicianLabour', blank=True, null=True)  # Field name made lowercase.
    supervisorlabour = models.BigIntegerField(db_column='supervisorLabour', blank=True, null=True)  # Field name made lowercase.
    technicianlabourcost = models.DecimalField(db_column='technicianLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcost = models.DecimalField(db_column='supervisorLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    laboursumcost = models.DecimalField(db_column='labourSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powercost = models.DecimalField(db_column='powerCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerrate = models.DecimalField(db_column='powerRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partinstance = models.IntegerField(db_column='partInstance', blank=True, null=True)  # Field name made lowercase.
    blankinstance = models.IntegerField(db_column='blankInstance', blank=True, null=True)  # Field name made lowercase.
    plyinstance = models.IntegerField(db_column='plyInstance', blank=True, null=True)  # Field name made lowercase.
    parttask = models.IntegerField(db_column='partTask')  # Field name made lowercase.
    blanktask = models.IntegerField(db_column='blankTask')  # Field name made lowercase.
    plytask = models.IntegerField(db_column='plyTask')  # Field name made lowercase.
    consolidationcheck = models.IntegerField(db_column='consolidationCheck')  # Field name made lowercase.
    cycletimeratio = models.DecimalField(db_column='cycleTimeRatio', max_digits=10, decimal_places=3)  # Field name made lowercase.
    plysurfacearea = models.DecimalField(db_column='plySurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    plyperimeter = models.DecimalField(db_column='plyPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsumofperimeter = models.DecimalField(db_column='totalSumOfPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsurfacearea = models.DecimalField(db_column='totalSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totaloffcutarea = models.DecimalField(db_column='totalOffcutArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerusage = models.DecimalField(db_column='powerUsage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialratearea = models.DecimalField(db_column='materialRateArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialrateweight = models.DecimalField(db_column='materialRateWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankarea = models.DecimalField(db_column='blankArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blank = models.ForeignKey(MaindataBlank, models.DO_NOTHING, blank=True, null=True)
    part = models.ForeignKey(MaindataPart, models.DO_NOTHING, blank=True, null=True)
    ply = models.ForeignKey(MaindataPly, models.DO_NOTHING, blank=True, null=True)
    processpart = models.ForeignKey(MaindataProcesspart, models.DO_NOTHING, db_column='processPart_id')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_subprocesspart'


class MaindataSubprocesspartweights(models.Model):
    id = models.BigAutoField(primary_key=True)
    weight = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    subpropart = models.ForeignKey(MaindataSubprocesspart, models.DO_NOTHING, db_column='subProPart_id')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MainData_subprocesspartweights'


class MainBlankinstance(models.Model):
    instance_id = models.IntegerField(primary_key=True)
    process = models.ForeignKey('MainProcess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_blankinstance'


class MainCompany(models.Model):
    id = models.BigAutoField(primary_key=True)
    company_name = models.CharField(max_length=50, blank=True, null=True)
    co2_choice = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    json = models.TextField(blank=True, null=True)
    total_power = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_company'


class MainCompanytime(models.Model):
    power = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    time = models.DateTimeField()
    id = models.BigAutoField(primary_key=True)
    company = models.ForeignKey(MainCompany, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_companytime'


class MainErpSchedule(models.Model):
    id = models.BigAutoField(primary_key=True)
    task_name = models.CharField(max_length=20, blank=True, null=True)
    date_of_execution = models.DateField(blank=True, null=True)
    time_of_execution = models.CharField(max_length=20, blank=True, null=True)
    changed = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_erp_schedule'


class MainInstancequeue(models.Model):
    id = models.BigAutoField(primary_key=True)
    instance_id = models.IntegerField(blank=True, null=True)
    process = models.ForeignKey('MainProcess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_instancequeue'


class MainMachine(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    status = models.IntegerField()
    company = models.ForeignKey(MainCompany, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_machine'


class MainMachineProjects(models.Model):
    id = models.BigAutoField(primary_key=True)
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING)
    project = models.ForeignKey('MainProject', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_machine_projects'
        unique_together = (('machine', 'project'),)


class MainMaterial(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=30, blank=True, null=True)
    optimumtime = models.BigIntegerField(db_column='optimumTime', blank=True, null=True)  # Field name made lowercase.
    optimumtemp = models.DecimalField(db_column='optimumTemp', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    optimumpressure = models.DecimalField(db_column='optimumPressure', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    pricekg = models.DecimalField(db_column='priceKG', max_digits=10, decimal_places=3)  # Field name made lowercase.
    pricem2 = models.DecimalField(db_column='priceM2', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialcost = models.DecimalField(db_column='materialCost', max_digits=10, decimal_places=3)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Main_material'


class MainPartinstance(models.Model):
    instance_id = models.IntegerField(primary_key=True)
    process = models.ForeignKey('MainProcess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_partinstance'


class MainPlyinstance(models.Model):
    instance_id = models.IntegerField(primary_key=True)
    process = models.ForeignKey('MainProcess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_plyinstance'


class MainPossibleprojectmachines(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING)
    project = models.ForeignKey('MainProject', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_possibleprojectmachines'


class MainPossibleprojectprocess(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING, blank=True, null=True)
    project = models.ForeignKey('MainProject', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_possibleprojectprocess'


class MainPossibleprojectsensors(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    modelid = models.CharField(db_column='modelID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING)
    project = models.ForeignKey('MainProject', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_possibleprojectsensors'


class MainPossibleprojecttia(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING, blank=True, null=True)
    project = models.ForeignKey('MainProject', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_possibleprojecttia'


class MainPossiblesensors(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    modelid = models.CharField(db_column='modelID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING, blank=True, null=True)
    process = models.ForeignKey('MainProcess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_possiblesensors'


class MainPossiblesubprocesses(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    process = models.ForeignKey('MainProcess', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_possiblesubprocesses'


class MainProcess(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    manualname = models.CharField(db_column='manualName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    viable = models.IntegerField()
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.DecimalField(db_column='labourInput', max_digits=5, decimal_places=2)  # Field name made lowercase.
    cycletime = models.BigIntegerField(db_column='cycleTime', blank=True, null=True)  # Field name made lowercase.
    processtime = models.BigIntegerField(db_column='processTime', blank=True, null=True)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    processstart = models.DateTimeField(db_column='processStart', blank=True, null=True)  # Field name made lowercase.
    processend = models.DateTimeField(db_column='processEnd', blank=True, null=True)  # Field name made lowercase.
    interfacetime = models.BigIntegerField(db_column='interfaceTime', blank=True, null=True)  # Field name made lowercase.
    badpart = models.IntegerField(db_column='badPart')  # Field name made lowercase.
    scraprate = models.DecimalField(db_column='scrapRate', max_digits=3, decimal_places=0)  # Field name made lowercase.
    minbatchsize = models.DecimalField(db_column='minBatchSize', max_digits=50, decimal_places=0)  # Field name made lowercase.
    maxbatchsize = models.DecimalField(db_column='maxBatchSize', max_digits=50, decimal_places=0)  # Field name made lowercase.
    power = models.DecimalField(max_digits=10, decimal_places=3)
    status = models.IntegerField()
    qualitycheck = models.IntegerField(db_column='qualityCheck', blank=True, null=True)  # Field name made lowercase.
    co2 = models.DecimalField(db_column='CO2', max_digits=50, decimal_places=5)  # Field name made lowercase.
    cyclecostratio = models.DecimalField(db_column='cycleCostRatio', max_digits=50, decimal_places=3)  # Field name made lowercase.
    wastedtime = models.BigIntegerField(db_column='wastedTime', blank=True, null=True)  # Field name made lowercase.
    editprocess = models.IntegerField(db_column='editProcess')  # Field name made lowercase.
    materialwastage = models.DecimalField(db_column='materialWastage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrap = models.DecimalField(db_column='materialScrap', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpart = models.DecimalField(db_column='materialPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecost = models.DecimalField(db_column='materialWastageCost', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    materialscrapcost = models.DecimalField(db_column='materialScrapCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpartcost = models.DecimalField(db_column='materialPartCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialsumcost = models.DecimalField(db_column='materialSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabour = models.BigIntegerField(db_column='technicianLabour', blank=True, null=True)  # Field name made lowercase.
    supervisorlabour = models.BigIntegerField(db_column='supervisorLabour', blank=True, null=True)  # Field name made lowercase.
    technicianlabourcost = models.DecimalField(db_column='technicianLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcost = models.DecimalField(db_column='supervisorLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    laboursumcost = models.DecimalField(db_column='labourSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powercost = models.DecimalField(db_column='powerCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    processcost = models.DecimalField(db_column='processCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partcreated = models.IntegerField(db_column='partCreated')  # Field name made lowercase.
    position = models.IntegerField(blank=True, null=True)
    startpoint = models.IntegerField(db_column='startPoint')  # Field name made lowercase.
    endpoint = models.IntegerField(db_column='endPoint')  # Field name made lowercase.
    initialised = models.IntegerField()
    project = models.ForeignKey('MainProject', models.DO_NOTHING, blank=True, null=True)
    blankcassetteinposition = models.IntegerField(db_column='blankCassetteInPosition')  # Field name made lowercase.
    blankincassette = models.IntegerField(db_column='blankInCassette')  # Field name made lowercase.
    blankplaced = models.IntegerField(db_column='blankPlaced')  # Field name made lowercase.
    blankremoved = models.IntegerField(db_column='blankRemoved')  # Field name made lowercase.
    blankwaiting = models.IntegerField(db_column='blankWaiting')  # Field name made lowercase.
    cached_co2 = models.DecimalField(db_column='cached_CO2', max_digits=50, decimal_places=4)  # Field name made lowercase.
    cassetteleftpreheater = models.IntegerField(db_column='cassetteLeftPreHeater')  # Field name made lowercase.
    destinationclear = models.IntegerField(db_column='destinationClear')  # Field name made lowercase.
    heatingdoneatcorrecttime = models.IntegerField(db_column='heatingDoneAtCorrectTime')  # Field name made lowercase.
    insertsattempandtime = models.IntegerField(db_column='insertsAtTempAndTime')  # Field name made lowercase.
    mouldinloadingarea = models.IntegerField(db_column='mouldInLoadingArea')  # Field name made lowercase.
    mouldinpress = models.IntegerField(db_column='mouldInPress')  # Field name made lowercase.
    pressisclear = models.IntegerField(db_column='pressIsClear')  # Field name made lowercase.
    robotconnected = models.IntegerField(db_column='robotConnected')  # Field name made lowercase.
    temperatureokay = models.IntegerField(db_column='temperatureOkay')  # Field name made lowercase.
    unloadexecuted = models.IntegerField(db_column='unloadExecuted')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Main_process'


class MainProcessMachine(models.Model):
    id = models.BigAutoField(primary_key=True)
    process = models.ForeignKey(MainProcess, models.DO_NOTHING)
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_process_machine'
        unique_together = (('process', 'machine'),)


class MainProfile(models.Model):
    username = models.CharField(primary_key=True, max_length=50)
    sequence_choice = models.IntegerField(blank=True, null=True)
    user = models.OneToOneField('AuthUser', models.DO_NOTHING)
    user_company = models.ForeignKey(MainCompany, models.DO_NOTHING, blank=True, null=True)
    duration_energy = models.DecimalField(max_digits=30, decimal_places=3, blank=True, null=True)
    energy_end_date = models.DateTimeField(blank=True, null=True)
    energy_start_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_profile'


class MainProject(models.Model):
    id = models.BigAutoField(primary_key=True)
    project_name = models.CharField(max_length=50)
    techrate = models.DecimalField(db_column='techRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    superrate = models.DecimalField(db_column='superRate', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerrate = models.DecimalField(db_column='powerRate', max_digits=10, decimal_places=5)  # Field name made lowercase.
    manual = models.IntegerField()
    setupcost = models.DecimalField(db_column='setUpCost', max_digits=10, decimal_places=2)  # Field name made lowercase.
    co2perpower = models.DecimalField(db_column='CO2PerPower', max_digits=10, decimal_places=2)  # Field name made lowercase.
    baselinepartno = models.IntegerField(db_column='baselinePartNo')  # Field name made lowercase.
    badpartcounter = models.IntegerField(db_column='badPartCounter')  # Field name made lowercase.
    goodpartcounter = models.IntegerField(db_column='goodPartCounter')  # Field name made lowercase.
    startdate = models.DateField(db_column='startDate', blank=True, null=True)  # Field name made lowercase.
    oeestartdate = models.DateField(db_column='OEEstartDate', blank=True, null=True)  # Field name made lowercase.
    enddate = models.DateField(db_column='endDate', blank=True, null=True)  # Field name made lowercase.
    oeeenddate = models.DateField(db_column='OEEendDate', blank=True, null=True)  # Field name made lowercase.
    pricekg = models.DecimalField(db_column='priceKG', max_digits=10, decimal_places=3)  # Field name made lowercase.
    pricem2 = models.DecimalField(db_column='priceM2', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    weighttolerance = models.DecimalField(db_column='weightTolerance', max_digits=10, decimal_places=3)  # Field name made lowercase.
    lengthtolerance = models.DecimalField(db_column='lengthTolerance', max_digits=10, decimal_places=3)  # Field name made lowercase.
    widthtolerance = models.DecimalField(db_column='widthTolerance', max_digits=10, decimal_places=3)  # Field name made lowercase.
    depthtolerance = models.DecimalField(db_column='depthTolerance', max_digits=10, decimal_places=3)  # Field name made lowercase.
    preformwrinklingtolerance = models.DecimalField(db_column='preformWrinklingTolerance', max_digits=10, decimal_places=3)  # Field name made lowercase.
    thicknesstolerance = models.DecimalField(db_column='thicknessTolerance', max_digits=10, decimal_places=3)  # Field name made lowercase.
    nominalvolumewrinkling = models.DecimalField(db_column='nominalVolumeWrinkling', max_digits=10, decimal_places=3)  # Field name made lowercase.
    nominalpartweight = models.DecimalField(db_column='nominalPartWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    nominalpartarea = models.DecimalField(db_column='nominalPartArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    nominalpartlength = models.DecimalField(db_column='nominalPartLength', max_digits=10, decimal_places=3)  # Field name made lowercase.
    nominalpartwidth = models.DecimalField(db_column='nominalPartWidth', max_digits=10, decimal_places=3)  # Field name made lowercase.
    nominalpartthickness = models.DecimalField(db_column='nominalPartThickness', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalshifttime = models.DecimalField(db_column='totalShiftTime', max_digits=10, decimal_places=3)  # Field name made lowercase.
    planneddowntime = models.DecimalField(db_column='plannedDownTime', max_digits=10, decimal_places=3)  # Field name made lowercase.
    alldowntime = models.DecimalField(db_column='allDownTime', max_digits=10, decimal_places=3)  # Field name made lowercase.
    allstoptime = models.DecimalField(db_column='allStopTime', max_digits=10, decimal_places=3)  # Field name made lowercase.
    theoreticalcycletime = models.DecimalField(db_column='theoreticalCycleTime', max_digits=10, decimal_places=3)  # Field name made lowercase.
    defectamount = models.DecimalField(db_column='defectAmount', max_digits=10, decimal_places=3)  # Field name made lowercase.
    material = models.CharField(max_length=50, blank=True, null=True)
    learningrate = models.FloatField(db_column='learningRate')  # Field name made lowercase.
    machineconfirmed = models.IntegerField(db_column='machineConfirmed')  # Field name made lowercase.
    processconfirmed = models.IntegerField(db_column='processConfirmed')  # Field name made lowercase.
    editstatus = models.IntegerField(db_column='editStatus')  # Field name made lowercase.
    nosuggested = models.IntegerField(db_column='noSuggested')  # Field name made lowercase.
    processwindow = models.IntegerField(db_column='processWindow')  # Field name made lowercase.
    technicianlabour = models.BigIntegerField(db_column='technicianLabour', blank=True, null=True)  # Field name made lowercase.
    supervisorlabour = models.BigIntegerField(db_column='supervisorLabour', blank=True, null=True)  # Field name made lowercase.
    technicianlabourcost = models.DecimalField(db_column='technicianLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcost = models.DecimalField(db_column='supervisorLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    assumedcost = models.FloatField(db_column='assumedCost', blank=True, null=True)  # Field name made lowercase.
    materialcost = models.DecimalField(db_column='materialCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powercost = models.DecimalField(db_column='powerCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    labourcost = models.DecimalField(db_column='labourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    company = models.ForeignKey(MainCompany, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_project'


class MainRepeatblock(models.Model):
    id = models.BigAutoField(primary_key=True)
    iteration = models.IntegerField(blank=True, null=True)
    number_of_iterations = models.IntegerField(blank=True, null=True)
    finished = models.IntegerField()
    process = models.ForeignKey(MainProcess, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_repeatblock'


class MainRepeatblocksubprocesses(models.Model):
    id = models.BigAutoField(primary_key=True)
    start = models.IntegerField()
    end = models.IntegerField()
    repeat_block = models.ForeignKey(MainRepeatblock, models.DO_NOTHING, blank=True, null=True)
    sub_process = models.ForeignKey('MainSubprocess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_repeatblocksubprocesses'


class MainSensor(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    proname = models.CharField(db_column='proName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    status = models.IntegerField()
    averageenergytime = models.IntegerField(db_column='averageEnergyTime')  # Field name made lowercase.
    averagetime = models.IntegerField(db_column='averageTime')  # Field name made lowercase.
    temperaturereached = models.IntegerField(db_column='temperatureReached')  # Field name made lowercase.
    tempreachedtime = models.CharField(db_column='tempReachedTime', max_length=50, blank=True, null=True)  # Field name made lowercase.
    pressurereached = models.IntegerField(db_column='pressureReached')  # Field name made lowercase.
    pressurereachedtime = models.CharField(db_column='pressureReachedTime', max_length=50, blank=True, null=True)  # Field name made lowercase.
    maxtemp = models.IntegerField(db_column='maxTemp', blank=True, null=True)  # Field name made lowercase.
    mintemp = models.IntegerField(db_column='minTemp', blank=True, null=True)  # Field name made lowercase.
    maxpressure = models.IntegerField(db_column='maxPressure', blank=True, null=True)  # Field name made lowercase.
    minpressure = models.IntegerField(db_column='minPressure', blank=True, null=True)  # Field name made lowercase.
    maxvoc = models.IntegerField(db_column='maxVOC', blank=True, null=True)  # Field name made lowercase.
    minvoc = models.IntegerField(db_column='minVOC', blank=True, null=True)  # Field name made lowercase.
    maxhumid = models.IntegerField(db_column='maxHumid', blank=True, null=True)  # Field name made lowercase.
    minhumid = models.IntegerField(db_column='minHumid', blank=True, null=True)  # Field name made lowercase.
    maxdust = models.IntegerField(db_column='maxDust', blank=True, null=True)  # Field name made lowercase.
    mindust = models.IntegerField(db_column='minDust', blank=True, null=True)  # Field name made lowercase.
    maxnoise = models.IntegerField(db_column='maxNoise', blank=True, null=True)  # Field name made lowercase.
    minnoise = models.IntegerField(db_column='minNoise', blank=True, null=True)  # Field name made lowercase.
    maxtorque = models.IntegerField(db_column='maxTorque', blank=True, null=True)  # Field name made lowercase.
    mintorque = models.IntegerField(db_column='minTorque', blank=True, null=True)  # Field name made lowercase.
    minaccel = models.IntegerField(db_column='minAccel', blank=True, null=True)  # Field name made lowercase.
    maxaccel = models.IntegerField(db_column='maxAccel', blank=True, null=True)  # Field name made lowercase.
    tolerance = models.IntegerField(blank=True, null=True)
    distance = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    poscheck = models.IntegerField(db_column='posCheck', blank=True, null=True)  # Field name made lowercase.
    actualweight = models.DecimalField(db_column='actualWeight', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    thickness = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    partpresent = models.IntegerField(db_column='partPresent', blank=True, null=True)  # Field name made lowercase.
    partdimx = models.DecimalField(db_column='partDimX', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    partdimy = models.DecimalField(db_column='partDimY', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    encoderpos = models.DecimalField(db_column='encoderPos', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    timercheck = models.IntegerField(db_column='timerCheck', blank=True, null=True)  # Field name made lowercase.
    servicedate = models.DateTimeField(db_column='serviceDate', blank=True, null=True)  # Field name made lowercase.
    contactnum = models.CharField(db_column='contactNum', unique=True, max_length=128, blank=True, null=True)  # Field name made lowercase.
    dateinstalled = models.DateTimeField(db_column='dateInstalled', blank=True, null=True)  # Field name made lowercase.
    modelid = models.CharField(db_column='modelID', max_length=50, blank=True, null=True)  # Field name made lowercase.
    warrentexp = models.DateTimeField(db_column='warrentExp', blank=True, null=True)  # Field name made lowercase.
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING, blank=True, null=True)
    process = models.ForeignKey(MainProcess, models.DO_NOTHING, blank=True, null=True)
    sub_process = models.ForeignKey('MainSubprocess', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_sensor'


class MainSensortime(models.Model):
    id = models.BigAutoField(primary_key=True)
    temp = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    distance = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    pressure = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    noise = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    energy = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    voc = models.DecimalField(db_column='VOC', max_digits=10, decimal_places=3, blank=True, null=True)  # Field name made lowercase.
    dust = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    humidity = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    torque = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    acceleration = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    time = models.DateTimeField()
    sensor = models.ForeignKey(MainSensor, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_sensortime'


class MainSubprocess(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    manualname = models.CharField(db_column='manualName', max_length=50, blank=True, null=True)  # Field name made lowercase.
    repeat = models.IntegerField()
    operator = models.CharField(max_length=50, blank=True, null=True)
    labourinput = models.IntegerField(db_column='labourInput')  # Field name made lowercase.
    processtime = models.BigIntegerField(db_column='processTime', blank=True, null=True)  # Field name made lowercase.
    jobstart = models.DateTimeField(db_column='jobStart', blank=True, null=True)  # Field name made lowercase.
    jobend = models.DateTimeField(db_column='jobEnd', blank=True, null=True)  # Field name made lowercase.
    date = models.DateTimeField(blank=True, null=True)
    position = models.IntegerField(blank=True, null=True)
    startpoint = models.IntegerField(db_column='startPoint')  # Field name made lowercase.
    endpoint = models.IntegerField(db_column='endPoint')  # Field name made lowercase.
    interfacetime = models.BigIntegerField(db_column='interfaceTime', blank=True, null=True)  # Field name made lowercase.
    badpart = models.IntegerField(db_column='badPart')  # Field name made lowercase.
    scraprate = models.DecimalField(db_column='scrapRate', max_digits=3, decimal_places=0)  # Field name made lowercase.
    batchsize = models.DecimalField(db_column='batchSize', max_digits=50, decimal_places=0)  # Field name made lowercase.
    power = models.DecimalField(max_digits=10, decimal_places=3)
    status = models.IntegerField()
    processcheck = models.IntegerField(db_column='processCheck', blank=True, null=True)  # Field name made lowercase.
    qualitycheck = models.IntegerField(db_column='qualityCheck', blank=True, null=True)  # Field name made lowercase.
    co2 = models.DecimalField(db_column='CO2', max_digits=50, decimal_places=5)  # Field name made lowercase.
    cyclecostratio = models.DecimalField(db_column='cycleCostRatio', max_digits=50, decimal_places=3)  # Field name made lowercase.
    presubcost = models.DecimalField(db_column='preSubCost', max_digits=50, decimal_places=3)  # Field name made lowercase.
    wastedtime = models.BigIntegerField(db_column='wastedTime')  # Field name made lowercase.
    criterion = models.CharField(max_length=800, blank=True, null=True)
    image = models.CharField(max_length=100, blank=True, null=True)
    file = models.CharField(max_length=100, blank=True, null=True)
    weighpoint = models.IntegerField(db_column='weighPoint')  # Field name made lowercase.
    finalweighpoint = models.IntegerField(db_column='finalWeighPoint')  # Field name made lowercase.
    posttrimweight = models.DecimalField(db_column='postTrimWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    pretrimweight = models.DecimalField(db_column='preTrimWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    actualthickness = models.DecimalField(db_column='actualThickness', max_digits=10, decimal_places=3)  # Field name made lowercase.
    actualwidth = models.DecimalField(db_column='actualWidth', max_digits=10, decimal_places=3)  # Field name made lowercase.
    actuallength = models.DecimalField(db_column='actualLength', max_digits=10, decimal_places=3)  # Field name made lowercase.
    centrepost = models.DecimalField(db_column='centrePosT', max_digits=10, decimal_places=3)  # Field name made lowercase.
    centreposmt = models.DecimalField(db_column='centrePosMT', max_digits=10, decimal_places=3)  # Field name made lowercase.
    tolerance = models.DecimalField(max_digits=10, decimal_places=3)
    temperature = models.DecimalField(max_digits=10, decimal_places=3)
    time = models.DecimalField(max_digits=10, decimal_places=3)
    pressure = models.DecimalField(max_digits=10, decimal_places=3)
    verticaleffector = models.DecimalField(db_column='verticalEffector', max_digits=10, decimal_places=3)  # Field name made lowercase.
    tolerancex2 = models.DecimalField(max_digits=10, decimal_places=3)
    materialwastage = models.DecimalField(db_column='materialWastage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrap = models.DecimalField(db_column='materialScrap', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpart = models.DecimalField(db_column='materialPart', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialwastagecost = models.DecimalField(db_column='materialWastageCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialscrapcost = models.DecimalField(db_column='materialScrapCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialpartcost = models.DecimalField(db_column='materialPartCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialsumcost = models.DecimalField(db_column='materialSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    technicianlabour = models.BigIntegerField(db_column='technicianLabour', blank=True, null=True)  # Field name made lowercase.
    supervisorlabour = models.BigIntegerField(db_column='supervisorLabour', blank=True, null=True)  # Field name made lowercase.
    technicianlabourcost = models.DecimalField(db_column='technicianLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    supervisorlabourcost = models.DecimalField(db_column='supervisorLabourCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    laboursumcost = models.DecimalField(db_column='labourSumCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powercost = models.DecimalField(db_column='powerCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalcost = models.DecimalField(db_column='totalCost', max_digits=10, decimal_places=3)  # Field name made lowercase.
    partinstance = models.IntegerField(db_column='partInstance', blank=True, null=True)  # Field name made lowercase.
    blankinstance = models.IntegerField(db_column='blankInstance', blank=True, null=True)  # Field name made lowercase.
    plyinstance = models.IntegerField(db_column='plyInstance', blank=True, null=True)  # Field name made lowercase.
    parttask = models.IntegerField(db_column='partTask')  # Field name made lowercase.
    blanktask = models.IntegerField(db_column='blankTask')  # Field name made lowercase.
    plytask = models.IntegerField(db_column='plyTask')  # Field name made lowercase.
    consolidationcheck = models.IntegerField(db_column='consolidationCheck')  # Field name made lowercase.
    plysurfacearea = models.DecimalField(db_column='plySurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    plyperimeter = models.DecimalField(db_column='plyPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsumofperimeter = models.DecimalField(db_column='totalSumOfPerimeter', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totalsurfacearea = models.DecimalField(db_column='totalSurfaceArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    totaloffcutarea = models.DecimalField(db_column='totalOffcutArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    powerusage = models.DecimalField(db_column='powerUsage', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialratearea = models.DecimalField(db_column='materialRateArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialrateweight = models.DecimalField(db_column='materialRateWeight', max_digits=10, decimal_places=3)  # Field name made lowercase.
    materialdensity = models.DecimalField(db_column='materialDensity', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankarea = models.DecimalField(db_column='blankArea', max_digits=10, decimal_places=3)  # Field name made lowercase.
    blankspickandplace = models.ForeignKey(MainMachine, models.DO_NOTHING, db_column='blanksPickAndPlace_id', blank=True, null=True)  # Field name made lowercase.
    plycutter = models.ForeignKey(MainMachine, models.DO_NOTHING, db_column='plyCutter_id', related_name='mainsubprocess_plycutter_set', blank=True, null=True)  # Field name made lowercase.
    preformcell = models.ForeignKey(MainMachine, models.DO_NOTHING, db_column='preformCell_id', related_name='mainsubprocess_preformcell_set', blank=True, null=True)  # Field name made lowercase.
    process = models.ForeignKey(MainProcess, models.DO_NOTHING)
    sortpickandplace = models.ForeignKey(MainMachine, models.DO_NOTHING, db_column='sortPickAndPlace_id', related_name='mainsubprocess_sortpickandplace_set', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Main_subprocess'


class MainSubprocessweights(models.Model):
    id = models.BigAutoField(primary_key=True)
    weight = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    subpropart = models.ForeignKey(MainSubprocess, models.DO_NOTHING, db_column='subProPart_id')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Main_subprocessweights'


class MainTiablocks(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    machine = models.ForeignKey(MainMachine, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Main_tiablocks'


class MainTiablocksProject(models.Model):
    id = models.BigAutoField(primary_key=True)
    tiablocks = models.ForeignKey(MainTiablocks, models.DO_NOTHING)
    project = models.ForeignKey(MainProject, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_tiablocks_project'
        unique_together = (('tiablocks', 'project'),)


class MainTiablocksSubprocess(models.Model):
    id = models.BigAutoField(primary_key=True)
    tiablocks = models.ForeignKey(MainTiablocks, models.DO_NOTHING)
    subprocess = models.ForeignKey(MainSubprocess, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'Main_tiablocks_subProcess'
        unique_together = (('tiablocks', 'subprocess'),)


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoCeleryBeatClockedschedule(models.Model):
    clocked_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_celery_beat_clockedschedule'


class DjangoCeleryBeatCrontabschedule(models.Model):
    minute = models.CharField(max_length=240)
    hour = models.CharField(max_length=96)
    day_of_week = models.CharField(max_length=64)
    day_of_month = models.CharField(max_length=124)
    month_of_year = models.CharField(max_length=64)
    timezone = models.CharField(max_length=63)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_crontabschedule'


class DjangoCeleryBeatIntervalschedule(models.Model):
    every = models.IntegerField()
    period = models.CharField(max_length=24)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_intervalschedule'


class DjangoCeleryBeatPeriodictask(models.Model):
    name = models.CharField(unique=True, max_length=200)
    task = models.CharField(max_length=200)
    args = models.TextField()
    kwargs = models.TextField()
    queue = models.CharField(max_length=200, blank=True, null=True)
    exchange = models.CharField(max_length=200, blank=True, null=True)
    routing_key = models.CharField(max_length=200, blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    enabled = models.IntegerField()
    last_run_at = models.DateTimeField(blank=True, null=True)
    total_run_count = models.PositiveIntegerField()
    date_changed = models.DateTimeField()
    description = models.TextField()
    crontab = models.ForeignKey(DjangoCeleryBeatCrontabschedule, models.DO_NOTHING, blank=True, null=True)
    interval = models.ForeignKey(DjangoCeleryBeatIntervalschedule, models.DO_NOTHING, blank=True, null=True)
    solar = models.ForeignKey('DjangoCeleryBeatSolarschedule', models.DO_NOTHING, blank=True, null=True)
    one_off = models.IntegerField()
    start_time = models.DateTimeField(blank=True, null=True)
    priority = models.PositiveIntegerField(blank=True, null=True)
    headers = models.TextField()
    clocked = models.ForeignKey(DjangoCeleryBeatClockedschedule, models.DO_NOTHING, blank=True, null=True)
    expire_seconds = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_periodictask'


class DjangoCeleryBeatPeriodictasks(models.Model):
    ident = models.SmallIntegerField(primary_key=True)
    last_update = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_celery_beat_periodictasks'


class DjangoCeleryBeatSolarschedule(models.Model):
    event = models.CharField(max_length=24)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        managed = False
        db_table = 'django_celery_beat_solarschedule'
        unique_together = (('event', 'latitude', 'longitude'),)


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class GuardianGroupobjectpermission(models.Model):
    object_pk = models.CharField(max_length=255)
    content_type = models.ForeignKey(DjangoContentType, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'guardian_groupobjectpermission'
        unique_together = (('group', 'permission', 'object_pk'),)


class GuardianUserobjectpermission(models.Model):
    object_pk = models.CharField(max_length=255)
    content_type = models.ForeignKey(DjangoContentType, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'guardian_userobjectpermission'
        unique_together = (('user', 'permission', 'object_pk'),)
