import sys
import os
import random
import AppKit
from mojo.UI import CurrentSpaceCenter, OpenSpaceCenter
from mojo.subscriber import Subscriber, registerSpaceCenterSubscriber
from lib.tools.unicodeTools import GN2UV

import metricsMachine

from vanilla import FloatingWindow, Button, TextBox, List, Window
from defconAppKit.windows.baseWindow import BaseWindowController
from mojo.events import addObserver, removeObserver
from vanilla import Button
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
import codecs
import ezui
import re

'''
MM2SpaceCenter by CJ Dunn
2019

Thanks to Tal Leming, Andy Clymer, David Jonathan Ross, Jackson Cavanaugh, 
Nina Stössinger for help and inspiration with this script

To do:       
- Remember pre-MM2 "Show Kerning" setting, revert when MM2 closes?
- Add ability to change word length
- Handle multiple SCs at once. Need subscriber?
- If no words, look for next member of the kern group. (Some way of showing/saying this has been done, though?)
- Underline the pair in Space Center. Add pref
- Handle suffixes, for open/close for instance (.cap, etc.)
- Make spacing string such that you can compare open/close around a control glyph, next to current pair
'''



EXTENSION_KEY = 'com.cjtype.mms2sc.settings'


def get_setting_from_defaults(setting):
    all_settings = getExtensionDefault(EXTENSION_KEY, fallback={setting:0})
    setting = all_settings[setting]

    return setting

def get_key(my_dict, val):
    for key, value in my_dict.items():
        if val == value:
            return key


class MM2SC_Tool(Subscriber):
    '''
    Carries forward all of the MM2SC utilities.
    '''
    
    def build(self):
        self.icon_path = os.path.abspath('../resources/_icon_MM2SC.pdf')  # Image icon to potentially be used on the SC button
        self.font = CurrentFont()

        try:
            self.pair = metricsMachine.GetCurrentPair() 
        except:
            self.pair = ('A', 'V')
            
        self.load_dictionaries()
        self.word_count = get_setting_from_defaults('wordCount')
        

    def spaceCenterDidOpen(self, info):
        '''
        Puts the MM2SC pref button in Space Center,
        and activates the MM observer. 
        '''

        self.sc = info['spaceCenter']
        gutter = 10
        b_w = 30
        inset_b = 1

        x, y, w, h = self.sc.top.glyphLineInput.getPosSize()
        b_h = h - inset_b * 2

        # Resize glyph line input
        self.sc.top.glyphLineInput.setPosSize((x, y, w - b_w - gutter, h))
        x, y, w, h = self.sc.top.glyphLineInput.getPosSize()

        # Create MM2SC button
        button_placement = (w + gutter, y + inset_b, b_w, b_h)
        self.sc.MM2SC_button = Button(
            button_placement, 
            title='MM',
            callback=self.button_callback, 
            sizeStyle='small'
            )
        self.sc.MM2SC_button.getNSButton().setBordered_(0)
        self.sc.MM2SC_button.getNSButton().setBezelStyle_(2)

        self.activate_module()


    def spaceCenterWillClose(self, info):
        self.deactivate_module()
        

    def button_callback(self, sender):
        '''
        Opens the prefs window.
        '''

        if len(AllFonts()) == 0:  # In case this is somehow possible despite having a Space Center open...
            print('You must have a font open.')
            return

        MM2SpaceCenterPopover(self.sc.MM2SC_button, self.sc)


    def activate_module(self):
        addObserver(self, 'MM_pair_changed', 'MetricsMachine.currentPairChanged')
        print('MM2SC observer is now activated.')
        
        
    def deactivate_module(self):
        removeObserver(self, 'MetricsMachine.currentPairChanged')
        print('MM2SC observer is deactivated.')


    def load_dictionaries(self):
        '''
        Loads the available wordlists and reads their contents.
        '''

        self.dict_words = {}
        self.text_files = ['catalan', 'czech', 'danish', 'dutch', 'ukacd', 'finnish', 'french', 'german', 'hungarian', 'icelandic', 'italian', 'latin', 'norwegian', 'polish', 'slovak', 'spanish', 'vietnamese']
        self.language_names = ['Catalan', 'Czech', 'Danish', 'Dutch', 'English', 'Finnish', 'French', 'German', 'Hungarian', 'Icelandic', 'Italian', 'Latin', 'Norwegian', 'Polish', 'Slovak', 'Spanish', 'Vietnamese syllables']

        # # Check if a custom word-list should be loaded. (Defunct)
        # custom_index = len(self.text_files) + 2
        # if sender.get() == custom_index: # Custom word list
        #     try:
        #         file_path = getFile(title='Load custom word list', messageText='Select a text file with words on separate lines', fileTypes=['txt'])[0]
        #     except TypeError:
        #         file_path = None
        #         self.custom_words = []
        #         print('Input of custom word list canceled, using default')
        #     if file_path is not None:
        #         with codecs.open(file_path, mode='r', encoding='utf-8') as fo:
        #             lines = fo.read()

        #         self.custom_words = []
        #         for line in lines.splitlines():
        #             w = line.strip() # strip whitespace from beginning/end
        #             self.custom_words.append(w)

        bundle = ExtensionBundle('MM2SpaceCenter')
        content_limit  = '*****'  # If word list file contains a header, start looking for content after this delimiter

        # Read included text files
        for text_file in self.text_files:
            path = bundle.getResourceFilePath(text_file)
            with codecs.open(path, mode='r', encoding='utf-8') as fo:
                lines = fo.read()
            self.dict_words[text_file] = lines.splitlines()  # This assumes no whitespace has to be stripped

            # Strip header
            try:
                content_start = self.dict_words[text_file].index(content_limit) + 1
                self.dict_words[text_file] = self.dict_words[text_file][content_start:]
            except ValueError:
                pass

        # Read user dictionary
        with open('/usr/share/dict/words', 'r') as userFile:
            lines = userFile.read()
        self.dict_words['user'] = lines.splitlines()

            
    def sort_words_by_width(self, word_list):
        '''
        Sorts the list of words by width.
        '''
        def find_kerning(chars):
            '''
            Helper function to find kerning between two given glyphs.
            This assumes MetricsMachine style group names.
            '''
            markers = ['@MMK_L_', '@MMK_R_']
            keys = [c for c in chars]
            for i in range(2):
                all_groups = self.font.groups.findGlyph(chars[i])
                if len(all_groups) > 0:
                    for g in all_groups:
                        if markers[i] in g:
                            keys[i] = g
                            continue
            key = (keys[0], keys[1])
            if self.font.kerning.has_key(key):
                return self.font.kerning[key]
            else:
                return 0

        f = self.font
        word_widths = []
        for word in word_list:
            unit_count = 0
            for char in word:
                glyph = None
                try:
                    glyph = f[char]
                except KeyError:
                    gname = self.get_gname_from_char(char)
                    if gname:
                        glyph = f[gname]
                if glyph:
                    unit_count += glyph.width
            # Add kerning
            for i in range(len(word) - 1):
                pair = word[i:i + 2]
                unit_count += int(find_kerning(pair))
            word_widths.append((word, unit_count))

        word_widths_sorted = sorted(word_widths, key=lambda x: x[1])

        return [word for word, width in word_widths_sorted]


    def MM_pair_changed(self, sender):
        if get_setting_from_defaults('activateToggle') == True:
            current_pair = sender['pair']
            if current_pair != self.pair:
                self.pair = current_pair
                self.font = metricsMachine.CurrentFont()
                self.words_for_pair()


    def set_space_center(self, font, text):    
        try:
            self.sc.setRaw(text)
            # Make sure 'Show Kerning' is on in the Space Center
            if not self.sc.glyphLineView.getApplyKerning():
                lv.setApplyKerning(True)
        except AttributeError:
            print('Opening Space Center. Go back to MetricsMachine.')
            OpenSpaceCenter(font, newWindow=False)
            self.sc = CurrentSpaceCenter()
            self.sc.setRaw(text)

    
    def randomize_list(self, word_list):
        return iter(random.sample(word_list, len(word_list)))


    def check_encoded(self, gname):
        escape_set = {'slash'}  # 'backslash'
        if gname in self.font.keys():
            if gname in escape_set or self.font[gname].unicodes == ():
                return False
            else: 
                return True
        else:
            return False


    def get_pair_to_char(self, pair):
        '''
        Converts glyph names to characters, in order to find words in dictionary.
        '''

        def remove_suffix(gname):
            '''
            Removes the suffix from a glyph name.
            '''
            period_pos = gname.find('.')
            return gname[:period_pos] if period_pos > 0 else gname
        
        try:
            left_no_suffix = remove_suffix(pair[0])
            right_no_suffix = remove_suffix(pair[1])
            return self.get_pair_string((left_no_suffix, right_no_suffix))
        except:
            if self.debug:
                print('Couldn’t convert pair to chars.')
            return pair


    def get_gname_from_char(self, char):
        uni = ord(char)
        gname = str(get_key(GN2UV, uni))
        return gname


    def get_pair_string(self, pair):
        return self.gname_to_sc_string(pair[0]), self.gname_to_sc_string(pair[1])


    def gname_to_sc_string(self, gname, chr_only=False):
        if not self.check_encoded(gname) and not chr_only:
            sc_string = '/' + gname + ' '
        else:
            uni = self.font[gname].unicodes[0]
            char = chr(uni)
            sc_string = char
        return sc_string 


    def get_spacing_string(self, pair_string):
        context = get_setting_from_defaults('context')

        context_strings = {
            1: 'HH__HO__OH__OO__HH',     # 'UC' context
            2: 'nn__no__on__oo__nn',     # 'LC' context
            3: '11__10__01__00__11',     # 'Figs' context
            4: '11__/10/__01__/00/__11'  # 'Frac' context
        }

        # If it's not set to Auto context, then just pull the context from above.
        if not context == 0:
            string = context_strings[context].replace('__', pair_string)

            # Not sure what this is, but keeping it in
            if context == 4:
                if pair_string.startswith('⁄'):  # fraction at start of pair
                    string = '11/eight.numr ' + pair_string + ' 10/one.numr ' + pair_string + '00'
                elif pair_string.endswith('⁄'):  # fraction at end of pair
                    string = '11' + pair_string + '/eight.dnom 10' + pair_string + '/eight.dnom 00'

        # Auto (Need to support suffixed here.)
        else:
            # Figures
            if bool(set(pair_string) & set("0123456789")):  # A check to see if any side of the pair is a figure
                string = context_strings[3].replace('__', pair_string)
            # UC
            elif pair_string == pair_string.upper():
                string = context_strings[1].replace('__', pair_string)
            # lc
            else:
                string = context_strings[2].replace('__', pair_string)
            # Support Fractions later

        return string + '\\n'



    open_close_pairs = {
        # Initial/final punctuation (from https://www.compart.com/en/unicode/category/Pi and https://www.compart.com/en/unicode/category/Pf)
        "’": "‘",
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
        #"”": "”",  # These will make two contexts show up for quotes so leaving them off for now
        #"’": "’",

        # Miscellaneous but common open/close pairs
        "'": "'",
        '"': '"',
        "¡": "!",
        "¿": "?",
        "←": "→",
        "→": "←",
        "/": "\\",
        
        "<": ">",  # less, greater
        ">": "<",  # greater, less

        # Opening/closing punctuation (from https://www.compart.com/en/unicode/category/Ps & https://www.compart.com/en/unicode/category/Pe)
        "(": ")",
        "[": "]",
        "{": "}",
        "༺": "༻", "༼": "༽", "᚛": "᚜", "‚": "‘", "„": "“", "⁅": "⁆", "⁽": "⁾", "₍": "₎", "⌈": "⌉", "⌊": "⌋", "〈": "〉", "❨": "❩", "❪": "❫", "❬": "❭", "❮": "❯", "❰": "❱", "❲": "❳", "❴": "❵", "⟅": "⟆", "⟦": "⟧", "⟨": "⟩", "⟪": "⟫", "⟬": "⟭", "⟮": "⟯", "⦃": "⦄", "⦅": "⦆", "⦇": "⦈", "⦉": "⦊", "⦋": "⦌", "⦍": "⦎", "⦏": "⦐", "⦑": "⦒", "⦓": "⦔", "⦕": "⦖", "⦗": "⦘", "⧘": "⧙", "⧚": "⧛", "⧼": "⧽", "⸢": "⸣", "⸤": "⸥", "⸦": "⸧", "⸨": "⸩", "〈": "〉", "《": "》", "「": "」", "『": "』", "【": "】", "〔": "〕", "〖": "〗", "〘": "〙", "〚": "〛", "〝": "〞", "⹂": "〟", "﴿": "﴾", "︗": "︘", "︵": "︶", "︷": "︸", "︹": "︺", "︻": "︼", "︽": "︾", "︿": "﹀", "﹁": "﹂", "﹃": "﹄", "﹇": "﹈", "﹙": "﹚", "﹛": "﹜", "﹝": "﹞", "（": "）", "［": "］", "｛": "｝", "｟": "｠", "｢": "｣",
    }

    # Note: Handle this programmatically (support any suffix) in the future, rather than hard-coding suffixes.
    open_close_pairs_unencoded = {
        "parenleft.uc": "parenright.uc", 
        "bracketleft.uc": "bracketright.uc", 
        "braceleft.uc": "braceright.uc", 
        "exclamdown.uc": "exclam.uc", 
        "questiondown.uc": "question.uc", 
        "guilsinglleft.uc": "guilsinglright.uc",
        "guillemotleft.uc": "guillemotright.uc",

        "guilsinglright.uc": "guilsinglleft.uc",
        "guillemotright.uc": "guillemotleft.uc",

        "slash": "backslash",  # Should be encoded but adding here because those aren't working for some reason
        "backslash": "slash",  # Should be encoded but adding here because those aren't working for some reason
    }

    def make_open_close_context(self, pair):
        '''
        Returns a string of the pair within an open/close context, to judge the symmetry of open/close kerns.
        '''

        # Get all unicodes to make sure we don’t show pairs that don’t exist in the font
        unis_in_font = [u for glyph in CurrentFont() for u in glyph.unicodes]

        # Left and right, to compare against the dictionary
        left, right = self.gname_to_sc_string(pair[0], chr_only=True),  self.gname_to_sc_string(pair[1], chr_only=True)
        # Left and right, to add to the Space Center
        l_sc, r_sc  = self.gname_to_sc_string(pair[0], chr_only=False), self.gname_to_sc_string(pair[1], chr_only=False)
        is_left_encoded  = self.check_encoded(pair[0])
        is_right_encoded = self.check_encoded(pair[1])

        print('MM2SC open/close info:', pair, left, right, "\tHave unicodes?:", is_left_encoded, is_right_encoded)

        # Stop if the glyphs aren't open/close
        if not left in self.open_close_pairs.keys() and not left in self.open_close_pairs.values():
            if not right in self.open_close_pairs.keys() and not right in self.open_close_pairs.values():
                return ''

        open_close_string = ''
        if is_left_encoded and is_right_encoded:
            for open_close_pair in self.open_close_pairs.items():
                if open_close_pair == (left, right):
                    # print('Debug: Open/Close situation 1')
                    open_close_string = l_sc + r_sc
                    break
                elif open_close_pair == (right, left):
                    # print('Debug: Open/Close situation 2')
                    open_close_string = r_sc + l_sc
                    break

                # Open and close
                elif open_close_pair[0] == left and ord(open_close_pair[1]) in unis_in_font:
                    # print('Debug: Open/Close situation 3')
                    open_close_string = l_sc + r_sc + self.open_close_pairs[left]
                    break
                elif open_close_pair[1] == right and ord(open_close_pair[0]) in unis_in_font:
                    # print('Debug: Open/Close situation 4')
                    open_close_string = get_key(self.open_close_pairs, right) + l_sc + r_sc
                    break

                # Now close and open
                elif open_close_pair[0] == right and ord(open_close_pair[1]) in unis_in_font:
                    # print('Debug: Open/Close situation 5')
                    open_close_string = self.open_close_pairs[right] + l_sc + r_sc
                    break
                elif open_close_pair[1] == left and ord(open_close_pair[0]) in unis_in_font:
                    # print('Debug: Open/Close situation 6')
                    open_close_string =  l_sc + r_sc + get_key(self.open_close_pairs, left)
                    break

        # Handle unencoded glyph names
        else:
            # Note: Handle this programmatically (support any suffix) in the future, rather than hard-coding suffixes.
            for gname_pair in self.open_close_pairs_unencoded.items():
                if gname_pair[0] in self.open_close_pairs_unencoded.items() and gname_pair[1] in self.open_close_pairs_unencoded.items(): # If both are in there:
                    # print('Debug: Open/Close situation 7')
                    open_close_string += self.gname_to_sc_string(gname_pair[1]) + self.gname_to_sc_string(gname_pair[0]) + self.gname_to_sc_string(gname_pair[1]) + self.gname_to_sc_string(gname_pair[0])
                    break
                elif pair[0] == gname_pair[0]:
                    # print('Debug: Open/Close situation 8')
                    open_close_string += l_sc + r_sc + self.gname_to_sc_string(gname_pair[1])
                    break
                elif pair[1] == gname_pair[1]:
                    # print('Debug: Open/Close situation 9')
                    open_close_string += self.gname_to_sc_string(gname_pair[0]) + l_sc + r_sc
                    break
                # Now reverse to close/open
                elif pair[0] == gname_pair[1]:
                    # print('Debug: Open/Close situation 10')
                    open_close_string += l_sc + r_sc + self.gname_to_sc_string(gname_pair[0])
                    break
                elif pair[1] == gname_pair[0]:
                    # print('Debug: Open/Close situation 11')
                    open_close_string += self.gname_to_sc_string(gname_pair[1]) + l_sc + r_sc
                    break

        print('Open/close string:', open_close_string)
        return open_close_string + ' '
           

    def pair_mirrored(self, pair):
        '''
        Returns a string of the pair mirrored, to judge the symmetry of kerns.
        '''

        left, right = self.get_pair_string(pair)
        return left + right + left + right + '  ' 


    def words_for_pair(self, ):
        '''
        Generates all output text and puts it in Space Center.
        '''

        # Store settings in variables so the function only needs to be called once
        language           = get_setting_from_defaults('language')
        word_count         = int(get_setting_from_defaults('wordCount'))
        all_uppercase      = get_setting_from_defaults('allUppercase')
        list_output        = get_setting_from_defaults('listOutput')
        mirrored_pair      = get_setting_from_defaults('mirroredPair')
        open_close_context = get_setting_from_defaults('openCloseContext')
        context            = get_setting_from_defaults('context')
        
        # Try getting pair_string once in order to check if encoded
        pair_string = ''.join(list(self.get_pair_string(self.pair)))

        # Convert MM tuple into search pair to check uc, lc, mixed case
        pair_to_char_string = ''.join(self.get_pair_to_char(self.pair))

        # Search for non-suffixed
        search_string = ''.join(chr(self.font[gname.split('.')[0]].unicode) for gname in self.pair)

        # Get the spacing string
        spacing_string = self.get_spacing_string(pair_string)

        # Check if string is uppercase
        if pair_to_char_string.isupper():
            make_upper = True
            search_string = search_string.lower()
        else:
            make_upper = False

        # Check for mixed case
        mixed_case = False
        pair_chars = self.get_pair_to_char(self.pair)
        is_left_encoded = self.check_encoded(self.pair[0])
        is_right_encoded = self.check_encoded(self.pair[1])
        if pair_chars[0].isupper() and pair_chars[1].islower() and is_left_encoded and is_right_encoded:
            mixed_case = True

        # Get all the words from the text file
        all_words = []
        if language == len(self.text_files):  # Use all languages
            for i in len(self.text_files):
                # If any language: concatenate all the word lists
                all_words.extend(self.dict_words[self.text_files[i]])
        else:
            all_words = self.dict_words[self.text_files[language]]

        # Add words to the word list until we reach the desired amount of words
        # Currently allows any word length. This could be customized later.
        count = 0
        word_list = []
        word_set = set(word_list)
        for word in self.randomize_list(all_words):
            if search_string in word and word not in word_set:
                word_set.add(word)
                word_list.append(word)
                count += 1

            # Try capitalizing lowercase words
            elif mixed_case and search_string.lower() in word[:2]:
                word = word.capitalize()
                if word not in word_set:
                    word_set.add(word)
                    word_list.append(word)
                    count += 1

            if count >= word_count:
                break

        if all_uppercase or make_upper:
            # Make text uppercase again
            word_list = [text.upper() for text in word_list]

        words_text = ''
        # If there are sample words
        if word_list:
            if list_output: # If 'Output as list' is checked:
                sorted_text = self.sort_words_by_width(word_list)
                join_string = '\\n'
                words_text = join_string.join(map(str, sorted_text))
            else:
                words_text = ' '.join(map(str, word_list))

            words_text = words_text.lstrip()
            words_text = words_text.replace(pair_to_char_string, '/'+'/'.join(self.pair)+' ' )
        # If there are no sample words, add some failure text in the place of words text.
        else:
            words_text = f'There are no words for pair: {pair_string}'
            
        # If you want your pair mirrored
        mirror_text = ''
        if mirrored_pair:
            mirror_text = self.pair_mirrored(self.pair)

        # If you want your pair in an open/close context
        open_close_text = ''
        if open_close_context:
            open_close_text = self.make_open_close_context(self.pair)

        text = ' '.join([mirror_text, open_close_text, spacing_string]) + words_text
        text = text.lstrip()
        text = re.sub(r'\s{3,}', '  ', text)  # Replace any 3+ spaces with 2 spaces. We keep 2 spaces, because of /glyphnames_
        self.set_space_center(self.font, text)








# ========== MM2SC Preferences Popover (Made with EZUI) ========== #

class MM2SpaceCenterPopover(ezui.WindowController):
    
    
    def build(self, parent, space_center):

        self.sc = space_center

        content = '''
        [ ] Activate MM2SC                 @activateToggle
        
        ---------------
        
        * TwoColumnForm @form

        > : Max word count:
        > [_30               _]            @wordCount
        
        > : Language:
        > (English ...)                    @language

        > : Fallback context:
        > (Auto ...)                       @context
        
        ---------------

        [ ] Make words all-caps            @allUppercase
        [ ] Output as list sorted by width @listOutput
        [X] Show mirrored pair (LRLR)      @mirroredPair
        [X] Show open & close context {n}  @openCloseContext
        '''
        
        initial_word_count = 30
        context_options = ['Auto', 'UC', 'LC', 'Figs', 'Frac']
        language_names = ['Catalan', 'Czech', 'Danish', 'Dutch', 'English', 'Finnish', 'French', 'German', 'Hungarian', 'Icelandic', 'Italian', 'Latin', 'Norwegian', 'Polish', 'Slovak', 'Spanish', 'Vietnamese syllables']

        descriptionData = dict(
            form=dict(
                titleColumnWidth=104,
                itemColumnWidth=78
            ),
            # wordCount=dict(
            #         continuous=False,
            # ),
            language=dict(
                    items=language_names
            ),
            context=dict(
                    items=context_options
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
            size='auto'
        )
        self.wordCountField   = self.w.getItem('wordCount')
        self.wordCountField.set(initial_word_count)
        # May not need these:
        self.activateToggle   = self.w.getItem('activateToggle')
        self.languageField    = self.w.getItem('language')
        self.contextField     = self.w.getItem('context')
        self.listOutput       = self.w.getItem('listOutput')
        self.openCloseContext = self.w.getItem('openCloseContext')
        self.mirroredPair     = self.w.getItem('mirroredPair')
        self.allUppercase     = self.w.getItem('allUppercase')
    
    def flush_and_register_defaults(self):
        setExtensionDefault(EXTENSION_KEY, {})  # This might not be necessary anymore.
        setExtensionDefault(EXTENSION_KEY, self.w.getItemValues(), validate=True)
        print(getExtensionDefault(EXTENSION_KEY))  # Print a readout of the user’s updated MM2SC settings

    def started(self):
        self.w.open()
        values = getExtensionDefault(EXTENSION_KEY, fallback=self.w.getItemValues())
        self.w.setItemValues(values)  # Set the previous preferences from user
        
    def activateToggleCallback(self, sender):
        self.flush_and_register_defaults()
        activation = sender.get()
        # Can no longer activate the actual observer from this pref menu object/class
        if activation == True:
            print(f'MM2SpaceCenter is now set to Active.')
        else:
            print(f'MM2SpaceCenter is now set to Inactive.')
        # Update the Space Center here somehow?
        
    def contextCallback(self,sender):
        self.flush_and_register_defaults()
    def listOutputCallback(self,sender):
        self.flush_and_register_defaults()  
    def openCloseContextCallback(self,sender):
        self.flush_and_register_defaults()  
    def mirroredPairCallback(self,sender):
        self.flush_and_register_defaults()  
    def allUppercaseCallback(self,sender):
        self.flush_and_register_defaults()  
    def sortedCallback(self, sender):
        self.flush_and_register_defaults()
    def wordCountCallback(self,sender):
        self.flush_and_register_defaults()
    def languageCallback(self,sender):
        self.flush_and_register_defaults()  
        # Update the Space Center here somehow?

    
        
registerSpaceCenterSubscriber(MM2SC_Tool)
