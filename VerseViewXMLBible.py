#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# VerseViewXMLBible.py
#
# Module handling VerseView XML Bibles
#
# Copyright (C) 2015 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module reading and loading VerseView XML Bibles:
    <?xml version="1.0" encoding="utf-8" standalone="yes"?>
    <bible>
    <fname>finnish_1938.xml</fname>
    <revision>1</revision>
    <title>Finnish (1938)</title>
    <font>Arial,Helvetica,sans-serif,Calibri</font>
    <copyright>Public Domain</copyright>
    <sizefactor>1</sizefactor>
    <b n="Genesis">
        <c n="1">
        <v n="1">
    Alussa loi Jumala taivaan ja maan.</v>
        <v n="2">
    Ja maa oli autio ja tyhjä, ja pimeys oli syvyyden päällä, ja Jumalan Henki liikkui vetten päällä.</v>
    ...


    <?xml version="1.0" encoding="UTF-8"?>
    <bible>
    <fname>portuguese-almeida-recebida.xml</fname>
    <revision>3</revision>
    <title>Almeida Recebida (Bíblia em Português)</title>
    <font>Arial,Helvetica,sans-serif,Calibri</font>
    <copyright>Public Domain</copyright>
    <sizefactor>1</sizefactor>
    <b n="Gênesis">
        <c n="1">
        <v n="1">No princípio criou Deus os céus e a terra.</v>
        <v n="2">E a terra estava sem forma e vazia; e havia trevas sobre a face do abismo, e o Espírito de Deus pairava sobre a face das águas.</v>
        <v n="3">E disse Deus: haja luz. E houve luz.</v>
    ...
"""

from gettext import gettext as _

LastModifiedDate = '2015-06-01' # by RJH
ShortProgName = "VerseViewBible"
ProgName = "VerseView XML Bible format handler"
ProgVersion = '0.13'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os
from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals
from BibleOrganizationalSystems import BibleOrganizationalSystem
from Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML', 'JAR',
                    'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'STY', 'SSF', 'TXT', 'USFM', 'USFX', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def VerseViewXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for VerseView XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one VerseView Bible is found,
        returns the loaded VerseViewXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "VerseViewXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if BibleOrgSysGlobals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("VerseViewXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("VerseViewXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " VerseViewXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories
    #print( 'ff', foundFiles )

    # See if there's an VerseView project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<3: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "HB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if '<bible>' not in firstLines[1]: continue
            if '<fname>' not in firstLines[2]: continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "VerseViewXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad and autoLoadBooks):
            ub = VerseViewXMLBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    VerseViewXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundSubfiles.append( something )
        #print( 'fsf', foundSubfiles )

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=3 )
                if not firstLines or len(firstLines)<3: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "VVB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if '<bible>' not in firstLines[1]: continue
                if '<fname>' not in firstLines[2]: continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "VerseViewXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert( len(foundProjects) == 1 )
            ub = VerseViewXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
# end of VerseViewXMLBibleFileCheck



class VerseViewXMLBible( Bible ):
    """
    Class for reading, validating, and converting VerseViewXMLBible XML.
    """
    XMLNameSpace = "{http://www.w3.org/2001/XMLSchema-instance}"
    treeTag = 'bible'
    filenameTag = 'fname'
    revisionTag = 'revision'
    titleTag = 'title'
    fontTag = 'font'
    copyrightTag = 'copyright'
    sizefactorTag = 'sizefactor'
    bookTag = 'b'
    chapterTag = 'c'
    verseTag = 'v'


    def __init__( self, sourceFolder, givenName, encoding='utf-8' ):
        """
        Constructor: just sets up the VerseView Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "VerseView XML Bible object"
        self.objectTypeString = "VerseView"

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.givenName )

        self.tree = self.header = None # Will hold the XML data

        # Get the data tables that we need for proper checking
        #self.ISOLanguages = ISO_639_3_Languages().loadData()
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            print( "VerseViewXMLBible: File {!r} is unreadable".format( self.sourceFilepath ) )

        self.name = self.givenName
        #if self.name is None:
            #pass
    # end of VerseViewXMLBible.__init__


    def load( self ):
        """
        Load a single source XML file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        self.tree = ElementTree().parse( self.sourceFilepath )
        if BibleOrgSysGlobals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['VerseView'] = {}

        # Find the main (bible) container
        if self.tree.tag == VerseViewXMLBible.treeTag:
            location = "VerseView XML file"
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoAttributes( self.tree, location, 'js24' )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location, '1wk8' )

            # Find the submain (various info and then book) containers
            bookNumber = 0
            for element in self.tree:
                if element.tag == VerseViewXMLBible.filenameTag:
                    sublocation = "filename in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    #self.filename = element.text
                elif element.tag == VerseViewXMLBible.revisionTag:
                    sublocation = "revision in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Revision'] = element.text
                elif element.tag == VerseViewXMLBible.titleTag:
                    sublocation = "title in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Title'] = element.text
                elif element.tag == VerseViewXMLBible.fontTag:
                    sublocation = "font in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Font'] = element.text
                elif element.tag == VerseViewXMLBible.copyrightTag:
                    sublocation = "copyright in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    self.suppliedMetadata['VerseView']['Copyright'] = element.text
                elif element.tag == VerseViewXMLBible.sizefactorTag:
                    sublocation = "sizefactor in " + location
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'jk86' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'hjk7' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'bh09' )
                    if BibleOrgSysGlobals.debugFlag: assert( element.text == '1' )
                elif element.tag == VerseViewXMLBible.bookTag:
                    sublocation = "book in " + location
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'g3g5' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'd3f6' )
                    bookNumber += 1
                    self.__validateAndExtractBook( element, bookNumber )
                else: logging.error( "xk15 Expected to find {!r} but got {!r}".format( VerseViewXMLBible.bookTag, element.tag ) )
        else: logging.error( "Expected to load {!r} but got {!r}".format( VerseViewXMLBible.treeTag, self.tree.tag ) )

        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            # These are all compulsory so they should all exist
            #print( "Filename is {!r}".format( self.filename ) )
            print( "Revision is {!r}".format( self.suppliedMetadata['VerseView']['Revision'] ) )
            print( "Title is {!r}".format( self.suppliedMetadata['VerseView']['Title'] ) )
            print( "Font is {!r}".format( self.suppliedMetadata['VerseView']['Font'] ) )
            print( "Copyright is {!r}".format( self.suppliedMetadata['VerseView']['Copyright'] ) )
            #print( "SizeFactor is {!r}".format( self.sizeFactor ) )

        self.applySuppliedMetadata( 'VerseView' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of VerseViewXMLBible.load



    def __validateAndExtractBook( self, book, bookNumber ):
        """
        Check/validate and extract book data from the given XML book record
            finding chapter subelements.
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Validating XML book...") )

        # Process the div attributes first
        BBB = bookName = None
        for attrib,value in book.items():
            if attrib=="n":
                bookName = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in book element".format( attrib, value ) )

        if bookName:
            BBB = self.genericBOS.getBBB( bookName )
        if BBB is None:
            adjustedBookName = BibleOrgSysGlobals.removeAccents( bookName )
            if adjustedBookName != bookName:
                BBB = self.genericBOS.getBBB( adjustedBookName )
        BBB2 = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromReferenceNumber( bookNumber )
        if BBB2 != BBB: # Just double check using the book number
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "Assuming that book {} {!r} is {} (not {})".format( bookNumber, bookName, BBB2, BBB ) )
            BBB = BBB2
            #print( BBB ); halt

        if BBB:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Validating {} {}...").format( BBB, bookName ) )
            thisBook = BibleBook( self, BBB )
            thisBook.objectNameString = "VerseView XML Bible Book object"
            thisBook.objectTypeString = "VerseView"
            #thisBook.sourceFilepath = self.sourceFilepath
            for element in book:
                if element.tag == VerseViewXMLBible.chapterTag:
                    sublocation = "chapter in {}".format( BBB )
                    BibleOrgSysGlobals.checkXMLNoText( element, sublocation, 'j3jd' )
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'al1d' )
                    self.__validateAndExtractChapter( BBB, thisBook, element )
                else: logging.error( "vb26 Expected to find {!r} but got {!r}".format( VerseViewXMLBible.chapterTag, element.tag ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Saving {} into results...".format( BBB ) )
            self.saveBook( thisBook )
    # end of VerseViewXMLBible.__validateAndExtractBook


    def __validateAndExtractChapter( self, BBB, thisBook, chapter ):
        """
        Check/validate and extract chapter data from the given XML book record
            finding and saving chapter numbers and
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BibleOrgSysGlobals.verbosityLevel > 3:
            print( _("Validating XML chapter...") )

        # Process the chapter attributes first
        chapterNumber = numVerses = None
        for attrib,value in chapter.items():
            if attrib=="n":
                chapterNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in chapter element".format( attrib, value ) )
        if chapterNumber:
            #print( BBB, 'c', chapterNumber )
            thisBook.addLine( 'c', chapterNumber )
        else: logging.error( "Missing 'n' attribute in chapter element for BBB".format( BBB ) )

        for element in chapter:
            if element.tag == VerseViewXMLBible.verseTag:
                location = "verse in {} {}".format( BBB, chapterNumber )
                self.__validateAndExtractVerse( BBB, chapterNumber, thisBook, element )
            else: logging.error( "sv34 Expected to find {!r} but got {!r}".format( VerseViewXMLBible.verseTag, element.tag ) )
    # end of VerseViewXMLBible.__validateAndExtractChapter


    def __validateAndExtractVerse( self, BBB, chapterNumber, thisBook, verse ):
        """
        Check/validate and extract verse data from the given XML book record
            finding and saving verse elements.
        """

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BibleOrgSysGlobals.verbosityLevel > 3:
            print( _("Validating XML verse...") )

        location = "verse in {} {}".format( BBB, chapterNumber )
        BibleOrgSysGlobals.checkXMLNoTail( verse, location, 'l5ks' )

        # Handle verse attributes
        verseNumber = toVerseNumber = None
        for attrib,value in verse.items():
            if attrib=="n":
                verseNumber = value
            else: logging.warning( "Unprocessed {!r} attribute ({}) in verse element".format( attrib, value ) )
        if BibleOrgSysGlobals.debugFlag: assert( verseNumber )
        location = "{}:{}".format( location, verseNumber ) # Get a better location description
        #thisBook.addLine( 'v', verseNumber )
        vText = '' if verse.text is None else verse.text
        if vText: vText = vText.strip()
        #if not vText: # This happens if a verse starts immediately with a style or note
            #logging.warning( "{} {}:{} has no text".format( BBB, chapterNumber, verseNumber ) )

        # Handle verse subelements (notes and styled portions)
        for subelement in verse:
            if subelement.tag == VerseViewXMLBible.noteTag:
                sublocation = "note in " + location
                noteType = None
                for attrib,value in subelement.items():
                    if attrib=="type": noteType = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if noteType and noteType not in ('variant',):
                    logging.warning( "Unexpected {} note type in {}".format( noteType, BBB ) )
                nText, nTail = subelement.text, subelement.tail
                #print( "note", BBB, chapterNumber, verseNumber, noteType, repr(nText), repr(nTail) )
                vText += "\\f + \\fk {} \\ft {}\\f*".format( noteType, nText ) if noteType else "\\f + \\ft {}\\f*".format( nText )
                if nTail:
                    if '\n' in nTail:
                        print( "VerseViewXMLBible.__validateAndExtractVerse: nTail {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, nTail ) )
                        nTail = nTail.replace( '\n', ' ' )
                    vText += nTail
                for subsubelement in subelement:
                    if subsubelement.tag == VerseViewXMLBible.styleTag:
                        subsublocation = "style in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( subsubelement, subsublocation, 'fyt4' )
                        fs = css = idStyle = None
                        for attrib,value in subsubelement.items():
                            if attrib=='fs': fs = value
                            #elif attrib=="css": css = value
                            #elif attrib=="id": idStyle = value
                            else: logging.warning( "Unprocessed {!r} attribute ({}) in style subsubelement".format( attrib, value ) )
                        if BibleOrgSysGlobals.debugFlag: assert( fs or css or idStyle )
                        SFM = None
                        if fs == 'italic': SFM = '\\it'
                        elif fs == 'super': SFM = '\\bdit'
                        elif fs == 'emphasis': SFM = '\\em'
                        else: print( "fs is", fs, "css is", css, "idStyle is", idStyle ); halt
                        #if css == "font-style:italic": SFM = '\\it'
                        #elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                        #elif css == "color:#FF0000": SFM = '\\em'
                        #elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                        #elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                        #else: print( "css is", css, "idStyle is", idStyle ); halt
                        sText, sTail = subsubelement.text.strip(), subsubelement.tail
                        if BibleOrgSysGlobals.debugFlag: assert( sText )
                        if SFM: vText += SFM+' ' + sText + SFM+'*'
                        else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                        if sTail: vText += sTail.strip()
                    else: logging.error( "df20 Expected to find {} but got {!r} in {}".format( VerseViewXMLBible.styleTag, subsubelement.tag, sublocation ) )

            elif subelement.tag == VerseViewXMLBible.styleTag:
                sublocation = "style in " + location
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'f5gh' )
                fs = css = idStyle = None
                for attrib,value in subelement.items():
                    if attrib=="fs": fs = value
                    #elif attrib=="css": css = value
                    #elif attrib=="id": idStyle = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert( fs )
                SFM = None
                if fs == 'super': SFM = '\\bdit'
                elif fs == 'emphasis': SFM = '\\em'
                else: print( "fs is", fs, "css is", css, "idStyle is", idStyle ); halt
                #if css == "font-style:italic": SFM = '\\it'
                #elif css == "font-style:italic;font-weight:bold": SFM = '\\bdit'
                #elif css == "color:#FF0000": SFM = '\\em'
                #elif css == "font-size: x-small; color:#8B8378": SFM = '\\add'
                #elif css is None and idStyle=='cl:divineName': SFM = '\\nd'
                #else: print( "css is", css, "idStyle is", idStyle ); halt
                sText, sTail = subelement.text.strip(), subelement.tail
                if BibleOrgSysGlobals.debugFlag: assert( sText )
                #print( BBB, chapterNumber, sublocation )
                if SFM: vText += SFM+' ' + sText + SFM+'*'
                else: vText += '\\sc ' + '['+css+']' + sText + '\\sc* ' # Use sc for unknown styles
                if sTail: vText += sTail.strip()

            elif subelement.tag == VerseViewXMLBible.breakTag:
                sublocation = "line break in " + location
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c1d4' )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'g4g8' )
                art = None
                for attrib,value in subelement.items():
                    if attrib=="art":
                        art = value
                    else: logging.warning( "Unprocessed {!r} attribute ({}) in style subelement".format( attrib, value ) )
                if BibleOrgSysGlobals.debugFlag: assert( art == 'x-nl' )
                #print( BBB, chapterNumber, verseNumber )
                #assert( vText )
                if vText:
                    thisBook.addLine( 'v', verseNumber + ' ' + vText ); verseNumber = None
                    vText = ''
                thisBook.addLine( 'm', subelement.tail.strip() if subelement.tail else '' )
                #bTail = subelement.tail
                #if bTail: vText = bTail.strip()
            else: logging.error( "bd47 Expected to find NOTE or STYLE but got {!r} in {}".format( subelement.tag, location ) )

        if vText: # This is the main text of the verse (follows the verse milestone)
            if '\n' in vText:
                print( "VerseViewXMLBible.__validateAndExtractVerse: vText {} {}:{} {!r}".format( BBB, chapterNumber, verseNumber, vText ) )
                vText = vText.replace( '\n', ' ' )
            thisBook.addLine( 'v', verseNumber + ' ' + vText ); verseNumber = None
    # end of VerseViewXMLBible.__validateAndExtractVerse
# end of VerseViewXMLBible class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    #testFolder = "../../../../../Data/Work/Bibles/OpenSong Bibles/" # These are quite similar
    testFolder = "Tests/DataFilesForTests/VerseViewXML/"

    if 1: # demo the file checking code
        print( "TestA1", VerseViewXMLBibleFileCheck( testFolder ) )
        print( "TestA2", VerseViewXMLBibleFileCheck( testFolder, autoLoad=True ) )


    if 1:
        count = totalBooks = 0
        if os.access( testFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isfile( somepath ) and something.endswith( '.xml' ):
                    count += 1
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nH B{}/ {}".format( count, something ) )
                    vvB = VerseViewXMLBible( testFolder, something )
                    vvB.load()
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( vvB )
                    if BibleOrgSysGlobals.strictCheckingFlag:
                        vvB.check()
                        #UBErrors = UB.getErrors()
                        # print( UBErrors )
                    #print( UB.getVersification () )
                    #print( UB.getAddedUnits () )
                    #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                        ##print( "Looking for", ref )
                        #print( "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
                    if 1: # Test verse lookup
                        import VerseReferences
                        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                                            ('OT','DAN','1','21'),
                                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                            (t, b, c, v) = reference
                            if t=='OT' and len(vvB)==27: continue # Don't bother with OT references if it's only a NT
                            if t=='NT' and len(vvB)==39: continue # Don't bother with NT references if it's only a OT
                            if t=='DC' and len(vvB)<=66: continue # Don't bother with DC references if it's too small
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #print( svk, ob.getVerseDataList( reference ) )
                            try: print( reference, svk.getShortText(), vvB.getVerseText( svk ) )
                            except KeyError: print( something, reference, "doesn't exist" )
                    if BibleOrgSysGlobals.commandLineOptions.export:
                        vvB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    #else:
                        #vvB.toHaggaiXML()
                else: print( "Sorry, skipping {}.".format( something ) )
            if count: print( "\n{} total VerseView Bibles processed.".format( count ) )
        else: print( "Sorry, test folder {!r} is not readable on this computer.".format( testBaseFolder ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of VerseViewXMLBible.py