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
    local_proxy_port = 1327
    requests_id = []
    requests_counter = 0
    thread_lock = threading.Lock()

    def get_next_request_count(self, *args):




        self.thread_lock.acquire()

        res = self.requests_counter + 1
        self.requests_counter = res
        self.thread_lock.release()
        return res

    def start_server(self):

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

    def geocell_sender(self, request, request_id=None, reqport=None, reqhost=None,random_port=random.choice(settings.remote_server_port_range)):

        if request_id:
            data_to_send = json.dumps({'op': 'send_req_data', 'data': request, 'request_id': str(request_id)},
                                      ensure_ascii=False).encode()
        else:
            data_to_send = json.dumps({'op': 'send_req_data', 'data': request, 'host': reqhost, 'port': reqport},
                                      ensure_ascii=False).encode()

        server_address = (settings.remote_server_ip, random_port)

        counter = 0
        status = ''
        while counter < settings.max_resend_try:

            counter = counter + 1

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)



                sock.sendto(data_to_send, server_address)

                sock.settimeout(settings.global_timeout)
                ack, addr = sock.recvfrom(settings.max_fragment_size)
                sock.settimeout(None)
                sock.close()


                if ack:
                    ack = ack.decode()
                    if not request_id:
                        json_data = json.loads(ack)
                        status = json_data['request_id']
                    else:
                        status = request_id

                    break
                else:

                    status = False
                    continue

            except Exception as e:
                sock.settimeout(None)
                status = False

                # print('ვერ მიიღო აცკი')
                continue

        return status

    def threaded_receiver(self, fragment_id, request_id, res,random_port=random.choice(settings.remote_server_port_range)):
        server_address = (settings.remote_server_ip, random_port)

        data_to_send = json.dumps({'op': 'receive_fr_data', 'request_id': str(request_id), 'fr_index': fragment_id},
                                  ensure_ascii=False)
        counter = 0
        res_data = b''
        while counter < settings.max_resend_try:

            counter = counter + 1

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


                sock.sendto(data_to_send.encode(), server_address)

                sock.settimeout(settings.global_timeout)
                ack, addr = sock.recvfrom(settings.max_fragment_size)
                sock.settimeout(None)
                sock.close()

                if ack:
                    res_data = ack
                    data_to_send = json.dumps(
                        {'op': 'receive_fr_data', 'fr_index': fragment_id, 'request_id': str(request_id),
                         'action': 'delete'},
                        ensure_ascii=False)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


                    sock.sendto(data_to_send.encode(), server_address)
                    sock.close()

                    # print("received fragment" + str(fragment_id) + ':' + str(request_id) + ' time:' + str(t2 - t))

                    break
                    # else:
                    #
                    #
                    #     continue

            except Exception as e:

                sock.settimeout(None)

        res.append({'counter': fragment_id, 'data': res_data})

    def geocell_receiver(self, request_id, https=False,random_port=random.choice(settings.remote_server_port_range)):
        ffst = datetime.datetime.now()
        if not https:
            data_to_send = json.dumps({'op': 'receive_fr_count', 'request_id': str(request_id)},
                                      ensure_ascii=False).encode()
        else:
            data_to_send = json.dumps({'op': 'https_receive_fr_count', 'request_id': str(request_id)},
                                      ensure_ascii=False).encode()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


        server_address = (settings.remote_server_ip, random_port)

        sock.sendto(data_to_send, server_address)
        # აქ დასაფიქრებელია ცოტა,ტაიმაუტი ხო არ უნდა
        # დომებია,ჩავასწორე
        imm=datetime.datetime.now()
        try:
            sock.settimeout(settings.responce_timeout)
            data, addr = sock.recvfrom(settings.max_fragment_size*3)
            sock.settimeout(None)
            sock.close()

        except:
            sock.close()

            return b''
        imme=datetime.datetime.now()

        data = data.decode()

        # print('************'+str(len(data)))

        if len(data)==1:
            sock.close()
            return b''
        data = json.loads(data)
        # print('|||||||||||||||||||||||||||||||||||||||||||')
        # print(data)
        dlen = data['len']
        fr_data = data['fragment']

        first_fragment = base64.decodebytes(fr_data.encode())
        # print('fr ken'+str(dlen))
        # print('b64len'+str(len(fr_data)))
        # print('bytelen'+str(len(first_fragment)))



        incoming_data_fragments_length = int(dlen)
        if incoming_data_fragments_length == 0: return b''
        # print(str(incoming_data_fragments_length)+' fr length'+' https:'+ str(https))

        # print('geocell fragmentebis migebis interval ' + str(time.time()-start))

        res_data =first_fragment

        res = []
        ths = []
        ffed=datetime.datetime.now()

        for i in range(1, incoming_data_fragments_length):
            th = threading.Thread(target=self.threaded_receiver, args=(i, request_id, res))
            ths.append(th)
        for j in ths:
            j.start()
        for j in ths:
            j.join()

        if len(res)+1 != incoming_data_fragments_length: return b''
        res.sort(key=lambda x: x['counter'])

        for i in res:
            dat = i['data']
            if data:
                res_data += dat
            else:
                return b''


            # print('geocel receibving interval '+str(start))

        return res_data

    def request_handler(self, conn, addr,random_port=random.choice(settings.remote_server_port_range)):

        request_id = ''
        data = b''
        try:
            # მივიღოთ დატა ბრაუზერისგან,ან სხვა პროქსი კლიენტისგან


            request =  conn.recv(65000)
            # try:
            #     conn.settimeout(0.1)
            #     tempp = conn.recv(1)
            #     conn.settimeout(None)
            #     request += tempp
            #     if tempp:
            #         print('^^^^^^^^^^^^^aaaaa')
            # except Exception as e:
            #     conn.settimeout(None)
            #     pass

            # print('req sig'+str(len(request)))
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


                    request_id = self.geocell_sender(request.decode(), reqhost=host, reqport=port)


                    if not request_id:
                        conn.close()
                        raise Exception('reqvestis aidi ar momivida')
                    print('{} , mivige serverisgan axal motxovis aidi '.format(request_id))

                    for i in range(7):




                        data = b''


                        request= conn.recv(65000)


                        while True:
                            try:

                                temp = b''
                                conn.settimeout(0.1)

                                temp = conn.recv(1)

                                conn.settimeout(None)

                                if len(temp) != 1: break
                                temp += conn.recv(65000)
                                request += temp
                            except Exception as e:


                                conn.settimeout(None)
                                break


                        print('{} , amovige brauzerisgan reqvesti, biji {}'.format(request_id,i))
                        recchaci = b'\x14\x03'

                        recalert = b'\x15\x03'

                        rechand = b'\x16\x03'

                        datarec = b'\x17\x03'

                        patterns = [recchaci, recalert, rechand, datarec]






                        if request:
                            ssss = datetime.datetime.now()
                            counter = 0


                            gggg=datetime.datetime.now()
                            if self.geocell_sender(base64.encodebytes(request).decode(), request_id=request_id):

                                ggee=datetime.datetime.now()


                                data = None

                                ggrr=datetime.datetime.now()
                                data = self.geocell_receiver(request_id, https=True)
                                ggse=datetime.datetime.now()


                                # აქ უნდა გზიპ დეკომპრესია
                                if not data:
                                    conn.close()
                                    raise Exception('jreciverma carieli data')

                                # tl=len(data)
                                # data = gzip.decompress(data)
                                # tl2=len(data)

                                conn.sendall(data)
                                ffff=datetime.datetime.now()

                        else:
                            conn.close()
                            raise Exception('brauzerma reqvesti ar mogvca')


                else:

                    counter = 0
                    while counter < settings.max_resend_try:
                        counter += 1
                        request_id = self.geocell_sender(request.decode())
                        if request_id: break
                    else:
                        raise Exception()

                    if not request_id:
                        raise Exception()

                    data = self.geocell_receiver(request_id)

                    # აქ უნდა გზიპ დეკომპრესია
                    if not data:
                        conn.close()
                        raise Exception()
                    # tl = len(data)
                    # data = gzip.decompress(data)
                    # tl2 = len(data)
                    # print('==================== ' + str(tl2) + ' ' + str(tl) + ' ' + str(tl2 - tl))
                    if not data:
                        conn.close()
                        raise Exception()

                    conn.sendall(data)
                    conn.close()

        except Exception as e:



           print(str(e))


        finally:

            if request_id:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


                server_address = (settings.remote_server_ip, random_port)
                data_to_send = json.dumps(
                    {'op': 'clean', 'request_id': str(request_id),
                     },
                    ensure_ascii=False)
                sock.sendto(data_to_send.encode(), server_address)
                sock.close()
                conn.close()


def server():
    a = local_server()
    a.start_server()


if __name__ == "__main__":
    server()