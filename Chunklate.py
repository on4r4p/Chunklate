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
    except AttributeError as e:
         pass
    Chunks_History.append(chunk)
def TheEnd():
     print("\n===========================")
     print("==========The=End==========")
     print("===========================\n")
     sys.exit()

def ToBitstory(bytenbr):
    global Bytes_History
    Bytes_History.append(bytenbr)

def FindMagic():
     print("\n===========================")
     print("Looking for magic header:")
     print("===========================\n")

     magic = "89504e470d0a1a0a"
     magc= "89504e470a1a0a00"

     lenmagic = len(magic)
     pos = DATAX.find(magic)
     if pos != -1:
          ToHistory("PNG")
          print("%s is Magic : %s"%(Sample_Name,DATAX[:lenmagic]))
          print("Found Png Signature at offset : hex %s bytes %s index %s\n"%(hex(int(pos/2)),int(pos/2),pos))
          if DATAX.startswith(magic) is False:
                print("Mkay ...I like where this is going ..\nI will have to cut %s bytes from %s since png header starts at this offset %s .\n"%(Sample_Name,int(pos/2),hex(int(pos/2))))
                Zankentsu = DATAX[pos::]
                SaveClone(Zankentsu)
          else:
              return(ReadPng(pos+lenmagic))

     else:
         print("\n\n%s isn't magic at all !!\n"%Sample_Name)
         print("This better be a real png or else ....")

         pos = DATAX.find(magc)
         if pos != -1:
             print("Wait a sec ..Oh!\nOww....This is bad news i m afraid..\n%s is badly corrupted due to line feed conversion between OS...\nI cannot guarantee any results but i will try my best ...\n",Sample_Name)
             print("TODO")
             TheEnd()

         print("\nTss..Ok let's dig a little bit deeper..\n")
         return(FindFuckingMagic())

def FindFuckingMagic():
     print("\n===========================")
     print("Looking harder for magic header:")
     print("===========================\n")
     print("This may take me sometimes please wait ..\n")
     FullMagic="89504e470d0a1a0a0000000d49484452"
     m_a_g_i_c = [i for i in FullMagic]
     start= 0
     end = len(FullMagic)
     BingoList = []
     while end <= len(DATAX):
            Bingo = 0 
            sample = DATAX[start:end]
            s_a_m_p_l_e = [i for i in sample]
            for i,j in zip(m_a_g_i_c,s_a_m_p_l_e):
                if i == j:
                    Bingo += 1
            BingoList.append(str(Bingo)+" "+str(sample))
            start+=1
            end+=1
     BingoList.sort(key=SplitDigits)
     BingoList = BingoList[::-1]
     BestBingoScore = BingoList[0].split(" ")[0]
     BestBingoSig = BingoList[0].split(" ")[1]
     BestBingoCount = len([b.split(" ")[0].count(BestBingoScore) for b in BingoList if int(b.split(" ")[0].count(BestBingoScore)) > 0])
         
     if BestBingoCount <= 2 and int(BestBingoScore) >= 14:
         pos = DATAX.find(BestBingoSig)
         print("\n...And Done!\n\nThis is what iv got at offset %s with a score of %s/32 : %s \nI think that a start to work with don't you think ?\nLets fix this corrupted signature and see where it leads us ...\n"%(hex(int(pos/2)),BestBingoScore,BestBingoSig))

         Odin = FullMagic + DATAX[pos+len(FullMagic)::]
         SaveClone(Odin)

     else:
         print("count:",BestBingoCount)
         print("score:",BestBingoScore)
         print("\nFewww ...Looks like there are multiple potentials signatures gona have to test them all.\nTODO")
         [print(BingoList[i]) for i in range(0,20)]
         TheEnd()

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
         print("===========================\n")
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

     print("Reached End of %s",Sample_Name)
     TheEnd()

def Double_Check(CType,bytesnbr,LastCType):
     print("\n===========================")
     print("Double Check:")
     print("===========================\n")

     print("Or maybe am i missing something ?\nJust let me double check again just to be sure...")

     if len(DATAX)/2 < 67 :
        print("\n...\n\nERrr...\nThere are not enough bytes in %s to be a valid png.\n%s is %s bytes long and the very minimum size for a png is 67 bytes so...\ni can't help you much further sorry.\n"%(Sample_Name,Sample_Name,int(len(DATAX)/2)))
        TheEnd()

     print("But this time let's forget about the usual specifications of png format\nThis way i will be able to know if a chunk is missing somewhere.\n")

     NearbyChunk(CType,bytesnbr,LastCType,DoubleCheck=True)


def NearbyChunk(CType,bytesnbr,LastCType,DoubleCheck=None):
     print("\nLet me check if i can fix that shit..")

     if DoubleCheck is None:
         Excluded = ChunkStory(LastCType)
     else:
         print("\n==Safety Off==\n")
         Excluded = []

     Needle = CLoffI+16

     while Needle < len(DATAX):

       scopex = DATAX[Needle:Needle+8]
       try:
         scope  = bytes.fromhex(scopex).lower()
#         print(scope)
#         print(len(scope))
       except Exception as e:
         print("Error:",e)
         print("Scopex",scopex)
         sys.exit()
       NeedleI = int(Needle/2)
       NeedleX = hex(int(Needle/2))
       Data_End_OffsetI = NeedleI -8

       for Chk in CHUNKS:
#             print("chk.lower ",Chk.lower())
#             print("scope.lower ",scope)
#             print(Chk.lower() == scope)
             if Chk.lower() == scope:
                 print("\nBingo!!!\n\nFound the closest Chunk to our position:%s at offset %s %s"%(Chk,NeedleX,NeedleI))
                 if Chk in Excluded:
                        print("\n...\n\nBut that chunk [%s] is not supposed to be here !\n\nITS A TRAP!\n\nRUN !!!!!!!\n\nRUN TO THE CHOPPER !!!\n"%Chk)
                        print("\n\nI seriously doubt i coud be of any use with this one ..")
                        print("If you are sure %s is a png i can try to fill the gap but i cannot guarantee any result.."%Sample_Name)
                        if b'IHDR' not in Chunks_History :
                             print("Especially without IHDR chunk..\n")
                        print("TODO")
                        exit()
                 else:
                      LenCalc = Data_End_OffsetI-CDoffB
                      if "-" in str(LenCalc):
                         print("\nAnother one byte the dust ...\nGot Wrong Result for lenght...:",LenCalc)
                         print("dataendofI:",Data_End_OffsetI)
                         print("CDoffb:",CDoffB)
                         print("TODO")
                         TheEnd()
                      print("That chunk position seems legit..\n")
                      FixedLen= str('0x%08X' % LenCalc)[2::] # str('0x%08X' % LenCalc)[2::].encode().hex()
                      FixShit(FixedLen,CLoffI,CLoffI+8)
                      return()
       Needle += 1
     if DoubleCheck is True:
        print("...??\n\nNOTHING AGAIN!?!?!?!?\n")
        print("\n\nTHEY PLAYED US LIKE A DAMN FIDDLE !!!\n\nAMa Outta Here !\n\nDo It YourSelf FFS!")
        TheEnd()
     else:
         print("\n...??\n\nJust Reach the EOF and found nothing!!\nCan't do much about that sorry ...\n")
     Double_Check(CType,bytesnbr,LastCType)

     return()

def ChunkStory(lastchunk):

  print("\n===========================")
  print("Checking last chunks:")
  print("===========================\n")

  Before_PLTE= [b'PNG', b'IHDR', b'gAMA', b'cHRM', b'iCCP', b'sRGB', b'sBIT']
  After_PLTE= [b'tRNS', b'hIST', b'bKGD'] #but before idat
  Before_IDAT=[b'sPLT',b'sBIT', b'pHYs', b'tRNS', b'hIST', b'bKGD', b'gAMA', b'cHRM', b'PLTE', b'IHDR', b'bKGD']
  OnlyOnce=[b'sBIT', b'IEND', b'tRNS', b'hIST', b'sTER', b'iCCP', b'sRGB', b'gAMA', b'sCAL', b'cHRM', b'bKGD', b'IHDR', b'oFFs', b'pCAL', b'PLTE', b'pHYs', b'IEND']
  Anywhere=[b'tIME', b'tEXt', b'zTXt', b'iTXt', b'fRAc', b'gIFg', b'gIFx', b'gIFt']
  Criticals =[b'PNG',b'IHDR',b'IDAT',b'IEND']
  try:
     lastchunk = lastchunk.encode()
  except AttributeError as e:
     print("Error:",e)

  if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
        print("After Png Header always Follow IHDR this is quite hard to miss..\nExcluding evrything else")
        Excluded = [exclude for exclude in CHUNKS if exclude != b"IHDR"]
        return(Excluded)
  
  Used_Chunks = list(dict.fromkeys(Chunks_History))
  Excluded = [used for used in Used_Chunks if used in OnlyOnce]

  print("So far we came across those chunks in %s :\n\n%s\n"%(Sample_Name,[i.decode() for i in Used_Chunks]))

  if b"IDAT" not in Used_Chunks:

      if lastchunk in Before_PLTE and b'IHDR' not in Used_Chunks:
         shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid not in Before_PLTE]
         print("%s chunk must be placed before any PLTE related chunks we can forget about thoses:\n\n%s"%(lastchunk.decode(),[i.decode() for i in Excluded]))


      if lastchunk in After_PLTE:
        shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_PLTE]
        print("%s chunk must be placed after PLTE related chunks we can forget about thoses:\n\n%s"%(lastchunk,[i.decode() for i in Excluded]))

  elif b"IDAT" in Used_Chunks:
          shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_IDAT]

          if int(IHDR_Color) == 3:
                shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid not in Before_PLTE]
                print("\nAH ! I knew this day would come ...\nYou See when Image Header color type is set to 3 (Indexed Colors)..\nPLTE chunk must be placed before any IDAT chunks so that only means one thing ..More code to write for me.\n(TODO)")
                TheEnd()
          elif (int(IHDR_Color) == 2) or (int(IHDR_Color) == 6):
               print("#################\nWarning:\nJust wanted you to know that if im not able to fix %s for some reason\nor if you can't view %s once my job is done here ...\nThis is maybe due to a PLTE Chunk that is missing between those guys :\n-------------------------------------------------------\n%s\n+++++++++++++++++\n***[PLTECHUNK]***\n+++++++++++++++++\n%s\n\nIn Any cases it's before IDAT. \n#################\n-------------------------------------------------------\n"%(Sample_Name,Sample_Name,[i.decode() for i in Before_PLTE],[i.decode() for i in After_PLTE]))


          if lastchunk == b"IDAT":
             print("So ..the last Chunk Type was IDAT so we either looking for another IDAT,IEND or one of them:\n\n%s"%[i.decode() for i in Anywhere])

  return(Excluded)



def BruteChunk(CType,LastCType,bytesnbr):
   ErrorA = False
   BingoLst = []
   try:
      CTypeLst = [i.lower() for i in CType]
   except AttributeError as a:
      print("Error:",a)
      CTypeLst = [i for i in CType]
      ErrorA = True

   print("\nMaybe it's name got corrupted somehow.\nLet's see about that.\n")

   Excluded = ChunkStory(LastCType)
   
   for name in CHUNKS:
       if name not in Excluded:
           Bingo = 0
           if ErrorA is True:
               ChkLst = [i for i in name]
           else:
               ChkLst = [i.lower() for i in name]
           for i,j in zip(CTypeLst,ChkLst):
                if i == j:
                    Bingo += 1
           BingoLst.append(str(Bingo)+" "+name.decode())

#   [print(i) for i in BingoLst]

   BingoLst.sort(key=SplitDigits)
   BingoLst = BingoLst[::-1]

   BestBingoScore = BingoLst[0].split(" ")[0]
   BestBingoName = BingoLst[0].split(" ")[1]

   BestBingoCount = len([b.count(BestBingoScore) for b in BingoLst if int(b.count(BestBingoScore)) > 0])

   if BestBingoCount <= 2 and int(BestBingoScore) >=2:
#      print(BingoLst)
      print("\nAh looks like we've got a winner! :",BestBingoName)
##TmpFix##
      FixShit(BestBingoName.encode().hex(),CrcoffI+16,CrcoffI+24)
      return()
   else:
       print("\n===========================")
       print("WHO'S THAT POKEMON !?:")
       print("===========================")
       print("\nArg that's all gibberish ...\nI need you to choose something looking a like [%s] that is actually a real chunk name can you help ?\nOk Please select the right name for the chunk:\n"%str(CType))

       for i,j in enumerate(BingoLst):
           print("Score %s ,if you choose this name enter number: %s"%(j,i))

       print("\nIf you as lost as me then this might be a Length Problem type : wtf")
       print("\nOr Type quit to ...quit.\n")
       Choice = input("WHO'S THAT POKEMON !? :")
       while True:
          try:
             if (Choice.lower() != "quit" or Choice.lower() != "wtf") and int(Choice) <= len(BingoLst):
                  FixShit(BingoLst[int(Choice)].encode().hex(),CrcoffI+16,CrcoffI+24)
                  return()
          except Exception as e:
#              print("Error: ",e)
               pass

          if Choice.lower() =="quit":
                    print("Take Care Bye !")
                    exit()
          if Choice.lower() =="wtf":
                     print("\nA length prob you say?")
                     NearbyChunk(CType,bytesnbr,LastCType)
                     return()
          Choice = input("WHO'S THAT POKEMON !? :")

def CheckChunkName(ChunkType,bytesnbr,LastCType):
   CType = ChunkType
   try:
       CType = bytes.fromhex(CType)
#       CType = bytes.fromhex(CType).decode(errors="replace")
   except Exception as e:
        print("Error:",e)
        print("ctyp ",CType)
        print(type(CType))

   for name in CHUNKS:
       if name.lower() == CType.lower():
               if name == CType:
                      print("\nChunk name:OK     8)")
                      ToHistory(bytes.fromhex(ChunkType))
                      return(None)

               else:
                      print("\nChunk name:FAIL 8(")
                      print("\nMonkey wanted Banana :",name)
                      print("Monkey got Pullover :",CType)
                      print()
                      FixShit(name.hex(),CLoffI,CLoffI+8)
                      return()

   print("\nChunk name:FAILED 8(")
   try:
      LastCType = bytes.fromhex(str(LastCType)).decode()
   except Exception as e:
        print("Error:",e)
        LastCType = LastCType.decode()

   if len(CType) >=4:
           BruteChunk(CType,LastCType,bytesnbr)
           return()
   else:
        print("\nOf course it has failed! There's nothing at this offset.....\n")
        
   wow = int(bytesnbr/8912)
   if wow >= 3:
      print("..Hum ..Zlib put a limit on buff size up to 8912 bytes..\n and this one is pretty big :%s which is %s times bigger.."%(bytesnbr,wow))
#      print(Bytes_History)
#      print(Bytes_History.count(Bytes_History[0])-1 == len(Bytes_History)-1)
#      print(Bytes_History.count(Bytes_History[0]) != len(Bytes_History))
      if len(Bytes_History) >0: ##ToFIx##
        if Bytes_History.count(Bytes_History[0])-1 == len(Bytes_History)-1:
            if Bytes_History.count(Bytes_History[0]) != len(Bytes_History):
                print("That doesnt mean there cannot be an IDAT chunk bigger than 8912Bytes!\nbut since all previous IDAT chunks were %s bytes long , it seems to me that's a little odd that this very one in particular is different from the others...\nUnless this is the Last IDAT.\nAnyway that is just a thought let's find it out .")
   else:
      print("..Hum ..Maybe thats a lenght problem.")
   NearbyChunk(CType,bytesnbr,LastCType)
   return()

def CheckLength(Cdata,Clen,Ctype):

       GoodEnding = "0000000049454E44AE426082"
       NextChunk = DATAX[CLoffI+32+len(Cdata):CLoffI+32+len(Cdata)+8]

       if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
               CheckChunkName(Ctype,int(Clen,16),Chunks_History[0])

       print("\n===========================")
       print("Checking Data Length:")
       print("===========================")
       
       print("So ..The lenght part is saying that data is %s bytes long."%int(Clen, 16))

       ToBitstory(int(Clen, 16))

       if int(Clen,16)>26736:
           print("Really!? That much ?")
       if len(bytes.fromhex(NextChunk).decode(errors="replace")) == 0:
            print("..And this is what iv found there: [NOTHING]")
       else:
            print("..And this is what iv found there: ",bytes.fromhex(NextChunk).decode(errors="replace"))

       if bytes.fromhex(Ctype) == b'IEND' and int(Clen, 16) == 0:
            if DATAX[-len(GoodEnding):].upper() == GoodEnding:

                     print("\nOk it may be related to the fucking fact that this is the end of file !!!")
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
         pause =input("pause:")
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
CHUNKS = [b'sBIT', b'IEND', b'sPLT', b'tRNS', b'fRAc', b'hIST', b'dSIG', b'sTER', b'iCCP', b'sRGB', b'zTXt', b'gAMA', b'IDAT', b'sCAL', b'cHRM', b'bKGD', b'tEXt', b'tIME', b'iTXt', b'IHDR', b'gIFx', b'gIFg', b'oFFs', b'pCAL', b'PLTE', b'gIFt', b'pHYs']
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
     Bytes_History = []
     print("\n")
     print("="*(len(Sample)+9))
     print("Opening:",Sample)
     print("="*(len(Sample)+9))
     print("\n")
     Sample_Name = os.path.basename(Sample)
     with open(Sample,"rb") as f:
         data = f.read()
     DATAX = data.hex()
     print("Done.")
     FindMagic()
