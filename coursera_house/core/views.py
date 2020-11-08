from django.urls import reverse_lazy
from django.views.generic import FormView
from django.http import JsonResponse

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import requests

import json

from .models import Setting
from .form import ControllerForm

url = settings.SMART_HOME_API_URL

class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()

        controllers = Setting.objects.exclude(controller_name__contains='target')

        context['data'] = {}
        for item in controllers:
            if item.value == 0 or item.value == 1:
                context['data'][item.controller_name] = bool(item.value)
            elif item.value > 100:
                context['data'][item.controller_name] = item.label
            else:
                context['data'][item.controller_name] = item.value

        return context

    def get_initial(self):
        bedroom_target_temperature, created_bedroom = \
            Setting.objects.get_or_create(controller_name='bedroom_target_temperature', defaults = {'value': 21, 'label': ''})
        hot_water_target_temperature, created_hot_water = \
            Setting.objects.get_or_create(controller_name='hot_water_target_temperature', defaults = {'value': 80, 'label': ''})

        try:
            bedroom_light = Setting.objects.get(controller_name='bedroom_light')
            bathroom_light = Setting.objects.get(controller_name='bathroom_light')

            initial = {'bedroom_target_temperature': bedroom_target_temperature.value,
                       'hot_water_target_temperature': hot_water_target_temperature.value,
                       'bedroom_light': bool(bedroom_light.value),
                       'bathroom_light': bool(bathroom_light.value)
                       }
        except ObjectDoesNotExist:
            print('First exception occurred.')

            initial = {'bedroom_target_temperature': bedroom_target_temperature.value,
                       'hot_water_target_temperature': hot_water_target_temperature.value
                       }
        return initial

    def form_valid(self, form):
        try:
            bedroom_target_temperature = Setting.objects.get(controller_name='bedroom_target_temperature')
            hot_water_target_temperature = Setting.objects.get(controller_name='hot_water_target_temperature')
            bedroom_target_temperature.value = form.cleaned_data['bedroom_target_temperature']
            hot_water_target_temperature.value = form.cleaned_data['hot_water_target_temperature']
            bedroom_target_temperature.save()
            hot_water_target_temperature.save()
        except ObjectDoesNotExist:
            print('Second exception occurred.')

        data = {
            "controllers": [
                {
                    "name": "bedroom_light",
                    "value": form.cleaned_data['bedroom_light']
                },
                {
                    "name": "bathroom_light",
                    "value": form.cleaned_data['bathroom_light']
                }
            ]
        }
        try:
            response = requests.post(url, headers={"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"},
                                     data=json.dumps(data)
                                     )
            print(json.loads(response.content)['status'])

        except Exception as e:
            template = "An exception of type {} occurred. Arguments:\n{!r}"
            mes = template.format(type(e).__name__, e.args)
            print(mes)
            return JsonResponse(response, status=502)

        return super(ControllerView, self).form_valid(form)