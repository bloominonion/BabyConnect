#!/usr/bin/python3
import sys
import time
import datetime
import json
import traceback
from BabyConnect import LogTypes, YourSecrets
from BabyConnect.LazyDaemon import Watchdog
from BabyConnect.Sqs import Listener
from BabyConnect.Web import LogData
from functools import partial
from os import environ, path, remove
from os.path import basename, exists

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

    with LogMessages(interval=0.5) as app:
        app.run()

class LogMessages(object):
    '''
    Class to log sqs messages from a source such as an Alexa skill or a button
    into the Baby Connect Web nterface.
    This will enventually support running as a service so it can be started/
    stopped/restarted as needed.

    Params:
        dump    : dumpfile to use when application crashes or halts to save any
                  pending work that hasn't been done.
        interval: Interval to poll the server in minutes for messages.

    '''
    def __init__(self, dump=None, interval=None):
        self.dumpFile = dump if dump is not None else 'BabyConnectDump.json'
        if interval is None:
            self.interval = 5
        else:
            self.interval = interval
        self.pendingRequests = []
        self._load_data()

    def __enter__(self):
        return self

    def __exit__(self ,type, value, traceback):
        print ("Closing logger:", self.dumpFile)
        self.close()

    def close(self):
        self._dump_data()

    def _load_data(self):
        if exists(self.dumpFile):
            print ("Loading previous session data...")
            with open(self.dumpFile, 'r') as dump:
                data = json.load(dump)
                for item in data:
                    if item['class'] == 'nursing':
                        log = LogTypes.Nursing(0)
                        try:
                            log.load_dict(item)
                            self.pendingRequests.append(log)
                        except:
                            pass
                    if item['class'] == 'diaper':
                        log = LogTypes.Diaper('wet')
                        try:
                            log.load_dict(item)
                            self.pendingRequests.append(log)
                        except:
                            pass
            remove(self.dumpFile)

    def _dump_data(self):
        if len(self.pendingRequests) > 0:
            dump = []
            for log in self.pendingRequests:
                dump.append(log.as_dict())
            with open(self.dumpFile, 'w') as dmp:
                json.dump(dump, dmp)
            print ("Records dumped to:", self.dumpFile)

    def run(self):
        try:
            self._process()
        except:
            self._dump_data()
            exc_info = sys.exc_info()
            raise exc_info[0].with_traceback(exc_info[1], exc_info[2])

    def _process(self):
        print ("Starting service...", datetime.datetime.now().strftime("%m-%d-%y %I:%M %p"))
        timeSleep = self.interval #(minutes)
        connectionSleep = 0.25

        watchdogs = [Watchdog(Listener), Watchdog(YourSecrets), Watchdog(LogData)]
        checkCount = 0
        SqsQueue = Listener.AwsMessageHandler(queue_name=YourSecrets.Sqs.QueueName,
                                              aws_key_id=YourSecrets.Sqs.AwsKeyID,
                                              aws_secret_key=YourSecrets.Sqs.AwsSecretKey,
                                              aws_region=YourSecrets.Sqs.AwsRegion)

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
            logs = SqsQueue.GetLogs()
            logs += self.pendingRequests
            self.pendingRequests = []

            if len(logs) > 0:
                print ("\nRequests to log:")
                print (len(logs), "logs found")
                print (logs)
                try:
                    with LogData.WebInterface(user=YourSecrets.BabyConnectLogin.user, 
                                              password=YourSecrets.BabyConnectLogin.password) as connection:
                        for i, log in enumerate(logs):
                            if isinstance(log, LogTypes.Nursing):
                                if (connection.LogNursing(log)):
                                    del(logs[i])
                            elif isinstance(log, LogTypes.Diaper):
                                if (connection.LogDiaper(log)):
                                    del(logs[i])
                            else:
                                print ("Unable to handle log:", log)
                except Exception as err:
                    print ("Failed to log:", err)
                    self.pendingRequests = logs
                    traceback.print_exc()
                self.pendingRequests = logs
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
