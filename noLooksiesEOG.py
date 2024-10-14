import aiohttp
import os
import logging
import psutil
import pystray
import threading
from PIL import Image
import tkinter as tk
import willump #if you want to import the class
import asyncio
import sys
import startup
import time
os.chdir(sys._MEIPASS)
global exitflag, running, wllp, tray, status, startstatus, notHonored
notHonored = True
currentqueue = None
exitflag = False
running = True
icon = Image.open("Icon.png")
status = "Status = On"
if startup.is_running_at_startup("NoLooksies", True):
    startstatus = "Start on Windows startup = On"
else:
    startstatus = "Start on Windows startup = Off"
print (startup.is_running_at_startup("NoLooksies", True))


async def set_event_listener():
	#creates a subscription to the server event OnJsonApiEvent (which is all Json updates)
    all_events_subscription = await wllp.subscribe('OnJsonApiEvent',default_handler=default_message_handler)
	#let's add an endpoint filter, and print when we get messages from this endpoint with our printing listener
    #wllp.subscription_filter_endpoint(all_events_subscription, '/riot-messaging-service/v1/message/honor/vote-completion', handler=check_print)   
    #wllp.subscription_filter_endpoint(all_events_subscription, '/lol-honor-v2/v1/vote-completion', handler=check_print)
    wllp.subscription_filter_endpoint(all_events_subscription, '/lol-gameflow/v1/gameflow-phase', handler=check_honored)
    wllp.subscription_filter_endpoint(all_events_subscription, '/lol-end-of-game/v1/eog-stats-block', handler=check_queue)
    #wllp.subscription_filter_endpoint(all_events_subscription, '/lol-end-of-game/v1/eog-stats-block', handler=check_test)

    
    #wllp.subscription_filter_endpoint(all_events_subscription, '/lol-honor-v2/v1/ballot', handler=check_test)
    #wllp.subscription_filter_endpoint(all_events_subscription, '/lol-pre-end-of-game/v1/currentSequenceEvent', handler=check_honors)

#create a function that will put the output of currentsequenceEvent subscription into a textfile

async def wllp_start():
    global wllp
    wllp = await willump.start()
    await set_event_listener()

async def to_jsonfile(data):
    import json
    from datetime import datetime
 
    data_with_time = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }

    with open('data.json', 'a') as f:
        f.write(json.dumps(data_with_time) + '\n')


async def check_queue(data):
    global currentqueue
    currentqueue = data['data']['queueType']
    print("Queue is", currentqueue)
 
async def wllp_close():
    await wllp.close()



async def check_honored(data):
    global notHonored
    print(data)
    if data['data'] == "EndOfGame" and running and currentqueue == "RANKED_SOLO_5x5":
        await wllp.request('post','/lol-end-of-game/v1/state/dismiss-stats')
        tray.notify("LP screen skipped!", "NoLooksies")

        asyncio.sleep(10)
        notHonored = True



async def check_test(data):
    global wllp
    global tray, queueType, running, notHonored
    print ("Game ended")
    print(data)
    if data['data'] != None:
        print(data['data']['queueType'])
        if True and running and data['data']['queueType'] == "RANKED_SOLO_5x5" and running:
            while not notHonored:
                await asyncio.sleep(0.05)

            print("Game is :", data['data']['queueType'])
            asyncio.sleep(5)
            await wllp.request('post','/lol-end-of-game/v1/state/dismiss-stats')
            tray.notify("LP screen skipped!", "NoLooksies")


def toggle_program(tray, loop):
    global running, wllp, status
    print("toggled running to", not running)
    if running:
        tray.remove_notification()
        tray.notify("Functionality turned Off!", "Toggle")
        status = "Status = Off"
        tray.update_menu()
        running = False
    else:
        tray.remove_notification()
        tray.notify("Functionality turned back On!", "Toggle")
        status = "Status = On"
        tray.update_menu()
        running = True

#Quits program        
def quit(tray, loop):
    global running, wllp, exitflag
    running = False
    try:
        loop.call_soon_threadsafe(asyncio.run_coroutine_threadsafe,wllp.close(), loop)
    except NameError:
        os._exit(1)
    tray.stop()
    exitflag = True
    os._exit(1)

def status_func():
    global status
    return status

def add_to_tray(loop):
    global tray, status
    tray = pystray.Icon("Game Monitor", icon)
    tray.menu = pystray.Menu(pystray.MenuItem(lambda text: status, status_func,enabled=False),pystray.MenuItem('Toggle Program', lambda : toggle_program(tray, loop)),pystray.MenuItem(lambda text: startstatus, on_start),pystray.MenuItem('Quit', lambda : quit(tray,loop)))
    tray.run()

async def default_message_handler(data):
    pass


def on_start():
    global startstatus, tray
    if not startup.is_running_at_startup("NoLooksies", True):
        startup.run_at_startup_set("NoLooksies",user=True)
        startstatus = "Start on Windows startup = On"
        tray.notify("NoLooksies now starting on windows startup!", "NoLooksies")
        
        pass
    else:
        startup.run_at_startup_remove("NoLooksies",True)
        startstatus = "Start on Windows startup = Off"
        tray.notify("NoLooksies no longer starting on windows startup!", "NoLooksies")
    tray.update_menu()

async def main():
    global wllp, notHonored
    loop = asyncio.get_running_loop()
    
    tray_thread = threading.Thread(target=add_to_tray, args=(loop,))
    tray_thread.start()
    wllp = await willump.start()
    print(wllp)    
    await set_event_listener()
    
    while not exitflag:
        try:
                response = await wllp.request('get','/riotclient/app-name')
                pass
        except (aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.ServerDisconnectedError):
                await wllp_close()
                print("wllp has closed")
                await wllp_start()
        except RuntimeError:
                pass
        await asyncio.sleep(8)

if __name__ == '__main__':
	# uncomment this line if you want to see willump complain (debug log)
    logging.getLogger().setLevel(level=logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        asyncio.run(wllp.close())
        os._exit(1)        
