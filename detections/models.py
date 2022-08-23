from django.db import models

from areas.models      import Area
from equipments.models import Equipment

class DetectionType(models.Model):
    id   = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45)

    class Meta:
        db_table = 'detection_types'

class State(models.Model):
    id   = models.AutoField(primary_key=True)
    name = models.CharField(max_length=45)

    class Meta:
        db_table = 'states'

class Detection(models.Model):
    id             = models.AutoField(primary_key=True)
    x              = models.IntegerField()
    y              = models.IntegerField()
    width          = models.IntegerField()
    height         = models.IntegerField()
    datetime       = models.DateTimeField()
    area           = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='detection')
    detection_type = models.ForeignKey(DetectionType, on_delete=models.CASCADE, related_name='detection')
    state          = models.ForeignKey(State, on_delete=models.CASCADE)
    equipment      = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = 'detections'

