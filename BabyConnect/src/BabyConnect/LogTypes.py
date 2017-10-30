import datetime

class Diaper(object):
    type=None
    id=None
    ids = { 
        "bm" : "diaper1", 
        "bmwet" : "diaper2",
        "wet" : "diaper3",
        "dry" : "diaper4"
    }
    def __init__(self, logType):
        self.logValue = logType
        dirtyOPts = 'poopy dirty messy poop crap'.split()
        wetOPts = 'wet pee'.split()

        isDirty = False
        isWet = False
        for opt in dirtyOPts:
            if opt in logType:
                isDirty = True
                break

        for opt in wetOPts:
            if opt in logType:
                isWet = True
                break

        if isDirty and isWet:
            self.type = "bmwet"
        elif isDirty and not isWet:
            self.type = "bm"
        else:
            self.type = "wet"

        # Sets the id code used on the BabyConnect website
        self.id = self.ids[self.type]

    def __repr__(self):
        return "Diaper: {} ({})".format(self.logValue, self.type)

    def get_type(self):
        return self.type

    def get_id(self):
        return self.id


# Class for handling the time tracking of a nursing session.
# This has the utilities to stop/start a session ans switch sides
class Nursing(object):
    def __init__(self, side, timeL=None, timeR=None, epoch=None, debug=None):
        self.timeStart = datetime.now() if epoch is None else datetime.fromtimestamp(epoch)
        if epoch is None:
            self.timeBegin = datetime.now() if timeL is None else datetime.now() - timedelta(seconds=(timeL+timeR))
        else:
            self.timeBegin = self.timeStart
        self.side = side  # 0 = L, 1 = R
        self.durL = 0 if timeL is None else timeL
        self.durR = 0 if timeR is None else timeR
        self.finishTime = self.timeStart
        self.done = False
        self.debug = debug
        self._debugMsg("Start:{}, Side:{}, Epoch:{}".format(self.timeStart, self.side, epoch))

    def __repr__(self):
        times = self.GetTimes()
        last = "right" if times["last"] else "left"
        outStr = "Nursing session:\n" + \
            "   Start       : {}\n".format(times["start"]) + \
            "   End Time    : {}\n".format(times["end"]) + \
            "   Time (Left) : {}\n".format(times["left"]) + \
            "   Time (Right): {}\n".format(times["right"]) + \
            "   Last Side   : {}\n".format(last)
        return str(outStr)

    def _GetNow(self, epoch=None):
        if epoch is None:
            return datetime.now()
        else:
            return datetime.fromtimestamp(epoch)

    def _debugMsg(self, msg):
        if self.debug is not None:
            print (msg)

    def Switch(self, epoch=None):
        self.AddTime(epoch)
        oldSide = self.side
        self.side = 0 if self.side else 1
        self._debugMsg("Switching sides: {}->{} --- epoch:{}".format(oldSide, self.side, epoch))

    def Pause(self, epoch=None):
        self.AddTime(epoch)
        self.timeStart = None
        self._debugMsg("Pause:{}".format(epoch))

    def Resume(self, epoch=None):
        self.timeStart = now = self._GetNow(epoch)
        self.done = False
        self._debugMsg("Resume:{}".format(epoch))

    def AddTime(self, epoch=None):
        now = self._GetNow(epoch)
        if self.timeStart is not None:
            length = (now - self.timeStart).total_seconds()
            if self.side:
                self.durR += length
                self._debugMsg("Adding {} seconds to right".format(length))
            else:
                self.durL += length
                self._debugMsg("Adding {} seconds to left".format(length))
        self.timeStart = now

    def Finish(self, epoch=None):
        self.AddTime(epoch)
        self.finishTime = self._GetNow(epoch)
        self.done = True
        self._debugMsg("Finishing: {}".format(self.finishTime))

    def GetTimes(self, epoch=None):
        now = None
        if not self.done:
            self.AddTime(epoch)
            now = self._GetNow(epoch)
        else:
            now = self.finishTime
        return {
            "start":self.timeBegin.strftime("%I:%M%p"), 
            "left":round((self.durL/60), 0), 
            "right":round((self.durR/60), 0),
            "end":now.strftime("%I:%M%p"),
            "last":self.side
        }
