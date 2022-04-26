import time, socket, sys
from _thread import *
# global hash_table
from collections import defaultdict
# connection list. 0-> client sends to you, 1-> you send to client
hash_table = defaultdict(list)
# message queue
# is_alive=defaultdict(lambda: [False])
def isvalid_username(username):
    # return True
    if username=="ALL" :
        return False
    if(len(username)>=3 and len(username)<=10):
        for i in username:
            if(i.isalpha() or i.isdigit()):
                continue
            else:
                return False
        return True
    return False

def register_user(first_response,conn):
    end=first_response.find("\n\n")
    # print(first_response)
    if(len(first_response)<19 or end==-1):
        conn.sendall('ERROR 101 No user registered\n\n'.encode())
        return "ERROR101",""
    if(first_response[0:15]=="REGISTER TOSEND"):
        username=first_response[16:end]         
        if (isvalid_username(username)):
            # print(username,"THIS is username")
            # username already taken and is alive
            # if(is_alive[username][0]):
            #     conn.sendall('ERROR 100 Malformed username\n\n'.encode())
            #     return "ERROR100",""
            if(hash_table[username]==[]):
                hash_table[username]+=[conn]
                # is_alive[username]=[True]
            elif len(hash_table[username])==1:
                temp=hash_table[username][0]
                hash_table[username][0]=conn
                hash_table[username]+=[temp]
                # is_alive[username]=[True]
            else:
                conn.sendall('ERROR 100 Malformed username\n\n'.encode())
                return "ERROR100",""
                hash_table[username]=[conn]
                # is_alive[username]=[True]
            data="REGISTERED TOSEND "+username+"\n\n"
            conn.sendall(data.encode())
            return "REGISTER_TOSEND",username
        else:
            conn.sendall('ERROR 100 Malformed username\n\n'.encode())
            return "ERROR100",""
    elif(first_response[0:15]=="REGISTER TORECV"):
        username=first_response[16:end]
        if (isvalid_username(username)):
            if(len(hash_table[username])==2):
                hash_table[username]=[]
            hash_table[username]+=[conn]
            # is_alive[username]=[True]
            # print(hash_table)
            data="REGISTERED TORECV "+username+"\n\n"
            conn.sendall(data.encode())
            return "REGISTER_TORECV",username
        else:
            conn.sendall('ERROR 100 Malformed username\n\n'.encode())
            return "ERROR100",""
    conn.sendall('ERROR 101 No user registered\n\n'.encode())
    return "ERROR101",""
# check headers corresponding to table 2
def check_msg_header(msg):
    rec=""
    msg_len=0
    msg_content=""
    if(len(msg)<20):
        return False,rec,msg_len,msg_content
    if(msg[0:4]!="SEND"):
        return False,rec,msg_len,msg_content
    back_pos=msg.find("\n")
    d_back_pos=msg.find("\n\n")
    cont_len_pos=msg.find("Content-length:")
    if( cont_len_pos<7 or back_pos<6 or d_back_pos<23):
        return False,rec,msg_len,msg_content
    rec=msg[5:back_pos]
    msg_len=msg[cont_len_pos+16:d_back_pos]
    msg_content=msg[d_back_pos+2:]
    if((not msg_len.isdigit() )or int(msg_len)!=len(msg_content)):
        print("message length is not given length. Given length is:",msg_len,len(msg_content))
        return False,rec,msg_len,msg_content
    return True,rec,int(msg_len),msg_content


def forward_to_recp(msg_response,sender_username):
    # sanity check for incoming message
    check,receipient,msg_length,msg_content=check_msg_header(msg_response)
    if(not check):
        return "ERROR103"
    print("message received is formatted.")
    if(receipient!="ALL" and receipient not in hash_table):
        return "ERROR102"
    if(msg_length!=len(msg_content)):
        print("message length not equal to given length")
        return "ERROR103" 
    # forwarding to recepient
    print("Forwarding the message")
    data="FORWARD "+sender_username+"\nContent-length: "+str(msg_length)+"\n\n"+msg_content
    
    if(receipient=="ALL"):
        for rec_username in hash_table:
            if rec_username!=sender_username:
                send_to_clinet_socket=hash_table[rec_username][1]
                send_to_clinet_socket.sendall(data.encode())
                print("Message Forwarded waiting for confirmation")
                receipient_ack=send_to_clinet_socket.recv(512).decode()
                print("Confirmation received")
                if(receipient_ack[0:8]!="RECEIVED"):
                    return "ERROR102"
        return "SEND"
    else:
        send_to_clinet_socket=hash_table[receipient][1]
        try:
            send_to_clinet_socket.sendall(data.encode())
            print("Message Forwarded waiting for confirmation")
            receipient_ack=send_to_clinet_socket.recv(512).decode()
        except:
            return "ERROR102"

        print("Confirmation received")
        if(receipient_ack[0:8]=="RECEIVED"):
            return "SEND"
        elif (receipient_ack[0:9]=="ERROR 103"):
            # this means that recipient link is not working. Issue is with server to receiver. Hence its better to return unable to send than header incomplete
            return "ERROR102"
        else:
            return "ERROR102"

def send_error102(conn):
    data="ERROR 102 Unable to send\n\n"
    conn.sendall(data.encode())
def send_error103(conn):
    data='ERROR 103 Header Incomplete\n\n'
    conn.send(data.encode())
def send_delivered(conn,username):
    data="SEND "+username+"\n\n"
    conn.sendall(data.encode())

def client_thread(conn, add):
    first_response = (conn.recv(512)).decode() 
    op_code,username=register_user(first_response,conn)
    # client is sending in this thread
    if op_code=="REGISTER_TOSEND":
        while True:
            # wait to receive to send message
            try:
                msg_response = (conn.recv(512)).decode()
            except:
                print(username+" disconnected")
                # is_alive[username]=False
                return
            # parse and if correct send message on other socket else ?
            # wait for confirmation from client2 (receiver)
            ack=forward_to_recp(msg_response,username)
            # convey the receipt to sender client
            if(ack=="ERROR102"):
                send_error102(conn)
            if(ack=="ERROR103"):
                send_error103(conn)
            if(ack=="SEND"):
                send_delivered(conn,username)
            print(ack)

    # client is receiving in this thread
    else:
        return
                
# create socket
new_socket = socket.socket()
host_name = socket.gethostname()
s_ip = socket.gethostbyname(host_name)
port = 8080
new_socket.bind((host_name, port))
print( 'Binding successful!')
print('This is your IP: ', s_ip)

thread_cnt = 0

# connection
while True:
    print('Waiting for connection...')
    new_socket.listen(10)               # Number of connections to queue
    conn, add = new_socket.accept()
    print("Connected to: ", add[0], ':', add[1])
    start_new_thread(client_thread, (conn, add))
    thread_cnt += 1

