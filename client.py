import time, socket, sys, threading
# socket creation
socket_server_send = socket.socket()
socket_server_receive = socket.socket()
username=""
dashed_line="--------------------"
exit_now=False
class bcolors:
    HEADER = '\033[95m'     # pink
    received = '\033[94m'   # Blue
    sent = '\033[92m'       # green
    time = '\033[93m'  # yellow
    error = '\033[91m'      # red
    ENDC = '\033[0m'
# print coloured
def print_colored(text,type):
    if type=='received':
        print(bcolors.received+text+bcolors.ENDC)
    elif type=='sent':
        print(bcolors.sent+text+bcolors.ENDC)
    elif type=='broadcast':
        print(bcolors.broadcast+text+bcolors.ENDC)
    elif type=='error':
        print(bcolors.error+text+bcolors.ENDC)
    elif type=='HEADER':
        print(bcolors.HEADER+text+bcolors.ENDC)
# add to logs
def print_logs(username,message):
    with open('logs.txt', 'a') as f:
        f.write(time.strftime("%d/%m/%Y %H:%M:%S")+"\t"+username+"\t"+message+"\n")
# print current time
def print_time():
    print(time.strftime("%d/%m/%Y %H:%M:%S"))
def register_to_send(sock, username):
    data='REGISTER TOSEND '+username+'\n\n'
    sock.send(data.encode())

def well_formed_username(username):
    if ' ' in username:
        return False
    else:
        return True

#  Client to server registration, for receiving messages
def register_to_receive(sock, username):
    data='REGISTER TORECV '+username+'\n\n'
    sock.send(data.encode())

def get_ack(response):
    end=response.find('\n\n')
    if response[0:9]=='ERROR 100':
        return "error", ""
    if response[0:10] == 'REGISTERED':
        return "success", response[18:end]
    else:
        return "error",""
def get_ack_sent(response):
    if response[0:9]=='ERROR 102':
        return "unable to send"
    if response[0:9] == 'ERROR 103':
        return "header incomplete"
    if response[0:4] == 'SEND':
        return "sent"
def get_rec_msg(in_line):
    space=in_line.find(' ')
    # print(len(in_line))
    if len(in_line)<4 or len(in_line)>400 or in_line[0]!='@' or space==-1 or space==len(in_line)-1 or in_line[space+1]=='\n':
        return False,"",""
    # print("FALINGFS")
    recepient = in_line[1:space]
    message = in_line[space+1:]
    return True,recepient, message

# Client to server message
def send_message(sock, username,message):
    data="SEND "+username+"\n"+"Content-length: "+str(len(message))+"\n\n"+message
    # print("sending data:",data)
    sock.send(data.encode())


def get_forwarded_message(sock ,response):
    # test code for evaluation starts
    # send_error103(sock)
    # return "error103", "",""
    # test code for evaluation ends
    if response[0:7]=='FORWARD':
        isformated,sender,message=is_formated(response)
        if isformated:
            # send ack
            send_received_ack(sock,sender)
            return "sent",message,sender
    send_error103(sock)
    return "error103", "",""

def send_error103(sock):
    data='ERROR 103 Header Incomplete\n\n'
    sock.send(data.encode())
def send_received_ack(sock,username):
    data='RECEIVED '+username+'\n\n'
    sock.send(data.encode())
def is_formated(response):
    if response[0:7]=='FORWARD':
        space=response.find(' ')
        end=response.find('\n')
        if space==-1:
            return False,"",""
        sender=response[space+1:end]
        len_message=response[response.find('Content-length:')+16:response.find('\n\n')]
        if not len_message.isdigit():
            return False,"",""
        message=response[response.find('\n\n')+2:response.find('\n\n')+int(len_message)+2]
        return True, sender, message
    else:
        return False,"",""

def send_message_thread(socket_server_send, username):
# 1.2 send message
    global exit_now
    while(True):
        if exit_now:
            return
        # print("Receipient: ",end="")
        in_line = input()
        ok,recipient, message = get_rec_msg(in_line)
        # for evaluation
        # ok=True
        if not ok:
            print_colored("Message format is wrong. Please retype in correct format", "error")
            print_time()
            print(dashed_line)
            continue
        send_message(socket_server_send, recipient, message)

        # receive acknowledgement from server
        sent=get_ack_sent(socket_server_send.recv(512).decode())
        if sent == "unable to send":
            # print(sent)
            print_colored("Unable to send message", "error")
            print_time()
            print(dashed_line)
            continue
        # header incomplete. Connection is unstable. hence close connection
        if sent == "header incomplete":
            print_colored("Header incomplete. Ending connection. Please reregister.", "error")
            print_time()
            print(dashed_line)
            socket_server_send.close()
            socket_server_receive.close()
            exit_now=True
            sys.exit()
            
        if(recipient!=username):
            print_time()
            print(dashed_line)

def receive_message_thread(socket_server_receive, username):
    # 1.3 receive message
    global exit_now
    while(True):
        # TODO:make this continous print green tick
        # print("listening for message",end='\r')
        if exit_now:
            return
        response=socket_server_receive.recv(512).decode()
        # print("Got message")
        ack,msg,sender=get_forwarded_message(socket_server_receive,response)
        # if server sends error. Implies connection is broken. so exit
        if ack!="sent":
            print_colored("Error in receiving message. Closing connection", "error")
            print_time()
            print(dashed_line)
            socket_server_receive.close()
            socket_server_send.close()
            exit_now=True
            sys.exit()

        print_colored("Sender: @"+sender+"\n---Message---\n"+msg, "received")
        print_time()
        print(dashed_line)



server_host = socket.gethostname()
ip = socket.gethostbyname(server_host)
s_port = 8080
print_colored('Welcome to the chat Application!\n1. Limit your messages to 400 characters\n2. Username can be alphanumeric with atleast 3 chars to at most 10 chars\n4. Do not repeat usernames\n','sent')
print_colored('This is your IP address: '+ip,"HEADER")
server_host = input('Enter server\'s IP address:')
# server_host = "192.168.137.1"
socket_server_send.connect((server_host, s_port))
socket_server_receive.connect((server_host, s_port))

while(True):
    print_colored("Enter your Username:","HEADER")
    username = input()
    # register_username(username, socket_server_send, socket_server_receive)
    # print("sending message for register")
    register_to_send(socket_server_send, username)
    register_to_receive(socket_server_receive, username)
    # print("message sent for registration")
    # receive acknowledgement from server
    ack_tosend,ack_username_tosend=get_ack(socket_server_send.recv(512).decode())
    ack_torecv,ack_username_toreceive=get_ack(socket_server_receive.recv(512).decode())
    # print("Registration ack to send",ack_tosend,ack_username_tosend)
    # print("Registration ack to recv",ack_torecv,ack_username_toreceive)
    if ack_tosend!= "success" or ack_torecv!= "success" or ack_username_tosend!=username or ack_username_toreceive!=username:
        print_colored("Error in registration... Try again", "error")
        continue
    break
print_colored("Registration Successful", "HEADER")
# create thread for sending and receiving messages
thread_send = threading.Thread(target=send_message_thread, args=(socket_server_send, username,))
thread_receive = threading.Thread(target=receive_message_thread, args=(socket_server_receive, username,))
thread_send.daemon = True
thread_receive.daemon = True
thread_send.start()
thread_receive.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print_colored(dashed_line+"\nClosing server... Bye...\n"+dashed_line+"\n", "error")
    socket_server_send.close()
    socket_server_receive.close()

    
    sys.exit(0)
