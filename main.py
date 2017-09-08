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

        print('[*] start proxy client at ip {} and port {}'.format(self.local_proxy_ip,str(self.local_proxy_port)))
        print('[*] protocol http/https')
        print('[*] socket protocol udp')

        while True:
            conn, addr = sock.accept()
            thr = threading.Thread(target=self.request_handler, args=(conn, addr))
            thr.start()
    
    

    def geocell_sender(self, request,request_id=None):
    
            if request_id:
                 data_to_send = json.dumps({'op': 'send_req_data', 'data': request,'request_id':str(request_id)}, ensure_ascii=False).encode()
            else:
                data_to_send = json.dumps({'op': 'send_req_data', 'data': request},ensure_ascii=False).encode()
                
             
          
                
                
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
            server_address = (settings.remote_server_ip, settings.remote_server_port)
        
            counter = 0
            status = ''
            while counter < settings.max_resend_try:
            
                counter = counter + 1
               
            
                try:
                    
                    sock.sendto(data_to_send,server_address)
                    
                
                 
                    sock.settimeout(settings.global_timeout)
                    ack,addr = sock.recvfrom(settings.max_fragment_size)
                    sock.settimeout(None)
                  
               
                
                    if ack:
                        ack=ack.decode()
                        if not request_id:
                            json_data = json.loads(ack)
                            status = json_data['request_id']
                        else:
                            status=request_id
                            
                        break
                    else:
                      
                        status = False
                        continue
            
                except Exception as e:
                    sock.settimeout(None)
                    status = False
                    
                    
                   #print('ვერ მიიღო აცკი')
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

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
               
                sock.sendto(data_to_send.encode(),server_address)
          
            
                

                sock.settimeout(settings.global_timeout)
                ack,addr= sock.recvfrom(settings.max_fragment_size)
                sock.settimeout(None)
                
              
                if ack:
                    res_data = ack
                    data_to_send = json.dumps(
                        {'op': 'receive_fr_data','fr_index': fragment_id,'request_id': str(request_id),'action':'delete'},
                        ensure_ascii=False)
                     
                    sock.sendto(data_to_send.encode(), server_address)
                    
                   
                
                    # print("received fragment" + str(fragment_id) + ':' + str(request_id) + ' time:' + str(t2 - t))
                
                    break
                # else:
                #
                #
                #     continue
        
            except Exception as e:
                
               
                sock.settimeout(None)
               
                
        res.append({'counter':fragment_id,'data':res_data})
        


    def geocell_receiver(self,request_id,https=False,firsts=False):
        start = time.time()
        if not https:
            data_to_send = json.dumps({'op': 'receive_fr_count', 'request_id': str(request_id)}, ensure_ascii=False).encode()
        else:
            data_to_send = json.dumps({'op': 'https_receive_fr_count', 'request_id': str(request_id)},
                                      ensure_ascii=False).encode()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server_address = (settings.remote_server_ip, settings.remote_server_port)
        
       

        sock.sendto( data_to_send,server_address)
        #აქ დასაფიქრებელია ცოტა,ტაიმაუტი ხო არ უნდა
        #დომებია,ჩავასწორე
        if firsts:return b''
        try:
            sock.settimeout(settings.responce_timeout)
            data,addr=sock.recvfrom(settings.max_fragment_size)
            sock.settimeout(None)
        except:
            return b''
        
        data=data.decode()
        incoming_data_fragments_length=int(data)
        if incoming_data_fragments_length==0:return b''
       #print(str(incoming_data_fragments_length)+' fr length'+' https:'+ str(https))

       #print('geocell fragmentebis migebis interval ' + str(time.time()-start))
        
        res_data=b''
        
        res=[]
        ths=[]
        for i in range(0,incoming_data_fragments_length):
         
            th=threading.Thread(target=self.threaded_receiver,args=(i,request_id,res))
            ths.append(th)
        for j in ths:
            j.start()
        for j in ths:
            j.join()
         
         
         
        if len(res)!=incoming_data_fragments_length:return b''
        res.sort(key=lambda x: x['counter'])
        
        for i in res:
            dat=i['data']
            if data:
               res_data+=dat
            else:return b''

        
       #print('geocel receibving interval '+str(start))
        
        
        
        
        return res_data
        
        
    
    def request_handler(self, conn, addr):
        request_id = ''
        data = b''
        try:
            # მივიღოთ დატა ბრაუზერისგან,ან სხვა პროქსი კლიენტისგან
            
            request = conn.recv(65000)
            # print('req sig'+str(len(request)))
            if request:
    
                
                try:
                    _, headers = request.decode().split('\r\n', 1)
                except:
                    pass
                   #print('sgsg erori')
    
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
                    
                    # request_id = self.get_next_request_count()

                    request_id= self. geocell_sender(request.decode())
                    
                    if not request_id:
                        return
                    self.geocell_receiver(request_id, https=True,firsts=True)
                    
                    while True:
                        data = b''
                        request=b''
                        while True:
                        
                            try:
                                 conn.settimeout(0.1)
                                 t=conn.recv(65000)
                                 conn.settimeout(None)
                                 request+=t
                                 
                                 if not t:
                                     conn.close()
                                     request=''
                                     break
                                 
                            except socket.timeout:
                                conn.settimeout(None)
                                break
                            except:
                                conn.close()
                                request=''
                                break
                        if request:
                            
                            counter=0
                            
                            print('send request with id:' + str(request_id) + ' size: ' + str(len(request)) + ' https:true')

                            print('send request with id:' + str(request_id) + ' size: ' + str(
                                len(request)) + ' https:true')
                            if self.geocell_sender(base64.encodebytes(request).decode(), request_id=request_id):
                                data = None
                                data = self.geocell_receiver(request_id, https=True)
                                print('receive responce with id:' + str(request_id) + ' size: ' + str(
                                    len(data)) + ' https:true')
    
                                # აქ უნდა გზიპ დეკომპრესია
                                if not data:
                                    conn.close()
                                    return
    
                                data = gzip.decompress(data)
                                if not data:
                                    conn.close()
        
                                    return
    
                                conn.sendall(data)

                            else:
                                conn.close()
                                return
                        else:
                            conn.close()
                            return
                            
                    
                else:
                   
                  
                        request_id=self.geocell_sender(request.decode())
                        if not request_id:
                            return
                        print('send request with id:' + str(request_id) + ' size: ' + str(len(request)))
                        data = self.geocell_receiver(request_id)
                        print('receive responce with id:' + str(request_id) + ' size: ' + str(len(data)))
                        # აქ უნდა გზიპ დეკომპრესია
                        if not data:
                            conn.close()
                            return
                        data=gzip.decompress(data)
                        if not data:
                            conn.close()
                            return
                         
                        conn.sendall(data)
                        conn.close()
        
        except Exception as e:
            pass
            logging.exception('message')
            print("error in request handler" + str(e))
        
        finally:
            conn.close()
            if request_id:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
                server_address = (settings.remote_server_ip, settings.remote_server_port)
                data_to_send = json.dumps(
                    {'op': 'clean', 'request_id': str(request_id),
                     },
                    ensure_ascii=False)
                sock.sendto(data_to_send.encode(),server_address)
            


def server():
    a=local_server()
    a.start_server()
if __name__ == "__main__":
    server()