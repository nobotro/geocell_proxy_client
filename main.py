import base64
import datetime
import email
import socket

from io import StringIO

import pickle

import zlib

import settings
import re
import threading
import time

import json


def recv_all(conn):
    result = b''
    while True:
        try:
            conn.settimeout(settings.socket_timeout)
            data = conn.recv(4096)
            conn.settimeout(None)
            if data:
                result += data
            else:
                raise Exception('sock_closed')
        except socket.timeout:
            conn.settimeout(None)
            
            print("received all")
    
    return result


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
        
        while True:
            conn, addr = sock.accept()
            thr = threading.Thread(target=self.request_handler, args=(conn, addr))
            thr.start()
    
    def request_fragment_geocell_sender(self, request: str):
        
        fragment_array = re.findall(''.join('(\S{{{}}})'.format(4000)), request)
        
        request_id = self.get_next_request_count()
        
        for fragment in fragment_array:
            
            data_to_send = json.dumps({'op': 'send', 'request_id': request_id, 'data': fragment}, ensure_ascii=False)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            server_address = (settings.remote_server_ip, settings.remote_server_port)
            
            counter = 0
            status=''
            while counter < settings.max_resend_try:
                
                counter=counter+1
                sock.connect(server_address)
                
                try:
                    sock.settimeout(4)
                    sock.sendall(data_to_send)
                    sock.settimeout(None)
                    
                    sock.settimeout(4)
                    
                    
                    ack = sock.recv(4000)
                    sock.settimeout(None)
                    
                    if ack:
                        sock.close()
                        status=request_id
                        
                        
                        break
                    else:
                        sock.settimeout(None)
                        sock.close()
                        status=False
                        continue
                       
                except socket.timeout:
                    sock.settimeout(None)
                    sock.close()
                    status=False
                    continue
                    
            if not status:
                return status
                    
        return status

    def geocell_sender(self, request,request_id):
    
            
            data_to_send = json.dumps({'op': 'send_req_data', 'request_id': str(request_id), 'data': request}, ensure_ascii=False).encode()
             
          
                
                
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
            server_address = (settings.remote_server_ip, settings.remote_server_port)
        
            counter = 0
            status = ''
            while counter < settings.max_resend_try:
            
                counter = counter + 1
                sock.connect(server_address)
            
                try:
                    sock.settimeout(4)
                    sock.sendall(data_to_send)
                    sock.settimeout(None)
                
                    sock.settimeout(4)
                  
                    ack = sock.recv(8000)
                
                  
                    sock.settimeout(None)
                
                    if ack:
                        sock.close()
                        status = request_id
                        
                    
                        break
                    else:
                        sock.settimeout(None)
                        sock.close()
                        status = False
                        continue
            
                except socket.timeout:
                    sock.settimeout(None)
                    sock.close()
                    status = False
                    continue
                    
            return status

    def threaded_receiver(self,fragment_id,request_id,res):
        server_address = (settings.remote_server_ip, settings.remote_server_port)
        
        data_to_send = json.dumps({'op': 'receive_fr_data', 'request_id': str(request_id), 'fr_index': fragment_id},
                                  ensure_ascii=False)
        counter = 0
        res_data = b''
        while counter < settings.max_resend_try:
            
            counter = counter + 1
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(server_address)
        
            try:
                sock.settimeout(4)
                sock.sendall(data_to_send.encode())
                sock.settimeout(None)
            
                
                t = datetime.datetime.now()
            
            
                ack=b''
                while True:
                    sock.settimeout(4)
                    t_ack= sock.recv(8000)
                    ack+=t_ack
                    sock.settimeout(None)
                    if len(ack)==8000:break
                    if not t_ack:break
                    
                print('ack len'+str(len(ack)))
                t2 = datetime.datetime.now()
               
            
                if ack:
                    res_data += ack
                    sock.close()
                
                    print("received fragment" + str(fragment_id) + ':' + str(request_id) + ' time:' + str(t2 - t))
                
                    break
                else:
                    sock.settimeout(None)
                    sock.close()
                
                    continue
        
            except socket.timeout:
                sock.settimeout(None)
                sock.close()
                
        res.append({'counter':fragment_id,'data':res_data})


    def geocell_receiver(self,request_id,https=False):
        
        if not https:
            data_to_send = json.dumps({'op': 'receive_fr_count', 'request_id': str(request_id)}, ensure_ascii=False).encode()
        else:
            data_to_send = json.dumps({'op': 'https_receive_fr_count', 'request_id': str(request_id)},
                                      ensure_ascii=False).encode()
            
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        server_address = (settings.remote_server_ip, settings.remote_server_port)
        
        sock.connect(server_address)
        
        sock.sendall(data_to_send)
  
        incoming_data_fragments_length=int(sock.recv(1024).decode())
        print(str(incoming_data_fragments_length)+' fr length'+' https:'+ str(https))
        sock.close()
        
        
        res_data=b''
        
        res=[]
        ths=[]
        for i in range(0,incoming_data_fragments_length):
            
            th=threading.Thread(target=self.threaded_receiver,args=(i,request_id,res,))
            ths.append(th)
        for j in ths:
            j.start()
        for j in ths:
            j.join()
            
        res.sort(key=lambda x: x['counter'])
        
        for i in res:
            res_data+=i['data']
            
        
        
            
             
    
        return res_data
            
            
    
    def request_handler(self, conn, addr):
        
        try:
            # მივიღოთ დატა ბრაუზერისგან,ან სხვა პროქსი კლიენტისგან
            request = conn.recv(8000)
            if request:
    
                data = b''
                try:
                    _, headers = request.decode().split('\r\n', 1)
                except:
                    print('sgsg erori')
    
                # construct a message from the request string
                message = email.message_from_file(StringIO(headers))
    
                # construct a dictionary containing the headers
                headers = dict(message.items())
                headers['method'], headers['path'], headers['http-version'] = _.split()
                
                if headers['method']=='CONNECT':
                    reply = "HTTP/1.0 200 Connection established\r\n"
                    reply += "Proxy-agent: Pyx\r\n"
                    reply += "\r\n"
                    conn.sendall(reply.encode())
                   
 
                    request_id = self.get_next_request_count()
                
                    self.geocell_sender(request.decode(), request_id)
                    self.geocell_receiver(request_id, https=True)
                    while True:
                        request=conn.recv(2048)
                        self.geocell_sender(base64.encodebytes(zlib.compress(request)).decode(),request_id)
                        data = self.geocell_receiver(request_id,https=True)
                        if not data:
                            conn.close()
                            break

                        conn.sendall(data)
                    
                    
                else:
                    request_id = self.get_next_request_count()
                    self.geocell_sender(request.decode(),request_id)
        
                    data = self.geocell_receiver(request_id)
        
                    conn.sendall(data)
        
        except Exception as e:
            print("error in request handler" + str(e))
        
        finally:
            conn.close()


def server():
    a=local_server()
    a.start_server()
if __name__ == "__main__":
    server()