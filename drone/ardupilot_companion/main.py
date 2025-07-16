'''
set stream rate on an APM
'''
from builtins import range
import sys
from pymavlink import mavutil

def wait_heartbeat(m):
    '''wait for a heartbeat so we know the target system IDs'''
    print("Waiting for APM heartbeat")
    m.wait_heartbeat()
    print("Heartbeat from APM (system %u component %u)" % (m.target_system, m.target_system))

def show_messages(m):
    '''show incoming mavlink messages'''
    while True:
        msg = m.recv_match(blocking=True)
        if not msg:
            return
        if msg.get_type() == "BAD_DATA":
            if mavutil.all_printable(msg.data):
                sys.stdout.write(msg.data)
                sys.stdout.flush()
        else:
            print(msg)

# create a mavlink serial instance
master = mavutil.mavlink_connection('/dev/serial0', baud=921600)

# wait for the heartbeat msg to find the system ID
wait_heartbeat(master)

stream_rate = 1
print("Sending all stream request for rate %u" % stream_rate)
for i in range(0, 3):
    master.mav.request_data_stream_send(master.target_system, master.target_component,
                                        mavutil.mavlink.MAV_DATA_STREAM_ALL, stream_rate, 1)

show_messages(master)