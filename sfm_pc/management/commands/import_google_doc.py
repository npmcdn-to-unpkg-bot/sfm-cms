import os
import json
from collections import OrderedDict
import re
from uuid import uuid4
from datetime import datetime
import csv

import httplib2

from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build

import datefinder

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction, IntegrityError
from django.db.utils import DataError
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.conf import settings

from django_date_extensions.fields import ApproximateDateField

from dateparser import parse as dateparser

from cities.models import Country, City, Region, Subregion

import reversion

from source.models import Source, Publication
from organization.models import Organization, OrganizationAlias, \
    OrganizationClassification, OrganizationName
from sfm_pc.utils import import_class, get_geoname_by_id
from sfm_pc.base_views import UtilityMixin
from geosite.models import Geosite
from emplacement.models import Emplacement
from area.models import Area
from association.models import Association
from composition.models import Composition
from person.models import Person
from membershipperson.models import MembershipPerson
from violation.models import Violation, Type, ViolationPerpetrator, \
    ViolationPerpetratorOrganization

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

CONFIDENCE_MAP = {
    'low': 1,
    'medium': 2,
    'high': 3,
}

class Command(UtilityMixin, BaseCommand):
    help = 'Import data from Google Drive Spreadsheet'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--doc_id',
            dest='doc_id',
            default='16cRBkrnXE5iGm8JXD7LSqbeFOg_anhVp2YAzYTRYDgU',
            help='Import data from specified Google Drive Document'
        )
        parser.add_argument(
            '--entity_types',
            dest='entity_types',
            default='organization,person,event',
            help='Comma separated list of entity types to import'
        )
        parser.add_argument(
            '--country_code',
            dest='country_code',
            default='ng',
            help='Two letter ISO code for the country that the Google Sheets are about'
        )
    
    def get_credentials(self):
        
        this_dir = os.path.dirname(__file__)
        secrets_path = os.path.join(this_dir, 'credentials.json')
        
        credentials = ServiceAccountCredentials.from_json_keyfile_name(secrets_path, 
                                                                       SCOPES)
        return credentials
    
    # @transaction.atomic
    def handle(self, *args, **options):
        
        # Get a handle on the "user" that will be doing the work
        importer_user = settings.IMPORTER_USER
        try:
            self.user = User.objects.create_user(importer_user['username'], 
                                                 email=importer_user['email'], 
                                                 password=importer_user['password'])
        except IntegrityError:
            self.user = User.objects.get(username=importer_user['username'])

        # Set the country code for the work
        self.country_code = options['country_code']

        credentials = self.get_credentials()
        
        http = credentials.authorize(httplib2.Http())

        service = build('sheets', 'v4', http=http)
        
        result = service.spreadsheets().get(
            spreadsheetId=options['doc_id'], includeGridData=False).execute()
        
        sheets = result['sheets']
        
        sheet_mapping = {}

        for sheet in sheets:
            title = sheet['properties']['title']

            sheet_data = service.spreadsheets().values().get(
                spreadsheetId=options['doc_id'], range=title).execute()

            sheet_mapping[title] = sheet_data['values']

        org_sheets = {title: data for title, data in sheet_mapping.items() \
                          if 'organization' in title.lower() or 'mopol' in title.lower()}
        
        person_sheets = {title: data for title, data in sheet_mapping.items() \
                            if 'people' in title.lower()}
        
        event_sheets = {title: data for title, data in sheet_mapping.items() \
                            if 'event' in title.lower()}
        
        all_sheets = {
            'organization': org_sheets,
            'person': person_sheets,
            'event': event_sheets,
        }
        
        skippers = ['Play Copy of Events']

        for entity_type in options['entity_types'].split(','):
            
            sheets = all_sheets[entity_type]
            
            for title, sheet in sheets.items():
            
                self.stdout.write(self.style.SUCCESS('Creating {0}s from {1} ... '.format(entity_type, title)))
                
                self.current_sheet = title
                
                if not title in skippers:

                    # Skip header row
                    for index, row in enumerate(sheet[1:]):
                        if row:
                            self.current_row = index + 2
                            getattr(self, 'create_{}'.format(entity_type))(row)
        
        self.stdout.write(self.style.SUCCESS('Successfully imported data from {}'.format(options['doc_id'])))
    
    def log_error(self, message):
        log_message = message + ' (context: Sheet {0}, Row {1})'.format(self.current_sheet, self.current_row)
        self.stdout.write(self.style.ERROR(log_message))
        file_name = '{}-errors.csv'.format(slugify(self.current_sheet)) 
        if not os.path.isfile(file_name):
            with open(file_name, 'w') as f:
                header = ['row', 'message']
                writer = csv.writer(f)
                writer.writerow(header)

        with open(file_name, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([self.current_row, 
                             message])
    
    def get_confidence(self, confidence_key):
        key = confidence_key.strip().lower()
        return CONFIDENCE_MAP[key]

    def create_organization(self, org_data):
        organization = None
        
        org_positions = {
            'Name': {
                'value': 14,
                'confidence': 16,
                'source': 15
            },
            'Alias': {
                'value': 17,
                'confidence': 19,
                'source': 18,
            },
            'Classification': {
                'value': 22,
                'confidence': 24,
                'source': 23,
            }
        }
        
        composition_positions = {
            'Parent': {
                'value': 1,
                'confidence': 3,
                'source': 2,
            },
            'StartDate': {
                'value': 7,
                'confidence': 9,
                'source': 8,
            },
            'EndDate': {
                'value': 10,
                'confidence': 12,
                'source': 11,
            },
            'Classification': {
                'value': 4,
                'confidence': 6,
                'source': 5,
            },
        }
        
        area_positions = {
            'Geoname': {
                'value': 45,
                'confidence': 48,
                'source': 47,
            },
            'GeonameId': {
                'value': 46,
                'confidence': 48,
                'source': 47,
            },
        }
        
        site_positions = {
            'Geoname': {
                'value': 27,
                'confidence': 30,
                'source': 29,
            },
            'GeonameId': {
                'value': 28,
                'confidence': 30,
                'source': 29,
            },
        }
        
        # Need to get or create name first

        try:
            name_value = org_data[org_positions['Name']['value']]
            confidence = org_data[org_positions['Name']['confidence']]
            source = org_data[org_positions['Name']['source']]
        except IndexError:
            self.log_error('Row seems to be empty')
            return None
        
        if confidence and source:
            
            try:
                confidence = self.get_confidence(confidence)
            except KeyError:
                confidence = None
            
            sources = self.create_sources(source)
            self.stdout.write(self.style.SUCCESS('Working on {}'.format(name_value)))
            
            if confidence and sources:
                
                org_info = {
                    'Organization_OrganizationName': {
                        'value': name_value,
                        'confidence': confidence,
                        'sources': sources
                    },
                    'Organization_OrganizationDivisionId': {
                        'value': 'ocd-division/country:{}'.format(self.country_code),
                        'confidence': confidence,
                        'sources': sources,
                    }
                }
                
                try:
                    organization = Organization.objects.get(organizationname__value=name_value)
                    sources = self.sourcesList(organization, 'name')
                    org_info["Organization_OrganizationName"]['sources'] += sources
                    
                    organization.update(org_info)

                except Organization.DoesNotExist:
                    organization = Organization.create(org_info)

                aliases = self.make_relation('Alias', 
                                             org_positions['Alias'], 
                                             org_data, 
                                             organization)
                
                classification = self.make_relation('Classification',
                                                    org_positions['Classification'],
                                                    org_data,
                                                    organization)
                

                # Create Emplacements
                try:
                    site_geoname_id = org_data[site_positions['GeonameId']['value']]
                except IndexError:
                    # self.log_error('No Site Geoname info for {}'.format(organization.name))
                    site_geoname_id = None

                if site_geoname_id:
                    
                    emplacement = self.make_emplacement(site_geoname_id, 
                                                        org_data, 
                                                        organization)
                
                # Create Areas
                try:
                    area_geoname_id = org_data[area_positions['GeonameId']['value']]
                except IndexError:
                    # self.log_error('No Area Geoname info for {}'.format(organization.name))
                    area_geoname_id = None

                if area_geoname_id:

                    area = self.make_area(area_geoname_id,
                                          org_data,
                                          organization)

                # Create Compositions

                parent_org_name = org_data[composition_positions['Parent']['value']]

                if parent_org_name:
                    
                    try:
                        parent_confidence = self.get_confidence(org_data[composition_positions['Parent']['confidence']])
                    except (IndexError, KeyError):
                        self.log_error('Parent organization for {} does not have confidence'.format(organization.name))
                        parent_confidence = None
                    
                    try:
                        parent_sources = self.create_sources(org_data[composition_positions['Parent']['source']])
                    except IndexError:
                        self.log_error('Parent organization for {} does not have a source'.format(organization.name))
                        parent_sources = None

                    if parent_confidence and parent_sources:
                        parent_org_info = {
                            'Organization_OrganizationName': {
                                'value': parent_org_name,
                                'confidence': parent_confidence,
                                'sources': parent_sources
                            }
                        }
                        try:
                            parent_organization = Organization.objects.get(organizationname__value=parent_org_name)
                            sources = self.sourcesList(parent_organization, 'name')
                            org_info["Organization_OrganizationName"]['sources'] = sources
                            
                        except Organization.DoesNotExist:
                            parent_organization = Organization.create(parent_org_info)
                        
                        with reversion.create_revision():
                            composition, created = Composition.objects.get_or_create(compositionparent__value=parent_organization,
                                                                                     compositionchild__value=organization)
                            reversion.set_user(self.user)
                        
                        comp_info = {
                            'Composition_CompositionParent': {
                                'value': parent_organization,
                                'confidence': parent_confidence,
                                'sources': parent_sources
                            },
                            'Composition_CompositionChild': {
                                'value': organization,
                                'confidence': parent_confidence,
                                'sources': parent_sources,
                            },
                        }
                        composition.update(comp_info)

                        self.make_relation('StartDate', 
                                           composition_positions['StartDate'], 
                                           org_data, 
                                           composition)
                        
                        self.make_relation('EndDate', 
                                           composition_positions['EndDate'], 
                                           org_data, 
                                           composition)
                        
                        self.make_relation('Classification', 
                                           composition_positions['Classification'], 
                                           org_data, 
                                           composition)


                    else:
                        self.log_error('Parent organization for {} does not have source or confidence'.format(organization.name))
                self.stdout.write(self.style.SUCCESS('Created {}'.format(organization.get_value())))

            else:
                self.log_error('{} did not have a confidence or source'.format(name_value))
        
        else:
            missing = []
            if not confidence:
                missing.append('confidence')
            if not source:
                missing.append('sources')
            
            self.log_error('{0} did not have {1}'.format(name_value, ', '.join(missing)))
        
        return organization
    
    def make_relation(self, 
                      field_name, 
                      positions, 
                      data,
                      instance,
                      required=False):

        value_position = positions['value']
        
        try:
            confidence_position = positions['confidence']
        except KeyError:
            confidence_position = None
            
            if instance.confidence_required:
                self.log_error('No confidence for {}'.format(field_name))
                return None
        
        source_position = positions['source']
        
        try:
            value = data[value_position]
            value = value.strip()
        except IndexError:
            value = None
        
        if required and not value:
            self.log_error('No {0} information for {1}'.format(field_name, instance.get_value()))
            return None
        
        elif value:
            try:
                confidence = self.get_confidence(data[confidence_position])
            except (KeyError, IndexError, TypeError):
                confidence = 1
                if instance.confidence_required:
                    self.log_error('No confidence for {}'.format(field_name))
                    return None
            
            try:
                sources = self.create_sources(data[source_position])
            except IndexError:
                self.log_error('No source for {}'.format(field_name))
                return None

            app_name = instance._meta.model_name
            model_name = instance._meta.object_name

            if sources and confidence:
                import_path = '{app_name}.models.{model_name}{field_name}'

                relation_path = import_path.format(app_name=app_name,
                                                   model_name=model_name,
                                                   field_name=field_name)

                relation_model = import_class(relation_path)
                
                if isinstance(relation_model._meta.get_field('value'), models.ForeignKey):
                    value_rel_path_fmt = '{app_name}.models.{field_name}'
                    value_rel_path = value_rel_path_fmt.format(app_name=app_name,
                                                               field_name=field_name)

                    try:
                        value_model = import_class(value_rel_path)
                    except AttributeError:
                        value_rel_path = value_rel_path_fmt.format(app_name=app_name,
                                                                   field_name='Context')
                        value_model = import_class(value_rel_path)
                   
                    value_objects = []
                    for value_text in value.split(';'):
                        
                            if value_model == Type:
                                with reversion.create_revision():
                                    value_obj, created = value_model.objects.get_or_create(code=value_text)
                                    reversion.set_user(self.user)
                            else:
                                with reversion.create_revision():
                                    value_obj, created = value_model.objects.get_or_create(value=value_text)
                                    reversion.set_user(self.user)
                            
                            with reversion.create_revision():
                                relation_instance, created = relation_model.objects.get_or_create(value=value_obj,
                                                                                                  object_ref=instance,
                                                                                                  lang='en')
                                reversion.set_user(self.user)
                
                elif isinstance(relation_model._meta.get_field('value'), ApproximateDateField):
                    parsed_value = dateparser(value)
                    
                    if parsed_value:
                        with reversion.create_revision():
                            relation_instance, created = relation_model.objects.get_or_create(value=parsed_value.strftime('%Y-%m-%d'), 
                                                                                              object_ref=instance,
                                                                                              lang='en')
                            reversion.set_user(self.user)
                    else:
                        self.log_error('Expected a date for {app_name}.models.{field_name} but got {value}'.format(app_name=app_name,
                                                                                                                   field_name=field_name,
                                                                                                                   value=value))
                        return None

                else:
                    with reversion.create_revision():
                        relation_instance, created = relation_model.objects.get_or_create(value=value, 
                                                                                          object_ref=instance,
                                                                                          lang='en')
                        reversion.set_user(self.user)
                
                for source in sources:
                    relation_instance.sources.add(source)
                
                with reversion.create_revision():
                    relation_instance.confidence = confidence
                    relation_instance.save()
                    reversion.set_user(self.user)

                return relation_instance
            
            else:
                missing = []
                if not confidence and instance.confidence_required:
                    missing.append('confidence')
                if not sources:
                    missing.append('sources')
                
                message = '{field_name} from {app_name}.{model_name} does not have {missing}'.format(field_name=field_name,
                                                                                                     app_name=app_name,
                                                                                                     model_name=model_name,
                                                                                                     missing=', '.join(missing))
                self.log_error(message)
            
            return None
    
    def make_area(self, geoname_id, org_data, organization):
        positions = {
            'Geoname': {
                'confidence': 50,
                'source': 49
            },
        }
        
        relation_positions = {
            'StartDate': {
                'value': 51,
                'confidence': 53,
                'source': 52,
            },
            'EndDate': {
                'value': 54,
                'confidence': 56,
                'source': 55
            }
        }

        try:
            geo = get_geoname_by_id(geoname_id)
        except DataError:
            self.log_error('Geoname ID for Area does not seem valid: {}'.format(geoname_id))
            geo = None

        if geo:
            
            if isinstance(geo, Country):
                country_code = geo.code.lower()
            elif isinstance(geo, Region):
                country_code = geo.country.code.lower()
            elif isinstance(geo, Subregion) or isinstance(geo, City):
                country_code = geo.region.country.code.lower()
            
            division_id = 'ocd-division/country:{}'.format(country_code)

            try:
                area_confidence = self.get_confidence(org_data[positions['Geoname']['confidence']])
            except (IndexError, KeyError):
                self.log_error('Geoname for Area for {} does not have confidence'.format(organization.name))
                return None

            try:
                area_sources = self.create_sources(org_data[positions['Geoname']['source']])
            except IndexError:
                self.log_error('Geoname for Area for {} does not have source'.format(organization.name))
                return None
            
            with reversion.create_revision():
                area, created = Area.objects.get_or_create(areageonameid__value=geo.id,
                                                           areageoname__value=geo.name)
                reversion.set_user(self.user)
            

            area_info = {
                'Area_AreaName': {
                    'value': geo.name,
                    'confidence': area_confidence,
                    'sources': area_sources
                },
                'Area_AreaGeoname': {
                    'value': geo.name,
                    'confidence': area_confidence,
                    'sources': area_sources
                },
                'Area_AreaGeonameId': {
                    'value': geo.id,
                    'confidence': area_confidence,
                    'sources': area_sources
                },
                'Area_AreaGeonameId': {
                    'value': division_id,
                    'confidence': area_confidence,
                    'sources': area_sources
                },
            }
            
            area.update(area_info)

            with reversion.create_revision():
                assoc, created = Association.objects.get_or_create(associationorganization__value=organization.id,
                                                                   associationarea__value=area.id)
                reversion.set_user(self.user)
            
            for field_name, positions in relation_positions.items():
                
                self.make_relation(field_name, 
                                   positions, 
                                   org_data, 
                                   assoc)


    def make_emplacement(self, 
                         geoname_id, 
                         org_data, 
                         organization):
        
        positions = {
            'Geoname': {
                'confidence': 30,
                'source': 29,
            },
            'AdminLevel1': {
                'confidence': 34,
                'source': 33,
            }
        }

        relation_positions = {
            'StartDate': {
                'value': 36,
                'confidence': 38,
                'source': 37,
            },
            'EndDate': {
                'value': 40,
                'confidence': 42,
                'source': 41,
            }
        }
        
        try:
            geo = get_geoname_by_id(geoname_id)
        except DataError:
            self.log_error('Geoname ID for Site does not seem valid: {}'.format(geoname_id))
            geo = None
        
        if geo:
            parent = geo.parent
            admin1 = parent.name
            coords = getattr(geo, 'location', None)
            
            if isinstance(geo, Country):
                country_code = geo.code.lower()
            elif isinstance(geo, Region):
                country_code = geo.country.code.lower()
            elif isinstance(geo, Subregion) or isinstance(geo, City):
                country_code = geo.region.country.code.lower()
            
            division_id = 'ocd-division/country:{}'.format(country_code)
            
            with reversion.create_revision():
                site, created = Geosite.objects.get_or_create(geositegeonameid__value=geo.id)
                reversion.set_user(self.user)

            site_data = {}

            geoname_confidence = self.get_confidence(org_data[positions['Geoname']['confidence']])
            geoname_sources = self.create_sources(org_data[positions['Geoname']['source']])
            
            if geoname_confidence and geoname_sources:

                site_data['Geosite_GeositeName'] = {
                    'value': geo.name,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                }
                site_data['Geosite_GeositeGeoname'] = {
                    'value': geo.name,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                }
                site_data['Geosite_GeositeGeonameId'] = {
                    'value': geo.id,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                }
                site_data['Geosite_GeositeDivisionId'] = {
                    'value': division_id,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                }
                site_data['Geosite_GeositeCoordinates'] = {
                    'value': coords,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                }
            
            else:
                missing = []
                if not geoname_confidence:
                    missing.append('confidence')
                if not geoname_sources:
                    missing.append('sources')
            
                self.log_error('Geoname {0} did not have {1}'.format(geo.name, ', '.join(missing)))
            
            try:
                admin1_confidence = self.get_confidence(org_data[positions['AdminLevel1']['confidence']])
            except KeyError:
                self.log_error('Admin Level 1 for {} does not have a confidence'.format(organization.name))
                return None

            admin1_sources = self.create_sources(org_data[positions['AdminLevel1']['source']])
            
            if admin1_confidence and admin1_sources:

                site_data['Geosite_GeositeAdminLevel1'] = {
                    'value': admin1,
                    'confidence': admin1_confidence,
                    'sources': admin1_sources,
                }
            
            else:
                missing = []
                if not admin1_confidence:
                    missing.append('confidence')
                if not admin1_sources:
                    missing.append('sources')
            
                self.log_error('AdminLevel1 {0} did not have {1}'.format(admin1, ', '.join(missing)))
            
            site.update(site_data)
            
            with reversion.create_revision():
                emplacement, created = Emplacement.objects.get_or_create(emplacementorganization__value=organization.id,
                                                                         emplacementsite__value=site.id)
                reversion.set_user(self.user)
            
            for field_name, positions in relation_positions.items():
                
                self.make_relation(field_name, 
                                   positions, 
                                   org_data, 
                                   emplacement)
            emp_data = {
                'Emplacement_EmplacementOrganization': {
                    'value': organization,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                },
                'Emplacement_EmplacementSite': {
                    'value': site,
                    'confidence': geoname_confidence,
                    'sources': geoname_sources,
                },
            }
            
            emplacement.update(emp_data)
        
        else:
            self.log_error('Could not find GeonameID {}'.format(geoname_id))

    def create_sources(self, sources_string):
        
        sources = []
        
        for source in sources_string.split(';'):
            
            date_gen = datefinder.find_dates(source, index=True)

            try:
                date_indices = next(date_gen)
            except StopIteration:
                self.log_error('Unable to parse published on date from source string: {}'.format(source))
                continue
            
            date, indices = date_indices
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            while date > now or date == today:
                try:
                    date_indices = next(date_gen)
                    date, indices = date_indices
                except StopIteration:
                    self.log_error('Unable to parse published on date from source string: {}'.format(source))
                    date = None
                    break
            
            if date:
                before_date, after_date = source[:indices[0]], source[indices[1]:]
                
                # Source title, publication title and publication country should be
                # before the date. If not, skip it
                
                try:
                    source_title, pub_title = before_date.split('.', 1)
                except ValueError:
                    self.log_error('Unable to parse source title and publication title from source string: {}'.format(source))
                    continue
                
                pub_country = None
                first_paren = pub_title.find('(')
                
                if first_paren > 0:
                    last_paren = pub_title.find(')')
                    pub_country = pub_title[first_paren + 1:last_paren]
                    pub_title = pub_title[:first_paren]
                
                try:
                    pub_country = pub_country.strip()
                    country = Country.objects.get(name=pub_country)
                except (Country.DoesNotExist, AttributeError):
                    # self.log_error('Unable to parse publication country from source string: {}'.format(source))
                    pub_country = None

                # Source URL and archive URL (if they exist) should be after the date.
                
                source_url = None
                urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', after_date)

                if urls:
                    source_url = urls[0]
                
                try:
                    publication = Publication.objects.get(title=pub_title.strip(),
                                                          country=pub_country)
                except Publication.DoesNotExist:
                    publication_id = str(uuid4())
                    publication = Publication.objects.create(title=pub_title.strip(),
                                                             id=publication_id,
                                                             country=pub_country)
                
                source, created = Source.objects.get_or_create(title=source_title.strip(),
                                                               source_url=source_url,
                                                               publication=publication,
                                                               published_on=date,
                                                               user=self.user)
                
                sources.append(source)

        return sources


    def create_person(self, person_data):
        person = None

        person_positions = {
            'Name': {
                'value': 1,
                'confidence': 3,
                'source': 2,
            },
            'Alias': {
                'value': 4,
                'confidence': 6,
                'source': 5,
            },
        }
        membership_positions = {
            'Organization': {
                'value': 7,
                'confidence': 9,
                'source': 8,
            },
            'Role': {
                'value': 10,
                'confidence': 12,
                'source': 11,
            },
            'Title': {
                'value': 13,
                'confidence': 15,
                'source': 14,
            },
            'Rank': {
                'value': 16,
                'confidence': 18,
                'source': 17,
            },
            'FirstCitedDate': {
                'value': 19,
                'confidence': 21,
                'source': 20,
            },
            'StartContext': {
                'value': 23,
                'confidence': 25,
                'source': 24,
            },
            'LastCitedDate': {
                'value': 26,
                'confidence': 28,
                'source': 27,
            },
            'EndContext': {
                'value': 30,
                'confidence': 32,
                'source': 31,
            },
        }
        
        try:
            name_value = person_data[person_positions['Name']['value']]
            confidence = person_data[person_positions['Name']['confidence']]
            source = person_data[person_positions['Name']['source']]
        except IndexError:
            self.log_error('Row seems to be empty')
            return None
        
        if confidence and source:
            
            try:
                confidence = self.get_confidence(confidence)
            except KeyError:
                confidence = None
            
            sources = self.create_sources(source)
            self.stdout.write(self.style.SUCCESS('Working on {}'.format(name_value)))
            
            if confidence and sources:
                
                person_info = {
                    'Person_PersonName': {
                        'value': name_value,
                        'confidence': confidence,
                        'sources': sources
                    },
                    'Person_PersonDivisionId': {
                        'value': 'ocd-division/country:{}'.format(self.country_code),
                        'confidence': confidence,
                        'sources': sources,
                    }
                }
                
                try:
                    person = Person.objects.get(personname__value=name_value)
                    sources = self.sourcesList(person, 'name')
                    person_info["Person_PersonName"]['sources'] += sources
                    person.update(person_info)
                    
                except Person.DoesNotExist:
                    person = Person.create(person_info)
                
                aliases = self.make_relation('Alias', 
                                             person_positions['Alias'], 
                                             person_data, 
                                             person)
                
                # Make membership objects
                try:
                    organization_name = person_data[membership_positions['Organization']['value']]
                except IndexError:
                    self.log_error('Row seems to be empty')
                    return None
                
                try:
                    confidence = self.get_confidence(person_data[membership_positions['Organization']['confidence']])
                except (KeyError, IndexError):
                    self.log_error('Person {0} as a member of {1} has no confidence'.format(name_value, organization_name))
                    return None
                
                try:
                    sources = self.create_sources(person_data[membership_positions['Organization']['source']])
                except (KeyError, IndexError):
                    self.log_error('Person {0} as a member of {1} has no sources'.format(name_value, organization_name))
                    return None
                
                org_info = {
                    'Organization_OrganizationName': {
                        'value': organization_name, 
                        'confidence': confidence,
                        'sources': sources,
                    },
                }
                
                try:
                    organization = Organization.objects.get(organizationname__value=organization_name)
                    organization.update(org_info)
                except Organization.DoesNotExist:
                    organization = Organization.create(org_info)

                membership_data = {
                    'MembershipPerson_MembershipPersonMember': {
                        'value': person,
                        'confidence': confidence,
                        'sources': sources,
                    },
                    'MembershipPerson_MembershipPersonOrganization': { 
                        'value': organization,
                        'confidence': confidence,
                        'sources': sources,
                    }
                }
                
                try:
                    membership = MembershipPerson.objects.get(membershippersonmember__value=person,
                                                              membershippersonorganization__value=organization)
                    sources = set(self.sourcesList(membership, 'member') + \
                                  self.sourcesList(membership, 'organization'))
                    membership_data['MembershipPerson_MembershipPersonMember']['sources'] += sources
                    membership.update(membership_data)

                except MembershipPerson.DoesNotExist:
                    membership = MembershipPerson.create(membership_data)
                
                self.make_relation('Role', 
                                   membership_positions['Role'], 
                                   person_data, 
                                   membership)
                
                self.make_relation('Title', 
                                   membership_positions['Title'], 
                                   person_data, 
                                   membership)
                
                self.make_relation('Rank', 
                                   membership_positions['Rank'], 
                                   person_data, 
                                   membership)
                
                self.make_relation('FirstCitedDate', 
                                   membership_positions['FirstCitedDate'], 
                                   person_data, 
                                   membership)
                
                self.make_relation('StartContext', 
                                   membership_positions['StartContext'], 
                                   person_data, 
                                   membership)
                
                self.make_relation('LastCitedDate', 
                                   membership_positions['LastCitedDate'], 
                                   person_data, 
                                   membership)
                
                self.make_relation('EndContext', 
                                   membership_positions['EndContext'], 
                                   person_data, 
                                   membership)
                
                self.stdout.write(self.style.SUCCESS('Created {}'.format(person.get_value())))

            else:
                self.log_error('{} did not have a confidence or source'.format(name_value))

    def create_event(self, event_data):
        positions = {
            'StartDate': {
                'value': 1,
                'source': 14,
                'model_field': 'violationstartdate',
            },
            'EndDate': {
                'value': 2,
                'source': 14,
                'model_field': 'violationenddate',
            },
            'LocationDescription': {
                'value': 3,
                'source': 14,
                'model_field': 'violationlocationdescription',
            },
            'Type': {
                'value': 9,
                'source': 14,
                'model_field': 'violationtype',
            },
            'Description': {
                'value': 10,
                'source': 14,
                'model_field': 'violationdescription',
            },
            'GeonameId': {
                'value': 5,
                'source': 14,
            },
            'Perpetrator': {
                'value': 11,
                'source': 14
            },
            'PerpetratorOrganization': {
                'value': 12,
                'source': 14
            },
            'PerpetratorClassification': {
                'value': 13,
                'source': 14
            }
        }

        with reversion.create_revision():
            violation = Violation()
            violation.save()
            reversion.set_user(self.user)

        self.make_relation('StartDate', 
                           positions['StartDate'], 
                           event_data, 
                           violation)
        
        self.make_relation('EndDate', 
                           positions['EndDate'], 
                           event_data, 
                           violation)
        
        self.make_relation('LocationDescription', 
                           positions['LocationDescription'], 
                           event_data, 
                           violation)
        
        self.make_relation('Type', 
                           positions['Type'], 
                           event_data, 
                           violation)
        
        self.make_relation('Description', 
                           positions['Description'], 
                           event_data, 
                           violation)
       
        try:
            sources = self.create_sources(event_data[positions['GeonameId']['source']])
        except IndexError:
            self.log_error('Row seems to be blank')
            return None
        
        # Make geoname stuff
        
        try:
            geoname_id = event_data[positions['GeonameId']['value']]
        except IndexError:
            geoname_id = None

        if geoname_id:
            
            try:
                geo = get_geoname_by_id(geoname_id)
            except DataError:
                self.log_error('Geoname ID for Site does not seem valid: {}'.format(geoname_id))
                geo = None

            if geo:
                parent = geo.parent
                admin1 = parent.name
                admin2 = getattr(parent.parent, 'name', None)
                coords = getattr(geo, 'location', None)
                
                if isinstance(geo, Country):
                    country_code = geo.code.lower()
                elif isinstance(geo, Region):
                    country_code = geo.country.code.lower()
                elif isinstance(geo, Subregion) or isinstance(geo, City):
                    country_code = geo.region.country.code.lower()
                
                division_id = 'ocd-division/country:{}'.format(country_code)
                
                event_info = {
                    'Violation_ViolationAdminLevel1': {
                        'value': admin1,
                        'confidence': 1,
                        'sources': sources
                    },
                    'Violation_ViolationAdminLevel1': {
                        'value': admin1,
                        'sources': sources,
                        'confidence': 1
                    },
                    'Violation_ViolationAdminLevel2': {
                        'value': admin2,
                        'sources': sources,
                        'confidence': 1
                    },
                    'Violation_ViolationGeoname': {
                        'value': geo.name,
                        'sources': sources,
                        'confidence': 1
                    },
                    'Violation_ViolationGeonameId': {
                        'value': geo.id,
                        'sources': sources,
                        'confidence': 1
                    },
                    'Violation_ViolationDivisionId': {
                        'value': division_id,
                        'sources': sources,
                        'confidence': 1
                    },
                    'Violation_ViolationLocation': {
                        'value': coords,
                        'sources': sources,
                        'confidence': 1
                    },
                }

                violation.update(event_info)
        
        # Record perpetrators
        
        try:
            perpetrator = event_data[positions['Perpetrator']['value']]
        except IndexError:
            perpetrator = None

        if perpetrator:
            
            perps = perpetrator.split(';')
            for perp in perps:
                try:
                    person = Person.objects.get(personname__value=perp)
                except Person.DoesNotExist:
                    person_info = {
                        'Person_PersonName': {
                            'value': perp,
                            'confidence': 1,
                            'sources': sources,
                        }
                    }
                    person = Person.create(person_info)

                vp, created = ViolationPerpetrator.objects.get_or_create(value=person,
                                                                         object_ref=violation)
                with reversion.create_revision():
                    for source in sources:
                        vp.sources.add(source)
                    vp.save()
                    reversion.set_user(self.user)
                


        try:
            perp_org = event_data[positions['PerpetratorOrganization']['value']]
        except IndexError:
            perp_org = None

        if perp_org:
            for org in perp_org.split(';'):
                
                try:
                    organization = Organization.objects.get(id=org)
                except (Organization.DoesNotExist, ValueError):
                    info = {
                        'Organization_OrganizationName': {
                            'value': org,
                            'confidence': 1,
                            'sources': sources,
                        }
                    }
                    organization = Organization.create(info)

                vpo_obj, created = ViolationPerpetratorOrganization.objects.get_or_create(value=organization,
                                                                                          object_ref=violation)
                
                with reversion.create_revision():
                    for source in sources:
                        vpo_obj.sources.add(source)
                    vpo_obj.save()
                    reversion.set_user(self.user)
        
        self.make_relation('PerpetratorClassification', 
                           positions['PerpetratorClassification'], 
                           event_data, 
                           violation)
