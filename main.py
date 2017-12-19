import base64
import datetime
import email
import logging
import socket

from io import StringIO

import pickle

import settings
import re
import threading
import time

import json

import gzip
import random


class local_server():
    # შიდა პროქსის ip და port რომელიც უნდა მიუთითოთ ბრაუზერში
    local_proxy_ip = '127.0.0.1'
    local_https_proxy_port = 1327
    local_http_proxy_port = 1328
    requests_id = []
    requests_counter = 0
    thread_lock = threading.Lock()

    def get_next_request_count(self, *args):




        self.thread_lock.acquire()

        res = self.requests_counter + 1
        self.requests_counter = res
        self.thread_lock.release()
        return res

    def start_https_server(self):

        # იხსნება სოკეტი და იწყება პორტზე მოსმენა
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


        sock.bind((self.local_proxy_ip, self.local_https_proxy_port))
        sock.listen(5)

        print('[*] start proxy client at ip {} and port {}'.format(self.local_proxy_ip, str(self.local_https_proxy_port)))

        print('[*] protocol http/https')
        print('[*] socket protocol udp')

        while True:

            conn, addr = sock.accept()


            thr = threading.Thread(target=self.https_request_handler, args=(conn, addr))
            thr.start()



    def start_http_server(self):

        # იხსნება სოკეტი და იწყება პორტზე მოსმენა
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


        sock.bind((self.local_proxy_ip, self.local_proxy_port))
        sock.listen(5)

        print('[*] start proxy client at ip {} and port {}'.format(self.local_proxy_ip, str(self.local_proxy_port)))

        print('[*] protocol http/https')
        print('[*] socket protocol udp')

        while True:

            conn, addr = sock.accept()

            thr = threading.Thread(target=self.request_handler, args=(conn, addr))
            thr.start()



    def sender(self,conn,req,random_port):
        while True:
                try:
                   data = conn.recv(65000)
                   if not data:raise Exception()


                except Exception as e:
                   conn.close()
                   return

                udpclient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                udpclient.sendto(req.encode() + b'|-1327-|' + data, (settings.remote_server_ip, random_port))
                print('send data to server')

    def receiver(self, conn, req, random_port):
        while True:
            time.sleep(0.1)



            udpclient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            udpclient.sendto(req.encode() + b'|-1327-|', (settings.remote_server_ip, random_port))
            data=udpclient.recvfrom(65000)
            print('received data from server')
            conn.sendall(data[0])

    def https_request_handler(self, conn, addr,random_port=random.choice(settings.remote_server_port_range)):

        request_id = ''
        data = b''
        try:
            # მივიღოთ დატა ბრაუზერისგან,ან სხვა პროქსი კლიენტისგან


            request =  conn.recv(65000)

            if request:

                try:
                    _, headers = request.decode().split('\r\n', 1)
                except:
                    pass
                    # print('sgsg erori')

                # construct a message from the request string
                message = email.message_from_file(StringIO(headers))

                # construct a dictionary containing the headers
                headers = dict(message.items())
                headers['method'], headers['path'], headers['http-version'] = _.split()

                if headers['method'] == 'CONNECT':
                    reply = "HTTP/1.0 200 Connection established\r\n"
                    reply += "Proxy-agent: Pyx\r\n"
                    reply += "\r\n"

                    conn.sendall(reply.encode())
                    time.sleep(0.01)



                host = headers['path']
                lr = host.split(':')
                host = lr[0]
                if len(lr) == 2:
                    port = int(lr[1])

                #get request id first
                udpclient=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                udpclient.sendto('request_id|{}|{}'.format(host,port).encode(),(settings.remote_server_ip,random_port))

                request_id=udpclient.recvfrom(65000)[0].decode()
                print('reqvestis aidi maq')
                time.sleep(0.1)
                if request_id:

                    thr = threading.Thread(target=self.sender, args=(conn,request_id,random_port))

                    thr.start()
                    thr2 = threading.Thread(target=self.receiver, args=(conn,request_id,random_port))

                    thr2.start()








        except Exception as e:



         logging.exception('msg')





def server():
    a = local_server()
    a.start_https_server()


if __name__ == "__main__":
    server()