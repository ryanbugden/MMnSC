import sys
import os
import random
import AppKit
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter
from mojo.subscriber import Subscriber, registerSpaceCenterSubscriber

import metricsMachine

from vanilla import FloatingWindow, Button, TextBox, List, Window
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
from vanilla import Button
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
import codecs
import ezui


EXTENSION_KEY = 'com.cjtype.mms2sc.settings'


def get_setting_from_defaults(setting):
    all_settings = getExtensionDefault(EXTENSION_KEY, fallback={setting:0})
    setting = all_settings[setting]

    return setting


class MM2SCButton(Subscriber):
    
    '''
    Puts the MM2SC pref button in Space Center.
    
    Ryan Bugden
    2023.03.24
    '''
    
    def build(self):
        self.icon_path = os.path.abspath('../resources/_icon_MM2SC.pdf')

        

        self.font = CurrentFont()

        try:
            self.pair = metricsMachine.GetCurrentPair() 
        except:
            self.pair = ('A', 'V')
            
        self.loadDictionaries()

        self.context = get_setting_from_defaults('context')
        self.wordCount = get_setting_from_defaults('wordCount')

        # print(self.icon_path)
        

    def spaceCenterDidOpen(self, info):
        self.sc = info['spaceCenter']
        
        gutter = 10
        b_w = 30
        inset_b = 1
        x, y, w, h = self.sc.top.glyphLineInput.getPosSize()
        b_h = h - inset_b*2
        # print("line is at", x, y, w, h)
        self.sc.top.glyphLineInput.setPosSize((x, y, w - b_w - gutter, h))
        x, y, w, h = self.sc.top.glyphLineInput.getPosSize()
        # print("now resized to", x, y, w, h)
        button_placement = (w + gutter, y + inset_b, b_w, b_h)
        # print('making button', button_placement)
        self.sc.MM2SC_button = Button(
            button_placement, 
            title = 'MM',
            # imageNamed=AppKit.NSImageNameMultipleDocuments,
            # imagePath = self.icon_path,  # For image buttons only
            callback = self.buttonCallback, 
            sizeStyle = 'small'
            )
        self.sc.MM2SC_button.getNSButton().setBordered_(0)
        self.sc.MM2SC_button.getNSButton().setBezelStyle_(2)

        self.activateModule()


    def spaceCenterWillClose(self, info):
        self.deactivateModule()
        

    def buttonCallback(self, sender):
        # run the prefs window
        if not len(AllFonts()) > 0:
            print ('You must have a font open.')
            return

        try:
            p = metricsMachine.GetCurrentPair()
            font = metricsMachine.CurrentFont()
        
        except:
            p = ('A', 'V') # set initial value
            font = CurrentFont()
        
        if font.path:
            p = MM2SpaceCenterPopover(self.sc.MM2SC_button, self.sc)    
        else:
            print("Save your font (give it a path) before trying to open MM2SC.")


    def activateModule(self):
        # Make sure Show Kerning is on in the Space Center
        lv = self.sc.glyphLineView
        v = lv.getApplyKerning()
        if v == False:
            lv.setApplyKerning(True)

        addObserver(self, "MMPairChanged", "MetricsMachine.currentPairChanged")
        print('MM observer is now activated.')
        
        
    def deactivateModule(self):

        removeObserver(self, "MetricsMachine.currentPairChanged")
        print('MM observer is deactivated.')


    def loadDictionaries(self):

        """Load the available wordlists and read their contents."""
        self.dictWords = {}
        self.allWords = []
        self.outputWords = []

        self.textfiles = ['catalan', 'czech', 'danish', 'dutch', 'ukacd', 'finnish', 'french', 'german', 'hungarian', 'icelandic', 'italian', 'latin', 'norwegian', 'polish', 'slovak', 'spanish', 'vietnamese']
        self.languageNames = ['Catalan', 'Czech', 'Danish', 'Dutch', 'English', 'Finnish', 'French', 'German', 'Hungarian', 'Icelandic', 'Italian', 'Latin', 'Norwegian', 'Polish', 'Slovak', 'Spanish', 'Vietnamese syllables']

        bundle = ExtensionBundle("MM2SpaceCenter")
        contentLimit  = '*****' # If word list file contains a header, start looking for content after this delimiter

        # read included textfiles
        for textfile in self.textfiles:
            path = bundle.getResourceFilePath(textfile)
            #print (path)
            with codecs.open(path, mode="r", encoding="utf-8") as fo:
                lines = fo.read()

            self.dictWords[textfile] = lines.splitlines() # this assumes no whitespace has to be stripped

            # strip header
            try:
                contentStart = self.dictWords[textfile].index(contentLimit) + 1
                self.dictWords[textfile] = self.dictWords[textfile][contentStart:]
            except ValueError:
                pass

        # read user dictionary
        with open('/usr/share/dict/words', 'r') as userFile:
            lines = userFile.read()
        self.dictWords["user"] = lines.splitlines()

            

    def sortWordsByWidth(self, wordlist):

        '''
        Sort output word list by width.
        '''

        f = self.font
        wordWidths = []

        for word in wordlist:
            unitCount = 0
            for char in word:
                try:
                    glyphWidth = f[char].width
                except:
                    try:
                        gname = self.glyphNamesForValues[char]
                        glyphWidth = f[gname].width
                    except:
                        glyphWidth = 0
                unitCount += glyphWidth
            # add kerning
            for i in range(len(word)-1):
                pair = list(word[i:i+2])
                unitCount += int(self.findKerning(pair))
            wordWidths.append(unitCount)

        wordWidths_sorted, wordlist_sorted = zip(*sorted(zip(wordWidths, wordlist))) # thanks, stackoverflow
        return wordlist_sorted


    def findKerning(self, chars):

        '''
        Helper function to find kerning between two given glyphs.
        This assumes MetricsMachine style group names.
        '''

        markers = ["@MMK_L_", "@MMK_R_"]
        keys = [c for c in chars]

        for i in range(2):
            allGroups = self.font.groups.findGlyph(chars[i])
            if len(allGroups) > 0:
                for g in allGroups:
                    if markers[i] in g:
                        keys[i] = g
                        continue

        key = (keys[0], keys[1])
        if self.font.kerning.has_key(key):
            return self.font.kerning[key]
        else:
            return 0


    def MMPairChanged(self, sender):

        # print("get_setting_from_defaults('mirroredPair')", get_setting_from_defaults('mirroredPair'))
        # not sure this is doing anything
        if get_setting_from_defaults('activateToggle') == True:

            #add code here for when myObserver is triggered
            currentPair = sender["pair"]
            if currentPair == self.pair:
                return
            
            self.pair = currentPair
        
            #print ('current MM pair changed', self.pair)        
            self.wordsForMMPair()


    ## same as MM Pair Changed Observer above, but making a separate function just to be safe
    def FPPairChangedObserver(self, sender):

        #add code here for when myObserver is triggered
        currentPair = sender["pair"]
        if currentPair == self.pair:
            return
        
        self.pair = currentPair
    
        #print ('current FP pair changed', self.pair)        
        self.wordsForMMPair()


    def setSpaceCenter(self, font, text):    

        currentSC = self.sc
        if currentSC is None:
            print ('opening space center, click back into kerning window')
            OpenSpaceCenter(font, newWindow=False)
            currentSC = self.sc
        currentSC.setRaw(text)

    
    def randomly(self, seq):

        shuffled = list(seq)
        random.shuffle(shuffled)
        return iter(shuffled)


    def gname2char(self, f, gname):

        uni = f[gname].unicodes[0]
        char = chr(uni)
        return char

    def spaceCenterStringForUnencoded(self, gname):
        
        scString = '/'+gname+' '
        return scString 


    def checkForUnencodedGname(self, font, gname):

        glyphIsEncoded = False
        
        escapeList = ['slash', 'backslash']
        
        if (not font[gname].unicodes) or (gname in escapeList):
            scString = self.spaceCenterStringForUnencoded(gname)
            
        else: 
            scString = self.gname2char(font, gname)
            glyphIsEncoded = True
            
        return(scString, glyphIsEncoded)


    def getPairstring(self, pair):

        left, self.leftEncoded = self.checkForUnencodedGname(self.font, pair[0])
        right, self.rightEncoded = self.checkForUnencodedGname(self.font, pair[1])
            
        pairstring = left+right
            
        return pairstring


    def pair2char(self, pair):

        '''
        Convert char gnames to chars to find words in dict.
        '''
        
        self.debug = False
        
        try:
            #print ('pair =', pair)

            leftNoSuffix = pair[0]
            rightNoSuffix = pair[1]

            leftPeriodPos = pair[0].find(".")
            if leftPeriodPos > 0:
                leftNoSuffix = pair[0][:leftPeriodPos]

            rightPeriodPos = pair[1].find(".")
            if rightPeriodPos > 0:
                rightNoSuffix = pair[1][:rightPeriodPos]

            left = self.gname2char(CurrentFont(), leftNoSuffix)
            right = self.gname2char(CurrentFont(), rightNoSuffix)
            pair_char = (left, right)
            return pair_char
        except:
            if self.debug == True:
                print ("couldn't convert pair to chars")            
            return pair
        

    def lcString(self, pairstring):

        string = 'non'+pairstring+'nono'+pairstring+'oo' #lc

        return string
            

    def getSpacingString(self, pairstring):

        string = 'non'+pairstring+'nono'+pairstring+'oo' #lc
        
        if self.context == 'Auto':
            string = 'non'+pairstring+'nono'+pairstring+'oo' #lc

        if self.context == 'UC':
            string = 'HH'+pairstring+'HOHO'+pairstring+'OO'

        if self.context == 'LC':
            string = 'non'+pairstring+'nono'+pairstring+'oo' #lc
        
        if self.context == 'Figs':
            string = '11'+pairstring+'1010'+pairstring+'00' #use for numbers

        if self.context == 'Frac': 
            # start with figs context
            string = '11'+pairstring+'⁄1010⁄'+pairstring+'00' #use for numbers

            #look for fraction at start of pair
            if pairstring.startswith('⁄'): ##fraction unicode glyph, not slash
                string = '11/eight.numr '+pairstring+' 10/one.numr '+pairstring+'00'
                #print('starts')

            #look for fraction at end of pair    
            if pairstring.endswith('⁄'): ##fraction unicode glyph, not slash
                string = '11'+pairstring+'/eight.dnom 10'+pairstring+'/eight.dnom 00'
                #print('ends')

        return string


    def ucString(self, pairstring):
        string = 'HH'+pairstring+'HOHO'+pairstring+'OO'
        return string


    openClosePairs = {

        # initial/final punctuation (from https://www.compart.com/en/unicode/category/Pi and https://www.compart.com/en/unicode/category/Pf)
        "‚": "‘",
        "„": "“",
        "„": "”",
        "‘": "’",
        "‛": "’",
        "“": "”",
        "‟": "”",
        "‹": "›",
        "›": "‹",
        "«": "»",
        "»": "«",
        "⸂": "⸃",
        "⸄": "⸅",
        "⸉": "⸊",
        "⸌": "⸍",
        "⸜": "⸝",
        "⸠": "⸡",
        #"”": "”",  ##these will make two contexts show up for quotes so leaving them off for now
        #"’": "’",

        # Miscellaneous but common open/close pairs
        "'": "'",
        '"': '"',
        "¡": "!",
        "¿": "?",
        "←": "→",
        "→": "←",
        "/": "\\",
        
        "<": ">", #less, greater
        ">": "<", #greater, less

        # opening/closing punctuation (from https://www.compart.com/en/unicode/category/Ps & https://www.compart.com/en/unicode/category/Pe)
        "(": ")",
        "[": "]",
        "{": "}",
        "༺": "༻", "༼": "༽", "᚛": "᚜", "‚": "‘", "„": "“", "⁅": "⁆", "⁽": "⁾", "₍": "₎", "⌈": "⌉", "⌊": "⌋", "〈": "〉", "❨": "❩", "❪": "❫", "❬": "❭", "❮": "❯", "❰": "❱", "❲": "❳", "❴": "❵", "⟅": "⟆", "⟦": "⟧", "⟨": "⟩", "⟪": "⟫", "⟬": "⟭", "⟮": "⟯", "⦃": "⦄", "⦅": "⦆", "⦇": "⦈", "⦉": "⦊", "⦋": "⦌", "⦍": "⦎", "⦏": "⦐", "⦑": "⦒", "⦓": "⦔", "⦕": "⦖", "⦗": "⦘", "⧘": "⧙", "⧚": "⧛", "⧼": "⧽", "⸢": "⸣", "⸤": "⸥", "⸦": "⸧", "⸨": "⸩", "〈": "〉", "《": "》", "「": "」", "『": "』", "【": "】", "〔": "〕", "〖": "〗", "〘": "〙", "〚": "〛", "〝": "〞", "⹂": "〟", "﴿": "﴾", "︗": "︘", "︵": "︶", "︷": "︸", "︹": "︺", "︻": "︼", "︽": "︾", "︿": "﹀", "﹁": "﹂", "﹃": "﹄", "﹇": "﹈", "﹙": "﹚", "﹛": "﹜", "﹝": "﹞", "（": "）", "［": "］", "｛": "｝", "｟": "｠", "｢": "｣", 
   
   
   
    }

    openCloseUnencodedPairs = {
        "parenleft.uc": "parenright.uc", 
        "bracketleft.uc": "bracketright.uc", 
        "braceleft.uc": "braceright.uc", 
        "exclamdown.uc": "exclam.uc", 
        "questiondown.uc": "question.uc", 
        "guilsinglleft.uc": "guilsinglright.uc",
        "guillemotleft.uc": "guillemotright.uc",

        "guilsinglright.uc": "guilsinglleft.uc",
        "guillemotright.uc": "guillemotleft.uc",

        "slash": "backslash", #should be encoded but adding here because those aren't working for some reason
        "backslash": "slash", #should be encoded but adding here because those aren't working for some reason
    }

    def openCloseContextReturn(self, pair):

        if get_setting_from_defaults('openCloseContext') == True:

            # get unicodes to make sure we don’t show pairs that don’t exist in the font
            # TODO? may be better to move outside this function, if running it each time is slow. BUT it would have to listen for the CurrentFont to change.
            unicodesInFont = [u for glyph in CurrentFont() for u in glyph.unicodes]

            left, self.leftEncoded = self.checkForUnencodedGname(self.font, pair[0])
            right, self.rightEncoded = self.checkForUnencodedGname(self.font, pair[1])
            
            
            #print ('left:', left, self.leftEncoded)
            #print ('right:', right, self.rightEncoded)
            

            openCloseString = ""

            for openClose in self.openClosePairs.items():
                
                #print (openClose[0], left, len(openClose[0]), len(left))                    
                
                # if left == openClose[0]:
                # #if left in openClose[0]:
                #     print ('left found', left)   
                # if right == openClose[1]:
                #     print ('right found', left)   
                
                # if both sides of pair are in an open+close pair, just add them
                if openClose[0] == left and openClose[1] == right:
                    openCloseString += left + right + "" #remove trailing space
                # if the left is in an openClose pair and its companion is in the font, add them
                if openClose[0] == left and ord(openClose[1]) in unicodesInFont:
                    openCloseString += left + right + self.openClosePairs[left] + "" #remove trailing space
                # if the right is in an openClose pair and its companion is in the font, add them
                if openClose[1] == right  and ord(openClose[0]) in unicodesInFont:
                    openCloseString += openClose[0] + left + right + "" #remove trailing space
                    
                    print ('right matches', right, openCloseString)
                
                else:
                    continue
            
  
            if (self.leftEncoded == False) or (self.rightEncoded == False):
                for openCloseGnames in self.openCloseUnencodedPairs.items():

                    #left
                    
                    openCloseLeft = openCloseGnames[0]

                    openCloseRight = openCloseGnames[1]

                    #spaceCenterStringForUnencoded
                    if self.pair[0] == openCloseLeft:
                        #print ('left unencoded pair found' )
                        openCloseString += left + right + self.spaceCenterStringForUnencoded(openCloseRight) + " "
                    
                    #right 
                    if self.pair[1] == openCloseRight:
                        #print ( 'right unencoded pair found' )  
                                              
                        openCloseString += self.spaceCenterStringForUnencoded(openCloseLeft) + left + right  + " "

            return openCloseString
            
        else:
            return ""


    # make mirrored pair to judge symmetry of kerns
    def pairMirrored(self, pair):

        if get_setting_from_defaults('mirroredPair') == True:
            left, self.leftEncoded = self.checkForUnencodedGname(self.font, pair[0])
            right, self.rightEncoded = self.checkForUnencodedGname(self.font, pair[1])
            return left + right + left + right + " " 
        else:
            return ""


    def wordsForMMPair(self, ):
        
        self.mixedCase = False

        wordsAll = []

        ### temp comment out to check speed
        self.language = get_setting_from_defaults('language')

        languageCount = len(self.textfiles)
        if self.language == languageCount: # Use all languages
            for i in range(languageCount):
                # if any language: concatenate all the wordlists
                wordsAll.extend(self.dictWords[self.textfiles[i]])
        else:
            wordsAll = self.dictWords[self.textfiles[self.language]]
        
        #default values are hard coded for now
        #self.wordCount = self.getIntegerValue(self.wordCount)

        #v = self.getIntegerValue(self.wordCount)
        
        wordCountValue = int(get_setting_from_defaults('wordCount')) 
        
        #print(v)

        #print ('self.wordCount', self.wordCount)
        
        #currently allows any word lenght, this could be customized later

        text = ''
        textList = []

        # try getting pairstring once in order to check if encoded
        pairstring = self.getPairstring(self.pair)

        #convert MM tuple into search pair to check uc, lc, mixed case. Maybe need a different var name here? 
        pair2charString = ''.join(self.pair2char(self.pair))

        # search for non-suffixed
        searchString = ""
        for g_name in self.pair:
            no_suff = g_name.split(".")[0]
            rep = chr(self.font[no_suff].unicode)
            searchString += rep

        #check Encoding
        
        #print (pairstring)

        #default value
        makeUpper = False

        if pair2charString.isupper():
            #print (pairstring, 'upper')
            makeUpper = True
            #make lower for searching
            searchString = searchString.lower()

        else:
            #print(pairstring, 'not upper')
            makeUpper = False
            searchString = searchString
            pass

        #check for mixed case
        if self.pair2char(self.pair)[0].isupper():
            if self.pair2char(self.pair)[1].islower():
                if (self.leftEncoded == True) and (self.rightEncoded == True) : 
                    self.mixedCase = True
    
        try:
            currentSC = self.sc
            previousText = currentSC.getRaw()
        except:
            previousText = ''
            pass

        count = 0 
        
        #self.usePhrases = False 
        
        # more results for mixed case if we include lc words and capitalize
        if self.mixedCase == True:
            for word in self.randomly(wordsAll):

                # first look for words that are already mixed case
                if searchString in word:              
                    #avoid duplicates
                    if not word in textList:
                
                        #print (word)
                        textList.append(word)
                        count +=1
                        
                #then try capitalizing lowercase words
                if (searchString.lower() in word[:2]):
                    word = word.capitalize()               
                    #avoid duplicates
                    if not word in textList:
                
                        #print (word)
                        textList.append(word)
                        count +=1
        
                #stop when you get enough results
                if count >= wordCountValue:
                    #print (text)
                
                    break
                    
            pass            
        
        else:
            for word in self.randomly(wordsAll):
                if searchString in word:
                
                    #avoid duplicates
                    if not word in textList:
                
                        #print (word)
                        textList.append(word)
                        count +=1
        
                #stop when you get enough results
                if count >= wordCountValue:
                    #print (text)
                
                    break
        
        ###### check All Uppercase setting, and if true set variable makeUpper to True, which makes space center text UC
        if get_setting_from_defaults('allUppercase') == True:
            makeUpper = True

        ###### check All Uppercase setting, and if true set variable makeUpper to True, which makes space center text UC
        if get_setting_from_defaults('allUppercase') == True:
            makeUpper = True

        if makeUpper == True:    
            #make text upper again
            ### should we force the pair to stay as is? for example with .uc punctuation if words are found, currently lc punct is shown. Should we find the pair in each work and re-insert the .uc version? 
            textList = list(  text.upper() for text in textList ) 

        if not len(textList) == 0:            
            #see if box is checked
            self.sorted = get_setting_from_defaults('listOutput')
        
            #self.sorted = False
            if self.sorted == True:
                sortedText = self.sortWordsByWidth(textList)
            
                textList = sortedText
            
                joinString = "\\n"            
                text = joinString.join([str(word) for word in textList])

                if get_setting_from_defaults('mirroredPair') == True:  #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + joinString + text 
                if get_setting_from_defaults('openCloseContext') == True: # if "show open+close" is checked, add this to text

                    text = self.openCloseContextReturn(self.pair) + text 

            else:
                text = ' '.join([str(word) for word in textList])
                if get_setting_from_defaults('mirroredPair') == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + text
                if get_setting_from_defaults('openCloseContext') == True: # if "show open+close" is checked, add this to text

                    text = self.openCloseContextReturn(self.pair) + text 


        # if no words are found, show spacing string and previous text
        if len(text) == 0:
            #do i need to get pairstring again or can I used the previous one? 
            #pairstring = self.getPairstring(self.pair)
            previousText = '\\n no words for pair ' + pairstring
                            
            #print(len(pairstring)) ## debugging

            if makeUpper == True:
                
                text = self.ucString(pairstring)+ previousText


                if self.context != 'Auto':
                    text = self.getSpacingString(pairstring)+ previousText

                if get_setting_from_defaults('openCloseContext') == True: # if "show open+close" is checked, add this to text
                    openClosePair = self.openCloseContextReturn( self.pair)  
                
                    ### debug start 2
                    #print ('openClosePair:'+openClosePair+'#')
                    openClosePair= openClosePair.lstrip()
                
                    #print ('openClosePair:'+openClosePair+'#')
                    ### debug end 2
                
                    if len(openClosePair) > 0 : ## pair found                 
                        spacingString = self.ucString( openClosePair )

                    else: ## pair not found
                    
                        if self.debug == True:
                            print ('open+close pair not found')
                        spacingString = self.ucString( pairstring )
                
                
                    ## for uc pair, if not auto, use context dropdown 
                    if self.context != 'Auto':
                        
                        spacingString = self.getSpacingString(pairstring)

                    spacingString = spacingString.replace("  ", " ") ## extra space gets added, later maybe it's best to change self.ucString function??
                    spacingString = spacingString.replace("  ", " ") ## do again to catch double spaces 

                    text = spacingString + previousText
            
                if get_setting_from_defaults('mirroredPair') == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + text 
 
            ## for non uc pair, if not auto, use context dropdown 
            else:
                ## auto will choose lc string
                spacingString = self.lcString(searchString)

                ## non-auto option will use dropdown context
                if self.context != 'Auto':
                    spacingString = self.getSpacingString(searchString)
                                    
                if get_setting_from_defaults('mirroredPair') == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + spacingString + previousText
                else:
                    text = spacingString + previousText
                
                if get_setting_from_defaults('mirroredPair') == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + text 
                if get_setting_from_defaults('openCloseContext') == True: # if "show open+close" is checked, add this to text

                    text = self.openCloseContextReturn(self.pair) + text 

                    openClosePair = self.openCloseContextReturn( self.pair) 
                
                    ### debug start
                    #print ('openClosePair:'+openClosePair+'#')
                    #print ('pair:'+str(self.pair)+'#')
                    #openClosePair= openClosePair.lstrip()
                    #print ('openClosePair:'+openClosePair+'#')
                    ### debug end

                    openClosePair = openClosePair.replace("  ", " ") ## extra space gets added, later maybe it's best to change self.ucString function??
                    openClosePair = openClosePair.replace("  ", " ") ## do again to catch double spaces 
                
                    if len(openClosePair) > 0 : ## pair found 
                                  
                        spacingString = self.lcString( openClosePair )
                    
                    else:
                        if self.debug == True:
                            print ('open+close pair not found')
                    
                        spacingString = self.lcString( pairstring )
                    
                    spacingString = spacingString.replace("  ", " ")                    
                    # spacingString = spacingString.replace("  ", " ") ## do again to catch double spaces 
                
                
                    if get_setting_from_defaults('mirroredPair') == True: #if "start with mirrored pair" is checked, add this to text
                        text = self.pairMirrored(self.pair) + spacingString + previousText
                    else:
                        text = spacingString + previousText   

            text = text.lstrip() #remove whitespace  
            self.setSpaceCenter(self.font, text)

        ## Success! words are found : )
        else:
            #set space center if words are found
            #not sure why there's always a /slash in from of the first word, added ' '+ to avoid losing the first word
        
            text = text.lstrip() #remove whitespace    

            # replace normalised search pair with original suffixed pair
            text = text.replace(pair2charString, '/'+'/'.join(self.pair)+' ' )                        

            self.setSpaceCenter(self.font, text)





class MM2SpaceCenterPopover(ezui.WindowController):
    
    '''
    MM2SpaceCenter by CJ Dunn
    2019

    Thanks to Tal Leming, Andy Clymer, David Jonathan Ross, Jackson Cavanaugh, 
    Nina Stössinger for help and inspiration with this script


    Ryan Bugden edit
    2023.03.24
    
    To do:       
    - Remember pre-MM2 "Show Kerning" setting, revert when MM2 closes?
    - Add ability to change word length
    - Handle multiple SCs at once. Need subscriber?
    '''

    
    def build(self, parent, space_center):

        self.sc = space_center

        content = """
        [ ] Activate MM2SC                 @activateToggle
        
        ---------------
        
        * TwoColumnForm @form

        > : Word count:
        > [_30               _]            @wordCount
        
        > : Language:
        > (English ...)                    @language

        > : Fallback context:
        > (Auto ...)                       @context
        
        ---------------

        [ ] Output as list sorted by width @listOutput
        [X] Show open & close context {n}  @openCloseContext
        [X] Show mirrored pair (LRLR)      @mirroredPair
        [ ] Make context all-caps          @allUppercase
        
        """
        
        initialWordCount = 30
        contextOptions = ['Auto', 'UC', 'LC', 'Figs', 'Frac']
        self.context = 'Auto'
        languageNames = ['Catalan', 'Czech', 'Danish', 'Dutch', 'English', 'Finnish', 'French', 'German', 'Hungarian', 'Icelandic', 'Italian', 'Latin', 'Norwegian', 'Polish', 'Slovak', 'Spanish', 'Vietnamese syllables']

        descriptionData = dict(
            form=dict(
                titleColumnWidth=104,
                itemColumnWidth=78
            ),
            language=dict(
                    items=languageNames
            ),
            context=dict(
                    items=contextOptions
            ),
            listOutput=dict(
                    sizeStyle='small'
            ),
            openCloseContext=dict(
                    sizeStyle='small'
            ),
            mirroredPair=dict(
                    sizeStyle='small'
            ),
            allUppercase=dict(
                    sizeStyle='small'
            ),
        )
        self.w = ezui.EZPopover(
            content=content,
            descriptionData=descriptionData,
            controller=self,
            parent=parent,
            parentAlignment='bottom',
            size="auto"
        )
        

        self.activateToggle   = self.w.getItem("activateToggle")
        self.wordCountField   = self.w.getItem("wordCount")
        self.wordCountField.set(initialWordCount)
        self.languageField    = self.w.getItem("language")
        self.contextField     = self.w.getItem("context")
        self.listOutput       = self.w.getItem("listOutput")
        self.openCloseContext = self.w.getItem("openCloseContext")
        self.mirroredPair     = self.w.getItem("mirroredPair")
        self.allUppercase     = self.w.getItem("allUppercase")

        # register extension defaults
        # print("1", getExtensionDefault(EXTENSION_KEY, fallback={}), self.w.getItemValues())

        # if this sc is int he prefs, set to extension defaults. If not, it should just start as default...
    

    
    def flush_and_register_defaults(self):
        setExtensionDefault(EXTENSION_KEY, {})  # This might not be necessary anymore.
        setExtensionDefault(EXTENSION_KEY, self.w.getItemValues(), validate=True)
        print(getExtensionDefault(EXTENSION_KEY))


    def started(self):
        self.w.open()

        values = getExtensionDefault(EXTENSION_KEY, fallback=self.w.getItemValues())
        self.w.setItemValues(values)

        
    def activateToggleCallback(self, sender):
        activation = sender.get()
        print(activation)
        
        # can no longer do observer stuff from the pref menu object
        if activation == True:
            print(f'MM2SpaceCenter is now activated.')
        else:
            print(f'MM2SpaceCenter is now deactivated.')

        self.flush_and_register_defaults()
        
        
    def sortedCallback(self, sender):

        self.sorted = get_setting_from_defaults('listOutput')
        self.wordsForMMPair()  
        
        

    def wordCountCallback(self,sender):

        #print ('old', self.wordCount)
        self.wordCount = get_setting_from_defaults('wordCount')

        self.flush_and_register_defaults()      


    
    def languageCallback(self,sender):
        self.flush_and_register_defaults()  
        """On changing source/wordlist, check if a custom word list should be loaded."""
        customIndex = len(self.textfiles) + 2
        if sender.get() == customIndex: # Custom word list
            try:
                filePath = getFile(title="Load custom word list", messageText="Select a text file with words on separate lines", fileTypes=["txt"])[0]
            except TypeError:
                filePath = None
                self.customWords = []
                print("Input of custom word list canceled, using default")
            if filePath is not None:
                with codecs.open(filePath, mode="r", encoding="utf-8") as fo:
                    lines = fo.read()

                self.customWords = []
                for line in lines.splitlines():
                    w = line.strip() # strip whitespace from beginning/end
                    self.customWords.append(w)
        
        # update space center
        self.wordsForMMPair()



    def contextCallback(self,sender):
        # print("3", getExtensionDefault(EXTENSION_KEY, fallback={}), self.w.getItemValues())
        self.flush_and_register_defaults()  
        """On changing source/wordlist, check if a custom word list should be loaded."""
        
        self.context = self.contextOptions[get_setting_from_defaults('context')]
        
        self.wordsForMMPair()
        if self.debug == True:
            print('Context =', self.context)


    def listOutputCallback(self,sender):
        # print("4", getExtensionDefault(EXTENSION_KEY, fallback={}), self.w.getItemValues())
        self.flush_and_register_defaults()  
    def openCloseContextCallback(self,sender):
        # print("5", getExtensionDefault(EXTENSION_KEY, fallback={}), self.w.getItemValues())
        self.flush_and_register_defaults()  
    def mirroredPairCallback(self,sender):
        self.flush_and_register_defaults()  
    def allUppercaseCallback(self,sender):
        self.flush_and_register_defaults()  
        

    

registerSpaceCenterSubscriber(MM2SCButton)