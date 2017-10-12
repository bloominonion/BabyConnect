# BabyConnect
## Why:
This project was started as a way to make my wife happier and help with tracking our baby's habits/health using BabyConnect.
I would probably use one of the other skills on GitHub, but none of them support nursing 
since it is an ongoing operation. To get around this I wrote my own in a way that I could
handle starting and stopping a nursing session without keeping the Echo busy by collecting
requests on the server side.
Currently this tool is setup to support logging of nursing sessions and diapers only.
It also only supports a single child and has no ability for multiple users.
Adding more abilities and children should be relatively simple using Selenium.

## What is it: 
This is a method to login to the BabyConnect website and create entries into their system. 
Since there is no API for their website, Selenium was used to allow a headless browser to 
perform the necessary operations for creating entries.

There are two options on how to use this skill.
### Option 1: FlaskAsk Alexa skill
This was the easiest to implement, but required setting up an https endpoint to serve the requests to Alexa. 
Since I didn't really want to do this, I moved on to option 2.

With this option, you just have to setup the FlaskAsk skill (AlexaSkill/AlexaService.py) to serve any requests from Alexa, and it will automatically
the tasks.

### Option 2: Alexa skill + AWS Lambda + SQS Message Queue + Raspberry Pi
This method is much more involved, but required little in the way of security on my part.
There is an Alexa skill served by an AWS skill that generates an SQS message. The messages
will be collected and processed by a Raspberry Pi (or any random machine) that will pull
the messages and perform the work using Selenium.

Alexa Skill:
Setup an Alexa skill using an AWS Lambda written in Python 3+ that will post a message to the
SQS messaging queue. The only main setup here is to add the AWS skill as authorized to use the queue
and the Alexa Skill must be authorize through the AWS Lambda user policy.

Once the queue is setup and recieving messages, the Python script can be run on a machine that polls the server at an
interval (I used 5 minutes) and will compile the messages into an action.
