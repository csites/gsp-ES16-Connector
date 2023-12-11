""" 
Send a test putt.  This is a small program to send a test putt
to the putt server
"""
import requests

# Data that we will send in post request.
speed = 4.5
launchDirection = -0.145
totalSpin=100


loop = True

while loop == True:
  data = {"ballData":{"BallSpeed":"%.2f" % speed,"TotalSpin":totalSpin,"LaunchDirection":"%.2f" % launchDirection}}
  try:
      res = requests.post('http://127.0.0.1:8888/putting', json=data)
      res.raise_for_status()
      # Convert response data to json
      returned_data = res.json()
  
      print(returned_data)
      result = returned_data['result']
      print("Response from Node.js:", result)
      launchDirection = launchDirection + 0.01
      
  except requests.exceptions.HTTPError as e:  # This is the correct syntax
      print(e)
      loop = False
  except requests.exceptions.RequestException as e:  # This is the correct syntax
      print(e)
      loop = False
