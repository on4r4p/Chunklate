#!/usr/bin/python3.6
from argparse import ArgumentParser
from threading import Thread
from datetime import datetime
import sys , os , binascii ,re ,random ,time , zlib


def Chunklate(sec):

   if os.name == "nt":
       print("""
╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮
  <[0x00000016]>[C|H|U|N|K|L|A|T|E]<[0x98bd5cb8]>
╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯
""")
       if PAUSE is True:
            time.sleep(sec)

       return

   color=["\033[1;31;49m","\033[1;32;49m","\033[1;34;49m","\033[1;35;49m","\033[1;33;49m","\033[1;37;49m"]

   lenght = "<[0x00000016]>"
   crc = "<[0x98bd5cb8]>"

   title = "\033[1;37;49m[\033[mC\033[1;37;49m|\033[mH\033[1;37;49m|\033[mU\033[1;37;49m|\033[mN\033[1;37;49m|\033[mK\033[1;37;49m|\033[mL\033[1;37;49m|\033[mA\033[1;37;49m|\033[mT\033[1;37;49m|\033[mE\033[1;37;49m]\033[m"

   top = "\n╭─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╮"
   bot = "╰─━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━─╯\n"

   t_o_p = [i for i in top]
   b_o_t = [i for i in bot]

   l_e_n = [i for i in lenght]
   c_r_c = [i for i in crc]

   colored_len = ""
   colored_crc = ""
   toped = ""
   boted = ""
   
   for i,j in zip(l_e_n,c_r_c):

        rnd = random.randint(0,len(color)-1)
        tmp = str(color[rnd])+str(i)+str("\033[m")

        rnd2 = random.randint(0,len(color)-1)
        tmp2 = str(color[rnd])+str(j)+str("\033[m")

        colored_len += tmp
        colored_crc += tmp2

   for i,j in zip(t_o_p,b_o_t):

        rnd2 = random.randint(0,len(color)-1)
        rnd3 = random.randint(0,len(color)-1)

        tmp2 = str(color[rnd2])+str(i)+str("\033[m")
        tmp3 = str(color[rnd3])+str(j)+str("\033[m")

        toped += tmp2
        boted += tmp3

   print(toped)
   print("  "+colored_len+title+colored_crc)
   print(boted)

   if PAUSE is True:
      time.sleep(sec)

def Minibar():
  global CharPos
  global GoBack
  global Loading_txt
  global Loading_sep
  point="."
  space=" "
  lnt = len(Loading_txt)
  if lnt < MAXCHAR and GoBack is False:
        Loading_txt = (point * CharPos) + space
        CharPos += 1
        print(Loading_txt, end = '\r')
        lnt = len(Loading_txt)
  else:
      if lnt > 2:
        GoBack = True
        Loading_txt = (point * CharPos) + space
        CharPos -= 1
        print(Loading_txt, end = '\r')
        lnt = len(Loading_txt)
      else:
        GoBack = False

def Loadingbar():

  Loading_txt=""
  GoBack = False
  CharPos =0
  PosLine = 0
  Tail = 0 
  MAXCHAR = int(os.get_terminal_size(0)[0])-1
  Line = "¸.·´¯`·.¸"
  Linelst=[]
  FishR = ["><(((º>","⸌<(((º>","><(((º>","⸝<(((º>"]
  FishL = ["<º)))><","<º)))>⸍","<º)))><","<º)))>⸜"]
  Trail = 3 * len(Line)
  TrailEnd = 0

  for i in range(0,MAXCHAR+7):
    if PosLine <= len(Line)-1:
         Linelst.append(Line[PosLine])
    else:
         PosLine = 0
         Linelst.append(Line[PosLine])
    PosLine += 1

  while WORKING == True:
     time.sleep(0.1)
     Ln = len(Loading_txt)
     if Ln < MAXCHAR-7 :
           if CharPos >=  Trail:
                Loading_txt = (" "*TrailEnd )+ Loading_txt[TrailEnd:]
                Loading_txt += Linelst[CharPos]
                TrailEnd += 1
           else:

               Loading_txt += Linelst[CharPos]

           if Tail > 3:
              Tail = 0

           print(Loading_txt+FishR[Tail], end = '\r')
           CharPos += 1
           Ln = len(Loading_txt)
           Tail += 1
     else:

                fishapear =(MAXCHAR-7) - (CharPos)
                Loading_txt = (" "*TrailEnd )+ Loading_txt[TrailEnd:]
                if fishapear >= -7:
                    Loading_txt += Linelst[CharPos]
                TrailEnd += 1

                if Tail > 3:
                   Tail = 0

                print(Loading_txt+FishR[Tail][:fishapear], end = '\r')
                CharPos += 1
                Tail += 1
                if TrailEnd >= MAXCHAR+2:

                    Loading_txt=""
                    PosLine = 0
                    Trail = 3 * len(Line)
                    Tail = 0 
                    TrailEnd = 0
                    CharPos =0
  return


def Sumform(waitforit,switch):
    if switch is True:
        sepa =" ▁ ▂ ▄ ▅ ▆ ▇ █ "
        rator=" █ ▇ ▆ ▅ ▄ ▂ ▁ "
    else:
        sepa =" ▁ ▂ ▄ ▅ ▆ ▇ █ █ ▇ ▆ ▅ ▄ ▂ ▁"
        rator  ="▁ ▂ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▂ ▁"

    Spaaaaaaaace = " " * int((MAXCHAR/2)-(len(sepa+waitforit+rator)/2))
    Seperator = "\n"+Spaaaaaaaace+sepa + waitforit +rator+"\n\n"
    return(Seperator)

def Summarise(infos,Summary_Footer=False):
         global Summary_Header

         folder = FILE_DIR+"Folder_"+ str(os.path.basename(FILE_Origin))
         folder = os.path.splitext(folder)[0]+"/"
         sep = "\n\n『" +Sample_Name+" :』\n"
         title = Sumform("▇ ▆ =|C|h|u|n|k|l|a|t|e| |S|u|m|m|a|r|y|= ▆ ▇",True)
         eof =Sumform("_,-=|S|u|m|m|a|r|y| |E|n|d|=-,_",False)
         tmp = ""
         if not os.path.exists(folder):
            os.mkdir(folder)

         if infos is not None:
              if len(SideNote) > 0:
                  for note in SideNote:
                       tmp += "\n"+str(note)+"\n"
                  infos = tmp+infos +"\n"
              else:
                  infos = "\n"+infos+"\n"
         elif len(SideNote) > 0:
                  for note in SideNote:
                       tmp += "\n"+str(note)+"\n"
                  infos = tmp

         filename = folder+"Summary_Of_"+os.path.splitext(os.path.basename(FILE_Origin))[0]
         print(Candy("Color","green","-Saving Summary : Somewhere/over/the/rainbow/blue/birds/are/flying "))
         with open(filename,'a+') as f:

             if Summary_Header is True:
                f.write(title)
                Summary_Header = False

             if infos is not None:
                f.write(sep)
                f.write(infos)

             if Summary_Footer is True:
                f.write("\n\n『File Informations: 』\n")


                if len(IHDR_Height) >0:
                   f.write("\n")
                   f.write("\n-IHDR Width    :"+IHDR_Height)
                if len(IHDR_Height) >0:
                   f.write("\n-IHDR Height   :"+IHDR_Width)
                if len(IHDR_Depht) >0:
                   f.write("\n-IHDR Depht    :"+IHDR_Depht)
                if len(IHDR_Color) >0:
                   f.write("\n-IHDR Color    :"+IHDR_Color)
                if len(IHDR_Method) >0:
                   f.write("\n-IHDR Method   :"+IHDR_Method)
                if len(IHDR_Interlace) >0:
                   f.write("\n-IHDR Interlace:"+IHDR_Interlace)

                if len(pHYs_X) > 0:
                   f.write("\n")
                   f.write("\n-pHYs Pixels per unit, X axis: "+pHYs_X)
                if len(pHYs_Y) > 0:
                   f.write("\n-pHYs Pixels per unit, Y axis: "+pHYs_Y)
                if len(pHYs_Unit) > 0:
                   f.write("\n-pHYs Unit specifier         :"+pHYs_Unit)

                if len(bKGD_Gray) > 0:
                  f.write("\n")
                  f.write("\n-bKGD Gray   :"+bKGD_Gray)
                if len(bKGD_Red) > 0:
                  f.write("\n")
                  f.write("\n-bKGD Red    :"+bKGD_Red)
                if len(bKGD_Green) > 0:
                  f.write("\n-bKGD Green  :"+bKGD_Green)
                if len(bKGD_Blue) > 0:
                  f.write("\n-bKGD Blue   :"+bKGD_Blue)
                if len(bKGD_Index) > 0:
                  f.write("\n-bKGD Palette:"+bKGD_Index)

                if len(gAMA) > 0:
                  f.write("\n")
                  f.write("\n-Gama   :"+gAMA)

                if len(PLTE_R) > 0:
                  f.write("\n")
                  f.write("\n-PLTE Red Palettes    :"+str(len(PLTE_R)))
                if len(PLTE_G) > 0:
                  f.write("\n-PLTE Green Palettes   :"+str(len(PLTE_G)))
                if len(PLTE_B) > 0:
                  f.write("\n-PLTE Blue Palettes    :"+str(len(PLTE_B)))

                if len(sPLT_Red) >0:
                  f.write("\n")
                  f.write("\n-sPLT Suggested Red palette stored:"+str(len(sPLT_Red)))
                if len(sPLT_Green) >0: 
                  f.write("\n-sPLT Suggested Green palettes stored:"+str(len(sPLT_Green)))
                if len(sPLT_Blue) >0: 
                  f.write("\n-sPLT Suggested Blue palettes stored:"+str(len(sPLT_Blue)))
                if len(sPLT_Alpha) >0: 
                  f.write("\n-sPLT Suggested Alpha palettes stored:"+str(len(sPLT_Alpha)))
                if len(sPLT_Freq) >0: 
                  f.write("\n-sPLT Suggested Frequencies palettes stored:"+str(len(sPLT_Freq)))

                if len(hIST) >0:
                   f.write("\n-Histogram frequencies stored:"+str(len(hIST)))

                if len(tRNS_Gray) >0:
                   f.write("\n") 
                   f.write("\n-tRNS Transparency Gray     :"+tRNS_Gray)
                if len(tRNS_TrueR) >0: 
                   f.write("\n-tRNS Transparency Red      :"+tRNS_TrueR)
                if len(tRNS_TrueG) >0: 
                   f.write("\n-tRNS Transparency Green    :"+tRNS_TrueG)
                if len(tRNS_TrueB) >0: 
                   f.write("\n-tRNS Transparency Blue     :"+tRNS_TrueB)
                if len(tRNS_Index) >0:
                   f.write("\n-tRNS Alpha indexes stored:"+str(len(tRNS_Index)))


                if len(sTER) >0:
                   f.write("\n-Subimage mode    :",sTER)

                if len(cHRM_WhiteX) >0:
                   f.write("\n")
                   f.write("\n-cHRM chromaticities WhiteX   :"+cHRM_WhiteX)
                if len(cHRM_WhiteY) >0:
                   f.write("\n-cHRM chromaticities WhiteY   :"+cHRM_WhiteY)
                if len(cHRM_Redx) >0:
                   f.write("\n-cHRM chromaticities RedX     :"+cHRM_Redx)
                if len(cHRM_Redy) >0:
                   f.write("\n-cHRM chromaticities RedY     :"+cHRM_Redy)
                if len(cHRM_Greenx) >0:
                   f.write("\n-cHRM chromaticities GreenX   :"+cHRM_Greenx)
                if len(cHRM_Greeny) >0:
                   f.write("\n-cHRM chromaticities GreenY   :"+cHRM_Greeny)
                if len(cHRM_Bluex) >0:
                   f.write("\n-cHRM chromaticities BlueX   :"+cHRM_Bluex)
                if len(cHRM_Bluey) >0:
                   f.write("\n-cHRM chromaticities BlueY   :"+cHRM_Bluey)

                if len(sBIT_Gray) >0:
                   f.write("\n")
                   f.write("\n-sBIT Significant greyscale bits    :"+sBIT_Gray)
                if len(sBIT_TrueR) >0:
                   f.write("\n-sBIT significant bits Red    :"+sBIT_TrueR)
                if len(sBIT_TrueG) >0:
                   f.write("\n-sBIT significant bits Green  :"+sBIT_TrueG)
                if len(sBIT_TrueB) >0:
                   f.write("\n-sBIT significant bits Blue   :"+sBIT_TrueB)
                if len(sBIT_GrayScale) >0:
                   f.write("\n-sBIT Gray scale significant bit:"+sBIT_GrayScale)
                if len(sBIT_GrayAlpha) >0:
                   f.write("\n-sBIT Gray alpha significant bit:"+sBIT_GrayAlpha)
                if len(sBIT_TrueAlphaR) >0:
                   f.write("\n-sBIT significant bits Alpha Red    :"+sBIT_TrueAlphaR)
                if len(sBIT_TrueAlphaG) >0:
                   f.write("\n-sBIT significant bits Alpha Green  :"+sBIT_TrueAlphaG)
                if len(sBIT_TrueAlphaB) >0:
                   f.write("\n-sBIT significant bits Alpha Blue   :"+sBIT_TrueAlphaB)
                if len(sBIT_TrueAlpha) >0:
                   f.write("\n-sBIT significant bits Alpha        :"+sBIT_TrueAlpha)

                if len(pCAL_Key) >0:
                   f.write("\n")
                   f.write("\n-pCAL Calibration name    :"+bytes.fromhex(pCAL_Key).decode(errors="replace"))
                if len(pCAL_Zero) >0:
                   f.write("\n-pCAL Original zero       :"+pCAL_Zero)
                if len(pCAL_Max) >0:
                   f.write("\n-pCAL Original max        :"+pCAL_Max)
                if len(pCAL_Eq) >0:
                   f.write("\n-pCAL Equation type       :"+pCAL_Eq)
                if len(pCAL_PNBR) >0:
                   f.write("\n-pCAL Number of parameters:"+pCAL_PNBR)


                if len(iCCP_Name) >0:
                  f.write("\n")
                  f.write("\n-iCCP Profile Name :"+iCCP_Name)

                if len(str(iCCP_Method)) >0:
                  f.write("\n-iCCP Profile Method :"+str(iCCP_Method))

                if len(sRGB)>0:
                  f.write("\n")
                  f.write("\n-sRGB Rendering    :"+sRGB)

                if len(tIME_Yr)>0:
                  f.write("\n")
                  f.write("\n-Year     :"+tIME_Yr)
                if len(tIME_Mth)>0:
                  f.write("\n-Month    :"+tIME_Mth)
                if len(tIME_Day)>0:
                  f.write("\n-Day      :"+tIME_Day)
                if len(tIME_Hr)>0:
                  f.write("\n-Hour     :"+tIME_Hr)
                if len(tIME_Min)>0:
                  f.write("\n-Minute   :"+tIME_Min)
                if len(tIME_Sec)>0:
                  f.write("\n-Seconde  :"+tIME_Sec)


                if len(tEXt_Key_List) > 0 and len(tEXt_Key_List) == len(tEXt_Str_List):
                    f.write("\n")
                    for s,k in zip(tEXt_Str_List,tEXt_Key_List):
                        txt = "\n-tEXt %s :\n%s\n"%(k,s)
                        f.write(txt)
                if len(iTXt_Key_List) > 0 and len(iTXt_Key_List) == len(iTXt_String_List):
                    f.write("\n")
                    for s,k in zip(iTXt_String_List,iTXt_Key_List):
                        txt = "\n-iTXt %s :\n%s\n"%(k,s)
                        f.write(txt)

                if len(zTXt_Key_List) > 0 and len(zTXt_Key_List) == len(zTXt_Str_List):
                    f.write("\n")
                    for s,k in zip(zTXt_Str_List,zTXt_Key_List):
                        txt = "\n-zTXt %s :\n%s\n"%(k,s)
                        f.write(txt)

                f.write(eof)




def Candy(mode,arg,data=None):
   if mode == "Emoj":
         rnd = random.randint(0,len("good"))
         if arg == "good":
             good = ["´ ▽ ` )ﾉ","Σ ◕ ◡ ◕","٩(｡͡•‿•｡)۶","ᕕ( ᐛ )ᕗ","☜(⌒▽⌒)☞","(｡◕‿‿◕｡)","(ღ˘⌣˘ღ)","(∪ ◡ ∪)","(▰˘◡˘▰)","(✿ ♥‿♥)","(｡◕ ‿ ◕｡)","( ͡° ͜ʖ ͡°)","(/◔ ◡ ◔)/","(ᵔᴥᵔ)"]
             return(good[rnd])
         elif arg == "bad":
             bad = ["(ಥ﹏ಥ)","(►_◄)","(◉ ︵◉)","ヽ(ｏ`皿′ｏ)ﾉ","凸ಠ益ಠ)凸","╯‵Д′)╯彡┻━┻","¯\_(⊙︿⊙)_/¯","ಠ︵ಠ凸","ヽ(`Д´)ﾉ","(╯°□°）╯︵ ┻━┻","(✖╭╮✖)","(︶︹︺)","(╯︵╰,)","ヽ(˚௰˚)づ"]
             return(bad[rnd])

   if mode == "Color" and os.name != "nt":
         if arg == "red":
            prnt = "\033[1;31;49m%s\033[m"%data
         elif arg == "green":
            prnt = "\033[1;32;49m%s\033[m"%data
         elif arg == "blue":
            prnt = "\033[1;34;49m%s\033[m"%data
         elif arg == "purple":
            prnt = "\033[1;35;49m%s\033[m"%data
         elif arg == "yellow":
            prnt = "\033[1;33;49m%s\033[m"%data
         elif arg == "white":
            prnt = "\033[1;37;49m%s\033[m"%data
         return(prnt)
   elif mode == "Color" and os.name == "nt":
            prnt = data

   if mode == "Title":
       BotL = "╰─"
       BotR = "─╯"
       TopL = "╭─"
       TopR ="─╮"
       Sep = "━"*len(str(arg)) if data == None  else "━"*(len(str(arg)+str(data))+3) if "\x1b[m" not in data else "━"*(len(str(arg)+str(data))-12)
       Toprnt = TopL+Sep+TopR
       Botrnp = BotL+Sep+BotR
       prnt = "  " +str(arg) if data == None else "  " +str(arg) +" "+str(data)
       Title = """
%s
%s
%s
"""%(Toprnt,prnt,Botrnp)
       print(Title)

def SplitDigits(lst):
    return([DigDigits(k) for k in re.split(r'(\d+)',lst)])

def DigDigits(dig):
    return(int(dig) if dig.isdigit() else dig)

def ToHistory(chunk):
    global Chunks_History

    try:
       chunk=chunk.encode()
    except AttributeError as e:
#       print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
        pass
    Chunks_History.append(chunk)
def TheEnd():
     Summarise(None,True)
     Chunklate(0)
     sys.exit(0)

def ToBitstory(bytenbr):
    global Bytes_History
    Bytes_History.append(bytenbr)

def ChunkForcer():
     global WORKING
     global SideNote
     Candy("Title","[DEMO]Attempting To Repair Corrupted Chunk Data:[DEMO]")
     Thread(target = Loadingbar).start()
     time.sleep(30)
     print("\n\nDemo ended.\n")
     SideNote.append( "\n-Launched Data Chunk Bruteforcer.\n-Demo ended well.")
     WORKING = False


def FindMagic():
     global SideNote

     Candy("Title","Looking for magic header:")

     magic = "89504e470d0a1a0a"
     magc= ["89504e470a1a0a00000004948445200","89504e470a1a0a0000000d4948445200"]

     lenmagic = len(magic)
     pos = DATAX.find(magic)
     if pos != -1:
          ToHistory("PNG")
          print("-%s is Magic : %s\n"%(Candy("Color","white",Sample_Name),Candy("Color","green",DATAX[:lenmagic])))
          print("-Found Png Signature at offset (%s/%s/%s): (%s/%s/%s)\n"%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",hex(int(pos/2))),Candy("Color","blue",int(pos/2)),Candy("Color","purple",pos)))
          if DATAX.startswith(magic) is False:
                print("-File does not start with a png signature.\n\nMkay ...I like where this is going ..\nI will have to cut %s bytes from %s since png header starts at this offset %s .\n"%(Candy("Color","white",Sample_Name),Candy("Color","blue",int(pos/2)),Candy("Color","white",Sample_Name),Candy("Color","blue",hex(int(pos/2)))))
                Zankentsu = DATAX[pos::]
                Summarise("-File does not start with a png signature.\n-Found a png signature at offset: %s\n-Creating starting with the right signature."%hex(int(pos/2))) 
                SaveClone(Zankentsu)
          else:
              return(ReadPng(pos+lenmagic))

     else:
         print("-File %s start with valid png signature .\n"%Candy("Color","red","does not"))
         print("This better be a real png or else ....")
         for badnews in magc:
             pos = DATAX.find(badnews)
             if pos != -1:
               if badnews == magc[1]:
                 print("\n-Some bytes are %s from Png Signature..\n\n%s seems corrupted due to line feed conversion between OS...\n\nIt doesnt look that bad...But I ll keep that in mind while im on it.."%(Candy("Color","red","missing"),Candy("Color","white",Sample_Name)))
                 print("\n-Not yet Implemented-\n")
                 SideNote.append("-Corruption due to line feed conversion\n-File may still be recovered.\n-Not yet implemented.")
                 ChunkForcer()
                 TheEnd()

               if badnews == magc[0]: 
                 print("\nHang on a sec....\nThis is bad news i m afraid..\n%s is badly corrupted ...\nI cannot guarantee any results and it may take forever to find a solution...\n"%Sample_Name)
                 print(Candy("Color","yellow","\n-ToDo"))
                 SideNote.append("-Major Corruption due to line feed conversion\n-File may not be recovered.\n-Not yet implemented.")
                 TheEnd()

         print("\nOk let's dig a little bit deeper..\n")
         return(FindFuckingMagic())

def FindFuckingMagic():
     global SideNote

     Candy("Title","Looking harder for magic header:")
     print("This may take me sometimes please wait ..\n")
     FullMagic="89504e470d0a1a0a0000000d49484452"
     m_a_g_i_c = [i for i in FullMagic]
     start= 0
     end = len(FullMagic)
     BingoList = []
     while end <= len(DATAX):
            Minibar()
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
         print("\n...And Done!\n\nThis is what iv got at offset %s with a score of %s/32 : %s \nI think that a start to work with don't you think ?\nLets fix this corrupted signature and see where it leads us ...\n"%(Candy("Color","blue",hex(int(pos/2))),Candy("Color","green",BestBingoScore),Candy("Color","purple",BestBingoSig)))

         Odin = FullMagic + DATAX[pos+len(FullMagic)::]
         SaveClone(Odin)

     elif int(BestBingoScore) >= 14:
         #print("count:",BestBingoCount)
         #print("score:",BestBingoScore)
         print("\n\n")
         [print(BingoList[i]) for i in range(0,20)]
         print("\n\n-Found multiple %s png signatures"%Candy("Color","yellow","potentials"))
         print("\n\nFewww ...\nLooks like i gonna have to test them all.")
         print(Candy("Color","yellow","\n-ToDo"))
         SideNote.append("-Found multiple potentials png signatures\n-Not Implemented yet")
         TheEnd()
     else:
         print("\n\n")
         [print(BingoList[i]) for i in range(0,20)]
         print("\n\n-Matching score :",Candy("Color","red","too low"))
         print("\nFewww ...\nIm afraid i wasn't able to find anything that looks like a png signature.\nMaybe i could try to find if there any Known Chunks names in this file ?")
         print(Candy("Color","yellow","\n-ToDo"))
         SideNote.append("-Png signatures matching score are too low\n-Not Implemented yet")
         TheEnd()

def SaveErrors(Chunk,Err,Data=None):#TODO#TOFIX
   global SideNote
   global ErrorsFlag
   global ErrorsList

   Candy("Title","Keeping Tracks of Errors:")
   print(Candy("Color","purple","-ToDo -Fix crc based on errors found\n-Not Implemented yet\n"))

   if Chunk not in ErrorsFlag: ErrorsFlag.append(Chunk)
   #[ErrorsList.append(Chunk+":"+e) for e in Err] 

   if Chunk == "IHDR":
      if "Width" in Err:
          SideNote.append("-Width : Wrong size Must be between 1 to 2147483647.")
      if "Height" in Err:
          SideNote.append("-Height : Wrong size Must be between 1 to 2147483647.")
      if "Bytes" in Err:
          SideNote.append("-Bytes number :IHDR have to always be 13 bytes.")
      if "Depht" in Err:
         SideNote.append("-Bit depht :Wrong bit value Must be 1,2,4,8 or 16")
      if "Filter" in Err:
         SideNote.append("-Filter Method :Wrong value must be 0.")
      if "Compression" in Err:
         SideNote.append("-Compression Algorithms : Wrong value must be 0.")
      if "Interlace" in Err:
         SideNote.append("-Interlace Method : Wrong value must be 0 (no interlace) or 1 (Adam7 interlace).")

   if Chunk == "pHYs":
      if "Y" in Err:
         SideNote.append("-Pixels per unit, Y axis : Wrong size Must be between 1 to 2147483647.")
      if "X" in Err:
         SideNote.append("-Pixels per unit, X axis : Wrong size Must be between 1 to 2147483647.")
      if "Unit" in Err:
          SideNote.append("-Unit specifier : Must be between 0 (unknown) or 1(meter).")

   if Chunk == "bKGD":
      if "Gray" in Err:
          SideNote.append("-Gray level :Wrong value Must be less than "+str((2**int(IHDR_Depht))-1))
      if "Red" in Err:
          SideNote.append("-Red level :Wrong value Must be less than "+str((2**int(IHDR_Depht))-1))
      if "Green" in Err:
          SideNote.append("-Green level :Wrong value Must be less than "+str((2**int(IHDR_Depht))-1))
      if "Blue" in Err:
          SideNote.append("-Blue level :Wrong value Must be less than "+str((2**int(IHDR_Depht))-1))

   if Chunk == "PLTE":

      if "div" in Err:
          SideNote.append("-PLTE Total palettes number must be divisible by 3")
     
      if "Depht" in Err:
          SideNote.append("PLTE palettes numbers must not be > 2 power of image Depht")

          SideNote.append("Todo")

      if "badpltr" in Err:
          SideNote.append("PLTE Wrong Red palettes range must not be > 2 power of image Depht")
          
      if "badpltg" in Err:
          SideNote.append("PLTE Wrong Green palettes range must not be > 2 power of image Depht")

      if "badpltb" in Err:
          SideNote.append("PLTE Wrong Blue palettes range must not be > 2 power of image Depht")

   if Chunk =="iCCP":
      if "name" in Err:
         SideNote.append("-Length of iCCP Profile name is not valid")

      if "badchar" in Err:
         SideNote.append("-Wrong Character in iCCP Profile name")

      if "method" in Err:
         SideNote.append("-Wrong Compression Method value")

      if "lenght" in Err:
         SideNote.append("-iCCP Profile length is not valid")


   if Chunk =="sPLT":

      if "badchar" in Err:
         SideNote.append("-Wrong Character in sPLT name")
 
      if "depht" in Err:
         SideNote.append("-Sample depth have to be either 8 or 16")

      if "name" in Err:
         SideNote.append("-sPLT name is too long")

      if "div8r" in Err:
         SideNote.append("-Red sPLT length is not divisible by 6")

      if "div16r" in Err:
         SideNote.append("-Red sPLT length is not divisible by 10")

      if "div8g" in Err:
         SideNote.append("-Green sPLT length is not divisible by 6")

      if "div16g" in Err:
         SideNote.append("-Green sPLT length is not divisible by 10")

      if "div8b" in Err:
         SideNote.append("-Blue sPLT length is not divisible by 6")

      if "div16b" in Err:
         SideNote.append("-Blue sPLT length is not divisible by 10")

      if "div8a" in Err:
         SideNote.append("-Alpha sPLT length is not divisible by 6")

      if "div16a" in Err:
         SideNote.append("-Alpha sPLT length is not divisible by 10")

      if "div8f" in Err:
         SideNote.append("-Frequency sPLT length is not divisible by 6")

      if "div16f" in Err:
         SideNote.append("-Frequency sPLT length is not divisible by 10")


   if Chunk == "hIST":

      if "missing" in Err:
         SideNote.append("-sPLT or PLTE have are missing and must be place before hIST")
      if "pnbr" in Err:
         SideNote.append("-Histogram frequencies entries must match PLTE entries number")
      if "snbr" in Err:
         SideNote.append("-Histogram frequencies entries must match sPLT entries number")

   if Chunk == "tRNS":

      if "missing" in Err:
         SideNote.append("-sPLT or PLTE have are missing and must be place before tRNS")
      if "pnbr" in Err:
         SideNote.append("-tRNS Alpha palettes indexes entries must match PLTE entries number")
      if "snbr" in Err:
         SideNote.append("-tRNS Alpha palettes indexes entries must match sPLT entries number")

   if Chunk == "sRGB":
      if "value" in Err:
         SideNote.append("-sRGB value must be between 0 to 3.")

   if Chunk == "cHRM":
      if "overide" in Err:
         SideNote.append("-cHRM is overide by sRGB chunk and iCCP")


   if Chunk == "sBIT":
     if "grayO" in Err:
        SideNote.append("-sBit gray value must be greater than 0")

     if "tredO" in Err:
        SideNote.append("-sBit True Red value must be greater than 0")


     if "tgreenO" in Err:
        SideNote.append("-sBit True Green value must be greater than 0")


     if "tblueO" in Err:
        SideNote.append("-sBit True Blue value must be greater than 0")

     if "grascalO" in Err:
        SideNote.append("-sBit Grayscale value must be greater than 0")

     if "grascalaO" in Err:
        SideNote.append("-sBit Grayscale Alpha value must be greater than 0")

     if "talpharO" in Err:
        SideNote.append("-sBit True Alpha Red value must be greater than 0")

     if "talphagO" in Err:
        SideNote.append("-sBit True Alpha Green value must be greater than 0")

     if "talphabO" in Err:
        SideNote.append("-sBit True Alpha Blue value must be greater than 0")

     if "talphaO" in Err:
        SideNote.append("-sBit True Alpha value must be greater than 0")

     if "red8depht" in Err:
        SideNote.append("-sBit True red value must not be greater than 8")

     if "green8depht" in Err:
        SideNote.append("-sBit True green value must not be greater than 8")

     if "blue8depht" in Err:
        SideNote.append("-sBit True blue value must not be greater than 8")

     if "reddepht" in Err:
        SideNote.append("-sBit True red value must not be greater than ",IDHR_Color)

     if "greendepht" in Err:
        SideNote.append("-sBit True green value must not be greater than ",IDHR_Color)

     if "bluedepht" in Err:
        SideNote.append("-sBit True blue value must not be greater than ",IDHR_Color)

     if "grascaldepth" in Err:
        SideNote.append("-sBit Grayscale value must not be greater than ",IDHR_Color)

     if "grascaladepth" in Err:
        SideNote.append("-sBit Grayscale Alpha value must not be greater than ",IDHR_Color)

     if "talphardepth" in Err:
        SideNote.append("-sBit True Alpha value must not be greater than ",IDHR_Color)

   if Chunk == "oFFs":

     if "xout" in Err:
        SideNode.append("-oFFs position Y must be between -2,147,483,647 to +2,147,483,647")
     if "yout" in Err:
        SideNode.append("-oFFs position Y must be between -2,147,483,647 to +2,147,483,647")
     if "uout" in Err:
        SideNode.append("-oFFs unit value must be between 0 or 1")



   if Chunk == "tIME":

      if "Year" in Err:
          SideNote.append("-tIME Year is > than the current year")
      if "Month" in Err:
          SideNote.append("-tIME Month value is not valid")
      if "Day" in Err:
          SideNote.append("-tIME Day value is not valid")
      if "Hour" in Err:
          SideNote.append("-tIME Hour value is not valid")
      if "Minute" in Err:
          SideNote.append("-tIME Minute value is not valid")
      if "Second" in Err:
          SideNote.append("-tIME Second value is not valid")

   if Chunk == "Critical":
       for chnk in Err:
          SideNote.append("-Critical Chunk %s is missing"%chnk)

#   TheEnd()

def NullFind(data,search4=None):
    null_pos = ''
    if search4 == None:
         search4 = "00"
    for i in range(0,len(data),len(search4)):
         if data[i:i+len(search4)] == search4:
              null_pos = i
              break
    return(null_pos)

def GetInfo(Chunk,data):
    global SideNote
    global IHDR_Height
    global IHDR_Width
    global IHDR_Depht
    global IHDR_Color
    global IHDR_Method
    global IHDR_Filter
    global IHDR_Interlace
    global bKGD_Gray
    global bKGD_Red
    global bKGD_Green
    global bKGD_Blue
    global bKGD_Index
    global PLTE_R
    global PLTE_G
    global PLTE_B
    global sPLT_Name
    global sPLT_Depht
    global sPLT_Red
    global sPLT_Green
    global sPLT_Blue
    global sPLT_Alpha
    global sPLT_Freq
    global cHRM_WhiteX
    global cHRM_WhiteY
    global cHRM_Redx
    global cHRM_Redy
    global cHRM_Greenx
    global cHRM_Greeny
    global cHRM_Bluex
    global cHRM_Bluey
    global gAMA
    global hIST
    global gIFID
    global gIFCD
    global gIFDT
    global gIFDT
    global gIFgM
    global gIFgU
    global gIFgT
    global iCCP_Name
    global iCCP_Method
    global iCCP_Profile
    global pHYs_Y
    global pHYs_X
    global pHYs_Unit
    global pCAL_Param
    global pCAL_Key
    global pCAL_Zero
    global pCAL_Max
    global pCAL_Eq
    global pCAL_PNBR
    global sBIT_Gray
    global sBIT_TrueR
    global sBIT_TrueG
    global sBIT_TrueB
    global sBIT_GrayScale
    global sBIT_GrayAlpha
    global sBIT_TrueAlphaR
    global sBIT_TrueAlphaG
    global sBIT_TrueAlphaB
    global sBIT_TrueAlpha
    global iTXt_String_List
    global iTXt_Key_List
    global iTXt_String
    global iTXt_Key
    global sTER
    global tEXt_Key_List
    global tEXt_Str_List
    global tEXt_Key
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
    global zTXt_Key_List
    global zTXt_Str_List
    global zTXt_Key
    global zTXt_sep
    global zTXt_Meth
    global zTXt_Text


    iCCP_Name = ""
    iTXt_String=""
    iTXt_Key=""
    zTXt_String=""
    zTXt_Key=""
    tEXt_Text=""
    tEXt_Key=""
    sPLT_Name =""

    ToFix = []

    Candy("Title","Getting infos about:",Candy("Color","white",str(Chunk)))

    if Chunk == "PNG":
          print("Well ..That's a start ..At least it looks like a png.")
    if Chunk == "IHDR":
        try:
             IHDR_Height=str(int(data[:8],16))
             IHDR_Width=str(int(data[8:16],16))
             IHDR_Depht=str(int(data[16:18],16))
             IHDR_Color=str(int(data[18:20],16))
             IHDR_Method=str(int(data[20:22],16))
             IHDR_Filter=str(int(data[22:24],16))
             IHDR_Interlace=str(int(data[24:26],16))

             print("-Width    :",Candy("Color","yellow",IHDR_Height))
             print("-Height   :",Candy("Color","yellow",IHDR_Width))
             print("-Depht    :",Candy("Color","yellow",IHDR_Depht))
             print("-Color    :",Candy("Color","yellow",IHDR_Color))
             print("-Method   :",Candy("Color","yellow",IHDR_Method))
             print("-Filter   :",Candy("Color","yellow",IHDR_Filter))
             print("-Interlace:",Candy("Color","yellow",IHDR_Interlace))

             if len(data) != 26:
                   print("-Bytes number :"+Candy("Color","red"," Wrong size")+"IHDR size have to always be 13 bytes."+Candy("Emoj","bad"))
                   ToFix.append("Bytes")

             if len(IHDR_Height) >0:
                    if int(IHDR_Height) > 2147483647:
                          print("-Height :"+Candy("Color","red"," Wrong size (Too high)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("Height")
             else:
                          print("-Height :"+Candy("Color","red"," Wrong size (Too low)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("Height")

             if len(IHDR_Width) >0:
                    if int(IHDR_Width) > 2147483647:
                          print("-Width :"+Candy("Color","red"," Wrong size (Too high)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("Width")
             else:
                          print("-Width :"+Candy("Color","red"," Wrong size (Too low)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("Width")

             if len(IHDR_Depht) > 0:
                     if IHDR_Depht not in ["1","2","4","8","16"]:
                         print("-Bit depht :"+Candy("Color","red"," Wrong bit value")+" Must be 1,2,4,8 or 16 "+Candy("Emoj","bad"))
                         ToFix.append("Depht")

             if len(IHDR_Color) > 0:
                 if IHDR_Color not in ["0","2","3","4","6"]:
                         print("-Color Chunk :"+Candy("Color","red"," Wrong bit value")+" Must be 0,2,3,4 or 6 "+Candy("Emoj","bad"))
                         ToFix.append("Color")
                 if IHDR_Color == "2" or IHDR_Color == "4" or IHDR_Color == "6":
                     if IHDR_Depht not in ["8","16"]:
                         print("-Color Chunk :"+Candy("Color","red"," Wrong bit depht ")+"for color Chunk "+IHDR_Color+" must be 8 or 16 "+Candy("Emoj","bad"))
                         ToFix.append("Color")
                 if IHDR_Color == "3":
                     if IHDR_Depht not in ["1","2","4","8"]:
                         print("-Color Chunk :"+Candy("Color","red"," Wrong bit depht ")+"for color Chunk 3 must be 1,2,4 or 8"+Candy("Emoj","bad"))
                         ToFix.append("Color")

             if len(IHDR_Filter) > 0 and IHDR_Filter != "0":
                   print("-Filter Method :"+Candy("Color","red"," Wrong value")+" must be 0."+Candy("Emoj","bad"))
                   ToFix.append("Filter")

             if len(IHDR_Method) > 0 and IHDR_Method != "0":
                   print("-Compression Algorithms :"+Candy("Color","red"," Wrong value")+" must be 0."+Candy("Emoj","bad"))
                   ToFix.append("Compression")

             if len(IHDR_Interlace) > 0 and (IHDR_Interlace != "0" and IHDR_Interlace != "1"):
                   print("-Interlace Method :"+Candy("Color","red"," Wrong value")+" must be 0 (no interlace) or 1 (Adam7 interlace)."+Candy("Emoj","bad"))
                   ToFix.append("Interlace")

             if len(ToFix) > 0:
                  SaveErrors(Chunk,ToFix)
             else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

        except Exception as e:
           SideNote.append("Error IHDR:"+str(e))
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
        return 


    if Chunk == "pHYs":
        try:
             pHYs_Y=str(int(data[:8],16))
             pHYs_X=str(int(data[8:16],16))
             pHYs_Unit=str(int(data[16:18],16))
             print("-Pixels per unit, X axis: ",Candy("Color","yellow",pHYs_X))
             print("-Pixels per unit, Y axis: ",Candy("Color","yellow",pHYs_Y))
             print("-Unit specifier         :",Candy("Color","yellow",pHYs_Unit))

             if len(pHYs_Y) >0:
                    if int(pHYs_Y) > 2147483647:
                          print("-Pixels per unit, Y axis:"+Candy("Color","red"," Wrong size (Too high)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))

                          ToFix.append("pHYs_Y")
             else:
                          print("-Pixels per unit, Y axis :"+Candy("Color","red"," Wrong size (Too low)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("pHYs_Y")

             if len(pHYs_X) >0:
                    if int(pHYs_X) > 2147483647:
                          print("Pixels per unit, X axis"+Candy("Color","red"," Wrong size (Too high)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("pHYs_X")
             else:
                          print("-Pixels per unit, X axis"+Candy("Color","red"," Wrong size (Too low)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("pHYs_X")

             if len(pHYs_Unit) >0:
                    if pHYs_Unit != "0" and pHYs_Unit != "1":
                          print("-Unit specifier :"+Candy("Color","red"," Wrong value")+" Must be between 0 (unknown) or 1(meter)."+Candy("Emoj","bad"))

                          ToFix.append("pHYs_Unit")
             if len(ToFix)>0:
                SaveErrors(Chunk,ToFix)
             else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

        except Exception as e:
           SideNote.append("Error pHys:"+str(e))
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
        return

    if Chunk == "bKGD":
        if IHDR_Color == "0" or IHDR_Color == "4":
             try:
                  bKGD_Gray=str(int(data[:4],16))
                  print("-Gray    :",Candy("Color","yellow",bKGD_Gray))
             except Exception as e:
                 print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

             if int(bKGD_Gray) > (2**int(IHDR_Depht))-1:
                 print("-Gray level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                 ToFix.append("Bkgd_Gray")
        if IHDR_Color == "2" or IHDR_Color == "6":
           try:
                  bKGD_Red=str(int(data[:4],16))
                  bKGD_Green=str(int(data[4:8],16))
                  bKGD_Blue=str(int(data[8:12],16))

                  print("-Red    :",Candy("Color","red",bKGD_Red))
                  print("-Green  :",Candy("Color","green",bKGD_Green))
                  print("-Blue   :",Candy("Color","blue",bKGD_Blue))

                  if int(bKGD_Red) > (2**int(IHDR_Depht))-1:
                      print("-Red level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                      ToFix.append("Bkgd_Red")
                  if int(bKGD_Green) > (2**int(IHDR_Depht))-1:
                      print("-Green level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                      ToFix.append("Bkgd_Green")
                  if int(bKGD_Blue) > (2**int(IHDR_Depht))-1:
                      print("-Blue level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                      ToFix.append("Bkgd_Blue")

           except Exception as e:
              print(Candy("Color","red","Error bKGD:"),Candy("Color","yellow",e))

        if IHDR_Color == "3":
            try:
                  bKGD_Index=str(int(data[:2],16))
                  print("-Palette    :",Candy("Color","yellow",bKGD_Index))
            except Exception as e:
              print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

        if len(ToFix) >0:
           SaveErrors(Chunk,ToFix)
        else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
        return

    if Chunk == "PLTE":
          PLTNbr = len(data)

          if not str(int(PLTNbr)/3).endswith(".0"):
             print("-%s PLTE length: %s/3= %s (not divisible by 3). %s"%(Candy("Color","red","Wrong"),PLTNbr,Candy("Color","red",PLTNbr),Candy("Emoj","bad")))
             ToFix.append("div")

          for i in range(0,PLTNbr,6):
             pltr = data[i:i+2]
             pltg = data[i+2:i+4]
             pltb = data[i+4:i+6]

             PLTE_R.append(str(pltr))
             PLTE_G.append(str(pltg))
             PLTE_B.append(str(pltb))

          print("-%s Red palettes are stored."%Candy("Color","yellow",len(PLTE_R)))
          print("-%s Green palettes are stored."%Candy("Color","yellow",len(PLTE_G)))
          print("-%s Blue palettes are stored."%Candy("Color","yellow",len(PLTE_B)))
          print("-%s RGB palettes are stored."%Candy("Color","yellow",len(PLTE_R)+len(PLTE_G)+len(PLTE_B)))

          if len(PLTE_R) > 2 ** int(IHDR_Depht):
               print("-PLTE %s Red palettes not in bitdepht range: (must not be > 2 power of image Depht:%s).%s"%(Candy("Color","red",str(len(pltb)-1)+" Wrong"),Candy("Color","yellow",2 ** int(IHDR_Depht)),Candy("Emoj","bad")))
               ToFix.append(badpltr)

          if len(PLTE_G) > 2 ** int(IHDR_Depht):
               print("-PLTE %s  Green palettes not in bitdepht range: (must not be > 2 power of image Depht:%s).%s"%(Candy("Color","red",str(len(pltb))+" Wrong"),Candy("Color","yellow",2 ** int(IHDR_Depht)),Candy("Emoj","bad")))
               ToFix.append(badpltg)

          if len(PLTE_B) > 2 ** int(IHDR_Depht):
               print("-PLTE %s Blue palettes not in bitdepht range: (must not be > 2 power of image Depht:%s). %s"%(Candy("Color","red",str(len(pltb))+" Wrong"),Candy("Color","yellow",2 ** int(IHDR_Depht)),Candy("Emoj","bad")))
               ToFix.append(badpltb)


          if len(ToFix) >0:
             SaveErrors(Chunk,ToFix)
          else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
          return

    if Chunk == "sPLT":

        sPLT_Ln = len(data)
        null_pos=NullFind(data)
        sPLT_Name = data[:null_pos]
        badchar=["badchar"]

        for i in sPLT_Name:
          nint = int(data[i:i+2],16)
          nchar = chr(nint)

          if (nint not in range(32,127)) and (nint not in range(161,256)):
                  print("-Character %s at index %s in sPLT_Name\n-Replaced by [€] %s"%(Candy("Color","red","not allowed ["+nchar+"]"),Candy("Color","red",i),Candy("Emoj","bad")))
                  sPLT_Name += "€"
                  badchar.append(i)
          else:
               sPLT_Name += nchar

        if len(badchar) > 1:
             ToFix.append(badchar)

        sPLT_Depht = int(data[null_pos+2:null_pos+4],16)
        if sPLT_Depht != 8 or sPLT_Depht != 16:
            print("-Sample depth is %s it must be 8 or 16 :%s %s"%(Candy("Color","red","not correct"),Candy("Color","red",sPLT_Depht),Candy("Emoj","bad")))
            ToFix.append("depth")
        pos = 0
        for i in range(sPLT_Ln+1):
             if sPLT_Depht == 8:
                 sPLT_Red.append(data[:pos])
                 sPLT_Green.append(data[pos:pos+2])
                 sPLT_Blue.append(data[pos+2:pos+4])
                 sPLT_Alpha.append(data[pos+4:pos+6])
                 sPLT_Freq.append(data[pos+6:pos+8])
                 pos += 8

             if sPLT_Depht == 16:
                 sPLT_Red.append(data[:pos])
                 sPLT_Green.append(data[pos:pos+4])
                 sPLT_Blue.append(data[pos+4:pos+8])
                 sPLT_Alpha.append(data[pos+8:pos+16])
                 sPLT_Freq.append(data[pos+16:pos+24])
                 pos += 24
             else:
                  break


        if sPLT_Name >79:
               print("-Length of sPLT name is %s :%s %s"%(Candy("Color","red","not Valid (Too long >79)"),Candy("Color","red",i),Candy("Emoj","bad")))
               ToFix.append("name")


        print("-%s Suggested Red palettes are stored."%Candy("Color","yellow",len(sPLT_Red)))

        if sPLT_Depht == 8:
          if not str(int(sPLT_Red)/6).endswith(".0"):
             print("-%s Red sPLT length: %s(not divisible by 6).%s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Red)),Candy("Emoj","bad")))
             ToFix.append("div8r")

        elif sPLT_Depht == 16:
          if not str(int(sPLT_Red)/10).endswith(".0"):
             print("-%s Red sPLT length: %s (not divisible by 10).%s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Red)),Candy("Emoj","bad")))
             ToFix.append("div16r")
        
        print("-%s Suggested Green palettes are stored."%Candy("Color","yellow",len(sPLT_Green)))


        if sPLT_Depht == 8:
          if not str(int(sPLT_Green)/6).endswith(".0"):
             print("-%s Green sPLT length: %s (not divisible by 3). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Green)),Candy("Emoj","bad")))
             ToFix.append("div8g")

        elif sPLT_Depht == 16:
          if not str(int(sPLT_Green)/10).endswith(".0"):
             print("-%s Green sPLT length: %s/10= %s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Green)),Candy("Emoj","bad")))
             ToFix.append("div16g")

        print("-%s Suggested Blue palettes are stored."%Candy("Color","yellow",len(sPLT_Blue)))


        if sPLT_Depht == 8:
          if not str(int(sPLT_Blue)/6).endswith(".0"):
             print("-%s Blue sPLT length: %s (not divisible by 6). %s "%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Blue)),Candy("Emoj","bad")))
             ToFix.append("div8b")

        elif sPLT_Depht == 16:
          if not str(int(sPLT_Blue)/10).endswith(".0"):
             print("-%s Blue sPLT length:%s (not divisible by 10). %s "%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Blue)),Candy("Emoj","bad")))
             ToFix.append("div16b")




        print("-%s Suggested Alpha palettes are stored."%Candy("Color","yellow",len(sPLT_Alpha)))

        if sPLT_Depht == 8:
          if not str(int(sPLT_Alpha)/6).endswith(".0"):
             print("-%s Aplha sPLT length: %s (not divisible by 6). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Alpha)),Candy("Emoj","bad")))
             ToFix.append("div8a")

        elif sPLT_Depht == 16:
          if not str(int(sPLT_Alpha)/10).endswith(".0"):
             print("-%s Aplha sPLT length:%s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Alpha)),Candy("Emoj","bad")))
             ToFix.append("div16a")



        print("-%s Suggested Frequency values are stored."%Candy("Color","yellow",len(sPLT_Freq)))

        if sPLT_Depht == 8:
          if not str(int(sPLT_Freq)/6).endswith(".0"):
             print("-%s Frequency sPLT length: %s (not divisible by 6). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Freq)),Candy("Emoj","bad")))
             ToFix.append("div8f")

        elif sPLT_Depht == 16:
          if not str(int(sPLT_Freq)/10).endswith(".0"):
             print("-%s Frequency sPLT length:%s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Freq)),Candy("Emoj","bad")))
             ToFix.append("div16f")

        if len(ToFix) >0:
              if len(badchar) >1:
                 SaveErrors(Chunk,ToFix,data)
              else:
                 SaveErrors(Chunk,ToFix)
        else:
               print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
        return

    if Chunk == "hIST":
        if b"PLTE" not in Chunks_History and b"sPLT" not in Chunks_History:
              print("-%s Chunk or %s is missing.(hIST must be used after one of them)"%(Candy("Color","red","PLTE"),Candy("Color","red","sPLT")))
              ToFix.append(Chunk,"missing",data)
        try:
            pos = 0
            for plt in range(0,len(data),2):
                 hIST.append(data[plt:plt+2])
                 pos = plt
            print("-%s Histogram frequencies are stored."%Candy("Color","yellow",len(hIST)))

            if b"PLTE" in Chunks_History:
                if len(hIST) != len(PLTE_R)+len(PLTE_G)+len(PLTE_B):
                       print("-Histogram frequencies entries %s PLTE entries number %"%(Candy("Color","red","must match"),Candy("Emoj","bad")))
                       ToFix.append("pnbr")


            if b"sPLT" in Chunks_History:
                if len(hIST) != len(sPLT_Red)+len(sPLT_Green)+len(sPLT_Blue)+len(sPLT_Aplha):
                       print("-Histogram frequencies entries %s sPLT entries number %s"%(Candy("Color","red","must match"),Candy("Emoj","bad")))
                       ToFix.append("snbr")

            if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix)
            else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

        except Exception as e:
            print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

        return

    if Chunk == "tIME":
             tIME_Yr=str(int(data[:4],16))
             tIME_Mth=str(int(data[4:6],16))
             tIME_Day=str(int(data[6:8],16))
             tIME_Hr=str(int(data[8:10],16))
             tIME_Min=str(int(data[10:12],16))
             tIME_Sec=str(int(data[12:14],16))

             print("-Last Modified: %s/%s/%s %s:%s:%s"%(Candy("Color","white",tIME_Day),Candy("Color","white",tIME_Mth),Candy("Color","white",tIME_Yr),Candy("Color","white",tIME_Hr),Candy("Color","white",tIME_Min),Candy("Color","white",tIME_Sec)))

             if int(tIME_Yr) > datetime.now().year:
                 print("-Year is > than current year    : %s %s"%(Candy("Color","red",tIME_Yr),Candy("Emoj","bad")))
                 ToFix.append("Year")
             if int(tIME_Mth) not in range(1,13):
                 print("-Month value is not valid   : %s %s"%(Candy("Color","red",tIME_Mth),Candy("Emoj","bad")))
                 ToFix.append("Month")
             if int(tIME_Day) not in range(1,32):
                 print("-Day value is not valid      : %s %s"%(Candy("Color","red",tIME_Day),Candy("Emoj","bad")))
                 ToFix.append("Day")
             if int(tIME_Hr) not in range(0,24):
                 print("-Hour value is not valid     : %s %s"%(Candy("Color","red",tIME_Hr),Candy("Emoj","bad")))
                 ToFix.append("Hour")
             if int(tIME_Min) not in range(0,60):
                  print("-Minute value is not valid  : %s %s"%(Candy("Color","red",tIME_Min),Candy("Emoj","bad")))
                  ToFix.append("Minute")
             if int(tIME_Sec) not in range(0,61):
                  print("-Second  value is not valid : %s %s"%(Candy("Color","red",tIME_Sec),Candy("Emoj","bad")))
                  ToFix.append("Second")

             if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix)
             else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

             return

    if Chunk == "tRNS":
         TRNSNBR = len(data)
         if IHDR_Color == "0":
                tRNS_Gray = str(int(data[:4],16))
                print("-Gray    :",Candy("Color","yellow",tRNS_Gray))
         if IHDR_Color == "2":
                tRNS_TrueR = str(int(data[:4],16))
                tRNS_TrueG =str(int(data[4:8],16))
                tRNS_TrueB =str(int(data[8:16],16))
                print("-Red    :",Candy("Color","red",tRNS_TrueR))
                print("-Green  :",Candy("Color","green",tRNS_TrueG))
                print("-Blue   :",Candy("Color","blue",tRNS_TrueB))
         if IHDR_Color == "3":
             if b"PLTE" not in Chunks_History and b"sPLT" not in Chunks_History:
              print("-%s Chunk or %s is missing.(tRNS must be used after one of them) %s"%(Candy("Color","red","PLTE"),Candy("Color","red","sPLT"),Candy("Emoj","bad")))
              ToFix.append(Chunk,"missing",data)

             for i in range(0,TRNSNBR,2):
                 tRNS_Index.append(str(int(data[i:i+2],16)))
             print("-%s Alpha indexes are stored."%Candy("Color","yellow",len(tRNS_Index)))


             if b"PLTE" in Chunks_History:
                if len(tRNS_Index) > len(PLTE_R)+len(PLTE_G)+len(PLTE_B):
                       print("-tRNS Alpha indexes palettes entries %s PLTE entries number %s"%(Candy("Color","red","must not be superior to"),Candy("Emoj","bad")))
                       ToFix.append("pnbr")

             if b"sPLT" in Chunks_History:
                if len(hIST) > len(sPLT_Red)+len(sPLT_Green)+len(sPLT_Blue)+len(sPLT_Aplha):
                       print("-tRNS Alpha indexes palettes entries %s sPLT entries number %s"%(Candy("Color","red","must not be superior to"),Candy("Emoj","bad")))
                       ToFix.append("snbr")

         if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix)
         else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

         return

    if Chunk == "sRGB":
         sRGB =str(int(data[:2],16))
         if sRGB == "0":
           print("-Rendering Perceptual :",Candy("Color","yellow",sRGB))
         elif sRGB == "1":
           print("-Rendering Relative colorimetric :",Candy("Color","yellow",sRGB))
         elif sRGB == "2":
           print("-Rendering Saturation :",Candy("Color","yellow",sRGB))
         elif sRGB == "3":
           print("-Rendering Absolute colorimetric :",Candy("Color","yellow",sRGB))
         else:
           print("-%s sRGB value must be between 0 to 3. %s"%(Candy("Color","red","Wrong"),Candy("Emoj","bad")))
           ToFix.append("value")

         if "cHRM".encode() in Chunks_History:
                 print("-%s already present cHRM will be %s if reconized by decoders %s"%(Candy("Color","red","cHRM"),Candy("Color","red","overide"),Candy("Emoj","bad")))
                 ToFix.append("overide")


         if len(ToFix) >0:
                SaveErrors(Chunk,ToFix)
         else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
         return

    if Chunk == "cHRM":

             cHRM_WhiteX=str(int(data[:8],16))
             cHRM_WhiteY=str(int(data[8:16],16))
             cHRM_Redx=str(int(data[16:24],16))
             cHRM_Redy=str(int(data[24:32],16))
             cHRM_Greenx=str(int(data[32:40],16))
             cHRM_Greeny=str(int(data[40:48],16))
             cHRM_Bluex=str(int(data[48:56],16))
             cHRM_Bluey=str(int(data[56:64],16))
             print("-WhiteX   :",Candy("Color","white",cHRM_WhiteX))
             print("-WhiteY   :",Candy("Color","white",cHRM_WhiteY))
             print("-RedX     :",Candy("Color","red",cHRM_Redx))
             print("-RedY     :",Candy("Color","red",cHRM_Redy))
             print("-GreenX   :",Candy("Color","green",cHRM_Greenx))
             print("-GreenY   :",Candy("Color","green",cHRM_Greeny))
             print("-BlueX    :",Candy("Color","blue",cHRM_Bluex))
             print("-BlueY    :",Candy("Color","blue",cHRM_Bluey))

             if "sRGB".encode() in Chunks_History or "iCCP".encode() in Chunks_History:
                 print("-%s or %s already present cHRM will be overide if reconized by decoders %s"%(Candy("Color","red","sRGB"),Candy("Color","red","iCCP"),Candy("Emoj","bad")))
                 ToFix.append("overide")

             if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix)
             else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

             return

    if Chunk == "gAMA":
             gAMA=str(int(data[:8],16))
             print("-Gama   :",Candy("Color","white",gAMA))
             return

    if Chunk == "iCCP":
        null="00"
        null_pos=0
        badchar=["badchar"]
        for i in range(0,len(data),2):
          nint = int(data[i:i+2],16)
          nchar = chr(nint)

          if data[i:i+2] == "00":
                 null_pos = i
                 if i >79:
                       print("-Length of iCCP Profile name is %s :%s"%(Candy("Color","red","not Valid"),Candy("Color","red",i)))
                       ToFix.append("name")
                 break
          if (int(nint) not in range(32,127)) and (int(nint) not in range(161,255)):
                  print("-Character %s at index %s in iCCP_Name\n-Replaced by [€]"%(Candy("Color","red","not allowed ["+nchar+"]"),Candy("Color","red",i)))
                  badchar.append(i)
                  iCCP_Name += "€"
          else:
               iCCP_Name += nchar
        if len(badchar) >1:
            ToFix.append(badchar)

        iCCP_Method = int(data[null_pos+2:null_pos+4],16)

        if iCCP_Method > 0:
             print("-Compression method is supposed to be %s but is %s instead ."%(Candy("Color","green","0"),Candy("Color","red",method)))
             ToFix.append("method")

        iCCP_Profile = data[null_pos+4:]

        if int(int(Orig_CL,16))-(int(null_pos/2)+2) != int(len(iCCP_Profile)/2):
            print("-iCCP Profile length is %s"%Candy("Color","red","not Valid"))
            ToFix.append("lenght")

        if "cHRM".encode() in Chunks_History:
                 print("-%s already present cHRM will be %s if reconized by decoders %s"%(Candy("Color","red","cHRM"),Candy("Color","red","overide"),Candy("Emoj","bad")))
                 ToFix.append("overide")

        print("-iCCP Profile Name :",Candy("Color","yellow",iCCP_Name))
        print("-iCCP Profile Method :",Candy("Color","yellow",iCCP_Method))


        if len(ToFix) >0:
             SaveErrors(Chunk,ToFix)
        else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
        return

    if Chunk == "sBIT":
         if IHDR_Color == "0":
                sBIT_Gray = str(int(data[:2],16))
                print("-Significant greyscale bits    :",Candy("Color","yellow",sBIT_Gray))
                if sBIT_Gray == "0":
                   print("-%s sBit value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("grayO")


         if IHDR_Color == "2" or  IHDR_Color == "3" :
                sBIT_TrueR = str(int(data[:2],16))
                sBIT_TrueG = str(int(data[2:4],16))
                sBIT_TrueB = str(int(data[4:6],16))
                print("-significant bits Red    :",Candy("Color","red",sBIT_TrueR))
                print("-significant bits Green  :",Candy("Color","green",sBIT_TrueG))
                print("-significant bits Blue   :",Candy("Color","blue",sBIT_TrueB))
                if sBIT_TrueR == "0":
                   print("-%s sBit red value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("tredO")

                if sBIT_TrueG == "0":
                   print("-%s sBit green value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("tgreenO")

                if sBIT_TrueB == "0":
                   print("-%s sBit blue value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red",
"0"),Candy("Emoj","bad")))
                   ToFix.append("tblueO")

                if IHDR_Color == "3":
                    if int(sBIT_TrueR) > 8:
                        print("-%s sBit red value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red","8"),Candy("Emoj","bad")))
                        ToFix.append("red8depht")
                    if int(sBIT_TrueG) > 8: 
                        print("-%s sBit green value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red","8"),Candy("Emoj","bad")))
                        ToFix.append("green8depht")
                    if int(sBIT_TrueB) > 8: 
                        print("-%s sBit blue value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red","8"),Candy("Emoj","bad")))
                        ToFix.append("blue8depht")
                else:
                    if int(sBIT_TrueR) > int(IHDR_Depht): 
                        print("-%s sBit red value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                        ToFix.append("reddepht")

                    if int(sBIT_TrueG) > int(IHDR_Depht): 
                        print("-%s sBit green value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                        ToFix.append("greendepht")

                    if int(sBIT_TrueB) > int(IHDR_Depht): 
                        print("-%s sBit blue value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                        ToFix.append("bluedepht")


         if IHDR_Color == "4":
            sBIT_GrayScale = str(int(data[:pos],16))
            sBIT_GrayAlpha = str(int(data[:pos],16))
            print("-Gray scale significant bit:",Candy("Color","white",sBIT_GrayScale))
            print("-Gray alpha significant bit:",Candy("Color","white",sBIT_GrayAlpha))
            if sBIT_GrayScale == "0":
                   print("-%s sBit Grayscale value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("grascalO")

            if sBIT_GrayAlpha == "0":
                   print("-%s sBit Grayscale alpha value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("grascalaO")

            if int(sBIT_GrayScale) > int(IHDR_Depht): 
                print("-%s sBit Grayscale value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                ToFix.append("grascaldepth")

            if int(sBIT_GrayScale) > int(IHDR_Depht): 
                print("-%s sBit Grayscale alpha value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                ToFix.append("grascaladepth")

         if IHDR_Color == "6":
                sBIT_TrueAlphaR = str(int(data[:2],16))
                sBIT_TrueAlphaG = str(int(data[2:4],16))
                sBIT_TrueAlphaB = str(int(data[4:6],16))
                sBIT_TrueAlpha = str(int(data[6:8],16))
                print("-significant bits Alpha Red    :",Candy("Color","red",sBIT_TrueAlphaR))
                print("-significant bits Alpha Green  :",Candy("Color","green",sBIT_TrueAlphaG))
                print("-significant bits Alpha Blue   :",Candy("Color","blue",sBIT_TrueAlphaB))
                print("-significant bits Alpha        :",Candy("Color","white",sBIT_TrueAlpha))

                if sBIT_TrueAlphaR == "0":
                   print("-%s sBit True alpha red value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("talpharO")

                if sBIT_TrueAlphaG == "0":
                   print("-%s sBit True alpha green value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("talphagO")

                if sBIT_TrueAlphaB == "0":
                   print("-%s sBit True alpha blue value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("talphabO")

                if sBIT_TrueAlpha == "0":
                   print("-%s sBit True alpha value (must be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","0"),Candy("Emoj","bad")))
                   ToFix.append("talphaO")

                if int(sBIT_TrueAlphaR) > int(IHDR_Depht): 
                  print("-%s sBit True alpha red value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                  ToFix.append("talphardepth")

                if int(sBIT_TrueAlphaG) > int(IHDR_Depht): 
                  print("-%s sBit True alpha green value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                  ToFix.append("talphagdepth")

                if int(sBIT_TrueAlphaB) > int(IHDR_Depht): 
                  print("-%s sBit True alpha blue value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                  ToFix.append("talphabdepth")

                if int(sBIT_TrueAlpha) > int(IHDR_Depht): 
                  print("-%s sBit True alpha value (must %s be greater than %s) %s"%(Candy("Color","red","Wrong"),Candy("Color","red","not"),Candy("Color","red",IHDR_Depht),Candy("Emoj","bad")))
                  ToFix.append("talphadepth")

         if len(ToFix) >0:
             SaveErrors(Chunk,ToFix)
         else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
         return


    if Chunk == "oFFs":
                oFFSX = str(int.from_bytes(bytes.fromhex(data[:8]),byteorder='big',signed=True))
                oFFSY = str(int.from_bytes(bytes.fromhex(data[8:16]),byteorder='big',signed=True))
                oFFSU = str(int(data[16:18],16))
                print("-Offset position X    :",Candy("Color","blue",oFFSX))
                print("-Offset position Y  :",Candy("Color","purple",oFFSY))
                print("-Offset Unit   :",Candy("Color","white",oFFSU))
                if int(oFFSX)  not in range(-2147483647,2147483648):
                   print("-%s Offset position X must be between -2,147,483,647 to +2,147,483,647 %s"%(Candy("Color","red","Wrong"),Candy("Emoj","bad")))
                   ToFix.append("xout")
                if int(oFFSY)  not in range(-2147483647,2147483648):
                   print("-%s Offset position Y must be between -2,147,483,647 to +2,147,483,647 %s"%(Candy("Color","red","Wrong"),Candy("Emoj","bad")))
                   ToFix.append("yout")
                if oFFSU != "0" and oFFSU != "1":
                   print("-%s Offset unit must be between 0 or 1 %s"%(Candy("Color","red","Wrong"),Candy("Emoj","bad")))
                   ToFix.append("uout")
                if len(ToFix) >0:
                    SaveErrors(Chunk,ToFix)
                else:
                    print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

                return

    if Chunk == "pCAL": 
      try:
           pCAL_Key = data.split("00")[0]
           for i in range(0,len(pCAL_Key),2):
             if int(pCAL_Key[i:i+2],16) not in range(32,127) and int(pCAL_Key[i:i+2],16) not in range(161,256):
               if pCAL_Key[i:i+2] != "00" and pCAL_Key[i:i+2] != "0a": 
                  print("-Character %s at index %s in pCAL Keyword (must be between 32-126 and 161-255 but is %s)"%(Candy("Color","red","not allowed ["+pCAL_Key[i:i+2]+"]"),Candy("Color","red",i),Candy("Color","red",int(pCAL_Key[i:i+2],16))))

           if len(pCAL_Key) >=79:
                      print("-pCAL Keyword length is %s :%s"%(Candy("Color","red","not Valid"),Candy("Color","red",i)))
           Keypos =len(pCAL_Key) + 2
           pCAL_Zero = str(int(data[Keypos:Keypos+8],16))
           pCAL_Max = str(int(data[Keypos+8:Keypos+16],16))
           pCAL_Eq = str(int(data[Keypos+16:Keypos+18],16))
           pCAL_PNBR = str(int(data[Keypos+18:Keypos+20],16))

           if pCAL_PNBR == "0":
                 pCAL_Unit = ""
           else:
              pCAL_Unit = bytes.fromhex(data[20:].split("00")[0])

           newlength = Keypos + 20

           for i in range(0,int(pCAL_PNBR)):
              param = ""
              try:
                 for j in range(0,len(data[newlength:]),2):
                       hx = data[newlength+j:newlength+j+2]
                       if hx != "00":
                          param += str(hx)
                       else:
                         break
                 pCAL_Param.append(param)
                 newlength += len(param)+2
              except Exception as e:
                 print(Candy("Color","red","Error pCAL:"),Candy("Color","yellow",e))
                 sys.exit()

           print("-Calibration name    :",Candy("Color","yellow",bytes.fromhex(pCAL_Key).decode(errors="replace")))
           print("-Original zero       :",Candy("Color","yellow",pCAL_Zero))
           print("-Original max        :",Candy("Color","yellow",pCAL_Max))
           print("-Equation type       :",Candy("Color","yellow",pCAL_Eq))
           print("-Number of parameters:",Candy("Color","yellow",pCAL_PNBR))

      except Exception as e:
                 print(Candy("Color","red","Error pCAL2:"),Candy("Color","yellow",e))
      return

    if Chunk == "gIFg":

                gIFgM = str(int(data[:2],16))
                gIFgU = str(int(data[2:4],16))
                gIFgT = str(int(data[4:6],16))

                print("-Disposal Method    :",Candy("Color","yellow",gIFgM))
                print("-User Input Flag    :",Candy("Color","yellow",gIFgT))
                print("-Delay Time    :",Candy("Color","yellow",gIFgT))
                return
    if Chunk == "gIFx":
                gIFID = str(int(data[:16],16))
                gIFCD = str(int(data[16:22],16))
                gIFDT = str(int(data[22:],16))

                print("-Application Identifier    :",Candy("Color","yellow",gIFID))
                print("-Authentication Code    :",Candy("Color","yellow",gIFCD))
                print("-Application Data    :",Candy("Color","yellow",gIFDT))
                return
    if Chunk == "sTER":

                sTER = str(int(data[:2],16))

                print("-Subimage mode    :",Candy("Color","yellow",sTER))
                return

    if Chunk == "tEXt": 

        try:
           null_pos = NullFind(data)
           tEXt_Key = data[:null_pos]
           tEXt_Text = data[null_pos+2:]

           for i in range(0,len(data),2):
             if int(data[i:i+2],16) not in range(32,127) and int(data[i:i+2],16) not in range(161,256):
               if data[i:i+2] != "00" and data[i:i+2] != "0a": 
                  print("-Character %s at index %s in tEXt Keyword (must be between 32-126 and 161-255 but is %s)"%(Candy("Color","red","not allowed ["+data[i:i+2]+"]"),Candy("Color","red",i),Candy("Color","red",int(data[i:i+2],16))))

           if len(tEXt_Key) >=79:
                      print("-tEXt Keyword length is %s :%s"%(Candy("Color","red","not Valid"),Candy("Color","red",i)))

           tEXt_Key_List.append(bytes.fromhex(tEXt_Key).decode(errors="replace"))
           tEXt_Str_List.append(bytes.fromhex(tEXt_Text).decode(errors="ignore"))
 
           print("-Keyword : ",Candy("Color","green",bytes.fromhex(tEXt_Key).decode(errors="replace")))
           print("-String  : ",Candy("Color","green",bytes.fromhex(tEXt_Text).decode(errors="replace")))

        except Exception as e:
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

           return

    if Chunk == "zTXt": 

        try:
           null_pos = NullFind(data)
           zTXt_Key = data[:null_pos]
           zTXt_Text = zlib.decompress(bytes.fromhex(data[null_pos+4:]))
           for i in range(0,len(zTXt_Key),2):
             if int(zTXt_Key[i:i+2],16) not in range(32,127) and int(zTXt_Key[i:i+2],16) not in range(161,256):
               if zTXt_Key[i:i+2] != "00" and zTXt_Key[i:i+2] != "0a": 
                  print("-Character %s at index %s in zTXt Keyword (must be between 32-126 and 161-255 but is %s)"%(Candy("Color","red","not allowed ["+zTXt_Key[i:i+2]+"]"),Candy("Color","red",i),Candy("Color","red",int(zTXt_Key[i:i+2],16))))

           if len(zTXt_Key) >=79:
                      print("-zTXt Keyword length is %s :%s"%(Candy("Color","red","not Valid"),Candy("Color","red",i)))

           zTXt_Key_List.append(bytes.fromhex(zTXt_Key).decode(errors="replace"))
           zTXt_Str_List.append(zTXt_Text.decode(errors="ignore"))
 
           print("-Keyword : ",Candy("Color","green",bytes.fromhex(zTXt_Key).decode(errors="replace")))
           print("-String  : ",Candy("Color","green",zTXt_Text.decode(errors="ignore")))

        except Exception as e:
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

        return

    if Chunk == "iTXt": 
        try:
           null_pos = NullFind(data)
           iTXt_Key = data[:null_pos]

           for i in range(0,len(iTXt_Key),2):
             if int(iTXt_Key[i:i+2],16) not in range(32,127) and int(iTXt_Key[i:i+2],16) not in range(161,256):
               if iTXt_Key[i:i+2] != "00" and iTXt_Key[i:i+2] != "0a": 
                  print("-Character %s at index %s in iTXt Keyword (must be between 32-126 and 161-255 but is %s)"%(Candy("Color","red","not allowed ["+iTXt_Key[i:i+2]+"]"),Candy("Color","red",i),Candy("Color","red",int(iTXt_Key[i:i+2],16))))

           if len(iTXt_Key) >=79:
                      print("-iTXt Keyword length is %s :%s"%(Candy("Color","red","not Valid"),Candy("Color","red",i)))


           iTXt_Flag = data[len(iTXt_Key)+2:len(iTXt_Key)+4]
           iTXt_Compression = data[len(iTXt_Key)+4:len(iTXt_Key)+6]

           newpos = len(iTXt_Key)+len(iTXt_Flag)+len(iTXt_Compression)+2

           if data[newpos:newpos+2] == "00":
               iTXt_Lang = ""
           else:
               null_pos = NullFind(data[newpos:])
               iTXt_Lang = data[newpos:newpos+null_pos] 

           newpos = newpos+len(iTXt_Lang)+2

           if iTXt_Lang == "00":
               iTXt_Key_Trad = ""
           else:
               null_pos = NullFind(data[newpos:])
               iTXt_Key_Trad = data[newpos:+newpos+null_pos] 
            
           newpos = newpos+len(iTXt_Key_Trad)+2
           iTXt_String = data[newpos:]

           if iTXt_Flag == "01":
               iTXt_String = zlib.decompress(bytes.fromhex(iTXt_String)).decode()
           elif iTXt_Flag == "00":
               iTXt_String = bytes.fromhex(iTXt_String).decode(errors="replace")

           iTXt_Key_List.append(bytes.fromhex(iTXt_Key).decode(errors="replace"))
           iTXt_String_List.append(iTXt_String)

           print("-Keyword             : ",Candy("Color","green",bytes.fromhex(iTXt_Key).decode(errors="replace")))
           print("-Compression Flag    : ",Candy("Color","green",iTXt_Flag))
           print("-Compression Method  : ",Candy("Color","green",iTXt_Compression))
           print("-Language            : ",Candy("Color","green",bytes.fromhex(iTXt_Lang).decode(errors="replace")))
           print("-Keyword Traduction  : ",Candy("Color","green",bytes.fromhex(iTXt_Key_Trad).decode(errors="replace")))
           print("-String              : ",Candy("Color","green",iTXt_String))

        except Exception as e:
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
        return

    if Chunk == "eXIf":
      eXIf_raw = []
      raw = ""
      sepcounter = 0
      eXIf_endian = bytes.fromhex(data[:4]).decode()

      if eXIf_endian == "II":
         print("-eXif endianess is little-endian : ",eXIf_endian)
      elif eXIf_endian == "MM":
        print("-eXif endianess is big-endian : ",eXIf_endian)

      print("\nRaw values from eXIf data :\n\n")
      for i in range(0,len(data),2):
           raw += data[i:i+2]
           if data[i:i+2] == "00":
               sepcounter +=1
               if sepcounter >=3:
                    eXIf_raw.append(raw)
                    raw = ""
                    sepcounter = 0
      for raw in eXIf_raw:
           if len(raw) < 150:
              print("- "+bytes.fromhex(raw).decode(errors="ignore"))
           else:
              print("-Raw data is too long to be displayed")
      return


    if Chunk == "spAL":
      print("-intermediate sPLT test version")
      return

    if Chunk.encode() in PRIVATE_CHUNKS:
      print("-Private Chunk")
      return

def ReadPng(offset):
     global Have_A_KitKat

     global Orig_CL
     global Orig_CT
     global Orig_CD
     global Orig_CRC

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
         Orig_CL = Chunk_Length
         CLoffX = hex(int(offset/2))
         CLoffB = int(offset/2)
         CLoffI = offset

         Chunk_Type = DATAX[offset+8:offset+16]
         try:
             Orig_CT = bytes.fromhex(Chunk_Type).decode(errors="replace")
         except Exception as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             Orig_CT = Chunk_Type

         CToffX = hex(int(offset/2)+4)
         CToffB = int(offset/2)+4
         CToffI = offset + 4

         Chunk_Data = DATAX[offset+16:offset+16+(int(Chunk_Length, 16)*2)]
         Orig_CD = Chunk_Data
         CDoffX = hex(int(offset/2)+8)
         CDoffB =int(offset/2)+8
         CDoffI = offset + 8

         Chunk_Crc =  DATAX[offset+16+len(Chunk_Data):offset+16+len(Chunk_Data)+8]
         Orig_CRC = Chunk_Crc
         CrcoffX = hex(int(offset/2)+int(Chunk_Length,16)+len(Chunk_Type))
         CrcoffB = int(offset/2)+int(Chunk_Length,16)+len(Chunk_Type)
         CrcoffI =(int(offset/2)+int(Chunk_Length,16)+len(Chunk_Type))*2

         Candy("Title","Chunk Infos:")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CLoffX),Candy("Color","blue",CLoffB),Candy("Color","purple",CLoffI)))
         print("-Chunk Length:              (%s/%s)"%( Candy("Color","yellow",hex(int(Chunk_Length,16)) ) ,Candy("Color","blue",int(Chunk_Length, 16)) ) )
         print("")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CToffX),Candy("Color","blue",CToffB),Candy("Color","purple",CToffI)))
         print("-Chunk Type :               (%s/%s)"%(Candy("Color","yellow",Chunk_Type),Candy("Color","blue",bytes.fromhex(Chunk_Type))))
         print("")
         print("-Found Chunk Data at offset (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CDoffX),Candy("Color","blue",CDoffB),Candy("Color","purple",CDoffI)))
         #print("Chunk Data len  : (%s/%s/%s) "%())
         print("")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CrcoffX),Candy("Color","blue",CrcoffB),Candy("Color","purple",CrcoffI)))
         print("-Chunk Crc:                 (%s/offset :  %s)"%(Candy("Color","yellow",Chunk_Crc),Candy("Color","yellow",hex(CrcoffB))))
##
         CheckLength(Chunk_Data,Chunk_Length,Chunk_Type)
##
         if bytes.fromhex(Chunk_Type) != b'IDAT':
               GetInfo(bytes.fromhex(Chunk_Type).decode(),Chunk_Data)

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

     print("Reached End of %s\n",Sample_Name)
     Critical()
     TheEnd()

def Double_Check(CType,bytesnbr,LastCType):

     Candy("Title","Double Check:")

     print("Or maybe am i missing something ?\nJust let me double check again just to be sure...")

     if len(DATAX)/2 < 67 :
        print("-Wrong File Length.\n\n...\n\nERrr...\nThere are not enough bytes in %s to be a valid png.\n%s is %s bytes long and the very minimum size for a png is 67 bytes so...\ni can't help you much further sorry.\n"%(Candy("Color","white",Sample_Name),Candy("Color","white",Sample_Name),Candy("Color","red",int(len(DATAX)/2))))
        TheEnd()

     print("But this time let's forget about the usual specifications of png format\nThis way i will be able to know if a chunk is missing somewhere.\n")

     NearbyChunk(CType,bytesnbr,LastCType,DoubleCheck=True)


def NearbyChunk(CType,bytesnbr,LastCType,DoubleCheck=None):
     Candy("Title","Chunk N Destroy:")
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
         print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
         print(Candy("Color","red","Scopex:"),Candy("Color","yellow",scopex))
         sys.exit()
       NeedleI = int(Needle/2)
       NeedleX = hex(int(Needle/2))
       Data_End_OffsetI = NeedleI -8

       for Chk in CHUNKS:
#             print("chk.lower ",Chk.lower())
#             print("scope.lower ",scope)
#             print(Chk.lower() == scope)
             if Chk.lower() == scope:
                 print("\nBingo!!!\n\n-Found the closest Chunk to our position:%s at offset %s %s"%(Candy("Color","green",Chk),Candy("Color","blue",NeedleX),Candy("Color","yellow",NeedleI)))
                 if Chk in Excluded:
                        print("\n-Chunk position is %s %s\n"%(Candy("Color","red","Not Valid "),Candy("Emoj","bad")))
                        print("\n...\n\nBut that chunk [%s] is not supposed to be here !\n\nITS A TRAP!\n\nRUN !!!!!!!\n\nRUN TO THE CHOPPER !!!\n"%Candy("Color","red",Chk))
                        print("\n\nI seriously doubt that i could be of any uses with this one ..")
                        print("If you are sure %s is a png i can try to fill the gap but i cannot guarantee any result.."%Candy("Color","white",Sample_Name))
                        if b'IHDR' not in Chunks_History :
                             print("Especially without IHDR chunk..\n")
                        print(Candy("Color","yellow","\n-ToDo"))
                        SideNote.append("-Missplaced Chunk")
                        TheEnd()
                 else:
                      LenCalc = Data_End_OffsetI-CDoffB
                      if "-" in str(LenCalc):
                         print("-Chunk position is %s %s\n"%(Candy("Color","red","Not Valid "),Candy("Emoj","bad")))
                         print("-Got Wrong Result for length...:",Candy("Color","red",LenCalc))
                         print("\nAnother one byte the dust ...\n")
                         print("dataendofI:",Data_End_OffsetI)
                         print("CDoffb:",CDoffB)
                         print(Candy("Color","yellow","\n-ToDo"))
                         TheEnd()
                      print("-Chunk position is %s %s\n"%(Candy("Color","green","Valid "),Candy("Emoj","good")))
                      FixedLen= str('0x%08X' % LenCalc)[2::] # str('0x%08X' % LenCalc)[2::].encode().hex()
                      FixShit(FixedLen,CLoffI,CLoffI+8,("-Found Chunk[%s] has Wrong length at offset: %s\n-Found next chunk: %s at: %s\n-Replaced with: %s old value was: %s"%(Orig_CT,CLoffX,Chk,NeedleX,FixedLen,Orig_CL)))
                      return()
       Needle += 1
     if DoubleCheck is True:
        print("...??\n\nNOTHING AGAIN!?!?!?!?\n")
        print("\n\nTHEY PLAYED US LIKE A DAMN FIDDLE !!!\n\nAMa Outta Here !\n\nDo It YourSelf FFS! "+Candy("Emoj","bad"))
        TheEnd()
     else:
         print("\n...??\n\nJust Reach the EOF and found nothing!!\nCan't do much about that sorry ...\n")
     Double_Check(CType,bytesnbr,LastCType)

     return()

def Critical():
    Candy("Title","Critical Chunks Check :")
    Criticals =[b'PNG',b'IHDR',b'IDAT',b'IEND']
    ToFix = []
    for chnk in Criticals:
         if chnk not in Chunks_History:
             print("-Critical Chunk %s is %s !"%(chnk,Candy("Color","red","Missing")))
             ToFix.append("chunk")
    if len(ToFix) >0:
             SaveErrors("Critical",ToFix)
             TheEnd()
    else:
          print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
    return


def ChunkStory(lastchunk):
  global Warning
  global SideNote

  Candy("Title","Chunklate Rain:")

  Before_PLTE= [b'PNG', b'IHDR', b'gAMA', b'cHRM', b'iCCP', b'sRGB', b'sBIT']
  After_PLTE= [b'tRNS', b'hIST', b'bKGD'] #but before idat
  Before_IDAT=[b'sPLT',b'sBIT', b'pHYs', b'tRNS', b'hIST', b'bKGD', b'gAMA', b'cHRM', b'PLTE', b'IHDR', b'bKGD']
  OnlyOnce=[b'sBIT', b'IEND', b'tRNS', b'hIST', b'sTER', b'iCCP', b'sRGB', b'gAMA', b'sCAL', b'cHRM', b'bKGD', b'IHDR', b'oFFs', b'pCAL', b'PLTE', b'pHYs', b'IEND',b'eXIf']
  Anywhere=[b'tIME', b'tEXt', b'zTXt', b'iTXt', b'fRAc', b'gIFg', b'gIFx', b'gIFt']
  Criticals =[b'PNG',b'IHDR',b'IDAT',b'IEND']

  try:
     lastchunk = lastchunk.encode()
  except AttributeError as e:
      print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

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
         print("%s chunk must be placed before any PLTE related chunks we can forget about thoses:\n\n%s"%(Candy("Color","green",lastchunk.decode()),[i.decode() for i in Excluded]))


      if lastchunk in After_PLTE:
        shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_PLTE]
        print("%s chunk must be placed after PLTE related chunks we can forget about thoses:\n\n%s"%(lastchunk,[i.decode() for i in Excluded]))

      Excluded.append(b'IEND') 

  elif b"IDAT" in Used_Chunks:
          shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_IDAT]

          if int(IHDR_Color) == 3:
                shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid not in Before_PLTE]
                print("\nAH ! I knew this day would come ...\nYou See when Image Header color type is set to 3 (Indexed Colors)..\nPLTE chunk must be placed before any IDAT chunks so that only means one thing ..More code to write for me.")
                print(Candy("Color","yellow","\n-ToDo"))
                TheEnd()

          elif (int(IHDR_Color) == 2) or (int(IHDR_Color) == 6) and Warning is False:
               Warning = True
               SideNote.append("-[Sidenote] There is a chance that Critical PLTE chunk is missing.")
               print("%s\n\nJust wanted you to know that if im not able to fix %s for some reason\nor if you can't view %s once my job is done here ...\nThis is maybe due to a PLTE Chunk that is missing between those guys :\n-------------------------------------------------------\n%s\n+++++++++++++++++\n***[PLTECHUNK]***\n+++++++++++++++++\n%s\n-------------------------------------------------------\nIn Any cases it's before IDAT. \n%s"%(Candy("Color","yellow","################# Warning #################"),Candy("Color","red",Sample_Name),Candy("Color","red",Sample_Name),[i.decode() for i in Before_PLTE],[i.decode() for i in After_PLTE],Candy("Color","yellow","###########################################\n")))


          if lastchunk == b"IDAT":
             print("So ..the last Chunk Type was IDAT so we either looking for another IDAT,IEND or one of them:\n\n%s"%[i.decode() for i in Anywhere])

  return(Excluded)



def BruteChunk(CType,LastCType,bytesnbr):
   Candy("Title","Chunk Scrabble Solver:")
   ErrorA = False
   BingoLst = []
   try:
      CTypeLst = [i.lower() for i in CType]
   except AttributeError as a:
      print(Candy("Color","red","Error:"),Candy("Color","yellow",a))
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
      print("\n\n-Solved Chunk name.\n\nAh looks like we've got a winner! :",Candy("Color","green",BestBingoName))
##TmpFix##
      FixShit(BestBingoName.encode().hex(),CrcoffI+16,CrcoffI+24,"-Found Chunk[%s] has wrong name at offset: %s\n-Chunk was corrupted changing %s bytes turn into a valid Chunk name: %s"%(Orig_CT,CToffX,int(BestBingoScore)-len(Orig_CT),BestBingoName))
      return()
   else:

       Candy("Title","WHO'S THAT POKEMON !?:")
       print("\nArg that's all gibberish ...\nI need you to choose something looking a like [%s] that is actually a real chunk name can you help ?\nOk Please select the right name for the chunk:\n"%Candy("Color","purple",str(CType)))

       for i,j in enumerate(BingoLst):
           print("Score %s ,if you choose this name enter number: %s"%(Candy("Color","green",j),Candy("Color","yellow",i)))

       print("\nIf you feel as lost as me then this might be a Length Problem type : wtf")
       print("\nOr Type quit to ...quit.\n")
       Choice = input("WHO'S THAT POKEMON !? :")
       while True:
          try:
             if (Choice.lower() != "quit" or Choice.lower() != "wtf") and int(Choice) <= len(BingoLst):
                  FixShit(BingoLst[int(Choice)].encode().hex(),CrcoffI+16,CrcoffI+24,"-Found Chunk[%s] has wrong name at offset: %s\n-Chunk seems corrupted user has decided to choose Chunk[%s] as a replacement."%(Orig_CT,CToffX,BingoLst[int(Choice)].encode()))
                  return()
          except Exception as e:
#              print("Error: ",e)
               pass

          if Choice.lower() =="quit":
                    print("Take Care Bye !")
                    TheEnd()
          if Choice.lower() =="wtf":
                     print("\nFine , time to investigate that length..")
                     NearbyChunk(CType,bytesnbr,LastCType)
                     return()
          Choice = input("WHO'S THAT POKEMON !? :")

def CheckChunkName(ChunkType,bytesnbr,LastCType,next=None):
   CType = ChunkType
   try:
       CType = bytes.fromhex(CType)
#       CType = bytes.fromhex(CType).decode(errors="replace")
   except Exception as e:
        print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
        print("ctyp ",CType)
        print(type(CType))

   if next != None:
        Candy("Title","Checking Next Chunk Type:",Candy("Color","white",CType))
   else:
        Candy("Title","Checking Chunk Type:",Candy("Color","white",CType))

   for name in CHUNKS:
       if name.lower() == CType.lower():
               if name == CType:
                      print("\n-Chunk name:"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
                      #if next == None:
                      ToHistory(bytes.fromhex(ChunkType))
                      return(None)

               else:
                      print("\n-Chunk name:"+Candy("Color","red"," FAIL ")+Candy("Emoj","bad"))
                      print("\nMonkey wanted Banana :",Candy("Color","green",name))
                      print("Monkey got Pullover :",Candy("Color","red",CType))
                      print()
                      FixShit(name.hex(),CLoffI,CLoffI+8,("-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"%(Orig_CT,CrcoffX,checksum[2::],Orig_CRC)))
                      return()


   for name in PRIVATE_CHUNKS:
       if name.lower() == CType.lower():
               if name == CType:
                      print("\n-Private Chunk name:"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
                      ToHistory(bytes.fromhex(ChunkType))
                      return(None)

               else:
                      print("\n-Private Chunk name:"+Candy("Color","red"," FAIL ")+Candy("Emoj","bad"))
                      print("\nMonkey wanted Banana :",Candy("Color","green",name))
                      print("Monkey got Pullover :",Candy("Color","red",CType))
                      print()
                      FixShit(name.hex(),CLoffI,CLoffI+8,("-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"%(Orig_CT,CrcoffX,checksum[2::],Orig_CRC)))
                      return()

   print("\n-Chunk name:"+Candy("Color","red"," FAILED ")+Candy("Emoj","bad"))
   try:
      LastCType = bytes.fromhex(str(LastCType)).decode()
   except Exception as e:
        print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
        LastCType = LastCType.decode()

   if len(CType) >=4:
           BruteChunk(CType,LastCType,bytesnbr)
           return()
   else:
        print("\nOf course it has failed! There's nothing at this offset.....\n")
        
   wow = int(bytesnbr/8912)
   if wow >= 3:
      print("..Hum ..Zlib put a limit on buff size up to 8912 bytes..\n and this one is pretty big :%s which is %s times bigger.."%(Candy("Color","yellow",bytesnbr),Candy("Color","red",wow)))
#      print(Bytes_History)
#      print(Bytes_History.count(Bytes_History[0])-1 == len(Bytes_History)-1)
#      print(Bytes_History.count(Bytes_History[0]) != len(Bytes_History))
      if len(Bytes_History) >0: ##ToFIx##
        if Bytes_History.count(Bytes_History[0])-1 == len(Bytes_History)-1:
            if Bytes_History.count(Bytes_History[0]) != len(Bytes_History):
                print("That doesnt mean there cannot be an IDAT chunk bigger than 8912Bytes!\nbut since all previous IDAT chunks had the same length , it seems to me that's a little odd that this very one in particular is different from the others...\nUnless this is the Last IDAT.\nAnyway that is just a thought let's find it out .")
   else:
      print("..Hum ..Maybe thats a length problem.")
   NearbyChunk(CType,bytesnbr,LastCType)
   return()

def CheckLength(Cdata,Clen,Ctype):

       GoodEnding = "0000000049454E44AE426082"
       NextChunk = DATAX[CLoffI+32+len(Cdata):CLoffI+32+len(Cdata)+8]

       if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
               CheckChunkName(Ctype,int(Clen,16),Chunks_History[0])

       Candy("Title","Checking Data Length:",Candy("Color","white",str(Clen)))

       print("So ..The length part is saying that data is %s bytes long."%Candy("Color","yellow",int(Clen, 16)))

       ToBitstory(int(Clen, 16))

       if int(Clen,16)>26736:
           print("Really!? That much ?")

       if len(bytes.fromhex(NextChunk).decode(errors="replace")) == 0:
            print("..And this is what iv found there: "+Candy("Color","red","[NOTHING]"))
       else:
            print("..And this is what iv found there: ",Candy("Color","yellow",bytes.fromhex(NextChunk).decode(errors="replace")))

       if bytes.fromhex(Ctype) == b'IEND' and int(Clen, 16) == 0:

            if DATAX[-len(GoodEnding):].upper() == GoodEnding:
                     Critical()
                     print("\nBut thats only because this is the end of file. ",Candy("Emoj","good"))
                     SideNote.append("-Reach the end of file without error.")

                     Candy("Title","All Done here hoped that did the job !")

                     TheEnd()
            else:
                print(DATAX[-len(GoodEnding):])
                exit()

       CheckChunkName(NextChunk,int(Clen,16),Ctype,True)

def Checksum(Ctype, Cdata, Crc):
    Candy("Title","Check Crc Validity:")
    Cdata = bytes.fromhex(Cdata)
    Ctype = bytes.fromhex(Ctype)
    Crc = hex(int.from_bytes(bytes.fromhex(Crc),byteorder='big'))
    checksum = hex(binascii.crc32(Ctype+Cdata))
    if checksum == Crc:
        print("-Crc Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
        return(None)
    else:
        print("-Crc Check :"+Candy("Color","red"," FAILED ")+Candy("Emoj","bad"))
        if len(Crc) == 0 or len(checksum) == 0:
             print("\nMonkey wanted Banana :",Candy("Color","green",checksum))
             print("Monkey got Pullover :",Candy("Color","red",Crc))
             print("Hold on a sec ... Must have missed something...")
             print()
             exit()

        if len(checksum) < 10:
             checksum = "0x"+(checksum[2::].zfill(8))
        print("\nMonkey wanted Banana :",Candy("Color","green",checksum))
        print("Monkey got Pullover :",Candy("Color","red",Crc))

#        pause = input("pause")
        FixShit(checksum[2::],CrcoffI,CrcoffI+8,("-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"%(Orig_CT,CrcoffX,checksum[2::],Orig_CRC)))



def FixShit(shit,start,end,infos):
         Candy("Title","Fixing File")
         print("-Data : %s\n"%shit)
         Summarise(infos)
         Before = DATAX[:start]
         After = DATAX[end:]
         Fix = Before + shit + After
         SaveClone(Fix)


def SaveClone(data):
         global Sample
         global Have_A_KitKat
         
         data = bytes.fromhex(data)
         name,dir = Naming(FILE_Origin)

         print(Candy("Color","green","-Saving to : "),dir+"/"+name)
         with open(dir+"/"+name,"wb") as f:
             f.write(data)
         Sample = dir+"/"+name
         Have_A_KitKat = True

         if PAUSE is True:
             pause =input("Press Return to continue:")

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
parser.add_argument("-c","--clear",dest="CLEAR",help="Clear screen at each saves.",action="store_true")
parser.add_argument("-p","--pause",dest="PAUSE",help="Pause at each saves.",action="store_true")
Args = parser.parse_args()


if len(sys.argv)==1:
    parser.print_help(sys.stderr)
    sys.exit(1)
if Args.FILENAME is None:
    print("-f,--filename arguments is missing.")
    sys.exit(1)


FILE_Origin = Args.FILENAME
Clear = Args.CLEAR
PAUSE = Args.PAUSE
FILE_DIR = os.path.dirname(os.path.realpath(FILE_Origin))+"/"
Loading_txt = ""
Switch = False
GoBack = False
WORKING = True
MAXCHAR = int(os.get_terminal_size(0)[0])-1
CharPos =1
Have_A_KitKat= False
Warning = False
Summary_Header= True
SideNote = []
ErrorsFlag = []
ErrorsList = []
CHUNKS = [b'sBIT', b'IEND', b'sPLT', b'tRNS', b'fRAc', b'hIST', b'dSIG', b'sTER', b'iCCP', b'sRGB', b'zTXt', b'gAMA', b'IDAT', b'sCAL', b'cHRM', b'bKGD', b'tEXt', b'tIME', b'iTXt', b'IHDR', b'gIFx', b'gIFg', b'oFFs', b'pCAL', b'PLTE', b'gIFt', b'pHYs',b'eXIf']
PRIVATE_CHUNKS = [b'cmOD',b'cmPP',b'cpIp',b'mkBF',b'mkBS',b'mkBT',b'mkTS',b'spAL',b'pcLb',b'prVW',b'JDAT',b'JSEP',b'DHDR',b'FRAM',b'SAVE',b'SEEK',b'nEED',b'DEFI',b'BACK',b'MOVE',b'CLON',b'SHOW',b'CLIP',b'LOOP',b'ENDL',b'PROM',b'fPRI',b'eXPI',b'BASI',b'IPNG',b'PPLT',b'PAST',b'TERM',b'DISC',b'pHYg',b'DROP',b'DBYK',b'ORDR',b'MAGN',b'MEND']
Orig_CL=""
Orig_CT=""
Orig_CD=""
Orig_CRC=""
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
iCCP_Name = ""
iCCP_Method =""
iCCP_Profile =""
IHDR_Height= ""
IHDR_Width= ""
IHDR_Depht= ""
IHDR_Color= ""
IHDR_Method= ""
IHDR_Filter = ""
IHDR_Interlace= ""
bKGD_Gray= ""
bKGD_Red= ""
bKGD_Green= ""
bKGD_Blue= ""
bKGD_Index= ""
sRGB = ""
pCAL_Param=[]
pCAL_Key=""
pCAL_Zero=""
pCAL_Max=""
pCAL_Eq=""
pCAL_PNBR=""
PLTE_R=[]
PLTE_G=[]
PLTE_B=[]
sPLT_Name = ""
sPLT_Depht = ""
sPLT_Red=[]
sPLT_Green=[]
sPLT_Blue=[]
sPLT_Alpha=[]
sPLT_Freq= []
cHRM_WhiteX= ""
cHRM_WhiteY= ""
cHRM_Redx= ""
cHRM_Redy= ""
cHRM_Greenx= ""
cHRM_Greeny= ""
cHRM_Bluex= ""
cHRM_Bluey= ""
gAMA= ""
hIST = []
pHYs_Y=""
pHYs_X=""
pHYs_Unit=""
sTER= ""
gIFID=""
gIFCD=""
gIFDT=""
gIFgM=""
gIFgU = ""
gIFgT =""
sBIT_Gray=""
sBIT_TrueR=""
sBIT_TrueG=""
sBIT_TrueB=""
sBIT_GrayScale=""
sBIT_GrayAlpha=""
sBIT_TrueAlphaR=""
sBIT_TrueAlphaG=""
sBIT_TrueAlphaB=""
sBIT_TrueAlpha=""
tEXt_Key_List = []
tEXt_Str_List =[]
tEXt_Key=""
tEXt_Text=""
iTXt_String_List = []
iTXt_Key_List = []
iTXt_String = ""
iTXt_Key = ""
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
zTXt_Key_List = []
zTXt_Str_List = []
zTXt_Key=""
zTXt_Meth=""
zTXt_Text=""
Sample = FILE_Origin
while True:
     Chunks_History = []
     Bytes_History = []
     Loading_txt = ""
     SideNote = []
     Chunklate(1)
     Sample_Name = os.path.basename(Sample)
     print("-Opening: ",Candy("Color","white",Sample_Name))
     try:
       with open(Sample,"rb") as f:
          data = f.read()
     except Exception as e:
         print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
         sys.exit(1)

     DATAX = data.hex()
     print("-Done.")
     FindMagic()
     if Clear is True:
         if os.name == "posix":
             sys.stdout.write('\033c')
         elif os.name == "nt":
               os.system("cls")
