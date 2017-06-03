import socket
import settings

import threading
import time




def recv_all(conn):
    
    result=b''
    while True:
        try:
                conn.settimeout(settings.socket_timeout)
                data=conn.recv(4096 )
                conn.settimeout(None)
                if data:result+=data
                else:
                    raise Exception('sock_closed')
        except socket.timeout:
            conn.settimeout(None)
             
            print("received all")
            
    return result




class local_server():
    
    #შიდა პროქსის ip და port რომელიც უნდა მიუთითოთ ბრაუზერში
    local_proxy_ip='127.0.0.1'
    local_proxy_port=1327
    
    def start_server(self):
        
        
        # იხსნება სოკეტი და იწყება პორტზე მოსმენა
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.local_proxy_ip, self.local_proxy_port))
        sock.listen(5)
        
        while True:
            conn,addr=sock.accept()
            thr = threading.Thread(target=self.request_handler, args=(conn, addr))
            thr.start()
         
         
         
    def geocell_sender(self,request):
        pass
    
    def geocell_receiver(self):
        pass
       
    def request_handler(self,conn,addr):
        
        
        try:
            #მივიღოთ დატა ბრაუზერისგან,ან სხვა პროქსი კლიენტისგან
            request=recv_all(conn)
            self.geocell_sender(request)
            data=self.geocell_receiver()
            
            conn.send_all(data)
            
        except Exception as e:
            print("error in request handler"+str(e))
            
        finally:
            conn.close()
            
            
            
            
            
            
            
        
    
    