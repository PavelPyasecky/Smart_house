from __future__ import absolute_import, unicode_literals
from django.core.exceptions import ObjectDoesNotExist

from celery import task
import requests
import json
from .models import Setting
from django.conf import settings
from django.core.mail import send_mail


url = settings.SMART_HOME_API_URL


def update_controller(name, value):

    str_value = str(value).lower()
    if str_value.isdigit() or value in [True, False]:
        controller_value = int(value)
        controller_label = ''
    else:
        controller_label = str_value
        controller_value = 101

    defaults = {'value': controller_value,
                'label': controller_label
                }

    controller, created = \
        Setting.objects.update_or_create(controller_name=name, defaults=defaults)
    #print('{}--------------- Was created?-----------{}'.format(name, created))


def change_state_controller_dict(dict):
    try:
        data = {"controllers": []}
        for key, value in dict.items():
            data["controllers"].append({
                        "name": key,
                        "value": value
                    }
            )
        #print(dict)
    except ObjectDoesNotExist:
        print('Third error occurred!')
        data = {}
    response = requests.post(url, headers={"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"},
                                 data=json.dumps(data)
                                 )
    data = json.loads(response.content)
    #print('{} --> !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'.format(data['status']))
    return json.loads(response.content)['status']



def control_data():
    try:
        bedroom_target_temperature, created_bedroom = \
            Setting.objects.get_or_create(controller_name='bedroom_target_temperature', defaults = {'value': 21, 'label': ''})
        hot_water_target_temperature, created_hot_water = \
            Setting.objects.get_or_create(controller_name='hot_water_target_temperature', defaults = {'value': 80, 'label': ''})

        smoke_detector = Setting.objects.get(controller_name='smoke_detector')
        leak_detector = Setting.objects.get(controller_name='leak_detector')
        cold_water = Setting.objects.get(controller_name='cold_water')
        hot_water = Setting.objects.get(controller_name='hot_water')
        boiler_temperature = Setting.objects.get(controller_name='boiler_temperature')
        bedroom_temperature = Setting.objects.get(controller_name='bedroom_temperature')
        outdoor_light = Setting.objects.get(controller_name='outdoor_light')
        bathroom_light = Setting.objects.get(controller_name='bathroom_light')
        bedroom_light = Setting.objects.get(controller_name='bedroom_light')
        curtains = Setting.objects.get(controller_name='curtains')
        boiler = Setting.objects.get(controller_name='boiler')
        washing_machine = Setting.objects.get(controller_name='washing_machine')
        air_conditioner = Setting.objects.get(controller_name='air_conditioner')
        dict = {}

        if leak_detector.value:
            send_mail("This is a WARNING message from your smart home!",
                      'Troubles with leak detector!',
                      "pyasecky2010pavel@mail.ru",
                      [settings.EMAIL_RECEPIENT],
                      )

            if cold_water.value:
                dict['cold_water'] = False
            if hot_water.value:
                dict['hot_water'] = False
            if boiler.value:
                dict['boiler'] = False
            if washing_machine.label != 'off':
                dict['washing_machine'] = 'off'

        if smoke_detector.value:
            if air_conditioner.value:
                dict['air_conditioner'] = False
            if bedroom_light.value:
                dict['bedroom_light'] = False
            if bathroom_light.value:
                dict['bathroom_light'] = False
            if boiler.value and 'boiler' not in dict.values():
                dict['boiler'] = False
            if washing_machine.label != 'off' and 'washing_machine' not in dict.values():
                dict['washing_machine'] = 'off'

            if dict:
                change_state_controller_dict(dict)
            return
        else:
            if not cold_water.value and 'cold_water' not in dict.values():
                if boiler.value and 'boiler' not in dict.values():
                    dict['boiler'] = False
                if washing_machine.label != 'off' and 'washing_machine' not in dict.values():
                    dict['washing_machine'] = 'off'
            else:

                if boiler_temperature.value < hot_water_target_temperature.value * 0.9 and boiler.value == 0 and 'boiler' not in dict.values():
                    dict['boiler'] = True
                if boiler_temperature.value > hot_water_target_temperature.value * 1.1 and boiler.value  and 'boiler' not in dict.values():
                    dict['boiler'] = False

            if bedroom_temperature.value < bedroom_target_temperature.value * 0.9 and air_conditioner.value and 'air_conditioner' not in dict.values():
                dict['air_conditioner'] = False
            if bedroom_temperature.value > bedroom_target_temperature.value * 1.1 and air_conditioner.value == 0 and 'air_conditioner' not in dict.values():
                dict['air_conditioner'] = True

            if not curtains.label == 'slightly_open':
                if outdoor_light.value < 50 and not bedroom_light.value and curtains.label == 'close':
                    dict['curtains'] = 'open'
                if outdoor_light.value > 50 or bedroom_light.value:
                    if curtains.label == 'open':
                        dict['curtains'] = 'close'
            if dict:
                change_state_controller_dict(dict)

    except ObjectDoesNotExist:
        print('Fourth error occurred!')


@task()
def smart_home_manager():
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"})
        data = json.loads(response.content)["data"]
        for item in data:
            update_controller(item['name'], item['value'])

        control_data()
    except Exception as e:
        template = "An exception of type {} occured. Arguments:\n{!r}"
        mes = template.format(type(e).__name__, e.args)
        print(mes)





