from os import environ
from os.path import basename, join, exists
from BabyConnect import LogTypes
import copy
import socket
import boto3

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

class AwsMessageHandler(object):
    def __init__(self, queue_name=None, aws_key_id=None, aws_secret_key=None, aws_region=None):
        self.key_id = aws_key_id
        self.key = aws_secret_key
        self.region = aws_region
        self.queue_name = queue_name
        self.requests = []
        self.nursingRequests = []
        self.configured = False
        

    def AssignQueueName(self, name):
        if name is None or not isinstance(name, str):
            raise ValueError("Queue name is invalid")
        self.queue_name = name

    def ConfigureSessionCredentials(self, aws_key_id, aws_secret_key, aws_region):
        self.key_id = aws_key_id
        self.key = aws_secret_key
        self.region = aws_region
        self.configured = True

    def _CheckIfConfigured(self):
        missing = []
        if self.key_id is None:
            missing.append('aws_key_id')
        if self.key is None:
            missing.append('aws_secret_key')
        if self.region is None:
            missing.append('aws_region')
        if self.queue_name is None:
            missing.append('aws_queue_name')
        if len(missing) > 0:
            raise AttributeError("Not configured. Missing the following:" + str(missing))

    def GetLogs(self):
        self._GetNewMessages()
        logs = []
        for log in self.requests:
            action = self._ConvertRequest(log)
            if action is not None:
                logs.append(action)
        self.requests = []
        return logs

    def _GetNewMessages(self):
        self._CheckIfConfigured()

        queue = self._GetQueue()

        client = boto3.client('sqs',
                              region_name=self.region,
                              aws_access_key_id=self.key_id,
                              aws_secret_access_key=self.key)
        nMessages = self._HasMessages(client, queue)
        if nMessages > 0:
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
            self.requests += requests


    def _GetQueue(self):
        sqs = boto3.resource('sqs',
                              region_name=self.region,
                              aws_access_key_id=self.key_id,
                              aws_secret_access_key=self.key)
        queue = sqs.get_queue_by_name(QueueName=self.queue_name)
        return queue

    def _HasMessages(self, client, queue):
        queue_attributes = client.get_queue_attributes(QueueUrl=queue.url, 
                                                       AttributeNames=['ApproximateNumberOfMessages'])
        nMessages = int(queue_attributes['Attributes']['ApproximateNumberOfMessages'])
        if nMessages == 0:
            return 0
        return nMessages

    # Convert requests to an instance known to the web interface
    def _ConvertRequest(self, request):
        intent = request['action']
        if 'LogDiaper' in intent:
            diaper = LogTypes.Diaper(request['intent'])
            return diaper
        elif 'Nursing' in intent:
            self.nursingRequests.append(request)
            if 'Complete' in intent:
                return self._HandleNursingRequests()
        else:
            print ("Swing and a miss...")
            return None
        return None

    # If it is a nursing message, build the nursing session up until 
    # and end message is encountered. Once that is, log the actual request
    # to the website
    def _HandleNursingRequests(self):
        nursing = None
        for request in self.nursingRequests:
            intent = request['action']
            reqTime = request['time']
            if 'NursingIntent' in intent:
                side = 0
                if request['intent'] == 'right':
                    side = 1
                nursing = LogTypes.Nursing(side=side, epoch=reqTime)
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
                    self.nursingRequests = []
                    nursing=None
                    return tmpNursing
            else:
                print("Bad request out of order...")
