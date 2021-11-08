#!/usr/bin/python3.6
from argparse import ArgumentParser
from threading import Thread
from datetime import datetime
from contextlib import contextmanager
import sys , os , binascii ,re ,random ,time , zlib ,cv2 , ctypes ,io ,tempfile



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
              if len(SideNotes) > 0:
                  for note in SideNotes:
                       tmp += "\n"+str(note)+"\n"
                  infos = tmp+infos +"\n"
              else:
                  infos = "\n"+infos+"\n"
         elif len(SideNotes) > 0:
                  for note in SideNotes:
                       tmp += "\n"+str(note)+"\n"
                  infos = tmp

         filename = folder+"Summary_Of_"+os.path.splitext(os.path.basename(FILE_Origin))[0]
         print(Candy("Color","green","-Saving Summary : "),filename)
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
                   f.write("\n-Subimage mode    :"+str(sTER))

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
         if arg == "good":
             good = ["´ ▽ ` )ﾉ","Σ ◕ ◡ ◕","٩(｡͡•‿•｡)۶","ᕕ( ᐛ )ᕗ","☜(⌒▽⌒)☞","(｡◕‿‿◕｡)","(ღ˘⌣˘ღ)","(∪ ◡ ∪)","(▰˘◡˘▰)","(✿ ♥‿♥)","(｡◕ ‿ ◕｡)","( ͡° ͜ʖ ͡°)","(/◔ ◡ ◔)/","(ᵔᴥᵔ)","ʕつ ͡◔ ᴥ ͡◔ʔつ","彡໒(⊙ ᴗ⊙)७彡","(´◡`)","(✯◡✯)","(๑˘︶˘๑)","｡^‿^｡","ヽ(ヅ)ノ","(^人^)","(°◡°♡)","(♥ ω♥ *)","❀ ◕ ‿ ◕ ❀","(⁀ᗢ⁀)","ミ=͟͟͞͞(✿ʘ ᴗʘ)っ","ଘ(੭*ˊᵕˋ)੭* ̀ˋ","─=≡Σ(((つ^̀ω^́)つ ","~( ˘▾˘~)","(=^･ω･^=)"," ＼ʕ •ᴥ•ʔ／","ヽ(•‿•)ノ","ヾ(☆▽☆)","(ツ)","◝(^⌣^)◜","ʕ ◉ ᴥ ◉ ʔ","( =① ω① =)",">(^.^)<"]
             rnd = random.randint(0,len(good)-1)
             return(good[rnd])
         elif arg == "bad":
             bad = ["(ಥ﹏ಥ)","(►_◄)","(◉ ︵◉)","ヽ(ｏ`皿′ｏ)ﾉ","凸ಠ益ಠ)凸","╯‵Д′)╯彡┻━┻","¯\_(⊙︿⊙)_/¯","ಠ︵ಠ 凸","ヽ(`Д´)ﾉ","(╯°□°）╯︵ ┻━┻","(✖╭╮✖)","(︶︹︺)","(╯︵╰,)","ヽ(˚௰˚)づ","凸(⊙ ▂⊙ ✖ )","ᕕ༼ ͠ຈ Ĺ̯ ͠ຈ ༽┌∩┐","凸(>皿<)凸","ʕ థ ౪ థ ʔ","༼ ༎ຶ ᆺ ༎ຶ༽","( ◥◣ _◢◤ )","(━┳━ _ ━┳━)","┐(￣ヘ￣)┌","༼☯﹏☯༽","(° -°） ︵ ┻━┻ ","┻━┻︵ \(°□°)/ ︵ ┻━┻ ","◕ ︵◕ ","( ◡ ︵◡ )","(；⌣̀_⌣́)","( ´〒^〒`)","(；￣Д￣)","ʕ TᴥT ʔ ","ヽ(๏ ∀ ๏ )ﾉ","┗(･ω･;)┛","(*￣o￣)","ヽ(O_O )ﾉ","ƪ( ` ▿▿▿▿ ´ ƪ) ","（ΦωΦ）","(x_x)⌒☆"]
             rnd = random.randint(0,len(bad)-1)
             return(bad[rnd])
         if arg == "com":
             com = ["~' ▽ '~ )ﾉ","⁀⊙ ෴ ☉⁀","(๏ᆺ   ๏ υ)","─=≡Σ((( つ•̀ω•́)つ ","⌗(́◉◞౪◟◉‵⌗)","(∩｀-´)⊃━☆ﾟ.*･｡ﾟ ","(〓￣(∵エ∵)￣〓)","┬┴┬┴┤ᵒᵏ (･_├┬┴┬┴ ","((유∀유|||))","ε=ε=(っ* ´□` )っ","（・⊝・∞）","( ● ´⌓ `● )","(╯•﹏•╰)","˛˛ƪ(⌾⃝ ౪ ⌾⃝ ๑)و ̉ ̉ ","( ؕؔʘ̥̥̥̥ ه ؔؕʘ̥̥̥̥ )? ","(´⊙ ω ⊙`)！","ლ(́◉◞౪◟◉‵ლ)","(*′☉.̫☉)","=͟͟͞͞ =͟͟͞͞ ﾍ ( ´ Д `)ﾉ ","  (⁄ ⁄•⁄ω⁄•⁄ ⁄)","(〃＞＿＜;〃)","<(￣ ﹌ ￣)>","(￣ ￣|||)","(￢_￢;)","＼(〇_ｏ)／","(／。＼)","〜(＞＜)〜","(/ω＼)","┐(￣～￣)┌","┐(︶▽︶)┌","ヽ(ˇヘˇ)ノ"]
             rnd = random.randint(0,len(com)-1)
             return(com[rnd])

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


   if mode == "Cowsay":
       BotL = "╰─"
       BotR = "─╯"
       mult = 0
#       print("arg:",arg)
#       print("barg:",arg.encode(errors='ignore'))
       for chr in arg:
                mult += 1
       
       if b"\x1b[1;31;49m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[1;31;49m")*arg.encode(errors='ignore').count(b"\x1b[1;31;49m"))
           Moj = str(Candy("Emoj","com"))
       if b"\x1b[1;32;49m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[1;32;49m")*arg.encode(errors='ignore').count(b"\x1b[1;32;49m"))
       if b"\x1b[1;33;49m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[1;33;49m")*arg.encode(errors='ignore').count(b"\x1b[1;33;49m"))
       if b"\x1b[1;34;49m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[1;34;49m")*arg.encode(errors='ignore').count(b"\x1b[1;34;49m"))
       if b"\x1b[1;35;49m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[1;35;49m")*arg.encode(errors='ignore').count(b"\x1b[1;35;49m"))
       if b"\x1b[1;37;49m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[1;37;49m")*arg.encode(errors='ignore').count(b"\x1b[1;37;49m"))
       if b"\x1b[m" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x1b[m")*arg.encode(errors='ignore').count(b"\x1b[m"))
       if b"\x0A" in arg.encode(errors='ignore'):
           mult = mult - (len(b"\x0A")*arg.encode(errors='ignore').count(b"\x0A"))

       Sep = "━"*mult 
       if data == "com":
           Moj = str(Candy("Emoj","com"))
           lnMoj = len(Moj)
       elif data =="good":
           Moj = str(Candy("Emoj","good"))
           lnMoj = len(Moj)
       else:
           Moj = str(Candy("Emoj","bad"))
           lnMoj = len(Moj)
       CowSep = " "*lnMoj
       CowSep += "/\n"
       CowSep += str(Moj)

       Botrnp = BotL+Sep+BotR
       prnt = " "+str(arg)
       if len(prnt) >= MAXCHAR:
          fullprnt = prnt
          prnt = " "
          mult = int(mult/2)+5
          Sep = "━"*mult 
          Botrnp = BotL+Sep+BotR
          for i in range(0,len(fullprnt),mult):
            if len(arg[i:]) > mult :
              prnt += "  " +str(arg[i:i+mult])+"\n"
            else:
              prnt += "  " +str(arg[i:])
       if data == "com" and os.name != "nt":
           Cowsay = """
%s
\033[1;33;49m%s
%s
\033[m"""%(prnt,Botrnp,CowSep)
       elif data =="good" and os.name != "nt":
           Cowsay = """
%s
\033[1;32;49m%s
%s
\033[m"""%(prnt,Botrnp,CowSep)
       elif data =="bad" and os.name != "nt":
           Cowsay = """
%s
\033[1;31;49m%s
%s
\033[m"""%(prnt,Botrnp,CowSep)
       elif os.name == "nt":
            Cowsay = """
%s
%s
%s
"""%(prnt,Botrnp,CowSep)

       else:
            Cowsay = """
%s
%s
%s
"""%(prnt,Botrnp,CowSep)

       print(Cowsay)

   if mode == "Title":
       BotL = "╰─"
       BotR = "─╯"
       TopL = "╭─"
       TopR ="─╮"
       Sep = "━"*len(str(arg)) if data == None  else "━"*(len(str(arg)+str(data))+3) if "\x1b[m" not in data else "━"*(len(str(arg)+str(data))-12)
       Toprnt = TopL+Sep+TopR
       Botrnp = BotL+Sep+BotR
       prnt = "  " +str(arg) if data == None else "  " +str(arg) +" "+str(data)
       if os.name == "nt":
           Title = """
%s
%s
%s
"""%(Toprnt,prnt,Botrnp)
       elif os.name != "nt":
           Title = """
\033[1;37;49m%s\033[m
%s
\033[1;37;49m%s\033[m
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
       if DEBUG is True:
          print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
       pass

    Chunks_History.append(chunk)
def TheEnd():
     Summarise(None,True)
     Chunklate(0)
     sys.exit(0)

def ToBitstory(bytenbr):
    global Bytes_History
    Bytes_History.append(bytenbr)

@contextmanager
def stderr_redirector(stream):
    original_stderr_fd = sys.stderr.fileno()

    def _redirect_stderr(to_fd):
        """Redirect stderr to the given file descriptor."""
        libc.fflush(c_stderr)
        sys.stderr.close()
        os.dup2(to_fd, original_stderr_fd)
        sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, 'wb'))
    saved_stderr_fd = os.dup(original_stderr_fd)
    try:
        tfile = tempfile.TemporaryFile(mode='w+b')
        _redirect_stderr(tfile.fileno())
        yield
        _redirect_stderr(saved_stderr_fd)
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stderr_fd)

def ChunkForcer():
     global WORKING
     global SideNotes
     Candy("Title","[DEMO]Attempting To Repair Corrupted Chunk Data:[DEMO]")
     Thread(target = Loadingbar).start()
     time.sleep(30)
     print("\n\nDemo ended.\n")
     SideNotes.append( "\n-Launched Data Chunk Bruteforcer.\n-Demo ended well.")
     WORKING = False


def FindMagic():
     global SideNotes

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
                print("-File does not start with a png signature.")
                Candy("Cowsay"," Mkay ...Things just keeps better and better ..","bad")
                print("-Cutting %s bytes from %s since png header starts at offset %s ."%(Candy("Color","white",Sample_Name),Candy("Color","blue",int(pos/2)),Candy("Color","white",Sample_Name),Candy("Color","blue",hex(int(pos/2)))))
                Zankentsu = DATAX[pos::]
                return(CheckPoint("FindMagic","Cutting at Magic",Zankentsu,hex(int(pos/2))))
                
          else:
              return(CheckPoint("FindMagic","Found Magic",pos+lenmagic))

     else:
         print("-File %s start with valid png signature .%s\n"%(Candy("Color","red","does not"),Candy("Emoj","bad")))
         Candy("Cowsay"," This better be a real png or else ....","bad")
         for badnews in magc:
             pos = DATAX.find(badnews)
             if pos != -1:
               if badnews == magc[1]:
                 print("-Some bytes are %s from Png Signature.."%Candy("Color","red","missing"))
                 Candy("Cowsay"," %s seems corrupted due to line feed conversion...It doesnt look that bad...But I ll keep that in mind while im on it.."%(Candy("Color","white",Sample_Name,"bad")))
                 SideNotes.append("-Corruption due to line feed conversion\n-File may still be recovered.\n-Not yet implemented.")
                 ChunkForcer()
                 TheEnd()

               if badnews == magc[0]: 
                 Candy("Cowsay"," Hang on a sec....This is bad news i m afraid..","com")
                 Candy("Cowsay"," %s is badly corrupted ...I cannot guarantee any results and it may take forever to find a solution..."%Sample_Name,"com")
                 print(Candy("Color","yellow","\n-ToDo"))
                 SideNotes.append("-Major Corruption due to line feed conversion\n-File may not be recovered.\n-Not yet implemented.")
                 TheEnd()

         Candy("Cowsay"," Ok let's dig a little bit deeper..","bad")
         return(CheckPoint("FindMagic","dig a little bit deeper"))


def FindFuckingMagic():
     global SideNotes

     Candy("Title","Looking harder for magic header:")
     Candy("Cowsay"," This may take me sometimes please wait ..","com")
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
         print("\n...\n")
         print("-Done! %s\n"%Candy("Emoj","good"))
         print("-Found at offset %s with a score of %s/32 :\n %s\n"%(Candy("Color","blue",hex(int(pos/2))),Candy("Color","green",BestBingoScore),Candy("Color","purple",BestBingoSig)))
         Candy("Cowsay"," I think this is a good start to work with.Lets fix this corrupted signature and see where it leads us...","good")
         
         Odin = FullMagic + DATAX[pos+len(FullMagic)::]
         return(CheckPoint("FindFuckingMagic","Cutting at Magic",Odin,hex(int(pos/2))))


     elif int(BestBingoScore) >= 14:
         #print("count:",BestBingoCount)
         #print("score:",BestBingoScore)
         print("\n\n")
         print("\n\n...")
         [print(BingoList[i]) for i in range(0,20)]
         print("\n\n-Found multiple %s png signatures"%Candy("Color","yellow","potentials"))
         Candy("Cowsay"," Looks like i gonna have to test them all.","bad")
         print(Candy("Color","yellow","\n-ToDo"))
         SideNotes.append("-Found multiple potentials png signatures\n-Not Implemented yet")
         TheEnd()
     else:
         print("\n\n")
         [print(BingoList[i]) for i in range(0,20)]
         print("\n\n-Matching score :",Candy("Color","red","too low"))
         print("\n...\n-Done\n")
         Candy("Cowsay"," Im afraid i wasn't able to find anything that looks like a png signature.Maybe i could try to find if there any Known Chunks names in this file ?","com")
         print(Candy("Color","yellow","\n-ToDo"))
         SideNotes.append("-Png signatures matching score are too low\n-Not Implemented yet")
         TheEnd()

def Ancillary(Chunk):
   global AnciCheck
   Candy("Title","Ancillary Check:",Candy("Color","white",Chunk))
   Charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
   Semantics = []
   try:
      Chunk = Chunk.decode(errors='ignore')
   except:
      pass

   for i in Chunk:
     if i in Charset:
        if i == i.upper():
           Semantics.append(i)
        elif i == i.lower():
           Semantics.append(i)
     else:
         break

   if len(Semantics) != 4:
        print("-[%s] is %s Chunks's naming conventions"%(Chunk,Candy("Color","red","Not Following")))
        Candy("Cowsay","Meaning that could be an unknown private chunk that got corrupt .....Or a Known chunk that got corrupt ...","com")
        Candy("Cowsay","..Or Not even a chunk's name at all ...","bad") 
        AnciCheck=False

   elif len(Semantics) == 4:
        print("-[%s] %s Chunks's naming conventions"%(Chunk,Candy("Color","green","Seems to be Following")))
        Candy("Cowsay","If this is a real Chunk this means that %s is :"%Chunk,"good")
        if Semantics[0] == Semantics[0].upper():
             print("-"+Candy("Color","green",Semantics[0])+":"+Candy("Color","yellow","Critical"))
        else :
             print("-"+Candy("Color","green",Semantics[0])+":"+Candy("Color","yellow","Not Critical"))
        if Semantics[1] == Semantics[1].upper():
             print("-"+Candy("Color","green",Semantics[1])+":"+Candy("Color","yellow","Private"))
        else :
             print("-"+Candy("Color","green",Semantics[1])+":"+Candy("Color","yellow","Not Private"))
        if Semantics[2] == Semantics[2].upper():
             print("-"+Candy("Color","green",Semantics[2])+":"+Candy("Color","yellow","Conform to PNG specifications"))
        else :
             print("-"+Candy("Color","green",Semantics[2])+":"+Candy("Color","yellow","Not Conform to PNG specifications"))
        if Semantics[3] == Semantics[3].upper():
             print("-"+Candy("Color","green",Semantics[3])+":"+Candy("Color","yellow","Unsafe to Copy"))
        else :
             print("-"+Candy("Color","green",Semantics[3])+":"+Candy("Color","yellow","Safe to Copy"))
        AnciCheck=True



def FixItFelix(Chunk):
    Candy("Title","Fix It Felix: ",Candy("Color","white",Chunk))
    try:
       chkd = Chunk.decode(errors="ignore")+"_Tool_"
    except AttributeError:
       chkd = Chunk+"_Tool_"

    for nb,key in enumerate(PandoraBox):
        print("-Currently Fixing",key)

        if DEBUG is True:
              print("len:",len(PandoraBox[key].items()))
              for toolkey,keyvalue in PandoraBox[key].items():
                        print("toolkey:",toolkey)
                        print("keyvalue:",keyvalue)


        if "] has wrong name at offset:" in str(key):

#      FixShit(BestBingoName.encode().hex(),CToffI,CToffI+8,"-Found Chunk[%s] has wrong name at offset: %s\n-Chunk was corrupted changing %s bytes turn into a valid Chunk name: %s"%(Orig_CT,CToffX,int(BestBingoScore)-len(Orig_CT),BestBingoName))
          return(FixShit(PandoraBox[key][chkd+"0"],PandoraBox[key][chkd+"1"],PandoraBox[key][chkd+"2"],str(key)))
          

        if "Wrong Chunk name at offset:" in str(key):
                if AnciCheck is not True:
                    return(FixShit(PandoraBox[key][chkd+"4"].hex(),PandoraBox[key][chkd+"1"],PandoraBox[key][chkd+"2"],("-Replacing %s with %s at %s"%(PandoraBox[key][chkd+"3"],PandoraBox[key][chkd+"4"],PandoraBox[key][chkd+"0"]))))
                if AnciCheck is True:
                   pause = input("pause")

        if "Wrong Crc at offset:" in str(key):

            FixShit(PandoraBox[key][chkd+"0"],PandoraBox[key][chkd+"2"],PandoraBox[key][chkd+"3"],("-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"%(PandoraBox[key][chkd+"4"],PandoraBox[key][chkd+"1"],PandoraBox[key][chkd+"0"],PandoraBox[key][chkd+"5"])))


def SaveErrors(Chunk,Err,*ToolKit):
   global SideNotes
   global ERRORSFLAG
   global PandoraBox
   
   Candy("Title","Keeping Tracks of Errors:")
   print(Candy("Color","purple","-Beta Testing-\n"))

   if type(Chunk) != bytes:
      try:
         ERRORSFLAG.append(Chunk.encode(errors='ignore'))
      except Exception as e:
         print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
         ERRORSFLAG.append(Chunk)
   else:
        ERRORSFLAG.append(Chunk)

   if Chunk == "Critical":
       for chnk in Err:
          print("-CriticalHit:",chnk)
          SideNotes.append("-Critical Chunk %s is missing"%chnk)

   elif type(Err) == list:
       for e in Err:

           if "] has wrong name at offset:" in str(e):
               print("-\033[1;31;49mCriticalHit\033[m:",e)
               SideNotes.append(str(e))
               TOOLS = {}
               Fnum = 0
               for key in PandoraBox:
                   while key.startswith(Chunk+"_Error_"+str(Fnum)):
                       Fnum += 1
               for Tnum,tool in enumerate(ToolKit):
                         TOOLS[Chunk+"_Tool_"+str(Tnum)] = tool
#               print(Chunk+"_Error_"+str(Fnum)+":"+str(e)+"= TOOLS")
               PandoraBox[Chunk+"_Error_"+str(Fnum)+":"+str(e)] = TOOLS

           elif "Wrong Crc at offset:" in str(e):
               print("-\033[1;31;49mCriticalHit\033[m:",e)
               SideNotes.append(str(e))
               TOOLS = {}
               Fnum = 0
               for key in PandoraBox:
                   while key.startswith(Chunk+"_Error_"+str(Fnum)):
                       Fnum += 1
               for Tnum,tool in enumerate(ToolKit):
                         TOOLS[Chunk+"_Tool_"+str(Tnum)] = tool
               PandoraBox[Chunk+"_Error_"+str(Fnum)+":"+str(e)] = TOOLS


           elif "Wrong Chunk name at offset:" in str(e):
               print("-\033[1;31;49mCriticalHit\033[m:",e)
               SideNotes.append(str(e))
               Fnum = 0
               TOOLS = {}
               for key in PandoraBox:
                   while key.startswith(Chunk+"_Error_"+str(Fnum)):
                       Fnum += 1
               for Tnum,tool in enumerate(ToolKit):
                         TOOLS[Chunk+"_Tool_"+str(Tnum)] = tool
               PandoraBox[Chunk+"_Error_"+str(Fnum)+":"+str(e)] = TOOLS


           elif "cHRM is missplaced must appears before PLTE Chunk" in str(e):
               print("-\033[1;31;49mCriticalHit\033[m:",e)
               SideNotes.append(str(e))
           elif "badchar" == str(e):
               print("-\033[1;31;49mCriticalHit\033[m:",e)
               for bad in e[1:]:
                   SideNotes.append("-iCCP name Wrong Character at:"+str(bad))
           elif "-IHDR Width : Wrong size Must be between 1 to 2147483647." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Height : Wrong size Must be between 1 to 2147483647." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "IHDR size have to always be 13 bytes" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Color 3: Wrong bit depht with IHDR Color type 3 (depht must be 1,2,4 or 8)":
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Depht: Wrong bit depht with IHDR Color type 3 (depht must be 1,2,4 or 8)" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Bit depht :Wrong bit value Must be 1,2,4,8 or 16" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Filter Method :Wrong value must be 0." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Compression Algorithms : Wrong value must be 0." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-IHDR Interlace Method : Wrong value must be 0 (no interlace) or 1 (Adam7 interlace)." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-pHYs Pixels per unit, Y axis : Wrong size Must be between 1 to 2147483647." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-pHYs Pixels per unit, X axis : Wrong size Must be between 1 to 2147483647." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-pHYs Unit specifier : Must be between 0 (unknown) or 1(meter)." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-bKGD Gray level :Wrong value Must be less than" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-bKGD Red level :Wrong value Must be less than" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-bKGD Green level :Wrong value Must be less than" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-bKGD Blue level :Wrong value Must be less than" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-PLTE Total palettes number must be divisible by 3" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "PLTE Red palettes entry must Not be empty" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "PLTE Green palettes entry must Not be empty" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "PLTE Blue palettes entry must Not be empty" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-PLTE Green palettes not in bitdepht range" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-PLTE Red palettes not in bitdepht range" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-PLTE Blue palettes not in bitdepht range" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "Error PLTER wrong value at" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "Error PLTEG wrong value at" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "Error PLTEB wrong value at" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Length of iCCP Profile name is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-iCCP Wrong Compression Method value" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-iCCP Profile length is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sPLT Sample depth have to be either 8 or 16" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sPLT name is too long" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Red sPLT length is not divisible by 6" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Red sPLT length is not divisible by 10" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Green sPLT length is not divisible by 6" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Green sPLT length is not divisible by 10" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Blue sPLT length is not divisible by 6" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Blue sPLT length is not divisible by 10" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Alpha sPLT length is not divisible by 6" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Alpha sPLT length is not divisible by 10" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Frequency sPLT length is not divisible by 6" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Frequency sPLT length is not divisible by 10" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Histogram sPLT or PLTE have are missing and must be place before hIST" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "Histogram frequencies entries must match PLTE entries number" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Histogram frequencies entries must match sPLT entries number" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tRNS:sPLT or PLTE have are missing and must be place before tRNS" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tRNS Alpha palettes indexes entries must match PLTE entries number" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "IHDR Color Have to be either 0,2 or 3 when used with tRNS" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tRNS Chunk Must not be empty" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Error tRNS_Gray:" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Error tRNS_TrueR:" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Error tRNS_TrueG:" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Error tRNS_TrueB:" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tRNS Alpha indexes palettes entries must not be superior to sPLT entries" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tRNS Alpha indexes palettes entries must not be superior to PLTE entries" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-Error tRNS_Index:" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sRGB value must be between 0 to 3." == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-cHRM is overided by sRGB chunk" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-cHRM is overided by sRGB chunk and iCCP" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "is missplaced must appears before PLTE Chunk" in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit gray value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Red value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Green value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Blue value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit Grayscale value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit Grayscale Alpha value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Alpha Red value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Alpha Green value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Alpha Blue value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Alpha value must be greater than 0" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True red value must not be greater than 8" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True green value must not be greater than 8" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True blue value must not be greater than 8" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True red value must not be greater than " in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True green value must not be greater than " in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True blue value must not be greater than " in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit Grayscale value must not be greater than " in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit Grayscale Alpha value must not be greater than " in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-sBit True Alpha value must not be greater than " in str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-oFFs position Y must be between -2,147,483,647 to +2,147,483,647" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-oFFs position Y must be between -2,147,483,647 to +2,147,483,647" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-oFFs unit value must be between 0 or 1" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tIME Year is > than the current year" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tIME Month value is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tIME Day value is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tIME Hour value is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tIME Minute value is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           elif "-tIME Second value is not valid" == str(e):
              print("-\033[1;31;49mCriticalHit\033[m:",e)
              SideNotes.append(str(e))
           else:
              print("-Unkown Error"+str(Chunk)+" :"+str(e))
              SideNotes.append("-Unkown Error "+str(Chunk)+" :"+str(e))
              sys.exit(0)
   else:
           print("Param is not a list")
           sys.exit()
#   TheEnd()

def NullFind(data,search4=None):
    null_pos = ''
    if search4 == None:
         search4 = "00"
    for i in range(0,len(data),len(search4)):
         if data[i:i+len(search4)] == search4:
              null_pos = i
              break
    if len(str(null_pos)) >0:
       return(null_pos)
    else:
       return(False)

def LibpngCheck(file):
    Candy("Title","Libpng is reading :%s"%(Candy("Color","white",Sample_Name)))
    f = io.BytesIO()
    with stderr_redirector(f):
        cv2.imread(file)
    result = "{0}".format(f.getvalue().decode('utf-8'))
    if len(result) > 0:
        
        print("-Libpng Check: %s %s"%(Candy("Color","red","Fail"),Candy("Emoj","bad")))
        return(CheckPoint("LibpngCheck",result))
    else:
        print("-Libpng Check: %s %s"%(Candy("Color","red","Ok"),Candy("Emoj","good")))
        return(CheckPoint("LibpngCheck","Oasis is good"))
        
def GetInfo(Chunk,data):
    global SideNotes
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

    ToFix = []
    iCCP_Name = ""
    iTXt_String=""
    iTXt_Key=""
    zTXt_String=""
    zTXt_Key=""
    tEXt_Text=""
    tEXt_Key=""
    Name =""
    lastnm = ""


    Candy("Title","Getting infos about:",Candy("Color","white",str(Chunk)))

    if Chunk == "PNG":
          Candy("Cowsay"," Well ..That's a start ..At least it looks like a png.","good")
    if Chunk == "IHDR":
        try:
             IHDR_Height=str(int(data[:8],16))
#             print(data[:8])
#             pause = input("pause")
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Height:"+e)
        try:
             IHDR_Width=str(int(data[8:16],16))
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Width:"+e)
        try:
             IHDR_Depht=str(int(data[16:18],16))
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Depht:"+e)

        try:
             IHDR_Color=str(int(data[18:20],16))
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Color:"+e)
        try:
             IHDR_Method=str(int(data[20:22],16))
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Method:"+e)

        try:
             IHDR_Filter=str(int(data[22:24],16))
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Filter:"+e)
        try:
             IHDR_Interlace=str(int(data[24:26],16))
        except (NameError,ValueError) as e:
             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             ToFix.append("Error IHDR Interlace:"+e)
        try:
             print("-Width    :",Candy("Color","yellow",IHDR_Height))
             print("-Height   :",Candy("Color","yellow",IHDR_Width))
             print("-Depht    :",Candy("Color","yellow",IHDR_Depht))
             print("-Color    :",Candy("Color","yellow",IHDR_Color))
             print("-Method   :",Candy("Color","yellow",IHDR_Method))
             print("-Filter   :",Candy("Color","yellow",IHDR_Filter))
             print("-Interlace:",Candy("Color","yellow",IHDR_Interlace))

             if len(data) != 26:
                   print("-Bytes number :"+Candy("Color","red"," Wrong size")+"IHDR size have to always be 13 bytes."+Candy("Emoj","bad"))
                   ToFix.append("IHDR size have to always be 13 bytes")

             if len(IHDR_Height) >0:
                    if int(IHDR_Height) > 2147483647:
                          print("-Height :"+Candy("Color","red"," Wrong size (Too high)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("-Height Must be between 1 to 2147483647.")
             else:
                          print("-Height :"+Candy("Color","red"," Wrong size (Too low)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("-Height Must be between 1 to 2147483647.")

             if len(IHDR_Width) >0:
                    if int(IHDR_Width) > 2147483647:
                          print("-Width :"+Candy("Color","red"," Wrong size (Too high)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("-Width Must be between 1 to 2147483647.")
             else:
                          print("-Width :"+Candy("Color","red"," Wrong size (Too low)")+" Must be between 1 to 2147483647."+Candy("Emoj","bad"))
                          ToFix.append("-Width Must be between 1 to 2147483647.")

             if len(IHDR_Depht) > 0:
                     if IHDR_Depht not in ["1","2","4","8","16"]:
                         print("-Bit depht :"+Candy("Color","red"," Wrong bit value")+" Must be 1,2,4,8 or 16 "+Candy("Emoj","bad"))
                         ToFix.append("-IHDR Depht: Wrong bit depht (depht must be 1,2,4,8 or 16)")
             else:
                         print("-Bit depht :"+Candy("Color","red"," Wrong bit value")+" Must not be empty "+Candy("Emoj","bad"))
                         ToFix.append("-IHDR Depht Must not be empty")

             if len(IHDR_Color) > 0:
                 if IHDR_Color not in ["0","2","3","4","6"]:
                         print("-IHDR Color :"+Candy("Color","red"," Wrong bit value")+" Must be 0,2,3,4 or 6 "+Candy("Emoj","bad"))
                         ToFix.append("-IHDR Color Must be 0,2,3,4 or 6.")
                 if IHDR_Color == "2" or IHDR_Color == "4" or IHDR_Color == "6":
                     if IHDR_Depht not in ["8","16"]:
                         print("-IHDR Color :"+Candy("Color","red"," Wrong bit depht ")+"for IHDR Color "+IHDR_Color+" must be 8 or 16 "+Candy("Emoj","bad"))
                         ToFix.append("Color")
                 if IHDR_Color == "3":
                     if IHDR_Depht not in ["1","2","4","8"]:
                         print("-IHDR Color :"+Candy("Color","red"," Wrong bit depht ")+"for IHDR Color 3 must be 1,2,4 or 8"+Candy("Emoj","bad"))
                         ToFix.append("-IHDR Color 3: Wrong bit depht with IHDR Color type 3 (depht must be 1,2,4 or 8)")
             else:
                         print("-IHDR Color %s "%(Candy("Color","red","Must not be empty"),Candy("Emoj","bad")))
                         ToFix.append("-IHDR Color Must not be empty")

             if len(IHDR_Filter) > 0 and IHDR_Filter != "0":
                   print("-Filter Method :"+Candy("Color","red"," Wrong value")+" must be 0."+Candy("Emoj","bad"))
                   ToFix.append("Filter")
             elif len(IHDR_Filter) == 0 :
                  print("-Filter Method %s %s "%(Candy("Color","red","Must not be empty"),Candy("Emoj","bad")))
                  ToFix.append("Filter")
             if len(IHDR_Method) > 0 and IHDR_Method != "0":
                   print("-Compression Algorithms :"+Candy("Color","red"," Wrong value")+" must be 0."+Candy("Emoj","bad"))
                   ToFix.append("Compression")
             elif len(IHDR_Method) == 0 :
                  print("-Compression Algorithms must not be empty %s %s "%(Candy("Color","red","Must not be empty"),Candy("Emoj","bad")))
                  ToFix.append("Compression")
             if len(IHDR_Interlace) > 0 and (IHDR_Interlace != "0" and IHDR_Interlace != "1"):
                   print("-Interlace Method :"+Candy("Color","red"," Wrong value")+" must be 0 (no interlace) or 1 (Adam7 interlace)."+Candy("Emoj","bad"))
                   ToFix.append("Interlace")
             elif len(IHDR_Interlace) == 0:
                 print("-Interlace %s %s "%(Candy("Color","red","Must not be empty"),Candy("Emoj","bad")))

             if len(ToFix) > 0:
                  SaveErrors(Chunk,ToFix)
             else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

        except Exception as e:
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
           ToFix.append("Error IHDR:"+str(e))
           SaveErrors(Chunk,ToFix)
         
    if Chunk == "IDAT":
        print("-Image Datastream.")

    if Chunk == "pHYs":
        try:
             pHYs_Y=str(int(data[:8],16))
             print("-Pixels per unit, Y axis: ",Candy("Color","yellow",pHYs_Y))
        except (NameError,ValueError) as e:
             ToFix.append("Error pHYs Y:"+e)
        try:
             pHYs_X=str(int(data[8:16],16))
             print("-Pixels per unit, X axis: ",Candy("Color","yellow",pHYs_X))
        except (NameError,ValueError) as e:
             ToFix.append("Error pHYs X:"+e)
        try:
             pHYs_Unit=str(int(data[16:18],16))
             print("-Unit specifier         :",Candy("Color","yellow",pHYs_Unit))
        except (NameError,ValueError) as e:
             ToFix.append("Error pHYs U:"+e)
        try:
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
           print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
           ToFix.append("Error pHys:"+str(e))
           SaveErrors(Chunk,ToFix)
        

    if Chunk == "bKGD":
        if IHDR_Color == "0" or IHDR_Color == "4":
             try:
                  bKGD_Gray=str(int(data[:4],16))
                  print("-Gray    :",Candy("Color","yellow",bKGD_Gray))
             except Exception as e:
                 ToFix.append("Error bKGD Gray:"+str(e))
                 print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

             if len(bKGD_Gray) >0:
                  if int(bKGD_Gray) > (2**int(IHDR_Depht))-1:
                    print("-Gray level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                    ToFix.append("Bkgd_Gray")

        if IHDR_Color == "2" or IHDR_Color == "6":
           try:
                try:
                   bKGD_Red=str(int(data[:4],16))
                   print("-Red    :",Candy("Color","red",bKGD_Red))
                except Exception as e:
                   ToFix.append("Error bKGD Red:"+str(e))
                   print(Candy("Color","red","Error bKGD Red:"),Candy("Color","yellow",e))

                try:
                  bKGD_Green=str(int(data[4:8],16))
                  print("-Green  :",Candy("Color","green",bKGD_Green))
                except Exception as e:
                   ToFix.append("Error bKGD Green:"+str(e))
                   print(Candy("Color","red","Error bKGD Green:"),Candy("Color","yellow",e))
                try:
                  bKGD_Blue=str(int(data[8:12],16))
                  print("-Blue   :",Candy("Color","blue",bKGD_Blue))
                except Exception as e:
                   ToFix.append("Error bKGD Blue:"+str(e))
                   print(Candy("Color","red","Error bKGD Blue:"),Candy("Color","yellow",e))

                if len(bKGD_Red) > 0:
                  if int(bKGD_Red) > (2**int(IHDR_Depht))-1:
                      print("-Red level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                      ToFix.append("Bkgd_Red")
                if len(bKGD_Green) > 0:
                  if int(bKGD_Green) > (2**int(IHDR_Depht))-1:
                      print("-Green level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                      ToFix.append("Bkgd_Green")
                if len(bKGD_Blue) > 0:
                  if int(bKGD_Blue) > (2**int(IHDR_Depht))-1:
                      print("-Blue level :"+Candy("Color","red"," Wrong value")+" Must be less than "+str((2**int(IHDR_Depht))-1))+Candy("Emoj","bad")
                      ToFix.append("Bkgd_Blue")

           except Exception as e:
              ToFix.append("Error Bkgd:"+str(e))
              SaveErrors(Chunk,ToFix)
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
        

    if Chunk == "PLTE":
          PLTNbr = len(data)


          if not str(int(PLTNbr)/3).endswith(".0"):
             print("-%s PLTE length: %s/3= %s (not divisible by 3). %s"%(Candy("Color","red","Wrong"),PLTNbr,Candy("Color","red",PLTNbr),Candy("Emoj","bad")))
             ToFix.append("-PLTE Total palettes number must be divisible by 3")

          for i in range(0,PLTNbr,6):
             pltr = data[i:i+2]
             try:
                int(pltr,16)
             except Exception as e:
                print(Candy("Color","red","Error palettes red number "+str(i)+":"),Candy("Color","yellow",e))
                ToFix.append("Error PLTER wrong value at"+str(i)+":"+e)

             pltg = data[i+2:i+4]
             try:
                int(pltg,16)
             except Exception as e:
                print(Candy("Color","red","Error palettes green number "+str(i+2)+":"),Candy("Color","yellow",e))
                ToFix.append("Error PLTEG wrong value at "+str(i+2)+":"+e)

             pltb = data[i+4:i+6]

             try:
                int(pltb,16)
             except Exception as e:
                print(Candy("Color","red","Error palettes blue number "+str(i+4)+":"),Candy("Color","yellow",e))
                ToFix.append("Error PLTEB wrong value at "+str(i+4)+":"+e)

             PLTE_R.append(str(pltr))
             PLTE_G.append(str(pltg))
             PLTE_B.append(str(pltb))

          print("-%s Red palettes are stored."%Candy("Color","yellow",len(PLTE_R)))
          print("-%s Green palettes are stored."%Candy("Color","yellow",len(PLTE_G)))
          print("-%s Blue palettes are stored."%Candy("Color","yellow",len(PLTE_B)))
          print("-%s RGB palettes are stored."%Candy("Color","yellow",len(PLTE_R)+len(PLTE_G)+len(PLTE_B)))

          if len(IHDR_Depht) > 0:
            if len(PLTE_R) > 2 ** int(IHDR_Depht):
               print("-PLTE %s Red palettes not in bitdepht range: (must not be > 2 power of image Depht:%s).%s"%(Candy("Color","red",str(len(pltb)-1)+" Wrong"),Candy("Color","yellow",2 ** int(IHDR_Depht)),Candy("Emoj","bad")))
               ToFix.append("-PLTE RED palettes not in bitdepht range")
            elif len(PLTE_R) == 0:
                 print("-PLTE RED palettes entry must %s . %s"%(Candy("Color","red","Not be empty"),Candy("Emoj","bad")))
                 ToFix.append("-PLTE RED palettes entry must Not be empty")

            if len(PLTE_G) > 2 ** int(IHDR_Depht):
               print("-PLTE %s  Green palettes not in bitdepht range: (must not be > 2 power of image Depht:%s).%s"%(Candy("Color","red",str(len(pltb))+" Wrong"),Candy("Color","yellow",2 ** int(IHDR_Depht)),Candy("Emoj","bad")))
               ToFix.append("-PLTE Green palettes not in bitdepht range")
            elif len(PLTE_G) == 0:
                 print("-PLTE Green palettes entry must %s . %s"%(Candy("Color","red","Not be empty"),Candy("Emoj","bad"))) 
                 ToFix.append("-PLTE Green palettes entry must Not be empty")

            if len(PLTE_B) > 2 ** int(IHDR_Depht):
               print("-PLTE %s Blue palettes not in bitdepht range: (must not be > 2 power of image Depht:%s). %s"%(Candy("Color","red",str(len(pltb))+" Wrong"),Candy("Color","yellow",2 ** int(IHDR_Depht)),Candy("Emoj","bad")))
               ToFix.append("-PLTE Blue palettes not in bitdepht range")
            elif len(PLTE_G) == 0:
                 print("-PLTE Blue palettes entry must %s . %s"%(Candy("Color","red","Not be empty"),Candy("Emoj","bad")))
                 ToFix.append("-PLTE Blue palettes entry must Not be empty")
          else:
              print("-IHDR Depht value %s first.%s"%(Candy("Color","red","have to be fixed"),Candy("Emoj","bad")))
              ToFix.append("-IHDR Depht value have to be fixed first")

          if len(ToFix) >0:
             SaveErrors(Chunk,ToFix)
          else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
          

    if Chunk == "sPLT":

      sPLT_Ln = len(data)
      if sPLT_Ln <= 0:
             print("-sPLT entries must %s . %s"%(Candy("Color","red","Not be empty"),Candy("Emoj","bad")))
             ToFix.append("Empty")

      elif NullFind(data) is False:
             print("-sPLT %s any Null Bytes !%s . %s"%(Candy("Color","red","haven't found"),Candy("Emoj","bad")))
             ToFix.append("noNull")
      elif sPLT_Ln > 0 and NullFind(data) is not False:
        null_pos=NullFind(data)
        Name = data[:null_pos]
        ChrName = ""
        badchar=["badchar"]

        for i in range(0,len(Name),2):
          try:
             nint = int(data[i:i+2],16)
             nchar = chr(nint)
          except Exception as e:
             print(Candy("Color","red","Error sPLt Name :"),Candy("Color","yellow",e))
             nint = 258
             nchar = chr(nint)

          if (nint not in range(32,127)) and (nint not in range(161,256)):
                  print("-Character %s at index %s in sPLT_Name\n-Replaced by [€] %s"%(Candy("Color","red","not allowed ["+nchar+"]"),Candy("Color","red",i),Candy("Emoj","bad")))
                  ChrName += "€"
                  badchar.append(i)
          else:
               ChrName += nchar

        if len(badchar) > 1:
             ToFix.append(badchar)
        
        Depht = str(int(data[null_pos+2:null_pos+4],16))
        if Depht != "8" and Depht != "16":
            print("-Sample depth is %s it must be 8 or 16 :%s %s"%(Candy("Color","red","not correct"),Candy("Color","red",Depht),Candy("Emoj","bad")))
            ToFix.append("depth")
        pos = 0
        for i in range(sPLT_Ln):
             if Depht == "8":
                 sPLT_Red.append(data[:pos])
                 sPLT_Green.append(data[pos:pos+2])
                 sPLT_Blue.append(data[pos+2:pos+4])
                 sPLT_Alpha.append(data[pos+4:pos+6])
                 sPLT_Freq.append(data[pos+6:pos+8])
                 pos += 8

             if Depht == "16":
                 sPLT_Red.append(data[:pos])
                 sPLT_Green.append(data[pos:pos+4])
                 sPLT_Blue.append(data[pos+4:pos+8])
                 sPLT_Alpha.append(data[pos+8:pos+16])
                 sPLT_Freq.append(data[pos+16:pos+24])
                 pos += 24
             else:
                  break


        if len(Name) >79:
               print("-Length of sPLT name is %s :%s %s"%(Candy("Color","red","not Valid (Too long >79)"),Candy("Color","red",i),Candy("Emoj","bad")))
               ToFix.append("name")

        print("-sPLT name : ",Candy("Color","white",ChrName))

        print("-%s Suggested Red palettes are stored."%Candy("Color","yellow",len(sPLT_Red)))

        if Depht == "8":
          if not str(int(len(sPLT_Red))/6).endswith(".0"):
             print("-%s Red sPLT length: %s /6= %s (not divisible by 6). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Red)),str(len(sPLT_Red)/6),Candy("Emoj","bad"))) 
             ToFix.append("div8r")

        elif Depht == "16":
          if not str(int(len(sPLT_Red))/10).endswith(".0"):
             print("-%s Red sPLT length: %s/10= %s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Red)),str(len(sPLT_Red)/10),Candy("Emoj","bad")))
             ToFix.append("div16r")
        
        print("-%s Suggested Green palettes are stored."%Candy("Color","yellow",len(sPLT_Green)))


        if Depht == "8":
          if not str(int(len(sPLT_Green))/6).endswith(".0"):
             print("-%s Green sPLT length: %s /6= %s (not divisible by 6). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Green)),str(len(sPLT_Green)/6),Candy("Emoj","bad")))
             ToFix.append("div8g")

        elif Depht == "16":
          if not str(int(len(sPLT_Green))/10).endswith(".0"):
             print("-%s Green sPLT length: %s/10= %s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Green)),str(len(sPLT_Green)/10),Candy("Emoj","bad")))
             ToFix.append("div16g")

        print("-%s Suggested Blue palettes are stored."%Candy("Color","yellow",len(sPLT_Blue)))


        if Depht == "8":
          if not str(int(len(sPLT_Blue))/6).endswith(".0"):
             print("-%s Blue sPLT length: %s /6= %s (not divisible by 6). %s "%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Blue)),str(len(sPLT_Blue)/6),Candy("Emoj","bad")))
             ToFix.append("div8b")

        elif Depht == "16":
          if not str(int(len(sPLT_Blue))/10).endswith(".0"):
             print("-%s Blue sPLT length:%s /10= %s (not divisible by 10). %s "%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Blue)),str(len(sPLT_Blue)/10),Candy("Emoj","bad")))
             ToFix.append("div16b")




        print("-%s Suggested Alpha palettes are stored."%Candy("Color","yellow",len(sPLT_Alpha)))

        if Depht == "8":
          if not str(int(len(sPLT_Alpha))/6).endswith(".0"):
             print("-%s Alpha sPLT length: %s /6= %s (not divisible by 6). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Alpha)),str(len(sPLT_Alpha)/6),Candy("Emoj","bad")))
             ToFix.append("div8a")

        elif Depht == "16":
          if not str(int(len(sPLT_Alpha))/10).endswith(".0"):
             print("-%s Aplha sPLT length:%s /10= %s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Alpha)),str(len(sPLT_Alpha)/10),Candy("Emoj","bad")))
             ToFix.append("div16a")



        print("-%s Suggested Frequency values are stored."%Candy("Color","yellow",len(sPLT_Freq)))

        if Depht == "8":
          if not str(int(len(sPLT_Freq))/6).endswith(".0"):
             print("-%s Frequency sPLT length: %s /6= %s (not divisible by 6). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Freq)),str(len(sPLT_Freq)/6),Candy("Emoj","bad")))
             ToFix.append("div8f")

        elif Depht == "16":
          if not str(int(len(sPLT_Freq))/10).endswith(".0"):
             print("-%s Frequency sPLT length:%s /10= %s (not divisible by 10). %s"%(Candy("Color","red","Wrong"),Candy("Color","red",len(sPLT_Freq)),str(len(sPLT_Freq)/10),Candy("Emoj","bad")))
             ToFix.append("div16f")

        sPLT_Depht.append(Depht)
        sPLT_Name.append(Name)

        for nm in sPLT_Name:
            if sPLT_Name.count(nm) >1 and nm != lastnm:
                print("-sPLT can be used multiple times %s share the same name. %s "%(Candy("Color","red","but cannot"),Candy("Emoj","bad")))
                lastnm = nm
                ToFix.append("name")

      if len(ToFix) >0:
              if len(badchar) >1:
                 SaveErrors(Chunk,ToFix,data)
              else:
                 SaveErrors(Chunk,ToFix)
      else:
               print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
        

    if Chunk == "hIST":
      if len(data) <= 0:
              print("-hIST must %s . %s"%(Candy("Color","red","Not be empty"),Candy("Emoj","bad")))
              ToFix.append("Empty")
    
      elif len(data) > 0:
        
        if b"PLTE" not in Chunks_History and b"sPLT" not in Chunks_History:
              print("-%s Chunk or %s is missing.(hIST must be used after one of them)"%(Candy("Color","red","PLTE"),Candy("Color","red","sPLT")))
              ToFix.append("missing")
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

        except Exception as e:
            print(Candy("Color","red","Error:"),Candy("Color","yellow",e))

      if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix,data)
      else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))


        

    if Chunk == "tIME":
       if len(data) < 14:
          print("-tIME %s inside tIME data.%s"%(Candy("Color","red","Not enough bytes"),Candy("Emoj","bad")))
          ToFix.append("Empty")

       else:
         try:
             tIME_Yr=str(int(data[:4],16))
         except Exception as e:
             print(Candy("Color","red","Error tIME Years:"),Candy("Color","yellow",e))
             ToFix.append("-tIME Year is > than the current year")
         try:
             tIME_Mth=str(int(data[4:6],16))
         except Exception as e:
             print(Candy("Color","red","Error tIME Months:"),Candy("Color","yellow",e))
             ToFix.append("-tIME Month value is not valid")
         try:
             tIME_Day=str(int(data[6:8],16))
         except Exception as e:
             print(Candy("Color","red","Error tIME Days:"),Candy("Color","yellow",e))
             ToFix.append("-tIME Day value is not valid")
         try:
             tIME_Hr=str(int(data[8:10],16))
         except Exception as e:
             print(Candy("Color","red","Error tIME Hours:"),Candy("Color","yellow",e))
             ToFix.append("-tIME Hour value is not valid")
         try:
             tIME_Min=str(int(data[10:12],16))
         except Exception as e:
             print(Candy("Color","red","Error tIME Minutes:"),Candy("Color","yellow",e))
             ToFix.append("-tIME Minute value is not valid")
         try:
             tIME_Sec=str(int(data[12:14],16))
         except Exception as e:
             print(Candy("Color","red","Error tIME Seconds:"),Candy("Color","yellow",e))
             ToFix.append("-tIME Second value is not valid")

         if len(ToFix) == 0:
             print("-Last Modified: %s/%s/%s %s:%s:%s"%(Candy("Color","white",tIME_Day),Candy("Color","white",tIME_Mth),Candy("Color","white",tIME_Yr),Candy("Color","white",tIME_Hr),Candy("Color","white",tIME_Min),Candy("Color","white",tIME_Sec)))
         if len(str(tIME_Yr)) > 0:
             if int(tIME_Yr) > datetime.now().year:
                 print("-Year is > than current year    : %s %s"%(Candy("Color","red",tIME_Yr),Candy("Emoj","bad")))
                 ToFix.append("Year")
         if len(str(tIME_Mth)) > 0:
             if int(tIME_Mth) not in range(1,13):
                 print("-Month value is not valid   : %s %s"%(Candy("Color","red",tIME_Mth),Candy("Emoj","bad")))
                 ToFix.append("Month")
         if len(str(tIME_Day)) > 0:
             if int(tIME_Day) not in range(1,32):
                 print("-Day value is not valid      : %s %s"%(Candy("Color","red",tIME_Day),Candy("Emoj","bad")))
                 ToFix.append("Day")
         if len(str(tIME_Hr)) > 0:
             if int(tIME_Hr) not in range(0,24):
                 print("-Hour value is not valid     : %s %s"%(Candy("Color","red",tIME_Hr),Candy("Emoj","bad")))
                 ToFix.append("Hour")
         if len(str(tIME_Min)) > 0:
             if int(tIME_Min) not in range(0,60):
                  print("-Minute value is not valid  : %s %s"%(Candy("Color","red",tIME_Min),Candy("Emoj","bad")))
                  ToFix.append("Minute")
         if len(str(tIME_Sec)) > 0:
             if int(tIME_Sec) not in range(0,61):
                  print("-Second  value is not valid : %s %s"%(Candy("Color","red",tIME_Sec),Candy("Emoj","bad")))
                  ToFix.append("Second")

         if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix)
         else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

             

    if Chunk == "tRNS":
      TRNSNBR = len(data)
      if len(IHDR_Color) == 0:
              print("-IHDR Color value %s first.%s"%(Candy("Color","red","have to be fixed"),Candy("Emoj","bad")))
              ToFix.append("IHDR Color Have to be either 0,2 or 3 when used with tRNS")
      elif len(data) == 0:
              print("-tRNS Chunk %s "%(Candy("Color","red","Must not be empty"),Candy("Emoj","bad")))
              ToFix.append("-tRNS Chunk Must not be empty")
      elif str(IHDR_Color) not in ["0","2","3"]:
              print("-IHDR Color %s either 0,2 or 3 when used with tRNS %s"%(Candy("Color","red","Have to be"),Candy("Emoj","bad")))
              print("-IHDR Color value %s first.%s"%(Candy("Color","red","have to be fixed"),Candy("Emoj","bad")))
              ToFix.append("IHDR Color IHDR Color Have to be either 0,2 or 3 when used with tRNS")
      elif len(data) > 0 and str(IHDR_Color) in ["0","2","3"]:
         if IHDR_Color == "0":
             try:
                tRNS_Gray = str(int(data[:4],16))
                print("-Gray    :",Candy("Color","yellow",tRNS_Gray))
             except Exception as e:
                    print(Candy("Color","red","Error tRNS gray:"),Candy("Color","yellow",e))
                    ToFix.append("Error tRNS_Gray:"+str(e))

         if IHDR_Color == "2":
           try:
                tRNS_TrueR = str(int(data[:4],16))
                print("-Red    :",Candy("Color","red",tRNS_TrueR))
           except Exception as e:
             print(Candy("Color","red","Error tRNS_TrueR:"),Candy("Color","yellow",e))
             ToFix.append("Error tRNS_TrueR:"+str(e))
           try:
                tRNS_TrueG =str(int(data[4:8],16))
                print("-Green  :",Candy("Color","green",tRNS_TrueG))
           except Exception as e:
             print(Candy("Color","red","Error tRNS_TrueG:"),Candy("Color","yellow",e))
             ToFix.append("Error tRNS_TrueG:"+str(e))
           try:
                tRNS_TrueB =str(int(data[8:16],16))
                print("-Blue   :",Candy("Color","blue",tRNS_TrueB))
           except Exception as e:
             print(Candy("Color","red","Error tRNS_TrueB:"),Candy("Color","yellow",e))
             ToFix.append("Error tRNS_TrueB:"+str(e))

         if IHDR_Color == "3":
             if b"PLTE" not in Chunks_History and b"sPLT" not in Chunks_History:
                print("-%s Chunk or %s is missing.(tRNS must be used after one of them) %s"%(Candy("Color","red","PLTE"),Candy("Color","red","sPLT"),Candy("Emoj","bad")))
                ToFix.append("-PLTE Chunk or sPLT is missing.(tRNS must be used after one of them)")

             for i in range(0,TRNSNBR,2):
                 try:
                    tRNS_Index.append(str(int(data[i:i+2],16)))
                 except Exception as e:
                    print(Candy("Color","red","Error tRNS_Index:"),Candy("Color","yellow",e))
                    ToFix.append("Error tRNS_Index:"+str(e))

             print("-%s Alpha indexes are stored."%Candy("Color","yellow",len(tRNS_Index)))


             if b"PLTE" in Chunks_History:
                if (len(tRNS_Index) > len(PLTE_R)) or (len(tRNS_Index) > len(PLTE_G)) or (len(tRNS_Index) > len(PLTE_B)):
                       print("-tRNS Alpha indexes palettes entries %s PLTE entries number %s"%(Candy("Color","red","must not be superior to"),Candy("Emoj","bad")))
                       ToFix.append("-tRNS Alpha indexes palettes entries must not be superior to PLTE entries")

             if b"sPLT" in Chunks_History:
                if (len(hIST) > len(sPLT_Red)) or (len(hIST) > len(sPLT_Green)) or (len(hIST) > len(sPLT_Blue)) or (len(hIST) > len(sPLT_Aplha)):
                       print("-tRNS Alpha indexes palettes entries %s sPLT entries number %s"%(Candy("Color","red","must not be superior to"),Candy("Emoj","bad")))
                       ToFix.append("-tRNS Alpha indexes palettes entries must not be superior to sPLT entries")

      if len(ToFix) >0:
           SaveErrors(Chunk,ToFix)
      else:
           print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

         

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
           ToFix.append("sRGB value must be between 0 to 3.")

         if "cHRM".encode() in Chunks_History:
                 print("-%s already present cHRM will be %s if reconized by decoders %s"%(Candy("Color","red","cHRM"),Candy("Color","red","overide"),Candy("Emoj","bad")))
                 ToFix.append("-cHRM is overided by sRGB chunk")


         if len(ToFix) >0:
                SaveErrors(Chunk,ToFix)
         else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
         

    if Chunk == "cHRM":
             try:
                cHRM_WhiteX=str(int.from_bytes(bytes.fromhex(data[:8]),byteorder='big',signed=False))
                print("-WhiteX   :",Candy("Color","white",cHRM_WhiteX))
             except Exception as e:
                print(Candy("Color","red","-cHRM WhiteX Error::"),Candy("Color","yellow",e))
                ToFix.append("-cHRM WhiteX Error:"+str(e))
             try:
                cHRM_WhiteY=str(int.from_bytes(bytes.fromhex(data[8:16]),byteorder='big',signed=False))
                print("-WhiteY   :",Candy("Color","white",cHRM_WhiteY))
             except Exception as e:
                print(Candy("Color","red","-cHRM WhiteY Error:"),Candy("Color","yellow",e))
                ToFix.append("-cHRM WhiteY Error:"+str(e))

             try:
                cHRM_Redx=str(int.from_bytes(bytes.fromhex(data[16:24]),byteorder='big',signed=False))
                print("-RedX     :",Candy("Color","red",cHRM_Redx))
             except Exception as e:
                print(Candy("Color","red","-cHRM RedX Error:"),Candy("Color","yellow",e))
                ToFix.append("-cHRM RedX Error:"+str(e))

             try:
                cHRM_Redy=str(int.from_bytes(bytes.fromhex(data[24:32]),byteorder='big',signed=False))
                print("-RedY     :",Candy("Color","red",cHRM_Redy))
             except Exception as e:
                print(Candy("Color","red","-cHRM RedY Error:"),Candy("Color","yellow",e))
                ToFix.append("-cHRM RedY Error:"+str(e))

             try:
                cHRM_Greenx=str(int.from_bytes(bytes.fromhex(data[32:40]),byteorder='big',signed=False))
                print("-GreenX   :",Candy("Color","green",cHRM_Greenx))
             except Exception as e:
                print(Candy("Color","red","-cHRM GreenX Error:"),Candy("Color","yellow",e))
  #              ToFix.append("-cHRM GreenX Error:"+str(e))
#
             try:
                cHRM_Greeny=str(int.from_bytes(bytes.fromhex(data[40:48]),byteorder='big',signed=False))
                print("-GreenY   :",Candy("Color","green",cHRM_Greeny))
             except Exception as e:
                print(Candy("Color","red","-cHRM GreenY Error:"),Candy("Color","yellow",e))
                ToFix.append("-cHRM GreenY Error:"+str(e))

             try:
                cHRM_Bluex=str(int.from_bytes(bytes.fromhex(data[48:56]),byteorder='big',signed=False))
                print("-BlueX    :",Candy("Color","blue",cHRM_Bluex))
             except Exception as e:
                print(Candy("Color","red","-cHRM BlueX Error:"),Candy("Color","yellow",e))
                ToFix.append("-cHRM BlueX Error:"+str(e))

             try:
                cHRM_Bluey=str(int.from_bytes(bytes.fromhex(data[56:64]),byteorder='big',signed=False))
                print("-BlueY    :",Candy("Color","blue",cHRM_Bluey))
             except Exception as e:
                print(Candy("Color","red","-cHRM BluY Error:"),Candy("Color","yellow",e))
                ToFix.append("-cHRM BlueY Error:"+str(e))

             if "sRGB".encode() in Chunks_History or "iCCP".encode() in Chunks_History:
                 print("-%s or %s already present cHRM will be overide if reconized by decoders %s"%(Candy("Color","red","sRGB"),Candy("Color","red","iCCP"),Candy("Emoj","bad")))
                 ToFix.append("-cHRM is overided by sRGB chunk and iCCP")

             if len(ToFix) >0:
                 SaveErrors(Chunk,ToFix)
             else:
                print("\n-Errors Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))

             

    if Chunk == "gAMA":
           try:
             gAMA=str(int(data[:8],16))
             print("-Gama   :",Candy("Color","white",gAMA))
           except Exception as e:
             ToFix.append("-Gama value error"+str(e))

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
                       ToFix.append("-Length of iCCP Profile name is not valid")
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
         


    if Chunk == "oFFs":
           try:
                oFFSX = str(int.from_bytes(bytes.fromhex(data[:8]),byteorder='big',signed=True))
           except Exception as e:
                oFFSX = ""
           try:
                oFFSY = str(int.from_bytes(bytes.fromhex(data[8:16]),byteorder='big',signed=True))
           except Exception as e:
                oFFSY = ""
           try:
                oFFSU = str(int(data[16:18],16))
           except:
                oFFSU = ""

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
      

    if Chunk == "gIFg":

                gIFgM = str(int(data[:2],16))
                gIFgU = str(int(data[2:4],16))
                gIFgT = str(int(data[4:6],16))

                print("-Disposal Method    :",Candy("Color","yellow",gIFgM))
                print("-User Input Flag    :",Candy("Color","yellow",gIFgT))
                print("-Delay Time    :",Candy("Color","yellow",gIFgT))
                
    if Chunk == "gIFx":
                gIFID = str(int(data[:16],16))
                gIFCD = str(int(data[16:22],16))
                gIFDT = str(int(data[22:],16))

                print("-Application Identifier    :",Candy("Color","yellow",gIFID))
                print("-Authentication Code    :",Candy("Color","yellow",gIFCD))
                print("-Application Data    :",Candy("Color","yellow",gIFDT))
                
    if Chunk == "sTER":

                sTER = str(int(data[:2],16))

                print("-Subimage mode    :",Candy("Color","yellow",sTER))
                

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
      


    if Chunk == "spAL":
      print("-intermediate sPLT test version")
      

    if Chunk.encode() in PRIVATE_CHUNKS:
      print("-Private Chunk")

    if Chunk.encode() not in ALLCHUNKS:

      print("-%s"%Candy("Color","red","Unknown Chunk."))

    ChunkStory(Chunk,"TheGoodPlace")
    return


def ChunkbyChunk(offset):
         global Have_A_KitKat

         global Raw_Length
         global Raw_Data
         global Raw_Crc
         global Raw_Type
         global Raw_NextChunk


         global Orig_CL
         global Orig_CT
         global Orig_NC
         global Orig_CD
         global Orig_CRC

         global CLoffX
         global CLoffB
         global CLoffI

         global CToffX
         global CToffB
         global CToffI

         global NCoffX
         global NCoffB
         global NCoffI

         global CDoffX
         global CDoffB
         global CDoffI

         global CrcoffX
         global CrcoffB
         global CrcoffI
     
         Raw_Length = DATAX[offset:offset+8]
         Orig_CL = Raw_Length
         CLoffX = hex(int(offset/2))
         CLoffB = int(offset/2)
         CLoffI = offset

         Raw_Type = DATAX[offset+8:offset+16]
         Orig_CT = bytes.fromhex(Raw_Type).decode(errors="ignore")
         CToffX = hex(int(offset/2)+4)
         CToffB = int(offset/2)+4
         CToffI = offset + 8

         Raw_Data = DATAX[offset+16:offset+16+(int(Raw_Length, 16)*2)]
         Orig_CD = Raw_Data
         CDoffX = hex(int(offset/2)+8)
         CDoffB =int(offset/2)+8
         CDoffI = offset + 8

         Raw_Crc =  DATAX[offset+16+len(Raw_Data):offset+16+len(Raw_Data)+8]
         Orig_CRC = Raw_Crc
         CrcoffX = hex(int(offset/2)+int(Raw_Length,16)+len(Raw_Type))
         CrcoffB = int(offset/2)+int(Raw_Length,16)+len(Raw_Type)
         CrcoffI =(int(offset/2)+int(Raw_Length,16)+len(Raw_Type))*2

         Raw_NextChunk = DATAX[offset+32+len(Raw_Data):offset+32+len(Raw_Data)+8]
         Orig_NC = bytes.fromhex(Raw_NextChunk)
         NCoffX = hex(int(offset/2)+int(Raw_Length,16)+len(Raw_Type)+len(Raw_Data))
         NCoffB = int(offset/2)+int(Raw_Length,16)+len(Raw_Type)+16
         NCoffI = (int(offset/2)+int(Raw_Length,16)+len(Raw_Type)+16)*2


         Candy("Title","Chunk Infos:")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CLoffX),Candy("Color","blue",CLoffB),Candy("Color","purple",CLoffI)))
         print("-Chunk Length:              (%s/%s)"%( Candy("Color","yellow",hex(int(Raw_Length,16)) ) ,Candy("Color","blue",int(Raw_Length, 16)) ) )
         print("")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CToffX),Candy("Color","blue",CToffB),Candy("Color","purple",CToffI)))
         print("-Chunk Type :               (%s/%s)"%(Candy("Color","yellow",Raw_Type),Candy("Color","blue",Orig_CT)))
         print("")
         print("-Found Chunk Data at offset (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CDoffX),Candy("Color","blue",CDoffB),Candy("Color","purple",CDoffI)))
         #print("Chunk Data len  : (%s/%s/%s) "%())
         print("")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",CrcoffX),Candy("Color","blue",CrcoffB),Candy("Color","purple",CrcoffI)))
         print("-Chunk Crc:                 (%s/offset :  %s)"%(Candy("Color","yellow",Raw_Crc),Candy("Color","yellow",hex(CrcoffB))))

         print("")
         print("-Found at offset            (%s/%s/%s): (%s/%s/%s) "%(Candy("Color","yellow","Hex"),Candy("Color","blue","Bytes"),Candy("Color","purple","Index"),Candy("Color","yellow",NCoffX),Candy("Color","blue",NCoffB),Candy("Color","purple",NCoffI)))
         print("-Raw_NextChunk Type :       (%s/%s)"%(Candy("Color","yellow",Raw_NextChunk),Candy("Color","blue",Orig_NC)))


         return





def Double_Check(CType,bytesnbr,LastCType):

     Candy("Title","Double Check:")

     print("Or maybe am i missing something ?\nJust let me double check again just to be sure...")

     if len(DATAX)/2 < 67 :
        print("-Wrong File Length.\n\n...\n\nERrr...\nThere are not enough bytes in %s to be a valid png.\n%s is %s bytes long and the very minimum size for a png is 67 bytes so...\ni can't help you much further sorry.\n"%(Candy("Color","white",Sample_Name),Candy("Color","white",Sample_Name),Candy("Color","red",int(len(DATAX)/2))))
        TheEnd()

     Candy("Cowsay"," But this time let's forget about the usual specifications of png format so This way i will be able to know if a chunk is missing somewhere.","good")

     NearbyChunk(CType,bytesnbr,LastCType,DoubleCheck=True)


def NearbyChunk(CType,bytesnbr,LastCType,DoubleCheck=None):
     Candy("Title","Chunk N Destroy:")
     Candy("Cowsay"," Let me check if i can fix that shit..","com")

     if DoubleCheck is None:
         Excluded = ChunkStory(LastCType,"Fix")
     else:
         Candy("Cowsay"," ==Safety Off==","com")
         Excluded = []

     Needle = CLoffI+16

     while Needle < len(DATAX):

       scopex = DATAX[Needle:Needle+8]
       try:
         scope  = bytes.fromhex(scopex).lower()
       except Exception as e:
         print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
         print(Candy("Color","red","Scopex:"),Candy("Color","yellow",scopex))
         sys.exit()
       NeedleI = int(Needle/2)
       NeedleX = hex(int(Needle/2))
       Data_End_OffsetI = NeedleI -8

       for Chk in CHUNKS:
             if Chk.lower() == scope:
                 Candy("Cowsay"," Bingo!!!","good")
                 print("-Found the closest Chunk to our position:%s at offset %s %s"%(Candy("Color","green",Chk),Candy("Color","blue",NeedleX),Candy("Color","yellow",NeedleI)))
                 if Chk in Excluded:
                        print("\n-Chunk position is %s %s\n"%(Candy("Color","red","Not Valid "),Candy("Emoj","bad")))
                        Candy("Cowsay"," But that chunk [%s] is not supposed to be here .."%Candy("Color","red",Chk),"com")
                        Candy("Cowsay"," ITS A TRAP !! RUN !!!!!!!","bad")
                        Candy("Cowsay"," I seriously doubt that i could be of any uses with this one ..","com")
                        Candy("Cowsay"," If you are sure %s is a png i can try to fill the gap but i cannot guarantee any result.."%Candy("Color","white",Sample_Name),"com")
                        if b'IHDR' not in Chunks_History :
                             Candy("Cowsay"," Especially without IHDR chunk..","bad")
                        print(Candy("Color","yellow","\n-ToDo"))
                        SideNotes.append("-Missplaced Chunk")
                        TheEnd()
                 else:
                      LenCalc = Data_End_OffsetI-CDoffB
                      if "-" in str(LenCalc):
                         print("-Chunk position is %s %s\n"%(Candy("Color","red","Not Valid "),Candy("Emoj","bad")))
                         print("-Got Wrong Result for length...:",Candy("Color","red",LenCalc))
                         Candy("Cowsay"," Another one byte the dust ...","bad")
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
        Candy("Cowsay"," ...??NOTHING AGAIN!?!?!?!?","bad")
        Candy("Cowsay"," THEY PLAYED US LIKE A DAMN FIDDLE !!!","bad")
        Candy("Cowsay"," AMa Outta Here !Do It YourSelf FFS!!","bad")
        TheEnd()
     else:
         Candy("Cowsay"," ...??Just Reach the EOF and found nothing!!Can't do much about that sorry ...","com")
     Double_Check(CType,bytesnbr,LastCType)

     return()

def History(Filename,Error):
    global Actions_History
    Actions_History[Filename] = Error
    print("-History Saved.")

def ChunkStory(lastchunk,mode):
  global Warning
  global SideNotes


  ToFix = []
  Before_PLTE= [b'PNG', b'IHDR', b'gAMA', b'cHRM', b'iCCP', b'sRGB', b'sBIT']
  After_PLTE= [b'tRNS', b'hIST', b'bKGD'] #but before idat

  Before_IDAT=[b'PNG',b'sPLT',b'sBIT', b'pHYs', b'tRNS', b'hIST', b'bKGD', b'gAMA',b'iCCP',b'sRGB', b'cHRM', b'PLTE', b'IHDR', b'bKGD']

  Before_IDAT2=[b'IHDR',b'sPLT',b'sBIT', b'pHYs', b'tRNS', b'hIST', b'bKGD', b'gAMA',b'iCCP',b'sRGB', b'cHRM', b'PLTE', b'IHDR', b'bKGD']

  OnlyOnce=[b'PNG',b'sBIT', b'IEND', b'tRNS', b'hIST', b'sTER', b'iCCP', b'sRGB', b'gAMA', b'sCAL', b'cHRM', b'bKGD', b'IHDR', b'oFFs', b'pCAL', b'PLTE', b'pHYs', b'IEND',b'eXIf']

  Anywhere=[b'tIME', b'tEXt', b'zTXt', b'iTXt', b'fRAc', b'gIFg', b'gIFx', b'gIFt']

  Criticals =[b'PNG',b'IHDR',b'IDAT',b'IEND']

  try:
     lastchunk = lastchunk.encode()
  except AttributeError as e:
#      print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
       pass

  if mode == "Critical":

    Candy("Title","Critical Chunks Check :")
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

  if mode == "TheGoodPlace":
    Candy("Title","Missplaced Chunks Check:")

    Used_Chunks = list(dict.fromkeys(Chunks_History))
    Excluded = [used for used in Used_Chunks if used in OnlyOnce]
#    print(Excluded)
    Candy("Cowsay"," So far we came across those chunks in "+Sample_Name +"\n "+ str([i.decode() for i in Used_Chunks]),"good")

    if lastchunk in OnlyOnce:
         if lastchunk in Excluded:
               print("-%s chunk %s be used multiple times."%(Candy("Color","red",lastchunk.decode()),Candy("Color","red","cannot")))
               ToFix.append("Multiple")

    if len(Chunks_History) >0:
        if Chunks_History[0] != b"PNG":
           print("-PNG signature have to be placed %s all the other chunks. %s"%(Candy("Color","red","Befor"),Candy("Emoj","bad")))
           ToFix.append("Missplaced")
    if len(Chunks_History) >1:
       if Chunks_History[1] != b"IHDR":
          print("-IHDR Chunk have to be placed %s and after Png Signature. %s"%(Candy("Color","red","Befor all the other chunks"),Candy("Emoj","bad")))
          ToFix.append("Missplaced")

    if b"PLTE" in Used_Chunks:
          if lastchunk in Before_PLTE:
            shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_PLTE]
            if lastchunk in Excluded:
                   print("-%s  %s must appears before PLTE Chunk. %s"%(Candy("Color","red",lastchunk.decode()+" is missplaced"),lastchunk.decode(),Candy("Emoj","bad")))
              #print(Excluded)
                   ToFix.append(lastchunk.decode()+" is missplaced must appears before PLTE Chunk")

    if b"IDAT" not in Used_Chunks:
          pass

    if b"IDAT" in Used_Chunks:
         shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_IDAT2]
         if lastchunk in Excluded:
              print("-%s  %s must be before IDAT Chunk. %s"%(Candy("Color","red",lastchunk.decode()+" is missplaced"),lastchunk.decode(),Candy("Emoj","bad")))
              #print(Excluded)
              ToFix.append("Missplaced")

    if len(ToFix) >0:
             SaveErrors(lastchunk,ToFix)
    else:
          print("\n-Missplaced Chunk Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
    return

  if mode == "Fix":

    Candy("Title","Checking Already Used Chunks :")
    if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
        Candy("Cowsay"," After Png Header always Follow IHDR this is quite hard to miss..Excluding evrything else","com")
        Excluded = [exclude for exclude in CHUNKS if exclude != b"IHDR"]
        return(Excluded)
  
    Used_Chunks = list(dict.fromkeys(Chunks_History))
    Excluded = [used for used in Used_Chunks if used in OnlyOnce]
    Candy("Cowsay"," So far we came across those chunks in "+Sample_Name + str([i.decode() for i in Used_Chunks]),"good")

    if b"IDAT" not in Used_Chunks:

      if lastchunk in Before_PLTE and b'IHDR' not in Used_Chunks:
         shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid not in Before_PLTE]
         Candy("Cowsay"," %s chunk must be placed before any PLTE related chunks we can forget about thoses:\n%s"%(Candy("Color","green",lastchunk.decode()),[i.decode() for i in Excluded]),"bad")


      if lastchunk in After_PLTE:
        shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_PLTE]
        Candy("Cowsay"," %s chunk must be placed after PLTE related chunks we can forget about thoses:\n%s"%(lastchunk,[i.decode() for i in Excluded]),"bad")

      Excluded.append(b'IEND') 

    elif b"IDAT" in Used_Chunks:
          shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid in Before_IDAT]

          if int(IHDR_Color) == 3:
                shutup = [Excluded.append(forbid) for forbid in CHUNKS if forbid not in Before_PLTE]
                Candy("Cowsay"," AH ! I knew this day would come ...You See when Image Header color type is set to 3 (Indexed Colors)..PLTE chunk must be placed before any IDAT chunks so that only means one thing ..More code to write for me.","com")
                print(Candy("Color","yellow","\n-ToDo"))
                TheEnd()

          elif (int(IHDR_Color) == 2) or (int(IHDR_Color) == 6) and ("PLTE".encode() not in Chunks_History and "sPLT".encode not in Chunks_History):
               if Warning is False:
                 Warning = True
                 ToFix.append("-There is a chance that some Critical Palette chunks are missing.")
                 Candy("Cowsay"," There is a chance that some %s chunks are %s."%(Candy("Color","red","Critical Palette"),Candy("Color","red","Missing")),"bad")
          if lastchunk == b"IDAT":
             Candy("Cowsay"," So ..the last Chunk Type was IDAT so we either looking for another IDAT,IEND or one of them:%s"%[i.decode() for i in Anywhere],"com")

    return(Excluded)



def BruteChunk(CType,LastCType,bytesnbr):
   Candy("Title","Chunk Scrabble Solver:")
   ErrorA = False
   BingoLst = []
   ToFix = []
   try:
      CTypeLst = [i.lower() for i in CType]
   except AttributeError as a:
      if DEBUG is True:
         print(Candy("Color","red","Error:"),Candy("Color","yellow",a))
      CTypeLst = [i for i in CType]
      ErrorA = True

   Candy("Cowsay"," Maybe it's name got corrupted somehow. Let's see about that.","com")

   Excluded = ChunkStory(LastCType,"Fix")
   
   for name in CHUNKS:
       if name not in Excluded:
           Bingo = 0
           if ErrorA is True:
               ChkLst = [i for i in name]
           else:
               ChkLst = [str(i).lower() for i in name]
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
      print("-"+str(Candy("Color","green","Scrabble Solved."))+str(Candy("Emoj","good")))
      Candy("Cowsay"," Ah looks like we've got a winner! :%s"%Candy("Color","green",BestBingoName),"good")

      SaveErrors(Orig_CT,["-Found Chunk[%s] has wrong name at offset: %s but changing %s bytes turn it into a valid Chunk name: %s"%(Orig_CT,CToffX,int(BestBingoScore)-len(Orig_CT),BestBingoName)],BestBingoName.encode().hex(),CToffI,CToffI+8)


      return()
   else:

       Candy("Title","WHO'S THAT POKEMON !?:")
       Candy("Cowsay"," Arg that's all gibberish ...","com")
       print("\nI need you to choose something looking a like [%s] that is actually a real chunk name can you help ?\nOk Please select the right name for the chunk:\n"%Candy("Color","purple",str(CType)))

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
                    Candy("Cowsay"," Take Care Bye !","good")
                    TheEnd()
          if Choice.lower() =="wtf":
                     Candy("Cowsay"," Fine , time to investigate that length..","com")
                     NearbyChunk(CType,bytesnbr,LastCType)
                     return()
          Choice = input("WHO'S THAT POKEMON !? :")

def CheckChunkName(ChunkType,bytesnbr,LastCType,next=None):


   if type(ChunkType) == bytes:
      CType = ChunkType
      #print("ctype is bytes")
   elif type(ChunkType) != bytes:
      try:
          CType = bytes.fromhex(ChunkType)
      except:
          CType = ChunkType.encode(errors="ignore")
   else:   
        print(type(CType))
        print(CType)
        sys.exit() 

   if next != None:
        Candy("Title","Checking Next Chunk Type:",Candy("Color","white",CType))
   else:
        Candy("Title","Checking Current Chunk Type:",Candy("Color","white",CType))

   for name in ALLCHUNKS:
       if name.lower() == CType.lower():
               if name == CType:
                      print("\n-Chunk name:"+Candy("Color","green"," OK ")+Candy("Emoj","good"))
                      #ToHistory(bytes.fromhex(ChunkType))
                      return(None)

               else:
                      print("\n-Chunk name:"+Candy("Color","red"," FAIL ")+Candy("Emoj","bad"))
                      print("\nMonkey wanted Banana :",Candy("Color","green",name))
                      print("Monkey got Pullover :",Candy("Color","red",CType))
                      print()
                      if next == None:
                          if len(CType) > 3:
                              Ancillary(CType)
                          SaveErrors(CType,["-Found Chunk[%s] Wrong Chunk name at offset: %s"%(Orig_CT,CToffX)],CToffX,CToffI,CToffI+8,Orig_CT,name)
                      return()

   if next == None:
       print("\n-Chunk name:"+Candy("Color","red"," FAILED ")+Candy("Emoj","bad"))
       if len(CType) > 3:
           Ancillary(CType)
       try:
          LastCType = bytes.fromhex(str(LastCType)).decode()
       except Exception as e:
            if DEBUG is True:
               print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
            pass

       if len(CType) >=4:
               BruteChunk(CType,LastCType,bytesnbr)
               return()
       else:
            Candy("Cowsay"," WTF!? There's nothing at this offset!!","com")
            
       wow = int(bytesnbr/8912)
       if wow >= 3:
          Candy("Cowsay"," Zlib put a conventional limit on buff size up to 8912 bytes and this one is pretty big :","com")
          print("- %s bytes"%Candy("Color","yellow",str(bytesnbr)))
          Candy("Cowsay"," Which is %s times bigger.."%(wow),"bad")

          if len(Bytes_History) >0: ##ToFIx##
            if Bytes_History.count(Bytes_History[0])-1 == len(Bytes_History)-1:
                if Bytes_History.count(Bytes_History[0]) != len(Bytes_History):
                    Candy("Cowsay"," That doesnt mean there cannot be an IDAT chunk bigger than 8912Bytes!but since all previous IDAT chunks had the same length , it seems to me that's a little odd that this very one in particular is different from the others...Unless this is the Last IDAT.Anyway that is just a thought let's find it out .","com")
       else:
          Candy("Cowsay"," ..Hum ..Maybe thats a length problem.","com")
       NearbyChunk(CType,bytesnbr,LastCType)
   else:
       print("\n-Chunk name:"+Candy("Color","red"," FAILED ")+Candy("Emoj","bad"))
       Candy("Cowsay","But let's ignore it for now we will see about that later ...","bad")
   return()

def CheckLength(Cdata,Clen,Ctype):

       Candy("Title","Checking Data Length:",Candy("Color","white",str(Clen)))

       Candy("Cowsay"," So ..The length part is saying that data is %s bytes long."%Candy("Color","yellow",int(Clen, 16)),"com")


#       if Chunks_History[0] == b"PNG" and len(Chunks_History) == 1:
#               CheckChunkName(Ctype,int(Clen,16),Chunks_History[-1])
#       else:
#               CheckChunkName(Raw_NextChunk,int(Clen,16),Ctype)

       ToBitstory(int(Clen, 16))

       if int(Clen,16)>26736:
           Candy("Cowsay"," Really!? That much ?","com")

       if len(Orig_NC) == 0:
            Candy("Cowsay"," ..And this is what iv found there: "+Candy("Color","red","[NOTHING]"),"com")
            return(CheckPoint("CheckLength","No NextChunk",Ctype,Clen))
       else:
            Candy("Cowsay"," ..And this is what iv found there: "+Candy("Color","yellow",Orig_NC),"com")
            return(CheckPoint("CheckLength","Found NextChunk",Ctype,Clen))



def Question(Chunk,Valid):

     Candy("Title","QUESTION!")
     print("Errors List:\n")
     for key in PandoraBox:print("\033[1;31;49m%s\033[m"%key)
     if Valid is True:
        if AnciCheck is True:
             Candy("Cowsay","I don't know that chunk but it has passed Ancillary nomenclature check and since Crc is valid too this may be a legit private chunk..","com")
        else:
             Candy("Cowsay","Hum errors has been detected but the CRC is still Valid !!! Usually this means that it has been made on purpose by someone...","bad")

        Candy("Cowsay","Do you wish to try to fix this regardless of CRC's validity ?","com")
     elif Valid is False and len(PandoraBox) <= 1:
         Candy("Cowsay","Crc checksum is not valid !!!","bad")
         Candy("Cowsay","This looks like an easy fix since there is no other errors beside the Crc issue.Do you wish to try to fix it ?","com")

     else:
         Candy("Cowsay","Crc checksum is not valid and there are %s other errors !"%(len(PandoraBox)-1),"bad")
         Candy("Cowsay","I can try to handle those errors.Do you wish to try to fix them ?","com")
     if AUTO == False or AnciCheck is True:

         Answer = input("Answer(yes/no):").lower()
         while Answer != "yes" and Answer != "no" :
               Answer = input("Answer(yes/no):").lower()
         if Answer == "yes":
                Candy("Cowsay","Fine , let me see what i can do .","good")
                FixItFelix(Chunk)
         else:
                Candy("Cowsay","Ok ,just do not make eye contact !","com")
                return
     else: 
                print("-%s\n"%Candy("Color","green","Auto Answer Mode"))
                FixItFelix(Chunk)

def Checksum(Ctype, Cdata, Crc,next=None):
    Candy("Title","Check Crc Validity:")
    Cdata = bytes.fromhex(Cdata)
    Ctype = bytes.fromhex(Ctype)
    Crc = hex(int.from_bytes(bytes.fromhex(Crc),byteorder='big'))
    checksum = hex(binascii.crc32(Ctype+Cdata))
    if checksum == Crc:
        print("-Crc Check :"+Candy("Color","green"," OK ")+Candy("Emoj","good")+"\n")
        if next == None:
             ToHistory(Ctype)
        if Ctype in ERRORSFLAG:
             print("-%s Chunks Errors left to be fixed. %s\n"%(Candy("Color","red",len(ERRORSFLAG)),Candy("Emoj","bad")))
             Question(Ctype,True)
#        else:
#            for i in ERRORSFLAG:
#                print(i)
#                print(type(i))
#            pause = input("pause")

        return(None)
    else:
        print("-Crc Check :"+Candy("Color","red"," FAILED ")+Candy("Emoj","bad"))
        if len(Crc) == 0 or len(checksum) == 0:
             print("\nMonkey wanted Banana :",Candy("Color","green",checksum))
             print("Monkey got Pullover :",Candy("Color","red",Crc))
             Candy("Cowsay"," Hold on a sec ... Must have missed something...","com")
             print()
             exit()

        if len(checksum) < 10:
             checksum = "0x"+(checksum[2::].zfill(8))
        print("\nMonkey wanted Banana :",Candy("Color","green",checksum))
        print("Monkey got Pullover :",Candy("Color","red",Crc))

#        pause = input("pause")
        return(CheckPoint("Checksum","Wrong Crc",checksum[2::],CrcoffI,CrcoffI+8,Orig_CT,CrcoffX,Orig_CRC))




def FixShit(shit,start,end,infos):
         Candy("Title","Fixing File")
         try:
            print("-Data : %s\n"%bytes.fromhex(shit))
         except:
            print("-Data : %s\n"%shit)

         History(Sample,infos)

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

def LoadClone():

    Candy("Cowsay","Damned!! We were so close !","bad")
    Candy("Cowsay","We should go some step back before and see if we can do something else..","com")
    Candy("Title","Loading Clone :")

    TmpFix = False

    if len(Actions_History) >=1:
        Candy("Cowsay","This is a quick summary of what we have done :","good")
 
        if len(Actions_History) >1:
            for nb,key in enumerate(Actions_History):
                      print("(Choice %s)-Errors fixed in File %s :"%(nb,key))
                      print("(Choice %s)-Error fixed: %s"%(nb,Actions_History.get(key)))
            print("TODO")
            TheEnd()
        elif len(Actions_History) == 1:
            for key in Actions_History:
                      print("-Errors fixed in File %s :"%key)
                      print(Actions_History.get(key))
                      if "Chunk[IHDR] has Wrong Crc at offset" in Actions_History.get(key):
                            TmpFix = True       
            Candy("Cowsay","That was short indeed ..","com")
            if TmpFix == True:
              Candy("Cowsay","Maybe it wasn't a Crc problem..","com")
              Candy("Cowsay","Maybe that was IHDR Data in Fact!","bad")
              Candy("Cowsay","How about taking a coffee break while im taking care of something?","good")
              ChunkForcer()
              TheEnd()
              

    else:
        print("-%s has been Fixed yet. %s"%(Candy("Color","red","No Error"),Candy("Emoj","bad")))
        Candy("Cowsay","What!? im out of idea atm...","bad")
        TheEnd()
        
               

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

def CheckPoint(function_name,action,*args):
    global SideNotes

    Candy("Title","CheckPoint")
    print("""
   ( (
    ) )
  ........
  |      |]
  \      /
   `----'""")


    if DEBUG is True:
        print("function_name:",function_name)
        print("action:",action)
        for i,a in enumerate(args):
            print("Arg%s:%s type:%s"%(i,a,type(a)))

        pause = input("Check point")

    if function_name == "LibpngCheck":
        if "libpng error:" in action:
            if "bad adaptive filter value" in action:
                SideNotes.append("-CheckPoint: %s"%action)
                SaveErrors("Libpng",["libpng error: bad adaptive filter value"])
            return(LoadClone())
                
        else:
             SideNotes.append("-CheckPoint: No more errors found")
             Candy("Cowsay","Good ! Libpng is happy everything is done here Later then!","good")
             TheEnd()

    if function_name == "FindMagic":
        if action == "Found Magic":
            offset = args[0]
            SideNotes.append("-CheckPoint: Returning next position based on Magic Offset %s"%args[0])
            return(offset)

        if action == "Cutting at Magic":
                Summarise("-File does not start with a png signature.\n-Found a png signature at offset: %s\n-Creating starting with the right signature."%args[1])
                return(SaveClone(args[0]))

        if action == "dig a little bit deeper":
                SideNotes.append("-CheckPoint: Finding Harder Magic Header")
                return(FindFuckingMagic())

    if function_name =="FindFuckingMagic":
        if action == "Cutting at Magic":
                Summarise("-File does not start with a png signature.\n-Found a png signature at offset: %s\n-Creating starting with the right signature."%args[1])
                return(SaveClone(args[0]))

    if function_name == "CheckLength":
       GoodEnding = "0000000049454E44AE426082"
       if action == "No NextChunk":
           if args[0] == 'IEND' and int(args[1]) == 0:
                ToHistory(b'IEND')
                if DATAX[-len(GoodEnding):].upper() == GoodEnding:
                         ChunkStory(b'IEND',"Critical")
                         Candy("Cowsay"," We have reached the end of file.","good")
                         SideNotes.append("-Reached the end of file.")
                         Candy("Cowsay","Ok let's feed the Kraken now..","com")
                         LibpngCheck(Sample)
                         
                else:
                    print(DATAX[-len(GoodEnding):])
                    SaveErrors(args[0],["-Not ending with regular IEND Chunk"])
                    sys.exit(0)
           elif args[0] == 'IEND':
                    SaveErrors(args[0],["-Wrong length for IEND"])
                    sys.exit(0)
           else:
                    
                    SaveErrors(b'IEND',["-IEND Chunk is missing"])
                    sys.exit(0)


       if action == "Found NextChunk":
          SideNotes.append("-CheckPoint: Returning bytes [%s] found at length previously indicated for checking."%args[0])
          return(CheckChunkName(Raw_NextChunk,int(args[1],16),args[0],True))


    if function_name == "Checksum":
       if action == "Wrong Crc":
            SaveErrors(args[3],["-Found Chunk[%s] has Wrong Crc at offset: %s"%(args[3],args[4])],args[0],args[4],args[1],args[2],args[3],args[5])
            return(Question(args[3],False))



    print("Not recognized")
    for i,a in enumerate(args):
        print("Arg%s:%s"%(i,a))	
    sys.exit(0)                          

def main():
    global FirStart
    global FILE_Origin
    global CLEAR
    global PAUSE
    global DEBUG
    global AUTO
    global AnciCheck
    global FILE_DIR
    global DATAX
    global ERRORSFLAG
    global PandoraBox
    global Chunks_History
    global Bytes_History
    global Loading_txt
    global SideNotes
    global Sample
    global Sample_Name
    global Have_A_KitKat

    parser = ArgumentParser()
    parser.add_argument("-f","--file",dest="FILENAME",help="File path.",default=None,metavar="FILE")
    parser.add_argument("-c","--CLEAR",dest="CLEAR",help="CLEAR screen at each saves.",action="store_true")
    parser.add_argument("-p","--pause",dest="PAUSE",help="Pause at each saves.",action="store_true")
    parser.add_argument("-d","--debug",dest="DEBUG",help="Debug stuffs.",action="store_true")
    parser.add_argument("-a","--auto",dest="AUTO",help="Auto Choose action.",action="store_true")
    Args = parser.parse_args()


    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if Args.FILENAME is None:
        print("-f,--filename arguments is missing.")
        sys.exit(1)
    
    FILE_Origin = Args.FILENAME
    CLEAR = Args.CLEAR
    PAUSE = Args.PAUSE
    DEBUG = Args.DEBUG
    AUTO = Args.AUTO
    Sample = FILE_Origin
    while True:

         if CLEAR is True :
            if FirStart is False:
               if os.name == "posix":
                  sys.stdout.write('\033c')
               elif os.name == "nt":
                  os.system("cls")
            else:
                 FirStart = False

         AnciCheck = False
         Chunks_History = []
         Bytes_History = []
         Loading_txt = ""
         ERRORSFLAG = []
         PandoraBox = {}
         SideNotes = []
         Chunklate(1)
         Sample_Name = os.path.basename(Sample)

         print("-Proceeding with: ",Candy("Color","white",Sample_Name))
         try:
           with open(Sample,"rb") as f:
              data = f.read()
         except Exception as e:

             print(Candy("Color","red","Error:"),Candy("Color","yellow",e))
             sys.exit(1)

         DATAX = data.hex()


         Candy("Cowsay"," %s us loaded!"%Candy("Color","green",Sample_Name),"good")
         Offset = FindMagic()
         if Offset != None:

             while Offset < len(DATAX):
             
                 ChunkbyChunk(Offset)
                 
                 CheckLength(Orig_CD,Orig_CL,Orig_CT)

                 CheckChunkName(Orig_CT,Orig_CL,Chunks_History[-1])

                 GetInfo(Orig_CT,Raw_Data)

                 Checksum(Raw_Type,Raw_Data,Raw_Crc)

                 Offset= Offset + len(Raw_Length)+len(Raw_Type)+len(Raw_Data)+len(Raw_Crc)

                 if Have_A_KitKat == True:
                    Have_A_KitKat = False
                    if DEBUG is True:
                       print("have a kitkat was true now false then break")
                       pause = input("pause")
                    break


         #print("Reached End of %s\n"%Sample_Name)
         #ChunkStory(b'IEND',"Critical")
         #TheEnd()
###


###

CHUNKS = [b'sBIT', b'IEND', b'sPLT', b'tRNS', b'fRAc', b'hIST', b'dSIG', b'sTER', b'iCCP', b'sRGB', b'zTXt', b'gAMA', b'IDAT', b'sCAL', b'cHRM', b'bKGD', b'tEXt', b'tIME', b'iTXt', b'IHDR', b'gIFx', b'gIFg', b'oFFs', b'pCAL', b'PLTE', b'gIFt', b'pHYs',b'eXIf']
PRIVATE_CHUNKS = [b'cmOD',b'cmPP',b'cpIp',b'mkBF',b'mkBS',b'mkBT',b'mkTS',b'spAL',b'pcLb',b'prVW',b'JDAT',b'JSEP',b'DHDR',b'FRAM',b'SAVE',b'SEEK',b'nEED',b'DEFI',b'BACK',b'MOVE',b'CLON',b'SHOW',b'CLIP',b'LOOP',b'ENDL',b'PROM',b'fPRI',b'eXPI',b'BASI',b'IPNG',b'PPLT',b'PAST',b'TERM',b'DISC',b'pHYg',b'DROP',b'DBYK',b'ORDR',b'MAGN',b'MEND']
ALLCHUNKS = [b'sBIT', b'IEND', b'sPLT', b'tRNS', b'fRAc', b'hIST', b'dSIG', b'sTER', b'iCCP', b'sRGB', b'zTXt', b'gAMA', b'IDAT',b'sCAL', b'cHRM', b'bKGD', b'tEXt', b'tIME', b'iTXt', b'IHDR', b'gIFx', b'gIFg', b'oFFs', b'pCAL', b'PLTE', b'gIFt', b'pHYs',b'eXIf',b'cmOD',b'cmPP',b'cpIp',b'mkBF',b'mkBS',b'mkBT',b'mkTS',b'spAL',b'pcLb',b'prVW',b'JDAT',b'JSEP',b'DHDR',b'FRAM',b'SAVE',b'SEEK',b'nEED',b'DEFI',b'BACK',b'MOVE',b'CLON',b'SHOW',b'CLIP',b'LOOP',b'ENDL',b'PROM',b'fPRI',b'eXPI',b'BASI',b'IPNG',b'PPLT',b'PAST',b'TERM',b'DISC',b'pHYg',b'DROP',b'DBYK',b'ORDR',b'MAGN',b'MEND']


Chunks_History = []
pCAL_Param=[]
PLTE_R=[]
PLTE_G=[]
PLTE_B=[]
sPLT_Name = []
sPLT_Depht = []
sPLT_Red=[]
sPLT_Green=[]
sPLT_Blue=[]
sPLT_Alpha=[]
sPLT_Freq= []
hIST = []
tEXt_Key_List = []
tEXt_Str_List =[]
iTXt_String_List = []
iTXt_Key_List = []
tRNS_Index=[]
zTXt_Key_List = []
zTXt_Str_List = []
SideNotes = []
ERRORSFLAG = []

PandoraBox = {}
Actions_History = {}

libc = ctypes.CDLL(None)
c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')

FirStart= True
Switch = False
GoBack = False
WORKING = True
MAXCHAR = int(os.get_terminal_size(0)[0])-1
CharPos =1
Have_A_KitKat= False
Warning = False
Summary_Header= True

FILE_Origin = ""
CLEAR = False
PAUSE = False
DEBUG = False
AUTO = False
FILE_DIR = ""
Loading_txt = ""
DATAX = ""
Sample_Name = ""
Sample = ""

Raw_Length=""
Raw_Data=""
Raw_Crc=""
Raw_NextChunk=""
Raw_Type=""
Orig_CL=""
Orig_CT=""
Orig_NC=""
Orig_CD=""
Orig_CRC=""
CLoffX=""
CLoffB=""
CLoffI=""
CToffX=""
CToffB=""
CToffI=""
NCoffX=""
NCoffB=""
NCoffI=""
NCoff_CRC=""
AnciCheck = ""
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

pCAL_Key=""
pCAL_Zero=""
pCAL_Max=""
pCAL_Eq=""
pCAL_PNBR=""

cHRM_WhiteX= ""
cHRM_WhiteY= ""
cHRM_Redx= ""
cHRM_Redy= ""
cHRM_Greenx= ""
cHRM_Greeny= ""
cHRM_Bluex= ""
cHRM_Bluey= ""

gAMA= ""

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

tEXt_Key=""
tEXt_Text=""

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

zTXt_Key=""
zTXt_Meth=""
zTXt_Text=""


if __name__ == "__main__":
    main()
