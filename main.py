from mpi4py import MPI
import numpy as np
import time
b = time.time()
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

graph = np.array([
    [0,0,0,1,1,0,0,1],
    [0,0,0,0,0,1,0,1],
    [0,0,0,1,1,0,1,0],
    [1,0,1,0,1,0,1,0],
    [1,0,1,1,0,1,0,1],
    [0,1, 0,0,1,0,0,1],
    [0,0,1,1,0,0,0,0],
    [1,1,0,0,1,1,0,0],
    ],dtype = int)

P = [0,7,6,0,0,1,3,0]
C = [[3,4,7],[5],[],[6],[],[],[2],[1]]

children = C[rank]
aChildren = C[rank]
parent = P[rank]
neighbors = set()
freeColors = {0,1,2,3,4,5,6,7,8,9,10} # set for avaible colors to chose from
colors = {}        # dictionary for neighbor colors

for i in range(len(graph[rank])):
    if graph[rank][i]:
        neighbors.add(i)
aNeighbors = neighbors.copy()

#node = Node(graph, rank, comm)
#msg types 
ROUND = 1
COLOR = 2
DISCARD = 3
ROVER = 4
FIN = 6

#states
UNDEC = 0
COLORED = 1
FINN = 2
STATE = 0

#other variables
colored = False
roundReceived = False
roundOver = False
msg = [-1,-1,-1] #[rank,type,data(roundNum,color,etc)]
roundNum = 0
self_color = -1
received = set()
lostNeighbors = set()
overChilds = set()
receivedFin = set()
#print(f"Im {rank} my children:{children} my parent {parent} my neighbors:{neighbors} ")
def dbgprint(node:int,str:str):
    if rank == node:
        print(str)

def msgToChild(msg,children,a):
    if children == None:
        return
    for i in children:
        comm.send(msg,i,a)

def msgToNeigh(msg,neighbors,a):
    if neighbors == None:
        return
    for i in neighbors:
        comm.send(msg,i,a)

run = True
while run:
    roundNum += 1
    if rank == 0:
        msg[0], msg[1], msg[2] = rank, ROUND, roundNum
        msgToChild(msg, children, ROUND)
        #print("round sent to child____________________________",roundNum)

        if len(neighbors) == 0 and STATE == COLORED:
            msg[0], msg[1], msg[2] = rank, COLOR, self_color
            msgToNeigh(msg, aNeighbors, COLOR)
            msg[0], msg[1] = rank, FIN
            comm.send(msg,parent,FIN)
            if len(children) == 0:
                run = False
                STATE = FINN
                #print(f"{rank} sender:{sender}, State:{STATE}, msg:{typ},neighbors:{neighbors} Finn:{receivedFin},round:{roundNum} LEAF")

            
        if len(neighbors) == 0 and STATE != COLORED:
            self_color = min(freeColors)
            colored = True
            STATE = COLORED
            msg[0], msg[1], msg[2] = rank, COLOR, self_color
            msgToNeigh(msg, aNeighbors, COLOR)
            #print("COLOR",aNeighbors,rank)


        if STATE != COLORED:
            if rank > max(neighbors):
                self_color = min(freeColors)
                colored = True
                STATE = COLORED
                #print(rank,f"my COLOR: {self_color}")
                msg[0], msg[1], msg[2] = rank, COLOR, self_color
                msgToNeigh(msg, aNeighbors, COLOR)
            else:
                msg[0], msg[1] = rank, DISCARD
                msgToNeigh(msg, neighbors, DISCARD)
        roundReceived = True


    overChilds = set()
    roundOver = False

    while not roundOver:

        msg = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG)
        sender, typ, data = msg[0], msg[1], msg[2] 
        #print(rank,neighbors,"AAAAAAAAA", roundNum, self_color)
        if typ == ROUND:
            #print(rank, sender, neighbors)
            #send round to children of middle nodes
            if len(children) != 0:
                msg[0], msg[1] = rank, ROUND
                msgToChild(msg, children, ROUND)


            if len(neighbors) == 0 and STATE == COLORED:
                msg[0], msg[1], msg[2] = rank, COLOR, self_color
                msgToNeigh(msg, aNeighbors, COLOR)
                msg[0], msg[1] = rank, FIN
                comm.send(msg,parent,FIN)
                if len(children) == 0:
                    run = False
                    STATE = FINN
                    #print(f"{rank} sender:{sender}, State:{STATE}, msg:{typ},neighbors:{neighbors} Finn:{receivedFin},round:{roundNum} LEAF")

                break
                
            if len(neighbors) == 0 and STATE != COLORED:
                self_color = min(freeColors)
                colored = True
                STATE = COLORED
                msg[0], msg[1], msg[2] = rank, COLOR, self_color
                msgToNeigh(msg, aNeighbors, COLOR)
                #print("COLOR",aNeighbors,rank)


            if STATE != COLORED:
                if rank > max(neighbors):
                    self_color = min(freeColors)
                    colored = True
                    STATE = COLORED
                    #print(rank,f"my COLOR: {self_color}")
                    msg[0], msg[1], msg[2] = rank, COLOR, self_color
                    msgToNeigh(msg, aNeighbors, COLOR)
                else:
                    msg[0], msg[1] = rank, DISCARD
                    msgToNeigh(msg, neighbors, DISCARD)

            #if colored:
            #    msg[0], msg[1] = rank, ROVER
            #    comm.send(msg,parent,ROVER)

            roundReceived = True

        elif typ == COLOR and STATE != FINN:
            received.add(msg[0])
            if msg[2] in freeColors:
                freeColors.remove(msg[2])

            lostNeighbors.add(msg[0])
            #print(rank,f"received color from {msg[0]} color:{msg[2]} received={received} lostNeighbors:{lostNeighbors}")

        elif typ == DISCARD and STATE != FINN:
            received.add(msg[0])
            #print(rank,f"received DISCARD from {msg[0]} received = {received}")

        elif typ == ROVER and STATE != FINN:
            overChilds.add(sender)
            if len(overChilds) >= len(children):
                msg[0], msg[1] = rank, ROVER
                comm.send(msg,parent,ROVER)
                roundOver = True

        elif typ == FIN:
            receivedFin.add(sender)
            #children.remove(sender)
            #print("FIN",rank, sender, receivedFin)
            if len(receivedFin) >= len(aChildren) and (STATE == COLORED or colored):
                msg[0], msg[1] = rank, FIN
                comm.send(msg, parent, FIN)
                STATE = FINN
                run = False
                #print(f"{rank} sender:{sender}, State:{STATE}, msg:{typ},neighbors:{neighbors} Finn:{receivedFin},round:{roundNum}")
                break
        else:

            print(f"case _ reached at {rank}")
        #print(rank,neighbors,"BBBBBBBBB", roundNum, self_color)

        if roundReceived and (len(received) == len(neighbors)):
                #print("ROUND END",rank, neighbors, lostNeighbors, self_color)
            neighbors.difference_update(lostNeighbors)#remove neighbors with colors
            roundReceived = False
            received.clear() ; lostNeighbors.clear() 
            if len(children) == 0:
                msg[0], msg[1] = rank, ROVER
                comm.send(msg,parent,ROVER)
                roundOver = True
        a = time.time()
        #print(f"{rank} sender:{sender}, State:{STATE}, msg:{typ},neighbors:{neighbors} Finn:{receivedFin},round:{roundNum} {a-b}")


        
a = time.time()
print(f"END Node:{rank} Color: {self_color} --------------------------------",a-b )  
