from os import environ, path
import datetime

thisDir = path.dirname(__file__)

import sys
sys.path.append(path.join(thisDir,"../WebLogin"))
sys.path.append(path.join(thisDir,"../SqsListener"))

import BabyConnect
import Authorization as auth
from LazyDaemon import Watchdog
import time
try:
   import boto3
except ImportError:
   import pip
   pip.main(['install', 'boto3'])
   import boto3

# Global for storing nursing requests as we get them
nursingRequests = list()

def main():
    timeSleep = 5 #(minutes)
    watchdog = Watchdog(BabyConnect)
    while True:
        print ("Checking server for requests...", datetime.datetime.now().strftime("%m-%d-%y %I:%M %p"))
        requests = GetAwsMessages()
        watchdog.check()
        if len(requests) > 0:
            with BabyConnect.WebInterface(user=auth.GetUser(), password=auth.GetPassword()) as connection:
                print ("Requests to log:")
                for request in requests:
                    print (request)
                    # print ("{r[time]} : Request to log action {r[action]} of type {r[intent]}".format(r=request))
                    LogRequest(connection, request)
        time.sleep(timeSleep*60)


# Collects the messages from the aws sqs queue and puts them into an ordered set.
def GetAwsMessages():
    global thisDir
    environ['AWS_SHARED_CREDENTIALS_FILE'] = path.join(thisDir, "..", ".aws/credentials")
    environ['AWS_CONFIG_FILE'] = path.join(thisDir, "..", ".aws/config")

    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='BabyConnectLogger')

    client = boto3.client('sqs')
    queue_attributes = client.get_queue_attributes(QueueUrl=queue.url, AttributeNames=['ApproximateNumberOfMessages'])
    nMessages = int(queue_attributes['Attributes']['ApproximateNumberOfMessages'])

    # Poll the queue and get the messages. Multiple polling is needed to
    # ensure we get all of them (hence using a set)
    # This is a documented limitation to the sqs queue where it may not recieve a message if
    # the queue has a small number of messages in it. 
    messages = set()
    pollCount = 0
    while len(messages) < nMessages:
        for message in queue.receive_messages(MessageAttributeNames=['LogAction', 'LogIntent', 'TimeSec']):
            messages.add(message)
            message.delete()
        pollCount += 1
        if pollCount > 2*nMessages:
            break
    
    # Process the messages recieved into a simple format for use (discard extra info)
    requests = []
    for message in messages:
        # print (message.body, ":", message.message_attributes)
        if message.message_attributes is not None:
            action = message.message_attributes.get('LogAction').get('StringValue')
            intent = message.message_attributes.get('LogIntent').get('StringValue')
            time = message.message_attributes.get('TimeSec').get('StringValue')
            requests.append({'time':float(time), 'action':action, 'intent':intent})
            # print ("Request to log action {} of type {}".format(action, intent))

    requests = sorted(requests, key=lambda k: k['time']) 
    return requests

# Handle incoming request
def LogRequest(con, request):
    global nursingRequests
    intent = request['action']
    if 'LogDiaper' in intent:
        diaper = BabyConnect.Diaper(request['intent'])
        if con is not None:
            con.LogDiaper(diaper)
    elif 'Nursing' in intent:
        nursingRequests.append(request)
        if 'Complete' in intent:
            LogNursingRequest(con)
    else:
        print ("Swing and a miss...")

# If it is a nursing message, build the nursing session up until 
# and end message is encountered. Once that is, log the actual request
# to the website
def LogNursingRequest(con):
    global nursingRequests
    nursing = None
    for request in nursingRequests:
        intent = request['action']
        reqTime = request['time']
        if 'NursingIntent' in intent:
            side = 0
            if request['intent'] == 'right':
                side = 1
            nursing = BabyConnect.Nursing(side=side, epoch=reqTime)
            continue
        if nursing is not None:
            if 'NursingSwitchIntent' in intent:
                nursing.Switch(epoch=reqTime)
            elif 'NursingPauseIntent' in intent:
                nursing.Pause(epoch=reqTime)
            elif 'NursingResumeIntent' in intent:
                nursing.Resume(epoch=reqTime)
            elif 'NursingCompleteIntent' in intent:
                nursing.GetTimes(epoch=reqTime)
                nursing.Finish(epoch=reqTime)
                if con is not None:
                    con.LogNursing(nursing)
                print (nursing)
                nursingRequests = []
                nursing=None
        else:
            print("Bad request out of order...")


if __name__ == '__main__':
    main()