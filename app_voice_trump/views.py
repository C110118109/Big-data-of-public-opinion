from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd

def load_data_trump():
    # Read data from csv file
    df_data = pd.read_csv('app_voice_trump/dataset/Trump_data.csv',sep=',')
    global response
    response = dict(list(df_data.values))
    del df_data

# load data
load_data_trump()

#print(response)

def home(request):
    return render(request,'app_voice_trump/home.html', response)

print('app_voice_trump was loaded!')
