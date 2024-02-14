import json
import urllib.request

import openai
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render

from .models import ClimateData, UserSubscription
import replicate
import boto3
import os

def index(request):
    if request.method == 'POST':
        if 'address' in request.POST:
            address = request.POST.get('address')
            climate_data = get_weather_data(address)
            is_weather_worsening = check_weather_worsening(climate_data)
            subscriptions_count = UserSubscription.objects.count()
            if is_weather_worsening:
                query = f"The weather condition is worsening. What precautions should be taken? Weather data is {climate_data}"
                precautions = process_precaution_with_weather(query)
                print(precautions)
                session = boto3.Session(
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_ACCESS_KEY_ID')  # Optional, if you didn't set a default region
                )
                sns_client = session.client('sns')
                message = f"New weather data available for {address}. Precautions:\n{precautions}."
                sns_client.publish(TopicArn='arn:aws:sns:us-east-2:510794644386:weather-aleart', Message=message)

            return render(request, 'index.html', {
                'climate_data': climate_data,
                'subscriptions_count': subscriptions_count,
                'is_weather_worsening': is_weather_worsening,
                'subscriptions': UserSubscription.objects.all()
            })
        else:
            email = request.POST.get('email')
            # Implement email validation here
            if not UserSubscription.objects.filter(email=email).exists():
                subscription = UserSubscription.objects.create(email=email)

                # Add SNS subscription here
                sns_client = boto3.Session(
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_ACCESS_KEY_ID')  # Optional, if you didn't set a default region
                ).client('sns')

                try:
                    # Replace with your actual topic ARN
                    response = sns_client.subscribe(
                        Protocol='email',
                        TopicArn=os.getenv('TopicArn'),
                        Endpoint=email,
                        AutoConfirm=True
                    )
                    subscription_arn = response['SubscriptionArn']
                    subscription.subscription_arn = subscription_arn
                    subscription.save()
                    print(f"Subscribed email: {email} with ARN: {subscription_arn}")
                except Exception as e:
                    print(f"Failed to subscribe email: {e}")

    return render(request, 'index.html', {
        'climate_data': ClimateData.objects.all(),
        'subscriptions_count': UserSubscription.objects.count(),
        'is_weather_worsening': False,
        'subscriptions': UserSubscription.objects.all()
    })


def get_weather_data(location):
    weather_api_key = "3R9H5TC8JCFMKSST67KRLJBA4"
    location = location.replace(' ', '%20')

    if not location:
        return {"error": "Location parameter is required."}

    try:
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}?unitGroup=us&elements=datetime%2Ctemp%2Cfeelslike%2Chumidity%2Cprecip%2Cpreciptype%2Cwindspeed&include=days&key={weather_api_key}&contentType=json"
        response = urllib.request.urlopen(url)
        response_content = response.read().decode('utf-8')
        data = json.loads(response_content)
        return data.get("days", [])[:5]  # Return all weather data
    except Exception as e:
        return {"error": f"Failed to fetch weather data: {e}"}


def check_weather_worsening(climate_data):
    # Check if there are at least 5 days of climate data
    if len(climate_data) < 5:
        return False

    # Initialize variables to track trends
    worst_condition = 5
    temperature_trend = 0  # 0: Stable, 1: Increasing, -1: Decreasing
    humidity_trend = 0
    wind_speed_trend = 0
    # Iterate through the climate data for the next 5 days
    for i in range(4):
        # Compare temperature
        if climate_data[i]['temp'] + worst_condition < climate_data[i + 1]['temp']:
            temperature_trend = 1
        elif climate_data[i]['temp'] > climate_data[i + 1]['temp']:
            temperature_trend = -1

        # Compare humidity
        if climate_data[i]['humidity'] + worst_condition < climate_data[i + 1]['humidity']:
            humidity_trend = 1
        elif climate_data[i]['humidity'] > climate_data[i + 1]['humidity']:
            humidity_trend = -1

        # Compare wind speed
        if climate_data[i]['windspeed'] + worst_condition < climate_data[i + 1]['windspeed']:
            wind_speed_trend = 1
        elif climate_data[i]['windspeed'] > climate_data[i + 1]['windspeed']:
            wind_speed_trend = -1

        # Check if any trend is worsening
        if temperature_trend == 1 or humidity_trend == 1 or wind_speed_trend == 1:
            return True  # Weather condition is worsening

    return False  # Weather condition is not worsening over the next 5 days


def process_precaution_with_weather(query):
    try:
        rep = replicate.Client(api_token=os.getenv('llm_api'))
        output = rep.run(
            "meta/llama-2-70b-chat:2d19859030ff705a87c746f7e96eea03aefb71f166725aee39692f1476566d48",
            input={
                "debug": False,
                "top_p": 1,
                "prompt": query,
                "temperature": 0.5,
                "system_prompt": "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.\n\nIf a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.",
                "max_new_tokens": 500,
                "min_new_tokens": -1
            }
        )
        # The yorickvp/llava-13b model can stream output as it's running.
        # The predict method returns an iterator, and you can iterate over that output.
        sentence = ""
        for item in output:
            # https://replicate.com/yorickvp/llava-13b/api#output-schema
            sentence += f"{item} "
        return sentence
    except Exception as e:
        return f"LLM MODEL ERROR: MODEL FAILED!! PLEASE TRY AGAIN AFTER SOMETIME, THANK YOU FOR TRYING OUT THE SYSTEM!!!\n{e}"


def remove_subscription(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        print("inside post")
        if email:
            try:
                subscription = UserSubscription.objects.get(email=email)
                subscription_arn = subscription.subscription_arn  # Access stored ARN
                subscription.delete()

                # Unsubscribe using saved ARN
                session = boto3.Session(
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_ACCESS_KEY_ID')  # Optional, if you didn't set a default region
                )
                sns_client = session.client('sns')

                try:
                    # Use list_subscriptions_by_topic to find the subscription
                    response = sns_client.list_subscriptions_by_topic(
                        TopicArn='arn:aws:sns:us-east-2:510794644386:weather-aleart'
                    )
                    print(response)
                    for sub in response['Subscriptions']:
                        if sub['Endpoint'] == email:
                            subscription_arn = sub['SubscriptionArn']
                            subscription.subscription_arn = subscription_arn
                            subscription.save()
                            print(f"Found subscription ARN: {subscription_arn} for email: {email}")
                            try:
                                sns_client.unsubscribe(
                                    SubscriptionArn=subscription_arn
                                )
                                print(f"Unsubscribed email: {email}")
                            except Exception as e:
                                print(f"Failed to unsubscribe email: {e}")

                    if not subscription.subscription_arn:
                        raise Exception(f"Subscription not found for email: {email}")

                except Exception as e:
                    print(f"Failed to fetch subscription ARN: {e}")

                # try:
                #     sns_client.unsubscribe(
                #         SubscriptionArn=subscription_arn
                #     )
                #     print(f"Unsubscribed email: {email}")
                # except Exception as e:
                #     print(f"Failed to unsubscribe email: {e}")

                return HttpResponseRedirect('/')  # Replace with your desired action

            except UserSubscription.DoesNotExist:
                pass

    return render(request, 'index.html', {
        'climate_data': ClimateData.objects.all(),
        'subscriptions_count': UserSubscription.objects.count(),
        'is_weather_worsening': False,
        'subscriptions': UserSubscription.objects.all()
    })
