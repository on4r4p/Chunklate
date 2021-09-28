#!/usr/bin/python3
from argparse import ArgumentParser
import sys , os , binascii ,re



def SplitDigits(lst):
    return([DigDigits(k) for k in re.split(r'(\d+)',lst)])

def DigDigits(dig):
    return(int(dig) if dig.isdigit() else dig)

def ToHistory(chunk):
    global Chunks_History

    try:
       chunk=chunk.encode()
#       print("After encode:",chunk)
    except Exception as e:
#         print("Error:",e)
         pass
    Chunks_History.append(chunk)

def FindMagic(magic):
     lenmagic = len(magic)
     pos = DATAX.find(magic)
     if pos != -1:
          ToHistory("PNG")
          print("This File is Magic :",DATAX[:lenmagic])
          return(ReadPng(pos+lenmagic))
     else:
         print("\n\nDidnt find Any Fucking magic in this file !!\n")
         sys.exit()

def GetInfo(type,data):
    global IHDR_Height
    global IHDR_Width
    global IHDR_Depht
    global IHDR_Color
    global IHDR_Method
    global IHDR_Interlace
    global bKGD_Gray
    global bKGD_Red
    global bKGD_Green
    global bKGD_Blue
    global bKGD_Index
    global PLTE_R
    global PLTE_G
    global PLTE_B
    global cHRM_WhiteX
    global cHRM_WhiteY
    global cHRM_Redx
    global cHRM_Redy
    global cHRM_Greenx
    global cHRM_Greeny
    global cHRM_Bluex
    global cHRM_Bluey
    global gAMA
    global hIST1
    global hIST2
    global hIST3
    global hIST4
    global hIST5
    global hIST6
    global hIST7
    global hIST8
    global pHYs_Y
    global pHYs_X
    global pHYs_Unit
    global sBIT_Gray
    global sBIT_True
    global sBIT_indexed
    global sBIT_GrayAlpha
    global sBIT_TrueAlpha
    global tEXt_Key
    global tEXt_sep
    global tEXt_Text
    global tIME_Yr
    global tIME_Mth
    global tIME_Day
    global tIME_Hr
    global tIME_Min
    global tIME_Sec
    global tRNS_Gray
    global tRNS_TrueR
    global tRNS_TrueG
    global tRNS_TrueB
    global tRNS_Index
    global ZtXt_Key
    global ZtXt_sep
    global ZtXt_Meth
    global ZtXt_Text

    print("\n===========================")
    print("Seeking infos about:",type)
    print("===========================\n")
    if type == "PNG":
          print("Well ..That's a start ..At least it looks like a png.")
    if type == "IHDR":
        try:
             IHDR_Height=str(int.from_bytes(bytes.fromhex(data[:8]),byteorder='big'))
             IHDR_Width=str(int.from_bytes(bytes.fromhex(data[8:16]),byteorder='big'))
             IHDR_Depht=str(int.from_bytes(bytes.fromhex(data[16:18]),byteorder='big'))
             IHDR_Color=str(int.from_bytes(bytes.fromhex(data[18:20]),byteorder='big'))
             IHDR_Method=str(int.from_bytes(bytes.fromhex(data[20:22]),byteorder='big'))
             IHDR_Interlace=str(int.from_bytes(bytes.fromhex(data[22:24]),byteorder='big'))
             print("Width    :",IHDR_Height)
             print("Height   :",IHDR_Width)
             print("Depht    :",IHDR_Depht)
             print("Color    :",IHDR_Color)
             print("Method   :",IHDR_Method)
             print("Interlace:",IHDR_Interlace)
        except Exception as e:
           print("Error:",e)
    
    if type == "bKGD":

        if IHDR_Color == "0" or IHDR_Color == "2":
             try:
                  bKGD_Gray=str(int.from_bytes(bytes.fromhex(data[:2]),byteorder='big'))
                  print("Gray    :",bKGD_Gray)
             except Exception as e:
                 print("Error:",e)
        if IHDR_Color == "2" or IHDR_Color == "6":
           try:
                  bKGD_Red=str(int.from_bytes(bytes.fromhex(data[:2]),byteorder='big'))
                  bKGD_Green=str(int.from_bytes(bytes.fromhex(data[2:4]),byteorder='big'))
                  bKGD_Blue=str(int.from_bytes(bytes.fromhex(data[4:6]),byteorder='big'))
                  print("Red    :",bKGD_Red)
                  print("Green  :",bKGD_Green)
                  print("Blue   :",bKGD_Blue)
           except Exception as e:
              print("Error:",e)
        if IHDR_Color == "3":
            try:
                  bKGD_Index=str(int.from_bytes(bytes.fromhex(data[:1]),byteorder='big'))
                  print("Palette    :",bKGD_Index)
            except Exception as e:
              print("Error:",e)
  
def ReadPng(offset):
     global Have_A_KitKat

     global CLoffX
     global CLoffB
     global CLoffI

     global CToffX
     global CToffB
     global CToffI

     global CDoffX
     global CDoffB
     global CDoffI

     global CrcoffX
     global CrcoffB
     global CrcoffI


     print("\n===========================")
     print("Searching for chunks:")
     print("===========================")
     while offset < len(DATAX):
     
         Chunk_Length = DATAX[offset:offset+8]
         CLoffX = hex(int(offset/2))
         CLoffB = int(offset/2)
         CLoffI = offset

         Chunk_Type = DATAX[offset+8:offset+16]
         CToffX = hex(int(offset/2)+4)
         CToffB = int(offset/2)+4
         CToffI = offset + 4

         Chunk_Data = DATAX[offset+16:offset+16+(int(Chunk_Length, 16)*2)]
         CDoffX = hex(int(offset/2)+8)
         CDoffB =int(offset/2)+8
         CDoffI = offset + 8

         Chunk_Crc =  DATAX[offset+16+len(Chunk_Data):offset+16+len(Chunk_Data)+8]
         CrcoffX = hex(int(offset/2)+int(Chunk_Length,16)+len(Chunk_Type))
         CrcoffB = int(offset/2)+int(Chunk_Length,16)+len(Chunk_Type)
         CrcoffI =(int(offset/2)+int(Chunk_Length,16)+len(Chunk_Type))*2

         print("\n===========================")
         print("Chunk Infos:")
         print("===========================")
         print("Found at offset : In Hex %s , Bytes %s , Index %s "%(CLoffX,CLoffB,CLoffI))
         print("Chunk Length: %s in Bytes: %s"%(hex(int(Chunk_Length,16)),int(Chunk_Length, 16)))
         print("***************************")
         print("Found at offset : In Hex %s , Bytes %s , Index %s "%(CToffX,CToffB,CToffI))
         print("Chunk Type : %s  In Bytes: %s "%(Chunk_Type,bytes.fromhex(Chunk_Type)))
         print("***************************")
         print("Found Chunk Data at offset : In Hex %s , Bytes %s , Index %s "%(CDoffX,CDoffB,CDoffI))
         #print("Chunk Data len  : In Hex %s , Bytes %s , Index %s "%())
         print("***************************")
         print("Found at offset : In Hex %s , Bytes %s , Index %s "%(CrcoffX,CrcoffB,CrcoffI))
         print("Chunk Crc: %s At offset: %s"%(Chunk_Crc,hex(CrcoffB)))
##
         GetInfo(bytes.fromhex(Chunk_Type).decode(),Chunk_Data) 
##
         CheckLength(Chunk_Data,Chunk_Length,Chunk_Type)
##
         if Have_A_KitKat == True:
            Have_A_KitKat = False
            return
##
         Checksum(Chunk_Type,Chunk_Data,Chunk_Crc)
##
         offset= offset + len(Chunk_Length)+len(Chunk_Type)+len(Chunk_Data)+len(Chunk_Crc)
         if Have_A_KitKat == True:
            Have_A_KitKat = False
            return

     exit()


def NearbyChunk(CType,bytesnbr,LastCType):
     print("\nLet me check if i can fix that shit..")
     Excluded = ChunkStory(LastCType)
     Needle = CLoffI+16

     while Needle < len(DATAX):

       scopex = DATAX[Needle:Needle+8]
       scope  = bytes.fromhex(scopex).decode(errors="ignore")
       NeedleI = int(Needle/2)
       NeedleX = hex(int(Needle/2))
       Data_End_OffsetI = NeedleI -8

       for Chk in CHUNKS:
             if Chk.lower() == scope.lower():
                 print("\nBingo!!!\n\nFound the closest Chunk to our position:%s at offset %s %s"%(Chk,NeedleI,NeedleX))
                 if Chk in Excluded:
                        print("\n..But that chunk [%s] is not supposed to be here !\nITS A TRAP!\nRUN!!!!!!!\nRUN TO THE CHOPPER !!!\n")
                        exit()
                 else:
                      print("That chunk length seems legit..\n")
                      LenCalc = Data_End_OffsetI-CDoffB
                      FixedLen= str('0x%08X' % LenCalc)[2::] # str('0x%08X' % LenCalc)[2::].encode().hex()
                      FixShit(FixedLen,CLoffI,CLoffI+8)
                      return()
       Needle += 1
     print("...??\n\nJust Reach the EOF and found nothing!!\nCan't do much about that sorry ...\n")
     exit()

def ChunkStory(lastchunk):
  Before_PLTE= [b'PNG', b'IHDR', b'gAMA', b'cHRM', b'iCCP', b'sRGB', b'sBIT']
  After_PLTE= [b'tRNS', b'hIST', b'bKGD'] #but before idat
  Before_IDAT=[b'sPLT',b'sBIT', b'pHYs', b'tRNS', b'hIST', b'bKGD', b'gAMA', b'cHRM', b'PLTE', b'IHDR', b'bKGD']
  OnlyOnce=[b'sBIT', b'IEND', b'tRNS', b'hIST', b'sTER', b'iCCP', b'sRGB', b'gAMA', b'sCAL', b'cHRM', b'bKGD', b'IHDR', b'oFFs', b'pCAL', b'PLTE', b'pHYs', b'IEND']
  Anywhere=[b'tIME', b'tEXt', b'zTXt', b'iTXt', b'fRAc', b'gIFg', b'gIFx', b'gIFt']

  try:
     lastchunk = lastchunk.encode()
  except Exception as e:
     print("Error:",e)

  if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
        print("After Png Header always Follow IHDR its quite hard to miss..\nExcluding evrything else")
        return(exclude for exclude in Chunks_History if exclude != "IHDR")

  Used_Chunks = list(dict.fromkeys(Chunks_History))

  Excluded = [used for used in Used_Chunks if used in OnlyOnce]
  if b"IDAT" not in Used_Chunks:

      if lastchunk in Before_PLTE:
         shutup = [Excluded.append(forbid.encode()) for forbid in CHUNKS if forbid.encode() not in Before_PLTE]
         print("%s chunk must be placed before any PLTE realted chunks we can forget about thoses:\n%s"%(lastchunk,Excluded))

      if lastchunk in After_PLTE:
        shutup = [Excluded.append(forbid.encode()) for forbid in CHUNKS if forbid.encode() in Before_PLTE]
        print("%s chunk must be placed after PLTE realted chunks we can forget about thoses:\n%s"%(lastchunk,Excluded))

  elif b"IDAT" in Used_Chunks:
          shutup = [Excluded.append(forbid.encode()) for forbid in CHUNKS if forbid.encode() in Before_IDAT]
          if lastchunk == b"IDAT":
             print("So ..the last Chunk Type was IDAT so we either looking for another IDAT,IEND or one of them:\n",Anywhere)

  return(Excluded)



def BruteChunk(CType,LastCType,bytesnbr):
   BingoLst = []
   CTypeLst = [i.lower() for i in CType]

   print("\nMaybe the name got corrupted somehow.\nLet's see about that.\n")

   Excluded = ChunkStory(LastCType)
   print(Excluded)
   
   for name in CHUNKS:
       if name.encode() not in Excluded:
           Bingo = 0
           ChkLst = [i.lower() for i in name]
           for i,j in zip(CTypeLst,ChkLst):
                if i == j:
                    Bingo += 1
           BingoLst.append(str(Bingo)+" "+str(name))

   [print(i) for i in BingoLst]

   BingoLst.sort(key=SplitDigits)
   BingoLst = BingoLst[::-1]

   BestBingoScore = BingoLst[0].split(" ")[0]
   BestBingoName = BingoLst[0].split(" ")[1]

   BestBingoCount = len([b.count(BestBingoScore) for b in BingoLst if int(b.count(BestBingoScore)) > 0])

   if BestBingoCount < 2:

      print("\nAh looks like we've got a winner! :",BestBingoName)
      FixShit(BestBingoName.encode().hex(),CrcoffI+16,CrcoffI+24)
      return()
   else:
       print("\nAh it seems that i can't make up a decision by myself ...\nI need you to choose something that look like [%s] \nCan you help ?\nOk Please select the right name for the chunk: "%str(CType))
       for i,j in enumerate(BingoLst):
           print("Score %s ,if you choose this name enter number: %s"%(j,i))
       print("If you think this is a length problem type : len")
       print("\nOr Type quit to ...quit.\n")
       Choice = input("WHO'S THAT POKEMON !? :")
       while True:
          try:
             if (Choice.lower() != "quit" or Choice.lower() != "len") and int(Choice) <= len(BingoLst):
                  FixShit(BingoLst[int(Choice)].encode().hex(),CrcoffI+16,CrcoffI+24)
                  return()
          except Exception as e:
              print("Error: ",e)
          if Choice.lower() =="quit":
                    print("Take Care Bye !")
                    exit()
          if Choice.lower() =="len":
                     print("A length prob ?")
                     NearbyChunk(CType,bytesnbr,LastCType)
                     return()
          Choice = input("WHO'S THAT POKEMON !? :")

def CheckChunkName(ChunkType,bytesnbr,LastCType):
   CType = ChunkType
   CType = bytes.fromhex(CType).decode(errors="replace").lower()
   for name in CHUNKS:
       if name.lower() == CType:
               if name.lower() == CType:
                      print("\nChunk name:OK     8)")
                      ToHistory(bytes.fromhex(ChunkType))
                      return(None)

               else:
                      print("\nChunk name:FAIL 8(")
                      print("\nMonkey wanted Banana :",name)
                      print("Monkey got Pullover :",CType)
                      print()
                      FixShit(name.encode().hex(),CLoffI,CLoffI+8)
                      return()

   print("\nChunk name:FAILED 8(")
   print("That Chunk name is unknown...")
   LastCType = bytes.fromhex(str(LastCType)).decode()
   if len(CType) >=4:
           BruteChunk(CType,LastCType,bytesnbr)
           return()
   else:
        print("\nOk it may be related to the fact that there's nothing at this offset.....\n")
        
   wow = int(bytesnbr/8912)
   if wow >= 3:
      print("..Hum ..Zlib put a limit on buff size up to 8912 bytes..\n and this one is pretty big :%s which is %s times bigger."%(bytesnbr,wow))
   else:
      print("..Hum ..Zlib put a limit on buff size up to 8912 bytes..\n and this one is pretty big :%s\nMaybe thats a lenght problem."%bytesnbr)
   NearbyChunk(CType,bytesnbr,LastCType)
   return()
#CheckLength(Chunk_Data,Chunk_Length,Chunk_Type,CLoffI,CLoffI+8)
def CheckLength(Cdata,Clen,Ctype):

       GoodEnding = "0000000049454E44AE426082"
       NextChunk = DATAX[CLoffI+32+len(Cdata):CLoffI+32+len(Cdata)+8]

       if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
               CheckChunkName(Ctype,int(Clen,16),Chunks_History[0])

       print("\n===========================")
       print("Checking Length:")
       print("===========================")
       print("So ..The lenght part is saying that data is %s bytes long."%int(Clen, 16))

       if int(Clen,16)>26736:
           print("Wow!? That much ?")
       if len(bytes.fromhex(NextChunk).decode(errors="replace")) == 0:
            print("..And this is what iv found there: [NOTHING]")
       else:
            print("..And this is what iv found there: ",bytes.fromhex(NextChunk).decode(errors="replace"))

       if bytes.fromhex(Ctype) == b'IEND' and int(Clen, 16) == 0:
            if DATAX[-len(GoodEnding):].upper() == GoodEnding:

                     print("\nOk it may be related to the fact that this is the end of file ...Maybe...\n")
                     print("=====================================")
                     print("All Done here hoped that has worked !")
                     print("=====================================")
                     exit()
            else:
                print(DATAX[-len(GoodEnding):])
                exit()
     


       CheckChunkName(NextChunk,int(Clen,16),Ctype)

def Checksum(Ctype, Cdata, Crc):
    Cdata = bytes.fromhex(Cdata)
    Ctype = bytes.fromhex(Ctype)
    Crc = hex(int.from_bytes(bytes.fromhex(Crc),byteorder='big'))
    checksum = hex(binascii.crc32(Ctype+Cdata))
    if checksum == Crc:
        print("Crc Check :OK     8)")
        return(None)
    else:
        print("Crc Check :FAILED 8(")
        if len(Crc) == 0 or len(checksum) == 0:
             print("\nMonkey wanted Banana :",checksum)
             print("Monkey got Pullover :",Crc)
             print("Hold on a sec ... Must have missed something...")
             print()
             exit()

        if len(checksum) < 10:
             checksum = "0x"+(checksum[2::].zfill(8))
        print("\nMonkey wanted Banana :",checksum)
        print("Monkey got Pullover :",Crc)
#        pause = input("pause")
        FixShit(checksum[2::],CrcoffI,CrcoffI+8)


def FixShit(shit,start,end):
         print("\n===========================")
         print("Fixing shit..")
         print("===========================")
         print("Inserting : ",shit)

         Before = DATAX[:start]
         After = DATAX[end:]
         Fix = Before + shit + After
         SaveClone(Fix)


def SaveClone(data):
         global Sample
         global Have_A_KitKat
         
         data = bytes.fromhex(data)
         name,dir = Naming(FILE_Origin)

         print("Saving to : ",dir+"/"+name)
         with open(dir+"/"+name,"wb") as f:
             f.write(data)
         Sample = dir+"/"+name
         Have_A_KitKat = True
         #pause =input("pause:")
         return(None)

def Naming(filename):

    newdir = FILE_DIR+"Folder_"+ str(os.path.basename(filename))
    newdir = os.path.splitext(newdir)[0]
    if not os.path.exists(newdir):
      os.mkdir(newdir)
    filename = os.path.basename(filename)

    if "." in filename:
      filename = os.path.splitext(filename)[0]
    filename += "."
    fileid=0
    check=os.path.exists(newdir+"/"+filename+str(fileid)+"_Fixed.png")
    while check == True:
         fileid += 1
         check=os.path.exists(newdir+"/"+filename+str(fileid)+"_Fixed.png")
    filename = filename+str(fileid)+"_Fixed.png"

    return(filename,newdir)



parser = ArgumentParser()
parser.add_argument("-f","--file",dest="FILENAME",help="File path.",default=None,metavar="FILE")
Args = parser.parse_args()

if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)
if Args.FILENAME is None:
    print("-f,--filename arguments is missing.")
    sys.exit(1)

FILE_Origin = Args.FILENAME
FILE_DIR = os.path.dirname(os.path.realpath(FILE_Origin))+"/"
Have_A_KitKat= False
CHUNKS = ['sBIT', 'IEND', 'sPLT', 'tRNS', 'fRAc', 'hIST', 'dSIG', 'sTER', 'iCCP', 'sRGB', 'zTXt', 'gAMA', 'IDAT', 'sCAL', 'cHRM', 'bKGD', 'tEXt','tIME', 'iTXt', 'IHDR', 'gIFx', 'gIFg', 'oFFs', 'pCAL', 'PLTE', 'gIFt', 'pHYs']
PNGHEADER ="89504e470d0a1a0a"
CLoffX=""
CLoffB=""
CLoffI=""
CToffX=""
CToffB=""
CToffI=""
CDoffX=""
CDoffB=""
CDoffI=""
CrcoffX=""
CrcoffB=""
CrcoffI=""
IHDR_Height= ""
IHDR_Width= ""
IHDR_Depht= ""
IHDR_Color= ""
IHDR_Method= ""
IHDR_Interlace= ""
bKGD_Gray= ""
bKGD_Red= ""
bKGD_Green= ""
bKGD_Blue= ""
bKGD_Index= ""
PLTE_R=""
PLTE_G=""
PLTE_B=""
cHRM_WhiteX= ""
cHRM_WhiteY= ""
cHRM_Redx= ""
cHRM_Redy= ""
cHRM_Greenx= ""
cHRM_Greeny= ""
cHRM_Bluex= ""
cHRM_Bluey= ""
gAMA= ""
hIST1= ""
hIST2= ""
hIST3= ""
hIST4= ""
hIST5= ""
hIST6= ""
hIST7= ""
hIST8= ""
pHYs_Y=""
pHYs_X=""
pHYs_Unit=""
sBIT_Gray=""
sBIT_True=""
sBIT_indexed=""
sBIT_GrayAlpha=""
sBIT_TrueAlpha=""
tEXt_Key=""
tEXt_sep=""
tEXt_Text=""
tIME_Yr=""
tIME_Mth=""
tIME_Day=""
tIME_Hr=""
tIME_Min=""
tIME_Sec=""
tRNS_Gray=""
tRNS_TrueR=""
tRNS_TrueG=""
tRNS_TrueB=""
tRNS_Index=[]
ZtXt_Key=""
ZtXt_sep=""
ZtXt_Meth=""
ZtXt_Text=""
Sample = FILE_Origin
i = 0
while True:
     Chunks_History = []
     print("\n\n")
     print("="*(len(Sample)+9))
     print("Opening:",Sample)
     print("="*(len(Sample)+9))
     print("\n\n")

     with open(Sample,"rb") as f:
         data = f.read()
     DATAX = data.hex()
     FindMagic(PNGHEADER)
