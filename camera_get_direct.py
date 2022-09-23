import sys
import os
import cv2 as cv
import time
from multiprocessing import Process, Queue
import multiprocessing
import socket

#导入百度api库
sys.path.append('./baidu_api_lib')
from baidu_picture import baidu_picture_2_msg
from baidu_sound import baidu_word_2_sound

pic_APP_ID = '24100391'
pic_API_KEY = 'o4F8DEtaGbAt3ys5Lb13iUjx'
pic_SECRET_KEY = 'xtVS1iE5pxNx98oEYr6hTK6w9nTSg7EW'

#百度AI的调用url
baidu_request_url = "https://aip.baidubce.com/rest/2.0/image-classify/v1/body_analysis"

#　获取摄像头图像
def camera_frame_func(task_name, mult_queue1, mydict):

    #初始化状态，不进行图像传输
    mydict["get_pic"] = "false"

    # 创建一个VideoCapture对象
    capture = cv.VideoCapture(0)

    #　给出提示信息
    print(task_name + "任务启动")

    try:
        while True:
            # 一帧一帧读取视频
            ret, frame = capture.read()

            #将拍摄到的图片发送到消息队列中
            if mydict["get_pic"]=="true":
                mydict["get_pic"]="false"
                mult_queue1.put(frame)

            # 本地显示视频图像
            cv.namedWindow("capture",0);
            cv.resizeWindow("capture", 80, 60);
            cv.imshow('capture', frame)
            cv.waitKey(1)

    except KeyboardInterrupt:
        # 释放cap,销毁窗口
        capture.release()
        print(task_name + "任务被终止")

#处理图像
def proc_frame_func(task_name, mult_queue, mydict):
    #　给出提示信息
    print(task_name + "任务启动")

    # 传入百度AI的参数，进行图像识别
    pic_msg = baidu_picture_2_msg(pic_APP_ID, pic_API_KEY, pic_SECRET_KEY)

    #创建UDP连接，设置目的端口和IP，通过本地回环发给贪吃蛇程序
    udpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sendArr = ('127.0.0.1', 20163)

    try:
        while True:

            #从队列中获取图片，显示图像质量
            mydict["get_pic"] = "true"
            frame = mult_queue.get()

            # 写入图片
            cv.imwrite('read_word.jpg',frame)

            #从百度AI获取图片分析结果
            response = pic_msg.pic_2_msg(baidu_request_url, 'read_word.jpg')

            #获取人体个数
            person_num = response.json()['person_num']
            # print(person_num)

            #人数大于0
            if person_num > 0:
                #获取第一个人的关键点信息
                p_info = response.json()['person_info']
                p_body_info = p_info[0]['body_parts']

                #获取头顶信息
                p_top_head_y = p_body_info['top_head']['y']

                #获取左肩信息
                p_left_shoulder_x = p_body_info['left_shoulder']['x']
                p_left_shoulder_y = p_body_info['left_shoulder']['y']

                #获取右肩信息
                p_right_shoulder_x = p_body_info['right_shoulder']['x']
                p_right_shoulder_y = p_body_info['right_shoulder']['y']

                #获取左手腕信息
                p_left_wrist_x = p_body_info['left_wrist']['x']
                p_left_wrist_y = p_body_info['left_wrist']['y']

                #获取右手腕信息
                p_right_wrist_x = p_body_info['right_wrist']['x']
                p_right_wrist_y = p_body_info['right_wrist']['y']

                #左手高于头部，则发送上键
                if p_left_wrist_y < p_top_head_y:
                    sendData = "上键"
                    udpSocket.sendto(sendData.encode('utf-8'),sendArr)
                #右手高于头部，则发送上键
                elif p_right_wrist_y < p_top_head_y:
                    sendData = "上键"
                    udpSocket.sendto(sendData.encode('utf-8'),sendArr)
                #左手腕在左肩的左面，则发送左键
                elif p_left_wrist_x > p_left_shoulder_x:
                    sendData = "左键"
                    udpSocket.sendto(sendData.encode('utf-8'),sendArr)
                #右手腕在右肩的右面，则发送右键
                elif p_right_wrist_x < p_right_shoulder_x:
                    sendData = "右键"
                    udpSocket.sendto(sendData.encode('utf-8'),sendArr)
                #左手腕低于左肩，则发送下键
                elif p_left_wrist_y > p_left_wrist_y:
                    sendData = "下键"
                    udpSocket.sendto(sendData.encode('utf-8'),sendArr)
                #右手腕低于右肩，则发送下键
                elif p_right_wrist_y > p_right_shoulder_y:
                    sendData = "下键"
                    udpSocket.sendto(sendData.encode('utf-8'),sendArr)
                else:
                    pass

    except KeyboardInterrupt:
        os.remove('read_word.jpg')
        print(task_name + "任务被终止")

if __name__ == "__main__":
    try:
        #定义共享变量
        mydict=multiprocessing.Manager().dict()
        mydict['get_pic'] = 'true'

        #　定义传递图像队列和传递图像处理结果队列
        q_frame = Queue()

        #　采集摄像头进程、处理图片进程
        get_camera_frame = Process(target=camera_frame_func, args=("获取摄像头图像", q_frame, mydict))
        proc_frame       = Process(target=proc_frame_func, args=("处理图像", q_frame, mydict))

        # 启动任务
        get_camera_frame.start()
        proc_frame.start()

        get_camera_frame.join()
        proc_frame.join()

    except KeyboardInterrupt:
        print("任务被终止了")
