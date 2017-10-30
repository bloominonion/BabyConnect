from os import environ
from os.path import basename, join, exists
import copy
import socket
from pkg_resources import resource_filename

# Global for storing nursing requests as we get them
nursingRequests = list()

def SetupAwsCredentials():
    '''
    Sets up the environment variables for the AWS boto3 interface to find 
    credential and configuration information.
    '''
    aws_credentials = resource_filename('BabyConnect.Sqs', 'aws_credentials')
    aws_config = resource_filename('BabyConnect.Sqs', 'aws_config')
    if not exists(aws_credentials) or not exists(aws_config):
        print ("aws_credentials:", aws_credentials)
        print ("aws_config:", aws_config)
        raise OSError("Could not find credentials directory. Listener must have a folder '.aws' with credential info.")
    environ['AWS_SHARED_CREDENTIALS_FILE'] = aws_credentials
    environ['AWS_CONFIG_FILE'] = aws_config

def CheckInternet(host="8.8.8.8", port=53, timeout=3):
   """
   Check for an internet connection.
   Host: 8.8.8.8 (google-public-dns-a.google.com)
   OpenPort: 53/tcp
   Service: domain (DNS/TCP)
   """
   try:
      socket.setdefaulttimeout(timeout)
      socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
      return True
   except Exception as ex:
      print (ex)
      return False

# Collects the messages from the aws sqs queue and puts them into an ordered set.
def GetAwsMessages():
    SetupAwsCredentials()
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
