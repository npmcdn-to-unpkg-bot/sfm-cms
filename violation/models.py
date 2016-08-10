from django.contrib.gis.db import models
from django.utils.translation import ugettext as _
from django.db.models import Max
from django.contrib.gis import geos

from django_date_extensions.fields import ApproximateDateField

from complex_fields.model_decorators import versioned, translated, sourced, sourced_optional
from complex_fields.models import ComplexField, ComplexFieldContainer, ComplexFieldListContainer
from complex_fields.base_models import BaseModel
from source.models import Source
from person.models import Person
from organization.models import Organization

CONFIDENCE_LEVELS = (
    ('1', _('Low')),
    ('2', _('Medium')),
    ('3', _('High')),
)


class Violation(models.Model, BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.startdate = ComplexFieldContainer(self, ViolationStartDate)
        self.enddate = ComplexFieldContainer(self, ViolationEndDate)
        self.locationdescription = ComplexFieldContainer(
            self, ViolationLocationDescription
        )
        self.adminlevel1 = ComplexFieldContainer(self, ViolationAdminLevel1)
        self.adminlevel2 = ComplexFieldContainer(self, ViolationAdminLevel2)
        self.geoname = ComplexFieldContainer(self, ViolationGeoname)
        self.geonameid = ComplexFieldContainer(self, ViolationGeonameId)
        self.location = ComplexFieldContainer(self, ViolationLocation)
        self.description = ComplexFieldContainer(self, ViolationDescription)
        self.perpetrator = ComplexFieldListContainer(self, ViolationPerpetrator)
        self.perpetratororganization = ComplexFieldListContainer(
            self, ViolationPerpetratorOrganization
        )

        self.complex_fields = [self.startdate, self.enddate, self.locationdescription,
                               self.adminlevel1, self.adminlevel2, self.geoname,
                               self.geonameid, self.location, self.description]

        self.required_fields = []

        self.types = ComplexFieldListContainer(self, ViolationType)

    def get_value(self):
        return self.description.get_value()

@versioned
@sourced
class ViolationStartDate(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("Start date")
    
    confidence_required = False

@versioned
@sourced
class ViolationEndDate(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = ApproximateDateField(default=None, blank=True, null=True)
    field_name = _("End date")
    
    confidence_required = False


@translated
@versioned
@sourced
class ViolationLocationDescription(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Location description")
    
    confidence_required = False

@versioned
@sourced
class ViolationAdminLevel1(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Admin level 1")
    
    confidence_required = False

@versioned
@sourced
class ViolationAdminLevel2(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Admin level 2")
    
    confidence_required = False

@versioned
@sourced
class ViolationGeoname(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("GeoName name")
    
    confidence_required = False

@versioned
@sourced
class ViolationGeonameId(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("GeoName ID")
    
    confidence_required = False

@versioned
@sourced
class ViolationLocation(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.PointField(default=None, blank=True, null=True)
    field_name = _("Location")
    
    confidence_required = False

@versioned
@sourced
class ViolationDescription(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.TextField(default=None, blank=True, null=True)
    field_name = _("Description")
    
    confidence_required = False

@versioned
@sourced
class ViolationPerpetrator(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.ForeignKey(Person, default=None, blank=True, null=True)
    field_name = _("Perpetrator")
    
    confidence_required = False

@versioned
@sourced
class ViolationPerpetratorOrganization(ComplexField):
    object_ref = models.ForeignKey('Violation')
    value = models.ForeignKey(Organization, default=None, blank=True, null=True)
    field_name = _("Perpetrator Organization")
    
    confidence_required = False

@versioned
@sourced
@translated
class ViolationType(ComplexField):
    object_ref = models.ForeignKey('Violation', null=True)
    value = models.ForeignKey('Type', default=None, blank=True, null=True)
    
    field_name = _("Event Type")
    
    confidence_required = False

class Type(models.Model):
    code = models.TextField()

    def __str__(self):
        return self.code
