import logging
from random import randint
from flask import Flask, render_template
from flask_ask import Ask, statement, question, session

# Local libs
import BabyConnect
import Authorization

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger("flask_ask").setLevel(logging.DEBUG)

nursing = None

@ask.intent("LogDiaperIntent", convert={'diaperType': str})
def LogDiaper(diaperType):
    con = BabyConnect.WebInterface(user=Authorization.GetUser(), password=Authorization.GetPassword())
    con.LogDiaper(diaperType)
    del(con)
    return statement(render_template('diaper_logged', logType=diaperType))

@ask.intent("NursingIntent", convert={'nursingSide': str})
def NursingBasic(nursingSide):
    global nursing
    print ("Nursing resuest:", nursingSide)
    side = 1
    if 'left' in nursingSide:
        side = 0
    if nursing is None:
        nursing = BabyConnect.Nursing(side)
    else:
        nursing.Switch()
    return statement(render_template('nursing_started'))

@ask.intent("NursingSwitchIntent")
def NursingSwitch():
    global nursing
    if nursing is None:
        return statement(render_template('nursing_not_found'))
    else:
        print ("Switching sides:", nursing.side)
        nursing.Switch()
        print ("Switching sides:", nursing.side)
    return statement(render_template('nursing_switch'))

@ask.intent("NursingPauseIntent")
def NursingPause():
    global nursing
    if nursing is None:
        return statement(render_template('nursing_not_found'))
    else:
        nursing.Pause()
    return statement(render_template('nursing_pause'))

@ask.intent("NursingResumeIntent")
def NursingResume():
    global nursing
    if nursing is None:
        return statement(render_template('nursing_not_found'))
    else:
        nursing.Resume()
    return statement(render_template('nursing_resume'))

@ask.intent("NursingCompleteIntent")
def NursingPause():
    global nursing
    if nursing is None:
        return statement(render_template('nursing_not_found'))
    else:
        con = BabyConnect.WebInterface(user=Authorization.GetUser(), password=Authorization.GetPassword())
        con.LogNursing(nursing)
        del(con)
        nursing = None
    return statement(render_template('nursing_logged'))

if __name__ == '__main__':
    app.run(debug=True)