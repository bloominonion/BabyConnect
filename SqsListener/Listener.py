import sys
sys.path.append("../WebLogin")
import BabyConnect
try:
   import boto3
except ImportError:
   import pip
   pip.main(['install', 'boto3'])
   import boto3


def main():
    requests = GetAwsMessages()
    print ("Requests to log:")
    for request in requests:
        print (request)
        # print ("{r[time]} : Request to log action {r[action]} of type {r[intent]}".format(r=request))



def GetAwsMessages():
    from os import environ, path
    environ['AWS_SHARED_CREDENTIALS_FILE'] = path.join(path.dirname(__file__), "..", ".aws/credentials")
    environ['AWS_CONFIG_FILE'] = path.join(path.dirname(__file__), "..", ".aws/config")

    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='BabyConnectLogger')

    # Poll the queue and get the messages. Multiple polling is needed to
    # ensure we get all of them (hence using a set)
    messages = set()
    for i in range (5):
        for message in queue.receive_messages(MessageAttributeNames=['LogAction', 'LogIntent', 'TimeSec'], WaitTimeSeconds=5):
            messages.add(message)
            # message.delete()
    
    # Process the messages recieved into a simple format for use (discard extra info)
    requests = []
    for message in messages:
        print (message.body, ":", message.message_attributes)
        if message.message_attributes is not None:
            action = message.message_attributes.get('LogAction').get('StringValue')
            intent = message.message_attributes.get('LogIntent').get('StringValue')
            time = message.message_attributes.get('TimeSec').get('StringValue')
            requests.append({'time':float(time), 'action':action, 'intent':intent})
            # print ("Request to log action {} of type {}".format(action, intent))

    requests = sorted(requests, key=lambda k: k['time']) 
    return requests

def LogRequest(con, request):
    if 'LogDiaper' in request['action']:
        con.LogDiaper(request['intent'])
    elif 'LogNursing' in request['action']:
        pass


if __name__ == '__main__':
    main()