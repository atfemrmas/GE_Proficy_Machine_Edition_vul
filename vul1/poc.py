 # coding=utf-8
import socket
import select
from multiprocessing import Process
import thread
import sys
import logging # reconstruct the code after
import json
from binascii import b2a_hex,a2b_hex
import time


class proxy(object):
    
    def __init__(self, sock,data):
        self.BUFSIZE = 10000
        self.server = sock
        self.inputs = [self.server]
        self.sock_dict = {} 
        self.sock_dict["device"] = None  # record for target connect

        self.data = data
        self.resp_idx = 0
        self.tag_idx = 0

    @staticmethod
    def socket_send(sock,data,tag):
        # logging.debug("in process:{}".format(tag))
        try:
            sock.send(data)
            time.sleep(0.1) # in case send two stream as one stream
        except Exception as exp:
            err = "{}:{}".format(tag,exp)
            logging.warning(err)



    def run(self):
        self.noblocking()
   
    def noblocking(self, timeout=10):
        while True:
            try:
                readable,_,exceps = select.select(self.inputs,[],self.inputs,timeout) 
                for soc in readable:
                    if soc is self.server: 
                        # proactive connect to to proxy, [controller,software], device should notify
                        client_con, _ = soc.accept() 
                        self.inputs.append(client_con)
                        logging.debug("connect success:{}".format(client_con.getpeername()))

                    else: 
                        data = soc.recv(self.BUFSIZE)
                        self.sock_dict["software"] = soc
                        logging.debug("connection from software")

                        # socket is ok!
                        if data != "": 
                        
                            logging.debug("data from software:{}".format(b2a_hex(data)))
                          

                            snd_data = self.data[self.resp_idx]
                            
                            self.socket_send(self.sock_dict["software"],snd_data,"device to software")


                            logging.debug("data resp to software:{}".format(b2a_hex(snd_data)))
                            self.resp_idx += 1
                        
                        # socket closed by peer
                        else: 
                            self.inputs.remove(soc)
                            self.resp_idx = 0
                            # self.sock_dict["software"] = None
                            self.tag_idx += 1
                            logging.debug("socket_closed_by_peer:{}".format("software offline!"))
                            self.sock_dict["software"] = None
                            soc.close()
                           
                             
                for exp in exceps:
                    # maybe server?
                    logging.warning('Exception:{}'.format(exp.getpeername()))
                    self.inputs.remove(exp)

            except Exception as error:
                self.tag_idx += 1
                logging.warning("{}->Error info:{}".format(self.tag_idx,error))
                errMsg = "{}".format(error)

                if errMsg.find("10054") >= 0 or errMsg.find('10053'):
                    self.inputs.remove(soc)
                    self.resp_idx = 0
                    self.sock_dict["software"] = None
                    logging.warning("exp software offline")
                    

def load_data(filename):
    data_t = open(filename,'r').readlines()
    resp_data = []
    for item in data_t:
        if item.find('server:') >= 0:
            resp_data.append(a2b_hex(item.strip('\r\n')[7:]))

    return resp_data

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG) # can show debug info
    
    filename = 'business_connect_close.txt'

    data = load_data(filename)

    s9 = '03000a00380000000000000000000000006031fdf78976ab6e94100a00000033004000003e00001800000101ff020000fc210200830000000000000000000000000000000000000000000e0000003e0000000000000030000000000000000000000001000800000000000000100a0000'
    data[9] = a2b_hex(s9)

    ADDR = ("0.0.0.0",18245)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen(10)
    p = proxy(server,data)
    print("proxy start")
    logging.debug("In logging level, proxy start")
    p.run()
