import time
import paho.mqtt.client as mqtt
from pop import Pilot

Car = Pilot.AutoCar()

SPD_VAL = 38
MESSAGE = ""
current_state = ""


pan = pan_prv = 90;   tilt = tilt_prv = -14

def on_connect(client, userdata, flags, rc):
    print("MQTT 연결 성공:", rc)
    client.subscribe("car/control")

def on_message(client, userdata, msg):
    global MESSAGE
    new_msg = msg.payload.decode().strip()
    print("📩 Received message:", new_msg)
    MESSAGE = new_msg  # 항상 새로운 메시지 반영

def setup_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("172.20.10.5", 1883, 60)
    client.loop_start()
    return client

def set_pt(p_val, t_val):
    Car.camPan(p_val)
    Car.camTilt(t_val)
    if pan != pan_prv or tilt != tilt_prv:
        print("pan = %s, tilt = %s" %(pan, tilt))
    else:   
        pass

def main_loop():
    global MESSAGE, current_state, pan, tilt, pan_prv, tilt_prv, SPD_VAL
    Car.setSpeed(SPD_VAL)

    while True:
        if MESSAGE != "":
            print(f"🕹️  Handling: {MESSAGE}")

            if MESSAGE == "go":
                Car.steering = 0
                Car.forward()
               
                current_state = "center"

            elif MESSAGE == "right1":
                Car.steering = 0.3
                SPD_VAL = 41
                Car.forward()
                current_state = "right1"

            elif MESSAGE == "right2":
                Car.steering = 0.8; 
                SPD_VAL = 42
                Car.forward()
                current_state = "right2"
            
            elif MESSAGE == "right3":
                Car.steering = 1; 
                SPD_VAL = 44
                Car.forward()
                current_state = "right3"

            elif MESSAGE == "left1":
                Car.steering = -0.3
                SPD_VAL = 41
                Car.forward()
                current_state = "left1"

            elif MESSAGE == "left2":    
                Car.steering = -0.7
                SPD_VAL = 42
                Car.forward()
                current_state = "left2"
            
            elif MESSAGE == "left3":    
                Car.steering = -1
                SPD_VAL = 44
                Car.forward()
                current_state = "left3"

            elif MESSAGE == "back":
                Car.steering = 0
                SPD_VAL = 40
                Car.backward()
                current_state = "back"

            else:
                pass

            # 메시지 처리 완료 후 초기화
            MESSAGE = ""
            time.sleep(0.0009)
            
        # 현재 상태를 유지하면서 0.05초 대기
        
        Car.setSpeed(SPD_VAL)
        
        

if __name__ == "__main__":
    try:
        setup_mqtt()
        print("🚗 Ready to receive driving commands...")
        set_pt(pan, tilt)
        main_loop()
    
    except KeyboardInterrupt:
        Car.stop()
        

