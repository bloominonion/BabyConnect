import sys
import time
import datetime
from BabyConnect import LogTypes
from BabyConnect.LazyDaemon import Watchdog
from BabyConnect.Sqs import Listener
from BabyConnect.Web import LogData, Authorization 
from functools import partial
from os import environ, path
from os.path import basename

print = partial(print, flush=True, file=sys.stdout)
def main():
    logFile=None if len(sys.argv) == 1 else sys.argv[1]

    if logFile is not None:
        print ("Using logfile:", logFile)
        logHandle = open(logFile, "a+")
        sys.stdout = logHandle
        sys.stderr = logHandle
    else:
        print ("Running without logfile")

    app = LogMessages()
    app.run()

class LogMessages(object):
    '''
    Class to log sqs messages from a source such as an Alexa skill or a button
    into the Baby Connect Web nterface.
    This will enventually support running as a service so it can be started/
    stopped/restarted as needed.
    '''
    def run(self, logFile=None):
        pendingRequests = list()

        print ("Starting service...", datetime.datetime.now().strftime("%m-%d-%y %I:%M %p"))
        timeSleep = 5 #(minutes)
        connectionSleep = 1
        
        watchdogs = [Watchdog(Listener), Watchdog(Authorization), Watchdog(LogData)]
        checkCount = 0
        while True:
            # Make sure there is internet before continuing.
            while not Listener.CheckInternet():
                print ("Failed to connect to internet..trying again in {} minutes".format(connectionSleep))
                time.sleep(connectionSleep*60)
                connectionSleep *= 2
            
            # Check for module file updates
            for watchdog in watchdogs:
                watchdog.check()

            print(".", end='')
            connectionSleep = timeSleep
            checkCount += 1
            curTime = datetime.datetime.now()
            if abs(curTime.hour - 1) < 0.1:
                time.sleep(5*60*60) #sleep 5 hours
            if checkCount % 10 == 0:
                print ("Checking server for requests...{}: {}".format(checkCount, curTime.strftime("%m-%d-%y %I:%M %p")))
            requests = Listener.GetAwsMessages()
            if pendingRequests:
                requests += pendingRequests
            logs = []
            for request in requests:
                result = Listener.ConvertRequest(request)
                if result is not None:
                    logs.append(result)

            if len(logs) > 0:
                print ("\nRequests to log:")
                print (len(logs), "logs found")
                print (logs)
                try:
                    with LogData.WebInterface(user=Authorization.GetUser(), password=Authorization.GetPassword()) as connection:
                        for log in logs:
                            if isinstance(log, LogTypes.Nursing):
                                connection.LogNursing(log)
                                print (log)
                            elif isinstance(log, LogTypes.Diaper):
                                connection.LogDiaper(log)
                                print (log)
                            else:
                                print ("Unable to handle log:", log)
                except:
                    pendingRequests = requests
            time.sleep(timeSleep*60)


# class MyDaemon(Daemon):
#     def run(self):
#         # Or simply merge your code with MyDaemon.
#         your_code = LogMessages()
#         your_code.run()


# if __name__ == "__main__":
#     daemon = MyDaemon(environ['TMP'] + '/daemon-example.pid')
#     if len(sys.argv) == 2:
#         if 'start' == sys.argv[1]:
#             daemon.start()
#         elif 'stop' == sys.argv[1]:
#             daemon.stop()
#         elif 'restart' == sys.argv[1]:
#             daemon.restart()
#         else:
#             print ("Unknown command")
#             sys.exit(2)
#         sys.exit(0)
#     else:
#         print ("usage: %s start|stop|restart" % sys.argv[0])
#         sys.exit(2)

if __name__ == '__main__':
    main()