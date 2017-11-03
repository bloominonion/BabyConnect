from os import environ, path
import boto3
import time

# Credentials for testing outside of lambda function
# environ['AWS_SHARED_CREDENTIALS_FILE'] = path.join(path.dirname(__file__), "..", ".aws/credentials")
# environ['AWS_CONFIG_FILE'] = path.join(path.dirname(__file__), "..", ".aws/config")

APP_ID = "YOUR-APP-ID"

def send_sqs_message(LogAction, LogIntent):
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='BabyConnectLogger')
    msg = LogAction + ":" + LogIntent
    response = queue.send_message(MessageBody=msg, 
        MessageAttributes={
            'LogAction': {
                'StringValue': LogAction,
                'DataType': 'String'
            },
            'LogIntent':{
                'StringValue': LogIntent,
                'DataType': 'String'
            },
            'TimeSec':{
                'StringValue': str(time.time()),
                'DataType': 'Number'
            }
    })


# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            # 'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def log_diaper(intent, session):
    """ Logs a diaper """

    if 'diaperType' in intent['slots']:
        diaperType = None
        try:
            diaperType = intent['slots']['diaperType']['value']
        except KeyError:
            pass
        print ("DiaperType:", diaperType)

        ok = False
        possibleTypes = "wet dirty poopy poop".split()
        for tp in possibleTypes:
            if tp in diaperType:
                ok = True
        if ok:
            send_sqs_message(intent['name'], diaperType)
            speech_output = "I have logged a " + diaperType + " diaper in Baby Connect"
            reprompt_text = ""
        else:
            speech_output = "I did not understand the diaper type requested."
            reprompt_text = "I couldn't understand the diaper type requested."
    return build_response({}, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, True))

def nursing_start(intent, session):
    """ Starts a nursing session """

    if 'nursingSide' in intent['slots']:
        nursingSide = None
        try:
            nursingSide = intent['slots']['nursingSide']['value']
        except KeyError:
            pass

        side = 'right'
        if 'left' in nursingSide:
            side = 'left'

        send_sqs_message(intent['name'], side)
        speech_output = "I started a nursing session on the " + side + " side in Baby Connect"
        reprompt_text = ""
    else:
        speech_output = "I couldn't understand the nursing side requested."
        reprompt_text = "I couldn't understand the nursing side requested."
    return build_response({}, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, True))

def nursing_switch(intent, session):
    ''' Switches nursing sides'''

    send_sqs_message(intent['name'], "SwitchSide")
    speech_output = "I have switched nursing sides in Baby Connect"
    return build_response({}, build_speechlet_response(intent['name'], speech_output, "", True))

def nursing_pause(intent, session):
    ''' Pauses nursing session '''

    send_sqs_message(intent['name'], "Pause")
    speech_output = "I have paused the current nursing session in Baby Connect"
    return build_response({}, build_speechlet_response(intent['name'], speech_output, "", True))

def nursing_resume(intent, session):
    ''' Resumes a paused nursing session '''

    send_sqs_message(intent['name'], "Resume")
    speech_output = "I have resumed the current nursing session in Baby Connect"
    return build_response({}, build_speechlet_response(intent['name'], speech_output, "", True))

def nursing_done(intent, session):
    ''' Completes nursing session '''

    send_sqs_message(intent['name'], "Done")
    speech_output = "I have stopped and logged the current nursing session in Baby Connect"
    return build_response({}, build_speechlet_response(intent['name'], speech_output, "", True))

def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    print("on_intent requestId=" + intent_request['requestId']
          + ", sessionId=" + session['sessionId']
          + ", intent=" + str(intent)
          + ", intentName=" + intent_name)

    # Dispatch to your skill's intent handlers
    if intent_name == 'LogDiaperIntent':
        return log_diaper(intent, session)
    elif intent_name == 'NursingIntent':
        return nursing_start(intent, session)
    elif intent_name == 'NursingSwitchIntent':
        return nursing_switch(intent, session)
    elif intent_name == 'NursingPauseIntent':
        return nursing_pause(intent, session)
    elif intent_name == 'NursingResumeIntent':
        return nursing_resume(intent, session)
    elif intent_name == 'NursingCompleteIntent':
        return nursing_done(intent, session)
    else:
        raise ValueError("Invalid intent")


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Ensure we are only allowing request from our skill.
    """
    if (event['session']['application']['applicationId'] != APP_ID):
        raise ValueError("Invalid Application ID")

    if event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
