import sys, os
import random
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter

import metricsMachine

from vanilla import FloatingWindow, Button, TextBox, List, Window
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
from vanilla import *
from mojo.extensions import *
from mojo.extensions import getExtensionDefault, setExtensionDefault
import codecs
import ezui

EXTENSION_KEY = 'com.cjtype.mms2sc.settings'

class MM2SpaceCenter(ezui.WindowController):
    
    '''
    MM2SpaceCenter by CJ Dunn
    2019

    Thanks to Tal Leming, Andy Clymer, David Jonathan Ross, Jackson Cavanaugh, 
    Nina Stössinger for help and inspiration with this script

    To do:       
    - Make sure space center "Show Kerning" is set to on
        - Remember pre-MM2 setting, revert when MM2 closes.
    - Add ability to change word length
    - Rebuild this with EZUI, so more features can be thrown in quickly in the future.
    - Make this window into a temporary preferences UI, where you can set-it-and-forget it.
        - Activate and deactivate from a button in Space Center itself?
        - Save preferences in RF lib.
    '''
    
    def build(self):
        content = """
        * TwoColumnForm @form

        > : Words:
        > [_30               _]            @wordCount
        
        > : Language:
        > (English ...)                    @language

        > : Fallback context:
        > (Auto ...)                       @context
        
        ---------------

        [ ] Output as list sorted by width @listOutput
        [X] Show open+close context {n}    @openCloseContext
        [X] Show mirrored pair (LRLR)      @mirroredPair
        [ ] All uppercase context          @allUppercase
        
        """
        
        self.wordCount = 30
        self.contextOptions = ['Auto', 'UC', 'LC', 'Figs', 'Frac']
        self.languageNames = ['Catalan', 'Czech', 'Danish', 'Dutch', 'English', 'Finnish', 'French', 'German', 'Hungarian', 'Icelandic', 'Italian', 'Latin', 'Norwegian', 'Polish', 'Slovak', 'Spanish', 'Vietnamese syllables']
        descriptionData = dict(
            form=dict(
                titleColumnWidth=104,
                itemColumnWidth=78
            ),
            language=dict(
                    items=self.languageNames
            ),
            context=dict(
                    items=self.contextOptions
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
        self.w = ezui.EZWindow(
            content=content,
            descriptionData=descriptionData,
            controller=self,
            title='MM2SC',
            size="auto"
        )
        
        self.font = CurrentFont()

        try:
            self.pair = metricsMachine.GetCurrentPair() 
        except:
            self.pair = ('A', 'V')
            
        self.loadDictionaries()
        
        self.wordCountField   = self.w.getItem("wordCount")
        self.wordCountField.set(self.wordCount)
        
        self.languageField    = self.w.getItem("language")
        self.languageField.set(4)      #default to English for now
        
        self.context          = self.w.getItem("context")
        self.listOutput       = self.w.getItem("listOutput")
        self.openCloseContext = self.w.getItem("openCloseContext")
        self.mirroredPair     = self.w.getItem("mirroredPair")
        self.allUppercase     = self.w.getItem("allUppercase")

        # register extension defaults
        value = getExtensionDefault(EXTENSION_KEY, fallback=self.w.getItemValues())
        self.w.setItemValues(value)


    def started(self):
        self.w.open()
        addObserver(self, "MMPairChangedObserver", "MetricsMachine.currentPairChanged")

        print('MM2SpaceCenter is now activated.')
        print()
        
        
    def destroy(self):
        setExtensionDefault(EXTENSION_KEY, self.w.getItemValues(), validate=True)
        removeObserver(self, "MetricsMachine.currentPairChanged")

        print('MM2SpaceCenter is now deactivated.')
        print()



    def sortedCallback(self, sender):

        self.sorted = self.listOutput.get()
        self.wordsForMMPair()  
        
        
    def wordCountCallback(self,sender):

        #print ('old', self.wordCount)
        self.wordCount = self.wordCountField.get() or 1
        #update space center
        self.wordsForMMPair()        
        

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


    def changeSourceCallback(self, sender):

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

        
    def changeContextCallback(self, sender):

        """On changing source/wordlist, check if a custom word list should be loaded."""
        
        self.context = self.context = self.contextOptions[self.context.get()]
        
        self.wordsForMMPair()
        if self.debug == True:
            print('Context =', self.context)
            

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


    def MMPairChangedObserver(self, sender):

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

        currentSC = CurrentSpaceCenter()
        if currentSC is None:
            print ('opening space center, click back into kerning window')
            OpenSpaceCenter(font, newWindow=False)
            currentSC = CurrentSpaceCenter()
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

        if self.openCloseContext.get() == True:

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

        if self.mirroredPair.get() == True:
            left, self.leftEncoded = self.checkForUnencodedGname(self.font, pair[0])
            right, self.rightEncoded = self.checkForUnencodedGname(self.font, pair[1])
            return left + right + left + right + " " 
        else:
            return ""


    def wordsForMMPair(self, ):
        
        self.mixedCase = False

        wordsAll = []

        ### temp comment out to check speed
        self.language = self.languageField.get()

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
        
        wordCountValue = int(self.wordCount) 
        
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
            currentSC = CurrentSpaceCenter()
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
        if self.allUppercase.get() == True:
            makeUpper = True

        ###### check All Uppercase setting, and if true set variable makeUpper to True, which makes space center text UC
        if self.allUppercase.get() == True:
            makeUpper = True

        if makeUpper == True:    
            #make text upper again
            ### should we force the pair to stay as is? for example with .uc punctuation if words are found, currently lc punct is shown. Should we find the pair in each work and re-insert the .uc version? 
            textList = list(  text.upper() for text in textList ) 

        if not len(textList) == 0:            
            #see if box is checked
            self.sorted = self.listOutput.get()
        
            #self.sorted = False
            if self.sorted == True:
                sortedText = self.sortWordsByWidth(textList)
            
                textList = sortedText
            
                joinString = "\\n"            
                text = joinString.join([str(word) for word in textList])

                if self.mirroredPair.get() == True:  #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + joinString + text 
                if self.openCloseContext.get() == True: # if "show open+close" is checked, add this to text

                    text = self.openCloseContextReturn(self.pair) + text 

            else:
                text = ' '.join([str(word) for word in textList])
                if self.mirroredPair.get() == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + text
                if self.openCloseContext.get() == True: # if "show open+close" is checked, add this to text

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

                if self.openCloseContext.get() == True: # if "show open+close" is checked, add this to text
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
            
                if self.mirroredPair.get() == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + text 
 
            ## for non uc pair, if not auto, use context dropdown 
            else:
                ## auto will choose lc string
                spacingString = self.lcString(searchString)

                ## non-auto option will use dropdown context
                if self.context != 'Auto':
                    spacingString = self.getSpacingString(searchString)
                                    
                if self.mirroredPair.get() == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + spacingString + previousText
                else:
                    text = spacingString + previousText
                
                if self.mirroredPair.get() == True: #if "start with mirrored pair" is checked, add this to text
                    text = self.pairMirrored(self.pair) + text 
                if self.openCloseContext.get() == True: # if "show open+close" is checked, add this to text

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
                
                
                    if self.mirroredPair.get() == True: #if "start with mirrored pair" is checked, add this to text
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



def run():

    if not len(AllFonts()) > 0:
        print ('You must have a font open.')
        return

    try:
        p = metricsMachine.GetCurrentPair()
        font = metricsMachine.CurrentFont()
        
    except:
        p = ('A', 'V') # set initial value
        font = CurrentFont()

    p = MM2SpaceCenter()    
            

run()
