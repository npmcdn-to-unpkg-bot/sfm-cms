from django.conf.urls import patterns, url

from .views import EventCreate, EventUpdate, event_csv

urlpatterns = [
    url(r'^create/$', EventCreate.as_view(), name="create-event"),
    url(r'csv/', event_csv, name='event_csv'),
    url(r'(?P<pk>\d+)/$', EventUpdate.as_view(), name='edit_event'),
]
