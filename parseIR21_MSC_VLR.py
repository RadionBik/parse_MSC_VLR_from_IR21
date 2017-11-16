import re
import glob
import os

def readIrregularOperators(filename):
    '''
    readIrregularOperators() reads filenames from a file with
    irregular operators and creates a list with ID's of the operators. 
    irregularOperators --- a list of operators whose the GT's 2nd part need 
    concatenating with the 1st, e.g. 111112641 / 333 <-- so 333 can not be the 
    last value in the range (111112641,111112333), but a suffix to 111112641, so 
    the result will be 111112641333
    '''
    
    file=open('irregularOperators.conf')
    content=file.read()
    files=content.splitlines()
    keys=[]
    print('Irregular files:')
    for filename in files:
        print(filename)
        keys.append(filename.split(' ')[0])
    return keys

def parseIR21txt(path):
    '''
    parseIR21txt() parses converted with 'pdftottext' IR.21 files [1] with aim to extract 
    Global titles (GT) of operators' VLRs or MSCs (if no VLR available) and 
    produces a .csv file with operators' IDs and the GTs.
    
    2 regular expressions have been developed:
    -- 'vlrReg' checks for presence of VLR with possible prefixes/suffixes, and GTs
    -- 'mscReg' checks for presence of MSC withOUT possible prefixes/suffixes, 
    and GTs if no VLR-entries has been found
    
    [1] -- use the "find . -iname '*.pdf' -exec pdftotext "{}" \;" command inside 
    the directory with the IR.21 pdf-files to convert the PDFs to .txt
    '''
    
    #            1       2                 3         4 w/lookAhead no-2-digits-in-row 5              6                      7
    vlrReg='(MS[CS]/)?(VLR)(-[23]G\n{,2}\+[23]G|-[23]G)?(\n{,2}\w+(?=\D{2,})\n)?(\n)*((?!\s?[12][01368]\s)\d[\d\ ]+)+([/\n\ \d]*)'
    #vlrReg='(MS[CS]/)?(VLR)(-[23]G\n{,2}\+[23]G|-[23]G)?(\n{,2}\w+(?=\D{2,})\n)?(\n)*(\d[\d\ ]+)+([/\n\ \d]*)'
    #            1       2                 3                         4              5     6            7
    mscReg='([^SM]MSC)(/VLR)?(-[23]G\n{,2}\+[23]G|-[23]G)?(\n{,2}\w+(?=\D{2,})\n)?(\n)*(\d[\d\ ]+)+([/\n\ \d]*)'
    #'list' with IR21 files not containing any VLR or MSC entries
    emptyFiles=[]
    #'dict' with an operator's ID as a key and its GTs as values 
    operator_MSC_VLR_raw={}
    keys=[]
    for filename in glob.glob(os.path.join(path, '*.txt')):
        #save operators IDs to a list
        key=filename.split('/')[1].split('.')[0].split(' ')[0]
        keys.append(key)
        #read content from the txt file
        file=open(filename)
        content=file.read()
        pattern=re.compile(vlrReg,re.DOTALL)
        vlrFound=re.findall(pattern,content)
        if vlrFound!=[]:
            operator_MSC_VLR_raw.update({key:vlrFound})
        else:
            mscFound=re.findall(mscReg,content)
            if mscFound!=[]:
                operator_MSC_VLR_raw.update({key:mscFound})
            else:
                #print('Look inside, need your attention!')
                emptyFiles.append(filename.split('/')[1].split('.')[0])
    
    return operator_MSC_VLR_raw,emptyFiles


def processGT(gt,irregularOperators):
    '''
    processGT() process individual entries found with the RegEx, accounting
    for operators, that defined the entries irregulary:
        1. Selectes only numerical values
        2. Removes whitespaces
        3. Concatenates parts of the GT
        4. Removes excess digits from a GT defined as a range, e.g. 
           111222000,111222999 --> 111222
               or
           111222100,111222999 --> 1112221,1112229
    '''
    #find only numerical values
    gt=re.findall('[\d ]+',''.join(list(entry[5:])))
    #remove all whitespaces
    gt=["".join(i.split()) for i in gt]
    if len(gt)==3:    
        gt=[gt[0]+gt[1],gt[0]+gt[2]]
    if len(gt)==2:
        #if 2nd term consist of more than 3 zeros
        if (re.match('0{3,}',gt[1]) and int(gt[1])==0):
            gt=[gt[0]+gt[1]]
        #if 2nd term is the same then remove it
        elif gt[0].endswith(gt[1]):
            gt.pop()
        else:
            if key in irregularOperators:
                gt=[gt[0]+gt[1]]
            else:
                #concatenate the 2nd term with prefix of the 1st
                gt[1]=gt[0][:-len(gt[1])]+gt[1]
            #check if we can remove redundant digits from the range
            if len(gt)>1:
                while(gt[1].endswith('9') and gt[0].endswith('0')):
                    gt[1]=gt[1][:-1]
                    gt[0]=gt[0][:-1]
                if (gt[1]==gt[0]):
                    gt.pop()

    return gt

def removeSubsetGT(GTs):
    '''
    removeSubsetGT() removes GTs entries that are subset of another within 
    the operator
    '''
    uniqueGTs=[]
    subsetGTs=[]
    for gt in GTs:
        for checkGT in GTs:
            if checkGT[0].startswith(gt[0]) and checkGT[0]!=gt[0]:
                subsetGTs.append(checkGT)
        if gt not in subsetGTs:
            uniqueGTs.append(gt)
    return uniqueGTs
 
def expandRangeGTandConvertToInt(GTs):
    '''
    expandRangeGTandConvertToInt() expands GTs defined as a range to a list, 
    also converts them from ['111222..000'] to the numeric form: 111222..000  
    '''
    expandedGTs=[]     
    for gt in GTs:
        if len(gt)==2:
            for subGT in range(int(gt[0]),int(gt[1])+1):
                expandedGTs.append(subGT)
        else:
            expandedGTs.append(int(gt[0]))
    return expandedGTs

def printGTsToFile(results,filename):
    '''
    printGTsToFile() takes dict with the results and destination file name 
    and prints the dict to .csv-compatible format   
    '''
    with open(filename, 'w') as f:
        for key in results.keys():
            for foundGTs in results[key]:
                print(key,';',foundGTs,file=f)

pathToFiles='allPartners2017-11-01'

irregularOperatorsFile='irregularOperators.conf'
irregularOperators=readIrregularOperators(irregularOperatorsFile)

operator_MSC_VLR_raw,emptyFiles=parseIR21txt(pathToFiles)

#get actual keys, accounting for the IR21s that don't contain any MSC/VLR entries  
actualKeys=list(operator_MSC_VLR_raw.keys())
resultsRaw = dict()
resultsCleaned = dict()

for key in actualKeys:
    #collect parsed with the RegEx entries to the dict
    resultsRaw.update({key:operator_MSC_VLR_raw[key]})
    
    foundGTs=[]        
    for entry in operator_MSC_VLR_raw[key]:
        gtMod=processGT(entry,irregularOperators)
        #find unique entries
        if gtMod not in foundGTs:
            foundGTs.append(gtMod)

    #process the GTs
    noSubsetGTs=removeSubsetGT(foundGTs)
    cleanGTs=expandRangeGTandConvertToInt(noSubsetGTs)
    resultsCleaned.update({key:cleanGTs})
    ##

       
print('Operators without any MSCs and VLRs:')
for faultyOperator in emptyFiles:
    print(faultyOperator)
printGTsToFile(resultsRaw,'outVLRraw.csv')
printGTsToFile(resultsCleaned,'outVLRcleanedCheck.csv')

print('Found {} raw entries'.format(sum([len(resultsRaw[key]) for key in actualKeys])))
print('Resulting entries: {}'.format(sum([len(resultsCleaned[key]) for key in actualKeys])))
