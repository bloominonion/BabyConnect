from os import environ, path
import copy
import datetime

thisDir = path.dirname(__file__)

import sys
sys.path.append(path.join(thisDir,"../WebLogin"))
sys.path.append(path.join(thisDir,"../SqsListener"))

import functools
print = functools.partial(print, flush=True)

logFile = path.join(thisDir, "Logfile.txt")
print ("Using logfile:", logFile)
logHandle = open(logFile, "a+")
sys.stdout = logHandle
sys.stderr = logHandle

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
    global logHandle
    print ("Starting service...", datetime.datetime.now().strftime("%m-%d-%y %I:%M %p"), file=sys.stdout)
    timeSleep = 5 #(minutes)
    connectionSleep = 5
    watchdog = Watchdog(BabyConnect)
    checkCount = 0
    while True:
        logHandle.write(".")
        
        # Make sure there is internet before continuing.
        while not internet():
            print ("Failed to connect to internet..trying again in {} minutes".format(connectionSleep), file=sys.stdout)
            time.sleep(connectionSleep*60)
            connectionSleep *= 2
            
        connectionSleep = timeSleep
        checkCount += 1
        curTime = datetime.datetime.now()
        if abs(curTime.hour - 1) < 0.1:
            time.sleep(5*60*60) #sleep 5 hours
        if checkCount % 10 == 0:
            print ("Checking server for requests...{}: {}".format(checkCount, curTime.strftime("%m-%d-%y %I:%M %p")), file=sys.stdout)
        requests = GetAwsMessages()
        watchdog.check()
        logs = []
        for request in requests:
            result = ConvertRequest(request)
            if result is not None:
                logs.append(result)

        if len(logs) > 0:
            print ("\nRequests to log:")
            print (len(logs), "logs found")
            print (logs)
            with BabyConnect.WebInterface(user=auth.GetUser(), password=auth.GetPassword()) as connection:
                for log in logs:
                    if isinstance(log, BabyConnect.Nursing):
                        connection.LogNursing(log)
                        print (log)
                    elif isinstance(log, BabyConnect.Diaper):
                        connection.LogDiaper(log)
                        print (log)
                    else:
                        print ("Unable to handle log:", log)
        #else:
        #    print ("...No logs found")
        time.sleep(timeSleep*60)

def internet(host="8.8.8.8", port=53, timeout=3):
   """
   Host: 8.8.8.8 (google-public-dns-a.google.com)
   OpenPort: 53/tcp
   Service: domain (DNS/TCP)
   """
   try:
      socket.setdefaulttimeout(timeout)
      socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
      return True
   except Exception as ex:
      print (ex.message)
      return False

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
    if nMessages == 0:
        return list()

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

# Convert requests to an instance known to the web interface
def ConvertRequest(request):
    global nursingRequests
    intent = request['action']
    if 'LogDiaper' in intent:
        diaper = BabyConnect.Diaper(request['intent'])
        return diaper
    elif 'Nursing' in intent:
        nursingRequests.append(request)
        if 'Complete' in intent:
            return HandleNursingRequests()
    else:
        print ("Swing and a miss...")
        return None
    return None

# If it is a nursing message, build the nursing session up until 
# and end message is encountered. Once that is, log the actual request
# to the website
def HandleNursingRequests():
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
                tmpNursing = copy.copy(nursing)
                nursingRequests = []
                nursing=None
                return tmpNursing
        else:
            print("Bad request out of order...")


if __name__ == '__main__':
    main()
